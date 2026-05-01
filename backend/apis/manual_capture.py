# manual_capture.py

from fastapi import APIRouter, HTTPException, Depends, Query, Request
from pydantic import BaseModel
from chromadb import PersistentClient
from logic.manual_capture_mode import extract_dom_metadata, match_and_update, get_last_match_result, set_last_match_result
from utils.match_utils import normalize_page_name
from utils.file_utils import build_standard_metadata
from config.settings import get_backend_public_base_url, get_chroma_path
from dataclasses import dataclass
from playwright.async_api import async_playwright, Page, Browser, BrowserContext
import json
import os
import asyncio
from pathlib import Path
from typing import Optional, Dict, Tuple, Any
from sqlalchemy.orm import Session
from database.session import get_db
from database.models import Project, ImageMetadata, User, OrganizationMember
from apis.projects_api import _ensure_project_structure, get_current_user, get_user_project
import auth
from utils.request_context import set_request_context, reset_request_context, get_project_context
from utils.project_paths import build_project_context, ProjectContext
import pprint
import re

router = APIRouter(prefix="/manual-enrichment", tags=["Manual Enrichment"])


@dataclass
class ManualCaptureSession:
    user_id: int
    project_id: int
    playwright: Any
    browser: Browser
    context: BrowserContext
    page: Optional[Page]
    current_page_name: str = "unknown_page"
    current_app_domain: str = ""
    metadata_dir: Optional[Path] = None
    closed: bool = False


_SESSIONS: Dict[Tuple[int, int], ManualCaptureSession] = {}
_SESSION_LOCK = asyncio.Lock()

def _resolve_internal_backend_base_url(default_base_url: str) -> str:
    configured = (os.getenv("BACKEND_INTERNAL_BASE_URL") or "").strip()
    if configured:
        return configured.rstrip("/")
    app_host = (os.getenv("APP_HOST") or "").strip() or "127.0.0.1"
    app_port = (os.getenv("APP_PORT") or "").strip() or "8001"
    if app_host in {"0.0.0.0", "::"}:
        app_host = "127.0.0.1"
    return f"http://{app_host}:{app_port}".rstrip("/")


def _session_key(user_id: int, project_id: int) -> Tuple[int, int]:
    return (int(user_id), int(project_id))


async def _get_session(
    user_id: int,
    project_id: int,
    *,
    required: bool = True,
) -> Optional[ManualCaptureSession]:
    key = _session_key(user_id, project_id)
    async with _SESSION_LOCK:
        session = _SESSIONS.get(key)
    if required and session is None:
        raise HTTPException(status_code=404, detail="No active manual capture session for this project.")
    return session


async def _store_session(session: ManualCaptureSession) -> None:
    key = _session_key(session.user_id, session.project_id)
    async with _SESSION_LOCK:
        _SESSIONS[key] = session


async def _delete_session(user_id: int, project_id: int) -> Optional[ManualCaptureSession]:
    key = _session_key(user_id, project_id)
    async with _SESSION_LOCK:
        return _SESSIONS.pop(key, None)


async def _close_session(session: ManualCaptureSession) -> None:
    if session.closed:
        return
    try:
        if session.page and not session.page.is_closed():
            await session.page.close()
    except Exception:
        pass
    try:
        if session.context:
            await session.context.close()
    except Exception:
        pass
    try:
        if session.browser:
            await session.browser.close()
    except Exception:
        pass
    try:
        if session.playwright:
            await session.playwright.stop()
    except Exception:
        pass
    session.closed = True


def _binding_source_page(source: Any) -> Optional[Page]:
    try:
        page = getattr(source, "page", None)
        if page is not None:
            return page
    except Exception:
        pass
    try:
        if isinstance(source, dict):
            page = source.get("page")
            if page is not None:
                return page
    except Exception:
        pass
    return None


def _context_open_pages(context: Optional[BrowserContext]) -> list[Page]:
    if context is None:
        return []
    try:
        pages = list(getattr(context, "pages", []) or [])
    except Exception:
        return []
    out: list[Page] = []
    for page in pages:
        if page is None:
            continue
        try:
            if page.is_closed():
                continue
        except Exception:
            pass
        out.append(page)
    return out


def _latest_open_page(context: Optional[BrowserContext], exclude: Optional[Page] = None) -> Optional[Page]:
    pages = [page for page in _context_open_pages(context) if page is not exclude]
    return pages[-1] if pages else None


async def _activate_session_page(session: ManualCaptureSession, page: Optional[Page]) -> Optional[Page]:
    if session.closed or page is None:
        return None
    session.page = page
    try:
        page_url = page.url or ""
    except Exception:
        page_url = ""
    page_domain = _domain_from_url(page_url)
    if page_domain:
        session.current_app_domain = page_domain
    try:
        page.on("close", lambda: asyncio.create_task(_handle_page_close(session, page)))
    except Exception:
        pass
    return page


async def _handle_page_close(session: ManualCaptureSession, page: Optional[Page]) -> None:
    if session.closed:
        return
    if session.page is page:
        session.page = _latest_open_page(session.context, exclude=page)


async def _resolve_session_page(session: ManualCaptureSession) -> Optional[Page]:
    current = session.page
    if current is not None:
        try:
            if not current.is_closed():
                return current
        except Exception:
            return current
    replacement = _latest_open_page(session.context)
    session.page = replacement
    return replacement

def _collection():
    client = PersistentClient(path=get_chroma_path())
    return client.get_or_create_collection(
        name=os.environ.get("SMARTAI_CHROMA_COLLECTION", "element_metadata")
    )

def _env_metadata_dirs() -> list[Path]:
    ctx = get_project_context(required=True)
    return [Path(ctx.generated_src_dir) / "metadata"]


