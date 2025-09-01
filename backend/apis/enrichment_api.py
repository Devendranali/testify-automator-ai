# # enrichment_api.py

# from utils.enrichment_status import reset_enriched
# from fastapi import APIRouter
# from fastapi import APIRouter, HTTPException
# from pydantic import BaseModel
# from chromadb import PersistentClient
# from logic.manual_capture_mode import extract_dom_metadata, match_and_update, get_last_match_result, set_last_match_result
# from utils.match_utils import normalize_page_name
# from utils.file_utils import build_standard_metadata
# from playwright.async_api import async_playwright, Page, Browser
# import json
# import os
# from pathlib import Path
# import pprint
# import time
# import asyncio
# from typing import Any, Dict, Optional

# router = APIRouter()
# client = PersistentClient(path="./data/chroma_db")
# collection = client.get_or_create_collection(name="element_metadata")

# BROWSER: Browser = None
# PAGE: Page = None
# PLAYWRIGHT = None
# CURRENT_PAGE_NAME: str = "unknown_page"
 
# class LaunchRequest(BaseModel):
#     url: str
# class CaptureRequest(BaseModel):
#     pass
# class PageNameSetRequest(BaseModel):
#     page_name: str
 
# # async def send_enrichment_requests(page_name: str):
# #     from httpx import AsyncClient
# #     async with AsyncClient() as client:
# #         try:
# #             await client.post("http://localhost:8001/set-current-page-name", json={"page_name": page_name})
# #             print('[DEBUG] set global CURRENT_PAGE_NAME = ', CURRENT_PAGE_NAME, ' Going for capture_dom_from_client')
# #         except Exception as e:
# #             print(f"🔥Error from: await client.post('8001/set-current-page-name': {e}")
# #             return {"status": "fail", "error": "set-current-page-name failed"}
        
# #         try:
# #             resp = await client.post(f"http://localhost:8001/capture-dom-from-client", json={})
# #             resp.raise_for_status()
# #         except Exception as e:
# #             # Print the full exception so you see “404 Not Found” or “Connection refused”
# #             print(f"🔥🔥Error POSTing to /capture-dom-from-client: {e!r}")
# #             return {"status": "fail", "count": 0, "error": str(e)}


# #         # try:
# #         #     resp = await client.post("http://localhost:8001/capture-dom-from-client", json={})
# #         #     print('[DEBUG] capture_dom_from_client done. resp = ', resp, "Now trying to convert the data to json", sep='\n')
# #         # except Exception as e:
# #         #     print("🔥🔥Error from: await client.post('8001/capture-from-dom-client'", e)
# #         #     return {"status": "fail", "error": "capture-dom-from-client failed"}
        
# #         # 3) parse JSON
# #         return resp.json()

# #         json_data = None
# #         try:
# #             json_data = await resp.aread()
# #             decoded_json_data = json_data.decode("utf-8").strip()
# #             if not decoded_json_data or decoded_json_data in ["null", "undefined"]:
# #                 return {"status": "fail", "error": "Empty or invalid response"}
# #         except Exception as e:
# #             print(f"🔥🔥🔥Error from: await resp.aread(): {e}")
# #             return {"status": "fail", "error": f"Error reading response: {e}"}
        
# #         # print("[DEBUG] decoded_json_data:", decoded_json_data)
# #         try:
# #             return json.loads(decoded_json_data)
# #         except Exception as e:
# #             print("🔥🔥🔥🔥[ERROR] JSON parsing failed:", e)
# #             return {"status": "fail", "error": "Response parsing failed : {e}"}

# # async def send_enrichment_requests(page_name: str):
# #     from httpx import AsyncClient, HTTPStatusError

# #     BASE = "http://localhost:8001"  # ← make sure this matches your uvicorn port!

# #     async with AsyncClient(timeout=None) as client:
# #         # 1) set the page name
# #         try:
# #             r = await client.post(f"{BASE}/set-current-page-name", json={"page_name": page_name})
# #             r.raise_for_status()
# #         except Exception as e:
# #             print(f"🔥Error setting page name: {e!r}")
# #             return {"status": "fail", "count": 0, "error": str(e)}

# #         # 2) call enrichment endpoint
# #         try:
# #             time.sleep(5)
# #             resp = await client.post(f"{BASE}/capture-dom-from-client", json={})
# #             resp.raise_for_status()
# #         except HTTPStatusError as e:
# #             # e.response.status_code & e.response.text will show you 404 or other codes
# #             print(f"🔥HTTP error {e.response.status_code}: {e.response.text!r}")
# #             return {"status": "fail", "count": 0, "error": f"HTTP {e.response.status_code}"}
# #         except Exception as e:
# #             print(f"🔥Network/connection error: {e!r}")
# #             return {"status": "fail", "count": 0, "error": str(e)}

# #         # 3) Success → parse JSON
# #         try:
# #             return resp.json()
# #         except Exception as e:
# #             print(f"🔥JSON parse error: {e!r}")
# #             return {"status": "fail", "count": 0, "error": "invalid JSON"}

# # async def send_enrichment_requests(
# #     page_name: str,
# #     target_url: str = "https://the-internet.herokuapp.com/login", 
# #     base: str = "http://localhost:8001",
# #     wait_seconds: float = 3.0,
# #     retries: int = 3,
# # ) -> Dict[str, Any]:
# #     """
# #     Ask the enrichment service to navigate to target_url (http/https),
# #     set the page name, and capture DOM metadata.
# #     Works with HTTPS sites like https://the-internet.herokuapp.com/login.
# #     """
# #     from httpx import AsyncClient, HTTPStatusError, RequestError

# #     # Ensure the URL has a scheme
# #     if not (target_url.startswith("http://") or target_url.startswith("https://")):
# #         target_url = "https://" + target_url  # default to https if not provided

# #     async with AsyncClient(timeout=None) as client:
# #         # 0) (optional) Launch the browser and navigate to the target URL.
# #         # If your backend already has the page open, this will just succeed/NO-OP.
# #         try:
# #             r_launch = await client.post(
# #                 f"{base}/launch-browser",
# #                 json={
# #                     "url": target_url,
# #                     "page_name": page_name,
# #                     "headless": False,
# #                     "ignore_https_errors": True,   # <-- important for HTTPS sites
# #                     "wait_until": "networkidle",    # backend can ignore if unsupported
# #                 },
# #             )
# #             # Some setups won't have /launch-browser; don't fail hard on 404.
# #             if r_launch.status_code not in (200, 404):
# #                 r_launch.raise_for_status()
# #         except RequestError as e:
# #             # It's OK to continue even if /launch-browser doesn't exist;
# #             # but if it's something other than a 404 we surface it.
# #             return {"status": "fail", "count": 0, "error": f"launch error: {e!r}"}

# #         # 1) Set the page name (needed by your matching logic)
# #         try:
# #             r = await client.post(
# #                 f"{base}/set-current-page-name",
# #                 json={"page_name": page_name},
# #             )
# #             r.raise_for_status()
# #         except (HTTPStatusError, RequestError) as e:
# #             return {"status": "fail", "count": 0, "error": f"set page name: {e!r}"}

# #         # 2) Give the backend a moment to be ready
# #         await asyncio.sleep(wait_seconds)

