# enrichment_api.py

from utils.enrichment_status import reset_enriched
from fastapi import APIRouter
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from chromadb import PersistentClient
from logic.manual_capture_mode import extract_dom_metadata, match_and_update, get_last_match_result, set_last_match_result
from utils.match_utils import normalize_page_name
from utils.file_utils import build_standard_metadata
from playwright.async_api import async_playwright, Page, Browser
import json
import os
from pathlib import Path
import pprint
import time
import asyncio
from typing import Any, Dict, Optional

router = APIRouter()
client = PersistentClient(path="./data/chroma_db")
collection = client.get_or_create_collection(name="element_metadata")

BROWSER: Browser = None
PAGE: Page = None
PLAYWRIGHT = None
CURRENT_PAGE_NAME: str = "unknown_page"
 
class LaunchRequest(BaseModel):
    url: str
class CaptureRequest(BaseModel):
    pass
class PageNameSetRequest(BaseModel):
    page_name: str
 
# async def send_enrichment_requests(page_name: str):
#     from httpx import AsyncClient
#     async with AsyncClient() as client:
#         try:
#             await client.post("http://localhost:8001/set-current-page-name", json={"page_name": page_name})
#             print('[DEBUG] set global CURRENT_PAGE_NAME = ', CURRENT_PAGE_NAME, ' Going for capture_dom_from_client')
#         except Exception as e:
#             print(f"🔥Error from: await client.post('8001/set-current-page-name': {e}")
#             return {"status": "fail", "error": "set-current-page-name failed"}
        
#         try:
#             resp = await client.post(f"http://localhost:8001/capture-dom-from-client", json={})
#             resp.raise_for_status()
#         except Exception as e:
#             # Print the full exception so you see “404 Not Found” or “Connection refused”
#             print(f"🔥🔥Error POSTing to /capture-dom-from-client: {e!r}")
#             return {"status": "fail", "count": 0, "error": str(e)}


#         # try:
#         #     resp = await client.post("http://localhost:8001/capture-dom-from-client", json={})
#         #     print('[DEBUG] capture_dom_from_client done. resp = ', resp, "Now trying to convert the data to json", sep='\n')
#         # except Exception as e:
#         #     print("🔥🔥Error from: await client.post('8001/capture-from-dom-client'", e)
#         #     return {"status": "fail", "error": "capture-dom-from-client failed"}
        
#         # 3) parse JSON
#         return resp.json()

#         json_data = None
#         try:
#             json_data = await resp.aread()
#             decoded_json_data = json_data.decode("utf-8").strip()
#             if not decoded_json_data or decoded_json_data in ["null", "undefined"]:
#                 return {"status": "fail", "error": "Empty or invalid response"}
#         except Exception as e:
#             print(f"🔥🔥🔥Error from: await resp.aread(): {e}")
#             return {"status": "fail", "error": f"Error reading response: {e}"}
        
#         # print("[DEBUG] decoded_json_data:", decoded_json_data)
#         try:
#             return json.loads(decoded_json_data)
#         except Exception as e:
#             print("🔥🔥🔥🔥[ERROR] JSON parsing failed:", e)
#             return {"status": "fail", "error": "Response parsing failed : {e}"}

# async def send_enrichment_requests(page_name: str):
#     from httpx import AsyncClient, HTTPStatusError

#     BASE = "http://localhost:8001"  # ← make sure this matches your uvicorn port!

#     async with AsyncClient(timeout=None) as client:
#         # 1) set the page name
#         try:
#             r = await client.post(f"{BASE}/set-current-page-name", json={"page_name": page_name})
#             r.raise_for_status()
#         except Exception as e:
#             print(f"🔥Error setting page name: {e!r}")
#             return {"status": "fail", "count": 0, "error": str(e)}

#         # 2) call enrichment endpoint
#         try:
#             time.sleep(5)
#             resp = await client.post(f"{BASE}/capture-dom-from-client", json={})
#             resp.raise_for_status()
#         except HTTPStatusError as e:
#             # e.response.status_code & e.response.text will show you 404 or other codes
#             print(f"🔥HTTP error {e.response.status_code}: {e.response.text!r}")
#             return {"status": "fail", "count": 0, "error": f"HTTP {e.response.status_code}"}
#         except Exception as e:
#             print(f"🔥Network/connection error: {e!r}")
#             return {"status": "fail", "count": 0, "error": str(e)}

#         # 3) Success → parse JSON
#         try:
#             return resp.json()
#         except Exception as e:
#             print(f"🔥JSON parse error: {e!r}")
#             return {"status": "fail", "count": 0, "error": "invalid JSON"}