def _candidate_metadata_dirs(domain: str) -> list[Path]:
    """
    Build a prioritized list of metadata directories for the active project.
    Priority:
      1. SMARTAI_SRC_DIR/metadata (if set)
      2. SMARTAI_PROJECT_DIR/generated_runs/src/metadata (if set)
      3. Repo-level generated_runs/src/metadata as a fallback (best-effort)
    """
    candidates: list[Path] = []

    candidates.extend(_env_metadata_dirs())

    uniq: list[Path] = []
    seen = set()
    for cand in candidates:
        try:
            resolved = cand.resolve()
        except Exception:
            continue
        if resolved in seen:
            continue
        seen.add(resolved)
        uniq.append(resolved)
    return uniq


def _src_dir(ctx: ProjectContext) -> Path:
    return Path(ctx.generated_src_dir)


def _metadata_dir(ctx: ProjectContext) -> Path:
    path = _src_dir(ctx) / "metadata"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _debug_dir(ctx: ProjectContext) -> Path:
    path = _src_dir(ctx) / "ocr-dom-metadata"
    path.mkdir(parents=True, exist_ok=True)
    return path

def _norm_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip().lower()

async def _extract_table_structured_data(page: Page, max_rows: int = 20, max_cells: int = 20) -> list[dict]:
    """
    Extract table headers and rows so table structure is captured during manual capture.
    """
    js = r"""
    (maxRows, maxCells) => {
      const out = [];
      const norm = s => (s || "").replace(/\s+/g, " ").trim();
      const textOf = el => norm(el ? (el.innerText || el.textContent || "") : "");

      const isVisible = el => {
        if (!el || !el.ownerDocument) return false;
        const cs = el.ownerDocument.defaultView.getComputedStyle(el);
        if (!cs || cs.visibility === "hidden" || cs.display === "none" || parseFloat(cs.opacity || "1") < 0.01)
          return false;
        const rect = el.getBoundingClientRect();
        if (!rect || rect.width < 1 || rect.height < 1) return false;
        if (rect.bottom < 0 || rect.right < 0) return false;
        return true;
      };

      const attr = (el, name) => {
        try { return (el.getAttribute && el.getAttribute(name)) || ""; }
        catch(e) { return ""; }
      };
      const selectorHint = el => {
        const testId = attr(el, "data-testid") || attr(el, "data-test-id") || attr(el, "data-test");
        if (testId) return `[data-testid="${testId.replace(/"/g, '\\"')}"]`;
        const dataQa = attr(el, "data-qa") || attr(el, "data-cy");
        if (dataQa) return `[data-qa="${dataQa.replace(/"/g, '\\"')}"]`;
        const id = el && el.id ? String(el.id) : "";
        if (id) {
          if (/^[A-Za-z_][A-Za-z0-9_-]*$/.test(id)) return `#${id}`;
          return `[id="${id.replace(/"/g, '\\"')}"]`;
        }
        const name = attr(el, "name");
        const tag = (el && el.tagName ? el.tagName.toLowerCase() : "");
        if (name && tag) return `${tag}[name="${name.replace(/"/g, '\\"')}"]`;
        return "";
      };

      const push = (tag, el, text, role="", name="") => {
        if (!text) return;
        const rect = el && el.getBoundingClientRect ? el.getBoundingClientRect() : {x:0,y:0,width:0,height:0};
        out.push({
          tag,
          role,
          id: (el && el.id) ? el.id : "",
          name: name || "",
          type: "",
          text,
          label_text: text,
          aria_label: "",
          placeholder: "",
          data_testid: attr(el, "data-testid") || "",
          data_qa: attr(el, "data-qa") || "",
          data_cy: attr(el, "data-cy") || "",
          data_test: attr(el, "data-test") || "",
          css_selector: selectorHint(el),
          is_draggable: false,
          is_droppable: false,
          drag_handle_selector: "",
          drag_handle_text: "",
          clickable: false,
          bbox: { x: rect.x, y: rect.y, width: rect.width, height: rect.height }
        });
      };

      const tables = Array.from(document.querySelectorAll("table"));
      for (const table of tables) {
        if (!isVisible(table)) continue;

        let headerCells = Array.from(table.querySelectorAll("thead th"));
        if (headerCells.length === 0) {
          const firstRow = table.querySelector("tr");
          if (firstRow) headerCells = Array.from(firstRow.querySelectorAll("th, td"));
        }
        for (const th of headerCells.slice(0, maxCells)) {
          if (!isVisible(th)) continue;
          const t = textOf(th);
          if (!t || t.length < 1) continue;
          push("th", th, t, "columnheader");
        }

        let rows = Array.from(table.querySelectorAll("tbody tr"));
        if (rows.length === 0) rows = Array.from(table.querySelectorAll("tr"));
        let rowCount = 0;
        for (const tr of rows) {
          if (!isVisible(tr)) continue;
          const cells = Array.from(tr.querySelectorAll("td, th")).slice(0, maxCells);
          if (cells.length === 0) continue;
          const cellTexts = cells.map(c => textOf(c)).filter(t => t);
          if (cellTexts.length === 0) continue;
          const rowText = cellTexts.join(" | ");
          rowCount += 1;
          if (rowCount > maxRows) break;
          push("tr", tr, rowText, "row", `row-${rowCount}`);
        }
      }
      return out;
    }
    """
    try:
        return await page.evaluate(js, max_rows, max_cells)
    except Exception as e:
        print(f"[WARN] _extract_table_structured_data failed: {e}")
        return []

HASH_SUFFIX_RE = re.compile(r"_[0-9a-f]{8}$", re.IGNORECASE)
 
class LaunchRequest(BaseModel):
    url: str
    metadata_dir: Optional[str] = None
    project_root: Optional[str] = None
    project_name: Optional[str] = None
    project_id: Optional[int] = None

