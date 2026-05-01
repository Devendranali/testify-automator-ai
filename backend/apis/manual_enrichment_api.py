from __future__ import annotations

import os
import json
import re
import pprint
import asyncio
import hashlib
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Tuple
from urllib.parse import urlparse
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from chromadb import PersistentClient
from config.settings import get_chroma_path
from playwright.async_api import (
    async_playwright,
    Page,
    Browser,
    BrowserContext,
    Frame,
    TimeoutError as PWTimeoutError,
)

from utils.enrichment_status import reset_enriched
from logic.manual_capture_mode import extract_dom_metadata
from utils.match_utils import normalize_page_name
from utils.project_context import filter_metadata_by_project
from utils.request_context import get_project_id as get_request_project_id
from utils.request_context import (
    set_request_context,
    reset_request_context,
    get_project_context,
)
from utils.project_paths import ProjectContext, build_project_context
from utils.file_utils import build_standard_metadata, generate_unique_name
from utils.ui_actions_async import dismiss_cookie_banner
from database.project_storage import DatabaseBackedProjectStorage
from database.session import get_db, session_scope
from database.models import Project, User, OrganizationMember
from apis.projects_api import (
    _ensure_project_structure,
    get_current_user,
    get_user_project,
)
from utils.session_manager import (
    auth_storage_path,
    auth_landing_path,
    should_start_auth_watch,
    wait_for_login_and_save,
    normalize_storage_state,
)
from sqlalchemy.orm import Session


# -----------------------------------------------------------------------------
# Router & DB
# -----------------------------------------------------------------------------
router = APIRouter()
_ACTIVE_STORAGE: Optional[DatabaseBackedProjectStorage] = None


# -----------------------------------------------------------------------------
# Runtime state
# -----------------------------------------------------------------------------
PLAYWRIGHT = None
BROWSER: Optional[Browser] = None
PAGE: Optional[Page] = None
TARGET: Optional[Union[Page, Frame]] = None
CURRENT_PAGE_NAME: str = "unknown_page"
MANUAL_BROWSER_CLOSED: bool = False

EXECUTION_MODE: bool = False
ENRICH_UI_ENABLED: bool = False
AUTOSCROLL_ENABLED: bool = True

DEEP_CAPTURE_ENABLED: bool = (
    os.getenv("SMARTAI_DEEP_CAPTURE", "").strip().lower() in {"1", "true", "yes"}
)
CAPTURE_ALL_DOM: bool = (
    os.getenv("SMARTAI_CAPTURE_ALL_DOM", "").strip().lower() in {"1", "true", "yes"}
)
INCLUDE_HIDDEN_ENABLED: bool = (
    CAPTURE_ALL_DOM
    or os.getenv("SMARTAI_INCLUDE_HIDDEN", "").strip().lower() in {"1", "true", "yes"}
)
STEALTH_ENABLED: bool = (
    os.getenv("SMARTAI_STEALTH", "").strip().lower() in {"1", "true", "yes"}
)
ENRICH_UI_DELAY_SEC: float = float(os.getenv("SMARTAI_ENRICH_UI_DELAY_SEC", "2.5"))
DISABLE_ENRICH_UI: bool = (
    os.getenv("SMARTAI_DISABLE_ENRICH_UI", "").strip().lower() in {"1", "true", "yes"}
)
_ENRICH_UI_BLOCKLIST = [
    d.strip().lower()
    for d in os.getenv("SMARTAI_ENRICH_UI_BLOCKLIST", "").split(",")
    if d.strip()
]

DEEP_TABS_ENABLED: bool = (
    os.getenv("SMARTAI_DEEP_TABS", "").strip().lower() in {"1", "true", "yes"}
)
DEEP_CONTAINER_SCROLL_ENABLED: bool = (
    os.getenv("SMARTAI_DEEP_CONTAINER_SCROLL", "").strip().lower()
    in {"1", "true", "yes"}
)
MODAL_CAPTURE_PAUSE_SEC: float = float(os.getenv("SMARTAI_MODAL_CAPTURE_SEC", "0.5"))
_AUTH_WATCH_TASK: Optional[asyncio.Task] = None


# -----------------------------------------------------------------------------
# Small browser helpers
# -----------------------------------------------------------------------------
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


def _get_chroma_collection():
    client = PersistentClient(path=get_chroma_path())
    return client.get_or_create_collection(
        name=os.environ.get("SMARTAI_CHROMA_COLLECTION", "element_metadata")
    )


def _enrich_ui_allowed(url: Optional[str]) -> bool:
    if DISABLE_ENRICH_UI:
        return False
    if not url:
        return True
    host = ""
    try:
        host = url.split("//", 1)[-1].split("/", 1)[0].lower()
    except Exception:
        host = url.lower()
    for blocked in _ENRICH_UI_BLOCKLIST:
        if blocked in host:
            return False
    return True


_DEFAULT_STEALTH_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0.0.0 Safari/537.36"
)


async def _apply_stealth_to_context(context: BrowserContext) -> None:
    if not STEALTH_ENABLED:
        return
    try:
        await context.add_init_script(
            """
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
            window.chrome = window.chrome || { runtime: {} };
            """
        )
    except Exception:
        pass


# -----------------------------------------------------------------------------
# Config
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


def _meta_dir(src_directory: Path) -> Path:
    path = src_directory / "metadata"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _debug_dir(src_directory: Path) -> Path:
    path = src_directory / "ocr-dom-metadata"
    path.mkdir(parents=True, exist_ok=True)
    return path


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
    apply_visual_patches: bool = False
    disable_gpu: bool = False
    disable_pinch_zoom: bool = True
    enable_enrichment_ui: bool = True


class CaptureRequest(BaseModel):
    pass


class PageNameSetRequest(BaseModel):
    page_name: str


class ExecutionModeRequest(BaseModel):
    enabled: bool


class EnrichFromUrlRequest(BaseModel):
    url: str = Field(..., description="Target URL to enrich")
    page_name: Optional[str] = None
    headless: bool = False
    slow_mo: int = 80
    wait_until: str = "auto"
    nav_timeout_ms: int = 60000
    ignore_https_errors: bool = True
    enable_enrichment_ui: bool = True
    close_after_enrich: bool = True


# -----------------------------------------------------------------------------
# UI injection
# -----------------------------------------------------------------------------
UI_KEYBRIDGE_JS = r"""
(() => {
  if (window === window.top) return;
  if (window._smartaiKeyBridgeInstalled) return;
  window._smartaiKeyBridgeInstalled = true;
  function isEditable(el){ if(!el) return false; const t=(el.tagName||'').toLowerCase(); return t==='input'||t==='textarea'||t==='select'||el.isContentEditable; }
  function onKey(e){
    if(window._smartaiDisabled) return;
    if(!(e.altKey && (e.key==='q'||e.key==='Q'))) return;
    if(e.ctrlKey||e.metaKey) return;
    if(isEditable(document.activeElement)) return;
    try{e.preventDefault();e.stopPropagation();}catch(_){}
    try{window.top.postMessage({__smartai:'TOGGLE_MODAL'},'*');}catch(_){}
  }
  window.addEventListener('keydown', onKey, true);
})();
"""

UI_MODAL_TOP_JS = r"""
(() => {
  if (window !== window.top) return;
  if (window._smartaiTopInstalled) return;
  window._smartaiTopInstalled = true;

  function killLegacyInputs() {
    try {
      ['ocrModal','ocrModalWrapper','pageDropdown','smartai_page_input']
        .forEach(id => document.getElementById(id)?.remove());

      const modal = document.getElementById('smartaiModal');
      if (modal) {
        modal.querySelectorAll('input, select').forEach(el => el.remove());
      }

      document.querySelectorAll('input').forEach(el => {
        const ph = (el.placeholder || '').toLowerCase();
        const val = (el.value || '').toLowerCase();
        if (
          ph.includes('page') ||
          ph.includes('url') ||
          ph.includes('customer') ||
          val.includes('page') ||
          val.includes('url')
        ) {
          el.remove();
        }
      });
    } catch (_) {}
  }

  function ensureModal() {
    killLegacyInputs();

    let modal = document.getElementById('smartaiModal');
    if (modal) return;

    modal = document.createElement('div');
    modal.id = 'smartaiModal';
    modal.style.cssText = `
      position: fixed;
      top: 40%;
      left: 50%;
      transform: translate(-50%, -50%);
      background: #ffffff;
      padding: 16px;
      border: 2px solid #000;
      z-index: 2147483647;
      display: none;
      min-width: 220px;
      border-radius: 10px;
      font-family: Arial, sans-serif;
    `;

    modal.innerHTML = `
      <div style="text-align:center;font-weight:bold;margin-bottom:10px;">
        Manual Enrich
      </div>

      <div style="display:flex;gap:10px;justify-content:center;flex-wrap:wrap;">
        <button id="smartai_enrich_btn">Enrich</button>
        <button id="smartai_close_browser_btn">Close Browser</button>
        <button id="smartai_close_btn">Close</button>
      </div>

      <div id="smartai_msg"
           style="margin-top:10px;font-weight:bold;text-align:center;">
      </div>

      <div style="margin-top:8px;color:#666;font-size:12px;text-align:center;">
        Tip: press <b>Alt+Q</b> to open / close
      </div>
    `;

    document.body.appendChild(modal);

    const msg = modal.querySelector('#smartai_msg');

    document.getElementById('smartai_enrich_btn').onclick = async () => {
      killLegacyInputs();
      msg.style.color = 'blue';
      msg.textContent = 'Capturing metadata...';

      try {
        const res = JSON.parse(await window.smartAI_enrich() || '{}');
        if (res.status === 'success') {
          msg.style.color = 'green';
          msg.textContent = `Captured ${res.count || 0} elements`;
        } else {
          msg.style.color = 'red';
          msg.textContent = res.error || 'Enrichment failed';
        }
      } catch {
        msg.style.color = 'red';
        msg.textContent = 'Error during enrichment';
      }
    };

    document.getElementById('smartai_close_btn').onclick = () => {
      modal.style.display = 'none';
      killLegacyInputs();
    };

    document.getElementById('smartai_close_browser_btn').onclick = async () => {
      killLegacyInputs();
      msg.style.color = 'blue';
      msg.textContent = 'Closing browser...';
      try {
        const res = JSON.parse(await window.smartAI_close_browser() || '{}');
        if (res.status === 'success') {
          msg.style.color = 'green';
          msg.textContent = 'Browser closed';
        } else {
          msg.style.color = 'red';
          msg.textContent = res.error || 'Failed to close browser';
        }
      } catch {
        msg.style.color = 'red';
        msg.textContent = 'Error closing browser';
      }
    };

    window.smartaiToggleModal = () => {
      killLegacyInputs();
      modal.style.display = modal.style.display === 'none' ? 'block' : 'none';
    };
  }

  function toggleModal() {
    ensureModal();
    window.smartaiToggleModal();
  }

  window.addEventListener('keydown', e => {
    if (!(e.altKey && (e.key === 'q' || e.key === 'Q'))) return;
    if (e.ctrlKey || e.metaKey) return;
    e.preventDefault();
    toggleModal();
  }, true);

  window.addEventListener('message', e => {
    if (e?.data?.__smartai === 'TOGGLE_MODAL') toggleModal();
  }, true);

})();
"""


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


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def _safe_log(*a):
    try:
        print(*a)
    except Exception:
        pass