# async def send_enrichment_requests(
#     page_name: str,
#     target_url: str = "https://the-internet.herokuapp.com/login", 
#     base: str = "http://localhost:8001",
#     wait_seconds: float = 3.0,
#     retries: int = 3,
# ) -> Dict[str, Any]:
#     """
#     Ask the enrichment service to navigate to target_url (http/https),
#     set the page name, and capture DOM metadata.
#     Works with HTTPS sites like https://the-internet.herokuapp.com/login.
#     """
#     from httpx import AsyncClient, HTTPStatusError, RequestError

#     # Ensure the URL has a scheme
#     if not (target_url.startswith("http://") or target_url.startswith("https://")):
#         target_url = "https://" + target_url  # default to https if not provided

#     async with AsyncClient(timeout=None) as client:
#         # 0) (optional) Launch the browser and navigate to the target URL.
#         # If your backend already has the page open, this will just succeed/NO-OP.
#         try:
#             r_launch = await client.post(
#                 f"{base}/launch-browser",
#                 json={
#                     "url": target_url,
#                     "page_name": page_name,
#                     "headless": False,
#                     "ignore_https_errors": True,   # <-- important for HTTPS sites
#                     "wait_until": "networkidle",    # backend can ignore if unsupported
#                 },
#             )
#             # Some setups won't have /launch-browser; don't fail hard on 404.
#             if r_launch.status_code not in (200, 404):
#                 r_launch.raise_for_status()
#         except RequestError as e:
#             # It's OK to continue even if /launch-browser doesn't exist;
#             # but if it's something other than a 404 we surface it.
#             return {"status": "fail", "count": 0, "error": f"launch error: {e!r}"}

#         # 1) Set the page name (needed by your matching logic)
#         try:
#             r = await client.post(
#                 f"{base}/set-current-page-name",
#                 json={"page_name": page_name},
#             )
#             r.raise_for_status()
#         except (HTTPStatusError, RequestError) as e:
#             return {"status": "fail", "count": 0, "error": f"set page name: {e!r}"}

#         # 2) Give the backend a moment to be ready
#         await asyncio.sleep(wait_seconds)

#         # 3) Try capture a few times (helps when HTTPS pages take longer)
#         last_err: Optional[str] = None
#         for attempt in range(1, retries + 1):
#             try:
#                 resp = await client.post(f"{base}/capture-dom-from-client", json={"page_name": page_name})
#                 resp.raise_for_status()
#                 try:
#                     data = resp.json()
#                     # If your backend stores the latest match and expects a separate fetch:
#                     # If data seems empty, try to poll /latest-match-result
#                     if not data or (isinstance(data, dict) and data.get("count", 0) == 0):
#                         # brief poll for a ready result
#                         for _ in range(10):
#                             await asyncio.sleep(0.5)
#                             latest = await client.get(f"{base}/latest-match-result")
#                             if latest.status_code == 200:
#                                 jd = latest.json()
#                                 if jd:
#                                     return jd
#                         # fall back to whatever we got
#                     return data
#                 except Exception as e:
#                     return {"status": "fail", "count": 0, "error": f"invalid JSON: {e!r}"}
#             except HTTPStatusError as e:
#                 last_err = f"HTTP {getattr(e.response,'status_code', '??')}: {getattr(e.response,'text','')!r}"
#             except RequestError as e:
#                 last_err = f"network error: {e!r}"

#             # backoff before next try
#             await asyncio.sleep(min(2 * attempt, 6))


#         return {"status": "fail", "count": 0, "error": last_err or "unknown error"}
import asyncio
import re
from typing import Any, Dict, Optional

URL_RE = re.compile(r'(https?://[^\s"\'\)]+)', re.I)

