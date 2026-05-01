import io
import os
import re
import json
import zipfile
import ast
import builtins
from pathlib import Path
from typing import Optional
import shutil

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel, EmailStr, ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import auth
from database.models import (
    Project,
    User,
    ProjectFile,
    ImageMetadata,
    Organization,
    OrganizationMember,
    TokenUsage,
)
from database.session import get_db
from database.project_storage import DatabaseBackedProjectStorage
from git_service import push_generated_project

from utils.chroma_client import reset_chroma_client
from utils.project_paths import build_project_context
from utils.request_context import set_request_context, reset_request_context

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


class TokenPayload(BaseModel):
    sub: EmailStr
    uid: int
    org: str
    org_id: Optional[int] = None
    exp: Optional[int] = None


def _org_slug(name: str) -> str:
    normalized = (name or "").strip().lower()
    return re.sub(r"[^a-z0-9_-]+", "-", normalized) or "default"


def _project_dir_segment(project: Project) -> str:
    """Return a filesystem-safe folder segment for the given project."""
    # Prefer the canonical slug if available; fall back to normalized key.
    base_slug = (project.slug or Project.normalized_key(project.project_name)).strip()
    base_slug = re.sub(r"[^a-z0-9_-]+", "-", base_slug.lower()) or "project"

    if project.id:
        return f"{project.id}-{base_slug}"
    return base_slug


def _project_root(project: Project) -> Path:
    backend_root = Path(__file__).resolve().parents[1]
    org_segment = _org_slug(project.organization)

    org_root = backend_root / "organizations" / org_segment
    desired = org_root / _project_dir_segment(project)

    # Backwards compatibility: projects created before this change stored data
    # under a plain folder named after the project. If that legacy folder still
    # exists and the new structure has not yet been created, migrate it so we
    # do not blend multiple projects together.
    legacy = org_root / project.project_name.strip()
    if legacy.exists() and not desired.exists():
        desired.parent.mkdir(parents=True, exist_ok=True)
        try:
            legacy.rename(desired)
        except Exception:
            # If the rename fails (e.g. permissions), keep using the legacy path.
            return legacy

    return desired


def _project_source_root(project: Project) -> Path:
    """Return the base directory that holds generated source artifacts."""
    return _project_root(project) / "generated_runs" / "src"


def _make_python_diagnostic(
    *,
    message: str,
    line: int = 1,
    column: int = 1,
    end_line: Optional[int] = None,
    end_column: Optional[int] = None,
    severity: str = "error",
    code: str = "",
) -> dict:
    safe_line = max(1, int(line or 1))
    safe_column = max(1, int(column or 1))
    safe_end_line = max(safe_line, int(end_line or safe_line))
    safe_end_column = max(safe_column + 1, int(end_column or (safe_column + 1)))
    return {
        "message": str(message or "Unknown Python error"),
        "line": safe_line,
        "column": safe_column,
        "end_line": safe_end_line,
        "end_column": safe_end_column,
        "severity": severity,
        "code": code or "",
    }


def _resolve_python_module_file(base_dir: Path, module_name: str) -> Optional[Path]:
    normalized = (module_name or "").strip().replace("\\", ".").strip(".")
    if not normalized:
        return None
    module_parts = [part for part in normalized.split(".") if part]
    if not module_parts:
        return None
    candidate = base_dir.joinpath(*module_parts).with_suffix(".py")
    if candidate.exists():
        return candidate
    package_init = base_dir.joinpath(*module_parts, "__init__.py")
    if package_init.exists():
        return package_init
    return None


def _extract_python_exports(module_path: Path) -> set[str]:
    try:
        source = module_path.read_text(encoding="utf-8")
    except Exception:
        return set()
    try:
        tree = ast.parse(source, filename=str(module_path))
    except SyntaxError:
        return set()

    exports: set[str] = set()
    explicit_all: Optional[set[str]] = None

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if not node.name.startswith("_"):
                exports.add(node.name)
            continue
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    if target.id == "__all__":
                        value = node.value
                        if isinstance(value, (ast.List, ast.Tuple, ast.Set)):
                            names = set()
                            for elt in value.elts:
                                if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                                    names.add(elt.value)
                            if names:
                                explicit_all = names
                    elif not target.id.startswith("_"):
                        exports.add(target.id)
            continue
        if isinstance(node, ast.Import):
            for alias in node.names:
                exported = (alias.asname or alias.name.split(".")[0]).strip()
                if exported and not exported.startswith("_"):
                    exports.add(exported)
            continue
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name == "*":
                    continue
                exported = (alias.asname or alias.name).strip()
                if exported and not exported.startswith("_"):
                    exports.add(exported)

    return explicit_all if explicit_all is not None else exports


