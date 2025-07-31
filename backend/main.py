import traceback
from fastapi.responses import JSONResponse
from fastapi.requests import Request
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apis.image_text_api import router as image_router
from apis.chroma_debug_api import router as debug_chroma_export_router
from apis.enrichment_api import router as enrichment_router
from apis.rag_testcase_runner import router as rag_router
from apis.generate_from_story import router as generate_from_story_router
from apis.generate_page_methods import router as generate_page_methods_router
from apis.generate_from_manual_testcases import router as generate_from_manual_testcase_router
from apis.generate_testcases_from_methods import router as generate_test_code_from_methods_router
from apis.manual_add_metadata import router as manual_add_metadata
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


# origins = [
#     "http://localhost:3000",
#     "https://www.saucedemo.com",
#     "http://localhost:3001",
#     "http://localhost:3001",
# ]


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
app.include_router(image_router)
app.include_router(generate_from_story_router)
app.include_router(enrichment_router)
app.include_router(rag_router)
app.include_router(debug_chroma_export_router)
app.include_router(generate_from_manual_testcase_router)
app.include_router(generate_page_methods_router)
app.include_router(generate_test_code_from_methods_router)
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
