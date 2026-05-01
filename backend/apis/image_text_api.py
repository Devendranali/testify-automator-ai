# image_text_api.py

import numpy as np
from fastapi import APIRouter, UploadFile, File, HTTPException, Form, Depends, Request
from fastapi.responses import JSONResponse
from typing import Any, List, Optional
from PIL import Image
import os
import zipfile
import tempfile
import json
import base64
import logging
import shutil
from threading import Lock
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from .projects_api import _ensure_project_structure, _project_root, get_current_user, get_user_project
from logic.image_text_extractor import process_image_gpt
from services.graph_service import build_dependency_graph
from utils.match_utils import normalize_page_name
from utils.chroma_client import get_collection
from database.session import get_db
from database.models import Project, ImageMetadata, ImageUploadRun, User, OrganizationMember, TestCaseMetadata
from database.project_storage import DatabaseBackedProjectStorage
from datetime import datetime
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
import re
from utils.request_context import set_request_context, reset_request_context, get_project_context
from utils.project_paths import build_project_context, ProjectContext
from pydantic import BaseModel

load_dotenv()

router = APIRouter()

# Logging (project-scoped; handler initialized per request)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

_MODEL_NAME = "all-MiniLM-L6-v2"
_embedding_function = None
_embedding_function_lock = Lock()
_upload_cancel_lock = Lock()
_upload_cancelled_sessions: set[tuple[int, str]] = set()


class UploadCancelledError(Exception):
    """Raised when an in-flight image upload is cancelled."""


def _normalize_upload_session_id(value: Optional[str]) -> str:
    return str(value or "").strip()


def _mark_upload_cancelled(project_id: int, session_id: Optional[str]) -> None:
    normalized = _normalize_upload_session_id(session_id)
    if not normalized:
        return
    with _upload_cancel_lock:
        _upload_cancelled_sessions.add((int(project_id), normalized))


def _is_upload_cancelled(project_id: int, session_id: Optional[str]) -> bool:
    normalized = _normalize_upload_session_id(session_id)
    if not normalized:
        return False
    with _upload_cancel_lock:
        return (int(project_id), normalized) in _upload_cancelled_sessions


def _clear_upload_cancelled(project_id: int, session_id: Optional[str]) -> None:
    normalized = _normalize_upload_session_id(session_id)
    if not normalized:
        return
    with _upload_cancel_lock:
        _upload_cancelled_sessions.discard((int(project_id), normalized))


def get_sentence_transformer_embedding_function():
    global _embedding_function
    if _embedding_function is not None:
        return _embedding_function

    with _embedding_function_lock:
        if _embedding_function is None:
            try:
                _embedding_function = SentenceTransformerEmbeddingFunction(model_name=_MODEL_NAME)
            except Exception as exc:
                raise RuntimeError(
                    f"Failed to load SentenceTransformer embedding model '{_MODEL_NAME}'. "
                    "Ensure the model is available locally or that outbound model download access is configured."
                ) from exc
    return _embedding_function


def _chroma_collection(chromaPath : str):
    return get_collection(
        chromaPath,
        "element_metadata",
        embedding_function=get_sentence_transformer_embedding_function(),
    )

def _get_active_project(db: Session, current_user: Optional[User] = None) -> Project:
    """Resolve the currently active project using request context."""
    ctx = get_project_context(required=True)
    query = db.query(Project).filter(Project.id == int(ctx.project_id))
    if current_user is not None:
        org_ids = OrganizationMember.user_org_ids(db, current_user.id)
        if not org_ids:
            raise HTTPException(status_code=403, detail="Organization membership required")
        query = query.filter(Project.organization_id.in_(org_ids))
    project = query.first()
    if project:
        return project
    raise HTTPException(status_code=400, detail="Active project not found in database.")


def _serialize_metadata_list(metadata_list: List[dict]) -> List[dict]:
    """Convert numpy/complex objects to JSON-friendly structures."""

    def _default(obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, set):
            return list(obj)
        return str(obj)

    return json.loads(json.dumps(metadata_list, default=_default))


def _serialize_results(results: List[dict]) -> List[dict]:
    return json.loads(json.dumps(results))


def _merge_metadata_entries(existing: List[dict], incoming: List[dict]) -> List[dict]:
    """Merge metadata lists, overwriting matches by stable identifiers."""
    merged: List[dict] = []
    index_map = {}

    def _key(item: dict) -> tuple:
        identifier = (
            (item or {}).get("id")
            or (item or {}).get("ocr_id")
            or (item or {}).get("unique_name")
            or (item or {}).get("label_text")
            or ""
        )
        intent = (item or {}).get("intent") or ""
        return (identifier.strip().lower(), intent.strip().lower())

    for entry in existing or []:
        key = _key(entry)
        index_map[key] = len(merged)
        merged.append(entry)

    for entry in incoming or []:
        key = _key(entry)
        if key in index_map:
            merged[index_map[key]] = entry
        else:
            index_map[key] = len(merged)
            merged.append(entry)

    return merged