def _collect_store_names(target: ast.AST) -> set[str]:
    names: set[str] = set()
    if isinstance(target, ast.Name):
        names.add(target.id)
    elif isinstance(target, (ast.Tuple, ast.List)):
        for elt in target.elts:
            names.update(_collect_store_names(elt))
    return names


def _collect_function_local_names(node: ast.AST) -> set[str]:
    locals_set: set[str] = set()
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
        args = getattr(node, "args", None)
        if args:
            for arg in list(args.posonlyargs) + list(args.args) + list(args.kwonlyargs):
                locals_set.add(arg.arg)
            if args.vararg:
                locals_set.add(args.vararg.arg)
            if args.kwarg:
                locals_set.add(args.kwarg.arg)
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        for child in node.body:
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                locals_set.add(child.name)

    for child in ast.walk(node):
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)) and child is not node:
            continue
        if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Store):
            locals_set.add(child.id)
        elif isinstance(child, (ast.For, ast.AsyncFor)):
            locals_set.update(_collect_store_names(child.target))
        elif isinstance(child, ast.With):
            for item in child.items:
                if item.optional_vars is not None:
                    locals_set.update(_collect_store_names(item.optional_vars))
        elif isinstance(child, ast.AsyncWith):
            for item in child.items:
                if item.optional_vars is not None:
                    locals_set.update(_collect_store_names(item.optional_vars))
        elif isinstance(child, ast.ExceptHandler) and child.name:
            locals_set.add(child.name)
    return locals_set


class _UndefinedCallVisitor(ast.NodeVisitor):
    def __init__(self, known_names: set[str]):
        self.known_names = known_names
        self.diagnostics: list[dict] = []
        self._reported: set[tuple[int, int, str]] = set()

    def visit_FunctionDef(self, node):
        return

    def visit_AsyncFunctionDef(self, node):
        return

    def visit_ClassDef(self, node):
        return

    def visit_Lambda(self, node):
        return

    def visit_Call(self, node):
        target = getattr(node, "func", None)
        if not isinstance(target, ast.Name):
            self.generic_visit(node)
            return
        if target.id in self.known_names:
            self.generic_visit(node)
            return
        key = (getattr(target, "lineno", 1), getattr(target, "col_offset", 0), target.id)
        if key in self._reported:
            self.generic_visit(node)
            return
        self._reported.add(key)
        end_column = getattr(target, "end_col_offset", None)
        if end_column is None:
            end_column = (key[1] + len(target.id) + 1)
        self.diagnostics.append(
            _make_python_diagnostic(
                message=f"Undefined function '{target.id}'",
                line=key[0],
                column=key[1] + 1,
                end_line=getattr(target, "end_lineno", key[0]),
                end_column=end_column + 1 if isinstance(end_column, int) else None,
                severity="error",
                code="undefined-call",
            )
        )
        self.generic_visit(node)


