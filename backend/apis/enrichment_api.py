
# enrichment_api.py
from __future__ import annotations

import os
import ast
import json
import re
import pprint
import asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union, Tuple
from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from chromadb import PersistentClient
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
from utils.file_utils import build_standard_metadata

# -----------------------------------------------------------------------------
# Router & DB
# -----------------------------------------------------------------------------
router = APIRouter()
client = PersistentClient(path=os.environ.get("SMARTAI_CHROMA_PATH", "./data/chroma_db"))
collection = client.get_or_create_collection(
    name=os.environ.get("SMARTAI_CHROMA_COLLECTION", "element_metadata")
)

# -----------------------------------------------------------------------------
# Runtime state
# -----------------------------------------------------------------------------
PLAYWRIGHT = None
BROWSER: Optional[Browser] = None
PAGE: Optional[Page] = None
TARGET: Optional[Union[Page, Frame]] = None  # chosen Page/Frame for extraction
CURRENT_PAGE_NAME: str = "unknown_page"

# -----------------------------------------------------------------------------
# Config
# -----------------------------------------------------------------------------
SRC_DIR = Path(os.environ.get("SMARTAI_SRC_DIR", "generated_runs/src"))
PAGES_DIR = Path(os.environ.get("SMARTAI_PAGES_DIR", str(SRC_DIR / "pages")))
META_DIR = Path(os.environ.get("SMARTAI_META_DIR", str(SRC_DIR / "metadata")))
PY_FILE_GLOB = os.environ.get("SMARTAI_PAGES_GLOB", "*.py")

# Regex (kept for internal helpers only)
PAGE_METHOD_RE = re.compile(
    os.environ.get(
        "SMARTAI_PAGE_METHOD_RE",
        r"(?i)(^page[_\-\s])|([_\-\s]page$)|(_page$)|(^.*\bpage\b.*$)",
    )
)
PAGE_CLASS_RE = re.compile(os.environ.get("SMARTAI_PAGE_CLASS_RE", r"(?i)(Page|Screen|View)$"))

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
    wait_until: str = "auto"           # safer default across SPAs/sites
    user_agent: Optional[str] = None
    extra_http_headers: Optional[Dict[str, str]] = None
    http_username: Optional[str] = None
    http_password: Optional[str] = None
    nav_timeout_ms: int = 60000        # 60s navigation timeout


class CaptureRequest(BaseModel):
    pass


class PageNameSetRequest(BaseModel):
    page_name: str


# -----------------------------------------------------------------------------
# UI JS (Top-only modal + key bridge from iframes) — minimalist dropdown
# -----------------------------------------------------------------------------
UI_KEYBRIDGE_JS = r"""
(() => {
  // Run only in iframes, never in the top window (prevents double-toggle).
  if (window === window.top) return;
  if (window._smartaiKeyBridgeInstalled) return;
  window._smartaiKeyBridgeInstalled = true;

  window.addEventListener('keydown', function(e){
    if (e.altKey && (e.key === 'q' || e.key === 'Q')) {
      try { window.top.postMessage({ __smartai: 'TOGGLE_MODAL' }, '*'); } catch(e) {}
    }
  }, true);
})();
"""