def _project_root_storage(project: Project, db: Session) -> Optional[DatabaseBackedProjectStorage]:
    ctx = get_project_context(required=True)
    try:
        root = Path(ctx.project_dir).resolve()
    except Exception:
        return None
    return DatabaseBackedProjectStorage(project, root, db)


def _persist_data_file(
    storage: Optional[DatabaseBackedProjectStorage],
    absolute_path: Path,
    payload: str,
    encoding: str = "utf-8",
) -> None:
    if not storage:
        return
    try:
        relative = absolute_path.resolve().relative_to(storage.base_dir.resolve())
    except Exception:
        return
    storage.write_file(relative.as_posix(), payload, encoding or "utf-8")

def _persist_binary_file(
    storage: Optional[DatabaseBackedProjectStorage],
    absolute_path: Path,
    payload: bytes,
) -> None:
    if not storage:
        return
    try:
        relative = absolute_path.resolve().relative_to(storage.base_dir.resolve())
    except Exception:
        return
    encoded = base64.b64encode(payload).decode("ascii")
    storage.write_file(relative.as_posix(), encoded, "base64")


def _delete_project_file(
    storage: Optional[DatabaseBackedProjectStorage],
    absolute_path: Path,
) -> bool:
    removed = False
    try:
        if absolute_path.exists() and absolute_path.is_file():
            absolute_path.unlink()
            removed = True
    except Exception:
        pass
    if not storage:
        return removed
    try:
        relative = absolute_path.resolve().relative_to(storage.base_dir.resolve())
    except Exception:
        return removed
    try:
        removed = storage.delete_file(relative.as_posix()) or removed
    except Exception:
        pass
    return removed


class DeleteUploadedImagesRequest(BaseModel):
    image_names: List[str]


class PreviewImageImpactRequest(BaseModel):
    image_name: str
    action_type: str = "delete"
    replacement_image_name: Optional[str] = None


class CancelUploadRequest(BaseModel):
    session_id: str


def _first_json_payload(response: Any) -> dict[str, Any]:
    body = getattr(response, "body", None)
    if not body:
        return {}
    try:
        return json.loads(body.decode("utf-8"))
    except Exception:
        return {}
    
def _project_root_storage_check(project_dir: Any, project: Project, db: Session) -> Optional[DatabaseBackedProjectStorage]:
    if not project_dir:
        return None
    try:
        root = Path(project_dir).resolve()
    except Exception:
        return None
    return DatabaseBackedProjectStorage(project, root, db)


def _project_log_path(ctx: ProjectContext) -> Path:
    return Path(ctx.logs_dir) / "upload_image_logs.txt"


def _ensure_project_logger(ctx: ProjectContext) -> Path:
    log_path = _project_log_path(ctx)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    for handler in logger.handlers:
        if isinstance(handler, logging.FileHandler) and Path(handler.baseFilename) == log_path:
            return log_path
    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    logger.addHandler(file_handler)
    return log_path


def _sanitize_image_names(image_names: List[str]) -> List[str]:
    sanitized: List[str] = []
    seen: set[str] = set()
    for value in image_names or []:
        name = os.path.basename((value or "").strip())
        if not name:
            continue
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)
        sanitized.append(name)
    return sanitized


def _page_class_name(page_name: str) -> str:
    tokens = re.split(r"[^a-zA-Z0-9]+", page_name or "")
    cleaned = [token for token in tokens if token]
    return "".join(token[:1].upper() + token[1:] for token in cleaned) + "Page" if cleaned else "PageObject"


def _read_project_text_file(src_root: Path, relative_path: Optional[str]) -> str:
    if not relative_path:
        return ""
    try:
        candidate = (src_root / relative_path).resolve()
        base = src_root.resolve()
        candidate.relative_to(base)
    except Exception:
        return ""
    if not candidate.exists() or not candidate.is_file():
        return ""
    try:
        return candidate.read_text(encoding="utf-8")
    except Exception:
        try:
            return candidate.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return ""


def _extract_page_modules(content: str) -> set[str]:
    if not content:
        return set()
    matches = re.findall(r"(?:from|import)\s+pages\.([A-Za-z0-9_]+)", content)
    return {match.strip().lower() for match in matches if match and match.strip()}


def _current_page_modules(src_root: Path) -> set[str]:
    pages_dir = src_root / "pages"
    if not pages_dir.exists():
        return set()
    return {
        path.stem.lower()
        for path in pages_dir.glob("*_page_methods.py")
        if path.is_file()
    }


def _build_impact_reason(change_type: str, missing_modules: set[str], changed_modules: set[str]) -> str:
    if missing_modules:
        return "page_missing_after_image_change"
    if change_type == "delete":
        return "page_deleted"
    if changed_modules:
        return "page_replaced"
    return "image_changed"