def _python_diagnostics_for_content(base_dir: Path, relative_path: str, content: str) -> list[dict]:
    path = (relative_path or "").strip()
    if not path.lower().endswith(".py"):
        return []

    try:
        tree = ast.parse(content or "", filename=path)
    except SyntaxError as exc:
        text = (exc.text or "").rstrip("\n")
        offset = int(exc.offset or 1)
        end_offset = offset + 1
        if text and 1 <= offset <= len(text):
            end_offset = min(len(text) + 1, offset + max(1, len(text[offset - 1 : offset])))
        return [
            _make_python_diagnostic(
                message=exc.msg or "Syntax error",
                line=exc.lineno or 1,
                column=offset,
                end_line=exc.lineno or 1,
                end_column=end_offset,
                severity="error",
                code="syntax-error",
            )
        ]

    diagnostics: list[dict] = []
    builtin_names = set(dir(builtins))
    module_known: set[str] = set(builtin_names)
    module_known.update({"__name__", "__file__", "__package__", "__doc__", "__annotations__"})

    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                bound_name = (alias.asname or alias.name.split(".")[0]).strip()
                if bound_name:
                    module_known.add(bound_name)
        elif isinstance(node, ast.ImportFrom):
            module_file = _resolve_python_module_file(base_dir, node.module) if node.module else None
            module_name = (node.module or "").strip()
            is_local_like = bool(module_name) and module_name.split(".")[0] in {"pages", "lib", "tests", "utils"}
            if module_name and is_local_like and module_file is None:
                diagnostics.append(
                    _make_python_diagnostic(
                        message=f"Cannot resolve local module '{module_name}'",
                        line=getattr(node, "lineno", 1),
                        column=getattr(node, "col_offset", 0) + 1,
                        end_line=getattr(node, "end_lineno", getattr(node, "lineno", 1)),
                        end_column=getattr(node, "end_col_offset", getattr(node, "col_offset", 0) + 2),
                        severity="error",
                        code="import-error",
                    )
                )
            if any(alias.name == "*" for alias in node.names):
                if module_file:
                    module_known.update(_extract_python_exports(module_file))
            else:
                exported_names = _extract_python_exports(module_file) if module_file else set()
                for alias in node.names:
                    bound_name = (alias.asname or alias.name).strip()
                    if bound_name:
                        module_known.add(bound_name)
                    if (
                        module_file
                        and alias.name != "*"
                        and alias.name not in exported_names
                        and alias.name not in {"__future__"}
                    ):
                        diagnostics.append(
                            _make_python_diagnostic(
                                message=f"Cannot import name '{alias.name}' from '{module_name}'",
                                line=getattr(node, "lineno", 1),
                                column=getattr(node, "col_offset", 0) + 1,
                                end_line=getattr(node, "end_lineno", getattr(node, "lineno", 1)),
                                end_column=getattr(node, "end_col_offset", getattr(node, "col_offset", 0) + 2),
                                severity="error",
                                code="import-error",
                            )
                        )
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            module_known.add(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                module_known.update(_collect_store_names(target))
        elif isinstance(node, ast.AnnAssign):
            module_known.update(_collect_store_names(node.target))

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            local_known = set(module_known)
            local_known.update(_collect_function_local_names(node))
            visitor = _UndefinedCallVisitor(local_known)
            for child in node.body:
                visitor.visit(child)
            diagnostics.extend(visitor.diagnostics)

    deduped: list[dict] = []
    seen: set[tuple[int, int, str]] = set()
    for item in diagnostics:
        key = (item["line"], item["column"], item["message"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def _count_project_testcases(project: Project) -> int:
    tests_dir = _project_source_root(project) / "tests"
    if not tests_dir.exists() or not tests_dir.is_dir():
        return 0
    count = 0
    for path in tests_dir.rglob("*.py"):
        if path.is_file() and path.name != "__init__.py":
            count += 1
    return count


_PROJECT_MODE_URL = "URL_EXECUTION"
_PROJECT_MODE_OCR = "OCR_EXECUTION"
_VALID_PROJECT_MODES = {_PROJECT_MODE_URL, _PROJECT_MODE_OCR}


def _project_meta_path(project: Project) -> Path:
    data_dir = _project_root(project) / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "project_meta.json"


def _read_project_meta(project: Project) -> dict:
    path = _project_meta_path(project)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _write_project_meta(project: Project, updates: dict) -> None:
    current = _read_project_meta(project)
    current.update({k: v for k, v in (updates or {}).items() if v is not None})
    path = _project_meta_path(project)
    path.write_text(json.dumps(current, indent=2), encoding="utf-8")


def _looks_like_url(value: str) -> bool:
    if not value or not isinstance(value, str):
        return False
    return value.startswith("http://") or value.startswith("https://")


def _has_url_metadata(project: Project) -> bool:
    meta_dir = _project_source_root(project) / "metadata"
    if not meta_dir.exists():
        return False
    candidates = [
        meta_dir / "after_enrichment.json",
        meta_dir / "before_enrichment.json",
    ]
    for path in candidates:
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        records = data if isinstance(data, list) else []
        for record in records:
            if not isinstance(record, dict):
                continue
            if record.get("source_type") == "url":
                return True
            for key in ("source_url", "url", "page_url", "app_url", "base_url"):
                if _looks_like_url(record.get(key)):
                    return True
    return False


def _has_ocr_images(db: Optional[Session], project: Project) -> bool:
    if db is None:
        return False
    try:
        return (
            db.query(ImageMetadata.id)
            .filter(ImageMetadata.project_id == project.id)
            .limit(1)
            .first()
            is not None
        )
    except Exception:
        return False


def _resolve_project_mode(
    project: Project,
    db: Optional[Session] = None,
    persist: bool = False,
) -> str:
    meta = _read_project_meta(project)
    stored = meta.get("project_mode")
    if stored in _VALID_PROJECT_MODES:
        return stored
    if _has_ocr_images(db, project):
        return _PROJECT_MODE_OCR
    if _has_url_metadata(project):
        if persist:
            _write_project_meta(project, {"project_mode": _PROJECT_MODE_URL})
        return _PROJECT_MODE_URL
    return _PROJECT_MODE_OCR


def _project_payload(
    project: Project,
    db: Optional[Session] = None,
    persist_mode: bool = False,
) -> dict:
    payload = project.to_dict()
    payload["project_mode"] = _resolve_project_mode(project, db=db, persist=persist_mode)
    return payload


def _user_org_ids(db: Session, user: User) -> set[int]:
    org_ids = OrganizationMember.user_org_ids(db, user.id)
    if not org_ids:
        raise HTTPException(status_code=403, detail="Organization membership required")
    return org_ids


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
        token_data = TokenPayload(**payload)
    except (JWTError, ValidationError) as exc:
        raise credentials_exception from exc

    user = (
        db.query(User)
        .filter(User.id == token_data.uid, User.email == str(token_data.sub).lower())
        .first()
    )
    if not user:
        raise credentials_exception

    if (user.organization or "").strip().lower() != (token_data.org or "").strip().lower():
        raise credentials_exception
    if token_data.org_id is not None and user.organization_id != token_data.org_id:
        raise credentials_exception

    org_ids = OrganizationMember.user_org_ids(db, user.id)
    if not org_ids:
        raise credentials_exception
    if token_data.org_id is not None and token_data.org_id not in org_ids:
        raise credentials_exception

    return user


class ProjectDetails(BaseModel):
    project_name: str
    framework: str
    language: str
    project_mode: Optional[str] = None


class ProjectActivateRequest(BaseModel):
    project_name: str


class ProjectFileUpdateRequest(BaseModel):
    path: str
    content: str
    encoding: Optional[str] = "utf-8"


class GitPushRequest(BaseModel):
    repo_url: str
    base_branch: str
    target_branch: str
    git_username: str
    git_token_env: Optional[str] = None
    git_token: Optional[str] = None
    commit_message: str
    author_name: str
    author_email: str


def _ensure_project_structure(project: Project) -> dict:
    project_root = _project_root(project)
    data_dir = project_root / "data"
    runs_dir = project_root / "generated_runs"
    runs_src = runs_dir / "src"

    data_dir.mkdir(parents=True, exist_ok=True)
    runs_dir.mkdir(parents=True, exist_ok=True)
    (runs_src / "metadata").mkdir(parents=True, exist_ok=True)
    (runs_src / "ocr-dom-metadata").mkdir(parents=True, exist_ok=True)
    (runs_src / "pages").mkdir(parents=True, exist_ok=True)
    (runs_src / "tests").mkdir(parents=True, exist_ok=True)
    
    prompts_dir = runs_src / "prompts"
    prompts_dir.mkdir(parents=True, exist_ok=True)

    existing_prompts = [p for p in prompts_dir.iterdir() if p.is_file() and p.suffix == ".txt"]
    if not existing_prompts:
        # Copy global prompts when starting a new project.
        global_prompts_dir = Path(__file__).resolve().parents[1] / "prompts"
        if global_prompts_dir.exists():
            for item in global_prompts_dir.iterdir():
                if item.is_file():
                    dest = prompts_dir / item.name
                    if dest.exists():
                        continue
                    try:
                        shutil.copy(item, dest)
                    except Exception as e:
                        print(f"ERROR: Failed to copy prompt '{item.name}' to '{prompts_dir}': {e}")
                else:
                    print(f"DEBUG: Skipping non-file item: {item.name}")
        else:
            print(f"ERROR: Global prompts directory does not exist: {global_prompts_dir}")

    return {
        "project_root": str(project_root.resolve()),
        "data_dir": str(data_dir.resolve()),
        "generated_runs": str(runs_dir.resolve()),
        "src_dir": str(runs_src.resolve()),
        "chroma_path": str((data_dir / "chroma_db").resolve()),
    }


def _persist_project_prompts(project: Project, project_paths: dict, db: Session) -> None:
    src_dir = Path(project_paths["src_dir"])
    prompts_dir = src_dir / "prompts"
    if not prompts_dir.exists() or not prompts_dir.is_dir():
        return
    storage = DatabaseBackedProjectStorage(project, src_dir, db)
    for item in prompts_dir.iterdir():
        if not item.is_file() or item.suffix != ".txt":
            continue
        try:
            content = item.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            content = item.read_text(encoding="utf-8", errors="replace")
        storage.write_file(f"prompts/{item.name}", content, "utf-8")


def _ensure_prompt_records(project: Project, project_paths: dict, db: Session) -> None:
    try:
        existing = (
            db.query(ProjectFile.path)
            .filter(
                ProjectFile.project_id == project.id,
                ProjectFile.path.like("prompts/%"),
            )
            .first()
        )
    except Exception:
        existing = None
    if existing is None:
        _persist_project_prompts(project, project_paths, db)


def _activate_project_context(project: Project, current_user: User, db: Session) -> dict:
    project_context = build_project_context(current_user, project.id, db)
    reset_chroma_client()
    return set_request_context(project_context=project_context)


def _clear_env_if_active(project_root: Path) -> None:
    """Deprecated no-op retained for backward compatibility."""
    return


def _resolve_project_path(base: Path, relative: str) -> Path:
    """Resolve a user-provided path safely within the project boundary."""
    relative_path = (Path(relative or ".")).as_posix().lstrip("/")
    target = (base / relative_path).resolve(strict=False)

    if target == base:
        return target

    try:
        target.relative_to(base)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid path") from exc

    return target


@router.post("/projects/save-details")
def save_project_details(
    details: ProjectDetails,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user_org = current_user.organization.strip()
    user_org_id = current_user.organization_id
    # Ensure the organization exists and the user points to a valid org id.
    if user_org_id is None or not db.query(Organization.id).filter(Organization.id == user_org_id).first():
        org = Organization.get_or_create(db, user_org)
        current_user.organization_id = org.id
        db.add(current_user)
        db.flush()
        user_org_id = org.id
    mode = None
    if details.project_mode:
        mode = details.project_mode.strip().upper()
        if mode not in _VALID_PROJECT_MODES:
            raise HTTPException(
                status_code=400,
                detail=f"project_mode must be one of: {', '.join(sorted(_VALID_PROJECT_MODES))}",
            )
    try:
        project = Project(
            organization=user_org,
            organization_id=user_org_id,
            created_by=current_user.id,
            project_name=details.project_name.strip(),
            framework=details.framework.strip(),
            language=details.language.strip()
        )
        db.add(project)
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        # If the project already exists in this org, return it instead of 409.
        normalized_key = Project.normalized_key(details.project_name)
        project = (
            db.query(Project)
            .filter(
                Project.organization_id == user_org_id,
                Project.project_key == normalized_key,
            )
            .first()
        )
        if project:
            pass
        else:
            # Only return 409 for actual duplicate project names. Otherwise surface the real issue.
            message = str(exc).lower()
            if "uq_projects_org_key" in message or "unique constraint" in message:
                raise HTTPException(
                    status_code=409,
                    detail=f"Project '{details.project_name.strip()}' already exists",
                )
            raise HTTPException(
                status_code=500,
                detail=f"Failed to create project due to database constraint: {exc}",
            )
    except ValueError as ve:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(ve))
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(exc))

    project_paths = {}
    try:
        project_paths = _ensure_project_structure(project)
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to prepare project directories: {exc}") from exc
    try:
        _persist_project_prompts(project, project_paths, db)
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to persist prompts: {exc}") from exc

    tokens = {}
    try:
        tokens = _activate_project_context(project, current_user, db)
    except Exception:
        # Context activation is best-effort; failures shouldn't prevent API success.
        pass
    if mode:
        _write_project_meta(project, {"project_mode": mode})
    OrganizationMember.ensure_member(db, current_user.id, project.organization_id, role="member")

    payload = {
        "status": "success" if project.id else "exists",
        "project": _project_payload(project, db=db),
        **project_paths,
    }

    if tokens:
        reset_request_context(tokens)
    return payload


@router.get("/projects")
def list_projects(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org_ids = _user_org_ids(db, current_user)
    projects = (
        db.query(Project)
        .filter(Project.organization_id.in_(org_ids))
        .order_by(Project.created_at.desc())
        .all()
    )
    return {"projects": [_project_payload(p, db=db) for p in projects]}


@router.get("/projects/testcase-counts")
def get_testcase_counts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org_ids = _user_org_ids(db, current_user)
    projects = db.query(Project).filter(Project.organization_id.in_(org_ids)).all()
    counts = {}
    total = 0
    for project in projects:
        count = _count_project_testcases(project)
        counts[str(project.id)] = count
        total += count
    return {"total": total, "by_project": counts}


@router.post("/projects/activate")
def activate_project(
    req: ProjectActivateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user_org = current_user.organization.strip()
    org_ids = _user_org_ids(db, current_user)
    name = (req.project_name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="project_name is required")

    project_key = Project.normalized_key(name)
    project = (
        db.query(Project)
        .filter(
            Project.project_key == project_key,
            Project.organization_id.in_(org_ids),
        )
        .first()
    )
    if not project:
        raise HTTPException(status_code=404, detail=f"Project '{name}' not found")

    try:
        project_paths = _ensure_project_structure(project)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to prepare project directories: {exc}",
        ) from exc
    try:
        _persist_project_prompts(project, project_paths, db)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to persist prompts: {exc}",
        ) from exc
    tokens = {}
    try:
        tokens = _activate_project_context(project, current_user, db)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to activate project: {exc}") from exc

    response = {
        "status": "activated",
        "project": _project_payload(project, db=db, persist_mode=True),
        **project_paths,
    }
    if tokens:
        reset_request_context(tokens)
    return response


@router.get("/projects/{project_id}")
def get_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org_ids = _user_org_ids(db, current_user)
    project = (
        db.query(Project)
        .filter(Project.id == project_id, Project.organization_id.in_(org_ids))
        .first()
    )
    if not project:
        raise HTTPException(status_code=404, detail=f"Project with id '{project_id}' not found")

    try:
        project_paths = _ensure_project_structure(project)
    except Exception:
        project_paths = {}

    return {
        "project": _project_payload(project, db=db, persist_mode=True),
        "paths": project_paths,
    }


@router.get("/projects/{project_id}/prompts")
def list_project_prompts(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = _get_project_for_user(project_id, db, current_user)
    project_paths = _ensure_project_structure(project)
    _ensure_prompt_records(project, project_paths, db)

    try:
        rows = (
            db.query(ProjectFile.path)
            .filter(
                ProjectFile.project_id == project.id,
                ProjectFile.path.like("prompts/%"),
            )
            .all()
        )
    except Exception as exc:
        print(f"ERROR in list_project_prompts: Failed to read prompt records: {exc}")
        raise HTTPException(status_code=500, detail=f"Failed to read prompt records: {exc}")

    prompt_files = sorted(
        {
            Path(path).name
            for (path,) in rows
            if path and path.endswith(".txt")
        }
    )
    return {"prompts": prompt_files}


def _get_project_for_user(project_id: int, db: Session, current_user: User) -> Project:
    org_ids = _user_org_ids(db, current_user)
    project = (
        db.query(Project)
        .filter(Project.id == project_id, Project.organization_id.in_(org_ids))
        .first()
    )
    if not project:
        raise HTTPException(status_code=404, detail=f"Project with id '{project_id}' not found")
    return project


@router.get("/projects/{project_id}/files")
def list_project_files(
    project_id: int,
    path: str = Query("", description="Relative path within the project's generated source tree."),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = _get_project_for_user(project_id, db, current_user)

    try:
        project_paths = _ensure_project_structure(project)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to prepare project directories: {exc}") from exc

    base_dir = Path(project_paths["src_dir"])
    normalized_path = (path or "").strip().strip("/")
    if normalized_path == "prompts":
        _ensure_prompt_records(project, project_paths, db)
        try:
            rows = (
                db.query(ProjectFile.path)
                .filter(
                    ProjectFile.project_id == project.id,
                    ProjectFile.path.like("prompts/%"),
                )
                .all()
            )
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Failed to read prompt records: {exc}") from exc

        entries = []
        for (row_path,) in rows:
            if not row_path:
                continue
            name = Path(row_path).name
            if not name.endswith(".txt"):
                continue
            entries.append(
                {
                    "name": name,
                    "path": row_path,
                    "type": "file",
                }
            )
        entries.sort(key=lambda item: item["name"].lower())
        return {
            "project_id": project_id,
            "base_path": base_dir.as_posix(),
            "path": "prompts",
            "entries": entries,
        }

    target = _resolve_project_path(base_dir, path)

    # Prefer DB-backed listings when available so projects survive across deployments.
    db_prefix = f"{normalized_path}/" if normalized_path else ""
    try:
        db_paths = (
            db.query(ProjectFile.path)
            .filter(
                ProjectFile.project_id == project.id,
                ProjectFile.path.like(f"{db_prefix}%"),
            )
            .all()
        )
    except Exception:
        db_paths = []

    if db_paths:
        entries_map = {}
        for (row_path,) in db_paths:
            if not row_path:
                continue
            if not row_path.startswith(db_prefix):
                continue
            remainder = row_path[len(db_prefix) :]
            if not remainder:
                continue
            head = remainder.split("/", 1)[0]
            if not head:
                continue
            entry_type = "directory" if "/" in remainder else "file"
            existing = entries_map.get(head)
            if existing == "directory":
                continue
            if existing == "file" and entry_type == "directory":
                entries_map[head] = entry_type
                continue
            entries_map.setdefault(head, entry_type)

        entries = [
            {
                "name": name,
                "path": f"{db_prefix}{name}".rstrip("/"),
                "type": entry_type,
            }
            for name, entry_type in entries_map.items()
        ]
        entries.sort(key=lambda item: (item["type"] == "file", item["name"].lower()))
        return {
            "project_id": project_id,
            "base_path": base_dir.as_posix(),
            "path": normalized_path,
            "entries": entries,
            "source": "database",
        }

    if not target.exists():
        raise HTTPException(status_code=404, detail="Path not found")
    if not target.is_dir():
        raise HTTPException(status_code=400, detail="Path is not a directory")

    entries = []
    try:
        for child in sorted(target.iterdir(), key=lambda x: (x.is_file(), x.name.lower())):
            rel_path = child.relative_to(base_dir).as_posix()
            entry_type = "file" if child.is_file() else "directory"
            entries.append(
                {
                    "name": child.name,
                    "path": rel_path,
                    "type": entry_type,
                }
            )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail="Access denied for requested path") from exc

    return {
        "project_id": project_id,
        "base_path": base_dir.as_posix(),
        "path": target.relative_to(base_dir).as_posix() if target != base_dir else "",
        "entries": entries,
    }


@router.get("/projects/{project_id}/files/content")
def get_project_file_content(
    project_id: int,
    path: str = Query(..., min_length=1, description="Relative file path within the project."),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = _get_project_for_user(project_id, db, current_user)

    try:
        project_paths = _ensure_project_structure(project)
    except Exception as exc:
        print(f"ERROR in get_project_file_content: Failed to prepare project directories: {exc}")
        raise HTTPException(status_code=500, detail=f"Failed to prepare project directories: {exc}") from exc
    _ensure_prompt_records(project, project_paths, db)

    base_dir = Path(project_paths["src_dir"])
    storage = DatabaseBackedProjectStorage(project, base_dir, db)
    target = _resolve_project_path(base_dir, path)

    relative_path = target.relative_to(base_dir).as_posix()
    record = (
        db.query(ProjectFile)
        .filter(ProjectFile.project_id == project.id, ProjectFile.path == relative_path)
        .first()
    )

    def _read_disk_text(file_path: Path) -> tuple[str, str]:
        try:
            return file_path.read_text(encoding="utf-8"), "utf-8"
        except UnicodeDecodeError:
            return file_path.read_text(encoding="utf-8", errors="replace"), "utf-8"

    def _read_disk_binary(file_path: Path) -> tuple[str, str]:
        import base64

        data = file_path.read_bytes()
        return base64.b64encode(data).decode("ascii"), "base64"

    if target.exists() and target.is_file():
        if record is None or (record.content or "") == "":
            extension = target.suffix.lower().lstrip(".")
            if extension in {"png", "jpg", "jpeg", "bmp", "gif", "webp"}:
                content, encoding = _read_disk_binary(target)
            else:
                content, encoding = _read_disk_text(target)
            storage.write_file(relative_path, content, encoding)
            diagnostics = _python_diagnostics_for_content(base_dir, relative_path, content)
            return {
                "project_id": project_id,
                "path": relative_path,
                "encoding": encoding,
                "language": extension or "text",
                "content": content,
                "diagnostics": diagnostics,
                "source": "filesystem",
            }
    elif record is None:
        raise HTTPException(status_code=404, detail="File not found")

    if record is None:
        file_data = storage.read_file(relative_path, target)
        extension = target.suffix.lower().lstrip(".")
        return {
            "project_id": project_id,
            "path": relative_path,
            "encoding": file_data.encoding,
            "language": extension or "text",
            "content": file_data.content,
            "diagnostics": _python_diagnostics_for_content(base_dir, relative_path, file_data.content),
            "source": file_data.source,
        }

    extension = Path(relative_path).suffix.lower().lstrip(".")
    content = record.content or ""
    encoding = record.encoding or "utf-8"

    return {
        "project_id": project_id,
        "path": relative_path,
        "encoding": encoding,
        "language": extension or "text",
        "content": content,
        "diagnostics": _python_diagnostics_for_content(base_dir, relative_path, content),
        "source": "database",
    }


@router.put("/projects/{project_id}/files/content")
def update_project_file_content(
    project_id: int,
    payload: ProjectFileUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = _get_project_for_user(project_id, db, current_user)

    try:
        project_paths = _ensure_project_structure(project)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to prepare project directories: {exc}") from exc

    base_dir = Path(project_paths["src_dir"])
    storage = DatabaseBackedProjectStorage(project, base_dir, db)
    relative_path = (payload.path or "").strip()
    if not relative_path:
        raise HTTPException(status_code=400, detail="Path is required")
    target = _resolve_project_path(base_dir, relative_path)

    if target.exists() and target.is_dir():
        raise HTTPException(status_code=400, detail="Cannot overwrite a directory")

    encoding = (payload.encoding or "utf-8").lower().strip() or "utf-8"
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"Failed to prepare directories: {exc}") from exc

    try:
        target.write_text(payload.content or "", encoding=encoding)
    except LookupError as exc:
        raise HTTPException(status_code=400, detail=f"Unsupported encoding '{encoding}'") from exc
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {exc}") from exc

    storage.write_file(target.relative_to(base_dir).as_posix(), payload.content or "", encoding)

    stat = target.stat()
    extension = target.suffix.lower().lstrip(".")

    return {
        "status": "saved",
        "project_id": project_id,
        "path": target.relative_to(base_dir).as_posix(),
        "encoding": encoding,
        "language": extension or "text",
        "diagnostics": _python_diagnostics_for_content(base_dir, target.relative_to(base_dir).as_posix(), payload.content or ""),
        "size": stat.st_size,
        "modified_at": stat.st_mtime,
    }


@router.delete("/projects/{project_id}")
def delete_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org_ids = _user_org_ids(db, current_user)
    project = (
        db.query(Project)
        .filter(Project.id == project_id, Project.organization_id.in_(org_ids))
        .first()
    )
    if not project:
        raise HTTPException(status_code=404, detail=f"Project with id '{project_id}' not found")

    project_root = _project_root(project)

    try:
        db.query(TokenUsage).filter(TokenUsage.project_id == project_id).delete(synchronize_session=False)
        db.delete(project)
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete project: {exc}")

    # No request-scoped context to clear here; cleanup handled by request lifecycle.

    return {"status": "deleted", "project_id": project_id}


@router.get("/projects/{project_id}/download")
def download_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org_ids = _user_org_ids(db, current_user)
    project = (
        db.query(Project)
        .filter(Project.id == project_id, Project.organization_id.in_(org_ids))
        .first()
    )
    if not project:
        raise HTTPException(status_code=404, detail=f"Project with id '{project_id}' not found")

    project_root = _project_root(project).resolve()
    if not project_root.exists() or not project_root.is_dir():
        raise HTTPException(status_code=404, detail=f"Project directory for '{project.project_name}' not found")

    buffer = io.BytesIO()
    base_prefix = Path(project.slug or project.project_name.strip() or f"project_{project_id}")

    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
        for file_path in project_root.rglob("*"):
            if file_path.is_file():
                arcname = base_prefix / file_path.relative_to(project_root)
                zipf.write(str(file_path), arcname=str(arcname))

    buffer.seek(0)
    filename = f"{base_prefix}.zip"

    return StreamingResponse(
        buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        },
    )


@router.post("/projects/{project_id}/git/push")
def push_project_to_git(
    project_id: int,
    payload: GitPushRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = _get_project_for_user(project_id, db, current_user)
    project_root = _project_root(project).resolve()
    generated_runs_path = project_root / "generated_runs"

    config = {
        "repo_url": payload.repo_url,
        "base_branch": payload.base_branch,
        "target_branch": payload.target_branch,
        "git_username": payload.git_username,
        "git_token_env": payload.git_token_env,
        "git_token": payload.git_token,
        "commit_message": payload.commit_message,
        "author_name": payload.author_name,
        "author_email": payload.author_email,
        "generated_runs_path": str(generated_runs_path),
    }

    result = push_generated_project(config)
    if result.get("status") != "success":
        raise HTTPException(status_code=500, detail=result.get("error_message") or "Git push failed.")
    return result


def get_user_project(
    db: Session,
    project_id: int,
    current_user: User,
) -> Project:
    org_ids = _user_org_ids(db, current_user)
    project = (
        db.query(Project)
        .filter(
            Project.id == project_id,
            Project.organization_id.in_(org_ids),
        )
        .first()
    )

    if not project:
        raise HTTPException(
            status_code=403,
            detail="You do not have access to this project"
        )

    return project

def get_project_by_projectId(
    db: Session,
    project_id: int,
    current_user: User,
) -> Project:
    # Enforce tenant/project scoping: do not trust client-supplied project_id.
    org_ids = _user_org_ids(db, current_user)
    project = (
        db.query(Project)
        .filter(
            Project.id == project_id,
            Project.organization_id.in_(org_ids),
        )
        .first()
    )

    if not project:
        raise HTTPException(
            status_code=403,
            detail="You do not have access to this project"
        )

    return project

