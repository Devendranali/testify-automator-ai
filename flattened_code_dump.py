

# === FILE: main.py ===
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



# === FILE: main_agent.py ===
# main.py

from orchestrator.orchestrator import send_message

# EXAMPLE: generate a method for a textbox
element_spec = {
    "ocr_type": "textbox",
    "label_text": "Username",
    "unique_name": "saucedemo_login_username_textbox"
}

response = send_message("python", "generate_method", element_spec)
print("[Python Agent] Generated Method:")
print(response.payload)

# EXAMPLE: generate a test
test_case_spec = {
    "steps": [
        "enter_username(page, 'standard_user')",
        "enter_password(page, 'secret_sauce')",
        "click_login(page)"
    ]
}

test_response = send_message("python", "generate_test", test_case_spec)
print("\n[Python Agent] Generated Test:")
print(test_response.payload)



# === FILE: README.md ===
############# Branches Information #############

# Main Branch :-

## Contains the Open AI based OCR data extractor in Image_text_extractor


# feature/v1-dev :-

## Contains the Tesseract based OCR Data extractor in Image_text_extractor

# feature/version-2 :-

## Contains the new code format which uses only locator not ocr and has a SmartAI concept used during methods generation.




# === FILE: requirements.txt ===
annotated-types==0.7.0
anyio==4.9.0
asgiref==3.8.1
attrs==25.3.0
backoff==2.2.1
bcrypt==4.3.0
beautifulsoup4==4.13.4
bs4==0.0.2
build==1.2.2.post1
cachetools==5.5.2
certifi==2025.4.26
charset-normalizer==3.4.2
chromadb==1.0.12
click==8.2.1
colorama==0.4.6
coloredlogs==15.0.1
contourpy==1.3.2
cycler==0.12.1
distro==1.9.0
durationpy==0.10
et_xmlfile==2.0.0
fastapi==0.115.9
filelock==3.18.0
flatbuffers==25.2.10
fonttools==4.58.2
fsspec==2025.5.1
google-auth==2.40.3
googleapis-common-protos==1.70.0
gpt==0.2
greenlet==3.2.3
grpcio==1.73.0
h11==0.16.0
httpcore==1.0.9
httptools==0.6.4
httpx==0.28.1
huggingface-hub==0.33.0
humanfriendly==10.0
idna==3.10
importlib_metadata==8.7.0
importlib_resources==6.5.2
iniconfig==2.1.0
Jinja2==3.1.6
jiter==0.10.0
joblib==1.5.1
jsonschema==4.24.0
jsonschema-specifications==2025.4.1
kiwisolver==1.4.8
kubernetes==33.1.0
markdown-it-py==3.0.0
MarkupSafe==3.0.2
matplotlib==3.10.3
mdurl==0.1.2
mmh3==5.1.0
mpmath==1.3.0
networkx==3.5
numpy==2.3.0
oauthlib==3.2.2
onnxruntime==1.22.0
openai==1.86.0
opencv-python==4.11.0.86
openpyxl==3.1.5
opentelemetry-api==1.34.1
opentelemetry-exporter-otlp-proto-common==1.34.1
opentelemetry-exporter-otlp-proto-grpc==1.34.1
opentelemetry-instrumentation==0.55b1
opentelemetry-instrumentation-asgi==0.55b1
opentelemetry-instrumentation-fastapi==0.55b1
opentelemetry-proto==1.34.1
opentelemetry-sdk==1.34.1
opentelemetry-semantic-conventions==0.55b1
opentelemetry-util-http==0.55b1
orjson==3.10.18
overrides==7.7.0
packaging==25.0
pandas==2.3.0
pathlib==1.0.1
pillow==11.2.1
playwright==1.52.0
pluggy==1.6.0
posthog==4.7.0
protobuf==5.29.5
psutil==7.0.0
py-cpuinfo==9.0.0
pyasn1==0.6.1
pyasn1_modules==0.4.2
pydantic==2.11.5
pydantic_core==2.33.2
pyee==13.0.0
Pygments==2.19.1
pyparsing==3.2.3
PyPika==0.48.9
pyproject_hooks==1.2.0
pyreadline3==3.5.4
pytesseract==0.3.13
pytest==8.4.1
pytest-base-url==2.1.0
pytest-playwright==0.7.0
python-dateutil==2.9.0.post0
python-dotenv==1.1.0
python-multipart==0.0.20
python-slugify==8.0.4
pytz==2025.2
PyYAML==6.0.2
RapidFuzz==3.13.0
referencing==0.36.2
regex==2024.11.6
requests==2.32.4
requests-oauthlib==2.0.0
rich==14.0.0
rpds-py==0.25.1
rsa==4.9.1
safetensors==0.5.3
scikit-learn==1.7.0
scipy==1.15.3
sentence-transformers==4.1.0
setuptools==80.9.0
shellingham==1.5.4
six==1.17.0
sniffio==1.3.1
soupsieve==2.7
starlette==0.45.3
sympy==1.14.0
tenacity==9.1.2
text-unidecode==1.3
threadpoolctl==3.6.0
tokenizers==0.21.1
torch==2.7.1
torchvision==0.22.1
tqdm==4.67.1
transformers==4.52.4
typer==0.16.0
typing-inspection==0.4.1
typing_extensions==4.14.0
tzdata==2025.2
ultralytics==8.3.153
ultralytics-thop==2.0.14
urllib3==2.4.0
uvicorn==0.34.3
watchfiles==1.0.5
websocket-client==1.8.0
websockets==15.0.1
wrapt==1.17.2
zipp==3.23.0



# === FILE: test_api.py ===
# apis/test_ui_vision_api.py

from fastapi import APIRouter, UploadFile, File, HTTPException
import zipfile
import tempfile
import os
import base64
from PIL import Image
import openai
import logging

from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

router = APIRouter()

# PROMPT = """ You are an expert computer vision model using OpenAI's capabilities.

# Your task is to analyze a given screenshot of a user interface (UI) and classify **every visible element** without summarization.

# Please follow these strict rules:

# 1. For every visible part of the image:
#    - Identify **all labels**, **buttons**, **descriptive paragraphs**, **headers**, **titles**, **dropdown values**, and **prices**.

# 2. For each identified element:
#    - Classify it into one of the following types: `textbox`, `button`, `checkbox`, `select`, or `label`.
#    - Output in this format: `<label text> - <element type>`

# 3. Preserve full text:
#    - Do NOT shorten, summarize, or omit any label or paragraph text.
#    - If a label has multiple lines (like product descriptions), output the entire text as one label.

# 4. Maintain visual order:
#    - Traverse from top-left to bottom-right in a vertical reading sequence.

# 5. Output formatting:
#    - Return the result as a plain newline-separated list.
#    - Do NOT explain anything.
#    - Do NOT include markdown, bullets, or JSON.
#    - Output only raw lines like: `Label Text - type`"""

PROMPT = """You are an expert computer vision model using OpenAI's capabilities.

Your task is to analyze a given screenshot of a user interface (UI) and extract every visible UI element, accurately identifying its type and intent.

1. Element Extraction:
   - Extract ALL visible UI text from the image, including:
     • Input fields
     • Buttons
     • Labels (including credentials, instructions)
     • Dropdowns, checkboxes

2. Element Classification:
   - For each element, output:
     • Label text (exact as visible)
     • Element type (one of: `textbox`, `button`, `label`, `checkbox`, `select`)
     • Intent (like: `login`, `username`, `password`, `price_label`, `submit`, `add_to_cart`, `password_info`, `username_info`, etc.)

   - For credentials or user types like `standard_user`, `secret_sauce`, assign type as `label` and use intent like `username_info`, `password_info`.

3. Format:
   - Each element on its own line:
     <label text> - <element type> - <intent>

4. Rules:
   - Do NOT rephrase or skip lines.
   - Preserve punctuation, line breaks.
   - Traverse from top-left to bottom-right.

5. Only output newline-separated lines like:
   Username - textbox - login
   Login - button - login
   secret_sauce - label - password_info
"""


@router.post("/test-ui-vision")
async def test_ui_vision(zipfile_upload: UploadFile = File(...)):
    if not zipfile_upload.filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="Please upload a .zip file")

    results = {}

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp_zip:
            tmp_zip.write(await zipfile_upload.read())
            tmp_zip_path = tmp_zip.name
            # logger.debug(f"📦 Temp ZIP saved at: {tmp_zip_path}")

        with zipfile.ZipFile(tmp_zip_path, 'r') as zip_ref:
            with tempfile.TemporaryDirectory() as extract_dir:
                zip_ref.extractall(extract_dir)
                # logger.debug(f"📂 Extracted files to: {extract_dir}")

                image_files = [
                    os.path.join(extract_dir, f)
                    for f in zip_ref.namelist()
                    if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))
                ]

                for image_path in image_files:
                    with open(image_path, "rb") as img_file:
                        image_base64 = base64.b64encode(img_file.read()).decode("utf-8")

                    # logger.debug(f"🧠 Sending image: {os.path.basename(image_path)} to OpenAI")

                    try:
                        client = openai.OpenAI()

                        response = client.chat.completions.create(
                            model="gpt-4o",
                            messages=[
                                {
                                    "role": "user",
                                    "content": [
                                        {"type": "text", "text": PROMPT},
                                        {
                                            "type": "image_url",
                                            "image_url": {
                                                "url": f"data:image/png;base64,{image_base64}"
                                            }
                                        }
                                    ]
                                }
                            ],
                            max_tokens=500
                        )

                        output = response.choices[0].message.content.strip()
                        results[os.path.basename(image_path)] = output
                        # logger.debug(f"✅ GPT-4o Output for {os.path.basename(image_path)}:\n{output}")

                    except Exception as gpt_error:
                        # logger.error(f"❌ Failed on {image_path}: {gpt_error}")
                        results[os.path.basename(image_path)] = f"ERROR: {str(gpt_error)}"

    except Exception as e:
        logger.error("❌ Error processing uploaded ZIP:", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

    return {"status": "success", "results": results}

if __name__ == "__main__":
    from fastapi import FastAPI
    import uvicorn

    app = FastAPI()
    app.include_router(router)

    uvicorn.run(app, host="127.0.0.1", port=8005, reload=False)




# === FILE: upload_image_logs.txt ===
2025-06-12 15:28:08,640 - DEBUG - 📷 Processing image: untitled.png
2025-06-12 15:28:13,582 - INFO - 📄 Ordered images logged to data/image_order.json
2025-06-12 15:47:11,040 - DEBUG - 📷 Processing image: untitled.png
2025-06-12 15:47:16,025 - INFO - 📄 Ordered images logged to data/image_order.json
2025-06-12 17:34:29,124 - DEBUG - 📷 Processing image: untitled.png
2025-06-12 17:34:36,690 - INFO - 📄 Ordered images logged to data/image_order.json
2025-06-12 17:54:33,781 - DEBUG - 📷 Processing image: untitled.png
2025-06-12 17:54:37,997 - INFO - 📄 Ordered images logged to data/image_order.json
2025-06-12 17:55:00,869 - DEBUG - 📷 Processing image: untitled.png
2025-06-12 17:55:05,585 - INFO - 📄 Ordered images logged to data/image_order.json
2025-06-13 12:20:01,526 - DEBUG - 📷 Processing image: screenshot (38).png
2025-06-13 12:20:13,824 - INFO - 📄 Ordered images logged to data/image_order.json
2025-06-13 12:27:22,317 - DEBUG - 📷 Processing image: screenshot (38).png
2025-06-13 12:27:32,971 - INFO - 📄 Ordered images logged to data/image_order.json
2025-06-13 15:09:25,559 - DEBUG - 📷 Processing image: screenshot (40).png
2025-06-13 15:09:36,606 - DEBUG - 📷 Processing image: screenshot (41).png
2025-06-13 15:09:47,652 - DEBUG - 📷 Processing image: screenshot (42).png
2025-06-13 15:09:53,279 - DEBUG - 📷 Processing image: screenshot (43).png
2025-06-13 15:10:11,001 - DEBUG - 📷 Processing image: screenshot (44).png
2025-06-13 15:10:19,255 - DEBUG - 📷 Processing image: screenshot (45).png
2025-06-13 15:10:24,977 - INFO - 📄 Ordered images logged to data/image_order.json
2025-06-13 16:00:02,239 - INFO - 🟢 Ordered images from frontend: ['Screenshot (45).png', 'Screenshot (44).png', 'Screenshot (43).png', 'Screenshot (42).png', 'Screenshot (41).png']
2025-06-13 16:00:02,305 - DEBUG - 📷 Processing image: Screenshot (45).png
2025-06-13 16:00:11,305 - DEBUG - 📷 Processing image: Screenshot (44).png
2025-06-13 16:00:21,802 - DEBUG - 📷 Processing image: Screenshot (43).png
2025-06-13 16:00:42,289 - DEBUG - 📷 Processing image: Screenshot (42).png
2025-06-13 16:00:47,398 - DEBUG - 📷 Processing image: Screenshot (41).png
2025-06-13 16:00:50,030 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-06-13 16:00:50,032 - INFO - 📄 Ordered images logged to data/image_order.json
2025-06-13 16:02:21,265 - INFO - 🟢 Ordered images from frontend: ['Screenshot (41).png', 'Screenshot (42).png', 'Screenshot (43).png', 'Screenshot (44).png', 'Screenshot (45).png']
2025-06-13 16:02:21,314 - DEBUG - 📷 Processing image: Screenshot (41).png
2025-06-13 16:02:38,300 - DEBUG - 📷 Processing image: Screenshot (42).png
2025-06-13 16:03:03,647 - DEBUG - 📷 Processing image: Screenshot (43).png
2025-06-13 16:03:10,696 - DEBUG - 📷 Processing image: Screenshot (44).png
2025-06-13 16:03:21,983 - DEBUG - 📷 Processing image: Screenshot (45).png
2025-06-13 16:03:27,121 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-06-13 16:03:27,122 - INFO - 📄 Ordered images logged to data/image_order.json
2025-06-13 17:16:28,709 - INFO - 🟢 Ordered images from frontend: ['Screenshot (41).png', 'Screenshot (42).png', 'Screenshot (43).png', 'Screenshot (44).png', 'Screenshot (45).png']
2025-06-13 17:16:28,900 - DEBUG - 📷 Processing image: Screenshot (41).png
2025-06-13 17:16:40,982 - ERROR - ❌ Error in upload_image
Traceback (most recent call last):
  File "C:\Users\Suchandan\Desktop\VNC\testify-automator-ai\backend\apis\image_text_api.py", line 106, in upload_image
    chroma_collection.add(
    ~~~~~~~~~~~~~~~~~~~~~^
        ids=[metadata["id"]],
        ^^^^^^^^^^^^^^^^^^^^^
        documents=[metadata["text"]],
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        metadatas=[metadata]
        ^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "C:\Users\Suchandan\Desktop\VNC\testify-automator-ai\venv\Lib\site-packages\chromadb\api\models\Collection.py", line 89, in add
    self._client._add(
    ~~~~~~~~~~~~~~~~~^
        collection_id=self.id,
        ^^^^^^^^^^^^^^^^^^^^^^
    ...<6 lines>...
        database=self.database,
        ^^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "C:\Users\Suchandan\Desktop\VNC\testify-automator-ai\venv\Lib\site-packages\chromadb\api\rust.py", line 407, in _add
    return self.bindings.add(
           ~~~~~~~~~~~~~~~~~^
        ids,
        ^^^^
    ...<6 lines>...
        database,
        ^^^^^^^^^
    )
    ^
chromadb.errors.InternalError: Error getting collection: Database error: error returned from database: (code: 1) no such table: collections
2025-06-13 17:17:10,724 - INFO - 🟢 Ordered images from frontend: ['Screenshot (41).png', 'Screenshot (42).png', 'Screenshot (43).png', 'Screenshot (44).png', 'Screenshot (45).png']
2025-06-13 17:17:10,751 - DEBUG - 📷 Processing image: Screenshot (41).png
2025-06-13 17:17:19,399 - ERROR - ❌ Error in upload_image
Traceback (most recent call last):
  File "C:\Users\Suchandan\Desktop\VNC\testify-automator-ai\backend\apis\image_text_api.py", line 106, in upload_image
    chroma_collection.add(
    ~~~~~~~~~~~~~~~~~~~~~^
        ids=[metadata["id"]],
        ^^^^^^^^^^^^^^^^^^^^^
        documents=[metadata["text"]],
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        metadatas=[metadata]
        ^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "C:\Users\Suchandan\Desktop\VNC\testify-automator-ai\venv\Lib\site-packages\chromadb\api\models\Collection.py", line 89, in add
    self._client._add(
    ~~~~~~~~~~~~~~~~~^
        collection_id=self.id,
        ^^^^^^^^^^^^^^^^^^^^^^
    ...<6 lines>...
        database=self.database,
        ^^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "C:\Users\Suchandan\Desktop\VNC\testify-automator-ai\venv\Lib\site-packages\chromadb\api\rust.py", line 407, in _add
    return self.bindings.add(
           ~~~~~~~~~~~~~~~~~^
        ids,
        ^^^^
    ...<6 lines>...
        database,
        ^^^^^^^^^
    )
    ^
chromadb.errors.InternalError: Error getting collection: Database error: error returned from database: (code: 1) no such table: collections
2025-06-13 17:18:58,206 - INFO - 🟢 Ordered images from frontend: ['Screenshot (41).png', 'Screenshot (42).png', 'Screenshot (43).png', 'Screenshot (44).png', 'Screenshot (45).png']
2025-06-13 17:18:58,235 - DEBUG - 📷 Processing image: Screenshot (41).png
2025-06-13 17:19:08,181 - ERROR - ❌ Error in upload_image
Traceback (most recent call last):
  File "C:\Users\Suchandan\Desktop\VNC\testify-automator-ai\backend\apis\image_text_api.py", line 106, in upload_image
    chroma_collection.add(
    ~~~~~~~~~~~~~~~~~~~~~^
        ids=[metadata["id"]],
        ^^^^^^^^^^^^^^^^^^^^^
        documents=[metadata["text"]],
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        metadatas=[metadata]
        ^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "C:\Users\Suchandan\Desktop\VNC\testify-automator-ai\venv\Lib\site-packages\chromadb\api\models\Collection.py", line 89, in add
    self._client._add(
    ~~~~~~~~~~~~~~~~~^
        collection_id=self.id,
        ^^^^^^^^^^^^^^^^^^^^^^
    ...<6 lines>...
        database=self.database,
        ^^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "C:\Users\Suchandan\Desktop\VNC\testify-automator-ai\venv\Lib\site-packages\chromadb\api\rust.py", line 407, in _add
    return self.bindings.add(
           ~~~~~~~~~~~~~~~~~^
        ids,
        ^^^^
    ...<6 lines>...
        database,
        ^^^^^^^^^
    )
    ^
chromadb.errors.InternalError: Error getting collection: Database error: error returned from database: (code: 1) no such table: collections
2025-06-13 18:22:44,990 - INFO - 🟢 Ordered images from frontend: ['Screenshot (41).png', 'Screenshot (42).png', 'Screenshot (43).png', 'Screenshot (44).png', 'Screenshot (45).png']
2025-06-13 18:22:45,018 - DEBUG - 📷 Processing image: Screenshot (41).png
2025-06-13 18:22:49,261 - DEBUG - 📷 Processing image: Screenshot (42).png
2025-06-13 18:23:02,052 - DEBUG - 📷 Processing image: Screenshot (43).png
2025-06-13 18:23:15,973 - DEBUG - 📷 Processing image: Screenshot (44).png
2025-06-13 18:23:27,046 - DEBUG - 📷 Processing image: Screenshot (45).png
2025-06-13 18:23:35,811 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-06-13 18:23:35,813 - INFO - 📄 Ordered images logged to data/image_order.json
2025-06-13 18:43:35,650 - INFO - 🟢 Ordered images from frontend: ['Screenshot (41).png', 'Screenshot (43).png', 'Screenshot (44).png', 'Screenshot (45).png']
2025-06-13 18:43:35,714 - DEBUG - 📷 Processing image: Screenshot (41).png
2025-06-13 18:43:47,663 - DEBUG - 📷 Processing image: Screenshot (43).png
2025-06-13 18:43:58,075 - DEBUG - 📷 Processing image: Screenshot (44).png
2025-06-13 18:44:08,301 - DEBUG - 📷 Processing image: Screenshot (45).png
2025-06-13 18:44:09,717 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-06-13 18:44:09,726 - INFO - 📄 Ordered images logged to data/image_order.json
2025-06-14 17:36:19,910 - INFO - 🟢 Ordered images from frontend: ['Screenshot (41).png', 'Screenshot (42).png', 'Screenshot (44).png', 'Screenshot (45).png']
2025-06-14 17:36:20,015 - DEBUG - 📷 Processing image: Screenshot (41).png
2025-06-14 17:36:24,762 - DEBUG - 📷 Processing image: Screenshot (42).png
2025-06-14 17:36:42,751 - DEBUG - 📷 Processing image: Screenshot (44).png
2025-06-14 17:36:52,302 - DEBUG - 📷 Processing image: Screenshot (45).png
2025-06-14 17:36:57,475 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-06-14 17:36:57,476 - INFO - 📄 Ordered images logged to data/image_order.json
2025-06-16 10:36:25,335 - WARNING - ⚠️ Failed to parse ordered_images: Expecting value: line 1 column 1 (char 0)
2025-06-16 10:36:25,362 - DEBUG - 📷 Processing image: screenshot (40).png
2025-06-16 10:36:29,211 - INFO - 📄 Ordered images logged to data/image_order.json
2025-06-19 00:04:30,769 - INFO - 🟢 Ordered images from frontend: ['1_login.png', '2_inventory.png', '3_cart.png', '4_checkout_info.png', '5_checkout_overview.png']
2025-06-19 00:04:31,019 - DEBUG - 📷 Processing image: 1_login.png
2025-06-19 00:04:44,050 - DEBUG - 📷 Processing image: 2_inventory.png
2025-06-19 00:05:12,586 - DEBUG - 📷 Processing image: 3_cart.png
2025-06-19 00:05:24,767 - DEBUG - 📷 Processing image: 4_checkout_info.png
2025-06-19 00:05:29,061 - DEBUG - 📷 Processing image: 5_checkout_overview.png
2025-06-19 00:05:47,616 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-06-19 00:05:47,619 - INFO - 📄 Ordered images logged to data/image_order.json
2025-06-19 08:35:51,578 - INFO - 🟢 Ordered images from frontend: ['1_login.png', '2_inventory.png', '3_cart.png', '4_checkout_info.png', '5_checkout_overview.png']
2025-06-19 08:35:51,869 - DEBUG - 📷 Processing image: 1_login.png
2025-06-19 08:36:13,726 - DEBUG - 📷 Processing image: 2_inventory.png
2025-06-19 08:36:26,393 - DEBUG - 📷 Processing image: 3_cart.png
2025-06-19 08:36:37,454 - DEBUG - 📷 Processing image: 4_checkout_info.png
2025-06-19 08:36:45,006 - DEBUG - 📷 Processing image: 5_checkout_overview.png
2025-06-19 08:37:00,470 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-06-19 08:37:00,473 - INFO - 📄 Ordered images logged to data/image_order.json
2025-06-21 17:43:49,380 - INFO - 🟢 Ordered images from frontend: ['1_login.png', '2_inventory.png', '3_cart.png', '4_checkout_info.png', '5_checkout_overview.png']
2025-06-21 17:43:49,613 - DEBUG - 📷 Processing image: 1_login.png
2025-06-21 17:44:01,794 - DEBUG - 📷 Processing image: 2_inventory.png
2025-06-21 17:44:10,884 - DEBUG - 📷 Processing image: 3_cart.png
2025-06-21 17:44:19,166 - DEBUG - 📷 Processing image: 4_checkout_info.png
2025-06-21 17:44:26,217 - DEBUG - 📷 Processing image: 5_checkout_overview.png
2025-06-21 17:44:30,016 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-06-21 17:44:30,035 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-06-21 17:44:30,039 - INFO - 📄 Ordered images logged to data/image_order.json
2025-06-21 18:07:50,048 - INFO - 🟢 Ordered images from frontend: ['1_login.png', '2_inventory.png', '3_cart.png', '4_checkout_info.png', '5_checkout_overview.png']
2025-06-21 18:07:50,095 - DEBUG - 📷 Processing image: 1_login.png
2025-06-21 18:07:59,597 - DEBUG - 📷 Processing image: 2_inventory.png
2025-06-21 18:08:05,198 - DEBUG - 📷 Processing image: 3_cart.png
2025-06-21 18:08:17,387 - DEBUG - 📷 Processing image: 4_checkout_info.png
2025-06-21 18:08:23,731 - DEBUG - 📷 Processing image: 5_checkout_overview.png
2025-06-21 18:08:30,155 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-06-21 18:08:30,160 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-06-21 18:08:30,162 - INFO - 📄 Ordered images logged to data/image_order.json
2025-06-21 18:44:24,894 - INFO - 🟢 Ordered images from frontend: ['1_login.png', '2_inventory.png', '3_cart.png', '4_checkout_info.png', '5_checkout_overview.png']
2025-06-21 18:44:24,946 - DEBUG - 📷 Processing image: 1_login.png
2025-06-21 18:44:35,763 - DEBUG - 📷 Processing image: 2_inventory.png
2025-06-21 18:44:54,231 - DEBUG - 📷 Processing image: 3_cart.png
2025-06-21 18:45:04,338 - DEBUG - 📷 Processing image: 4_checkout_info.png
2025-06-21 18:45:10,042 - DEBUG - 📷 Processing image: 5_checkout_overview.png
2025-06-21 18:45:23,036 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-06-21 18:45:23,038 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-06-21 18:45:23,040 - INFO - 📄 Ordered images logged to data/image_order.json
2025-06-21 19:17:54,031 - INFO - 🟢 Ordered images from frontend: ['1_login.png', '2_inventory.png', '3_cart.png', '4_checkout_info.png', '5_checkout_overview.png']
2025-06-21 19:17:54,086 - DEBUG - 📷 Processing image: 1_login.png
2025-06-21 19:18:05,626 - DEBUG - 📷 Processing image: 2_inventory.png
2025-06-21 19:18:34,180 - DEBUG - 📷 Processing image: 3_cart.png
2025-06-21 19:18:46,932 - DEBUG - 📷 Processing image: 4_checkout_info.png
2025-06-21 19:19:00,009 - DEBUG - 📷 Processing image: 5_checkout_overview.png
2025-06-21 19:19:14,019 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-06-21 19:19:14,021 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-06-21 19:19:14,023 - INFO - 📄 Ordered images logged to data/image_order.json
2025-06-21 19:28:41,007 - INFO - 🟢 Ordered images from frontend: ['1_login.png', '2_inventory.png', '3_cart.png', '4_checkout_info.png', '5_checkout_overview.png']
2025-06-21 19:28:41,058 - DEBUG - 📷 Processing image: 1_login.png
2025-06-21 19:28:53,097 - DEBUG - 📷 Processing image: 2_inventory.png
2025-06-21 19:29:14,951 - DEBUG - 📷 Processing image: 3_cart.png
2025-06-21 19:29:23,835 - DEBUG - 📷 Processing image: 4_checkout_info.png
2025-06-21 19:29:30,620 - DEBUG - 📷 Processing image: 5_checkout_overview.png
2025-06-21 19:29:44,740 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-06-21 19:29:44,744 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-06-21 19:29:44,748 - INFO - 📄 Ordered images logged to data/image_order.json
2025-06-21 19:38:24,758 - INFO - 🟢 Ordered images from frontend: ['1_login.png', '2_inventory.png', '3_cart.png', '4_checkout_info.png', '5_checkout_overview.png']
2025-06-21 19:38:24,826 - DEBUG - 📷 Processing image: 1_login.png
2025-06-21 19:38:43,202 - DEBUG - 📷 Processing image: 2_inventory.png
2025-06-21 19:38:48,043 - DEBUG - 📷 Processing image: 3_cart.png
2025-06-21 19:38:58,358 - DEBUG - 📷 Processing image: 4_checkout_info.png
2025-06-21 19:39:05,188 - DEBUG - 📷 Processing image: 5_checkout_overview.png
2025-06-21 19:39:21,674 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-06-21 19:39:21,678 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-06-21 19:39:21,679 - INFO - 📄 Ordered images logged to data/image_order.json
2025-06-21 20:07:22,918 - INFO - 🟢 Ordered images from frontend: ['1_login.png', '2_inventory.png', '3_cart.png', '4_checkout_info.png', '5_checkout_overview.png']
2025-06-21 20:07:23,201 - DEBUG - 📷 Processing image: 1_login.png
2025-06-21 20:07:35,876 - DEBUG - 📷 Processing image: 2_inventory.png
2025-06-21 20:07:44,441 - DEBUG - 📷 Processing image: 3_cart.png
2025-06-21 20:07:53,196 - DEBUG - 📷 Processing image: 4_checkout_info.png
2025-06-21 20:08:01,531 - DEBUG - 📷 Processing image: 5_checkout_overview.png
2025-06-21 20:08:10,578 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-06-21 20:08:10,580 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-06-21 20:08:10,581 - INFO - 📄 Ordered images logged to data/image_order.json
2025-06-21 20:10:31,299 - INFO - 🟢 Ordered images from frontend: ['1_login.png', '2_inventory.png', '3_cart.png', '4_checkout_info.png', '5_checkout_overview.png']
2025-06-21 20:10:31,468 - DEBUG - 📷 Processing image: 1_login.png
2025-06-21 20:10:43,152 - DEBUG - 📷 Processing image: 2_inventory.png
2025-06-21 20:11:06,205 - DEBUG - 📷 Processing image: 3_cart.png
2025-06-21 20:11:20,335 - DEBUG - 📷 Processing image: 4_checkout_info.png
2025-06-21 20:11:28,111 - DEBUG - 📷 Processing image: 5_checkout_overview.png
2025-06-21 20:11:54,030 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-06-21 20:11:54,032 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-06-21 20:11:54,033 - INFO - 📄 Ordered images logged to data/image_order.json
2025-06-22 13:28:30,069 - INFO - 🟢 Ordered images from frontend: ['1_login.png', '2_inventory.png', '3_cart.png', '4_checkout_info.png', '5_checkout_overview.png']
2025-06-22 13:28:30,260 - DEBUG - 📷 Processing image: 1_login.png
2025-06-22 13:28:41,516 - DEBUG - 📷 Processing image: 2_inventory.png
2025-06-22 13:28:47,192 - DEBUG - 📷 Processing image: 3_cart.png
2025-06-22 13:28:57,904 - DEBUG - 📷 Processing image: 4_checkout_info.png
2025-06-22 13:29:04,630 - DEBUG - 📷 Processing image: 5_checkout_overview.png
2025-06-22 13:29:21,915 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-06-22 13:29:21,918 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-06-22 13:29:21,919 - INFO - 📄 Ordered images logged to data/image_order.json
2025-06-22 13:30:43,636 - INFO - 🟢 Ordered images from frontend: ['1_login.png', '2_inventory.png', '3_cart.png', '4_checkout_info.png', '5_checkout_overview.png']
2025-06-22 13:30:43,845 - DEBUG - 📷 Processing image: 1_login.png
2025-06-22 13:30:59,804 - DEBUG - 📷 Processing image: 2_inventory.png
2025-06-22 13:31:07,899 - DEBUG - 📷 Processing image: 3_cart.png
2025-06-22 13:31:13,755 - DEBUG - 📷 Processing image: 4_checkout_info.png
2025-06-22 13:31:17,164 - DEBUG - 📷 Processing image: 5_checkout_overview.png
2025-06-22 13:31:20,148 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-06-22 13:31:20,150 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-06-22 13:31:20,152 - INFO - 📄 Ordered images logged to data/image_order.json
2025-06-22 13:37:13,135 - INFO - 🟢 Ordered images from frontend: ['1_login.png', '2_inventory.png', '3_cart.png', '4_checkout_info.png', '5_checkout_overview.png']
2025-06-22 13:37:13,198 - DEBUG - 📷 Processing image: 1_login.png
2025-06-22 13:37:25,184 - DEBUG - 📷 Processing image: 2_inventory.png
2025-06-22 13:37:55,041 - DEBUG - 📷 Processing image: 3_cart.png
2025-06-22 13:38:04,864 - DEBUG - 📷 Processing image: 4_checkout_info.png
2025-06-22 13:38:11,299 - DEBUG - 📷 Processing image: 5_checkout_overview.png
2025-06-22 13:38:21,729 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-06-22 13:38:21,731 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-06-22 13:38:21,734 - INFO - 📄 Ordered images logged to data/image_order.json
2025-06-22 13:46:21,359 - INFO - 🟢 Ordered images from frontend: ['login.png', 'inventory.png', 'cart.png', 'checkout_info.png', 'checkout_overview.png']
2025-06-22 13:46:21,414 - DEBUG - 📷 Processing image: login.png
2025-06-22 13:46:24,447 - DEBUG - 📷 Processing image: inventory.png
2025-06-22 13:46:45,232 - DEBUG - 📷 Processing image: cart.png
2025-06-22 13:46:54,695 - DEBUG - 📷 Processing image: checkout_info.png
2025-06-22 13:46:59,886 - DEBUG - 📷 Processing image: checkout_overview.png
2025-06-22 13:47:02,108 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-06-22 13:47:02,110 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-06-22 13:47:02,112 - INFO - 📄 Ordered images logged to data/image_order.json
2025-06-22 13:48:33,415 - INFO - 🟢 Ordered images from frontend: ['login.png', 'inventory.png', 'cart.png', 'checkout_info.png', 'checkout_overview.png']
2025-06-22 13:48:33,504 - DEBUG - 📷 Processing image: login.png
2025-06-22 13:48:45,599 - DEBUG - 📷 Processing image: inventory.png
2025-06-22 13:49:06,291 - DEBUG - 📷 Processing image: cart.png
2025-06-22 13:49:16,175 - DEBUG - 📷 Processing image: checkout_info.png
2025-06-22 13:49:29,875 - DEBUG - 📷 Processing image: checkout_overview.png
2025-06-22 13:49:42,043 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-06-22 13:49:42,044 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-06-22 13:49:42,049 - INFO - 📄 Ordered images logged to data/image_order.json
2025-06-22 17:02:43,412 - INFO - 🟢 Ordered images from frontend: ['login.png', 'inventory.png', 'cart.png', 'checkout_info.png', 'checkout_overview.png']
2025-06-22 17:02:43,537 - DEBUG - 📷 Processing image: login.png
2025-06-22 17:02:48,345 - DEBUG - 📷 Processing image: inventory.png
2025-06-22 17:02:53,762 - DEBUG - 📷 Processing image: cart.png
2025-06-22 17:03:05,101 - DEBUG - 📷 Processing image: checkout_info.png
2025-06-22 17:03:07,166 - DEBUG - 📷 Processing image: checkout_overview.png
2025-06-22 17:03:21,270 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-06-22 17:03:21,271 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-06-22 17:03:21,273 - INFO - 📄 Ordered images logged to data/image_order.json
2025-06-22 17:04:14,303 - INFO - 🟢 Ordered images from frontend: ['login.png', 'inventory.png', 'cart.png', 'checkout_info.png', 'checkout_overview.png']
2025-06-22 17:04:14,322 - DEBUG - 📷 Processing image: login.png
2025-06-22 17:04:23,194 - DEBUG - 📷 Processing image: inventory.png
2025-06-22 17:04:32,013 - DEBUG - 📷 Processing image: cart.png
2025-06-22 17:04:41,003 - DEBUG - 📷 Processing image: checkout_info.png
2025-06-22 17:04:47,093 - DEBUG - 📷 Processing image: checkout_overview.png
2025-06-22 17:04:59,077 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-06-22 17:04:59,079 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-06-22 17:04:59,080 - INFO - 📄 Ordered images logged to data/image_order.json
2025-06-22 20:27:03,615 - INFO - 🟢 Ordered images from frontend: ['login.png', 'inventory.png', 'cart.png', 'checkout_info.png', 'checkout_overview.png']
2025-06-22 20:27:03,918 - DEBUG - 📷 Processing image: login.png
2025-06-22 20:27:13,598 - DEBUG - 📷 Processing image: inventory.png
2025-06-22 20:27:39,226 - DEBUG - 📷 Processing image: cart.png
2025-06-22 20:27:51,112 - DEBUG - 📷 Processing image: checkout_info.png
2025-06-22 20:27:59,641 - DEBUG - 📷 Processing image: checkout_overview.png
2025-06-22 20:28:22,427 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-06-22 20:28:22,429 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-06-22 20:28:22,430 - INFO - 📄 Ordered images logged to data/image_order.json
2025-06-22 20:46:16,700 - INFO - 🟢 Ordered images from frontend: ['login.png', 'inventory.png', 'cart.png', 'checkout_info.png', 'checkout_overview.png']
2025-06-22 20:46:17,023 - DEBUG - 📷 Processing image: login.png
2025-06-22 20:46:29,462 - DEBUG - 📷 Processing image: inventory.png
2025-06-22 20:46:41,092 - DEBUG - 📷 Processing image: cart.png
2025-06-22 20:46:49,932 - DEBUG - 📷 Processing image: checkout_info.png
2025-06-22 20:46:56,605 - DEBUG - 📷 Processing image: checkout_overview.png
2025-06-22 20:46:59,715 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-06-22 20:46:59,721 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-06-22 20:46:59,725 - INFO - 📄 Ordered images logged to data/image_order.json
2025-06-22 21:11:38,882 - INFO - 🟢 Ordered images from frontend: ['login.png', 'inventory.png', 'cart.png', 'checkout_info.png', 'checkout_overview.png']
2025-06-22 21:11:39,143 - DEBUG - 📷 Processing image: login.png
2025-06-22 21:11:58,112 - DEBUG - 📷 Processing image: inventory.png
2025-06-22 21:12:42,907 - DEBUG - 📷 Processing image: cart.png
2025-06-22 21:12:55,259 - DEBUG - 📷 Processing image: checkout_info.png
2025-06-22 21:13:00,474 - DEBUG - 📷 Processing image: checkout_overview.png
2025-06-22 21:13:03,943 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-06-22 21:13:03,945 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-06-22 21:13:03,947 - INFO - 📄 Ordered images logged to data/image_order.json
2025-06-22 21:15:32,708 - INFO - 🟢 Ordered images from frontend: ['login.png', 'inventory.png', 'cart.png', 'checkout_info.png', 'checkout_overview.png']
2025-06-22 21:15:32,790 - DEBUG - 📷 Processing image: login.png
2025-06-22 21:15:42,940 - DEBUG - 📷 Processing image: inventory.png
2025-06-22 21:16:21,316 - DEBUG - 📷 Processing image: cart.png
2025-06-22 21:16:30,356 - DEBUG - 📷 Processing image: checkout_info.png
2025-06-22 21:16:36,284 - DEBUG - 📷 Processing image: checkout_overview.png
2025-06-22 21:16:47,432 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-06-22 21:16:47,434 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-06-22 21:16:47,435 - INFO - 📄 Ordered images logged to data/image_order.json
2025-06-23 15:15:36,412 - INFO - 🟢 Ordered images from frontend: ['login.png', 'inventory.png', 'cart.png', 'checkout_info.png', 'checkout_overview.png']
2025-06-23 15:15:36,528 - DEBUG - 📷 Processing image: login.png
2025-06-23 15:15:47,852 - DEBUG - 📷 Processing image: inventory.png
2025-06-23 15:16:08,732 - DEBUG - 📷 Processing image: cart.png
2025-06-23 15:16:18,022 - DEBUG - 📷 Processing image: checkout_info.png
2025-06-23 15:16:24,905 - DEBUG - 📷 Processing image: checkout_overview.png
2025-06-23 15:16:27,355 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-06-23 15:16:27,357 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-06-23 15:16:27,359 - INFO - 📄 Ordered images logged to data/image_order.json
2025-06-23 15:34:19,903 - INFO - 🟢 Ordered images from frontend: ['login.png', 'inventory.png', 'cart.png', 'checkout_info.png', 'checkout_overview.png']
2025-06-23 15:34:19,967 - DEBUG - 📷 Processing image: login.png
2025-06-23 15:34:26,628 - ERROR - ❌ Error in upload_image
Traceback (most recent call last):
  File "C:\Users\Suchandan\Desktop\VNC\testify-automator-ai\backend\apis\image_text_api.py", line 103, in upload_image
    metadata_list = await process_image_gpt(
                    ^^^^^^^^^^^^^^^^^^^^^^^^
    ...<3 lines>...
    )
    ^
  File "C:\Users\Suchandan\Desktop\VNC\testify-automator-ai\backend\logic\image_text_extractor.py", line 220, in process_image_gpt
    metadata = build_standard_metadata(
        element,
        page_name,
        image_path=region_path
    )
  File "C:\Users\Suchandan\Desktop\VNC\testify-automator-ai\backend\utils\file_utils.py", line 58, in build_standard_metadata
    unique_name = generate_unique_name(page_name,intent,label_text,ocr_type)
TypeError: generate_unique_name() takes 3 positional arguments but 4 were given
2025-06-23 15:38:20,344 - INFO - 🟢 Ordered images from frontend: ['login.png', 'inventory.png', 'cart.png', 'checkout_info.png', 'checkout_overview.png']
2025-06-23 15:38:20,398 - DEBUG - 📷 Processing image: login.png
2025-06-23 15:38:30,551 - DEBUG - 📷 Processing image: inventory.png
2025-06-23 15:38:53,727 - DEBUG - 📷 Processing image: cart.png
2025-06-23 15:39:01,817 - DEBUG - 📷 Processing image: checkout_info.png
2025-06-23 15:39:07,250 - DEBUG - 📷 Processing image: checkout_overview.png
2025-06-23 15:39:23,543 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-06-23 15:39:23,546 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-06-23 15:39:23,548 - INFO - 📄 Ordered images logged to data/image_order.json
2025-06-23 17:22:21,628 - INFO - 🟢 Ordered images from frontend: ['login.png', 'inventory.png', 'cart.png', 'checkout_info.png', 'checkout_overview.png']
2025-06-23 17:22:21,701 - DEBUG - 📷 Processing image: login.png
2025-06-23 17:22:26,488 - DEBUG - 📷 Processing image: inventory.png
2025-06-23 17:22:48,701 - DEBUG - 📷 Processing image: cart.png
2025-06-23 17:22:58,580 - DEBUG - 📷 Processing image: checkout_info.png
2025-06-23 17:23:05,774 - DEBUG - 📷 Processing image: checkout_overview.png
2025-06-23 17:23:11,285 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-06-23 17:23:11,287 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-06-23 17:23:11,288 - INFO - 📄 Ordered images logged to data/image_order.json
2025-06-23 17:25:19,244 - INFO - 🟢 Ordered images from frontend: ['login.png', 'inventory.png', 'cart.png', 'checkout_info.png', 'checkout_overview.png']
2025-06-23 17:25:19,307 - DEBUG - 📷 Processing image: login.png
2025-06-23 17:25:31,538 - DEBUG - 📷 Processing image: inventory.png
2025-06-23 17:25:57,032 - DEBUG - 📷 Processing image: cart.png
2025-06-23 17:26:00,564 - DEBUG - 📷 Processing image: checkout_info.png
2025-06-23 17:26:05,605 - DEBUG - 📷 Processing image: checkout_overview.png
2025-06-23 17:26:22,001 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-06-23 17:26:22,003 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-06-23 17:26:22,004 - INFO - 📄 Ordered images logged to data/image_order.json
2025-06-23 17:27:33,417 - INFO - 🟢 Ordered images from frontend: ['login.png', 'inventory.png', 'cart.png', 'checkout_info.png', 'checkout_overview.png']
2025-06-23 17:27:33,471 - DEBUG - 📷 Processing image: login.png
2025-06-23 17:27:45,182 - DEBUG - 📷 Processing image: inventory.png
2025-06-23 17:27:49,790 - DEBUG - 📷 Processing image: cart.png
2025-06-23 17:28:00,205 - DEBUG - 📷 Processing image: checkout_info.png
2025-06-23 17:28:06,339 - DEBUG - 📷 Processing image: checkout_overview.png
2025-06-23 17:28:17,482 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-06-23 17:28:17,484 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-06-23 17:28:17,485 - INFO - 📄 Ordered images logged to data/image_order.json
2025-06-23 17:59:49,575 - INFO - 🟢 Ordered images from frontend: ['login.png', 'inventory.png', 'cart.png', 'checkout_info.png', 'checkout_overview.png']
2025-06-23 17:59:49,648 - DEBUG - 📷 Processing image: login.png
2025-06-23 17:59:59,981 - DEBUG - 📷 Processing image: inventory.png
2025-06-23 18:00:17,625 - DEBUG - 📷 Processing image: cart.png
2025-06-23 18:00:26,413 - DEBUG - 📷 Processing image: checkout_info.png
2025-06-23 18:00:31,668 - DEBUG - 📷 Processing image: checkout_overview.png
2025-06-23 18:00:46,860 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-06-23 18:00:46,862 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-06-23 18:00:46,867 - INFO - 📄 Ordered images logged to data/image_order.json
2025-06-23 22:18:37,371 - INFO - 🟢 Ordered images from frontend: ['login.png', 'inventory.png', 'cart.png', 'checkout_info.png', 'checkout_overview.png']
2025-06-23 22:18:37,466 - DEBUG - 📷 Processing image: login.png
2025-06-23 22:18:41,877 - DEBUG - 📷 Processing image: inventory.png
2025-06-23 22:19:03,421 - DEBUG - 📷 Processing image: cart.png
2025-06-23 22:19:15,247 - DEBUG - 📷 Processing image: checkout_info.png
2025-06-23 22:19:20,658 - DEBUG - 📷 Processing image: checkout_overview.png
2025-06-23 22:19:35,262 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-06-23 22:19:35,267 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-06-23 22:19:35,268 - INFO - 📄 Ordered images logged to data/image_order.json
2025-06-23 22:21:13,060 - INFO - 🟢 Ordered images from frontend: ['login.png', 'inventory.png', 'cart.png', 'checkout_info.png', 'checkout_overview.png']
2025-06-23 22:21:13,121 - DEBUG - 📷 Processing image: login.png
2025-06-23 22:21:26,970 - DEBUG - 📷 Processing image: inventory.png
2025-06-23 22:21:45,482 - DEBUG - 📷 Processing image: cart.png
2025-06-23 22:21:56,546 - DEBUG - 📷 Processing image: checkout_info.png
2025-06-23 22:22:02,161 - DEBUG - 📷 Processing image: checkout_overview.png
2025-06-23 22:22:06,037 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-06-23 22:22:06,039 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-06-23 22:22:06,040 - INFO - 📄 Ordered images logged to data/image_order.json
2025-06-23 22:22:22,563 - INFO - 🟢 Ordered images from frontend: ['login.png', 'inventory.png', 'cart.png', 'checkout_info.png', 'checkout_overview.png']
2025-06-23 22:22:22,592 - DEBUG - 📷 Processing image: login.png
2025-06-23 22:22:34,800 - DEBUG - 📷 Processing image: inventory.png
2025-06-23 22:22:56,651 - DEBUG - 📷 Processing image: cart.png
2025-06-23 22:23:04,502 - DEBUG - 📷 Processing image: checkout_info.png
2025-06-23 22:23:11,005 - DEBUG - 📷 Processing image: checkout_overview.png
2025-06-23 22:23:30,601 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-06-23 22:23:30,602 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-06-23 22:23:30,603 - INFO - 📄 Ordered images logged to data/image_order.json
2025-06-23 22:55:57,330 - INFO - 🟢 Ordered images from frontend: ['login.png', 'inventory.png', 'cart.png', 'checkout_info.png', 'checkout_overview.png']
2025-06-23 22:55:57,391 - DEBUG - 📷 Processing image: login.png
2025-06-23 22:56:10,059 - DEBUG - 📷 Processing image: inventory.png
2025-06-23 22:56:36,562 - DEBUG - 📷 Processing image: cart.png
2025-06-23 22:56:47,438 - DEBUG - 📷 Processing image: checkout_info.png
2025-06-23 22:56:52,714 - DEBUG - 📷 Processing image: checkout_overview.png
2025-06-23 22:57:08,107 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-06-23 22:57:08,109 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-06-23 22:57:08,111 - INFO - 📄 Ordered images logged to data/image_order.json
2025-06-25 20:36:18,475 - INFO - 🟢 Ordered images from frontend: ['login.png', 'inventory.png', 'cart.png', 'checkout_info.png', 'checkout_overview.png']
2025-06-25 20:36:18,578 - DEBUG - 📷 Processing image: login.png
2025-06-25 20:36:32,407 - DEBUG - 📷 Processing image: inventory.png
2025-06-25 20:36:52,410 - DEBUG - 📷 Processing image: cart.png
2025-06-25 20:37:02,235 - DEBUG - 📷 Processing image: checkout_info.png
2025-06-25 20:37:08,526 - DEBUG - 📷 Processing image: checkout_overview.png
2025-06-25 20:37:26,359 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-06-25 20:37:26,364 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-06-25 20:37:26,366 - INFO - 📄 Ordered images logged to data/image_order.json
2025-06-25 21:54:28,103 - INFO - 🟢 Ordered images from frontend: ['login.png', 'inventory.png', 'cart.png', 'checkout_info.png', 'checkout_overview.png']
2025-06-25 21:54:28,192 - DEBUG - 📷 Processing image: login.png
2025-06-25 21:54:36,219 - DEBUG - 📷 Processing image: inventory.png
2025-06-25 21:54:55,163 - DEBUG - 📷 Processing image: cart.png
2025-06-25 21:55:05,228 - DEBUG - 📷 Processing image: checkout_info.png
2025-06-25 21:55:11,258 - DEBUG - 📷 Processing image: checkout_overview.png
2025-06-25 21:55:24,290 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-06-25 21:55:24,292 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-06-25 21:55:24,294 - INFO - 📄 Ordered images logged to data/image_order.json
2025-06-25 21:56:51,286 - INFO - 🟢 Ordered images from frontend: ['login.png', 'inventory.png', 'cart.png', 'checkout_info.png', 'checkout_overview.png']
2025-06-25 21:56:51,340 - DEBUG - 📷 Processing image: login.png
2025-06-25 21:57:08,188 - DEBUG - 📷 Processing image: inventory.png
2025-06-25 21:57:40,142 - DEBUG - 📷 Processing image: cart.png
2025-06-25 21:57:57,493 - DEBUG - 📷 Processing image: checkout_info.png
2025-06-25 21:58:06,629 - DEBUG - 📷 Processing image: checkout_overview.png
2025-06-25 21:58:25,803 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-06-25 21:58:25,806 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-06-25 21:58:25,809 - INFO - 📄 Ordered images logged to data/image_order.json
2025-06-25 23:37:46,557 - INFO - 🟢 Ordered images from frontend: ['login.png', 'inventory.png', 'cart.png', 'checkout_info.png', 'checkout_overview.png']
2025-06-25 23:37:46,608 - DEBUG - 📷 Processing image: login.png
2025-06-25 23:37:57,566 - DEBUG - 📷 Processing image: inventory.png
2025-06-25 23:38:35,574 - DEBUG - 📷 Processing image: cart.png
2025-06-25 23:38:45,133 - DEBUG - 📷 Processing image: checkout_info.png
2025-06-25 23:38:52,529 - DEBUG - 📷 Processing image: checkout_overview.png
2025-06-25 23:39:05,531 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-06-25 23:39:05,534 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-06-25 23:39:05,535 - INFO - 📄 Ordered images logged to data/image_order.json
2025-06-25 23:58:50,043 - INFO - 🟢 Ordered images from frontend: ['login.png', 'inventory.png', 'cart.png', 'checkout_info.png', 'checkout_overview.png']
2025-06-25 23:58:50,092 - DEBUG - 📷 Processing image: login.png
2025-06-25 23:58:54,348 - DEBUG - 📷 Processing image: inventory.png
2025-06-25 23:59:25,993 - DEBUG - 📷 Processing image: cart.png
2025-06-25 23:59:33,478 - DEBUG - 📷 Processing image: checkout_info.png
2025-06-25 23:59:41,181 - DEBUG - 📷 Processing image: checkout_overview.png
2025-06-25 23:59:44,693 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-06-25 23:59:44,695 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-06-25 23:59:44,697 - INFO - 📄 Ordered images logged to data/image_order.json
2025-06-26 00:10:12,407 - INFO - 🟢 Ordered images from frontend: ['login.png', 'inventory.png', 'cart.png', 'checkout_info.png', 'checkout_overview.png']
2025-06-26 00:10:12,455 - DEBUG - 📷 Processing image: login.png
2025-06-26 00:10:23,691 - DEBUG - 📷 Processing image: inventory.png
2025-06-26 00:10:53,899 - DEBUG - 📷 Processing image: cart.png
2025-06-26 00:11:02,549 - DEBUG - 📷 Processing image: checkout_info.png
2025-06-26 00:11:12,692 - DEBUG - 📷 Processing image: checkout_overview.png
2025-06-26 00:11:27,015 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-06-26 00:11:27,017 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-06-26 00:11:27,018 - INFO - 📄 Ordered images logged to data/image_order.json
2025-06-28 12:19:30,725 - INFO - 🟢 Ordered images from frontend: ['login.png', 'inventory.png', 'cart.png', 'checkout_info.png', 'checkout_overview.png']
2025-06-28 12:19:30,822 - DEBUG - 📷 Processing image: login.png
2025-06-28 12:19:41,688 - DEBUG - 📷 Processing image: inventory.png
2025-06-28 12:19:48,703 - DEBUG - 📷 Processing image: cart.png
2025-06-28 12:19:55,973 - DEBUG - 📷 Processing image: checkout_info.png
2025-06-28 12:20:02,229 - DEBUG - 📷 Processing image: checkout_overview.png
2025-06-28 12:20:13,678 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-06-28 12:20:13,680 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-06-28 12:20:13,681 - INFO - 📄 Ordered images logged to data/image_order.json
2025-06-28 12:20:35,269 - INFO - 🟢 Ordered images from frontend: ['inventory.png']
2025-06-28 12:20:35,285 - DEBUG - 📷 Processing image: inventory.png
2025-06-28 12:20:41,543 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-06-28 12:20:41,593 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-06-28 12:20:41,596 - INFO - 📄 Ordered images logged to data/image_order.json
2025-06-28 12:22:35,054 - INFO - 🟢 Ordered images from frontend: ['login.png', 'inventory.png', 'cart.png', 'checkout_info.png', 'checkout_overview.png']
2025-06-28 12:22:35,101 - DEBUG - 📷 Processing image: login.png
2025-06-28 12:22:45,435 - DEBUG - 📷 Processing image: inventory.png
2025-06-28 12:22:59,852 - DEBUG - 📷 Processing image: cart.png
2025-06-28 12:23:07,591 - DEBUG - 📷 Processing image: checkout_info.png
2025-06-28 12:23:14,093 - DEBUG - 📷 Processing image: checkout_overview.png
2025-06-28 12:23:27,002 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-06-28 12:23:27,005 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-06-28 12:23:27,007 - INFO - 📄 Ordered images logged to data/image_order.json
2025-06-28 13:20:30,431 - INFO - 🟢 Ordered images from frontend: ['login.png', 'inventory.png', 'cart.png', 'checkout_info.png', 'checkout_overview.png']
2025-06-28 13:20:30,493 - DEBUG - 📷 Processing image: login.png
2025-06-28 13:20:42,982 - DEBUG - 📷 Processing image: inventory.png
2025-06-28 13:21:01,993 - DEBUG - 📷 Processing image: cart.png
2025-06-28 13:21:10,880 - DEBUG - 📷 Processing image: checkout_info.png
2025-06-28 13:21:16,418 - DEBUG - 📷 Processing image: checkout_overview.png
2025-06-28 13:21:27,995 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-06-28 13:21:27,997 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-06-28 13:21:28,000 - INFO - 📄 Ordered images logged to data/image_order.json
2025-06-29 08:34:09,751 - INFO - 🟢 Ordered images from frontend: ['login.png', 'inventory.png', 'cart.png', 'checkout_info.png', 'checkout_overview.png']
2025-06-29 08:34:09,855 - DEBUG - 📷 Processing image: login.png
2025-06-29 08:34:23,921 - DEBUG - 📷 Processing image: inventory.png
2025-06-29 08:35:02,299 - DEBUG - 📷 Processing image: cart.png
2025-06-29 08:35:31,498 - DEBUG - 📷 Processing image: checkout_info.png
2025-06-29 08:35:39,098 - DEBUG - 📷 Processing image: checkout_overview.png
2025-06-29 08:35:54,887 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-06-29 08:35:54,889 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-06-29 08:35:54,891 - INFO - 📄 Ordered images logged to data/image_order.json
2025-06-29 10:53:18,458 - INFO - 🟢 Ordered images from frontend: ['login.png', 'inventory.png', 'cart.png', 'checkout_info.png', 'checkout_overview.png']
2025-06-29 10:53:18,552 - DEBUG - 📷 Processing image: login.png
2025-06-29 10:53:28,357 - DEBUG - 📷 Processing image: inventory.png
2025-06-29 10:53:42,389 - DEBUG - 📷 Processing image: cart.png
2025-06-29 10:53:49,531 - DEBUG - 📷 Processing image: checkout_info.png
2025-06-29 10:53:50,675 - DEBUG - 📷 Processing image: checkout_overview.png
2025-06-29 10:54:04,862 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-06-29 10:54:04,864 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-06-29 10:54:04,865 - INFO - 📄 Ordered images logged to data/image_order.json
2025-06-29 11:26:51,873 - INFO - 🟢 Ordered images from frontend: ['login.png', 'inventory.png', 'cart.png', 'checkout_info.png', 'checkout_overview.png']
2025-06-29 11:26:51,932 - DEBUG - 📷 Processing image: login.png
2025-06-29 11:27:01,203 - DEBUG - 📷 Processing image: inventory.png
2025-06-29 11:27:23,764 - DEBUG - 📷 Processing image: cart.png
2025-06-29 11:27:29,845 - DEBUG - 📷 Processing image: checkout_info.png
2025-06-29 11:27:33,733 - DEBUG - 📷 Processing image: checkout_overview.png
2025-06-29 11:27:44,425 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-06-29 11:27:44,427 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-06-29 11:27:44,429 - INFO - 📄 Ordered images logged to data/image_order.json
2025-06-30 09:57:14,546 - INFO - 🟢 Ordered images from frontend: ['login.png', 'inventory.png', 'cart.png', 'checkout_info.png', 'checkout_overview.png']
2025-06-30 09:57:14,694 - DEBUG - 📷 Processing image: login.png
2025-06-30 09:57:26,580 - DEBUG - 📷 Processing image: inventory.png
2025-06-30 09:57:35,974 - DEBUG - 📷 Processing image: cart.png
2025-06-30 09:57:45,108 - DEBUG - 📷 Processing image: checkout_info.png
2025-06-30 09:57:52,074 - DEBUG - 📷 Processing image: checkout_overview.png
2025-06-30 09:58:06,928 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-06-30 09:58:06,930 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-06-30 09:58:06,932 - INFO - 📄 Ordered images logged to data/image_order.json
2025-06-30 10:00:10,848 - INFO - 🟢 Ordered images from frontend: ['login.png', 'inventory.png', 'cart.png', 'checkout_info.png', 'checkout_overview.png']
2025-06-30 10:00:10,947 - DEBUG - 📷 Processing image: login.png
2025-06-30 10:00:26,804 - DEBUG - 📷 Processing image: inventory.png
2025-06-30 10:00:55,363 - DEBUG - 📷 Processing image: cart.png
2025-06-30 10:01:09,270 - DEBUG - 📷 Processing image: checkout_info.png
2025-06-30 10:01:17,867 - DEBUG - 📷 Processing image: checkout_overview.png
2025-06-30 10:01:31,402 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-06-30 10:01:31,405 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-06-30 10:01:31,406 - INFO - 📄 Ordered images logged to data/image_order.json
2025-06-30 10:25:46,918 - INFO - 🟢 Ordered images from frontend: ['login.png', 'inventory.png', 'cart.png', 'checkout_info.png', 'checkout_overview.png']
2025-06-30 10:25:47,033 - DEBUG - 📷 Processing image: login.png
2025-06-30 10:25:58,569 - DEBUG - 📷 Processing image: inventory.png
2025-06-30 10:26:24,809 - DEBUG - 📷 Processing image: cart.png
2025-06-30 10:26:31,608 - DEBUG - 📷 Processing image: checkout_info.png
2025-06-30 10:26:37,999 - DEBUG - 📷 Processing image: checkout_overview.png
2025-06-30 10:26:48,027 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-06-30 10:26:48,029 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-06-30 10:26:48,030 - INFO - 📄 Ordered images logged to data/image_order.json
2025-06-30 10:28:51,114 - INFO - 🟢 Ordered images from frontend: ['login.png', 'inventory.png', 'cart.png', 'checkout_info.png', 'checkout_overview.png']
2025-06-30 10:28:51,167 - DEBUG - 📷 Processing image: login.png
2025-06-30 10:29:03,584 - DEBUG - 📷 Processing image: inventory.png
2025-06-30 10:29:19,612 - DEBUG - 📷 Processing image: cart.png
2025-06-30 10:29:30,474 - DEBUG - 📷 Processing image: checkout_info.png
2025-06-30 10:29:34,541 - DEBUG - 📷 Processing image: checkout_overview.png
2025-06-30 10:29:47,449 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-06-30 10:29:47,453 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-06-30 10:29:47,455 - INFO - 📄 Ordered images logged to data/image_order.json
2025-06-30 11:28:18,108 - INFO - 🟢 Ordered images from frontend: ['login.png', 'inventory.png', 'cart.png', 'checkout_info.png', 'checkout_overview.png']
2025-06-30 11:28:18,162 - DEBUG - 📷 Processing image: login.png
2025-06-30 11:28:29,703 - DEBUG - 📷 Processing image: inventory.png
2025-06-30 11:28:55,159 - DEBUG - 📷 Processing image: cart.png
2025-06-30 11:29:06,818 - DEBUG - 📷 Processing image: checkout_info.png
2025-06-30 11:29:12,499 - DEBUG - 📷 Processing image: checkout_overview.png
2025-06-30 11:29:23,804 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-06-30 11:29:23,806 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-06-30 11:29:23,808 - INFO - 📄 Ordered images logged to data/image_order.json
2025-06-30 11:40:01,636 - INFO - 🟢 Ordered images from frontend: ['login.png', 'inventory.png', 'cart.png', 'checkout_info.png', 'checkout_overview.png']
2025-06-30 11:40:01,687 - DEBUG - 📷 Processing image: login.png
2025-06-30 11:40:06,484 - DEBUG - 📷 Processing image: inventory.png
2025-06-30 11:40:24,619 - DEBUG - 📷 Processing image: cart.png
2025-06-30 11:40:34,116 - DEBUG - 📷 Processing image: checkout_info.png
2025-06-30 11:40:39,008 - DEBUG - 📷 Processing image: checkout_overview.png
2025-06-30 11:40:55,115 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-06-30 11:40:55,119 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-06-30 11:40:55,121 - INFO - 📄 Ordered images logged to data/image_order.json
2025-06-30 11:41:47,675 - INFO - 🟢 Ordered images from frontend: ['login.png', 'inventory.png', 'cart.png', 'checkout_info.png', 'checkout_overview.png']
2025-06-30 11:41:47,725 - DEBUG - 📷 Processing image: login.png
2025-06-30 11:41:57,599 - DEBUG - 📷 Processing image: inventory.png
2025-06-30 11:42:12,355 - DEBUG - 📷 Processing image: cart.png
2025-06-30 11:42:19,558 - DEBUG - 📷 Processing image: checkout_info.png
2025-06-30 11:42:27,339 - DEBUG - 📷 Processing image: checkout_overview.png
2025-06-30 11:42:41,333 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-06-30 11:42:41,335 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-06-30 11:42:41,336 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-02 22:12:01,024 - INFO - 🟢 Ordered images from frontend: ['login.png', 'inventory.png', 'cart.png', 'checkout_info.png', 'checkout_overview.png']
2025-07-02 22:12:01,339 - DEBUG - 📷 Processing image: login.png
2025-07-02 22:12:16,265 - DEBUG - 📷 Processing image: inventory.png
2025-07-02 22:12:38,530 - DEBUG - 📷 Processing image: cart.png
2025-07-02 22:12:45,698 - DEBUG - 📷 Processing image: checkout_info.png
2025-07-02 22:12:52,046 - DEBUG - 📷 Processing image: checkout_overview.png
2025-07-02 22:13:06,387 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-07-02 22:13:06,392 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-02 22:13:06,393 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-03 10:40:28,833 - INFO - 🟢 Ordered images from frontend: ['login.png', 'inventory.png', 'cart.png', 'checkout_info.png', 'checkout_overview.png']
2025-07-03 10:40:28,917 - DEBUG - 📷 Processing image: login.png
2025-07-03 10:40:38,525 - DEBUG - 📷 Processing image: inventory.png
2025-07-03 10:40:53,743 - DEBUG - 📷 Processing image: cart.png
2025-07-03 10:41:02,499 - DEBUG - 📷 Processing image: checkout_info.png
2025-07-03 10:41:08,288 - DEBUG - 📷 Processing image: checkout_overview.png
2025-07-03 10:41:24,409 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-07-03 10:41:24,411 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-03 10:41:24,414 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-03 10:42:12,832 - INFO - 🟢 Ordered images from frontend: ['inventory.png']
2025-07-03 10:42:12,850 - DEBUG - 📷 Processing image: inventory.png
2025-07-03 10:42:31,028 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-07-03 10:42:31,034 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-03 10:42:31,035 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-03 10:58:58,770 - INFO - 🟢 Ordered images from frontend: ['Dashboard.png', 'Customers.png', 'add_customer.png']
2025-07-03 10:58:58,816 - DEBUG - 📷 Processing image: Dashboard.png
2025-07-03 10:59:08,047 - DEBUG - 📷 Processing image: Customers.png
2025-07-03 10:59:14,514 - DEBUG - 📷 Processing image: add_customer.png
2025-07-03 10:59:18,172 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-07-03 10:59:18,175 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-03 10:59:18,176 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-03 10:59:48,953 - INFO - 🟢 Ordered images from frontend: ['add_customer.png', 'Customers.png', 'Dashboard.png']
2025-07-03 10:59:48,975 - DEBUG - 📷 Processing image: add_customer.png
2025-07-03 11:00:03,119 - DEBUG - 📷 Processing image: Customers.png
2025-07-03 11:00:28,124 - DEBUG - 📷 Processing image: Dashboard.png
2025-07-03 11:00:30,371 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-07-03 11:00:30,373 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-03 11:00:30,375 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-03 11:00:43,652 - INFO - 🟢 Ordered images from frontend: ['Dashboard.png', 'Customers.png', 'add_customer.png']
2025-07-03 11:00:43,667 - DEBUG - 📷 Processing image: Dashboard.png
2025-07-03 11:00:45,662 - DEBUG - 📷 Processing image: Customers.png
2025-07-03 11:01:16,466 - DEBUG - 📷 Processing image: add_customer.png
2025-07-03 11:01:28,638 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-07-03 11:01:28,640 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-03 11:01:28,641 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-03 11:01:44,434 - INFO - 🟢 Ordered images from frontend: ['Dashboard.png', 'Customers.png', 'add_customer.png']
2025-07-03 11:01:44,448 - DEBUG - 📷 Processing image: Dashboard.png
2025-07-03 11:01:47,007 - DEBUG - 📷 Processing image: Customers.png
2025-07-03 11:02:18,815 - DEBUG - 📷 Processing image: add_customer.png
2025-07-03 11:02:30,413 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-07-03 11:02:30,415 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-03 11:02:30,416 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-03 11:02:35,495 - INFO - 🟢 Ordered images from frontend: ['Dashboard.png', 'Customers.png', 'add_customer.png']
2025-07-03 11:02:35,511 - DEBUG - 📷 Processing image: Dashboard.png
2025-07-03 11:02:43,182 - DEBUG - 📷 Processing image: Customers.png
2025-07-03 11:03:06,410 - DEBUG - 📷 Processing image: add_customer.png
2025-07-03 11:03:18,196 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-07-03 11:03:18,198 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-03 11:03:18,199 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-03 11:30:41,084 - INFO - 🟢 Ordered images from frontend: ['Dashboard.png', 'Customers.png', 'add_customer.png']
2025-07-03 11:30:41,131 - DEBUG - 📷 Processing image: Dashboard.png
2025-07-03 11:30:47,426 - DEBUG - 📷 Processing image: Customers.png
2025-07-03 11:30:50,541 - DEBUG - 📷 Processing image: add_customer.png
2025-07-03 11:31:05,589 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-07-03 11:31:05,591 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-03 11:31:05,593 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-03 11:35:25,216 - INFO - 🟢 Ordered images from frontend: ['dashboard.png', 'customers.png', 'add_customer.png']
2025-07-03 11:35:25,255 - DEBUG - 📷 Processing image: dashboard.png
2025-07-03 11:35:29,800 - DEBUG - 📷 Processing image: customers.png
2025-07-03 11:36:06,655 - DEBUG - 📷 Processing image: add_customer.png
2025-07-03 11:36:16,059 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-07-03 11:36:16,061 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-03 11:36:16,064 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-03 11:36:30,347 - INFO - 🟢 Ordered images from frontend: ['dashboard.png']
2025-07-03 11:36:30,359 - DEBUG - 📷 Processing image: dashboard.png
2025-07-03 11:36:37,150 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-07-03 11:36:37,152 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-03 11:36:37,153 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-03 11:36:46,223 - INFO - 🟢 Ordered images from frontend: ['dashboard.png']
2025-07-03 11:36:46,236 - DEBUG - 📷 Processing image: dashboard.png
2025-07-03 11:36:50,092 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-07-03 11:36:50,093 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-03 11:36:50,095 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-03 11:36:57,140 - INFO - 🟢 Ordered images from frontend: ['dashboard.png']
2025-07-03 11:36:57,157 - DEBUG - 📷 Processing image: dashboard.png
2025-07-03 11:37:00,637 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-07-03 11:37:00,639 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-03 11:37:00,640 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-03 11:37:05,006 - INFO - 🟢 Ordered images from frontend: ['dashboard.png']
2025-07-03 11:37:05,022 - DEBUG - 📷 Processing image: dashboard.png
2025-07-03 11:37:20,929 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-07-03 11:37:20,931 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-03 11:37:20,932 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-03 12:48:24,920 - INFO - 🟢 Ordered images from frontend: ['dashboard.png', 'customers.png', 'add_customer.png']
2025-07-03 12:48:24,967 - DEBUG - 📷 Processing image: dashboard.png
2025-07-03 12:48:33,196 - DEBUG - 📷 Processing image: customers.png
2025-07-03 12:48:35,274 - DEBUG - 📷 Processing image: add_customer.png
2025-07-03 12:48:40,219 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-07-03 12:48:40,221 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-03 12:48:40,223 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-03 12:51:36,795 - INFO - 🟢 Ordered images from frontend: ['dashboard.png', 'customers.png', 'add_customer.png']
2025-07-03 12:51:36,841 - DEBUG - 📷 Processing image: dashboard.png
2025-07-03 12:51:53,153 - DEBUG - 📷 Processing image: customers.png
2025-07-03 12:51:55,101 - DEBUG - 📷 Processing image: add_customer.png
2025-07-03 12:52:10,132 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-07-03 12:52:10,134 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-03 12:52:10,135 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-03 13:02:07,191 - INFO - 🟢 Ordered images from frontend: ['dashboard.png', 'customers.png', 'add_customer.png']
2025-07-03 13:02:07,237 - DEBUG - 📷 Processing image: dashboard.png
2025-07-03 13:02:25,721 - DEBUG - 📷 Processing image: customers.png
2025-07-03 13:02:42,882 - DEBUG - 📷 Processing image: add_customer.png
2025-07-03 13:02:59,645 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-07-03 13:02:59,647 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-03 13:02:59,649 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-03 15:06:18,425 - INFO - 🟢 Ordered images from frontend: ['customers.png', 'dashboard.png', 'newCustomer.png']
2025-07-03 15:06:18,488 - DEBUG - 📷 Processing image: customers.png
2025-07-03 15:06:58,252 - DEBUG - 📷 Processing image: dashboard.png
2025-07-03 15:07:15,998 - DEBUG - 📷 Processing image: newCustomer.png
2025-07-03 15:07:31,870 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-07-03 15:07:31,873 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-03 15:07:31,874 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-03 15:08:06,163 - INFO - 🟢 Ordered images from frontend: ['dashboard.png', 'customers.png', 'newCustomer.png']
2025-07-03 15:08:06,213 - DEBUG - 📷 Processing image: dashboard.png
2025-07-03 15:08:08,971 - DEBUG - 📷 Processing image: customers.png
2025-07-03 15:08:15,252 - DEBUG - 📷 Processing image: newCustomer.png
2025-07-03 15:10:01,882 - INFO - 🟢 Ordered images from frontend: ['dashboard.png', 'customers.png', 'newCustomer.png']
2025-07-03 15:10:01,932 - DEBUG - 📷 Processing image: dashboard.png
2025-07-03 15:10:07,153 - DEBUG - 📷 Processing image: customers.png
2025-07-03 15:10:11,694 - DEBUG - 📷 Processing image: newCustomer.png
2025-07-03 15:10:14,688 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-07-03 15:10:14,691 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-03 15:10:14,692 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-03 15:10:21,664 - INFO - 🟢 Ordered images from frontend: ['dashboard.png', 'customers.png', 'newCustomer.png']
2025-07-03 15:10:21,696 - DEBUG - 📷 Processing image: dashboard.png
2025-07-03 15:10:25,584 - DEBUG - 📷 Processing image: customers.png
2025-07-03 15:10:28,638 - DEBUG - 📷 Processing image: newCustomer.png
2025-07-03 15:10:41,989 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-07-03 15:10:41,991 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-03 15:10:41,992 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-03 15:13:48,391 - INFO - 🟢 Ordered images from frontend: ['dashboard.png', 'customers.png', 'newCustomer.png']
2025-07-03 15:13:48,440 - DEBUG - 📷 Processing image: dashboard.png
2025-07-03 15:13:56,304 - DEBUG - 📷 Processing image: customers.png
2025-07-03 15:14:00,067 - DEBUG - 📷 Processing image: newCustomer.png
2025-07-03 15:14:17,419 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-07-03 15:14:17,423 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-03 15:14:17,425 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-03 15:14:30,159 - INFO - 🟢 Ordered images from frontend: ['dashboard.png', 'customers.png']
2025-07-03 15:14:30,177 - DEBUG - 📷 Processing image: dashboard.png
2025-07-03 15:14:59,226 - DEBUG - 📷 Processing image: customers.png
2025-07-03 15:15:01,076 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-07-03 15:15:01,079 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-03 15:15:01,080 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-03 15:15:11,222 - INFO - 🟢 Ordered images from frontend: ['customers.png']
2025-07-03 15:15:11,237 - DEBUG - 📷 Processing image: customers.png
2025-07-03 15:15:13,605 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-07-03 15:15:13,607 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-03 15:15:13,608 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-03 15:15:19,646 - INFO - 🟢 Ordered images from frontend: ['customers.png']
2025-07-03 15:15:19,665 - DEBUG - 📷 Processing image: customers.png
2025-07-03 15:15:21,359 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-07-03 15:15:21,361 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-03 15:15:21,363 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-03 15:15:24,817 - INFO - 🟢 Ordered images from frontend: ['customers.png']
2025-07-03 15:15:24,836 - DEBUG - 📷 Processing image: customers.png
2025-07-03 15:15:29,387 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-07-03 15:15:29,389 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-03 15:15:29,390 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-03 15:15:40,347 - INFO - 🟢 Ordered images from frontend: ['customers.png']
2025-07-03 15:15:40,363 - DEBUG - 📷 Processing image: customers.png
2025-07-03 15:15:45,332 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-07-03 15:15:45,334 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-03 15:15:45,335 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-03 15:16:22,773 - INFO - 🟢 Ordered images from frontend: ['customers.png']
2025-07-03 15:16:22,801 - DEBUG - 📷 Processing image: customers.png
2025-07-03 15:16:26,013 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-07-03 15:16:26,016 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-03 15:16:26,017 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-03 15:16:31,566 - INFO - 🟢 Ordered images from frontend: ['customers.png']
2025-07-03 15:16:31,582 - DEBUG - 📷 Processing image: customers.png
2025-07-03 15:16:55,418 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-07-03 15:16:55,421 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-03 15:16:55,423 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-03 15:26:50,387 - INFO - 🟢 Ordered images from frontend: ['dashboard.png', 'customers.png', 'newCustomer.png']
2025-07-03 15:26:50,429 - DEBUG - 📷 Processing image: dashboard.png
2025-07-03 15:27:14,985 - DEBUG - 📷 Processing image: customers.png
2025-07-03 15:27:35,614 - DEBUG - 📷 Processing image: newCustomer.png
2025-07-03 15:27:51,604 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-07-03 15:27:51,606 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-03 15:27:51,608 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-03 18:40:37,997 - INFO - 🟢 Ordered images from frontend: ['dashboard.png', 'customers.png', 'newCustomer.png']
2025-07-03 18:40:38,097 - DEBUG - 📷 Processing image: dashboard.png
2025-07-03 18:40:44,182 - DEBUG - 📷 Processing image: customers.png
2025-07-03 18:40:49,382 - DEBUG - 📷 Processing image: newCustomer.png
2025-07-03 18:41:08,851 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-07-03 18:41:08,854 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-03 18:41:08,856 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-03 18:42:19,399 - INFO - 🟢 Ordered images from frontend: ['dashboard.png', 'customers.png', 'newCustomer.png']
2025-07-03 18:42:19,450 - DEBUG - 📷 Processing image: dashboard.png
2025-07-03 18:42:25,408 - DEBUG - 📷 Processing image: customers.png
2025-07-03 18:42:58,431 - DEBUG - 📷 Processing image: newCustomer.png
2025-07-03 18:43:15,783 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-07-03 18:43:15,787 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-03 18:43:15,788 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-03 18:43:33,857 - INFO - 🟢 Ordered images from frontend: ['dashboard.png', 'customers.png', 'newCustomer.png']
2025-07-03 18:43:33,915 - DEBUG - 📷 Processing image: dashboard.png
2025-07-03 18:43:38,796 - DEBUG - 📷 Processing image: customers.png
2025-07-03 18:44:07,431 - DEBUG - 📷 Processing image: newCustomer.png
2025-07-03 18:44:24,223 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-07-03 18:44:24,225 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-03 18:44:24,226 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-03 18:44:49,240 - INFO - 🟢 Ordered images from frontend: ['dashboard.png']
2025-07-03 18:44:49,256 - DEBUG - 📷 Processing image: dashboard.png
2025-07-03 18:45:05,469 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-07-03 18:45:05,471 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-03 18:45:05,472 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-03 18:45:11,418 - INFO - 🟢 Ordered images from frontend: ['dashboard.png']
2025-07-03 18:45:11,430 - DEBUG - 📷 Processing image: dashboard.png
2025-07-03 18:45:15,598 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-07-03 18:45:15,600 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-03 18:45:15,601 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-03 18:45:21,068 - INFO - 🟢 Ordered images from frontend: ['dashboard.png']
2025-07-03 18:45:21,085 - DEBUG - 📷 Processing image: dashboard.png
2025-07-03 18:45:29,564 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-07-03 18:45:29,567 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-03 18:45:29,568 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-03 18:48:28,701 - INFO - 🟢 Ordered images from frontend: ['dashboard.png', 'customers.png', 'newCustomer.png']
2025-07-03 18:48:28,748 - DEBUG - 📷 Processing image: dashboard.png
2025-07-03 18:48:47,901 - DEBUG - 📷 Processing image: customers.png
2025-07-03 18:48:53,958 - DEBUG - 📷 Processing image: newCustomer.png
2025-07-03 18:49:10,249 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-07-03 18:49:10,251 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-03 18:49:10,252 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-03 18:49:15,569 - INFO - 🟢 Ordered images from frontend: ['dashboard.png', 'customers.png', 'newCustomer.png']
2025-07-03 18:49:15,586 - DEBUG - 📷 Processing image: dashboard.png
2025-07-03 18:49:22,023 - DEBUG - 📷 Processing image: customers.png
2025-07-03 18:49:32,965 - DEBUG - 📷 Processing image: newCustomer.png
2025-07-03 18:49:59,682 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-07-03 18:49:59,683 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-03 18:49:59,685 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-03 18:50:10,364 - INFO - 🟢 Ordered images from frontend: ['dashboard.png', 'customers.png', 'newCustomer.png']
2025-07-03 18:50:10,395 - DEBUG - 📷 Processing image: dashboard.png
2025-07-03 18:50:15,625 - DEBUG - 📷 Processing image: customers.png
2025-07-03 18:50:51,015 - DEBUG - 📷 Processing image: newCustomer.png
2025-07-03 18:51:08,812 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-07-03 18:51:08,813 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-03 18:51:08,815 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-03 18:56:58,427 - INFO - 🟢 Ordered images from frontend: ['dashboard.png', 'customers.png', 'newCustomer.png']
2025-07-03 18:56:58,449 - DEBUG - 📷 Processing image: dashboard.png
2025-07-03 18:57:07,275 - DEBUG - 📷 Processing image: customers.png
2025-07-03 18:57:40,232 - DEBUG - 📷 Processing image: newCustomer.png
2025-07-03 18:58:02,620 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-07-03 18:58:02,622 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-03 18:58:02,623 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-05 18:35:51,453 - INFO - 🟢 Ordered images from frontend: ['dashboard.png', 'customers.png', 'newCustomer.png']
2025-07-05 18:35:51,545 - DEBUG - 📷 Processing image: dashboard.png
2025-07-05 18:36:11,503 - DEBUG - 📷 Processing image: customers.png
2025-07-05 18:36:46,041 - DEBUG - 📷 Processing image: newCustomer.png
2025-07-05 18:36:50,433 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-07-05 18:36:50,435 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-05 18:36:50,436 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-05 18:37:04,630 - INFO - 🟢 Ordered images from frontend: ['newCustomer.png']
2025-07-05 18:37:04,642 - DEBUG - 📷 Processing image: newCustomer.png
2025-07-05 18:37:20,007 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-07-05 18:37:20,009 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-05 18:37:20,010 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-15 20:07:41,256 - INFO - 🟢 Ordered images from frontend: ['login.png', 'inventory.png', 'cart.png', 'checkout_info.png', 'checkout_overview.png']
2025-07-15 20:07:41,383 - DEBUG - 📷 Processing image: login.png
2025-07-15 20:07:54,746 - DEBUG - 📷 Processing image: inventory.png
2025-07-15 20:08:08,175 - DEBUG - 📷 Processing image: cart.png
2025-07-15 20:08:18,648 - DEBUG - 📷 Processing image: checkout_info.png
2025-07-15 20:08:25,717 - DEBUG - 📷 Processing image: checkout_overview.png
2025-07-15 20:08:36,811 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-07-15 20:08:36,813 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-15 20:08:36,815 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-16 12:03:30,020 - INFO - 🟢 Ordered images from frontend: ['login.png', 'inventory.png', 'cart.png', 'checkout_info.png', 'checkout_overview.png']
2025-07-16 12:03:30,186 - DEBUG - 📷 Processing image: login.png
2025-07-16 12:03:46,708 - DEBUG - 📷 Processing image: inventory.png
2025-07-16 12:04:09,723 - DEBUG - 📷 Processing image: cart.png
2025-07-16 12:04:22,737 - DEBUG - 📷 Processing image: checkout_info.png
2025-07-16 12:04:29,365 - DEBUG - 📷 Processing image: checkout_overview.png
2025-07-16 12:04:31,500 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-07-16 12:04:31,502 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-16 12:04:31,504 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-16 12:04:59,059 - INFO - 🟢 Ordered images from frontend: ['checkout_overview.png']
2025-07-16 12:04:59,073 - DEBUG - 📷 Processing image: checkout_overview.png
2025-07-16 12:05:18,769 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-07-16 12:05:18,781 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-16 12:05:18,785 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-16 14:52:03,467 - INFO - 🟢 Ordered images from frontend: ['login.png', 'inventory.png', 'cart.png', 'checkout_info.png', 'checkout_overview.png']
2025-07-16 14:52:03,544 - DEBUG - 📷 Processing image: login.png
2025-07-16 14:52:17,149 - DEBUG - 📷 Processing image: inventory.png
2025-07-16 14:52:36,750 - DEBUG - 📷 Processing image: cart.png
2025-07-16 14:52:46,978 - DEBUG - 📷 Processing image: checkout_info.png
2025-07-16 14:52:52,952 - DEBUG - 📷 Processing image: checkout_overview.png
2025-07-16 14:52:55,805 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-07-16 14:52:55,808 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-16 14:52:55,809 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-16 14:53:17,348 - INFO - 🟢 Ordered images from frontend: ['checkout_overview.png']
2025-07-16 14:53:17,367 - DEBUG - 📷 Processing image: checkout_overview.png
2025-07-16 14:53:22,868 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-07-16 14:53:22,871 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-16 14:53:22,872 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-16 14:53:26,214 - INFO - 🟢 Ordered images from frontend: ['checkout_overview.png']
2025-07-16 14:53:26,232 - DEBUG - 📷 Processing image: checkout_overview.png
2025-07-16 14:53:28,586 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-07-16 14:53:28,589 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-16 14:53:28,591 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-16 14:53:30,922 - INFO - 🟢 Ordered images from frontend: ['checkout_overview.png']
2025-07-16 14:53:30,944 - DEBUG - 📷 Processing image: checkout_overview.png
2025-07-16 14:53:52,724 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-07-16 14:53:52,727 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-16 14:53:52,728 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-16 15:29:56,313 - INFO - 🟢 Ordered images from frontend: ['login.png', 'inventory.png', 'cart.png', 'checkout_info.png', 'checkout_overview.png']
2025-07-16 15:29:56,406 - DEBUG - 📷 Processing image: login.png
2025-07-16 15:30:19,255 - DEBUG - 📷 Processing image: inventory.png
2025-07-16 15:30:26,809 - DEBUG - 📷 Processing image: cart.png
2025-07-16 15:30:40,782 - DEBUG - 📷 Processing image: checkout_info.png
2025-07-16 15:30:51,041 - DEBUG - 📷 Processing image: checkout_overview.png
2025-07-16 15:31:17,498 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-07-16 15:31:17,529 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-16 15:31:17,531 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-16 15:31:26,564 - INFO - 🟢 Ordered images from frontend: ['inventory.png']
2025-07-16 15:31:26,588 - DEBUG - 📷 Processing image: inventory.png
2025-07-16 15:31:30,148 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-07-16 15:31:30,152 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-16 15:31:30,153 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-16 15:31:34,716 - INFO - 🟢 Ordered images from frontend: ['inventory.png']
2025-07-16 15:31:34,749 - DEBUG - 📷 Processing image: inventory.png
2025-07-16 15:32:11,486 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-07-16 15:32:11,688 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-16 15:32:11,764 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-16 22:15:32,717 - INFO - 🟢 Ordered images from frontend: ['dashboard.png', 'customers.png', 'customers_2.png']
2025-07-16 22:15:32,836 - DEBUG - 📷 Processing image: dashboard.png
2025-07-16 22:16:04,305 - DEBUG - 📷 Processing image: customers.png
2025-07-16 22:16:09,704 - DEBUG - 📷 Processing image: customers_2.png
2025-07-16 22:16:34,900 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-07-16 22:16:34,901 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-16 22:16:34,903 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-16 22:16:42,177 - INFO - 🟢 Ordered images from frontend: ['customers.png']
2025-07-16 22:16:42,189 - DEBUG - 📷 Processing image: customers.png
2025-07-16 22:16:50,431 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-07-16 22:16:50,433 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-16 22:16:50,434 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-16 22:16:54,736 - INFO - 🟢 Ordered images from frontend: ['customers.png']
2025-07-16 22:16:54,757 - DEBUG - 📷 Processing image: customers.png
2025-07-16 22:16:56,863 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-07-16 22:16:56,865 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-16 22:16:56,866 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-16 22:17:00,885 - INFO - 🟢 Ordered images from frontend: ['customers.png']
2025-07-16 22:17:00,900 - DEBUG - 📷 Processing image: customers.png
2025-07-16 22:17:26,599 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-07-16 22:17:26,600 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-16 22:17:26,602 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-16 22:19:07,307 - INFO - 🟢 Ordered images from frontend: ['dashboard.png', 'customers.png', 'customers_2.png']
2025-07-16 22:19:07,361 - DEBUG - 📷 Processing image: dashboard.png
2025-07-16 22:19:43,706 - DEBUG - 📷 Processing image: customers.png
2025-07-16 22:20:21,645 - DEBUG - 📷 Processing image: customers_2.png
2025-07-16 22:20:26,324 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-07-16 22:20:26,326 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-16 22:20:26,327 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-16 22:20:34,021 - INFO - 🟢 Ordered images from frontend: ['customers_2.png']
2025-07-16 22:20:34,033 - DEBUG - 📷 Processing image: customers_2.png
2025-07-16 22:21:02,467 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-07-16 22:21:02,468 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-16 22:21:02,469 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-16 22:28:19,918 - INFO - 🟢 Ordered images from frontend: ['dashboard.png', 'customers.png', 'customers_2.png']
2025-07-16 22:28:19,998 - DEBUG - 📷 Processing image: dashboard.png
2025-07-16 22:28:51,972 - DEBUG - 📷 Processing image: customers.png
2025-07-16 22:29:15,604 - DEBUG - 📷 Processing image: customers_2.png
2025-07-16 22:29:21,614 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-07-16 22:29:21,616 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-16 22:29:21,618 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-16 22:29:27,372 - INFO - 🟢 Ordered images from frontend: ['customers.png', 'customers_2.png']
2025-07-16 22:29:27,405 - DEBUG - 📷 Processing image: customers.png
2025-07-16 22:29:41,687 - DEBUG - 📷 Processing image: customers_2.png
2025-07-16 22:30:06,402 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-07-16 22:30:06,404 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-16 22:30:06,405 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-16 22:30:10,878 - INFO - 🟢 Ordered images from frontend: ['customers.png']
2025-07-16 22:30:10,901 - DEBUG - 📷 Processing image: customers.png
2025-07-16 22:30:15,027 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-07-16 22:30:15,029 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-16 22:30:15,030 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-16 22:30:17,931 - INFO - 🟢 Ordered images from frontend: ['customers.png']
2025-07-16 22:30:17,955 - DEBUG - 📷 Processing image: customers.png
2025-07-16 22:30:21,783 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-07-16 22:30:21,785 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-16 22:30:21,786 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-16 22:30:23,772 - INFO - 🟢 Ordered images from frontend: ['customers.png']
2025-07-16 22:30:23,797 - DEBUG - 📷 Processing image: customers.png
2025-07-16 22:30:29,092 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-07-16 22:30:29,094 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-16 22:30:29,095 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-16 22:30:33,658 - INFO - 🟢 Ordered images from frontend: ['customers.png']
2025-07-16 22:30:33,681 - DEBUG - 📷 Processing image: customers.png
2025-07-16 22:30:38,004 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-07-16 22:30:38,005 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-16 22:30:38,007 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-16 22:30:39,797 - INFO - 🟢 Ordered images from frontend: ['customers.png']
2025-07-16 22:30:39,823 - DEBUG - 📷 Processing image: customers.png
2025-07-16 22:30:43,737 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-07-16 22:30:43,738 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-16 22:30:43,739 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-16 22:30:47,339 - INFO - 🟢 Ordered images from frontend: ['customers.png']
2025-07-16 22:30:47,366 - DEBUG - 📷 Processing image: customers.png
2025-07-16 22:30:50,360 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-07-16 22:30:50,362 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-16 22:30:50,363 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-16 22:30:52,948 - INFO - 🟢 Ordered images from frontend: ['customers.png']
2025-07-16 22:30:52,970 - DEBUG - 📷 Processing image: customers.png
2025-07-16 22:30:56,618 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-07-16 22:30:56,620 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-16 22:30:56,621 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-16 22:31:04,016 - INFO - 🟢 Ordered images from frontend: ['customers.png']
2025-07-16 22:31:04,029 - DEBUG - 📷 Processing image: customers.png
2025-07-16 22:31:41,189 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-07-16 22:31:41,191 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-16 22:31:41,192 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-16 22:40:05,260 - INFO - 🟢 Ordered images from frontend: ['dashboard.png', 'customers.png', 'customers_2.png']
2025-07-16 22:40:05,339 - DEBUG - 📷 Processing image: dashboard.png
2025-07-16 22:40:09,358 - DEBUG - 📷 Processing image: customers.png
2025-07-16 22:40:11,991 - DEBUG - 📷 Processing image: customers_2.png
2025-07-16 22:40:35,291 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-07-16 22:40:35,295 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-16 22:40:35,298 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-16 22:40:41,756 - INFO - 🟢 Ordered images from frontend: ['dashboard.png', 'customers.png']
2025-07-16 22:40:41,789 - DEBUG - 📷 Processing image: dashboard.png
2025-07-16 22:41:04,988 - DEBUG - 📷 Processing image: customers.png
2025-07-16 22:41:32,293 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-07-16 22:41:32,298 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-16 22:41:32,299 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-17 10:24:21,461 - INFO - 🟢 Ordered images from frontend: ['dashboard.png', 'customers.png', 'customers_2.png']
2025-07-17 10:24:21,548 - DEBUG - 📷 Processing image: dashboard.png
2025-07-17 10:24:45,721 - DEBUG - 📷 Processing image: customers.png
2025-07-17 10:24:51,466 - DEBUG - 📷 Processing image: customers_2.png
2025-07-17 10:25:14,361 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-07-17 10:25:14,363 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-17 10:25:14,364 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-17 10:27:18,218 - INFO - 🟢 Ordered images from frontend: ['customers.png']
2025-07-17 10:27:18,251 - DEBUG - 📷 Processing image: customers.png
2025-07-17 10:27:49,883 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-07-17 10:27:49,885 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-17 10:27:49,886 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-17 10:45:13,692 - INFO - 🟢 Ordered images from frontend: ['login.png', 'inventory.png', 'cart.png', 'checkout_info.png', 'checkout_overview.png']
2025-07-17 10:45:13,772 - DEBUG - 📷 Processing image: login.png
2025-07-17 10:45:25,473 - DEBUG - 📷 Processing image: inventory.png
2025-07-17 10:45:42,163 - DEBUG - 📷 Processing image: cart.png
2025-07-17 10:45:50,287 - DEBUG - 📷 Processing image: checkout_info.png
2025-07-17 10:45:57,129 - DEBUG - 📷 Processing image: checkout_overview.png
2025-07-17 10:45:59,466 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-07-17 10:45:59,468 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-17 10:45:59,470 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-17 10:46:16,271 - INFO - 🟢 Ordered images from frontend: ['checkout_overview.png']
2025-07-17 10:46:16,296 - DEBUG - 📷 Processing image: checkout_overview.png
2025-07-17 10:46:29,014 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-07-17 10:46:29,017 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-17 10:46:29,019 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-18 11:35:27,594 - INFO - 🟢 Ordered images from frontend: ['dashboard.png', 'customers.png', 'customers_2.png']
2025-07-18 11:35:27,771 - DEBUG - 📷 Processing image: dashboard.png
2025-07-18 11:35:38,707 - DEBUG - 📷 Processing image: customers.png
2025-07-18 11:36:06,957 - DEBUG - 📷 Processing image: customers_2.png
2025-07-18 11:36:33,227 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-07-18 11:36:33,229 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-18 11:36:33,230 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-18 11:37:02,390 - INFO - 🟢 Ordered images from frontend: ['dashboard.png']
2025-07-18 11:37:02,410 - DEBUG - 📷 Processing image: dashboard.png
2025-07-18 11:37:23,654 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-07-18 11:37:23,656 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-18 11:37:23,657 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-18 12:10:46,047 - INFO - 🟢 Ordered images from frontend: ['customers_2.png']
2025-07-18 12:10:46,090 - DEBUG - 📷 Processing image: customers_2.png
2025-07-18 12:10:50,383 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-07-18 12:10:50,385 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-18 12:10:50,390 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-18 12:10:53,117 - INFO - 🟢 Ordered images from frontend: ['customers_2.png']
2025-07-18 12:10:53,156 - DEBUG - 📷 Processing image: customers_2.png
2025-07-18 12:10:55,329 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-07-18 12:10:55,331 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-18 12:10:55,332 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-18 12:10:57,734 - INFO - 🟢 Ordered images from frontend: ['customers_2.png']
2025-07-18 12:10:57,768 - DEBUG - 📷 Processing image: customers_2.png
2025-07-18 12:11:16,348 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-07-18 12:11:16,350 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-18 12:11:16,351 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-18 13:16:38,989 - INFO - 🟢 Ordered images from frontend: ['dashboard.png', 'customers.png', 'customers_2.png']
2025-07-18 13:16:39,125 - DEBUG - 📷 Processing image: dashboard.png
2025-07-18 13:17:16,945 - DEBUG - 📷 Processing image: customers.png
2025-07-18 13:17:43,627 - DEBUG - 📷 Processing image: customers_2.png
2025-07-18 13:18:11,129 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-07-18 13:18:11,132 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-18 13:18:11,133 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-18 14:59:25,459 - INFO - 🟢 Ordered images from frontend: ['dashboard.png', 'customers.png', 'customers_2.png']
2025-07-18 14:59:25,660 - DEBUG - 📷 Processing image: dashboard.png
2025-07-18 14:59:58,038 - DEBUG - 📷 Processing image: customers.png
2025-07-18 15:00:23,280 - DEBUG - 📷 Processing image: customers_2.png
2025-07-18 15:00:37,789 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-07-18 15:00:37,791 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-18 15:00:37,792 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-18 16:05:56,377 - INFO - 🟢 Ordered images from frontend: ['dashboard.png', 'customers.png', 'customers_2.png']
2025-07-18 16:05:56,482 - DEBUG - 📷 Processing image: dashboard.png
2025-07-18 16:06:16,467 - DEBUG - 📷 Processing image: customers.png
2025-07-18 16:06:19,119 - DEBUG - 📷 Processing image: customers_2.png
2025-07-18 16:06:26,245 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-07-18 16:06:26,248 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-18 16:06:26,250 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-18 16:06:33,744 - INFO - 🟢 Ordered images from frontend: ['customers.png', 'customers_2.png']
2025-07-18 16:06:33,771 - DEBUG - 📷 Processing image: customers.png
2025-07-18 16:06:37,692 - DEBUG - 📷 Processing image: customers_2.png
2025-07-18 16:06:53,309 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-07-18 16:06:53,311 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-18 16:06:53,312 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-18 16:06:59,444 - INFO - 🟢 Ordered images from frontend: ['customers.png']
2025-07-18 16:06:59,468 - DEBUG - 📷 Processing image: customers.png
2025-07-18 16:07:29,747 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-07-18 16:07:29,749 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-18 16:07:29,753 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-18 17:14:44,191 - INFO - 🟢 Ordered images from frontend: ['dashboard.png', 'customers.png', 'customers_2.png']
2025-07-18 17:14:44,291 - DEBUG - 📷 Processing image: dashboard.png
2025-07-18 17:14:48,715 - DEBUG - 📷 Processing image: customers.png
2025-07-18 17:15:16,072 - DEBUG - 📷 Processing image: customers_2.png
2025-07-18 17:15:28,914 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-07-18 17:15:28,916 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-18 17:15:28,918 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-18 17:15:34,718 - INFO - 🟢 Ordered images from frontend: ['dashboard.png']
2025-07-18 17:15:34,745 - DEBUG - 📷 Processing image: dashboard.png
2025-07-18 17:15:37,633 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-07-18 17:15:37,635 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-18 17:15:37,636 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-18 17:15:41,461 - INFO - 🟢 Ordered images from frontend: ['dashboard.png']
2025-07-18 17:15:41,480 - DEBUG - 📷 Processing image: dashboard.png
2025-07-18 17:15:45,401 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-07-18 17:15:45,402 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-18 17:15:45,404 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-18 17:15:47,817 - INFO - 🟢 Ordered images from frontend: ['dashboard.png']
2025-07-18 17:15:47,841 - DEBUG - 📷 Processing image: dashboard.png
2025-07-18 17:16:18,392 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-07-18 17:16:18,394 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-18 17:16:18,396 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-18 17:33:38,833 - INFO - 🟢 Ordered images from frontend: ['dashboard.png', 'customers.png', 'customers_2.png']
2025-07-18 17:33:38,963 - DEBUG - 📷 Processing image: dashboard.png
2025-07-18 17:34:10,746 - DEBUG - 📷 Processing image: customers.png
2025-07-18 17:34:41,594 - DEBUG - 📷 Processing image: customers_2.png
2025-07-18 17:34:57,612 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-07-18 17:34:57,614 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-18 17:34:57,615 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-18 17:41:07,938 - INFO - 🟢 Ordered images from frontend: ['dashboard.png', 'customers.png', 'customers_2.png']
2025-07-18 17:41:08,054 - DEBUG - 📷 Processing image: dashboard.png
2025-07-18 17:41:19,696 - DEBUG - 📷 Processing image: customers.png
2025-07-18 17:41:24,297 - DEBUG - 📷 Processing image: customers_2.png
2025-07-18 17:41:35,470 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-07-18 17:41:35,472 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-18 17:41:35,474 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-18 17:44:47,818 - INFO - 🟢 Ordered images from frontend: ['dashboard.png']
2025-07-18 17:44:47,839 - DEBUG - 📷 Processing image: dashboard.png
2025-07-18 17:45:08,088 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-07-18 17:45:08,090 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-18 17:45:08,091 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-18 17:48:25,051 - INFO - 🟢 Ordered images from frontend: ['dashboard.png', 'customers.png', 'customers_2.png']
2025-07-18 17:48:25,225 - DEBUG - 📷 Processing image: dashboard.png
2025-07-18 17:48:29,625 - DEBUG - 📷 Processing image: customers.png
2025-07-18 17:48:59,687 - DEBUG - 📷 Processing image: customers_2.png
2025-07-18 17:49:04,853 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-07-18 17:49:04,855 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-18 17:49:04,856 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-18 17:49:23,473 - INFO - 🟢 Ordered images from frontend: ['dashboard.png', 'customers_2.png']
2025-07-18 17:49:23,495 - DEBUG - 📷 Processing image: dashboard.png
2025-07-18 17:49:29,087 - DEBUG - 📷 Processing image: customers_2.png
2025-07-18 17:49:57,930 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-07-18 17:49:57,932 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-18 17:49:57,933 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-18 17:51:26,132 - INFO - 🟢 Ordered images from frontend: ['dashboard.png']
2025-07-18 17:51:26,148 - DEBUG - 📷 Processing image: dashboard.png
2025-07-18 17:52:02,550 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-07-18 17:52:02,552 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-18 17:52:02,553 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-18 17:54:51,065 - INFO - 🟢 Ordered images from frontend: ['customer_2.png']
2025-07-18 17:54:51,085 - DEBUG - 📷 Processing image: customer_2.png
2025-07-18 17:54:55,663 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-07-18 17:54:55,665 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-18 17:54:55,666 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-18 17:55:00,050 - INFO - 🟢 Ordered images from frontend: ['customer_2.png']
2025-07-18 17:55:00,068 - DEBUG - 📷 Processing image: customer_2.png
2025-07-18 17:55:01,355 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-07-18 17:55:01,357 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-18 17:55:01,358 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-18 17:55:15,711 - INFO - 🟢 Ordered images from frontend: ['customer_2.png']
2025-07-18 17:55:15,731 - DEBUG - 📷 Processing image: customer_2.png
2025-07-18 17:55:22,273 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-07-18 17:55:22,275 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-18 17:55:22,276 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-18 17:55:23,954 - INFO - 🟢 Ordered images from frontend: ['customer_2.png']
2025-07-18 17:55:23,974 - DEBUG - 📷 Processing image: customer_2.png
2025-07-18 17:55:37,698 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-07-18 17:55:37,700 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-18 17:55:37,701 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-18 18:24:45,668 - INFO - 🟢 Ordered images from frontend: ['dashboard.png', 'customers.png', 'customers_2.png']
2025-07-18 18:24:45,881 - DEBUG - 📷 Processing image: dashboard.png
2025-07-18 18:24:50,153 - DEBUG - 📷 Processing image: customers.png
2025-07-18 18:24:52,137 - DEBUG - 📷 Processing image: customers_2.png
2025-07-18 18:25:15,199 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-07-18 18:25:15,203 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-18 18:25:15,206 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-18 18:25:32,488 - INFO - 🟢 Ordered images from frontend: ['dashboard.png', 'customers.png']
2025-07-18 18:25:32,517 - DEBUG - 📷 Processing image: dashboard.png
2025-07-18 18:25:35,020 - DEBUG - 📷 Processing image: customers.png
2025-07-18 18:26:16,518 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-07-18 18:26:16,520 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-18 18:26:16,522 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-18 18:28:07,729 - INFO - 🟢 Ordered images from frontend: ['dashboard.png']
2025-07-18 18:28:07,754 - DEBUG - 📷 Processing image: dashboard.png
2025-07-18 18:28:14,239 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-07-18 18:28:14,248 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-18 18:28:14,255 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-18 18:28:44,937 - INFO - 🟢 Ordered images from frontend: ['dashboard.png']
2025-07-18 18:28:44,977 - DEBUG - 📷 Processing image: dashboard.png
2025-07-18 18:29:12,537 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-07-18 18:29:12,539 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-18 18:29:12,542 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-19 17:44:49,980 - INFO - 🟢 Ordered images from frontend: ['dashboard.png', 'customers.png', 'customers_2.png']
2025-07-19 17:44:50,181 - DEBUG - 📷 Processing image: dashboard.png
2025-07-19 17:45:25,683 - DEBUG - 📷 Processing image: customers.png
2025-07-19 17:45:47,295 - DEBUG - 📷 Processing image: customers_2.png
2025-07-19 17:46:09,835 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-07-19 17:46:09,837 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-19 17:46:09,839 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-19 18:13:03,565 - INFO - 🟢 Ordered images from frontend: ['dashboard.png', 'customers.png', 'customers_2.png']
2025-07-19 18:13:03,766 - DEBUG - 📷 Processing image: dashboard.png
2025-07-19 18:13:27,014 - DEBUG - 📷 Processing image: customers.png
2025-07-19 18:13:31,162 - DEBUG - 📷 Processing image: customers_2.png
2025-07-19 18:13:45,516 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-07-19 18:13:45,517 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-19 18:13:45,519 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-19 18:13:53,984 - INFO - 🟢 Ordered images from frontend: ['customers.png']
2025-07-19 18:13:54,013 - DEBUG - 📷 Processing image: customers.png
2025-07-19 18:14:10,521 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-07-19 18:14:10,523 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-19 18:14:10,524 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-19 18:23:28,476 - INFO - 🟢 Ordered images from frontend: ['dashboard.png', 'customers.png', 'customers_2.png']
2025-07-19 18:23:28,625 - DEBUG - 📷 Processing image: dashboard.png
2025-07-19 18:24:02,379 - DEBUG - 📷 Processing image: customers.png
2025-07-19 18:24:18,224 - DEBUG - 📷 Processing image: customers_2.png
2025-07-19 18:24:33,442 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-07-19 18:24:33,453 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-19 18:24:33,455 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-19 20:10:32,345 - INFO - 🟢 Ordered images from frontend: ['dashboard.png', 'customers.png', 'customers_2.png']
2025-07-19 20:10:32,466 - DEBUG - 📷 Processing image: dashboard.png
2025-07-19 20:10:49,774 - DEBUG - 📷 Processing image: customers.png
2025-07-19 20:11:02,917 - DEBUG - 📷 Processing image: customers_2.png
2025-07-19 20:11:13,843 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-07-19 20:11:13,845 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-19 20:11:13,847 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-19 20:27:38,587 - INFO - 🟢 Ordered images from frontend: ['dashboard.png', 'customers.png', 'customers_2.png']
2025-07-19 20:27:38,614 - DEBUG - 📷 Processing image: dashboard.png
2025-07-19 20:27:51,724 - DEBUG - 📷 Processing image: customers.png
2025-07-19 20:28:21,397 - DEBUG - 📷 Processing image: customers_2.png
2025-07-19 20:28:28,586 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-07-19 20:28:28,676 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-19 20:28:28,678 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-19 20:31:40,293 - INFO - 🟢 Ordered images from frontend: ['dashboard.png', 'customers.png', 'customers_2.png']
2025-07-19 20:31:40,374 - DEBUG - 📷 Processing image: dashboard.png
2025-07-19 20:31:44,236 - DEBUG - 📷 Processing image: customers.png
2025-07-19 20:32:00,662 - DEBUG - 📷 Processing image: customers_2.png
2025-07-19 20:32:10,427 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-07-19 20:32:10,436 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-19 20:32:10,439 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-19 20:35:55,387 - INFO - 🟢 Ordered images from frontend: ['dashboard.png', 'customers.png', 'customers_2.png']
2025-07-19 20:35:55,410 - DEBUG - 📷 Processing image: dashboard.png
2025-07-19 20:36:02,245 - DEBUG - 📷 Processing image: customers.png
2025-07-19 20:36:09,506 - DEBUG - 📷 Processing image: customers_2.png
2025-07-19 20:36:18,568 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-07-19 20:36:18,570 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-19 20:36:18,575 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-19 20:56:55,490 - INFO - 🟢 Ordered images from frontend: ['dashboard.png', 'customers.png', 'customers_2.png']
2025-07-19 20:56:55,586 - DEBUG - 📷 Processing image: dashboard.png
2025-07-19 20:57:02,883 - DEBUG - 📷 Processing image: customers.png
2025-07-19 20:57:15,189 - DEBUG - 📷 Processing image: customers_2.png
2025-07-19 20:57:24,646 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-07-19 20:57:24,648 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-19 20:57:24,649 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-19 21:12:49,948 - INFO - 🟢 Ordered images from frontend: ['dashboard.png', 'customers.png', 'customers_2.png']
2025-07-19 21:12:50,025 - DEBUG - 📷 Processing image: dashboard.png
2025-07-19 21:13:03,939 - DEBUG - 📷 Processing image: customers.png
2025-07-19 21:13:05,776 - DEBUG - 📷 Processing image: customers_2.png
2025-07-19 21:13:20,171 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-07-19 21:13:20,173 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-19 21:13:20,174 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-19 21:15:55,933 - INFO - 🟢 Ordered images from frontend: ['dashboard.png', 'customers.png', 'customers_2.png']
2025-07-19 21:15:55,960 - DEBUG - 📷 Processing image: dashboard.png
2025-07-19 21:16:15,250 - DEBUG - 📷 Processing image: customers.png
2025-07-19 21:16:18,076 - DEBUG - 📷 Processing image: customers_2.png
2025-07-19 21:16:41,936 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-07-19 21:16:41,938 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-19 21:16:41,939 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-19 22:27:35,852 - INFO - 🟢 Ordered images from frontend: ['dashboard.png', 'customers.png', 'customers_2.png']
2025-07-19 22:27:36,041 - DEBUG - 📷 Processing image: dashboard.png
2025-07-19 22:27:40,662 - DEBUG - 📷 Processing image: customers.png
2025-07-19 22:27:44,460 - DEBUG - 📷 Processing image: customers_2.png
2025-07-19 22:28:00,387 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-07-19 22:28:00,389 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-19 22:28:00,390 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-19 22:28:33,862 - INFO - 🟢 Ordered images from frontend: ['dashboard.png', 'customers.png', 'customers_2.png']
2025-07-19 22:28:33,902 - DEBUG - 📷 Processing image: dashboard.png
2025-07-19 22:28:46,759 - DEBUG - 📷 Processing image: customers.png
2025-07-19 22:28:54,259 - DEBUG - 📷 Processing image: customers_2.png
2025-07-19 22:28:56,461 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-07-19 22:28:56,464 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-19 22:28:56,465 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-19 22:32:52,265 - INFO - 🟢 Ordered images from frontend: ['dashboard.png', 'customers.png', 'customers_2.png']
2025-07-19 22:32:52,436 - DEBUG - 📷 Processing image: dashboard.png
2025-07-19 22:32:58,245 - DEBUG - 📷 Processing image: customers.png
2025-07-19 22:33:02,229 - DEBUG - 📷 Processing image: customers_2.png
2025-07-19 22:33:16,943 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-07-19 22:33:16,945 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-19 22:33:16,947 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-19 22:35:27,011 - INFO - 🟢 Ordered images from frontend: ['dashboard.png', 'customers.png', 'customers_2.png']
2025-07-19 22:35:27,049 - DEBUG - 📷 Processing image: dashboard.png
2025-07-19 22:35:29,682 - DEBUG - 📷 Processing image: customers.png
2025-07-19 22:35:44,836 - DEBUG - 📷 Processing image: customers_2.png
2025-07-19 22:35:56,113 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-07-19 22:35:56,118 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-19 22:35:56,119 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-19 22:46:11,718 - INFO - 🟢 Ordered images from frontend: ['dashboard.png', 'customers.png', 'customers_2.png']
2025-07-19 22:46:11,793 - DEBUG - 📷 Processing image: dashboard.png
2025-07-19 22:46:24,080 - ERROR - ❌ Error in upload_image
Traceback (most recent call last):
  File "C:\Users\Suchandan\Desktop\VNC\testify-automator-ai\backend\apis\image_text_api.py", line 138, in upload_image
    metadata_list = await process_image_gpt(
                    ^^^^^^^^^^^^^^^^^^^^^^^^
    ...<3 lines>...
    )
    ^
  File "C:\Users\Suchandan\Desktop\VNC\testify-automator-ai\backend\logic\image_text_extractor.py", line 281, in process_image_gpt
    f.write("|" * 30, " After Cleaning ", "|" * 30 + "\n")
    ~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
TypeError: TextIOWrapper.write() takes exactly one argument (3 given)
2025-07-19 22:53:26,615 - INFO - 🟢 Ordered images from frontend: ['dashboard.png', 'customers.png', 'customers_2.png']
2025-07-19 22:53:26,703 - DEBUG - 📷 Processing image: dashboard.png
2025-07-19 22:53:40,400 - DEBUG - 📷 Processing image: customers.png
2025-07-19 22:53:43,362 - DEBUG - 📷 Processing image: customers_2.png
2025-07-19 22:53:54,698 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-07-19 22:53:54,700 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-19 22:53:54,702 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-19 22:57:35,485 - INFO - 🟢 Ordered images from frontend: ['dashboard.png', 'customers.png', 'customers_2.png']
2025-07-19 22:57:35,627 - DEBUG - 📷 Processing image: dashboard.png
2025-07-19 22:57:42,358 - DEBUG - 📷 Processing image: customers.png
2025-07-19 22:57:48,098 - DEBUG - 📷 Processing image: customers_2.png
2025-07-19 22:58:01,576 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-07-19 22:58:01,578 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-19 22:58:01,579 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-19 23:02:11,567 - INFO - 🟢 Ordered images from frontend: ['dashboard.png', 'customers.png', 'customers_2.png']
2025-07-19 23:02:11,585 - DEBUG - 📷 Processing image: dashboard.png
2025-07-19 23:02:18,724 - DEBUG - 📷 Processing image: customers.png
2025-07-19 23:02:20,834 - DEBUG - 📷 Processing image: customers_2.png
2025-07-19 23:02:34,155 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-07-19 23:02:34,157 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-19 23:02:34,158 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-19 23:03:26,450 - INFO - 🟢 Ordered images from frontend: ['dashboard.png', 'customers.png', 'customers_2.png']
2025-07-19 23:03:26,475 - DEBUG - 📷 Processing image: dashboard.png
2025-07-19 23:03:39,649 - DEBUG - 📷 Processing image: customers.png
2025-07-19 23:04:01,965 - DEBUG - 📷 Processing image: customers_2.png
2025-07-19 23:04:08,688 - INFO - 📝 Saved all raw GPT metadata to data\raw_data_from_gpt.json
2025-07-19 23:04:08,690 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-19 23:04:08,692 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-20 17:58:00,438 - INFO - 🟢 Ordered images from frontend: ['dashboard.png', 'customers.png', 'customers_2.png']
2025-07-20 17:58:00,541 - DEBUG - 📷 Processing image: dashboard.png
2025-07-20 17:58:15,078 - ERROR - ❌ Error in upload_image
Traceback (most recent call last):
  File "C:\Users\Suchandan\Desktop\VNC\testify-automator-ai\backend\apis\image_text_api.py", line 138, in upload_image
    metadata_list = await process_image_gpt(
                    ^^^^^^^^^^^^^^^^^^^^^^^^
    ...<3 lines>...
    )
    ^
  File "C:\Users\Suchandan\Desktop\VNC\testify-automator-ai\backend\logic\image_text_extractor.py", line 231, in process_image_gpt
    metadata = build_standard_metadata(
        element,
        page_name,
        image_path=region_path
    )
  File "C:\Users\Suchandan\Desktop\VNC\testify-automator-ai\backend\utils\file_utils.py", line 41, in build_standard_metadata
    unique_name = generate_unique_name(page_name, label_text, ocr_type, intent)
  File "C:\Users\Suchandan\Desktop\VNC\testify-automator-ai\backend\utils\file_utils.py", line 93, in generate_unique_name
    hash_part = hashlib.sha256(unique_str.encode("utf-8")).hexdigest()[:8]
                               ^^^^^^^^^^
NameError: name 'unique_str' is not defined
2025-07-20 18:02:57,533 - INFO - 🟢 Ordered images from frontend: ['dashboard.png', 'customers.png', 'customers_2.png']
2025-07-20 18:02:57,614 - DEBUG - 📷 Processing image: dashboard.png
2025-07-20 18:03:07,379 - DEBUG - 📷 Processing image: customers.png
2025-07-20 18:03:32,960 - ERROR - ❌ Error in upload_image
Traceback (most recent call last):
  File "C:\Users\Suchandan\Desktop\VNC\testify-automator-ai\backend\apis\image_text_api.py", line 151, in upload_image
    json.dump(metadata_list, f, indent=4, ensure_ascii=False)
    ~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\Suchandan\AppData\Local\Programs\Python\Python313\Lib\json\__init__.py", line 179, in dump
    for chunk in iterable:
                 ^^^^^^^^
  File "C:\Users\Suchandan\AppData\Local\Programs\Python\Python313\Lib\json\encoder.py", line 430, in _iterencode
    yield from _iterencode_list(o, _current_indent_level)
  File "C:\Users\Suchandan\AppData\Local\Programs\Python\Python313\Lib\json\encoder.py", line 326, in _iterencode_list
    yield from chunks
  File "C:\Users\Suchandan\AppData\Local\Programs\Python\Python313\Lib\json\encoder.py", line 406, in _iterencode_dict
    yield from chunks
  File "C:\Users\Suchandan\AppData\Local\Programs\Python\Python313\Lib\json\encoder.py", line 439, in _iterencode
    o = _default(o)
  File "C:\Users\Suchandan\AppData\Local\Programs\Python\Python313\Lib\json\encoder.py", line 180, in default
    raise TypeError(f'Object of type {o.__class__.__name__} '
                    f'is not JSON serializable')
TypeError: Object of type ndarray is not JSON serializable
2025-07-20 18:14:39,759 - INFO - 🟢 Ordered images from frontend: ['dashboard.png', 'customers.png', 'customers_2.png']
2025-07-20 18:14:39,839 - DEBUG - 📷 Processing image: dashboard.png
2025-07-20 18:15:04,325 - DEBUG - 📷 Processing image: customers.png
2025-07-20 18:15:34,042 - DEBUG - 📷 Processing image: customers_2.png
2025-07-20 18:15:44,239 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-20 18:15:44,240 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-20 21:52:05,431 - INFO - 🟢 Ordered images from frontend: ['dashboard.png', 'customers.png', 'customers_2.png']
2025-07-20 21:52:05,562 - DEBUG - 📷 Processing image: dashboard.png
2025-07-20 21:52:27,401 - DEBUG - 📷 Processing image: customers.png
2025-07-20 21:52:46,256 - DEBUG - 📷 Processing image: customers_2.png
2025-07-20 21:52:55,655 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-20 21:52:55,657 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-20 22:15:38,979 - INFO - 🟢 Ordered images from frontend: ['dashboard.png', 'customers.png', 'customers_2.png']
2025-07-20 22:15:39,001 - DEBUG - 📷 Processing image: dashboard.png
2025-07-20 22:15:42,144 - DEBUG - 📷 Processing image: customers.png
2025-07-20 22:15:44,264 - DEBUG - 📷 Processing image: customers_2.png
2025-07-20 22:15:51,948 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-20 22:15:51,949 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-20 22:29:33,862 - INFO - 🟢 Ordered images from frontend: ['dashboard.png', 'customers.png', 'customers_2.png']
2025-07-20 22:29:33,945 - DEBUG - 📷 Processing image: dashboard.png
2025-07-20 22:29:55,860 - DEBUG - 📷 Processing image: customers.png
2025-07-20 22:29:58,721 - DEBUG - 📷 Processing image: customers_2.png
2025-07-20 22:30:10,910 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-20 22:30:10,911 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-20 23:41:42,966 - INFO - 🟢 Ordered images from frontend: ['dashboard.png', 'customers.png', 'customers_2.png']
2025-07-20 23:41:43,047 - DEBUG - 📷 Processing image: dashboard.png
2025-07-20 23:41:48,158 - DEBUG - 📷 Processing image: customers.png
2025-07-20 23:41:51,828 - DEBUG - 📷 Processing image: customers_2.png
2025-07-20 23:42:01,797 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-20 23:42:01,798 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-20 23:42:13,611 - INFO - 🟢 Ordered images from frontend: ['dashboard.png', 'customers.png', 'customers_2.png']
2025-07-20 23:42:13,633 - DEBUG - 📷 Processing image: dashboard.png
2025-07-20 23:42:16,726 - DEBUG - 📷 Processing image: customers.png
2025-07-20 23:42:43,234 - DEBUG - 📷 Processing image: customers_2.png
2025-07-20 23:42:51,089 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-20 23:42:51,090 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-20 23:43:24,281 - INFO - 🟢 Ordered images from frontend: ['dashboard.png', 'customers.png', 'customers_2.png']
2025-07-20 23:43:24,304 - DEBUG - 📷 Processing image: dashboard.png
2025-07-20 23:43:31,984 - DEBUG - 📷 Processing image: customers.png
2025-07-20 23:43:57,431 - DEBUG - 📷 Processing image: customers_2.png
2025-07-20 23:44:12,139 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-20 23:44:12,140 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-20 23:47:20,135 - INFO - 🟢 Ordered images from frontend: ['dashboard.png']
2025-07-20 23:47:20,152 - DEBUG - 📷 Processing image: dashboard.png
2025-07-20 23:47:40,956 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-20 23:47:40,957 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-20 23:52:44,926 - INFO - 🟢 Ordered images from frontend: ['dashboard.png']
2025-07-20 23:52:45,198 - DEBUG - 📷 Processing image: dashboard.png
2025-07-20 23:53:15,410 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-20 23:53:15,411 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-21 01:43:34,212 - INFO - 🟢 Ordered images from frontend: ['dashboard.png', 'customers.png', 'customers_2.png']
2025-07-21 01:43:34,336 - DEBUG - 📷 Processing image: dashboard.png
2025-07-21 01:43:59,257 - DEBUG - 📷 Processing image: customers.png
2025-07-21 01:44:21,823 - DEBUG - 📷 Processing image: customers_2.png
2025-07-21 01:44:35,949 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-21 01:44:35,951 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-21 02:13:19,848 - INFO - 🟢 Ordered images from frontend: ['customers_2.png']
2025-07-21 02:13:19,998 - DEBUG - 📷 Processing image: customers_2.png
2025-07-21 02:13:35,574 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-21 02:13:35,577 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-21 02:42:01,324 - INFO - 🟢 Ordered images from frontend: ['dashboard.png', 'customers.png', 'customers_2.png']
2025-07-21 02:42:01,415 - DEBUG - 📷 Processing image: dashboard.png
2025-07-21 02:42:17,339 - DEBUG - 📷 Processing image: customers.png
2025-07-21 02:42:20,547 - DEBUG - 📷 Processing image: customers_2.png
2025-07-21 02:42:29,157 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-21 02:42:29,158 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-21 02:42:39,512 - INFO - 🟢 Ordered images from frontend: ['dashboard.png', 'customers.png']
2025-07-21 02:42:39,534 - DEBUG - 📷 Processing image: dashboard.png
2025-07-21 02:42:47,322 - DEBUG - 📷 Processing image: customers.png
2025-07-21 02:43:10,034 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-21 02:43:10,035 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-21 02:45:10,930 - INFO - 🟢 Ordered images from frontend: ['dashboard.png']
2025-07-21 02:45:10,969 - DEBUG - 📷 Processing image: dashboard.png
2025-07-21 02:45:33,110 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-21 02:45:33,111 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-21 02:56:38,115 - INFO - 🟢 Ordered images from frontend: ['login.png', 'inventory.png', 'cart.png', 'checkout_info.png', 'checkout_overview.png']
2025-07-21 02:56:38,211 - DEBUG - 📷 Processing image: login.png
2025-07-21 02:56:45,591 - DEBUG - 📷 Processing image: inventory.png
2025-07-21 02:57:00,463 - DEBUG - 📷 Processing image: cart.png
2025-07-21 02:57:02,318 - DEBUG - 📷 Processing image: checkout_info.png
2025-07-21 02:57:09,419 - DEBUG - 📷 Processing image: checkout_overview.png
2025-07-21 02:57:19,510 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-21 02:57:19,512 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-21 02:57:35,137 - INFO - 🟢 Ordered images from frontend: ['cart.png']
2025-07-21 02:57:35,157 - DEBUG - 📷 Processing image: cart.png
2025-07-21 02:57:40,841 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-21 02:57:40,843 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-21 11:23:33,890 - INFO - 🟢 Ordered images from frontend: ['dashboard.png', 'customers.png', 'customers_2.png']
2025-07-21 11:23:34,243 - DEBUG - 📷 Processing image: dashboard.png
2025-07-21 11:23:42,386 - DEBUG - 📷 Processing image: customers.png
2025-07-21 11:24:05,777 - DEBUG - 📷 Processing image: customers_2.png
2025-07-21 11:24:18,179 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-21 11:24:18,180 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-21 11:26:32,511 - INFO - 🟢 Ordered images from frontend: ['dashboard.png']
2025-07-21 11:26:32,530 - DEBUG - 📷 Processing image: dashboard.png
2025-07-21 11:26:35,679 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-21 11:26:35,681 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-21 11:26:53,785 - INFO - 🟢 Ordered images from frontend: ['dashboard.png']
2025-07-21 11:26:53,807 - DEBUG - 📷 Processing image: dashboard.png
2025-07-21 11:27:21,414 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-21 11:27:21,415 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-21 11:43:08,703 - INFO - 🟢 Ordered images from frontend: ['customers_2.png']
2025-07-21 11:43:09,236 - DEBUG - 📷 Processing image: customers_2.png
2025-07-21 11:43:12,270 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-21 11:43:12,272 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-21 11:43:24,921 - INFO - 🟢 Ordered images from frontend: ['customers_2.png']
2025-07-21 11:43:24,944 - DEBUG - 📷 Processing image: customers_2.png
2025-07-21 11:43:37,767 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-21 11:43:37,768 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-21 11:45:45,967 - INFO - 🟢 Ordered images from frontend: ['customers_2.png']
2025-07-21 11:45:45,993 - DEBUG - 📷 Processing image: customers_2.png
2025-07-21 11:45:57,047 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-21 11:45:57,049 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-21 11:47:02,413 - INFO - 🟢 Ordered images from frontend: ['customers_2.png']
2025-07-21 11:47:02,437 - DEBUG - 📷 Processing image: customers_2.png
2025-07-21 11:47:12,215 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-21 11:47:12,216 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-21 11:58:25,487 - INFO - 🟢 Ordered images from frontend: ['customers_2.png']
2025-07-21 11:58:25,514 - DEBUG - 📷 Processing image: customers_2.png
2025-07-21 11:58:35,650 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-21 11:58:35,651 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-21 12:07:14,299 - INFO - 🟢 Ordered images from frontend: ['customers_2.png']
2025-07-21 12:07:14,454 - DEBUG - 📷 Processing image: customers_2.png
2025-07-21 12:07:37,544 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-21 12:07:37,546 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-21 12:15:17,904 - INFO - 🟢 Ordered images from frontend: ['customers_2.png']
2025-07-21 12:15:18,417 - DEBUG - 📷 Processing image: customers_2.png
2025-07-21 12:15:31,625 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-21 12:15:31,627 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-21 12:16:03,414 - INFO - 🟢 Ordered images from frontend: ['dashboard.png', 'customers.png', 'customers_2.png']
2025-07-21 12:16:03,442 - DEBUG - 📷 Processing image: dashboard.png
2025-07-21 12:16:21,226 - DEBUG - 📷 Processing image: customers.png
2025-07-21 12:16:48,295 - DEBUG - 📷 Processing image: customers_2.png
2025-07-21 12:16:58,153 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-21 12:16:58,154 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-21 12:35:18,310 - INFO - 🟢 Ordered images from frontend: ['dashboard.png', 'customers.png', 'customers_2.png']
2025-07-21 12:35:18,396 - DEBUG - 📷 Processing image: dashboard.png
2025-07-21 12:36:17,301 - DEBUG - 📷 Processing image: customers.png
2025-07-21 12:36:42,907 - DEBUG - 📷 Processing image: customers_2.png
2025-07-21 12:36:53,361 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-21 12:36:53,363 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-21 18:52:33,101 - INFO - 🟢 Ordered images from frontend: ['login.png', 'inventory.png', 'cart.png', 'checkout_info.png', 'checkout_overview.png']
2025-07-21 18:52:33,364 - DEBUG - 📷 Processing image: login.png
2025-07-21 18:52:45,250 - DEBUG - 📷 Processing image: inventory.png
2025-07-21 18:53:02,113 - DEBUG - 📷 Processing image: cart.png
2025-07-21 18:53:12,267 - DEBUG - 📷 Processing image: checkout_info.png
2025-07-21 18:53:19,857 - DEBUG - 📷 Processing image: checkout_overview.png
2025-07-21 18:53:31,288 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-21 18:53:31,292 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-21 23:43:56,358 - INFO - 🟢 Ordered images from frontend: ['dashboard.png', 'customers.png', 'customers_2.png']
2025-07-21 23:43:56,743 - DEBUG - 📷 Processing image: dashboard.png
2025-07-21 23:44:23,833 - DEBUG - 📷 Processing image: customers.png
2025-07-21 23:44:57,362 - DEBUG - 📷 Processing image: customers_2.png
2025-07-21 23:45:11,479 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-21 23:45:11,481 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-21 23:47:06,526 - INFO - 🟢 Ordered images from frontend: ['dashboard.png', 'customers.png', 'customers_2.png']
2025-07-21 23:47:06,600 - DEBUG - 📷 Processing image: dashboard.png
2025-07-21 23:47:33,374 - DEBUG - 📷 Processing image: customers.png
2025-07-21 23:48:00,714 - DEBUG - 📷 Processing image: customers_2.png
2025-07-21 23:48:12,946 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-21 23:48:12,947 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-23 19:42:24,000 - INFO - 🟢 Ordered images from frontend: ['dashboard.png', 'customers.png', 'customers_2.png']
2025-07-23 19:42:24,372 - DEBUG - 📷 Processing image: dashboard.png
2025-07-23 19:43:09,568 - DEBUG - 📷 Processing image: customers.png
2025-07-23 19:43:34,302 - DEBUG - 📷 Processing image: customers_2.png
2025-07-23 19:43:46,677 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-23 19:43:46,679 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-25 11:15:37,360 - INFO - 🟢 Ordered images from frontend: ['dashboard.png', 'customers.png', 'customers_2.png']
2025-07-25 11:15:37,638 - DEBUG - 📷 Processing image: dashboard.png
2025-07-25 11:16:06,453 - DEBUG - 📷 Processing image: customers.png
2025-07-25 11:16:31,800 - DEBUG - 📷 Processing image: customers_2.png
2025-07-25 11:16:41,808 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-25 11:16:41,810 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-25 11:34:28,801 - INFO - 🟢 Ordered images from frontend: ['dashboard.png', 'customers.png', 'customers_2.png']
2025-07-25 11:34:28,980 - DEBUG - 📷 Processing image: dashboard.png
2025-07-25 11:34:48,580 - DEBUG - 📷 Processing image: customers.png
2025-07-25 11:35:10,952 - DEBUG - 📷 Processing image: customers_2.png
2025-07-25 11:35:24,194 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-25 11:35:24,196 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-25 11:40:24,105 - INFO - 🟢 Ordered images from frontend: ['customers.png', 'dashboard.png', 'customers_2.png']
2025-07-25 11:40:24,183 - DEBUG - 📷 Processing image: customers.png
2025-07-25 11:40:48,848 - DEBUG - 📷 Processing image: customers_2.png
2025-07-25 11:40:59,391 - DEBUG - 📷 Processing image: dashboard.png
2025-07-25 11:41:28,376 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-25 11:41:28,377 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-25 11:44:51,322 - INFO - 🟢 Ordered images from frontend: ['dashboard.png', 'customers.png', 'customers_2.png']
2025-07-25 11:44:51,403 - DEBUG - 📷 Processing image: dashboard.png
2025-07-25 11:45:00,338 - DEBUG - 📷 Processing image: customers.png
2025-07-25 11:45:34,696 - DEBUG - 📷 Processing image: customers_2.png
2025-07-25 11:45:47,300 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-25 11:45:47,301 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-25 11:45:49,013 - INFO - 🟢 Ordered images from frontend: ['dashboard.png']
2025-07-25 11:45:49,026 - DEBUG - 📷 Processing image: dashboard.png
2025-07-25 11:45:55,869 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-25 11:45:55,870 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-25 11:45:58,092 - INFO - 🟢 Ordered images from frontend: ['dashboard.png']
2025-07-25 11:45:58,115 - DEBUG - 📷 Processing image: dashboard.png
2025-07-25 11:46:22,060 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-25 11:46:22,062 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-25 11:50:13,792 - INFO - 🟢 Ordered images from frontend: ['customers.png', 'dashboard.png', 'customers_2.png']
2025-07-25 11:50:13,862 - DEBUG - 📷 Processing image: customers.png
2025-07-25 11:50:38,761 - DEBUG - 📷 Processing image: customers_2.png
2025-07-25 11:50:51,303 - DEBUG - 📷 Processing image: dashboard.png
2025-07-25 11:50:58,001 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-25 11:50:58,002 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-25 11:52:47,998 - INFO - 🟢 Ordered images from frontend: ['dashboard.png', 'customers.png', 'customers_2.png']
2025-07-25 11:52:48,071 - DEBUG - 📷 Processing image: dashboard.png
2025-07-25 11:53:11,985 - DEBUG - 📷 Processing image: customers.png
2025-07-25 11:53:37,290 - DEBUG - 📷 Processing image: customers_2.png
2025-07-25 11:53:49,906 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-25 11:53:49,908 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-25 12:35:23,882 - INFO - 🟢 Ordered images from frontend: ['dashboard.png', 'customers.png', 'customers_2.png']
2025-07-25 12:35:24,041 - DEBUG - 📷 Processing image: dashboard.png
2025-07-25 12:35:52,813 - DEBUG - 📷 Processing image: customers.png
2025-07-25 12:36:29,439 - DEBUG - 📷 Processing image: customers_2.png
2025-07-25 12:36:39,589 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-25 12:36:39,591 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-26 00:25:43,524 - INFO - 🟢 Ordered images from frontend: ['dashboard.png', 'customers.png', 'customers_2.png']
2025-07-26 00:25:43,688 - DEBUG - 📷 Processing image: dashboard.png
2025-07-26 00:26:22,051 - DEBUG - 📷 Processing image: customers.png
2025-07-26 00:27:09,640 - DEBUG - 📷 Processing image: customers_2.png
2025-07-26 00:27:25,693 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-26 00:27:25,696 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-26 10:36:08,195 - INFO - 🟢 Ordered images from frontend: ['dashboard.png', 'customers.png', 'customers_2.png']
2025-07-26 10:36:08,362 - DEBUG - 📷 Processing image: dashboard.png
2025-07-26 10:36:39,774 - DEBUG - 📷 Processing image: customers.png
2025-07-26 10:37:09,770 - DEBUG - 📷 Processing image: customers_2.png
2025-07-26 10:37:19,611 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-26 10:37:19,613 - INFO - 📄 Ordered images logged to data/image_order.json
2025-07-26 15:12:55,451 - INFO - 🟢 Ordered images from frontend: ['dashboard.png', 'customers.png', 'customers_2.png']
2025-07-26 15:12:55,727 - DEBUG - 📷 Processing image: dashboard.png
2025-07-26 15:13:15,366 - DEBUG - 📷 Processing image: customers.png
2025-07-26 15:13:39,034 - DEBUG - 📷 Processing image: customers_2.png
2025-07-26 15:13:48,667 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-07-26 15:13:48,669 - INFO - 📄 Ordered images logged to data/image_order.json



# === FILE: .pytest_cache\README.md ===
# pytest cache directory #

This directory contains data from the pytest's cache plugin,
which provides the `--lf` and `--ff` options, as well as the `cache` fixture.

**Do not** commit this to version control.

See [the docs](https://docs.pytest.org/en/stable/how-to/cache.html) for more information.



# === FILE: agents\agent_manifest_python.json ===
{
  "agent_name": "PlaywrightPythonAgent",
  "language": "python",
  "capabilities": ["codegen", "run", "explain"],
  "actions": [
      { "action": "generate_method", "input": "elementSpec", "output": "code" },
      { "action": "generate_test", "input": "testCaseSpec", "output": "code" },
      { "action": "generate_page_file", "input": "pageSpec", "output": "code" }
  ]
}



# === FILE: agents\agent_manifest_typescript.json ===
{
  "agent_name": "PlaywrightTypescriptAgent",
  "language": "typescript",
  "capabilities": ["codegen", "run", "explain"],
  "actions": [
    {"action": "generate_method", "input": "elementSpec", "output": "code"},
    {"action": "generate_test", "input": "testCaseSpec", "output": "code"},
    {"action": "generate_page_file", "input": "entries", "output": "file"}
  ]
}



# === FILE: agents\python_agent.py ===
import re
from mcp.protocol import MCPAgentBase, MCPResponse
from utils.match_utils import normalize_page_name


def safe(name: str) -> str:
    return re.sub(r'\W+', '_', name.lower()).strip('_')


class PlaywrightPythonAgent(MCPAgentBase):
    def generate_method(self, element_spec):
        return MCPResponse(False, error="generate_method is now part of generate_page_file")

    def generate_test(self, test_case_spec):
        page_imports = test_case_spec["imports"]  # e.g. ['from pages.dashboard_page import DashboardPage']
        method_calls = test_case_spec["calls"]    # e.g. ['await page.enter_username("standard_user")', ...]

        code = "\n".join([
            *page_imports,
            "\n\nasync def test_generated_flow(smartai_page):",
            "    page = DashboardPage(smartai_page)",
            *["    " + line for line in method_calls]
        ])
        return MCPResponse(True, code)

    def generate_page_file(self, payload):
        entries = payload["entries"]
        page_name = normalize_page_name(payload.get("page_name", "page"))
        class_name = f"{page_name.capitalize()}Page"

        import_block = (
            "import asyncio\n"
            "from services.page_enricher import enrich_page\n"
            "from utils.enrichment_status import is_enriched\n"
        )

        class_header = (
            f"\n\nclass {class_name}:\n"
            f"    def __init__(self, playwright_page):\n"
            f"        self.page = playwright_page\n"
            f"        self.page_name = \"{page_name}\"\n"
            f"        self._enriched = False\n\n"
            f"    async def _enrich_if_needed(self, force=False):\n"
            f"        if force or not is_enriched(self.page_name):\n"
            f"            await enrich_page(self.page, self.page_name)\n"
            f"            self._enriched = True\n"
        )

        method_blocks = []
        seen_method_names = set()

        ignored_types = {}

        for entry in entries:
            ocr_type = (entry.get("ocr_type") or "").lower()
            label = entry.get("label_text", "") or entry.get(
                "intent", "") or "element"
            smartai_name = entry.get("unique_name", "")
            base_name = safe(label)

            if ocr_type in ignored_types:
                continue  # Skip passive elements

            # --- Map ocr_type to method template ---
            if ocr_type in ("textbox", "text", "textarea", "password", "email", "input"):
                method_name = f"enter_{base_name}"
                block = (
                    f"    async def {method_name}(self, value):\n"
                    f"        await self._enrich_if_needed()\n"
                    f"        await self.page.smartAI('{smartai_name}').fill(value)\n"
                )

            elif ocr_type in ("button", "submit", "link", "iconbutton", "imagebutton", "tab", "panel", "accordion", "menu", "breadcrumb"):
                method_name = f"click_{base_name}"
                block = (
                    f"    async def {method_name}(self):\n"
                    f"        await self._enrich_if_needed()\n"
                    f"        await self.page.smartAI('{smartai_name}').click()\n"
                )

            elif ocr_type in ("select", "dropdown", "combobox"):
                method_name = f"select_{base_name}"
                block = (
                    f"    async def {method_name}(self, value):\n"
                    f"        await self._enrich_if_needed()\n"
                    f"        await self.page.smartAI('{smartai_name}').select_option(value)\n"
                )

            elif ocr_type == "multiselect":
                method_name = f"select_{base_name}_values"
                block = (
                    f"    async def {method_name}(self, values):\n"
                    f"        await self._enrich_if_needed()\n"
                    f"        await self.page.smartAI('{smartai_name}').select_options(values)\n"
                )

            elif ocr_type in ("checkbox", "switch", "toggle"):
                method_name = f"toggle_{base_name}"
                block = (
                    f"    async def {method_name}(self):\n"
                    f"        await self._enrich_if_needed()\n"
                    f"        await self.page.smartAI('{smartai_name}').click()\n"
                )

            elif ocr_type in ("date", "datepicker", "time", "timepicker", "slider", "range"):
                method_name = f"set_{base_name}"
                block = (
                    f"    async def {method_name}(self, value):\n"
                    f"        await self._enrich_if_needed()\n"
                    f"        await self.page.smartAI('{smartai_name}').fill(value)\n"
                )

            elif ocr_type in ("image", "avatar", "userpic", "badge", "chip", "tag", "alert", "modal", "toast", "dialog"):
                method_name = f"verify_{base_name}_visible"
                block = (
                    f"    async def {method_name}(self):\n"
                    f"        await self._enrich_if_needed()\n"
                    f"        assert await self.page.smartAI('{smartai_name}').is_visible()\n"
                )

            elif ocr_type == "pagination":
                method_name = f"goto_{base_name}"
                block = (
                    f"    async def {method_name}(self, page_number):\n"
                    f"        await self._enrich_if_needed()\n"
                    f"        await self.page.smartAI('{smartai_name}').goto_page(page_number)\n"
                )

            elif ocr_type in ("table", "grid", "datatable"):
                method_name = f"read_{base_name}_data"
                block = (
                    f"    async def {method_name}(self):\n"
                    f"        await self._enrich_if_needed()\n"
                    f"        return await self.page.smartAI('{smartai_name}').get_table_data()\n"
                )

            elif ocr_type in ("file", "upload", "fileinput"):
                method_name = f"upload_{base_name}"
                block = (
                    f"    async def {method_name}(self, file_path):\n"
                    f"        await self._enrich_if_needed()\n"
                    f"        await self.page.smartAI('{smartai_name}').set_input_files(file_path)\n"
                )

            else:
                method_name = f"interact_{base_name}"
                block = (
                    f"    async def {method_name}(self):\n"
                    f"        await self._enrich_if_needed()\n"
                    f"        # TODO: Define behavior for '{ocr_type}'\n"
                )

            # Avoid duplicates
            if method_name in seen_method_names:
                continue
            seen_method_names.add(method_name)
            method_blocks.append(block)

        # Assemble file
        code = import_block + "\n\n" + class_header + "\n".join(method_blocks)
        filename = f"{page_name}_page.py"

        return MCPResponse(True, {
            "page_file": filename,
            "code": code
        })



# === FILE: agents\typescript_agent.py ===
from mcp.protocol import MCPAgentBase, MCPResponse
import re

import re

def safe_ts(s):
    # Remove quotes, keep only alphanumerics/underscore, limit to 50 chars
    return re.sub(r'\W+', '_', s.replace("'", "").replace('"', "").lower())[:50].strip('_')

def build_method_ts(entry, language="typescript"):
    ocr_type = (entry.get("ocr_type") or "").lower()
    intent = (entry.get("intent") or "").lower()
    label_text = entry.get("label_text", "")
    unique_name = entry.get("unique_name")

    def func(name):
        label = (label_text or intent or name).replace("'", "").replace('"', "")
        if len(label) > 50:
            label = label[:50]
        return safe_ts(label)

    # --- Text Inputs ---
    if ocr_type in ("textbox", "text", "input"):
        func_name = f"enter_{func('textbox')}"
        code = (
            f"export function {func_name}(page, value) {{\n"
            f"    page.smartAI('{unique_name}').fill(value);\n"
            f"}}\n"
        )
    elif ocr_type == "textarea":
        func_name = f"enter_{func('textarea')}"
        code = (
            f"export function {func_name}(page, value) {{\n"
            f"    page.smartAI('{unique_name}').fill(value);\n"
            f"}}\n"
        )
    elif ocr_type == "password":
        func_name = f"enter_{func('password')}"
        code = (
            f"export function {func_name}(page, value) {{\n"
            f"    page.smartAI('{unique_name}').fill(value);\n"
            f"}}\n"
        )
    elif ocr_type == "email":
        func_name = f"enter_{func('email')}"
        code = (
            f"export function {func_name}(page, value) {{\n"
            f"    page.smartAI('{unique_name}').fill(value);\n"
            f"}}\n"
        )
    # --- Buttons, Links, Icons ---
    elif ocr_type in ("button", "submit", "iconbutton"):
        func_name = f"click_{func('button')}"
        code = (
            f"export function {func_name}(page) {{\n"
            f"    page.smartAI('{unique_name}').click();\n"
            f"}}\n"
        )
    elif ocr_type in ("link", "anchor"):
        func_name = f"click_{func('link')}"
        code = (
            f"export function {func_name}(page) {{\n"
            f"    page.smartAI('{unique_name}').click();\n"
            f"}}\n"
        )
    elif ocr_type == "imagebutton":
        func_name = f"click_{func('imagebutton')}"
        code = (
            f"export function {func_name}(page) {{\n"
            f"    page.smartAI('{unique_name}').click();\n"
            f"}}\n"
        )
    # --- Selectors ---
    elif ocr_type in ("select", "dropdown", "combobox"):
        func_name = f"select_{func('select')}"
        code = (
            f"export function {func_name}(page, value) {{\n"
            f"    page.smartAI('{unique_name}').selectOption(value);\n"
            f"}}\n"
        )
    elif ocr_type == "multiselect":
        func_name = f"select_{func('multiselect')}_values"
        code = (
            f"export function {func_name}(page, values) {{\n"
            f"    page.smartAI('{unique_name}').selectOptions(values);\n"
            f"}}\n"
        )
    # --- Checkboxes, Radios, Toggles, Switches ---
    elif ocr_type == "checkbox":
        func_name = f"toggle_{func('checkbox')}"
        code = (
            f"export function {func_name}(page) {{\n"
            f"    page.smartAI('{unique_name}').click();\n"
            f"}}\n"
        )
    elif ocr_type in ("radio", "radiogroup"):
        func_name = f"select_{func('radio')}_option"
        code = (
            f"export function {func_name}(page, value) {{\n"
            f"    page.smartAI('{unique_name}').check(value);\n"
            f"}}\n"
        )
    elif ocr_type in ("toggle", "switch"):
        func_name = f"toggle_{func('toggle')}"
        code = (
            f"export function {func_name}(page) {{\n"
            f"    page.smartAI('{unique_name}').click();\n"
            f"}}\n"
        )
    # --- Date/Time Pickers ---
    elif ocr_type in ("date", "datepicker"):
        func_name = f"pick_{func('date')}"
        code = (
            f"export function {func_name}(page, value) {{\n"
            f"    page.smartAI('{unique_name}').fill(value);\n"
            f"}}\n"
        )
    elif ocr_type in ("time", "timepicker"):
        func_name = f"pick_{func('time')}"
        code = (
            f"export function {func_name}(page, value) {{\n"
            f"    page.smartAI('{unique_name}').fill(value);\n"
            f"}}\n"
        )
    # --- File Upload ---
    elif ocr_type in ("file", "fileinput", "upload"):
        func_name = f"upload_{func('file')}"
        code = (
            f"export function {func_name}(page, filePath) {{\n"
            f"    page.smartAI('{unique_name}').setInputFiles(filePath);\n"
            f"}}\n"
        )
    # --- Table/Grid/Data Grid ---
    elif ocr_type in ("table", "datatable", "grid"):
        func_name = f"read_{func('table')}_data"
        code = (
            f"export function {func_name}(page) {{\n"
            f"    return page.smartAI('{unique_name}').getTableData();\n"
            f"}}\n"
        )
    elif ocr_type in ("tablecell", "cell"):
        func_name = f"get_{func('cell')}_text"
        code = (
            f"export function {func_name}(page, row, col) {{\n"
            f"    return page.smartAI('{unique_name}').getCellText(row, col);\n"
            f"}}\n"
        )
    # --- Image ---
    elif ocr_type == "image":
        func_name = f"verify_{func('image')}_visible"
        code = (
            f"export async function {func_name}(page) {{\n"
            f"    if (!(await page.smartAI('{unique_name}').isVisible())) throw new Error('Element not visible');\n"
            f"}}\n"
        )
    # --- Slider/Range ---
    elif ocr_type in ("slider", "range"):
        func_name = f"set_{func('slider')}_value"
        code = (
            f"export function {func_name}(page, value) {{\n"
            f"    page.smartAI('{unique_name}').fill(value);\n"
            f"}}\n"
        )
    # --- Progressbar ---
    elif ocr_type == "progressbar":
        func_name = f"get_{func('progressbar')}_value"
        code = (
            f"export function {func_name}(page) {{\n"
            f"    return page.smartAI('{unique_name}').getAttribute('value');\n"
            f"}}\n"
        )
    # --- Alert/Dialog/Modal/Toast ---
    elif ocr_type in ("alert", "dialog", "modal", "toast"):
        func_name = f"verify_{func('alert')}_visible"
        code = (
            f"export async function {func_name}(page) {{\n"
            f"    if (!(await page.smartAI('{unique_name}').isVisible())) throw new Error('Element not visible');\n"
            f"}}\n"
        )
    # --- Tab/Accordion/Panel ---
    elif ocr_type in ("tab", "tabpanel"):
        func_name = f"open_{func('tab')}"
        code = (
            f"export function {func_name}(page) {{\n"
            f"    page.smartAI('{unique_name}').click();\n"
            f"}}\n"
        )
    elif ocr_type in ("accordion", "panel"):
        func_name = f"expand_{func('accordion')}"
        code = (
            f"export function {func_name}(page) {{\n"
            f"    page.smartAI('{unique_name}').click();\n"
            f"}}\n"
        )
    # --- Tree/Treeview ---
    elif ocr_type in ("tree", "treeview"):
        func_name = f"expand_{func('tree')}"
        code = (
            f"export function {func_name}(page, nodeLabel) {{\n"
            f"    page.smartAI('{unique_name}').expandNode(nodeLabel);\n"
            f"}}\n"
        )
    # --- Menu ---
    elif ocr_type in ("menu", "menubar"):
        func_name = f"open_{func('menu')}"
        code = (
            f"export function {func_name}(page) {{\n"
            f"    page.smartAI('{unique_name}').click();\n"
            f"}}\n"
        )
    # --- Breadcrumb ---
    elif ocr_type == "breadcrumb":
        func_name = f"navigate_{func('breadcrumb')}"
        code = (
            f"export function {func_name}(page, crumbLabel) {{\n"
            f"    page.smartAI('{unique_name}').clickCrumb(crumbLabel);\n"
            f"}}\n"
        )
    # --- Badge/Chip/Tag ---
    elif ocr_type in ("badge", "chip", "tag"):
        func_name = f"verify_{func('badge')}_visible"
        code = (
            f"export async function {func_name}(page) {{\n"
            f"    if (!(await page.smartAI('{unique_name}').isVisible())) throw new Error('Element not visible');\n"
            f"}}\n"
        )
    # --- Avatar/Userpic ---
    elif ocr_type in ("avatar", "userpic"):
        func_name = f"verify_{func('avatar')}_visible"
        code = (
            f"export async function {func_name}(page) {{\n"
            f"    if (!(await page.smartAI('{unique_name}').isVisible())) throw new Error('Element not visible');\n"
            f"}}\n"
        )
    # --- Pagination ---
    elif ocr_type == "pagination":
        func_name = f"goto_{func('page')}"
        code = (
            f"export function {func_name}(page, pageNumber) {{\n"
            f"    page.smartAI('{unique_name}').gotoPage(pageNumber);\n"
            f"}}\n"
        )
    # --- Default/Fallback ---
    else:
        func_name = f"verify_{func('element')}_visible"
        code = (
            f"export async function {func_name}(page) {{\n"
            f"    if (!(await page.smartAI('{unique_name}').isVisible())) throw new Error('Element not visible');\n"
            f"}}\n"
        )
    return code

class PlaywrightTypescriptAgent(MCPAgentBase):
    def generate_method(self, element_spec):
        code = build_method_ts(element_spec)
        return MCPResponse(True, code)

    def generate_test(self, test_case_spec):
        steps = "\n    ".join(test_case_spec.get("steps", []))
        code = (
            "import { test } from '@playwright/test';\n"
            "import * as methods from './page_methods';\n\n"
            "test('Generated Test', async ({ page }) => {\n"
            f"    {steps}\n"
            "});\n"
        )
        return MCPResponse(True, code)

    def generate_page_file(self, payload):
        entries = payload["entries"]
        page_name = payload.get("page_name", "page")
        header = (
            "// SmartAI Patch Import here if needed\n"
            f"// Methods for page: {page_name}\n\n"
        )
        methods = [self.generate_method(e).payload for e in entries]
        filename = f"{page_name}_page_methods.ts"  # TypeScript agent returns .ts
        code = header + "\n".join(methods)
        return MCPResponse(True, {"filename": filename, "code": code})



# === FILE: apis\chroma_debug_api.py ===
from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse, FileResponse
from services.chroma_service import collection as chroma_collection
import json
from pathlib import Path

router = APIRouter()

EXPORT_PATH = Path("chromadb_export.json")

@router.get("/debug/export-chromadb")
async def export_chroma_data(
    record_type: str = Query(None, description="Filter by record type: 'ocr', 'locator', etc."),
    locator_null: bool = Query(False, description="Only include entries where locator is null"),
    page_name: str = Query(None, description="Filter by page name"),
    as_file: bool = Query(False, description="If true, return as downloadable JSON file")
):
    try:
        data = chroma_collection.get(include=["documents", "metadatas", "embeddings"])
        results = []

        for idx, meta in enumerate(data["metadatas"]):
            doc = data["documents"][idx]
            item = {"text": doc}
            item.update(meta)

            if record_type and item.get("type") != record_type:
                continue

            if locator_null and item.get("locator") not in [None, ""]:
                continue

            if page_name and item.get("page_name") != page_name:
                continue

            results.append(item)

        if as_file:
            with open(EXPORT_PATH, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            return FileResponse(EXPORT_PATH, filename="chromadb_export.json", media_type="application/json")

        return JSONResponse(content={"count": len(results), "data": results})

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})



# === FILE: apis\enrichment_api.py ===
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

async def send_enrichment_requests(page_name: str):
    from httpx import AsyncClient, HTTPStatusError

    BASE = "http://localhost:8001"  # ← make sure this matches your uvicorn port!

    async with AsyncClient(timeout=None) as client:
        # 1) set the page name
        try:
            r = await client.post(f"{BASE}/set-current-page-name", json={"page_name": page_name})
            r.raise_for_status()
        except Exception as e:
            print(f"🔥Error setting page name: {e!r}")
            return {"status": "fail", "count": 0, "error": str(e)}

        # 2) call enrichment endpoint
        try:
            time.sleep(5)
            resp = await client.post(f"{BASE}/capture-dom-from-client", json={})
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


# === FILE: apis\generate_from_manual_testcases.py ===
from fastapi import APIRouter
from pydantic import BaseModel, Field
from datetime import datetime
import re
from services.test_generation_utils import client

router = APIRouter()

class ManualTestcaseRequest(BaseModel):
    manual_testcase: str | list[str] = Field(..., example=[
        "1. Navigate to login page",
        "2. Enter username 'standard_user'",
        "3. Enter password 'secret_sauce'",
        "4. Click Login button",
        "5. Verify Products page is displayed"
    ])
    prompt: str = Field(
    default=(
        "Write a Playwright Python test for the following manual steps.\n"
        "- Use only visible selectors (get_by_text, get_by_role, get_by_placeholder).\n"
        "- Print before each action.\n"
        "- For every verification, 'should be displayed', or 'verify' step, add a Playwright `expect` assertion, such as `expect(page.get_by_text('...')).to_be_visible()`.\n"
        "- Do not use page.locator or xpath.\n"
        "- Site URL: {site_url}\n"
        "Steps:\n"
        "{manual_steps}"
        )
    )
    site_url: str = Field(default="https://www.saucedemo.com/")

@router.post("/rag/generate-from-manual-testcase")
def generate_from_manual_testcase(req: ManualTestcaseRequest):
    manual_steps = "\n".join(req.manual_testcase) if isinstance(req.manual_testcase, list) else req.manual_testcase.strip()
    prompt = req.prompt.format(manual_steps=manual_steps, site_url=req.site_url)
    result = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=4096
    )
    test_code = result.choices[0].message.content.strip()
    code = re.sub(r"```(?:python)?|```|^\s*Here is.*?:", "", test_code, flags=re.MULTILINE).strip()

    # Write to file in root folder
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"test_manualcase_{timestamp}.py"
    filepath = filename  # root folder
    # Optionally add Playwright import if not present
    if "from playwright.sync_api" not in code:
        code = "from playwright.sync_api import sync_playwright, expect\n\n" + code

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(code)
    
    return {"auto_testcase": code, "filename": filename}



# === FILE: apis\generate_from_story.py ===
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pathlib import Path
import re
import json
import ast
import pandas as pd
from pydantic import BaseModel, Field
from typing import List, Optional
import textwrap
from chromadb import PersistentClient
import io

from services.test_generation_utils import openai_client
from utils.prompt_utils import build_prompt
from utils.match_utils import normalize_page_name
from services.graph_service import read_dependency_graph, get_adjacency_list, find_path

router = APIRouter()
chroma_client = PersistentClient(path="./data/chroma_db")
collection = chroma_client.get_or_create_collection(name="element_metadata")


def create_default_test_data(run_folder):
    data = {
        "login": {"username": "standard_user", "password": "secret_sauce"},
        "checkout": {"first_name": "John", "last_name": "Doe", "zip_code": "12345"},
        "product": {"name": "Sauce Labs Backpack"}
    }
    data_dir = Path(run_folder) / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "__init__.py").touch()
    with open(data_dir / "test_data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def extract_method_names_from_file(file_path):
    method_names = []
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("async def "):
            m = re.match(
                r"async def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(", stripped)
            if m:
                method_names.append(m.group(1))
    return method_names


def get_all_page_methods(pages_dir):
    page_method_map = {}
    for py_file in Path(pages_dir).glob("*_page.py"):
        page_name = py_file.stem.replace("_page", "")
        method_list = extract_method_names_from_file(py_file)
        print(f"📄 {page_name}: {len(method_list)} methods")
        page_method_map[page_name] = method_list
    return page_method_map


def next_index(target_dir, pattern="test_{}.py"):
    files = list(target_dir.glob(pattern.format("*")))
    indices = [int(m.group(1))
               for f in files if (m := re.match(r".*_(\d+)\.", f.name))]
    return max(indices, default=0) + 1


def generate_test_code_from_methods(user_story, method_map, page_names, site_url):
    dynamic_steps = []
    for page, methods in method_map.items():
        for method in methods:
            if method.startswith("enter_"):
                param = method.replace("enter_", "")
                dynamic_steps.append(
                    f"    - Call `await {page}_page.{method}(\"<{param}>\")`")
            elif method.startswith("click_") or method.startswith("select_"):
                dynamic_steps.append(
                    f"    - Call `await {page}_page.{method}()`")

    story_block = f'"""{user_story.strip()}"""'
    method_prompt_block = json.dumps(
        {f"{page}_page": methods for page, methods in method_map.items()}, indent=2)

    prompt = f"""
You are an expert QA automation engineer.

You are given the following:
- A user story.
- A set of page classes with available async methods.
- Each page is initialized like `customers_page = CustomersPage(page)`
- Method calls are in the form: `await page_name.method_name()` or `await page_name.method_name(value)`

Using only the available methods, generate a full Playwright async test case that fulfills the story.

Constraints:
- Use only the provided method names.
- Do not generate selectors or locators.
- Use `async def` test function.
- Use `await` before all page method calls.
- Do not explain anything. Output code only.

User Story:
{story_block}

Pages and Methods:
{method_prompt_block}

URL: {site_url}
"""

    result = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=4096,
        temperature=0
    )

    print("\n📤 Prompt sent to LLM:\n", prompt)
    print("\n📥 LLM raw response:\n", result.choices[0].message.content)

    clean_output = re.sub(r"```(?:python)?|^\s*Here is.*?:", "",
                          result.choices[0].message.content.strip(), flags=re.MULTILINE).strip()
    return clean_output


def get_inferred_pages(user_story: str, method_map_full: dict):
    page_list_str = "\n".join(
        [f"{i+1}. {k.replace('_', ' ')}" for i, k in enumerate(method_map_full.keys())])
    prompt = f"""
You are an expert QA automation engineer.
Given the following available application pages:
{page_list_str}

Here is a user story:
\"\"\"{user_story}\"\"\"

Output ONLY a Python list (in order) of the page keys (use the keys exactly as shown) that must be visited for this story. Do not explain.
"""
    result = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=2000,
        temperature=0
    )
    try:
        output = result.choices[0].message.content.strip()
        return [p for p in ast.literal_eval(output) if p in method_map_full]
    except Exception:
        return list(method_map_full.keys())


@router.post("/rag/generate-from-story")
async def generate_from_user_story(
    user_story: Optional[str] = Form(None),
    site_url: Optional[str] = Form(
        "https://preview--bank-buddy-crm-react.lovable.app/"),
    file: Optional[UploadFile] = File(None)
):
    run_folder = Path("generated_runs") / "src"
    pages_dir = run_folder / "pages"
    tests_dir = run_folder / "tests"
    for d in [pages_dir, tests_dir]:
        d.mkdir(parents=True, exist_ok=True)
        (d / "__init__.py").touch()

    stories = []
    if file:
        content = await file.read()
        if file.filename.endswith((".xls", ".xlsx")):
            xls = pd.ExcelFile(io.BytesIO(content))
            df = pd.read_excel(io.BytesIO(content), sheet_name="User Stories")
        elif file.filename.endswith(".csv"):
            df = pd.read_csv(io.StringIO(content.decode()))
        else:
            raise HTTPException(
                status_code=400, detail="Unsupported file type")

        column_map = {col.strip().lower(): col for col in df.columns}
        if "user story" not in column_map:
            raise HTTPException(
                status_code=400, detail="Column 'User Story' not found")

        column_name = column_map["user story"]
        stories = df[column_name].dropna().astype(str).tolist()

    elif user_story:
        stories = [user_story]
    else:
        raise HTTPException(
            status_code=400, detail="Provide user_story or file")

    all_chroma_data = collection.get()
    all_chroma_metadatas = all_chroma_data.get("metadatas", [])
    metadata_dir = run_folder / "metadata"
    metadata_dir.mkdir(exist_ok=True)
    with open(metadata_dir / "before_enrichment.json", "w", encoding="utf-8") as f:
        json.dump(all_chroma_metadatas, f, indent=2)

    method_map_full = get_all_page_methods(pages_dir)
    test_functions = []
    for story in stories:
        path_pages = get_inferred_pages(story, method_map_full)
        sub_method_map = {p: method_map_full[p]
                          for p in path_pages if p in method_map_full}
        code = generate_test_code_from_methods(
            story, sub_method_map, path_pages, site_url)
        # 👇 Ensure all async test functions are decorated and import is present
        pattern = r'(?m)^(async def test_)'
        code = re.sub(pattern, '@pytest.mark.asyncio\n\\1', code)
        if 'import pytest' not in code:
            code = 'import pytest\n' + code
        # Remove _enrich_if_needed calls (if present)
        code = re.sub(
            r'await\s+\w+_page\._enrich_if_needed\([^\)]*\)\s*\n', '', code)
        test_functions.append(code)

    idx = next_index(tests_dir, "test_{}.py")
    test_file = tests_dir / f"test_{idx}.py"

    imports = []
    for page in method_map_full:
        class_name = f"{page.capitalize()}Page"
        imports.append(f"from pages.{page}_page import {class_name}")

    full_code = "\n\n".join(imports + test_functions)
    test_file.write_text(full_code, encoding="utf-8")
    create_default_test_data(run_folder)

    return {"results": stories, "test_file": str(test_file)}



# === FILE: apis\generate_page_methods.py ===
from fastapi import APIRouter
from pathlib import Path
from services.test_generation_utils import collection, filter_all_pages
from utils.smart_ai_utils import ensure_smart_ai_module
from orchestrator.orchestrator import send_message

router = APIRouter()

# ✅ Function to dynamically generate BasePage with your DOM enrichment logic


def generate_base_page(base_page_path: Path):
    base_page_content = '''from services.page_enricher import enrich_page

class BasePage:
    enriched_pages = set()

    def __init__(self, page, page_name, url=None):
        self.page = page
        self.page_name = page_name
        self.url = url

    async def goto(self):
        if self.url:
            await self.page.goto(self.url)
        else:
            raise ValueError(f"URL not set for {self.page_name}")

    async def enrich_once(self, force=False):
        if force or self.page_name not in BasePage.enriched_pages:
            await enrich_page(self.page, self.page_name)  # DOM enrichment clearly triggered
            BasePage.enriched_pages.add(self.page_name)
            print(f"🌟 Enriched page: {self.page_name}")
        else:
            print(f"✅ Already enriched: {self.page_name}")
'''
    base_page_path.write_text(base_page_content.strip(), encoding="utf-8")
    print("✅ Generated BasePage class")


@router.post("/rag/generate-page-methods")
def generate_page_methods():
    ensure_smart_ai_module()
    target_pages = filter_all_pages()
    result = {}

    # ✅ Generate conftest.py once
    def create_conftest_file():
        conftest_content = '''import pytest
import json
from pathlib import Path
from lib.smart_ai import patch_page_with_smartai

@pytest.fixture(autouse=True)
def smartai_page(page):    
    metadata_path = (Path(__file__).parent.parent / "metadata" / "after_enrichment.json").resolve()
    with open(metadata_path, "r") as f:
        actual_metadata = json.load(f)
    patch_page_with_smartai(page, actual_metadata)
    return page
'''
        tests_dir = Path(__file__).parent.parent / \
            "generated_runs" / "src" / "tests"
        tests_dir.mkdir(parents=True, exist_ok=True)
        (tests_dir / "conftest.py").write_text(conftest_content.strip(), encoding="utf-8")

    create_conftest_file()

    # ✅ Ensure pages directory exists
    outdir = Path("generated_runs") / "src" / "pages"
    outdir.mkdir(parents=True, exist_ok=True)

    # ✅ Dynamically generate BasePage (if not exists)
    base_page_path = outdir / "base_page.py"
    if not base_page_path.exists():
        generate_base_page(base_page_path)

    for page in target_pages:
        page_data = collection.get(where={"page_name": page})
        entries = page_data.get("metadatas", [])

        page_spec = {
            "page_name": page,
            "entries": entries  # agent handles logic
        }

        response = send_message("python", "generate_page_file", page_spec)
        payload = response.payload

        # ✅ Inject BasePage inheritance clearly and consistently
        page_class_code = payload["code"]

        # Remove existing enrichment methods to avoid duplicates/conflicts
        lines = page_class_code.splitlines()
        new_lines = []
        inserted_import = False
        skip_next = False

        for line in lines:
            if 'def _enrich_if_needed' in line or skip_next:
                skip_next = line.strip() != ''
                continue  # Skip the existing enrichment method entirely
            if not inserted_import and line.strip().startswith("class"):
                new_lines.append("from .base_page import BasePage\n")
                if "(object)" in line:
                    line = line.replace("(object)", "(BasePage)")
                elif ":" in line and "(BasePage)" not in line:
                    line = line.replace(":", "(BasePage):")
                inserted_import = True
            new_lines.append(line)
        page_class_code = "\n".join(new_lines)

        # Write the generated page class
        filepath = outdir / payload["page_file"]
        filepath.write_text(page_class_code, encoding="utf-8")

        result[page] = {
            "filename": str(filepath),
            "code": page_class_code
        }

    return result



# === FILE: apis\generate_testcases_from_methods.py ===
from fastapi import APIRouter
from pathlib import Path
import re

router = APIRouter()

def next_test_index(tests_dir):
    """Returns the next test index for file naming."""
    test_files = list(tests_dir.glob("test_*.py"))
    if not test_files:
        return 1
    indices = [
        int(re.search(r"test_(\d+)\.py", f.name).group(1))
        for f in test_files if re.match(r"test_\d+\.py", f.name)
    ]
    return max(indices, default=0) + 1

def read_page_methods(page_method_path):
    """Reads the contents of a generated page methods file."""
    with open(page_method_path, "r", encoding="utf-8") as f:
        return f.read()

@router.post("/rag/generate-from-method")
def generate_test_from_methods():
    run_folder = Path("generated_runs")
    pages_dir = run_folder / "pages"
    tests_dir = run_folder / "tests"
    metadata_dir = run_folder / "metadata"

    # clean_old_files(tests_dir, age_seconds=3600)
    # clean_old_files(metadata_dir, age_seconds=3600)

    tests_dir.mkdir(parents=True, exist_ok=True)
    pages_dir.mkdir(parents=True, exist_ok=True)

    # Find all *_page_methods.py in pages_dir
    method_files = list(pages_dir.glob("*_page_methods.py"))
    if not method_files:
        return {"error": "No page methods found. Please generate page methods first."}
    
    # Collect all imports and function defs
    all_imports = set()
    all_func_defs = []
    test_invocations = []

    for method_file in method_files:
        methods_code = read_page_methods(method_file)
        # Separate import lines and function defs
        for line in methods_code.splitlines():
            line = line.strip()
            if line.startswith("from ") or line.startswith("import "):
                all_imports.add(line)
            elif line.startswith("def "):
                all_func_defs.append(line)
            elif line:  # collect body as well
                all_func_defs.append(line)

        # Detect and queue function invocation
        func_defs = re.findall(r'def\s+([a-zA-Z_][a-zA-Z0-9_]*)\((.*?)\):', methods_code)
        for fn, params in func_defs:
            if "page, value" in params:
                # Fill/select function; provide sample value
                test_invocations.append(f"        {fn}(page, 'demo_value')")
            elif "page" in params:
                # Click/toggle/verify function
                test_invocations.append(f"        {fn}(page)")

    # Ensure all necessary imports exist
    all_imports.add("from playwright.sync_api import sync_playwright")
    for method_file in method_files:
        module_name = method_file.stem  # like login_page_methods
        all_imports.add(f"from pages.{module_name} import *")


    # Build the full test script content
    script_lines = []
    script_lines += sorted(all_imports)
    script_lines.append("")  # spacer
    # Append all function definitions (no duplicates)
    script_lines += all_func_defs
    script_lines.append("")  # spacer

    # Test runner boilerplate
    script_lines.append("def test_generated():")
    script_lines.append("    with sync_playwright() as p:")
    script_lines.append("        browser = p.chromium.launch(headless=False)")
    script_lines.append("        context = browser.new_context()")
    script_lines.append("        page = context.new_page()")
    script_lines += test_invocations
    script_lines.append("        browser.close()")

    script_content = "\n".join(script_lines)

    # Write to tests folder as test_{N}.py
    idx = next_test_index(tests_dir)
    out_file = tests_dir / f"test_{idx}.py"
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(script_content)

    return {
        "filename": str(out_file),
        "status": "Test generated",
        "test_code": script_content
    }



# === FILE: apis\generate_test_data.py ===
from fastapi import FastAPI
import uvicorn

router=APIRouter()

from fastapi import APIRouter
from pathlib import Path
import json
from services.test_generation_utils import collection  # <-- Your chromadb client

router = APIRouter()

@router.post("/generate-test-data-from-chromadb")
def generate_test_data_from_chromadb():
    # Query all metadata
    all_records = collection.get()
    metadatas = all_records.get("metadatas", [])
    
    # Filter for textbox or select, and build test data dict
    test_data = {}
    for meta in metadatas:
        ocr_type = (meta.get("ocr_type") or "").lower()
        label = meta.get("label_text") or meta.get("intent") or ""
        label = label.strip().replace(" ", "_").lower()
        if ocr_type in {"textbox", "select"} and label:
            test_data[label] = "fakedata"
    
    # Directory and file path
    run_folder = Path("generated_runs")
    data_dir = run_folder / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    test_data_file = data_dir / "test_data.json"
    
    # Write out the JSON
    with open(test_data_file, "w", encoding="utf-8") as f:
        json.dump(test_data, f, indent=2)
    
    return {"status": "success", "file": str(test_data_file), "test_data": test_data}



# === FILE: apis\image_text_api.py ===
# image_text_api.py

import numpy as np
from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from fastapi.responses import JSONResponse
from typing import List
from PIL import Image
import os
import zipfile
import tempfile
import json
import logging
from dotenv import load_dotenv
from logic.image_text_extractor import process_image_gpt
from services.graph_service import build_dependency_graph
from utils.match_utils import normalize_page_name
from config.settings import DATA_PATH
import chromadb
from datetime import datetime
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
import re

load_dotenv()

router = APIRouter()

# Logging
os.makedirs("data", exist_ok=True)
file_handler = logging.FileHandler("upload_image_logs.txt", encoding="utf-8")
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.addHandler(file_handler)

# ChromaDB setup
embedding_function = SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
chroma_client = chromadb.PersistentClient(path="./data/chroma_db")
chroma_collection = chroma_client.get_or_create_collection(name="element_metadata", embedding_function=embedding_function)


@router.post("/upload-image")
async def upload_image(
    images: List[UploadFile] = File(...),
    ordered_images: str = Form(None)
):
    os.makedirs("data/regions", exist_ok=True)
    os.makedirs("data/images", exist_ok=True)
    results = []
    ordered_image_list = []

    # Step 1: Parse frontend ordering
    if ordered_images:
        try:
            parsed_json = json.loads(ordered_images)
            ordered_image_list = parsed_json.get("ordered_images", [])
            ordered_image_list = [os.path.basename(
                f) for f in ordered_image_list]
            logger.info(
                f"🟢 Ordered images from frontend: {ordered_image_list}")
        except Exception as parse_err:
            logger.warning(f"⚠️ Failed to parse ordered_images: {parse_err}")
            ordered_image_list = []

    # Step 2: Extract uploaded files
    temp_dir = tempfile.mkdtemp()
    image_file_map = {}
    actual_received_images = []

    try:
        for file in images:
            filename = file.filename.lower()
            if filename.endswith(".zip"):
                with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp_zip:
                    tmp_zip.write(await file.read())
                    tmp_zip_path = tmp_zip.name
                with zipfile.ZipFile(tmp_zip_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_dir)
            else:
                if filename.endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp')):
                    file_path = os.path.join(temp_dir, filename)
                    with open(file_path, "wb") as out_file:
                        out_file.write(await file.read())

        # Step 3: Final image order
        extracted_images = [f for f in os.listdir(temp_dir) if f.lower().endswith(
            ('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp'))]
        image_names = ordered_image_list if ordered_image_list else sorted(
            extracted_images)

        # Group images by normalized page_name
        page_images = {}
        for image_name in image_names:
            page_name = normalize_page_name(image_name)
            page_images.setdefault(page_name, []).append(image_name)

        # For saving all raw metadata
        # all_raw_metadata = []

        # Step 4: Process images grouped by logical page
        for page_name, image_group in page_images.items():
            # Fetch existing label_texts for this page from chroma
            try:
                existing = chroma_collection.get(
                    where={"page_name": page_name})
                existing_label_texts = set(
                    m["label_text"].strip().lower()
                    for m in (existing["metadatas"] or [])
                    if m and m.get("label_text")
                )
            except Exception as fetch_err:
                logger.warning(
                    f"⚠️ Failed to fetch existing metadatas for {page_name}: {fetch_err}")
                existing_label_texts = set()

            # For each image for this logical page
            for image_name in image_group:
                image_path = os.path.join(temp_dir, image_name)
                if not os.path.exists(image_path):
                    logger.warning(f"⚠️ Skipping missing image: {image_name}")
                    continue

                with Image.open(image_path) as img:
                    logger.debug(f"📷 Processing image: {image_name}")

                    permanent_image_path = os.path.join(
                        DATA_PATH, "images", image_name)
                    img.save(permanent_image_path)

                    # timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    # DEBUG_LOG_PATH = f"./data/metadata_logs_{timestamp}.json"

                    # GPT image extraction
                    metadata_list = await process_image_gpt(
                        img, image_name,
                        image_path=permanent_image_path,
                        # debug_log_path=DEBUG_LOG_PATH
                    )                    

                    # Save per-image metadata to data/stored/timestamp_imageName.json
                    def to_serializable(obj):
                        if isinstance(obj, np.ndarray):
                            return obj.tolist()
                        if isinstance(obj, (set,)):
                            return list(obj)
                        return obj
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    base_image_name = os.path.splitext(os.path.basename(image_name))[0]
                    os.makedirs("data/stored", exist_ok=True)
                    out_file = os.path.join(
                        "data", "stored", f"{timestamp}_{base_image_name}.json")
                    with open(out_file, "w", encoding="utf-8") as f:
                        json.dump(metadata_list, f, indent=4, ensure_ascii=False, default=to_serializable)

                    
                    
                    
                    # all_raw_metadata.append({
                    #     "image_name": image_name,
                    #     "metadata": metadata_list
                    # })

                    # # Only add new label_texts for this logical page
                    # for metadata in metadata_list:
                    #     original_label_text = metadata.get("label_text", "")
                    #     cleaned_label_text = clean_label_text(
                    #         original_label_text)
                    #     # Overwrite with cleaned version
                    #     metadata["label_text"] = cleaned_label_text
                    #     if cleaned_label_text and cleaned_label_text not in existing_label_texts:
                    #         chroma_collection.add(
                    #             ids=[metadata["id"]],
                    #             documents=[metadata["text"]],
                    #             metadatas=[metadata]
                    #         )
                    #         results.append(metadata)
                    #         existing_label_texts.add(cleaned_label_text)

                image_file_map[image_name] = (image_path, page_name)
                actual_received_images.append(image_name)

        # # Save all raw GPT metadata to a single file
        # raw_data_file_path = os.path.join("data", "raw_data_from_gpt.json")
        # with open(raw_data_file_path, "w", encoding="utf-8") as f:
        #     json.dump(all_raw_metadata, f, indent=2, ensure_ascii=False)
        # logger.info(f"📝 Saved all raw GPT metadata to {raw_data_file_path}")

        # Step 5: Store dependency graph
        if ordered_image_list:
            build_dependency_graph(
                ordered_image_list, output_path="data/dependency_graph.json")
            logger.info(
                "📄 Dependency graph stored in data/dependency_graph.json")

        # Step 6: Log order metadata
        order_json_path = os.path.join("data", "image_order.json")
        with open(order_json_path, "w") as f:
            json.dump({
                "ordered_from_frontend": ordered_image_list,
                "processed_order": actual_received_images
            }, f, indent=2)
        logger.info("📄 Ordered images logged to data/image_order.json")

        return JSONResponse(content={"status": "success", "data": results})

    except Exception as e:
        logger.error("❌ Error in upload_image", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))



def clean_label_text(text: str) -> str:
    # Remove leading/trailing numbers, dots, dashes, and spaces
    cleaned = re.sub(r"^[\s\W\d_]+|[\s\W\d_]+$", "", text, flags=re.UNICODE)
    return cleaned



# === FILE: apis\manual_add_metadata.py ===
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from services.test_generation_utils import collection  # Your ChromaDB collection instance

from pydantic import BaseModel, Field
from typing import Optional

import uuid
from datetime import datetime

router = APIRouter()



class ManualMetadataInput(BaseModel):
    page_name: str
    placeholder: Optional[str] = ""
    text: Optional[str] = ""
    label_text: Optional[str] = ""
    value: Optional[str] = ""
    intent: Optional[str] = ""
    ocr_type: Optional[str] = ""  # e.g., "button", "textbox", etc.
    tag_name: Optional[str] = ""
    dom_id: Optional[str] = ""
    dom_class: Optional[str] = ""

@router.post("/manual-add-metadata")
async def manual_add_metadata(input: ManualMetadataInput):
    # 1. Build full metadata from minimal input
    metadata = build_complete_metadata(input)
    # 2. Insert into ChromaDB
    collection.add(
        ids=[metadata["id"]],
        documents=[metadata["label_text"]],
        metadatas=[metadata]
    )
    # 3. Return the metadata for verification
    return JSONResponse(content=metadata)

def build_complete_metadata(manual: ManualMetadataInput):
    # You can add logic to auto-calculate bounding box or set dummy values
    bbox = "0,0,100,40"
    now = datetime.utcnow().isoformat()
    uid = str(uuid.uuid4())
    label_text = manual.label_text or manual.placeholder or manual.text or manual.value or ""
    unique_name = f"{manual.page_name}_{manual.intent}_{label_text}_{manual.ocr_type}".replace(" ", "_").lower()
    return {
        "element_id": uid,
        "ocr_id": uid,
        "page_name": manual.page_name,
        "text": manual.text or "",
        "label_text": label_text,
        "x": 0,
        "y": 0,
        "width": 100,
        "height": 40,
        "confidence_score": 1.0,
        "visibility_score": 1.0,
        "locator_stability_score": 1.0,
        "used_in_tests": "[]",
        "last_tested": "",
        "healing_success_rate": 0.0,
        "snapshot_id": "",
        "match_timestamp": now,
        "region_image_path": "",
        "source_url": "",
        "bbox": bbox,
        "position_relation": "{}",
        "tag_name": manual.tag_name,
        "xpath": "",
        "get_by_text": manual.text or "",
        "get_by_role": "",
        "intent": manual.intent or "",
        "html_snippet": "",
        "dom_matched": False,
        "ocr_type": manual.ocr_type,
        "unique_name": unique_name,
        "placeholder": manual.placeholder or "",
        "external": True,
        "dom_class": manual.dom_class,
        "dom_id": manual.dom_id,
    }


# How to Use
# POST to /manual-add-metadata with body:
    page_name: str
    placeholder: Optional[str] = ""
    text: Optional[str] = ""
    label_text: Optional[str] = ""
    value: Optional[str] = ""
    intent: Optional[str] = ""
    ocr_type: Optional[str] = ""  # e.g., "button", "textbox", etc.
    tag_name: Optional[str] = ""
    dom_id: Optional[str] = ""
    dom_class: Optional[str] = ""

{
  "page_name": "saucedemo_inventory",
  "placeholder": "",
  "text": "",
  "label_text": "shopping_cart",
  "value": "",
  "intent": "go_to_cart",
  "ocr_type": "button",
  "dom_id": "",
  "dom_class": "shopping_cart"
}

{
  "page_name": "dashboard",
  "placeholder": "",
  "text": "customers",
  "label_text": "customers",
  "value": "",
  "intent": "",
  "ocr_type": "button",
  "tag_name": "a",
  "dom_id": "",
  "dom_class": ""
}



# === FILE: apis\rag_testcase_runner.py ===
from fastapi import APIRouter, HTTPException
import os, sys, subprocess, json
from datetime import datetime
from pathlib import Path

router = APIRouter()

project_root = Path(__file__).resolve().parents[1]
generated_runs_dir = project_root / "generated_runs" / "src"
tests_dir = generated_runs_dir / "tests"
logs_dir = generated_runs_dir / "logs"
meta_dir = generated_runs_dir / "metadata"

@router.post("/rag/run-generated-story-test")
def run_latest_generated_story_test():
    try:
        # 1. Find the latest ui_script_*.py in generated_runs/src/tests/
        ui_script_files = sorted(
            [f for f in tests_dir.glob("ui_script_*.py") if f.is_file()],
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )
        if not ui_script_files:
            raise HTTPException(
                status_code=404,
                detail=f"No generated ui_script_*.py files found in {tests_dir.resolve()}"
            )
        latest_ui_script = ui_script_files[0]

        # 2. Prepare logs and meta output
        logs_dir.mkdir(parents=True, exist_ok=True)
        meta_dir.mkdir(parents=True, exist_ok=True)
        log_file = logs_dir / f"test_output_{latest_ui_script.stem}.log"
        meta_file = meta_dir / f"execution_metadata_{latest_ui_script.stem}.json"

        # 3. Run the script like: PYTHONPATH=. python tests/ui_script_N.py
        env = os.environ.copy()
        env["PYTHONPATH"] = str(generated_runs_dir)  # Set to "generated_runs/src"

        # Note: Run from generated_runs/src, so `tests/ui_script_N.py` exists relative to cwd
        result = subprocess.run(
            [sys.executable, f"tests/{latest_ui_script.name}"],
            cwd=generated_runs_dir,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        output = result.stdout + "\n" + result.stderr
        log_file.write_text(output, encoding="utf-8")
        status = "PASS" if result.returncode == 0 else "FAIL"

        # --- Parse error summary from output ---
        error_lines = []
        in_summary = False
        for line in output.splitlines():
            if "Summary of failures:" in line:
                in_summary = True
                continue
            if in_summary:
                if line.strip().startswith("- "):
                    error_lines.append(line.strip())
                # Optionally: stop at blank line or next heading
                if not line.strip():
                    break

        json.dump(
            {"status": status, "timestamp": datetime.now().isoformat()},
            open(meta_file, "w"),
            indent=2
        )

        return {
            "status": status,
            "log": output,
            "errors": error_lines,  # <-- errors summary lines!
            "executed_from": str(latest_ui_script),
            "log_file": str(log_file),
            "meta_file": str(meta_file),
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))



# === FILE: apis\test.py ===

import numpy as np
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))
import json
import orjson
from utils.match_utils import normalize_page_name
from chromadb import PersistentClient

chroma_client = PersistentClient(path="data/chroma_db")
collection = chroma_client.get_or_create_collection("element_metadata")

# Helper function
def convert_np(obj):
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, (np.float32, np.float64)):
        return float(obj)
    if isinstance(obj, (np.int32, np.int64)):
        return int(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


dashboard_page_data = collection.get(where={"page_name": 'dashboard'})
customers_page_data = collection.get(where={"page_name": 'customers'})


# Save to 'dashboard_page_data.json' in the current folder
with open("apis/dashboard_page_data.json", "w", encoding="utf-8") as f:
    json.dump(dashboard_page_data, f, indent=4, ensure_ascii=False, default=convert_np)

# Save to 'customers_page_data.json' in the current folder
with open("apis/customers_page_data.json", "w", encoding="utf-8") as f:
    json.dump(customers_page_data, f, indent=4,
              ensure_ascii=False, default=convert_np)

# # Save to 'data.json' in the current folder
# with open("apis/data.json", "wb") as f:
#     f.write(orjson.dumps(page_data, option=orjson.OPT_INDENT_2))

# print(page_data)


# === FILE: app\api.py ===
# app/api.py

from fastapi import FastAPI, Body
from orchestrator.orchestrator import send_message

app = FastAPI()

@app.post("/mcp/")
def mcp_endpoint(language: str = Body(...), action: str = Body(...), payload: dict = Body(...)):
    resp = send_message(language, action, payload)
    return resp.__dict__



# === FILE: config\settings.py ===
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_PATH = os.path.abspath(os.path.join(BASE_DIR, ".."))
DATA_PATH = os.path.join(ROOT_PATH, "data")
REGION_PATH = os.path.join(DATA_PATH, "regions")
CHROMA_PATH = os.path.join(DATA_PATH, "chroma_db")

os.makedirs(DATA_PATH + "/images", exist_ok=True)
os.makedirs(REGION_PATH, exist_ok=True)
os.makedirs(CHROMA_PATH, exist_ok=True)


# === FILE: data\dependency_graph.json ===
[
  {
    "from": "dashboard.png",
    "to": "customers.png"
  },
  {
    "from": "customers.png",
    "to": "customers_2.png"
  }
]


# === FILE: data\image_order.json ===
{
  "ordered_from_frontend": [
    "dashboard.png",
    "customers.png",
    "customers_2.png"
  ],
  "processed_order": [
    "dashboard.png",
    "customers.png",
    "customers_2.png"
  ]
}


# === FILE: data\openai_response\20250726_151305_dashboard.txt ===
- button - navigation
Search customers, loans, transactions... - textbox - search
Dashboard - button - navigation
Customers - button - navigation
Loans - button - navigation
Transactions - button - navigation
Tasks - button - navigation
Reports - button - navigation
Analytics - button - navigation
Settings - button - navigation
Dashboard - label - page_title
Welcome back! Here's your banking overview. - label - welcome_message
Total Customers - label - total_customers
2,847 - label - total_customers_value
Active Loans - label - active_loans
$45.2M - label - active_loans_value
Monthly Transactions - label - monthly_transactions
18,394 - label - monthly_transactions_value
Revenue Growth - label - revenue_growth
23.4% - label - revenue_growth_value
Export Report - button - export
Loan Portfolio Trend - label - loan_portfolio_trend
Monthly loan disbursements over the last 6 months - label - loan_portfolio_description
Customer Distribution - label - customer_distribution
Customer segments by account type - label - customer_distribution_description
Recent Activities - label - recent_activities
Latest customer interactions and transactions - label - recent_activities_description
Sarah Johnson - label - recent_activity_user
Loan Application Approved - label - recent_activity_description
Michael Chen - label - recent_activity_user
- label - recent_activity_description
$250,000 - label - recent_activity_value
Edit with - label - edit_tool
Lovable - button - edit_tool
---------------------------------------- After Cleaning ----------------------------------------
- button - navigation
Search customers, loans, transactions... - textbox - search
Dashboard - button - navigation
Customers - button - navigation
Loans - button - navigation
Transactions - button - navigation
Tasks - button - navigation
Reports - button - navigation
Analytics - button - navigation
Settings - button - navigation
Dashboard - label - page_title
Welcome back! Here's your banking overview. - label - welcome_message
Total Customers - label - total_customers
2,847 - label - total_customers_value
Active Loans - label - active_loans
$45.2M - label - active_loans_value
Monthly Transactions - label - monthly_transactions
18,394 - label - monthly_transactions_value
Revenue Growth - label - revenue_growth
4% - label - revenue_growth_value
Export Report - button - export
Loan Portfolio Trend - label - loan_portfolio_trend
Monthly loan disbursements over the last 6 months - label - loan_portfolio_description
Customer Distribution - label - customer_distribution
Customer segments by account type - label - customer_distribution_description
Recent Activities - label - recent_activities
Latest customer interactions and transactions - label - recent_activities_description
Sarah Johnson - label - recent_activity_user
Loan Application Approved - label - recent_activity_description
Michael Chen - label - recent_activity_user
- label - recent_activity_description
$250,000 - label - recent_activity_value
Edit with - label - edit_tool
Lovable - button - edit_tool



# === FILE: data\openai_response\20250726_151326_customers.txt ===
- button - navigation
Dashboard - button - navigation
Customers - button - navigation
Loans - button - navigation
Transactions - button - navigation
Tasks - button - navigation
Reports - button - navigation
Analytics - button - navigation
Settings - button - navigation
Search customers, loans, transactions... - textbox - search
Customers - label - header
Manage your customer relationships and accounts - label - subheader
Search customers... - textbox - search
Filters - button - filter
Customer List - label - section_header
3 customers found - label - info
Customer - label - column_header
Account Type - label - column_header
Balance - label - column_header
Status - label - column_header
Join Date - label - column_header
Actions - label - column_header
Sarah Johnson - label - customer_name
sarah.johnson@email.com - label - customer_email
Premium - label - account_type
$1,45,000 - label - balance
Active - label - status
2023-01-15 - label - join_date
- button - view_action
- button - edit_action
Michael Chen - label - customer_name
michael.chen@email.com - label - customer_email
Standard - label - account_type
$52,000 - label - balance
Active - label - status
2023-03-22 - label - join_date
- button - view_action
- button - edit_action
Emma Davis - label - customer_name
emma.davis@email.com - label - customer_email
Premium - label - account_type
$89,000 - label - balance
Active - label - status
2022-11-08 - label - join_date
- button - view_action
- button - edit_action
Export - button - export
New Customer - button - add_customer
Edit with - label - footer
Lovable - label - footer_brand
---------------------------------------- After Cleaning ----------------------------------------
- button - navigation
Dashboard - button - navigation
Customers - button - navigation
Loans - button - navigation
Transactions - button - navigation
Tasks - button - navigation
Reports - button - navigation
Analytics - button - navigation
Settings - button - navigation
Search customers, loans, transactions... - textbox - search
Customers - label - header
Manage your customer relationships and accounts - label - subheader
Search customers... - textbox - search
Filters - button - filter
Customer List - label - section_header
3 customers found - label - info
Customer - label - column_header
Account Type - label - column_header
Balance - label - column_header
Status - label - column_header
Join Date - label - column_header
Actions - label - column_header
Sarah Johnson - label - customer_name
sarah.johnson@email.com - label - customer_email
Premium - label - account_type
$1,45,000 - label - balance
Active - label - status
2023-01-15 - label - join_date
- button - view_action
- button - edit_action
Michael Chen - label - customer_name
michael.chen@email.com - label - customer_email
Standard - label - account_type
$52,000 - label - balance
Active - label - status
2023-03-22 - label - join_date
- button - view_action
- button - edit_action
Emma Davis - label - customer_name
emma.davis@email.com - label - customer_email
Premium - label - account_type
$89,000 - label - balance
Active - label - status
2022-11-08 - label - join_date
- button - view_action
- button - edit_action
Export - button - export
New Customer - button - add_customer
Edit with - label - footer
Lovable - label - footer_brand



# === FILE: data\openai_response\20250726_151342_customers_2.txt ===
Add New Customer - label - form_title  
Enter the customer details to create a new account. - label - form_instruction  
Full Name * - label - full_name_label  
- textbox - full_name_input  
Email * - label - email_label  
- textbox - email_input  
Phone Number * - label - phone_number_label  
- textbox - phone_number_input  
Account Type * - label - account_type_label  
Select account type - select - account_type_select  
Address - label - address_label  
- textbox - address_input  
Occupation - label - occupation_label  
- textbox - occupation_input  
Annual Income - label - annual_income_label  
- textbox - annual_income_input  
Initial Deposit - label - initial_deposit_label  
- textbox - initial_deposit_input  
Cancel - button - cancel  
Add Customer - button - submit
---------------------------------------- After Cleaning ----------------------------------------
Add New Customer - label - form_title  
Enter the customer details to create a new account. - label - form_instruction  
Full Name  - label - full_name_label  
- textbox - full_name_input  
Email  - label - email_label  
- textbox - email_input  
Phone Number  - label - phone_number_label  
- textbox - phone_number_input  
Account Type  - label - account_type_label  
Select account type - select - account_type_select  
Address - label - address_label  
- textbox - address_input  
Occupation - label - occupation_label  
- textbox - occupation_input  
Annual Income - label - annual_income_label  
- textbox - annual_income_input  
Initial Deposit - label - initial_deposit_label  
- textbox - initial_deposit_input  
Cancel - button - cancel  
Add Customer - button - submit



# === FILE: data\stored\20250726_151315_dashboard.json ===
[
    {
        "id": "1233c562-20f0-4202-90fd-663914b09c9d",
        "document": "",
        "metadata": {
            "dom_matched": false,
            "unique_name": "dashboard_button_navigation_34c032c8",
            "placeholder": "",
            "page_name": "dashboard",
            "ocr_type": "button",
            "type": "ocr",
            "element_id": "1233c562-20f0-4202-90fd-663914b09c9d",
            "label_text": "",
            "get_by_text": "",
            "intent": "navigation",
            "external": false
        }
    },
    {
        "id": "0da341dd-0730-4547-b6b2-b2d3f0cc8a1a",
        "document": "Search customers, loans, transactions...",
        "metadata": {
            "type": "ocr",
            "element_id": "0da341dd-0730-4547-b6b2-b2d3f0cc8a1a",
            "ocr_type": "textbox",
            "dom_matched": false,
            "external": false,
            "placeholder": "Search customers, loans, transactions...",
            "get_by_text": "Search customers, loans, transactions...",
            "page_name": "dashboard",
            "label_text": "Search customers, loans, transactions...",
            "intent": "search",
            "unique_name": "dashboard_search_customers,_loans,_transactions..._textbox_search_3310a968"
        }
    },
    {
        "id": "fcab9ebe-5767-462d-8cfb-82bd3348f3f9",
        "document": "Dashboard",
        "metadata": {
            "type": "ocr",
            "element_id": "fcab9ebe-5767-462d-8cfb-82bd3348f3f9",
            "dom_matched": false,
            "intent": "navigation",
            "get_by_text": "Dashboard",
            "placeholder": "Dashboard",
            "external": false,
            "label_text": "Dashboard",
            "page_name": "dashboard",
            "ocr_type": "button",
            "unique_name": "dashboard_dashboard_button_navigation_83914516"
        }
    },
    {
        "id": "45394f62-91b9-4529-adae-5627e4313b4c",
        "document": "Customers",
        "metadata": {
            "get_by_text": "Customers",
            "dom_matched": false,
            "unique_name": "dashboard_customers_button_navigation_bb4303b6",
            "type": "ocr",
            "element_id": "45394f62-91b9-4529-adae-5627e4313b4c",
            "placeholder": "Customers",
            "page_name": "dashboard",
            "intent": "navigation",
            "ocr_type": "button",
            "external": false,
            "label_text": "Customers"
        }
    },
    {
        "id": "24e6ff1a-d33a-4ba8-a5a6-be626370a5dd",
        "document": "Loans",
        "metadata": {
            "dom_matched": false,
            "external": false,
            "get_by_text": "Loans",
            "placeholder": "Loans",
            "type": "ocr",
            "label_text": "Loans",
            "unique_name": "dashboard_loans_button_navigation_42436e2a",
            "element_id": "24e6ff1a-d33a-4ba8-a5a6-be626370a5dd",
            "ocr_type": "button",
            "page_name": "dashboard",
            "intent": "navigation"
        }
    },
    {
        "id": "c8b402b6-f1f8-4c0e-ae27-ccab631cd424",
        "document": "Transactions",
        "metadata": {
            "placeholder": "Transactions",
            "ocr_type": "button",
            "page_name": "dashboard",
            "type": "ocr",
            "unique_name": "dashboard_transactions_button_navigation_f0479a72",
            "label_text": "Transactions",
            "element_id": "c8b402b6-f1f8-4c0e-ae27-ccab631cd424",
            "get_by_text": "Transactions",
            "intent": "navigation",
            "dom_matched": false,
            "external": false
        }
    },
    {
        "id": "560d2d8f-c76a-4d45-9a08-a11877b31d9e",
        "document": "Tasks",
        "metadata": {
            "get_by_text": "Tasks",
            "type": "ocr",
            "page_name": "dashboard",
            "label_text": "Tasks",
            "ocr_type": "button",
            "placeholder": "Tasks",
            "unique_name": "dashboard_tasks_button_navigation_cde2a4d6",
            "external": false,
            "intent": "navigation",
            "element_id": "560d2d8f-c76a-4d45-9a08-a11877b31d9e",
            "dom_matched": false
        }
    },
    {
        "id": "b95730ff-2fe4-44c4-baf5-ad976c203079",
        "document": "Reports",
        "metadata": {
            "unique_name": "dashboard_reports_button_navigation_578fb659",
            "page_name": "dashboard",
            "dom_matched": false,
            "placeholder": "Reports",
            "element_id": "b95730ff-2fe4-44c4-baf5-ad976c203079",
            "intent": "navigation",
            "ocr_type": "button",
            "label_text": "Reports",
            "type": "ocr",
            "get_by_text": "Reports",
            "external": false
        }
    },
    {
        "id": "16d843ef-d207-41e4-884a-80192b4cd287",
        "document": "Analytics",
        "metadata": {
            "page_name": "dashboard",
            "placeholder": "Analytics",
            "intent": "navigation",
            "dom_matched": false,
            "external": false,
            "element_id": "16d843ef-d207-41e4-884a-80192b4cd287",
            "label_text": "Analytics",
            "ocr_type": "button",
            "unique_name": "dashboard_analytics_button_navigation_49884ab5",
            "type": "ocr",
            "get_by_text": "Analytics"
        }
    },
    {
        "id": "fd2f64e0-9d2a-4bb1-9af2-7c439720110f",
        "document": "Settings",
        "metadata": {
            "type": "ocr",
            "ocr_type": "button",
            "get_by_text": "Settings",
            "element_id": "fd2f64e0-9d2a-4bb1-9af2-7c439720110f",
            "page_name": "dashboard",
            "unique_name": "dashboard_settings_button_navigation_7a36fd5d",
            "intent": "navigation",
            "dom_matched": false,
            "placeholder": "Settings",
            "label_text": "Settings",
            "external": false
        }
    },
    {
        "id": "fe6111b7-5b58-44b0-be3a-0e52f5d35069",
        "document": "Dashboard",
        "metadata": {
            "external": false,
            "intent": "page_title",
            "unique_name": "dashboard_dashboard_label_page_title_a353b4f0",
            "ocr_type": "label",
            "dom_matched": false,
            "get_by_text": "Dashboard",
            "placeholder": "Dashboard",
            "type": "ocr",
            "page_name": "dashboard",
            "element_id": "fe6111b7-5b58-44b0-be3a-0e52f5d35069",
            "label_text": "Dashboard"
        }
    },
    {
        "id": "e2660127-d787-4393-a482-66947dcfdf81",
        "document": "Welcome back! Here's your banking overview.",
        "metadata": {
            "unique_name": "dashboard_welcome_back!_heres_your_banking_overview._label_welcome_message_479a4097",
            "type": "ocr",
            "external": false,
            "intent": "welcome_message",
            "placeholder": "Welcome back! Here's your banking overview.",
            "page_name": "dashboard",
            "element_id": "e2660127-d787-4393-a482-66947dcfdf81",
            "ocr_type": "label",
            "get_by_text": "Welcome back! Here's your banking overview.",
            "dom_matched": false,
            "label_text": "Welcome back! Here's your banking overview."
        }
    },
    {
        "id": "51501189-4e74-41b9-b6da-987a9a839f87",
        "document": "Total Customers",
        "metadata": {
            "ocr_type": "label",
            "get_by_text": "Total Customers",
            "external": false,
            "label_text": "Total Customers",
            "intent": "total_customers",
            "dom_matched": false,
            "page_name": "dashboard",
            "placeholder": "Total Customers",
            "element_id": "51501189-4e74-41b9-b6da-987a9a839f87",
            "type": "ocr",
            "unique_name": "dashboard_total_customers_label_total_customers_228048fb"
        }
    },
    {
        "id": "e46b7f1c-c443-45db-912e-43c546fe068d",
        "document": "2,847",
        "metadata": {
            "get_by_text": "2,847",
            "placeholder": "2,847",
            "unique_name": "dashboard_2,847_label_total_customers_value_6d9c1e09",
            "element_id": "e46b7f1c-c443-45db-912e-43c546fe068d",
            "label_text": "2,847",
            "intent": "total_customers_value",
            "external": false,
            "ocr_type": "label",
            "page_name": "dashboard",
            "type": "ocr",
            "dom_matched": false
        }
    },
    {
        "id": "754d67d0-6559-4e6a-8f28-a97134bbc10f",
        "document": "Active Loans",
        "metadata": {
            "unique_name": "dashboard_active_loans_label_active_loans_3dfc1d95",
            "type": "ocr",
            "placeholder": "Active Loans",
            "external": false,
            "label_text": "Active Loans",
            "ocr_type": "label",
            "get_by_text": "Active Loans",
            "page_name": "dashboard",
            "dom_matched": false,
            "element_id": "754d67d0-6559-4e6a-8f28-a97134bbc10f",
            "intent": "active_loans"
        }
    },
    {
        "id": "b449e2aa-16c0-442c-bc74-179c54c09378",
        "document": "$45.2M",
        "metadata": {
            "type": "ocr",
            "dom_matched": false,
            "label_text": "$45.2M",
            "get_by_text": "$45.2M",
            "ocr_type": "label",
            "placeholder": "$45.2M",
            "intent": "active_loans_value",
            "unique_name": "dashboard_$45.2m_label_active_loans_value_e93e7652",
            "external": false,
            "element_id": "b449e2aa-16c0-442c-bc74-179c54c09378",
            "page_name": "dashboard"
        }
    },
    {
        "id": "74c7e9d8-4ec9-4da5-a7b6-7d178729f85d",
        "document": "Monthly Transactions",
        "metadata": {
            "intent": "monthly_transactions",
            "label_text": "Monthly Transactions",
            "get_by_text": "Monthly Transactions",
            "dom_matched": false,
            "unique_name": "dashboard_monthly_transactions_label_monthly_transactions_914c549d",
            "page_name": "dashboard",
            "type": "ocr",
            "element_id": "74c7e9d8-4ec9-4da5-a7b6-7d178729f85d",
            "external": false,
            "ocr_type": "label",
            "placeholder": "Monthly Transactions"
        }
    },
    {
        "id": "b7db7fa6-1bb0-49bc-84bd-6a392ecff739",
        "document": "18,394",
        "metadata": {
            "element_id": "b7db7fa6-1bb0-49bc-84bd-6a392ecff739",
            "unique_name": "dashboard_18,394_label_monthly_transactions_value_fc666ffb",
            "get_by_text": "18,394",
            "label_text": "18,394",
            "placeholder": "18,394",
            "external": false,
            "ocr_type": "label",
            "intent": "monthly_transactions_value",
            "type": "ocr",
            "dom_matched": false,
            "page_name": "dashboard"
        }
    },
    {
        "id": "9d226a1f-3b4f-4a1c-8b4a-7a2fd9cf79c9",
        "document": "Revenue Growth",
        "metadata": {
            "external": false,
            "type": "ocr",
            "get_by_text": "Revenue Growth",
            "ocr_type": "label",
            "dom_matched": false,
            "page_name": "dashboard",
            "unique_name": "dashboard_revenue_growth_label_revenue_growth_bfb3b4b4",
            "intent": "revenue_growth",
            "placeholder": "Revenue Growth",
            "element_id": "9d226a1f-3b4f-4a1c-8b4a-7a2fd9cf79c9",
            "label_text": "Revenue Growth"
        }
    },
    {
        "id": "9b39d3eb-ace4-4812-88b7-7105876d6531",
        "document": "4%",
        "metadata": {
            "type": "ocr",
            "label_text": "4%",
            "page_name": "dashboard",
            "unique_name": "dashboard_4%_label_revenue_growth_value_de36ce03",
            "intent": "revenue_growth_value",
            "element_id": "9b39d3eb-ace4-4812-88b7-7105876d6531",
            "ocr_type": "label",
            "get_by_text": "4%",
            "dom_matched": false,
            "external": false,
            "placeholder": "4%"
        }
    },
    {
        "id": "2719b853-b04e-43ab-b4e5-9880b4baf57a",
        "document": "Export Report",
        "metadata": {
            "placeholder": "Export Report",
            "ocr_type": "button",
            "intent": "export",
            "page_name": "dashboard",
            "element_id": "2719b853-b04e-43ab-b4e5-9880b4baf57a",
            "type": "ocr",
            "get_by_text": "Export Report",
            "unique_name": "dashboard_export_report_button_export_ed26f6d4",
            "dom_matched": false,
            "external": false,
            "label_text": "Export Report"
        }
    },
    {
        "id": "ec19b4f9-6cd7-432b-a516-b6b6a804b28a",
        "document": "Loan Portfolio Trend",
        "metadata": {
            "get_by_text": "Loan Portfolio Trend",
            "dom_matched": false,
            "type": "ocr",
            "placeholder": "Loan Portfolio Trend",
            "element_id": "ec19b4f9-6cd7-432b-a516-b6b6a804b28a",
            "ocr_type": "label",
            "page_name": "dashboard",
            "external": false,
            "label_text": "Loan Portfolio Trend",
            "intent": "loan_portfolio_trend",
            "unique_name": "dashboard_loan_portfolio_trend_label_loan_portfolio_trend_16637d4f"
        }
    },
    {
        "id": "eefdc81a-f3bb-4988-a13b-c59f1516172e",
        "document": "Monthly loan disbursements over the last 6 months",
        "metadata": {
            "label_text": "Monthly loan disbursements over the last 6 months",
            "type": "ocr",
            "intent": "loan_portfolio_description",
            "placeholder": "Monthly loan disbursements over the last 6 months",
            "unique_name": "dashboard_monthly_loan_disbursements_over_the_last_6_months_label_loan_portfolio_description_179404d2",
            "dom_matched": false,
            "get_by_text": "Monthly loan disbursements over the last 6 months",
            "ocr_type": "label",
            "element_id": "eefdc81a-f3bb-4988-a13b-c59f1516172e",
            "page_name": "dashboard",
            "external": false
        }
    },
    {
        "id": "566f2f07-8d6c-4eb4-814d-fe9ff1ef96b5",
        "document": "Customer Distribution",
        "metadata": {
            "page_name": "dashboard",
            "get_by_text": "Customer Distribution",
            "unique_name": "dashboard_customer_distribution_label_customer_distribution_28babd8d",
            "placeholder": "Customer Distribution",
            "external": false,
            "label_text": "Customer Distribution",
            "dom_matched": false,
            "type": "ocr",
            "ocr_type": "label",
            "intent": "customer_distribution",
            "element_id": "566f2f07-8d6c-4eb4-814d-fe9ff1ef96b5"
        }
    },
    {
        "id": "94543a4a-3be0-4ac3-a63a-ee736da203fc",
        "document": "Customer segments by account type",
        "metadata": {
            "dom_matched": false,
            "placeholder": "Customer segments by account type",
            "element_id": "94543a4a-3be0-4ac3-a63a-ee736da203fc",
            "unique_name": "dashboard_customer_segments_by_account_type_label_customer_distribution_description_6bb14ee4",
            "type": "ocr",
            "get_by_text": "Customer segments by account type",
            "page_name": "dashboard",
            "external": false,
            "ocr_type": "label",
            "label_text": "Customer segments by account type",
            "intent": "customer_distribution_description"
        }
    },
    {
        "id": "26e6f30a-7516-47d0-a717-53551fee8afa",
        "document": "Recent Activities",
        "metadata": {
            "unique_name": "dashboard_recent_activities_label_recent_activities_cdc77597",
            "intent": "recent_activities",
            "dom_matched": false,
            "label_text": "Recent Activities",
            "page_name": "dashboard",
            "external": false,
            "placeholder": "Recent Activities",
            "get_by_text": "Recent Activities",
            "ocr_type": "label",
            "type": "ocr",
            "element_id": "26e6f30a-7516-47d0-a717-53551fee8afa"
        }
    },
    {
        "id": "29b524a5-ef27-424d-96a0-3eb05eca8822",
        "document": "Latest customer interactions and transactions",
        "metadata": {
            "label_text": "Latest customer interactions and transactions",
            "get_by_text": "Latest customer interactions and transactions",
            "intent": "recent_activities_description",
            "page_name": "dashboard",
            "element_id": "29b524a5-ef27-424d-96a0-3eb05eca8822",
            "placeholder": "Latest customer interactions and transactions",
            "external": false,
            "type": "ocr",
            "dom_matched": false,
            "ocr_type": "label",
            "unique_name": "dashboard_latest_customer_interactions_and_transactions_label_recent_activities_description_425a612e"
        }
    },
    {
        "id": "bddd6c63-04b8-4717-8491-dbabe64e25f8",
        "document": "Sarah Johnson",
        "metadata": {
            "external": false,
            "type": "ocr",
            "ocr_type": "label",
            "dom_matched": false,
            "element_id": "bddd6c63-04b8-4717-8491-dbabe64e25f8",
            "label_text": "Sarah Johnson",
            "placeholder": "Sarah Johnson",
            "get_by_text": "Sarah Johnson",
            "intent": "recent_activity_user",
            "unique_name": "dashboard_sarah_johnson_label_recent_activity_user_83be4551",
            "page_name": "dashboard"
        }
    },
    {
        "id": "35266659-f7d9-4615-9809-27e668a40a11",
        "document": "Loan Application Approved",
        "metadata": {
            "label_text": "Loan Application Approved",
            "ocr_type": "label",
            "get_by_text": "Loan Application Approved",
            "intent": "recent_activity_description",
            "placeholder": "Loan Application Approved",
            "type": "ocr",
            "dom_matched": false,
            "page_name": "dashboard",
            "external": false,
            "element_id": "35266659-f7d9-4615-9809-27e668a40a11",
            "unique_name": "dashboard_loan_application_approved_label_recent_activity_description_9696f002"
        }
    },
    {
        "id": "df350293-b561-48df-9bc0-eda7b8524834",
        "document": "Michael Chen",
        "metadata": {
            "external": false,
            "type": "ocr",
            "label_text": "Michael Chen",
            "dom_matched": false,
            "intent": "recent_activity_user",
            "unique_name": "dashboard_michael_chen_label_recent_activity_user_70395558",
            "ocr_type": "label",
            "page_name": "dashboard",
            "element_id": "df350293-b561-48df-9bc0-eda7b8524834",
            "placeholder": "Michael Chen",
            "get_by_text": "Michael Chen"
        }
    },
    {
        "id": "261701b8-bd45-41e6-be98-7a5ee237c90e",
        "document": "",
        "metadata": {
            "get_by_text": "",
            "dom_matched": false,
            "intent": "recent_activity_description",
            "external": false,
            "unique_name": "dashboard_label_recent_activity_description_e2ee0ccc",
            "label_text": "",
            "ocr_type": "label",
            "element_id": "261701b8-bd45-41e6-be98-7a5ee237c90e",
            "page_name": "dashboard",
            "placeholder": "",
            "type": "ocr"
        }
    },
    {
        "id": "995a1d10-05d2-4914-92f9-b5a6ca372ed6",
        "document": "$250,000",
        "metadata": {
            "ocr_type": "label",
            "unique_name": "dashboard_$250,000_label_recent_activity_value_91add15c",
            "element_id": "995a1d10-05d2-4914-92f9-b5a6ca372ed6",
            "type": "ocr",
            "external": false,
            "get_by_text": "$250,000",
            "label_text": "$250,000",
            "placeholder": "$250,000",
            "intent": "recent_activity_value",
            "page_name": "dashboard",
            "dom_matched": false
        }
    },
    {
        "id": "01a5cc09-ce60-4f55-9e92-e4c4494bc834",
        "document": "Edit with",
        "metadata": {
            "intent": "edit_tool",
            "placeholder": "Edit with",
            "type": "ocr",
            "dom_matched": false,
            "page_name": "dashboard",
            "element_id": "01a5cc09-ce60-4f55-9e92-e4c4494bc834",
            "label_text": "Edit with",
            "external": false,
            "unique_name": "dashboard_edit_with_label_edit_tool_e1025d09",
            "ocr_type": "label",
            "get_by_text": "Edit with"
        }
    },
    {
        "id": "50a898e4-51bc-42c4-82d9-7b038a0bf40e",
        "document": "Lovable",
        "metadata": {
            "intent": "edit_tool",
            "placeholder": "Lovable",
            "page_name": "dashboard",
            "type": "ocr",
            "dom_matched": false,
            "label_text": "Lovable",
            "unique_name": "dashboard_lovable_button_edit_tool_2de51406",
            "external": false,
            "get_by_text": "Lovable",
            "element_id": "50a898e4-51bc-42c4-82d9-7b038a0bf40e",
            "ocr_type": "button"
        }
    }
]


# === FILE: data\stored\20250726_151339_customers.json ===
[
    {
        "id": "38657081-c699-44a6-ab88-0f10f54c0593",
        "document": "",
        "metadata": {
            "ocr_type": "button",
            "label_text": "",
            "element_id": "38657081-c699-44a6-ab88-0f10f54c0593",
            "unique_name": "customers_button_navigation_6ab61bef",
            "external": false,
            "type": "ocr",
            "dom_matched": false,
            "get_by_text": "",
            "intent": "navigation",
            "placeholder": "",
            "page_name": "customers"
        }
    },
    {
        "id": "7c70ce16-c61f-4d53-b57c-72849ffb0c78",
        "document": "Dashboard",
        "metadata": {
            "placeholder": "Dashboard",
            "ocr_type": "button",
            "external": false,
            "label_text": "Dashboard",
            "dom_matched": false,
            "unique_name": "customers_dashboard_button_navigation_fb22376c",
            "get_by_text": "Dashboard",
            "page_name": "customers",
            "element_id": "7c70ce16-c61f-4d53-b57c-72849ffb0c78",
            "type": "ocr",
            "intent": "navigation"
        }
    },
    {
        "id": "7695cca0-6637-4653-8803-35dac62b7e05",
        "document": "Customers",
        "metadata": {
            "page_name": "customers",
            "get_by_text": "Customers",
            "intent": "navigation",
            "dom_matched": false,
            "unique_name": "customers_customers_button_navigation_62cd2bf8",
            "label_text": "Customers",
            "type": "ocr",
            "placeholder": "Customers",
            "element_id": "7695cca0-6637-4653-8803-35dac62b7e05",
            "external": false,
            "ocr_type": "button"
        }
    },
    {
        "id": "257efc0d-1658-41d9-9616-cdb735df4d96",
        "document": "Loans",
        "metadata": {
            "external": false,
            "get_by_text": "Loans",
            "dom_matched": false,
            "element_id": "257efc0d-1658-41d9-9616-cdb735df4d96",
            "placeholder": "Loans",
            "intent": "navigation",
            "unique_name": "customers_loans_button_navigation_f083cd47",
            "label_text": "Loans",
            "page_name": "customers",
            "ocr_type": "button",
            "type": "ocr"
        }
    },
    {
        "id": "387617de-1fb7-4fcc-b5b0-6a2c7c75af8f",
        "document": "Transactions",
        "metadata": {
            "page_name": "customers",
            "unique_name": "customers_transactions_button_navigation_bb833203",
            "get_by_text": "Transactions",
            "label_text": "Transactions",
            "ocr_type": "button",
            "intent": "navigation",
            "element_id": "387617de-1fb7-4fcc-b5b0-6a2c7c75af8f",
            "external": false,
            "dom_matched": false,
            "type": "ocr",
            "placeholder": "Transactions"
        }
    },
    {
        "id": "0c1b8c7b-c218-44e9-929a-659bf6d860bf",
        "document": "Tasks",
        "metadata": {
            "get_by_text": "Tasks",
            "page_name": "customers",
            "dom_matched": false,
            "intent": "navigation",
            "placeholder": "Tasks",
            "ocr_type": "button",
            "element_id": "0c1b8c7b-c218-44e9-929a-659bf6d860bf",
            "label_text": "Tasks",
            "type": "ocr",
            "unique_name": "customers_tasks_button_navigation_63e52ff9",
            "external": false
        }
    },
    {
        "id": "5d451e44-64af-4b69-afa5-1c33eb979bb7",
        "document": "Reports",
        "metadata": {
            "label_text": "Reports",
            "dom_matched": false,
            "get_by_text": "Reports",
            "ocr_type": "button",
            "page_name": "customers",
            "element_id": "5d451e44-64af-4b69-afa5-1c33eb979bb7",
            "type": "ocr",
            "unique_name": "customers_reports_button_navigation_1dc35b9f",
            "external": false,
            "placeholder": "Reports",
            "intent": "navigation"
        }
    },
    {
        "id": "c5c02338-6b39-454e-b0c1-36f8a6075803",
        "document": "Analytics",
        "metadata": {
            "label_text": "Analytics",
            "placeholder": "Analytics",
            "type": "ocr",
            "element_id": "c5c02338-6b39-454e-b0c1-36f8a6075803",
            "page_name": "customers",
            "dom_matched": false,
            "intent": "navigation",
            "ocr_type": "button",
            "get_by_text": "Analytics",
            "unique_name": "customers_analytics_button_navigation_8227d101",
            "external": false
        }
    },
    {
        "id": "715a03a7-141c-42a9-bf3c-c658a1375db2",
        "document": "Settings",
        "metadata": {
            "dom_matched": false,
            "label_text": "Settings",
            "intent": "navigation",
            "type": "ocr",
            "element_id": "715a03a7-141c-42a9-bf3c-c658a1375db2",
            "unique_name": "customers_settings_button_navigation_9de99b8a",
            "get_by_text": "Settings",
            "page_name": "customers",
            "placeholder": "Settings",
            "ocr_type": "button",
            "external": false
        }
    },
    {
        "id": "7105e58b-74dd-40f0-9a30-58ee5246da4e",
        "document": "Search customers, loans, transactions...",
        "metadata": {
            "element_id": "7105e58b-74dd-40f0-9a30-58ee5246da4e",
            "type": "ocr",
            "page_name": "customers",
            "external": false,
            "dom_matched": false,
            "placeholder": "Search customers, loans, transactions...",
            "get_by_text": "Search customers, loans, transactions...",
            "unique_name": "customers_search_customers,_loans,_transactions..._textbox_search_be73039f",
            "label_text": "Search customers, loans, transactions...",
            "ocr_type": "textbox",
            "intent": "search"
        }
    },
    {
        "id": "40c845b5-8970-4593-bf8d-2673a8dbabfc",
        "document": "Customers",
        "metadata": {
            "placeholder": "Customers",
            "external": false,
            "get_by_text": "Customers",
            "label_text": "Customers",
            "dom_matched": false,
            "type": "ocr",
            "page_name": "customers",
            "unique_name": "customers_customers_label_header_ab76000b",
            "ocr_type": "label",
            "element_id": "40c845b5-8970-4593-bf8d-2673a8dbabfc",
            "intent": "header"
        }
    },
    {
        "id": "12637cc5-45e3-42f0-8814-324597a00630",
        "document": "Manage your customer relationships and accounts",
        "metadata": {
            "type": "ocr",
            "unique_name": "customers_manage_your_customer_relationships_and_accounts_label_subheader_e7e5084f",
            "element_id": "12637cc5-45e3-42f0-8814-324597a00630",
            "label_text": "Manage your customer relationships and accounts",
            "page_name": "customers",
            "ocr_type": "label",
            "placeholder": "Manage your customer relationships and accounts",
            "external": false,
            "dom_matched": false,
            "get_by_text": "Manage your customer relationships and accounts",
            "intent": "subheader"
        }
    },
    {
        "id": "9675a87f-02e2-40ac-8474-c57ecc71c158",
        "document": "Search customers...",
        "metadata": {
            "ocr_type": "textbox",
            "intent": "search",
            "placeholder": "Search customers...",
            "unique_name": "customers_search_customers..._textbox_search_85d3ce1f",
            "page_name": "customers",
            "element_id": "9675a87f-02e2-40ac-8474-c57ecc71c158",
            "label_text": "Search customers...",
            "dom_matched": false,
            "type": "ocr",
            "get_by_text": "Search customers...",
            "external": false
        }
    },
    {
        "id": "1d9037d4-c8c8-400e-b98a-c998c576c443",
        "document": "Filters",
        "metadata": {
            "ocr_type": "button",
            "dom_matched": false,
            "type": "ocr",
            "label_text": "Filters",
            "external": false,
            "intent": "filter",
            "get_by_text": "Filters",
            "unique_name": "customers_filters_button_filter_4c0a3d63",
            "page_name": "customers",
            "placeholder": "Filters",
            "element_id": "1d9037d4-c8c8-400e-b98a-c998c576c443"
        }
    },
    {
        "id": "eff3c1dd-6717-4f43-b625-b1f64dc2003a",
        "document": "Customer List",
        "metadata": {
            "external": false,
            "element_id": "eff3c1dd-6717-4f43-b625-b1f64dc2003a",
            "type": "ocr",
            "ocr_type": "label",
            "page_name": "customers",
            "label_text": "Customer List",
            "intent": "section_header",
            "unique_name": "customers_customer_list_label_section_header_93cd1f20",
            "placeholder": "Customer List",
            "get_by_text": "Customer List",
            "dom_matched": false
        }
    },
    {
        "id": "33619458-ffbe-47ed-8685-527bbe9514cf",
        "document": "3 customers found",
        "metadata": {
            "page_name": "customers",
            "ocr_type": "label",
            "type": "ocr",
            "element_id": "33619458-ffbe-47ed-8685-527bbe9514cf",
            "placeholder": "3 customers found",
            "unique_name": "customers_3_customers_found_label_info_61b9a471",
            "dom_matched": false,
            "intent": "info",
            "label_text": "3 customers found",
            "get_by_text": "3 customers found",
            "external": false
        }
    },
    {
        "id": "402309d6-48b7-4854-b40e-d45cb9feee7a",
        "document": "Customer",
        "metadata": {
            "get_by_text": "Customer",
            "external": false,
            "element_id": "402309d6-48b7-4854-b40e-d45cb9feee7a",
            "label_text": "Customer",
            "page_name": "customers",
            "placeholder": "Customer",
            "unique_name": "customers_customer_label_column_header_cd74c3eb",
            "type": "ocr",
            "dom_matched": false,
            "ocr_type": "label",
            "intent": "column_header"
        }
    },
    {
        "id": "e32b6975-ef80-4288-9ea6-85684f58a442",
        "document": "Account Type",
        "metadata": {
            "element_id": "e32b6975-ef80-4288-9ea6-85684f58a442",
            "placeholder": "Account Type",
            "type": "ocr",
            "label_text": "Account Type",
            "ocr_type": "label",
            "unique_name": "customers_account_type_label_column_header_a712d19c",
            "external": false,
            "get_by_text": "Account Type",
            "intent": "column_header",
            "dom_matched": false,
            "page_name": "customers"
        }
    },
    {
        "id": "416dec62-6344-4748-9b84-6f9bbf3cd6e6",
        "document": "Balance",
        "metadata": {
            "page_name": "customers",
            "intent": "column_header",
            "ocr_type": "label",
            "unique_name": "customers_balance_label_column_header_d6648fd2",
            "type": "ocr",
            "get_by_text": "Balance",
            "external": false,
            "element_id": "416dec62-6344-4748-9b84-6f9bbf3cd6e6",
            "label_text": "Balance",
            "placeholder": "Balance",
            "dom_matched": false
        }
    },
    {
        "id": "0a918660-dc9e-401b-b76c-fd45bb9a7182",
        "document": "Status",
        "metadata": {
            "external": false,
            "page_name": "customers",
            "get_by_text": "Status",
            "element_id": "0a918660-dc9e-401b-b76c-fd45bb9a7182",
            "placeholder": "Status",
            "unique_name": "customers_status_label_column_header_57a06b20",
            "ocr_type": "label",
            "intent": "column_header",
            "dom_matched": false,
            "type": "ocr",
            "label_text": "Status"
        }
    },
    {
        "id": "3d481146-cb25-4159-a796-27d57ea12ad8",
        "document": "Join Date",
        "metadata": {
            "type": "ocr",
            "unique_name": "customers_join_date_label_column_header_cb167d9a",
            "page_name": "customers",
            "get_by_text": "Join Date",
            "label_text": "Join Date",
            "dom_matched": false,
            "ocr_type": "label",
            "placeholder": "Join Date",
            "element_id": "3d481146-cb25-4159-a796-27d57ea12ad8",
            "external": false,
            "intent": "column_header"
        }
    },
    {
        "id": "045bf295-91b2-49b6-b36d-ec85dff9ff93",
        "document": "Actions",
        "metadata": {
            "get_by_text": "Actions",
            "element_id": "045bf295-91b2-49b6-b36d-ec85dff9ff93",
            "external": false,
            "ocr_type": "label",
            "intent": "column_header",
            "dom_matched": false,
            "unique_name": "customers_actions_label_column_header_177ddb69",
            "type": "ocr",
            "page_name": "customers",
            "placeholder": "Actions",
            "label_text": "Actions"
        }
    },
    {
        "id": "de35605e-d0b9-4489-b47a-942b5b464ca0",
        "document": "Sarah Johnson",
        "metadata": {
            "unique_name": "customers_sarah_johnson_label_customer_name_91134cc9",
            "dom_matched": false,
            "label_text": "Sarah Johnson",
            "get_by_text": "Sarah Johnson",
            "type": "ocr",
            "placeholder": "Sarah Johnson",
            "page_name": "customers",
            "external": false,
            "ocr_type": "label",
            "intent": "customer_name",
            "element_id": "de35605e-d0b9-4489-b47a-942b5b464ca0"
        }
    },
    {
        "id": "29e97aac-53bf-474a-bc7c-3d96431bd189",
        "document": "sarah.johnson@email.com",
        "metadata": {
            "placeholder": "sarah.johnson@email.com",
            "get_by_text": "sarah.johnson@email.com",
            "element_id": "29e97aac-53bf-474a-bc7c-3d96431bd189",
            "page_name": "customers",
            "type": "ocr",
            "intent": "customer_email",
            "external": false,
            "ocr_type": "label",
            "unique_name": "customers_sarah.johnson@email.com_label_customer_email_ea79968a",
            "label_text": "sarah.johnson@email.com",
            "dom_matched": false
        }
    },
    {
        "id": "b13f458a-8d84-4ea6-8763-2031599b7a88",
        "document": "Premium",
        "metadata": {
            "intent": "account_type",
            "placeholder": "Premium",
            "ocr_type": "label",
            "unique_name": "customers_premium_label_account_type_c1ae4279",
            "dom_matched": false,
            "page_name": "customers",
            "label_text": "Premium",
            "element_id": "b13f458a-8d84-4ea6-8763-2031599b7a88",
            "get_by_text": "Premium",
            "type": "ocr",
            "external": false
        }
    },
    {
        "id": "bbbf68ac-5e0a-4a30-8f63-168e90940fa3",
        "document": "$1,45,000",
        "metadata": {
            "placeholder": "$1,45,000",
            "unique_name": "customers_$1,45,000_label_balance_dc74e6a8",
            "intent": "balance",
            "get_by_text": "$1,45,000",
            "element_id": "bbbf68ac-5e0a-4a30-8f63-168e90940fa3",
            "label_text": "$1,45,000",
            "type": "ocr",
            "dom_matched": false,
            "ocr_type": "label",
            "external": false,
            "page_name": "customers"
        }
    },
    {
        "id": "aa089598-7d33-4557-8748-804c1065deb3",
        "document": "Active",
        "metadata": {
            "ocr_type": "label",
            "page_name": "customers",
            "placeholder": "Active",
            "external": false,
            "unique_name": "customers_active_label_status_5fc1bbb1",
            "intent": "status",
            "dom_matched": false,
            "type": "ocr",
            "get_by_text": "Active",
            "label_text": "Active",
            "element_id": "aa089598-7d33-4557-8748-804c1065deb3"
        }
    },
    {
        "id": "98ea9a03-dfc9-45b2-a1d8-7197a3f73067",
        "document": "2023-01-15",
        "metadata": {
            "page_name": "customers",
            "type": "ocr",
            "placeholder": "2023-01-15",
            "get_by_text": "2023-01-15",
            "element_id": "98ea9a03-dfc9-45b2-a1d8-7197a3f73067",
            "unique_name": "customers_2023-01-15_label_join_date_13b4a3e0",
            "dom_matched": false,
            "ocr_type": "label",
            "external": false,
            "intent": "join_date",
            "label_text": "2023-01-15"
        }
    },
    {
        "id": "3530b22b-4b27-40ed-8c8c-36b4191b6990",
        "document": "",
        "metadata": {
            "type": "ocr",
            "dom_matched": false,
            "page_name": "customers",
            "unique_name": "customers_button_view_action_cc60ce91",
            "external": false,
            "ocr_type": "button",
            "intent": "view_action",
            "element_id": "3530b22b-4b27-40ed-8c8c-36b4191b6990",
            "get_by_text": "",
            "placeholder": "",
            "label_text": ""
        }
    },
    {
        "id": "10c0c6b4-6bd0-4fc2-b751-5a623dda8f79",
        "document": "",
        "metadata": {
            "label_text": "",
            "element_id": "10c0c6b4-6bd0-4fc2-b751-5a623dda8f79",
            "intent": "edit_action",
            "external": false,
            "type": "ocr",
            "ocr_type": "button",
            "get_by_text": "",
            "dom_matched": false,
            "unique_name": "customers_button_edit_action_d3d0df61",
            "page_name": "customers",
            "placeholder": ""
        }
    },
    {
        "id": "e65dd83c-241c-41b5-b5a9-ed5165e974da",
        "document": "Michael Chen",
        "metadata": {
            "ocr_type": "label",
            "page_name": "customers",
            "type": "ocr",
            "unique_name": "customers_michael_chen_label_customer_name_8dbd8345",
            "placeholder": "Michael Chen",
            "intent": "customer_name",
            "get_by_text": "Michael Chen",
            "label_text": "Michael Chen",
            "element_id": "e65dd83c-241c-41b5-b5a9-ed5165e974da",
            "dom_matched": false,
            "external": false
        }
    },
    {
        "id": "8d4ba95e-d5b3-46d2-9f85-0abe1d65945f",
        "document": "michael.chen@email.com",
        "metadata": {
            "label_text": "michael.chen@email.com",
            "placeholder": "michael.chen@email.com",
            "page_name": "customers",
            "element_id": "8d4ba95e-d5b3-46d2-9f85-0abe1d65945f",
            "dom_matched": false,
            "external": false,
            "get_by_text": "michael.chen@email.com",
            "ocr_type": "label",
            "unique_name": "customers_michael.chen@email.com_label_customer_email_8f50f16b",
            "type": "ocr",
            "intent": "customer_email"
        }
    },
    {
        "id": "a643f356-2cf1-44ed-835f-85dd1cb62402",
        "document": "Standard",
        "metadata": {
            "get_by_text": "Standard",
            "intent": "account_type",
            "label_text": "Standard",
            "page_name": "customers",
            "ocr_type": "label",
            "type": "ocr",
            "dom_matched": false,
            "unique_name": "customers_standard_label_account_type_ef9be216",
            "external": false,
            "element_id": "a643f356-2cf1-44ed-835f-85dd1cb62402",
            "placeholder": "Standard"
        }
    },
    {
        "id": "df13ee85-1d3b-494b-9e54-27d4a8375f38",
        "document": "$52,000",
        "metadata": {
            "element_id": "df13ee85-1d3b-494b-9e54-27d4a8375f38",
            "external": false,
            "get_by_text": "$52,000",
            "unique_name": "customers_$52,000_label_balance_b6e2bd67",
            "placeholder": "$52,000",
            "intent": "balance",
            "label_text": "$52,000",
            "page_name": "customers",
            "dom_matched": false,
            "ocr_type": "label",
            "type": "ocr"
        }
    },
    {
        "id": "aa089598-7d33-4557-8748-804c1065deb3",
        "document": "Active",
        "metadata": {
            "page_name": "customers",
            "unique_name": "customers_active_label_status_5fc1bbb1",
            "ocr_type": "label",
            "intent": "status",
            "placeholder": "Active",
            "element_id": "aa089598-7d33-4557-8748-804c1065deb3",
            "external": false,
            "label_text": "Active",
            "dom_matched": false,
            "type": "ocr",
            "get_by_text": "Active"
        }
    },
    {
        "id": "5988d487-3cb4-4859-97e4-bc403115037e",
        "document": "2023-03-22",
        "metadata": {
            "label_text": "2023-03-22",
            "get_by_text": "2023-03-22",
            "external": false,
            "placeholder": "2023-03-22",
            "dom_matched": false,
            "intent": "join_date",
            "page_name": "customers",
            "ocr_type": "label",
            "element_id": "5988d487-3cb4-4859-97e4-bc403115037e",
            "type": "ocr",
            "unique_name": "customers_2023-03-22_label_join_date_363240e3"
        }
    },
    {
        "id": "3530b22b-4b27-40ed-8c8c-36b4191b6990",
        "document": "",
        "metadata": {
            "unique_name": "customers_button_view_action_cc60ce91",
            "dom_matched": false,
            "get_by_text": "",
            "page_name": "customers",
            "ocr_type": "button",
            "intent": "view_action",
            "type": "ocr",
            "placeholder": "",
            "external": false,
            "element_id": "3530b22b-4b27-40ed-8c8c-36b4191b6990",
            "label_text": ""
        }
    },
    {
        "id": "10c0c6b4-6bd0-4fc2-b751-5a623dda8f79",
        "document": "",
        "metadata": {
            "dom_matched": false,
            "element_id": "10c0c6b4-6bd0-4fc2-b751-5a623dda8f79",
            "page_name": "customers",
            "unique_name": "customers_button_edit_action_d3d0df61",
            "label_text": "",
            "ocr_type": "button",
            "get_by_text": "",
            "external": false,
            "intent": "edit_action",
            "placeholder": "",
            "type": "ocr"
        }
    },
    {
        "id": "e72a7f93-47e0-49ae-b7ea-b598c4626734",
        "document": "Emma Davis",
        "metadata": {
            "ocr_type": "label",
            "element_id": "e72a7f93-47e0-49ae-b7ea-b598c4626734",
            "unique_name": "customers_emma_davis_label_customer_name_671b9ccd",
            "dom_matched": false,
            "type": "ocr",
            "external": false,
            "get_by_text": "Emma Davis",
            "label_text": "Emma Davis",
            "page_name": "customers",
            "intent": "customer_name",
            "placeholder": "Emma Davis"
        }
    },
    {
        "id": "80627a11-a898-4ba8-8b1e-f6ed9788a791",
        "document": "emma.davis@email.com",
        "metadata": {
            "page_name": "customers",
            "type": "ocr",
            "element_id": "80627a11-a898-4ba8-8b1e-f6ed9788a791",
            "get_by_text": "emma.davis@email.com",
            "unique_name": "customers_emma.davis@email.com_label_customer_email_1680f20b",
            "intent": "customer_email",
            "external": false,
            "dom_matched": false,
            "label_text": "emma.davis@email.com",
            "ocr_type": "label",
            "placeholder": "emma.davis@email.com"
        }
    },
    {
        "id": "b13f458a-8d84-4ea6-8763-2031599b7a88",
        "document": "Premium",
        "metadata": {
            "ocr_type": "label",
            "placeholder": "Premium",
            "element_id": "b13f458a-8d84-4ea6-8763-2031599b7a88",
            "label_text": "Premium",
            "type": "ocr",
            "get_by_text": "Premium",
            "page_name": "customers",
            "external": false,
            "unique_name": "customers_premium_label_account_type_c1ae4279",
            "intent": "account_type",
            "dom_matched": false
        }
    },
    {
        "id": "62c9875c-f7fb-452f-b16f-92beb73b460c",
        "document": "$89,000",
        "metadata": {
            "page_name": "customers",
            "type": "ocr",
            "external": false,
            "element_id": "62c9875c-f7fb-452f-b16f-92beb73b460c",
            "intent": "balance",
            "label_text": "$89,000",
            "ocr_type": "label",
            "dom_matched": false,
            "get_by_text": "$89,000",
            "placeholder": "$89,000",
            "unique_name": "customers_$89,000_label_balance_f3422319"
        }
    },
    {
        "id": "aa089598-7d33-4557-8748-804c1065deb3",
        "document": "Active",
        "metadata": {
            "dom_matched": false,
            "page_name": "customers",
            "ocr_type": "label",
            "unique_name": "customers_active_label_status_5fc1bbb1",
            "element_id": "aa089598-7d33-4557-8748-804c1065deb3",
            "external": false,
            "get_by_text": "Active",
            "label_text": "Active",
            "intent": "status",
            "type": "ocr",
            "placeholder": "Active"
        }
    },
    {
        "id": "bbce3c3b-1ea4-4fd5-b9e6-6b70bdbb2f88",
        "document": "2022-11-08",
        "metadata": {
            "type": "ocr",
            "dom_matched": false,
            "page_name": "customers",
            "element_id": "bbce3c3b-1ea4-4fd5-b9e6-6b70bdbb2f88",
            "ocr_type": "label",
            "unique_name": "customers_2022-11-08_label_join_date_bcd7c000",
            "placeholder": "2022-11-08",
            "label_text": "2022-11-08",
            "get_by_text": "2022-11-08",
            "external": false,
            "intent": "join_date"
        }
    },
    {
        "id": "3530b22b-4b27-40ed-8c8c-36b4191b6990",
        "document": "",
        "metadata": {
            "intent": "view_action",
            "placeholder": "",
            "type": "ocr",
            "ocr_type": "button",
            "page_name": "customers",
            "label_text": "",
            "element_id": "3530b22b-4b27-40ed-8c8c-36b4191b6990",
            "unique_name": "customers_button_view_action_cc60ce91",
            "get_by_text": "",
            "external": false,
            "dom_matched": false
        }
    },
    {
        "id": "10c0c6b4-6bd0-4fc2-b751-5a623dda8f79",
        "document": "",
        "metadata": {
            "unique_name": "customers_button_edit_action_d3d0df61",
            "dom_matched": false,
            "element_id": "10c0c6b4-6bd0-4fc2-b751-5a623dda8f79",
            "placeholder": "",
            "page_name": "customers",
            "ocr_type": "button",
            "external": false,
            "intent": "edit_action",
            "label_text": "",
            "get_by_text": "",
            "type": "ocr"
        }
    },
    {
        "id": "8b718123-3555-41a3-b5b5-e784c99a698d",
        "document": "Export",
        "metadata": {
            "ocr_type": "button",
            "external": false,
            "element_id": "8b718123-3555-41a3-b5b5-e784c99a698d",
            "intent": "export",
            "type": "ocr",
            "placeholder": "Export",
            "page_name": "customers",
            "dom_matched": false,
            "label_text": "Export",
            "get_by_text": "Export",
            "unique_name": "customers_export_button_export_ec306f18"
        }
    },
    {
        "id": "6461e89d-cf66-4832-a8ea-d9761a631529",
        "document": "New Customer",
        "metadata": {
            "ocr_type": "button",
            "get_by_text": "New Customer",
            "label_text": "New Customer",
            "page_name": "customers",
            "unique_name": "customers_new_customer_button_add_customer_33383326",
            "type": "ocr",
            "placeholder": "New Customer",
            "external": false,
            "element_id": "6461e89d-cf66-4832-a8ea-d9761a631529",
            "dom_matched": false,
            "intent": "add_customer"
        }
    },
    {
        "id": "632cc2eb-760f-4589-941f-5fe5665afdb2",
        "document": "Edit with",
        "metadata": {
            "type": "ocr",
            "element_id": "632cc2eb-760f-4589-941f-5fe5665afdb2",
            "placeholder": "Edit with",
            "unique_name": "customers_edit_with_label_footer_ca0fec1e",
            "label_text": "Edit with",
            "get_by_text": "Edit with",
            "external": false,
            "dom_matched": false,
            "page_name": "customers",
            "ocr_type": "label",
            "intent": "footer"
        }
    },
    {
        "id": "076ae535-1ec4-4d8e-ac1b-aaa6ad79f1d3",
        "document": "Lovable",
        "metadata": {
            "element_id": "076ae535-1ec4-4d8e-ac1b-aaa6ad79f1d3",
            "unique_name": "customers_lovable_label_footer_brand_301dffac",
            "external": false,
            "ocr_type": "label",
            "placeholder": "Lovable",
            "type": "ocr",
            "intent": "footer_brand",
            "get_by_text": "Lovable",
            "label_text": "Lovable",
            "dom_matched": false,
            "page_name": "customers"
        }
    }
]


# === FILE: data\stored\20250726_151348_customers_2.json ===
[
    {
        "id": "95bf0180-6790-4215-91b5-f687892ec5fd",
        "document": "Add New Customer",
        "metadata": {
            "external": false,
            "label_text": "Add New Customer",
            "element_id": "95bf0180-6790-4215-91b5-f687892ec5fd",
            "get_by_text": "Add New Customer",
            "intent": "form_title",
            "type": "ocr",
            "dom_matched": false,
            "placeholder": "Add New Customer",
            "unique_name": "customers_add_new_customer_label_form_title_2b3b0780",
            "page_name": "customers",
            "ocr_type": "label"
        }
    },
    {
        "id": "1ae4070a-51bc-4a91-98fa-a080f1141adb",
        "document": "Enter the customer details to create a new account.",
        "metadata": {
            "intent": "form_instruction",
            "placeholder": "Enter the customer details to create a new account.",
            "label_text": "Enter the customer details to create a new account.",
            "element_id": "1ae4070a-51bc-4a91-98fa-a080f1141adb",
            "ocr_type": "label",
            "page_name": "customers",
            "unique_name": "customers_enter_the_customer_details_to_create_a_new_account._label_form_instruction_4e368c65",
            "external": false,
            "get_by_text": "Enter the customer details to create a new account.",
            "dom_matched": false,
            "type": "ocr"
        }
    },
    {
        "id": "7563fa40-7908-413b-8842-5a205b83fbb0",
        "document": "Full Name",
        "metadata": {
            "ocr_type": "label",
            "intent": "full_name_label",
            "external": false,
            "placeholder": "Full Name",
            "get_by_text": "Full Name",
            "element_id": "7563fa40-7908-413b-8842-5a205b83fbb0",
            "type": "ocr",
            "unique_name": "customers_full_name_label_full_name_label_7fa7eb35",
            "dom_matched": false,
            "page_name": "customers",
            "label_text": "Full Name"
        }
    },
    {
        "id": "4fc76c41-e666-4be8-bdfd-434f0120ad48",
        "document": "",
        "metadata": {
            "page_name": "customers",
            "external": false,
            "intent": "full_name_input",
            "ocr_type": "textbox",
            "type": "ocr",
            "element_id": "4fc76c41-e666-4be8-bdfd-434f0120ad48",
            "label_text": "",
            "placeholder": "",
            "get_by_text": "",
            "dom_matched": false,
            "unique_name": "customers_textbox_full_name_input_b5555c13"
        }
    },
    {
        "id": "c5b03e6c-7ece-4075-ac3f-8fd0f3e641f7",
        "document": "Email",
        "metadata": {
            "placeholder": "Email",
            "ocr_type": "label",
            "external": false,
            "unique_name": "customers_email_label_email_label_1e22d7f0",
            "get_by_text": "Email",
            "label_text": "Email",
            "dom_matched": false,
            "intent": "email_label",
            "element_id": "c5b03e6c-7ece-4075-ac3f-8fd0f3e641f7",
            "page_name": "customers",
            "type": "ocr"
        }
    },
    {
        "id": "f120a144-ff93-416c-91dc-6af41aa86bb6",
        "document": "",
        "metadata": {
            "get_by_text": "",
            "type": "ocr",
            "ocr_type": "textbox",
            "label_text": "",
            "intent": "email_input",
            "element_id": "f120a144-ff93-416c-91dc-6af41aa86bb6",
            "dom_matched": false,
            "unique_name": "customers_textbox_email_input_b7f01675",
            "external": false,
            "placeholder": "",
            "page_name": "customers"
        }
    },
    {
        "id": "d146407e-2129-4572-8e7c-bfecdc8f619a",
        "document": "Phone Number",
        "metadata": {
            "type": "ocr",
            "placeholder": "Phone Number",
            "element_id": "d146407e-2129-4572-8e7c-bfecdc8f619a",
            "intent": "phone_number_label",
            "page_name": "customers",
            "unique_name": "customers_phone_number_label_phone_number_label_03e465fd",
            "dom_matched": false,
            "external": false,
            "label_text": "Phone Number",
            "ocr_type": "label",
            "get_by_text": "Phone Number"
        }
    },
    {
        "id": "b6b33ed1-7a9a-4819-955b-c7a58242cc7e",
        "document": "",
        "metadata": {
            "element_id": "b6b33ed1-7a9a-4819-955b-c7a58242cc7e",
            "placeholder": "",
            "ocr_type": "textbox",
            "intent": "phone_number_input",
            "dom_matched": false,
            "unique_name": "customers_textbox_phone_number_input_bb72a72b",
            "page_name": "customers",
            "external": false,
            "label_text": "",
            "get_by_text": "",
            "type": "ocr"
        }
    },
    {
        "id": "1b06e63a-6e85-49f0-81b1-5cf05a84cb54",
        "document": "Account Type",
        "metadata": {
            "intent": "account_type_label",
            "type": "ocr",
            "ocr_type": "label",
            "placeholder": "Account Type",
            "dom_matched": false,
            "label_text": "Account Type",
            "external": false,
            "element_id": "1b06e63a-6e85-49f0-81b1-5cf05a84cb54",
            "page_name": "customers",
            "unique_name": "customers_account_type_label_account_type_label_a1b76de7",
            "get_by_text": "Account Type"
        }
    },
    {
        "id": "83de4a69-5821-4d05-8918-c11403dece47",
        "document": "Select account type",
        "metadata": {
            "external": false,
            "dom_matched": false,
            "ocr_type": "select",
            "element_id": "83de4a69-5821-4d05-8918-c11403dece47",
            "label_text": "Select account type",
            "type": "ocr",
            "page_name": "customers",
            "intent": "account_type_select",
            "placeholder": "Select account type",
            "unique_name": "customers_select_account_type_select_account_type_select_739bf8ef",
            "get_by_text": "Select account type"
        }
    },
    {
        "id": "23679824-8cbe-4cd7-bc8e-9e60a319a45f",
        "document": "Address",
        "metadata": {
            "page_name": "customers",
            "dom_matched": false,
            "get_by_text": "Address",
            "external": false,
            "unique_name": "customers_address_label_address_label_bfa99020",
            "ocr_type": "label",
            "element_id": "23679824-8cbe-4cd7-bc8e-9e60a319a45f",
            "intent": "address_label",
            "type": "ocr",
            "placeholder": "Address",
            "label_text": "Address"
        }
    },
    {
        "id": "22921c87-15c6-4cbf-a35a-42ce97a26fcb",
        "document": "",
        "metadata": {
            "page_name": "customers",
            "get_by_text": "",
            "external": false,
            "element_id": "22921c87-15c6-4cbf-a35a-42ce97a26fcb",
            "type": "ocr",
            "unique_name": "customers_textbox_address_input_0da1bba0",
            "intent": "address_input",
            "label_text": "",
            "placeholder": "",
            "dom_matched": false,
            "ocr_type": "textbox"
        }
    },
    {
        "id": "3c0da3bc-1298-40e7-8cf9-b78acd1d2c6d",
        "document": "Occupation",
        "metadata": {
            "unique_name": "customers_occupation_label_occupation_label_78041ebe",
            "page_name": "customers",
            "type": "ocr",
            "get_by_text": "Occupation",
            "ocr_type": "label",
            "dom_matched": false,
            "label_text": "Occupation",
            "intent": "occupation_label",
            "element_id": "3c0da3bc-1298-40e7-8cf9-b78acd1d2c6d",
            "external": false,
            "placeholder": "Occupation"
        }
    },
    {
        "id": "14bde66a-1b44-45b4-9e19-9883caf63b1d",
        "document": "",
        "metadata": {
            "get_by_text": "",
            "page_name": "customers",
            "label_text": "",
            "external": false,
            "ocr_type": "textbox",
            "element_id": "14bde66a-1b44-45b4-9e19-9883caf63b1d",
            "intent": "occupation_input",
            "dom_matched": false,
            "placeholder": "",
            "unique_name": "customers_textbox_occupation_input_7c88216e",
            "type": "ocr"
        }
    },
    {
        "id": "a072d846-062f-47ae-b0df-f77d359425ff",
        "document": "Annual Income",
        "metadata": {
            "get_by_text": "Annual Income",
            "element_id": "a072d846-062f-47ae-b0df-f77d359425ff",
            "label_text": "Annual Income",
            "ocr_type": "label",
            "page_name": "customers",
            "placeholder": "Annual Income",
            "intent": "annual_income_label",
            "external": false,
            "unique_name": "customers_annual_income_label_annual_income_label_41327b0b",
            "dom_matched": false,
            "type": "ocr"
        }
    },
    {
        "id": "9e6119b3-2d6c-4445-ad07-3a0e72a48f71",
        "document": "",
        "metadata": {
            "placeholder": "",
            "label_text": "",
            "ocr_type": "textbox",
            "type": "ocr",
            "external": false,
            "page_name": "customers",
            "unique_name": "customers_textbox_annual_income_input_7b960691",
            "dom_matched": false,
            "intent": "annual_income_input",
            "get_by_text": "",
            "element_id": "9e6119b3-2d6c-4445-ad07-3a0e72a48f71"
        }
    },
    {
        "id": "eff18cd5-3b5d-48a6-ac2d-58b76784ba58",
        "document": "Initial Deposit",
        "metadata": {
            "external": false,
            "intent": "initial_deposit_label",
            "element_id": "eff18cd5-3b5d-48a6-ac2d-58b76784ba58",
            "dom_matched": false,
            "unique_name": "customers_initial_deposit_label_initial_deposit_label_a98dd99a",
            "placeholder": "Initial Deposit",
            "get_by_text": "Initial Deposit",
            "label_text": "Initial Deposit",
            "type": "ocr",
            "page_name": "customers",
            "ocr_type": "label"
        }
    },
    {
        "id": "94288828-20cd-438f-85b1-8970413e0a2b",
        "document": "",
        "metadata": {
            "unique_name": "customers_textbox_initial_deposit_input_842f44e3",
            "intent": "initial_deposit_input",
            "element_id": "94288828-20cd-438f-85b1-8970413e0a2b",
            "get_by_text": "",
            "page_name": "customers",
            "label_text": "",
            "type": "ocr",
            "ocr_type": "textbox",
            "dom_matched": false,
            "placeholder": "",
            "external": false
        }
    },
    {
        "id": "b13ea0e7-0235-41be-842d-5b83fb617804",
        "document": "Cancel",
        "metadata": {
            "intent": "cancel",
            "unique_name": "customers_cancel_button_cancel_71a3913d",
            "external": false,
            "get_by_text": "Cancel",
            "dom_matched": false,
            "type": "ocr",
            "element_id": "b13ea0e7-0235-41be-842d-5b83fb617804",
            "page_name": "customers",
            "label_text": "Cancel",
            "ocr_type": "button",
            "placeholder": "Cancel"
        }
    },
    {
        "id": "a4c9805f-fad4-42ca-b8e6-d9235a0ebafa",
        "document": "Add Customer",
        "metadata": {
            "get_by_text": "Add Customer",
            "page_name": "customers",
            "dom_matched": false,
            "external": false,
            "unique_name": "customers_add_customer_button_submit_bce56d38",
            "type": "ocr",
            "label_text": "Add Customer",
            "element_id": "a4c9805f-fad4-42ca-b8e6-d9235a0ebafa",
            "placeholder": "Add Customer",
            "ocr_type": "button",
            "intent": "submit"
        }
    }
]


# === FILE: generated_runs\src\data\test_data.json ===
{
  "login": {
    "username": "standard_user",
    "password": "secret_sauce"
  },
  "checkout": {
    "first_name": "John",
    "last_name": "Doe",
    "zip_code": "12345"
  },
  "product": {
    "name": "Sauce Labs Backpack"
  }
}


# === FILE: generated_runs\src\data\__init__.py ===



# === FILE: generated_runs\src\lib\smart_ai.py ===
import json
import numpy as np
from sentence_transformers import SentenceTransformer, util

class SmartAILocatorError(Exception):
    pass

# 🟢 Minimal wrapper to handle select_option fallback automatically
class SmartAIWrappedLocator:
    def __init__(self, locator, page):
        self._locator = locator
        self._page = page

    def __getattr__(self, name):
        # Delegate all other methods/attributes to Playwright's locator
        return getattr(self._locator, name)

    def select_option(self, value):
        try:
            return self._locator.select_option(value)
        except Exception as e:
            print(f"[SmartAI][select_option fallback] Native select_option failed: {e}")
            try:
                self._page.get_by_role("combobox").click()
                self._page.get_by_role("option", name=value).click()
                print(f"[SmartAI][select_option fallback] Selected '{value}' via combobox+option fallback")
            except Exception as e2:
                print(f"[SmartAI][select_option fallback] Fallback also failed: {e2}")
                raise

class SmartAISelfHealing:
    def __init__(self, metadata):
        self.metadata = metadata
        self.model = SentenceTransformer("all-MiniLM-L6-v2")
        # 1️⃣ Cache embeddings for all metadata elements for fast ML matching
        self.embeddings = [
            self.model.encode(self._element_to_string(e), convert_to_tensor=True, show_progress_bar=False)
            for e in self.metadata
        ]
        # 10️⃣ Track failed locators (element unique_name → fail count)
        self.locator_fail_count = {}

    # 5️⃣ Single definition; all prioritization inside
    def _try_all_locators(self, element, page):
        strategies = []

        # Highest priority: try by role and label_text (esp for button, input, etc)
        if element.get("tag_name") and element.get("label_text"):
            role = self._map_tag_to_role(element["tag_name"])
            if role:
                strategies.append((lambda: page.get_by_role(
                    role, name=element["label_text"]), f"get_by_role({role}, name={element['label_text']})"))

        # Try by label (best for inputs)
        if element.get("label_text"):
            strategies.append((lambda: page.get_by_label(
                element["label_text"]), f"get_by_label({element['label_text']})"))

        # Try by visible text (good for buttons, links, etc)
        if element.get("label_text"):
            strategies.append((lambda: page.get_by_text(
                element["label_text"], exact=True), f"get_by_text({element['label_text']}, exact=True)"))

        # Try by placeholder (for textboxes/inputs)
        if element.get("placeholder"):
            strategies.append((lambda: page.get_by_placeholder(
                element["placeholder"]), f"get_by_placeholder({element['placeholder']})"))

        # Try by sample value (displayed value in input)
        if element.get("sample_value"):
            strategies.append((lambda: page.get_by_display_value(
                element["sample_value"]), f"get_by_display_value({element['sample_value']})"))

        # Data attributes (testid/qa)
        data_attrs = element.get("data_attrs", {})
        for k, v in data_attrs.items():
            if "test" in k.lower() or "qa" in k.lower():
                strategies.append((lambda: page.get_by_test_id(v),
                                f"get_by_test_id({v}) for {k}"))

        # By id (exact and partial)
        if element.get("dom_id"):
            id_value = element["dom_id"]
            strategies.append((lambda: page.locator(
                f'#{id_value}'), f"locator(#{id_value}) [ID exact]"))
            strategies.append((lambda: page.locator(
                f'[id*="{id_value}"]'), f'locator([id*="{id_value}"]) [ID partial]'))

        # By class (exact and partial)
        if element.get("dom_class"):
            class_value = element["dom_class"]
            class_sel = "." + ".".join(class_value.split())
            strategies.append((lambda: page.locator(class_sel),
                            f"locator({class_sel}) [class exact]"))
            strategies.append((lambda: page.locator(
                f'[class*="{class_value}"]'), f'locator([class*="{class_value}"]) [class partial]'))

        # By class_list
        if element.get("class_list"):
            sel = "." + ".".join(element["class_list"])
            strategies.append((lambda: page.locator(
                sel), f"locator({sel}) [class_list]"))

        # Custom CSS locator
        if element.get("locator") and element["locator"].get("type") == "css":
            strategies.append((lambda: page.locator(
                element["locator"]["value"]), f"locator({element['locator']['value']}) [custom css]"))
                
        # Now try each strategy in order
        for func, desc in strategies:
            try:
                locator = func()
                if locator and locator.count() > 0:
                    print(f"[SmartAI][Return] {desc} succeeded.")
                    self.locator_fail_count[element.get("unique_name")] = 0
                    return locator.last
            except Exception as e:
                unique_name = element.get("unique_name", "")
                self.locator_fail_count[unique_name] = self.locator_fail_count.get(
                    unique_name, 0) + 1
                print(f"[SmartAI][Skip] {desc} failed: {e}")

        print("[SmartAI][Return] No locator found for element.")
        return None

    # def _try_all_locators(self, element, page):
    #     # Tries various locator strategies in strict priority order.
    #     # Enhancement: Prioritize, early return, minimal .count() checks.
    #     # Enhancement: Penalize recently failing locators.
    #     def should_skip(unique_name):
    #         return self.locator_fail_count.get(unique_name, 0) >= 3

    #     strategies = []

    #     data_attrs = element.get("data_attrs", {})
    #     for k, v in data_attrs.items():
    #         if "test" in k.lower() or "qa" in k.lower():
    #             strategies.append((lambda: page.get_by_test_id(v), f"get_by_test_id({v}) for {k}"))

    #     if element.get("tag_name"):
    #         role = self._map_tag_to_role(element["tag_name"])
    #         if role and element.get("label_text"):
    #             strategies.append((lambda: page.get_by_role(role, name=element["label_text"]), f"get_by_role({role}, name={element['label_text']})"))

    #     if element.get("label_text"):
    #         strategies.append((lambda: page.get_by_label(element["label_text"]), f"get_by_label({element['label_text']})"))

    #     if element.get("placeholder"):
    #         strategies.append((lambda: page.get_by_placeholder(element["placeholder"]), f"get_by_placeholder({element['placeholder']})"))

    #     if element.get("label_text"):
    #         strategies.append((lambda: page.get_by_text(element["label_text"], exact=True), f"get_by_text({element['label_text']}, exact=True)"))

    #     if element.get("sample_value"):
    #         strategies.append((lambda: page.get_by_display_value(element["sample_value"]), f"get_by_display_value({element['sample_value']})"))

    #     if element.get("dom_id"):
    #         id_value = element["dom_id"]
    #         strategies.append((lambda: page.locator(f'#{id_value}'), f"locator(#{id_value}) [ID exact]"))
    #         strategies.append((lambda: page.locator(f'[id*="{id_value}"]'), f'locator([id*="{id_value}"]) [ID partial]'))

    #     if element.get("dom_class"):
    #         class_value = element["dom_class"]
    #         class_sel = "." + ".".join(class_value.split())
    #         strategies.append((lambda: page.locator(class_sel), f"locator({class_sel}) [class exact]"))
    #         strategies.append((lambda: page.locator(f'[class*="{class_value}"]'), f'locator([class*="{class_value}"]) [class partial]'))

    #     if element.get("class_list"):
    #         sel = "." + ".".join(element["class_list"])
    #         strategies.append((lambda: page.locator(sel), f"locator({sel}) [class_list]"))

    #     if element.get("locator") and element["locator"].get("type") == "css":
    #         strategies.append((lambda: page.locator(element["locator"]["value"]), f"locator({element['locator']['value']}) [custom css]"))

    #     # Attempt strategies in order, skipping if penalized
    #     for func, desc in strategies:
    #         try:
    #             locator = func()
    #             # 2️⃣ Only check .count() once per strategy, early return
    #             if locator and locator.count() > 0:
    #                 print(f"[SmartAI][Return] {desc} succeeded.")
    #                 self.locator_fail_count[element.get("unique_name")] = 0  # Reset fail count
    #                 return locator.last
    #         except Exception as e:
    #             # 10️⃣ Track fail count for this unique_name
    #             unique_name = element.get("unique_name", "")
    #             self.locator_fail_count[unique_name] = self.locator_fail_count.get(unique_name, 0) + 1
    #             print(f"[SmartAI][Skip] {desc} failed: {e}")

    #     print("[SmartAI][Return] No locator found for element.")
    #     return None

    def find_element(self, unique_name, page):
        # Main entry for SmartAI: tries direct lookup, then ML self-healing, then heuristics.
        element = self._find_by_unique_name(unique_name)
        if element:
            locator = self._try_all_locators(element, page)
            if locator:
                print(f"[SmartAI] Element '{unique_name}' found using primary metadata.")
                return SmartAIWrappedLocator(locator, page)  # <--- PATCHED

            print(f"[SmartAI] Primary methods failed for '{unique_name}', trying ML self-healing...")

        # ML-based fallback
        element_ml, ml_score = self._ml_self_heal(unique_name)
        if element_ml:
            locator_ml = self._try_all_locators(element_ml, page)
            if locator_ml:
                print(f"[SmartAI] Healed element via ML ({ml_score:.2f}): '{element_ml.get('unique_name')}'")
                return SmartAIWrappedLocator(locator_ml, page)  # <--- PATCHED

        # 9️⃣ Intent-aware fallback: try other elements with same intent
        target_intent = element_ml.get("intent") if element_ml else None
        if target_intent:
            for e in self.metadata:
                if e.get("intent") == target_intent and e.get("unique_name") != unique_name:
                    locator = self._try_all_locators(e, page)
                    if locator:
                        print(f"[SmartAI] Healed element by intent ('{target_intent}'): '{e.get('unique_name')}'")
                        return SmartAIWrappedLocator(locator, page)  # <--- PATCHED

        # 11️⃣ Visual/position fallback (commented for extension)
        # print("[SmartAI] Trying fallback by position (not implemented)...")

        raise SmartAILocatorError(f"Element '{unique_name}' not found and cannot self-heal.")

    def _find_by_unique_name(self, unique_name):
        return next((e for e in self.metadata if e.get("unique_name") == unique_name), None)

    def _map_tag_to_role(self, tag):
        tag_role_map = {
            'button': 'button',
            'input': 'textbox',
            'select': 'combobox',
            'textarea': 'textbox',
            'checkbox': 'checkbox'
        }
        return tag_role_map.get(tag.lower(), None)

    def _ml_self_heal(self, unique_name):
        # Returns best-matched element and score.
        # Enhancement: Uses pre-cached embeddings for performance!
        # 3️⃣ Uses higher threshold for accuracy.
        query_embedding = self.model.encode(unique_name, convert_to_tensor=True, show_progress_bar=False)
        scores = [util.cos_sim(query_embedding, emb).item() for emb in self.embeddings]
        best_idx = int(np.argmax(scores))
        best_score = scores[best_idx]
        print(f"[SmartAI] ML healed best match score: {best_score:.2f}")
        # 3️⃣ Higher threshold (was 0.3, now 0.6)
        return (self.metadata[best_idx], best_score) if best_score > 0.6 else (None, best_score)

    def _element_to_string(self, element):
        # Enhancement: Fast string construction, no json.dumps.
        fields = [
            element.get("unique_name", ""),
            element.get("label_text", ""),
            element.get("intent", ""),
            element.get("ocr_type", ""),
            element.get("element_type", ""),
            element.get("tag_name", ""),
            element.get("placeholder", ""),
            " ".join(element.get("class_list", [])) if element.get("class_list") else "",
            # 4️⃣ Fast join for data_attrs
            " ".join(f"{k}:{v}" for k, v in (element.get("data_attrs", {}) or {}).items()),
            element.get("sample_value", ""),
        ]
        return " ".join([str(f) for f in fields if f])

# ====== PAGE PATCH ======
def patch_page_with_smartai(page, metadata):
    ai_healer = SmartAISelfHealing(metadata)
    def smartAI(unique_name):
        return ai_healer.find_element(unique_name, page)
    page.smartAI = smartAI
    return page



# === FILE: generated_runs\src\lib\__init__.py ===



# === FILE: generated_runs\src\metadata\before_enrichment.json ===
[
  {
    "unique_name": "dashboard_button_navigation_34c032c8",
    "ocr_type": "button",
    "intent": "navigation",
    "get_by_text": "",
    "placeholder": "",
    "external": false,
    "dom_matched": false,
    "type": "ocr",
    "element_id": "1233c562-20f0-4202-90fd-663914b09c9d",
    "label_text": "",
    "page_name": "dashboard"
  },
  {
    "unique_name": "dashboard_search_customers,_loans,_transactions..._textbox_search_3310a968",
    "ocr_type": "textbox",
    "get_by_text": "Search customers, loans, transactions...",
    "dom_matched": false,
    "intent": "search",
    "label_text": "Search customers, loans, transactions...",
    "element_id": "0da341dd-0730-4547-b6b2-b2d3f0cc8a1a",
    "type": "ocr",
    "external": false,
    "placeholder": "Search customers, loans, transactions...",
    "page_name": "dashboard"
  },
  {
    "intent": "navigation",
    "ocr_type": "button",
    "label_text": "Dashboard",
    "dom_matched": false,
    "placeholder": "Dashboard",
    "page_name": "dashboard",
    "get_by_text": "Dashboard",
    "unique_name": "dashboard_dashboard_button_navigation_83914516",
    "external": false,
    "element_id": "fcab9ebe-5767-462d-8cfb-82bd3348f3f9",
    "type": "ocr"
  },
  {
    "label_text": "Customers",
    "page_name": "dashboard",
    "dom_matched": false,
    "unique_name": "dashboard_customers_button_navigation_bb4303b6",
    "external": false,
    "intent": "navigation",
    "placeholder": "Customers",
    "element_id": "45394f62-91b9-4529-adae-5627e4313b4c",
    "type": "ocr",
    "get_by_text": "Customers",
    "ocr_type": "button"
  },
  {
    "label_text": "Loans",
    "intent": "navigation",
    "ocr_type": "button",
    "external": false,
    "dom_matched": false,
    "page_name": "dashboard",
    "placeholder": "Loans",
    "unique_name": "dashboard_loans_button_navigation_42436e2a",
    "element_id": "24e6ff1a-d33a-4ba8-a5a6-be626370a5dd",
    "type": "ocr",
    "get_by_text": "Loans"
  },
  {
    "external": false,
    "get_by_text": "Transactions",
    "label_text": "Transactions",
    "type": "ocr",
    "intent": "navigation",
    "element_id": "c8b402b6-f1f8-4c0e-ae27-ccab631cd424",
    "ocr_type": "button",
    "unique_name": "dashboard_transactions_button_navigation_f0479a72",
    "page_name": "dashboard",
    "dom_matched": false,
    "placeholder": "Transactions"
  },
  {
    "unique_name": "dashboard_tasks_button_navigation_cde2a4d6",
    "page_name": "dashboard",
    "intent": "navigation",
    "element_id": "560d2d8f-c76a-4d45-9a08-a11877b31d9e",
    "type": "ocr",
    "external": false,
    "dom_matched": false,
    "placeholder": "Tasks",
    "ocr_type": "button",
    "label_text": "Tasks",
    "get_by_text": "Tasks"
  },
  {
    "unique_name": "dashboard_reports_button_navigation_578fb659",
    "placeholder": "Reports",
    "dom_matched": false,
    "element_id": "b95730ff-2fe4-44c4-baf5-ad976c203079",
    "ocr_type": "button",
    "page_name": "dashboard",
    "label_text": "Reports",
    "type": "ocr",
    "intent": "navigation",
    "external": false,
    "get_by_text": "Reports"
  },
  {
    "intent": "navigation",
    "type": "ocr",
    "get_by_text": "Analytics",
    "placeholder": "Analytics",
    "unique_name": "dashboard_analytics_button_navigation_49884ab5",
    "page_name": "dashboard",
    "element_id": "16d843ef-d207-41e4-884a-80192b4cd287",
    "external": false,
    "ocr_type": "button",
    "label_text": "Analytics",
    "dom_matched": false
  },
  {
    "dom_matched": false,
    "external": false,
    "type": "ocr",
    "get_by_text": "Settings",
    "placeholder": "Settings",
    "ocr_type": "button",
    "element_id": "fd2f64e0-9d2a-4bb1-9af2-7c439720110f",
    "intent": "navigation",
    "unique_name": "dashboard_settings_button_navigation_7a36fd5d",
    "label_text": "Settings",
    "page_name": "dashboard"
  },
  {
    "type": "ocr",
    "get_by_text": "Dashboard",
    "intent": "page_title",
    "label_text": "Dashboard",
    "external": false,
    "unique_name": "dashboard_dashboard_label_page_title_a353b4f0",
    "page_name": "dashboard",
    "dom_matched": false,
    "placeholder": "Dashboard",
    "element_id": "fe6111b7-5b58-44b0-be3a-0e52f5d35069",
    "ocr_type": "label"
  },
  {
    "unique_name": "dashboard_welcome_back!_heres_your_banking_overview._label_welcome_message_479a4097",
    "dom_matched": false,
    "external": false,
    "get_by_text": "Welcome back! Here's your banking overview.",
    "ocr_type": "label",
    "page_name": "dashboard",
    "element_id": "e2660127-d787-4393-a482-66947dcfdf81",
    "intent": "welcome_message",
    "placeholder": "Welcome back! Here's your banking overview.",
    "label_text": "Welcome back! Here's your banking overview.",
    "type": "ocr"
  },
  {
    "placeholder": "Total Customers",
    "unique_name": "dashboard_total_customers_label_total_customers_228048fb",
    "label_text": "Total Customers",
    "type": "ocr",
    "external": false,
    "get_by_text": "Total Customers",
    "element_id": "51501189-4e74-41b9-b6da-987a9a839f87",
    "intent": "total_customers",
    "ocr_type": "label",
    "page_name": "dashboard",
    "dom_matched": false
  },
  {
    "external": false,
    "element_id": "e46b7f1c-c443-45db-912e-43c546fe068d",
    "ocr_type": "label",
    "intent": "total_customers_value",
    "label_text": "2,847",
    "get_by_text": "2,847",
    "page_name": "dashboard",
    "dom_matched": false,
    "unique_name": "dashboard_2,847_label_total_customers_value_6d9c1e09",
    "type": "ocr",
    "placeholder": "2,847"
  },
  {
    "element_id": "754d67d0-6559-4e6a-8f28-a97134bbc10f",
    "external": false,
    "placeholder": "Active Loans",
    "page_name": "dashboard",
    "get_by_text": "Active Loans",
    "dom_matched": false,
    "type": "ocr",
    "label_text": "Active Loans",
    "ocr_type": "label",
    "intent": "active_loans",
    "unique_name": "dashboard_active_loans_label_active_loans_3dfc1d95"
  },
  {
    "ocr_type": "label",
    "external": false,
    "type": "ocr",
    "element_id": "b449e2aa-16c0-442c-bc74-179c54c09378",
    "unique_name": "dashboard_$45.2m_label_active_loans_value_e93e7652",
    "dom_matched": false,
    "label_text": "$45.2M",
    "placeholder": "$45.2M",
    "get_by_text": "$45.2M",
    "page_name": "dashboard",
    "intent": "active_loans_value"
  },
  {
    "external": false,
    "unique_name": "dashboard_monthly_transactions_label_monthly_transactions_914c549d",
    "ocr_type": "label",
    "intent": "monthly_transactions",
    "placeholder": "Monthly Transactions",
    "element_id": "74c7e9d8-4ec9-4da5-a7b6-7d178729f85d",
    "label_text": "Monthly Transactions",
    "type": "ocr",
    "page_name": "dashboard",
    "dom_matched": false,
    "get_by_text": "Monthly Transactions"
  },
  {
    "ocr_type": "label",
    "element_id": "b7db7fa6-1bb0-49bc-84bd-6a392ecff739",
    "placeholder": "18,394",
    "dom_matched": false,
    "unique_name": "dashboard_18,394_label_monthly_transactions_value_fc666ffb",
    "intent": "monthly_transactions_value",
    "external": false,
    "get_by_text": "18,394",
    "page_name": "dashboard",
    "label_text": "18,394",
    "type": "ocr"
  },
  {
    "intent": "revenue_growth",
    "get_by_text": "Revenue Growth",
    "external": false,
    "type": "ocr",
    "unique_name": "dashboard_revenue_growth_label_revenue_growth_bfb3b4b4",
    "ocr_type": "label",
    "page_name": "dashboard",
    "label_text": "Revenue Growth",
    "dom_matched": false,
    "element_id": "9d226a1f-3b4f-4a1c-8b4a-7a2fd9cf79c9",
    "placeholder": "Revenue Growth"
  },
  {
    "intent": "revenue_growth_value",
    "dom_matched": false,
    "ocr_type": "label",
    "unique_name": "dashboard_4%_label_revenue_growth_value_de36ce03",
    "element_id": "9b39d3eb-ace4-4812-88b7-7105876d6531",
    "placeholder": "4%",
    "page_name": "dashboard",
    "type": "ocr",
    "label_text": "4%",
    "external": false,
    "get_by_text": "4%"
  },
  {
    "dom_matched": false,
    "type": "ocr",
    "ocr_type": "button",
    "element_id": "2719b853-b04e-43ab-b4e5-9880b4baf57a",
    "external": false,
    "label_text": "Export Report",
    "unique_name": "dashboard_export_report_button_export_ed26f6d4",
    "intent": "export",
    "page_name": "dashboard",
    "placeholder": "Export Report",
    "get_by_text": "Export Report"
  },
  {
    "type": "ocr",
    "page_name": "dashboard",
    "label_text": "Loan Portfolio Trend",
    "dom_matched": false,
    "unique_name": "dashboard_loan_portfolio_trend_label_loan_portfolio_trend_16637d4f",
    "placeholder": "Loan Portfolio Trend",
    "get_by_text": "Loan Portfolio Trend",
    "intent": "loan_portfolio_trend",
    "ocr_type": "label",
    "element_id": "ec19b4f9-6cd7-432b-a516-b6b6a804b28a",
    "external": false
  },
  {
    "placeholder": "Monthly loan disbursements over the last 6 months",
    "dom_matched": false,
    "unique_name": "dashboard_monthly_loan_disbursements_over_the_last_6_months_label_loan_portfolio_description_179404d2",
    "element_id": "eefdc81a-f3bb-4988-a13b-c59f1516172e",
    "page_name": "dashboard",
    "external": false,
    "ocr_type": "label",
    "type": "ocr",
    "intent": "loan_portfolio_description",
    "get_by_text": "Monthly loan disbursements over the last 6 months",
    "label_text": "Monthly loan disbursements over the last 6 months"
  },
  {
    "external": false,
    "element_id": "566f2f07-8d6c-4eb4-814d-fe9ff1ef96b5",
    "placeholder": "Customer Distribution",
    "unique_name": "dashboard_customer_distribution_label_customer_distribution_28babd8d",
    "label_text": "Customer Distribution",
    "page_name": "dashboard",
    "ocr_type": "label",
    "dom_matched": false,
    "type": "ocr",
    "get_by_text": "Customer Distribution",
    "intent": "customer_distribution"
  },
  {
    "intent": "customer_distribution_description",
    "ocr_type": "label",
    "external": false,
    "placeholder": "Customer segments by account type",
    "type": "ocr",
    "unique_name": "dashboard_customer_segments_by_account_type_label_customer_distribution_description_6bb14ee4",
    "label_text": "Customer segments by account type",
    "get_by_text": "Customer segments by account type",
    "dom_matched": false,
    "element_id": "94543a4a-3be0-4ac3-a63a-ee736da203fc",
    "page_name": "dashboard"
  },
  {
    "ocr_type": "label",
    "label_text": "Recent Activities",
    "dom_matched": false,
    "placeholder": "Recent Activities",
    "external": false,
    "get_by_text": "Recent Activities",
    "unique_name": "dashboard_recent_activities_label_recent_activities_cdc77597",
    "page_name": "dashboard",
    "intent": "recent_activities",
    "type": "ocr",
    "element_id": "26e6f30a-7516-47d0-a717-53551fee8afa"
  },
  {
    "unique_name": "dashboard_latest_customer_interactions_and_transactions_label_recent_activities_description_425a612e",
    "get_by_text": "Latest customer interactions and transactions",
    "ocr_type": "label",
    "element_id": "29b524a5-ef27-424d-96a0-3eb05eca8822",
    "placeholder": "Latest customer interactions and transactions",
    "dom_matched": false,
    "external": false,
    "intent": "recent_activities_description",
    "page_name": "dashboard",
    "type": "ocr",
    "label_text": "Latest customer interactions and transactions"
  },
  {
    "type": "ocr",
    "unique_name": "dashboard_sarah_johnson_label_recent_activity_user_83be4551",
    "external": false,
    "ocr_type": "label",
    "placeholder": "Sarah Johnson",
    "page_name": "dashboard",
    "intent": "recent_activity_user",
    "label_text": "Sarah Johnson",
    "get_by_text": "Sarah Johnson",
    "element_id": "bddd6c63-04b8-4717-8491-dbabe64e25f8",
    "dom_matched": false
  },
  {
    "unique_name": "dashboard_loan_application_approved_label_recent_activity_description_9696f002",
    "placeholder": "Loan Application Approved",
    "external": false,
    "ocr_type": "label",
    "label_text": "Loan Application Approved",
    "dom_matched": false,
    "get_by_text": "Loan Application Approved",
    "intent": "recent_activity_description",
    "page_name": "dashboard",
    "element_id": "35266659-f7d9-4615-9809-27e668a40a11",
    "type": "ocr"
  },
  {
    "type": "ocr",
    "ocr_type": "label",
    "placeholder": "Michael Chen",
    "element_id": "df350293-b561-48df-9bc0-eda7b8524834",
    "label_text": "Michael Chen",
    "page_name": "dashboard",
    "unique_name": "dashboard_michael_chen_label_recent_activity_user_70395558",
    "get_by_text": "Michael Chen",
    "intent": "recent_activity_user",
    "dom_matched": false,
    "external": false
  },
  {
    "ocr_type": "label",
    "page_name": "dashboard",
    "external": false,
    "element_id": "261701b8-bd45-41e6-be98-7a5ee237c90e",
    "type": "ocr",
    "unique_name": "dashboard_label_recent_activity_description_e2ee0ccc",
    "dom_matched": false,
    "intent": "recent_activity_description",
    "placeholder": "",
    "get_by_text": "",
    "label_text": ""
  },
  {
    "get_by_text": "$250,000",
    "page_name": "dashboard",
    "type": "ocr",
    "dom_matched": false,
    "element_id": "995a1d10-05d2-4914-92f9-b5a6ca372ed6",
    "label_text": "$250,000",
    "placeholder": "$250,000",
    "ocr_type": "label",
    "intent": "recent_activity_value",
    "unique_name": "dashboard_$250,000_label_recent_activity_value_91add15c",
    "external": false
  },
  {
    "type": "ocr",
    "ocr_type": "label",
    "external": false,
    "element_id": "01a5cc09-ce60-4f55-9e92-e4c4494bc834",
    "placeholder": "Edit with",
    "intent": "edit_tool",
    "get_by_text": "Edit with",
    "label_text": "Edit with",
    "dom_matched": false,
    "page_name": "dashboard",
    "unique_name": "dashboard_edit_with_label_edit_tool_e1025d09"
  },
  {
    "ocr_type": "button",
    "external": false,
    "get_by_text": "Lovable",
    "label_text": "Lovable",
    "type": "ocr",
    "element_id": "50a898e4-51bc-42c4-82d9-7b038a0bf40e",
    "dom_matched": false,
    "intent": "edit_tool",
    "unique_name": "dashboard_lovable_button_edit_tool_2de51406",
    "page_name": "dashboard",
    "placeholder": "Lovable"
  },
  {
    "unique_name": "customers_button_navigation_6ab61bef",
    "external": false,
    "placeholder": "",
    "page_name": "customers",
    "element_id": "38657081-c699-44a6-ab88-0f10f54c0593",
    "dom_matched": false,
    "get_by_text": "",
    "type": "ocr",
    "label_text": "",
    "intent": "navigation",
    "ocr_type": "button"
  },
  {
    "get_by_text": "Dashboard",
    "ocr_type": "button",
    "page_name": "customers",
    "label_text": "Dashboard",
    "element_id": "7c70ce16-c61f-4d53-b57c-72849ffb0c78",
    "external": false,
    "intent": "navigation",
    "unique_name": "customers_dashboard_button_navigation_fb22376c",
    "type": "ocr",
    "dom_matched": false,
    "placeholder": "Dashboard"
  },
  {
    "intent": "navigation",
    "get_by_text": "Customers",
    "type": "ocr",
    "unique_name": "customers_customers_button_navigation_62cd2bf8",
    "element_id": "7695cca0-6637-4653-8803-35dac62b7e05",
    "label_text": "Customers",
    "placeholder": "Customers",
    "page_name": "customers",
    "ocr_type": "button",
    "external": false,
    "dom_matched": false
  },
  {
    "dom_matched": false,
    "external": false,
    "placeholder": "Loans",
    "type": "ocr",
    "ocr_type": "button",
    "label_text": "Loans",
    "element_id": "257efc0d-1658-41d9-9616-cdb735df4d96",
    "page_name": "customers",
    "unique_name": "customers_loans_button_navigation_f083cd47",
    "intent": "navigation",
    "get_by_text": "Loans"
  },
  {
    "get_by_text": "Transactions",
    "element_id": "387617de-1fb7-4fcc-b5b0-6a2c7c75af8f",
    "intent": "navigation",
    "dom_matched": false,
    "ocr_type": "button",
    "unique_name": "customers_transactions_button_navigation_bb833203",
    "label_text": "Transactions",
    "type": "ocr",
    "external": false,
    "placeholder": "Transactions",
    "page_name": "customers"
  },
  {
    "intent": "navigation",
    "get_by_text": "Tasks",
    "placeholder": "Tasks",
    "label_text": "Tasks",
    "type": "ocr",
    "unique_name": "customers_tasks_button_navigation_63e52ff9",
    "ocr_type": "button",
    "dom_matched": false,
    "external": false,
    "page_name": "customers",
    "element_id": "0c1b8c7b-c218-44e9-929a-659bf6d860bf"
  },
  {
    "dom_matched": false,
    "ocr_type": "button",
    "external": false,
    "element_id": "5d451e44-64af-4b69-afa5-1c33eb979bb7",
    "get_by_text": "Reports",
    "label_text": "Reports",
    "intent": "navigation",
    "placeholder": "Reports",
    "unique_name": "customers_reports_button_navigation_1dc35b9f",
    "page_name": "customers",
    "type": "ocr"
  },
  {
    "dom_matched": false,
    "element_id": "c5c02338-6b39-454e-b0c1-36f8a6075803",
    "type": "ocr",
    "ocr_type": "button",
    "unique_name": "customers_analytics_button_navigation_8227d101",
    "get_by_text": "Analytics",
    "external": false,
    "intent": "navigation",
    "label_text": "Analytics",
    "page_name": "customers",
    "placeholder": "Analytics"
  },
  {
    "intent": "navigation",
    "unique_name": "customers_settings_button_navigation_9de99b8a",
    "page_name": "customers",
    "external": false,
    "dom_matched": false,
    "label_text": "Settings",
    "placeholder": "Settings",
    "element_id": "715a03a7-141c-42a9-bf3c-c658a1375db2",
    "get_by_text": "Settings",
    "type": "ocr",
    "ocr_type": "button"
  },
  {
    "external": false,
    "type": "ocr",
    "get_by_text": "Search customers, loans, transactions...",
    "page_name": "customers",
    "unique_name": "customers_search_customers,_loans,_transactions..._textbox_search_be73039f",
    "label_text": "Search customers, loans, transactions...",
    "intent": "search",
    "element_id": "7105e58b-74dd-40f0-9a30-58ee5246da4e",
    "placeholder": "Search customers, loans, transactions...",
    "dom_matched": false,
    "ocr_type": "textbox"
  },
  {
    "intent": "header",
    "label_text": "Customers",
    "page_name": "customers",
    "type": "ocr",
    "placeholder": "Customers",
    "unique_name": "customers_customers_label_header_ab76000b",
    "external": false,
    "ocr_type": "label",
    "dom_matched": false,
    "element_id": "40c845b5-8970-4593-bf8d-2673a8dbabfc",
    "get_by_text": "Customers"
  },
  {
    "ocr_type": "label",
    "dom_matched": false,
    "get_by_text": "Manage your customer relationships and accounts",
    "external": false,
    "intent": "subheader",
    "placeholder": "Manage your customer relationships and accounts",
    "page_name": "customers",
    "element_id": "12637cc5-45e3-42f0-8814-324597a00630",
    "unique_name": "customers_manage_your_customer_relationships_and_accounts_label_subheader_e7e5084f",
    "label_text": "Manage your customer relationships and accounts",
    "type": "ocr"
  },
  {
    "get_by_text": "Search customers...",
    "type": "ocr",
    "external": false,
    "element_id": "9675a87f-02e2-40ac-8474-c57ecc71c158",
    "dom_matched": false,
    "ocr_type": "textbox",
    "placeholder": "Search customers...",
    "label_text": "Search customers...",
    "unique_name": "customers_search_customers..._textbox_search_85d3ce1f",
    "intent": "search",
    "page_name": "customers"
  },
  {
    "type": "ocr",
    "page_name": "customers",
    "label_text": "Filters",
    "unique_name": "customers_filters_button_filter_4c0a3d63",
    "placeholder": "Filters",
    "get_by_text": "Filters",
    "intent": "filter",
    "ocr_type": "button",
    "external": false,
    "dom_matched": false,
    "element_id": "1d9037d4-c8c8-400e-b98a-c998c576c443"
  },
  {
    "dom_matched": false,
    "unique_name": "customers_customer_list_label_section_header_93cd1f20",
    "type": "ocr",
    "placeholder": "Customer List",
    "ocr_type": "label",
    "label_text": "Customer List",
    "element_id": "eff3c1dd-6717-4f43-b625-b1f64dc2003a",
    "external": false,
    "get_by_text": "Customer List",
    "page_name": "customers",
    "intent": "section_header"
  },
  {
    "placeholder": "3 customers found",
    "type": "ocr",
    "label_text": "3 customers found",
    "unique_name": "customers_3_customers_found_label_info_61b9a471",
    "element_id": "33619458-ffbe-47ed-8685-527bbe9514cf",
    "page_name": "customers",
    "dom_matched": false,
    "get_by_text": "3 customers found",
    "intent": "info",
    "external": false,
    "ocr_type": "label"
  },
  {
    "dom_matched": false,
    "page_name": "customers",
    "intent": "column_header",
    "type": "ocr",
    "placeholder": "Customer",
    "get_by_text": "Customer",
    "element_id": "402309d6-48b7-4854-b40e-d45cb9feee7a",
    "ocr_type": "label",
    "unique_name": "customers_customer_label_column_header_cd74c3eb",
    "label_text": "Customer",
    "external": false
  },
  {
    "label_text": "Account Type",
    "element_id": "e32b6975-ef80-4288-9ea6-85684f58a442",
    "ocr_type": "label",
    "get_by_text": "Account Type",
    "external": false,
    "page_name": "customers",
    "type": "ocr",
    "dom_matched": false,
    "intent": "column_header",
    "placeholder": "Account Type",
    "unique_name": "customers_account_type_label_column_header_a712d19c"
  },
  {
    "element_id": "416dec62-6344-4748-9b84-6f9bbf3cd6e6",
    "ocr_type": "label",
    "intent": "column_header",
    "unique_name": "customers_balance_label_column_header_d6648fd2",
    "page_name": "customers",
    "label_text": "Balance",
    "dom_matched": false,
    "external": false,
    "type": "ocr",
    "get_by_text": "Balance",
    "placeholder": "Balance"
  },
  {
    "intent": "column_header",
    "page_name": "customers",
    "external": false,
    "placeholder": "Status",
    "type": "ocr",
    "get_by_text": "Status",
    "dom_matched": false,
    "unique_name": "customers_status_label_column_header_57a06b20",
    "label_text": "Status",
    "element_id": "0a918660-dc9e-401b-b76c-fd45bb9a7182",
    "ocr_type": "label"
  },
  {
    "type": "ocr",
    "external": false,
    "unique_name": "customers_join_date_label_column_header_cb167d9a",
    "element_id": "3d481146-cb25-4159-a796-27d57ea12ad8",
    "dom_matched": false,
    "ocr_type": "label",
    "label_text": "Join Date",
    "intent": "column_header",
    "page_name": "customers",
    "get_by_text": "Join Date",
    "placeholder": "Join Date"
  },
  {
    "page_name": "customers",
    "placeholder": "Actions",
    "type": "ocr",
    "external": false,
    "unique_name": "customers_actions_label_column_header_177ddb69",
    "get_by_text": "Actions",
    "element_id": "045bf295-91b2-49b6-b36d-ec85dff9ff93",
    "dom_matched": false,
    "ocr_type": "label",
    "intent": "column_header",
    "label_text": "Actions"
  },
  {
    "placeholder": "Sarah Johnson",
    "element_id": "de35605e-d0b9-4489-b47a-942b5b464ca0",
    "page_name": "customers",
    "type": "ocr",
    "external": false,
    "dom_matched": false,
    "unique_name": "customers_sarah_johnson_label_customer_name_91134cc9",
    "get_by_text": "Sarah Johnson",
    "label_text": "Sarah Johnson",
    "intent": "customer_name",
    "ocr_type": "label"
  },
  {
    "intent": "customer_email",
    "type": "ocr",
    "ocr_type": "label",
    "get_by_text": "sarah.johnson@email.com",
    "page_name": "customers",
    "unique_name": "customers_sarah.johnson@email.com_label_customer_email_ea79968a",
    "dom_matched": false,
    "placeholder": "sarah.johnson@email.com",
    "element_id": "29e97aac-53bf-474a-bc7c-3d96431bd189",
    "label_text": "sarah.johnson@email.com",
    "external": false
  },
  {
    "element_id": "b13f458a-8d84-4ea6-8763-2031599b7a88",
    "unique_name": "customers_premium_label_account_type_c1ae4279",
    "label_text": "Premium",
    "ocr_type": "label",
    "page_name": "customers",
    "get_by_text": "Premium",
    "type": "ocr",
    "external": false,
    "placeholder": "Premium",
    "intent": "account_type",
    "dom_matched": false
  },
  {
    "element_id": "bbbf68ac-5e0a-4a30-8f63-168e90940fa3",
    "unique_name": "customers_$1,45,000_label_balance_dc74e6a8",
    "placeholder": "$1,45,000",
    "type": "ocr",
    "intent": "balance",
    "get_by_text": "$1,45,000",
    "label_text": "$1,45,000",
    "page_name": "customers",
    "ocr_type": "label",
    "external": false,
    "dom_matched": false
  },
  {
    "ocr_type": "label",
    "intent": "status",
    "label_text": "Active",
    "type": "ocr",
    "element_id": "aa089598-7d33-4557-8748-804c1065deb3",
    "placeholder": "Active",
    "unique_name": "customers_active_label_status_5fc1bbb1",
    "page_name": "customers",
    "external": false,
    "dom_matched": false,
    "get_by_text": "Active"
  },
  {
    "unique_name": "customers_2023-01-15_label_join_date_13b4a3e0",
    "placeholder": "2023-01-15",
    "get_by_text": "2023-01-15",
    "type": "ocr",
    "external": false,
    "page_name": "customers",
    "ocr_type": "label",
    "dom_matched": false,
    "label_text": "2023-01-15",
    "intent": "join_date",
    "element_id": "98ea9a03-dfc9-45b2-a1d8-7197a3f73067"
  },
  {
    "get_by_text": "",
    "type": "ocr",
    "label_text": "",
    "dom_matched": false,
    "placeholder": "",
    "unique_name": "customers_button_view_action_cc60ce91",
    "page_name": "customers",
    "ocr_type": "button",
    "external": false,
    "element_id": "3530b22b-4b27-40ed-8c8c-36b4191b6990",
    "intent": "view_action"
  },
  {
    "dom_matched": false,
    "page_name": "customers",
    "element_id": "10c0c6b4-6bd0-4fc2-b751-5a623dda8f79",
    "unique_name": "customers_button_edit_action_d3d0df61",
    "type": "ocr",
    "external": false,
    "get_by_text": "",
    "placeholder": "",
    "intent": "edit_action",
    "ocr_type": "button",
    "label_text": ""
  },
  {
    "type": "ocr",
    "external": false,
    "get_by_text": "Michael Chen",
    "ocr_type": "label",
    "unique_name": "customers_michael_chen_label_customer_name_8dbd8345",
    "element_id": "e65dd83c-241c-41b5-b5a9-ed5165e974da",
    "placeholder": "Michael Chen",
    "page_name": "customers",
    "label_text": "Michael Chen",
    "dom_matched": false,
    "intent": "customer_name"
  },
  {
    "ocr_type": "label",
    "placeholder": "michael.chen@email.com",
    "label_text": "michael.chen@email.com",
    "page_name": "customers",
    "intent": "customer_email",
    "element_id": "8d4ba95e-d5b3-46d2-9f85-0abe1d65945f",
    "type": "ocr",
    "external": false,
    "dom_matched": false,
    "get_by_text": "michael.chen@email.com",
    "unique_name": "customers_michael.chen@email.com_label_customer_email_8f50f16b"
  },
  {
    "intent": "account_type",
    "page_name": "customers",
    "label_text": "Standard",
    "type": "ocr",
    "external": false,
    "placeholder": "Standard",
    "ocr_type": "label",
    "element_id": "a643f356-2cf1-44ed-835f-85dd1cb62402",
    "unique_name": "customers_standard_label_account_type_ef9be216",
    "dom_matched": false,
    "get_by_text": "Standard"
  },
  {
    "external": false,
    "dom_matched": false,
    "element_id": "df13ee85-1d3b-494b-9e54-27d4a8375f38",
    "placeholder": "$52,000",
    "unique_name": "customers_$52,000_label_balance_b6e2bd67",
    "type": "ocr",
    "page_name": "customers",
    "ocr_type": "label",
    "intent": "balance",
    "label_text": "$52,000",
    "get_by_text": "$52,000"
  },
  {
    "external": false,
    "unique_name": "customers_2023-03-22_label_join_date_363240e3",
    "dom_matched": false,
    "get_by_text": "2023-03-22",
    "ocr_type": "label",
    "type": "ocr",
    "intent": "join_date",
    "element_id": "5988d487-3cb4-4859-97e4-bc403115037e",
    "label_text": "2023-03-22",
    "placeholder": "2023-03-22",
    "page_name": "customers"
  },
  {
    "intent": "customer_name",
    "unique_name": "customers_emma_davis_label_customer_name_671b9ccd",
    "type": "ocr",
    "element_id": "e72a7f93-47e0-49ae-b7ea-b598c4626734",
    "ocr_type": "label",
    "get_by_text": "Emma Davis",
    "external": false,
    "placeholder": "Emma Davis",
    "dom_matched": false,
    "page_name": "customers",
    "label_text": "Emma Davis"
  },
  {
    "intent": "customer_email",
    "ocr_type": "label",
    "unique_name": "customers_emma.davis@email.com_label_customer_email_1680f20b",
    "type": "ocr",
    "placeholder": "emma.davis@email.com",
    "dom_matched": false,
    "label_text": "emma.davis@email.com",
    "element_id": "80627a11-a898-4ba8-8b1e-f6ed9788a791",
    "get_by_text": "emma.davis@email.com",
    "page_name": "customers",
    "external": false
  },
  {
    "dom_matched": false,
    "page_name": "customers",
    "unique_name": "customers_$89,000_label_balance_f3422319",
    "intent": "balance",
    "external": false,
    "label_text": "$89,000",
    "element_id": "62c9875c-f7fb-452f-b16f-92beb73b460c",
    "type": "ocr",
    "ocr_type": "label",
    "placeholder": "$89,000",
    "get_by_text": "$89,000"
  },
  {
    "intent": "join_date",
    "ocr_type": "label",
    "placeholder": "2022-11-08",
    "unique_name": "customers_2022-11-08_label_join_date_bcd7c000",
    "type": "ocr",
    "get_by_text": "2022-11-08",
    "element_id": "bbce3c3b-1ea4-4fd5-b9e6-6b70bdbb2f88",
    "label_text": "2022-11-08",
    "dom_matched": false,
    "page_name": "customers",
    "external": false
  },
  {
    "ocr_type": "button",
    "unique_name": "customers_export_button_export_ec306f18",
    "get_by_text": "Export",
    "intent": "export",
    "element_id": "8b718123-3555-41a3-b5b5-e784c99a698d",
    "dom_matched": false,
    "label_text": "Export",
    "placeholder": "Export",
    "page_name": "customers",
    "external": false,
    "type": "ocr"
  },
  {
    "external": false,
    "type": "ocr",
    "intent": "add_customer",
    "label_text": "New Customer",
    "get_by_text": "New Customer",
    "element_id": "6461e89d-cf66-4832-a8ea-d9761a631529",
    "dom_matched": false,
    "placeholder": "New Customer",
    "ocr_type": "button",
    "unique_name": "customers_new_customer_button_add_customer_33383326",
    "page_name": "customers"
  },
  {
    "intent": "footer",
    "dom_matched": false,
    "element_id": "632cc2eb-760f-4589-941f-5fe5665afdb2",
    "type": "ocr",
    "ocr_type": "label",
    "get_by_text": "Edit with",
    "unique_name": "customers_edit_with_label_footer_ca0fec1e",
    "page_name": "customers",
    "external": false,
    "placeholder": "Edit with",
    "label_text": "Edit with"
  },
  {
    "element_id": "076ae535-1ec4-4d8e-ac1b-aaa6ad79f1d3",
    "intent": "footer_brand",
    "dom_matched": false,
    "page_name": "customers",
    "get_by_text": "Lovable",
    "external": false,
    "unique_name": "customers_lovable_label_footer_brand_301dffac",
    "ocr_type": "label",
    "placeholder": "Lovable",
    "label_text": "Lovable",
    "type": "ocr"
  },
  {
    "ocr_type": "label",
    "dom_matched": false,
    "intent": "form_title",
    "page_name": "customers",
    "unique_name": "customers_add_new_customer_label_form_title_2b3b0780",
    "get_by_text": "Add New Customer",
    "element_id": "95bf0180-6790-4215-91b5-f687892ec5fd",
    "type": "ocr",
    "label_text": "Add New Customer",
    "placeholder": "Add New Customer",
    "external": false
  },
  {
    "external": false,
    "type": "ocr",
    "get_by_text": "Enter the customer details to create a new account.",
    "ocr_type": "label",
    "page_name": "customers",
    "unique_name": "customers_enter_the_customer_details_to_create_a_new_account._label_form_instruction_4e368c65",
    "intent": "form_instruction",
    "placeholder": "Enter the customer details to create a new account.",
    "label_text": "Enter the customer details to create a new account.",
    "element_id": "1ae4070a-51bc-4a91-98fa-a080f1141adb",
    "dom_matched": false
  },
  {
    "dom_matched": false,
    "type": "ocr",
    "label_text": "Full Name",
    "external": false,
    "element_id": "7563fa40-7908-413b-8842-5a205b83fbb0",
    "placeholder": "Full Name",
    "page_name": "customers",
    "get_by_text": "Full Name",
    "unique_name": "customers_full_name_label_full_name_label_7fa7eb35",
    "intent": "full_name_label",
    "ocr_type": "label"
  },
  {
    "type": "ocr",
    "get_by_text": "",
    "label_text": "",
    "page_name": "customers",
    "intent": "full_name_input",
    "ocr_type": "textbox",
    "element_id": "4fc76c41-e666-4be8-bdfd-434f0120ad48",
    "unique_name": "customers_textbox_full_name_input_b5555c13",
    "placeholder": "",
    "external": false,
    "dom_matched": false
  },
  {
    "ocr_type": "label",
    "intent": "email_label",
    "type": "ocr",
    "unique_name": "customers_email_label_email_label_1e22d7f0",
    "element_id": "c5b03e6c-7ece-4075-ac3f-8fd0f3e641f7",
    "get_by_text": "Email",
    "label_text": "Email",
    "dom_matched": false,
    "external": false,
    "page_name": "customers",
    "placeholder": "Email"
  },
  {
    "intent": "email_input",
    "label_text": "",
    "get_by_text": "",
    "placeholder": "",
    "unique_name": "customers_textbox_email_input_b7f01675",
    "ocr_type": "textbox",
    "page_name": "customers",
    "type": "ocr",
    "external": false,
    "element_id": "f120a144-ff93-416c-91dc-6af41aa86bb6",
    "dom_matched": false
  },
  {
    "ocr_type": "label",
    "label_text": "Phone Number",
    "placeholder": "Phone Number",
    "external": false,
    "dom_matched": false,
    "element_id": "d146407e-2129-4572-8e7c-bfecdc8f619a",
    "get_by_text": "Phone Number",
    "page_name": "customers",
    "intent": "phone_number_label",
    "type": "ocr",
    "unique_name": "customers_phone_number_label_phone_number_label_03e465fd"
  },
  {
    "ocr_type": "textbox",
    "intent": "phone_number_input",
    "type": "ocr",
    "get_by_text": "",
    "external": false,
    "placeholder": "",
    "unique_name": "customers_textbox_phone_number_input_bb72a72b",
    "element_id": "b6b33ed1-7a9a-4819-955b-c7a58242cc7e",
    "dom_matched": false,
    "page_name": "customers",
    "label_text": ""
  },
  {
    "external": false,
    "ocr_type": "label",
    "label_text": "Account Type",
    "placeholder": "Account Type",
    "get_by_text": "Account Type",
    "type": "ocr",
    "unique_name": "customers_account_type_label_account_type_label_a1b76de7",
    "intent": "account_type_label",
    "dom_matched": false,
    "page_name": "customers",
    "element_id": "1b06e63a-6e85-49f0-81b1-5cf05a84cb54"
  },
  {
    "label_text": "Select account type",
    "unique_name": "customers_select_account_type_select_account_type_select_739bf8ef",
    "external": false,
    "get_by_text": "Select account type",
    "placeholder": "Select account type",
    "ocr_type": "select",
    "page_name": "customers",
    "intent": "account_type_select",
    "element_id": "83de4a69-5821-4d05-8918-c11403dece47",
    "type": "ocr",
    "dom_matched": false
  },
  {
    "page_name": "customers",
    "get_by_text": "Address",
    "dom_matched": false,
    "external": false,
    "element_id": "23679824-8cbe-4cd7-bc8e-9e60a319a45f",
    "intent": "address_label",
    "type": "ocr",
    "ocr_type": "label",
    "label_text": "Address",
    "unique_name": "customers_address_label_address_label_bfa99020",
    "placeholder": "Address"
  },
  {
    "external": false,
    "placeholder": "",
    "dom_matched": false,
    "ocr_type": "textbox",
    "page_name": "customers",
    "type": "ocr",
    "unique_name": "customers_textbox_address_input_0da1bba0",
    "intent": "address_input",
    "get_by_text": "",
    "label_text": "",
    "element_id": "22921c87-15c6-4cbf-a35a-42ce97a26fcb"
  },
  {
    "element_id": "3c0da3bc-1298-40e7-8cf9-b78acd1d2c6d",
    "page_name": "customers",
    "placeholder": "Occupation",
    "get_by_text": "Occupation",
    "intent": "occupation_label",
    "external": false,
    "type": "ocr",
    "unique_name": "customers_occupation_label_occupation_label_78041ebe",
    "dom_matched": false,
    "ocr_type": "label",
    "label_text": "Occupation"
  },
  {
    "unique_name": "customers_textbox_occupation_input_7c88216e",
    "dom_matched": false,
    "label_text": "",
    "page_name": "customers",
    "placeholder": "",
    "get_by_text": "",
    "element_id": "14bde66a-1b44-45b4-9e19-9883caf63b1d",
    "type": "ocr",
    "ocr_type": "textbox",
    "external": false,
    "intent": "occupation_input"
  },
  {
    "ocr_type": "label",
    "label_text": "Annual Income",
    "external": false,
    "intent": "annual_income_label",
    "get_by_text": "Annual Income",
    "dom_matched": false,
    "type": "ocr",
    "unique_name": "customers_annual_income_label_annual_income_label_41327b0b",
    "element_id": "a072d846-062f-47ae-b0df-f77d359425ff",
    "page_name": "customers",
    "placeholder": "Annual Income"
  },
  {
    "element_id": "9e6119b3-2d6c-4445-ad07-3a0e72a48f71",
    "dom_matched": false,
    "external": false,
    "intent": "annual_income_input",
    "ocr_type": "textbox",
    "unique_name": "customers_textbox_annual_income_input_7b960691",
    "placeholder": "",
    "label_text": "",
    "page_name": "customers",
    "get_by_text": "",
    "type": "ocr"
  },
  {
    "type": "ocr",
    "get_by_text": "Initial Deposit",
    "label_text": "Initial Deposit",
    "placeholder": "Initial Deposit",
    "unique_name": "customers_initial_deposit_label_initial_deposit_label_a98dd99a",
    "page_name": "customers",
    "intent": "initial_deposit_label",
    "element_id": "eff18cd5-3b5d-48a6-ac2d-58b76784ba58",
    "ocr_type": "label",
    "dom_matched": false,
    "external": false
  },
  {
    "ocr_type": "textbox",
    "page_name": "customers",
    "dom_matched": false,
    "get_by_text": "",
    "type": "ocr",
    "intent": "initial_deposit_input",
    "external": false,
    "unique_name": "customers_textbox_initial_deposit_input_842f44e3",
    "label_text": "",
    "element_id": "94288828-20cd-438f-85b1-8970413e0a2b",
    "placeholder": ""
  },
  {
    "page_name": "customers",
    "element_id": "b13ea0e7-0235-41be-842d-5b83fb617804",
    "placeholder": "Cancel",
    "dom_matched": false,
    "intent": "cancel",
    "ocr_type": "button",
    "get_by_text": "Cancel",
    "external": false,
    "label_text": "Cancel",
    "unique_name": "customers_cancel_button_cancel_71a3913d",
    "type": "ocr"
  },
  {
    "external": false,
    "get_by_text": "Add Customer",
    "dom_matched": false,
    "label_text": "Add Customer",
    "unique_name": "customers_add_customer_button_submit_bce56d38",
    "type": "ocr",
    "intent": "submit",
    "page_name": "customers",
    "element_id": "a4c9805f-fad4-42ca-b8e6-d9235a0ebafa",
    "placeholder": "Add Customer",
    "ocr_type": "button"
  }
]


# === FILE: generated_runs\src\pages\base_page.py ===
from services.page_enricher import enrich_page

class BasePage:
    enriched_pages = set()

    def __init__(self, page, page_name, url=None):
        self.page = page
        self.page_name = page_name
        self.url = url

    async def goto(self):
        if self.url:
            await self.page.goto(self.url)
        else:
            raise ValueError(f"URL not set for {self.page_name}")

    async def enrich_once(self, force=False):
        if force or self.page_name not in BasePage.enriched_pages:
            await enrich_page(self.page, self.page_name)  # DOM enrichment clearly triggered
            BasePage.enriched_pages.add(self.page_name)
            print(f"🌟 Enriched page: {self.page_name}")
        else:
            print(f"✅ Already enriched: {self.page_name}")



# === FILE: generated_runs\src\pages\customers_page.py ===
import asyncio
from services.page_enricher import enrich_page
from utils.enrichment_status import is_enriched




from .base_page import BasePage

class CustomersPage(BasePage):
    def __init__(self, playwright_page):
        self.page = playwright_page
        self.page_name = "customers"
        self._enriched = False

    async def click_dashboard(self):
        await self._enrich_if_needed()
        await self.page.smartAI('customers_dashboard_button_navigation_fb22376c').click()

    async def click_customers(self):
        await self._enrich_if_needed()
        await self.page.smartAI('customers_customers_button_navigation_62cd2bf8').click()

    async def click_loans(self):
        await self._enrich_if_needed()
        await self.page.smartAI('customers_loans_button_navigation_f083cd47').click()

    async def click_transactions(self):
        await self._enrich_if_needed()
        await self.page.smartAI('customers_transactions_button_navigation_bb833203').click()

    async def click_tasks(self):
        await self._enrich_if_needed()
        await self.page.smartAI('customers_tasks_button_navigation_63e52ff9').click()

    async def click_reports(self):
        await self._enrich_if_needed()
        await self.page.smartAI('customers_reports_button_navigation_1dc35b9f').click()

    async def click_analytics(self):
        await self._enrich_if_needed()
        await self.page.smartAI('customers_analytics_button_navigation_8227d101').click()

    async def click_settings(self):
        await self._enrich_if_needed()
        await self.page.smartAI('customers_settings_button_navigation_9de99b8a').click()

    async def enter_search_customers_loans_transactions(self, value):
        await self._enrich_if_needed()
        await self.page.smartAI('customers_search_customers,_loans,_transactions..._textbox_search_be73039f').fill(value)

    async def enter_search_customers(self, value):
        await self._enrich_if_needed()
        await self.page.smartAI('customers_search_customers..._textbox_search_85d3ce1f').fill(value)

    async def click_filters(self):
        await self._enrich_if_needed()
        await self.page.smartAI('customers_filters_button_filter_4c0a3d63').click()

    async def click_view_action(self):
        await self._enrich_if_needed()
        await self.page.smartAI('customers_button_view_action_cc60ce91').click()

    async def click_edit_action(self):
        await self._enrich_if_needed()
        await self.page.smartAI('customers_button_edit_action_d3d0df61').click()

    async def click_export(self):
        await self._enrich_if_needed()
        await self.page.smartAI('customers_export_button_export_ec306f18').click()

    async def click_new_customer(self):
        await self._enrich_if_needed()
        await self.page.smartAI('customers_new_customer_button_add_customer_33383326').click()

    async def enter_full_name_input(self, value):
        await self._enrich_if_needed()
        await self.page.smartAI('customers_textbox_full_name_input_b5555c13').fill(value)

    async def enter_email_input(self, value):
        await self._enrich_if_needed()
        await self.page.smartAI('customers_textbox_email_input_b7f01675').fill(value)

    async def enter_phone_number_input(self, value):
        await self._enrich_if_needed()
        await self.page.smartAI('customers_textbox_phone_number_input_bb72a72b').fill(value)

    async def select_select_account_type(self, value):
        await self._enrich_if_needed()
        await self.page.smartAI('customers_select_account_type_select_account_type_select_739bf8ef').select_option(value)

    async def enter_address_input(self, value):
        await self._enrich_if_needed()
        await self.page.smartAI('customers_textbox_address_input_0da1bba0').fill(value)

    async def enter_occupation_input(self, value):
        await self._enrich_if_needed()
        await self.page.smartAI('customers_textbox_occupation_input_7c88216e').fill(value)

    async def enter_annual_income_input(self, value):
        await self._enrich_if_needed()
        await self.page.smartAI('customers_textbox_annual_income_input_7b960691').fill(value)

    async def enter_initial_deposit_input(self, value):
        await self._enrich_if_needed()
        await self.page.smartAI('customers_textbox_initial_deposit_input_842f44e3').fill(value)

    async def click_cancel(self):
        await self._enrich_if_needed()
        await self.page.smartAI('customers_cancel_button_cancel_71a3913d').click()

    async def click_add_customer(self):
        await self._enrich_if_needed()
        await self.page.smartAI('customers_add_customer_button_submit_bce56d38').click()


# === FILE: generated_runs\src\pages\dashboard_page.py ===
import asyncio
from services.page_enricher import enrich_page
from utils.enrichment_status import is_enriched




from .base_page import BasePage

class DashboardPage(BasePage):
    def __init__(self, playwright_page):
        self.page = playwright_page
        self.page_name = "dashboard"
        self._enriched = False

    async def enter_search_customers_loans_transactions(self, value):
        await self._enrich_if_needed()
        await self.page.smartAI('dashboard_search_customers,_loans,_transactions..._textbox_search_3310a968').fill(value)

    async def click_dashboard(self):
        await self._enrich_if_needed()
        await self.page.smartAI('dashboard_dashboard_button_navigation_83914516').click()

    async def click_customers(self):
        await self._enrich_if_needed()
        await self.page.smartAI('dashboard_customers_button_navigation_bb4303b6').click()

    async def click_loans(self):
        await self._enrich_if_needed()
        await self.page.smartAI('dashboard_loans_button_navigation_42436e2a').click()

    async def click_transactions(self):
        await self._enrich_if_needed()
        await self.page.smartAI('dashboard_transactions_button_navigation_f0479a72').click()

    async def click_tasks(self):
        await self._enrich_if_needed()
        await self.page.smartAI('dashboard_tasks_button_navigation_cde2a4d6').click()

    async def click_reports(self):
        await self._enrich_if_needed()
        await self.page.smartAI('dashboard_reports_button_navigation_578fb659').click()

    async def click_analytics(self):
        await self._enrich_if_needed()
        await self.page.smartAI('dashboard_analytics_button_navigation_49884ab5').click()

    async def click_settings(self):
        await self._enrich_if_needed()
        await self.page.smartAI('dashboard_settings_button_navigation_7a36fd5d').click()

    async def click_export_report(self):
        await self._enrich_if_needed()
        await self.page.smartAI('dashboard_export_report_button_export_ed26f6d4').click()

    async def click_lovable(self):
        await self._enrich_if_needed()
        await self.page.smartAI('dashboard_lovable_button_edit_tool_2de51406').click()


# === FILE: generated_runs\src\pages\__init__.py ===



# === FILE: generated_runs\src\tests\conftest.py ===
import pytest
import json
from pathlib import Path
from lib.smart_ai import patch_page_with_smartai

@pytest.fixture(autouse=True)
def smartai_page(page):    
    metadata_path = (Path(__file__).parent.parent / "metadata" / "after_enrichment.json").resolve()
    with open(metadata_path, "r") as f:
        actual_metadata = json.load(f)
    patch_page_with_smartai(page, actual_metadata)
    return page


# === FILE: generated_runs\src\tests\test_1.py ===
from pages.base_page import BasePage

from pages.customers_page import CustomersPage

from pages.dashboard_page import DashboardPage

import pytest
@pytest.mark.asyncio
async def test_add_customer(page):
    dashboard_page = DashboardPage(page)
    customers_page = CustomersPage(page)

    await dashboard_page.click_customers()
    await customers_page.click_new_customer()
    await customers_page.enter_full_name_input("John Doe")
    await customers_page.enter_email_input("john.doe@example.com")
    await customers_page.enter_phone_number_input("1234567890")
    await customers_page.select_select_account_type("Standard")
    await customers_page.enter_address_input("123 Main St, Anytown, USA")
    await customers_page.enter_occupation_input("Software Engineer")
    await customers_page.enter_annual_income_input("75000")
    await customers_page.enter_initial_deposit_input("1000")
    await customers_page.click_add_customer()


# === FILE: generated_runs\src\tests\__init__.py ===



# === FILE: logic\image_text_extractor.py ===
# # image_text_extractor.py

# ############################ Open AI Logic for Image API ############################


from PIL import Image
from openai import OpenAI
import os
import base64
import uuid
from dotenv import load_dotenv
import json
from datetime import datetime
import re
from config.settings import DATA_PATH
from utils.file_utils import save_region, build_standard_metadata
from utils.match_utils import normalize_page_name,assign_intent_semantic
from services.chroma_service import upsert_text_record  

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
# OLD PROMPT
# PROMPT = """You are an expert computer vision model using OpenAI's capabilities.

# Your task is to analyze a given screenshot of a user interface (UI) and extract every visible UI element, accurately identifying its type and intent.

# 1. Element Extraction:
#    - Extract ALL visible UI text from the image, including:
#      • Input fields 
#      • Buttons
#      • Labels (including credentials, instructions)
#      • Dropdowns, checkboxes

# 2. Element Classification:
#    - For each element, output:
#      • Label text (exact as visible)
#      • Element type (one of: `textbox`, `button`, `label`, `checkbox`, `select`)
#      • Intent (like: `login`, `username`, `password`, `price_label`, `submit`, `add_to_cart`, `password_info`, `username_info`, etc.)

#    - For credentials or user types like `standard_user`, `secret_sauce`, assign type as `label` and use intent like `username_info`, `password_info`.

# 3. Format:
#    - Each element on its own line:
#      <label text> - <element type> - <intent>

# 4. Rules:
#    - Do NOT rephrase or skip lines.
#    - Preserve punctuation, line breaks.
#    - Traverse from top-left to bottom-right.

# 5. Only output newline-separated lines like:
#    Username - textbox - login
#    Login - button - login
#    secret_sauce - label - password_info
# """

PROMPT = """You are an expert computer vision model using OpenAI's capabilities.

Your task is to analyze a given screenshot of a user interface (UI) and extract every visible UI element, accurately identifying its type and intent.

1. Element Extraction:
   - Extract ALL visible UI text from the image, including:
     • Input fields
     • Buttons
     • Labels (including credentials, instructions)
     • Dropdowns, checkboxes

2. Element Classification:
   - For each element, output:
     • Label text (exact as visible)
     • Element type (one of: `textbox`, `button`, `label`, `checkbox`, `select`)
     • Intent (like: `login`, `username`, `password`, `price_label`, `submit`, `add_to_cart`, `password_info`, `username_info`, etc.)

   - For credentials or user types like `standard_user`, `secret_sauce`, assign type as `label` and use intent like `username_info`, `password_info`.

   - If the UI element appears as part of a vertical or horizontal navigation menu, always classify it as `button` or `link`.
   - If uncertain whether an element is clickable or navigational, prefer classifying it as a `button` over a `label`.

3. Format:
    - Each element on its own line:
    Always give response in the below format:
    Either
        <label_text> - <ocr_type> - <intent> => if label_text present 
    or 
        - <ocr_type> - <intent> => if label_text is empty 

4. Rules:
   - Do NOT rephrase or skip lines.
   - Preserve punctuation, line breaks.
   - Traverse from top-left to bottom-right.

5. Only output newline-separated lines like:
   Username - textbox - login
   Login - button - login
   secret_sauce - label - password_info
   Dashboard - button - navigation

"""

# PROMPT = """You are an expert computer vision model using OpenAI's capabilities.

# Your task is to analyze a given screenshot of a user interface (UI) and extract every visible UI element, accurately identifying its type and intent.

# 1. Element Extraction:
#    - Extract ALL visible UI text from the image, including:
#      • Input fields (textboxes), even if empty
#      • Buttons
#      • Labels (e.g. "Full Name", "Phone Number", etc.)
#      • Dropdowns, checkboxes

#    - For each input-related label, generate a corresponding textbox/select entry even if it has no typed value.

# 2. Element Classification:
#    - For each element, output:
#      • Label text (exact as visible)
#      • Element type (one of: `textbox`, `button`, `label`, `checkbox`, `select`)
#      • Intent — infer from label (e.g. "Full Name" → `fullname`, "Phone Number" → `phonenumber`, "Email" → `email`, etc.). Use lowercase and remove spaces/underscores.

#    - If the element is a textbox, dropdown, or select without filled values, still extract it using the label.

#    - Use generic fallback intent `valueinput` if unsure.

# 3. Format:
#    - Each element on its own line:
#      <label text> - <element type> - <intent>

# 4. Rules:
#    - Do NOT rephrase or skip lines.
#    - Preserve punctuation, line breaks.
#    - Traverse from top-left to bottom-right.
#    - Even if the textbox has no content, generate its label and input as two elements.

# 5. Examples:
#    Full Name - textbox - fullname
#    Email - textbox - email
#    Account Type - select - accounttype
#    Add Customer - button - submit
# """


async def process_image_gpt(
    image: Image.Image,
    filename: str,
    image_path: str = "",
    debug_log_path: str = None
) -> list:
    
    page_name = normalize_page_name(filename)

    # Convert image to base64 for OpenAI Vision API
    with open(image_path, "rb") as f:
        image_base64 = base64.b64encode(f.read()).decode("utf-8")

    # Call OpenAI Vision API with your prompt
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": PROMPT},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_base64}"}}
                ]
            }
        ],
        max_tokens=1500,
        temperature=0
    )

    raw_lines = response.choices[0].message.content.strip().splitlines()
    results = []    
    
    # raw_lines = ...   # (your OpenAI output as a list of strings)
    clean_lines = []
    for line in raw_lines:
        # Remove leading serial numbers (like '1. ')
        line = re.sub(r'^\d+\.\s*', '', line)
        # Remove markdown symbols
        line = re.sub(r'(\*\*|\*|`)', '', line)
        # Count dashes
        dash_count = line.count('-')
        if dash_count > 2:
            # Remove leading dash only if there are at least two ' - '
            line = re.sub(r'^\s*-\s*', '', line)

        clean_lines.append(line)


    # Timestamped file naming
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = os.path.splitext(os.path.basename(filename))[0]
    file_name = f"{timestamp}_{base}.txt"
    folder = "data/openai_response"
    os.makedirs(folder, exist_ok=True)
    out_file = os.path.join(folder, file_name)
    with open(out_file, "w", encoding="utf-8") as f:
        for line in raw_lines:
            f.write(line + "\n")
        f.write(f"{'-'*40} After Cleaning {'-'*40}\n")
        for line in clean_lines:
            f.write(line + "\n")

    # ====================
    for line in clean_lines:
        line = line.strip()
        if not line or " - " not in line:
            continue

        # Always split into parts from right
        parts = line.rsplit(" - ", 2)
        if len(parts) == 3:
            label_text, ocr_type, intent = [p.strip() for p in parts]
            if not intent:
                intent = assign_intent_semantic(label_text)
        elif len(parts) == 2:
            first, second = [p.strip() for p in parts]
            # If the first part is empty or looks like a type (starts with dash), treat accordingly
            if line.startswith("-") or not first:
                label_text = ""
                ocr_type = first.lstrip("-").strip()
                intent = second
            else:
                label_text = first
                ocr_type = second
                intent = assign_intent_semantic(label_text)
        else:
            continue

        # # Handle both 3-part and 2-part formats
        # parts = line.rsplit(" - ", 2)
        # if len(parts) == 3:
        #     label_text, ocr_type, intent = [p.strip() for p in parts]
        #     if not intent:
        #         intent = assign_intent_semantic(label_text)
        # elif len(parts) == 2:
        #     label_text, ocr_type = [p.strip() for p in parts]
        #     intent = assign_intent_semantic(label_text)
        # else:
        #     continue

        unique_id = str(uuid.uuid4())
        x, y, w, h = 10, 10, 100, 40  # Dummy values; plug in YOLO here if needed

        region_path = save_region(
            image, x, y, w, h,
            os.path.join(DATA_PATH, "regions"),
            page_name,
            image_path=image_path
        )

        element = {
            "label_text": label_text,
            "ocr_type": ocr_type,
            "intent": intent,
            "x": x,
            "y": y,
            "width": w,
            "height": h,
            "bbox": f"{x},{y},{w},{h}",
            "confidence_score": 1.0,
        }

        metadata = build_standard_metadata(
            element,
            page_name,
            image_path=region_path
        )
        metadata["id"] = unique_id
        metadata["ocr_id"] = unique_id
        metadata["get_by_text"] = label_text

        # Storing metadata in ChromaDB
        try:
            stored_metadata = upsert_text_record(metadata)
            results.append(stored_metadata)
        except Exception as e:
            print(f"[ERROR] Failed to upsert to ChromaDB for label='{label_text}': {e}")

        # if debug_log_path:
        #     with open(debug_log_path, "a", encoding="utf-8") as log_file:
        #         log_file.write(json.dumps(metadata, ensure_ascii=False) + "\n")

        
    return results



# === FILE: logic\manual_capture_mode.py ===
# manual_capture_mode.py

# from chromadb import PersistentClient
# from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
# from sentence_transformers import SentenceTransformer
# from sklearn.metrics.pairwise import cosine_similarity
# import numpy as np
# from typing import List, Dict, Any
# from datetime import datetime
# from playwright.async_api import Page
# from utils.file_utils import build_standard_metadata
 
 
 
# # 🔧 Embedding setup
# embedding_fn = SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
# text_model = SentenceTransformer("all-MiniLM-L6-v2")
 
# # 🔧 Persistent ChromaDB
# client = PersistentClient(path="./data/chroma_db")
# collection = client.get_or_create_collection(
#     name="element_metadata",
#     embedding_function=embedding_fn
# )
 
# # 🧠 Memory store
# CURRENT_PAGE_NAME = None
# LAST_MATCHED_RESULTS = []
 
# def set_page_name(name: str):
#     global CURRENT_PAGE_NAME
#     CURRENT_PAGE_NAME = name
#     print(f"✅ Page name set to: {CURRENT_PAGE_NAME}")
 
# def get_page_name() -> str:
#     return CURRENT_PAGE_NAME
 
# def set_last_match_result(data):
#     global LAST_MATCHED_RESULTS
#     LAST_MATCHED_RESULTS = data
 
# def get_last_match_result():
#     return LAST_MATCHED_RESULTS
 
# # ✅ Normalize bbox input
# def bbox_distance(b1, b2) -> float:
#     if isinstance(b1, str):
#         try:
#             x, y, w, h = map(int, b1.split(','))
#             b1 = {"x": x, "y": y, "width": w, "height": h}
#         except Exception as e:
#             print(f"[❌] Invalid bbox string: {b1} — Error: {e}")
#             return float('inf')
#     return np.sqrt((b1['x'] - b2['x'])**2 + (b1['y'] - b2['y'])**2)
 
# # ✅ Text similarity
# def text_similarity(t1: str, t2: str) -> float:
#     vecs = text_model.encode([t1, t2], show_progress_bar=False)
#     return float(cosine_similarity([vecs[0]], [vecs[1]])[0][0])
 
# # ✅ Extract DOM metadata from page
# async def extract_dom_metadata(page: Page, page_name: str) -> List[Dict[str, Any]]:
#     if page.is_closed():
#         print("[❌] Attempted to access a closed page.")
#         return []

#     # elements = await page.locator("body *").all()
#     # This selector matches all elements under <body> EXCEPT anything inside #ocrModal
#     elements = await page.locator("body *:not(#ocrModal *):not(#ocrModal)").all()

#     print(f"[DEBUG] Got {len(elements)} locator from dom except ocrModal")
    
#     output_lines = []
#     data = []
#     output_lines.append(f"All DOM elements")
#     for i, elem in enumerate(elements):
#         try:
#             if await elem.is_visible():            
#                 tag = await elem.evaluate("e => e.tagName.toLowerCase()")
#                 text = await elem.evaluate("e => e.textContent.toLowerCase()")
#                 elem_id = await elem.get_attribute("id")
#                 elem_class = await elem.get_attribute("class")
#                 placeholder = await elem.get_attribute("placeholder")
#                 input_type = await elem.get_attribute("type") if tag and tag.lower() == "input" else ""
#                 attrs = await elem.evaluate("e => { let a = {}; for (let attr of e.attributes) { a[attr.name] = attr.value; } return a; }")
#                 value = attrs.get('value', "")
#                 outer_html = await elem.evaluate("e => e.outerHTML")
#                 visible = await elem.is_visible()
#                 enable = await elem.is_enabled()

#                 editable = False
#                 if tag and tag.lower() in ("input", "textarea", "select"):
#                     editable = await elem.is_editable()
#                 else:
#                     contenteditable = await elem.get_attribute("contenteditable")
#                     if contenteditable == "true":
#                         editable = await elem.is_editable()
#                 bounding_box = await elem.bounding_box()

#                 element_lines = [
#                     f"Element {i+1}:",
#                     f"  page_name:      {page_name}",
#                     f"  tag_name:       {tag or ''}",
#                     f"  text:           {text.strip() if text else ''}",
#                     f"  id:             {elem_id or ''}",
#                     f"  class:          {elem_class or ''}",
#                     f"  value:          {value or ''}",
#                     f"  placeholder:    {placeholder or ''}",
#                     f"  type:           {input_type or ''}",
#                     f"  attributes:     {attrs or ''}",
#                     f"  enable?         {enable or ''}",
#                     f"  visible?        {visible or ''}",
#                     f"  editable?       {editable or ''}",
#                     f"  HTML:           {outer_html[:120]}{'...' if outer_html and len(outer_html) > 120 else ''}",
#                     "-" * 60
#                 ]
#                 output_lines.extend(element_lines)

#                 # If any of these fields are present, append the data
#                 if not (tag or text or placeholder or value):
#                     continue
#                 data.append({
#                     "page_name": page_name or "",
#                     "tag_name": tag or "",
#                     "text": text or "",
#                     "class": elem_class or "",
#                     "value": value or "",
#                     "placeholder": placeholder or "",
#                     "type": input_type or "",
#                     "enable": enable,        # bool (True/False) is fine!
#                     "visible": visible,      # bool (True/False) is fine!
#                     "editable": editable,    # bool (True/False) is fine!
#                     "x": bounding_box["x"] if bounding_box and bounding_box.get("x") is not None else "",
#                     "y": bounding_box["y"] if bounding_box and bounding_box.get("y") is not None else "",
#                     "width": bounding_box["width"] if bounding_box and bounding_box.get("width") is not None else "",
#                     "height": bounding_box["height"] if bounding_box and bounding_box.get("height") is not None else "",
#                 })

#         except Exception as e:
#             print(f"[⚠️] Skipping element {i+1} due to error: {e}")
#             output_lines.append(f"[⚠️] Skipping element {i+1} due to error: {e}")
#             continue

#     # Write all info to a file
#     from pathlib import Path
#     debug_metadata_dir = Path("generated_runs") / "src" / "ocr-dom-metadata"
#     debug_metadata_dir.mkdir(parents=True, exist_ok=True)
#     out_file = debug_metadata_dir / f"dom_elements_{page_name}.txt"
#     with open(out_file, "w", encoding="utf-8") as f:
#         f.write("\n".join(output_lines))
        
#     print(f"[INFO] DOM extracted element data saved to {out_file}")    
#     print("[DEBUG] DOM DATA Length: ", len(data))

#     return data


# def match_and_update(ocr_data, dom_data, collection, text_thresh=0.5, bbox_thresh=300):
#     global LAST_MATCHED_RESULTS
#     matched_records = []

#     print(f"[DEBUG] Matching {len(ocr_data)} OCRs with {len(dom_data)} DOMs")

#     for ocr in ocr_data:
#         if not ocr.get("external"):
#             if not ocr.get("label_text") or not ocr.get("bbox"):
#                 print(f"[SKIP] OCR missing label_text or bbox: {ocr}")
#                 continue

#             best_match = None
#             best_score = 0.0

#             for dom in dom_data:            
#                 dom_text = dom.get("text", "") or dom.get("placeholder", "") or dom.get("value")
#                 if not dom_text:
#                     continue

#                 sim = text_similarity(ocr["text"].lower(), dom_text.lower())

#                 if sim >= text_thresh and sim > best_score:
#                     best_match = dom
#                     best_score = sim                

#             if best_match:
#                 updated = ocr.copy()
#                 updated.update({
#                     "tag_name": best_match.get("tag_name", ""),
#                     "label_text": best_match.get("text") or best_match.get("placeholder") or best_match.get("value") or "",
#                     "dom-id": best_match.get("id", ""),
#                     "dom_class": best_match.get("class", ""),
#                     "value": best_match.get("value", ""),
#                     "placeholder": best_match.get("placeholder", ""),
#                     "type": best_match.get("type", ""),
#                     # "attributes": best_match.get("attributes", ""),
#                     "enable": best_match.get("enable", ""),
#                     "visible": best_match.get("visible", ""),
#                     "editable": best_match.get("editable", ""),
                    
#                     "x": best_match.get("x", ""),
#                     "y": best_match.get("y", ""),
#                     "width": best_match.get("width", ""),
#                     "height": best_match.get("height", ""),
#                     "dom_matched": True,
#                     "match_timestamp": datetime.utcnow().isoformat()
#                 })
#                 # Set label_text with your preferred fallback order
#                 updated["label_text"] = (
#                     (best_match.get("text")).strip() or
#                     (best_match.get("placeholder")).strip() or
#                     (best_match.get("value")).strip() or
#                     ""
#                 )

#                 collection.upsert(
#                     ids=[updated["id"]],
#                     documents=[updated["label_text"]],
#                     metadatas=[updated],
#                 )
#                 matched_records.append(updated)

#     LAST_MATCHED_RESULTS = matched_records
#     print(f"[✅] Matched {len(matched_records)} elements.")
#     return matched_records

# ==================================== NEW CODE =============================

# manual_capture_mode.py

from chromadb import PersistentClient
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from typing import List, Dict, Any
from datetime import datetime
from playwright.async_api import Page
from utils.file_utils import build_standard_metadata
import json

# 🔧 Embedding setup
embedding_fn = SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
text_model = SentenceTransformer("all-MiniLM-L6-v2")

# 🔧 Persistent ChromaDB
client = PersistentClient(path="./data/chroma_db")
collection = client.get_or_create_collection(
    name="element_metadata",
    embedding_function=embedding_fn
)

# 🧠 Memory store
CURRENT_PAGE_NAME = None
LAST_MATCHED_RESULTS = []

def set_page_name(name: str):
    global CURRENT_PAGE_NAME
    CURRENT_PAGE_NAME = name
    print(f"✅ Page name set to: {CURRENT_PAGE_NAME}")

def get_page_name() -> str:
    return CURRENT_PAGE_NAME

def set_last_match_result(data):
    global LAST_MATCHED_RESULTS
    LAST_MATCHED_RESULTS = data

def get_last_match_result():
    return LAST_MATCHED_RESULTS

# ✅ Normalize bbox input
def bbox_distance(b1, b2) -> float:
    if isinstance(b1, str):
        try:
            x, y, w, h = map(int, b1.split(','))
            b1 = {"x": x, "y": y, "width": w, "height": h}
        except Exception as e:
            print(f"[❌] Invalid bbox string: {b1} — Error: {e}")
            return float('inf')
    return np.sqrt((b1['x'] - b2['x'])**2 + (b1['y'] - b2['y'])**2)

# ✅ Text similarity
def text_similarity(t1: str, t2: str) -> float:
    vecs = text_model.encode([t1, t2], show_progress_bar=False)
    return float(cosine_similarity([vecs[0]], [vecs[1]])[0][0])

# # ✅ OLD CODE Extract DOM metadata from page with smart label association
# async def extract_dom_metadata(page: Page, page_name: str) -> List[Dict[str, Any]]:
#     if page.is_closed():
#         print("[❌] Attempted to access a closed page.")
#         return []

#     # 1. Build a mapping from input IDs to label texts (for smart association)
#     label_for_map = {}
#     label_elems = await page.query_selector_all("label[for]")
#     for label in label_elems:
#         label_for = await label.get_attribute("for")
#         label_text = (await label.inner_text()).strip()
#         if label_for and label_text:
#             label_for_map[label_for] = label_text

#     # 2. Collect all interactive fields and other elements except anything in ocrModal
#     elements = await page.locator("body *:not(#ocrModal *):not(#ocrModal)").all()
#     print(f"[DEBUG] Got {len(elements)} locator from dom except ocrModal")

#     output_lines = []
#     data = []
#     output_lines.append(f"All DOM elements")
#     for i, elem in enumerate(elements):
#         try:
#             if await elem.is_visible():
#                 tag = await elem.evaluate("e => e.tagName.toLowerCase()")
#                 text = await elem.evaluate("e => e.textContent") or ""
#                 elem_id = await elem.get_attribute("id")
#                 elem_class = await elem.get_attribute("class")
#                 placeholder = await elem.get_attribute("placeholder")
#                 input_type = await elem.get_attribute("type") if tag and tag.lower() == "input" else ""
#                 attrs = await elem.evaluate("e => { let a = {}; for (let attr of e.attributes) { a[attr.name] = attr.value; } return a; }")
#                 value = attrs.get('value', "")
#                 outer_html = await elem.evaluate("e => e.outerHTML")
#                 visible = await elem.is_visible()
#                 enable = await elem.is_enabled()

#                 editable = False
#                 if tag and tag.lower() in ("input", "textarea", "select"):
#                     editable = await elem.is_editable()
#                 else:
#                     contenteditable = await elem.get_attribute("contenteditable")
#                     if contenteditable == "true":
#                         editable = await elem.is_editable()
#                 bounding_box = await elem.bounding_box()

#                 # --- LABEL LOGIC ---
#                 label_text = ""
#                 if elem_id and elem_id in label_for_map:
#                     label_text = label_for_map[elem_id]
#                 elif await elem.get_attribute("aria-label"):
#                     label_text = await elem.get_attribute("aria-label")
#                 elif placeholder:
#                     label_text = placeholder
#                 elif tag in ("button",):
#                     label_text = text.strip()
#                 elif await elem.get_attribute("data-lov-name"):
#                     label_text = await elem.get_attribute("data-lov-name")

#                 element_lines = [
#                     f"Element {i+1}:",
#                     f"  page_name:      {page_name}",
#                     f"  tag_name:       {tag or ''}",
#                     f"  text:           {text.strip() if text else ''}",
#                     f"  id:             {elem_id or ''}",
#                     f"  class:          {elem_class or ''}",
#                     f"  value:          {value or ''}",
#                     f"  placeholder:    {placeholder or ''}",
#                     f"  type:           {input_type or ''}",
#                     f"  attributes:     {attrs or ''}",
#                     f"  enable?         {enable or ''}",
#                     f"  visible?        {visible or ''}",
#                     f"  editable?       {editable or ''}",
#                     f"  label_text:     {label_text or ''}",
#                     f"  HTML:           {outer_html[:120]}{'...' if outer_html and len(outer_html) > 120 else ''}",
#                     "-" * 60
#                 ]
#                 output_lines.extend(element_lines)

#                 # If none of these fields, skip
#                 if not (tag or text or placeholder or value):
#                     continue
#                 data.append({
#                     "page_name": page_name or "",
#                     "tag_name": tag or "",
#                     "text": text.strip() or "",
#                     "class": elem_class or "",
#                     "value": value or "",
#                     "placeholder": placeholder or "",
#                     "type": input_type or "",
#                     "enable": enable,        # bool (True/False) is fine!
#                     "visible": visible,      # bool (True/False) is fine!
#                     "editable": editable,    # bool (True/False) is fine!
#                     "label_text": label_text or "",
#                     "id": elem_id or "",
#                     "x": bounding_box["x"] if bounding_box and bounding_box.get("x") is not None else "",
#                     "y": bounding_box["y"] if bounding_box and bounding_box.get("y") is not None else "",
#                     "width": bounding_box["width"] if bounding_box and bounding_box.get("width") is not None else "",
#                     "height": bounding_box["height"] if bounding_box and bounding_box.get("height") is not None else "",
#                 })

#         except Exception as e:
#             print(f"[⚠️] Skipping element {i+1} due to error: {e}")
#             output_lines.append(f"[⚠️] Skipping element {i+1} due to error: {e}")
#             continue

#     # Write all info to a file
#     from pathlib import Path
#     debug_metadata_dir = Path("generated_runs") / "src" / "ocr-dom-metadata"
#     debug_metadata_dir.mkdir(parents=True, exist_ok=True)
#     out_file = debug_metadata_dir / f"dom_elements_{page_name}.txt"
#     with open(out_file, "w", encoding="utf-8") as f:
#         f.write("\n".join(output_lines))
        
#     print(f"[INFO] DOM extracted element data saved to {out_file}")    
#     print("[DEBUG] DOM DATA Length: ", len(data))

#     return data

# # ✅ NEW CODE Extract DOM metadata from page with smart label association
async def extract_dom_metadata(page: Page, page_name: str) -> list:
    """
    Extracts DOM metadata for all elements except those inside #ocrModal,
    using a single, fast JS evaluation. The return format matches your existing logic.
    """
    elements_data = await page.evaluate("""
    (pageName) => {
        // Query all elements except those inside #ocrModal
        const nodes = Array.from(document.querySelectorAll('body *:not(#ocrModal *):not(#ocrModal)'));
        return nodes.map((e, i) => {
            // Bounding box
            let bbox = {x: '', y: '', width: '', height: ''};
            try {
                const b = e.getBoundingClientRect();
                bbox = {x: b.x, y: b.y, width: b.width, height: b.height};
            } catch {}
            // Attributes dict
            const attrs = {};
            for (const attr of e.attributes) {
                attrs[attr.name] = attr.value;
            }
            // Label logic
            let label = '';
            if (e.id) {
                const labelElem = document.querySelector(`label[for="${e.id}"]`);
                if (labelElem) label = labelElem.innerText.trim();
            }
            if (!label && e.getAttribute('aria-label')) label = e.getAttribute('aria-label');
            if (!label && e.placeholder) label = e.placeholder;
            if (!label && e.tagName.toLowerCase() === "button") label = e.textContent.trim();
            if (!label && e.getAttribute('data-lov-name')) label = e.getAttribute('data-lov-name');
            // Editable
            let editable = false;
            const tn = e.tagName.toLowerCase();
            if (["input", "textarea", "select"].includes(tn)) {
                editable = !e.readOnly && !e.disabled;
            } else if (e.getAttribute('contenteditable') === "true") {
                editable = true;
            }
            // Visible
            let visible = !!(e.offsetWidth || e.offsetHeight || e.getClientRects().length);
            // Enabled
            let enable = !e.disabled;

            return {
                page_name: pageName || "",
                tag_name: tn,
                text: (e.textContent || "").trim(),
                class: e.className || "",
                id: e.id || "",
                value: (typeof e.value === "string" ? e.value : "") || "",
                placeholder: e.placeholder || "",
                type: e.type || "",
                enable: enable,
                visible: visible,
                editable: editable,
                label_text: label || "",
                x: bbox.x,
                y: bbox.y,
                width: bbox.width,
                height: bbox.height,
                attributes: attrs,
                outer_html: (e.outerHTML || "").slice(0, 120)
            };
        });
    }
    """, page_name)

    # No further async calls needed! You can filter/process in Python if needed.
    print(f"[DEBUG] Got {len(elements_data)} locator from dom except ocrModal")

    output_lines = []
    output_lines.append(f"All DOM elements")
    for i, elem in enumerate(elements_data):
        element_lines = [
            f"Element {i+1}:",
            f"  page_name:      {elem.get('page_name', '')}",
            f"  tag_name:       {elem.get('tag_name', '')}",
            f"  text:           {elem.get('text', '')}",
            f"  id:             {elem.get('id', '')}",
            f"  class:          {elem.get('class', '')}",
            f"  value:          {elem.get('value', '')}",
            f"  placeholder:    {elem.get('placeholder', '')}",
            f"  type:           {elem.get('type', '')}",
            f"  attributes:     {elem.get('attributes', '')}",
            f"  enable?         {elem.get('enable', '')}",
            f"  visible?        {elem.get('visible', '')}",
            f"  editable?       {elem.get('editable', '')}",
            f"  label_text:     {elem.get('label_text', '')}",
            f"  HTML:           {elem.get('outer_html', '')}{'...' if elem.get('outer_html') and len(elem.get('outer_html')) > 120 else ''}",
            "-" * 60
        ]
        output_lines.extend(element_lines)

    # Write all info to a file (exactly as before)
    from pathlib import Path
    debug_metadata_dir = Path("generated_runs") / "src" / "ocr-dom-metadata"
    debug_metadata_dir.mkdir(parents=True, exist_ok=True)
    out_file = debug_metadata_dir / f"dom_elements_{page_name}.txt"
    with open(out_file, "w", encoding="utf-8") as f:
        f.write("\n".join(output_lines))

    print(f"[INFO] DOM extracted element data saved to {out_file}")
    print("[DEBUG] DOM DATA Length: ", len(elements_data))

    return elements_data


# New Optimized match_and_update
def match_and_update(ocr_data, dom_data, collection, text_thresh=0.5, bbox_thresh=300):
    global LAST_MATCHED_RESULTS
    matched_records = []

    print(f"[DEBUG] Matching {len(ocr_data)} OCRs with {len(dom_data)} DOMs")

    # --- Precompute DOM text features and embeddings for text-based matching ---
    dom_texts = []
    dom_candidates = []
    for dom in dom_data:
        dom_text = dom.get("label_text", "") or dom.get(
            "text", "") or dom.get("placeholder", "") or dom.get("value", "")
        dom_texts.append(dom_text.lower())
        dom_candidates.append(dom)
    if dom_texts:
        dom_embeddings = text_model.encode(dom_texts, show_progress_bar=False)
    else:
        dom_embeddings = []

    for ocr in ocr_data:
        if not ocr.get("external"):
            # ---- If label_text exists: optimized vectorized similarity search ----
            if ocr.get("label_text"):
                ocr_label = ocr["label_text"].lower()
                ocr_embedding = text_model.encode([ocr_label])[0]
                if len(dom_embeddings) > 0:  # <-- FIXED ambiguous check
                    sims = cosine_similarity(
                        [ocr_embedding], dom_embeddings)[0]
                    best_idx = int(np.argmax(sims))
                    best_score = float(sims[best_idx])
                    if best_score >= text_thresh:
                        best_match = dom_candidates[best_idx]
                        updated = ocr.copy()
                        updated.update({
                            "tag_name": best_match.get("tag_name", ""),
                            "label_text": best_match.get("label_text") or best_match.get("text") or best_match.get("placeholder") or best_match.get("value") or "",
                            "dom-id": best_match.get("id", ""),
                            "dom_class": best_match.get("class", ""),
                            "value": best_match.get("value", ""),
                            "placeholder": best_match.get("placeholder", ""),
                            "type": best_match.get("type", ""),
                            "enable": best_match.get("enable", ""),
                            "visible": best_match.get("visible", ""),
                            "editable": best_match.get("editable", ""),
                            "x": best_match.get("x", ""),
                            "y": best_match.get("y", ""),
                            "width": best_match.get("width", ""),
                            "height": best_match.get("height", ""),
                            "dom_matched": True,
                            "match_timestamp": datetime.utcnow().isoformat()
                        })
                        # Use label_text with best fallback
                        updated["label_text"] = (
                            (best_match.get("label_text") or "").strip() or
                            (best_match.get("text") or "").strip() or
                            (best_match.get("placeholder") or "").strip() or
                            (best_match.get("value") or "").strip() or
                            ""
                        )
                        # PATCH: Ensure attributes is a string
                        # ... Inside your match/update logic, before collection.upsert:
                        updated = clean_metadata(updated)
                        collection.upsert(
                            ids=[updated.get("element_id")],
                            documents=[updated["label_text"]],
                            metadatas=[updated],
                        )
                        matched_records.append(updated)

            # ---- If label_text not exists: fallback using ocr_type + intent (no change) ----
            elif not ocr.get("label_text"):
                ocr_type = ocr.get("ocr_type", "").lower()
                intent = ocr.get("intent", "").lower()
                best_match = None
                best_score = 0.0
                for dom in dom_data:
                    dom_tag = (dom.get("tag_name") or "").lower()
                    dom_id = (dom.get("id") or "").lower()
                    dom_class = (dom.get("class") or "").lower()
                    dom_label = (dom.get("label_text") or "").strip()
                    if dom_label:
                        continue
                    # Match ocr_type to allowed tag names
                    if ocr_type == "textbox" and dom_tag in ("input", "textarea", "text"):
                        score = 0
                        if intent and (intent in dom_id or intent in dom_class):
                            score = 1.0
                        elif intent.split('_')[0] in dom_id or intent.split('_')[0] in dom_class:
                            score = 0.8
                        if score > best_score:
                            best_score = score
                            best_match = dom
                    # Add more type-intent/tag logic here as needed!
                if best_match:
                    updated = ocr.copy()
                    updated.update({
                        "tag_name": best_match.get("tag_name", ""),
                        "label_text": best_match.get("label_text") or best_match.get("text") or best_match.get("placeholder") or best_match.get("value") or "",
                        "dom-id": best_match.get("id", ""),
                        "dom_class": best_match.get("class", ""),
                        "value": best_match.get("value", ""),
                        "placeholder": best_match.get("placeholder", ""),
                        "type": best_match.get("type", ""),
                        "enable": best_match.get("enable", ""),
                        "visible": best_match.get("visible", ""),
                        "editable": best_match.get("editable", ""),
                        "x": best_match.get("x", ""),
                        "y": best_match.get("y", ""),
                        "width": best_match.get("width", ""),
                        "height": best_match.get("height", ""),
                        "dom_matched": True,
                        "match_timestamp": datetime.utcnow().isoformat()
                    })
                    # Use label_text with best fallback
                    updated["label_text"] = (
                        (best_match.get("label_text") or "").strip() or
                        (best_match.get("text") or "").strip() or
                        (best_match.get("placeholder") or "").strip() or
                        (best_match.get("value") or "").strip() or
                        ""
                    )
                    # PATCH: Ensure attributes is a string
                    # ... Inside your match/update logic, before collection.upsert:
                    updated = clean_metadata(updated)
                    collection.upsert(
                        ids=[updated.get("element_id")],
                        documents=[updated["label_text"]],
                        metadatas=[updated],
                    )
                    matched_records.append(updated)

    LAST_MATCHED_RESULTS = matched_records
    print(f"[✅] Matched {len(matched_records)} elements.")
    return matched_records


# Old code
# def match_and_update(ocr_data, dom_data, collection, text_thresh=0.5, bbox_thresh=300):
#     global LAST_MATCHED_RESULTS
#     matched_records = []

#     print(f"[DEBUG] Matching {len(ocr_data)} OCRs with {len(dom_data)} DOMs")

#     for ocr in ocr_data:
#         if not ocr.get("external"):
            
#             # If label_text exists
#             if ocr.get("label_text"):
#                 best_match = None
#                 best_score = 0.0

#                 for dom in dom_data:            
#                     dom_text = dom.get("label_text", "") or dom.get("text", "") or dom.get("placeholder", "") or dom.get("value")
#                     if not dom_text:
#                         continue

#                     sim = text_similarity(ocr["label_text"].lower(), dom_text.lower())

#                     if sim >= text_thresh and sim > best_score:
#                         best_match = dom
#                         best_score = sim                

#                 if best_match:
#                     updated = ocr.copy()
#                     updated.update({
#                         "tag_name": best_match.get("tag_name", ""),
#                         "label_text": best_match.get("label_text") or best_match.get("text") or best_match.get("placeholder") or best_match.get("value") or "",
#                         "dom-id": best_match.get("id", ""),
#                         "dom_class": best_match.get("class", ""),
#                         "value": best_match.get("value", ""),
#                         "placeholder": best_match.get("placeholder", ""),
#                         "type": best_match.get("type", ""),
#                         "enable": best_match.get("enable", ""),
#                         "visible": best_match.get("visible", ""),
#                         "editable": best_match.get("editable", ""),
#                         "x": best_match.get("x", ""),
#                         "y": best_match.get("y", ""),
#                         "width": best_match.get("width", ""),
#                         "height": best_match.get("height", ""),
#                         "dom_matched": True,
#                         "match_timestamp": datetime.utcnow().isoformat()
#                     })
#                     # Use label_text with best fallback
#                     updated["label_text"] = (
#                         (best_match.get("label_text") or "").strip() or
#                         (best_match.get("text") or "").strip() or
#                         (best_match.get("placeholder") or "").strip() or
#                         (best_match.get("value") or "").strip() or
#                         ""
#                     )

#                     collection.upsert(
#                         ids=[updated["element_id"]],
#                         documents=[updated["label_text"]],
#                         metadatas=[updated],
#                     )
#                     matched_records.append(updated)

#             # If label_text not exists
#             elif not ocr.get("label_text"):
#                 # --- Fallback using ocr_type + intent ---
#                 ocr_type = ocr.get("ocr_type", "").lower()
#                 intent = ocr.get("intent", "").lower()

#                 best_match = None
#                 best_score = 0.0

#                 for dom in dom_data:
#                     dom_tag = (dom.get("tag_name") or "").lower()
#                     dom_id = (dom.get("id") or "").lower()
#                     dom_class = (dom.get("class") or "").lower()
#                     dom_label = (dom.get("label_text") or "").strip()

#                     # Only consider DOM elements without label_text (unlabeled fields)
#                     if dom_label:
#                         continue

#                     # Match ocr_type to allowed tag names
#                     if ocr_type == "textbox" and dom_tag in ("input", "textarea", "text"):
#                         score = 0
#                         # Simple semantic: intent in dom_id/class
#                         if intent and (intent in dom_id or intent in dom_class):
#                             score = 1.0
#                         elif intent.split('_')[0] in dom_id or intent.split('_')[0] in dom_class:
#                             score = 0.8
#                         # You can add more heuristics (partial match, synonyms, etc.)
#                         if score > best_score:
#                             best_score = score
#                             best_match = dom
#                     # (Repeat similar mapping logic for buttons, selects, etc.)
#                 if best_match:
#                     updated = ocr.copy()
#                     updated.update({
#                         "tag_name": best_match.get("tag_name", ""),
#                         "label_text": best_match.get("label_text") or best_match.get("text") or best_match.get("placeholder") or best_match.get("value") or "",
#                         "dom-id": best_match.get("id", ""),
#                         "dom_class": best_match.get("class", ""),
#                         "value": best_match.get("value", ""),
#                         "placeholder": best_match.get("placeholder", ""),
#                         "type": best_match.get("type", ""),
#                         "enable": best_match.get("enable", ""),
#                         "visible": best_match.get("visible", ""),
#                         "editable": best_match.get("editable", ""),
#                         "x": best_match.get("x", ""),
#                         "y": best_match.get("y", ""),
#                         "width": best_match.get("width", ""),
#                         "height": best_match.get("height", ""),
#                         "dom_matched": True,
#                         "match_timestamp": datetime.utcnow().isoformat()
#                     })
#                     # Use label_text with best fallback
#                     updated["label_text"] = (
#                         (best_match.get("label_text") or "").strip() or
#                         (best_match.get("text") or "").strip() or
#                         (best_match.get("placeholder") or "").strip() or
#                         (best_match.get("value") or "").strip() or
#                         ""
#                     )

#                     collection.upsert(
#                         ids=[updated["element_id"]],
#                         documents=[updated["label_text"]],
#                         metadatas=[updated],
#                     )
#                     matched_records.append(updated)

#     LAST_MATCHED_RESULTS = matched_records
#     print(f"[✅] Matched {len(matched_records)} elements.")
#     return matched_records


def clean_metadata(d):
    # Recursively clean all dict/list/set values in the dict d
    for k, v in list(d.items()):
        if isinstance(v, (dict, list, set)):
            # Convert dict/list/set (even empty) to string
            d[k] = json.dumps(v)
        elif not isinstance(v, (str, int, float, bool)) and v is not None:
            d[k] = str(v)
    return d





# === FILE: logic\url_locator_extractor.py ===
# # logic/url_locator_extractor.py
# from bs4 import BeautifulSoup
# from playwright.async_api import async_playwright
# from urllib.parse import urlparse
# from datetime import datetime
# import uuid
# from utils.match_utils import normalize_page_name

# def sanitize_metadata(record: dict) -> dict:
#     sanitized = {}
#     for k, v in record.items():
#         if v is None:
#             sanitized[k] = ""
#         elif isinstance(v, (dict, list)):
#             sanitized[k] = str(v)
#         else:
#             sanitized[k] = v
#     return sanitized

# async def process_url_and_update_chroma(url: str, chroma_collection=None, embedding_function=None, page_name: str = None) -> list[dict]:
#     element_metadata = []
#     page_name = page_name or normalize_page_name(url)
#     snapshot_id = f"{page_name}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

#     print(f"✍️ [DEBUG] Processing URL: {url}")
#     print(f"✍️ [DEBUG] Extracted page_name: {page_name}")

#     async with async_playwright() as p:
#         browser = await p.chromium.launch()
#         page = await browser.new_page()
#         try:
#             await page.goto(url)
#             await page.wait_for_load_state("networkidle")
#             html = await page.content()
#         except Exception as e:
#             print(f"❌ [ERROR] Failed to load {url}: {e}")
#             await browser.close()
#             return []

#         soup = BeautifulSoup(html, "html.parser")

#         for tag in soup.find_all(["button", "input", "a", "label"]):
#             tag_name = tag.name
#             label_text = (
#                 tag.get("aria-label") or
#                 tag.get("placeholder") or
#                 tag.get("alt") or
#                 tag.get("name") or
#                 tag.get_text(strip=True) or
#                 ""
#             ).strip()

#             element_id = f"{tag_name}_{label_text or str(uuid.uuid4())}"
#             selector = f"#{tag.get('id')}" if tag.get("id") else None
#             role = tag.get("role")
#             name = tag.get("aria-label") or tag.get("name") or label_text

#             try:
#                 pw_selector = selector if selector else f"{tag_name}:has-text(\"{label_text}\")"
#                 locator = page.locator(pw_selector)
#                 box = await locator.bounding_box() or {}
#             except Exception:
#                 box = {}

#             document_content = str(tag)
#             record = {
#                 "element_id": element_id,
#                 "page_name": page_name,
#                 "intent": tag_name + "_" + (label_text or element_id),
#                 "tag": tag_name,
#                 "label_text": label_text,
#                 "css_selector": selector,
#                 "get_by_text": label_text if tag_name in ["button", "a", "label"] else None,
#                 "get_by_role": {"role": role, "name": name} if role else None,
#                 "xpath": f"//{tag_name}[contains(text(), '{label_text}')]" if label_text else None,
#                 "x": box.get("x", 0),
#                 "y": box.get("y", 0),
#                 "width": box.get("width", 0),
#                 "height": box.get("height", 0),
#                 "position_relation": {},
#                 "html_snippet": document_content,
#                 "confidence_score": 1.0,
#                 "visibility_score": 1.0,
#                 "locator_stability_score": 1.0,
#                 "snapshot_id": snapshot_id,
#                 "timestamp": datetime.utcnow().isoformat(),
#                 "source_url": url,
#                 "used_in_tests": [],
#                 "last_tested": None,
#                 "healing_success_rate": 0.0
#             }
#             element_metadata.append(record)

#             print(f"   🏷️  [DEBUG] Extracted locator for tag: {tag_name}, label: '{label_text}', page_name: {page_name}")

#             if chroma_collection:
#                 embedding = None
#                 if embedding_function:
#                     try:
#                         text_to_embed = label_text.strip() or tag.get("aria-label") or tag.get("placeholder") or tag.get("alt") or tag.get("name") or tag.get_text(strip=True) or document_content
#                         embedding = embedding_function([text_to_embed])[0]
#                     except Exception as emb_err:
#                         print(f"⚠️ [EMBEDDING] Failed: {emb_err}")

#                 try:
#                     sanitized_record = sanitize_metadata(record)
#                     embedding_vector = embedding.tolist() if embedding is not None else None
#                     chroma_collection.upsert(
#                         ids=[element_id],
#                         documents=[text_to_embed],
#                         metadatas=[sanitized_record],
#                         embeddings=[embedding_vector] if embedding_vector else None
#                     )
#                     print(f"✅ [CHROMA] Upserted locator {element_id} into ChromaDB.")
#                 except Exception as insert_err:
#                     print(f"❌ [CHROMA] Failed to upsert {element_id}: {insert_err}")

#         await browser.close()

#     print(f"✅ [DEBUG] Total locators extracted from {url}: {len(element_metadata)}")
#     return element_metadata

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
from urllib.parse import urlparse
from datetime import datetime
import uuid
from utils.match_utils import normalize_page_name

def sanitize_metadata(record: dict) -> dict:
    sanitized = {}
    for k, v in record.items():
        if v is None:
            sanitized[k] = ""
        elif isinstance(v, (dict, list)):
            sanitized[k] = str(v)
        else:
            sanitized[k] = v
    return sanitized

async def process_url_and_update_chroma(url: str, chroma_collection=None, embedding_function=None, page_name: str = None) -> list[dict]:
    element_metadata = []
    page_name = page_name or normalize_page_name(url)
    snapshot_id = f"{page_name}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

    print(f"✍️ [DEBUG] Processing URL: {url}")
    # print(f"✍️ [DEBUG] Extracted page_name: {page_name}")

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        try:
            await page.goto(url)
            await page.wait_for_load_state("networkidle")
            html = await page.content()
        except Exception as e:
            print(f"❌ [ERROR] Failed to load {url}: {e}")
            await browser.close()
            return []

        soup = BeautifulSoup(html, "html.parser")

        # Native interactive tags
        interactive_tags = [
            "a", "button", "input", "textarea", "select", "option", "label", "summary", "details"
        ]
        # ARIA roles that indicate interactivity (even if on div/span/etc.)
        role_interactive = {
            "button", "link", "checkbox", "radio", "switch", "menuitem", "tab", "combobox", "textbox"
        }

        for tag in soup.find_all(True):  # all tags
            tag_name = tag.name
            role = tag.get("role", "").lower()
            tabindex = tag.get("tabindex")
            is_focusable = tabindex is not None and int(tabindex) >= 0

            is_standard_interactive = tag_name in interactive_tags
            is_custom_interactive = role in role_interactive or is_focusable

            if not (is_standard_interactive or is_custom_interactive):
                continue

            if tag_name == "input" and tag.get("type") == "hidden":
                continue  # skip hidden inputs

            label_text = (
                tag.get("aria-label") or
                tag.get("placeholder") or
                tag.get("alt") or
                tag.get("name") or
                tag.get_text(strip=True) or
                ""
            ).strip()

            element_id = f"{tag_name}_{label_text or str(uuid.uuid4())}"
            selector = f"#{tag.get('id')}" if tag.get("id") else None
            name = tag.get("aria-label") or tag.get("name") or label_text

            try:
                pw_selector = selector if selector else f"{tag_name}:has-text(\"{label_text}\")"
                locator = page.locator(pw_selector)
                box = await locator.bounding_box() or {}
            except Exception:
                box = {}

            document_content = str(tag)
            record = {
                "element_id": element_id,
                "page_name": page_name,
                "intent": tag_name + "_" + (label_text or element_id),
                "tag": tag_name,
                "label_text": label_text,
                "css_selector": selector,
                "get_by_text": label_text if tag_name in ["button", "a", "label"] else None,
                "get_by_role": {"role": role, "name": name} if role else None,
                "xpath": f"//{tag_name}[contains(text(), '{label_text}')]" if label_text else None,
                "x": box.get("x", 0),
                "y": box.get("y", 0),
                "width": box.get("width", 0),
                "height": box.get("height", 0),
                "position_relation": {},
                "html_snippet": document_content,
                "confidence_score": 1.0,
                "visibility_score": 1.0,
                "locator_stability_score": 1.0,
                "snapshot_id": snapshot_id,
                "timestamp": datetime.utcnow().isoformat(),
                "source_url": url,
                "used_in_tests": [],
                "last_tested": None,
                "healing_success_rate": 0.0
            }
            element_metadata.append(record)

            # print(f"   🏷️  [DEBUG] Extracted locator: {tag_name}, label: '{label_text}', role: '{role}'")

            if chroma_collection:
                embedding = None
                if embedding_function:
                    try:
                        text_to_embed = label_text or tag.get("aria-label") or document_content
                        embedding = embedding_function([text_to_embed])[0]
                    except Exception as emb_err:
                        print(f"⚠️ [EMBEDDING] Failed: {emb_err}")

                try:
                    sanitized_record = sanitize_metadata(record)
                    chroma_collection.upsert(
                        ids=[element_id],
                        documents=[text_to_embed],
                        metadatas=[sanitized_record],
                        embeddings=[embedding.tolist()] if embedding is not None else None
                    )
                    print(f"✅ [CHROMA] Upserted locator {element_id}")
                except Exception as insert_err:
                    print(f"❌ [CHROMA] Upsert failed for {element_id}: {insert_err}")

        await browser.close()

    print(f"✅ [DEBUG] Total interactive elements extracted: {len(element_metadata)}")
    return element_metadata



# === FILE: mcp\messages.py ===
# mcp/messages.py

class MCPMessage:
    def __init__(self, sender, recipient, action, payload):
        self.sender = sender
        self.recipient = recipient
        self.action = action
        self.payload = payload

class MCPResponse:
    def __init__(self, success, payload=None, error=None):
        self.success = success
        self.payload = payload
        self.error = error



# === FILE: mcp\protocol.py ===
# mcp/protocol.py

from mcp.messages import MCPMessage, MCPResponse

class MCPAgentBase:
    def __init__(self, manifest):
        self.manifest = manifest
        self.agent_name = manifest.get("agent_name", "unknown")

    def handle_message(self, msg: MCPMessage):
        action = msg.action
        payload = msg.payload

        if action == "generate_method":
            return self.generate_method(payload)
        elif action == "generate_test":
            return self.generate_test(payload)
        elif action == "ping":
            return MCPResponse(True, f"{self.agent_name} alive")
        elif action == "generate_page_file":
            return self.generate_page_file(msg.payload)
        else:
            return MCPResponse(False, error=f"Action '{action}' not supported by {self.agent_name}")

    def generate_method(self, element_spec):
        raise NotImplementedError

    def generate_test(self, test_case_spec):
        raise NotImplementedError

    def generate_page_file(self, page_spec):
        raise NotImplementedError



# === FILE: ml_models_training\data\yolo_ui_detection\labels\train\saucedemo_cart.txt ===
0 0.866 0.342 0.083 0.055
0 0.872 0.697 0.091 0.062
0 0.209 0.697 0.121 0.055
2 0.066 0.161 0.089 0.026
2 0.192 0.161 0.118 0.026



# === FILE: ml_models_training\data\yolo_ui_detection\labels\train\saucedemo_checkout_overview.txt ===
0 0.883 0.731 0.068 0.057
0 0.150 0.732 0.073 0.057
2 0.189 0.226 0.228 0.045
2 0.194 0.299 0.211 0.037
2 0.158 0.377 0.139 0.036



# === FILE: ml_models_training\data\yolo_ui_detection\labels\train\saucedemo_login.txt ===
0 0.506 0.536 0.185 0.058
1 0.500 0.425 0.368 0.033
1 0.500 0.345 0.368 0.033
2 0.232 0.627 0.228 0.045
2 0.732 0.625 0.224 0.038



# === FILE: ml_models_training\data\yolo_ui_detection\labels\val\saucedemo_cart.txt ===
0 0.866 0.342 0.083 0.055
0 0.872 0.697 0.091 0.062
0 0.209 0.697 0.121 0.055
2 0.066 0.161 0.089 0.026
2 0.192 0.161 0.118 0.026



# === FILE: ml_models_training\data\yolo_ui_detection\labels\val\saucedemo_checkout_overview.txt ===
0 0.883 0.731 0.068 0.057
0 0.150 0.732 0.073 0.057
2 0.189 0.226 0.228 0.045
2 0.194 0.299 0.211 0.037
2 0.158 0.377 0.139 0.036



# === FILE: ml_models_training\data\yolo_ui_detection\labels\val\saucedemo_login.txt ===
0 0.506 0.536 0.185 0.058
1 0.500 0.425 0.368 0.033
1 0.500 0.345 0.368 0.033
2 0.232 0.627 0.228 0.045
2 0.732 0.625 0.224 0.038



# === FILE: ml_models_training\scripts\train_mobilnet.py ===
# import os
# import torch
# import torch.nn as nn
# import torch.optim as optim
# from torchvision import datasets, models, transforms
# from torch.utils.data import DataLoader
# from tqdm import tqdm

# # Parameters
# num_classes = 3
# batch_size = 16
# epochs = 10
# lr = 1e-4
# device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# # Paths
# base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
# data_dir = os.path.join(base_dir, "data", "ocr_type")
# model_dir = os.path.join(base_dir, "models")
# os.makedirs(model_dir, exist_ok=True)
# model_save_path = os.path.join(model_dir, "mobilenet_v2_ocr.pth")

# # Transform
# transform = transforms.Compose([
#     transforms.Resize((224, 224)),
#     transforms.ToTensor(),
# ])

# # Dataset and DataLoader
# train_data = datasets.ImageFolder(data_dir, transform=transform)
# train_loader = DataLoader(train_data, batch_size=batch_size, shuffle=True)

# # Model
# model = models.mobilenet_v2(pretrained=True)
# model.classifier[1] = nn.Linear(model.last_channel, num_classes)
# model = model.to(device)

# # Loss and Optimizer
# criterion = nn.CrossEntropyLoss()
# optimizer = optim.Adam(model.parameters(), lr=lr)

# # Training Loop
# for epoch in range(epochs):
#     model.train()
#     running_loss = 0.0
#     correct = 0

#     for inputs, labels in tqdm(train_loader, desc=f"Epoch {epoch+1}/{epochs}"):
#         inputs, labels = inputs.to(device), labels.to(device)
#         optimizer.zero_grad()
#         outputs = model(inputs)
#         loss = criterion(outputs, labels)
#         loss.backward()
#         optimizer.step()

#         running_loss += loss.item()
#         correct += (outputs.argmax(1) == labels).sum().item()

#     acc = 100 * correct / len(train_loader.dataset)
#     print(f"Epoch {epoch+1}/{epochs}, Loss: {running_loss:.4f}, Accuracy: {acc:.2f}%")

# # Save model
# torch.save(model.state_dict(), model_save_path)
# print(f"[✅] Model saved to {model_save_path}")



# ============================= MY NEW UPDATED CODE ==============================================
import os
import torch
import torch.nn as nn
import torch.optim as optim
from torchvision import datasets, models, transforms
from torch.utils.data import DataLoader
from tqdm import tqdm

# Parameters
num_classes = 3
batch_size = 16
epochs = 10
lr = 1e-4
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Paths
base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
data_dir = os.path.join(base_dir, "data", "ocr_type")
model_dir = os.path.join(base_dir, "models")
os.makedirs(model_dir, exist_ok=True)
model_save_path = os.path.join(model_dir, "mobilenet_v2_ocr.pth")

# Transform
transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
])

# Dataset and DataLoader
train_data = datasets.ImageFolder(data_dir, transform=transform)
train_loader = DataLoader(train_data, batch_size=batch_size, shuffle=True)

# Model
model = models.mobilenet_v2(pretrained=True)
model.classifier[1] = nn.Linear(model.last_channel, num_classes)
model = model.to(device)

# Loss and Optimizer
criterion = nn.CrossEntropyLoss()
optimizer = optim.Adam(model.parameters(), lr=lr)

# Training Loop
for epoch in range(epochs):
    model.train()
    running_loss = 0.0
    correct = 0

    # ✅ Use a single persistent progress bar for this epoch
    progress_bar = tqdm(
        train_loader,
        desc=f"Epoch {epoch + 1}/{epochs}",
        leave=True,              # keeps the bar in one line
        dynamic_ncols=True       # fits your terminal width
    )

    for inputs, labels in progress_bar:
        inputs, labels = inputs.to(device), labels.to(device)
        optimizer.zero_grad()
        outputs = model(inputs)
        loss = criterion(outputs, labels)
        loss.backward()
        optimizer.step()

        running_loss += loss.item()
        correct += (outputs.argmax(1) == labels).sum().item()

    acc = 100 * correct / len(train_loader.dataset)
    # print(f"Epoch {epoch+1}/{epochs}, Loss: {running_loss:.4f}, Accuracy: {acc:.2f}%")

# Save model
torch.save(model.state_dict(), model_save_path)
# print(f"ml_models_training/scripts/train_mobilnet.py [✅] Model saved to {model_save_path}")




# === FILE: ml_models_training\scripts\train_yolov8.py ===
from ultralytics import YOLO
import os

# Absolute path to yolov8 config file
config_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "config", "yolov8_config.yaml"))

model = YOLO("yolov8n.pt")

model.train(
    data=config_path,
    epochs=50,
    imgsz=640,
    project="../models",         # Save under backend/ml_models_training/models/
    name="ui_elements_yolov8",   # Folder: models/ui_elements_yolov8/
    device="cpu"                 # Or "cuda" if available
)



# === FILE: ml_models_training\utils\dataset_splitter.py ===
import os, shutil, random

def split_dataset(image_dir, label_dir, train_ratio=0.8):
    images = [f for f in os.listdir(image_dir) if f.endswith(".jpg")]
    random.shuffle(images)
    split = int(train_ratio * len(images))
    train, val = images[:split], images[split:]

    for folder in ['train', 'val']:
        os.makedirs(f"{image_dir}/{folder}", exist_ok=True)
        os.makedirs(f"{label_dir}/{folder}", exist_ok=True)

    for f in train:
        shutil.move(os.path.join(image_dir, f), os.path.join(image_dir, "train", f))
        shutil.move(os.path.join(label_dir, f.replace(".jpg", ".txt")), os.path.join(label_dir, "train", f.replace(".jpg", ".txt")))
    for f in val:
        shutil.move(os.path.join(image_dir, f), os.path.join(image_dir, "val", f))
        shutil.move(os.path.join(label_dir, f.replace(".jpg", ".txt")), os.path.join(label_dir, "val", f.replace(".jpg", ".txt")))

split_dataset("data/yolo_ui_detection/images", "data/yolo_ui_detection/labels")



# === FILE: orchestrator\orchestrator.py ===
# orchestrator/orchestrator.py

from mcp.messages import MCPMessage
from agents.python_agent import PlaywrightPythonAgent
from agents.typescript_agent import PlaywrightTypescriptAgent
import json

with open("agents/agent_manifest_python.json") as f:
    python_manifest = json.load(f)
with open("agents/agent_manifest_typescript.json") as f:
    ts_manifest = json.load(f)

AGENTS = {
    "python": PlaywrightPythonAgent(python_manifest),
    "typescript": PlaywrightTypescriptAgent(ts_manifest)
}

def send_message(language, action, payload):
    agent = AGENTS[language]
    msg = MCPMessage(sender="orchestrator", recipient=agent.agent_name, action=action, payload=payload)
    resp = agent.handle_message(msg)
    return resp



# === FILE: services\chroma_service.py ===
# chroma_services.py

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from config.settings import CHROMA_PATH
from fastapi.concurrency import run_in_threadpool
from services.ocr_type_classifier import classify_ocr_type
import logging
import json

# Setup ChromaDB client and collection
embedding_function = SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
client = chromadb.PersistentClient(path=CHROMA_PATH)
collection = client.get_or_create_collection(name="element_metadata", embedding_function=embedding_function)

# Logger
error_logger = logging.getLogger("chroma_upsert_errors")
error_logger.setLevel(logging.WARNING)
handler = logging.FileHandler("chroma_upsert_errors.log")
handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
error_logger.addHandler(handler)

def _sanitize_metadata_value(value):
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value)
    return value

def upsert_text_record(record: dict):
    # print(f"[DEBUG] Upserting OCR record: {record}")
    bbox_values = record.get('bbox') or [0, 0, 0, 0]
    bbox_str = ",".join(map(str, bbox_values))

    metadata = {
        "element_id": _sanitize_metadata_value(record.get("id")),
        "page_name": _sanitize_metadata_value(record.get("page_name")),
        
        "label_text": _sanitize_metadata_value(record.get("label_text")),
        "ocr_type": _sanitize_metadata_value(record.get("ocr_type", "")),
        "intent": _sanitize_metadata_value(record.get("intent")),
        
        "unique_name": _sanitize_metadata_value(record.get("unique_name")),
        "external": _sanitize_metadata_value(record.get("external")),
        "dom_matched": _sanitize_metadata_value(record.get("dom_matched")),      
        "placeholder": _sanitize_metadata_value(record.get("label_text", "intent")),
        
        "get_by_text": _sanitize_metadata_value(record.get("label_text")),
        "type": "ocr",
    }
    
    # ---- DUPLICATE CHECK START ----
    # 1. Query by the broadest field (the one with the most candidates)
    possible_matches = collection.get(
        where={"label_text": metadata.get("label_text")},
        include=["metadatas"]
    )

    # 2. Loop through matches and check all fields
    for idx, meta in enumerate(possible_matches.get("metadatas", [])):
        if (
            meta.get("page_name") == metadata.get("page_name") and
            meta.get("ocr_type") == metadata.get("ocr_type") and
            meta.get("intent") == metadata.get("intent")
        ):
            existing_id = possible_matches["ids"][idx]
            existing_record = collection.get(ids=[existing_id], include=["documents", "metadatas", "embeddings"])
            return {
                "id": existing_record["ids"][0],
                "document": existing_record["documents"][0],
                "metadata": existing_record["metadatas"][0],
                # "embedding": existing_record["embeddings"][0]
            }
    # ---- DUPLICATE CHECK END ----

    try:
        text_to_embed = build_embedding_text(record)
        embedding_value = embedding_function([text_to_embed])[0]
        collection.upsert(
            ids=[record["id"]],
            documents=[metadata["label_text"]],
            metadatas=[metadata],
            embeddings=[embedding_value],
        )
        
        # Fetch what was actually stored
        stored_data = collection.get(ids=[record["id"]], include=["documents", "metadatas", "embeddings"]
        )

        # Return it as a structured object
        return {
            "id": stored_data["ids"][0],
            "document": stored_data["documents"][0],
            "metadata": stored_data["metadatas"][0],
            # "embedding": stored_data["embeddings"][0]
        }

    except Exception as e:
        error_logger.warning(f"upsert_text_record failed: {str(e)} | Record: {record}")

def build_embedding_text(record: dict) -> str:
    parts = [
        record.get("label_text", "").strip(),
        record.get("ocr_type", "").strip(),
        record.get("intent", "").strip(),
        record.get("page_name", "").strip()
    ]
    # Remove empty fields and join with a space
    return " | ".join([p for p in parts if p])

def upsert_element_record(record: dict):
    document_content = record.get("html_snippet") or record.get("label_text") or record.get("intent")

    metadata = {
        "element_id": _sanitize_metadata_value(record.get("element_id")),
        "page_name": _sanitize_metadata_value(record.get("page_name")),
        "intent": _sanitize_metadata_value(record.get("intent")),
        "tag": _sanitize_metadata_value(record.get("tag")),
        "label_text": _sanitize_metadata_value(record.get("label_text")),
        "css_selector": _sanitize_metadata_value(record.get("css_selector")),
        "get_by_text": _sanitize_metadata_value(record.get("get_by_text")),
        "get_by_role": _sanitize_metadata_value(record.get("get_by_role")),
        "xpath": _sanitize_metadata_value(record.get("xpath")),
        "x": record.get("x") or 0,
        "y": record.get("y") or 0,
        "width": record.get("width") or 0,
        "height": record.get("height") or 0,
        "position_relation": _sanitize_metadata_value(record.get("position_relation")),
        "html_snippet": _sanitize_metadata_value(record.get("html_snippet")),
        "confidence_score": record.get("confidence_score") or 0.0,
        "visibility_score": record.get("visibility_score") or 0.0,
        "locator_stability_score": record.get("locator_stability_score") or 0.0,
        "snapshot_id": _sanitize_metadata_value(record.get("snapshot_id")),
        "timestamp": _sanitize_metadata_value(record.get("timestamp")),
        "source_url": _sanitize_metadata_value(record.get("source_url")),
        "used_in_tests": _sanitize_metadata_value(record.get("used_in_tests")),
        "last_tested": _sanitize_metadata_value(record.get("last_tested")),
        "healing_success_rate": record.get("healing_success_rate") or 0.0,
        "type": "locator"
    }

    try:
        embedding_value = record.get("combined_embedding") or record.get("text_embedding")
        if not embedding_value:
            embedding_value = embedding_function([document_content])[0]

        collection.upsert(
            documents=[document_content],
            metadatas=[metadata],
            embeddings=[embedding_value],
            ids=[record["element_id"]]
        )
    except Exception as e:
        error_logger.warning(f"upsert_element_record failed: {str(e)} | Record: {record}")

def fetch_ocr_entries():
    try:
        results = collection.get(where={"type": "ocr"})
        ocr_entries = []
        for id_, doc, meta in zip(results["ids"], results["documents"], results["metadatas"]):
            ocr_entries.append({
                "id": id_,
                "text": doc,
                "page": meta.get("page_name", "")
            })

        # print(f"[FETCH OCR] Found {len(ocr_entries)} OCR entries")
        for entry in ocr_entries:
            # print(f"  ID: {entry['id']} | Text: {entry['text']} | Page: {entry['page']}")
            pass
        return ocr_entries
    except Exception as e:
        error_logger.warning(f"fetch_ocr_entries failed: {str(e)}")
        return []


def _update_locator_by_text_sync(entry_id: str, locator: str):
    """Synchronously update the locator field for a given record."""
    try:
        item = collection.get(ids=[entry_id])
        doc = item["documents"][0]
        meta = item["metadatas"][0]
        meta["locator"] = locator
        meta["source_type"] = "url"
        meta_sanitized = {k: _sanitize_metadata_value(v) for k, v in meta.items()}

        collection.upsert(
            documents=[doc],
            metadatas=[meta_sanitized],
            ids=[entry_id]
        )
    except Exception as e:
        error_logger.warning(f"_update_locator_by_text_sync failed: {str(e)} | ID: {entry_id}")


async def update_locator_by_text(entry_id: str, locator: str):
    await run_in_threadpool(_update_locator_by_text_sync, entry_id, locator)



# === FILE: services\graph_service.py ===
from collections import deque
import json
import os
from typing import List
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def build_dependency_graph(ordered_images: List[str], output_path: str = "./data/navigation_graph.json") -> None:
    """
    Builds a simple directed graph based on ordered image names.
    Stores edges in JSON format: [ {"from": "image1.png", "to": "image2.png"}, ... ]
    """
    edges = []
    for i in range(len(ordered_images) - 1):
        edges.append({"from": ordered_images[i], "to": ordered_images[i + 1]})

    # Ensure the folder exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    try:
        with open(output_path, "w") as f:
            json.dump(edges, f, indent=2)
        logger.debug(f"[GRAPH] ✅ Dependency graph written to: {os.path.abspath(output_path)}")
        # logger.debug(f"[GRAPH] Contents:\n{json.dumps(edges, indent=2)}")
    except Exception as e:
        logger.error(f"[GRAPH] ❌ Failed to write dependency graph: {e}")


def read_dependency_graph(input_path: str = "./data/navigation_graph.json") -> List[dict]:
    """
    Reads the stored navigation graph.
    Returns list of edges.
    """
    try:
        with open(input_path, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"[GRAPH] ❌ Error reading graph: {e}")
        return []


def find_path(graph, start, end):
    queue = deque([[start]])
    visited = set()

    while queue:
        path = queue.popleft()
        node = path[-1]
        if node == end:
            return path
        if node not in visited:
            visited.add(node)
            for neighbor in graph.get(node, []):
                new_path = list(path)
                new_path.append(neighbor)
                queue.append(new_path)
    return []

def get_adjacency_list(edges: List[dict]) -> dict:
    graph = {}
    for edge in edges:
        graph.setdefault(edge["from"], []).append(edge["to"])
    return graph



# === FILE: services\ocr_type_classifier.py ===
from PIL import Image
import torch
import os
from torchvision import transforms, models

# Define output label map
_label_map = {0: "button", 1: "textbox", 2: "label"}

# Preprocess for MobileNet
_transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
])

# Load fine-tuned MobileNet from disk (replace path if needed)
model_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ml_models_training", "models", "mobilenet_v2_ocr.pth"))


_model = models.mobilenet_v2(pretrained=False)
_model.classifier[1] = torch.nn.Linear(_model.last_channel, 3)
_model.load_state_dict(torch.load(model_path, map_location="cpu"))  # Load weights
_model.eval()

def classify_ocr_type(image_path: str) -> str:
    try:
        image = Image.open(image_path).convert("RGB")
        input_tensor = _transform(image).unsqueeze(0)
        with torch.no_grad():
            output = _model(input_tensor)
            predicted_class = output.argmax(dim=1).item()
            return _label_map.get(predicted_class, "unknown")
    except Exception as e:
        print(f"[OCR TYPE ERROR] Failed to classify '{image_path}': {e}")
        return "unknown"



# === FILE: services\page_enricher.py ===
from utils.enrichment_status import set_enriched, is_enriched
from utils.match_utils import normalize_page_name
from logic.manual_capture_mode import extract_dom_metadata, match_and_update
from chromadb import PersistentClient
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
import asyncio


async def enrich_page(page, page_name):
    if is_enriched(page_name):
        return  # Already enriched

    # --- DOM Extraction ---
    dom_data = await extract_dom_metadata(page, page_name)

    # --- OCR Data Fetch ---
    embedding_fn = SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
    client = PersistentClient(path="./data/chroma_db")
    collection = client.get_or_create_collection(name="element_metadata", embedding_function=embedding_fn)
    ocr_data = [r for r in collection.get(where={"page_name": page_name, "type": "ocr"}).get("metadatas", [])]

    # --- Match and Update ---
    match_and_update(ocr_data, dom_data, collection)

    set_enriched(page_name, True)



# === FILE: services\test_generation_utils.py ===
import os
import re
from pathlib import Path
from dotenv import load_dotenv
from chromadb import PersistentClient
from openai import OpenAI
from utils.match_utils import normalize_page_name

load_dotenv()

project_root = Path(__file__).resolve().parents[1]
chroma_client = PersistentClient(path=str(project_root / "data" / "chroma_db"))
collection = chroma_client.get_or_create_collection("element_metadata")
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
openai_client = client  # <-- Add this line

def get_class_name(page_name: str) -> str:
    return f"Saucedemo_{page_name}Page"

def filter_all_pages():
    records = collection.get()
    return list(set(normalize_page_name(meta.get("page_name", "unknown")) for meta in records.get("metadatas", [])))

__all__ = ["openai_client", "collection", "filter_all_pages", "get_class_name"]



# === FILE: services\yolo_detector.py ===
from ultralytics import YOLO
from PIL import Image
import os
import math
from collections import Counter

# Load your trained YOLOv8 model (adjust path if needed)
# Set absolute path to trained model
model_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ml_models_training", "models", "ui_elements_yolov8", "weights", "best.pt"))
model = YOLO(model_path)



# Allowed UI types
ALLOWED_CLASSES = set(model.names.values())  # Accept all class names from the model

# Class names for debug logs
CLASS_NAMES = model.names

def iou(boxA, boxB):
    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[2], boxB[2])
    yB = min(boxA[3], boxB[3])
    interArea = max(0, xB - xA) * max(0, yB - yA)
    boxAArea = (boxA[2] - boxA[0]) * (boxA[3] - boxA[1])
    boxBArea = (boxB[2] - boxB[0]) * (boxB[3] - boxB[1])
    return interArea / float(boxAArea + boxBArea - interArea + 1e-6)

def center_distance(boxA, boxB):
    ax, ay = (boxA[0] + boxA[2]) / 2, (boxA[1] + boxA[3]) / 2
    bx, by = (boxB[0] + boxB[2]) / 2, (boxB[1] + boxB[3]) / 2
    return math.sqrt((ax - bx) ** 2 + (ay - by) ** 2)

def detect_ui_elements_yolo(image_path: str, ocr_bbox: tuple[int, int, int, int], verbose: bool = False) -> tuple[int, int, int, int, str, float]:
    """
    Detect UI components in full screenshot and return most relevant match for OCR region.
    Returns (x, y, w, h, detected_type, confidence_score)
    """
    image = Image.open(image_path).convert("RGB")
    results = model.predict(source=image, conf=0.10, save=False, verbose=False)[0]

    ocr_x, ocr_y, ocr_w, ocr_h = ocr_bbox
    ocr_box = [ocr_x, ocr_y, ocr_x + ocr_w, ocr_y + ocr_h]
    best_iou = 0
    best_box = ocr_box
    best_class = "unknown"
    min_distance = float("inf")
    
    class_counts = Counter()
    ignored_classes = []

    for box in results.boxes:
        cls_id = int(box.cls)
        cls_name = CLASS_NAMES.get(cls_id, "unknown").strip().lower()

        if cls_name not in ALLOWED_CLASSES:
            ignored_classes.append(cls_name)
            continue

        class_counts[cls_name] += 1

        x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
        detection_box = [x1, y1, x2, y2]
        iou_val = iou(ocr_box, detection_box)

        if iou_val > best_iou:
            best_iou = iou_val
            best_box = detection_box
            best_class = cls_name
        elif best_iou < 0.05:
            dist = center_distance(ocr_box, detection_box)
            if dist < min_distance:
                min_distance = dist
                best_box = detection_box
                best_class = cls_name

    final_x, final_y = best_box[0], best_box[1]
    final_w, final_h = best_box[2] - best_box[0], best_box[3] - best_box[1]
    confidence = round(float(best_iou if best_iou > 0 else 0.0), 2)

    if verbose:
        # print(f"[YOLO DETECT] Classes detected: {dict(class_counts)}")
        if ignored_classes:
            # print(f"[YOLO DETECT] Ignored classes: {ignored_classes}")
            pass
        # print(f"[YOLO DETECT] Selected type: {best_class} with IOU={best_iou:.2f} for OCR text bbox={ocr_bbox}")

    return final_x, final_y, final_w, final_h, best_class, confidence



# === FILE: utils\enrichment_status.py ===
import json
from pathlib import Path

STATUS_FILE = Path("generated_runs/src/metadata/enrichment_status.json")


def load_status():
    if STATUS_FILE.exists():
        return json.loads(STATUS_FILE.read_text())
    return {}


def save_status(status):
    STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATUS_FILE.write_text(json.dumps(status, indent=2))


def is_enriched(page_name):
    status = load_status()
    return status.get(page_name, False)


def set_enriched(page_name, value=True):
    status = load_status()
    status[page_name] = value
    save_status(status)


def reset_enriched(page_name):
    status = load_status()
    if page_name in status:
        del status[page_name]
        save_status(status)



# === FILE: utils\export_chromadb.py ===
import json
from pathlib import Path
from chromadb import PersistentClient

# Path to your existing ChromaDB directory
chroma_path = Path(__file__).resolve().parents[0] / "data" / "chroma_db"

# Connect to ChromaDB
client = PersistentClient(path=str(chroma_path))
collection = client.get_or_create_collection("element_metadata")

# Fetch all records
records = collection.get()

# Extract relevant data
output = []
for i in range(len(records["ids"])):
    entry = {
        "id": records["ids"][i],
        "document": records["documents"][i],
        "metadata": records["metadatas"][i]
    }
    output.append(entry)

# Write to JSON
output_path = Path("chromadb_export.json")
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(output, f, indent=2, ensure_ascii=False)

print(f"utils/export_chromaDB.py ✅ ChromaDB exported to {output_path}")



# === FILE: utils\file_utils.py ===
import os
import time
from pathlib import Path
from PIL import Image
from datetime import datetime
from utils.match_utils import assign_intent_semantic
from services.ocr_type_classifier import classify_ocr_type 
from services.yolo_detector import detect_ui_elements_yolo

def save_region(image: Image.Image, x: int, y: int, w: int, h: int, output_dir: str, page_name: str = "page", image_path: str = "") -> str:
    if image_path and os.path.exists(image_path):
        try:
            x, y, w, h = detect_ui_elements_yolo(image_path, (x, y, w, h))
        except Exception as e:
            # print(f"[YOLO FALLBACK] Using default bbox due to: {e}")
            pass

    # ✅ Clamp bounding box to image dimensions
    x = max(0, min(x, image.width - 1))
    y = max(0, min(y, image.height - 1))
    w = max(1, min(w, image.width - x))
    h = max(1, min(h, image.height - y))

    # Generate file name
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
    filename = f"{page_name}_{x}_{y}_{w}_{h}_{timestamp}.png"
    region_path = os.path.join(output_dir, filename)

    # Crop and save
    cropped = image.crop((x, y, x + w, y + h))
    cropped.save(region_path)
    return region_path
    
    
    
def build_standard_metadata(element: dict, page_name: str, image_path: str = "", source_url: str = "") -> dict:
    label_text = element.get("label_text", "")  
    ocr_type = element.get("ocr_type", "")
    intent = element.get("intent", "")
    
    unique_name = generate_unique_name(page_name, label_text, ocr_type, intent)

    return sanitize_metadata({
        "page_name": page_name,
        "label_text": label_text,
        "ocr_type": ocr_type,
        "intent": intent,
        "unique_name":unique_name,
        "external": False,
        "dom_matched": element.get("dom_matched", False), 
        
        "region_image_path": image_path,
        "source_url": source_url,
        "confidence_score": element.get("confidence_score", 1.0),
        "visibility_score": element.get("visibility_score", 1.0),
        "locator_stability_score": element.get("locator_stability_score", 1.0),
        
        "id": element.get("id") or element.get("ocr_id") or element.get("element_id", ""),
        "ocr_id": element.get("ocr_id") or element.get("id") or element.get("element_id", ""),
        "text": element.get("text") or label_text,        
        "x": element.get("x", element.get("boundingBox", {}).get("x", 0)),
        "y": element.get("y", element.get("boundingBox", {}).get("y", 0)),
        "width": element.get("width", element.get("boundingBox", {}).get("width", 0)),
        "height": element.get("height", element.get("boundingBox", {}).get("height", 0)),
        "used_in_tests": element.get("used_in_tests", []),
        "last_tested": element.get("last_tested", ""),
        "healing_success_rate": element.get("healing_success_rate", 0.0),
        "snapshot_id": element.get("snapshot_id", ""),
        "match_timestamp": element.get("match_timestamp", ""),
        "bbox": element.get("bbox", f"{element.get('x', 0)},{element.get('y', 0)},{element.get('width', 0)},{element.get('height', 0)}"),
        "position_relation": element.get("position_relation", {}),
        "tag_name": element.get("tag_name", ""),
        "xpath": element.get("xpath", ""),
        "get_by_text": element.get("get_by_text", ""),
        "get_by_role": element.get("get_by_role", ""),
        "html_snippet": element.get("html_snippet", ""),
        "placeholder": element.get("placeholder", ""),   
    })

# def generate_unique_name(page_name: str, intent: str, label_text: str, ocr_type: str) -> str:
#     label = label_text.lower().strip().replace(" ", "_")
#     return f"{page_name}_{intent}_{label}_{ocr_type}"

import hashlib
def generate_unique_name(page_name: str, label_text: str, ocr_type: str, intent: str) -> str:
    # Remove quotes from label_text
    cleaned_label = (label_text or "").replace("'", "").replace('"', "")
    # Lowercase and replace spaces with underscores
    label = cleaned_label.lower().strip().replace(" ", "_")
    # Truncate to 50 chars
    cleaned_label = cleaned_label[:50]
    # Define unique string to hash
    unique_str = f"{page_name}_{label}_{ocr_type}_{intent}"
    # Use SHA256, take the first 8 chars for brevity
    hash_part = hashlib.sha256(unique_str.encode("utf-8")).hexdigest()[:8]    
    # Assemble the final unique name
    if label_text:
        return f"{page_name}_{label}_{ocr_type}_{intent}_{hash_part}"
    else:
        return f"{page_name}_{ocr_type}_{intent}_{hash_part}"



def sanitize_metadata(metadata: dict) -> dict:
    def safe_convert(value):
        if isinstance(value, (str, int, float, bool)):
            return value
        if value is None:
            return ""
        if isinstance(value, (dict, list)):
            return str(value)
        return str(value)
    return {k: safe_convert(v) for k, v in metadata.items()}


def clean_old_files(directory: str, age_seconds: int = 3600):
    """
    Deletes files older than `age_seconds` from the given directory.
    """
    dir_path = Path(directory)
    if not dir_path.exists():
        return

    now = time.time()
    for file in dir_path.glob("*"):
        if file.is_file():
            file_age = now - file.stat().st_mtime
            if file_age > age_seconds:
                try:
                    file.unlink()
                    # print(f"[CLEANUP] Deleted old file: {file}")
                except Exception as e:
                    print(f"[CLEANUP ERROR] Failed to delete {file}: {e}")




# === FILE: utils\match_utils.py ===
# utils/match_utils.py
from sentence_transformers import SentenceTransformer, util
import difflib
import re
import os
from urllib.parse import urlparse


def find_best_match(target: str, ocr_entries: dict, threshold=0.8):
    best_score = 0
    best_id = None
    for entry_id, text in ocr_entries.items():
        score = difflib.SequenceMatcher(
            None, target.lower(), text.lower()).ratio()
        if score > threshold and score > best_score:
            best_score = score
            best_id = entry_id
    return best_id


def normalize_text(text: str) -> str:
    """
    Normalize text for embedding comparison.
    """
    text = text.lower().strip()
    text = re.sub(r'[^\w\s]', '', text)  # remove punctuation
    text = re.sub(r'\s+', ' ', text)     # collapse whitespace
    return text


def normalize_page_name(input_string: str) -> str:
    input_string = input_string.strip().lower()

    # Handle URLs
    if input_string.startswith("http"):
        parsed = urlparse(input_string)
        domain = (parsed.hostname or "").replace(
            "www.", "").split('.')[0] if parsed.hostname else ""
        path = parsed.path.strip("/")

        # Just use the last non-empty path segment, or "login" as fallback
        if path:
            segments = [seg for seg in path.split("/") if seg]
            page = segments[-1] if segments else "login"
            page = re.sub(r'\.html?$', '', page)
            page = re.sub(r'_\d+$', '', page)
        else:
            page = "login"
        return f"{domain}_{page}" if domain else page

    # Handle images: strip extension and trailing _<digits>
    if input_string.endswith((".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp")):
        base = re.sub(r'\.(png|jpg|jpeg|bmp|gif|webp)$', '', input_string)
        base = re.sub(r'_\d+$', '', base)
        return base.lower()

    # Fallback: just remove trailing _<digits> for anything else
    return re.sub(r'_\d+$', '', input_string)


def generalize_label(label: str) -> str:
    """Map raw field names to semantic equivalents like username/password."""
    label = normalize_text(label)
    if "user" in label or "email" in label or "login" in label:
        return "username"
    if "pass" in label or "pwd" in label:
        return "password"
    return label


intent_model = SentenceTransformer("all-MiniLM-L6-v2")

# Define common test intents and their typical label meanings
INTENT_TEMPLATES = {
    "fill_username": ["username", "user name", "email", "login id"],
    "fill_password": ["password", "passcode"],
    "click_login": ["login", "sign in", "submit", "continue"],
    "click_cart": ["cart", "basket"],
    "click_checkout": ["checkout", "place order"],
    "click_continue": ["continue", "next"],
    "click_finish": ["finish", "complete", "done"],
    "click_logout": ["logout", "sign out"],
}

intent_embeddings = {
    intent: intent_model.encode(
        labels, convert_to_tensor=True, show_progress_bar=False)
    for intent, labels in INTENT_TEMPLATES.items()
}


def assign_intent_semantic(label_text: str) -> str:
    label_embedding = intent_model.encode(
        label_text, convert_to_tensor=True, show_progress_bar=False)

    best_intent = None
    best_score = -1

    for intent, embeddings in intent_embeddings.items():
        score = util.pytorch_cos_sim(label_embedding, embeddings).max().item()
        if score > best_score:
            best_score = score
            best_intent = intent

    return best_intent if best_score > 0.6 else None



# === FILE: utils\prompt_utils.py ===
def build_method_prompt_block(method_map: dict) -> str:
    """
    Converts { "login": ["enter_username", "click_login"] }
    → string:
    login_page:
      - enter_username
      - click_login
    """
    lines = []
    for page, methods in method_map.items():
        lines.append(f"{page}_page:")
        for m in methods:
            lines.append(f"  - {m}")
    return "\n".join(lines)


def build_prompt(
    story_block: str,
    method_map: dict,
    page_names: list[str],
    site_url: str,
    dynamic_steps: list[str]
) -> str:
    page_method_section = build_method_prompt_block(method_map)
    dynamic_steps_joined = "\n".join(dynamic_steps)

    return (
        f"You are an expert QA automation engineer.\n"
        f"Generate **Playwright async Python test cases** using the provided user story.\n\n"
        f"User Story:\n{story_block}\n\n"
        f"⚠️ STRICT RULES:\n"
        f"- Use ONLY the methods listed in the Pages and Methods section below.\n"
        f"- NEVER make up method names.\n"
        f"- Each method call must start with the correct page object variable (e.g. `await login_page.enter_username(...)`).\n"
        f"- Import only required pages. Use `LoginPage(page)`, `DashboardPage(page)` etc.\n"
        f"- Assign each imported class to a variable with `_page` suffix.\n"
        f"- Use the following naming pattern:\n"
        f"  e.g. `login_page = LoginPage(page)`\n\n"
        f"🚀 OUTPUT FORMAT:\n"
        f"- Write 3 test functions: test_positive_<feature>, test_negative_<feature>, test_edge_<feature>.\n"
        f"- Use async def and Playwright's sync idioms.\n"
        f"- Use `try/except` inside each test and print pass/fail messages.\n"
        f"- Start each test by navigating to: `{site_url}`\n"
        f"- Use proper async/await for all method calls.\n"
        f"- Do NOT include markdown, explanation, or imports.\n"
        f"- Output only raw Python code with the test functions.\n\n"
        f"📘 Pages and Methods:\n{page_method_section}\n\n"
        f"💡 Additional Hints:\n{dynamic_steps_joined}\n\n"
        f"Generate the full test code now."
    )



# === FILE: utils\smart_ai_utils.py ===
from pathlib import Path

SMART_AI_CODE = """import json
import numpy as np
from sentence_transformers import SentenceTransformer, util

class SmartAILocatorError(Exception):
    pass

# 🟢 Minimal wrapper to handle select_option fallback automatically
class SmartAIWrappedLocator:
    def __init__(self, locator, page):
        self._locator = locator
        self._page = page

    def __getattr__(self, name):
        # Delegate all other methods/attributes to Playwright's locator
        return getattr(self._locator, name)

    def select_option(self, value):
        try:
            return self._locator.select_option(value)
        except Exception as e:
            print(f"[SmartAI][select_option fallback] Native select_option failed: {e}")
            try:
                self._page.get_by_role("combobox").click()
                self._page.get_by_role("option", name=value).click()
                print(f"[SmartAI][select_option fallback] Selected '{value}' via combobox+option fallback")
            except Exception as e2:
                print(f"[SmartAI][select_option fallback] Fallback also failed: {e2}")
                raise

class SmartAISelfHealing:
    def __init__(self, metadata):
        self.metadata = metadata
        self.model = SentenceTransformer("all-MiniLM-L6-v2")
        # 1️⃣ Cache embeddings for all metadata elements for fast ML matching
        self.embeddings = [
            self.model.encode(self._element_to_string(e), convert_to_tensor=True, show_progress_bar=False)
            for e in self.metadata
        ]
        # 10️⃣ Track failed locators (element unique_name → fail count)
        self.locator_fail_count = {}

    # 5️⃣ Single definition; all prioritization inside
    def _try_all_locators(self, element, page):
        strategies = []

        # Highest priority: try by role and label_text (esp for button, input, etc)
        if element.get("tag_name") and element.get("label_text"):
            role = self._map_tag_to_role(element["tag_name"])
            if role:
                strategies.append((lambda: page.get_by_role(
                    role, name=element["label_text"]), f"get_by_role({role}, name={element['label_text']})"))

        # Try by label (best for inputs)
        if element.get("label_text"):
            strategies.append((lambda: page.get_by_label(
                element["label_text"]), f"get_by_label({element['label_text']})"))

        # Try by visible text (good for buttons, links, etc)
        if element.get("label_text"):
            strategies.append((lambda: page.get_by_text(
                element["label_text"], exact=True), f"get_by_text({element['label_text']}, exact=True)"))

        # Try by placeholder (for textboxes/inputs)
        if element.get("placeholder"):
            strategies.append((lambda: page.get_by_placeholder(
                element["placeholder"]), f"get_by_placeholder({element['placeholder']})"))

        # Try by sample value (displayed value in input)
        if element.get("sample_value"):
            strategies.append((lambda: page.get_by_display_value(
                element["sample_value"]), f"get_by_display_value({element['sample_value']})"))

        # Data attributes (testid/qa)
        data_attrs = element.get("data_attrs", {})
        for k, v in data_attrs.items():
            if "test" in k.lower() or "qa" in k.lower():
                strategies.append((lambda: page.get_by_test_id(v),
                                f"get_by_test_id({v}) for {k}"))

        # By id (exact and partial)
        if element.get("dom_id"):
            id_value = element["dom_id"]
            strategies.append((lambda: page.locator(
                f'#{id_value}'), f"locator(#{id_value}) [ID exact]"))
            strategies.append((lambda: page.locator(
                f'[id*="{id_value}"]'), f'locator([id*="{id_value}"]) [ID partial]'))

        # By class (exact and partial)
        if element.get("dom_class"):
            class_value = element["dom_class"]
            class_sel = "." + ".".join(class_value.split())
            strategies.append((lambda: page.locator(class_sel),
                            f"locator({class_sel}) [class exact]"))
            strategies.append((lambda: page.locator(
                f'[class*="{class_value}"]'), f'locator([class*="{class_value}"]) [class partial]'))

        # By class_list
        if element.get("class_list"):
            sel = "." + ".".join(element["class_list"])
            strategies.append((lambda: page.locator(
                sel), f"locator({sel}) [class_list]"))

        # Custom CSS locator
        if element.get("locator") and element["locator"].get("type") == "css":
            strategies.append((lambda: page.locator(
                element["locator"]["value"]), f"locator({element['locator']['value']}) [custom css]"))
                
        # Now try each strategy in order
        for func, desc in strategies:
            try:
                locator = func()
                if locator and locator.count() > 0:
                    print(f"[SmartAI][Return] {desc} succeeded.")
                    self.locator_fail_count[element.get("unique_name")] = 0
                    return locator.last
            except Exception as e:
                unique_name = element.get("unique_name", "")
                self.locator_fail_count[unique_name] = self.locator_fail_count.get(
                    unique_name, 0) + 1
                print(f"[SmartAI][Skip] {desc} failed: {e}")

        print("[SmartAI][Return] No locator found for element.")
        return None

    # def _try_all_locators(self, element, page):
    #     # Tries various locator strategies in strict priority order.
    #     # Enhancement: Prioritize, early return, minimal .count() checks.
    #     # Enhancement: Penalize recently failing locators.
    #     def should_skip(unique_name):
    #         return self.locator_fail_count.get(unique_name, 0) >= 3

    #     strategies = []

    #     data_attrs = element.get("data_attrs", {})
    #     for k, v in data_attrs.items():
    #         if "test" in k.lower() or "qa" in k.lower():
    #             strategies.append((lambda: page.get_by_test_id(v), f"get_by_test_id({v}) for {k}"))

    #     if element.get("tag_name"):
    #         role = self._map_tag_to_role(element["tag_name"])
    #         if role and element.get("label_text"):
    #             strategies.append((lambda: page.get_by_role(role, name=element["label_text"]), f"get_by_role({role}, name={element['label_text']})"))

    #     if element.get("label_text"):
    #         strategies.append((lambda: page.get_by_label(element["label_text"]), f"get_by_label({element['label_text']})"))

    #     if element.get("placeholder"):
    #         strategies.append((lambda: page.get_by_placeholder(element["placeholder"]), f"get_by_placeholder({element['placeholder']})"))

    #     if element.get("label_text"):
    #         strategies.append((lambda: page.get_by_text(element["label_text"], exact=True), f"get_by_text({element['label_text']}, exact=True)"))

    #     if element.get("sample_value"):
    #         strategies.append((lambda: page.get_by_display_value(element["sample_value"]), f"get_by_display_value({element['sample_value']})"))

    #     if element.get("dom_id"):
    #         id_value = element["dom_id"]
    #         strategies.append((lambda: page.locator(f'#{id_value}'), f"locator(#{id_value}) [ID exact]"))
    #         strategies.append((lambda: page.locator(f'[id*="{id_value}"]'), f'locator([id*="{id_value}"]) [ID partial]'))

    #     if element.get("dom_class"):
    #         class_value = element["dom_class"]
    #         class_sel = "." + ".".join(class_value.split())
    #         strategies.append((lambda: page.locator(class_sel), f"locator({class_sel}) [class exact]"))
    #         strategies.append((lambda: page.locator(f'[class*="{class_value}"]'), f'locator([class*="{class_value}"]) [class partial]'))

    #     if element.get("class_list"):
    #         sel = "." + ".".join(element["class_list"])
    #         strategies.append((lambda: page.locator(sel), f"locator({sel}) [class_list]"))

    #     if element.get("locator") and element["locator"].get("type") == "css":
    #         strategies.append((lambda: page.locator(element["locator"]["value"]), f"locator({element['locator']['value']}) [custom css]"))

    #     # Attempt strategies in order, skipping if penalized
    #     for func, desc in strategies:
    #         try:
    #             locator = func()
    #             # 2️⃣ Only check .count() once per strategy, early return
    #             if locator and locator.count() > 0:
    #                 print(f"[SmartAI][Return] {desc} succeeded.")
    #                 self.locator_fail_count[element.get("unique_name")] = 0  # Reset fail count
    #                 return locator.last
    #         except Exception as e:
    #             # 10️⃣ Track fail count for this unique_name
    #             unique_name = element.get("unique_name", "")
    #             self.locator_fail_count[unique_name] = self.locator_fail_count.get(unique_name, 0) + 1
    #             print(f"[SmartAI][Skip] {desc} failed: {e}")

    #     print("[SmartAI][Return] No locator found for element.")
    #     return None

    def find_element(self, unique_name, page):
        # Main entry for SmartAI: tries direct lookup, then ML self-healing, then heuristics.
        element = self._find_by_unique_name(unique_name)
        if element:
            locator = self._try_all_locators(element, page)
            if locator:
                print(f"[SmartAI] Element '{unique_name}' found using primary metadata.")
                return SmartAIWrappedLocator(locator, page)  # <--- PATCHED

            print(f"[SmartAI] Primary methods failed for '{unique_name}', trying ML self-healing...")

        # ML-based fallback
        element_ml, ml_score = self._ml_self_heal(unique_name)
        if element_ml:
            locator_ml = self._try_all_locators(element_ml, page)
            if locator_ml:
                print(f"[SmartAI] Healed element via ML ({ml_score:.2f}): '{element_ml.get('unique_name')}'")
                return SmartAIWrappedLocator(locator_ml, page)  # <--- PATCHED

        # 9️⃣ Intent-aware fallback: try other elements with same intent
        target_intent = element_ml.get("intent") if element_ml else None
        if target_intent:
            for e in self.metadata:
                if e.get("intent") == target_intent and e.get("unique_name") != unique_name:
                    locator = self._try_all_locators(e, page)
                    if locator:
                        print(f"[SmartAI] Healed element by intent ('{target_intent}'): '{e.get('unique_name')}'")
                        return SmartAIWrappedLocator(locator, page)  # <--- PATCHED

        # 11️⃣ Visual/position fallback (commented for extension)
        # print("[SmartAI] Trying fallback by position (not implemented)...")

        raise SmartAILocatorError(f"Element '{unique_name}' not found and cannot self-heal.")

    def _find_by_unique_name(self, unique_name):
        return next((e for e in self.metadata if e.get("unique_name") == unique_name), None)

    def _map_tag_to_role(self, tag):
        tag_role_map = {
            'button': 'button',
            'input': 'textbox',
            'select': 'combobox',
            'textarea': 'textbox',
            'checkbox': 'checkbox'
        }
        return tag_role_map.get(tag.lower(), None)

    def _ml_self_heal(self, unique_name):
        # Returns best-matched element and score.
        # Enhancement: Uses pre-cached embeddings for performance!
        # 3️⃣ Uses higher threshold for accuracy.
        query_embedding = self.model.encode(unique_name, convert_to_tensor=True, show_progress_bar=False)
        scores = [util.cos_sim(query_embedding, emb).item() for emb in self.embeddings]
        best_idx = int(np.argmax(scores))
        best_score = scores[best_idx]
        print(f"[SmartAI] ML healed best match score: {best_score:.2f}")
        # 3️⃣ Higher threshold (was 0.3, now 0.6)
        return (self.metadata[best_idx], best_score) if best_score > 0.6 else (None, best_score)

    def _element_to_string(self, element):
        # Enhancement: Fast string construction, no json.dumps.
        fields = [
            element.get("unique_name", ""),
            element.get("label_text", ""),
            element.get("intent", ""),
            element.get("ocr_type", ""),
            element.get("element_type", ""),
            element.get("tag_name", ""),
            element.get("placeholder", ""),
            " ".join(element.get("class_list", [])) if element.get("class_list") else "",
            # 4️⃣ Fast join for data_attrs
            " ".join(f"{k}:{v}" for k, v in (element.get("data_attrs", {}) or {}).items()),
            element.get("sample_value", ""),
        ]
        return " ".join([str(f) for f in fields if f])

# ====== PAGE PATCH ======
def patch_page_with_smartai(page, metadata):
    ai_healer = SmartAISelfHealing(metadata)
    def smartAI(unique_name):
        return ai_healer.find_element(unique_name, page)
    page.smartAI = smartAI
    return page
"""

def ensure_smart_ai_module():
    lib_path = Path("generated_runs/src/lib")
    lib_path.mkdir(parents=True, exist_ok=True)
    # --- ADD THIS LINE! ---
    (lib_path / "__init__.py").touch()
    # ----------------------
    smart_ai_file = lib_path / "smart_ai.py"
    if not smart_ai_file.exists():
        smart_ai_file.write_text(SMART_AI_CODE, encoding="utf-8")



# === FILE: utils\test.py ===
def filter_dom_matched_elements(page_name: str):
    return [r for r in collection.get(where={"page_name": page_name}).get("metadatas", []) if r.get("dom_matched")]

def sanitize_identifier(label: str) -> str:
    return re.sub(r'\W|^(?=\d)', '_', label.lower()) if label else "element"

def generate_page_object_class(page_name: str, locators: list[dict]) -> tuple[str, dict]:
    class_name = get_class_name(page_name)
    base_url = os.getenv("BASE_URL", "https://www.saucedemo.com/")
    lines = [
        "from playwright.sync_api import Page, expect",
        f"class {class_name}:",
        "    def __init__(self, page: Page):",
        "        self.page = page",
        "",
        "    def navigate_to_site(self):",
        f"        print(\"Navigating to site...\")",
        f"        self.page.goto('{base_url}')",
        ""
    ]
    method_names = {}

    for loc in locators:
        raw_label = (
            loc.get("label_text")
            or loc.get("text")
            or loc.get("placeholder")
            or loc.get("aria_label")
            or loc.get("name")
            or loc.get("id")
        )
        if not raw_label:
            continue

        label = generalize_label(raw_label)
        tag = loc.get("tag_name", "").lower()
        selector = loc.get("css") or f"text={label}"
        safe = sanitize_identifier(label)

        lines += [
            f"    def click_{safe}(self):",
            f"        print(\"Clicking {label}\")",
            f"        self.page.locator(\"{selector}\").click()",
            ""
        ]
        method_names.setdefault(label, []).append(f"click_{safe}()")

        if tag in ["input", "textarea", "select"]:
            lines += [
                f"    def fill_{safe}(self, value):",
                f"        print(\"Filling {label} with value\")",
                f"        self.page.locator(\"{selector}\").fill(value)",
                ""
            ]
            method_names[label].append(f"fill_{safe}(value)")

        lines += [
            f"    def expect_{safe}_visible(self):",
            f"        print(\"Expecting {label} to be visible\")",
            f"        expect(self.page.locator(\"{selector}\")).to_be_visible()",
            ""
        ]
        method_names[label].append(f"expect_{safe}_visible()")

    return "\n".join(lines), method_names

def generate_test_code_from_gpt(page_names: list[str], method_info: dict, source_url: str) -> str:
    prompt = f"""
You are a senior QA automation engineer.
Generate a complete Python Playwright test function called `test_end_to_end()`.

Instructions:
- Only write one test function `test_end_to_end()`
- Assume the following classes are already defined and imported:
{', '.join(get_class_name(page) for page in page_names)}
- Use:
with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
- Instantiate page objects like: `page_obj = ClassName(page)`
- Use only the available methods:
"""
    for page in page_names:
        prompt += f"\n# {get_class_name(page)}:\n"
        for method in method_info.get(page, []):
            prompt += f"- {method}\n"

    prompt += f"""
- Print "[PASS]" if successful, "[CRASH]" if any exception occurs
- End the test with `browser.close()`
- Do NOT include import statements, markdown, or comments
- Do NOT define any page classes; assume they are already imported

Target URL: {source_url}
Return ONLY executable Python code for test_end_to_end() with `if __name__ == "__main__"` block.
"""

    result = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=2000
    )
    return result.choices[0].message.content.strip()



# === FILE: utils\__init__.py ===

