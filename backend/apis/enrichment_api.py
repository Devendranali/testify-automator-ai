# enrichment_api.py
from __future__ import annotations

import os
import sys
import json
import re
import pprint
import asyncio
import hashlib
import time
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union, Tuple
from dataclasses import dataclass, field
from urllib.parse import urlparse, urljoin
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from chromadb import PersistentClient
from .projects_api import _ensure_project_structure, get_current_user, get_user_project
from config.settings import get_chroma_path
from playwright.async_api import (
    async_playwright,
    Page,
    Browser,
    Frame,
    TimeoutError as PWTimeoutError,
)

from utils.enrichment_status import reset_enriched
from logic.manual_capture_mode import (
    extract_dom_metadata,
    match_and_update,
    set_last_match_result,
)
from utils.match_utils import normalize_page_name
from utils.project_context import (
    filter_metadata_by_project,
)
from utils.request_context import get_project_id as get_request_project_id
from utils.request_context import set_request_context, reset_request_context, get_project_context
from utils.project_paths import ProjectContext, build_project_context
from utils.file_utils import build_standard_metadata
from utils.ui_actions_async import dismiss_cookie_banner
from utils.async_jobs import AsyncJobManager
from utils.session_manager import (
    auth_storage_path,
    auth_landing_path,
    should_start_auth_watch,
    wait_for_login_and_save,
    normalize_storage_state,
)
from database.project_storage import DatabaseBackedProjectStorage
from database.session import get_db, session_scope
from database.models import Project, User, OrganizationMember
from sqlalchemy.orm import Session

# -----------------------------------------------------------------------------
# Router & DB
# -----------------------------------------------------------------------------
router = APIRouter()
_ACTIVE_STORAGE_VAR: ContextVar[Optional[DatabaseBackedProjectStorage]] = ContextVar(
    "active_storage", default=None
)
_JOB_MANAGER = AsyncJobManager("enrichment")
_ENRICH_LAUNCH_LOCK = asyncio.Lock()


async def _safe_click(locator, *, timeout: int = 1000):
    try:
        await locator.wait_for(state="visible", timeout=timeout)
    except Exception:
        pass
    return await locator.click(timeout=timeout)


async def _wait_for_iframe(page: Page, *, timeout: int = 3000):
    try:
        await page.wait_for_selector("iframe", state="attached", timeout=timeout)
    except Exception:
        await page.wait_for_selector("iframe", timeout=timeout)


@dataclass
class ProjectBrowserSession:
    project_id: int
    user_id: int
    playwright: Any = None
    browser: Optional[Browser] = None
    page: Optional[Page] = None
    target: Optional[Union[Page, Frame]] = None
    current_page_name: str = "unknown_page"
    execution_mode: bool = False
    enrich_ui_enabled: bool = False
    autoscroll_enabled: bool = True
    src_directory: Optional[Path] = None
    chroma_path: Optional[Path] = None
    auth_watch_task: Optional[asyncio.Task] = None
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)


_PROJECT_SESSIONS: Dict[Tuple[int, int], ProjectBrowserSession] = {}
_SESSIONS_LOCK = asyncio.Lock()
_WRITE_LOCKS: Dict[Tuple[int, str], asyncio.Lock] = {}
_WRITE_LOCKS_LOCK = asyncio.Lock()


def _session_key(project_id: int, user_id: int) -> Tuple[int, int]:
    return (int(project_id), int(user_id))


async def _get_session(project_id: int, user_id: int) -> ProjectBrowserSession:
    session = _PROJECT_SESSIONS.get(_session_key(project_id, user_id))
    if not session:
        raise HTTPException(
            status_code=404,
            detail="No active browser session for this project. Launch the browser first.",
        )
    return session


async def _create_or_reset_session(
    project_id: int,
    user_id: int,
    src_directory: Path,
    chroma_path: Path,
) -> ProjectBrowserSession:
    async with _SESSIONS_LOCK:
        key = _session_key(project_id, user_id)
        session = _PROJECT_SESSIONS.get(key)
        if session is None:
            session = ProjectBrowserSession(project_id=project_id, user_id=user_id)
            _PROJECT_SESSIONS[key] = session
        async with session.lock:
            session.src_directory = src_directory
            session.chroma_path = chroma_path
            session.current_page_name = "unknown_page"
            session.execution_mode = False
            session.enrich_ui_enabled = False
            session.autoscroll_enabled = True
        return session


async def _remove_session(project_id: int, user_id: int) -> None:
    async with _SESSIONS_LOCK:
        _PROJECT_SESSIONS.pop(_session_key(project_id, user_id), None)


async def _get_write_lock(project_id: int, page_name: str) -> asyncio.Lock:
    key = (int(project_id or 0), str(page_name or ""))
    async with _WRITE_LOCKS_LOCK:
        lock = _WRITE_LOCKS.get(key)
        if lock is None:
            lock = asyncio.Lock()
            _WRITE_LOCKS[key] = lock
        return lock


@contextmanager
def _temporary_project_context(project_context: ProjectContext):
    tokens = set_request_context(project_context=project_context)
    try:
        yield
    finally:
        reset_request_context(tokens)


# Lazy chroma accessor to avoid creating repo-level data folder before a project is active
def _get_chroma_collection(projectChromaPath: Path):
    client = PersistentClient(projectChromaPath)
    return client.get_or_create_collection(
        name=os.environ.get("SMARTAI_CHROMA_COLLECTION", "element_metadata")
    )


_CHROMA_CACHE: Dict[Tuple[int, str], Tuple[float, Dict[str, Any]]] = {}
_CHROMA_CACHE_LOCK = asyncio.Lock()
_CHROMA_CACHE_TTL_S = 5.0


async def _invalidate_chroma_cache(project_id: int, page_name: Optional[str] = None) -> None:
    pid = int(project_id or 0)
    async with _CHROMA_CACHE_LOCK:
        keys = list(_CHROMA_CACHE.keys())
        for key in keys:
            if key[0] != pid:
                continue
            if page_name is None or key[1] == (page_name or ""):
                _CHROMA_CACHE.pop(key, None)


async def _get_cached_chroma(project_id: int, page_name: Optional[str]) -> Optional[Dict[str, Any]]:
    pid = int(project_id or 0)
    key = (pid, str(page_name or ""))
    now = time.time()
    async with _CHROMA_CACHE_LOCK:
        entry = _CHROMA_CACHE.get(key)
        if not entry:
            return None
        expires, payload = entry
        if expires < now:
            _CHROMA_CACHE.pop(key, None)
            return None
        return payload


async def _set_cached_chroma(project_id: int, page_name: Optional[str], payload: Dict[str, Any]) -> None:
    pid = int(project_id or 0)
    key = (pid, str(page_name or ""))
    async with _CHROMA_CACHE_LOCK:
        _CHROMA_CACHE[key] = (time.time() + _CHROMA_CACHE_TTL_S, payload)


def _filter_chroma_records(
    records: Dict[str, Any],
    *,
    project_id: Optional[int],
    page_name: Optional[str],
) -> Dict[str, Any]:
    metas = records.get("metadatas") or []
    ids = records.get("ids") or []
    docs = records.get("documents") or []
    want_pid = int(project_id) if project_id is not None else None
    want_page = _canonical(page_name) if page_name else None

    keep_idx: List[int] = []
    for idx, meta in enumerate(metas):
        if not isinstance(meta, dict):
            continue
        if want_pid is not None and meta.get("project_id") != want_pid:
            continue
        if want_page is not None and _canonical(meta.get("page_name", "")) != want_page:
            continue
        keep_idx.append(idx)

    def _slice(items: List[Any]) -> List[Any]:
        if not items:
            return []
        return [items[i] for i in keep_idx if i < len(items)]

    return {
        "ids": _slice(ids),
        "metadatas": _slice(metas),
        "documents": _slice(docs),
    }


async def _chroma_get_records(
    projectChromaPath: Path,
    *,
    project_id: Optional[int] = None,
    page_name: Optional[str] = None,
) -> Dict[str, Any]:
    collection = _get_chroma_collection(projectChromaPath)
    where: Dict[str, Any] = {}
    if project_id is not None:
        where["project_id"] = int(project_id)
    if page_name:
        where["page_name"] = page_name
    if where:
        try:
            recs = collection.get(where=where) or {}
            if recs.get("metadatas"):
                return recs
        except Exception:
            pass

        cached = await _get_cached_chroma(project_id or 0, page_name)
        if cached is not None:
            return cached

        recs = collection.get() or {}
        filtered = _filter_chroma_records(recs, project_id=project_id, page_name=page_name)
        await _set_cached_chroma(project_id or 0, page_name, filtered)
        return filtered

    return collection.get() or {}


# -----------------------------------------------------------------------------
# Runtime state
# -----------------------------------------------------------------------------
# PLAYWRIGHT = None
# BROWSER: Optional[Browser] = None
# PAGE: Optional[Page] = None
# TARGET: Optional[Union[Page, Frame]] = None
# CURRENT_PAGE_NAME: str = "unknown_page"

# execution/enrichment toggles
# EXECUTION_MODE: bool = False
# ENRICH_UI_ENABLED: bool = False           # modal disabled by default
# AUTOSCROLL_ENABLED: bool = True           # on by default for better capture


# -----------------------------------------------------------------------------
# Config (paths resolved lazily so project activation can update them)
# -----------------------------------------------------------------------------
def _src_dir() -> Path:
    ctx = get_project_context(required=True)
    path = Path(ctx.generated_src_dir)
    path.mkdir(parents=True, exist_ok=True)
    if not getattr(_src_dir, "_logged", False):
        print(f"[DEBUG] Using SRC_DIR={path} (ProjectContext)")
        _src_dir._logged = True
    return path


def _pages_dir() -> Path:
    path = _src_dir() / "pages"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _meta_dir(src_directory) -> Path:
    path = src_directory / "metadata"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _debug_dir(src_directory: Path) -> Path:
    path = src_directory / "ocr-dom-metadata"
    path.mkdir(parents=True, exist_ok=True)
    return path


# For default cookie path: backend/apis/enrichment_api.py -> backend/
_BACKEND_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_STORAGE_DIR = _BACKEND_ROOT / "storage"
_DEFAULT_COOKIES = _DEFAULT_STORAGE_DIR / "cookies.json"


# -----------------------------------------------------------------------------
# Models
# -----------------------------------------------------------------------------
class LaunchRequest(BaseModel):
    url: str = Field(..., description="Target URL (scheme optional; https tried first)")
    headless: bool = False
    slow_mo: int = 80
    ignore_https_errors: bool = True
    viewport_width: int = 1400
    viewport_height: int = 900
    wait_until: str = "auto"
    user_agent: Optional[str] = None
    extra_http_headers: Optional[Dict[str, str]] = None
    http_username: Optional[str] = None
    http_password: Optional[str] = None
    nav_timeout_ms: int = 60000

    # Stability toggles (opt-in)
    apply_visual_patches: bool = False
    enable_watchdog_reload: bool = False
    disable_gpu: bool = False
    disable_pinch_zoom: bool = True

    # UI / scroll
    enable_enrichment_ui: bool = False
    enable_autoscroll: bool = True

    # Auto-enrichment
    auto_enrich: bool = True
    enrich_strategy: str = Field(
        "mixed", description="one of: 'ocr' | 'crawl' | 'mixed'"
    )
    crawl_max_pages: int = 10
    crawl_max_depth: int = 2
    crawl_delay_ms: int = 400
    crawl_same_origin_only: bool = True
    close_after_enrich: bool = True  # <-- close browser when auto-enrich completes
    job_timeout_s: Optional[int] = None  # override ENRICH_JOB_TIMEOUT; <=0 disables timeout
    fast_mode: bool = False  # opt-in: speed-focused defaults for large apps


class CaptureRequest(BaseModel):
    pass


class PageNameSetRequest(BaseModel):
    page_name: str


class ExecutionModeRequest(BaseModel):
    enabled: bool


class AutoEnrichRequest(BaseModel):
    enrich_strategy: str = "mixed"
    crawl_max_pages: int = 10
    crawl_max_depth: int = 2
    crawl_delay_ms: int = 400
    crawl_same_origin_only: bool = True
    close_after_enrich: bool = True
    job_timeout_s: Optional[int] = None  # override ENRICH_JOB_TIMEOUT; <=0 disables timeout
    fast_mode: bool = False  # opt-in: speed-focused defaults for large apps


class CrawlRequest(BaseModel):
    start_url: Optional[str] = None
    max_pages: int = 10
    max_depth: int = 2
    delay_ms: int = 400
    same_origin_only: bool = True
    close_after_enrich: bool = True
    job_timeout_s: Optional[int] = None  # override ENRICH_JOB_TIMEOUT; <=0 disables timeout


class AuthStorageRequest(BaseModel):
    landing_url: Optional[str] = None
    storage: Optional[Dict[str, Any]] = None
    storage_json: Optional[str] = None
    cookies: Optional[List[Dict[str, Any]]] = None
    origins: Optional[List[Dict[str, Any]]] = None


# -----------------------------------------------------------------------------
# Optional UI (kept for compatibility; disabled by default)
# -----------------------------------------------------------------------------
UI_KEYBRIDGE_JS = r"""
(() => {
  if (window === window.top) return;
  if (window._smartaiKeyBridgeInstalled) return;
  window._smartaiKeyBridgeInstalled = true;
  function isEditable(el){ if(!el) return false; const t=(el.tagName||'').toLowerCase(); return t==='input'||t==='textarea'||t==='select'||el.isContentEditable; }
  function onKey(e){ if(window._smartaiDisabled) return; if(!(e.altKey && (e.key==='q'||e.key==='Q'))) return; if(e.ctrlKey||e.metaKey) return; if(isEditable(document.activeElement)) return; try{e.preventDefault();e.stopPropagation();}catch(_){} try{window.top.postMessage({__smartai:'TOGGLE_MODAL'},'*');}catch(_){}}  
  window.addEventListener('keydown', onKey, true);
})();
"""