class CaptureRequest(BaseModel):
    page_name: Optional[str] = None
    project_id: Optional[int] = None
    project_name: Optional[str] = None
    metadata_dir: Optional[str] = None
    project_root: Optional[str] = None
class PageNameSetRequest(BaseModel):
    page_name: str


def _domain_from_url(url: str) -> str:
    try:
        from urllib.parse import urlparse
        return (urlparse(url).netloc or "").lower()
    except Exception:
        return ""


def _infer_page_name_from_url(url: str) -> str:
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url or "")
        path = (parsed.path or "").strip().strip("/")
        if not path:
            return "page"
        # Use the last path segment as the page name.
        segment = path.split("/")[-1]
        name = _normalize_page_value(segment)
        return name or "page"
    except Exception:
        return "page"


def _domain_matches(active: str, entry: str) -> bool:
    if not active or active == "unknown":
        return True
    if not entry:
        return False
    return entry.lower() == active.lower()


def _load_json(path: Path):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return None


def _metadata_matches_domain(meta_dir: Path, domain: str) -> bool:
    if not domain or domain == "unknown":
        return meta_dir.exists()
    saw_domainless = False
    for filename in ("before_enrichment.json", "after_enrichment.json"):
        data = _load_json(meta_dir / filename)
        if not isinstance(data, list):
            continue
        for entry in data:
            if not isinstance(entry, dict):
                continue
            entry_domain = _domain_from_url(entry.get("source_url") or "")
            if entry_domain == domain:
                return True
            if not entry_domain:
                saw_domainless = True
    # If metadata exists but lacks explicit domain tagging, treat it as eligible.
    return saw_domainless


def _safe_existing_dir(path_str: Optional[str]) -> Optional[Path]:
    if not path_str:
        return None
    try:
        candidate = Path(path_str).expanduser()
    except Exception:
        return None
    try:
        resolved = candidate.resolve()
    except Exception:
        resolved = candidate
    if resolved.exists() and resolved.is_dir():
        return resolved
    return None


def _coerce_to_metadata_dir(path: Path) -> Optional[Path]:
    if not path.exists() or not path.is_dir():
        return None
    if path.name == "metadata":
        return path.resolve()
    direct = path / "metadata"
    if direct.exists():
        return direct.resolve()
    nested = path / "generated_runs" / "src" / "metadata"
    if nested.exists():
        return nested.resolve()
    return None


def _slugify_project_name(name: str) -> str:
    normalized = (name or "").strip().lower()
    return re.sub(r"[^a-z0-9_-]+", "-", normalized)


def _metadata_dir_from_project_name(project_name: Optional[str]) -> Optional[Path]:
    slug = _slugify_project_name(project_name or "")
    if not slug:
        return None
    backend_root = Path(__file__).resolve().parents[1]
    matches: list[Path] = []
    for org_dir in backend_root.glob("organizations/*"):
        if not org_dir.is_dir():
            continue
        for project_dir in org_dir.iterdir():
            if not project_dir.is_dir():
                continue
            name = project_dir.name.lower()
            if name == slug or name.endswith(f"-{slug}"):
                meta = project_dir / "generated_runs" / "src" / "metadata"
                if meta.exists():
                    try:
                        matches.append(meta.resolve())
                    except Exception:
                        matches.append(meta)
    if not matches:
        return None
    if len(matches) == 1:
        return matches[0]
    try:
        matches.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    except Exception:
        pass
    return matches[0]


def _resolve_explicit_metadata_dir(
    metadata_dir: Optional[str],
    project_root: Optional[str],
    project_name: Optional[str],
) -> Optional[Path]:
    for raw in (metadata_dir, project_root):
        path = _safe_existing_dir(raw)
        if not path:
            continue
        meta = _coerce_to_metadata_dir(path)
        if meta:
            return meta
    return _metadata_dir_from_project_name(project_name)


def _strip_hash_suffix(value: str | None) -> str:
    if not value:
        return ""
    return HASH_SUFFIX_RE.sub("", value.strip())


def _normalize_page_value(value: str | None) -> str:
    normalized = normalize_page_name(value or "")
    normalized = _strip_hash_suffix(normalized) or normalized
    return normalized or (value or "").strip()


def _normalize_domain_value(domain: str | None) -> str:
    return (domain or "").strip().lower()


def _entry_domain(entry: dict | None) -> str:
    if not isinstance(entry, dict):
        return ""
    for key in ("source_url", "url", "page_url", "base_url", "app_url"):
        value = entry.get(key)
        if isinstance(value, str):
            domain = _domain_from_url(value)
            if domain:
                return domain
    raw_domain = entry.get("domain") or entry.get("app_domain")
    return (raw_domain or "").strip().lower()


def _entry_matches_page(entry: dict, normalized_page: str, domain: str) -> bool:
    if not isinstance(entry, dict):
        return False
    entry_page = _normalize_page_value(entry.get("page_name"))
    if entry_page != normalized_page:
        return False
    normalized_domain = _normalize_domain_value(domain)
    if not normalized_domain or normalized_domain == "unknown":
        return True
    entry_domain = _entry_domain(entry)
    if not entry_domain:
        return False
    return _domain_matches(normalized_domain, entry_domain)


def _as_record_list(data) -> list[dict]:
    if isinstance(data, list):
        return [entry for entry in data if isinstance(entry, dict)]
    if isinstance(data, dict):
        for key in ("metadatas", "data", "records"):
            value = data.get(key)
            if isinstance(value, list):
                return [entry for entry in value if isinstance(entry, dict)]
    return []


def _split_records_for_page(records: list[dict], page_name: str, domain: str) -> tuple[list[dict], list[dict]]:
    matched: list[dict] = []
    others: list[dict] = []
    normalized_page = _normalize_page_value(page_name)
    normalized_domain = _normalize_domain_value(domain)
    for record in records or []:
        if _entry_matches_page(record, normalized_page, normalized_domain):
            matched.append(record)
        else:
            others.append(record)
    return matched, others


