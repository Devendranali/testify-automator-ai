import traceback
from fastapi.responses import JSONResponse
from fastapi.requests import Request
from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
import httpx








import sys
import asyncio
import os
import subprocess
import logging
from dotenv import load_dotenv

load_dotenv()

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "0"
    try:
        subprocess.run(["playwright", "install", "chromium"], check=True)
    except Exception as e:
        print("Playwright install failed:", e)

# ✅ FastAPI app initialization
app = FastAPI(title="AI Test Extractor")


origins = [
    "http://localhost:3000",
    "https://www.saucedemo.com",
    "http://localhost:3001",
    "http://localhost:3001",
]


app.add_middleware(
    CORSMiddleware,
    # allow_origins=origins,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Global exception handler with CORS headers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    print("❌ Unhandled Exception:")
    traceback.print_exc()

    
    headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Credentials": "true",
    }

    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)},
        headers=headers
    )

# ✅ Include API routers

@app.post("/upload-image")
async def upload_image_proxy(request: Request):
    image_text_service_url = os.getenv("IMAGE_TEXT_SERVICE_URL")
    if not image_text_service_url:
        raise HTTPException(status_code=500, detail="IMAGE_TEXT_SERVICE_URL not configured")

    async with httpx.AsyncClient() as client:
        # Forward the request including headers and body
        # FastAPI's Request object can be directly used to stream the body
        # and headers can be copied.
        # We need to reconstruct the form data for httpx
        form_data = await request.form()
        files = []
        data = {}
        for field_name, field_value in form_data.items():
            if isinstance(field_value, UploadFile):
                files.append((field_name, (field_value.filename, field_value.file, field_value.content_type)))
            else:
                data[field_name] = field_value

        try:
            response = await client.post(f"{image_text_service_url}/upload-image", data=data, files=files, timeout=None)
            response.raise_for_status()
            return JSONResponse(content=response.json(), status_code=response.status_code)
        except httpx.RequestError as e:
            raise HTTPException(status_code=500, detail=f"Proxy request failed: {e}")
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=f"Service responded with error: {e.response.text}")

app.include_router(generate_from_story_router)

@app.post("/launch-browser")
async def launch_browser_proxy(req: Request):
    enrichment_service_url = os.getenv("ENRICHMENT_SERVICE_URL")
    if not enrichment_service_url:
        raise HTTPException(status_code=500, detail="ENRICHMENT_SERVICE_URL not configured")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(f"{enrichment_service_url}/launch-browser", json=await req.json(), timeout=None)
            response.raise_for_status()
            return JSONResponse(content=response.json(), status_code=response.status_code)
        except httpx.RequestError as e:
            raise HTTPException(status_code=500, detail=f"Proxy request failed: {e}")
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=f"Service responded with error: {e.response.text}")

@app.post("/set-current-page-name")
async def set_current_page_name_proxy(req: Request):
    enrichment_service_url = os.getenv("ENRICHMENT_SERVICE_URL")
    if not enrichment_service_url:
        raise HTTPException(status_code=500, detail="ENRICHMENT_SERVICE_URL not configured")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(f"{enrichment_service_url}/set-current-page-name", json=await req.json(), timeout=None)
            response.raise_for_status()
            return JSONResponse(content=response.json(), status_code=response.status_code)
        except httpx.RequestError as e:
            raise HTTPException(status_code=500, detail=f"Proxy request failed: {e}")
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=f"Service responded with error: {e.response.text}")

@app.post("/capture-dom-from-client")
async def capture_dom_from_client_proxy(req: Request):
    enrichment_service_url = os.getenv("ENRICHMENT_SERVICE_URL")
    if not enrichment_service_url:
        raise HTTPException(status_code=500, detail="ENRICHMENT_SERVICE_URL not configured")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(f"{enrichment_service_url}/capture-dom-from-client", json=await req.json(), timeout=None)
            response.raise_for_status()
            return JSONResponse(content=response.json(), status_code=response.status_code)
        except httpx.RequestError as e:
            raise HTTPException(status_code=500, detail=f"Proxy request failed: {e}")
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=f"Service responded with error: {e.response.text}")