def _clean_text(value: Optional[str]) -> str:
    return " ".join((value or "").split()).strip()


def _label_priority(rec: Dict[str, Any]) -> str:
    return (
        rec.get("label_text")
        or rec.get("aria_label")
        or rec.get("placeholder")
        or rec.get("nearby_label")
        or rec.get("text")
        or rec.get("title")
        or ""
    )


def _infer_payment_provider(source: str) -> str:
    s = (source or "").lower()
    if "stripe" in s:
        return "stripe"
    if "razorpay" in s:
        return "razorpay"
    if "paypal" in s:
        return "paypal"
    if "adyen" in s:
        return "adyen"
    if "braintree" in s:
        return "braintree"
    if "checkout" in s:
        return "checkout"
    return ""


async def _remove_legacy_modal(page: Page):
    try:
        await page.add_init_script(
            """
            (() => {
              const killIds = ['ocrModal','ocrModalWrapper','pageDropdown','smartai_page_input'];
              const nuke = () => {
                killIds.forEach(id => { const el = document.getElementById(id); if (el) el.remove(); });
                document.querySelectorAll('*').forEach(el => {
                  const txt = (el.innerText || '').toLowerCase();
                  if (txt.includes('page/url') && el.tagName === 'DIV' && el.id === 'smartaiModal') {
                    el.remove();
                  }
                });
              };
              nuke();
              document.addEventListener('DOMContentLoaded', nuke);
            })();
            """
        )
    except Exception:
        pass
    try:
        await page.evaluate(
            """
            (() => {
              const killIds = ['ocrModal','ocrModalWrapper','pageDropdown','smartai_page_input'];
              killIds.forEach(id => { const el = document.getElementById(id); if (el) el.remove(); });
            })();
            """
        )
    except Exception:
        pass


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


def _file_key(name: str) -> str:
    base = _canonical(name or "page")
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", base).strip("_")
    return safe or "page"


def _ensure_dirs(src_directory: Optional[Path] = None) -> Dict[str, Path]:
    if src_directory is None:
        src_directory = _src_dir()
    return {"debug": _debug_dir(src_directory), "meta": _meta_dir(src_directory)}


def _set_active_storage(storage: Optional[DatabaseBackedProjectStorage]) -> None:
    global _ACTIVE_STORAGE
    _ACTIVE_STORAGE = storage


@contextmanager
def _temporary_project_context(project_context: ProjectContext):
    tokens = set_request_context(project_context=project_context)
    try:
        yield
    finally:
        reset_request_context(tokens)


@contextmanager
def _activate_project_storage(db: Session, org_id: Optional[int] = None):
    project = _get_active_project(db, org_id=org_id)
    storage = DatabaseBackedProjectStorage(project, _src_dir(), db)
    _set_active_storage(storage)
    try:
        yield project, storage
    finally:
        _set_active_storage(None)


@contextmanager
def _activate_project_storage_from_scope(org_id: Optional[int] = None):
    with session_scope() as scoped_db:
        with _activate_project_storage(scoped_db, org_id=org_id) as ctx:
            yield ctx


def _persist_project_file(path: Path, content: str, encoding: str = "utf-8") -> None:
    if path.suffix.lower() == ".txt":
        return
    storage = _ACTIVE_STORAGE
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


def _project_query(db: Session, org_ids: Optional[set[int]]):
    query = db.query(Project)
    if org_ids:
        query = query.filter(Project.organization_id.in_(org_ids))
    return query


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


def _get_active_project(db: Session, org_id: Optional[int] = None) -> Project:
    request_project_id = get_request_project_id()
    if request_project_id is None:
        raise HTTPException(status_code=400, detail="project_id is required")
    org_ids = {org_id} if org_id is not None else set()
    project = (
        _project_query(db, org_ids)
        .filter(Project.id == int(request_project_id))
        .first()
    )
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    return project


def _same_origin(a: Optional[str], b: Optional[str]) -> bool:
    pa, pb = urlparse(a or ""), urlparse(b or "")
    return (pa.netloc or "").lower() != "" and (pa.netloc or "").lower() == (
        pb.netloc or ""
    ).lower()


def _resolve_storage_file(env_val: Optional[str] = None) -> Path:
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


def _load_storage_state_for_context(storage_file: Optional[Path]) -> Optional[Any]:
    if not storage_file or not storage_file.exists():
        return None
    try:
        raw_state = json.loads(storage_file.read_text(encoding="utf-8"))
        return normalize_storage_state(raw_state)
    except Exception:
        return str(storage_file)


def _ocr_name_counts() -> Dict[str, int]:
    counts: Dict[str, int] = {}
    try:
        recs = _get_chroma_collection().get() or {}
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


def _available_pages_for_dropdown() -> List[str]:
    counts = _ocr_name_counts()
    noise = {"unknown", "unknown_page", "basepage"}
    for k in list(counts.keys()):
        if k in noise:
            counts.pop(k, None)
    names = list(counts.keys())
    names.sort(key=lambda n: (-counts[n], n))
    return names


def _looks_like_url(val: str) -> bool:
    if not val:
        return False
    val = val.strip()
    return val.startswith(("http://", "https://", "/"))


def _short_hash(s: str) -> str:
    try:
        return hashlib.md5((s or "").encode("utf-8")).hexdigest()[:8]
    except Exception:
        return "00000000"


def _clean_label_text(label: str) -> str:
    if not label:
        return label
    return re.sub(r"[^A-Za-z0-9\s]", "", label).strip()


def _slug_from_url(source_url: Optional[str]) -> Optional[str]:
    if not source_url:
        return None
    try:
        parsed = urlparse(source_url)
        fragment = (parsed.fragment or "").split("?")[0].lstrip("!/")
        if fragment:
            return _canonical(fragment.replace("/", "_"))
        path = (parsed.path or "").strip("/")
        if not path:
            return None
        for segment in reversed(path.split("/")):
            if segment:
                return _canonical(segment)
        return None
    except Exception:
        return None


def _url_hash(source_url: Optional[str]) -> Optional[str]:
    if not source_url:
        return None
    try:
        parsed = urlparse(source_url)
        key = (parsed.netloc or "") + (parsed.path or "")
    except Exception:
        key = source_url
    try:
        return hashlib.md5(key.encode("utf-8")).hexdigest()[:8]
    except Exception:
        return None


def _strip_dom_flags(rec: Dict[str, Any]) -> Dict[str, Any]:
    cleaned = dict(rec or {})
    cleaned.pop("dom_matched", None)

    bbox = cleaned.get("bbox")
    if isinstance(bbox, str):
        parts = [p.strip() for p in bbox.split(",")]
        try:
            if len(parts) == 4:
                cleaned["bbox"] = {
                    "x": float(parts[0]) if parts[0] else 0,
                    "y": float(parts[1]) if parts[1] else 0,
                    "width": float(parts[2]) if parts[2] else 0,
                    "height": float(parts[3]) if parts[3] else 0,
                }
        except Exception:
            pass
    elif isinstance(bbox, dict):
        cleaned["bbox"] = {
            "x": bbox.get("x", 0),
            "y": bbox.get("y", 0),
            "width": bbox.get("width", 0),
            "height": bbox.get("height", 0),
        }
    else:
        x = cleaned.get("x", 0)
        y = cleaned.get("y", 0)
        w = cleaned.get("width", 0)
        h = cleaned.get("height", 0)
        if any([x, y, w, h]):
            cleaned["bbox"] = {"x": x, "y": y, "width": w, "height": h}

    return cleaned


