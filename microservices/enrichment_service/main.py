from fastapi import APIRouter, HTTPException, FastAPI
from pydantic import BaseModel
import chromadb
from logic.manual_capture_mode import extract_dom_metadata, match_and_update, get_last_match_result, set_last_match_result
from utils.match_utils import normalize_page_name
from utils.file_utils import build_standard_metadata
from playwright.async_api import async_playwright, Page, Browser
import json
import os
from pathlib import Path
import pprint
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Enrichment Service")

# ChromaDB setup
chroma_client = chromadb.HttpClient(host=os.getenv("CHROMA_DB_HOST", "chromadb"), port=os.getenv("CHROMA_DB_PORT", "8000"))

try:
    collection = chroma_client.get_or_create_collection(name="element_metadata")
except Exception as e:
    print(f"Error connecting to ChromaDB or getting collection: {e}")
    collection = None # Handle case where ChromaDB is not available

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

async def send_enrichment_requests(page_name: str):
    # This function was originally making HTTP calls to the backend itself.
    # Now, it will directly call the internal functions.
    global CURRENT_PAGE_NAME
    CURRENT_PAGE_NAME = normalize_page_name(page_name)
    print(f'"message": f"✅ Page name set to: {CURRENT_PAGE_NAME}"')

    try:
        page_name = CURRENT_PAGE_NAME
        print(f"[INFO] Enrichment triggered for: {page_name}")
        if PAGE.is_closed():
            raise HTTPException(status_code=500, detail="❌ Cannot extract. Page is already closed.")
        dom_data = await extract_dom_metadata(PAGE, page_name)

        print("[DEBUG] DOM elements extracted:", len(dom_data))

        ocr_data = collection.get(where={"page_name": page_name})["metadatas"]
        
        debug_metadata_dir = Path("generated_runs") / "src" / "ocr-dom-metadata"
        debug_metadata_dir.mkdir(parents=True, exist_ok=True)                 
        with open(debug_metadata_dir / f"dom_data_{page_name}.txt", "w", encoding="utf-8") as f:
            f.write(pprint.pformat(dom_data))
        with open(debug_metadata_dir / f"ocr_data_{page_name}.txt", "w", encoding="utf-8") as f:
            f.write(pprint.pformat(ocr_data))
        
        updated_matches = match_and_update(ocr_data, dom_data, collection)
    
        with open(debug_metadata_dir / f"after_match_and_update{page_name}.txt", "w", encoding="utf-8") as f:
            f.write(pprint.pformat(updated_matches))
    
        standardized_matches = [
            build_standard_metadata(m, page_name, image_path="", source_url=PAGE.url)
            for m in updated_matches
        ]
        
        with open(debug_metadata_dir / f"standardized_matchesd{page_name}.txt", "w", encoding="utf-8") as f:
            f.write(pprint.pformat(standardized_matches))
    
        set_last_match_result(standardized_matches)
    
        metadata_dir = Path("generated_runs") / "src" / "metadata"
        metadata_dir.mkdir(parents=True, exist_ok=True)
        outfile = metadata_dir / f"after_enrichment_{page_name}.json"
        with open(outfile, "w", encoding="utf-8") as f:
            json.dump(standardized_matches, f, indent=2)
    
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

@app.post("/launch-browser")
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
                        const res = await fetch('http://localhost:8004/available-pages'); // Updated port
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

@app.get("/available-pages")
async def list_page_names():
    try:
        records = collection.get()
        page_names = list({meta.get("page_name", "unknown") for meta in records.get("metadatas", [])})
        return {"pages": page_names}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.on_event("shutdown")
async def shutdown_browser():
    global PLAYWRIGHT
    if PLAYWRIGHT:
        await PLAYWRIGHT.stop()
 
@app.get("/latest-match-result")
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004) # Using a different port for the new service