UI_MODAL_TOP_JS = r"""
(() => {
  if (window !== window.top) return;
  if (window._smartaiTopInstalled) return;
  window._smartaiTopInstalled = true;

  function ensureModal() {
    if (document.getElementById('ocrModal')) return;
    const modal = document.createElement('div');
    modal.innerHTML = `
      <div id="ocrModal" style="position:fixed;top:40%;left:50%;
        transform:translate(-50%,-50%);background:white;padding:16px;border:2px solid black;
        z-index:2147483647;display:none;min-width:360px;font-family:Arial,sans-serif;">
        <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;">
          <label style="min-width:70px;">Page:</label>
          <select id="pageDropdown" style="padding:6px;min-width:220px;"></select>
          <button id="smartAI_refresh_pages">Refresh</button>
        </div>
        <div style="margin-top:10px;display:flex;gap:8px;flex-wrap:wrap;">
          <button id="smartAI_enrich_btn">Enrich</button>
          <button id="smartAI_close_btn">Close</button>
        </div>
        <div id="enrichmentMessageBox" style="margin-top:10px;font-weight:bold;color:green;"></div>
        <div style="margin-top:8px;color:#666;font-size:12px;">Tip: press <b>Alt+Q</b> to open/close</div>
      </div>
    `;
    document.body.appendChild(modal);

    async function triggerEnrichment() {
      const dropdown = document.getElementById('pageDropdown');
      const msg = document.getElementById('enrichmentMessageBox');

      const chosen = (dropdown && dropdown.value || '').trim();
      if (!chosen) { msg.textContent = "❌ No page found for this image."; msg.style.color = "red"; return; }

      msg.textContent = "⏳ Enrichment in progress…"; msg.style.color = "blue";
      try {
        const resultStr = await window.smartAI_enrich(chosen);
        const result = JSON.parse(resultStr || '{}');
        if (result.status !== "success") { msg.textContent = "❌ " + (result.error || "Enrichment failed"); msg.style.color = "red"; }
        else if (!result.count) { msg.textContent = "❌ Enrichment succeeded but no elements matched."; msg.style.color = "red"; }
        else { msg.textContent = `✅ Enriched ${result.count} elements`; msg.style.color = "green"; }
      } catch (err) { msg.textContent = "❌ Error: " + (err && err.message ? err.message : err); msg.style.color = "red"; }
    }

    document.getElementById('smartAI_enrich_btn').onclick = triggerEnrichment;
    document.getElementById('smartAI_close_btn').onclick = () => { document.getElementById('ocrModal').style.display = 'none'; };
    document.getElementById('smartAI_refresh_pages').onclick = populateDropdown;
  }

  async function populateDropdown() {
    const dropdown = document.getElementById('pageDropdown');
    const msg = document.getElementById('enrichmentMessageBox');
    if (!dropdown) return;
    dropdown.innerHTML = "";
    try {
      const respStr = await window.smartAI_availablePages();
      const data = JSON.parse(respStr || '{}');
      const pages = (data && data.status === 'success' && Array.isArray(data.pages)) ? data.pages : [];
      if (!pages.length) { msg.textContent = "⚠️ No extracted image pages found."; msg.style.color = "orange"; }
      pages.forEach(p => { const opt = document.createElement('option'); opt.value = p; opt.innerText = p; dropdown.appendChild(opt); });
    } catch(e) { msg.textContent = "❌ Failed to load pages."; msg.style.color = "red"; }
  }

  function toggleModal() {
    // Debounce to prevent "blinking" when multiple handlers fire close together.
    if (!window.__smartai_lastToggleTs) window.__smartai_lastToggleTs = 0;
    const now = Date.now();
    if (now - window.__smartai_lastToggleTs < 200) return;
    window.__smartai_lastToggleTs = now;

    ensureModal();
    const modal = document.getElementById('ocrModal');
    if (!modal) return;
    if (modal.style.display === 'none') {
      modal.style.display = 'block';
      populateDropdown();
    } else {
      modal.style.display = 'none';
    }
  }

  window.addEventListener('message', function(ev){
    const data = (ev && ev.data) || {};
    if (data && data.__smartai === 'TOGGLE_MODAL') toggleModal();
  });

  window.addEventListener('keydown', function(e){
    if (e.altKey && (e.key === 'q' || e.key === 'Q')) toggleModal();
  }, true);

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', ensureModal);
  else ensureModal();
})();
"""

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def _norm_text(s: Optional[str]) -> str:
    if not s:
        return ""
    return (
        " ".join(s.replace("\n", " ").replace("\r", " ").strip().strip(":").split())
        .lower()
    )