@app.get("/available-pages")
async def available_pages_proxy(req: Request):
    enrichment_service_url = os.getenv("ENRICHMENT_SERVICE_URL")
    if not enrichment_service_url:
        raise HTTPException(status_code=500, detail="ENRICHMENT_SERVICE_URL not configured")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{enrichment_service_url}/available-pages", timeout=None)
            response.raise_for_status()
            return JSONResponse(content=response.json(), status_code=response.status_code)
        except httpx.RequestError as e:
            raise HTTPException(status_code=500, detail=f"Proxy request failed: {e}")
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=f"Service responded with error: {e.response.text}")

@app.get("/latest-match-result")
async def latest_match_result_proxy(req: Request):
    enrichment_service_url = os.getenv("ENRICHMENT_SERVICE_URL")
    if not enrichment_service_url:
        raise HTTPException(status_code=500, detail="ENRICHMENT_SERVICE_URL not configured")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{enrichment_service_url}/latest-match-result", timeout=None)
            response.raise_for_status()
            return JSONResponse(content=response.json(), status_code=response.status_code)
        except httpx.RequestError as e:
            raise HTTPException(status_code=500, detail=f"Proxy request failed: {e}")
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=f"Service responded with error: {e.response.text}")


@app.post("/rag/run-generated-story-test")
async def run_generated_story_test_proxy(request: Request):
    rag_service_url = os.getenv("RAG_SERVICE_URL")
    if not rag_service_url:
        raise HTTPException(status_code=500, detail="RAG_SERVICE_URL not configured")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(f"{rag_service_url}/rag/run-generated-story-test", json=await request.json(), timeout=None)
            response.raise_for_status()
            return JSONResponse(content=response.json(), status_code=response.status_code)
        except httpx.RequestError as e:
            raise HTTPException(status_code=500, detail=f"Proxy request failed: {e}")
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=f"Service responded with error: {e.response.text}")


@app.get("/debug/export-chromadb")
async def export_chroma_data_proxy(request: Request, record_type: str = None, locator_null: bool = False, page_name: str = None, as_file: bool = False):
    chroma_debug_service_url = os.getenv("CHROMA_DEBUG_SERVICE_URL")
    if not chroma_debug_service_url:
        raise HTTPException(status_code=500, detail="CHROMA_DEBUG_SERVICE_URL not configured")

    params = {
        "record_type": record_type,
        "locator_null": locator_null,
        "page_name": page_name,
        "as_file": as_file
    }
    # Filter out None values
    params = {k: v for k, v in params.items() if v is not None}

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{chroma_debug_service_url}/debug/export-chromadb", params=params, timeout=None)
            response.raise_for_status()
            if as_file:
                # For file responses, return as is
                return FileResponse(response.content, media_type=response.headers['content-type'], filename="chromadb_export.json")
            return JSONResponse(content=response.json(), status_code=response.status_code)
        except httpx.RequestError as e:
            raise HTTPException(status_code=500, detail=f"Proxy request failed: {e}")
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=f"Service responded with error: {e.response.text}")



@app.post("/rag/generate-from-story")
async def generate_from_story_proxy(req: Request):
    test_generation_service_url = os.getenv("TEST_GENERATION_SERVICE_URL")
    if not test_generation_service_url:
        raise HTTPException(status_code=500, detail="TEST_GENERATION_SERVICE_URL not configured")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(f"{test_generation_service_url}/rag/generate-from-story", json=await req.json(), timeout=None)
            response.raise_for_status()
            return JSONResponse(content=response.json(), status_code=response.status_code)
        except httpx.RequestError as e:
            raise HTTPException(status_code=500, detail=f"Proxy request failed: {e}")
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=f"Service responded with error: {e.response.text}")