UI_MODAL_TOP_JS = r"""
(() => {
  if (window !== window.top) return;
  if (window._smartaiTopInstalled) return;
  window._smartaiTopInstalled = true;
  function isEditable(el){ if(!el) return false; const t=(el.tagName||'').toLowerCase(); return t==='input'||t==='textarea'||t==='select'||el.isContentEditable; }
  function ensureModal(){
    if(document.getElementById('ocrModal')) return;
    const wrap=document.createElement('div');
    wrap.id='ocrModalWrapper';
    wrap.innerHTML=`<div id="ocrModal" style="position:fixed;top:40%;left:50%;transform:translate(-50%,-50%);background:#fff;padding:16px;border:2px solid #000;z-index:2147483647;display:none;min-width:360px;max-width:90vw;max-height:80vh;overflow:auto;border-radius:10px;font-family:Arial,sans-serif;">
      <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;">
        <label style="min-width:70px;">Page:</label>
        <select id="pageDropdown" style="padding:6px;min-width:220px;max-width:60vw;"></select>
        <button id="smartAI_refresh_pages">Refresh</button>
      </div>
      <div style="margin-top:10px;display:flex;gap:8px;flex-wrap:wrap;">
        <button id="smartAI_enrich_btn">Enrich</button>
        <button id="smartAI_close_btn">Close</button>
      </div>
      <div id="enrichmentMessageBox" style="margin-top:10px;font-weight:bold;color:green;"></div>
      <div style="margin-top:8px;color:#666;font-size:12px;">Tip: press <b>Alt+Q</b> to open/close</div>
    </div>`;
    document.body.appendChild(wrap);
    async function trigger(){ if(window._smartaiDisabled) return; const dd=document.getElementById('pageDropdown'); const msg=document.getElementById('enrichmentMessageBox'); const chosen=(dd&&dd.value||'').trim(); if(!chosen){ msg.textContent='âŒ No page found for this image.'; msg.style.color='red'; return; } msg.textContent='â³ Enrichment in progressâ€¦'; msg.style.color='blue'; try{ const res=JSON.parse(await window.smartAI_enrich(chosen)||'{}'); if(res.status!=='success'){ msg.textContent='âŒ '+(res.error||'Enrichment failed'); msg.style.color='red'; } else if(!res.count){ msg.textContent='âŒ Enrichment succeeded but no elements matched.'; msg.style.color='red'; } else { msg.textContent=`âœ… Enriched ${res.count} elements`; msg.style.color='green'; } } catch(e){ msg.textContent='âŒ Error: '+(e&&e.message||e); msg.style.color='red'; } }
    document.getElementById('smartAI_enrich_btn').onclick = trigger;
    document.getElementById('smartAI_close_btn').onclick = () => { const m=document.getElementById('ocrModal'); if(m) m.style.display='none'; };
    document.getElementById('smartAI_refresh_pages').onclick = async () => {
      const dd=document.getElementById('pageDropdown'); const msg=document.getElementById('enrichmentMessageBox'); if(!dd) return; dd.innerHTML=''; try{ const data=JSON.parse(await window.smartAI_availablePages()||'{}'); const pages=(data&&data.status==='success'&&Array.isArray(data.pages))?data.pages:[]; if(!pages.length){ msg.textContent='âš ï¸ No extracted image pages found.'; msg.style.color='orange'; } pages.forEach(p=>{ const opt=document.createElement('option'); opt.value=p; opt.innerText=p; dd.appendChild(opt); }); }catch(_){ msg.textContent='âŒ Failed to load pages.'; msg.style.color='red'; }
    };
  }
  function toggle(){ if(window._smartaiDisabled) return; if(!document.getElementById('ocrModal')) ensureModal(); const m=document.getElementById('ocrModal'); if(!m) return; m.style.display = m.style.display==='none' ? 'block' : 'none'; if(m.style.display==='block'){ document.getElementById('smartAI_refresh_pages').click(); } }
  window.addEventListener('keydown', e=>{ if(window._smartaiDisabled) return; if(!(e.altKey && (e.key==='q'||e.key==='Q'))) return; if(e.ctrlKey||e.metaKey) return; if(isEditable(document.activeElement)) return; try{e.preventDefault();e.stopPropagation();}catch(_){ } toggle(); }, true);
  window.addEventListener('message', ev => { if(window._smartaiDisabled) return; if((ev&&ev.data||{}).__smartai==='TOGGLE_MODAL') toggle(); });
  window.smartAI_disableUI = () => { try{ window._smartaiDisabled=true; const w=document.getElementById('ocrModalWrapper'); if(w) w.remove(); }catch(_){ } };
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded', ensureModal); else ensureModal();
})();
"""

# -----------------------------------------------------------------------------
# Optional stability JS
# -----------------------------------------------------------------------------
STABILITY_VIEWPORT_CSS_JS = r"""
(() => {
  try {
    let m=document.querySelector('meta[name="viewport"]');
    if(!m){ m=document.createElement('meta'); m.name='viewport'; document.head.appendChild(m); }
    const content=m.getAttribute('content')||'';
    const kv=new Map(content.split(',').map(s=>s.trim()).filter(Boolean).map(s=>s.split('=')));
    kv.set('width','device-width'); kv.set('initial-scale','1'); kv.set('maximum-scale','1'); kv.set('user-scalable','no');
    m.setAttribute('content', Array.from(kv.entries()).map(([k,v])=>`${k}=${v}`).join(','));
    const css=`html,body{scroll-behavior:auto!important;overscroll-behavior:none!important;} *{animation:none!important;transition:none!important;}`;
    const s=document.createElement('style'); s.textContent=css; document.head.appendChild(s);
  } catch(e) {}
})();
"""

WATCHDOG_RELOAD_JS = r"""
(() => {
  if (window._smartaiWatchdog) return;
  window._smartaiWatchdog = true;
  let blanks = 0;
  const tick = async () => {
    try {
      const body = document.body;
      const hasBox = !!(body && body.getBoundingClientRect && body.getBoundingClientRect().width>0);
      const len = (body && (body.innerText||"").trim().length) || 0;
      const looksBlank = hasBox && len === 0;
      blanks = looksBlank ? (blanks+1) : 0;
      if (blanks >= 6) { blanks = 0; location.reload(); }
    } catch(e) {}
    setTimeout(tick, 200);
  };
  setTimeout(tick, 200);
})();
"""


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def _safe_log(*a):
    try:
        print(*a)
    except Exception:
        pass


def _enrich_debug_enabled() -> bool:
    return str(os.getenv("SMARTAI_ENRICH_DEBUG", "")).strip().lower() in (
        "1",
        "true",
        "yes",
        "y",
        "on",
    )


def _json_safe(value: Any) -> Any:
    """Ensure response payload is JSON-serializable."""
    if value is None:
        return None
    try:
        json.dumps(value)
        return value
    except Exception:
        try:
            return json.loads(json.dumps(value, default=str))
        except Exception:
            return str(value)


def _ts() -> str:
    return datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")


def _canonical(name: str) -> str:
    n = normalize_page_name(name or "")
    if not n:
        return n
    n = re.sub(r"(?i)^(page|screen|view)+", "", n)
    n = re.sub(r"(?i)(page|screen|view)+$", "", n)
    n = re.sub(r"[_\-\s]+", "_", n).strip("_")
    return n or "page"


def _ensure_dirs(src_directory) -> Dict[str, Path]:
    return {"debug": _debug_dir(src_directory), "meta": _meta_dir(src_directory)}


def _set_active_storage(storage: Optional[DatabaseBackedProjectStorage]) -> None:
    _ACTIVE_STORAGE_VAR.set(storage)


@contextmanager
def _activate_project_storage(db: Session):
    project = _get_active_project(db)
    storage = DatabaseBackedProjectStorage(project, _src_dir(), db)
    _set_active_storage(storage)
    try:
        yield project, storage
    finally:
        _set_active_storage(None)


@contextmanager
def _activate_project_storage_from_scope():
    with session_scope() as scoped_db:
        with _activate_project_storage(scoped_db) as ctx:
            yield ctx


def _persist_project_file(path: Path, content: str, encoding: str = "utf-8") -> None:
    if path.suffix.lower() == ".txt":
        return
    storage = _ACTIVE_STORAGE_VAR.get()
    if not storage:
        return
    try:
        relative = path.relative_to(storage.base_dir)
    except ValueError:
        try:
            relative = path.relative_to(_src_dir())
        except ValueError:
            return
    storage.write_file(relative.as_posix(), content, encoding)


def _write_project_file(path: Path, content: str, encoding: str = "utf-8") -> None:
    path.write_text(content, encoding=encoding)
    _persist_project_file(path, content, encoding)


def _atomic_write_project_file(path: Path, content: str, encoding: str = "utf-8") -> None:
    tmp_name = f"{path.name}.tmp_{os.getpid()}_{_ts()}"
    tmp_path = path.with_name(tmp_name)
    tmp_path.write_text(content, encoding=encoding)
    tmp_path.replace(path)
    _persist_project_file(path, content, encoding)


async def _atomic_merge_write_enrichment_page(
    *,
    project_id: int,
    page_name: str,
    src_directory: Path,
    output_path: Path,
    new_records: list[dict],
) -> list[dict]:
    lock = await _get_write_lock(project_id, page_name)
    async with lock:
        try:
            existing_payload = (
                json.loads(output_path.read_text(encoding="utf-8") or "[]")
                if output_path.exists()
                else []
            )
        except Exception:
            existing_payload = []
        combined_payload = _merge_enrichment_records(existing_payload, new_records)
        _atomic_write_project_file(
            output_path, json.dumps(combined_payload, indent=2), encoding="utf-8"
        )
        await _invalidate_chroma_cache(project_id, page_name)
    return combined_payload


def _resolve_project_for_user(
    db: Session,
    current_user: Optional[User],
    project_id: Optional[int] = None,
) -> Project:
    pid = project_id or get_request_project_id()
    if pid is None:
        raise HTTPException(status_code=400, detail="project_id is required")
    if current_user is None:
        raise HTTPException(status_code=403, detail="Organization membership required")
    org_ids = OrganizationMember.user_org_ids(db, current_user.id)
    if not org_ids:
        raise HTTPException(status_code=403, detail="Organization membership required")
    project = (
        db.query(Project)
        .filter(Project.id == int(pid), Project.organization_id.in_(org_ids))
        .first()
    )
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    return project


def _get_active_project(db: Session, current_user: Optional[User] = None) -> Project:
    return _resolve_project_for_user(db, current_user)


def _build_storage_state(payload: AuthStorageRequest) -> Dict[str, Any]:
    if payload.storage_json:
        try:
            parsed = json.loads(payload.storage_json)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Invalid storage_json: {exc}") from exc
        if isinstance(parsed, dict):
            storage_state = parsed
        else:
            raise HTTPException(status_code=400, detail="storage_json must be a JSON object")
    elif payload.storage:
        storage_state = payload.storage
    else:
        storage_state = {
            "cookies": payload.cookies or [],
            "origins": payload.origins or [],
        }

    if not isinstance(storage_state, dict):
        raise HTTPException(status_code=400, detail="Storage payload must be an object")

    storage_state.setdefault("cookies", [])
    storage_state.setdefault("origins", [])
    if not isinstance(storage_state.get("cookies"), list):
        raise HTTPException(status_code=400, detail="cookies must be a list")
    if not isinstance(storage_state.get("origins"), list):
        raise HTTPException(status_code=400, detail="origins must be a list")
    return storage_state


def _same_origin(a: Optional[str], b: Optional[str]) -> bool:
    pa, pb = urlparse(a or ""), urlparse(b or "")
    return (pa.netloc or "").lower() != "" and (pa.netloc or "").lower() == (
        pb.netloc or ""
    ).lower()


def _resolve_storage_file(env_val: Optional[str] = None) -> Path:
    """
    Accept a file path or a directory; if directory, auto-append cookies.json.
    Priority:
      0) auth/storage.json (project-level auth storage)
      1) UI_STORAGE_FILE env (if set)
      2) SMARTAI_STORAGE_FILE env (if set)
      3) backend/storage/cookies.json (default)
    """
    raw = (env_val or "").strip()
    if not raw:
        raw = (
            os.getenv("UI_STORAGE_FILE", "").strip()
            or os.getenv("SMARTAI_STORAGE_FILE", "").strip()
        )
    if not raw:
        ctx = get_project_context(required=True)
        candidate = auth_storage_path(Path(ctx.project_dir))
        if candidate.exists():
            return candidate.resolve()
    if raw:
        p = Path(raw)
        if p.exists() and p.is_dir():
            return (p / "cookies.json").resolve()
        return p.resolve()
    return _DEFAULT_COOKIES.resolve()


async def _ocr_name_counts(projectChromaPath: Path) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    try:
        pid = get_request_project_id()
        recs = await _chroma_get_records(projectChromaPath, project_id=pid)
        for m in filter_metadata_by_project(recs.get("metadatas") or []):
            pn = (m or {}).get("page_name")
            if not pn:
                continue
            c = _canonical(pn)
            if not c:
                continue
            counts[c] = counts.get(c, 0) + 1
    except Exception:
        pass
    return counts


async def _available_pages_for_dropdown(projectChromaPath: Path) -> List[str]:
    counts = await _ocr_name_counts(projectChromaPath)
    noise = {"unknown", "unknown_page", "basepage"}
    for k in list(counts.keys()):
        if k in noise:
            counts.pop(k, None)
    names = list(counts.keys())
    names.sort(key=lambda n: (-counts[n], n))
    return names


def _short_hash(s: str) -> str:
    try:
        return hashlib.md5((s or "").encode("utf-8")).hexdigest()[:8]
    except Exception:
        return "00000000"


def _output_path_for_page(
    src_directory: Path, page_name: str, source_url: Optional[str]
) -> Path:
    meta_dir = _ensure_dirs(src_directory)["meta"]
    return meta_dir / f"after_enrichment_{page_name}.json"