# #         # 3) Try capture a few times (helps when HTTPS pages take longer)
# #         last_err: Optional[str] = None
# #         for attempt in range(1, retries + 1):
# #             try:
# #                 resp = await client.post(f"{base}/capture-dom-from-client", json={"page_name": page_name})
# #                 resp.raise_for_status()
# #                 try:
# #                     data = resp.json()
# #                     # If your backend stores the latest match and expects a separate fetch:
# #                     # If data seems empty, try to poll /latest-match-result
# #                     if not data or (isinstance(data, dict) and data.get("count", 0) == 0):
# #                         # brief poll for a ready result
# #                         for _ in range(10):
# #                             await asyncio.sleep(0.5)
# #                             latest = await client.get(f"{base}/latest-match-result")
# #                             if latest.status_code == 200:
# #                                 jd = latest.json()
# #                                 if jd:
# #                                     return jd
# #                         # fall back to whatever we got
# #                     return data
# #                 except Exception as e:
# #                     return {"status": "fail", "count": 0, "error": f"invalid JSON: {e!r}"}
# #             except HTTPStatusError as e:
# #                 last_err = f"HTTP {getattr(e.response,'status_code', '??')}: {getattr(e.response,'text','')!r}"
# #             except RequestError as e:
# #                 last_err = f"network error: {e!r}"

# #             # backoff before next try
# #             await asyncio.sleep(min(2 * attempt, 6))


# #         return {"status": "fail", "count": 0, "error": last_err or "unknown error"}
# import asyncio
# import re
# from typing import Any, Dict, Optional

# URL_RE = re.compile(r'(https?://[^\s"\'\)]+)', re.I)

# async def send_enrichment_requests(
#     page_name: str,
#     target_url: Optional[str] = None,          # <- now optional (backward compatible)
#     base: str = "http://localhost:8001",
#     wait_seconds: float = 3.0,
#     retries: int = 3,
#     story: Optional[str] = None,               # <- optional: we can auto-extract URL from a user story
# ) -> Dict[str, Any]:
#     """
#     Ask the enrichment service to set the page name and capture DOM metadata.

#     Behavior:
#       - If target_url is provided: try to launch/navigate via /launch-browser, then capture.
#       - Else if story is provided: extract the first https? URL from the story and use it.
#       - Else: skip launch (assumes your backend has already opened the right page),
#               still sets page name and captures DOM.
#       - If backend exposes /current-url and target_url is still None, we'll try to use that.

#     Works with http/https targets and keeps HTTPS errors ignored when launching.
#     """
#     from httpx import AsyncClient, HTTPStatusError, RequestError

#     # Resolve target_url if not passed
#     if not target_url and story:
#         m = URL_RE.search(story)
#         if m:
#             target_url = m.group(1).rstrip(".,);")

#     async with AsyncClient(timeout=None) as client:
#         # If still no target_url, try asking the backend (optional endpoint)
#         if not target_url:
#             try:
#                 r_cur = await client.get(f"{base}/current-url")
#                 if r_cur.status_code == 200:
#                     jd = r_cur.json()
#                     if isinstance(jd, dict) and jd.get("url"):
#                         target_url = jd["url"]
#             except Exception:
#                 # It's fine if /current-url doesn't exist
#                 pass

#         # Normalize scheme if we got a URL
#         if target_url and not (target_url.startswith("http://") or target_url.startswith("https://")):
#             target_url = "https://" + target_url  # default to https if scheme missing

#         # 0) Launch & navigate only if we have a URL; otherwise skip this step
#         if target_url:
#             try:
#                 r_launch = await client.post(
#                     f"{base}/launch-browser",
#                     json={
#                         "url": target_url,
#                         "page_name": page_name,
#                         "headless": False,
#                         "ignore_https_errors": True,
#                         "wait_until": "networkidle",
#                     },
#                 )
#                 # Accept 200 or 404 (some servers don't implement /launch-browser)
#                 if r_launch.status_code not in (200, 404):
#                     r_launch.raise_for_status()
#             except RequestError as e:
#                 # Non-fatal: you may still want to proceed to set page name and capture
#                 # if your page is already open on the backend.
#                 # Return early if you prefer strict failure on launch.
#                 return {"status": "fail", "count": 0, "error": f"launch error: {e!r}"}

#         # 1) Set the page name (your matcher relies on this)
#         try:
#             r = await client.post(
#                 f"{base}/set-current-page-name",
#                 json={"page_name": page_name},
#             )
#             r.raise_for_status()
#         except (HTTPStatusError, RequestError) as e:
#             return {"status": "fail", "count": 0, "error": f"set page name: {e!r}"}

#         # 2) Let the backend settle
#         await asyncio.sleep(wait_seconds)

#         # 3) Capture with retries
#         last_err: Optional[str] = None
#         for attempt in range(1, retries + 1):
#             try:
#                 resp = await client.post(
#                     f"{base}/capture-dom-from-client",
#                     json={"page_name": page_name}
#                 )
#                 resp.raise_for_status()
#                 try:
#                     data = resp.json()
#                     # Optionally poll a "latest" endpoint if capture returns empty
#                     if not data or (isinstance(data, dict) and data.get("count", 0) == 0):
#                         for _ in range(10):
#                             await asyncio.sleep(0.5)
#                             latest = await client.get(f"{base}/latest-match-result")
#                             if latest.status_code == 200:
#                                 jd = latest.json()
#                                 if jd:
#                                     return jd
#                     return data
#                 except Exception as e:
#                     return {"status": "fail", "count": 0, "error": f"invalid JSON: {e!r}"}
#             except HTTPStatusError as e:
#                 sc = getattr(e.response, "status_code", "??")
#                 txt = getattr(e.response, "text", "")
#                 last_err = f"HTTP {sc}: {txt!r}"
#             except RequestError as e:
#                 last_err = f"network error: {e!r}"

#             # backoff
#             await asyncio.sleep(min(2 * attempt, 6))

#         return {"status": "fail", "count": 0, "error": last_err or "unknown error"}



# @router.post("/launch-browser")
# async def launch_browser(req: LaunchRequest):
#     global PLAYWRIGHT, BROWSER, PAGE
 
#     try:
#         PLAYWRIGHT = await async_playwright().start()
#         BROWSER = await PLAYWRIGHT.chromium.launch(headless=False, slow_mo=100)
#         PAGE = await BROWSER.new_page()
#         await PAGE.goto(req.url)

#         async def send_enrichment_wrapper(source, page_name):
#             print("[DEBUG] Triggering enrichment for:", page_name)
#             result = await send_enrichment_requests(page_name)
#             # print("[DEBUG] Got:", result.count," from send_enrichment_requests")
#             return json.dumps(result)

#         await PAGE.expose_binding("sendEnrichmentRequests", send_enrichment_wrapper)


#         await PAGE.evaluate("""
#             if (!window._ocrShortcutRegistered) {
#                 window._ocrShortcutRegistered = true;
#                 console.log('[SmartAI] Modal enrichment JS injected');

#                 const modal = document.createElement('div');
#                 modal.innerHTML = `
#                     <div id="ocrModal" style="position:fixed;top:40%;left:50%;transform:translate(-50%,-50%);background:white;padding:20px;border:2px solid black;z-index:9999;display:none;">
#                         <label>Enter Page Name:</label><br/>
#                         <select id="pageDropdown" style="margin:5px;padding:5px;width:250px;"></select><br/>
#                         <button onclick="triggerEnrichment()">Enrich</button>
#                         <button onclick="document.getElementById('ocrModal').style.display='none'">Close</button>
#                         <div id="enrichmentMessageBox" style="margin-top:10px;font-weight:bold;color:green;"></div>
#                     </div>
#                 `;
#                 document.body.appendChild(modal);