def _conservative_impacted_testcases(
    db: Session,
    project: Project,
    src_root: Path,
    changed_page_names: list[str],
    change_type: str,
) -> list[dict[str, Any]]:
    normalized_pages = [
        normalize_page_name(page_name or "")
        for page_name in changed_page_names or []
        if normalize_page_name(page_name or "")
    ]
    changed_modules = {
        f"{page_name}_page_methods".lower()
        for page_name in normalized_pages
    }
    changed_markers = {
        marker
        for page_name in normalized_pages
        for marker in (
            page_name.lower(),
            f"{page_name}_page_methods".lower(),
            f"pages/{page_name}_page_methods.py".lower(),
            _page_class_name(page_name).lower(),
        )
        if marker
    }

    if not changed_modules and not changed_markers:
        return []

    current_modules = _current_page_modules(src_root)

    impacted: list[dict[str, Any]] = []
    records = (
        db.query(TestCaseMetadata)
        .filter(TestCaseMetadata.project_id == project.id)
        .all()
    )

    for record in records:
        matched_via: set[str] = set()
        impacted_modules: set[str] = set()
        where_impacted: list[str] = []
        script_paths = [
            ("script_path", record.script_path),
            ("runner_script_path", record.runner_script_path),
        ]
        for field_name, relative_path in script_paths:
            content = _read_project_text_file(src_root, relative_path)
            if not content:
                continue
            haystack = content.lower().replace("\\", "/")
            imported_modules = _extract_page_modules(content)
            missing_modules = {
                module for module in imported_modules
                if module.endswith("_page_methods") and module not in current_modules
            }
            changed_imports = imported_modules & changed_modules
            marker_hits = {marker for marker in changed_markers if marker in haystack}
            if missing_modules or changed_imports or marker_hits:
                matched_via.add(field_name)
                impacted_modules.update(missing_modules)
                impacted_modules.update(changed_imports)
                impacted_modules.update(
                    marker for marker in marker_hits if marker.endswith("_page_methods")
                )
                if relative_path:
                    where_impacted.append(relative_path)
        if not matched_via:
            continue
        missing_modules = {
            module for module in impacted_modules
            if module.endswith("_page_methods") and module not in current_modules
        }
        changed_modules_hit = impacted_modules & changed_modules
        impacted.append(
            {
                "case_uuid": record.case_uuid,
                "display_name": record.display_name,
                "test_name": record.test_name,
                "script_path": record.script_path,
                "runner_script_path": record.runner_script_path,
                "test_type": record.test_type,
                "reason": _build_impact_reason(change_type, missing_modules, changed_modules_hit),
                "matched_via": sorted(matched_via),
                "where_impacted": where_impacted,
                "impacted_page_modules": sorted(impacted_modules),
            }
        )
    return impacted