def _coerce_json_value(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    s = value.strip()
    if not s:
        return value
    if s[0] in "{[" and s[-1] in "]}":
        try:
            return json.loads(s)
        except Exception:
            try:
                return json.loads(s.replace("'", '"'))
            except Exception:
                return value
    return value


def _normalize_metadata_json(rec: Dict[str, Any]) -> Dict[str, Any]:
    cleaned = dict(rec or {})
    for key in ("bbox", "position_relation", "used_in_tests"):
        if key in cleaned:
            cleaned[key] = _coerce_json_value(cleaned.get(key))
    return cleaned


def _is_container_stub(rec: Dict[str, Any]) -> bool:
    tag = (rec.get("tag_name") or rec.get("tag") or "").lower()
    dom_id = (rec.get("dom-id") or rec.get("dom_id") or rec.get("id") or "").lower()
    bbox = rec.get("bbox")
    if isinstance(bbox, str):
        try:
            parsed = json.loads(bbox.replace("'", '"'))
            bbox = parsed if isinstance(parsed, dict) else {}
        except Exception:
            bbox = {}
    if not isinstance(bbox, dict):
        bbox = {}
    w = float(bbox.get("width", 0) or 0)
    h = float(bbox.get("height", 0) or 0)

    looks_fullpage = w >= 1200 and h >= 800
    too_large = w >= 1600 and h >= 1600

    if tag == "body":
        return True
    if tag == "div" and (dom_id in {"root", "app"} or looks_fullpage or too_large):
        return True
    return False


def _is_form_wrapper(rec: Dict[str, Any]) -> bool:
    tag = (rec.get("tag_name") or rec.get("tag") or "").lower()
    label = ((rec.get("label_text") or rec.get("text") or "") or "").strip()
    if not label:
        return False

    star_count = label.count("*")
    word_count = len(label.split())

    is_wrapper_tag = tag in {"div", "span", "p", "section", "article", "form"}
    has_input_semantics = (rec.get("type") or "").strip() or tag in {
        "input",
        "textarea",
        "select",
        "button",
    }

    if not is_wrapper_tag or has_input_semantics:
        return False

    if star_count >= 2:
        return True
    if star_count >= 1 and word_count >= 8:
        return True
    if word_count >= 20:
        return True

    return False


def _split_label_segments(label: str) -> List[str]:
    if not label:
        return []
    parts = re.split(r"[\n\r]+|\s{2,}", label)
    cleaned: List[str] = []
    for part in parts:
        segment = part.strip(" *:\t")
        if segment:
            cleaned.append(segment)
    return cleaned


def _norm_text(s: Optional[str]) -> str:
    if not s:
        return ""
    return " ".join(
        (s or "").replace("\n", " ").replace("\r", " ").strip().strip(":").split()
    ).lower()


def _has_other_record_with_norm(
    recs: List[Dict[str, Any]], norm: str, current_index: int
) -> bool:
    for idx, candidate in enumerate(recs):
        if idx == current_index:
            continue
        cand_label = _norm_text(candidate.get("label_text") or candidate.get("text") or "")
        if cand_label == norm:
            return True
    return False


def _is_combined_label(
    rec: Dict[str, Any], recs: List[Dict[str, Any]], current_index: int
) -> bool:
    label = (rec.get("label_text") or rec.get("text") or "") or ""
    segments = [seg for seg in _split_label_segments(label) if _norm_text(seg)]
    if len(segments) < 2:
        return False
    normalized_segments = [_norm_text(seg) for seg in segments if _norm_text(seg)]
    if len(normalized_segments) < 2:
        return False
    for norm in normalized_segments:
        if not _has_other_record_with_norm(recs, norm, current_index):
            return False
    return True


def _filter_secondary_labels(recs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    primaries: set[str] = set()
    for r in recs:
        lbl = _norm_text(r.get("label_text") or r.get("text") or "")
        tag = (r.get("tag_name") or r.get("tag") or "").lower()
        ocr_type = (r.get("ocr_type") or "").lower()
        primary_hint = tag in {"input", "select", "textarea", "option"} or ocr_type in {
            "textbox",
            "text",
            "input",
            "textarea",
            "email",
            "password",
            "select",
            "dropdown",
            "combobox",
            "checkbox",
            "radio",
            "toggle",
            "switch",
            "date",
            "datepicker",
            "time",
            "timepicker",
            "file",
            "upload",
        }
        if primary_hint and lbl:
            primaries.add(lbl)

    filtered: List[Dict[str, Any]] = []
    for idx, r in enumerate(recs):
        lbl = _norm_text(r.get("label_text") or r.get("text") or "")
        tag = (r.get("tag_name") or r.get("tag") or "").lower()
        ocr_type = (r.get("ocr_type") or "").lower()
        is_primary = tag in {"input", "select", "textarea", "option"} or ocr_type in {
            "textbox",
            "text",
            "input",
            "textarea",
            "email",
            "password",
            "select",
            "dropdown",
            "combobox",
            "checkbox",
            "radio",
            "toggle",
            "switch",
            "date",
            "datepicker",
            "time",
            "timepicker",
            "file",
            "upload",
        }
        is_wrapper_tag = tag in {"div", "span", "p", "section", "article"}
        if not is_primary and is_wrapper_tag and _is_combined_label(r, recs, idx):
            continue
        if lbl in primaries and not is_primary:
            continue
        filtered.append(r)
    return filtered


def _output_path_for_page(page_name: str, source_url: Optional[str]) -> Path:
    meta_dir = _ensure_dirs()["meta"]
    page_key = _file_key(page_name or "page")
    url_slug = _file_key(_slug_from_url(source_url) or "")
    if url_slug and url_slug != page_key:
        filename_key = f"{page_key}__{url_slug}"
    else:
        filename_key = page_key
    return meta_dir / f"{_file_key(filename_key)}.json"


def _ocr_only_path_for_page(page_name: str, source_url: Optional[str] = None) -> Path:
    meta_dir = _ensure_dirs()["meta"]
    page_key = _file_key(page_name or "page")
    url_slug = _file_key(_slug_from_url(source_url) or "")
    if url_slug and url_slug != page_key:
        filename_key = f"{page_key}__{url_slug}"
    else:
        filename_key = page_key
    return meta_dir / f"after_enrichment_{_file_key(filename_key)}.json"


def _write_filtered_aggregate(
    meta_dir: Path, current_payload: List[Dict[str, Any]]
) -> None:
    def _with_ocr_type(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return [r for r in (items or []) if (r.get("ocr_type") or "").strip()]

    aggregate: List[Dict[str, Any]] = []
    aggregate.extend(_with_ocr_type(current_payload))

    try:
        for f in sorted(meta_dir.glob("after_enrichment_*.json")):
            if f.name == "after_enrichment.json":
                continue
            try:
                data = json.loads(f.read_text(encoding="utf-8") or "[]")
                if isinstance(data, list):
                    aggregate.extend(_with_ocr_type(data))
            except Exception:
                continue
    except Exception:
        pass

    aggregate = _merge_enrichment_records([], aggregate)
    aggregate = [
        _strip_dom_flags(r)
        for r in aggregate
        if (r.get("ocr_type") or "").strip()
    ]
    _write_project_file(
        meta_dir / "after_enrichment.json",
        json.dumps(aggregate, indent=2),
        encoding="utf-8",
    )


def _merge_enrichment_records(
    existing: List[Dict[str, Any]], incoming: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    merged: List[Dict[str, Any]] = []
    index_map: Dict[tuple, int] = {}

    def _key(item: Dict[str, Any]) -> tuple:
        if not item:
            return ("", "")

        intent = (item.get("intent") or "").strip().lower()
        unique_name = (item.get("unique_name") or "").strip().lower()
        ocr_id = (item.get("ocr_id") or "").strip().lower()
        dom_id = (item.get("id") or "").strip().lower()

        if unique_name:
            return ("un|" + unique_name, intent)
        if ocr_id:
            return ("ocr|" + ocr_id, intent)
        if dom_id:
            return ("id|" + dom_id, intent)

        label_norm = _norm_text(item.get("label_text") or item.get("text") or "")
        tag = (item.get("tag_name") or item.get("tag") or "").lower()
        bbox = item.get("bbox") or {}

        if isinstance(bbox, str):
            try:
                parsed = json.loads(bbox.replace("'", '"'))
                if isinstance(parsed, dict):
                    bbox = parsed
            except Exception:
                bbox = {}

        try:
            cx = float(bbox.get("x", 0) or 0) + float(bbox.get("width", 0) or 0) / 2.0
            cy = float(bbox.get("y", 0) or 0) + float(bbox.get("height", 0) or 0) / 2.0
        except Exception:
            cx, cy = 0.0, 0.0

        pos_key = f"{round(cx):04d}:{round(cy):04d}"
        return (f"{tag}|{label_norm}|{pos_key}", intent)

    for entry in existing or []:
        k = _key(entry)
        index_map[k] = len(merged)
        merged.append(entry)

    for entry in incoming or []:
        k = _key(entry)
        if k in index_map:
            merged[index_map[k]] = entry
        else:
            index_map[k] = len(merged)
            merged.append(entry)

    return merged


def _trim_label_noise(label: str) -> str:
    if not label:
        return label
    lbl = " ".join(str(label).split())
    price_pat = re.compile(r"\s(?:rs\.?|₹|\$|€)\s*\d", re.IGNORECASE)
    m = price_pat.search(lbl)
    if m:
        lbl = lbl[: m.start()].strip()
    if len(lbl) > 100:
        lbl = lbl[:100].rsplit(" ", 1)[0].strip()
    return lbl or label


def _is_option_list_label(label: str, tag: str, role: str) -> bool:
    if not label:
        return False
    tag = (tag or "").lower()
    role = (role or "").lower()
    tokens = [t for t in label.split() if t]
    if len(tokens) < 3:
        return False
    if tag not in {"select"} and role not in {"combobox", "listbox"}:
        return False
    title_like = all(t[0].isupper() for t in tokens if t and t[0].isalpha())
    alpha_only = all(t.isalpha() for t in tokens)
    return bool(title_like and alpha_only)


def _standardize_dom_only(
    rec: Dict[str, Any], page_name: str, source_url: Optional[str]
) -> Dict[str, Any]:
    bbox = rec.get("bbox") or {}
    label = _label_priority(rec)
    label = _trim_label_noise(label)
    ocr_type = (
        (rec.get("ocr_type") or rec.get("tag") or rec.get("role") or "").strip().lower()
    )
    intent = (rec.get("intent") or "").strip()

    tag = (rec.get("tag") or rec.get("tag_name") or "").lower()
    role = (rec.get("role") or "").lower()
    get_by_role = (rec.get("get_by_role") or "").lower()
    data_sidebar = (
        rec.get("data_sidebar")
        or rec.get("data-sidebar")
        or rec.get("data-sidebar-menu")
        or ""
    )
    clickable = rec.get("clickable") or rec.get("editable") or False
    frame_url = rec.get("frame_url") or ""
    provider_hint = _infer_payment_provider(
        " ".join(
            [
                frame_url,
                rec.get("src") or "",
                rec.get("title") or "",
                rec.get("name") or "",
                rec.get("css_selector") or "",
            ]
        )
    )

    if not CAPTURE_ALL_DOM and _is_option_list_label(label, tag, role):
        return {}

    select_like_roles = {"combobox", "listbox", "tree", "option"}
    aria_multiselectable = str(
        rec.get("aria_multiselectable") or rec.get("aria-multiselectable") or ""
    ).lower()
    is_select_like = (
        role in select_like_roles
        or get_by_role in select_like_roles
        or tag == "select"
        or aria_multiselectable == "true"
    )

    if is_select_like:
        ocr_type = "select"
    elif tag == "iframe":
        ocr_type = "iframe"
    elif tag == "li" and clickable:
        ocr_type = "button"
    elif tag in {"button", "a"} or role in {"menuitem", "link"} or data_sidebar:
        ocr_type = "button"
    elif tag in {"input", "textarea"}:
        ocr_type = "textbox"
    elif clickable and (not ocr_type or ocr_type == "button"):
        ocr_type = "button"

    unique_name = generate_unique_name(page_name, label or tag or "element", ocr_type, intent)
    out = {
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
        "tag_name": rec.get("tag") or rec.get("tag_name"),
        "role": rec.get("role"),
        "id": rec.get("id"),
        "name": rec.get("name"),
        "type": rec.get("type"),
        "src": rec.get("src"),
        "nearby_label": rec.get("nearby_label"),
        "is_draggable": rec.get("is_draggable", False),
        "is_droppable": rec.get("is_droppable", False),
        "click_type": rec.get("click_type", ""),
        "drag_handle_selector": rec.get("drag_handle_selector", ""),
        "drag_handle_text": rec.get("drag_handle_text", ""),
        "unique_name": unique_name,
        "intent": intent,
        "ocr_type": ocr_type or "unknown",
        "bbox": {
            "x": bbox.get("x", 0),
            "y": bbox.get("y", 0),
            "width": bbox.get("width", 0),
            "height": bbox.get("height", 0),
        },
        "ocr_present": False,
        "ts": _ts(),
    }

    if rec.get("frame_path"):
        out["frame_path"] = rec.get("frame_path")
    if rec.get("frame_depth") is not None:
        out["frame_depth"] = rec.get("frame_depth")
    if rec.get("frame_selector"):
        out["frame_selector"] = rec.get("frame_selector")
    if rec.get("frame_name"):
        out["frame_name"] = rec.get("frame_name")
    if rec.get("frame_url"):
        out["frame_url"] = rec.get("frame_url")
    if provider_hint:
        out["provider_hint"] = provider_hint

    return out


def _no_elements_record(page_name: str, source_url: Optional[str]) -> Dict[str, Any]:
    return {
        "page_name": page_name,
        "source_url": source_url or "",
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


async def _progressive_autoscroll(
    fr: Union[Page, Frame], steps: int = 6, pause_ms: int = 250
):
    try:
        await fr.evaluate(
            f"""
        (async () => {{
          const sleep = t=>new Promise(r=>setTimeout(r,t));
          const doc=document; const se=doc.scrollingElement||doc.documentElement||doc.body;
          const vh = Math.max(1, (window.innerHeight || doc.documentElement.clientHeight || 800));
          let prevH = 0;
          let stableCount = 0;
          for (let pass=0; pass<3; pass++) {{
            const H = se ? (se.scrollHeight||0) : (doc.documentElement.scrollHeight||doc.body.scrollHeight||0);
            if (H <= prevH) stableCount++;
            else stableCount = 0;
            prevH = H;
            const totalSteps = Math.max({max(1, steps)}, Math.min(50, Math.ceil(H / Math.max(1, Math.floor(vh * 0.8)))));
            const step = Math.max(1, Math.floor(H/totalSteps));
            let y=0;
            for(let i=0;i<totalSteps;i++){{ y+=step; window.scrollTo(0,y); await sleep({max(0, pause_ms)}); }}
            await sleep({max(0, pause_ms)});
            if (stableCount >= 1) break;
          }}
          window.scrollTo(0,0);
        }})()"""
        )
    except Exception:
        pass


async def _deep_capture_expand(fr: Union[Page, Frame], max_rounds: int = 4) -> None:
    if not DEEP_CAPTURE_ENABLED:
        return
    selectors = [
        "button:has-text('Load more')",
        "button:has-text('Show more')",
        "button:has-text('More')",
        "button:has-text('View more')",
        "button:has-text('Expand')",
        "a:has-text('Load more')",
        "a:has-text('Show more')",
        "[aria-label*='load more' i]",
        "[aria-label*='show more' i]",
        "[data-testid*='load' i]",
    ]
    for _ in range(max_rounds):
        clicked_any = False
        for sel in selectors:
            try:
                loc = fr.locator(sel)
                count = min(await loc.count(), 3)
                for i in range(count):
                    try:
                        target = loc.nth(i)
                        if not await target.is_visible():
                            continue
                        await _safe_click(target, timeout=800)
                        clicked_any = True
                        await asyncio.sleep(0.3)
                    except Exception:
                        continue
            except Exception:
                continue
        if not clicked_any:
            break


async def _deep_expand_tabs_and_accordions(
    fr: Union[Page, Frame], max_rounds: int = 2
) -> None:
    if not DEEP_TABS_ENABLED:
        return
    selectors = [
        "[role='tab']",
        "[data-bs-toggle='tab']",
        "[data-toggle='tab']",
        "[role='button'][aria-expanded='false']",
        "[aria-controls][aria-expanded='false']",
        ".accordion-button",
    ]
    for _ in range(max_rounds):
        clicked_any = False
        for sel in selectors:
            try:
                loc = fr.locator(sel)
                count = min(await loc.count(), 5)
                for i in range(count):
                    try:
                        target = loc.nth(i)
                        if not await target.is_visible():
                            continue
                        await _safe_click(target, timeout=800)
                        clicked_any = True
                        await asyncio.sleep(0.2)
                    except Exception:
                        continue
            except Exception:
                continue
        if not clicked_any:
            break


async def _deep_scroll_containers(fr: Union[Page, Frame], max_rounds: int = 2) -> None:
    if not DEEP_CONTAINER_SCROLL_ENABLED:
        return
    try:
        await fr.evaluate(
            """
            (rounds) => {
              const sleep = t => new Promise(r => setTimeout(r, t));
              const isScrollable = el => {
                if (!el) return false;
                const cs = window.getComputedStyle(el);
                const oy = cs.overflowY;
                return (oy === 'auto' || oy === 'scroll') && el.scrollHeight > el.clientHeight + 50;
              };
              const candidates = Array.from(document.querySelectorAll('*')).filter(isScrollable).slice(0, 8);
              return (async () => {
                for (let r=0; r<rounds; r++) {
                  for (const el of candidates) {
                    el.scrollTop = el.scrollHeight;
                    await sleep(150);
                    el.scrollTop = 0;
                    await sleep(150);
                  }
                }
              })();
            }
            """,
            max_rounds,
        )
    except Exception:
        pass


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


async def _open_action_modals(fr: Union[Page, Frame], wait_ms: int = 600):
    try:
        try:
            candidates = await fr.query_selector_all(
                "button, a[role='button'], [data-bs-toggle='modal'], [data-toggle='modal']"
            )
        except Exception:
            candidates = []

        keywords = re.compile(r"(create|add|new|edit|open)", re.I)
        clicked = 0
        for el in candidates:
            if clicked >= 3:
                break
            try:
                label = (
                    (await el.inner_text() or "")
                    + " "
                    + (await el.get_attribute("aria-label") or "")
                )
                if not keywords.search(label):
                    continue
                visible = await el.is_visible()
                disabled = await el.get_attribute("disabled")
                if not visible or disabled:
                    continue
                await _safe_click(el)
                clicked += 1
                await asyncio.sleep(max(0, wait_ms) / 1000)
            except Exception:
                continue
    except Exception:
        pass


async def _close_open_modals(fr: Union[Page, Frame], wait_ms: int = 400):
    try:
        try:
            await fr.keyboard.press("Escape")
        except Exception:
            pass

        close_selectors = [
            '[data-bs-dismiss="modal"]',
            '[aria-label="Close"]',
            '.modal button:has-text("Close")',
            '.modal button:has-text("Cancel")',
            'button:has-text("Close")',
            'button:has-text("Cancel")',
        ]
        for sel in close_selectors:
            try:
                buttons = await fr.query_selector_all(sel)
                for btn in buttons[:5]:
                    try:
                        try:
                            in_smartai_modal = await btn.evaluate(
                                "el => !!el.closest('#smartaiModal')"
                            )
                        except Exception:
                            in_smartai_modal = False
                        if in_smartai_modal:
                            continue
                        if await btn.is_visible():
                            await _safe_click(btn)
                            await asyncio.sleep(max(0, wait_ms) / 1000)
                    except Exception:
                        continue
            except Exception:
                continue
    except Exception:
        pass


def __log_page_events(page: Page):
    page.on(
        "console",
        lambda m: _safe_log(
            f"[console:{m.type() if callable(getattr(m, 'type', None)) else getattr(m, 'type', None)}] {m.text}"
        ),
    )
    page.on("pageerror", lambda e: _safe_log(f"[pageerror] {e}"))

    def _req_failed(req):
        failure = getattr(req, "failure", None)
        err = getattr(failure, "error_text", None) if failure else None
        if err is None and isinstance(failure, str):
            err = failure
        _safe_log(f"[requestfailed] {getattr(req, 'url', None)} -> {err}")

    page.on("requestfailed", _req_failed)
    page.on(
        "response",
        lambda resp: (
            _safe_log(f"[http {resp.status}] {resp.url}") if resp.status >= 400 else None
        ),
    )


async def __snapshot_if_blank(page: Page, tag: str):
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


async def _freeze_navigation(page: Page):
    await page.add_init_script(
        """
        (() => {
            window.__smartai_nav_locked = true;

            const block = () => {
                if (window.__smartai_nav_locked) {
                    throw new Error("Navigation locked during enrichment");
                }
            };

            history.pushState = new Proxy(history.pushState, { apply: block });
            history.replaceState = new Proxy(history.replaceState, { apply: block });

            window.addEventListener('beforeunload', block);
        })();
        """
    )


async def _unfreeze_navigation(page: Page):
    try:
        await page.evaluate("window.__smartai_nav_locked = false;")
    except Exception:
        pass


async def _dismiss_cookie_banner(page: Page) -> bool:
    return await dismiss_cookie_banner(page)


async def _smart_navigate(
    page: Page, raw_url: str, wait_until: str = "auto", timeout_ms: int = 60000
):
    def _with_scheme(u: str, scheme: str) -> str:
        p = urlparse(u)
        return f"{scheme}://{u}" if not p.scheme else u

    targets = [_with_scheme(raw_url, "https"), _with_scheme(raw_url, "http")]
    for url in targets:
        try:
            resp = await page.goto(
                url,
                wait_until=(
                    "domcontentloaded"
                    if (wait_until or "").lower() == "auto"
                    else wait_until
                ),
                timeout=timeout_ms,
            )
            try:
                await page.wait_for_selector("body", state="attached", timeout=min(5000, timeout_ms))
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
            continue
    return None


async def _clean_restart(page=None, browser=None, playwright=None):
    global PAGE, BROWSER, PLAYWRIGHT, TARGET, MANUAL_BROWSER_CLOSED
    if page is None:
        page = PAGE
    if browser is None:
        browser = BROWSER
    if playwright is None:
        playwright = PLAYWRIGHT
    try:
        if page and hasattr(page, "is_closed") and not page.is_closed():
            await page.close()
    except Exception:
        pass
    try:
        if browser:
            await browser.close()
    except Exception:
        pass
    try:
        if playwright:
            await playwright.stop()
    except Exception:
        pass
    PLAYWRIGHT = None
    BROWSER = None
    PAGE = None
    TARGET = None
    MANUAL_BROWSER_CLOSED = True


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
                    "document.querySelectorAll('input,select,textarea,button,a,iframe,[role],[contenteditable=\"true\"]').length"
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
# Derive page name
# -----------------------------------------------------------------------------
async def _derive_page_name(p: Page) -> str:
    try:
        title = (await p.title()) or ""
    except Exception:
        title = ""
    url = getattr(p, "url", "") or ""
    parsed = urlparse(url)
    path = (parsed.path or "/").strip("/").replace("/", "_") or "home"
    fragment = (parsed.fragment or "").strip()
    if fragment.startswith("/"):
        fragment = fragment[1:]
    if "?" in fragment:
        fragment = fragment.split("?", 1)[0]
    fragment = fragment.replace("/", "_").strip("_")
    # Prefer URL-based path so distinct routes don't collapse to a shared title.
    url_piece = normalize_page_name(path)
    fragment_piece = normalize_page_name(fragment)
    title_piece = normalize_page_name(title or "")
    if fragment_piece:
        pieces = [fragment_piece, url_piece, title_piece]
    else:
        pieces = (
            [url_piece, title_piece]
            if path and path != "home"
            else [title_piece, url_piece]
        )
    candidate = next((c for c in pieces if c), "unknown_page")
    return _canonical(candidate)


# -----------------------------------------------------------------------------
# Extraction core
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
                or r.get("nearby_label")
                or r.get("text")
                or ""
            ),
        )
        if key in seen:
            continue
        seen.add(key)
        out.append(r)
    return out


async def _frame_descriptor(frame: Frame) -> Dict[str, str]:
    try:
        handle = await frame.frame_element()
    except Exception:
        handle = None

    attrs: Dict[str, str] = {}
    if handle is not None:
        try:
            attrs = await handle.evaluate(
                """el => ({
                  id: el.id || "",
                  name: el.getAttribute("name") || "",
                  src: el.getAttribute("src") || "",
                  title: el.getAttribute("title") || "",
                  role: el.getAttribute("role") || "",
                  data_testid: el.getAttribute("data-testid") || el.getAttribute("data-test-id") || "",
                  data_qa: el.getAttribute("data-qa") || "",
                  data_cy: el.getAttribute("data-cy") || "",
                  data_test: el.getAttribute("data-test") || ""
                })"""
            )
        except Exception:
            attrs = {}

    name = frame.name or attrs.get("name", "") or ""
    url = frame.url or ""
    selector = ""
    if attrs.get("id"):
        selector = f"#{attrs['id']}"
    elif attrs.get("data_testid"):
        selector = f"[data-testid=\"{attrs['data_testid']}\"]"
    elif name:
        selector = f"iframe[name=\"{name}\"]"
    elif attrs.get("src"):
        selector = f"iframe[src*=\"{attrs['src']}\"]"
    else:
        selector = "iframe"

    return {
        "id": attrs.get("id", ""),
        "name": name,
        "src": attrs.get("src", ""),
        "title": attrs.get("title", ""),
        "role": attrs.get("role", ""),
        "data_testid": attrs.get("data_testid", ""),
        "data_qa": attrs.get("data_qa", ""),
        "data_cy": attrs.get("data_cy", ""),
        "data_test": attrs.get("data_test", ""),
        "selector": selector,
        "url": url,
    }


async def _build_frame_path(frame: Frame) -> List[Dict[str, str]]:
    path: List[Dict[str, str]] = []
    current = frame
    while current is not None and current.parent_frame:
        desc = await _frame_descriptor(current)
        path.append(desc)
        current = current.parent_frame
    path.reverse()
    return path


async def _rich_extract_dom_metadata(fr: Union[Page, Frame]) -> List[Dict[str, Any]]:
    js = r"""
    (() => {
      const out = [];
      const seen = new Set();
      const norm = s => (s || "").replace(/\s+/g, " ").trim();

      const textOf = el => norm(el ? (el.innerText || el.textContent || "") : "");

      const CAPTURE_ALL = %s;
      const INCLUDE_HIDDEN = %s;
      const isVisible = el => {
        if (CAPTURE_ALL) return true;
        if (!el || !el.ownerDocument) return false;
        const cs = el.ownerDocument.defaultView.getComputedStyle(el);
        if (!INCLUDE_HIDDEN) {
          if (!cs || cs.visibility === "hidden" || cs.display === "none" || parseFloat(cs.opacity || "1") < 0.01)
            return false;
        }
        const rect = el.getBoundingClientRect();
        if (!rect || rect.width < 1 || rect.height < 1) return false;
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
      const clickType = el => {
        try {
          const data = [
            attr(el, "data-action"),
            attr(el, "data-click"),
            attr(el, "data-event"),
            attr(el, "data-handler"),
            attr(el, "data-action-type"),
            attr(el, "contextmenu")
          ].join(" ").toLowerCase();
          const hasContext = hasAttr(el, "oncontextmenu") || hasAttr(el, "contextmenu") || /contextmenu|rightclick|right_click/.test(data);
          const hasDouble = hasAttr(el, "ondblclick") || /dblclick|doubleclick/.test(data);
          if (hasContext && hasDouble) return "right,double";
          if (hasContext) return "right";
          if (hasDouble) return "double";
        } catch(e) {}
        return "";
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
          if (hasAttr(el, "data-rbd-droppable-id")) return true;
          if (hasAttr(el, "data-dnd-kit-droppable-id")) return true;
          const cls = classListText(el);
          if (cls.includes("droppable") || cls.includes("drop-zone") || cls.includes("dropzone")) return true;
        } catch(e) {}
        return false;
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

      const getNearbyLabel = el => {
        try {
          const rect = el.getBoundingClientRect();
          const candidates = Array.from(document.querySelectorAll("label,span,div,p,strong,legend,h1,h2,h3,h4,h5,h6"));
          let best = "";
          let bestScore = Number.POSITIVE_INFINITY;
          for (const cand of candidates) {
            if (!cand || cand === el || cand.contains(el) || el.contains(cand)) continue;
            const text = textOf(cand);
            if (!text || text.length < 1 || text.length > 120) continue;
            const r = cand.getBoundingClientRect();
            if (!r || r.width < 1 || r.height < 1) continue;
            const dx = Math.abs(r.left - rect.left);
            const dy = Math.abs((r.top + r.height / 2) - (rect.top + rect.height / 2));
            const above = r.bottom <= rect.top + 12;
            const leftish = r.right <= rect.left + 24;
            if (!(above || leftish)) continue;
            const score = dx + dy;
            if (score < bestScore) {
              bestScore = score;
              best = text;
            }
          }
          return norm(best);
        } catch (e) {
          return "";
        }
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

      const accessibleName = (el, doc, _lmap) => {
        const aria = el.getAttribute && el.getAttribute("aria-label");
        if (aria) return norm(aria);

        const lb = el.getAttribute && el.getAttribute("aria-labelledby");
        if (lb) {
          const txt = lb.split(/\s+/).map(id => {
            const n = doc.getElementById(id);
            return n ? textOf(n) : "";
          }).join(" ");
          if (txt) return norm(txt);
        }

        const nearby = isInputLike(el) ? getNearbyLabel(el) : "";
        const explicit = bestExplicitLabel(el, _lmap, nearby);
        if (explicit) return explicit;

        const lab = el.closest("label");
        if (lab) return norm(textOf(lab));

        const ph = el.getAttribute && el.getAttribute("placeholder");
        if (ph) return norm(ph);

        const nearby = getNearbyLabel(el);
        if (nearby) return nearby;

        const title = el.getAttribute && el.getAttribute("title");
        if (title) return norm(title);

        return norm(el.innerText || el.value || el.textContent || "");
      };

      const push = r => {
        const key = JSON.stringify([
          r.tag || "", r.id || "", r.name || "", r.type || "",
          norm(r.label_text || r.aria_label || r.placeholder || r.nearby_label || r.text || "")
        ]).slice(0, 500);
        if (!seen.has(key)) {
          seen.add(key);
          out.push(r);
        }
      };

      const pick = (el, doc, _lmap) => {
        if (!CAPTURE_ALL && el && el.closest && el.closest('#smartaiModal')) return;
        if (!isVisible(el)) return;

        const tag = (el.tagName || "").toLowerCase();
        const rect = el.getBoundingClientRect();
        let clickable = false;

        if (["button", "a", "option", "summary"].includes(tag)) clickable = true;

        const role = el.getAttribute("role");
        if (role === "button" || role === "menuitem" || role === "link") clickable = true;

        if (tag === "li" || el.getAttribute("role") === "listitem") {
          const style = window.getComputedStyle(el);
          const cursorPointer = style && style.cursor === "pointer";
          const hasClickEvent =
            el.onclick ||
            el.getAttribute("onclick") ||
            el.getAttribute("role") === "button";
          if (cursorPointer || hasClickEvent) clickable = true;
        }

        const txt = accessibleName(el, doc, _lmap);
        const nearby = isInputLike(el) ? getNearbyLabel(el) : "";
        const dragHandle = dragHandleFor(el);

        push({
          tag,
          role: role || "",
          id: el.id || "",
          name: el.getAttribute("name") || "",
          type: el.getAttribute("type") || "",
          text: txt,
          aria_label: el.getAttribute("aria-label") || "",
          placeholder: el.getAttribute("placeholder") || "",
          title: el.getAttribute("title") || "",
          src: el.getAttribute("src") || "",
          data_testid: attr(el, "data-testid") || attr(el, "data-test-id") || "",
          data_qa: attr(el, "data-qa") || "",
          data_cy: attr(el, "data-cy") || "",
          data_test: attr(el, "data-test") || "",
          label_text: txt,
          nearby_label: nearby,
          click_type: clickType(el),
          clickable: clickable,
          bbox: { x: rect.x, y: rect.y, width: rect.width, height: rect.height },
          css_selector: selectorHint(el),
          is_draggable: isDraggable(el),
          is_droppable: isDroppable(el),
          drag_handle_selector: dragHandle.selector || "",
          drag_handle_text: dragHandle.text || ""
        });
      };

      const pickText = (el, doc, _lmap) => {
        if (!CAPTURE_ALL && el && el.closest && el.closest('#smartaiModal')) return;
        if (!isVisible(el)) return;
        const tag = (el.tagName || "").toLowerCase();
        if (!/^(h1|h2|h3|h4|h5|h6|label|legend|span|strong|em|p|div)$/.test(tag))
          return;

        const txt = textOf(el);
        if (!txt || txt.length < 2) return;

        const rect = el.getBoundingClientRect();
        if (!rect || rect.width < 1 || rect.height < 1) return;

        push({
          tag,
          role: el.getAttribute("role") || "",
          id: el.id || "",
          name: el.getAttribute("name") || "",
          type: "",
          text: txt,
          label_text: txt,
          aria_label: el.getAttribute("aria-label") || "",
          placeholder: "",
          title: el.getAttribute("title") || "",
          nearby_label: "",
          clickable: false,
          bbox: { x: rect.x, y: rect.y, width: rect.width, height: rect.height }
        });
      };

      const visit = root => {
        const doc = root;
        const _lmap = labelForMap(doc);
        const walker = doc.createTreeWalker(root, NodeFilter.SHOW_ELEMENT);

        while (walker.nextNode()) {
          const el = walker.currentNode;
          pick(el, doc, _lmap);
          pickText(el, doc, _lmap);
          if (el.shadowRoot) visit(el.shadowRoot);
        }
      };

      visit(document);
      return out;
    })();
    """ % (
        "true" if CAPTURE_ALL_DOM else "false",
        "true" if INCLUDE_HIDDEN_ENABLED else "false",
    )

    try:
        frames = fr.frames if isinstance(fr, Page) else [fr]

        all_elements: List[Dict[str, Any]] = []
        counts_by_frame: Dict[str, int] = {}

        for frame in frames:
            try:
                elements = await frame.evaluate(js)
            except Exception:
                elements = []

            try:
                frame_path = await _build_frame_path(frame)
                frame_depth = len(frame_path)
                frame_selector = frame_path[-1]["selector"] if frame_path else ""
                frame_name = frame.name or ""
                frame_url = frame.url or ""
                frame_hint = "iframe/" * frame_depth if frame_depth else ""
            except Exception:
                frame_path = []
                frame_depth = 0
                frame_selector = ""
                frame_name = ""
                frame_url = ""
                frame_hint = ""

            for e in elements:
                if isinstance(e, dict):
                    e["frame_path"] = frame_path
                    e["frame_depth"] = frame_depth
                    e["frame_selector"] = frame_selector
                    e["frame_name"] = frame_name
                    e["frame_url"] = frame_url
                    e["frame"] = frame_hint
                all_elements.append(e)

            key = frame_selector or frame_name or frame_url or "top"
            counts_by_frame[key] = counts_by_frame.get(key, 0) + len(elements)

            if frame_url and _infer_payment_provider(frame_url):
                try:
                    handle = await frame.frame_element()
                    if handle:
                        iframe_meta = await handle.evaluate(
                            """el => {
                              const r = el.getBoundingClientRect();
                              return {
                                tag: (el.tagName || "").toLowerCase(),
                                role: el.getAttribute("role") || "",
                                id: el.id || "",
                                name: el.getAttribute("name") || "",
                                type: "",
                                src: el.getAttribute("src") || "",
                                title: el.getAttribute("title") || "",
                                text: "",
                                aria_label: el.getAttribute("aria-label") || "",
                                placeholder: "",
                                data_testid: el.getAttribute("data-testid") || el.getAttribute("data-test-id") || "",
                                data_qa: el.getAttribute("data-qa") || "",
                                data_cy: el.getAttribute("data-cy") || "",
                                data_test: el.getAttribute("data-test") || "",
                                label_text: el.getAttribute("title") || el.getAttribute("aria-label") || el.getAttribute("name") || "payment iframe",
                                clickable: false,
                                bbox: { x: r.x, y: r.y, width: r.width, height: r.height },
                                css_selector: el.id ? `#${el.id}` : "iframe"
                              };
                            }"""
                        )
                        if isinstance(iframe_meta, dict):
                            iframe_meta["frame_path"] = frame_path
                            iframe_meta["frame_depth"] = frame_depth
                            iframe_meta["frame_selector"] = frame_selector
                            iframe_meta["frame_name"] = frame_name
                            iframe_meta["frame_url"] = frame_url
                            iframe_meta["frame"] = frame_hint
                            all_elements.append(iframe_meta)
                except Exception:
                    pass

        _safe_log(f"[DEBUG] Extracted {len(all_elements)} DOM elements across frames.")
        _safe_log(f"[DEBUG] Elements grouped by frame: {counts_by_frame}")
        return all_elements

    except Exception as e:
        _safe_log(f"[ERROR] _rich_extract_dom_metadata failed: {e}")
        return []


async def _extract_table_structured_data(
    fr: Union[Page, Frame], max_rows: int = 20, max_cells: int = 20
) -> List[Dict[str, Any]]:
    js = r"""
    (maxRows, maxCells) => {
      const out = [];
      const norm = s => (s || "").replace(/\s+/g, " ").trim();
      const textOf = el => norm(el ? (el.innerText || el.textContent || "") : "");

      const CAPTURE_ALL = %s;
      const INCLUDE_HIDDEN = %s;
      const isVisible = el => {
        if (CAPTURE_ALL) return true;
        if (!el || !el.ownerDocument) return false;
        const cs = el.ownerDocument.defaultView.getComputedStyle(el);
        if (!INCLUDE_HIDDEN) {
          if (!cs || cs.visibility === "hidden" || cs.display === "none" || parseFloat(cs.opacity || "1") < 0.01)
            return false;
        }
        const rect = el.getBoundingClientRect();
        if (!rect || rect.width < 1 || rect.height < 1) return false;
        return true;
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
    """ % (
        "true" if CAPTURE_ALL_DOM else "false",
        "true" if INCLUDE_HIDDEN_ENABLED else "false",
    )
    try:
        return await fr.evaluate(js, max_rows, max_cells)
    except Exception as e:
        _safe_log(f"[WARN] _extract_table_structured_data failed: {e}")
        return []


# -----------------------------------------------------------------------------
# Enrichment
# -----------------------------------------------------------------------------
async def _refresh_target(reason: str = ""):
    global PAGE, TARGET
    try:
        if PAGE is None:
            return
        TARGET = await _select_extraction_target(PAGE)
        _safe_log(f"[stability] TARGET refreshed ({reason}) -> {getattr(TARGET, 'url', None)}")
    except Exception as e:
        _safe_log(f"[stability] TARGET refresh failed ({reason}): {e}")


def _get_ocr_data_by_canonical(canonical_page_name: str) -> List[Dict[str, Any]]:
    try:
        recs = _get_chroma_collection().get() or {}
        metas = filter_metadata_by_project(recs.get("metadatas", []) or [])
        return [
            m
            for m in metas
            if _canonical((m or {}).get("page_name", "")) == canonical_page_name
        ]
    except Exception:
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
            or r.get("nearby_label")
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
    stable_url = getattr(PAGE, "url", None)
    if PAGE is None:
        raise HTTPException(status_code=500, detail="Cannot extract. No active page handle.")
    if hasattr(PAGE, "is_closed") and PAGE.is_closed():
        raise HTTPException(status_code=500, detail="Cannot extract. Page is already closed.")

    current_page_name = _canonical(page_name)
    await _refresh_target("enrich-start")
    paths = _ensure_dirs(src_directory)

    if TARGET is None or not await _is_js_accessible(TARGET):
        try:
            if await _is_js_accessible(PAGE.main_frame):
                TARGET = PAGE.main_frame
            else:
                TARGET = PAGE
        except Exception:
            TARGET = PAGE

    await _pre_settle(TARGET, timeout_ms=8000)
    if AUTOSCROLL_ENABLED:
        await _progressive_autoscroll(TARGET, steps=6, pause_ms=250)
    await _open_action_modals(TARGET, wait_ms=600)
    if DEEP_TABS_ENABLED:
        await _deep_expand_tabs_and_accordions(TARGET, max_rounds=2)
    if DEEP_CONTAINER_SCROLL_ENABLED:
        await _deep_scroll_containers(TARGET, max_rounds=2)
    if DEEP_CAPTURE_ENABLED:
        await _deep_capture_expand(TARGET, max_rounds=4)
        await _progressive_autoscroll(TARGET, steps=10, pause_ms=300)

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
        debug_path = paths["debug"] / f"dom_eval_debug_{_file_key(current_page_name)}.json"
        _write_project_file(
            debug_path,
            json.dumps(probe, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception as e:
        try:
            error_path = paths["debug"] / f"dom_eval_debug_{_file_key(current_page_name)}_error.txt"
            _write_project_file(error_path, str(e), encoding="utf-8")
        except Exception:
            pass

    dom_data = await _rich_extract_dom_metadata(TARGET) or []
    table_data = await _extract_table_structured_data(TARGET) or []
    if table_data:
        dom_data = list(dom_data) + list(table_data)
    try:
        _ = len(dom_data)
    except Exception:
        dom_data = list(dom_data)

    if _assess_dom_quality(dom_data):
        try:
            basic = await extract_dom_metadata(TARGET, current_page_name) or []
            if basic:
                dom_data = _dedupe_records(list(dom_data) + list(basic))
        except Exception:
            pass

    if stable_url and PAGE.url != stable_url:
        await PAGE.goto(stable_url, wait_until="domcontentloaded")
        try:
            await _dismiss_cookie_banner(PAGE)
        except Exception:
            pass

    dom_data = _dedupe_records(dom_data)

    for rec in dom_data:
        try:
            label = (
                rec.get("label_text")
                or rec.get("nearby_label")
                or rec.get("label")
                or rec.get("aria_label")
                or rec.get("placeholder")
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

    _write_project_file(
        paths["debug"] / f"dom_data_{_file_key(current_page_name)}.txt",
        pprint.pformat(dom_data),
        encoding="utf-8",
    )

    updated_matches = dom_data or []
    _write_project_file(
        paths["debug"] / f"captured_dom_{_file_key(current_page_name)}.txt",
        pprint.pformat(updated_matches),
        encoding="utf-8",
    )

    standardized_matches = []
    for m in updated_matches or []:
        m = _standardize_dom_only(m, current_page_name, getattr(PAGE, "url", None))
        if not m:
            continue

        m = build_standard_metadata(
            m, current_page_name, image_path="", source_url=getattr(PAGE, "url", None)
        )
        standardized_matches.append(m)

    for m in standardized_matches:
        m["label_text"] = _clean_label_text(m.get("label_text", ""))
        m["text"] = _clean_label_text(m.get("text", ""))

    standardized_matches = [
        m for m in standardized_matches if not _is_container_stub(m) and not _is_form_wrapper(m)
    ]
    standardized_matches = _filter_secondary_labels(standardized_matches)

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
                page_name=current_page_name,
                image_path="",
                source_url=getattr(PAGE, "url", None),
            )
        )
        existing_keys.add(key)

    for m in standardized_matches:
        m["label_text"] = _clean_label_text(m.get("label_text", ""))
        m["text"] = _clean_label_text(m.get("text", ""))

    if not standardized_matches:
        if dom_data:
            standardized_matches = []
            for r in dom_data:
                rec = dict(r or {})
                tag = (rec.get("tag") or rec.get("tag_name") or "").lower()
                if not rec.get("ocr_type") and tag == "li":
                    rec["ocr_type"] = "button"

                bbox = rec.get("bbox")
                if isinstance(bbox, str):
                    try:
                        parsed = json.loads(bbox.replace("'", '"'))
                        if isinstance(parsed, dict):
                            bbox = parsed
                    except Exception:
                        bbox = {}
                if isinstance(bbox, dict):
                    rec["bbox"] = {
                        "x": bbox.get("x", 0),
                        "y": bbox.get("y", 0),
                        "width": bbox.get("width", 0),
                        "height": bbox.get("height", 0),
                    }
                else:
                    rec["bbox"] = {
                        "x": rec.get("x", 0),
                        "y": rec.get("y", 0),
                        "width": rec.get("width", 0),
                        "height": rec.get("height", 0),
                    }

                if not rec.get("tag_name") and rec.get("tag"):
                    rec["tag_name"] = rec.get("tag")
                if not rec.get("xpath"):
                    rec["xpath"] = rec.get("xpath") or rec.get("locator_xpath") or ""
                if not rec.get("get_by_text"):
                    rec["get_by_text"] = rec.get("text", "")
                if not rec.get("get_by_role"):
                    rec["get_by_role"] = rec.get("role", "")
                if not rec.get("placeholder"):
                    rec["placeholder"] = rec.get("placeholder", "")

                rec["label_text"] = _clean_label_text(
                    _label_priority(rec) or rec.get("label_text", "")
                )
                rec["text"] = _clean_label_text(rec.get("text", ""))

                dom_role = (rec.get("role") or "").lower()
                dom_tag = (rec.get("tag") or rec.get("tag_name") or "").lower()
                dom_get_by_role = (rec.get("get_by_role") or "").lower()
                aria_multiselectable = str(
                    rec.get("aria_multiselectable")
                    or rec.get("aria-multiselectable")
                    or ""
                ).lower()
                select_like_roles = {"combobox", "listbox", "tree", "option"}

                if (
                    dom_role in select_like_roles
                    or dom_get_by_role in select_like_roles
                    or dom_tag == "select"
                    or aria_multiselectable == "true"
                ):
                    if _is_option_list_label(
                        rec.get("label_text") or rec.get("text") or "",
                        dom_tag,
                        dom_role,
                    ):
                        continue
                    rec["ocr_type"] = "select"
                elif not rec.get("ocr_type"):
                    if dom_role in {"button", "link", "checkbox", "textbox"}:
                        rec["ocr_type"] = dom_role
                    elif dom_tag in {"button", "a"}:
                        rec["ocr_type"] = "button"
                    elif dom_tag in {"input", "textarea", "select"}:
                        rec["ocr_type"] = "textbox" if dom_tag in {"input", "textarea"} else "select"
                    elif dom_tag == "iframe":
                        rec["ocr_type"] = "iframe"

                label_text = rec.get("label_text") or rec.get("text") or ""
                if len(label_text) > 5000:
                    continue

                standardized_matches.append(
                    build_standard_metadata(
                        rec,
                        page_name=current_page_name,
                        image_path="",
                        source_url=getattr(PAGE, "url", None),
                    )
                )
            standardized_matches = [m for m in standardized_matches if not _is_container_stub(m)]
            standardized_matches = [m for m in standardized_matches if not _is_form_wrapper(m)]
            standardized_matches = _filter_secondary_labels(standardized_matches)
        else:
            standardized_matches = [
                _no_elements_record(current_page_name, getattr(PAGE, "url", None))
            ]

    out_path = _output_path_for_page(current_page_name, getattr(PAGE, "url", None))
    try:
        existing_payload = (
            json.loads(out_path.read_text(encoding="utf-8") or "[]")
            if out_path.exists()
            else []
        )
    except Exception:
        existing_payload = []

    combined_payload = _merge_enrichment_records(existing_payload, standardized_matches)
    combined_payload = [_strip_dom_flags(r) for r in combined_payload]
    _write_project_file(out_path, json.dumps(combined_payload, indent=2), encoding="utf-8")

    ocr_only_payload = [r for r in combined_payload if (r.get("ocr_type") or "").strip()]
    ocr_only_path = _ocr_only_path_for_page(current_page_name, getattr(PAGE, "url", None))
    _write_project_file(
        ocr_only_path, json.dumps(ocr_only_payload, indent=2), encoding="utf-8"
    )

    meta_dir = paths["meta"]
    _write_filtered_aggregate(meta_dir, ocr_only_payload)

    _safe_log(
        f"[enrich] wrote: {out_path} raw={len(dom_data)} final={len(standardized_matches)} target={getattr(TARGET, 'url', None)}"
    )

    try:
        await asyncio.sleep(max(0.0, MODAL_CAPTURE_PAUSE_SEC))
    except Exception:
        pass
    await _close_open_modals(TARGET)
    try:
        await TARGET.keyboard.press("Escape")
    except Exception:
        pass

    return {
        "status": "success",
        "message": f"Captured {len(standardized_matches)} elements for page: {current_page_name}",
        "captured_data": standardized_matches,
        "count": len(standardized_matches),
        "output_path": str(out_path),
        "ocr_only_path": str(ocr_only_path),
    }


# -----------------------------------------------------------------------------
# Routes
# -----------------------------------------------------------------------------
@router.post("/{project_id}/manual/launch-browser")
async def launch_browser(
    project_id: int,
    req: LaunchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    global PLAYWRIGHT, BROWSER, PAGE, TARGET, CURRENT_PAGE_NAME
    global EXECUTION_MODE, ENRICH_UI_ENABLED, AUTOSCROLL_ENABLED, MANUAL_BROWSER_CLOSED
    global _AUTH_WATCH_TASK

    PLAYWRIGHT = None
    BROWSER = None
    PAGE = None
    TARGET = None
    CURRENT_PAGE_NAME = "unknown_page"
    EXECUTION_MODE = False
    ENRICH_UI_ENABLED = False
    AUTOSCROLL_ENABLED = True
    MANUAL_BROWSER_CLOSED = False

    project = get_user_project(db, project_id, current_user)
    project_paths = _ensure_project_structure(project)
    src_directory = Path(project_paths["src_dir"])
    projectChromaPath = project_paths["chroma_path"]
    project_root = Path(project_paths["project_root"])
    project_context = build_project_context(current_user, project.id, db)
    tokens = set_request_context(project_context=project_context)
    storage = DatabaseBackedProjectStorage(project, _src_dir(), db)
    _set_active_storage(storage)

    try:
        await _clean_restart(PAGE, BROWSER, PLAYWRIGHT)
        MANUAL_BROWSER_CLOSED = False
        PLAYWRIGHT = await async_playwright().start()

        launch_args: List[str] = []
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
        if STEALTH_ENABLED:
            launch_args += [
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars",
            ]

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
        elif STEALTH_ENABLED:
            context_kwargs["user_agent"] = _DEFAULT_STEALTH_UA
        if req.extra_http_headers:
            context_kwargs["extra_http_headers"] = req.extra_http_headers
        if req.http_username and req.http_password:
            context_kwargs["http_credentials"] = {
                "username": req.http_username,
                "password": req.http_password,
            }

        storage_file = auth_storage_path(project_root)
        if not storage_file.exists():
            storage_file = _resolve_storage_file()
        storage_state = _load_storage_state_for_context(storage_file)
        if storage_state is not None:
            context_kwargs["storage_state"] = storage_state
            _safe_log(f"[enrichment] Using storage_state from {storage_file}")
        else:
            _safe_log(f"[enrichment] No storage_state file at {storage_file}")

        headless = req.headless
        if not auth_storage_path(project_root).exists():
            headless = False

        BROWSER = await PLAYWRIGHT.chromium.launch(
            headless=headless, slow_mo=req.slow_mo, args=launch_args
        )
        context = await BROWSER.new_context(**context_kwargs)
        await _apply_stealth_to_context(context)

        ENRICH_UI_ENABLED = bool(req.enable_enrichment_ui)
        AUTOSCROLL_ENABLED = True

        PAGE = await context.new_page()
        __log_page_events(PAGE)
        await _remove_legacy_modal(PAGE)

        try:
            PAGE.set_default_timeout(req.nav_timeout_ms)
            PAGE.set_default_navigation_timeout(req.nav_timeout_ms)
        except Exception:
            pass

        async def _binding_enrich(source, page_or_url: Optional[str] = None):
            try:
                target_page = await _derive_page_name(PAGE)
                globals()["CURRENT_PAGE_NAME"] = target_page

                await _freeze_navigation(PAGE)
                with _activate_project_storage_from_scope(current_user.organization_id):
                    result = await _run_enrichment_for(
                        PAGE,
                        TARGET,
                        AUTOSCROLL_ENABLED,
                        EXECUTION_MODE,
                        src_directory,
                        projectChromaPath,
                        target_page,
                    )
                await _unfreeze_navigation(PAGE)
                return json.dumps(result)
            except Exception as e:
                return json.dumps({"status": "fail", "error": str(e)})

        await PAGE.expose_binding("smartAI_enrich", _binding_enrich)

        async def _binding_close_browser(source):
            try:
                globals()["MANUAL_BROWSER_CLOSED"] = True
                await _clean_restart()
                return json.dumps({"status": "success"})
            except Exception as e:
                return json.dumps({"status": "fail", "error": str(e)})

        await PAGE.expose_binding("smartAI_close_browser", _binding_close_browser)

        if ENRICH_UI_ENABLED and _enrich_ui_allowed(req.url):
            await _remove_legacy_modal(PAGE)
            await PAGE.add_init_script(UI_KEYBRIDGE_JS)
            await PAGE.add_init_script(UI_MODAL_TOP_JS)

        await _smart_navigate(
            PAGE,
            req.url,
            wait_until=req.wait_until if req.wait_until else "auto",
            timeout_ms=req.nav_timeout_ms,
        )

        if should_start_auth_watch(auth_storage_path(project_root), getattr(PAGE, "url", "")):
            if _AUTH_WATCH_TASK and not _AUTH_WATCH_TASK.done():
                _AUTH_WATCH_TASK.cancel()
            _AUTH_WATCH_TASK = asyncio.create_task(wait_for_login_and_save(PAGE, project_root))

        await _remove_legacy_modal(PAGE)

        if ENRICH_UI_ENABLED and _enrich_ui_allowed(getattr(PAGE, "url", None)):
            try:
                if ENRICH_UI_DELAY_SEC > 0:
                    await asyncio.sleep(ENRICH_UI_DELAY_SEC)
                await PAGE.evaluate(
                    "window._smartaiDisabled = false; window._smartaiTopInstalled = false; window._smartaiKeyBridgeInstalled = false;"
                )
                await PAGE.add_init_script(UI_KEYBRIDGE_JS)
                await PAGE.add_init_script(UI_MODAL_TOP_JS)
                await PAGE.wait_for_function(
                    "typeof window.smartaiToggleModal === 'function'",
                    timeout=3000,
                )
                await PAGE.evaluate(
                    """
                    (() => {
                      if (typeof window.smartaiToggleModal === 'function') {
                        window.smartaiToggleModal();
                      }
                    })();
                    """
                )
            except Exception:
                pass

        try:
            navigated_url = getattr(PAGE, "url", None) or req.url
            if navigated_url:
                os.environ["SITE_URL"] = navigated_url
        except Exception:
            pass

        await __snapshot_if_blank(PAGE, "launch-browser")
        try:
            TARGET = await _select_extraction_target(PAGE)
        except Exception:
            TARGET = PAGE

        CURRENT_PAGE_NAME = _canonical(await _derive_page_name(PAGE))
        msg = f"Browser launched and navigated to {req.url}. Modal available (Alt+Q)."
        return {"status": "success", "message": msg, "auto_enrich_result": None}

    except HTTPException:
        raise
    except Exception as e:
        import traceback

        traceback.print_exc()
        await _clean_restart(PAGE, BROWSER, PLAYWRIGHT)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        _set_active_storage(None)
        reset_request_context(tokens)


@router.post("/manual/storage-state/save")
async def save_manual_storage_state(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_id: Optional[int] = None,
):
    project = _resolve_project_for_user(db, current_user, project_id)
    project_paths = _ensure_project_structure(project)
    if PAGE is None or (hasattr(PAGE, "is_closed") and PAGE.is_closed()):
        raise HTTPException(status_code=409, detail="No active page to capture storage state.")
    path = auth_storage_path(Path(project_paths["project_root"]))
    try:
        await PAGE.context.storage_state(path=str(path))
        try:
            current_url = PAGE.url or ""
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
        raise HTTPException(
            status_code=500, detail=f"Failed to save storage state: {exc}"
        ) from exc
    return {"status": "success", "path": str(path)}


@router.post("/enrich-from-url")
async def enrich_from_url(
    req: EnrichFromUrlRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_id: Optional[int] = None,
):
    global PLAYWRIGHT, BROWSER, PAGE, TARGET, AUTOSCROLL_ENABLED, ENRICH_UI_ENABLED
    global MANUAL_BROWSER_CLOSED, CURRENT_PAGE_NAME, _AUTH_WATCH_TASK

    MANUAL_BROWSER_CLOSED = False
    project = _resolve_project_for_user(db, current_user, project_id)
    project_paths = _ensure_project_structure(project)
    src_directory = Path(project_paths["src_dir"])
    projectChromaPath = project_paths["chroma_path"]
    project_root = Path(project_paths["project_root"])
    project_context = build_project_context(current_user, project.id, db)
    tokens = set_request_context(project_context=project_context)
    storage = DatabaseBackedProjectStorage(project, _src_dir(), db)
    _set_active_storage(storage)

    try:
        await _clean_restart()
        MANUAL_BROWSER_CLOSED = False
        PLAYWRIGHT = await async_playwright().start()

        context_kwargs: Dict[str, Any] = {
            "ignore_https_errors": req.ignore_https_errors,
            "viewport": {"width": 1400, "height": 900},
            "bypass_csp": True,
            "has_touch": False,
            "device_scale_factor": 1,
            "reduced_motion": "reduce",
            "color_scheme": "light",
        }
        if STEALTH_ENABLED:
            context_kwargs["user_agent"] = _DEFAULT_STEALTH_UA

        storage_file = auth_storage_path(project_root)
        if not storage_file.exists():
            storage_file = _resolve_storage_file()
        storage_state = _load_storage_state_for_context(storage_file)
        if storage_state is not None:
            context_kwargs["storage_state"] = storage_state
            _safe_log(f"[enrichment] Using storage_state from {storage_file}")
        else:
            _safe_log(f"[enrichment] No storage_state file at {storage_file}")

        headless = req.headless
        if not auth_storage_path(project_root).exists():
            headless = False

        launch_args: List[str] = []
        if STEALTH_ENABLED:
            launch_args += [
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars",
            ]

        BROWSER = await PLAYWRIGHT.chromium.launch(
            headless=headless, slow_mo=req.slow_mo, args=launch_args
        )
        context = await BROWSER.new_context(**context_kwargs)
        await _apply_stealth_to_context(context)
        PAGE = await context.new_page()
        __log_page_events(PAGE)

        try:
            PAGE.set_default_timeout(req.nav_timeout_ms)
            PAGE.set_default_navigation_timeout(req.nav_timeout_ms)
        except Exception:
            pass

        ENRICH_UI_ENABLED = bool(req.enable_enrichment_ui)
        AUTOSCROLL_ENABLED = False

        async def _binding_enrich(source, page_name: Optional[str] = None):
            try:
                target_page = _canonical(page_name or CURRENT_PAGE_NAME or "page")
                globals()["CURRENT_PAGE_NAME"] = target_page
                with _activate_project_storage_from_scope(current_user.organization_id):
                    res = await _run_enrichment_for(
                        PAGE,
                        TARGET,
                        AUTOSCROLL_ENABLED,
                        EXECUTION_MODE,
                        src_directory,
                        projectChromaPath,
                        target_page,
                    )
                return json.dumps(res)
            except HTTPException as he:
                return json.dumps({"status": "fail", "error": he.detail})
            except Exception as e:
                return json.dumps({"status": "fail", "error": str(e)})

        await PAGE.expose_binding("smartAI_enrich", _binding_enrich)

        async def _binding_close_browser(source):
            try:
                globals()["MANUAL_BROWSER_CLOSED"] = True
                await _clean_restart()
                return json.dumps({"status": "success"})
            except Exception as e:
                return json.dumps({"status": "fail", "error": str(e)})

        await PAGE.expose_binding("smartAI_close_browser", _binding_close_browser)

        if ENRICH_UI_ENABLED and _enrich_ui_allowed(req.url):
            await _remove_legacy_modal(PAGE)
            await PAGE.add_init_script(UI_KEYBRIDGE_JS)
            await PAGE.add_init_script(UI_MODAL_TOP_JS)

        await _smart_navigate(
            PAGE,
            req.url,
            wait_until=req.wait_until if req.wait_until else "auto",
            timeout_ms=req.nav_timeout_ms,
        )

        if should_start_auth_watch(auth_storage_path(project_root), getattr(PAGE, "url", "")):
            if _AUTH_WATCH_TASK and not _AUTH_WATCH_TASK.done():
                _AUTH_WATCH_TASK.cancel()
            _AUTH_WATCH_TASK = asyncio.create_task(wait_for_login_and_save(PAGE, project_root))

        try:
            navigated_url = getattr(PAGE, "url", None) or req.url
            if navigated_url:
                os.environ["SITE_URL"] = navigated_url
        except Exception:
            pass

        if (
            ENRICH_UI_ENABLED
            and _enrich_ui_allowed(getattr(PAGE, "url", None))
            and ENRICH_UI_DELAY_SEC > 0
        ):
            try:
                await asyncio.sleep(ENRICH_UI_DELAY_SEC)
            except Exception:
                pass

        await __snapshot_if_blank(PAGE, "enrich-from-url")
        try:
            TARGET = await _select_extraction_target(PAGE)
        except Exception:
            TARGET = PAGE

        CURRENT_PAGE_NAME = "page"
        msg = f"Ready for manual enrichment on {req.url}. Open modal (Alt+Q) and click Enrich."
        return {"status": "success", "message": msg, "page_name": CURRENT_PAGE_NAME}

    except HTTPException:
        raise
    except Exception as e:
        import traceback

        traceback.print_exc()
        await _clean_restart()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        _set_active_storage(None)
        reset_request_context(tokens)


@router.post("/set-current-page-name")
async def set_page_name(
    req: PageNameSetRequest,
    project_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _resolve_project_for_user(db, current_user, project_id)
    global CURRENT_PAGE_NAME
    CURRENT_PAGE_NAME = _canonical(req.page_name)
    _safe_log(f"[INFO] Page name set to: {CURRENT_PAGE_NAME}")
    return {"status": "success", "page_name": CURRENT_PAGE_NAME}


@router.post("/execution-mode")
async def toggle_execution_mode(
    req: ExecutionModeRequest,
    project_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _resolve_project_for_user(db, current_user, project_id)
    global EXECUTION_MODE, ENRICH_UI_ENABLED, AUTOSCROLL_ENABLED, TARGET
    EXECUTION_MODE = bool(req.enabled)
    AUTOSCROLL_ENABLED = False if EXECUTION_MODE else AUTOSCROLL_ENABLED
    if EXECUTION_MODE and PAGE is not None:
        try:
            await PAGE.evaluate(
                "window._smartaiDisabled = true; if (window.smartAI_disableUI) window.smartAI_disableUI();"
            )
        except Exception:
            pass
        ENRICH_UI_ENABLED = False
    try:
        TARGET = await _select_extraction_target(PAGE) if PAGE is not None else None
    except Exception:
        TARGET = PAGE
    return {"status": "success", "execution_mode": EXECUTION_MODE}


@router.post("/ui/disable")
async def disable_ui(
    project_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _resolve_project_for_user(db, current_user, project_id)
    global ENRICH_UI_ENABLED
    ENRICH_UI_ENABLED = False
    if PAGE is not None:
        try:
            await PAGE.evaluate(
                "window._smartaiDisabled = true; if (window.smartAI_disableUI) window.smartAI_disableUI();"
            )
        except Exception:
            pass
    return {"status": "success", "ui_enabled": ENRICH_UI_ENABLED}


@router.post("/capture-dom-from-client")
async def capture_from_keyboard(
    _: CaptureRequest,
    db: Session = Depends(get_db),
    project_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
):
    _resolve_project_for_user(db, current_user, project_id)
    global PAGE, TARGET, CURRENT_PAGE_NAME, AUTOSCROLL_ENABLED
    try:
        if PAGE is None:
            raise HTTPException(status_code=500, detail="Cannot extract. No active page handle.")
        if hasattr(PAGE, "is_closed") and PAGE.is_closed():
            raise HTTPException(status_code=500, detail="Cannot extract. Page is already closed.")
        if not CURRENT_PAGE_NAME:
            CURRENT_PAGE_NAME = "page"

        page_name = CURRENT_PAGE_NAME
        _safe_log(f"[INFO] Enrichment triggered for: {page_name}")

        await _refresh_target("capture-start")
        await __snapshot_if_blank(PAGE, "before-capture")

        project = _resolve_project_for_user(db, current_user, project_id)
        project_paths = _ensure_project_structure(project)
        src_directory = Path(project_paths["src_dir"])
        projectChromaPath = project_paths["chroma_path"]
        with _activate_project_storage(db, org_id=current_user.organization_id):
            result = await _run_enrichment_for(
                PAGE,
                TARGET,
                AUTOSCROLL_ENABLED,
                EXECUTION_MODE,
                src_directory,
                projectChromaPath,
                page_name,
            )
        await __snapshot_if_blank(PAGE, "after-capture")
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
            status_code=500, detail=f"Capture failed: {e.__class__.__name__}: {e}"
        )


@router.get("/current-url")
async def current_url(
    project_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _resolve_project_for_user(db, current_user, project_id)
    try:
        target_url = None
        if TARGET is not None:
            try:
                target_url = TARGET.url
            except Exception:
                target_url = None
        return {"page_url": getattr(PAGE, "url", None), "target_url": target_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/manual/browser-status")
async def manual_browser_status(current_user: User = Depends(get_current_user)):
    return {"closed": MANUAL_BROWSER_CLOSED}


@router.get("/manual/latest-result")
async def manual_latest_result(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = get_user_project(db, project_id, current_user)
    project_paths = _ensure_project_structure(project)
    meta_dir = Path(project_paths["src_dir"]) / "metadata"
    page_name = (CURRENT_PAGE_NAME or "").strip()
    results: list[dict] = []

    def _safe_load(path: Path) -> list[dict]:
        try:
            data = json.loads(path.read_text(encoding="utf-8") or "[]")
            if isinstance(data, list):
                return [r for r in data if isinstance(r, dict)]
        except Exception:
            return []
        return []

    def _page_name_from_filename(path: Path) -> str:
        name = path.stem.replace("after_enrichment_", "", 1)
        base = name.split("__", 1)[0]
        return _canonical(base) or base

    # Prefer per-page OCR-only files if available
    try:
        per_page_files = [
            p
            for p in meta_dir.glob("after_enrichment_*.json")
            if p.is_file() and p.name != "after_enrichment.json"
        ]
    except Exception:
        per_page_files = []

    if per_page_files:
        for path in sorted(per_page_files, key=lambda p: p.stat().st_mtime, reverse=True):
            records = _safe_load(path)
            if records:
                detected_name = (records[0].get("page_name") or "").strip()
            else:
                detected_name = ""
            resolved_name = _canonical(detected_name) if detected_name else _page_name_from_filename(path)
            results.append(
                {
                    "page_name": resolved_name,
                    "count": len(records),
                    "file": str(path),
                }
            )
    else:
        # Fallback to aggregate file if per-page files are missing
        aggregate_path = meta_dir / "after_enrichment.json"
        if aggregate_path.exists():
            aggregate = _safe_load(aggregate_path)
            grouped: Dict[str, list[dict]] = {}
            for rec in aggregate:
                rec_name = _canonical((rec.get("page_name") or "").strip()) or "page"
                grouped.setdefault(rec_name, []).append(rec)
            for name, items in grouped.items():
                results.append({"page_name": name, "count": len(items), "file": None})

    # Determine current page details (if any)
    current_match = None
    if page_name:
        canonical = _canonical(page_name)
        for item in results:
            if _canonical(item.get("page_name", "")) == canonical:
                current_match = item
                break
    if current_match is None and results:
        current_match = results[0]

    return {
        "status": "success",
        "page_name": page_name,
        "count": current_match.get("count", 0) if current_match else 0,
        "file": current_match.get("file") if current_match else None,
        "results": results,
        "total_count": sum(item.get("count", 0) or 0 for item in results),
    }


@router.on_event("shutdown")
async def shutdown_browser():
    await _clean_restart()


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