#                 async function loadAvailablePages() {
#                     try {
#                         const res = await fetch('http://localhost:8001/available-pages');
#                         const data = await res.json();
#                         const dropdown = document.getElementById('pageDropdown');
#                         dropdown.innerHTML = "";
#                         for (const page of data.pages) {
#                             const option = document.createElement("option");
#                             option.value = page;
#                             option.innerText = page;
#                             dropdown.appendChild(option);
#                         }
#                     } catch (err) {
#                         alert("❌ Failed to load available pages.");
#                     }
#                 }

                
#                 window.triggerEnrichment = async function() {
#                     const pageName = document.getElementById('pageDropdown').value;
#                     const msg = document.getElementById("enrichmentMessageBox")
#                     if (!pageName) {
#                         msg.innerText = "❌ Page name is required.";
#                         msg.style.color = "red";
#                         return;
#                     }
#                     msg.innerText = "⏳ Enrichment in progress…"
#                     msg.style.color   = "blue"
#                     msg.offsetHeight  // force repaint

#                     try {
#                         const resultStr = await window.sendEnrichmentRequests(pageName)
#                         const result    = JSON.parse(resultStr)
#                         console.log("✅ Matched:", result);

#                         if (result.status !== "success") {
#                         msg.innerText = `❌ Enrichment failed: ${result.error}`
#                         msg.style.color = "red"

#                         } else if (result.count === 0) {
#                         msg.innerText = "❌ Enrichment succeeded but no elements matched."
#                         msg.style.color = "red"

#                         } else {
#                         msg.innerText = `✅ Enriched ${result.count} elements successfully.`
#                         msg.style.color = "green"
#                         }

#                     } catch (err) {
#                         console.error("Enrichment Error:", err);
#                         msg.innerText = "❌ Enrichment Error: " + (err.message || err)
#                         msg.style.color = "red"
#                     }
#                 };

#                 document.addEventListener('keydown', function(e) {
#                     if (e.altKey && (e.key === 'q' || e.key === 'Q')) {
#                         const modal = document.getElementById('ocrModal');
#                         modal.style.display = 'block';
#                         loadAvailablePages();
#                     }
#                 });
#             }
#             """)
        
#         return {
#             "message": f"✅ Browser launched and navigated to {req.url}. Press Alt+E to enrich any page."
#         }

#     except Exception as e:
#         import traceback
#         traceback.print_exc()
#         raise HTTPException(status_code=500, detail=str(e))

# @router.post("/set-current-page-name")
# async def set_page_name(req: PageNameSetRequest):
#     global CURRENT_PAGE_NAME
#     CURRENT_PAGE_NAME = normalize_page_name(req.page_name)
#     print(f'"message": f"✅ Page name set to: {CURRENT_PAGE_NAME}"')
#     return
# from fastapi import HTTPException
# from pathlib import Path
# import json, pprint, traceback

# # Expect these to be provided elsewhere in your app:
# # PAGE: playwright.sync_api.Page or playwright.async_api.Page
# # CURRENT_PAGE_NAME: str
# # collection: Chroma collection (has .get and .upsert etc.)
# # extract_dom_metadata, match_and_update, build_standard_metadata, set_last_match_result

# def _norm_text(s: str) -> str:
#     if not s:
#         return ""
#     # normalize labels like "Subject:", " Message ", newlines, etc.
#     return " ".join(s.replace("\n", " ").replace("\r", " ").strip().strip(":").split()).lower()

# @router.post("/capture-dom-from-client")
# async def capture_from_keyboard(_: "CaptureRequest"):
#     global PAGE, CURRENT_PAGE_NAME, collection
#     try:
#         # -------- guards --------
#         if PAGE is None:
#             raise HTTPException(status_code=500, detail="❌ Cannot extract. No active page handle.")
#         if hasattr(PAGE, "is_closed") and PAGE.is_closed():
#             raise HTTPException(status_code=500, detail="❌ Cannot extract. Page is already closed.")
#         if not CURRENT_PAGE_NAME:
#             raise HTTPException(status_code=400, detail="❌ No current page name set.")
#         if collection is None:
#             raise HTTPException(status_code=500, detail="❌ Chroma collection is not initialized.")

#         page_name = CURRENT_PAGE_NAME
#         print(f"[INFO] Enrichment triggered for: {page_name}")

#         # -------- extract DOM --------
#         dom_data = await extract_dom_metadata(PAGE, page_name)  # should be iterable of elements/records
#         dom_count = 0
#         if dom_data is None:
#             dom_data = []
#         try:
#             dom_count = len(dom_data)  # works for list/tuple
#         except Exception:
#             # fallback for generators/iterables
#             dom_data = list(dom_data)
#             dom_count = len(dom_data)

#         print("[DEBUG] DOM elements extracted:", dom_count)

#         # Lightweight normalization preview (kept alongside raw for better matching later)
#         for rec in dom_data:
#             try:
#                 label = rec.get("label") or rec.get("aria_label") or rec.get("text")
#                 placeholder = rec.get("placeholder")
#                 role = rec.get("role")
#                 tag = rec.get("tag")
#                 rec["_norm"] = {
#                     "label": _norm_text(label),
#                     "placeholder": _norm_text(placeholder),
#                     "role": (role or "").lower(),
#                     "tag": (tag or "").lower(),
#                 }
#             except Exception:
#                 # keep going; don't let a single bad node kill the batch
#                 pass

#         # -------- fetch OCR metadata for this page --------
#         # ensure get() returns dict with "metadatas"
#         chroma_resp = collection.get(where={"page_name": page_name}) or {}
#         ocr_data = chroma_resp.get("metadatas", []) or []

#         # -------- debug dumps --------
#         debug_metadata_dir = Path("generated_runs") / "src" / "ocr-dom-metadata"
#         debug_metadata_dir.mkdir(parents=True, exist_ok=True)

#         (debug_metadata_dir / f"dom_data_{page_name}.txt").write_text(
#             pprint.pformat(dom_data), encoding="utf-8"
#         )
#         (debug_metadata_dir / f"ocr_data_{page_name}.txt").write_text(
#             pprint.pformat(ocr_data), encoding="utf-8"
#         )

#         # -------- match & update --------
#         updated_matches = match_and_update(ocr_data, dom_data, collection)

#         (debug_metadata_dir / f"after_match_and_update_{page_name}.txt").write_text(
#             pprint.pformat(updated_matches), encoding="utf-8"
#         )

#         # -------- standardize --------
#         standardized_matches = [
#             build_standard_metadata(m, page_name, image_path="", source_url=getattr(PAGE, "url", None))
#             for m in (updated_matches or [])
#         ]

#         (debug_metadata_dir / f"standardized_matches_{page_name}.txt").write_text(
#             pprint.pformat(standardized_matches), encoding="utf-8"
#         )

#         set_last_match_result(standardized_matches)

#         # -------- persist JSON snapshots --------
#         metadata_dir = Path("generated_runs") / "src" / "metadata"
#         metadata_dir.mkdir(parents=True, exist_ok=True)

#         # per-page snapshot
#         (metadata_dir / f"after_enrichment_{page_name}.json").write_text(
#             json.dumps(standardized_matches, indent=2), encoding="utf-8"
#         )

#         # full collection snapshot
#         chroma_all = collection.get() or {}
#         chroma_all_metadatas = chroma_all.get("metadatas", []) or []
#         (metadata_dir / "after_enrichment.json").write_text(
#             json.dumps(chroma_all_metadatas, indent=2), encoding="utf-8"
#         )

#         return {
#             "status": "success",
#             "message": f"[Keyboard Trigger] Enriched {len(standardized_matches)} elements for page: {page_name}",
#             "matched_data": standardized_matches,
#             "count": len(standardized_matches),
#         }