def _filter_records_for_page(records: list[dict], page_name: str, domain: str) -> list[dict]:
    matched, _ = _split_records_for_page(records, page_name, domain)
    return matched


def _page_file_paths(meta_dir: Path, prefix: str, page_name: str) -> tuple[Path, list[Path]]:
    raw = (page_name or "").strip()
    normalized = _normalize_page_value(raw)
    stripped = _strip_hash_suffix(raw)

    search_names: list[str] = []
    seen_names: set[str] = set()
    for candidate in (normalized, stripped, raw):
        candidate = (candidate or "").strip()
        if candidate and candidate not in seen_names:
            seen_names.add(candidate)
            search_names.append(candidate)
    if not search_names:
        search_names.append("page")

    base_name = search_names[0]
    base_path = meta_dir / f"{prefix}_{base_name}.json"

    variants: list[Path] = []
    seen_paths: set[Path] = set()

    def _append(path: Path):
        try:
            resolved = path.resolve()
        except Exception:
            resolved = path
        if resolved in seen_paths:
            return
        seen_paths.add(resolved)
        variants.append(path)

    for name in search_names:
        candidate = meta_dir / f"{prefix}_{name}.json"
        if candidate.exists():
            _append(candidate)
        pattern = f"{prefix}_{name}_*.json"
        for path in sorted(meta_dir.glob(pattern)):
            _append(path)

    if base_path not in variants:
        variants.insert(0, base_path)

    return base_path, variants


def _is_blank_value(value) -> bool:
    if value is None:
        return True
    if isinstance(value, bool):
        return False
    if isinstance(value, str):
        stripped = value.strip().lower()
        return stripped == "" or stripped in {"[]", "{}"}
    if isinstance(value, (list, tuple, set, dict)):
        return len(value) == 0
    return False


def _record_identity(record: dict) -> str | None:
    if not isinstance(record, dict):
        return None
    for key in ("ocr_id", "id", "unique_name"):
        value = record.get(key)
        if isinstance(value, str) and value.strip():
            return f"{key}:{value.strip().lower()}"
    label = (record.get("label_text") or "").strip().lower()
    intent = (record.get("intent") or "").strip().lower()
    ocr_type = (record.get("ocr_type") or "").strip().lower()
    if any((label, intent, ocr_type)):
        return f"fallback:{label}|{intent}|{ocr_type}"
    bbox = record.get("bbox")
    if isinstance(bbox, str) and bbox.strip():
        return f"bbox:{bbox.strip().lower()}"
    return None


def _should_replace(old_value, new_value) -> bool:
    if isinstance(new_value, bool):
        return new_value and not bool(old_value)
    if _is_blank_value(new_value):
        return False
    return old_value is None or _is_blank_value(old_value)


def _merge_record(existing: dict, incoming: dict) -> dict:
    merged = dict(existing or {})
    for key, value in (incoming or {}).items():
        if key not in merged or _should_replace(merged.get(key), value):
            merged[key] = value
    return merged


def _merge_metadata_records(existing_records: list[dict], new_records: list[dict]) -> list[dict]:
    merged: dict[str, dict] = {}
    order: list[str] = []
    counter = 0

    def _store(key: str, record: dict):
        if key not in order:
            order.append(key)
        merged[key] = dict(record or {})

    for record in existing_records or []:
        key = _record_identity(record)
        if not key:
            key = f"existing-{counter}"
            counter += 1
        _store(key, record)

    for record in new_records or []:
        key = _record_identity(record)
        if not key:
            key = f"new-{counter}"
            counter += 1
        if key in merged:
            merged[key] = _merge_record(merged[key], record)
        else:
            _store(key, record)

    return [merged[k] for k in order if k in merged]


def _resolve_page_file(meta_dir: Path, prefix: str, page_name: str) -> Path:
    raw = (page_name or "").strip()
    normalized = _normalize_page_value(raw)
    stripped = _strip_hash_suffix(raw)
    search_names = []
    seen_names = set()
    for name in (raw, normalized, stripped):
        if name and name not in seen_names:
            seen_names.add(name)
            search_names.append(name)

    candidates: list[Path] = []
    seen_paths: set[Path] = set()

    def _add_path(path: Path):
        nonlocal candidates
        try:
            resolved = path.resolve()
        except Exception:
            resolved = path
        if resolved in seen_paths:
            return
        seen_paths.add(resolved)
        candidates.append(path)

    for name in search_names:
        base = meta_dir / f"{prefix}_{name}.json"
        _add_path(base)
        pattern = f"{prefix}_{name}_*.json"
        for path in sorted(meta_dir.glob(pattern)):
            _add_path(path)

    for path in candidates:
        if path.exists():
            return path

    fallback_name = normalized or stripped or raw or "page"
    return meta_dir / f"{prefix}_{fallback_name}.json"


def _resolve_metadata_dir(domain: str) -> Path:
    env_dirs = [d for d in _env_metadata_dirs() if d.exists()]
    if env_dirs:
        return env_dirs[0].resolve()
    candidates = _candidate_metadata_dirs(domain)
    for meta in candidates:
        if not meta.exists():
            continue
        if _metadata_matches_domain(meta, domain):
            return meta
    for meta in candidates:
        if meta.exists():
            return meta
    raise HTTPException(status_code=404, detail="No metadata directory found.")
 