async def send_enrichment_requests(
    page_name: str,
    target_url: Optional[str] = None,          # <- now optional (backward compatible)
    base: str = "http://localhost:8001",
    wait_seconds: float = 3.0,
    retries: int = 3,
    story: Optional[str] = None,               # <- optional: we can auto-extract URL from a user story
) -> Dict[str, Any]:
    """
    Ask the enrichment service to set the page name and capture DOM metadata.

    Behavior:
      - If target_url is provided: try to launch/navigate via /launch-browser, then capture.
      - Else if story is provided: extract the first https? URL from the story and use it.
      - Else: skip launch (assumes your backend has already opened the right page),
              still sets page name and captures DOM.
      - If backend exposes /current-url and target_url is still None, we'll try to use that.

    Works with http/https targets and keeps HTTPS errors ignored when launching.
    """
    from httpx import AsyncClient, HTTPStatusError, RequestError

    # Resolve target_url if not passed
    if not target_url and story:
        m = URL_RE.search(story)
        if m:
            target_url = m.group(1).rstrip(".,);")

    async with AsyncClient(timeout=None) as client:
        # If still no target_url, try asking the backend (optional endpoint)
        if not target_url:
            try:
                r_cur = await client.get(f"{base}/current-url")
                if r_cur.status_code == 200:
                    jd = r_cur.json()
                    if isinstance(jd, dict) and jd.get("url"):
                        target_url = jd["url"]
            except Exception:
                # It's fine if /current-url doesn't exist
                pass

        # Normalize scheme if we got a URL
        if target_url and not (target_url.startswith("http://") or target_url.startswith("https://")):
            target_url = "https://" + target_url  # default to https if scheme missing

        # 0) Launch & navigate only if we have a URL; otherwise skip this step
        if target_url:
            try:
                r_launch = await client.post(
                    f"{base}/launch-browser",
                    json={
                        "url": target_url,
                        "page_name": page_name,
                        "headless": False,
                        "ignore_https_errors": True,
                        "wait_until": "networkidle",
                    },
                )
                # Accept 200 or 404 (some servers don't implement /launch-browser)
                if r_launch.status_code not in (200, 404):
                    r_launch.raise_for_status()
            except RequestError as e:
                # Non-fatal: you may still want to proceed to set page name and capture
                # if your page is already open on the backend.
                # Return early if you prefer strict failure on launch.
                return {"status": "fail", "count": 0, "error": f"launch error: {e!r}"}

        # 1) Set the page name (your matcher relies on this)
        try:
            r = await client.post(
                f"{base}/set-current-page-name",
                json={"page_name": page_name},
            )
            r.raise_for_status()
        except (HTTPStatusError, RequestError) as e:
            return {"status": "fail", "count": 0, "error": f"set page name: {e!r}"}

        # 2) Let the backend settle
        await asyncio.sleep(wait_seconds)

        # 3) Capture with retries
        last_err: Optional[str] = None
        for attempt in range(1, retries + 1):
            try:
                resp = await client.post(
                    f"{base}/capture-dom-from-client",
                    json={"page_name": page_name}
                )
                resp.raise_for_status()
                try:
                    data = resp.json()
                    # Optionally poll a "latest" endpoint if capture returns empty
                    if not data or (isinstance(data, dict) and data.get("count", 0) == 0):
                        for _ in range(10):
                            await asyncio.sleep(0.5)
                            latest = await client.get(f"{base}/latest-match-result")
                            if latest.status_code == 200:
                                jd = latest.json()
                                if jd:
                                    return jd
                    return data
                except Exception as e:
                    return {"status": "fail", "count": 0, "error": f"invalid JSON: {e!r}"}
            except HTTPStatusError as e:
                sc = getattr(e.response, "status_code", "??")
                txt = getattr(e.response, "text", "")
                last_err = f"HTTP {sc}: {txt!r}"
            except RequestError as e:
                last_err = f"network error: {e!r}"

            # backoff
            await asyncio.sleep(min(2 * attempt, 6))

        return {"status": "fail", "count": 0, "error": last_err or "unknown error"}