#     except HTTPException:
#         raise
#     except Exception as e:
#         # helpful diagnostics for client + server logs
#         trace = traceback.format_exc()
#         print("[ERROR] capture_from_keyboard failed:", e, "\n", trace)
#         raise HTTPException(
#             status_code=500,
#             detail=f"❌ Capture failed: {e.__class__.__name__}: {e}"
#         )

    
#     except Exception as e:
#         import traceback
#         traceback.print_exc()
#         print(e)
#         raise HTTPException(status_code=500, detail=str(e))
    
# @router.get("/available-pages")
# async def list_page_names():
#     try:
#         records = collection.get()
#         page_names = list({meta.get("page_name", "unknown") for meta in records.get("metadatas", [])})
#         return {"pages": page_names}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))
    
# @router.on_event("shutdown")
# async def shutdown_browser():
#     global PLAYWRIGHT
#     if PLAYWRIGHT:
#         await PLAYWRIGHT.stop()
 
# @router.get("/latest-match-result")
# async def get_latest_match_result():
#     try:
#         records = collection.get()
#         matched = [r for r in records.get("metadatas", []) if r.get("dom_matched") is True]
#         return {
#             "status": "success",
#             "matched_elements": matched,
#             "count": len(matched)
#         }
#     except Exception as e:
#         import traceback
#         traceback.print_exc()
#         raise HTTPException(status_code=500, detail=str(e))


# @router.post("/reset-enrichment/{page_name}")
# async def reset_enrichment_api(page_name: str):
#     reset_enriched(page_name)
#     return {"success": True, "message": f"Enrichment reset for {page_name}"}


# __all__ = ["router"]



# # enrichment_api.py
# from __future__ import annotations

# # stdlib
# import ast
# import json
# import pprint
# import re
# from pathlib import Path
# from typing import Any, Dict, List, Optional, Set
# from urllib.parse import urlparse

# # third-party
# from fastapi import APIRouter, HTTPException
# from pydantic import BaseModel, Field
# from chromadb import PersistentClient
# from playwright.async_api import async_playwright, Page, Browser

# # your modules
# from utils.enrichment_status import reset_enriched
# from logic.manual_capture_mode import (
#     extract_dom_metadata,
#     match_and_update,
#     set_last_match_result,
# )
# from utils.match_utils import normalize_page_name
# from utils.file_utils import build_standard_metadata

# # -----------------------------------------------------------------------------
# # Router & DB
# # -----------------------------------------------------------------------------
# router = APIRouter()
# client = PersistentClient(path="./data/chroma_db")
# collection = client.get_or_create_collection(name="element_metadata")

# # -----------------------------------------------------------------------------
# # Runtime state
# # -----------------------------------------------------------------------------
# PLAYWRIGHT = None
# BROWSER: Optional[Browser] = None
# PAGE: Optional[Page] = None
# CURRENT_PAGE_NAME: str = "unknown_page"

# # folders
# SRC_DIR = Path("generated_runs") / "src"
# PAGES_DIR = SRC_DIR / "pages"
# META_DIR = SRC_DIR / "metadata"

# # discovery heuristics
# EXCLUDE_FILES: Set[str] = {"__init__.py", "auto_stubs.py", "base_page.py", "restful_page.py"}
# PAGEY_METHOD = re.compile(r"(page|screen|view)", re.IGNORECASE)

# # -----------------------------------------------------------------------------
# # Models
# # -----------------------------------------------------------------------------
# class LaunchRequest(BaseModel):
#     url: str = Field(..., description="Target URL (scheme optional; https tried first)")
#     headless: bool = False
#     slow_mo: int = 80
#     ignore_https_errors: bool = True
#     viewport_width: int = 1400
#     viewport_height: int = 900
#     wait_until: str = "networkidle"  # 'load'|'domcontentloaded'|'networkidle'|'commit'
#     user_agent: Optional[str] = None
#     extra_http_headers: Optional[Dict[str, str]] = None
#     http_username: Optional[str] = None
#     http_password: Optional[str] = None

# class CaptureRequest(BaseModel):
#     pass

# class PageNameSetRequest(BaseModel):
#     page_name: str

# # -----------------------------------------------------------------------------
# # Utilities
# # -----------------------------------------------------------------------------
# def _norm_text(s: Optional[str]) -> str:
#     if not s:
#         return ""
#     return " ".join(s.replace("\n", " ").replace("\r", " ").strip().strip(":").split()).lower()

# def _ensure_dirs() -> Dict[str, Path]:
#     paths = {"debug": SRC_DIR / "ocr-dom-metadata", "meta": SRC_DIR / "metadata"}
#     for p in paths.values():
#         p.mkdir(parents=True, exist_ok=True)
#     return paths

# async def _smart_navigate(page: Page, raw_url: str, wait_until: str = "networkidle"):
#     """Navigate even if scheme is missing; try https then http."""
#     def _with_scheme(u: str, scheme: str) -> str:
#         p = urlparse(u)
#         return f"{scheme}://{u}" if not p.scheme else u

#     url_https = _with_scheme(raw_url, "https")
#     url_http  = _with_scheme(raw_url, "http")
#     try:
#         resp = await page.goto(url_https, wait_until=wait_until)
#         if resp is None or getattr(resp, "ok", True):
#             return resp
#     except Exception:
#         pass
#     return await page.goto(url_http, wait_until=wait_until)

# async def _clean_restart():
#     global PLAYWRIGHT, BROWSER, PAGE
#     try:
#         if PAGE and hasattr(PAGE, "is_closed") and not PAGE.is_closed():
#             await PAGE.close()
#     except Exception:
#         pass
#     try:
#         if BROWSER:
#             await BROWSER.close()
#     except Exception:
#         pass
#     try:
#         if PLAYWRIGHT:
#             await PLAYWRIGHT.stop()
#     except Exception:
#         pass
#     PLAYWRIGHT = None
#     BROWSER = None
#     PAGE = None

# # ---- Page name discovery for dropdown --------------------------------------------------
# def _discover_from_poms() -> Set[str]:
#     names: Set[str] = set()
#     if not PAGES_DIR.exists():
#         return names
#     for py in PAGES_DIR.glob("*.py"):
#         if py.name in EXCLUDE_FILES:
#             continue
#         names.add(normalize_page_name(py.stem))
#         try:
#             text = py.read_text(encoding="utf-8", errors="ignore")
#             tree = ast.parse(text, filename=str(py))
#         except Exception:
#             continue
#         for node in ast.iter_child_nodes(tree):
#             if isinstance(node, ast.ClassDef):
#                 cls = node.name
#                 base = cls[:-4] if cls.lower().endswith("page") else cls
#                 names.add(normalize_page_name(base))
#                 for sub in node.body:
#                     if isinstance(sub, ast.FunctionDef) and PAGEY_METHOD.search(sub.name):
#                         names.add(normalize_page_name(sub.name))
#             elif isinstance(node, ast.FunctionDef) and PAGEY_METHOD.search(node.name):
#                 names.add(normalize_page_name(node.name))
#     return {n for n in names if n and n != "unknown"}

# def _discover_from_chroma() -> Set[str]:
#     names: Set[str] = set()
#     try:
#         recs = collection.get() or {}
#         for m in (recs.get("metadatas") or []):
#             pn = (m or {}).get("page_name")
#             if pn:
#                 names.add(normalize_page_name(pn))
#     except Exception:
#         pass
#     return names