async def send_enrichment_requests(page_name: str, project_id: int, token: str, backend_base_url: str):
    from httpx import AsyncClient, HTTPStatusError

    BASE = f"{backend_base_url.rstrip('/')}/manual-enrichment"
    headers = {"Authorization": f"Bearer {token}"} if token else {}

    async with AsyncClient(timeout=None) as client:
        # 1) set the page name
        try:
            r = await client.post(f"{BASE}/set-current-page-name", params={"project_id": project_id}, json={"page_name": page_name}, headers=headers)
            r.raise_for_status()
        except Exception as e:
            print(f"🔥Error setting page name: {e!r}")
            return {"status": "fail", "count": 0, "error": str(e)}

        # 2) call enrichment endpoint
        try:
            await asyncio.sleep(2)
            resp = await client.post(f"{BASE}/capture-dom-from-client", params={"project_id": project_id}, json={}, headers=headers)
            resp.raise_for_status()
        except HTTPStatusError as e:
            # e.response.status_code & e.response.text will show you 404 or other codes
            print(f"🔥HTTP error {e.response.status_code}: {e.response.text!r}")
            return {"status": "fail", "count": 0, "error": f"HTTP {e.response.status_code}"}
        except Exception as e:
            print(f"🔥Network/connection error: {e!r}")
            return {"status": "fail", "count": 0, "error": str(e)}

        # 3) Success → parse JSON
        try:
            return resp.json()
        except Exception as e:
            print(f"🔥JSON parse error: {e!r}")
            return {"status": "fail", "count": 0, "error": "invalid JSON"}