@app.post("/rag/generate-page-methods")
async def generate_page_methods_proxy(req: Request):
    page_method_generation_service_url = os.getenv("PAGE_METHOD_GENERATION_SERVICE_URL")
    if not page_method_generation_service_url:
        raise HTTPException(status_code=500, detail="PAGE_METHOD_GENERATION_SERVICE_URL not configured")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(f"{page_method_generation_service_url}/rag/generate-page-methods", json=await req.json(), timeout=None)
            response.raise_for_status()
            return JSONResponse(content=response.json(), status_code=response.status_code)
        except httpx.RequestError as e:
            raise HTTPException(status_code=500, detail=f"Proxy request failed: {e}")
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=f"Service responded with error: {e.response.text}")


@app.post("/rag/generate-from-manual-testcase")
async def generate_from_manual_testcase_proxy(req: Request):
    manual_testcase_generation_service_url = os.getenv("MANUAL_TESTCASE_GENERATION_SERVICE_URL")
    if not manual_testcase_generation_service_url:
        raise HTTPException(status_code=500, detail="MANUAL_TESTCASE_GENERATION_SERVICE_URL not configured")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(f"{manual_testcase_generation_service_url}/rag/generate-from-manual-testcase", json=await req.json(), timeout=None)
            response.raise_for_status()
            return JSONResponse(content=response.json(), status_code=response.status_code)
        except httpx.RequestError as e:
            raise HTTPException(status_code=500, detail=f"Proxy request failed: {e}")
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=f"Service responded with error: {e.response.text}")



@app.post("/rag/generate-from-method")
async def generate_from_method_proxy(req: Request):
    testcase_generation_service_url = os.getenv("TESTCASE_GENERATION_SERVICE_URL")
    if not testcase_generation_service_url:
        raise HTTPException(status_code=500, detail="TESTCASE_GENERATION_SERVICE_URL not configured")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(f"{testcase_generation_service_url}/rag/generate-from-method", json=await req.json(), timeout=None)
            response.raise_for_status()
            return JSONResponse(content=response.json(), status_code=response.status_code)
        except httpx.RequestError as e:
            raise HTTPException(status_code=500, detail=f"Proxy request failed: {e}")
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=f"Service responded with error: {e.response.text}")


@app.post("/rag/generate-from-method")
async def generate_from_method_proxy(req: Request):
    testcase_generation_service_url = os.getenv("TESTCASE_GENERATION_SERVICE_URL")
    if not testcase_generation_service_url:
        raise HTTPException(status_code=500, detail="TESTCASE_GENERATION_SERVICE_URL not configured")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(f"{testcase_generation_service_url}/rag/generate-from-method", json=await req.json(), timeout=None)
            response.raise_for_status()
            return JSONResponse(content=response.json(), status_code=response.status_code)
        except httpx.RequestError as e:
            raise HTTPException(status_code=500, detail=f"Proxy request failed: {e}")
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=f"Service responded with error: {e.response.text}")

app.include_router(manual_add_metadata)


# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run("main:app", host="127.0.0.1", port=8001, reload=False)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,  # 👈 Show only INFO and above
        format="%(levelname)s: %(message)s"
    )    
    # Reduce noise from third-party libraries
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("chromadb").setLevel(logging.WARNING)
    logging.getLogger("PIL").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("python_multipart").setLevel(logging.WARNING)
    # logging.getLogger("uvicorn").setLevel(logging.INFO)            # Default server logs
    # logging.getLogger("uvicorn.access").setLevel(logging.WARNING)  # Access logs
    # logging.getLogger("httpcore").setLevel(logging.WARNING)        # HTTP-level logs
    logging.getLogger("watchfiles").setLevel(logging.ERROR)
    logging.getLogger("tqdm").setLevel(logging.WARNING)

    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8001, reload=False, log_level="info")