# def _discover_from_metadata() -> Set[str]:
#     names: Set[str] = set()
#     if not META_DIR.exists():
#         return names
#     for path in META_DIR.glob("after_enrichment_*.json"):
#         stem = path.stem  # after_enrichment_<page>
#         parts = stem.split("after_enrichment_", 1)
#         if len(parts) == 2 and parts[1]:
#             names.add(normalize_page_name(parts[1]))
#         try:
#             data = json.loads(path.read_text(encoding="utf-8"))
#             if isinstance(data, list):
#                 for rec in data:
#                     pn = (rec or {}).get("page_name")
#                     if pn:
#                         names.add(normalize_page_name(pn))
#         except Exception:
#             pass
#     return names

# def _aggregate_available_pages() -> List[str]:
#     names: Set[str] = set()
#     names |= _discover_from_poms()
#     names |= _discover_from_chroma()
#     names |= _discover_from_metadata()
#     return sorted({n for n in names if n and n != "unknown"})

# # ---- Enrichment core ------------------------------------------------------------------
# async def _run_enrichment_for(page_name: str) -> Dict[str, Any]:
#     global PAGE, collection, CURRENT_PAGE_NAME
#     if PAGE is None:
#         raise HTTPException(status_code=500, detail="❌ Cannot extract. No active page handle.")
#     if hasattr(PAGE, "is_closed") and PAGE.is_closed():
#         raise HTTPException(status_code=500, detail="❌ Cannot extract. Page is already closed.")
#     if collection is None:
#         raise HTTPException(status_code=500, detail="❌ Chroma collection is not initialized.")

#     CURRENT_PAGE_NAME = normalize_page_name(page_name)
#     paths = _ensure_dirs()

#     dom_data = await extract_dom_metadata(PAGE, CURRENT_PAGE_NAME) or []
#     try:
#         _ = len(dom_data)
#     except Exception:
#         dom_data = list(dom_data)

#     for rec in dom_data:
#         try:
#             label = rec.get("label") or rec.get("aria_label") or rec.get("text")
#             placeholder = rec.get("placeholder")
#             role = rec.get("role")
#             tag = rec.get("tag")
#             rec["_norm"] = {
#                 "label": _norm_text(label),
#                 "placeholder": _norm_text(placeholder),
#                 "role": (role or "").lower(),
#                 "tag": (tag or "").lower(),
#             }
#         except Exception:
#             pass

#     chroma_resp = collection.get(where={"page_name": CURRENT_PAGE_NAME}) or {}
#     ocr_data = chroma_resp.get("metadatas", []) or []

#     (paths["debug"] / f"dom_data_{CURRENT_PAGE_NAME}.txt").write_text(
#         pprint.pformat(dom_data), encoding="utf-8"
#     )
#     (paths["debug"] / f"ocr_data_{CURRENT_PAGE_NAME}.txt").write_text(
#         pprint.pformat(ocr_data), encoding="utf-8"
#     )

#     updated_matches = match_and_update(ocr_data, dom_data, collection)
#     (paths["debug"] / f"after_match_and_update_{CURRENT_PAGE_NAME}.txt").write_text(
#         pprint.pformat(updated_matches), encoding="utf-8"
#     )

#     standardized_matches = [
#         build_standard_metadata(m, CURRENT_PAGE_NAME, image_path="", source_url=getattr(PAGE, "url", None))
#         for m in (updated_matches or [])
#     ]
#     set_last_match_result(standardized_matches)

#     (paths["meta"] / f"after_enrichment_{CURRENT_PAGE_NAME}.json").write_text(
#         json.dumps(standardized_matches, indent=2), encoding="utf-8"
#     )
#     chroma_all = collection.get() or {}
#     chroma_all_metadatas = chroma_all.get("metadatas", []) or []
#     (paths["meta"] / "after_enrichment.json").write_text(
#         json.dumps(chroma_all_metadatas, indent=2), encoding="utf-8"
#     )

#     return {
#         "status": "success",
#         "message": f"Enriched {len(standardized_matches)} elements for page: {CURRENT_PAGE_NAME}",
#         "matched_data": standardized_matches,
#         "count": len(standardized_matches),
#     }

# # -----------------------------------------------------------------------------
# # Routes
# # -----------------------------------------------------------------------------
# @router.post("/launch-browser")
# async def launch_browser(req: LaunchRequest):
#     """
#     Launch Chromium, navigate (HTTPS→HTTP fallback), inject Alt+Q modal.
#     Dropdown UI is the same as your original (select + options).
#     """
#     global PLAYWRIGHT, BROWSER, PAGE

#     try:
#         await _clean_restart()

#         PLAYWRIGHT = await async_playwright().start()
#         BROWSER = await PLAYWRIGHT.chromium.launch(headless=req.headless, slow_mo=req.slow_mo)

#         context_kwargs: Dict[str, Any] = {
#             "ignore_https_errors": req.ignore_https_errors,
#             "viewport": {"width": req.viewport_width, "height": req.viewport_height},
#         }
#         if req.user_agent:
#             context_kwargs["user_agent"] = req.user_agent
#         if req.extra_http_headers:
#             context_kwargs["extra_http_headers"] = req.extra_http_headers
#         if req.http_username and req.http_password:
#             context_kwargs["http_credentials"] = {"username": req.http_username, "password": req.http_password}

#         context = await BROWSER.new_context(**context_kwargs)
#         PAGE = await context.new_page()
#         await _smart_navigate(PAGE, req.url, wait_until=req.wait_until)

#         # ---- bindings (no CORS) ----
#         async def _binding_enrich(source, page_name: str):
#             try:
#                 res = await _run_enrichment_for(page_name)
#                 return json.dumps(res)
#             except HTTPException as he:
#                 return json.dumps({"status": "fail", "error": he.detail})
#             except Exception as e:
#                 return json.dumps({"status": "fail", "error": str(e)})

#         async def _binding_available_pages(source):
#             try:
#                 pages = _aggregate_available_pages()
#                 return json.dumps({"status": "success", "pages": pages})
#             except Exception as e:
#                 return json.dumps({"status": "fail", "error": str(e), "pages": []})

#         async def _binding_current_page(source):
#             return json.dumps({"page_name": CURRENT_PAGE_NAME})

#         await PAGE.expose_binding("smartAI_enrich", _binding_enrich)
#         await PAGE.expose_binding("smartAI_availablePages", _binding_available_pages)
#         await PAGE.expose_binding("smartAI_currentPage", _binding_current_page)

#         # ---- inject your SAME modal (select dropdown) ----
#         await PAGE.evaluate("""
#           (function(){
#             if (window._ocrShortcutRegistered) return;
#             window._ocrShortcutRegistered = true;
#             console.log('[SmartAI] Modal enrichment JS injected');

#             const modal = document.createElement('div');
#             modal.innerHTML = `
#               <div id="ocrModal" style="position:fixed;top:40%;left:50%;transform:translate(-50%,-50%);background:white;padding:20px;border:2px solid black;z-index:2147483647;display:none;min-width:360px;font-family:Arial,sans-serif;">
#                 <label>Enter Page Name:</label><br/>
#                 <select id="pageDropdown" style="margin:5px;padding:5px;width:250px;"></select><br/>
#                 <button id="smartAI_enrich_btn">Enrich</button>
#                 <button id="smartAI_close_btn">Close</button>
#                 <div id="enrichmentMessageBox" style="margin-top:10px;font-weight:bold;color:green;"></div>
#                 <div style="margin-top:8px;color:#666;font-size:12px;">Tip: press <b>Alt+Q</b> to open/close</div>
#               </div>
#             `;
#             document.body.appendChild(modal);