def _ensure_dirs() -> Dict[str, Path]:
    paths = {"debug": SRC_DIR / "ocr-dom-metadata", "meta": META_DIR}
    for p in paths.values():
        p.mkdir(parents=True, exist_ok=True)
    return paths

def _canonical(name: str) -> str:
    """
    Canonical display name:
      - normalize (snake-case, lowercase via normalize_page_name)
      - drop leading/trailing 'page|screen|view' even when concatenated (e.g., 'RedBusPage' -> 'redbus')
      - collapse separators and trim
    """
    n = normalize_page_name(name or "")
    if not n:
        return n
    n = re.sub(r'(?i)^(page|screen|view)+', '', n)
    n = re.sub(r'(?i)(page|screen|view)+$', '', n)
    n = re.sub(r'[_\-\s]+', '_', n).strip('_')
    return n

def _ocr_name_counts() -> Dict[str, int]:
    """
    Return {canonical_page_name: count} from Chroma metadatas (OCR/imports/enriched).
    Only uses 'page_name' fields and canonicalizes them.
    """
    counts: Dict[str, int] = {}
    try:
        recs = collection.get() or {}
        for m in (recs.get("metadatas") or []):
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

def _sorted_all_image_pages() -> List[str]:
    """
    All image-extracted page names:
      - Take every canonical 'page_name' from Chroma
      - Remove obvious noise (unknown/basepage)
      - Sort by: current page first (if present) → frequency desc → alphabetical
    """
    counts = _ocr_name_counts()
    if not counts:
        return []

    # filter out noise
    noise = {"unknown", "unknown_page", "basepage"}
    for k in list(counts.keys()):
        if k in noise:
            counts.pop(k, None)

    if not counts:
        return []

    cur = _canonical(CURRENT_PAGE_NAME or "")
    names = list(counts.keys())

    def sort_key(n: str):
        return (
            0 if (cur and n == cur) else 1,  # current page first
            -counts[n],                      # higher frequency first
            n                                # then alphabetical
        )

    names.sort(key=sort_key)
    return names

# -----------------------------------------------------------------------------
# Navigation & target picking
# -----------------------------------------------------------------------------
async def _smart_navigate(
    page: Page, raw_url: str, wait_until: str = "auto", timeout_ms: int = 60000
):
    """
    Robust navigation with https→http and adaptive waits.
    """
    def _with_scheme(u: str, scheme: str) -> str:
        p = urlparse(u)
        return f"{scheme}://{u}" if not p.scheme else u

    strategies = (
        ["networkidle", "load", "domcontentloaded", "commit"]
        if (wait_until or "").lower() == "auto"
        else [wait_until]
    )

    for scheme in ("https", "http"):
        url = _with_scheme(raw_url, scheme)
        for wu in strategies:
            try:
                resp = await page.goto(url, wait_until=wu, timeout=timeout_ms)
                try:
                    await page.wait_for_load_state("domcontentloaded", timeout=min(10000, timeout_ms))
                except Exception:
                    pass
                try:
                    await page.wait_for_selector("body", state="attached", timeout=5000)
                except Exception:
                    pass
                return resp
            except PWTimeoutError:
                continue
            except Exception:
                break

    try:
        _ = await page.goto(_with_scheme(raw_url, "https"), timeout=timeout_ms)
    except Exception:
        pass
    return None

async def _clean_restart():
    global PLAYWRIGHT, BROWSER, PAGE, TARGET
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
    PLAYWRIGHT = None
    BROWSER = None
    PAGE = None
    TARGET = None