@router.post("/launch-browser")
async def launch_browser(
    req: LaunchRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        if req.project_id is None:
            raise HTTPException(status_code=400, detail="project_id is required")
        active_domain = _domain_from_url(req.url)
        resolved_project = get_user_project(db, req.project_id, current_user)
        token = auth.create_access_token(
            {
                "sub": current_user.email,
                "uid": current_user.id,
                "org": current_user.organization,
                "org_id": current_user.organization_id,
            }
        )
        backend_public_base_url = get_backend_public_base_url(str(request.base_url).rstrip("/"))
        backend_internal_base_url = _resolve_internal_backend_base_url(
            str(request.base_url).rstrip("/")
        )
        project_context = build_project_context(current_user, resolved_project.id, db)
        tokens = set_request_context(project_context=project_context)
        project_paths = _ensure_project_structure(resolved_project)
        metadata_dir = Path(project_context.generated_src_dir) / "metadata"

        existing = await _get_session(current_user.id, req.project_id, required=False)
        if existing is not None:
            await _close_session(existing)
            await _delete_session(current_user.id, req.project_id)

        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(headless=False, slow_mo=100)
        context = await browser.new_context(bypass_csp=True)
        page = await context.new_page()
        inferred_page = _infer_page_name_from_url(req.url)
        session = ManualCaptureSession(
            user_id=current_user.id,
            project_id=req.project_id,
            playwright=playwright,
            browser=browser,
            context=context,
            page=page,
            current_page_name=inferred_page,
            current_app_domain=active_domain,
            metadata_dir=metadata_dir,
            closed=False,
        )
        await _store_session(session)

        def _mark_closed() -> None:
            session.closed = True

        await _activate_session_page(session, page)
        try:
            context.on("page", lambda new_page: asyncio.create_task(_activate_session_page(session, new_page)))
        except Exception:
            pass
        try:
            browser.on("disconnected", lambda: _mark_closed())
        except Exception:
            pass
        await page.goto(req.url, wait_until="domcontentloaded", timeout=60000)

        async def send_enrichment_wrapper(source, page_name):
            source_page = _binding_source_page(source)
            if source_page is not None:
                await _activate_session_page(session, source_page)
            print("[DEBUG] Triggering enrichment for:", page_name)
            result = await send_enrichment_requests(page_name, resolved_project.id, token, backend_internal_base_url)
            return json.dumps(result)

        async def get_available_pages_wrapper(source):
            source_page = _binding_source_page(source)
            if source_page is not None:
                await _activate_session_page(session, source_page)
            pages = _page_names_from_uploaded_images(db, resolved_project.id)
            return json.dumps({"pages": pages})

        async def close_browser_wrapper(source):
            print("[INFO] Close browser requested from client.")
            s = await _get_session(current_user.id, req.project_id, required=False)
            if s:
                await _close_session(s)
                await _delete_session(current_user.id, req.project_id)
            return json.dumps({"status": "success", "message": "Browser session closed."})

        try:
            await context.expose_binding("sendEnrichmentRequests", send_enrichment_wrapper)
            await context.expose_binding("getAvailablePages", get_available_pages_wrapper)
            await context.expose_binding("closeBrowser", close_browser_wrapper)
        except Exception:
            await page.expose_binding("sendEnrichmentRequests", send_enrichment_wrapper)
            await page.expose_binding("getAvailablePages", get_available_pages_wrapper)
            await page.expose_binding("closeBrowser", close_browser_wrapper)


        project_name = req.project_name
        project_name_js = json.dumps(project_name or "")
        project_id_js = json.dumps(req.project_id if req.project_id is not None else "")
        token_js = json.dumps(token or "")
        backend_base_url_js = json.dumps(backend_public_base_url)
        js = """
            if (!window._ocrShortcutRegistered) {
                window._ocrShortcutRegistered = true;
                console.log('[SmartAI] Modal enrichment JS injected');

                function ensureModal() {
                    if (document.getElementById('ocrModal')) return;
                    if (!document.body) return;
                    const modal = document.createElement('div');
                    modal.innerHTML = `
                        <div id="ocrModal" style="position:fixed;top:40%;left:50%;transform:translate(-50%,-50%);background:white;padding:20px;border:2px solid black;z-index:9999;display:none;">
                            <label>Select Page:</label><br/>
                            <select id="pageDropdown" style="margin:5px;padding:5px;width:250px;"></select><br/>
                            <button style="border:1px solid #333;padding:4px 8px;margin-right:6px;" onclick="triggerEnrichment()">Enrich</button>
                            <button style="border:1px solid #333;padding:4px 8px;margin-right:6px;" onclick="document.getElementById('ocrModal').style.display='none'">Close</button>
                            <button style="border:1px solid #333;padding:4px 8px;" onclick="closeManualCaptureBrowser()">Close Browser</button>
                            <div id="enrichmentMessageBox" style="margin-top:10px;font-weight:bold;color:green;"></div>
                        </div>
                    `;
                    document.body.appendChild(modal);
                }
                if (document.readyState === "loading") {
                    document.addEventListener("DOMContentLoaded", ensureModal, { once: true });
                } else {
                    ensureModal();
                }

                async function loadAvailablePages() {
                    try {
                        if (window.getAvailablePages) {
                            const resultStr = await window.getAvailablePages()
                            const data = JSON.parse(resultStr)
                            const dropdown = document.getElementById('pageDropdown');
                            const msg = document.getElementById("enrichmentMessageBox");
                            dropdown.innerHTML = "";
                            if (Array.isArray(data.pages) && data.pages.length > 0) {
                                for (const page of data.pages) {
                                    const option = document.createElement("option");
                                    option.value = page;
                                    option.innerText = page;
                                    dropdown.appendChild(option);
                                }
                                dropdown.value = dropdown.options[0].value;
                                if (msg) {
                                    msg.innerText = "";
                                }
                            } else {
                                const option = document.createElement("option");
                                option.value = "";
                                option.innerText = "No pages found";
                                dropdown.appendChild(option);
                                if (msg) {
                                    msg.innerText = "No pages available to select.";
                                    msg.style.color = "red";
                                }
                            }
                            return;
                        }
                        const activeDomain = encodeURIComponent((window.location.host || '').toLowerCase());
                        const projectName = PROJECT_NAME_TOKEN;
                        const projectId = PROJECT_ID_TOKEN;
                        const authToken = AUTH_TOKEN_TOKEN;
                        const backendBaseUrl = BACKEND_BASE_URL_TOKEN;
                        const projectParam = projectName ? `&project_name=${encodeURIComponent(projectName)}` : "";
                        const projectIdParam = (projectId !== null && projectId !== undefined && projectId !== "") ? `&project_id=${encodeURIComponent(projectId)}` : "";
                        const res = await fetch(`${backendBaseUrl}/manual-enrichment/available-pages?domain=${activeDomain}${projectParam}${projectIdParam}`, {
                            headers: authToken ? { "Authorization": `Bearer ${authToken}` } : {}
                        });
                        const data = await res.json();
                        const dropdown = document.getElementById('pageDropdown');
                        const msg = document.getElementById("enrichmentMessageBox");
                        dropdown.innerHTML = "";
                        if (Array.isArray(data.pages) && data.pages.length > 0) {
                            for (const page of data.pages) {
                                const option = document.createElement("option");
                                option.value = page;
                                option.innerText = page;
                                dropdown.appendChild(option);
                            }
                            dropdown.value = dropdown.options[0].value;
                            if (msg) {
                                msg.innerText = "";
                            }
                        } else {
                            const option = document.createElement("option");
                            option.value = "";
                            option.innerText = "No pages found";
                            dropdown.appendChild(option);
                            if (msg) {
                                msg.innerText = "No pages available to select.";
                                msg.style.color = "red";
                            }
                        }
                    } catch (err) {
                        const msg = document.getElementById("enrichmentMessageBox");
                        if (msg) {
                            msg.innerText = "❌ Failed to load available pages.";
                            msg.style.color = "red";
                        } else {
                            alert("❌ Failed to load available pages.");
                        }
                    }
                }

                window.closeManualCaptureBrowser = async function() {
                    const msg = document.getElementById("enrichmentMessageBox");
                    if (msg) {
                        msg.innerText = "Closing browser...";
                        msg.style.color = "blue";
                    }
                    try {
                        await window.closeBrowser();
                    } catch (err) {
                        if (msg) {
                            msg.innerText = "Failed to close browser: " + (err.message || err);
                            msg.style.color = "red";
                        }
                    }
                };
                
                window.triggerEnrichment = async function() {
                    const pageName = document.getElementById('pageDropdown').value;
                    const msg = document.getElementById("enrichmentMessageBox")
                    if (!pageName) {
                        msg.innerText = "❌ Page name is required.";
                        msg.style.color = "red";
                        return;
                    }
                    msg.innerText = "⏳ Enrichment in progress…"
                    msg.style.color   = "blue"
                    msg.offsetHeight  // force repaint

                    try {
                        const resultStr = await window.sendEnrichmentRequests(pageName)
                        const result    = JSON.parse(resultStr)
                        console.log("✅ Matched:", result);

                        if (result.status !== "success") {
                        msg.innerText = `❌ Enrichment failed: ${result.error}`
                        msg.style.color = "red"

                        } else if (result.count === 0) {
                        msg.innerText = "❌ Enrichment succeeded but no elements matched."
                        msg.style.color = "red"

                        } else {
                        msg.innerText = `✅ Enriched ${result.count} elements successfully.`
                        msg.style.color = "green"
                        }

                    } catch (err) {
                        console.error("Enrichment Error:", err);
                        msg.innerText = "❌ Enrichment Error: " + (err.message || err)
                        msg.style.color = "red"
                    }
                };

                document.addEventListener('keydown', function(e) {
                    if (e.altKey && (e.key === 'q' || e.key === 'Q')) {
                        ensureModal();
                        const modal = document.getElementById('ocrModal');
                        if (modal) {
                            modal.style.display = 'block';
                            loadAvailablePages();
                        }
                    }
                });
            }
            """
        js = js.replace("PROJECT_NAME_TOKEN", project_name_js)
        js = js.replace("PROJECT_ID_TOKEN", project_id_js)
        js = js.replace("AUTH_TOKEN_TOKEN", token_js)
        js = js.replace("BACKEND_BASE_URL_TOKEN", backend_base_url_js)
        # Persist the modal + hotkey on all future navigations.
        try:
            await context.add_init_script(js)
        except Exception:
            pass
        # Inject immediately for the current page.
        await page.evaluate(js)
        
        return {
            "message": f"✅ Browser launched and navigated to {req.url}. Press Alt+Q to open manual capture."
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if "tokens" in locals() and tokens:
            reset_request_context(tokens)

@router.post("/set-current-page-name")
async def set_page_name(
    req: PageNameSetRequest,
    project_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if project_id is None:
        raise HTTPException(status_code=400, detail="project_id is required")
    get_user_project(db, project_id, current_user)
    session = await _get_session(current_user.id, project_id)
    session.current_page_name = (req.page_name or "").strip() or "unknown_page"
    print(f'"message": f"??? Page name set to: {session.current_page_name}"')
    return

@router.post("/capture-dom-from-client")
async def capture_from_keyboard(
    req: CaptureRequest,
    project_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        effective_project_id = req.project_id or project_id
        if effective_project_id is None:
            raise HTTPException(status_code=400, detail="project_id is required")
        session = await _get_session(current_user.id, effective_project_id)
        page_name = (req.page_name or session.current_page_name or "").strip() or "unknown_page"
        if req.page_name:
            session.current_page_name = page_name
        print(f"[INFO] Enrichment triggered for: {page_name}")
        active_page = await _resolve_session_page(session)
        if active_page is None:
            raise HTTPException(status_code=500, detail="??? Cannot extract. No active page handle.")
        if active_page.is_closed():
            session.page = None
            raise HTTPException(status_code=500, detail="??? Cannot extract. Page is already closed.")
        # print('10')

        project = get_user_project(db, effective_project_id, current_user)
        project_paths = _ensure_project_structure(project)
        ctx = build_project_context(current_user, effective_project_id, db)
        tokens = set_request_context(project_context=ctx)
        metadata_dir = _metadata_dir(ctx)
        ocr_data = _load_ocr_records_for_page(db, project.id, page_name)
        if not ocr_data:
            raise HTTPException(
                status_code=404,
                detail=f"No OCR image metadata found for {page_name}",
            )

        dom_data = await extract_dom_metadata(active_page, page_name)
        table_data = await _extract_table_structured_data(active_page) or []
        if table_data:
            dom_data = list(dom_data) + list(table_data)
        # print('11 ', dom_data.count)

        print("[DEBUG] DOM elements extracted:", len(dom_data))

        col = _collection()
        # Create folder for debug metadata dump added by subhankar
        debug_metadata_dir = _debug_dir(ctx)
        # Write DOM data as raw text added by subhankar
        dom_dump_path = debug_metadata_dir / f"dom_data_{page_name}.txt"
        if dom_data:
            dom_dump_path.write_text(pprint.pformat(dom_data), encoding="utf-8")
        elif not dom_dump_path.exists():
            dom_dump_path.write_text("# No DOM data captured for this page.\n[]", encoding="utf-8")
        # Write OCR data as raw text added by subhankar
        ocr_dump_path = debug_metadata_dir / f"ocr_data_{page_name}.txt"
        if ocr_data:
            ocr_dump_path.write_text(pprint.pformat(ocr_data), encoding="utf-8")
        elif not ocr_dump_path.exists():
            ocr_dump_path.write_text("# No OCR data available for this page.\n[]", encoding="utf-8")
        
        updated_matches = match_and_update(ocr_data, dom_data, col)
    
        # Write after_match_and_update data as raw text added by subhankar
        after_dump_path = debug_metadata_dir / f"after_match_and_update_{page_name}.txt"
        if updated_matches:
            after_dump_path.write_text(pprint.pformat(updated_matches), encoding="utf-8")
        elif not after_dump_path.exists():
            after_dump_path.write_text("# No matches were produced for this page.\n[]", encoding="utf-8")
    
        standardized_matches = [
            build_standard_metadata(m, page_name, image_path="", source_url=active_page.url)
            for m in updated_matches
        ]

        existing_keys = {
            (_norm_text(m.get("label_text") or m.get("text") or ""), (m.get("tag_name") or "").lower())
            for m in standardized_matches
        }
        for rec in dom_data:
            tag = (rec.get("tag") or rec.get("tag_name") or "").lower()
            if tag not in {"th", "tr"}:
                continue
            label = rec.get("label_text") or rec.get("text") or ""
            if not label:
                continue
            key = (_norm_text(label), tag)
            if key in existing_keys:
                continue
            rec_copy = dict(rec)
            rec_copy.setdefault("label_text", label)
            rec_copy.setdefault("text", label)
            rec_copy.setdefault("tag_name", tag)
            rec_copy.setdefault("get_by_text", label)
            if not rec_copy.get("ocr_type"):
                rec_copy["ocr_type"] = "label" if tag == "th" else "text"
            standardized_matches.append(
                build_standard_metadata(
                    rec_copy,
                    page_name=page_name,
                    image_path="",
                    source_url=active_page.url,
                )
            )
            existing_keys.add(key)
        
        # Write standardized_matches data as raw text added by subhankar
        with open(debug_metadata_dir / f"standardized_matchesd{page_name}.txt", "w", encoding="utf-8") as f:
            f.write(pprint.pformat(standardized_matches))
    
        set_last_match_result(standardized_matches)
    
        # Save enriched metadata as JSON
        after_base, after_variants = _page_file_paths(metadata_dir, "after_enrichment", page_name)
        existing_after: list[dict] = []
        for variant in after_variants:
            existing_after.extend(_as_record_list(_load_json(variant)))
        matched_after, preserved_after = _split_records_for_page(
            existing_after,
            page_name,
            session.current_app_domain,
        )
        merged_after = _merge_metadata_records(matched_after, standardized_matches)
        with open(after_base, "w", encoding="utf-8") as f:
            json.dump(preserved_after + merged_after, f, indent=2)
        for variant in after_variants:
            try:
                if variant != after_base and variant.exists():
                    variant.unlink()
            except Exception:
                pass

        # Save aggregated after_enrichment data scoped to this project
        all_chroma_file = metadata_dir / "after_enrichment.json"
        aggregated_records = _as_record_list(_load_json(all_chroma_file))
        matched_aggregated, other_aggregated = _split_records_for_page(
            aggregated_records,
            page_name,
            session.current_app_domain,
        )
        merged_aggregated = _merge_metadata_records(matched_aggregated, standardized_matches)
        with open(all_chroma_file, "w", encoding="utf-8") as f:
            json.dump(other_aggregated + merged_aggregated, f, indent=2)
    
        return {
            "status": "success",
            "message": f"[Keyboard Trigger] Enriched {len(standardized_matches)} elements for page: {page_name}",
            "matched_data": standardized_matches,
            "count": len(standardized_matches)
        }
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(e)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if "tokens" in locals() and tokens:
            reset_request_context(tokens)

def _get_active_project(db: Session) -> Project:
    raise HTTPException(
        status_code=400,
        detail="project_id is required. Start a project before manual capture.",
    )


def _page_names_from_uploaded_images(db: Session, project_id: int) -> list[str]:
    names: set[str] = set()
    records = (
        db.query(ImageMetadata.page_name, ImageMetadata.image_name)
        .filter(ImageMetadata.project_id == project_id)
        .all()
    )
    for page_name, image_name in records:
        candidate = (page_name or "").strip()
        if not candidate and image_name:
            candidate = Path(image_name).stem
        if candidate:
            names.add(candidate)
    return sorted(names)


def _load_ocr_records_for_page(db: Session, project_id: int, page_name: str) -> list[dict]:
    records = (
        db.query(ImageMetadata.metadata_json)
        .filter(
            ImageMetadata.project_id == project_id,
            ImageMetadata.page_name == page_name,
        )
        .all()
    )
    ocr_records: list[dict] = []
    for (payload,) in records:
        if isinstance(payload, list):
            for item in payload:
                if not isinstance(item, dict):
                    continue
                entry = item.get("metadata") if isinstance(item.get("metadata"), dict) else item
                if isinstance(entry, dict):
                    ocr_records.append(entry)
    return ocr_records


def _resolve_project_from_request(
    db: Session,
    project_id: Optional[int] = None,
    project_name: Optional[str] = None,
    org_id: Optional[int] = None,
) -> Optional[Project]:
    if project_id is not None:
        query = db.query(Project).filter(Project.id == project_id)
        if org_id is not None:
            query = query.filter(Project.organization_id == org_id)
        project = query.first()
        if project:
            return project
    if project_name:
        normalized = Project.normalized_key(project_name)
        query = db.query(Project).filter(Project.project_key == normalized)
        if org_id is not None:
            query = query.filter(Project.organization_id == org_id)
        project = query.order_by(Project.created_at.desc()).first()
        if project:
            return project
    return None


@router.get("/available-pages")
async def list_page_names(
    project_id: int,
    domain: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = get_user_project(db, project_id, current_user)
    pages = _page_names_from_uploaded_images(db, project.id)
    return {"pages": sorted(pages), "status": "success", "domain": (domain or "").strip().lower()}

@router.on_event("shutdown")
async def shutdown_browser():
    sessions: list[ManualCaptureSession] = []
    async with _SESSION_LOCK:
        sessions = list(_SESSIONS.values())
        _SESSIONS.clear()
    for session in sessions:
        await _close_session(session)
 
@router.get("/latest-match-result")
async def get_latest_match_result(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        project = get_user_project(db, project_id, current_user)
        records = _collection().get(where={"project_id": project_id})
        matched = [r for r in records.get("metadatas", []) if r.get("dom_matched") is True]
        page_name = ""
        if matched:
            page_name = (matched[0].get("page_name") or "").strip()
        file_path = None
        results = []
        try:
            project_paths = _ensure_project_structure(project)
            meta_dir = Path(project_paths["src_dir"]) / "metadata"
            if page_name:
                after_base, _ = _page_file_paths(meta_dir, "after_enrichment", page_name)
                if after_base.exists():
                    file_path = str(after_base)

            page_counts: dict[str, int] = {}
            for rec in matched:
                pname = (rec.get("page_name") or "").strip() or "page"
                page_counts[pname] = page_counts.get(pname, 0) + 1

            for pname in sorted(page_counts.keys()):
                per_file = None
                try:
                    after_base, _ = _page_file_paths(meta_dir, "after_enrichment", pname)
                    if after_base.exists():
                        per_file = str(after_base)
                except Exception:
                    per_file = None
                results.append(
                    {
                        "page_name": pname,
                        "count": page_counts[pname],
                        "file": per_file,
                    }
                )
        except Exception:
            file_path = None
            results = []
        return {
            "status": "success",
            "matched_elements": matched,
            "count": len(matched),
            "page_name": page_name,
            "file": file_path,
            "results": results,
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/browser-status")
async def manual_browser_status(
    project_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
):
    if project_id is None:
        return {"closed": False, "reason": "project_id required"}
    session = await _get_session(current_user.id, project_id, required=False)
    return {"closed": True if session is None else bool(session.closed)}


@router.post("/cleanup-session")
async def cleanup_session(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    get_user_project(db, project_id, current_user)
    session = await _delete_session(current_user.id, project_id)
    if session is None:
        return {"status": "no-session"}
    await _close_session(session)
    return {"status": "closed"}