#             async function loadAvailablePages() {
#               const dropdown = document.getElementById('pageDropdown');
#               dropdown.innerHTML = "";
#               // Prefer Playwright binding (no CORS). Fallback to fetch if available.
#               try {
#                 let data;
#                 if (window.smartAI_availablePages) {
#                   const respStr = await window.smartAI_availablePages();
#                   data = JSON.parse(respStr || '{}');
#                 } else {
#                   const res = await fetch('http://localhost:8001/available-pages');
#                   data = await res.json();
#                 }
#                 const pages = Array.isArray(data.pages) ? data.pages : (data.status==='success' ? data.pages : []);
#                 for (const page of pages || []) {
#                   const option = document.createElement("option");
#                   option.value = page;
#                   option.innerText = page;
#                   dropdown.appendChild(option);
#                 }
#                 // Preselect current page name if any
#                 try {
#                   if (window.smartAI_currentPage) {
#                     const curStr = await window.smartAI_currentPage();
#                     const cur = JSON.parse(curStr || '{}');
#                     if (cur && cur.page_name) dropdown.value = cur.page_name;
#                   }
#                 } catch(e) {}
#               } catch (err) {
#                 const msg = document.getElementById('enrichmentMessageBox');
#                 msg.textContent = "❌ Failed to load available pages.";
#                 msg.style.color = "red";
#               }
#             }

#             async function triggerEnrichment() {
#               const dropdown = document.getElementById('pageDropdown');
#               const msg = document.getElementById("enrichmentMessageBox");
#               const pageName = (dropdown.value || '').trim();
#               if (!pageName) {
#                 msg.innerText = "❌ Page name is required.";
#                 msg.style.color = "red";
#                 return;
#               }
#               msg.innerText = "⏳ Enrichment in progress…";
#               msg.style.color = "blue";
#               msg.offsetHeight;
#               try {
#                 if (!window.smartAI_enrich) throw new Error("Binding not available");
#                 const resultStr = await window.smartAI_enrich(pageName);
#                 const result = JSON.parse(resultStr || '{}');
#                 if (result.status !== "success") {
#                   msg.innerText = `❌ Enrichment failed: ${result.error || 'unknown error'}`;
#                   msg.style.color = "red";
#                 } else if (!result.count) {
#                   msg.innerText = "❌ Enrichment succeeded but no elements matched.";
#                   msg.style.color = "red";
#                 } else {
#                   msg.innerText = `✅ Enriched ${result.count} elements successfully.`;
#                   msg.style.color = "green";
#                 }
#               } catch (err) {
#                 console.error("Enrichment Error:", err);
#                 msg.innerText = "❌ Enrichment Error: " + (err.message || err);
#                 msg.style.color = "red";
#               }
#             }

#             document.addEventListener('keydown', function(e) {
#               if (e.altKey && (e.key === 'q' || e.key === 'Q')) {
#                 const modal = document.getElementById('ocrModal');
#                 if (modal.style.display === 'none') {
#                   modal.style.display = 'block';
#                   loadAvailablePages();
#                 } else {
#                   modal.style.display = 'none';
#                 }
#               }
#             });

#             document.getElementById('smartAI_enrich_btn').onclick = triggerEnrichment;
#             document.getElementById('smartAI_close_btn').onclick  = () => {
#               document.getElementById('ocrModal').style.display = 'none';
#             };
#           })();
#         """)

#         return {
#             "status": "success",
#             "message": f"✅ Browser launched and navigated to {req.url}. Press Alt+Q to open the enrichment modal."
#         }

#     except Exception as e:
#         import traceback
#         traceback.print_exc()
#         await _clean_restart()
#         raise HTTPException(status_code=500, detail=str(e))

# @router.post("/set-current-page-name")
# async def set_page_name(req: PageNameSetRequest):
#     global CURRENT_PAGE_NAME
#     CURRENT_PAGE_NAME = normalize_page_name(req.page_name)
#     print(f"[INFO] ✅ Page name set to: {CURRENT_PAGE_NAME}")
#     return {"status": "success", "page_name": CURRENT_PAGE_NAME}

# @router.post("/capture-dom-from-client")
# async def capture_from_keyboard(_: CaptureRequest):
#     global PAGE, CURRENT_PAGE_NAME, collection
#     try:
#         if PAGE is None:
#             raise HTTPException(status_code=500, detail="❌ Cannot extract. No active page handle.")
#         if hasattr(PAGE, "is_closed") and PAGE.is_closed():
#             raise HTTPException(status_code=500, detail="❌ Cannot extract. Page is already closed.")
#         if not CURRENT_PAGE_NAME:
#             raise HTTPException(status_code=400, detail="❌ No current page name set.")
#         if collection is None:
#             raise HTTPException(status_code=500, detail="❌ Chroma collection is not initialized.")

#         page_name = CURRENT_PAGE_NAME
#         print(f"[INFO] Enrichment triggered for: {page_name}")

#         paths = _ensure_dirs()

#         dom_data = await extract_dom_metadata(PAGE, page_name) or []
#         try:
#             _ = len(dom_data)
#         except Exception:
#             dom_data = list(dom_data)

#         for rec in dom_data:
#             try:
#                 label = rec.get("label") or rec.get("aria_label") or rec.get("text")
#                 placeholder = rec.get("placeholder")
#                 role = rec.get("role")
#                 tag = rec.get("tag")
#                 rec["_norm"] = {
#                     "label": _norm_text(label),
#                     "placeholder": _norm_text(placeholder),
#                     "role": (role or "").lower(),
#                     "tag": (tag or "").lower(),
#                 }
#             except Exception:
#                 pass

#         chroma_resp = collection.get(where={"page_name": page_name}) or {}
#         ocr_data = chroma_resp.get("metadatas", []) or []

#         (paths["debug"] / f"dom_data_{page_name}.txt").write_text(pprint.pformat(dom_data), encoding="utf-8")
#         (paths["debug"] / f"ocr_data_{page_name}.txt").write_text(pprint.pformat(ocr_data), encoding="utf-8")

#         updated_matches = match_and_update(ocr_data, dom_data, collection)
#         (paths["debug"] / f"after_match_and_update_{page_name}.txt").write_text(
#             pprint.pformat(updated_matches), encoding="utf-8"
#         )

#         standardized_matches = [
#             build_standard_metadata(m, page_name, image_path="", source_url=getattr(PAGE, "url", None))
#             for m in (updated_matches or [])
#         ]
#         (paths["debug"] / f"standardized_matches_{page_name}.txt").write_text(
#             pprint.pformat(standardized_matches), encoding="utf-8"
#         )

#         set_last_match_result(standardized_matches)

#         (paths["meta"] / f"after_enrichment_{page_name}.json").write_text(
#             json.dumps(standardized_matches, indent=2), encoding="utf-8"
#         )
#         chroma_all = collection.get() or {}
#         chroma_all_metadatas = chroma_all.get("metadatas", []) or []
#         (paths["meta"] / "after_enrichment.json").write_text(
#             json.dumps(chroma_all_metadatas, indent=2), encoding="utf-8"
#         )

#         return {
#             "status": "success",
#             "message": f"[Keyboard Trigger] Enriched {len(standardized_matches)} elements for page: {page_name}",
#             "matched_data": standardized_matches,
#             "count": len(standardized_matches),
#         }

#     except HTTPException:
#         raise
#     except Exception as e:
#         import traceback
#         traceback.print_exc()
#         raise HTTPException(status_code=500, detail=f"❌ Capture failed: {e.__class__.__name__}: {e}")