def _merge_enrichment_records(
    existing: List[Dict[str, Any]], incoming: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    merged: List[Dict[str, Any]] = []
    index_map: Dict[tuple, int] = {}

    def _key(item: Dict[str, Any]) -> tuple:
        identifier = (
            (item or {}).get("unique_name")
            or (item or {}).get("id")
            or (item or {}).get("ocr_id")
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


def _norm_text(s: Optional[str]) -> str:
    if not s:
        return ""
    return " ".join(
        (s or "").replace("\n", " ").replace("\r", " ").strip().strip(":").split()
    ).lower()


def _standardize_dom_only(
    rec: Dict[str, Any], page_name: str, source_url: Optional[str]
) -> Dict[str, Any]:
    bbox = rec.get("bbox") or {}
    label = (
        rec.get("label_text")
        or rec.get("aria_label")
        or rec.get("placeholder")
        or rec.get("text")
        or ""
    )
    return {
        "page_name": page_name,
        "source_url": source_url or "",
        "label_text": label,
        "text": rec.get("text"),
        "aria_label": rec.get("aria_label"),
        "placeholder": rec.get("placeholder"),
        "title": rec.get("title"),
        "data_testid": rec.get("data_testid"),
        "data_qa": rec.get("data_qa"),
        "data_cy": rec.get("data_cy"),
        "data_test": rec.get("data_test"),
        "css_selector": rec.get("css_selector"),
        "tag_name": rec.get("tag"),
        "role": rec.get("role"),
        "id": rec.get("id"),
        "name": rec.get("name"),
        "type": rec.get("type"),
        "is_draggable": rec.get("is_draggable", False),
        "is_droppable": rec.get("is_droppable", False),
        "click_type": rec.get("click_type", ""),
        "drag_handle_selector": rec.get("drag_handle_selector", ""),
        "drag_handle_text": rec.get("drag_handle_text", ""),
        "bbox": {
            "x": bbox.get("x", 0),
            "y": bbox.get("y", 0),
            "width": bbox.get("width", 0),
            "height": bbox.get("height", 0),
        },
        "dom_matched": False,
        "ocr_present": False,
        "ts": _ts(),
    }


def _no_elements_record(page_name: str, source_url: Optional[str]) -> Dict[str, Any]:
    return {
        "page_name": page_name,
        "source_url": source_url or "",
        "dom_matched": False,
        "ocr_present": False,
        "no_elements_found": True,
        "ts": _ts(),
    }


# -----------------------------------------------------------------------------
# Page / frame helpers
# -----------------------------------------------------------------------------
async def _is_js_accessible(fr: Union[Page, Frame]) -> bool:
    try:
        return await fr.evaluate("!!document && !!document.body")
    except Exception:
        return False


async def _pre_settle(fr: Union[Page, Frame], timeout_ms: int = 8000) -> None:
    try:
        try:
            await fr.wait_for_load_state("domcontentloaded", timeout=timeout_ms)
        except Exception:
            pass
        try:
            await fr.wait_for_selector("body", state="attached", timeout=timeout_ms)
        except Exception:
            pass
    except Exception:
        pass


async def _progressive_autoscroll(
    AUTOSCROLL_ENABLED: bool,
    EXECUTION_MODE: bool,
    fr: Union[Page, Frame],
    steps: int = 6,
    pause_ms: int = 250,
):
    if EXECUTION_MODE or not AUTOSCROLL_ENABLED:
        return
    try:
        await fr.evaluate(
            f"""
        (async () => {{
          const sleep = t=>new Promise(r=>setTimeout(r,t));
          const doc=document; const se=doc.scrollingElement||doc.documentElement||doc.body;
          const H = se ? (se.scrollHeight||0) : (doc.documentElement.scrollHeight||doc.body.scrollHeight||0);
          const step = Math.max(1, Math.floor(H/{max(1, steps)}));
          let y=0; for(let i=0;i<{max(1, steps)};i++){{ y+=step; window.scrollTo(0,y); await sleep({max(0, pause_ms)}); }}
          await sleep({max(0, pause_ms)}); window.scrollTo(0,0);
        }})()"""
        )
    except Exception:
        pass


async def _open_potential_modals(fr: Union[Page, Frame]):
    """
    Attempt to open modals by clicking elements that might trigger them.
    This is a heuristic approach to capture modal DOM during enrichment.
    """
    try:
        # Select elements that likely open modals: buttons/links with onclick or common modal triggers
        selectors = [
            "button[onclick]",
            'input[type="button"][onclick]',
            "a[onclick]",
            'button[data-toggle="modal"]',
            "button[data-target]",
            '[role="button"][onclick]',
            'button:has-text("Open"), button:has-text("Show"), button:has-text("Modal")',  # Playwright pseudo-selectors
        ]
        for selector in selectors:
            try:
                elements = await fr.query_selector_all(selector)
                for el in elements[:5]:  # Limit to avoid excessive clicks
                    try:
                        # Check if visible and not disabled
                        is_visible = await el.is_visible()
                        is_disabled = await el.get_attribute("disabled")
                        if is_visible and not is_disabled:
                            await _safe_click(el)
                            await asyncio.sleep(0.5)  # Wait for modal to appear
                    except Exception:
                        pass
            except Exception:
                pass
    except Exception:
        pass


def __log_page_events(page: Page):
    page.on("console", lambda m: _safe_log(f"[console:{m.type}] {m.text}"))
    page.on("pageerror", lambda e: _safe_log(f"[pageerror] {e}"))
    page.on(
        "requestfailed",
        lambda req: _safe_log(f"[requestfailed] {req.url} -> {req.failure}"),
    )
    page.on(
        "response",
        lambda resp: (
            _safe_log(f"[http {resp.status}] {resp.url}")
            if resp.status >= 400
            else None
        ),
    )


async def __snapshot_if_blank(page: Page, tag: str):
    if not _enrich_debug_enabled():
        return
    try:
        is_blank = await page.evaluate(
            """() => {
          const b=document.body; if(!b) return false;
          const rect=b.getBoundingClientRect(); const len=(b.innerText||"").trim().length;
          return rect && rect.width>0 && rect.height>0 && len===0;
        }"""
        )
        if is_blank:
            try:
                dbg = _ensure_dirs()["debug"]
                path = dbg / f"blank_{tag}_{_ts()}.png"
                await page.screenshot(path=str(path), full_page=True)
                _safe_log(f"[blank-detector] Saved screenshot: {path}")
            except Exception as e:
                _safe_log(f"[blank-detector] could not write blank snapshot: {e}")
    except Exception as e:
        _safe_log(f"[blank-detector] snapshot error: {e}")


async def _dismiss_cookie_banner(page: Page) -> bool:
    return await dismiss_cookie_banner(page)


async def _smart_navigate(
    page: Page, raw_url: str, wait_until: str = "auto", timeout_ms: int = 60000
):
    def _with_scheme(u: str, scheme: str) -> str:
        p = urlparse(u)
        return f"{scheme}://{u}" if not p.scheme else u

    strategies = (
        ["domcontentloaded", "load", "commit", "networkidle"]
        if (wait_until or "").lower() == "auto"
        else [wait_until]
    )

    for scheme in ("https", "http"):
        url = _with_scheme(raw_url, scheme)
        for wu in strategies:
            try:
                resp = await page.goto(url, wait_until=wu, timeout=timeout_ms)
                try:
                    await page.wait_for_load_state(
                        "domcontentloaded", timeout=min(10000, timeout_ms)
                    )
                except Exception:
                    pass
                try:
                    await page.wait_for_selector("body", state="attached", timeout=5000)
                except Exception:
                    pass
                try:
                    await _dismiss_cookie_banner(page)
                except Exception:
                    pass
                return resp
            except PWTimeoutError:
                continue
            except Exception:
                break
    try:
        await page.goto(_with_scheme(raw_url, "https"), timeout=timeout_ms)
    except Exception:
        pass
    try:
        await _dismiss_cookie_banner(page)
    except Exception:
        pass
    return None


async def _clean_restart(PAGE, BROWSER, PLAYWRIGHT):
    try:
        if PAGE and hasattr(PAGE, "is_closed") and not PAGE.is_closed():
            await PAGE.close()
    except Exception:
        pass
    try:
        if BROWSER:
            await BROWSER.close()
    except Exception:
        pass
    try:
        if PLAYWRIGHT:
            await PLAYWRIGHT.stop()
    except Exception:
        pass


async def _select_extraction_target(page: Page) -> Union[Page, Frame]:
    try:
        await _wait_for_iframe(page, timeout=3000)
    except Exception:
        pass

    candidates: List[Union[Page, Frame]] = []
    if page.main_frame:
        candidates.append(page.main_frame)
    candidates.extend([f for f in page.frames if f is not page.main_frame])

    top_url = getattr(page, "url", "") or ""
    ad_like = re.compile(
        r"(onetag|rubicon|adnxs|doubleclick|googlesyndication|taboola|adsystem|bidswitch|pubmatic|criteo|cloudflare|googletagmanager|trustarc|consent|cookie|privacy-center)",
        re.I,
    )

    async def _score_frame(fr: Union[Page, Frame]) -> Tuple[int, bool, str]:
        try:
            ok = await fr.evaluate("Boolean(document && document.body)")
            if not ok:
                return (-10_000, False, "")
            area = await fr.evaluate(
                """() => { try { const w=window.innerWidth||0, h=window.innerHeight||0; return Math.max(1,w)*Math.max(1,h); } catch { return 1; } }"""
            )
            interactive = int(
                await fr.evaluate(
                    "document.querySelectorAll('input,select,textarea,button,a,[role],[contenteditable=\"true\"]').length"
                )
            )
            url = ""
            try:
                url = fr.url or ""
            except Exception:
                url = ""
            same = _same_origin(top_url, url)
            score = (
                int(area / 10)
                + interactive * 20
                + (3000 if same else 0)
                - (8000 if ad_like.search(url) else 0)
            )
            return (score, same, url)
        except Exception:
            return (-10_000, False, "")

    best: Union[Page, Frame] = page
    best_score = -10_000
    for fr in candidates:
        score, _, _ = await _score_frame(fr)
        if score > best_score:
            best_score = score
            best = fr
    return best or page


# -----------------------------------------------------------------------------
# Derive page name & links
# -----------------------------------------------------------------------------
async def _derive_page_name(p: Page) -> str:
    try:
        title = (await p.title()) or ""
    except Exception:
        title = ""
    url = getattr(p, "url", "") or ""
    parsed = urlparse(url)
    path = (parsed.path or "/").strip("/").replace("/", "_") or "home"
    host = (parsed.netloc or "site").split(":")[0]
    pieces = [normalize_page_name(title or ""), normalize_page_name(f"{host}_{path}")]
    candidate = next((c for c in pieces if c), "unknown_page")
    return _canonical(candidate)


async def _enumerate_links(p: Page, same_origin_only: bool = True) -> List[str]:
    top = getattr(p, "url", "") or ""
    try:
        hrefs = await p.evaluate(
            """() => Array.from(document.querySelectorAll('a[href]')).map(a=>a.getAttribute('href')).filter(Boolean)"""
        )
    except Exception:
        return []
    out = []
    for h in hrefs:
        full = urljoin(top, h)
        if same_origin_only and not _same_origin(top, full):
            continue
        if full.startswith("mailto:") or full.startswith("tel:"):
            continue
        if urlparse(full).fragment:
            full = full.split("#", 1)[0]
        if full not in out:
            out.append(full)
    return out


# -----------------------------------------------------------------------------
# NEW: URL harvesting & navigation-to-page logic
# -----------------------------------------------------------------------------
async def _candidate_urls_for_page(page_name: str, projectChromaPath: Path) -> List[str]:
    """
    Collect possible URLs for a given canonical page name from ChromaDB metadatas.
    We look for common fields and rank by frequency.
    """
    can = _canonical(page_name)
    url_fields = ("source_url", "url", "page_url", "origin_url")
    freq: Dict[str, int] = {}
    try:
        pid = get_request_project_id()
        recs = await _chroma_get_records(
            projectChromaPath, project_id=pid, page_name=page_name
        )
        for m in recs.get("metadatas") or []:
            if _canonical((m or {}).get("page_name", "")) != can:
                continue
            for f in url_fields:
                u = (m or {}).get(f)
                if not u:
                    continue
                u = str(u).strip()
                if not u:
                    continue
                # ignore data URLs / mailto / tel etc.
                if (
                    u.startswith("data:")
                    or u.startswith("mailto:")
                    or u.startswith("tel:")
                ):
                    continue
                freq[u] = freq.get(u, 0) + 1
    except Exception:
        pass
    # rank by count desc, then shorter path first (heuristic)
    urls = list(freq.keys())

    def _rank(u: str) -> Tuple[int, int]:
        try:
            p = urlparse(u)
            path_len = len((p.path or "").strip("/").split("/"))
        except Exception:
            path_len = 999
        return (-freq[u], path_len)

    urls.sort(key=_rank)
    return urls


async def _click_nav_element_for_tokens(
    p: Page, token_words: List[str], timeout_ms: int = 8000
) -> bool:
    """
    Try clicking a link/button/menu whose visible text contains most of the token words.
    """
    words = [w for w in token_words if w]
    if not words:
        return False
    pattern = " ".join(words)
    # Try roles first for accessibility-friendly sites
    try:
        btn = p.get_by_role("link", name=re.compile(pattern, re.I))
        await _safe_click(btn.first, timeout=timeout_ms)
        return True
    except Exception:
        pass
    try:
        btn = p.get_by_role("button", name=re.compile(pattern, re.I))
        await _safe_click(btn.first, timeout=timeout_ms)
        return True
    except Exception:
        pass
    # Generic locator with :has-text()
    try:
        loc = p.locator(
            f"a:has-text(/{'|'.join(map(re.escape, words))}/i), button:has-text(/{'|'.join(map(re.escape, words))}/i)"
        )
        count = await loc.count()
        if count > 0:
            await _safe_click(loc.first, timeout=timeout_ms)
            return True
    except Exception:
        pass
    return False


async def _derive_matches_name(p: Page, desired_can: str) -> bool:
    try:
        got = await _derive_page_name(p)
        return got == desired_can
    except Exception:
        return False


async def _ensure_on_page(
    PAGE: Page,
    page_name: str,
    projectChromaPath: Path,
    same_origin_only: bool = True,
    nav_timeout_ms: int = 60000,
) -> None:
    """
    Make best effort to navigate the browser to the page corresponding to `page_name`.
    Strategy:
      1) If current page already matches canonical name -> return.
      2) Navigate to best candidate URL(s) harvested from Chroma metadata.
      3) Try clicking a nav link/button based on page-name tokens.
      4) Probe discovered links (limited BFS) looking for a page-name match.
    """

    if PAGE is None:
        raise HTTPException(status_code=500, detail="No active page to navigate")

    desired_can = _canonical(page_name)

    # 1) Already there?
    try:
        if await _derive_matches_name(PAGE, desired_can):
            _safe_log(f"[nav] Already on target page '{desired_can}'")
            return
    except Exception:
        pass

    base_url = getattr(PAGE, "url", None)

    # 2) Candidate URLs from metadata
    candidates = await _candidate_urls_for_page(page_name, projectChromaPath)
    for u in candidates:
        if same_origin_only and base_url and not _same_origin(base_url, u):
            continue
        _safe_log(f"[nav] Trying candidate URL for '{desired_can}': {u}")
        try:
            await _smart_navigate(PAGE, u, wait_until="auto", timeout_ms=nav_timeout_ms)
            await __snapshot_if_blank(PAGE, "after-candidate-url")
            if await _derive_matches_name(PAGE, desired_can):
                _safe_log(f"[nav] Matched page after direct URL: {u}")
                return
        except Exception as e:
            _safe_log(f"[nav] Candidate URL failed: {e}")

    # 3) Try clicking nav element(s) that match page-name tokens
    tokens = re.split(r"[_\-\s]+", desired_can)
    try:
        clicked = await _click_nav_element_for_tokens(
            PAGE, tokens, timeout_ms=min(8000, nav_timeout_ms)
        )
        if clicked:
            try:
                await PAGE.wait_for_load_state("domcontentloaded", timeout=8000)
            except Exception:
                pass
            await __snapshot_if_blank(PAGE, "after-click-nav")
            if await _derive_matches_name(PAGE, desired_can):
                _safe_log("[nav] Matched page after clicking nav element")
                return
    except Exception:
        pass

    # 4) Limited BFS over discovered links from current page
    try:
        links = await _enumerate_links(PAGE, same_origin_only=same_origin_only)
    except Exception:
        links = []

    queue = links[:20]  # cap exploration
    visited: Set[str] = set()
    while queue:
        u = queue.pop(0)
        if u in visited:
            continue
        visited.add(u)
        _safe_log(f"[nav] BFS probing: {u}")
        try:
            await _smart_navigate(PAGE, u, wait_until="auto", timeout_ms=nav_timeout_ms)
            await __snapshot_if_blank(PAGE, "after-bfs")
            if await _derive_matches_name(PAGE, desired_can):
                _safe_log(f"[nav] Matched page via BFS: {u}")
                return
        except Exception:
            continue

    _safe_log(
        f"[nav] âš ï¸ Could not confidently navigate to page '{desired_can}'. Continuing with current page."
    )


# -----------------------------------------------------------------------------
# Extraction & enrichment core
# -----------------------------------------------------------------------------
def _dedupe_records(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    out: List[Dict[str, Any]] = []
    for r in rows or []:
        key = (
            (r.get("tag") or ""),
            (r.get("id") or ""),
            (r.get("name") or ""),
            (r.get("type") or ""),
            _norm_text(
                r.get("label_text")
                or r.get("aria_label")
                or r.get("placeholder")
                or r.get("text")
                or ""
            ),
        )
        if key in seen:
            continue
        seen.add(key)
        out.append(r)
    return out


async def _rich_extract_dom_metadata(fr: Union[Page, Frame]) -> List[Dict[str, Any]]:
    js = r"""
    (() => {
      const out = [], seen = new Set();
      const norm = s => (s || "").replace(/\s+/g, " ").trim();
 
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
 
      const isInteractable = el => !el.disabled && !el.closest('nav,[role="navigation"],header,footer,[aria-hidden="true"],[hidden]');
      const textOf = el => norm(el ? (el.innerText || el.textContent || "") : "");
      const clickType = el => {
        try {
          const attr = name => (el.getAttribute && el.getAttribute(name)) || "";
          const data = [
            attr("data-action"),
            attr("data-click"),
            attr("data-event"),
            attr("data-handler"),
            attr("data-action-type"),
            attr("contextmenu")
          ].join(" ").toLowerCase();
          const hasContext = (el.getAttribute && el.getAttribute("oncontextmenu") !== null) || (el.oncontextmenu != null) || /contextmenu|rightclick|right_click/.test(data);
          const hasDouble = (el.getAttribute && el.getAttribute("ondblclick") !== null) || (el.ondblclick != null) || /dblclick|doubleclick/.test(data);
          if (hasContext && hasDouble) return "right,double";
          if (hasContext) return "right";
          if (hasDouble) return "double";
        } catch(e) {}
        return "";
      };
 
      const idText = (doc, id) => {
        if (!id) return "";
        const n = doc.getElementById(id);
        return n ? textOf(n) : "";
      };
 
      const labelForMap = doc => {
        const m = new Map();
        doc.querySelectorAll("label[for]").forEach(l => {
          const f = l.getAttribute("for");
          const txt = textOf(l);
          if (!f || !txt) return;
          const arr = m.get(f) || [];
          if (!arr.includes(txt)) arr.push(txt);
          m.set(f, arr);
        });
        return m;
      };

      const wrapLabelText = input => {
        const lab = input.closest("label");
        return lab ? textOf(lab) : "";
      };

      const tokenList = txt => norm(txt).toLowerCase().replace(/[^a-z0-9]+/g, " ").split(/\s+/).filter(Boolean);

      const tokenOverlap = (a, b) => {
        const left = new Set(tokenList(a));
        const right = new Set(tokenList(b));
        if (!left.size || !right.size) return 0;
        let hits = 0;
        for (const token of left) if (right.has(token)) hits += 1;
        return hits;
      };

      const isInputLike = el => {
        const tag = (el.tagName || "").toLowerCase();
        if (["input", "textarea", "select"].includes(tag)) return true;
        const role = (el.getAttribute && el.getAttribute("role") || "").toLowerCase();
        return ["textbox", "combobox", "searchbox", "spinbutton"].includes(role);
      };

      const controlHints = el => {
        const values = [
          el.id || "",
          el.getAttribute && el.getAttribute("name") || "",
          el.getAttribute && el.getAttribute("formcontrolname") || "",
          el.getAttribute && el.getAttribute("autocomplete") || "",
          el.getAttribute && el.getAttribute("placeholder") || "",
          el.getAttribute && el.getAttribute("type") || "",
          el.getAttribute && el.getAttribute("title") || "",
        ];
        return norm(values.join(" "));
      };

      const getNearbyLabel = el => {
        try {
          const rect = el.getBoundingClientRect();
          const candidates = Array.from(document.querySelectorAll("label,legend,span,div,p,strong,h1,h2,h3,h4,h5,h6"));
          let best = "";
          let bestScore = Number.POSITIVE_INFINITY;
          for (const cand of candidates) {
            if (!cand || cand === el || cand.contains(el) || el.contains(cand)) continue;
            const text = textOf(cand);
            if (!text || text.length > 120) continue;
            const r = cand.getBoundingClientRect();
            if (!r || r.width < 1 || r.height < 1) continue;
            const above = r.bottom <= rect.top + 18;
            const leftish = r.right <= rect.left + 28;
            if (!(above || leftish)) continue;
            const dx = Math.abs(r.left - rect.left);
            const dy = Math.abs((r.top + r.height / 2) - (rect.top + rect.height / 2));
            const score = dx + dy;
            if (score < bestScore) {
              bestScore = score;
              best = text;
            }
          }
          return norm(best);
        } catch(e) {
          return "";
        }
      };

      const bestExplicitLabel = (el, _lmap, nearby) => {
        const id = el.id || "";
        const labels = id && _lmap.has(id) ? (_lmap.get(id) || []) : [];
        if (!labels.length) return "";
        if (labels.length === 1) return norm(labels[0]);
        const hints = controlHints(el);
        let best = "";
        let bestScore = Number.NEGATIVE_INFINITY;
        for (const label of labels) {
          let score = tokenOverlap(label, hints) * 10;
          if (nearby && norm(label) === nearby) score += 50;
          score -= Math.abs((label || "").length - (nearby || "").length) * 0.01;
          if (score > bestScore) {
            bestScore = score;
            best = label;
          }
        }
        return norm(best || labels[0]);
      };

      const syntheticIconLabel = el => {
        try {
          if (!el) return "";
          const rect = el.getBoundingClientRect();
          if (!rect || rect.width < 12 || rect.height < 12 || rect.width > 96 || rect.height > 96) return "";
          const vw = Math.max(window.innerWidth || 0, 1);
          const vh = Math.max(window.innerHeight || 0, 1);
          if (rect.x > vw * 0.35 || rect.y > Math.max(180, vh * 0.35)) return "";
          const attrs = [
            attr(el, "aria-label"),
            attr(el, "title"),
            attr(el, "alt"),
            attr(el, "id"),
            attr(el, "class"),
            attr(el, "data-testid"),
            attr(el, "data-test"),
          ].join(" ").toLowerCase();
          if (/(app|apps|launcher|grid|waffle|menu)/.test(attrs)) return "app launcher";
          const text = textOf(el).toLowerCase();
          if (text && /(app|apps|launcher|grid|menu)/.test(text)) return "app launcher";
          const role = (el.getAttribute && (el.getAttribute("role") || "") || "").toLowerCase();
          const clickable = ["button", "link", "menuitem"].includes(role) || ["button", "a"].includes((el.tagName || "").toLowerCase()) || hasAttr(el, "onclick");
          if (!clickable) return "";
          const nodes = el.querySelectorAll("svg, rect, circle, path, span, i");
          if (nodes.length >= 4 && nodes.length <= 18) return "app launcher";
        } catch(e) {}
        return "";
      };
 
      const accessibleName = (el, doc, _lmap) => {
        const aria = el.getAttribute && el.getAttribute("aria-label");
        if (aria) return norm(aria);
 
        const lb = el.getAttribute && el.getAttribute("aria-labelledby");
        if (lb) {
          const txt = lb.split(/\s+/).map(id => idText(doc, id)).join(" ").trim();
          if (txt) return norm(txt);
        }
 
        const nearby = isInputLike(el) ? getNearbyLabel(el) : "";
        const explicit = bestExplicitLabel(el, _lmap, nearby);
        if (explicit) return explicit;
 
        const wrap = wrapLabelText(el);
        if (wrap) return norm(wrap);

        const synthetic = syntheticIconLabel(el);
        if (synthetic) return synthetic;

        if (nearby) return nearby;
 
        const ph = el.getAttribute && el.getAttribute("placeholder");
        if (ph) return norm(ph);
 
        const title = el.getAttribute && el.getAttribute("title");
        if (title) return norm(title);
 
        return norm(el.innerText || el.value || el.textContent || "");
      };
 
      const push = r => {
        const key = JSON.stringify([
          r.tag || "", r.id || "", r.name || "", r.type || "",
          norm(r.label_text || r.aria_label || r.placeholder || r.text || "")
        ]).slice(0, 400);
        if (seen.has(key)) return;
        seen.add(key);
        out.push(r);
      };
 
      const pick = (el, doc, _lmap, framePrefix="") => {
        if (!isVisible(el) || !isInteractable(el)) return;
        const tag = (el.tagName || "").toLowerCase();
        const role = el.getAttribute && (el.getAttribute("role") || "");
        if (role && /^(none|presentation)$/i.test(role)) return;
        const rect = el.getBoundingClientRect() || { x: 0, y: 0, width: 0, height: 0 };
 
        const dragHandle = dragHandleFor(el);

        const nearby = isInputLike(el) ? getNearbyLabel(el) : "";

        push({
          tag,
          role,
          id: el.id || "",
          name: el.getAttribute && el.getAttribute("name") || "",
          type: el.getAttribute && el.getAttribute("type") || "",
          text: textOf(el),
          aria_label: el.getAttribute && el.getAttribute("aria-label") || "",
          placeholder: el.getAttribute && el.getAttribute("placeholder") || "",
          label_text: accessibleName(el, doc, _lmap),
          nearby_label: nearby,
          click_type: clickType(el),
          title: el.getAttribute && el.getAttribute("title") || "",
          data_testid: el.getAttribute && el.getAttribute("data-testid") || "",
          data_qa: attr(el, "data-qa") || "",
          data_cy: attr(el, "data-cy") || "",
          data_test: attr(el, "data-test") || "",
          data_id: el.getAttribute && el.getAttribute("data-id") || "",
          data_name: el.getAttribute && el.getAttribute("data-name") || "",
          data_field: el.getAttribute && el.getAttribute("data-field") || "",
          visible: true,
          bbox: { x: rect.x, y: rect.y, width: rect.width, height: rect.height },
          css_selector: selectorHint(el),
          is_draggable: isDraggable(el),
          is_droppable: isDroppable(el),
          drag_handle_selector: dragHandle.selector || "",
          drag_handle_text: dragHandle.text || "",
          frame: framePrefix
        });
      };
 
      const pickText = (el, doc, _lmap, framePrefix="") => {
        if (!isVisible(el) || el.closest('nav,header,footer,[aria-hidden="true"],[hidden]')) return;
        const tag = (el.tagName || "").toLowerCase();
        if (!/^(h1|h2|h3|h4|h5|h6|label|legend|span|strong|em|p|div)$/.test(tag)) return;
        const txt = textOf(el);
        if (!txt || txt.length < 2) return;
        const rect = el.getBoundingClientRect();
        if (!rect || rect.width < 1 || rect.height < 1) return;
 
        push({
          tag,
          role: el.getAttribute && (el.getAttribute("role") || ""),
          id: el.id || "",
          name: el.getAttribute && el.getAttribute("name") || "",
          type: "",
          text: txt,
          aria_label: el.getAttribute && el.getAttribute("aria-label") || "",
          placeholder: "",
          label_text: txt,
          title: el.getAttribute && el.getAttribute("title") || "",
          data_testid: el.getAttribute && el.getAttribute("data-testid") || "",
          data_qa: attr(el, "data-qa") || "",
          data_cy: attr(el, "data-cy") || "",
          data_test: attr(el, "data-test") || "",
          data_id: el.getAttribute && el.getAttribute("data-id") || "",
          data_name: el.getAttribute && el.getAttribute("data-name") || "",
          data_field: el.getAttribute && el.getAttribute("data-field") || "",
          visible: true,
          bbox: { x: rect.x, y: rect.y, width: rect.width, height: rect.height },
          frame: framePrefix
        });
      };
 
      const visit = (root, framePrefix="") => {
        if (!root) return;
        const doc = root;
        const _lmap = labelForMap(doc);
        const walker = doc.createTreeWalker(root, NodeFilter.SHOW_ELEMENT);
 
        while (walker.nextNode()) {
          const el = walker.currentNode;
          const tag = (el.tagName || "").toLowerCase();
          if (tag === "input" || tag === "button" || tag === "select" || tag === "textarea" || tag === "a" || el.hasAttribute("role"))
            pick(el, doc, _lmap, framePrefix);
          pickText(el, doc, _lmap, framePrefix);
 
          // shadow DOM traversal
          if (el.shadowRoot) {
            const w = doc.createTreeWalker(el.shadowRoot, NodeFilter.SHOW_ELEMENT);
            while (w.nextNode()) {
              const s = w.currentNode;
              const st = (s.tagName || "").toLowerCase();
              if (st === "input" || st === "button" || st === "select" || st === "textarea" || st === "a" || s.hasAttribute("role"))
                pick(s, el.shadowRoot, _lmap, framePrefix);
              pickText(s, el.shadowRoot, _lmap, framePrefix);
            }
          }
        }
 
        // âœ… NEW: recurse into same-origin iframes
        const iframes = doc.querySelectorAll("iframe");
        for (const f of iframes) {
          try {
            const id = f.id || f.name || "";
            const prefix = framePrefix + (id ? id : "iframe") + "/";
            if (f.contentDocument) visit(f.contentDocument, prefix);
          } catch (e) {
            // skip cross-origin frames
          }
        }
      };
 
      visit(document);
      return out;
    })();
    """

    try:
        elements = await fr.evaluate(js)
        print(f"[DEBUG] Extracted {len(elements)} DOM elements (including iframes).")
        # Optional: debug grouping by frame
        const_by_frame = {}
        for e in elements:
            f = e.get("frame", "")
            const_by_frame[f] = const_by_frame.get(f, 0) + 1
        print("[DEBUG] Elements grouped by frame:", const_by_frame)
        return elements
    except Exception as e:
        print("[ERROR] _rich_extract_dom_metadata failed:", e)
        return []

async def _extract_table_structured_data(
    fr: Union[Page, Frame], max_rows: int = 20, max_cells: int = 20
) -> List[Dict[str, Any]]:
    """
    Extract table headers and rows so table structure is captured during auto-enrichment.
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
      const hasAttr = (el, name) => {
        try { return el.getAttribute && el.getAttribute(name) !== null; }
        catch(e) { return false; }
      };
      const classListText = el => (el && el.className ? String(el.className) : "").toLowerCase();

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

      const dragHandleFor = el => {
        try {
          const handle = el.querySelector(
            "[data-rbd-drag-handle-draggable-id],[data-dnd-kit-drag-handle],[data-dnd-handle],.drag-handle,[aria-grabbed='true'],[draggable='true']"
          );
          if (handle) {
            return { selector: selectorHint(handle), text: textOf(handle) };
          }
        } catch(e) {}
        return { selector: "", text: "" };
      };

      const isDraggable = el => {
        try {
          if (el.draggable === true || attr(el, "draggable") === "true") return true;
          if (attr(el, "aria-grabbed") === "true") return true;
          if (hasAttr(el, "data-rbd-draggable-id") || hasAttr(el, "data-rbd-drag-handle-draggable-id")) return true;
          if (hasAttr(el, "data-dnd-kit-draggable-id") || hasAttr(el, "data-dnd-kit-drag-handle")) return true;
          const cls = classListText(el);
          if (cls.includes("draggable") || cls.includes("drag-handle") || cls.includes("drag-item")) return true;
          const style = window.getComputedStyle(el);
          if (style && (style.cursor === "grab" || style.cursor === "grabbing" || style.cursor === "move")) return true;
        } catch(e) {}
        return false;
      };

      const isDroppable = el => {
        try {
          if (hasAttr(el, "ondrop") || hasAttr(el, "ondragover") || hasAttr(el, "ondragenter")) return true;
          if (hasAttr(el, "data-rbd-droppable-id") || hasAttr(el, "data-dropzone") || hasAttr(el, "data-droppable") || hasAttr(el, "data-drop-target")) return true;
          if (hasAttr(el, "data-dnd-kit-droppable-id") || hasAttr(el, "data-dnd-kit-droppable")) return true;
          const cls = classListText(el);
          if (cls.includes("dropzone") || cls.includes("droppable") || cls.includes("drop-target")) return true;
          const role = (el.getAttribute("role") || "").toLowerCase();
          if (["listbox", "grid", "tree", "table"].includes(role)) return true;
        } catch(e) {}
        return false;
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
        return await fr.evaluate(js, max_rows, max_cells)
    except Exception as e:
        _safe_log(f"[WARN] _extract_table_structured_data failed: {e}")
        return []


# -----------------------------------------------------------------------------
# Enrichment
# -----------------------------------------------------------------------------
async def _refresh_target(PAGE: Page, reason: str = ""):
    try:
        if PAGE is None:
            return
        TARGET = await _select_extraction_target(PAGE)
        _safe_log(
            f"[stability] TARGET refreshed ({reason}) â†’ {getattr(TARGET,'url',None)}"
        )
    except Exception as e:
        _safe_log(f"[stability] TARGET refresh failed ({reason}): {e}")


async def _get_ocr_data_by_canonical(
    canonical_page_name: str,
    projectChromaPath: Path,
    src_directory: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    try:
        pid = get_request_project_id()
        recs = await _chroma_get_records(
            projectChromaPath, project_id=pid, page_name=canonical_page_name
        )
        metas = filter_metadata_by_project(recs.get("metadatas", []) or [])
        matched = [
            m
            for m in metas
            if (m or {}).get("type") == "ocr"
            and _canonical((m or {}).get("page_name", "")) == canonical_page_name
        ]
        if matched:
            return matched
    except Exception:
        matched = []

    # Fallback: pull latest OCR snapshot from metadata files when canonical name differs
    if src_directory is not None:
        for filename in ("after_enrichment.json", "before_enrichment.json"):
            try:
                path = _meta_dir(src_directory) / filename
                if not path.exists():
                    continue
                data = json.loads(path.read_text(encoding="utf-8") or "[]")
                ocr = [m for m in data if isinstance(m, dict) and m.get("type") == "ocr"]
                if ocr:
                    return ocr
            except Exception:
                continue
    return []


def _assess_dom_quality(recs: List[Dict[str, Any]]) -> bool:
    if not recs:
        return True
    n = len(recs)
    labeled = 0
    with_bbox = 0
    for r in recs:
        if (
            r.get("aria_label")
            or r.get("placeholder")
            or r.get("label")
            or r.get("text")
            or r.get("label_text")
        ):
            labeled += 1
        bb = r.get("bbox") or {}
        if (bb.get("width", 0) or 0) > 0 and (bb.get("height", 0) or 0) > 0:
            with_bbox += 1
    return n < 5 or (labeled / max(1, n) < 0.30) or (with_bbox / max(1, n) < 0.30)


async def _run_enrichment_for(
    PAGE: Page,
    TARGET: Page | Frame | None,
    AUTOSCROLL_ENABLED: bool,
    EXECUTION_MODE: bool,
    src_directory: Path,
    projectChromaPath: Path,
    page_name: str,
) -> Dict[str, Any]:
    if PAGE is None:
        raise HTTPException(
            status_code=500, detail="âŒ Cannot extract. No active page handle."
        )
    if hasattr(PAGE, "is_closed") and PAGE.is_closed():
        raise HTTPException(
            status_code=500, detail="âŒ Cannot extract. Page is already closed."
        )
    # Ensure chroma path is available via project activation

    CURRENT_PAGE_NAME = _canonical(page_name)

    # >>> NEW: ensure we're on the correct page BEFORE extraction
    await _ensure_on_page(PAGE, CURRENT_PAGE_NAME, projectChromaPath)

    await _refresh_target(PAGE, "enrich-start")
    paths = _ensure_dirs(src_directory)

    # ensure target
    if not await _is_js_accessible(TARGET):
        try:
            if await _is_js_accessible(PAGE.main_frame):
                TARGET = PAGE.main_frame
        except Exception:
            TARGET = PAGE

    await _pre_settle(TARGET, timeout_ms=8000)
    prev_scroll = AUTOSCROLL_ENABLED
    try:
        AUTOSCROLL_ENABLED = True
        await _progressive_autoscroll(
            AUTOSCROLL_ENABLED, EXECUTION_MODE, TARGET, steps=6, pause_ms=250
        )
    finally:
        AUTOSCROLL_ENABLED = prev_scroll

    # Attempt to open potential modals before extraction
    await _open_potential_modals(TARGET)

    # extract DOM
    # --- Diagnostic probe: record readyState, node count, and accessibility ---
    if _enrich_debug_enabled():
        try:
            probe = {"url": getattr(TARGET, "url", None)}
            try:
                probe["readyState"] = await TARGET.evaluate("() => document.readyState")
            except Exception as _e:
                probe["readyState"] = f"eval-error: {_e}"
            try:
                probe["body_node_count"] = await TARGET.evaluate(
                    "() => document.querySelectorAll('body *').length"
                )
            except Exception as _e:
                probe["body_node_count"] = f"eval-error: {_e}"
            try:
                probe["is_js_accessible"] = bool(await _is_js_accessible(TARGET))
            except Exception:
                probe["is_js_accessible"] = False
            debug_path = paths["debug"] / f"dom_eval_debug_{CURRENT_PAGE_NAME}.json"
            _write_project_file(
                debug_path,
                json.dumps(probe, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as e:
            try:
                error_path = (
                    paths["debug"] / f"dom_eval_debug_{CURRENT_PAGE_NAME}_error.txt"
                )
                _write_project_file(error_path, str(e), encoding="utf-8")
            except Exception:
                pass

    # Prefer fast, rich, single-eval extraction first
    dom_data = await _rich_extract_dom_metadata(TARGET) or []
    table_data = await _extract_table_structured_data(TARGET) or []
    if table_data:
        dom_data = list(dom_data) + list(table_data)
    try:
        _ = len(dom_data)
    except Exception:
        dom_data = list(dom_data)

    # If still low-quality or empty, supplement with Playwright locator-based extraction
    if _assess_dom_quality(dom_data):
        try:
            basic = await extract_dom_metadata(TARGET, CURRENT_PAGE_NAME) or []
            if basic:
                dom_data = _dedupe_records(list(dom_data) + list(basic))
        except Exception:
            pass

    dom_data = _dedupe_records(dom_data)

    # Normalize fields for matching (include nearby_label as fallback)
    for rec in dom_data:
        try:
            # prefer explicit label_text, then nearby_label, then aria/placeholder/text
            label = (
                rec.get("label_text")
                or rec.get("nearby_label")
                or rec.get("label")
                or rec.get("aria_label")
                or rec.get("text")
            )
            placeholder = rec.get("placeholder")
            role = rec.get("role")
            tag = rec.get("tag")
            rec["_norm"] = {
                "label": _norm_text(label),
                "nearby": _norm_text(rec.get("nearby_label")),
                "placeholder": _norm_text(placeholder),
                "role": (role or "").lower(),
                "tag": (tag or "").lower(),
            }
        except Exception:
            pass

    ocr_data = await _get_ocr_data_by_canonical(
        CURRENT_PAGE_NAME, projectChromaPath, src_directory=src_directory
    )

    # debug dumps
    if _enrich_debug_enabled():
        _write_project_file(
            paths["debug"] / f"dom_data_{CURRENT_PAGE_NAME}.txt",
            pprint.pformat(dom_data),
            encoding="utf-8",
        )
        _write_project_file(
            paths["debug"] / f"ocr_data_{CURRENT_PAGE_NAME}.txt",
            pprint.pformat(ocr_data),
            encoding="utf-8",
        )

    # matching
    updated_matches = match_and_update(
        ocr_data, dom_data, _get_chroma_collection(projectChromaPath)
    )
    pid = get_request_project_id() or 0
    await _invalidate_chroma_cache(pid, CURRENT_PAGE_NAME)
    if _enrich_debug_enabled():
        _write_project_file(
            paths["debug"] / f"after_match_and_update_{CURRENT_PAGE_NAME}.txt",
            pprint.pformat(updated_matches),
            encoding="utf-8",
        )

    standardized_matches = [
        build_standard_metadata(
            m, CURRENT_PAGE_NAME, image_path="", source_url=getattr(PAGE, "url", None)
        )
        for m in (updated_matches or [])
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
                page_name=CURRENT_PAGE_NAME,
                image_path="",
                source_url=getattr(PAGE, "url", None),
            )
        )
        existing_keys.add(key)
    set_last_match_result(standardized_matches)

    # fallback if nothing matched
    if not standardized_matches:
        if dom_data:
            standardized_matches = [
                _standardize_dom_only(r, CURRENT_PAGE_NAME, getattr(PAGE, "url", None))
                for r in dom_data
            ]
        else:
            standardized_matches = [
                _no_elements_record(CURRENT_PAGE_NAME, getattr(PAGE, "url", None))
            ]

    # write per-page JSON (merge with existing if present)
    out_path = _output_path_for_page(
        src_directory, CURRENT_PAGE_NAME, getattr(PAGE, "url", None)
    )
    pid = get_request_project_id() or 0
    combined_payload = await _atomic_merge_write_enrichment_page(
        project_id=pid,
        page_name=CURRENT_PAGE_NAME,
        src_directory=src_directory,
        output_path=out_path,
        new_records=standardized_matches,
    )

    # refresh global snapshot
    chroma_all = await _chroma_get_records(projectChromaPath, project_id=pid)
    chroma_all_metadatas = filter_metadata_by_project(
        chroma_all.get("metadatas", []) or []
    )
    meta_path = paths["meta"] / "after_enrichment.json"
    meta_lock = await _get_write_lock(pid, "after_enrichment")
    async with meta_lock:
        _atomic_write_project_file(
            meta_path,
            json.dumps(chroma_all_metadatas, indent=2),
            encoding="utf-8",
        )
        await _invalidate_chroma_cache(pid)

    _safe_log(f"[enrich] wrote: {out_path} ({len(standardized_matches)} records)")
    return {
        "status": "success",
        "message": f"Enriched {len(standardized_matches)} elements for page: {CURRENT_PAGE_NAME}",
        "matched_data": standardized_matches,
        "count": len(standardized_matches),
        "output_path": str(out_path),
    }


# -----------------------------------------------------------------------------
# Strategy engines (OCR, crawl, mixed)
# -----------------------------------------------------------------------------
async def _enrich_ocr_pages(
    PAGE: Page,
    TARGET: Page | Frame | None,
    AUTOSCROLL_ENABLED: bool,
    EXECUTION_MODE: bool,
    src_directory: Path,
    projectChromaPath: Path,
) -> Dict[str, Any]:
    pages = await _available_pages_for_dropdown(projectChromaPath)
    results = []
    for pn in pages:
        try:
            _safe_log(f"[auto] OCR page -> {pn}")
            res = await _run_enrichment_for(
                PAGE,
                TARGET,
                AUTOSCROLL_ENABLED,
                EXECUTION_MODE,
                src_directory,
                projectChromaPath,
                pn,
            )
            results.append(
                {
                    "page_name": pn,
                    "count": res.get("count", 0),
                    "file": res.get("output_path"),
                }
            )
        except Exception as e:
            _safe_log(f"[auto] OCR page '{pn}' failed: {e}")
            results.append({"page_name": pn, "error": str(e), "count": 0})
    # If no OCR pages exist, enrich the current page at least once
    if not pages:
        pn = await _derive_page_name(PAGE)
        _safe_log(f"[auto] No OCR pages; enriching current: {pn}")
        res = await _run_enrichment_for(
            PAGE,
            TARGET,
            AUTOSCROLL_ENABLED,
            EXECUTION_MODE,
            src_directory,
            projectChromaPath,
            pn,
        )
        results.append(
            {
                "page_name": pn,
                "count": res.get("count", 0),
                "file": res.get("output_path"),
            }
        )
    return {"strategy": "ocr", "results": results}


async def _crawl_and_enrich(
    PAGE: Page,
    TARGET: Page | Frame | None,
    AUTOSCROLL_ENABLED: bool,
    EXECUTION_MODE: bool,
    src_directory: Path,
    projectChromaPath: Path,
    start_url: Optional[str],
    max_pages: int,
    max_depth: int,
    delay_ms: int,
    same_origin_only: bool,
    time_budget_s: Optional[int] = None,
) -> Dict[str, Any]:
    if PAGE is None:
        raise HTTPException(status_code=500, detail="No active page")
    seed = start_url or getattr(PAGE, "url", None)
    if not seed:
        raise HTTPException(status_code=400, detail="No start URL available for crawl")

    visited: Set[str] = set()
    queue: List[Tuple[str, int]] = [(seed, 0)]
    results: List[Dict[str, Any]] = []
    count = 0

    start_ts = asyncio.get_event_loop().time()
    while queue and count < max_pages:
        if time_budget_s is not None and time_budget_s > 0:
            elapsed = asyncio.get_event_loop().time() - start_ts
            if elapsed >= time_budget_s:
                _safe_log(f"[crawl] time budget exceeded ({time_budget_s}s). stopping crawl.")
                break
        url, depth = queue.pop(0)
        if url in visited:
            continue
        visited.add(url)

        _safe_log(f"[crawl] visiting d={depth} url={url}")
        try:
            await _smart_navigate(PAGE, url, wait_until="auto", timeout_ms=60000)
            await __snapshot_if_blank(PAGE, "crawl-visit")

            try:
                TARGET = await _select_extraction_target(PAGE)
            except Exception:
                TARGET = PAGE

            page_name = await _derive_page_name(PAGE)
            res = await _run_enrichment_for(
                PAGE,
                TARGET,
                AUTOSCROLL_ENABLED,
                EXECUTION_MODE,
                src_directory,
                projectChromaPath,
                page_name,
            )
            results.append(
                {
                    "url": url,
                    "page_name": page_name,
                    "count": res.get("count", 0),
                    "file": res.get("output_path"),
                }
            )
            count += 1
        except Exception as e:
            _safe_log(f"[crawl] failed {url}: {e}")
            results.append({"url": url, "error": str(e), "count": 0})

        if depth < max_depth and count < max_pages:
            try:
                links = await _enumerate_links(PAGE, same_origin_only=same_origin_only)
                for link in links:
                    if link not in visited and len(queue) + count < max_pages * 3:
                        queue.append((link, depth + 1))
            except Exception:
                pass

        if delay_ms > 0:
            await asyncio.sleep(max(0, delay_ms) / 1000.0)

    return {"strategy": "crawl", "results": results}


async def _auto_enrich(
    PAGE: Page,
    TARGET: Page | Frame | None,
    AUTOSCROLL_ENABLED: bool,
    EXECUTION_MODE: bool,
    src_directory: Path,
    projectChromaPath: Path,
    strategy: str,
    crawl_max_pages: int,
    crawl_max_depth: int,
    crawl_delay_ms: int,
    crawl_same_origin_only: bool,
    job_timeout_s: Optional[int] = None,
) -> Dict[str, Any]:
    strat = (strategy or "mixed").lower().strip()
    if strat not in {"ocr", "crawl", "mixed"}:
        strat = "mixed"
    has_ocr_pages = bool(await _available_pages_for_dropdown(projectChromaPath))

    if strat == "ocr":
        return await _enrich_ocr_pages(
            PAGE,
            TARGET,
            AUTOSCROLL_ENABLED,
            EXECUTION_MODE,
            src_directory,
            projectChromaPath,
        )

    if strat == "crawl":
        return await _crawl_and_enrich(
            PAGE,
            TARGET,
            AUTOSCROLL_ENABLED,
            EXECUTION_MODE,
            src_directory=src_directory,
            projectChromaPath=projectChromaPath,
            start_url=getattr(PAGE, "url", None),
            max_pages=crawl_max_pages,
            max_depth=crawl_max_depth,
            delay_ms=crawl_delay_ms,
            same_origin_only=crawl_same_origin_only,
            time_budget_s=job_timeout_s,
        )

    # mixed
    if has_ocr_pages:
        return await _enrich_ocr_pages(
            PAGE,
            TARGET,
            AUTOSCROLL_ENABLED,
            EXECUTION_MODE,
            src_directory,
            projectChromaPath,
        )
    return await _crawl_and_enrich(
        PAGE,
        TARGET,
        AUTOSCROLL_ENABLED,
        EXECUTION_MODE,
        src_directory=src_directory,
        projectChromaPath=projectChromaPath,
        start_url=getattr(PAGE, "url", None),
        max_pages=crawl_max_pages,
        max_depth=crawl_max_depth,
        delay_ms=crawl_delay_ms,
        same_origin_only=crawl_same_origin_only,
        time_budget_s=job_timeout_s,
    )


# -----------------------------------------------------------------------------
# Routes
# -----------------------------------------------------------------------------
@router.post("/{project_id}/launch-browser")
async def launch_browser(
    project_id: int,
    req: LaunchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    async_enrich: bool = Query(True, description="Run auto-enrich asynchronously to avoid timeouts."),
    async_launch: bool = Query(False, description="Run launch + enrich in background to avoid gateway timeouts."),
):
    project = get_user_project(db, project_id, current_user)

    async def _launch_impl(
        db_session: Session,
        project_obj: Project,
        *,
        async_enrich_local: bool,
        apply_default_timeout: bool,
    ):
        PLAYWRIGHT = None
        BROWSER: Optional[Browser] = None
        PAGE: Optional[Page] = None
        TARGET: Optional[Union[Page, Frame]] = None
        CURRENT_PAGE_NAME: str = "unknown_page"
        EXECUTION_MODE: bool = False
        ENRICH_UI_ENABLED: bool = False
        AUTOSCROLL_ENABLED: bool = True

        async with _ENRICH_LAUNCH_LOCK:
            project_paths = _ensure_project_structure(project_obj)
            src_directory = Path(project_paths["src_dir"])
            projectChromaPath = project_paths["chroma_path"]
            project_context = build_project_context(current_user, project_obj.id, db_session)
            tokens = set_request_context(project_context=project_context)
            storage = DatabaseBackedProjectStorage(project_obj, src_directory, db_session)
            session = await _create_or_reset_session(project_obj.id, current_user.id, src_directory, projectChromaPath)
            async with session.lock:
                existing_page = session.page
                existing_browser = session.browser
                existing_playwright = session.playwright
            if existing_page or existing_browser or existing_playwright:
                await _clean_restart(existing_page, existing_browser, existing_playwright)
            _set_active_storage(storage)
            try:
                await _clean_restart(PAGE, BROWSER, PLAYWRIGHT)
                PLAYWRIGHT = await async_playwright().start()

                launch_args = []
                if req.disable_pinch_zoom:
                    launch_args += [
                        "--disable-pinch",
                        "--force-device-scale-factor=1",
                        "--high-dpi-support=1",
                        "--overscroll-history-navigation=0",
                    ]
                if req.disable_gpu:
                    launch_args += [
                        "--disable-gpu",
                        "--disable-accelerated-2d-canvas",
                        "--disable-features=IsolateOrigins,site-per-process",
                    ]

                def _truthy(v: str) -> bool:
                    return str(v or "").strip().lower() in ("1", "true", "yes", "y", "on")

                def _gui_available() -> bool:
                    # Headful Chromium frequently fails in server/container deployments.
                    # Treat Windows/macOS as GUI-capable; for Linux require DISPLAY/Wayland.
                    try:
                        if os.name == "nt":
                            return True
                        if sys.platform == "darwin":
                            return True
                    except Exception:
                        pass
                    return bool(os.getenv("DISPLAY") or os.getenv("WAYLAND_DISPLAY"))

                headless = req.headless
                if not _gui_available() and not headless:
                    # Force headless when no GUI is available to avoid X server failures.
                    _safe_log("[enrichment] GUI not available; forcing headless mode.")
                    headless = True
                storage_state_path = auth_storage_path(Path(project_paths["project_root"]))
                if not storage_state_path.exists():
                    # Do NOT force headful by default; it breaks non-GUI deployments and causes
                    # intermittent "Error enriching locators" depending on whether auth exists.
                    # If callers want interactive login, they can opt-in explicitly.
                    if _truthy(os.getenv("SMARTAI_REQUIRE_AUTH_STORAGE", "")) and headless:
                        raise HTTPException(
                            status_code=409,
                            detail=(
                                "Auth storage_state not found (auth/storage.json). "
                                "Run Manual Capture once to create it, or disable SMARTAI_REQUIRE_AUTH_STORAGE."
                            ),
                        )
                    if _truthy(os.getenv("SMARTAI_FORCE_HEADFUL_LOGIN", "")) and _gui_available():
                        headless = False
                    elif _truthy(os.getenv("SMARTAI_FORCE_HEADFUL_LOGIN", "")) and not _gui_available():
                        _safe_log("[enrichment] SMARTAI_FORCE_HEADFUL_LOGIN requested but GUI is not available; staying headless.")
                BROWSER = await PLAYWRIGHT.chromium.launch(
                    headless=headless, slow_mo=req.slow_mo, args=launch_args
                )

                context_kwargs: Dict[str, Any] = {
                    "ignore_https_errors": req.ignore_https_errors,
                    "viewport": {"width": req.viewport_width, "height": req.viewport_height},
                    "bypass_csp": True,
                    "has_touch": False,
                    "device_scale_factor": 1,
                    "reduced_motion": "reduce",
                    "color_scheme": "light",
                }
                if req.user_agent:
                    context_kwargs["user_agent"] = req.user_agent
                if req.extra_http_headers:
                    context_kwargs["extra_http_headers"] = req.extra_http_headers
                if req.http_username and req.http_password:
                    context_kwargs["http_credentials"] = {
                        "username": req.http_username,
                        "password": req.http_password,
                    }

                ENRICH_UI_ENABLED = bool(req.enable_enrichment_ui)
                AUTOSCROLL_ENABLED = bool(req.enable_autoscroll)
                async with session.lock:
                    session.enrich_ui_enabled = ENRICH_UI_ENABLED
                    session.autoscroll_enabled = AUTOSCROLL_ENABLED

                # Resolve optional storage file (cookies / localStorage) and apply to context kwargs if present
                storage_file = auth_storage_path(Path(project_paths["project_root"]))
                if not storage_file.exists():
                    storage_file = _resolve_storage_file()
                try:
                    if storage_file and storage_file.exists():
                        try:
                            raw_state = json.loads(storage_file.read_text(encoding="utf-8"))
                            context_kwargs["storage_state"] = normalize_storage_state(raw_state)
                        except Exception:
                            context_kwargs["storage_state"] = str(storage_file)
                        _safe_log(f"[enrichment] Using storage_state from {storage_file}")
                    else:
                        _safe_log(f"[enrichment] No storage_state file at {storage_file}")
                except Exception:
                    _safe_log(f"[enrichment] Failed to apply storage_state from {storage_file}")

                # Create browser context and page now that context_kwargs is finalized
                context = await BROWSER.new_context(**context_kwargs)
                PAGE = await context.new_page()
                __log_page_events(PAGE)
                async with session.lock:
                    session.playwright = PLAYWRIGHT
                    session.browser = BROWSER
                    session.page = PAGE

                PAGE.on(
                    "framenavigated",
                    lambda frame: asyncio.create_task(_refresh_target(PAGE, "framenavigated")),
                )
                PAGE.on(
                    "framedetached",
                    lambda frame: asyncio.create_task(_refresh_target(PAGE, "framedetached")),
                )
                PAGE.on(
                    "crash", lambda: asyncio.create_task(_refresh_target(PAGE, "page crash"))
                )

                async def _binding_enrich(source, page_name: str):
                    try:
                        with session_scope() as scoped_db:
                            scoped_project = (
                                scoped_db.query(Project)
                                .filter(Project.id == project_obj.id)
                                .first()
                            )
                            if not scoped_project:
                                raise HTTPException(status_code=404, detail="Project not found.")
                            storage = DatabaseBackedProjectStorage(scoped_project, src_directory, scoped_db)
                            _set_active_storage(storage)
                            with _temporary_project_context(project_context):
                                res = await _run_enrichment_for(
                                    PAGE,
                                    TARGET,
                                    AUTOSCROLL_ENABLED,
                                    EXECUTION_MODE,
                                    src_directory,
                                    projectChromaPath,
                                    page_name,
                                )
                        return json.dumps(res)
                    except HTTPException as he:
                        return json.dumps({"status": "fail", "error": he.detail})
                    except Exception as e:
                        return json.dumps({"status": "fail", "error": str(e)})
                    finally:
                        _set_active_storage(None)

                async def _binding_available_pages(source):
                    try:
                        with _temporary_project_context(project_context):
                            pages = await _available_pages_for_dropdown(projectChromaPath)
                        return json.dumps({"status": "success", "pages": pages})
                    except Exception as e:
                        return json.dumps({"status": "fail", "error": str(e), "pages": []})

                await PAGE.expose_binding("smartAI_enrich", _binding_enrich)
                await PAGE.expose_binding("smartAI_availablePages", _binding_available_pages)

                if req.apply_visual_patches:
                    await PAGE.add_init_script(STABILITY_VIEWPORT_CSS_JS)
                if req.enable_watchdog_reload:
                    await PAGE.add_init_script(WATCHDOG_RELOAD_JS)
                if ENRICH_UI_ENABLED:
                    await PAGE.add_init_script(UI_KEYBRIDGE_JS)
                    await PAGE.add_init_script(UI_MODAL_TOP_JS)

                try:
                    PAGE.set_default_timeout(req.nav_timeout_ms)
                    PAGE.set_default_navigation_timeout(req.nav_timeout_ms)
                except Exception:
                    pass

                await _smart_navigate(
                    PAGE,
                    req.url,
                    wait_until=req.wait_until if req.wait_until else "auto",
                    timeout_ms=req.nav_timeout_ms,
                )
                if should_start_auth_watch(auth_storage_path(Path(project_paths["project_root"])), getattr(PAGE, "url", "")):
                    async with session.lock:
                        if session.auth_watch_task and not session.auth_watch_task.done():
                            session.auth_watch_task.cancel()
                        session.auth_watch_task = asyncio.create_task(
                            wait_for_login_and_save(PAGE, Path(project_paths["project_root"]))
                        )
                await __snapshot_if_blank(PAGE, "after-nav")
                try:
                    TARGET = await _select_extraction_target(PAGE)
                except Exception:
                    TARGET = PAGE
                async with session.lock:
                    session.target = TARGET

                auto_result = None
                auto_job = None
                def _resolve_job_timeout() -> Optional[int]:
                    if req.job_timeout_s is not None:
                        return req.job_timeout_s
                    if not apply_default_timeout:
                        return None
                    try:
                        return int(os.getenv("ENRICH_JOB_TIMEOUT", "300"))
                    except Exception:
                        return 300
                pages_available = False
                try:
                    pages_available = bool(await _available_pages_for_dropdown(projectChromaPath))
                except Exception:
                    pages_available = False

                def _apply_fast_mode():
                    nonlocal AUTOSCROLL_ENABLED
                    if not req.fast_mode:
                        return
                    # Speed-focused defaults (opt-in only)
                    AUTOSCROLL_ENABLED = False
                    if req.enrich_strategy == "mixed":
                        # Prefer OCR when available; otherwise crawl minimal pages.
                        if pages_available:
                            req.enrich_strategy = "ocr"
                        else:
                            req.enrich_strategy = "crawl"
                    req.crawl_max_pages = min(req.crawl_max_pages, 3)
                    req.crawl_max_depth = min(req.crawl_max_depth, 1)
                    req.crawl_delay_ms = 0

                _apply_fast_mode()
                if req.auto_enrich:
                    _safe_log(
                        f"[auto] Starting auto-enrichment strategy='{req.enrich_strategy}'"
                    )
                    if async_enrich_local:
                        async def _auto_runner():
                            with session_scope() as scoped_db:
                                scoped_project = (
                                    scoped_db.query(Project)
                                    .filter(Project.id == project_obj.id)
                                    .first()
                                )
                                if not scoped_project:
                                    raise HTTPException(status_code=404, detail="Project not found.")
                                storage = DatabaseBackedProjectStorage(
                                    scoped_project, src_directory, scoped_db
                                )
                                _set_active_storage(storage)
                                try:
                                    with _temporary_project_context(project_context):
                                        job_timeout = _resolve_job_timeout()
                                        if job_timeout is not None and job_timeout > 0:
                                            try:
                                                res = await asyncio.wait_for(
                                                    _auto_enrich(
                                                        PAGE,
                                                        TARGET,
                                                        AUTOSCROLL_ENABLED,
                                                        EXECUTION_MODE,
                                                        src_directory=src_directory,
                                                        projectChromaPath=projectChromaPath,
                                                        strategy=req.enrich_strategy,
                                                        crawl_max_pages=req.crawl_max_pages,
                                                        crawl_max_depth=req.crawl_max_depth,
                                                        crawl_delay_ms=req.crawl_delay_ms,
                                                        crawl_same_origin_only=req.crawl_same_origin_only,
                                                        job_timeout_s=job_timeout,
                                                    ),
                                                    timeout=job_timeout,
                                                )
                                            except asyncio.TimeoutError as exc:
                                                raise RuntimeError(
                                                    f"Enrichment exceeded {job_timeout}s and was cancelled."
                                                ) from exc
                                        else:
                                            res = await _auto_enrich(
                                                PAGE,
                                                TARGET,
                                                AUTOSCROLL_ENABLED,
                                                EXECUTION_MODE,
                                                src_directory=src_directory,
                                                projectChromaPath=projectChromaPath,
                                                strategy=req.enrich_strategy,
                                                crawl_max_pages=req.crawl_max_pages,
                                                crawl_max_depth=req.crawl_max_depth,
                                                crawl_delay_ms=req.crawl_delay_ms,
                                                crawl_same_origin_only=req.crawl_same_origin_only,
                                                job_timeout_s=job_timeout,
                                            )
                                finally:
                                    _set_active_storage(None)
                            if req.close_after_enrich:
                                try:
                                    await _clean_restart(PAGE, BROWSER, PLAYWRIGHT)
                                    async with session.lock:
                                        session.playwright = None
                                        session.browser = None
                                        session.page = None
                                        session.target = None
                                    await _remove_session(project_obj.id, current_user.id)
                                except Exception:
                                    pass
                            return res

                        job = await _JOB_MANAGER.create(_auto_runner)
                        job["project_id"] = project_obj.id
                        job["org_id"] = current_user.organization_id
                        auto_job = {
                            "job_id": job["id"],
                            "job_endpoint": f"/enrichment/jobs/{job['id']}",
                            "result_endpoint": f"/enrichment/jobs/{job['id']}/result",
                        }
                    else:
                        job_timeout = _resolve_job_timeout()
                        if job_timeout is not None and job_timeout > 0:
                            try:
                                auto_result = await asyncio.wait_for(
                                    _auto_enrich(
                                        PAGE,
                                        TARGET,
                                        AUTOSCROLL_ENABLED,
                                        EXECUTION_MODE,
                                        src_directory=src_directory,
                                        projectChromaPath=projectChromaPath,
                                        strategy=req.enrich_strategy,
                                        crawl_max_pages=req.crawl_max_pages,
                                        crawl_max_depth=req.crawl_max_depth,
                                        crawl_delay_ms=req.crawl_delay_ms,
                                        crawl_same_origin_only=req.crawl_same_origin_only,
                                        job_timeout_s=job_timeout,
                                    ),
                                    timeout=job_timeout,
                                )
                            except asyncio.TimeoutError as exc:
                                raise RuntimeError(
                                    f"Enrichment exceeded {job_timeout}s and was cancelled."
                                ) from exc
                        else:
                            auto_result = await _auto_enrich(
                                PAGE,
                                TARGET,
                                AUTOSCROLL_ENABLED,
                                EXECUTION_MODE,
                                src_directory=src_directory,
                                projectChromaPath=projectChromaPath,
                                strategy=req.enrich_strategy,
                                crawl_max_pages=req.crawl_max_pages,
                                crawl_max_depth=req.crawl_max_depth,
                                crawl_delay_ms=req.crawl_delay_ms,
                                crawl_same_origin_only=req.crawl_same_origin_only,
                                job_timeout_s=job_timeout,
                            )
                        _safe_log(
                            f"[auto] Completed auto-enrichment with {len(auto_result.get('results', []))} item(s)"
                        )

                msg = f"? Browser launched and navigated to {req.url}."
                if ENRICH_UI_ENABLED:
                    msg += " Modal available (Alt+Q)."
                if req.auto_enrich and auto_result:
                    msg += (
                        f" Auto-enrichment finished using '{auto_result.get('strategy')}'."
                    )

                # AUTO-CLOSE when requested
                if req.auto_enrich and req.close_after_enrich and not async_enrich_local:
                    try:
                        await _clean_restart(PAGE, BROWSER, PLAYWRIGHT)
                        async with session.lock:
                            session.playwright = None
                            session.browser = None
                            session.page = None
                            session.target = None
                        await _remove_session(project_obj.id, current_user.id)
                        msg += " Browser closed after auto-enrichment."
                    except Exception:
                        pass

                safe_auto_result = _json_safe(auto_result)
                return {
                    "status": "success",
                    "message": msg,
                    "auto_enrich_result": safe_auto_result,
                    "auto_enrich_job": auto_job,
                }

            except Exception as e:
                import traceback; traceback.print_exc()
                await _clean_restart(PAGE, BROWSER, PLAYWRIGHT)
                async with session.lock:
                    session.playwright = None
                    session.browser = None
                    session.page = None
                    session.target = None
                raise HTTPException(status_code=500, detail=str(e))
            finally:
                _set_active_storage(None)
                reset_request_context(tokens)

    if async_launch:
        async def _launch_runner():
            with session_scope() as scoped_db:
                scoped_project = (
                    scoped_db.query(Project)
                    .filter(Project.id == project.id)
                    .first()
                )
                if not scoped_project:
                    raise HTTPException(status_code=404, detail="Project not found.")
                return await _launch_impl(
                    scoped_db,
                    scoped_project,
                    async_enrich_local=False,
                    apply_default_timeout=False,
                )

        job = await _JOB_MANAGER.create(_launch_runner)
        job["project_id"] = project.id
        job["org_id"] = current_user.organization_id
        return {
            "status": "accepted",
            "auto_enrich_job": {
                "job_id": job["id"],
                "job_endpoint": f"/enrichment/jobs/{job['id']}",
                "result_endpoint": f"/enrichment/jobs/{job['id']}/result",
            },
        }

    return await _launch_impl(
        db,
        project,
        async_enrich_local=async_enrich,
        apply_default_timeout=True,
    )


@router.get("/enrichment/jobs/{job_id}")
async def get_enrichment_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = await _JOB_MANAGER.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    project_id = job.get("project_id")
    if project_id is not None:
        get_user_project(db, int(project_id), current_user)
    return {
        "id": job.get("id"),
        "status": job.get("status"),
        "created_at": job.get("created_at"),
        "started_at": job.get("started_at"),
        "finished_at": job.get("finished_at"),
        "error": job.get("error"),
    }


@router.get("/enrichment/jobs/{job_id}/result")
async def get_enrichment_job_result(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = await _JOB_MANAGER.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    project_id = job.get("project_id")
    if project_id is not None:
        get_user_project(db, int(project_id), current_user)
    return {
        "id": job.get("id"),
        "status": job.get("status"),
        "result": _json_safe(job.get("result")),
        "error": job.get("error"),
        "finished_at": job.get("finished_at"),
    }


@router.post("/{project_id}/auth/session/save")
async def save_project_auth_session(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = get_user_project(db, project_id, current_user)
    project_paths = _ensure_project_structure(project)
    session = await _get_session(project.id, current_user.id)
    async with session.lock:
        page = session.page
    if page is None or (hasattr(page, "is_closed") and page.is_closed()):
        raise HTTPException(status_code=409, detail="No active page to capture storage state.")
    path = auth_storage_path(Path(project_paths["project_root"]))
    try:
        await page.context.storage_state(path=str(path))
        try:
            current_url = page.url or ""
        except Exception:
            current_url = ""
        if current_url:
            try:
                auth_landing_path(Path(project_paths["project_root"])).write_text(
                    current_url,
                    encoding="utf-8",
                )
            except Exception:
                pass
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to save storage state: {exc}") from exc
    return {"status": "success", "path": str(path)}


@router.post("/{project_id}/auth/storage")
async def save_project_auth_storage(
    project_id: int,
    payload: AuthStorageRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = get_user_project(db, project_id, current_user)
    project_paths = _ensure_project_structure(project)
    storage_state = _build_storage_state(payload)
    storage_path = auth_storage_path(Path(project_paths["project_root"]))
    try:
        storage_path.write_text(json.dumps(storage_state, indent=2), encoding="utf-8")
        if payload.landing_url:
            auth_landing_path(Path(project_paths["project_root"])).write_text(
                payload.landing_url, encoding="utf-8"
            )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to save auth storage: {exc}") from exc
    return {"status": "success", "path": str(storage_path)}


@router.post("/auto-enrich")
async def auto_enrich_endpoint(
    req: AutoEnrichRequest,
    project_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    async_enrich: bool = Query(True, description="Run auto-enrich asynchronously to avoid timeouts."),
):
    project = _resolve_project_for_user(db, current_user, project_id)
    project_paths = _ensure_project_structure(project)
    project_context = build_project_context(current_user, project.id, db)
    session = await _get_session(project.id, current_user.id)
    async with session.lock:
        src_directory = session.src_directory or Path(project_paths["src_dir"])
        project_chroma = session.chroma_path or Path(project_paths["chroma_path"])
        page = session.page
        target = session.target
        autoscroll_enabled = session.autoscroll_enabled
        execution_mode = session.execution_mode
    storage = DatabaseBackedProjectStorage(project, src_directory, db)
    _set_active_storage(storage)
    try:
        async def _auto_runner():
            with session_scope() as scoped_db:
                scoped_project = (
                    scoped_db.query(Project)
                    .filter(Project.id == project.id)
                    .first()
                )
                if not scoped_project:
                    raise HTTPException(status_code=404, detail="Project not found.")
                storage = DatabaseBackedProjectStorage(
                    scoped_project, src_directory, scoped_db
                )
                _set_active_storage(storage)
                try:
                    with _temporary_project_context(project_context):
                        if req.fast_mode:
                            if req.enrich_strategy == "mixed":
                                if await _available_pages_for_dropdown(project_chroma):
                                    req.enrich_strategy = "ocr"
                                else:
                                    req.enrich_strategy = "crawl"
                            req.crawl_max_pages = min(req.crawl_max_pages, 3)
                            req.crawl_max_depth = min(req.crawl_max_depth, 1)
                            req.crawl_delay_ms = 0
                        job_timeout = req.job_timeout_s
                        if job_timeout is None:
                            job_timeout = int(os.getenv("ENRICH_JOB_TIMEOUT", "300"))
                        if job_timeout <= 0:
                            res = await _auto_enrich(
                                page,
                                target,
                                autoscroll_enabled,
                                execution_mode,
                                src_directory=src_directory,
                                projectChromaPath=project_chroma,
                                strategy=req.enrich_strategy,
                                crawl_max_pages=req.crawl_max_pages,
                                crawl_max_depth=req.crawl_max_depth,
                                crawl_delay_ms=req.crawl_delay_ms,
                                crawl_same_origin_only=req.crawl_same_origin_only,
                                job_timeout_s=job_timeout,
                            )
                        else:
                            try:
                                res = await asyncio.wait_for(
                                    _auto_enrich(
                                        page,
                                        target,
                                        autoscroll_enabled,
                                        execution_mode,
                                        src_directory=src_directory,
                                        projectChromaPath=project_chroma,
                                        strategy=req.enrich_strategy,
                                        crawl_max_pages=req.crawl_max_pages,
                                        crawl_max_depth=req.crawl_max_depth,
                                        crawl_delay_ms=req.crawl_delay_ms,
                                        crawl_same_origin_only=req.crawl_same_origin_only,
                                        job_timeout_s=job_timeout,
                                    ),
                                    timeout=job_timeout,
                                )
                            except asyncio.TimeoutError as exc:
                                raise RuntimeError(
                                    f"Enrichment exceeded {job_timeout}s and was cancelled."
                                ) from exc
                finally:
                    _set_active_storage(None)
            if req.close_after_enrich:
                try:
                    async with session.lock:
                        play = session.playwright
                        brow = session.browser
                        pg = session.page
                    await _clean_restart(pg, brow, play)
                    async with session.lock:
                        session.playwright = None
                        session.browser = None
                        session.page = None
                        session.target = None
                    await _remove_session(project.id, current_user.id)
                except Exception:
                    pass
            return res

        # Always run asynchronously to avoid request timeouts.
        job = await _JOB_MANAGER.create(_auto_runner)
        job["project_id"] = project.id
        job["org_id"] = current_user.organization_id
        return {
            "status": "accepted",
            "auto_enrich_job": {
                "job_id": job["id"],
                "job_endpoint": f"/enrichment/jobs/{job['id']}",
                "result_endpoint": f"/enrichment/jobs/{job['id']}/result",
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        _set_active_storage(None)


@router.post("/crawl-and-enrich")
async def crawl_and_enrich_endpoint(
    req: CrawlRequest,
    project_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    async_enrich: bool = Query(True, description="Run crawl asynchronously to avoid timeouts."),
):
    project = _resolve_project_for_user(db, current_user, project_id)
    project_paths = _ensure_project_structure(project)
    project_context = build_project_context(current_user, project.id, db)
    session = await _get_session(project.id, current_user.id)
    async with session.lock:
        src_directory = session.src_directory or Path(project_paths["src_dir"])
        project_chroma = session.chroma_path or Path(project_paths["chroma_path"])
        page = session.page
        target = session.target
        autoscroll_enabled = session.autoscroll_enabled
        execution_mode = session.execution_mode
    storage = DatabaseBackedProjectStorage(project, src_directory, db)
    _set_active_storage(storage)
    try:
        async def _crawl_runner():
            with session_scope() as scoped_db:
                scoped_project = (
                    scoped_db.query(Project)
                    .filter(Project.id == project.id)
                    .first()
                )
                if not scoped_project:
                    raise HTTPException(status_code=404, detail="Project not found.")
                storage = DatabaseBackedProjectStorage(
                    scoped_project, src_directory, scoped_db
                )
                _set_active_storage(storage)
                try:
                    with _temporary_project_context(project_context):
                        job_timeout = req.job_timeout_s
                        if job_timeout is None:
                            job_timeout = int(os.getenv("ENRICH_JOB_TIMEOUT", "300"))
                        if job_timeout <= 0:
                            res = await _crawl_and_enrich(
                                page,
                                target,
                                autoscroll_enabled,
                                execution_mode,
                                src_directory=src_directory,
                                projectChromaPath=project_chroma,
                                start_url=req.start_url or getattr(page, "url", None),
                                max_pages=req.max_pages,
                                max_depth=req.max_depth,
                                delay_ms=req.delay_ms,
                                same_origin_only=req.same_origin_only,
                            )
                        else:
                            try:
                                res = await asyncio.wait_for(
                                    _crawl_and_enrich(
                                        page,
                                        target,
                                        autoscroll_enabled,
                                        execution_mode,
                                        src_directory=src_directory,
                                        projectChromaPath=project_chroma,
                                        start_url=req.start_url or getattr(page, "url", None),
                                        max_pages=req.max_pages,
                                        max_depth=req.max_depth,
                                        delay_ms=req.delay_ms,
                                        same_origin_only=req.same_origin_only,
                                    ),
                                    timeout=job_timeout,
                                )
                            except asyncio.TimeoutError as exc:
                                raise RuntimeError(
                                    f"Crawl enrichment exceeded {job_timeout}s and was cancelled."
                                ) from exc
                finally:
                    _set_active_storage(None)
            if req.close_after_enrich:
                try:
                    async with session.lock:
                        play = session.playwright
                        brow = session.browser
                        pg = session.page
                    await _clean_restart(pg, brow, play)
                    async with session.lock:
                        session.playwright = None
                        session.browser = None
                        session.page = None
                        session.target = None
                    await _remove_session(project.id, current_user.id)
                except Exception:
                    pass
            return res

        # Always run asynchronously to avoid request timeouts.
        job = await _JOB_MANAGER.create(_crawl_runner)
        job["project_id"] = project.id
        job["org_id"] = current_user.organization_id
        return {
            "status": "accepted",
            "auto_enrich_job": {
                "job_id": job["id"],
                "job_endpoint": f"/enrichment/jobs/{job['id']}",
                "result_endpoint": f"/enrichment/jobs/{job['id']}/result",
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        _set_active_storage(None)


@router.post("/set-current-page-name")
async def set_page_name(
    req: PageNameSetRequest,
    project_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = _resolve_project_for_user(db, current_user, project_id)
    session = await _get_session(project.id, current_user.id)
    async with session.lock:
        session.current_page_name = _canonical(req.page_name)
        page_name = session.current_page_name
    _safe_log(f"[INFO] âœ… Page name set to: {page_name}")
    return {"status": "success", "page_name": page_name}


@router.post("/execution-mode")
async def toggle_execution_mode(
    req: ExecutionModeRequest,
    project_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = _resolve_project_for_user(db, current_user, project_id)
    session = await _get_session(project.id, current_user.id)
    async with session.lock:
        session.execution_mode = bool(req.enabled)
        session.autoscroll_enabled = False if session.execution_mode else session.autoscroll_enabled
        page = session.page
        execution_mode = session.execution_mode
    if execution_mode and page:
        try:
            await page.evaluate(
                "window._smartaiDisabled = true; if (window.smartAI_disableUI) window.smartAI_disableUI();"
            )
        except Exception:
            pass
        async with session.lock:
            session.enrich_ui_enabled = False
    if page:
        try:
            target = await _select_extraction_target(page)
            async with session.lock:
                session.target = target
        except Exception:
            async with session.lock:
                session.target = page
    return {"status": "success", "execution_mode": execution_mode}


@router.post("/ui/disable")
async def disable_ui(
    project_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = _resolve_project_for_user(db, current_user, project_id)
    session = await _get_session(project.id, current_user.id)
    async with session.lock:
        session.enrich_ui_enabled = False
        page = session.page
        ui_enabled = session.enrich_ui_enabled
    if page:
        try:
            await page.evaluate(
                "window._smartaiDisabled = true; if (window.smartAI_disableUI) window.smartAI_disableUI();"
            )
        except Exception:
            pass
    return {"status": "success", "ui_enabled": ui_enabled}


@router.post("/capture-dom-from-client")
async def capture_from_keyboard(
    _: CaptureRequest,
    project_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Manual trigger kept; does NOT auto-close.
    project = _resolve_project_for_user(db, current_user, project_id)
    session = await _get_session(project.id, current_user.id)
    try:
        async with session.lock:
            page = session.page
            target = session.target
            current_page_name = session.current_page_name
            autoscroll_enabled = session.autoscroll_enabled
            execution_mode = session.execution_mode
            src_directory = session.src_directory
            chroma_path = session.chroma_path
        if page is None:
            raise HTTPException(
                status_code=500, detail="âŒ Cannot extract. No active page handle."
            )
        if hasattr(page, "is_closed") and page.is_closed():
            raise HTTPException(
                status_code=500, detail="âŒ Cannot extract. Page is already closed."
            )
        if not current_page_name:
            current_page_name = await _derive_page_name(page)
            async with session.lock:
                session.current_page_name = current_page_name

        page_name = current_page_name
        _safe_log(f"[INFO] Enrichment triggered for: {page_name}")

        await _refresh_target(page, "capture-start")
        await __snapshot_if_blank(page, "before-capture")

        prev_scroll = autoscroll_enabled
        try:
            async with session.lock:
                session.autoscroll_enabled = True
            await _progressive_autoscroll(target, steps=6, pause_ms=250)
        finally:
            async with session.lock:
                session.autoscroll_enabled = prev_scroll

        project = _resolve_project_for_user(db, current_user, project.id)
        project_paths = _ensure_project_structure(project)
        project_context = build_project_context(current_user, project.id, db)
        storage = DatabaseBackedProjectStorage(project, src_directory, db)
        _set_active_storage(storage)
        with _temporary_project_context(project_context):
            result = await _run_enrichment_for(
                page,
                target,
                autoscroll_enabled,
                execution_mode,
                src_directory,
                chroma_path,
                page_name,
            )
        await __snapshot_if_blank(page, "after-capture")
        return {
            "status": "success",
            "message": f"[Keyboard Trigger] {result['message']}",
            **result,
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(
            status_code=500, detail=f"âŒ Capture failed: {e.__class__.__name__}: {e}"
        )
    finally:
        _set_active_storage(None)


@router.get("/available-pages")
async def list_page_names(
    project_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = _resolve_project_for_user(db, current_user, project_id)
    project_paths = _ensure_project_structure(project)
    project_context = build_project_context(current_user, project.id, db)
    try:
        with _temporary_project_context(project_context):
            return {
                "status": "success",
                "pages": await _available_pages_for_dropdown(project_paths["chroma_path"]),
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/current-url")
async def current_url(
    project_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = _resolve_project_for_user(db, current_user, project_id)
    session = await _get_session(project.id, current_user.id)
    try:
        async with session.lock:
            page = session.page
            target = session.target
        target_url = None
        if target is not None:
            try:
                target_url = target.url
            except Exception:
                target_url = None
        return {
            "page_url": getattr(page, "url", None),
            "target_url": target_url,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.on_event("shutdown")
async def shutdown_browser():
    await _clean_restart()


@router.get("/latest-match-result")
async def get_latest_match_result(
    project_id: int = Query(..., description="Project ID to scope the match results to"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        project = _resolve_project_for_user(db, current_user, project_id)
        project_paths = _ensure_project_structure(project)
        records = await _chroma_get_records(
            Path(project_paths["chroma_path"]),
            project_id=project.id,
        )
        matched = [
            r for r in records.get("metadatas", []) if r.get("dom_matched") is True
        ]
        return {"status": "success", "matched_elements": matched, "count": len(matched)}
    except HTTPException:
        raise
    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reset-enrichment/{page_name}")
async def reset_enrichment_api(
    page_name: str,
    project_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = _resolve_project_for_user(db, current_user, project_id)
    project_paths = _ensure_project_structure(project)
    project_context = build_project_context(current_user, project.id, db)
    with _temporary_project_context(project_context):
        reset_enriched(page_name)
    return {"success": True, "message": f"Enrichment reset for {page_name}"}


__all__ = ["router"]