async def _select_extraction_target(page: Page) -> Union[Page, Frame]:
    """
    Pick the most 'interactive' frame automatically.
    """
    try:
        await page.wait_for_selector("iframe", timeout=3000)
    except Exception:
        pass

    candidates: List[Union[Page, Frame]] = []
    if page.main_frame:
        candidates.append(page.main_frame)
    candidates.extend([f for f in page.frames if f is not page.main_frame])

    best: Union[Page, Frame] = page
    best_score = -1
    for fr in candidates:
        try:
            has_dom = await fr.evaluate("Boolean(document && document.body)")
            if not has_dom:
                continue
            text_len = await fr.evaluate("document.body?.innerText?.length || 0")
            interactive = await fr.evaluate(
                "document.querySelectorAll('input,select,textarea,button,a,[role],[contenteditable=\"true\"]').length"
            )
            url = ""
            try:
                url = fr.url or ""
            except Exception:
                pass
            bonus = 30 if re.search(r"(demo|example|playground|sample|demos?|resources)", url, re.I) else 0
            score = interactive * 10 + int(text_len) + bonus
            if score > best_score:
                best_score = score
                best = fr
        except Exception:
            continue
    return best

# -----------------------------------------------------------------------------
# Discovery (dropdown)
# -----------------------------------------------------------------------------
def _available_pages_for_dropdown() -> List[str]:
    """
    Return **all** OCR/imported page names (one per image), cleaned & sorted.
    This ensures if you imported 2 images, you see 2 names, etc.
    """
    return _sorted_all_image_pages()

# -----------------------------------------------------------------------------
# Enrichment core
# -----------------------------------------------------------------------------
async def _run_enrichment_for(page_name: str) -> Dict[str, Any]:
    global PAGE, TARGET, collection, CURRENT_PAGE_NAME
    if PAGE is None:
        raise HTTPException(status_code=500, detail="❌ Cannot extract. No active page handle.")
    if hasattr(PAGE, "is_closed") and PAGE.is_closed():
        raise HTTPException(status_code=500, detail="❌ Cannot extract. Page is already closed.")
    if collection is None:
        raise HTTPException(status_code=500, detail="❌ Chroma collection is not initialized.")

    CURRENT_PAGE_NAME = _canonical(page_name)
    TARGET = await _select_extraction_target(PAGE)
    paths = _ensure_dirs()

    dom_data = await extract_dom_metadata(TARGET, CURRENT_PAGE_NAME) or []
    try:
        _ = len(dom_data)
    except Exception:
        dom_data = list(dom_data)

    for rec in dom_data:
        try:
            label = rec.get("label") or rec.get("aria_label") or rec.get("text")
            placeholder = rec.get("placeholder")
            role = rec.get("role")
            tag = rec.get("tag")
            rec["_norm"] = {
                "label": _norm_text(label),
                "placeholder": _norm_text(placeholder),
                "role": (role or "").lower(),
                "tag": (tag or "").lower(),
            }
        except Exception:
            pass

    chroma_resp = collection.get(where={"page_name": CURRENT_PAGE_NAME}) or {}
    ocr_data = chroma_resp.get("metadatas", []) or []

    (paths["debug"] / f"dom_data_{CURRENT_PAGE_NAME}.txt").write_text(
        pprint.pformat(dom_data), encoding="utf-8"
    )
    (paths["debug"] / f"ocr_data_{CURRENT_PAGE_NAME}.txt").write_text(
        pprint.pformat(ocr_data), encoding="utf-8"
    )

    updated_matches = match_and_update(ocr_data, dom_data, collection)
    (paths["debug"] / f"after_match_and_update_{CURRENT_PAGE_NAME}.txt").write_text(
        pprint.pformat(updated_matches), encoding="utf-8"
    )

    standardized_matches = [
        build_standard_metadata(
            m, CURRENT_PAGE_NAME, image_path="", source_url=getattr(PAGE, "url", None)
        )
        for m in (updated_matches or [])
    ]
    set_last_match_result(standardized_matches)

    (paths["meta"] / f"after_enrichment_{CURRENT_PAGE_NAME}.json").write_text(
        json.dumps(standardized_matches, indent=2), encoding="utf-8"
    )
    chroma_all = collection.get() or {}
    chroma_all_metadatas = chroma_all.get("metadatas", []) or []
    (paths["meta"] / "after_enrichment.json").write_text(
        json.dumps(chroma_all_metadatas, indent=2), encoding="utf-8"
    )

    return {
        "status": "success",
        "message": f"Enriched {len(standardized_matches)} elements for page: {CURRENT_PAGE_NAME}",
        "matched_data": standardized_matches,
        "count": len(standardized_matches),
    }