# @router.get("/available-pages")
# async def list_page_names():
#     """Also expose as HTTP (for your legacy fetch)."""
#     try:
#         return {"pages": _aggregate_available_pages()}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

# @router.get("/current-url")
# async def current_url():
#     try:
#         return {"url": getattr(PAGE, "url", None)}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

# @router.on_event("shutdown")
# async def shutdown_browser():
#     await _clean_restart()

# @router.get("/latest-match-result")
# async def get_latest_match_result():
#     try:
#         records = collection.get()
#         matched = [r for r in records.get("metadatas", []) if r.get("dom_matched") is True]
#         return {"status": "success", "matched_elements": matched, "count": len(matched)}
#     except Exception as e:
#         import traceback
#         traceback.print_exc()
#         raise HTTPException(status_code=500, detail=str(e))

# @router.post("/reset-enrichment/{page_name}")
# async def reset_enrichment_api(page_name: str):
#     reset_enriched(page_name)
#     return {"success": True, "message": f"Enrichment reset for {page_name}"}

# __all__ = ["router"]



# enrichment_api.py
from __future__ import annotations

import os
import ast
import json
import re
import pprint
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from chromadb import PersistentClient
from playwright.async_api import async_playwright, Page, Browser

from utils.enrichment_status import reset_enriched
from logic.manual_capture_mode import extract_dom_metadata, match_and_update, set_last_match_result
from utils.match_utils import normalize_page_name
from utils.file_utils import build_standard_metadata

# -----------------------------------------------------------------------------
# Router & DB
# -----------------------------------------------------------------------------
router = APIRouter()
client = PersistentClient(path=os.environ.get("SMARTAI_CHROMA_PATH", "./data/chroma_db"))
collection = client.get_or_create_collection(name=os.environ.get("SMARTAI_CHROMA_COLLECTION", "element_metadata"))

# -----------------------------------------------------------------------------
# Runtime state
# -----------------------------------------------------------------------------
PLAYWRIGHT = None
BROWSER: Optional[Browser] = None
PAGE: Optional[Page] = None
CURRENT_PAGE_NAME: str = "unknown_page"

# -----------------------------------------------------------------------------
# Config
# -----------------------------------------------------------------------------
SRC_DIR = Path(os.environ.get("SMARTAI_SRC_DIR", "generated_runs/src"))
PAGES_DIR = Path(os.environ.get("SMARTAI_PAGES_DIR", str(SRC_DIR / "pages")))
META_DIR  = Path(os.environ.get("SMARTAI_META_DIR",  str(SRC_DIR / "metadata")))
PY_FILE_GLOB = os.environ.get("SMARTAI_PAGES_GLOB", "*.py")

# Regex to identify methods that *explicitly* look like page methods (lenient)
PAGE_METHOD_RE = re.compile(os.environ.get(
    "SMARTAI_PAGE_METHOD_RE",
    r"(?i)(^page[_\-\s])|([_\-\s]page$)|(_page$)|(^.*\bpage\b.*$)"
))

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
    wait_until: str = "networkidle"
    user_agent: Optional[str] = None
    extra_http_headers: Optional[Dict[str, str]] = None
    http_username: Optional[str] = None
    http_password: Optional[str] = None

class CaptureRequest(BaseModel):
    pass

class PageNameSetRequest(BaseModel):
    page_name: str

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def _norm_text(s: Optional[str]) -> str:
    if not s:
        return ""
    return " ".join(s.replace("\n", " ").replace("\r", " ").strip().strip(":").split()).lower()

def _ensure_dirs() -> Dict[str, Path]:
    paths = {"debug": SRC_DIR / "ocr-dom-metadata", "meta": META_DIR}
    for p in paths.values():
        p.mkdir(parents=True, exist_ok=True)
    return paths

def _canonical(name: str) -> str:
    """
    Canonical display name: remove 'page' token anywhere, collapse separators,
    normalize with your helper. e.g. 'page_orange'/'orange_page' -> 'orange'
    """
    n = normalize_page_name(name or "")
    if not n:
        return n
    tokens = re.split(r"[_\-\s]+", n)
    tokens = [t for t in tokens if t and t.lower() != "page"]
    return normalize_page_name("_".join(tokens))

def _is_explicit_page_method(fn_name: str, docstring: Optional[str]) -> bool:
    if PAGE_METHOD_RE.search(fn_name):
        return True
    if docstring and "@page" in docstring.lower():
        return True
    return False

async def _smart_navigate(page: Page, raw_url: str, wait_until: str = "networkidle"):
    def _with_scheme(u: str, scheme: str) -> str:
        p = urlparse(u)
        return f"{scheme}://{u}" if not p.scheme else u
    url_https = _with_scheme(raw_url, "https")
    url_http  = _with_scheme(raw_url, "http")
    try:
        resp = await page.goto(url_https, wait_until=wait_until)
        if resp is None or getattr(resp, "ok", True):
            return resp
    except Exception:
        pass
    return await page.goto(url_http, wait_until=wait_until)

async def _clean_restart():
    global PLAYWRIGHT, BROWSER, PAGE
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

# -----------------------------------------------------------------------------
# Discovery
# -----------------------------------------------------------------------------
def _ocr_page_names_from_chroma() -> Set[str]:
    """All page_name values that exist in Chroma (from OCR/imported images)."""
    names: Set[str] = set()
    try:
        recs = collection.get() or {}
        for m in (recs.get("metadatas") or []):
            pn = (m or {}).get("page_name")
            if pn:
                names.add(_canonical(pn))
    except Exception:
        pass
    return names

def _discover_methods_from_poms(ocr_names: Set[str]) -> Set[str]:
    """
    Methods discovered from your POMs. We keep a method if:
      - it explicitly looks like a page method (PAGE_METHOD_RE or '@page' in docstring), OR
      - its canonical name is present in OCR page names (so 'orange' is kept if OCR has 'orange').
    """
    names: Set[str] = set()
    if not PAGES_DIR.exists():
        return names

    for py in PAGES_DIR.glob(PY_FILE_GLOB):
        try:
            text = py.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(text, filename=str(py))
        except Exception:
            continue

        for node in ast.iter_child_nodes(tree):
            # top-level function
            if isinstance(node, ast.FunctionDef):
                doc = ast.get_docstring(node)
                cn = _canonical(node.name)
                if _is_explicit_page_method(node.name, doc) or (cn in ocr_names):
                    names.add(cn)
            # class methods
            elif isinstance(node, ast.ClassDef):
                for sub in node.body:
                    if isinstance(sub, ast.FunctionDef):
                        doc = ast.get_docstring(sub)
                        cn = _canonical(sub.name)
                        if _is_explicit_page_method(sub.name, doc) or (cn in ocr_names):
                            names.add(cn)
    return {n for n in names if n and n != "unknown"}

def _available_pages_for_dropdown() -> List[str]:
    """
    What the UI shows:
      1) intersection(methods, ocr)
      2) else OCR names
      3) else methods
    This guarantees you see the page name of the image you extracted.
    """
    ocr_names = _ocr_page_names_from_chroma()
    methods   = _discover_methods_from_poms(ocr_names)

    inter = methods & ocr_names
    if inter:
        pages = sorted(inter)
        print(f"[DROPDOWN] methods∩ocr = {pages}")
        return pages

    if ocr_names:
        pages = sorted(ocr_names)
        print(f"[DROPDOWN] fallback to OCR only = {pages}")
        return pages

    pages = sorted(methods)
    print(f"[DROPDOWN] fallback to methods only = {pages}")
    return pages