def _refresh_order_files(
    data_dir: Path,
    root_storage: Optional[DatabaseBackedProjectStorage],
) -> None:
    images_dir = data_dir / "images"
    remaining_images = sorted(
        [
            path.name
            for path in images_dir.iterdir()
            if path.is_file() and path.suffix.lower() in {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp"}
        ]
    ) if images_dir.exists() else []

    order_payload = {
        "ordered_from_frontend": remaining_images,
        "processed_order": remaining_images,
    }
    order_path = data_dir / "image_order.json"
    order_text = json.dumps(order_payload, indent=2)
    order_path.write_text(order_text, encoding="utf-8")
    _persist_data_file(root_storage, order_path, order_text)

    graph_path = data_dir / "dependency_graph.json"
    if remaining_images:
        build_dependency_graph(remaining_images, output_path=str(graph_path))
        if graph_path.exists():
            _persist_data_file(root_storage, graph_path, graph_path.read_text(encoding="utf-8"))
    else:
        _delete_project_file(root_storage, graph_path)


def _preview_image_change_impact(
    *,
    project: Project,
    src_root: Path,
    db: Session,
    image_name: str,
    action_type: str,
    replacement_image_name: Optional[str] = None,
) -> dict[str, Any]:
    normalized_image_name = os.path.basename((image_name or "").strip())
    normalized_action = (action_type or "delete").strip().lower()
    if normalized_action not in {"delete", "replace"}:
        raise HTTPException(status_code=400, detail="action_type must be 'delete' or 'replace'.")
    if not normalized_image_name:
        raise HTTPException(status_code=400, detail="image_name is required.")

    existing_record = (
        db.query(ImageMetadata)
        .filter(ImageMetadata.project_id == project.id, ImageMetadata.image_name == normalized_image_name)
        .first()
    )
    old_page_name = (
        existing_record.page_name if existing_record and existing_record.page_name else normalize_page_name(normalized_image_name)
    )

    changed_page_names = [old_page_name]
    normalized_replacement_name = os.path.basename((replacement_image_name or "").strip())
    new_page_name = ""
    if normalized_action == "replace" and normalized_replacement_name:
        new_page_name = normalize_page_name(normalized_replacement_name)
        if new_page_name and new_page_name not in changed_page_names:
            changed_page_names.append(new_page_name)

    impacted_testcases = _conservative_impacted_testcases(
        db=db,
        project=project,
        src_root=src_root,
        changed_page_names=changed_page_names,
        change_type=normalized_action,
    )

    return {
        "mode": "conservative",
        "change_type": normalized_action,
        "affected_page": old_page_name,
        "affected_pages": [page for page in changed_page_names if page],
        "count": len(impacted_testcases),
        "impacted_testcases": impacted_testcases,
        "old_image_name": normalized_image_name,
        "new_image_name": normalized_replacement_name or None,
        "new_page_name": new_page_name or None,
    }


def _prune_page_from_aggregate_metadata_file(path: Path, page_name: str) -> bool:
    if not path.exists() or not path.is_file():
        return False
    try:
        raw = json.loads(path.read_text(encoding="utf-8") or "[]")
    except Exception:
        return False
    if not isinstance(raw, list):
        return False
    filtered = []
    removed = False
    normalized_page = normalize_page_name(page_name or "")
    for entry in raw:
        if not isinstance(entry, dict):
            filtered.append(entry)
            continue
        entry_page = normalize_page_name((entry.get("page_name") or entry.get("page") or "").strip())
        if entry_page and entry_page == normalized_page:
            removed = True
            continue
        filtered.append(entry)
    if removed:
        path.write_text(json.dumps(filtered, indent=2), encoding="utf-8")
    return removed

@router.post("/{project_id}/upload-image")
async def upload_image(
    request: Request,
    project_id: int,
    images: List[UploadFile] = File(...),
    ordered_images: str = Form(None),
    upload_session_id: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):  # Require an active project so we don't write to repo-level defaults
    project = get_user_project(db, project_id, current_user)
    project_paths = _ensure_project_structure(project)
    ctx = build_project_context(current_user, project_id, db)
    projectDir = str(ctx.project_dir)
    projectSrcDir = str(ctx.generated_src_dir)
    projectChromaPath = str(ctx.chroma_path)
    _ensure_project_logger(ctx)
    tokens = set_request_context(project_context=ctx)
    # Upload Designs: supported image formats only.
    allowed_exts = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp"}
    allowed_exts_label = "PNG, JPG, JPEG, BMP, GIF, WEBP"
    # If a ZIP contains images in these formats, we reject the upload with a clear message.
    known_image_exts = allowed_exts | {".tif", ".tiff", ".jfif", ".heic", ".heif", ".svg", ".avif", ".ico"}
   
   
    # if not os.environ.get("SMARTAI_PROJECT_DIR") or not os.environ.get("SMARTAI_SRC_DIR"):
    #     raise HTTPException(status_code=400, detail="No active project. Start a project first (POST /projects/save-details).")
   # project = _get_active_project(db)
    data_storage = _project_root_storage_check(projectDir , project, db)
    dp = os.path.join(projectDir, "data")
    os.makedirs(os.path.join(dp, "regions"), exist_ok=True)
    os.makedirs(os.path.join(dp, "images"), exist_ok=True)
    results = []
    ordered_image_list = []
    normalized_upload_session_id = _normalize_upload_session_id(upload_session_id)

    async def _raise_if_upload_cancelled() -> None:
        disconnected = False
        try:
            disconnected = await request.is_disconnected()
        except Exception:
            disconnected = False
        if disconnected:
            _mark_upload_cancelled(project.id, normalized_upload_session_id)
        if disconnected or _is_upload_cancelled(project.id, normalized_upload_session_id):
            raise UploadCancelledError("Upload canceled by user.")

    # Step 1: Parse frontend ordering
    if ordered_images:
        try:
            parsed_json = json.loads(ordered_images)
            ordered_image_list = parsed_json.get("ordered_images", [])
            ordered_image_list = [os.path.basename(
                f) for f in ordered_image_list]
            logger.info(
                f"🟢 Ordered images from frontend: {ordered_image_list}")
        except Exception as parse_err:
            logger.warning(f"⚠️ Failed to parse ordered_images: {parse_err}")
            ordered_image_list = []

    # Step 2: Extract uploaded files
    temp_dir = tempfile.mkdtemp()
    image_file_map = {}
    actual_received_images = []

    def _normalize_image_key(name: str) -> str:
        return os.path.basename(name or "").strip().lower()

    def _unique_filename(target_dir: str, name: str) -> str:
        base, ext = os.path.splitext(name)
        candidate = name
        counter = 1
        while os.path.exists(os.path.join(target_dir, candidate)):
            candidate = f"{base}_{counter}{ext}"
            counter += 1
        return candidate

    try:
        unsupported_top_level: list[str] = []
        for file in images:
            await _raise_if_upload_cancelled()
            raw_name = os.path.basename(file.filename or "")
            lower_name = raw_name.lower()
            if lower_name.endswith(".zip"):
                with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp_zip:
                    tmp_zip.write(await file.read())
                    tmp_zip_path = tmp_zip.name
                with zipfile.ZipFile(tmp_zip_path, 'r') as zip_ref:
                    unsupported_in_zip: list[str] = []
                    extracted_any = False
                    for member in zip_ref.infolist():
                        if member.is_dir():
                            continue
                        member_name = os.path.basename(member.filename)
                        if not member_name:
                            continue
                        ext = os.path.splitext(member_name)[1].lower()
                        if ext in allowed_exts:
                            extracted_any = True
                        elif ext in known_image_exts:
                            unsupported_in_zip.append(member_name)
                            continue
                        else:
                            # Ignore non-image payloads in ZIPs (e.g., README.txt).
                            continue
                        safe_name = _unique_filename(temp_dir, member_name)
                        with zip_ref.open(member) as src, open(os.path.join(temp_dir, safe_name), "wb") as dst:
                            dst.write(src.read())

                    if unsupported_in_zip:
                        preview = ", ".join(unsupported_in_zip[:10])
                        suffix = "..." if len(unsupported_in_zip) > 10 else ""
                        raise HTTPException(
                            status_code=400,
                            detail=(
                                f"Unsupported image format(s) in ZIP '{raw_name}': {preview}{suffix}. "
                                f"Supported formats: {allowed_exts_label}."
                            ),
                        )
                    if not extracted_any:
                        raise HTTPException(
                            status_code=400,
                            detail=(
                                f"ZIP '{raw_name}' contains no supported images. "
                                f"Supported formats: {allowed_exts_label}."
                            ),
                        )
            else:
                ext = os.path.splitext(lower_name)[1]
                if ext not in allowed_exts:
                    unsupported_top_level.append(raw_name or "unknown")
                    continue
                safe_name = _unique_filename(temp_dir, raw_name)
                file_path = os.path.join(temp_dir, safe_name)
                with open(file_path, "wb") as out_file:
                    out_file.write(await file.read())

        if unsupported_top_level:
            preview = ", ".join(unsupported_top_level[:10])
            suffix = "..." if len(unsupported_top_level) > 10 else ""
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Unsupported file format(s): {preview}{suffix}. "
                    f"Supported formats: {allowed_exts_label}."
                ),
            )

        # Step 3: Final image order
        extracted_images = [
            f
            for f in os.listdir(temp_dir)
            if os.path.splitext(f.lower())[1] in allowed_exts
        ]
        if not extracted_images:
            raise HTTPException(
                status_code=400,
                detail=(
                    "No supported images were uploaded. "
                    f"Supported formats: {allowed_exts_label}."
                ),
            )
        if ordered_image_list:
            extracted_map = { _normalize_image_key(name): name for name in extracted_images }
            image_names = []
            missing = []
            for requested in ordered_image_list:
                key = _normalize_image_key(requested)
                actual = extracted_map.get(key)
                if actual:
                    image_names.append(actual)
                else:
                    missing.append(requested)
            if missing:
                logger.warning(f"Ordered images not found in upload: {missing}")
            remaining = [name for name in extracted_images if _normalize_image_key(name) not in {_normalize_image_key(n) for n in image_names}]
            image_names.extend(sorted(remaining))
        else:
            image_names = sorted(extracted_images)

        # Group images by normalized page_name
        page_images = {}
        for image_name in image_names:
            page_name = normalize_page_name(image_name)
            page_images.setdefault(page_name, []).append(image_name)

        # For saving all raw metadata
        # all_raw_metadata = []

        # Step 4: Process images grouped by logical page
        for page_name, image_group in page_images.items():
            await _raise_if_upload_cancelled()
            # Fetch existing label_texts for this page from chroma
            try:
                existing = _chroma_collection(projectChromaPath).get(
                    where={"page_name": page_name})
                existing_label_texts = set(
                    m["label_text"].strip().lower()
                    for m in (existing["metadatas"] or [])
                    if m and m.get("label_text")
                )
            except Exception as fetch_err:
                logger.warning(
                    f"⚠️ Failed to fetch existing metadatas for {page_name}: {fetch_err}")
                existing_label_texts = set()

            # For each image for this logical page
            for image_name in image_group:
                await _raise_if_upload_cancelled()
                image_path = os.path.join(temp_dir, image_name)
                if not os.path.exists(image_path):
                    logger.warning(f"Skipping missing image: {image_name}")
                    results.append(
                        {
                            "image_name": image_name,
                            "page_name": page_name,
                            "metadata_id": None,
                            "metadata_count": 0,
                            "error": "missing_file",
                        }
                    )
                    image_file_map[image_name] = (image_path, page_name)
                    actual_received_images.append(image_name)
                    continue

                error_reason = None
                serialized_metadata: List[dict] = []
                permanent_image_path = os.path.join(dp, "images", image_name)

                try:
                    with Image.open(image_path) as img:
                        await _raise_if_upload_cancelled()
                        logger.debug(f"Processing image: {image_name}")
                        # GPT image extraction
                        region_Path = os.path.join(dp, "regions")
                        metadata_list = await process_image_gpt(
                            img, image_name,
                            image_path=image_path,
                            regionsPath= region_Path,
                            projectChromaPath=projectChromaPath,
                            db=db,
                            project_id=project.id,
                            # debug_log_path=DEBUG_LOG_PATH
                        )
                        metadata_list = metadata_list or []
                        serialized_metadata = _serialize_metadata_list(metadata_list)
                        await _raise_if_upload_cancelled()
                        img.save(permanent_image_path)
                        try:
                            _persist_binary_file(
                                data_storage, Path(permanent_image_path), Path(permanent_image_path).read_bytes()
                            )
                        except Exception as persist_err:
                            logger.warning(f"Failed to persist image {image_name} to DB: {persist_err}")
                except Exception as img_err:
                    if isinstance(img_err, UploadCancelledError):
                        _delete_project_file(data_storage, Path(permanent_image_path))
                        raise
                    error_reason = f"image_processing_failed: {img_err}"
                    logger.warning(f"Failed to process image {image_name}: {img_err}")
                    try:
                        with open(image_path, "rb") as src, open(permanent_image_path, "wb") as dst:
                            dst.write(src.read())
                        try:
                            _persist_binary_file(
                                data_storage, Path(permanent_image_path), Path(permanent_image_path).read_bytes()
                            )
                        except Exception as persist_err:
                            logger.warning(f"Failed to persist image {image_name} to DB: {persist_err}")
                    except Exception as copy_err:
                        logger.warning(
                            f"Failed to persist raw image {image_name}: {copy_err}"
                        )

                # Save per-image metadata to data/stored/timestamp_imageName.json
                base_image_name = os.path.splitext(os.path.basename(image_name))[0]
                store_dir = Path(dp) / "stored"
                store_dir.mkdir(parents=True, exist_ok=True)
                out_path = store_dir / f"{base_image_name}.json"
                await _raise_if_upload_cancelled()
                if out_path.exists():
                    try:
                        existing_meta = json.loads(out_path.read_text(encoding="utf-8") or "[]")
                    except json.JSONDecodeError:
                        existing_meta = []
                    combined = _merge_metadata_entries(existing_meta, serialized_metadata)
                else:
                    combined = serialized_metadata
                stored_payload = json.dumps(combined, indent=4, ensure_ascii=False)
                out_path.write_text(stored_payload, encoding="utf-8")
                _persist_data_file(data_storage, out_path, stored_payload)

                record = (
                    db.query(ImageMetadata)
                    .filter(
                        ImageMetadata.project_id == project.id,
                        ImageMetadata.image_name == image_name,
                    )
                    .first()
                )
                if record:
                    record.page_name = page_name
                    record.metadata_json = serialized_metadata
                else:
                    record = ImageMetadata(
                        project_id=project.id,
                        page_name=page_name,
                        image_name=image_name,
                        metadata_json=serialized_metadata,
                    )
                    db.add(record)
                    db.flush()

                result_payload = {
                    "image_name": image_name,
                    "page_name": page_name,
                    "metadata_id": record.id,
                    "metadata_count": len(serialized_metadata),
                }
                if error_reason:
                    result_payload["error"] = error_reason
                results.append(result_payload)

                # all_raw_metadata.append({
                #     "image_name": image_name,
                #     "metadata": metadata_list
                # })

                image_file_map[image_name] = (image_path, page_name)
                actual_received_images.append(image_name)

        # # Save all raw GPT metadata to a single file
        # raw_data_file_path = os.path.join("data", "raw_data_from_gpt.json")
        # with open(raw_data_file_path, "w", encoding="utf-8") as f:
        #     json.dump(all_raw_metadata, f, indent=2, ensure_ascii=False)
        # logger.info(f"📝 Saved all raw GPT metadata to {raw_data_file_path}")

        # Step 5: Store dependency graph
        if ordered_image_list:
            build_dependency_graph(
                ordered_image_list, output_path=os.path.join(dp, "dependency_graph.json"))
            logger.info(
                "📄 Dependency graph stored in data/dependency_graph.json")

        # Step 6: Log order metadata
        order_json_path = os.path.join(dp, "image_order.json")
        with open(order_json_path, "w") as f:
            json.dump({
                "ordered_from_frontend": ordered_image_list,
                "processed_order": actual_received_images
            }, f, indent=2)
        logger.info("[FILES] Ordered images logged to data/image_order.json")

        run_record = ImageUploadRun(
            project_id=project.id,
            results=_serialize_results(results),
            image_count=len(results),
        )
        db.add(run_record)
        db.flush()

        return JSONResponse(content={"status": "success", "data": results, "run_id": run_record.id})

    except UploadCancelledError as cancel_err:
        logger.info("Image upload canceled for project %s: %s", project.id, cancel_err)
        raise HTTPException(status_code=499, detail=str(cancel_err))
    except Exception as e:
        logger.error("❌ Error in upload_image", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        _clear_upload_cancelled(project.id, normalized_upload_session_id)
        shutil.rmtree(temp_dir, ignore_errors=True)
        reset_request_context(tokens)


@router.post("/{project_id}/upload-image/cancel")
async def cancel_upload_image(
    project_id: int,
    payload: CancelUploadRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = get_user_project(db, project_id, current_user)
    session_id = _normalize_upload_session_id(payload.session_id)
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id is required.")
    _mark_upload_cancelled(project.id, session_id)
    return {"status": "success", "message": "Upload cancellation requested."}


@router.post("/{project_id}/images/impact-preview")
async def preview_image_change_impact(
    project_id: int,
    payload: PreviewImageImpactRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = get_user_project(db, project_id, current_user)
    ctx = build_project_context(current_user, project_id, db)
    tokens = set_request_context(project_context=ctx)
    try:
        impact = _preview_image_change_impact(
            project=project,
            src_root=Path(ctx.generated_src_dir),
            db=db,
            image_name=payload.image_name,
            action_type=payload.action_type,
            replacement_image_name=payload.replacement_image_name,
        )
        return {"status": "success", "impact": impact}
    finally:
        reset_request_context(tokens)


def clean_label_text(text: str) -> str:
    # Remove leading/trailing numbers, dots, dashes, and spaces
    cleaned = re.sub(r"^[\s\W\d_]+|[\s\W\d_]+$", "", text, flags=re.UNICODE)
    return cleaned


@router.delete("/{project_id}/images")
async def delete_uploaded_images(
    project_id: int,
    payload: DeleteUploadedImagesRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = get_user_project(db, project_id, current_user)
    project_paths = _ensure_project_structure(project)
    ctx = build_project_context(current_user, project_id, db)
    _ensure_project_logger(ctx)
    tokens = set_request_context(project_context=ctx)

    try:
        image_names = _sanitize_image_names(payload.image_names)
        if not image_names:
            raise HTTPException(status_code=400, detail="At least one image name is required.")

        project_root = Path(ctx.project_dir)
        src_root = Path(ctx.generated_src_dir)
        data_dir = project_root / "data"
        meta_dir = src_root / "metadata"
        root_storage = DatabaseBackedProjectStorage(project, project_root, db)
        src_storage = DatabaseBackedProjectStorage(project, src_root, db)

        existing_records = (
            db.query(ImageMetadata)
            .filter(
                ImageMetadata.project_id == project.id,
                ImageMetadata.image_name.in_(image_names),
            )
            .all()
        )
        records_by_name = {record.image_name: record for record in existing_records}
        changed_page_names = [
            (record.page_name or normalize_page_name(record.image_name))
            for record in existing_records
            if record is not None
        ]
        for image_name in image_names:
            if image_name not in records_by_name:
                changed_page_names.append(normalize_page_name(image_name))

        deleted_images: list[dict[str, Any]] = []
        missing_images: list[str] = []

        for image_name in image_names:
            record = records_by_name.get(image_name)
            page_name = (record.page_name or normalize_page_name(image_name)) if record else normalize_page_name(image_name)
            base_image_name = Path(image_name).stem

            image_deleted = _delete_project_file(root_storage, data_dir / "images" / image_name)
            stored_deleted = _delete_project_file(root_storage, data_dir / "stored" / f"{base_image_name}.json")

            regions_dir = data_dir / "regions"
            deleted_region_count = 0
            if regions_dir.exists():
                for region_path in regions_dir.glob(f"{page_name}_*.png"):
                    if _delete_project_file(root_storage, region_path):
                        deleted_region_count += 1

            pom_relative = f"pages/{page_name}_page_methods.py"
            pom_deleted = src_storage.delete_file(pom_relative)
            legacy_pom_relative = f"pages/{page_name}_page.py"
            legacy_pom_deleted = src_storage.delete_file(legacy_pom_relative)

            deleted_metadata_files: list[str] = []
            for relative_path in (
                f"metadata/after_enrichment_{page_name}.json",
                f"metadata/before_enrichment_{page_name}.json",
            ):
                if src_storage.delete_file(relative_path):
                    deleted_metadata_files.append(relative_path)

            for aggregate_name in ("after_enrichment.json", "before_enrichment.json"):
                aggregate_path = meta_dir / aggregate_name
                if _prune_page_from_aggregate_metadata_file(aggregate_path, page_name):
                    try:
                        src_storage.write_file(
                            f"metadata/{aggregate_name}",
                            aggregate_path.read_text(encoding="utf-8"),
                            "utf-8",
                        )
                    except Exception:
                        pass
                    deleted_metadata_files.append(f"metadata/{aggregate_name}")

            if record is not None:
                db.delete(record)

            try:
                _chroma_collection(str(ctx.chroma_path)).delete(where={"page_name": page_name})
            except Exception as exc:
                logger.warning(f"Failed to delete Chroma metadata for page '{page_name}': {exc}")

            if (
                image_deleted
                or stored_deleted
                or pom_deleted
                or legacy_pom_deleted
                or deleted_region_count
                or deleted_metadata_files
                or record is not None
            ):
                deleted_images.append(
                    {
                        "image_name": image_name,
                        "page_name": page_name,
                        "pom_path": pom_relative,
                        "deleted_pom": bool(pom_deleted),
                        "deleted_legacy_pom": bool(legacy_pom_deleted),
                        "deleted_metadata_files": deleted_metadata_files,
                        "deleted_regions": deleted_region_count,
                    }
                )
            else:
                missing_images.append(image_name)

        db.flush()
        _refresh_order_files(data_dir, root_storage)
        impacted_testcases = _conservative_impacted_testcases(
            db=db,
            project=project,
            src_root=src_root,
            changed_page_names=changed_page_names,
            change_type="delete",
        )

        return {
            "status": "success",
            "deleted": deleted_images,
            "missing": missing_images,
            "impact": {
                "mode": "conservative",
                "change_type": "delete",
                "affected_pages": [page for page in changed_page_names if page],
                "count": len(impacted_testcases),
                "impacted_testcases": impacted_testcases,
            },
        }
    finally:
        reset_request_context(tokens)


@router.post("/{project_id}/images/replace")
async def replace_uploaded_image(
    project_id: int,
    old_image_name: str = Form(...),
    image: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    normalized_old_name = os.path.basename((old_image_name or "").strip())
    replacement_name = os.path.basename(image.filename or "")

    if not normalized_old_name:
        raise HTTPException(status_code=400, detail="old_image_name is required.")
    if not replacement_name:
        raise HTTPException(status_code=400, detail="Replacement image filename is required.")

    project = get_user_project(db, project_id, current_user)
    ctx = build_project_context(current_user, project_id, db)
    src_root = Path(ctx.generated_src_dir)
    existing_record = (
        db.query(ImageMetadata)
        .filter(ImageMetadata.project_id == project.id, ImageMetadata.image_name == normalized_old_name)
        .first()
    )
    old_page_name = (
        existing_record.page_name if existing_record and existing_record.page_name else normalize_page_name(normalized_old_name)
    )

    delete_result = await delete_uploaded_images(
        project_id=project_id,
        payload=DeleteUploadedImagesRequest(image_names=[normalized_old_name]),
        db=db,
        current_user=current_user,
    )

    upload_response = await upload_image(
        project_id=project_id,
        images=[image],
        ordered_images=json.dumps({"ordered_images": [replacement_name]}),
        db=db,
        current_user=current_user,
    )
    upload_payload = _first_json_payload(upload_response)
    upload_rows = upload_payload.get("data") if isinstance(upload_payload, dict) else None
    uploaded_entry = upload_rows[0] if isinstance(upload_rows, list) and upload_rows else {}
    new_page_name = normalize_page_name(uploaded_entry.get("page_name") or replacement_name)

    from apis.generate_page_methods import generate_page_methods as _generate_page_methods

    pom_result = _generate_page_methods(
        project_id=project_id,
        pages=new_page_name,
        db=db,
        current_user=current_user,
    )
    impacted_testcases = _conservative_impacted_testcases(
        db=db,
        project=project,
        src_root=src_root,
        changed_page_names=[old_page_name, new_page_name],
        change_type="replace",
    )

    return {
        "status": "success",
        "replaced": {
            "old_image_name": normalized_old_name,
            "new_image_name": replacement_name,
            "old_page_name": old_page_name,
            "new_page_name": new_page_name,
            "deleted": delete_result.get("deleted", []),
            "missing": delete_result.get("missing", []),
            "upload": uploaded_entry,
            "generated": pom_result.get(new_page_name) if isinstance(pom_result, dict) else None,
        },
        "impact": {
            "mode": "conservative",
            "change_type": "replace",
            "affected_page": old_page_name,
            "affected_pages": [page for page in [old_page_name, new_page_name] if page],
            "count": len(impacted_testcases),
            "impacted_testcases": impacted_testcases,
        },
    }