# -----------------------------------------------------------------------------
# Routes
# -----------------------------------------------------------------------------
@router.post("/launch-browser")
async def launch_browser(req: LaunchRequest):
    global PLAYWRIGHT, BROWSER, PAGE, TARGET, CURRENT_PAGE_NAME
    try:
        await _clean_restart()

        PLAYWRIGHT = await async_playwright().start()
        BROWSER = await PLAYWRIGHT.chromium.launch(
            headless=req.headless, slow_mo=req.slow_mo
        )

        context_kwargs: Dict[str, Any] = {
            "ignore_https_errors": req.ignore_https_errors,
            "viewport": {"width": req.viewport_width, "height": req.viewport_height},
            "bypass_csp": True,  # ensure injected UI works on strict CSP sites
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

        context = await BROWSER.new_context(**context_kwargs)
        PAGE = await context.new_page()

        # Bindings used by the modal
        async def _binding_enrich(source, page_name: str):
            try:
                res = await _run_enrichment_for(page_name)
                return json.dumps(res)
            except HTTPException as he:
                return json.dumps({"status": "fail", "error": he.detail})
            except Exception as e:
                return json.dumps({"status": "fail", "error": str(e)})

        async def _binding_available_pages(source):
            try:
                pages = _available_pages_for_dropdown()
                return json.dumps({"status": "success", "pages": pages})
            except Exception as e:
                return json.dumps({"status": "fail", "error": str(e), "pages": []})

        await PAGE.expose_binding("smartAI_enrich", _binding_enrich)
        await PAGE.expose_binding("smartAI_availablePages", _binding_available_pages)

        # Scripts for ALL future documents/frames
        await PAGE.add_init_script(UI_KEYBRIDGE_JS)  # iframes forward Alt+Q to top
        await PAGE.add_init_script(UI_MODAL_TOP_JS)  # modal renders only on top

        # Saner timeouts
        try:
            PAGE.set_default_timeout(req.nav_timeout_ms)
            PAGE.set_default_navigation_timeout(req.nav_timeout_ms)
        except Exception:
            pass

        # Navigate robustly
        await _smart_navigate(
            PAGE,
            req.url,
            wait_until=req.wait_until if req.wait_until else "auto",
            timeout_ms=req.nav_timeout_ms,
        )

        # Ensure the modal exists now
        try:
            await PAGE.evaluate(UI_MODAL_TOP_JS)
        except Exception:
            pass

        # Choose best extraction target (main frame or interactive iframe)
        try:
            TARGET = await _select_extraction_target(PAGE)
        except Exception:
            TARGET = PAGE

        return {
            "status": "success",
            "message": f"✅ Browser launched and navigated to {req.url}. Press Alt+Q to open the enrichment modal.",
        }

    except Exception as e:
        import traceback

        traceback.print_exc()
        await _clean_restart()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/set-current-page-name")
async def set_page_name(req: PageNameSetRequest):
    global CURRENT_PAGE_NAME
    CURRENT_PAGE_NAME = _canonical(req.page_name)
    print(f"[INFO] ✅ Page name set to: {CURRENT_PAGE_NAME}")
    return {"status": "success", "page_name": CURRENT_PAGE_NAME}


@router.post("/capture-dom-from-client")
async def capture_from_keyboard(_: CaptureRequest):
    global PAGE, TARGET, CURRENT_PAGE_NAME, collection
    try:
        if PAGE is None:
            raise HTTPException(status_code=500, detail="❌ Cannot extract. No active page handle.")
        if hasattr(PAGE, "is_closed") and PAGE.is_closed():
            raise HTTPException(status_code=500, detail="❌ Cannot extract. Page is already closed.")
        if not CURRENT_PAGE_NAME:
            raise HTTPException(status_code=400, detail="❌ No current page name set.")
        if collection is None:
            raise HTTPException(status_code=500, detail="❌ Chroma collection is not initialized.")

        page_name = CURRENT_PAGE_NAME
        print(f"[INFO] Enrichment triggered for: {page_name}")

        # Re-evaluate best target each time (user may have navigated)
        TARGET = await _select_extraction_target(PAGE)

        paths = _ensure_dirs()
        dom_data = await extract_dom_metadata(TARGET, page_name) or []
        try:
            _ = len(dom_data)
        except Exception:
            dom_data = list(dom_data)

        for rec in dom_data:
            try:
                label = rec.get("label") or rec.get("aria_label") or rec.get("text")
                placeholder = rec.get("placeholder")
                role = rec.get("role")
                tag = rec.get("tag")
                rec["_norm"] = {
                    "label": _norm_text(label),
                    "placeholder": _norm_text(placeholder),
                    "role": (role or "").lower(),
                    "tag": (tag or "").lower(),
                }
            except Exception:
                pass

        chroma_resp = collection.get(where={"page_name": page_name}) or {}
        ocr_data = chroma_resp.get("metadatas", []) or []

        (paths["debug"] / f"dom_data_{page_name}.txt").write_text(
            pprint.pformat(dom_data), encoding="utf-8"
        )
        (paths["debug"] / f"ocr_data_{page_name}.txt").write_text(
            pprint.pformat(ocr_data), encoding="utf-8"
        )

        updated_matches = match_and_update(ocr_data, dom_data, collection)
        (paths["debug"] / f"after_match_and_update_{page_name}.txt").write_text(
            pprint.pformat(updated_matches), encoding="utf-8"
        )

        standardized_matches = [
            build_standard_metadata(
                m, page_name, image_path="", source_url=getattr(PAGE, "url", None)
            )
            for m in (updated_matches or [])
        ]
        (paths["debug"] / f"standardized_matches_{page_name}.txt").write_text(
            pprint.pformat(standardized_matches), encoding="utf-8"
        )

        set_last_match_result(standardized_matches)

        (paths["meta"] / f"after_enrichment_{page_name}.json").write_text(
            json.dumps(standardized_matches, indent=2), encoding="utf-8"
        )
        chroma_all = collection.get() or {}
        chroma_all_metadatas = chroma_all.get("metadatas", []) or []
        (paths["meta"] / "after_enrichment.json").write_text(
            json.dumps(chroma_all_metadatas, indent=2), encoding="utf-8"
        )

        return {
            "status": "success",
            "message": f"[Keyboard Trigger] Enriched {len(standardized_matches)} elements for page: {page_name}",
            "matched_data": standardized_matches,
            "count": len(standardized_matches),
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(
            status_code=500, detail=f"❌ Capture failed: {e.__class__.__name__}: {e}"
        )


@router.get("/available-pages")
async def list_page_names():
    try:
        return {"status": "success", "pages": _available_pages_for_dropdown()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/current-url")
async def current_url():
    try:
        target_url = None
        if TARGET is not None:
            try:
                target_url = TARGET.url  # Frame and Page both expose .url
            except Exception:
                target_url = None
        return {"page_url": getattr(PAGE, "url", None), "target_url": target_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.on_event("shutdown")
async def shutdown_browser():
    await _clean_restart()


@router.get("/latest-match-result")
async def get_latest_match_result():
    try:
        records = collection.get()
        matched = [
            r for r in records.get("metadatas", []) if r.get("dom_matched") is True
        ]
        return {"status": "success", "matched_elements": matched, "count": len(matched)}
    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reset-enrichment/{page_name}")
async def reset_enrichment_api(page_name: str):
    reset_enriched(page_name)
    return {"success": True, "message": f"Enrichment reset for {page_name}"}


__all__ = ["router"]