# -----------------------------------------------------------------------------
# Enrichment core
# -----------------------------------------------------------------------------
async def _run_enrichment_for(page_name: str) -> Dict[str, Any]:
    global PAGE, collection, CURRENT_PAGE_NAME
    if PAGE is None:
        raise HTTPException(status_code=500, detail="❌ Cannot extract. No active page handle.")
    if hasattr(PAGE, "is_closed") and PAGE.is_closed():
        raise HTTPException(status_code=500, detail="❌ Cannot extract. Page is already closed.")
    if collection is None:
        raise HTTPException(status_code=500, detail="❌ Chroma collection is not initialized.")

    CURRENT_PAGE_NAME = _canonical(page_name)
    paths = _ensure_dirs()

    dom_data = await extract_dom_metadata(PAGE, CURRENT_PAGE_NAME) or []
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
        build_standard_metadata(m, CURRENT_PAGE_NAME, image_path="", source_url=getattr(PAGE, "url", None))
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
    global PLAYWRIGHT, BROWSER, PAGE
    try:
        await _clean_restart()

        PLAYWRIGHT = await async_playwright().start()
        BROWSER = await PLAYWRIGHT.chromium.launch(headless=req.headless, slow_mo=req.slow_mo)

        context_kwargs: Dict[str, Any] = {
            "ignore_https_errors": req.ignore_https_errors,
            "viewport": {"width": req.viewport_width, "height": req.viewport_height},
        }
        if req.user_agent:
            context_kwargs["user_agent"] = req.user_agent
        if req.extra_http_headers:
            context_kwargs["extra_http_headers"] = req.extra_http_headers
        if req.http_username and req.http_password:
            context_kwargs["http_credentials"] = {"username": req.http_username, "password": req.http_password}

        context = await BROWSER.new_context(**context_kwargs)
        PAGE = await context.new_page()
        await _smart_navigate(PAGE, req.url, wait_until=req.wait_until)

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

        async def _binding_current_page(source):
            return json.dumps({"page_name": CURRENT_PAGE_NAME})

        await PAGE.expose_binding("smartAI_enrich", _binding_enrich)
        await PAGE.expose_binding("smartAI_availablePages", _binding_available_pages)
        await PAGE.expose_binding("smartAI_currentPage", _binding_current_page)

        # Modal with dropdown (Alt+Q)
        await PAGE.evaluate("""
          (function(){
            if (window._ocrShortcutRegistered) return;
            window._ocrShortcutRegistered = true;

            const modal = document.createElement('div');
            modal.innerHTML = `
              <div id="ocrModal" style="position:fixed;top:40%;left:50%;transform:translate(-50%,-50%);background:white;padding:20px;border:2px solid black;z-index:2147483647;display:none;min-width:360px;font-family:Arial,sans-serif;">
                <label>Page:</label><br/>
                <select id="pageDropdown" style="margin:5px;padding:5px;width:250px;"></select><br/>
                <button id="smartAI_enrich_btn">Enrich</button>
                <button id="smartAI_close_btn">Close</button>
                <div id="enrichmentMessageBox" style="margin-top:10px;font-weight:bold;color:green;"></div>
                <div style="margin-top:8px;color:#666;font-size:12px;">Tip: press <b>Alt+Q</b> to open/close</div>
              </div>
            `;
            document.body.appendChild(modal);

            async function loadAvailablePages() {
              const dropdown = document.getElementById('pageDropdown');
              dropdown.innerHTML = "";
              try {
                const respStr = await window.smartAI_availablePages();
                const data = JSON.parse(respStr || '{}');
                const pages = (data && data.status === 'success' && Array.isArray(data.pages)) ? data.pages : [];
                if (!pages.length) {
                  const msg = document.getElementById('enrichmentMessageBox');
                  msg.textContent = "⚠️ No pages found. Import OCR or add a page method.";
                  msg.style.color = "orange";
                }
                for (const p of pages) {
                  const opt = document.createElement('option');
                  opt.value = p;
                  opt.innerText = p;
                  dropdown.appendChild(opt);
                }
                try {
                  const curStr = await window.smartAI_currentPage();
                  const cur = JSON.parse(curStr || '{}');
                  if (cur && cur.page_name) dropdown.value = cur.page_name;
                } catch(e) {}
              } catch (err) {
                const msg = document.getElementById('enrichmentMessageBox');
                msg.textContent = "❌ Failed to load available pages.";
                msg.style.color = "red";
              }
            }

            async function triggerEnrichment() {
              const dropdown = document.getElementById('pageDropdown');
              const msg = document.getElementById('enrichmentMessageBox');
              const pageName = (dropdown.value || '').trim();
              if (!pageName) {
                msg.textContent = "❌ Page name is required.";
                msg.style.color = "red";
                return;
              }
              msg.textContent = "⏳ Enrichment in progress…";
              msg.style.color = "blue";
              try {
                const resultStr = await window.smartAI_enrich(pageName);
                const result = JSON.parse(resultStr || '{}');
                if (result.status !== "success") {
                  msg.textContent = "❌ " + (result.error || "Enrichment failed");
                  msg.style.color = "red";
                } else if (!result.count) {
                  msg.textContent = "❌ Enrichment succeeded but no elements matched.";
                  msg.style.color = "red";
                } else {
                  msg.textContent = `✅ Enriched ${result.count} elements`;
                  msg.style.color = "green";
                }
              } catch (err) {
                msg.textContent = "❌ Error: " + (err && err.message ? err.message : err);
                msg.style.color = "red";
              }
            }

            document.addEventListener('keydown', function(e){
              if (e.altKey && (e.key === 'q' || e.key === 'Q')) {
                const modal = document.getElementById('ocrModal');
                if (modal.style.display === 'none') {
                  modal.style.display = 'block';
                  loadAvailablePages();
                } else {
                  modal.style.display = 'none';
                }
              }
            });

            document.getElementById('smartAI_enrich_btn').onclick = triggerEnrichment;
            document.getElementById('smartAI_close_btn').onclick  = () => {
              document.getElementById('ocrModal').style.display = 'none';
            };
          })();
        """)

        return {
            "status": "success",
            "message": f"✅ Browser launched and navigated to {req.url}. Press Alt+Q to open the enrichment modal."
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
    global PAGE, CURRENT_PAGE_NAME, collection
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

        paths = _ensure_dirs()
        dom_data = await extract_dom_metadata(PAGE, page_name) or []
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

        (paths["debug"] / f"dom_data_{page_name}.txt").write_text(pprint.pformat(dom_data), encoding="utf-8")
        (paths["debug"] / f"ocr_data_{page_name}.txt").write_text(pprint.pformat(ocr_data), encoding="utf-8")

        updated_matches = match_and_update(ocr_data, dom_data, collection)
        (paths["debug"] / f"after_match_and_update_{page_name}.txt").write_text(
            pprint.pformat(updated_matches), encoding="utf-8"
        )

        standardized_matches = [
            build_standard_metadata(m, page_name, image_path="", source_url=getattr(PAGE, "url", None))
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
        raise HTTPException(status_code=500, detail=f"❌ Capture failed: {e.__class__.__name__}: {e}")

@router.get("/available-pages")
async def list_page_names():
    try:
        return {"pages": _available_pages_for_dropdown()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/current-url")
async def current_url():
    try:
        return {"url": getattr(PAGE, "url", None)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.on_event("shutdown")
async def shutdown_browser():
    await _clean_restart()

@router.get("/latest-match-result")
async def get_latest_match_result():
    try:
        records = collection.get()
        matched = [r for r in records.get("metadatas", []) if r.get("dom_matched") is True]
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