@router.post("/launch-browser")
async def launch_browser(req: LaunchRequest):
    global PLAYWRIGHT, BROWSER, PAGE
 
    try:
        PLAYWRIGHT = await async_playwright().start()
        BROWSER = await PLAYWRIGHT.chromium.launch(headless=False, slow_mo=100)
        PAGE = await BROWSER.new_page()
        await PAGE.goto(req.url)

        async def send_enrichment_wrapper(source, page_name):
            print("[DEBUG] Triggering enrichment for:", page_name)
            result = await send_enrichment_requests(page_name)
            # print("[DEBUG] Got:", result.count," from send_enrichment_requests")
            return json.dumps(result)

        await PAGE.expose_binding("sendEnrichmentRequests", send_enrichment_wrapper)


        await PAGE.evaluate("""
            if (!window._ocrShortcutRegistered) {
                window._ocrShortcutRegistered = true;
                console.log('[SmartAI] Modal enrichment JS injected');

                const modal = document.createElement('div');
                modal.innerHTML = `
                    <div id="ocrModal" style="position:fixed;top:40%;left:50%;transform:translate(-50%,-50%);background:white;padding:20px;border:2px solid black;z-index:9999;display:none;">
                        <label>Enter Page Name:</label><br/>
                        <select id="pageDropdown" style="margin:5px;padding:5px;width:250px;"></select><br/>
                        <button onclick="triggerEnrichment()">Enrich</button>
                        <button onclick="document.getElementById('ocrModal').style.display='none'">Close</button>
                        <div id="enrichmentMessageBox" style="margin-top:10px;font-weight:bold;color:green;"></div>
                    </div>
                `;
                document.body.appendChild(modal);

                async function loadAvailablePages() {
                    try {
                        const res = await fetch('http://localhost:8001/available-pages');
                        const data = await res.json();
                        const dropdown = document.getElementById('pageDropdown');
                        dropdown.innerHTML = "";
                        for (const page of data.pages) {
                            const option = document.createElement("option");
                            option.value = page;
                            option.innerText = page;
                            dropdown.appendChild(option);
                        }
                    } catch (err) {
                        alert("❌ Failed to load available pages.");
                    }
                }

                
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
                        const modal = document.getElementById('ocrModal');
                        modal.style.display = 'block';
                        loadAvailablePages();
                    }
                });
            }
            """)
        
        return {
            "message": f"✅ Browser launched and navigated to {req.url}. Press Alt+E to enrich any page."
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/set-current-page-name")
async def set_page_name(req: PageNameSetRequest):
    global CURRENT_PAGE_NAME
    CURRENT_PAGE_NAME = normalize_page_name(req.page_name)
    print(f'"message": f"✅ Page name set to: {CURRENT_PAGE_NAME}"')
    return

@router.post("/capture-dom-from-client")
async def capture_from_keyboard(_: CaptureRequest):
    global PAGE, CURRENT_PAGE_NAME
    try:
        page_name = CURRENT_PAGE_NAME
        print(f"[INFO] Enrichment triggered for: {page_name}")
        if PAGE.is_closed():
            raise HTTPException(status_code=500, detail="❌ Cannot extract. Page is already closed.")
        # print('10')
        dom_data = await extract_dom_metadata(PAGE, page_name)
        # print('11 ', dom_data.count)

        print("[DEBUG] DOM elements extracted:", len(dom_data))

        ocr_data = collection.get(where={"page_name": page_name})["metadatas"]
        
        # Create folder for debug metadata dump added by subhankar
        debug_metadata_dir = Path("generated_runs") / "src" / "ocr-dom-metadata"
        debug_metadata_dir.mkdir(parents=True, exist_ok=True)                 
        # Write DOM data as raw text added by subhankar
        with open(debug_metadata_dir / f"dom_data_{page_name}.txt", "w", encoding="utf-8") as f:
            f.write(pprint.pformat(dom_data))
        # Write OCR data as raw text added by subhankar
        with open(debug_metadata_dir / f"ocr_data_{page_name}.txt", "w", encoding="utf-8") as f:
            f.write(pprint.pformat(ocr_data))
        
        updated_matches = match_and_update(ocr_data, dom_data, collection)
    
        # Write after_match_and_update data as raw text added by subhankar
        with open(debug_metadata_dir / f"after_match_and_update{page_name}.txt", "w", encoding="utf-8") as f:
            f.write(pprint.pformat(updated_matches))
    
        standardized_matches = [
            build_standard_metadata(m, page_name, image_path="", source_url=PAGE.url)
            for m in updated_matches
        ]
        
        # Write standardized_matches data as raw text added by subhankar
        with open(debug_metadata_dir / f"standardized_matchesd{page_name}.txt", "w", encoding="utf-8") as f:
            f.write(pprint.pformat(standardized_matches))
    
        set_last_match_result(standardized_matches)
    
        # Save enriched metadata as JSON
        metadata_dir = Path("generated_runs") / "src" / "metadata"
        metadata_dir.mkdir(parents=True, exist_ok=True)
        outfile = metadata_dir / f"after_enrichment_{page_name}.json"
        with open(outfile, "w", encoding="utf-8") as f:
            json.dump(standardized_matches, f, indent=2)
    
        # Save ALL current ChromaDB metadata as one file in the same folder
        chroma_all_data = collection.get()
        chroma_all_metadatas = chroma_all_data.get("metadatas", [])
        all_chroma_file = metadata_dir / "after_enrichment.json"
        with open(all_chroma_file, "w", encoding="utf-8") as f:
            json.dump(chroma_all_metadatas, f, indent=2)
    
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
    
@router.get("/available-pages")
async def list_page_names():
    try:
        records = collection.get()
        page_names = list({meta.get("page_name", "unknown") for meta in records.get("metadatas", [])})
        return {"pages": page_names}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.on_event("shutdown")
async def shutdown_browser():
    global PLAYWRIGHT
    if PLAYWRIGHT:
        await PLAYWRIGHT.stop()
 
@router.get("/latest-match-result")
async def get_latest_match_result():
    try:
        records = collection.get()
        matched = [r for r in records.get("metadatas", []) if r.get("dom_matched") is True]
        return {
            "status": "success",
            "matched_elements": matched,
            "count": len(matched)
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reset-enrichment/{page_name}")
async def reset_enrichment_api(page_name: str):
    reset_enriched(page_name)
    return {"success": True, "message": f"Enrichment reset for {page_name}"}


__all__ = ["router"]


