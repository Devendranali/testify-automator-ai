

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
2025-08-04 15:02:58,379 - INFO - 🟢 Ordered images from frontend: ['login.png', 'inventory.png', 'cart.png', 'checkout_info.png', 'checkout_overview.png']
2025-08-04 15:02:58,578 - DEBUG - 📷 Processing image: login.png
2025-08-04 15:03:09,825 - DEBUG - 📷 Processing image: inventory.png
2025-08-04 15:03:29,228 - DEBUG - 📷 Processing image: cart.png
2025-08-04 15:03:39,334 - DEBUG - 📷 Processing image: checkout_info.png
2025-08-04 15:03:45,946 - DEBUG - 📷 Processing image: checkout_overview.png
2025-08-04 15:04:06,832 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-08-04 15:04:06,834 - INFO - 📄 Ordered images logged to data/image_order.json
2025-08-06 19:44:35,942 - INFO - 🟢 Ordered images from frontend: ['customers.png', 'dashboard.png', 'customers_2.png']
2025-08-06 19:44:36,113 - DEBUG - 📷 Processing image: customers.png
2025-08-06 19:45:03,827 - DEBUG - 📷 Processing image: customers_2.png
2025-08-06 19:45:16,484 - DEBUG - 📷 Processing image: dashboard.png
2025-08-06 19:45:38,588 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-08-06 19:45:38,590 - INFO - 📄 Ordered images logged to data/image_order.json
2025-08-07 11:27:59,301 - INFO - 🟢 Ordered images from frontend: ['dashboard.png', 'customers.png', 'customers_2.png']
2025-08-07 11:27:59,649 - DEBUG - 📷 Processing image: dashboard.png
2025-08-07 11:28:22,133 - DEBUG - 📷 Processing image: customers.png
2025-08-07 11:28:45,784 - DEBUG - 📷 Processing image: customers_2.png
2025-08-07 11:28:59,371 - INFO - 📄 Dependency graph stored in data/dependency_graph.json
2025-08-07 11:28:59,374 - INFO - 📄 Ordered images logged to data/image_order.json



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
        # e.g. ['from pages.dashboard_page import DashboardPage']
        page_imports = test_case_spec["imports"]
        # e.g. ['await page.enter_username("standard_user")', ...]
        method_calls = test_case_spec["calls"]
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
        class_name = f"{''.join([word.capitalize() for word in page_name.split('_')])}Page"

        import_block = (
            "import asyncio\n"
            "from services.page_enricher import enrich_page\n"
            "from utils.enrichment_status import is_enriched\n"
        )

        class_header = (
            f"\n\nclass {class_name}(BasePage):\n"
            f"    def __init__(self, page=None, page_name=\"{page_name}\"):\n"
            f"        super().__init__(page, page_name)\n"
            f"        self._enriched = False\n"
            f"        metadata = self._fetch_metadata_from_chroma(page_name)\n"
            f"        patch_page_with_smartai(self.page, metadata)\n\n"
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

            # --- All methods use locator assignment first ---
            if ocr_type in ("textbox", "text", "textarea", "password", "email", "input"):
                method_name = f"enter_{base_name}"
                block = (
                    f"    async def {method_name}(self, value):\n"
                    f"        await self._enrich_if_needed()\n"
                    f"        locator = await self.page.smartAI('{smartai_name}')\n"
                    f"        await locator.fill(value)\n"
                )

            elif ocr_type in ("button", "submit", "link", "iconbutton", "imagebutton", "tab", "panel", "accordion", "menu", "breadcrumb"):
                method_name = f"click_{base_name}"
                block = (
                    f"    async def {method_name}(self):\n"
                    f"        await self._enrich_if_needed()\n"
                    f"        locator = await self.page.smartAI('{smartai_name}')\n"
                    f"        await locator.click()\n"
                )

            elif ocr_type in ("select", "dropdown", "combobox"):
                method_name = f"select_{base_name}"
                block = (
                    f"    async def {method_name}(self, value):\n"
                    f"        await self._enrich_if_needed()\n"
                    f"        locator = await self.page.smartAI('{smartai_name}')\n"
                    f"        await locator.select_option(value)\n"
                )

            elif ocr_type == "multiselect":
                method_name = f"select_{base_name}_values"
                block = (
                    f"    async def {method_name}(self, values):\n"
                    f"        await self._enrich_if_needed()\n"
                    f"        locator = await self.page.smartAI('{smartai_name}')\n"
                    f"        await locator.select_options(values)\n"
                )

            elif ocr_type in ("checkbox", "switch", "toggle"):
                method_name = f"toggle_{base_name}"
                block = (
                    f"    async def {method_name}(self):\n"
                    f"        await self._enrich_if_needed()\n"
                    f"        locator = await self.page.smartAI('{smartai_name}')\n"
                    f"        await locator.click()\n"
                )

            elif ocr_type in ("date", "datepicker", "time", "timepicker", "slider", "range"):
                method_name = f"set_{base_name}"
                block = (
                    f"    async def {method_name}(self, value):\n"
                    f"        await self._enrich_if_needed()\n"
                    f"        locator = await self.page.smartAI('{smartai_name}')\n"
                    f"        await locator.fill(value)\n"
                )

            elif ocr_type in ("image", "avatar", "userpic", "badge", "chip", "tag", "alert", "modal", "toast", "dialog", "label"):
                method_name = f"verify_{base_name}_visible"
                block = (
                    f"    async def {method_name}(self):\n"
                    f"        await self._enrich_if_needed()\n"
                    f"        locator = await self.page.smartAI('{smartai_name}')\n"
                    f"        assert await locator.is_visible()\n"
                )

            elif ocr_type == "pagination":
                method_name = f"goto_{base_name}"
                block = (
                    f"    async def {method_name}(self, page_number):\n"
                    f"        await self._enrich_if_needed()\n"
                    f"        locator = await self.page.smartAI('{smartai_name}')\n"
                    f"        await locator.goto_page(page_number)\n"
                )

            elif ocr_type in ("table", "grid", "datatable"):
                method_name = f"read_{base_name}_data"
                block = (
                    f"    async def {method_name}(self):\n"
                    f"        await self._enrich_if_needed()\n"
                    f"        locator = await self.page.smartAI('{smartai_name}')\n"
                    f"        return await locator.get_table_data()\n"
                )

            elif ocr_type in ("file", "upload", "fileinput"):
                method_name = f"upload_{base_name}"
                block = (
                    f"    async def {method_name}(self, file_path):\n"
                    f"        await self._enrich_if_needed()\n"
                    f"        locator = await self.page.smartAI('{smartai_name}')\n"
                    f"        await locator.set_input_files(file_path)\n"
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



# === FILE: apis\customers.json ===
{
    "ids": [
        "fc6b0e65-8ffb-4695-92aa-0c3ebc82bf72",
        "7e56e647-e531-44be-88b8-466a63c7c2ac",
        "e2e25454-025d-4d10-b125-d2174618dfe2",
        "f50f575d-109d-4a6d-8916-2fb8045c4bfc",
        "4f7a3d85-62f9-49a2-9c13-f33d69217b43",
        "d260e470-0460-42ad-a57e-0b8da2c9f190",
        "a941fd52-fa54-4252-8100-dadaa1a06747",
        "559f3a75-6f90-4af9-911d-67406cff9e79",
        "229671c9-f7e8-427f-af4b-6410a8dfeb31",
        "fef318bb-171d-4e29-905a-0c7a69d46bcc",
        "b444aebb-dc8b-4611-bf97-6445db2f8b7a",
        "fad65ef2-a270-41e4-bc76-d0e0303b0876",
        "4a2581bb-3a36-402a-917a-56f080503349",
        "2ee1f23a-7ca9-4f4d-a230-fe8d2b575bb3",
        "e07b8c7b-bfa1-4b03-97c7-080235aeda0c",
        "f805fcda-46e4-4da5-afe2-b6b23f375f6d",
        "fc2edce7-0d6f-4f3b-8415-60a9b3e77741",
        "d7b1c255-9d39-4c0b-a771-f015ec1860e0",
        "838f3761-f89c-472d-beb5-3e7f6ddd29a0",
        "b8c183db-497d-4cfe-b92a-b160c48f0c5c",
        "9e7bdd63-ac1d-426b-836c-ad90a7e8c91d",
        "f702bde6-2277-401b-a5dd-afaad03e8ea5",
        "6f667768-b763-438e-9b00-76f7f7ec0567",
        "c514ead6-e25a-4f51-ae3f-9ec03546bd97",
        "26dac36b-3665-49e8-a083-b1af2f77825c",
        "0a174e5a-de46-45b0-b0ea-93c499676998",
        "f4f609a1-be0a-469a-b87b-3c2f727226d2",
        "a0452d6a-1a92-4dca-80d1-96d044d4b0b9",
        "9ed36159-2ee6-4eb6-9a98-6dc73d244c64",
        "07852be5-0170-4093-812d-a4d396507405",
        "d1844027-a515-44df-9776-e8651e8296d6",
        "62b2565e-81b3-4406-8a96-c504bcc58179",
        "e2f8d6cb-4397-44c2-a7a2-f12442846c72",
        "338dcf5c-c760-440a-b749-cd8c1166587c",
        "b6c0bf5d-bce1-402c-86c3-6bfb7aaeeb2c",
        "427ef217-7188-4883-9e2d-1e30c7a200c7",
        "a5f93c70-1552-4412-b3d0-b85629e76c31",
        "d0359914-eb55-465b-9181-1ae0ede4305e",
        "caef0247-1d74-40ba-996c-2ace81dcb1fa",
        "0e97e660-04a4-41f4-92ec-64632780f724",
        "b0735fce-9fbc-45f1-92cc-2e2e8a71baa3",
        "e271b4dc-24c9-46b9-9f2e-ed0475690e5e",
        "01c9b209-9793-47f1-8c48-b23926042e2f",
        "50db0a7b-af9f-425b-bdcf-db3d148f33a9",
        "70c78a9e-b303-43a7-8c1d-cb4ee9bdb44e",
        "7bfb4221-3707-44ad-84df-f557035b54cb",
        "2be6c9d3-3652-4a50-981b-12ffc22cfb8e",
        "60c33e4b-117c-4d68-89df-7445e5943a2a",
        "4584aad1-4df3-4687-ad41-104188164d62",
        "aac3525b-7019-4e3b-841d-1a08585d5a69",
        "8619662f-c77d-4ca1-a12c-7943e9ff34a5",
        "ee51dd1a-e474-4735-a5f5-f4399f086745",
        "bd4edd12-0ee7-400a-b0a0-ee7ab3de9487",
        "0cdd71d2-b258-4086-a727-6541be3eb560",
        "f6398f05-5ab8-4b47-8f19-777badc36a6e",
        "1791d135-cc42-4f99-823c-84ae162f00a7",
        "7a53f093-3d9e-4f96-9d83-27d3107113fd",
        "4e2f9a0f-ec4f-421a-aa84-81d3574ec36e",
        "7e9e6770-a376-40f5-9725-418a43f12a21",
        "53d41797-0aba-4655-8964-578918ce2fc5",
        "a771d766-6ffe-4728-8d9d-76b213fe254b"
    ],
    "embeddings": null,
    "documents": [
        "",
        "Search customers, loans, transactions...",
        "Dashboard",
        "Search customers, loans, transactions...",
        "Search customers, loans, transactions...",
        "Transactions",
        "Tasks",
        "Export Report",
        "Analytics",
        "Settings",
        "Search customers, loans, transactions...",
        "Manage your customer relationships and accounts",
        "Search customers, loans, transactions...",
        "Filters",
        "Customer List",
        "3 customers found",
        "Customer",
        "Account Type",
        "Balance",
        "Status",
        "Join Date",
        "Actions",
        "Sarah Johnson",
        "sarah.johnson@email.com",
        "Premium 35%",
        "4500000",
        "Active",
        "2023-01-15",
        "",
        "",
        "Michael Chen",
        "michael.chen@email.com",
        "Standard 45%",
        "$52,000",
        "2023-03-22",
        "Emma Davis",
        "emma.davis@email.com",
        "$89,000",
        "2022-11-08",
        "Export Report",
        "New Customer",
        "Add New Customer",
        "Enter the customer details to create a new account.",
        "Full Name",
        "",
        "Email",
        "",
        "Phone Number",
        "",
        "Account Type",
        "Select account type",
        "Address",
        "",
        "Occupation",
        "",
        "Annual Income",
        "",
        "Initial Deposit",
        "",
        "Cancel",
        "Add Customer"
    ],
    "uris": null,
    "included": [
        "metadatas",
        "documents"
    ],
    "data": null,
    "metadatas": [
        {
            "external": false,
            "placeholder": "",
            "label_text": "",
            "dom_matched": false,
            "ocr_type": "button",
            "page_name": "customers",
            "type": "ocr",
            "intent": "navigation",
            "unique_name": "customers_button_navigation_6ab61bef",
            "get_by_text": "",
            "element_id": "fc6b0e65-8ffb-4695-92aa-0c3ebc82bf72"
        },
        {
            "unique_name": "customers_search_customers,_loans,_transactions..._textbox_search_be73039f",
            "external": false,
            "y": 16,
            "dom-id": "",
            "match_timestamp": "2025-08-07T04:22:27.377009",
            "enable": true,
            "value": "",
            "editable": true,
            "placeholder": "Search customers, loans, transactions...",
            "dom_class": "flex h-10 rounded-md border border-input bg-background px-3 py-2 text-base ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium file:text-foreground placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 md:text-sm pl-10 w-96",
            "label_text": "Search customers, loans, transactions...",
            "type": "text",
            "get_by_text": "Search customers, loans, transactions...",
            "tag_name": "input",
            "visible": true,
            "x": 324,
            "element_id": "7e56e647-e531-44be-88b8-466a63c7c2ac",
            "page_name": "customers",
            "width": 384,
            "height": 40,
            "dom_matched": true,
            "ocr_type": "textbox",
            "intent": "search"
        },
        {
            "element_id": "e2e25454-025d-4d10-b125-d2174618dfe2",
            "ocr_type": "button",
            "page_name": "customers",
            "external": false,
            "intent": "navigation",
            "placeholder": "Dashboard",
            "get_by_text": "Dashboard",
            "dom_matched": false,
            "unique_name": "customers_dashboard_button_navigation_fb22376c",
            "type": "ocr",
            "label_text": "Dashboard"
        },
        {
            "dom_matched": true,
            "y": 16,
            "value": "",
            "element_id": "f50f575d-109d-4a6d-8916-2fb8045c4bfc",
            "external": false,
            "placeholder": "Search customers, loans, transactions...",
            "dom-id": "",
            "width": 384,
            "unique_name": "customers_customers_button_navigation_62cd2bf8",
            "height": 40,
            "match_timestamp": "2025-08-07T04:22:27.517694",
            "type": "text",
            "visible": true,
            "x": 324,
            "intent": "navigation",
            "editable": true,
            "ocr_type": "button",
            "label_text": "Search customers, loans, transactions...",
            "enable": true,
            "get_by_text": "Customers",
            "tag_name": "input",
            "dom_class": "flex h-10 rounded-md border border-input bg-background px-3 py-2 text-base ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium file:text-foreground placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 md:text-sm pl-10 w-96",
            "page_name": "customers"
        },
        {
            "value": "",
            "visible": true,
            "type": "text",
            "dom-id": "",
            "dom_matched": true,
            "editable": true,
            "label_text": "Search customers, loans, transactions...",
            "get_by_text": "Loans",
            "page_name": "customers",
            "height": 40,
            "tag_name": "input",
            "intent": "navigation",
            "x": 324,
            "enable": true,
            "match_timestamp": "2025-08-07T04:22:27.601089",
            "width": 384,
            "unique_name": "customers_loans_button_navigation_f083cd47",
            "y": 16,
            "dom_class": "flex h-10 rounded-md border border-input bg-background px-3 py-2 text-base ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium file:text-foreground placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 md:text-sm pl-10 w-96",
            "element_id": "4f7a3d85-62f9-49a2-9c13-f33d69217b43",
            "external": false,
            "placeholder": "Search customers, loans, transactions...",
            "ocr_type": "button"
        },
        {
            "page_name": "customers",
            "intent": "navigation",
            "element_id": "d260e470-0460-42ad-a57e-0b8da2c9f190",
            "unique_name": "customers_transactions_button_navigation_bb833203",
            "external": false,
            "get_by_text": "Transactions",
            "ocr_type": "button",
            "placeholder": "Transactions",
            "type": "ocr",
            "label_text": "Transactions",
            "dom_matched": false
        },
        {
            "element_id": "a941fd52-fa54-4252-8100-dadaa1a06747",
            "ocr_type": "button",
            "dom_matched": false,
            "placeholder": "Tasks",
            "type": "ocr",
            "label_text": "Tasks",
            "unique_name": "customers_tasks_button_navigation_63e52ff9",
            "get_by_text": "Tasks",
            "intent": "navigation",
            "external": false,
            "page_name": "customers"
        },
        {
            "element_id": "559f3a75-6f90-4af9-911d-67406cff9e79",
            "tag_name": "button",
            "y": 111,
            "type": "submit",
            "match_timestamp": "2025-08-07T04:22:27.733948",
            "x": 1096.21875,
            "dom_class": "justify-center whitespace-nowrap rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0 bg-primary text-primary-foreground hover:bg-primary/90 h-10 px-4 py-2 flex items-center gap-2",
            "ocr_type": "button",
            "value": "",
            "placeholder": "",
            "dom_matched": true,
            "unique_name": "customers_reports_button_navigation_1dc35b9f",
            "dom-id": "",
            "intent": "navigation",
            "width": 144.78125,
            "get_by_text": "Reports",
            "external": false,
            "enable": true,
            "visible": true,
            "height": 40,
            "page_name": "customers",
            "editable": false,
            "label_text": "Export Report"
        },
        {
            "get_by_text": "Analytics",
            "intent": "navigation",
            "element_id": "229671c9-f7e8-427f-af4b-6410a8dfeb31",
            "unique_name": "customers_analytics_button_navigation_8227d101",
            "ocr_type": "button",
            "external": false,
            "page_name": "customers",
            "dom_matched": false,
            "label_text": "Analytics",
            "placeholder": "Analytics",
            "type": "ocr"
        },
        {
            "page_name": "customers",
            "ocr_type": "button",
            "type": "ocr",
            "element_id": "fef318bb-171d-4e29-905a-0c7a69d46bcc",
            "get_by_text": "Settings",
            "unique_name": "customers_settings_button_navigation_9de99b8a",
            "dom_matched": false,
            "placeholder": "Settings",
            "intent": "navigation",
            "label_text": "Settings",
            "external": false
        },
        {
            "y": 16,
            "page_name": "customers",
            "match_timestamp": "2025-08-07T04:22:27.871353",
            "label_text": "Search customers, loans, transactions...",
            "element_id": "b444aebb-dc8b-4611-bf97-6445db2f8b7a",
            "value": "",
            "dom_class": "flex h-10 rounded-md border border-input bg-background px-3 py-2 text-base ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium file:text-foreground placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 md:text-sm pl-10 w-96",
            "dom-id": "",
            "width": 384,
            "dom_matched": true,
            "x": 324,
            "ocr_type": "label",
            "unique_name": "customers_customers_label_section_title_2ec8510a",
            "height": 40,
            "type": "text",
            "get_by_text": "Customers",
            "intent": "section_title",
            "placeholder": "Search customers, loans, transactions...",
            "enable": true,
            "tag_name": "input",
            "editable": true,
            "external": false,
            "visible": true
        },
        {
            "placeholder": "Manage your customer relationships and accounts",
            "page_name": "customers",
            "external": false,
            "dom_matched": false,
            "ocr_type": "label",
            "type": "ocr",
            "unique_name": "customers_manage_your_customer_relationships_and_accounts_label_section_info_f20c0595",
            "intent": "section_info",
            "element_id": "fad65ef2-a270-41e4-bc76-d0e0303b0876",
            "get_by_text": "Manage your customer relationships and accounts",
            "label_text": "Manage your customer relationships and accounts"
        },
        {
            "external": false,
            "value": "",
            "page_name": "customers",
            "ocr_type": "textbox",
            "y": 16,
            "label_text": "Search customers, loans, transactions...",
            "editable": true,
            "element_id": "4a2581bb-3a36-402a-917a-56f080503349",
            "visible": true,
            "unique_name": "customers_search_customers..._textbox_search_85d3ce1f",
            "dom_matched": true,
            "tag_name": "input",
            "enable": true,
            "placeholder": "Search customers, loans, transactions...",
            "dom_class": "flex h-10 rounded-md border border-input bg-background px-3 py-2 text-base ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium file:text-foreground placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 md:text-sm pl-10 w-96",
            "width": 384,
            "dom-id": "",
            "match_timestamp": "2025-08-07T04:22:27.995289",
            "type": "text",
            "height": 40,
            "get_by_text": "Search customers...",
            "intent": "search",
            "x": 324
        },
        {
            "intent": "filter",
            "label_text": "Filters",
            "unique_name": "customers_filters_button_filter_4c0a3d63",
            "element_id": "2ee1f23a-7ca9-4f4d-a230-fe8d2b575bb3",
            "dom_matched": false,
            "external": false,
            "page_name": "customers",
            "ocr_type": "button",
            "placeholder": "Filters",
            "type": "ocr",
            "get_by_text": "Filters"
        },
        {
            "unique_name": "customers_customer_list_label_section_title_ad47eb6a",
            "ocr_type": "label",
            "get_by_text": "Customer List",
            "intent": "section_title",
            "dom_matched": false,
            "placeholder": "Customer List",
            "element_id": "e07b8c7b-bfa1-4b03-97c7-080235aeda0c",
            "label_text": "Customer List",
            "type": "ocr",
            "page_name": "customers",
            "external": false
        },
        {
            "element_id": "f805fcda-46e4-4da5-afe2-b6b23f375f6d",
            "label_text": "3 customers found",
            "dom_matched": false,
            "intent": "info",
            "ocr_type": "label",
            "page_name": "customers",
            "placeholder": "3 customers found",
            "unique_name": "customers_3_customers_found_label_info_61b9a471",
            "type": "ocr",
            "external": false,
            "get_by_text": "3 customers found"
        },
        {
            "external": false,
            "element_id": "fc2edce7-0d6f-4f3b-8415-60a9b3e77741",
            "type": "ocr",
            "ocr_type": "label",
            "intent": "column_title",
            "page_name": "customers",
            "unique_name": "customers_customer_label_column_title_01dacf22",
            "dom_matched": false,
            "get_by_text": "Customer",
            "placeholder": "Customer",
            "label_text": "Customer"
        },
        {
            "label_text": "Account Type",
            "external": false,
            "element_id": "d7b1c255-9d39-4c0b-a771-f015ec1860e0",
            "unique_name": "customers_account_type_label_column_title_1b2a9c41",
            "ocr_type": "label",
            "get_by_text": "Account Type",
            "intent": "column_title",
            "placeholder": "Account Type",
            "dom_matched": false,
            "type": "ocr",
            "page_name": "customers"
        },
        {
            "placeholder": "Balance",
            "label_text": "Balance",
            "external": false,
            "type": "ocr",
            "unique_name": "customers_balance_label_column_title_a5832ecf",
            "ocr_type": "label",
            "get_by_text": "Balance",
            "page_name": "customers",
            "dom_matched": false,
            "element_id": "838f3761-f89c-472d-beb5-3e7f6ddd29a0",
            "intent": "column_title"
        },
        {
            "unique_name": "customers_status_label_column_title_b24a10b1",
            "page_name": "customers",
            "element_id": "b8c183db-497d-4cfe-b92a-b160c48f0c5c",
            "label_text": "Status",
            "dom_matched": false,
            "placeholder": "Status",
            "get_by_text": "Status",
            "intent": "column_title",
            "external": false,
            "type": "ocr",
            "ocr_type": "label"
        },
        {
            "placeholder": "Join Date",
            "intent": "column_title",
            "get_by_text": "Join Date",
            "element_id": "9e7bdd63-ac1d-426b-836c-ad90a7e8c91d",
            "external": false,
            "type": "ocr",
            "unique_name": "customers_join_date_label_column_title_c808519b",
            "dom_matched": false,
            "ocr_type": "label",
            "page_name": "customers",
            "label_text": "Join Date"
        },
        {
            "element_id": "f702bde6-2277-401b-a5dd-afaad03e8ea5",
            "placeholder": "Actions",
            "get_by_text": "Actions",
            "dom_matched": false,
            "label_text": "Actions",
            "intent": "column_title",
            "ocr_type": "label",
            "external": false,
            "type": "ocr",
            "page_name": "customers",
            "unique_name": "customers_actions_label_column_title_32bd0b21"
        },
        {
            "unique_name": "customers_sarah_johnson_label_customer_name_91134cc9",
            "get_by_text": "Sarah Johnson",
            "label_text": "Sarah Johnson",
            "ocr_type": "label",
            "type": "ocr",
            "external": false,
            "dom_matched": false,
            "page_name": "customers",
            "element_id": "6f667768-b763-438e-9b00-76f7f7ec0567",
            "placeholder": "Sarah Johnson",
            "intent": "customer_name"
        },
        {
            "ocr_type": "label",
            "placeholder": "sarah.johnson@email.com",
            "type": "ocr",
            "page_name": "customers",
            "dom_matched": false,
            "external": false,
            "get_by_text": "sarah.johnson@email.com",
            "intent": "customer_email",
            "element_id": "c514ead6-e25a-4f51-ae3f-9ec03546bd97",
            "unique_name": "customers_sarah.johnson@email.com_label_customer_email_ea79968a",
            "label_text": "sarah.johnson@email.com"
        },
        {
            "external": false,
            "dom-id": "",
            "height": 21,
            "visible": true,
            "page_name": "customers",
            "placeholder": "",
            "tag_name": "g",
            "intent": "account_type",
            "label_text": "Premium 35%",
            "dom_class": "{}",
            "ocr_type": "label",
            "unique_name": "customers_premium_label_account_type_c1ae4279",
            "x": 1052.3990478515625,
            "editable": false,
            "enable": true,
            "element_id": "26dac36b-3665-49e8-a083-b1af2f77825c",
            "type": "",
            "dom_matched": true,
            "get_by_text": "Premium",
            "width": 98.109375,
            "value": "",
            "y": 569.8993530273438,
            "match_timestamp": "2025-08-07T04:22:28.345780"
        },
        {
            "type": "",
            "width": 69.375,
            "label_text": "4500000",
            "enable": true,
            "match_timestamp": "2025-08-07T04:22:28.423930",
            "tag_name": "g",
            "unique_name": "customers_$1,45,000_label_balance_dc74e6a8",
            "page_name": "customers",
            "placeholder": "",
            "value": "",
            "visible": true,
            "editable": false,
            "intent": "balance",
            "dom_class": "{}",
            "x": 300.625,
            "y": 584.6799926757812,
            "height": 21,
            "external": false,
            "dom_matched": true,
            "ocr_type": "label",
            "element_id": "0a174e5a-de46-45b0-b0ea-93c499676998",
            "dom-id": "",
            "get_by_text": "$1,45,000"
        },
        {
            "unique_name": "customers_active_label_status_5fc1bbb1",
            "ocr_type": "label",
            "element_id": "f4f609a1-be0a-469a-b87b-3c2f727226d2",
            "intent": "status",
            "external": false,
            "dom_matched": false,
            "placeholder": "Active",
            "page_name": "customers",
            "label_text": "Active",
            "get_by_text": "Active",
            "type": "ocr"
        },
        {
            "dom_matched": false,
            "unique_name": "customers_2023-01-15_label_join_date_13b4a3e0",
            "intent": "join_date",
            "type": "ocr",
            "placeholder": "2023-01-15",
            "external": false,
            "ocr_type": "label",
            "label_text": "2023-01-15",
            "element_id": "a0452d6a-1a92-4dca-80d1-96d044d4b0b9",
            "page_name": "customers",
            "get_by_text": "2023-01-15"
        },
        {
            "unique_name": "customers_button_view_action_cc60ce91",
            "intent": "view_action",
            "dom_matched": false,
            "placeholder": "",
            "page_name": "customers",
            "element_id": "9ed36159-2ee6-4eb6-9a98-6dc73d244c64",
            "ocr_type": "button",
            "label_text": "",
            "external": false,
            "type": "ocr",
            "get_by_text": ""
        },
        {
            "dom_matched": false,
            "type": "ocr",
            "unique_name": "customers_button_edit_action_d3d0df61",
            "placeholder": "",
            "label_text": "",
            "external": false,
            "get_by_text": "",
            "intent": "edit_action",
            "page_name": "customers",
            "ocr_type": "button",
            "element_id": "07852be5-0170-4093-812d-a4d396507405"
        },
        {
            "intent": "customer_name",
            "label_text": "Michael Chen",
            "external": false,
            "page_name": "customers",
            "element_id": "d1844027-a515-44df-9776-e8651e8296d6",
            "unique_name": "customers_michael_chen_label_customer_name_8dbd8345",
            "get_by_text": "Michael Chen",
            "ocr_type": "label",
            "placeholder": "Michael Chen",
            "dom_matched": false,
            "type": "ocr"
        },
        {
            "intent": "customer_email",
            "unique_name": "customers_michael.chen@email.com_label_customer_email_8f50f16b",
            "placeholder": "michael.chen@email.com",
            "get_by_text": "michael.chen@email.com",
            "label_text": "michael.chen@email.com",
            "external": false,
            "ocr_type": "label",
            "dom_matched": false,
            "element_id": "62b2565e-81b3-4406-8a96-c504bcc58179",
            "page_name": "customers",
            "type": "ocr"
        },
        {
            "dom-id": "",
            "ocr_type": "label",
            "y": 704.3990478515625,
            "editable": false,
            "tag_name": "g",
            "page_name": "customers",
            "dom_class": "{}",
            "value": "",
            "external": false,
            "element_id": "e2f8d6cb-4397-44c2-a7a2-f12442846c72",
            "height": 21,
            "placeholder": "",
            "visible": true,
            "label_text": "Standard 45%",
            "intent": "account_type",
            "get_by_text": "Standard",
            "unique_name": "customers_standard_label_account_type_ef9be216",
            "width": 97.875,
            "dom_matched": true,
            "enable": true,
            "x": 820.0243530273438,
            "match_timestamp": "2025-08-07T04:22:28.629728",
            "type": ""
        },
        {
            "dom_matched": false,
            "type": "ocr",
            "element_id": "338dcf5c-c760-440a-b749-cd8c1166587c",
            "get_by_text": "$52,000",
            "placeholder": "$52,000",
            "ocr_type": "label",
            "external": false,
            "intent": "balance",
            "unique_name": "customers_$52,000_label_balance_b6e2bd67",
            "page_name": "customers",
            "label_text": "$52,000"
        },
        {
            "external": false,
            "get_by_text": "2023-03-22",
            "dom_matched": false,
            "intent": "join_date",
            "ocr_type": "label",
            "placeholder": "2023-03-22",
            "element_id": "b6c0bf5d-bce1-402c-86c3-6bfb7aaeeb2c",
            "label_text": "2023-03-22",
            "unique_name": "customers_2023-03-22_label_join_date_363240e3",
            "page_name": "customers",
            "type": "ocr"
        },
        {
            "unique_name": "customers_emma_davis_label_customer_name_671b9ccd",
            "type": "ocr",
            "placeholder": "Emma Davis",
            "element_id": "427ef217-7188-4883-9e2d-1e30c7a200c7",
            "external": false,
            "get_by_text": "Emma Davis",
            "intent": "customer_name",
            "dom_matched": false,
            "ocr_type": "label",
            "page_name": "customers",
            "label_text": "Emma Davis"
        },
        {
            "element_id": "a5f93c70-1552-4412-b3d0-b85629e76c31",
            "ocr_type": "label",
            "page_name": "customers",
            "intent": "customer_email",
            "external": false,
            "get_by_text": "emma.davis@email.com",
            "unique_name": "customers_emma.davis@email.com_label_customer_email_1680f20b",
            "type": "ocr",
            "placeholder": "emma.davis@email.com",
            "dom_matched": false,
            "label_text": "emma.davis@email.com"
        },
        {
            "label_text": "$89,000",
            "type": "ocr",
            "dom_matched": false,
            "placeholder": "$89,000",
            "intent": "balance",
            "element_id": "d0359914-eb55-465b-9181-1ae0ede4305e",
            "ocr_type": "label",
            "page_name": "customers",
            "external": false,
            "unique_name": "customers_$89,000_label_balance_f3422319",
            "get_by_text": "$89,000"
        },
        {
            "unique_name": "customers_2022-11-08_label_join_date_bcd7c000",
            "external": false,
            "ocr_type": "label",
            "intent": "join_date",
            "page_name": "customers",
            "element_id": "caef0247-1d74-40ba-996c-2ace81dcb1fa",
            "get_by_text": "2022-11-08",
            "dom_matched": false,
            "type": "ocr",
            "placeholder": "2022-11-08",
            "label_text": "2022-11-08"
        },
        {
            "visible": true,
            "editable": false,
            "unique_name": "customers_export_button_export_ec306f18",
            "type": "submit",
            "value": "",
            "dom_matched": true,
            "height": 40,
            "external": false,
            "placeholder": "",
            "enable": true,
            "ocr_type": "button",
            "tag_name": "button",
            "y": 111,
            "width": 144.78125,
            "element_id": "0e97e660-04a4-41f4-92ec-64632780f724",
            "page_name": "customers",
            "dom_class": "justify-center whitespace-nowrap rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0 bg-primary text-primary-foreground hover:bg-primary/90 h-10 px-4 py-2 flex items-center gap-2",
            "intent": "export",
            "get_by_text": "Export",
            "label_text": "Export Report",
            "x": 1096.21875,
            "match_timestamp": "2025-08-07T04:22:28.869783",
            "dom-id": ""
        },
        {
            "label_text": "New Customer",
            "page_name": "customers",
            "ocr_type": "button",
            "intent": "add_customer",
            "get_by_text": "New Customer",
            "placeholder": "New Customer",
            "element_id": "b0735fce-9fbc-45f1-92cc-2e2e8a71baa3",
            "external": false,
            "type": "ocr",
            "dom_matched": false,
            "unique_name": "customers_new_customer_button_add_customer_33383326"
        },
        {
            "get_by_text": "Add New Customer",
            "dom_matched": false,
            "page_name": "customers",
            "element_id": "e271b4dc-24c9-46b9-9f2e-ed0475690e5e",
            "intent": "form_title",
            "label_text": "Add New Customer",
            "ocr_type": "label",
            "type": "ocr",
            "unique_name": "customers_add_new_customer_label_form_title_2b3b0780",
            "placeholder": "Add New Customer",
            "external": false
        },
        {
            "dom_matched": false,
            "external": false,
            "label_text": "Enter the customer details to create a new account.",
            "page_name": "customers",
            "get_by_text": "Enter the customer details to create a new account.",
            "type": "ocr",
            "placeholder": "Enter the customer details to create a new account.",
            "intent": "form_instruction",
            "ocr_type": "label",
            "element_id": "01c9b209-9793-47f1-8c48-b23926042e2f",
            "unique_name": "customers_enter_the_customer_details_to_create_a_new_account._label_form_instruction_4e368c65"
        },
        {
            "get_by_text": "Full Name",
            "intent": "full_name_info",
            "dom_matched": false,
            "type": "ocr",
            "element_id": "50db0a7b-af9f-425b-bdcf-db3d148f33a9",
            "placeholder": "Full Name",
            "unique_name": "customers_full_name_label_full_name_info_03b2686c",
            "ocr_type": "label",
            "page_name": "customers",
            "external": false,
            "label_text": "Full Name"
        },
        {
            "get_by_text": "",
            "dom_matched": false,
            "intent": "full_name",
            "element_id": "70c78a9e-b303-43a7-8c1d-cb4ee9bdb44e",
            "unique_name": "customers_textbox_full_name_471e92b0",
            "label_text": "",
            "ocr_type": "textbox",
            "external": false,
            "page_name": "customers",
            "type": "ocr",
            "placeholder": ""
        },
        {
            "type": "ocr",
            "page_name": "customers",
            "dom_matched": false,
            "element_id": "7bfb4221-3707-44ad-84df-f557035b54cb",
            "get_by_text": "Email",
            "label_text": "Email",
            "ocr_type": "label",
            "external": false,
            "placeholder": "Email",
            "unique_name": "customers_email_label_email_info_5a7cb4ad",
            "intent": "email_info"
        },
        {
            "get_by_text": "",
            "label_text": "",
            "type": "ocr",
            "element_id": "2be6c9d3-3652-4a50-981b-12ffc22cfb8e",
            "external": false,
            "intent": "email",
            "page_name": "customers",
            "unique_name": "customers_textbox_email_76456fa1",
            "ocr_type": "textbox",
            "placeholder": "",
            "dom_matched": false
        },
        {
            "label_text": "Phone Number",
            "dom_matched": false,
            "type": "ocr",
            "placeholder": "Phone Number",
            "element_id": "60c33e4b-117c-4d68-89df-7445e5943a2a",
            "intent": "phone_number_info",
            "get_by_text": "Phone Number",
            "external": false,
            "unique_name": "customers_phone_number_label_phone_number_info_012f42e5",
            "ocr_type": "label",
            "page_name": "customers"
        },
        {
            "ocr_type": "textbox",
            "get_by_text": "",
            "label_text": "",
            "page_name": "customers",
            "external": false,
            "placeholder": "",
            "unique_name": "customers_textbox_phone_number_25a7ab1e",
            "intent": "phone_number",
            "dom_matched": false,
            "element_id": "4584aad1-4df3-4687-ad41-104188164d62",
            "type": "ocr"
        },
        {
            "placeholder": "Account Type",
            "label_text": "Account Type",
            "ocr_type": "label",
            "element_id": "aac3525b-7019-4e3b-841d-1a08585d5a69",
            "page_name": "customers",
            "unique_name": "customers_account_type_label_account_type_info_c7142d65",
            "external": false,
            "intent": "account_type_info",
            "get_by_text": "Account Type",
            "dom_matched": false,
            "type": "ocr"
        },
        {
            "type": "ocr",
            "unique_name": "customers_select_account_type_select_account_type_dd2f2c16",
            "intent": "account_type",
            "ocr_type": "select",
            "placeholder": "Select account type",
            "dom_matched": false,
            "external": false,
            "get_by_text": "Select account type",
            "element_id": "8619662f-c77d-4ca1-a12c-7943e9ff34a5",
            "label_text": "Select account type",
            "page_name": "customers"
        },
        {
            "page_name": "customers",
            "intent": "address_info",
            "element_id": "ee51dd1a-e474-4735-a5f5-f4399f086745",
            "external": false,
            "get_by_text": "Address",
            "unique_name": "customers_address_label_address_info_2a2922ef",
            "dom_matched": false,
            "placeholder": "Address",
            "label_text": "Address",
            "ocr_type": "label",
            "type": "ocr"
        },
        {
            "element_id": "bd4edd12-0ee7-400a-b0a0-ee7ab3de9487",
            "placeholder": "",
            "ocr_type": "textbox",
            "intent": "address",
            "external": false,
            "get_by_text": "",
            "unique_name": "customers_textbox_address_8a78b39b",
            "dom_matched": false,
            "label_text": "",
            "page_name": "customers",
            "type": "ocr"
        },
        {
            "element_id": "0cdd71d2-b258-4086-a727-6541be3eb560",
            "page_name": "customers",
            "type": "ocr",
            "get_by_text": "Occupation",
            "ocr_type": "label",
            "unique_name": "customers_occupation_label_occupation_info_ba1b14e0",
            "external": false,
            "label_text": "Occupation",
            "dom_matched": false,
            "intent": "occupation_info",
            "placeholder": "Occupation"
        },
        {
            "unique_name": "customers_textbox_occupation_bf706400",
            "external": false,
            "element_id": "f6398f05-5ab8-4b47-8f19-777badc36a6e",
            "placeholder": "",
            "get_by_text": "",
            "ocr_type": "textbox",
            "type": "ocr",
            "intent": "occupation",
            "label_text": "",
            "page_name": "customers",
            "dom_matched": false
        },
        {
            "intent": "annual_income_info",
            "external": false,
            "label_text": "Annual Income",
            "get_by_text": "Annual Income",
            "type": "ocr",
            "unique_name": "customers_annual_income_label_annual_income_info_fc16d9d2",
            "dom_matched": false,
            "page_name": "customers",
            "element_id": "1791d135-cc42-4f99-823c-84ae162f00a7",
            "placeholder": "Annual Income",
            "ocr_type": "label"
        },
        {
            "label_text": "",
            "page_name": "customers",
            "intent": "annual_income",
            "element_id": "7a53f093-3d9e-4f96-9d83-27d3107113fd",
            "get_by_text": "",
            "dom_matched": false,
            "external": false,
            "type": "ocr",
            "unique_name": "customers_textbox_annual_income_405f76ef",
            "ocr_type": "textbox",
            "placeholder": ""
        },
        {
            "external": false,
            "intent": "initial_deposit_info",
            "page_name": "customers",
            "ocr_type": "label",
            "dom_matched": false,
            "element_id": "4e2f9a0f-ec4f-421a-aa84-81d3574ec36e",
            "unique_name": "customers_initial_deposit_label_initial_deposit_info_b991c434",
            "get_by_text": "Initial Deposit",
            "type": "ocr",
            "label_text": "Initial Deposit",
            "placeholder": "Initial Deposit"
        },
        {
            "external": false,
            "ocr_type": "textbox",
            "unique_name": "customers_textbox_initial_deposit_4fa6bb7e",
            "label_text": "",
            "dom_matched": false,
            "page_name": "customers",
            "element_id": "7e9e6770-a376-40f5-9725-418a43f12a21",
            "type": "ocr",
            "intent": "initial_deposit",
            "get_by_text": "",
            "placeholder": ""
        },
        {
            "get_by_text": "Cancel",
            "dom_matched": false,
            "element_id": "53d41797-0aba-4655-8964-578918ce2fc5",
            "unique_name": "customers_cancel_button_cancel_71a3913d",
            "label_text": "Cancel",
            "intent": "cancel",
            "external": false,
            "type": "ocr",
            "placeholder": "Cancel",
            "ocr_type": "button",
            "page_name": "customers"
        },
        {
            "intent": "submit",
            "page_name": "customers",
            "get_by_text": "Add Customer",
            "type": "ocr",
            "dom_matched": false,
            "label_text": "Add Customer",
            "ocr_type": "button",
            "placeholder": "Add Customer",
            "external": false,
            "element_id": "a771d766-6ffe-4728-8d9d-76b213fe254b",
            "unique_name": "customers_add_customer_button_submit_bce56d38"
        }
    ]
}


# === FILE: apis\dashboard.json ===
{
    "ids": [
        "3b6774b8-cef9-4aca-9310-c0e04f78cf03",
        "d8640139-182e-4c99-be69-ffbf98bd62cf",
        "d65504d1-2ab8-426a-b23f-1fbce4d9ba44",
        "ad229396-9891-4a4a-a701-9ca192ad33b2",
        "b458201c-005b-4ada-b7ff-b6d91789f75f",
        "3036f103-0352-4173-89d8-8856f0982719",
        "af8bfe3f-a07f-400b-9697-8fdbc96a8c2b",
        "2a8d025b-46ef-4b4d-871e-8a2b37616c95",
        "4dfb9b73-ed7e-4423-abba-48a1f48c5ca0",
        "9900ee18-8db4-492d-bbc2-8e5ddcf391c0",
        "eb92abba-1050-4960-9ac6-65c29b7630ee",
        "080ef0b3-fe2e-41c6-a187-35c0e1d78bb9",
        "5f135448-f6ef-4de9-88c4-0bd01d79ca8e",
        "2da68604-58b8-4e7b-86f7-8beb8723972c",
        "a48bd699-7fa0-4711-a433-737867b848fb",
        "d12d1c15-0412-40f5-9ecd-fa76a67f32e5",
        "3b3c5b3c-eafd-4952-bf1c-c6e38d22b0e1",
        "f0c330ad-3cf8-43b2-b400-c7163dd2490d",
        "29db2006-910c-4ffc-8828-ed5887a80c44",
        "caada266-a43f-400b-bab9-f8a703f03471",
        "7c507423-4b2f-4340-8906-c4a87b0c2a43",
        "27f7cb8b-862d-411d-b8fd-90dc5c0b0043",
        "71a0ebed-4dd9-4688-b786-2fc3d63bbfab",
        "b694f38c-f54a-4a6d-952f-63cecc3c32e9",
        "d384cbbc-f910-4ea4-ae1b-02d31a6c6c96",
        "e9dbc3ab-8d76-4b43-b066-793d4ed1fa99",
        "003ce538-7def-483c-b5b3-bbc1ed00517b",
        "b581a3d5-9788-4ed3-b634-28d007248a71",
        "805f74cf-5799-4fd2-9131-e6c3a83edae6",
        "62068b8c-83a4-4a03-8dfe-c3ac69fc7630",
        "7cd4e104-9630-498e-a3ef-1a51d1c458cb",
        "5075fd2e-2873-4a4f-a6ee-1958d704d651",
        "8a81cffe-3ea7-46ca-8d03-3e2b0e074109",
        "03cdecf4-7fec-4da4-be48-81f97759920b",
        "42dc2d5f-475b-42d0-9f41-b0ac13b0946e"
    ],
    "embeddings": null,
    "documents": [
        "",
        "Search customers, loans, transactions...",
        "Dashboard",
        "Search customers, loans, transactions...",
        "Search customers, loans, transactions...",
        "Transactions",
        "Tasks",
        "Export Report",
        "Analytics",
        "Settings",
        "Dashboard",
        "Bank CRMNavigationDashboardCustomersLoansTransactionsTasksReportsAnalyticsSettingsToggle SidebarJohn DoeDashboardWelcome back! Here's your banking overview.Export ReportTotal Customers2,847+12.5% from last monthActive Loans$45.2M+8.2% from last monthMonthly Transactions18,394+15.3% from last monthRevenue Growth23.4%+2.1% from last monthLoan Portfolio TrendMonthly loan disbursements over the last 6 monthsJanFebMarAprMayJun01500000300000045000006000000Customer DistributionCustomer segments by account typePremium 35%Standard 45%Basic 20%Recent ActivitiesLatest customer interactions and transactionsSarah JohnsonLoan Application Approved$250,0002 hours agoMichael ChenAccount Verification Pending-4 hours agoEmma DavisLarge Transaction Alert$75,0006 hours agoRobert WilsonMonthly Payment Received$3,2008 hours ago",
        "Total Customers",
        "2,847",
        "Active Loans",
        "Standard 45%",
        "Monthly Transactions",
        "18,394",
        "Revenue Growth",
        "Standard 45%",
        "Loan Portfolio Trend",
        "Monthly loan disbursements over the last 6 months",
        "Customer Distribution",
        "Customer segments by account type",
        "Recent Activities",
        "Latest customer interactions and transactions",
        "Sarah Johnson",
        "Loan Application Approved",
        "Michael Chen",
        "",
        "1500000",
        "2 hours ago",
        "Export Report",
        "Edit with",
        "Lovable"
    ],
    "uris": null,
    "included": ["metadatas", "documents"],
    "data": null,
    "metadatas": [
        {
            "label_text": "",
            "get_by_text": "",
            "external": false,
            "page_name": "dashboard",
            "type": "ocr",
            "intent": "navigation",
            "ocr_type": "button",
            "unique_name": "dashboard_button_navigation_34c032c8",
            "placeholder": "",
            "element_id": "3b6774b8-cef9-4aca-9310-c0e04f78cf03",
            "dom_matched": false
        },
        {
            "y": 16,
            "dom-id": "",
            "match_timestamp": "2025-08-06T14:23:16.175705",
            "placeholder": "Search customers, loans, transactions...",
            "editable": true,
            "unique_name": "dashboard_search_customers,_loans,_transactions..._textbox_search_3310a968",
            "intent": "search",
            "width": 384,
            "enable": true,
            "height": 40,
            "get_by_text": "Search customers, loans, transactions...",
            "x": 324,
            "value": "",
            "visible": true,
            "tag_name": "input",
            "type": "text",
            "page_name": "dashboard",
            "element_id": "d8640139-182e-4c99-be69-ffbf98bd62cf",
            "ocr_type": "textbox",
            "dom_matched": true,
            "dom_class": "flex h-10 rounded-md border border-input bg-background px-3 py-2 text-base ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium file:text-foreground placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 md:text-sm pl-10 w-96",
            "external": false,
            "label_text": "Search customers, loans, transactions..."
        },
        {
            "element_id": "d65504d1-2ab8-426a-b23f-1fbce4d9ba44",
            "external": false,
            "page_name": "dashboard",
            "intent": "navigation",
            "label_text": "Dashboard",
            "type": "ocr",
            "placeholder": "Dashboard",
            "dom_matched": false,
            "get_by_text": "Dashboard",
            "unique_name": "dashboard_dashboard_button_navigation_83914516",
            "ocr_type": "button"
        },
        {
            "value": "",
            "dom_matched": true,
            "get_by_text": "Customers",
            "dom-id": "",
            "editable": true,
            "intent": "navigation",
            "page_name": "dashboard",
            "width": 384,
            "tag_name": "input",
            "external": false,
            "type": "text",
            "enable": true,
            "element_id": "ad229396-9891-4a4a-a701-9ca192ad33b2",
            "height": 40,
            "y": 16,
            "dom_class": "",
            "ocr_type": "button",
            "unique_name": "dashboard_customers_button_navigation_bb4303b6",
            "x": 324,
            "label_text": "Customers",
            "visible": true,
            "placeholder": "Customers",
            "match_timestamp": "2025-08-06T14:23:16.263343"
        },
        {
            "dom-id": "",
            "ocr_type": "button",
            "tag_name": "input",
            "dom_matched": true,
            "x": 324,
            "intent": "navigation",
            "value": "",
            "external": false,
            "page_name": "dashboard",
            "element_id": "b458201c-005b-4ada-b7ff-b6d91789f75f",
            "label_text": "Search customers, loans, transactions...",
            "match_timestamp": "2025-08-06T14:23:16.314804",
            "width": 384,
            "type": "text",
            "editable": true,
            "get_by_text": "Loans",
            "visible": true,
            "placeholder": "Search customers, loans, transactions...",
            "unique_name": "dashboard_loans_button_navigation_42436e2a",
            "dom_class": "flex h-10 rounded-md border border-input bg-background px-3 py-2 text-base ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium file:text-foreground placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 md:text-sm pl-10 w-96",
            "height": 40,
            "y": 16,
            "enable": true
        },
        {
            "label_text": "Transactions",
            "external": false,
            "unique_name": "dashboard_transactions_button_navigation_f0479a72",
            "intent": "navigation",
            "get_by_text": "Transactions",
            "element_id": "3036f103-0352-4173-89d8-8856f0982719",
            "page_name": "dashboard",
            "dom_matched": false,
            "placeholder": "Transactions",
            "ocr_type": "button",
            "type": "ocr"
        },
        {
            "element_id": "af8bfe3f-a07f-400b-9697-8fdbc96a8c2b",
            "ocr_type": "button",
            "intent": "navigation",
            "placeholder": "Tasks",
            "label_text": "Tasks",
            "type": "ocr",
            "page_name": "dashboard",
            "external": false,
            "get_by_text": "Tasks",
            "unique_name": "dashboard_tasks_button_navigation_cde2a4d6",
            "dom_matched": false
        },
        {
            "dom_class": "justify-center whitespace-nowrap rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0 bg-primary text-primary-foreground hover:bg-primary/90 h-10 px-4 py-2 flex items-center gap-2",
            "tag_name": "button",
            "get_by_text": "Reports",
            "dom-id": "",
            "page_name": "dashboard",
            "external": false,
            "label_text": "Export Report",
            "unique_name": "dashboard_reports_button_navigation_578fb659",
            "element_id": "2a8d025b-46ef-4b4d-871e-8a2b37616c95",
            "dom_matched": true,
            "ocr_type": "button",
            "type": "submit",
            "y": 110.8000030517578,
            "value": "",
            "intent": "navigation",
            "height": 40,
            "enable": true,
            "editable": false,
            "match_timestamp": "2025-08-06T14:23:16.394435",
            "visible": true,
            "width": 144.77500915527344,
            "placeholder": "",
            "x": 1096.0250244140625
        },
        {
            "ocr_type": "button",
            "external": false,
            "intent": "navigation",
            "dom_matched": false,
            "element_id": "4dfb9b73-ed7e-4423-abba-48a1f48c5ca0",
            "type": "ocr",
            "label_text": "Analytics",
            "placeholder": "Analytics",
            "unique_name": "dashboard_analytics_button_navigation_49884ab5",
            "get_by_text": "Analytics",
            "page_name": "dashboard"
        },
        {
            "page_name": "dashboard",
            "external": false,
            "placeholder": "Settings",
            "dom_matched": false,
            "intent": "navigation",
            "label_text": "Settings",
            "unique_name": "dashboard_settings_button_navigation_7a36fd5d",
            "element_id": "9900ee18-8db4-492d-bbc2-8e5ddcf391c0",
            "get_by_text": "Settings",
            "ocr_type": "button",
            "type": "ocr"
        },
        {
            "element_id": "eb92abba-1050-4960-9ac6-65c29b7630ee",
            "get_by_text": "Dashboard",
            "dom_matched": false,
            "label_text": "Dashboard",
            "unique_name": "dashboard_dashboard_label_page_title_a353b4f0",
            "placeholder": "Dashboard",
            "type": "ocr",
            "page_name": "dashboard",
            "external": false,
            "ocr_type": "label",
            "intent": "page_title"
        },
        {
            "y": 0,
            "dom-id": "root",
            "label_text": "Bank CRMNavigationDashboardCustomersLoansTransactionsTasksReportsAnalyticsSettingsToggle SidebarJohn DoeDashboardWelcome back! Here's your banking overview.Export ReportTotal Customers2,847+12.5% from last monthActive Loans$45.2M+8.2% from last monthMonthly Transactions18,394+15.3% from last monthRevenue Growth23.4%+2.1% from last monthLoan Portfolio TrendMonthly loan disbursements over the last 6 monthsJanFebMarAprMayJun01500000300000045000006000000Customer DistributionCustomer segments by account typePremium 35%Standard 45%Basic 20%Recent ActivitiesLatest customer interactions and transactionsSarah JohnsonLoan Application Approved$250,0002 hours agoMichael ChenAccount Verification Pending-4 hours agoEmma DavisLarge Transaction Alert$75,0006 hours agoRobert WilsonMonthly Payment Received$3,2008 hours ago",
            "unique_name": "dashboard_welcome_back!_heres_your_banking_overview._label_greeting_bd321dde",
            "external": false,
            "type": "",
            "visible": true,
            "match_timestamp": "2025-08-06T14:23:16.484625",
            "ocr_type": "label",
            "placeholder": "",
            "dom_class": "",
            "intent": "greeting",
            "get_by_text": "Welcome back! Here's your banking overview.",
            "page_name": "dashboard",
            "editable": false,
            "enable": true,
            "x": 0,
            "width": 1264.800048828125,
            "element_id": "080ef0b3-fe2e-41c6-a187-35c0e1d78bb9",
            "tag_name": "div",
            "dom_matched": true,
            "value": "",
            "height": 1380
        },
        {
            "dom_matched": false,
            "label_text": "Total Customers",
            "placeholder": "Total Customers",
            "ocr_type": "label",
            "element_id": "5f135448-f6ef-4de9-88c4-0bd01d79ca8e",
            "external": false,
            "type": "ocr",
            "get_by_text": "Total Customers",
            "intent": "metric_label",
            "page_name": "dashboard",
            "unique_name": "dashboard_total_customers_label_metric_label_199f5783"
        },
        {
            "external": false,
            "intent": "metric_value",
            "dom_matched": false,
            "page_name": "dashboard",
            "element_id": "2da68604-58b8-4e7b-86f7-8beb8723972c",
            "label_text": "2,847",
            "type": "ocr",
            "get_by_text": "2,847",
            "ocr_type": "label",
            "unique_name": "dashboard_2,847_label_metric_value_fdec317c",
            "placeholder": "2,847"
        },
        {
            "get_by_text": "Active Loans",
            "element_id": "a48bd699-7fa0-4711-a433-737867b848fb",
            "ocr_type": "label",
            "external": false,
            "unique_name": "dashboard_active_loans_label_metric_label_cc5f77df",
            "intent": "metric_label",
            "placeholder": "Active Loans",
            "type": "ocr",
            "page_name": "dashboard",
            "dom_matched": false,
            "label_text": "Active Loans"
        },
        {
            "visible": true,
            "editable": false,
            "external": false,
            "dom_matched": true,
            "get_by_text": "$45.2M",
            "dom-id": "",
            "intent": "metric_value",
            "height": 21.600000381469727,
            "ocr_type": "label",
            "match_timestamp": "2025-08-06T14:23:16.660680",
            "y": 702.9990844726562,
            "page_name": "dashboard",
            "label_text": "Standard 45%",
            "x": 819.7243041992188,
            "width": 97.875,
            "enable": true,
            "dom_class": "{}",
            "element_id": "d12d1c15-0412-40f5-9ecd-fa76a67f32e5",
            "tag_name": "g",
            "type": "",
            "value": "",
            "placeholder": "",
            "unique_name": "dashboard_$45.2m_label_metric_value_4a2ef93a"
        },
        {
            "get_by_text": "Monthly Transactions",
            "element_id": "3b3c5b3c-eafd-4952-bf1c-c6e38d22b0e1",
            "type": "ocr",
            "page_name": "dashboard",
            "ocr_type": "label",
            "unique_name": "dashboard_monthly_transactions_label_metric_label_dc905c66",
            "dom_matched": false,
            "external": false,
            "label_text": "Monthly Transactions",
            "intent": "metric_label",
            "placeholder": "Monthly Transactions"
        },
        {
            "placeholder": "18,394",
            "unique_name": "dashboard_18,394_label_metric_value_b6b442dd",
            "page_name": "dashboard",
            "get_by_text": "18,394",
            "type": "ocr",
            "dom_matched": false,
            "intent": "metric_value",
            "label_text": "18,394",
            "ocr_type": "label",
            "external": false,
            "element_id": "f0c330ad-3cf8-43b2-b400-c7163dd2490d"
        },
        {
            "external": false,
            "intent": "metric_label",
            "type": "ocr",
            "unique_name": "dashboard_revenue_growth_label_metric_label_d86362eb",
            "get_by_text": "Revenue Growth",
            "ocr_type": "label",
            "element_id": "29db2006-910c-4ffc-8828-ed5887a80c44",
            "dom_matched": false,
            "page_name": "dashboard",
            "label_text": "Revenue Growth",
            "placeholder": "Revenue Growth"
        },
        {
            "dom_class": "{}",
            "page_name": "dashboard",
            "ocr_type": "label",
            "enable": true,
            "unique_name": "dashboard_4%_label_metric_value_316201d4",
            "height": 21.600000381469727,
            "x": 819.7243041992188,
            "dom_matched": true,
            "type": "",
            "intent": "metric_value",
            "placeholder": "",
            "label_text": "Standard 45%",
            "dom-id": "",
            "width": 97.875,
            "external": false,
            "tag_name": "g",
            "match_timestamp": "2025-08-06T14:23:16.755348",
            "element_id": "caada266-a43f-400b-bab9-f8a703f03471",
            "value": "",
            "editable": false,
            "visible": true,
            "y": 702.9990844726562,
            "get_by_text": "4%"
        },
        {
            "dom_matched": false,
            "ocr_type": "label",
            "get_by_text": "Loan Portfolio Trend",
            "type": "ocr",
            "intent": "section_title",
            "placeholder": "Loan Portfolio Trend",
            "label_text": "Loan Portfolio Trend",
            "external": false,
            "page_name": "dashboard",
            "unique_name": "dashboard_loan_portfolio_trend_label_section_title_32cf7d0c",
            "element_id": "7c507423-4b2f-4340-8906-c4a87b0c2a43"
        },
        {
            "element_id": "27f7cb8b-862d-411d-b8fd-90dc5c0b0043",
            "intent": "section_info",
            "ocr_type": "label",
            "placeholder": "Monthly loan disbursements over the last 6 months",
            "external": false,
            "type": "ocr",
            "unique_name": "dashboard_monthly_loan_disbursements_over_the_last_6_months_label_section_info_790102ea",
            "get_by_text": "Monthly loan disbursements over the last 6 months",
            "dom_matched": false,
            "page_name": "dashboard",
            "label_text": "Monthly loan disbursements over the last 6 months"
        },
        {
            "unique_name": "dashboard_customer_distribution_label_section_title_4bc10c83",
            "external": false,
            "ocr_type": "label",
            "dom_matched": false,
            "intent": "section_title",
            "placeholder": "Customer Distribution",
            "label_text": "Customer Distribution",
            "type": "ocr",
            "page_name": "dashboard",
            "get_by_text": "Customer Distribution",
            "element_id": "71a0ebed-4dd9-4688-b786-2fc3d63bbfab"
        },
        {
            "type": "ocr",
            "element_id": "b694f38c-f54a-4a6d-952f-63cecc3c32e9",
            "external": false,
            "placeholder": "Customer segments by account type",
            "ocr_type": "label",
            "page_name": "dashboard",
            "label_text": "Customer segments by account type",
            "get_by_text": "Customer segments by account type",
            "unique_name": "dashboard_customer_segments_by_account_type_label_section_info_e21a781f",
            "dom_matched": false,
            "intent": "section_info"
        },
        {
            "label_text": "Recent Activities",
            "unique_name": "dashboard_recent_activities_label_section_title_c5dd6139",
            "external": false,
            "get_by_text": "Recent Activities",
            "element_id": "d384cbbc-f910-4ea4-ae1b-02d31a6c6c96",
            "ocr_type": "label",
            "intent": "section_title",
            "page_name": "dashboard",
            "type": "ocr",
            "placeholder": "Recent Activities",
            "dom_matched": false
        },
        {
            "label_text": "Latest customer interactions and transactions",
            "placeholder": "Latest customer interactions and transactions",
            "ocr_type": "label",
            "get_by_text": "Latest customer interactions and transactions",
            "page_name": "dashboard",
            "type": "ocr",
            "element_id": "e9dbc3ab-8d76-4b43-b066-793d4ed1fa99",
            "unique_name": "dashboard_latest_customer_interactions_and_transactions_label_section_info_5c741538",
            "external": false,
            "dom_matched": false,
            "intent": "section_info"
        },
        {
            "placeholder": "Sarah Johnson",
            "unique_name": "dashboard_sarah_johnson_label_activity_user_309b9d18",
            "get_by_text": "Sarah Johnson",
            "intent": "activity_user",
            "label_text": "Sarah Johnson",
            "type": "ocr",
            "dom_matched": false,
            "ocr_type": "label",
            "external": false,
            "element_id": "003ce538-7def-483c-b5b3-bbc1ed00517b",
            "page_name": "dashboard"
        },
        {
            "element_id": "b581a3d5-9788-4ed3-b634-28d007248a71",
            "get_by_text": "Loan Application Approved",
            "placeholder": "Loan Application Approved",
            "unique_name": "dashboard_loan_application_approved_label_activity_info_969d6763",
            "dom_matched": false,
            "external": false,
            "label_text": "Loan Application Approved",
            "ocr_type": "label",
            "page_name": "dashboard",
            "intent": "activity_info",
            "type": "ocr"
        },
        {
            "element_id": "805f74cf-5799-4fd2-9131-e6c3a83edae6",
            "ocr_type": "label",
            "unique_name": "dashboard_michael_chen_label_activity_user_f041a3aa",
            "intent": "activity_user",
            "placeholder": "Michael Chen",
            "type": "ocr",
            "label_text": "Michael Chen",
            "dom_matched": false,
            "external": false,
            "page_name": "dashboard",
            "get_by_text": "Michael Chen"
        },
        {
            "unique_name": "dashboard_label_activity_info_1a0fecd2",
            "dom_matched": false,
            "label_text": "",
            "placeholder": "",
            "element_id": "62068b8c-83a4-4a03-8dfe-c3ac69fc7630",
            "page_name": "dashboard",
            "intent": "activity_info",
            "get_by_text": "",
            "type": "ocr",
            "external": false,
            "ocr_type": "label"
        },
        {
            "dom_class": "{}",
            "visible": true,
            "height": 21.600000381469727,
            "y": 713.2799682617188,
            "type": "",
            "page_name": "dashboard",
            "match_timestamp": "2025-08-06T14:23:16.967262",
            "external": false,
            "placeholder": "",
            "dom-id": "",
            "unique_name": "dashboard_$250,000_label_transaction_value_5404abc5",
            "x": 301.4250183105469,
            "tag_name": "g",
            "width": 68.375,
            "element_id": "7cd4e104-9630-498e-a3ef-1a51d1c458cb",
            "get_by_text": "$250,000",
            "intent": "transaction_value",
            "ocr_type": "label",
            "label_text": "1500000",
            "editable": false,
            "dom_matched": true,
            "enable": true,
            "value": ""
        },
        {
            "ocr_type": "label",
            "page_name": "dashboard",
            "dom_matched": false,
            "placeholder": "2 hours ago",
            "get_by_text": "2 hours ago",
            "element_id": "5075fd2e-2873-4a4f-a6ee-1958d704d651",
            "unique_name": "dashboard_2_hours_ago_label_transaction_time_a74efe28",
            "label_text": "2 hours ago",
            "intent": "transaction_time",
            "external": false,
            "type": "ocr"
        },
        {
            "dom-id": "",
            "enable": true,
            "editable": false,
            "value": "",
            "visible": true,
            "height": 40,
            "dom_matched": true,
            "tag_name": "button",
            "element_id": "8a81cffe-3ea7-46ca-8d03-3e2b0e074109",
            "external": false,
            "intent": "export",
            "x": 1096.0250244140625,
            "y": 110.8000030517578,
            "type": "submit",
            "dom_class": "justify-center whitespace-nowrap rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0 bg-primary text-primary-foreground hover:bg-primary/90 h-10 px-4 py-2 flex items-center gap-2",
            "page_name": "dashboard",
            "ocr_type": "button",
            "get_by_text": "Export Report",
            "match_timestamp": "2025-08-06T14:23:17.036771",
            "width": 144.77500915527344,
            "placeholder": "",
            "unique_name": "dashboard_export_report_button_export_ed26f6d4",
            "label_text": "Export Report"
        },
        {
            "element_id": "03cdecf4-7fec-4da4-be48-81f97759920b",
            "height": 18,
            "editable": false,
            "visible": true,
            "external": false,
            "y": 687,
            "dom-id": "",
            "x": 1126.800048828125,
            "enable": true,
            "placeholder": "",
            "dom_matched": true,
            "value": "",
            "ocr_type": "label",
            "width": 45.36249923706055,
            "unique_name": "dashboard_edit_with_label_edit_tool_e1025d09",
            "tag_name": "span",
            "intent": "edit_tool",
            "label_text": "Edit with",
            "page_name": "dashboard",
            "dom_class": "",
            "match_timestamp": "2025-08-06T14:23:17.158475",
            "get_by_text": "Edit with",
            "type": ""
        },
        {
            "label_text": "Lovable",
            "type": "ocr",
            "intent": "edit_tool",
            "page_name": "dashboard",
            "get_by_text": "Lovable",
            "placeholder": "Lovable",
            "dom_matched": false,
            "unique_name": "dashboard_lovable_button_edit_tool_2de51406",
            "external": false,
            "ocr_type": "button",
            "element_id": "42dc2d5f-475b-42d0-9f41-b0ac13b0946e"
        }
    ]
}



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


def to_pascal_case(name: str) -> str:
    return ''.join(word.capitalize() for word in name.split('_')) + "Page"


def generate_test_code_from_methods(user_story, method_map, page_names, site_url):
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


def fix_page_object_initialization(code, page_names):
    for class_name, page_name in page_names.items():
        code = re.sub(
            rf"{class_name}\s*\(\s*page\s*\)",
            f'{class_name}(page, "{page_name}")',
            code
        )
    return code


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
    test_functions, ui_scripts = [], []

    page_names_map = {to_pascal_case(page): page for page in method_map_full}

    for story in stories:
        path_pages = get_inferred_pages(story, method_map_full)
        sub_method_map = {p: method_map_full[p]
                          for p in path_pages if p in method_map_full}
        code = generate_test_code_from_methods(
            story, sub_method_map, path_pages, site_url)

        # Test Code Adjustments
        code = re.sub(r'(?m)^(async def test_)',
                      '@pytest.mark.asyncio\n\\1', code)
        if 'import pytest' not in code:
            code = 'import pytest\n' + code
        code = re.sub(
            r'await\s+\w+_page\._enrich_if_needed\([^\)]*\)\s*\n', '', code)
        test_functions.append(
            fix_page_object_initialization(code, page_names_map))

        # UI Script Adjustments
        ui_code = re.sub(r'import pytest\n?', '', code)
        ui_code = re.sub(r'@pytest\.mark\.asyncio\n?', '', ui_code)
        ui_code = re.sub(r'async def test_\w+\(page\):',
                         'async def main():', ui_code)
        ui_code = fix_page_object_initialization(ui_code, page_names_map)

        main_body_match = re.search(
            r'async def main\(\):\n((?:.|\n)*)', ui_code)
        main_body_lines = main_body_match.group(
            1).splitlines() if main_body_match else []
        main_body_clean = [line.strip()
                           for line in main_body_lines if line.strip()]

        # Detect first usage and initialize exactly before that
        page_class_names = {page: to_pascal_case(
            page) for page in method_map_full}
        seen_pages = set()
        adjusted_main_body = []
        for line in main_body_clean:
            method_call_match = re.match(r'await\s+(\w+_page)\.', line)
            if method_call_match:
                page_var = method_call_match.group(1)
                page_key = page_var.replace("_page", "")
                if page_key not in seen_pages:
                    instantiation_line = f"{page_var} = {page_class_names[page_key]}(page, '{page_key}')"
                    adjusted_main_body.append(instantiation_line)
                    seen_pages.add(page_key)
            adjusted_main_body.append(line)

        # Compose UI script imports
        ui_imports = [
            "import asyncio",
            "from playwright.async_api import async_playwright",
            "from generated_runs.src.pages.base_page import BasePage",
        ] + [
            f"from generated_runs.src.pages.{page}_page import {to_pascal_case(page)}"
            for page in sorted(method_map_full)
        ]

        # Final UI Script
        ui_script_full = f"""{chr(10).join(ui_imports)}

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        base_page = BasePage(page, "base", url='{site_url}')
        await base_page.goto("{site_url}")

{"".join(f"        {line}\n" for line in adjusted_main_body)}

if __name__ == "__main__":
    asyncio.run(main())
""".strip()

        ui_scripts.append(ui_script_full)

    idx = next_index(tests_dir, "test_{}.py")
    test_file = tests_dir / f"test_{idx}.py"
    ui_file = tests_dir / f"ui_scripts_{idx}.py"

    full_test_code = "\n\n".join(
        [f"from generated_runs.src.pages.{page}_page import {to_pascal_case(page)}"
         for page in sorted(method_map_full)]
        + test_functions
    )
    test_file.write_text(full_test_code, encoding="utf-8")

    ui_code_full = "\n\n".join(ui_scripts)
    ui_file.write_text(ui_code_full, encoding="utf-8")

    create_default_test_data(run_folder)

    return {"results": stories, "test_file": str(test_file), "ui_script": str(ui_file)}



# === FILE: apis\generate_page_methods.py ===
from fastapi import APIRouter
from pathlib import Path
from services.test_generation_utils import collection, filter_all_pages
from utils.smart_ai_utils import ensure_smart_ai_module
from orchestrator.orchestrator import send_message

router = APIRouter()


def generate_base_page(base_page_path: Path):
    base_page_content = '''from services.page_enricher import enrich_page
from generated_runs.src.lib.smart_ai import patch_page_with_smartai
from services.chroma_service import get_chroma_collection

class BasePage:
    enriched_pages = set()
    shared_page = None  # Class-level page sharing

    def __init__(self, page=None, page_name="base", url=None):
        if page is not None:
            BasePage.shared_page = page
        elif BasePage.shared_page is None:
            raise ValueError("Playwright page instance must be provided at least once.")

        self.page = BasePage.shared_page
        self.page_name = page_name
        self.url = url

    def _fetch_metadata_from_chroma(self, page_name):
        collection = get_chroma_collection()
        all_metadata = collection.get(where={"page_name": page_name}).get("metadatas", [])
        return all_metadata

    async def goto(self, url=None):
        target_url = url or self.url
        if not target_url:
            raise ValueError(f"URL not set for {self.page_name}")
        await self.page.goto(target_url)

    async def enrich_once(self, force=False):
        if force or self.page_name not in BasePage.enriched_pages:
            await enrich_page(self.page, self.page_name)
            BasePage.enriched_pages.add(self.page_name)
'''
    base_page_path.write_text(base_page_content.strip(), encoding="utf-8")
    print("✅ Generated BasePage class")


@router.post("/rag/generate-page-methods")
def generate_page_methods():
    ensure_smart_ai_module()
    target_pages = filter_all_pages()
    result = {}

    # Generate conftest.py for SmartAI patching
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

    # Ensure pages directory exists
    outdir = Path("generated_runs") / "src" / "pages"
    outdir.mkdir(parents=True, exist_ok=True)

    # Generate BasePage class
    base_page_path = outdir / "base_page.py"
    generate_base_page(base_page_path)

    for page in target_pages:
        page_data = collection.get(where={"page_name": page})
        entries = page_data.get("metadatas", [])

        page_spec = {
            "page_name": page,
            "entries": entries
        }

        response = send_message("python", "generate_page_file", page_spec)
        payload = response.payload
        page_class_code = payload["code"]

        # Extract class name
        class_name = page_class_code.split('class ')[1].split('(')[0].strip()

        header = f'''from generated_runs.src.pages.base_page import BasePage
from services.page_enricher import enrich_page
from generated_runs.src.lib.smart_ai import patch_page_with_smartai
from utils.enrichment_status import is_enriched

class {class_name}(BasePage):
    def __init__(self, page=None, page_name="{page}"):
        super().__init__(page, page_name)
        self._enriched = False
        metadata = self._fetch_metadata_from_chroma(page_name)
        patch_page_with_smartai(self.page, metadata)

    async def _enrich_if_needed(self, force=False):
        if force or not is_enriched(self.page_name):
            await enrich_page(self.page, self.page_name)
            self._enriched = True
'''

        # 1. Split out all method blocks (grab all async defs, skip _enrich_if_needed duplicates)
        methods = []
        for block in page_class_code.split('\n'):
            # Capture only async def methods (skip _enrich_if_needed outside the header)
            if block.strip().startswith("async def _enrich_if_needed"):
                continue  # We inject this above, skip all else
            if block.strip().startswith("async def "):
                methods.append(block)
            elif methods:
                # For lines after async def (body), as long as we started a method
                methods[-1] += "\n" + block

        # 2. Join all method blocks and ensure proper indentation
        # (Assume incoming block is already correctly indented by LLM; otherwise, indent manually)
        method_blocks = "\n\n".join(methods)

        # 3. Final code assembly
        final_code = f"{header}\n\n{method_blocks}\n"

        # Write the generated page class
        filepath = outdir / payload["page_file"]
        filepath.write_text(final_code.strip(), encoding="utf-8")

        result[page] = {
            "filename": str(filepath),
            "code": final_code
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
        "id": uid,
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


page1_data = collection.get(where={"page_name": 'dashboard'})
page2_data = collection.get(where={"page_name": 'customers'})

# Ensure 'apis' folder exists!
Path("apis").mkdir(parents=True, exist_ok=True)

# Save to 'page1_data.json' in the current folder
with open("apis/dashboard.json", "w", encoding="utf-8") as f:
    json.dump(page1_data, f, indent=4, ensure_ascii=False, default=convert_np)

# Save to 'page2_data.json' in the current folder
with open("apis/customers.json", "w", encoding="utf-8") as f:
    json.dump(page2_data, f, indent=4, ensure_ascii=False, default=convert_np)

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


# === FILE: data\openai_response\20250807_112812_dashboard.txt ===
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
Welcome back! Here's your banking overview. - label - greeting
Total Customers - label - metric_title
2,847 - label - metric_value
Active Loans - label - metric_title
$45.2M - label - metric_value
Monthly Transactions - label - metric_title
18,394 - label - metric_value
Revenue Growth - label - metric_title
23.4% - label - metric_value
Export Report - button - export
Loan Portfolio Trend - label - section_title
Monthly loan disbursements over the last 6 months - label - section_info
Customer Distribution - label - section_title
Customer segments by account type - label - section_info
Premium 35% - label - chart_info
Standard 45% - label - chart_info
Basic 20% - label - chart_info
Recent Activities - label - section_title
Latest customer interactions and transactions - label - section_info
Sarah Johnson - label - activity_user
Loan Application Approved - label - activity_info
Michael Chen - label - activity_user
$250,000 - label - transaction_amount
2 hours ago - label - transaction_time
Edit with - label - edit_option
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
Welcome back! Here's your banking overview. - label - greeting
Total Customers - label - metric_title
2,847 - label - metric_value
Active Loans - label - metric_title
$45.2M - label - metric_value
Monthly Transactions - label - metric_title
18,394 - label - metric_value
Revenue Growth - label - metric_title
4% - label - metric_value
Export Report - button - export
Loan Portfolio Trend - label - section_title
Monthly loan disbursements over the last 6 months - label - section_info
Customer Distribution - label - section_title
Customer segments by account type - label - section_info
Premium 35% - label - chart_info
Standard 45% - label - chart_info
Basic 20% - label - chart_info
Recent Activities - label - section_title
Latest customer interactions and transactions - label - section_info
Sarah Johnson - label - activity_user
Loan Application Approved - label - activity_info
Michael Chen - label - activity_user
$250,000 - label - transaction_amount
2 hours ago - label - transaction_time
Edit with - label - edit_option
Lovable - button - edit_tool



# === FILE: data\openai_response\20250807_112833_customers.txt ===
- Search customers, loans, transactions... - textbox - search
Dashboard - button - navigation
Customers - button - navigation
Loans - button - navigation
Transactions - button - navigation
Tasks - button - navigation
Reports - button - navigation
Analytics - button - navigation
Settings - button - navigation
John Doe - label - user_info
Customers - label - section_title
Manage your customer relationships and accounts - label - section_info
- Search customers... - textbox - search
Export - button - export
+ New Customer - button - add_customer
Filters - button - filter
Customer List - label - section_title
3 customers found - label - section_info
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
Edit with - label - edit_info
Lovable - button - edit_tool
---------------------------------------- After Cleaning ----------------------------------------
Search customers, loans, transactions... - textbox - search
Dashboard - button - navigation
Customers - button - navigation
Loans - button - navigation
Transactions - button - navigation
Tasks - button - navigation
Reports - button - navigation
Analytics - button - navigation
Settings - button - navigation
John Doe - label - user_info
Customers - label - section_title
Manage your customer relationships and accounts - label - section_info
Search customers... - textbox - search
Export - button - export
+ New Customer - button - add_customer
Filters - button - filter
Customer List - label - section_title
3 customers found - label - section_info
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
Edit with - label - edit_info
Lovable - button - edit_tool



# === FILE: data\openai_response\20250807_112854_customers_2.txt ===
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



# === FILE: data\stored\20250807_112822_dashboard.json ===
[
    {
        "id": "c8b96af7-c667-4cf7-ab10-f00534e1358f",
        "document": "",
        "metadata": {
            "external": false,
            "type": "ocr",
            "get_by_text": "",
            "page_name": "dashboard",
            "label_text": "",
            "ocr_type": "button",
            "intent": "navigation",
            "unique_name": "dashboard_button_navigation_34c032c8",
            "element_id": "c8b96af7-c667-4cf7-ab10-f00534e1358f",
            "dom_matched": false,
            "placeholder": ""
        }
    },
    {
        "id": "96804809-411a-4a65-824e-44aecb8eed2d",
        "document": "Search customers, loans, transactions...",
        "metadata": {
            "label_text": "Search customers, loans, transactions...",
            "unique_name": "dashboard_search_customers,_loans,_transactions..._textbox_search_3310a968",
            "external": false,
            "ocr_type": "textbox",
            "page_name": "dashboard",
            "element_id": "96804809-411a-4a65-824e-44aecb8eed2d",
            "dom_matched": false,
            "placeholder": "Search customers, loans, transactions...",
            "get_by_text": "Search customers, loans, transactions...",
            "type": "ocr",
            "intent": "search"
        }
    },
    {
        "id": "c01e1667-86a9-4c43-834c-58d9403b2f54",
        "document": "Dashboard",
        "metadata": {
            "type": "ocr",
            "unique_name": "dashboard_dashboard_button_navigation_83914516",
            "get_by_text": "Dashboard",
            "external": false,
            "label_text": "Dashboard",
            "intent": "navigation",
            "dom_matched": false,
            "page_name": "dashboard",
            "element_id": "c01e1667-86a9-4c43-834c-58d9403b2f54",
            "placeholder": "Dashboard",
            "ocr_type": "button"
        }
    },
    {
        "id": "3bce5461-20c5-476c-a822-3e58412043cf",
        "document": "Customers",
        "metadata": {
            "type": "ocr",
            "intent": "navigation",
            "dom_matched": false,
            "page_name": "dashboard",
            "ocr_type": "button",
            "external": false,
            "label_text": "Customers",
            "unique_name": "dashboard_customers_button_navigation_bb4303b6",
            "placeholder": "Customers",
            "get_by_text": "Customers",
            "element_id": "3bce5461-20c5-476c-a822-3e58412043cf"
        }
    },
    {
        "id": "5011d652-56a6-4e0e-b013-a1d6a1f1dc7c",
        "document": "Loans",
        "metadata": {
            "ocr_type": "button",
            "external": false,
            "placeholder": "Loans",
            "unique_name": "dashboard_loans_button_navigation_42436e2a",
            "type": "ocr",
            "page_name": "dashboard",
            "dom_matched": false,
            "label_text": "Loans",
            "element_id": "5011d652-56a6-4e0e-b013-a1d6a1f1dc7c",
            "intent": "navigation",
            "get_by_text": "Loans"
        }
    },
    {
        "id": "e0cd985e-43a7-4faa-8f39-cc0c10bef035",
        "document": "Transactions",
        "metadata": {
            "placeholder": "Transactions",
            "page_name": "dashboard",
            "get_by_text": "Transactions",
            "type": "ocr",
            "intent": "navigation",
            "external": false,
            "unique_name": "dashboard_transactions_button_navigation_f0479a72",
            "label_text": "Transactions",
            "ocr_type": "button",
            "element_id": "e0cd985e-43a7-4faa-8f39-cc0c10bef035",
            "dom_matched": false
        }
    },
    {
        "id": "958eaaee-2088-4840-a811-34bbe4c7f4ee",
        "document": "Tasks",
        "metadata": {
            "get_by_text": "Tasks",
            "dom_matched": false,
            "unique_name": "dashboard_tasks_button_navigation_cde2a4d6",
            "ocr_type": "button",
            "intent": "navigation",
            "type": "ocr",
            "external": false,
            "element_id": "958eaaee-2088-4840-a811-34bbe4c7f4ee",
            "placeholder": "Tasks",
            "label_text": "Tasks",
            "page_name": "dashboard"
        }
    },
    {
        "id": "3fe79ef0-fcb3-4049-bb6c-564ba85d6d15",
        "document": "Reports",
        "metadata": {
            "placeholder": "Reports",
            "dom_matched": false,
            "intent": "navigation",
            "page_name": "dashboard",
            "get_by_text": "Reports",
            "ocr_type": "button",
            "label_text": "Reports",
            "type": "ocr",
            "element_id": "3fe79ef0-fcb3-4049-bb6c-564ba85d6d15",
            "external": false,
            "unique_name": "dashboard_reports_button_navigation_578fb659"
        }
    },
    {
        "id": "9a53c302-4c9f-454e-bb36-50f9fd1785a4",
        "document": "Analytics",
        "metadata": {
            "intent": "navigation",
            "dom_matched": false,
            "placeholder": "Analytics",
            "external": false,
            "type": "ocr",
            "unique_name": "dashboard_analytics_button_navigation_49884ab5",
            "label_text": "Analytics",
            "page_name": "dashboard",
            "get_by_text": "Analytics",
            "ocr_type": "button",
            "element_id": "9a53c302-4c9f-454e-bb36-50f9fd1785a4"
        }
    },
    {
        "id": "bd6766fc-75f1-4154-b4ed-3fa7142c0b70",
        "document": "Settings",
        "metadata": {
            "get_by_text": "Settings",
            "type": "ocr",
            "element_id": "bd6766fc-75f1-4154-b4ed-3fa7142c0b70",
            "dom_matched": false,
            "intent": "navigation",
            "ocr_type": "button",
            "placeholder": "Settings",
            "unique_name": "dashboard_settings_button_navigation_7a36fd5d",
            "page_name": "dashboard",
            "label_text": "Settings",
            "external": false
        }
    },
    {
        "id": "2d8b143f-aa2b-4e82-8ffc-cf27174d281e",
        "document": "Dashboard",
        "metadata": {
            "label_text": "Dashboard",
            "unique_name": "dashboard_dashboard_label_page_title_a353b4f0",
            "page_name": "dashboard",
            "placeholder": "Dashboard",
            "type": "ocr",
            "dom_matched": false,
            "get_by_text": "Dashboard",
            "external": false,
            "ocr_type": "label",
            "element_id": "2d8b143f-aa2b-4e82-8ffc-cf27174d281e",
            "intent": "page_title"
        }
    },
    {
        "id": "589cf01e-f3b2-41a4-b45e-a3e8b5877c56",
        "document": "Welcome back! Here's your banking overview.",
        "metadata": {
            "unique_name": "dashboard_welcome_back!_heres_your_banking_overview._label_greeting_bd321dde",
            "get_by_text": "Welcome back! Here's your banking overview.",
            "type": "ocr",
            "intent": "greeting",
            "external": false,
            "placeholder": "Welcome back! Here's your banking overview.",
            "element_id": "589cf01e-f3b2-41a4-b45e-a3e8b5877c56",
            "dom_matched": false,
            "label_text": "Welcome back! Here's your banking overview.",
            "page_name": "dashboard",
            "ocr_type": "label"
        }
    },
    {
        "id": "ccf017b5-69b6-49c5-84e9-afbcaf35a632",
        "document": "Total Customers",
        "metadata": {
            "placeholder": "Total Customers",
            "type": "ocr",
            "unique_name": "dashboard_total_customers_label_metric_title_9728f1cf",
            "element_id": "ccf017b5-69b6-49c5-84e9-afbcaf35a632",
            "label_text": "Total Customers",
            "page_name": "dashboard",
            "dom_matched": false,
            "intent": "metric_title",
            "external": false,
            "get_by_text": "Total Customers",
            "ocr_type": "label"
        }
    },
    {
        "id": "c659e1be-61d0-4ad9-a1ef-570349d6dde5",
        "document": "2,847",
        "metadata": {
            "label_text": "2,847",
            "ocr_type": "label",
            "unique_name": "dashboard_2,847_label_metric_value_fdec317c",
            "dom_matched": false,
            "placeholder": "2,847",
            "type": "ocr",
            "get_by_text": "2,847",
            "external": false,
            "page_name": "dashboard",
            "element_id": "c659e1be-61d0-4ad9-a1ef-570349d6dde5",
            "intent": "metric_value"
        }
    },
    {
        "id": "3d2b69f8-4ba3-44fa-a682-41fa61403283",
        "document": "Active Loans",
        "metadata": {
            "dom_matched": false,
            "label_text": "Active Loans",
            "ocr_type": "label",
            "page_name": "dashboard",
            "element_id": "3d2b69f8-4ba3-44fa-a682-41fa61403283",
            "type": "ocr",
            "external": false,
            "unique_name": "dashboard_active_loans_label_metric_title_7b8dadc2",
            "get_by_text": "Active Loans",
            "placeholder": "Active Loans",
            "intent": "metric_title"
        }
    },
    {
        "id": "5149fba3-5d4c-456d-8bf1-80fe6d14d028",
        "document": "$45.2M",
        "metadata": {
            "type": "ocr",
            "label_text": "$45.2M",
            "dom_matched": false,
            "ocr_type": "label",
            "intent": "metric_value",
            "external": false,
            "page_name": "dashboard",
            "element_id": "5149fba3-5d4c-456d-8bf1-80fe6d14d028",
            "get_by_text": "$45.2M",
            "unique_name": "dashboard_$45.2m_label_metric_value_4a2ef93a",
            "placeholder": "$45.2M"
        }
    },
    {
        "id": "e7d2dc34-a120-4378-9daf-c79c97eb33b3",
        "document": "Monthly Transactions",
        "metadata": {
            "external": false,
            "ocr_type": "label",
            "placeholder": "Monthly Transactions",
            "intent": "metric_title",
            "label_text": "Monthly Transactions",
            "dom_matched": false,
            "type": "ocr",
            "get_by_text": "Monthly Transactions",
            "page_name": "dashboard",
            "unique_name": "dashboard_monthly_transactions_label_metric_title_12ed8182",
            "element_id": "e7d2dc34-a120-4378-9daf-c79c97eb33b3"
        }
    },
    {
        "id": "c66a73b8-d209-4c69-af99-b528514ab320",
        "document": "18,394",
        "metadata": {
            "element_id": "c66a73b8-d209-4c69-af99-b528514ab320",
            "label_text": "18,394",
            "type": "ocr",
            "dom_matched": false,
            "get_by_text": "18,394",
            "external": false,
            "unique_name": "dashboard_18,394_label_metric_value_b6b442dd",
            "ocr_type": "label",
            "intent": "metric_value",
            "placeholder": "18,394",
            "page_name": "dashboard"
        }
    },
    {
        "id": "8621f44c-3a17-4bc0-9074-2ae49c0649ed",
        "document": "Revenue Growth",
        "metadata": {
            "dom_matched": false,
            "label_text": "Revenue Growth",
            "page_name": "dashboard",
            "intent": "metric_title",
            "get_by_text": "Revenue Growth",
            "external": false,
            "ocr_type": "label",
            "type": "ocr",
            "element_id": "8621f44c-3a17-4bc0-9074-2ae49c0649ed",
            "unique_name": "dashboard_revenue_growth_label_metric_title_d1a487c9",
            "placeholder": "Revenue Growth"
        }
    },
    {
        "id": "2317fcd1-0194-45aa-b353-1a31c81e4a56",
        "document": "4%",
        "metadata": {
            "dom_matched": false,
            "element_id": "2317fcd1-0194-45aa-b353-1a31c81e4a56",
            "placeholder": "4%",
            "external": false,
            "intent": "metric_value",
            "ocr_type": "label",
            "get_by_text": "4%",
            "label_text": "4%",
            "type": "ocr",
            "unique_name": "dashboard_4%_label_metric_value_316201d4",
            "page_name": "dashboard"
        }
    },
    {
        "id": "57192da2-3cc2-4855-b250-3cf3d80f0a62",
        "document": "Export Report",
        "metadata": {
            "external": false,
            "page_name": "dashboard",
            "get_by_text": "Export Report",
            "ocr_type": "button",
            "element_id": "57192da2-3cc2-4855-b250-3cf3d80f0a62",
            "unique_name": "dashboard_export_report_button_export_ed26f6d4",
            "intent": "export",
            "placeholder": "Export Report",
            "label_text": "Export Report",
            "type": "ocr",
            "dom_matched": false
        }
    },
    {
        "id": "7068d846-c40e-4aa1-9ecf-241bdcbd6a76",
        "document": "Loan Portfolio Trend",
        "metadata": {
            "external": false,
            "placeholder": "Loan Portfolio Trend",
            "label_text": "Loan Portfolio Trend",
            "type": "ocr",
            "intent": "section_title",
            "page_name": "dashboard",
            "dom_matched": false,
            "unique_name": "dashboard_loan_portfolio_trend_label_section_title_32cf7d0c",
            "ocr_type": "label",
            "element_id": "7068d846-c40e-4aa1-9ecf-241bdcbd6a76",
            "get_by_text": "Loan Portfolio Trend"
        }
    },
    {
        "id": "1d298799-b832-40df-84c0-7e40b4e10e9f",
        "document": "Monthly loan disbursements over the last 6 months",
        "metadata": {
            "label_text": "Monthly loan disbursements over the last 6 months",
            "type": "ocr",
            "unique_name": "dashboard_monthly_loan_disbursements_over_the_last_6_months_label_section_info_790102ea",
            "dom_matched": false,
            "page_name": "dashboard",
            "ocr_type": "label",
            "intent": "section_info",
            "element_id": "1d298799-b832-40df-84c0-7e40b4e10e9f",
            "get_by_text": "Monthly loan disbursements over the last 6 months",
            "placeholder": "Monthly loan disbursements over the last 6 months",
            "external": false
        }
    },
    {
        "id": "bb6942fc-68bb-466d-9d24-aff2ce7728ec",
        "document": "Customer Distribution",
        "metadata": {
            "get_by_text": "Customer Distribution",
            "unique_name": "dashboard_customer_distribution_label_section_title_4bc10c83",
            "type": "ocr",
            "page_name": "dashboard",
            "ocr_type": "label",
            "label_text": "Customer Distribution",
            "external": false,
            "element_id": "bb6942fc-68bb-466d-9d24-aff2ce7728ec",
            "placeholder": "Customer Distribution",
            "intent": "section_title",
            "dom_matched": false
        }
    },
    {
        "id": "9d778496-97a6-452d-858c-ccedd1f9d85b",
        "document": "Customer segments by account type",
        "metadata": {
            "placeholder": "Customer segments by account type",
            "ocr_type": "label",
            "intent": "section_info",
            "unique_name": "dashboard_customer_segments_by_account_type_label_section_info_e21a781f",
            "label_text": "Customer segments by account type",
            "element_id": "9d778496-97a6-452d-858c-ccedd1f9d85b",
            "type": "ocr",
            "external": false,
            "page_name": "dashboard",
            "dom_matched": false,
            "get_by_text": "Customer segments by account type"
        }
    },
    {
        "id": "a9c9e92f-aa27-4aea-b103-12bd04f427f3",
        "document": "Premium 35%",
        "metadata": {
            "dom_matched": false,
            "element_id": "a9c9e92f-aa27-4aea-b103-12bd04f427f3",
            "placeholder": "Premium 35%",
            "intent": "chart_info",
            "unique_name": "dashboard_premium_35%_label_chart_info_e6423d22",
            "external": false,
            "get_by_text": "Premium 35%",
            "ocr_type": "label",
            "type": "ocr",
            "label_text": "Premium 35%",
            "page_name": "dashboard"
        }
    },
    {
        "id": "2ab97d9e-ded8-4325-8bf9-cfb1b0eb3854",
        "document": "Standard 45%",
        "metadata": {
            "page_name": "dashboard",
            "external": false,
            "ocr_type": "label",
            "dom_matched": false,
            "type": "ocr",
            "placeholder": "Standard 45%",
            "element_id": "2ab97d9e-ded8-4325-8bf9-cfb1b0eb3854",
            "get_by_text": "Standard 45%",
            "unique_name": "dashboard_standard_45%_label_chart_info_d70c74e7",
            "intent": "chart_info",
            "label_text": "Standard 45%"
        }
    },
    {
        "id": "fe24f6db-3635-45e0-a23f-8921e6bcdb73",
        "document": "Basic 20%",
        "metadata": {
            "dom_matched": false,
            "external": false,
            "placeholder": "Basic 20%",
            "get_by_text": "Basic 20%",
            "ocr_type": "label",
            "page_name": "dashboard",
            "label_text": "Basic 20%",
            "intent": "chart_info",
            "unique_name": "dashboard_basic_20%_label_chart_info_7bda856f",
            "element_id": "fe24f6db-3635-45e0-a23f-8921e6bcdb73",
            "type": "ocr"
        }
    },
    {
        "id": "70f8cd90-eab3-428a-a474-b6a37688197d",
        "document": "Recent Activities",
        "metadata": {
            "ocr_type": "label",
            "dom_matched": false,
            "type": "ocr",
            "element_id": "70f8cd90-eab3-428a-a474-b6a37688197d",
            "external": false,
            "placeholder": "Recent Activities",
            "label_text": "Recent Activities",
            "page_name": "dashboard",
            "intent": "section_title",
            "get_by_text": "Recent Activities",
            "unique_name": "dashboard_recent_activities_label_section_title_c5dd6139"
        }
    },
    {
        "id": "48893a94-fbcc-44ab-a8b4-86c0c13f3e0d",
        "document": "Latest customer interactions and transactions",
        "metadata": {
            "unique_name": "dashboard_latest_customer_interactions_and_transactions_label_section_info_5c741538",
            "type": "ocr",
            "get_by_text": "Latest customer interactions and transactions",
            "page_name": "dashboard",
            "intent": "section_info",
            "placeholder": "Latest customer interactions and transactions",
            "element_id": "48893a94-fbcc-44ab-a8b4-86c0c13f3e0d",
            "external": false,
            "ocr_type": "label",
            "label_text": "Latest customer interactions and transactions",
            "dom_matched": false
        }
    },
    {
        "id": "8a7c9a5c-4c74-4a40-8c78-252f4f867ef5",
        "document": "Sarah Johnson",
        "metadata": {
            "page_name": "dashboard",
            "label_text": "Sarah Johnson",
            "dom_matched": false,
            "unique_name": "dashboard_sarah_johnson_label_activity_user_309b9d18",
            "intent": "activity_user",
            "external": false,
            "get_by_text": "Sarah Johnson",
            "element_id": "8a7c9a5c-4c74-4a40-8c78-252f4f867ef5",
            "placeholder": "Sarah Johnson",
            "ocr_type": "label",
            "type": "ocr"
        }
    },
    {
        "id": "6ca1c4d1-b5ab-4640-8317-3f9cfaf56437",
        "document": "Loan Application Approved",
        "metadata": {
            "element_id": "6ca1c4d1-b5ab-4640-8317-3f9cfaf56437",
            "unique_name": "dashboard_loan_application_approved_label_activity_info_969d6763",
            "intent": "activity_info",
            "type": "ocr",
            "external": false,
            "dom_matched": false,
            "placeholder": "Loan Application Approved",
            "page_name": "dashboard",
            "get_by_text": "Loan Application Approved",
            "ocr_type": "label",
            "label_text": "Loan Application Approved"
        }
    },
    {
        "id": "0ffa2134-5c60-475e-bbe5-2cf962c6458c",
        "document": "Michael Chen",
        "metadata": {
            "get_by_text": "Michael Chen",
            "ocr_type": "label",
            "dom_matched": false,
            "intent": "activity_user",
            "external": false,
            "page_name": "dashboard",
            "type": "ocr",
            "placeholder": "Michael Chen",
            "unique_name": "dashboard_michael_chen_label_activity_user_f041a3aa",
            "label_text": "Michael Chen",
            "element_id": "0ffa2134-5c60-475e-bbe5-2cf962c6458c"
        }
    },
    {
        "id": "c146bcdb-14d3-41e8-a42c-11a22809eb1f",
        "document": "$250,000",
        "metadata": {
            "intent": "transaction_amount",
            "element_id": "c146bcdb-14d3-41e8-a42c-11a22809eb1f",
            "label_text": "$250,000",
            "placeholder": "$250,000",
            "unique_name": "dashboard_$250,000_label_transaction_amount_14fd1f5f",
            "dom_matched": false,
            "get_by_text": "$250,000",
            "external": false,
            "page_name": "dashboard",
            "ocr_type": "label",
            "type": "ocr"
        }
    },
    {
        "id": "50bb6bbd-9c7f-4789-bd90-01d516da1f73",
        "document": "2 hours ago",
        "metadata": {
            "label_text": "2 hours ago",
            "type": "ocr",
            "page_name": "dashboard",
            "element_id": "50bb6bbd-9c7f-4789-bd90-01d516da1f73",
            "intent": "transaction_time",
            "get_by_text": "2 hours ago",
            "ocr_type": "label",
            "external": false,
            "unique_name": "dashboard_2_hours_ago_label_transaction_time_a74efe28",
            "placeholder": "2 hours ago",
            "dom_matched": false
        }
    },
    {
        "id": "04ea7dde-967c-4d48-bc75-8969ad8d6bb6",
        "document": "Edit with",
        "metadata": {
            "placeholder": "Edit with",
            "get_by_text": "Edit with",
            "element_id": "04ea7dde-967c-4d48-bc75-8969ad8d6bb6",
            "external": false,
            "page_name": "dashboard",
            "dom_matched": false,
            "unique_name": "dashboard_edit_with_label_edit_option_88c64fc9",
            "intent": "edit_option",
            "ocr_type": "label",
            "type": "ocr",
            "label_text": "Edit with"
        }
    },
    {
        "id": "7b6de3c9-af25-42d1-b55c-721722bd7138",
        "document": "Lovable",
        "metadata": {
            "label_text": "Lovable",
            "unique_name": "dashboard_lovable_button_edit_tool_2de51406",
            "external": false,
            "dom_matched": false,
            "get_by_text": "Lovable",
            "element_id": "7b6de3c9-af25-42d1-b55c-721722bd7138",
            "intent": "edit_tool",
            "type": "ocr",
            "placeholder": "Lovable",
            "page_name": "dashboard",
            "ocr_type": "button"
        }
    }
]


# === FILE: data\stored\20250807_112845_customers.json ===
[
    {
        "id": "7c8603cf-65e2-42e4-be5a-ab7dfb10587c",
        "document": "Search customers, loans, transactions...",
        "metadata": {
            "dom_matched": false,
            "external": false,
            "element_id": "7c8603cf-65e2-42e4-be5a-ab7dfb10587c",
            "intent": "search",
            "placeholder": "Search customers, loans, transactions...",
            "get_by_text": "Search customers, loans, transactions...",
            "type": "ocr",
            "label_text": "Search customers, loans, transactions...",
            "page_name": "customers",
            "unique_name": "customers_search_customers,_loans,_transactions..._textbox_search_be73039f",
            "ocr_type": "textbox"
        }
    },
    {
        "id": "a950f551-13a8-4bde-aaa2-c4b96125f740",
        "document": "Dashboard",
        "metadata": {
            "dom_matched": false,
            "intent": "navigation",
            "get_by_text": "Dashboard",
            "label_text": "Dashboard",
            "unique_name": "customers_dashboard_button_navigation_fb22376c",
            "placeholder": "Dashboard",
            "page_name": "customers",
            "type": "ocr",
            "external": false,
            "ocr_type": "button",
            "element_id": "a950f551-13a8-4bde-aaa2-c4b96125f740"
        }
    },
    {
        "id": "b3c09d9d-297d-43fb-866f-d6d6fdb6be27",
        "document": "Customers",
        "metadata": {
            "placeholder": "Customers",
            "page_name": "customers",
            "ocr_type": "button",
            "unique_name": "customers_customers_button_navigation_62cd2bf8",
            "dom_matched": false,
            "external": false,
            "get_by_text": "Customers",
            "type": "ocr",
            "label_text": "Customers",
            "element_id": "b3c09d9d-297d-43fb-866f-d6d6fdb6be27",
            "intent": "navigation"
        }
    },
    {
        "id": "510084f4-bc9a-4cd5-8221-bcae4ea15eba",
        "document": "Loans",
        "metadata": {
            "external": false,
            "intent": "navigation",
            "get_by_text": "Loans",
            "type": "ocr",
            "dom_matched": false,
            "placeholder": "Loans",
            "page_name": "customers",
            "element_id": "510084f4-bc9a-4cd5-8221-bcae4ea15eba",
            "ocr_type": "button",
            "label_text": "Loans",
            "unique_name": "customers_loans_button_navigation_f083cd47"
        }
    },
    {
        "id": "18a781ff-8f2a-4f8b-b201-0b62956c3652",
        "document": "Transactions",
        "metadata": {
            "intent": "navigation",
            "label_text": "Transactions",
            "element_id": "18a781ff-8f2a-4f8b-b201-0b62956c3652",
            "placeholder": "Transactions",
            "ocr_type": "button",
            "dom_matched": false,
            "unique_name": "customers_transactions_button_navigation_bb833203",
            "type": "ocr",
            "external": false,
            "page_name": "customers",
            "get_by_text": "Transactions"
        }
    },
    {
        "id": "e7856553-2167-4099-8d07-90018bb009bc",
        "document": "Tasks",
        "metadata": {
            "page_name": "customers",
            "placeholder": "Tasks",
            "type": "ocr",
            "external": false,
            "element_id": "e7856553-2167-4099-8d07-90018bb009bc",
            "ocr_type": "button",
            "unique_name": "customers_tasks_button_navigation_63e52ff9",
            "label_text": "Tasks",
            "dom_matched": false,
            "get_by_text": "Tasks",
            "intent": "navigation"
        }
    },
    {
        "id": "b0cbf374-0acb-4b04-9625-19da9eb7c8b6",
        "document": "Reports",
        "metadata": {
            "get_by_text": "Reports",
            "placeholder": "Reports",
            "ocr_type": "button",
            "dom_matched": false,
            "label_text": "Reports",
            "external": false,
            "element_id": "b0cbf374-0acb-4b04-9625-19da9eb7c8b6",
            "unique_name": "customers_reports_button_navigation_1dc35b9f",
            "type": "ocr",
            "page_name": "customers",
            "intent": "navigation"
        }
    },
    {
        "id": "e785909d-e9b1-428b-b8c7-cd2abf051547",
        "document": "Analytics",
        "metadata": {
            "ocr_type": "button",
            "element_id": "e785909d-e9b1-428b-b8c7-cd2abf051547",
            "placeholder": "Analytics",
            "page_name": "customers",
            "intent": "navigation",
            "type": "ocr",
            "get_by_text": "Analytics",
            "unique_name": "customers_analytics_button_navigation_8227d101",
            "external": false,
            "dom_matched": false,
            "label_text": "Analytics"
        }
    },
    {
        "id": "e8c7501c-a8a1-47e3-acc8-b3ed5513a410",
        "document": "Settings",
        "metadata": {
            "page_name": "customers",
            "placeholder": "Settings",
            "type": "ocr",
            "unique_name": "customers_settings_button_navigation_9de99b8a",
            "intent": "navigation",
            "label_text": "Settings",
            "element_id": "e8c7501c-a8a1-47e3-acc8-b3ed5513a410",
            "external": false,
            "ocr_type": "button",
            "dom_matched": false,
            "get_by_text": "Settings"
        }
    },
    {
        "id": "397ca042-75d0-4c05-ae59-dd12b3420594",
        "document": "John Doe",
        "metadata": {
            "element_id": "397ca042-75d0-4c05-ae59-dd12b3420594",
            "type": "ocr",
            "external": false,
            "placeholder": "John Doe",
            "label_text": "John Doe",
            "intent": "user_info",
            "page_name": "customers",
            "get_by_text": "John Doe",
            "ocr_type": "label",
            "dom_matched": false,
            "unique_name": "customers_john_doe_label_user_info_64be4d99"
        }
    },
    {
        "id": "54403b9a-6ab1-4eed-8a3c-2b94060a9e6f",
        "document": "Customers",
        "metadata": {
            "type": "ocr",
            "get_by_text": "Customers",
            "element_id": "54403b9a-6ab1-4eed-8a3c-2b94060a9e6f",
            "label_text": "Customers",
            "unique_name": "customers_customers_label_section_title_2ec8510a",
            "placeholder": "Customers",
            "external": false,
            "ocr_type": "label",
            "page_name": "customers",
            "dom_matched": false,
            "intent": "section_title"
        }
    },
    {
        "id": "fddfa206-8a58-42d8-8422-0dd00056b662",
        "document": "Manage your customer relationships and accounts",
        "metadata": {
            "page_name": "customers",
            "label_text": "Manage your customer relationships and accounts",
            "unique_name": "customers_manage_your_customer_relationships_and_accounts_label_section_info_f20c0595",
            "placeholder": "Manage your customer relationships and accounts",
            "ocr_type": "label",
            "external": false,
            "dom_matched": false,
            "type": "ocr",
            "element_id": "fddfa206-8a58-42d8-8422-0dd00056b662",
            "get_by_text": "Manage your customer relationships and accounts",
            "intent": "section_info"
        }
    },
    {
        "id": "84a21b00-b3cc-44ab-af92-cb32a03b80a5",
        "document": "Search customers...",
        "metadata": {
            "unique_name": "customers_search_customers..._textbox_search_85d3ce1f",
            "placeholder": "Search customers...",
            "type": "ocr",
            "intent": "search",
            "get_by_text": "Search customers...",
            "label_text": "Search customers...",
            "ocr_type": "textbox",
            "page_name": "customers",
            "element_id": "84a21b00-b3cc-44ab-af92-cb32a03b80a5",
            "dom_matched": false,
            "external": false
        }
    },
    {
        "id": "754e885e-ab7c-41d7-894a-7d6c2a7232dd",
        "document": "Export",
        "metadata": {
            "element_id": "754e885e-ab7c-41d7-894a-7d6c2a7232dd",
            "dom_matched": false,
            "get_by_text": "Export",
            "intent": "export",
            "type": "ocr",
            "ocr_type": "button",
            "page_name": "customers",
            "external": false,
            "label_text": "Export",
            "unique_name": "customers_export_button_export_ec306f18",
            "placeholder": "Export"
        }
    },
    {
        "id": "bb353c7f-0aed-40b1-ad07-8e9411162863",
        "document": "+ New Customer",
        "metadata": {
            "get_by_text": "+ New Customer",
            "unique_name": "customers_+_new_customer_button_add_customer_e84a62b3",
            "placeholder": "+ New Customer",
            "ocr_type": "button",
            "page_name": "customers",
            "external": false,
            "element_id": "bb353c7f-0aed-40b1-ad07-8e9411162863",
            "label_text": "+ New Customer",
            "intent": "add_customer",
            "dom_matched": false,
            "type": "ocr"
        }
    },
    {
        "id": "9d406a26-39b0-4e72-b9ba-44dcd3719729",
        "document": "Filters",
        "metadata": {
            "ocr_type": "button",
            "label_text": "Filters",
            "external": false,
            "unique_name": "customers_filters_button_filter_4c0a3d63",
            "placeholder": "Filters",
            "intent": "filter",
            "page_name": "customers",
            "dom_matched": false,
            "type": "ocr",
            "element_id": "9d406a26-39b0-4e72-b9ba-44dcd3719729",
            "get_by_text": "Filters"
        }
    },
    {
        "id": "ae4fdb25-97b8-42a3-816e-70cd76825558",
        "document": "Customer List",
        "metadata": {
            "type": "ocr",
            "page_name": "customers",
            "external": false,
            "label_text": "Customer List",
            "ocr_type": "label",
            "element_id": "ae4fdb25-97b8-42a3-816e-70cd76825558",
            "unique_name": "customers_customer_list_label_section_title_ad47eb6a",
            "get_by_text": "Customer List",
            "dom_matched": false,
            "intent": "section_title",
            "placeholder": "Customer List"
        }
    },
    {
        "id": "4f0d441d-eecf-473a-9759-37d9a9b724e3",
        "document": "3 customers found",
        "metadata": {
            "placeholder": "3 customers found",
            "external": false,
            "element_id": "4f0d441d-eecf-473a-9759-37d9a9b724e3",
            "dom_matched": false,
            "type": "ocr",
            "get_by_text": "3 customers found",
            "unique_name": "customers_3_customers_found_label_section_info_f58e240e",
            "label_text": "3 customers found",
            "intent": "section_info",
            "ocr_type": "label",
            "page_name": "customers"
        }
    },
    {
        "id": "41bdc51c-bd13-43ac-b2f6-f4c14fc096b7",
        "document": "Customer",
        "metadata": {
            "type": "ocr",
            "element_id": "41bdc51c-bd13-43ac-b2f6-f4c14fc096b7",
            "page_name": "customers",
            "get_by_text": "Customer",
            "intent": "column_header",
            "label_text": "Customer",
            "ocr_type": "label",
            "unique_name": "customers_customer_label_column_header_cd74c3eb",
            "external": false,
            "placeholder": "Customer",
            "dom_matched": false
        }
    },
    {
        "id": "6f9c2f5e-d59d-4c9a-9e12-736f73e4fe23",
        "document": "Account Type",
        "metadata": {
            "ocr_type": "label",
            "type": "ocr",
            "page_name": "customers",
            "unique_name": "customers_account_type_label_column_header_a712d19c",
            "placeholder": "Account Type",
            "intent": "column_header",
            "dom_matched": false,
            "external": false,
            "label_text": "Account Type",
            "element_id": "6f9c2f5e-d59d-4c9a-9e12-736f73e4fe23",
            "get_by_text": "Account Type"
        }
    },
    {
        "id": "5f45165f-06fa-4ea2-aff0-7c15c8319963",
        "document": "Balance",
        "metadata": {
            "page_name": "customers",
            "ocr_type": "label",
            "placeholder": "Balance",
            "dom_matched": false,
            "external": false,
            "intent": "column_header",
            "unique_name": "customers_balance_label_column_header_d6648fd2",
            "type": "ocr",
            "get_by_text": "Balance",
            "label_text": "Balance",
            "element_id": "5f45165f-06fa-4ea2-aff0-7c15c8319963"
        }
    },
    {
        "id": "457fdd49-d324-4c7b-9368-689ba17e8d32",
        "document": "Status",
        "metadata": {
            "unique_name": "customers_status_label_column_header_57a06b20",
            "external": false,
            "page_name": "customers",
            "label_text": "Status",
            "placeholder": "Status",
            "ocr_type": "label",
            "type": "ocr",
            "dom_matched": false,
            "element_id": "457fdd49-d324-4c7b-9368-689ba17e8d32",
            "get_by_text": "Status",
            "intent": "column_header"
        }
    },
    {
        "id": "85b72c0b-7dc8-4139-82f6-01de76a16cef",
        "document": "Join Date",
        "metadata": {
            "type": "ocr",
            "ocr_type": "label",
            "element_id": "85b72c0b-7dc8-4139-82f6-01de76a16cef",
            "dom_matched": false,
            "external": false,
            "get_by_text": "Join Date",
            "placeholder": "Join Date",
            "page_name": "customers",
            "intent": "column_header",
            "label_text": "Join Date",
            "unique_name": "customers_join_date_label_column_header_cb167d9a"
        }
    },
    {
        "id": "0cd3cbe2-e666-45cb-86f7-7b988f5ba329",
        "document": "Actions",
        "metadata": {
            "dom_matched": false,
            "ocr_type": "label",
            "page_name": "customers",
            "type": "ocr",
            "label_text": "Actions",
            "intent": "column_header",
            "get_by_text": "Actions",
            "unique_name": "customers_actions_label_column_header_177ddb69",
            "external": false,
            "element_id": "0cd3cbe2-e666-45cb-86f7-7b988f5ba329",
            "placeholder": "Actions"
        }
    },
    {
        "id": "26629015-b51a-43bd-80cb-f1df561bf09f",
        "document": "Sarah Johnson",
        "metadata": {
            "ocr_type": "label",
            "element_id": "26629015-b51a-43bd-80cb-f1df561bf09f",
            "intent": "customer_name",
            "dom_matched": false,
            "unique_name": "customers_sarah_johnson_label_customer_name_91134cc9",
            "label_text": "Sarah Johnson",
            "get_by_text": "Sarah Johnson",
            "type": "ocr",
            "placeholder": "Sarah Johnson",
            "external": false,
            "page_name": "customers"
        }
    },
    {
        "id": "fba877fa-d301-4d55-8733-4d94c8765702",
        "document": "sarah.johnson@email.com",
        "metadata": {
            "external": false,
            "get_by_text": "sarah.johnson@email.com",
            "unique_name": "customers_sarah.johnson@email.com_label_customer_email_ea79968a",
            "page_name": "customers",
            "ocr_type": "label",
            "type": "ocr",
            "element_id": "fba877fa-d301-4d55-8733-4d94c8765702",
            "intent": "customer_email",
            "placeholder": "sarah.johnson@email.com",
            "label_text": "sarah.johnson@email.com",
            "dom_matched": false
        }
    },
    {
        "id": "3d7db369-1820-41e6-99ac-1b5871f6ed0a",
        "document": "Premium",
        "metadata": {
            "type": "ocr",
            "unique_name": "customers_premium_label_account_type_c1ae4279",
            "intent": "account_type",
            "ocr_type": "label",
            "external": false,
            "page_name": "customers",
            "placeholder": "Premium",
            "dom_matched": false,
            "element_id": "3d7db369-1820-41e6-99ac-1b5871f6ed0a",
            "label_text": "Premium",
            "get_by_text": "Premium"
        }
    },
    {
        "id": "ac3036e9-4360-4e93-9f29-35910c410ccb",
        "document": "$1,45,000",
        "metadata": {
            "label_text": "$1,45,000",
            "page_name": "customers",
            "type": "ocr",
            "placeholder": "$1,45,000",
            "intent": "balance",
            "dom_matched": false,
            "external": false,
            "unique_name": "customers_$1,45,000_label_balance_dc74e6a8",
            "get_by_text": "$1,45,000",
            "element_id": "ac3036e9-4360-4e93-9f29-35910c410ccb",
            "ocr_type": "label"
        }
    },
    {
        "id": "817de9de-248f-4451-86dd-3c22b855609e",
        "document": "Active",
        "metadata": {
            "label_text": "Active",
            "element_id": "817de9de-248f-4451-86dd-3c22b855609e",
            "ocr_type": "label",
            "unique_name": "customers_active_label_status_5fc1bbb1",
            "page_name": "customers",
            "get_by_text": "Active",
            "type": "ocr",
            "dom_matched": false,
            "intent": "status",
            "external": false,
            "placeholder": "Active"
        }
    },
    {
        "id": "6498a461-79ea-4f52-8fa1-4bbe99421e00",
        "document": "2023-01-15",
        "metadata": {
            "unique_name": "customers_2023-01-15_label_join_date_13b4a3e0",
            "page_name": "customers",
            "dom_matched": false,
            "element_id": "6498a461-79ea-4f52-8fa1-4bbe99421e00",
            "label_text": "2023-01-15",
            "ocr_type": "label",
            "intent": "join_date",
            "placeholder": "2023-01-15",
            "get_by_text": "2023-01-15",
            "external": false,
            "type": "ocr"
        }
    },
    {
        "id": "91a1c76a-a72a-4043-a53c-1923168c1674",
        "document": "",
        "metadata": {
            "label_text": "",
            "ocr_type": "button",
            "placeholder": "",
            "get_by_text": "",
            "dom_matched": false,
            "external": false,
            "page_name": "customers",
            "element_id": "91a1c76a-a72a-4043-a53c-1923168c1674",
            "unique_name": "customers_button_view_action_cc60ce91",
            "intent": "view_action",
            "type": "ocr"
        }
    },
    {
        "id": "1f7500c4-990c-47c5-9278-0f811b26226e",
        "document": "",
        "metadata": {
            "type": "ocr",
            "dom_matched": false,
            "external": false,
            "ocr_type": "button",
            "intent": "edit_action",
            "unique_name": "customers_button_edit_action_d3d0df61",
            "placeholder": "",
            "element_id": "1f7500c4-990c-47c5-9278-0f811b26226e",
            "label_text": "",
            "get_by_text": "",
            "page_name": "customers"
        }
    },
    {
        "id": "f19fe4b7-6bed-4ead-8aa9-ac3de9246a17",
        "document": "Michael Chen",
        "metadata": {
            "ocr_type": "label",
            "page_name": "customers",
            "type": "ocr",
            "placeholder": "Michael Chen",
            "unique_name": "customers_michael_chen_label_customer_name_8dbd8345",
            "intent": "customer_name",
            "dom_matched": false,
            "label_text": "Michael Chen",
            "get_by_text": "Michael Chen",
            "external": false,
            "element_id": "f19fe4b7-6bed-4ead-8aa9-ac3de9246a17"
        }
    },
    {
        "id": "b977bf95-51a2-41c7-a529-6a76f39d28fc",
        "document": "michael.chen@email.com",
        "metadata": {
            "element_id": "b977bf95-51a2-41c7-a529-6a76f39d28fc",
            "placeholder": "michael.chen@email.com",
            "unique_name": "customers_michael.chen@email.com_label_customer_email_8f50f16b",
            "type": "ocr",
            "ocr_type": "label",
            "dom_matched": false,
            "get_by_text": "michael.chen@email.com",
            "label_text": "michael.chen@email.com",
            "external": false,
            "page_name": "customers",
            "intent": "customer_email"
        }
    },
    {
        "id": "47b9416a-2e37-4d48-9cb5-490b3ab5d3d9",
        "document": "Standard",
        "metadata": {
            "dom_matched": false,
            "external": false,
            "type": "ocr",
            "unique_name": "customers_standard_label_account_type_ef9be216",
            "page_name": "customers",
            "get_by_text": "Standard",
            "intent": "account_type",
            "ocr_type": "label",
            "placeholder": "Standard",
            "label_text": "Standard",
            "element_id": "47b9416a-2e37-4d48-9cb5-490b3ab5d3d9"
        }
    },
    {
        "id": "0a552a01-927a-4f39-b59d-54a65c5aeaad",
        "document": "$52,000",
        "metadata": {
            "type": "ocr",
            "ocr_type": "label",
            "dom_matched": false,
            "get_by_text": "$52,000",
            "placeholder": "$52,000",
            "element_id": "0a552a01-927a-4f39-b59d-54a65c5aeaad",
            "external": false,
            "unique_name": "customers_$52,000_label_balance_b6e2bd67",
            "label_text": "$52,000",
            "intent": "balance",
            "page_name": "customers"
        }
    },
    {
        "id": "817de9de-248f-4451-86dd-3c22b855609e",
        "document": "Active",
        "metadata": {
            "element_id": "817de9de-248f-4451-86dd-3c22b855609e",
            "get_by_text": "Active",
            "page_name": "customers",
            "label_text": "Active",
            "dom_matched": false,
            "placeholder": "Active",
            "intent": "status",
            "external": false,
            "type": "ocr",
            "unique_name": "customers_active_label_status_5fc1bbb1",
            "ocr_type": "label"
        }
    },
    {
        "id": "4c127842-8648-4508-bbeb-e7cebfd480d2",
        "document": "2023-03-22",
        "metadata": {
            "external": false,
            "dom_matched": false,
            "placeholder": "2023-03-22",
            "page_name": "customers",
            "get_by_text": "2023-03-22",
            "unique_name": "customers_2023-03-22_label_join_date_363240e3",
            "label_text": "2023-03-22",
            "element_id": "4c127842-8648-4508-bbeb-e7cebfd480d2",
            "type": "ocr",
            "intent": "join_date",
            "ocr_type": "label"
        }
    },
    {
        "id": "91a1c76a-a72a-4043-a53c-1923168c1674",
        "document": "",
        "metadata": {
            "ocr_type": "button",
            "page_name": "customers",
            "unique_name": "customers_button_view_action_cc60ce91",
            "get_by_text": "",
            "element_id": "91a1c76a-a72a-4043-a53c-1923168c1674",
            "external": false,
            "label_text": "",
            "dom_matched": false,
            "type": "ocr",
            "placeholder": "",
            "intent": "view_action"
        }
    },
    {
        "id": "1f7500c4-990c-47c5-9278-0f811b26226e",
        "document": "",
        "metadata": {
            "element_id": "1f7500c4-990c-47c5-9278-0f811b26226e",
            "ocr_type": "button",
            "type": "ocr",
            "label_text": "",
            "unique_name": "customers_button_edit_action_d3d0df61",
            "get_by_text": "",
            "placeholder": "",
            "dom_matched": false,
            "page_name": "customers",
            "intent": "edit_action",
            "external": false
        }
    },
    {
        "id": "c43ac2f8-db98-4ac4-9482-a4d88b4aff25",
        "document": "Emma Davis",
        "metadata": {
            "page_name": "customers",
            "ocr_type": "label",
            "label_text": "Emma Davis",
            "unique_name": "customers_emma_davis_label_customer_name_671b9ccd",
            "type": "ocr",
            "external": false,
            "element_id": "c43ac2f8-db98-4ac4-9482-a4d88b4aff25",
            "dom_matched": false,
            "intent": "customer_name",
            "get_by_text": "Emma Davis",
            "placeholder": "Emma Davis"
        }
    },
    {
        "id": "d380bf82-8d5c-415a-b80a-0c0b17b49ed1",
        "document": "emma.davis@email.com",
        "metadata": {
            "unique_name": "customers_emma.davis@email.com_label_customer_email_1680f20b",
            "element_id": "d380bf82-8d5c-415a-b80a-0c0b17b49ed1",
            "external": false,
            "ocr_type": "label",
            "dom_matched": false,
            "placeholder": "emma.davis@email.com",
            "intent": "customer_email",
            "label_text": "emma.davis@email.com",
            "type": "ocr",
            "get_by_text": "emma.davis@email.com",
            "page_name": "customers"
        }
    },
    {
        "id": "3d7db369-1820-41e6-99ac-1b5871f6ed0a",
        "document": "Premium",
        "metadata": {
            "page_name": "customers",
            "type": "ocr",
            "ocr_type": "label",
            "label_text": "Premium",
            "placeholder": "Premium",
            "dom_matched": false,
            "element_id": "3d7db369-1820-41e6-99ac-1b5871f6ed0a",
            "unique_name": "customers_premium_label_account_type_c1ae4279",
            "intent": "account_type",
            "get_by_text": "Premium",
            "external": false
        }
    },
    {
        "id": "7bd8dad6-2eab-413c-b035-fc9d3dc40af7",
        "document": "$89,000",
        "metadata": {
            "element_id": "7bd8dad6-2eab-413c-b035-fc9d3dc40af7",
            "dom_matched": false,
            "intent": "balance",
            "get_by_text": "$89,000",
            "label_text": "$89,000",
            "page_name": "customers",
            "placeholder": "$89,000",
            "unique_name": "customers_$89,000_label_balance_f3422319",
            "ocr_type": "label",
            "external": false,
            "type": "ocr"
        }
    },
    {
        "id": "817de9de-248f-4451-86dd-3c22b855609e",
        "document": "Active",
        "metadata": {
            "label_text": "Active",
            "placeholder": "Active",
            "intent": "status",
            "dom_matched": false,
            "ocr_type": "label",
            "unique_name": "customers_active_label_status_5fc1bbb1",
            "get_by_text": "Active",
            "type": "ocr",
            "element_id": "817de9de-248f-4451-86dd-3c22b855609e",
            "page_name": "customers",
            "external": false
        }
    },
    {
        "id": "a53212d2-6ff3-4100-a779-1e52efba9c80",
        "document": "2022-11-08",
        "metadata": {
            "unique_name": "customers_2022-11-08_label_join_date_bcd7c000",
            "page_name": "customers",
            "placeholder": "2022-11-08",
            "type": "ocr",
            "dom_matched": false,
            "external": false,
            "ocr_type": "label",
            "get_by_text": "2022-11-08",
            "intent": "join_date",
            "label_text": "2022-11-08",
            "element_id": "a53212d2-6ff3-4100-a779-1e52efba9c80"
        }
    },
    {
        "id": "91a1c76a-a72a-4043-a53c-1923168c1674",
        "document": "",
        "metadata": {
            "ocr_type": "button",
            "type": "ocr",
            "label_text": "",
            "intent": "view_action",
            "element_id": "91a1c76a-a72a-4043-a53c-1923168c1674",
            "placeholder": "",
            "unique_name": "customers_button_view_action_cc60ce91",
            "get_by_text": "",
            "dom_matched": false,
            "page_name": "customers",
            "external": false
        }
    },
    {
        "id": "1f7500c4-990c-47c5-9278-0f811b26226e",
        "document": "",
        "metadata": {
            "unique_name": "customers_button_edit_action_d3d0df61",
            "get_by_text": "",
            "external": false,
            "dom_matched": false,
            "element_id": "1f7500c4-990c-47c5-9278-0f811b26226e",
            "page_name": "customers",
            "ocr_type": "button",
            "type": "ocr",
            "intent": "edit_action",
            "label_text": "",
            "placeholder": ""
        }
    },
    {
        "id": "3b1d6cd1-40a5-4933-a5a7-ae9280d9c3cf",
        "document": "Edit with",
        "metadata": {
            "ocr_type": "label",
            "intent": "edit_info",
            "type": "ocr",
            "element_id": "3b1d6cd1-40a5-4933-a5a7-ae9280d9c3cf",
            "external": false,
            "get_by_text": "Edit with",
            "dom_matched": false,
            "unique_name": "customers_edit_with_label_edit_info_0a420ebf",
            "placeholder": "Edit with",
            "page_name": "customers",
            "label_text": "Edit with"
        }
    },
    {
        "id": "43488c62-d6f6-4850-8f23-1a37fccc1657",
        "document": "Lovable",
        "metadata": {
            "label_text": "Lovable",
            "dom_matched": false,
            "get_by_text": "Lovable",
            "external": false,
            "element_id": "43488c62-d6f6-4850-8f23-1a37fccc1657",
            "intent": "edit_tool",
            "page_name": "customers",
            "type": "ocr",
            "ocr_type": "button",
            "unique_name": "customers_lovable_button_edit_tool_efcb8fa0",
            "placeholder": "Lovable"
        }
    }
]


# === FILE: data\stored\20250807_112859_customers_2.json ===
[
    {
        "id": "00015d8a-287f-47d9-bb1a-7f29748d9892",
        "document": "Add New Customer",
        "metadata": {
            "element_id": "00015d8a-287f-47d9-bb1a-7f29748d9892",
            "page_name": "customers",
            "placeholder": "Add New Customer",
            "type": "ocr",
            "label_text": "Add New Customer",
            "get_by_text": "Add New Customer",
            "unique_name": "customers_add_new_customer_label_form_title_2b3b0780",
            "external": false,
            "intent": "form_title",
            "ocr_type": "label",
            "dom_matched": false
        }
    },
    {
        "id": "569c91f8-9a32-4562-8c97-39f7ebc3bccd",
        "document": "Enter the customer details to create a new account.",
        "metadata": {
            "get_by_text": "Enter the customer details to create a new account.",
            "ocr_type": "label",
            "page_name": "customers",
            "placeholder": "Enter the customer details to create a new account.",
            "label_text": "Enter the customer details to create a new account.",
            "external": false,
            "type": "ocr",
            "dom_matched": false,
            "element_id": "569c91f8-9a32-4562-8c97-39f7ebc3bccd",
            "unique_name": "customers_enter_the_customer_details_to_create_a_new_account._label_form_instruction_4e368c65",
            "intent": "form_instruction"
        }
    },
    {
        "id": "33639538-f356-4621-aa2d-1a2816be7beb",
        "document": "Full Name",
        "metadata": {
            "dom_matched": false,
            "page_name": "customers",
            "type": "ocr",
            "unique_name": "customers_full_name_label_full_name_label_7fa7eb35",
            "label_text": "Full Name",
            "external": false,
            "intent": "full_name_label",
            "placeholder": "Full Name",
            "ocr_type": "label",
            "get_by_text": "Full Name",
            "element_id": "33639538-f356-4621-aa2d-1a2816be7beb"
        }
    },
    {
        "id": "d08c4210-8206-4034-9d71-12c1081cd19b",
        "document": "",
        "metadata": {
            "external": false,
            "intent": "full_name_input",
            "placeholder": "",
            "element_id": "d08c4210-8206-4034-9d71-12c1081cd19b",
            "type": "ocr",
            "dom_matched": false,
            "page_name": "customers",
            "ocr_type": "textbox",
            "get_by_text": "",
            "label_text": "",
            "unique_name": "customers_textbox_full_name_input_b5555c13"
        }
    },
    {
        "id": "c018935e-b93b-43cd-be34-85f1536ffc5e",
        "document": "Email",
        "metadata": {
            "dom_matched": false,
            "placeholder": "Email",
            "ocr_type": "label",
            "get_by_text": "Email",
            "type": "ocr",
            "intent": "email_label",
            "unique_name": "customers_email_label_email_label_1e22d7f0",
            "external": false,
            "element_id": "c018935e-b93b-43cd-be34-85f1536ffc5e",
            "page_name": "customers",
            "label_text": "Email"
        }
    },
    {
        "id": "0d54c4ac-3769-452e-8b37-0e0d94210c8f",
        "document": "",
        "metadata": {
            "unique_name": "customers_textbox_email_input_b7f01675",
            "placeholder": "",
            "external": false,
            "dom_matched": false,
            "ocr_type": "textbox",
            "element_id": "0d54c4ac-3769-452e-8b37-0e0d94210c8f",
            "type": "ocr",
            "page_name": "customers",
            "label_text": "",
            "get_by_text": "",
            "intent": "email_input"
        }
    },
    {
        "id": "3d89dd5d-02c4-48f7-bf4d-d3f531f16f56",
        "document": "Phone Number",
        "metadata": {
            "label_text": "Phone Number",
            "external": false,
            "page_name": "customers",
            "placeholder": "Phone Number",
            "type": "ocr",
            "intent": "phone_number_label",
            "element_id": "3d89dd5d-02c4-48f7-bf4d-d3f531f16f56",
            "dom_matched": false,
            "ocr_type": "label",
            "unique_name": "customers_phone_number_label_phone_number_label_03e465fd",
            "get_by_text": "Phone Number"
        }
    },
    {
        "id": "486b218f-714e-4919-a331-54892bc256a2",
        "document": "",
        "metadata": {
            "dom_matched": false,
            "page_name": "customers",
            "label_text": "",
            "unique_name": "customers_textbox_phone_number_input_bb72a72b",
            "get_by_text": "",
            "type": "ocr",
            "intent": "phone_number_input",
            "external": false,
            "placeholder": "",
            "ocr_type": "textbox",
            "element_id": "486b218f-714e-4919-a331-54892bc256a2"
        }
    },
    {
        "id": "d4d79322-d3ba-4a18-9384-c80d2d45ee36",
        "document": "Account Type",
        "metadata": {
            "ocr_type": "label",
            "external": false,
            "unique_name": "customers_account_type_label_account_type_label_a1b76de7",
            "type": "ocr",
            "element_id": "d4d79322-d3ba-4a18-9384-c80d2d45ee36",
            "placeholder": "Account Type",
            "dom_matched": false,
            "intent": "account_type_label",
            "get_by_text": "Account Type",
            "label_text": "Account Type",
            "page_name": "customers"
        }
    },
    {
        "id": "7b481fc3-f77e-4e08-b2bf-26b16ea64afa",
        "document": "Select account type",
        "metadata": {
            "ocr_type": "select",
            "element_id": "7b481fc3-f77e-4e08-b2bf-26b16ea64afa",
            "page_name": "customers",
            "label_text": "Select account type",
            "intent": "account_type_select",
            "type": "ocr",
            "placeholder": "Select account type",
            "dom_matched": false,
            "unique_name": "customers_select_account_type_select_account_type_select_739bf8ef",
            "get_by_text": "Select account type",
            "external": false
        }
    },
    {
        "id": "a62c6ddd-4aa1-476d-a551-33cd610df667",
        "document": "Address",
        "metadata": {
            "external": false,
            "placeholder": "Address",
            "unique_name": "customers_address_label_address_label_bfa99020",
            "intent": "address_label",
            "type": "ocr",
            "element_id": "a62c6ddd-4aa1-476d-a551-33cd610df667",
            "page_name": "customers",
            "get_by_text": "Address",
            "label_text": "Address",
            "dom_matched": false,
            "ocr_type": "label"
        }
    },
    {
        "id": "469c9e87-3429-4950-b45f-ae171b5c8f53",
        "document": "",
        "metadata": {
            "type": "ocr",
            "element_id": "469c9e87-3429-4950-b45f-ae171b5c8f53",
            "placeholder": "",
            "intent": "address_input",
            "dom_matched": false,
            "get_by_text": "",
            "label_text": "",
            "external": false,
            "page_name": "customers",
            "unique_name": "customers_textbox_address_input_0da1bba0",
            "ocr_type": "textbox"
        }
    },
    {
        "id": "eebc5cb1-4c08-4413-b81d-a7b8a805466d",
        "document": "Occupation",
        "metadata": {
            "type": "ocr",
            "unique_name": "customers_occupation_label_occupation_label_78041ebe",
            "page_name": "customers",
            "label_text": "Occupation",
            "element_id": "eebc5cb1-4c08-4413-b81d-a7b8a805466d",
            "dom_matched": false,
            "intent": "occupation_label",
            "ocr_type": "label",
            "placeholder": "Occupation",
            "external": false,
            "get_by_text": "Occupation"
        }
    },
    {
        "id": "7a137420-b5d9-4855-b662-a95b115e9204",
        "document": "",
        "metadata": {
            "element_id": "7a137420-b5d9-4855-b662-a95b115e9204",
            "ocr_type": "textbox",
            "intent": "occupation_input",
            "page_name": "customers",
            "external": false,
            "type": "ocr",
            "label_text": "",
            "unique_name": "customers_textbox_occupation_input_7c88216e",
            "get_by_text": "",
            "placeholder": "",
            "dom_matched": false
        }
    },
    {
        "id": "9be4a552-0333-4fdd-8049-a42dde9c6ff1",
        "document": "Annual Income",
        "metadata": {
            "intent": "annual_income_label",
            "placeholder": "Annual Income",
            "get_by_text": "Annual Income",
            "element_id": "9be4a552-0333-4fdd-8049-a42dde9c6ff1",
            "page_name": "customers",
            "type": "ocr",
            "ocr_type": "label",
            "external": false,
            "label_text": "Annual Income",
            "unique_name": "customers_annual_income_label_annual_income_label_41327b0b",
            "dom_matched": false
        }
    },
    {
        "id": "3e390a3e-ce76-4d63-9e73-0740abdb4b87",
        "document": "",
        "metadata": {
            "unique_name": "customers_textbox_annual_income_input_7b960691",
            "intent": "annual_income_input",
            "type": "ocr",
            "external": false,
            "dom_matched": false,
            "get_by_text": "",
            "element_id": "3e390a3e-ce76-4d63-9e73-0740abdb4b87",
            "label_text": "",
            "placeholder": "",
            "page_name": "customers",
            "ocr_type": "textbox"
        }
    },
    {
        "id": "4f5b78a9-3586-44e6-b598-460dd44d9da5",
        "document": "Initial Deposit",
        "metadata": {
            "intent": "initial_deposit_label",
            "placeholder": "Initial Deposit",
            "type": "ocr",
            "unique_name": "customers_initial_deposit_label_initial_deposit_label_a98dd99a",
            "label_text": "Initial Deposit",
            "element_id": "4f5b78a9-3586-44e6-b598-460dd44d9da5",
            "dom_matched": false,
            "ocr_type": "label",
            "get_by_text": "Initial Deposit",
            "page_name": "customers",
            "external": false
        }
    },
    {
        "id": "108e3be9-517f-4c06-9199-25d4da6dfa13",
        "document": "",
        "metadata": {
            "unique_name": "customers_textbox_initial_deposit_input_842f44e3",
            "label_text": "",
            "intent": "initial_deposit_input",
            "ocr_type": "textbox",
            "placeholder": "",
            "dom_matched": false,
            "element_id": "108e3be9-517f-4c06-9199-25d4da6dfa13",
            "type": "ocr",
            "page_name": "customers",
            "external": false,
            "get_by_text": ""
        }
    },
    {
        "id": "15677d30-13f4-4a84-ad48-efa81a819a7e",
        "document": "Cancel",
        "metadata": {
            "page_name": "customers",
            "external": false,
            "element_id": "15677d30-13f4-4a84-ad48-efa81a819a7e",
            "type": "ocr",
            "label_text": "Cancel",
            "intent": "cancel",
            "ocr_type": "button",
            "get_by_text": "Cancel",
            "unique_name": "customers_cancel_button_cancel_71a3913d",
            "dom_matched": false,
            "placeholder": "Cancel"
        }
    },
    {
        "id": "56635ce8-128b-4269-af74-c7c96884bb70",
        "document": "Add Customer",
        "metadata": {
            "page_name": "customers",
            "external": false,
            "type": "ocr",
            "unique_name": "customers_add_customer_button_submit_bce56d38",
            "dom_matched": false,
            "element_id": "56635ce8-128b-4269-af74-c7c96884bb70",
            "get_by_text": "Add Customer",
            "placeholder": "Add Customer",
            "label_text": "Add Customer",
            "intent": "submit",
            "ocr_type": "button"
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
            print(
                f"[SmartAI][select_option fallback] Native select_option failed: {e}")
            try:
                self._page.get_by_role("combobox").click()
                self._page.get_by_role("option", name=value).click()
                print(
                    f"[SmartAI][select_option fallback] Selected '{value}' via combobox+option fallback")
            except Exception as e2:
                print(
                    f"[SmartAI][select_option fallback] Fallback also failed: {e2}")
                raise


class SmartAISelfHealing:
    def __init__(self, metadata):
        self.metadata = metadata
        self.model = SentenceTransformer("all-MiniLM-L6-v2")
        # 1️⃣ Cache embeddings for all metadata elements for fast ML matching
        self.embeddings = [
            self.model.encode(self._element_to_string(
                e), convert_to_tensor=True, show_progress_bar=False)
            for e in self.metadata
        ]
        # 10️⃣ Track failed locators (element unique_name → fail count)
        self.locator_fail_count = {}

    # 5️⃣ Single definition; all prioritization inside
    async def _try_all_locators(self, element, page):
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
                if locator and await locator.count() > 0:
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

    async def find_element(self, unique_name, page):
        # Main entry for SmartAI: tries direct lookup, then ML self-healing, then heuristics.
        element = self._find_by_unique_name(unique_name)
        if element:
            locator = await self._try_all_locators(element, page)
            if locator:
                print(
                    f"[SmartAI] Element '{unique_name}' found using primary metadata.")
                return SmartAIWrappedLocator(locator, page)  # <--- PATCHED

            print(
                f"[SmartAI] Primary methods failed for '{unique_name}', trying ML self-healing...")

        # ML-based fallback
        element_ml, ml_score = self._ml_self_heal(unique_name)
        if element_ml:
            locator_ml = await self._try_all_locators(element_ml, page)
            if locator_ml:
                print(
                    f"[SmartAI] Healed element via ML ({ml_score:.2f}): '{element_ml.get('unique_name')}'")
                return SmartAIWrappedLocator(locator_ml, page)  # <--- PATCHED

        # 9️⃣ Intent-aware fallback: try other elements with same intent
        target_intent = element_ml.get("intent") if element_ml else None
        if target_intent:
            for e in self.metadata:
                if e.get("intent") == target_intent and e.get("unique_name") != unique_name:
                    locator = await self._try_all_locators(e, page)
                    if locator:
                        print(
                            f"[SmartAI] Healed element by intent ('{target_intent}'): '{e.get('unique_name')}'")
                        # <--- PATCHED
                        return SmartAIWrappedLocator(locator, page)

        # 11️⃣ Visual/position fallback (commented for extension)
        # print("[SmartAI] Trying fallback by position (not implemented)...")

        raise SmartAILocatorError(
            f"Element '{unique_name}' not found and cannot self-heal.")

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
        query_embedding = self.model.encode(
            unique_name, convert_to_tensor=True, show_progress_bar=False)
        scores = [util.cos_sim(query_embedding, emb).item()
                  for emb in self.embeddings]
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
            " ".join(element.get("class_list", [])) if element.get(
                "class_list") else "",
            # 4️⃣ Fast join for data_attrs
            " ".join(f"{k}:{v}" for k, v in (
                element.get("data_attrs", {}) or {}).items()),
            element.get("sample_value", ""),
        ]
        return " ".join([str(f) for f in fields if f])


# ====== PAGE PATCH ======
def patch_page_with_smartai(page, metadata):
    ai_healer = SmartAISelfHealing(metadata)

    async def smartAI(unique_name):
        return await ai_healer.find_element(unique_name, page)
    page.smartAI = smartAI
    return page



# === FILE: generated_runs\src\lib\__init__.py ===



# === FILE: generated_runs\src\metadata\before_enrichment.json ===
[
  {
    "get_by_text": "",
    "page_name": "dashboard",
    "external": false,
    "unique_name": "dashboard_button_navigation_34c032c8",
    "ocr_type": "button",
    "dom_matched": false,
    "placeholder": "",
    "element_id": "c8b96af7-c667-4cf7-ab10-f00534e1358f",
    "intent": "navigation",
    "label_text": "",
    "type": "ocr"
  },
  {
    "ocr_type": "textbox",
    "type": "ocr",
    "element_id": "96804809-411a-4a65-824e-44aecb8eed2d",
    "placeholder": "Search customers, loans, transactions...",
    "external": false,
    "dom_matched": false,
    "page_name": "dashboard",
    "unique_name": "dashboard_search_customers,_loans,_transactions..._textbox_search_3310a968",
    "label_text": "Search customers, loans, transactions...",
    "get_by_text": "Search customers, loans, transactions...",
    "intent": "search"
  },
  {
    "external": false,
    "dom_matched": false,
    "element_id": "c01e1667-86a9-4c43-834c-58d9403b2f54",
    "label_text": "Dashboard",
    "get_by_text": "Dashboard",
    "unique_name": "dashboard_dashboard_button_navigation_83914516",
    "type": "ocr",
    "ocr_type": "button",
    "placeholder": "Dashboard",
    "page_name": "dashboard",
    "intent": "navigation"
  },
  {
    "page_name": "dashboard",
    "get_by_text": "Customers",
    "element_id": "3bce5461-20c5-476c-a822-3e58412043cf",
    "dom_matched": false,
    "external": false,
    "type": "ocr",
    "intent": "navigation",
    "unique_name": "dashboard_customers_button_navigation_bb4303b6",
    "ocr_type": "button",
    "label_text": "Customers",
    "placeholder": "Customers"
  },
  {
    "element_id": "5011d652-56a6-4e0e-b013-a1d6a1f1dc7c",
    "placeholder": "Loans",
    "ocr_type": "button",
    "dom_matched": false,
    "unique_name": "dashboard_loans_button_navigation_42436e2a",
    "page_name": "dashboard",
    "get_by_text": "Loans",
    "label_text": "Loans",
    "external": false,
    "type": "ocr",
    "intent": "navigation"
  },
  {
    "page_name": "dashboard",
    "intent": "navigation",
    "external": false,
    "label_text": "Transactions",
    "unique_name": "dashboard_transactions_button_navigation_f0479a72",
    "ocr_type": "button",
    "placeholder": "Transactions",
    "type": "ocr",
    "get_by_text": "Transactions",
    "element_id": "e0cd985e-43a7-4faa-8f39-cc0c10bef035",
    "dom_matched": false
  },
  {
    "unique_name": "dashboard_tasks_button_navigation_cde2a4d6",
    "external": false,
    "label_text": "Tasks",
    "intent": "navigation",
    "element_id": "958eaaee-2088-4840-a811-34bbe4c7f4ee",
    "placeholder": "Tasks",
    "type": "ocr",
    "ocr_type": "button",
    "page_name": "dashboard",
    "dom_matched": false,
    "get_by_text": "Tasks"
  },
  {
    "element_id": "3fe79ef0-fcb3-4049-bb6c-564ba85d6d15",
    "placeholder": "Reports",
    "unique_name": "dashboard_reports_button_navigation_578fb659",
    "dom_matched": false,
    "intent": "navigation",
    "label_text": "Reports",
    "get_by_text": "Reports",
    "external": false,
    "page_name": "dashboard",
    "ocr_type": "button",
    "type": "ocr"
  },
  {
    "element_id": "9a53c302-4c9f-454e-bb36-50f9fd1785a4",
    "external": false,
    "placeholder": "Analytics",
    "unique_name": "dashboard_analytics_button_navigation_49884ab5",
    "page_name": "dashboard",
    "ocr_type": "button",
    "label_text": "Analytics",
    "intent": "navigation",
    "type": "ocr",
    "get_by_text": "Analytics",
    "dom_matched": false
  },
  {
    "label_text": "Settings",
    "external": false,
    "page_name": "dashboard",
    "unique_name": "dashboard_settings_button_navigation_7a36fd5d",
    "ocr_type": "button",
    "element_id": "bd6766fc-75f1-4154-b4ed-3fa7142c0b70",
    "intent": "navigation",
    "placeholder": "Settings",
    "type": "ocr",
    "get_by_text": "Settings",
    "dom_matched": false
  },
  {
    "element_id": "2d8b143f-aa2b-4e82-8ffc-cf27174d281e",
    "ocr_type": "label",
    "external": false,
    "placeholder": "Dashboard",
    "intent": "page_title",
    "unique_name": "dashboard_dashboard_label_page_title_a353b4f0",
    "dom_matched": false,
    "get_by_text": "Dashboard",
    "page_name": "dashboard",
    "type": "ocr",
    "label_text": "Dashboard"
  },
  {
    "external": false,
    "page_name": "dashboard",
    "dom_matched": false,
    "intent": "greeting",
    "ocr_type": "label",
    "label_text": "Welcome back! Here's your banking overview.",
    "placeholder": "Welcome back! Here's your banking overview.",
    "element_id": "589cf01e-f3b2-41a4-b45e-a3e8b5877c56",
    "type": "ocr",
    "get_by_text": "Welcome back! Here's your banking overview.",
    "unique_name": "dashboard_welcome_back!_heres_your_banking_overview._label_greeting_bd321dde"
  },
  {
    "label_text": "Total Customers",
    "intent": "metric_title",
    "page_name": "dashboard",
    "dom_matched": false,
    "type": "ocr",
    "element_id": "ccf017b5-69b6-49c5-84e9-afbcaf35a632",
    "get_by_text": "Total Customers",
    "unique_name": "dashboard_total_customers_label_metric_title_9728f1cf",
    "external": false,
    "ocr_type": "label",
    "placeholder": "Total Customers"
  },
  {
    "label_text": "2,847",
    "get_by_text": "2,847",
    "placeholder": "2,847",
    "unique_name": "dashboard_2,847_label_metric_value_fdec317c",
    "intent": "metric_value",
    "type": "ocr",
    "dom_matched": false,
    "external": false,
    "element_id": "c659e1be-61d0-4ad9-a1ef-570349d6dde5",
    "page_name": "dashboard",
    "ocr_type": "label"
  },
  {
    "external": false,
    "placeholder": "Active Loans",
    "type": "ocr",
    "label_text": "Active Loans",
    "unique_name": "dashboard_active_loans_label_metric_title_7b8dadc2",
    "get_by_text": "Active Loans",
    "ocr_type": "label",
    "dom_matched": false,
    "intent": "metric_title",
    "page_name": "dashboard",
    "element_id": "3d2b69f8-4ba3-44fa-a682-41fa61403283"
  },
  {
    "unique_name": "dashboard_$45.2m_label_metric_value_4a2ef93a",
    "external": false,
    "page_name": "dashboard",
    "intent": "metric_value",
    "dom_matched": false,
    "get_by_text": "$45.2M",
    "label_text": "$45.2M",
    "placeholder": "$45.2M",
    "type": "ocr",
    "ocr_type": "label",
    "element_id": "5149fba3-5d4c-456d-8bf1-80fe6d14d028"
  },
  {
    "dom_matched": false,
    "get_by_text": "Monthly Transactions",
    "page_name": "dashboard",
    "unique_name": "dashboard_monthly_transactions_label_metric_title_12ed8182",
    "ocr_type": "label",
    "label_text": "Monthly Transactions",
    "intent": "metric_title",
    "type": "ocr",
    "external": false,
    "element_id": "e7d2dc34-a120-4378-9daf-c79c97eb33b3",
    "placeholder": "Monthly Transactions"
  },
  {
    "element_id": "c66a73b8-d209-4c69-af99-b528514ab320",
    "type": "ocr",
    "label_text": "18,394",
    "external": false,
    "get_by_text": "18,394",
    "dom_matched": false,
    "placeholder": "18,394",
    "intent": "metric_value",
    "ocr_type": "label",
    "unique_name": "dashboard_18,394_label_metric_value_b6b442dd",
    "page_name": "dashboard"
  },
  {
    "element_id": "8621f44c-3a17-4bc0-9074-2ae49c0649ed",
    "external": false,
    "page_name": "dashboard",
    "intent": "metric_title",
    "dom_matched": false,
    "ocr_type": "label",
    "unique_name": "dashboard_revenue_growth_label_metric_title_d1a487c9",
    "placeholder": "Revenue Growth",
    "get_by_text": "Revenue Growth",
    "type": "ocr",
    "label_text": "Revenue Growth"
  },
  {
    "label_text": "4%",
    "type": "ocr",
    "dom_matched": false,
    "page_name": "dashboard",
    "element_id": "2317fcd1-0194-45aa-b353-1a31c81e4a56",
    "ocr_type": "label",
    "intent": "metric_value",
    "placeholder": "4%",
    "unique_name": "dashboard_4%_label_metric_value_316201d4",
    "external": false,
    "get_by_text": "4%"
  },
  {
    "ocr_type": "button",
    "placeholder": "Export Report",
    "unique_name": "dashboard_export_report_button_export_ed26f6d4",
    "page_name": "dashboard",
    "label_text": "Export Report",
    "element_id": "57192da2-3cc2-4855-b250-3cf3d80f0a62",
    "external": false,
    "get_by_text": "Export Report",
    "dom_matched": false,
    "intent": "export",
    "type": "ocr"
  },
  {
    "get_by_text": "Loan Portfolio Trend",
    "intent": "section_title",
    "page_name": "dashboard",
    "element_id": "7068d846-c40e-4aa1-9ecf-241bdcbd6a76",
    "unique_name": "dashboard_loan_portfolio_trend_label_section_title_32cf7d0c",
    "type": "ocr",
    "external": false,
    "ocr_type": "label",
    "dom_matched": false,
    "label_text": "Loan Portfolio Trend",
    "placeholder": "Loan Portfolio Trend"
  },
  {
    "placeholder": "Monthly loan disbursements over the last 6 months",
    "element_id": "1d298799-b832-40df-84c0-7e40b4e10e9f",
    "external": false,
    "unique_name": "dashboard_monthly_loan_disbursements_over_the_last_6_months_label_section_info_790102ea",
    "label_text": "Monthly loan disbursements over the last 6 months",
    "page_name": "dashboard",
    "ocr_type": "label",
    "dom_matched": false,
    "get_by_text": "Monthly loan disbursements over the last 6 months",
    "type": "ocr",
    "intent": "section_info"
  },
  {
    "type": "ocr",
    "element_id": "bb6942fc-68bb-466d-9d24-aff2ce7728ec",
    "label_text": "Customer Distribution",
    "ocr_type": "label",
    "dom_matched": false,
    "get_by_text": "Customer Distribution",
    "intent": "section_title",
    "unique_name": "dashboard_customer_distribution_label_section_title_4bc10c83",
    "external": false,
    "placeholder": "Customer Distribution",
    "page_name": "dashboard"
  },
  {
    "get_by_text": "Customer segments by account type",
    "type": "ocr",
    "placeholder": "Customer segments by account type",
    "page_name": "dashboard",
    "unique_name": "dashboard_customer_segments_by_account_type_label_section_info_e21a781f",
    "label_text": "Customer segments by account type",
    "external": false,
    "element_id": "9d778496-97a6-452d-858c-ccedd1f9d85b",
    "ocr_type": "label",
    "intent": "section_info",
    "dom_matched": false
  },
  {
    "get_by_text": "Premium 35%",
    "unique_name": "dashboard_premium_35%_label_chart_info_e6423d22",
    "intent": "chart_info",
    "ocr_type": "label",
    "page_name": "dashboard",
    "type": "ocr",
    "placeholder": "Premium 35%",
    "label_text": "Premium 35%",
    "element_id": "a9c9e92f-aa27-4aea-b103-12bd04f427f3",
    "dom_matched": false,
    "external": false
  },
  {
    "unique_name": "dashboard_standard_45%_label_chart_info_d70c74e7",
    "element_id": "2ab97d9e-ded8-4325-8bf9-cfb1b0eb3854",
    "external": false,
    "ocr_type": "label",
    "page_name": "dashboard",
    "dom_matched": false,
    "intent": "chart_info",
    "type": "ocr",
    "placeholder": "Standard 45%",
    "get_by_text": "Standard 45%",
    "label_text": "Standard 45%"
  },
  {
    "type": "ocr",
    "get_by_text": "Basic 20%",
    "element_id": "fe24f6db-3635-45e0-a23f-8921e6bcdb73",
    "ocr_type": "label",
    "placeholder": "Basic 20%",
    "unique_name": "dashboard_basic_20%_label_chart_info_7bda856f",
    "external": false,
    "label_text": "Basic 20%",
    "intent": "chart_info",
    "dom_matched": false,
    "page_name": "dashboard"
  },
  {
    "external": false,
    "intent": "section_title",
    "get_by_text": "Recent Activities",
    "page_name": "dashboard",
    "dom_matched": false,
    "element_id": "70f8cd90-eab3-428a-a474-b6a37688197d",
    "unique_name": "dashboard_recent_activities_label_section_title_c5dd6139",
    "label_text": "Recent Activities",
    "ocr_type": "label",
    "type": "ocr",
    "placeholder": "Recent Activities"
  },
  {
    "label_text": "Latest customer interactions and transactions",
    "type": "ocr",
    "external": false,
    "unique_name": "dashboard_latest_customer_interactions_and_transactions_label_section_info_5c741538",
    "intent": "section_info",
    "ocr_type": "label",
    "page_name": "dashboard",
    "element_id": "48893a94-fbcc-44ab-a8b4-86c0c13f3e0d",
    "dom_matched": false,
    "get_by_text": "Latest customer interactions and transactions",
    "placeholder": "Latest customer interactions and transactions"
  },
  {
    "type": "ocr",
    "ocr_type": "label",
    "get_by_text": "Sarah Johnson",
    "placeholder": "Sarah Johnson",
    "external": false,
    "label_text": "Sarah Johnson",
    "unique_name": "dashboard_sarah_johnson_label_activity_user_309b9d18",
    "intent": "activity_user",
    "page_name": "dashboard",
    "dom_matched": false,
    "element_id": "8a7c9a5c-4c74-4a40-8c78-252f4f867ef5"
  },
  {
    "get_by_text": "Loan Application Approved",
    "label_text": "Loan Application Approved",
    "dom_matched": false,
    "type": "ocr",
    "intent": "activity_info",
    "external": false,
    "page_name": "dashboard",
    "ocr_type": "label",
    "unique_name": "dashboard_loan_application_approved_label_activity_info_969d6763",
    "element_id": "6ca1c4d1-b5ab-4640-8317-3f9cfaf56437",
    "placeholder": "Loan Application Approved"
  },
  {
    "external": false,
    "ocr_type": "label",
    "type": "ocr",
    "get_by_text": "Michael Chen",
    "intent": "activity_user",
    "placeholder": "Michael Chen",
    "label_text": "Michael Chen",
    "dom_matched": false,
    "unique_name": "dashboard_michael_chen_label_activity_user_f041a3aa",
    "page_name": "dashboard",
    "element_id": "0ffa2134-5c60-475e-bbe5-2cf962c6458c"
  },
  {
    "element_id": "c146bcdb-14d3-41e8-a42c-11a22809eb1f",
    "placeholder": "$250,000",
    "dom_matched": false,
    "page_name": "dashboard",
    "external": false,
    "unique_name": "dashboard_$250,000_label_transaction_amount_14fd1f5f",
    "type": "ocr",
    "label_text": "$250,000",
    "ocr_type": "label",
    "get_by_text": "$250,000",
    "intent": "transaction_amount"
  },
  {
    "label_text": "2 hours ago",
    "ocr_type": "label",
    "page_name": "dashboard",
    "type": "ocr",
    "intent": "transaction_time",
    "get_by_text": "2 hours ago",
    "dom_matched": false,
    "placeholder": "2 hours ago",
    "external": false,
    "unique_name": "dashboard_2_hours_ago_label_transaction_time_a74efe28",
    "element_id": "50bb6bbd-9c7f-4789-bd90-01d516da1f73"
  },
  {
    "intent": "edit_option",
    "element_id": "04ea7dde-967c-4d48-bc75-8969ad8d6bb6",
    "unique_name": "dashboard_edit_with_label_edit_option_88c64fc9",
    "dom_matched": false,
    "page_name": "dashboard",
    "get_by_text": "Edit with",
    "type": "ocr",
    "external": false,
    "label_text": "Edit with",
    "placeholder": "Edit with",
    "ocr_type": "label"
  },
  {
    "dom_matched": false,
    "ocr_type": "button",
    "type": "ocr",
    "label_text": "Lovable",
    "unique_name": "dashboard_lovable_button_edit_tool_2de51406",
    "page_name": "dashboard",
    "placeholder": "Lovable",
    "intent": "edit_tool",
    "external": false,
    "element_id": "7b6de3c9-af25-42d1-b55c-721722bd7138",
    "get_by_text": "Lovable"
  },
  {
    "page_name": "customers",
    "element_id": "7c8603cf-65e2-42e4-be5a-ab7dfb10587c",
    "ocr_type": "textbox",
    "type": "ocr",
    "label_text": "Search customers, loans, transactions...",
    "placeholder": "Search customers, loans, transactions...",
    "dom_matched": false,
    "external": false,
    "unique_name": "customers_search_customers,_loans,_transactions..._textbox_search_be73039f",
    "intent": "search",
    "get_by_text": "Search customers, loans, transactions..."
  },
  {
    "label_text": "Dashboard",
    "intent": "navigation",
    "get_by_text": "Dashboard",
    "external": false,
    "type": "ocr",
    "page_name": "customers",
    "placeholder": "Dashboard",
    "ocr_type": "button",
    "unique_name": "customers_dashboard_button_navigation_fb22376c",
    "dom_matched": false,
    "element_id": "a950f551-13a8-4bde-aaa2-c4b96125f740"
  },
  {
    "external": false,
    "element_id": "b3c09d9d-297d-43fb-866f-d6d6fdb6be27",
    "ocr_type": "button",
    "dom_matched": false,
    "unique_name": "customers_customers_button_navigation_62cd2bf8",
    "get_by_text": "Customers",
    "placeholder": "Customers",
    "intent": "navigation",
    "page_name": "customers",
    "type": "ocr",
    "label_text": "Customers"
  },
  {
    "placeholder": "Loans",
    "get_by_text": "Loans",
    "unique_name": "customers_loans_button_navigation_f083cd47",
    "external": false,
    "element_id": "510084f4-bc9a-4cd5-8221-bcae4ea15eba",
    "intent": "navigation",
    "label_text": "Loans",
    "page_name": "customers",
    "ocr_type": "button",
    "dom_matched": false,
    "type": "ocr"
  },
  {
    "get_by_text": "Transactions",
    "element_id": "18a781ff-8f2a-4f8b-b201-0b62956c3652",
    "external": false,
    "unique_name": "customers_transactions_button_navigation_bb833203",
    "placeholder": "Transactions",
    "ocr_type": "button",
    "label_text": "Transactions",
    "dom_matched": false,
    "type": "ocr",
    "intent": "navigation",
    "page_name": "customers"
  },
  {
    "dom_matched": false,
    "ocr_type": "button",
    "element_id": "e7856553-2167-4099-8d07-90018bb009bc",
    "get_by_text": "Tasks",
    "placeholder": "Tasks",
    "label_text": "Tasks",
    "type": "ocr",
    "unique_name": "customers_tasks_button_navigation_63e52ff9",
    "external": false,
    "page_name": "customers",
    "intent": "navigation"
  },
  {
    "label_text": "Reports",
    "dom_matched": false,
    "type": "ocr",
    "intent": "navigation",
    "get_by_text": "Reports",
    "element_id": "b0cbf374-0acb-4b04-9625-19da9eb7c8b6",
    "ocr_type": "button",
    "unique_name": "customers_reports_button_navigation_1dc35b9f",
    "placeholder": "Reports",
    "page_name": "customers",
    "external": false
  },
  {
    "external": false,
    "element_id": "e785909d-e9b1-428b-b8c7-cd2abf051547",
    "label_text": "Analytics",
    "type": "ocr",
    "ocr_type": "button",
    "get_by_text": "Analytics",
    "dom_matched": false,
    "unique_name": "customers_analytics_button_navigation_8227d101",
    "placeholder": "Analytics",
    "intent": "navigation",
    "page_name": "customers"
  },
  {
    "dom_matched": false,
    "placeholder": "Settings",
    "unique_name": "customers_settings_button_navigation_9de99b8a",
    "ocr_type": "button",
    "intent": "navigation",
    "type": "ocr",
    "page_name": "customers",
    "label_text": "Settings",
    "get_by_text": "Settings",
    "element_id": "e8c7501c-a8a1-47e3-acc8-b3ed5513a410",
    "external": false
  },
  {
    "placeholder": "John Doe",
    "intent": "user_info",
    "element_id": "397ca042-75d0-4c05-ae59-dd12b3420594",
    "ocr_type": "label",
    "get_by_text": "John Doe",
    "unique_name": "customers_john_doe_label_user_info_64be4d99",
    "page_name": "customers",
    "label_text": "John Doe",
    "type": "ocr",
    "dom_matched": false,
    "external": false
  },
  {
    "placeholder": "Customers",
    "page_name": "customers",
    "get_by_text": "Customers",
    "unique_name": "customers_customers_label_section_title_2ec8510a",
    "element_id": "54403b9a-6ab1-4eed-8a3c-2b94060a9e6f",
    "ocr_type": "label",
    "type": "ocr",
    "label_text": "Customers",
    "external": false,
    "dom_matched": false,
    "intent": "section_title"
  },
  {
    "dom_matched": false,
    "intent": "section_info",
    "external": false,
    "get_by_text": "Manage your customer relationships and accounts",
    "placeholder": "Manage your customer relationships and accounts",
    "ocr_type": "label",
    "label_text": "Manage your customer relationships and accounts",
    "element_id": "fddfa206-8a58-42d8-8422-0dd00056b662",
    "page_name": "customers",
    "unique_name": "customers_manage_your_customer_relationships_and_accounts_label_section_info_f20c0595",
    "type": "ocr"
  },
  {
    "type": "ocr",
    "label_text": "Search customers...",
    "intent": "search",
    "external": false,
    "ocr_type": "textbox",
    "get_by_text": "Search customers...",
    "page_name": "customers",
    "placeholder": "Search customers...",
    "unique_name": "customers_search_customers..._textbox_search_85d3ce1f",
    "element_id": "84a21b00-b3cc-44ab-af92-cb32a03b80a5",
    "dom_matched": false
  },
  {
    "intent": "export",
    "label_text": "Export",
    "type": "ocr",
    "page_name": "customers",
    "element_id": "754e885e-ab7c-41d7-894a-7d6c2a7232dd",
    "unique_name": "customers_export_button_export_ec306f18",
    "get_by_text": "Export",
    "placeholder": "Export",
    "dom_matched": false,
    "ocr_type": "button",
    "external": false
  },
  {
    "external": false,
    "page_name": "customers",
    "element_id": "bb353c7f-0aed-40b1-ad07-8e9411162863",
    "unique_name": "customers_+_new_customer_button_add_customer_e84a62b3",
    "get_by_text": "+ New Customer",
    "type": "ocr",
    "placeholder": "+ New Customer",
    "label_text": "+ New Customer",
    "ocr_type": "button",
    "dom_matched": false,
    "intent": "add_customer"
  },
  {
    "element_id": "9d406a26-39b0-4e72-b9ba-44dcd3719729",
    "dom_matched": false,
    "page_name": "customers",
    "external": false,
    "get_by_text": "Filters",
    "label_text": "Filters",
    "ocr_type": "button",
    "type": "ocr",
    "unique_name": "customers_filters_button_filter_4c0a3d63",
    "placeholder": "Filters",
    "intent": "filter"
  },
  {
    "page_name": "customers",
    "unique_name": "customers_customer_list_label_section_title_ad47eb6a",
    "dom_matched": false,
    "external": false,
    "type": "ocr",
    "get_by_text": "Customer List",
    "intent": "section_title",
    "placeholder": "Customer List",
    "label_text": "Customer List",
    "ocr_type": "label",
    "element_id": "ae4fdb25-97b8-42a3-816e-70cd76825558"
  },
  {
    "intent": "section_info",
    "external": false,
    "type": "ocr",
    "get_by_text": "3 customers found",
    "element_id": "4f0d441d-eecf-473a-9759-37d9a9b724e3",
    "page_name": "customers",
    "label_text": "3 customers found",
    "dom_matched": false,
    "unique_name": "customers_3_customers_found_label_section_info_f58e240e",
    "placeholder": "3 customers found",
    "ocr_type": "label"
  },
  {
    "label_text": "Customer",
    "type": "ocr",
    "get_by_text": "Customer",
    "placeholder": "Customer",
    "element_id": "41bdc51c-bd13-43ac-b2f6-f4c14fc096b7",
    "ocr_type": "label",
    "unique_name": "customers_customer_label_column_header_cd74c3eb",
    "external": false,
    "dom_matched": false,
    "page_name": "customers",
    "intent": "column_header"
  },
  {
    "ocr_type": "label",
    "intent": "column_header",
    "dom_matched": false,
    "placeholder": "Account Type",
    "element_id": "6f9c2f5e-d59d-4c9a-9e12-736f73e4fe23",
    "unique_name": "customers_account_type_label_column_header_a712d19c",
    "get_by_text": "Account Type",
    "type": "ocr",
    "external": false,
    "label_text": "Account Type",
    "page_name": "customers"
  },
  {
    "page_name": "customers",
    "placeholder": "Balance",
    "element_id": "5f45165f-06fa-4ea2-aff0-7c15c8319963",
    "unique_name": "customers_balance_label_column_header_d6648fd2",
    "get_by_text": "Balance",
    "ocr_type": "label",
    "type": "ocr",
    "label_text": "Balance",
    "dom_matched": false,
    "external": false,
    "intent": "column_header"
  },
  {
    "ocr_type": "label",
    "dom_matched": false,
    "intent": "column_header",
    "placeholder": "Status",
    "type": "ocr",
    "get_by_text": "Status",
    "page_name": "customers",
    "label_text": "Status",
    "unique_name": "customers_status_label_column_header_57a06b20",
    "external": false,
    "element_id": "457fdd49-d324-4c7b-9368-689ba17e8d32"
  },
  {
    "type": "ocr",
    "element_id": "85b72c0b-7dc8-4139-82f6-01de76a16cef",
    "placeholder": "Join Date",
    "intent": "column_header",
    "get_by_text": "Join Date",
    "page_name": "customers",
    "external": false,
    "ocr_type": "label",
    "dom_matched": false,
    "label_text": "Join Date",
    "unique_name": "customers_join_date_label_column_header_cb167d9a"
  },
  {
    "ocr_type": "label",
    "get_by_text": "Actions",
    "page_name": "customers",
    "placeholder": "Actions",
    "external": false,
    "unique_name": "customers_actions_label_column_header_177ddb69",
    "label_text": "Actions",
    "type": "ocr",
    "intent": "column_header",
    "element_id": "0cd3cbe2-e666-45cb-86f7-7b988f5ba329",
    "dom_matched": false
  },
  {
    "ocr_type": "label",
    "type": "ocr",
    "placeholder": "Sarah Johnson",
    "intent": "customer_name",
    "unique_name": "customers_sarah_johnson_label_customer_name_91134cc9",
    "dom_matched": false,
    "page_name": "customers",
    "element_id": "26629015-b51a-43bd-80cb-f1df561bf09f",
    "external": false,
    "label_text": "Sarah Johnson",
    "get_by_text": "Sarah Johnson"
  },
  {
    "get_by_text": "sarah.johnson@email.com",
    "ocr_type": "label",
    "dom_matched": false,
    "intent": "customer_email",
    "label_text": "sarah.johnson@email.com",
    "external": false,
    "unique_name": "customers_sarah.johnson@email.com_label_customer_email_ea79968a",
    "placeholder": "sarah.johnson@email.com",
    "page_name": "customers",
    "type": "ocr",
    "element_id": "fba877fa-d301-4d55-8733-4d94c8765702"
  },
  {
    "type": "ocr",
    "external": false,
    "page_name": "customers",
    "unique_name": "customers_premium_label_account_type_c1ae4279",
    "get_by_text": "Premium",
    "label_text": "Premium",
    "element_id": "3d7db369-1820-41e6-99ac-1b5871f6ed0a",
    "ocr_type": "label",
    "intent": "account_type",
    "placeholder": "Premium",
    "dom_matched": false
  },
  {
    "placeholder": "$1,45,000",
    "element_id": "ac3036e9-4360-4e93-9f29-35910c410ccb",
    "external": false,
    "get_by_text": "$1,45,000",
    "ocr_type": "label",
    "dom_matched": false,
    "label_text": "$1,45,000",
    "intent": "balance",
    "unique_name": "customers_$1,45,000_label_balance_dc74e6a8",
    "page_name": "customers",
    "type": "ocr"
  },
  {
    "external": false,
    "dom_matched": false,
    "get_by_text": "Active",
    "ocr_type": "label",
    "unique_name": "customers_active_label_status_5fc1bbb1",
    "label_text": "Active",
    "type": "ocr",
    "placeholder": "Active",
    "element_id": "817de9de-248f-4451-86dd-3c22b855609e",
    "intent": "status",
    "page_name": "customers"
  },
  {
    "page_name": "customers",
    "label_text": "2023-01-15",
    "ocr_type": "label",
    "element_id": "6498a461-79ea-4f52-8fa1-4bbe99421e00",
    "unique_name": "customers_2023-01-15_label_join_date_13b4a3e0",
    "dom_matched": false,
    "get_by_text": "2023-01-15",
    "intent": "join_date",
    "placeholder": "2023-01-15",
    "type": "ocr",
    "external": false
  },
  {
    "page_name": "customers",
    "element_id": "91a1c76a-a72a-4043-a53c-1923168c1674",
    "intent": "view_action",
    "unique_name": "customers_button_view_action_cc60ce91",
    "ocr_type": "button",
    "get_by_text": "",
    "type": "ocr",
    "external": false,
    "label_text": "",
    "dom_matched": false,
    "placeholder": ""
  },
  {
    "label_text": "",
    "page_name": "customers",
    "ocr_type": "button",
    "unique_name": "customers_button_edit_action_d3d0df61",
    "dom_matched": false,
    "type": "ocr",
    "element_id": "1f7500c4-990c-47c5-9278-0f811b26226e",
    "external": false,
    "get_by_text": "",
    "placeholder": "",
    "intent": "edit_action"
  },
  {
    "ocr_type": "label",
    "element_id": "f19fe4b7-6bed-4ead-8aa9-ac3de9246a17",
    "placeholder": "Michael Chen",
    "external": false,
    "type": "ocr",
    "get_by_text": "Michael Chen",
    "intent": "customer_name",
    "dom_matched": false,
    "page_name": "customers",
    "unique_name": "customers_michael_chen_label_customer_name_8dbd8345",
    "label_text": "Michael Chen"
  },
  {
    "type": "ocr",
    "external": false,
    "placeholder": "michael.chen@email.com",
    "unique_name": "customers_michael.chen@email.com_label_customer_email_8f50f16b",
    "page_name": "customers",
    "dom_matched": false,
    "get_by_text": "michael.chen@email.com",
    "element_id": "b977bf95-51a2-41c7-a529-6a76f39d28fc",
    "label_text": "michael.chen@email.com",
    "intent": "customer_email",
    "ocr_type": "label"
  },
  {
    "external": false,
    "get_by_text": "Standard",
    "page_name": "customers",
    "label_text": "Standard",
    "dom_matched": false,
    "ocr_type": "label",
    "element_id": "47b9416a-2e37-4d48-9cb5-490b3ab5d3d9",
    "intent": "account_type",
    "placeholder": "Standard",
    "unique_name": "customers_standard_label_account_type_ef9be216",
    "type": "ocr"
  },
  {
    "element_id": "0a552a01-927a-4f39-b59d-54a65c5aeaad",
    "label_text": "$52,000",
    "unique_name": "customers_$52,000_label_balance_b6e2bd67",
    "intent": "balance",
    "ocr_type": "label",
    "external": false,
    "placeholder": "$52,000",
    "get_by_text": "$52,000",
    "type": "ocr",
    "dom_matched": false,
    "page_name": "customers"
  },
  {
    "intent": "join_date",
    "dom_matched": false,
    "type": "ocr",
    "placeholder": "2023-03-22",
    "unique_name": "customers_2023-03-22_label_join_date_363240e3",
    "external": false,
    "ocr_type": "label",
    "page_name": "customers",
    "element_id": "4c127842-8648-4508-bbeb-e7cebfd480d2",
    "get_by_text": "2023-03-22",
    "label_text": "2023-03-22"
  },
  {
    "dom_matched": false,
    "intent": "customer_name",
    "ocr_type": "label",
    "page_name": "customers",
    "type": "ocr",
    "unique_name": "customers_emma_davis_label_customer_name_671b9ccd",
    "label_text": "Emma Davis",
    "element_id": "c43ac2f8-db98-4ac4-9482-a4d88b4aff25",
    "get_by_text": "Emma Davis",
    "placeholder": "Emma Davis",
    "external": false
  },
  {
    "label_text": "emma.davis@email.com",
    "unique_name": "customers_emma.davis@email.com_label_customer_email_1680f20b",
    "page_name": "customers",
    "external": false,
    "get_by_text": "emma.davis@email.com",
    "type": "ocr",
    "ocr_type": "label",
    "dom_matched": false,
    "placeholder": "emma.davis@email.com",
    "intent": "customer_email",
    "element_id": "d380bf82-8d5c-415a-b80a-0c0b17b49ed1"
  },
  {
    "intent": "balance",
    "type": "ocr",
    "ocr_type": "label",
    "placeholder": "$89,000",
    "label_text": "$89,000",
    "external": false,
    "get_by_text": "$89,000",
    "dom_matched": false,
    "page_name": "customers",
    "element_id": "7bd8dad6-2eab-413c-b035-fc9d3dc40af7",
    "unique_name": "customers_$89,000_label_balance_f3422319"
  },
  {
    "label_text": "2022-11-08",
    "placeholder": "2022-11-08",
    "unique_name": "customers_2022-11-08_label_join_date_bcd7c000",
    "dom_matched": false,
    "page_name": "customers",
    "element_id": "a53212d2-6ff3-4100-a779-1e52efba9c80",
    "get_by_text": "2022-11-08",
    "ocr_type": "label",
    "intent": "join_date",
    "external": false,
    "type": "ocr"
  },
  {
    "page_name": "customers",
    "dom_matched": false,
    "unique_name": "customers_edit_with_label_edit_info_0a420ebf",
    "element_id": "3b1d6cd1-40a5-4933-a5a7-ae9280d9c3cf",
    "intent": "edit_info",
    "placeholder": "Edit with",
    "label_text": "Edit with",
    "ocr_type": "label",
    "get_by_text": "Edit with",
    "type": "ocr",
    "external": false
  },
  {
    "external": false,
    "label_text": "Lovable",
    "ocr_type": "button",
    "element_id": "43488c62-d6f6-4850-8f23-1a37fccc1657",
    "page_name": "customers",
    "placeholder": "Lovable",
    "type": "ocr",
    "unique_name": "customers_lovable_button_edit_tool_efcb8fa0",
    "dom_matched": false,
    "intent": "edit_tool",
    "get_by_text": "Lovable"
  },
  {
    "label_text": "Add New Customer",
    "type": "ocr",
    "page_name": "customers",
    "intent": "form_title",
    "external": false,
    "unique_name": "customers_add_new_customer_label_form_title_2b3b0780",
    "placeholder": "Add New Customer",
    "element_id": "00015d8a-287f-47d9-bb1a-7f29748d9892",
    "get_by_text": "Add New Customer",
    "ocr_type": "label",
    "dom_matched": false
  },
  {
    "unique_name": "customers_enter_the_customer_details_to_create_a_new_account._label_form_instruction_4e368c65",
    "placeholder": "Enter the customer details to create a new account.",
    "element_id": "569c91f8-9a32-4562-8c97-39f7ebc3bccd",
    "get_by_text": "Enter the customer details to create a new account.",
    "label_text": "Enter the customer details to create a new account.",
    "ocr_type": "label",
    "external": false,
    "page_name": "customers",
    "intent": "form_instruction",
    "type": "ocr",
    "dom_matched": false
  },
  {
    "type": "ocr",
    "external": false,
    "intent": "full_name_label",
    "ocr_type": "label",
    "get_by_text": "Full Name",
    "dom_matched": false,
    "placeholder": "Full Name",
    "label_text": "Full Name",
    "page_name": "customers",
    "unique_name": "customers_full_name_label_full_name_label_7fa7eb35",
    "element_id": "33639538-f356-4621-aa2d-1a2816be7beb"
  },
  {
    "type": "ocr",
    "unique_name": "customers_textbox_full_name_input_b5555c13",
    "ocr_type": "textbox",
    "get_by_text": "",
    "intent": "full_name_input",
    "page_name": "customers",
    "external": false,
    "placeholder": "",
    "label_text": "",
    "dom_matched": false,
    "element_id": "d08c4210-8206-4034-9d71-12c1081cd19b"
  },
  {
    "unique_name": "customers_email_label_email_label_1e22d7f0",
    "placeholder": "Email",
    "intent": "email_label",
    "label_text": "Email",
    "ocr_type": "label",
    "type": "ocr",
    "page_name": "customers",
    "external": false,
    "element_id": "c018935e-b93b-43cd-be34-85f1536ffc5e",
    "get_by_text": "Email",
    "dom_matched": false
  },
  {
    "element_id": "0d54c4ac-3769-452e-8b37-0e0d94210c8f",
    "dom_matched": false,
    "get_by_text": "",
    "intent": "email_input",
    "placeholder": "",
    "label_text": "",
    "external": false,
    "unique_name": "customers_textbox_email_input_b7f01675",
    "page_name": "customers",
    "ocr_type": "textbox",
    "type": "ocr"
  },
  {
    "get_by_text": "Phone Number",
    "page_name": "customers",
    "placeholder": "Phone Number",
    "label_text": "Phone Number",
    "external": false,
    "unique_name": "customers_phone_number_label_phone_number_label_03e465fd",
    "intent": "phone_number_label",
    "element_id": "3d89dd5d-02c4-48f7-bf4d-d3f531f16f56",
    "ocr_type": "label",
    "type": "ocr",
    "dom_matched": false
  },
  {
    "placeholder": "",
    "type": "ocr",
    "label_text": "",
    "intent": "phone_number_input",
    "element_id": "486b218f-714e-4919-a331-54892bc256a2",
    "ocr_type": "textbox",
    "dom_matched": false,
    "get_by_text": "",
    "unique_name": "customers_textbox_phone_number_input_bb72a72b",
    "page_name": "customers",
    "external": false
  },
  {
    "element_id": "d4d79322-d3ba-4a18-9384-c80d2d45ee36",
    "external": false,
    "label_text": "Account Type",
    "type": "ocr",
    "unique_name": "customers_account_type_label_account_type_label_a1b76de7",
    "ocr_type": "label",
    "placeholder": "Account Type",
    "page_name": "customers",
    "intent": "account_type_label",
    "dom_matched": false,
    "get_by_text": "Account Type"
  },
  {
    "external": false,
    "get_by_text": "Select account type",
    "page_name": "customers",
    "intent": "account_type_select",
    "placeholder": "Select account type",
    "ocr_type": "select",
    "unique_name": "customers_select_account_type_select_account_type_select_739bf8ef",
    "element_id": "7b481fc3-f77e-4e08-b2bf-26b16ea64afa",
    "label_text": "Select account type",
    "dom_matched": false,
    "type": "ocr"
  },
  {
    "ocr_type": "label",
    "label_text": "Address",
    "page_name": "customers",
    "get_by_text": "Address",
    "type": "ocr",
    "element_id": "a62c6ddd-4aa1-476d-a551-33cd610df667",
    "intent": "address_label",
    "placeholder": "Address",
    "external": false,
    "unique_name": "customers_address_label_address_label_bfa99020",
    "dom_matched": false
  },
  {
    "external": false,
    "placeholder": "",
    "ocr_type": "textbox",
    "intent": "address_input",
    "page_name": "customers",
    "dom_matched": false,
    "type": "ocr",
    "unique_name": "customers_textbox_address_input_0da1bba0",
    "element_id": "469c9e87-3429-4950-b45f-ae171b5c8f53",
    "get_by_text": "",
    "label_text": ""
  },
  {
    "external": false,
    "type": "ocr",
    "element_id": "eebc5cb1-4c08-4413-b81d-a7b8a805466d",
    "ocr_type": "label",
    "get_by_text": "Occupation",
    "page_name": "customers",
    "label_text": "Occupation",
    "placeholder": "Occupation",
    "dom_matched": false,
    "unique_name": "customers_occupation_label_occupation_label_78041ebe",
    "intent": "occupation_label"
  },
  {
    "external": false,
    "page_name": "customers",
    "intent": "occupation_input",
    "dom_matched": false,
    "type": "ocr",
    "element_id": "7a137420-b5d9-4855-b662-a95b115e9204",
    "get_by_text": "",
    "unique_name": "customers_textbox_occupation_input_7c88216e",
    "ocr_type": "textbox",
    "label_text": "",
    "placeholder": ""
  },
  {
    "unique_name": "customers_annual_income_label_annual_income_label_41327b0b",
    "page_name": "customers",
    "label_text": "Annual Income",
    "dom_matched": false,
    "element_id": "9be4a552-0333-4fdd-8049-a42dde9c6ff1",
    "ocr_type": "label",
    "placeholder": "Annual Income",
    "intent": "annual_income_label",
    "external": false,
    "get_by_text": "Annual Income",
    "type": "ocr"
  },
  {
    "ocr_type": "textbox",
    "page_name": "customers",
    "external": false,
    "label_text": "",
    "element_id": "3e390a3e-ce76-4d63-9e73-0740abdb4b87",
    "placeholder": "",
    "unique_name": "customers_textbox_annual_income_input_7b960691",
    "type": "ocr",
    "get_by_text": "",
    "dom_matched": false,
    "intent": "annual_income_input"
  },
  {
    "get_by_text": "Initial Deposit",
    "external": false,
    "label_text": "Initial Deposit",
    "type": "ocr",
    "unique_name": "customers_initial_deposit_label_initial_deposit_label_a98dd99a",
    "placeholder": "Initial Deposit",
    "dom_matched": false,
    "intent": "initial_deposit_label",
    "page_name": "customers",
    "element_id": "4f5b78a9-3586-44e6-b598-460dd44d9da5",
    "ocr_type": "label"
  },
  {
    "external": false,
    "label_text": "",
    "dom_matched": false,
    "ocr_type": "textbox",
    "element_id": "108e3be9-517f-4c06-9199-25d4da6dfa13",
    "placeholder": "",
    "unique_name": "customers_textbox_initial_deposit_input_842f44e3",
    "get_by_text": "",
    "type": "ocr",
    "intent": "initial_deposit_input",
    "page_name": "customers"
  },
  {
    "ocr_type": "button",
    "placeholder": "Cancel",
    "page_name": "customers",
    "element_id": "15677d30-13f4-4a84-ad48-efa81a819a7e",
    "type": "ocr",
    "get_by_text": "Cancel",
    "dom_matched": false,
    "intent": "cancel",
    "external": false,
    "unique_name": "customers_cancel_button_cancel_71a3913d",
    "label_text": "Cancel"
  },
  {
    "label_text": "Add Customer",
    "element_id": "56635ce8-128b-4269-af74-c7c96884bb70",
    "type": "ocr",
    "intent": "submit",
    "placeholder": "Add Customer",
    "external": false,
    "unique_name": "customers_add_customer_button_submit_bce56d38",
    "ocr_type": "button",
    "get_by_text": "Add Customer",
    "page_name": "customers",
    "dom_matched": false
  }
]


# === FILE: generated_runs\src\metadata\enrichment_status.json ===
{
  "dashboard": true,
  "customers": true
}


# === FILE: generated_runs\src\ocr-dom-metadata\dom_elements_customers.txt ===
All DOM elements
Element 1:
  page_name:      customers
  tag_name:       div
  text:           Bank CRMNavigationDashboardCustomersLoansTransactionsTasksReportsAnalyticsSettingsToggle SidebarJohn DoeCustomersManage your customer relationships and accountsExportAdd CustomerFiltersCustomer List3 customers foundCustomerAccount TypeBalanceStatusJoin DateActionsSJSarah Johnsonsarah.johnson@email.comPremium$145,000Active2023-01-15MCMichael Chenmichael.chen@email.comStandard$52,000Active2023-03-22EDEmma Davisemma.davis@email.comPremium$89,000Active2022-11-08
  id:             root
  class:          
  value:          
  placeholder:    
  type:           
  attributes:     {'id': 'root'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <div id="root"><div role="region" aria-label="Notifications (F8)" tabindex="-1" style="pointer-events: none;"><ol tabind
------------------------------------------------------------
Element 2:
  page_name:      customers
  tag_name:       div
  text:           
  id:             
  class:          
  value:          
  placeholder:    
  type:           
  attributes:     {'role': 'region', 'aria-label': 'Notifications (F8)', 'tabindex': '-1', 'style': 'pointer-events: none;'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     Notifications (F8)
  HTML:           <div role="region" aria-label="Notifications (F8)" tabindex="-1" style="pointer-events: none;"><ol tabindex="-1" data-lo
------------------------------------------------------------
Element 3:
  page_name:      customers
  tag_name:       ol
  text:           
  id:             
  class:          fixed top-0 z-[100] flex max-h-screen w-full flex-col-reverse p-4 sm:bottom-0 sm:right-0 sm:top-auto sm:flex-col md:max-w-[420px]
  value:          
  placeholder:    
  type:           
  attributes:     {'tabindex': '-1', 'data-lov-id': 'src/components/ui/toaster.tsx:30:6', 'data-lov-name': 'ToastViewport', 'data-component-path': 'src/components/ui/toaster.tsx', 'data-component-line': '30', 'data-component-file': 'toaster.tsx', 'data-component-name': 'ToastViewport', 'data-component-content': '%7B%7D', 'class': 'fixed top-0 z-[100] flex max-h-screen w-full flex-col-reverse p-4 sm:bottom-0 sm:right-0 sm:top-auto sm:flex-col md:max-w-[420px]'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     ToastViewport
  HTML:           <ol tabindex="-1" data-lov-id="src/components/ui/toaster.tsx:30:6" data-lov-name="ToastViewport" data-component-path="sr
------------------------------------------------------------
Element 4:
  page_name:      customers
  tag_name:       div
  text:           Bank CRMNavigationDashboardCustomersLoansTransactionsTasksReportsAnalyticsSettingsToggle SidebarJohn DoeCustomersManage your customer relationships and accountsExportAdd CustomerFiltersCustomer List3 customers foundCustomerAccount TypeBalanceStatusJoin DateActionsSJSarah Johnsonsarah.johnson@email.comPremium$145,000Active2023-01-15MCMichael Chenmichael.chen@email.comStandard$52,000Active2023-03-22EDEmma Davisemma.davis@email.comPremium$89,000Active2022-11-08
  id:             
  class:          group/sidebar-wrapper flex min-h-svh w-full has-[[data-variant=inset]]:bg-sidebar
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/components/Layout.tsx:9:4', 'data-lov-name': 'SidebarProvider', 'data-component-path': 'src/components/Layout.tsx', 'data-component-line': '9', 'data-component-file': 'Layout.tsx', 'data-component-name': 'SidebarProvider', 'data-component-content': '%7B%7D', 'class': 'group/sidebar-wrapper flex min-h-svh w-full has-[[data-variant=inset]]:bg-sidebar', 'style': '--sidebar-width: 16rem; --sidebar-width-icon: 3rem;'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     SidebarProvider
  HTML:           <div data-lov-id="src/components/Layout.tsx:9:4" data-lov-name="SidebarProvider" data-component-path="src/components/Lay
------------------------------------------------------------
Element 5:
  page_name:      customers
  tag_name:       div
  text:           Bank CRMNavigationDashboardCustomersLoansTransactionsTasksReportsAnalyticsSettingsToggle SidebarJohn DoeCustomersManage your customer relationships and accountsExportAdd CustomerFiltersCustomer List3 customers foundCustomerAccount TypeBalanceStatusJoin DateActionsSJSarah Johnsonsarah.johnson@email.comPremium$145,000Active2023-01-15MCMichael Chenmichael.chen@email.comStandard$52,000Active2023-03-22EDEmma Davisemma.davis@email.comPremium$89,000Active2022-11-08
  id:             
  class:          min-h-screen flex w-full bg-gray-50
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/components/Layout.tsx:10:6', 'data-lov-name': 'div', 'data-component-path': 'src/components/Layout.tsx', 'data-component-line': '10', 'data-component-file': 'Layout.tsx', 'data-component-name': 'div', 'data-component-content': '%7B%22className%22%3A%22min-h-screen%20flex%20w-full%20bg-gray-50%22%7D', 'class': 'min-h-screen flex w-full bg-gray-50'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     div
  HTML:           <div data-lov-id="src/components/Layout.tsx:10:6" data-lov-name="div" data-component-path="src/components/Layout.tsx" da
------------------------------------------------------------
Element 6:
  page_name:      customers
  tag_name:       div
  text:           Bank CRMNavigationDashboardCustomersLoansTransactionsTasksReportsAnalyticsSettings
  id:             
  class:          group peer hidden md:block text-sidebar-foreground
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/components/ui/sidebar.tsx:214:6', 'data-lov-name': 'div', 'data-component-path': 'src/components/ui/sidebar.tsx', 'data-component-line': '214', 'data-component-file': 'sidebar.tsx', 'data-component-name': 'div', 'data-component-content': '%7B%22className%22%3A%22group%20peer%20hidden%20md%3Ablock%20text-sidebar-foreground%22%7D', 'class': 'group peer hidden md:block text-sidebar-foreground', 'data-state': 'expanded', 'data-collapsible': '', 'data-variant': 'sidebar', 'data-side': 'left'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     div
  HTML:           <div data-lov-id="src/components/ui/sidebar.tsx:214:6" data-lov-name="div" data-component-path="src/components/ui/sideba
------------------------------------------------------------
Element 7:
  page_name:      customers
  tag_name:       div
  text:           
  id:             
  class:          duration-200 relative h-svh w-[--sidebar-width] bg-transparent transition-[width] ease-linear group-data-[collapsible=offcanvas]:w-0 group-data-[side=right]:rotate-180 group-data-[collapsible=icon]:w-[--sidebar-width-icon]
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/components/ui/sidebar.tsx:223:8', 'data-lov-name': 'div', 'data-component-path': 'src/components/ui/sidebar.tsx', 'data-component-line': '223', 'data-component-file': 'sidebar.tsx', 'data-component-name': 'div', 'data-component-content': '%7B%7D', 'class': 'duration-200 relative h-svh w-[--sidebar-width] bg-transparent transition-[width] ease-linear group-data-[collapsible=offcanvas]:w-0 group-data-[side=right]:rotate-180 group-data-[collapsible=icon]:w-[--sidebar-width-icon]'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     div
  HTML:           <div data-lov-id="src/components/ui/sidebar.tsx:223:8" data-lov-name="div" data-component-path="src/components/ui/sideba
------------------------------------------------------------
Element 8:
  page_name:      customers
  tag_name:       div
  text:           Bank CRMNavigationDashboardCustomersLoansTransactionsTasksReportsAnalyticsSettings
  id:             
  class:          duration-200 fixed inset-y-0 z-10 hidden h-svh w-[--sidebar-width] transition-[left,right,width] ease-linear md:flex left-0 group-data-[collapsible=offcanvas]:left-[calc(var(--sidebar-width)*-1)] group-data-[collapsible=icon]:w-[--sidebar-width-icon] group-data-[side=left]:border-r group-data-[side=right]:border-l border-r bg-sidebar
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/components/AppSidebar.tsx:57:4', 'data-lov-name': 'Sidebar', 'data-component-path': 'src/components/AppSidebar.tsx', 'data-component-line': '57', 'data-component-file': 'AppSidebar.tsx', 'data-component-name': 'Sidebar', 'data-component-content': '%7B%22className%22%3A%22border-r%20bg-sidebar%22%7D', 'class': 'duration-200 fixed inset-y-0 z-10 hidden h-svh w-[--sidebar-width] transition-[left,right,width] ease-linear md:flex left-0 group-data-[collapsible=offcanvas]:left-[calc(var(--sidebar-width)*-1)] group-data-[collapsible=icon]:w-[--sidebar-width-icon] group-data-[side=left]:border-r group-data-[side=right]:border-l border-r bg-sidebar'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     Sidebar
  HTML:           <div data-lov-id="src/components/AppSidebar.tsx:57:4" data-lov-name="Sidebar" data-component-path="src/components/AppSid
------------------------------------------------------------
Element 9:
  page_name:      customers
  tag_name:       div
  text:           Bank CRMNavigationDashboardCustomersLoansTransactionsTasksReportsAnalyticsSettings
  id:             
  class:          flex h-full w-full flex-col bg-sidebar group-data-[variant=floating]:rounded-lg group-data-[variant=floating]:border group-data-[variant=floating]:border-sidebar-border group-data-[variant=floating]:shadow
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/components/ui/sidebar.tsx:247:10', 'data-lov-name': 'div', 'data-component-path': 'src/components/ui/sidebar.tsx', 'data-component-line': '247', 'data-component-file': 'sidebar.tsx', 'data-component-name': 'div', 'data-component-content': '%7B%22className%22%3A%22flex%20h-full%20w-full%20flex-col%20bg-sidebar%20group-data-%5Bvariant%3Dfloating%5D%3Arounded-lg%20group-data-%5Bvariant%3Dfloating%5D%3Aborder%20group-data-%5Bvariant%3Dfloating%5D%3Aborder-sidebar-border%20group-data-%5Bvariant%3Dfloating%5D%3Ashadow%22%7D', 'data-sidebar': 'sidebar', 'class': 'flex h-full w-full flex-col bg-sidebar group-data-[variant=floating]:rounded-lg group-data-[variant=floating]:border group-data-[variant=floating]:border-sidebar-border group-data-[variant=floating]:shadow'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     div
  HTML:           <div data-lov-id="src/components/ui/sidebar.tsx:247:10" data-lov-name="div" data-component-path="src/components/ui/sideb
------------------------------------------------------------
Element 10:
  page_name:      customers
  tag_name:       div
  text:           Bank CRMNavigationDashboardCustomersLoansTransactionsTasksReportsAnalyticsSettings
  id:             
  class:          flex min-h-0 flex-1 flex-col gap-2 overflow-auto group-data-[collapsible=icon]:overflow-hidden bg-sidebar
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/components/AppSidebar.tsx:58:6', 'data-lov-name': 'SidebarContent', 'data-component-path': 'src/components/AppSidebar.tsx', 'data-component-line': '58', 'data-component-file': 'AppSidebar.tsx', 'data-component-name': 'SidebarContent', 'data-component-content': '%7B%22className%22%3A%22bg-sidebar%22%7D', 'data-sidebar': 'content', 'class': 'flex min-h-0 flex-1 flex-col gap-2 overflow-auto group-data-[collapsible=icon]:overflow-hidden bg-sidebar'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     SidebarContent
  HTML:           <div data-lov-id="src/components/AppSidebar.tsx:58:6" data-lov-name="SidebarContent" data-component-path="src/components
------------------------------------------------------------
Element 11:
  page_name:      customers
  tag_name:       div
  text:           Bank CRM
  id:             
  class:          p-6
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/components/AppSidebar.tsx:59:8', 'data-lov-name': 'div', 'data-component-path': 'src/components/AppSidebar.tsx', 'data-component-line': '59', 'data-component-file': 'AppSidebar.tsx', 'data-component-name': 'div', 'data-component-content': '%7B%22className%22%3A%22p-6%22%7D', 'class': 'p-6'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     div
  HTML:           <div data-lov-id="src/components/AppSidebar.tsx:59:8" data-lov-name="div" data-component-path="src/components/AppSidebar
------------------------------------------------------------
Element 12:
  page_name:      customers
  tag_name:       div
  text:           Bank CRM
  id:             
  class:          flex items-center gap-2
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/components/AppSidebar.tsx:60:10', 'data-lov-name': 'div', 'data-component-path': 'src/components/AppSidebar.tsx', 'data-component-line': '60', 'data-component-file': 'AppSidebar.tsx', 'data-component-name': 'div', 'data-component-content': '%7B%22className%22%3A%22flex%20items-center%20gap-2%22%7D', 'class': 'flex items-center gap-2'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     div
  HTML:           <div data-lov-id="src/components/AppSidebar.tsx:60:10" data-lov-name="div" data-component-path="src/components/AppSideba
------------------------------------------------------------
Element 13:
  page_name:      customers
  tag_name:       div
  text:           
  id:             
  class:          w-8 h-8 bg-white rounded-lg flex items-center justify-center
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/components/AppSidebar.tsx:61:12', 'data-lov-name': 'div', 'data-component-path': 'src/components/AppSidebar.tsx', 'data-component-line': '61', 'data-component-file': 'AppSidebar.tsx', 'data-component-name': 'div', 'data-component-content': '%7B%22className%22%3A%22w-8%20h-8%20bg-white%20rounded-lg%20flex%20items-center%20justify-center%22%7D', 'class': 'w-8 h-8 bg-white rounded-lg flex items-center justify-center'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     div
  HTML:           <div data-lov-id="src/components/AppSidebar.tsx:61:12" data-lov-name="div" data-component-path="src/components/AppSideba
------------------------------------------------------------
Element 14:
  page_name:      customers
  tag_name:       svg
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'xmlns': 'http://www.w3.org/2000/svg', 'width': '24', 'height': '24', 'viewBox': '0 0 24 24', 'fill': 'none', 'stroke': 'currentColor', 'stroke-width': '2', 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'class': 'lucide lucide-dollar-sign w-5 h-5 text-primary', 'data-lov-id': 'src/components/AppSidebar.tsx:62:14', 'data-lov-name': 'DollarSign', 'data-component-path': 'src/components/AppSidebar.tsx', 'data-component-line': '62', 'data-component-file': 'AppSidebar.tsx', 'data-component-name': 'DollarSign', 'data-component-content': '%7B%22className%22%3A%22w-5%20h-5%20text-primary%22%7D'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     DollarSign
  HTML:           <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" str
------------------------------------------------------------
Element 15:
  page_name:      customers
  tag_name:       line
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'x1': '12', 'x2': '12', 'y1': '2', 'y2': '22'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <line x1="12" x2="12" y1="2" y2="22"></line>
------------------------------------------------------------
Element 16:
  page_name:      customers
  tag_name:       path
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'d': 'M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"></path>
------------------------------------------------------------
Element 17:
  page_name:      customers
  tag_name:       div
  text:           Bank CRM
  id:             
  class:          text-sidebar-foreground
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/components/AppSidebar.tsx:65:14', 'data-lov-name': 'div', 'data-component-path': 'src/components/AppSidebar.tsx', 'data-component-line': '65', 'data-component-file': 'AppSidebar.tsx', 'data-component-name': 'div', 'data-component-content': '%7B%22className%22%3A%22text-sidebar-foreground%22%7D', 'class': 'text-sidebar-foreground'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     div
  HTML:           <div data-lov-id="src/components/AppSidebar.tsx:65:14" data-lov-name="div" data-component-path="src/components/AppSideba
------------------------------------------------------------
Element 18:
  page_name:      customers
  tag_name:       h2
  text:           Bank CRM
  id:             
  class:          font-bold text-lg
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/components/AppSidebar.tsx:66:16', 'data-lov-name': 'h2', 'data-component-path': 'src/components/AppSidebar.tsx', 'data-component-line': '66', 'data-component-file': 'AppSidebar.tsx', 'data-component-name': 'h2', 'data-component-content': '%7B%22text%22%3A%22Bank%20CRM%22%2C%22className%22%3A%22font-bold%20text-lg%22%7D', 'class': 'font-bold text-lg'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     h2
  HTML:           <h2 data-lov-id="src/components/AppSidebar.tsx:66:16" data-lov-name="h2" data-component-path="src/components/AppSidebar.
------------------------------------------------------------
Element 19:
  page_name:      customers
  tag_name:       div
  text:           NavigationDashboardCustomersLoansTransactionsTasksReportsAnalyticsSettings
  id:             
  class:          relative flex w-full min-w-0 flex-col p-2
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/components/AppSidebar.tsx:72:8', 'data-lov-name': 'SidebarGroup', 'data-component-path': 'src/components/AppSidebar.tsx', 'data-component-line': '72', 'data-component-file': 'AppSidebar.tsx', 'data-component-name': 'SidebarGroup', 'data-component-content': '%7B%7D', 'data-sidebar': 'group', 'class': 'relative flex w-full min-w-0 flex-col p-2'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     SidebarGroup
  HTML:           <div data-lov-id="src/components/AppSidebar.tsx:72:8" data-lov-name="SidebarGroup" data-component-path="src/components/A
------------------------------------------------------------
Element 20:
  page_name:      customers
  tag_name:       div
  text:           Navigation
  id:             
  class:          duration-200 flex h-8 shrink-0 items-center rounded-md px-2 text-xs font-medium outline-none ring-sidebar-ring transition-[margin,opa] ease-linear focus-visible:ring-2 [&>svg]:size-4 [&>svg]:shrink-0 group-data-[collapsible=icon]:-mt-8 group-data-[collapsible=icon]:opacity-0 text-sidebar-foreground/70
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/components/AppSidebar.tsx:73:10', 'data-lov-name': 'SidebarGroupLabel', 'data-component-path': 'src/components/AppSidebar.tsx', 'data-component-line': '73', 'data-component-file': 'AppSidebar.tsx', 'data-component-name': 'SidebarGroupLabel', 'data-component-content': '%7B%22className%22%3A%22text-sidebar-foreground%2F70%22%7D', 'data-sidebar': 'group-label', 'class': 'duration-200 flex h-8 shrink-0 items-center rounded-md px-2 text-xs font-medium outline-none ring-sidebar-ring transition-[margin,opa] ease-linear focus-visible:ring-2 [&>svg]:size-4 [&>svg]:shrink-0 group-data-[collapsible=icon]:-mt-8 group-data-[collapsible=icon]:opacity-0 text-sidebar-foreground/70'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     SidebarGroupLabel
  HTML:           <div data-lov-id="src/components/AppSidebar.tsx:73:10" data-lov-name="SidebarGroupLabel" data-component-path="src/compon
------------------------------------------------------------
Element 21:
  page_name:      customers
  tag_name:       div
  text:           DashboardCustomersLoansTransactionsTasksReportsAnalyticsSettings
  id:             
  class:          w-full text-sm
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/components/AppSidebar.tsx:76:10', 'data-lov-name': 'SidebarGroupContent', 'data-component-path': 'src/components/AppSidebar.tsx', 'data-component-line': '76', 'data-component-file': 'AppSidebar.tsx', 'data-component-name': 'SidebarGroupContent', 'data-component-content': '%7B%7D', 'data-sidebar': 'group-content', 'class': 'w-full text-sm'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     SidebarGroupContent
  HTML:           <div data-lov-id="src/components/AppSidebar.tsx:76:10" data-lov-name="SidebarGroupContent" data-component-path="src/comp
------------------------------------------------------------
Element 22:
  page_name:      customers
  tag_name:       ul
  text:           DashboardCustomersLoansTransactionsTasksReportsAnalyticsSettings
  id:             
  class:          flex w-full min-w-0 flex-col gap-1
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/components/AppSidebar.tsx:77:12', 'data-lov-name': 'SidebarMenu', 'data-component-path': 'src/components/AppSidebar.tsx', 'data-component-line': '77', 'data-component-file': 'AppSidebar.tsx', 'data-component-name': 'SidebarMenu', 'data-component-content': '%7B%7D', 'data-sidebar': 'menu', 'class': 'flex w-full min-w-0 flex-col gap-1'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     SidebarMenu
  HTML:           <ul data-lov-id="src/components/AppSidebar.tsx:77:12" data-lov-name="SidebarMenu" data-component-path="src/components/Ap
------------------------------------------------------------
Element 23:
  page_name:      customers
  tag_name:       li
  text:           Dashboard
  id:             
  class:          group/menu-item relative
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/components/AppSidebar.tsx:79:16', 'data-lov-name': 'SidebarMenuItem', 'data-component-path': 'src/components/AppSidebar.tsx', 'data-component-line': '79', 'data-component-file': 'AppSidebar.tsx', 'data-component-name': 'SidebarMenuItem', 'data-component-content': '%7B%7D', 'data-sidebar': 'menu-item', 'class': 'group/menu-item relative'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     SidebarMenuItem
  HTML:           <li data-lov-id="src/components/AppSidebar.tsx:79:16" data-lov-name="SidebarMenuItem" data-component-path="src/component
------------------------------------------------------------
Element 24:
  page_name:      customers
  tag_name:       a
  text:           Dashboard
  id:             
  class:          peer/menu-button flex w-full items-center gap-2 overflow-hidden rounded-md p-2 text-left outline-none ring-sidebar-ring transition-[width,height,padding] focus-visible:ring-2 active:bg-sidebar-accent active:text-sidebar-accent-foreground disabled:pointer-events-none disabled:opacity-50 group-has-[[data-sidebar=menu-action]]/menu-item:pr-8 aria-disabled:pointer-events-none aria-disabled:opacity-50 data-[active=true]:bg-sidebar-accent data-[active=true]:font-medium data-[active=true]:text-sidebar-accent-foreground data-[state=open]:hover:bg-sidebar-accent data-[state=open]:hover:text-sidebar-accent-foreground group-data-[collapsible=icon]:!size-8 group-data-[collapsible=icon]:!p-2 [&>span:last-child]:truncate [&>svg]:size-4 [&>svg]:shrink-0 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground h-8 text-sm w-full justify-start transition-colors hover:bg-sidebar-accent hover:text-sidebar-accent-foreground
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/components/AppSidebar.tsx:81:20', 'data-lov-name': 'NavLink', 'data-component-path': 'src/components/AppSidebar.tsx', 'data-component-line': '81', 'data-component-file': 'AppSidebar.tsx', 'data-component-name': 'NavLink', 'data-component-content': '%7B%7D', 'data-sidebar': 'menu-button', 'data-size': 'default', 'data-active': 'false', 'class': 'peer/menu-button flex w-full items-center gap-2 overflow-hidden rounded-md p-2 text-left outline-none ring-sidebar-ring transition-[width,height,padding] focus-visible:ring-2 active:bg-sidebar-accent active:text-sidebar-accent-foreground disabled:pointer-events-none disabled:opacity-50 group-has-[[data-sidebar=menu-action]]/menu-item:pr-8 aria-disabled:pointer-events-none aria-disabled:opacity-50 data-[active=true]:bg-sidebar-accent data-[active=true]:font-medium data-[active=true]:text-sidebar-accent-foreground data-[state=open]:hover:bg-sidebar-accent data-[state=open]:hover:text-sidebar-accent-foreground group-data-[collapsible=icon]:!size-8 group-data-[collapsible=icon]:!p-2 [&>span:last-child]:truncate [&>svg]:size-4 [&>svg]:shrink-0 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground h-8 text-sm w-full justify-start transition-colors hover:bg-sidebar-accent hover:text-sidebar-accent-foreground', 'href': '/'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     NavLink
  HTML:           <a data-lov-id="src/components/AppSidebar.tsx:81:20" data-lov-name="NavLink" data-component-path="src/components/AppSide
------------------------------------------------------------
Element 25:
  page_name:      customers
  tag_name:       svg
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'xmlns': 'http://www.w3.org/2000/svg', 'width': '24', 'height': '24', 'viewBox': '0 0 24 24', 'fill': 'none', 'stroke': 'currentColor', 'stroke-width': '2', 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'class': 'lucide lucide-house w-4 h-4', 'data-lov-id': 'src/components/AppSidebar.tsx:82:22', 'data-lov-name': 'item.icon', 'data-component-path': 'src/components/AppSidebar.tsx', 'data-component-line': '82', 'data-component-file': 'AppSidebar.tsx', 'data-component-name': 'item.icon', 'data-component-content': '%7B%22className%22%3A%22w-4%20h-4%22%7D'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     item.icon
  HTML:           <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" str
------------------------------------------------------------
Element 26:
  page_name:      customers
  tag_name:       path
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'d': 'M15 21v-8a1 1 0 0 0-1-1h-4a1 1 0 0 0-1 1v8'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <path d="M15 21v-8a1 1 0 0 0-1-1h-4a1 1 0 0 0-1 1v8"></path>
------------------------------------------------------------
Element 27:
  page_name:      customers
  tag_name:       path
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'d': 'M3 10a2 2 0 0 1 .709-1.528l7-5.999a2 2 0 0 1 2.582 0l7 5.999A2 2 0 0 1 21 10v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <path d="M3 10a2 2 0 0 1 .709-1.528l7-5.999a2 2 0 0 1 2.582 0l7 5.999A2 2 0 0 1 21 10v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z">
------------------------------------------------------------
Element 28:
  page_name:      customers
  tag_name:       span
  text:           Dashboard
  id:             
  class:          
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/components/AppSidebar.tsx:83:39', 'data-lov-name': 'span', 'data-component-path': 'src/components/AppSidebar.tsx', 'data-component-line': '83', 'data-component-file': 'AppSidebar.tsx', 'data-component-name': 'span', 'data-component-content': '%7B%7D'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     span
  HTML:           <span data-lov-id="src/components/AppSidebar.tsx:83:39" data-lov-name="span" data-component-path="src/components/AppSide
------------------------------------------------------------
Element 29:
  page_name:      customers
  tag_name:       li
  text:           Customers
  id:             
  class:          group/menu-item relative
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/components/AppSidebar.tsx:79:16', 'data-lov-name': 'SidebarMenuItem', 'data-component-path': 'src/components/AppSidebar.tsx', 'data-component-line': '79', 'data-component-file': 'AppSidebar.tsx', 'data-component-name': 'SidebarMenuItem', 'data-component-content': '%7B%7D', 'data-sidebar': 'menu-item', 'class': 'group/menu-item relative'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     SidebarMenuItem
  HTML:           <li data-lov-id="src/components/AppSidebar.tsx:79:16" data-lov-name="SidebarMenuItem" data-component-path="src/component
------------------------------------------------------------
Element 30:
  page_name:      customers
  tag_name:       a
  text:           Customers
  id:             
  class:          peer/menu-button flex w-full items-center gap-2 overflow-hidden rounded-md p-2 text-left outline-none ring-sidebar-ring transition-[width,height,padding] focus-visible:ring-2 active:bg-sidebar-accent active:text-sidebar-accent-foreground disabled:pointer-events-none disabled:opacity-50 group-has-[[data-sidebar=menu-action]]/menu-item:pr-8 aria-disabled:pointer-events-none aria-disabled:opacity-50 data-[active=true]:bg-sidebar-accent data-[active=true]:font-medium data-[active=true]:text-sidebar-accent-foreground data-[state=open]:hover:bg-sidebar-accent data-[state=open]:hover:text-sidebar-accent-foreground group-data-[collapsible=icon]:!size-8 group-data-[collapsible=icon]:!p-2 [&>span:last-child]:truncate [&>svg]:size-4 [&>svg]:shrink-0 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground h-8 text-sm w-full justify-start transition-colors bg-sidebar-accent text-sidebar-accent-foreground active
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/components/AppSidebar.tsx:81:20', 'data-lov-name': 'NavLink', 'data-component-path': 'src/components/AppSidebar.tsx', 'data-component-line': '81', 'data-component-file': 'AppSidebar.tsx', 'data-component-name': 'NavLink', 'data-component-content': '%7B%7D', 'data-sidebar': 'menu-button', 'data-size': 'default', 'data-active': 'false', 'class': 'peer/menu-button flex w-full items-center gap-2 overflow-hidden rounded-md p-2 text-left outline-none ring-sidebar-ring transition-[width,height,padding] focus-visible:ring-2 active:bg-sidebar-accent active:text-sidebar-accent-foreground disabled:pointer-events-none disabled:opacity-50 group-has-[[data-sidebar=menu-action]]/menu-item:pr-8 aria-disabled:pointer-events-none aria-disabled:opacity-50 data-[active=true]:bg-sidebar-accent data-[active=true]:font-medium data-[active=true]:text-sidebar-accent-foreground data-[state=open]:hover:bg-sidebar-accent data-[state=open]:hover:text-sidebar-accent-foreground group-data-[collapsible=icon]:!size-8 group-data-[collapsible=icon]:!p-2 [&>span:last-child]:truncate [&>svg]:size-4 [&>svg]:shrink-0 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground h-8 text-sm w-full justify-start transition-colors bg-sidebar-accent text-sidebar-accent-foreground active', 'href': '/customers', 'aria-current': 'page'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     NavLink
  HTML:           <a data-lov-id="src/components/AppSidebar.tsx:81:20" data-lov-name="NavLink" data-component-path="src/components/AppSide
------------------------------------------------------------
Element 31:
  page_name:      customers
  tag_name:       svg
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'xmlns': 'http://www.w3.org/2000/svg', 'width': '24', 'height': '24', 'viewBox': '0 0 24 24', 'fill': 'none', 'stroke': 'currentColor', 'stroke-width': '2', 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'class': 'lucide lucide-users w-4 h-4', 'data-lov-id': 'src/components/AppSidebar.tsx:82:22', 'data-lov-name': 'item.icon', 'data-component-path': 'src/components/AppSidebar.tsx', 'data-component-line': '82', 'data-component-file': 'AppSidebar.tsx', 'data-component-name': 'item.icon', 'data-component-content': '%7B%22className%22%3A%22w-4%20h-4%22%7D'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     item.icon
  HTML:           <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" str
------------------------------------------------------------
Element 32:
  page_name:      customers
  tag_name:       path
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'d': 'M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"></path>
------------------------------------------------------------
Element 33:
  page_name:      customers
  tag_name:       circle
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'cx': '9', 'cy': '7', 'r': '4'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <circle cx="9" cy="7" r="4"></circle>
------------------------------------------------------------
Element 34:
  page_name:      customers
  tag_name:       path
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'d': 'M22 21v-2a4 4 0 0 0-3-3.87'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <path d="M22 21v-2a4 4 0 0 0-3-3.87"></path>
------------------------------------------------------------
Element 35:
  page_name:      customers
  tag_name:       path
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'d': 'M16 3.13a4 4 0 0 1 0 7.75'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <path d="M16 3.13a4 4 0 0 1 0 7.75"></path>
------------------------------------------------------------
Element 36:
  page_name:      customers
  tag_name:       span
  text:           Customers
  id:             
  class:          
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/components/AppSidebar.tsx:83:39', 'data-lov-name': 'span', 'data-component-path': 'src/components/AppSidebar.tsx', 'data-component-line': '83', 'data-component-file': 'AppSidebar.tsx', 'data-component-name': 'span', 'data-component-content': '%7B%7D'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     span
  HTML:           <span data-lov-id="src/components/AppSidebar.tsx:83:39" data-lov-name="span" data-component-path="src/components/AppSide
------------------------------------------------------------
Element 37:
  page_name:      customers
  tag_name:       li
  text:           Loans
  id:             
  class:          group/menu-item relative
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/components/AppSidebar.tsx:79:16', 'data-lov-name': 'SidebarMenuItem', 'data-component-path': 'src/components/AppSidebar.tsx', 'data-component-line': '79', 'data-component-file': 'AppSidebar.tsx', 'data-component-name': 'SidebarMenuItem', 'data-component-content': '%7B%7D', 'data-sidebar': 'menu-item', 'class': 'group/menu-item relative'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     SidebarMenuItem
  HTML:           <li data-lov-id="src/components/AppSidebar.tsx:79:16" data-lov-name="SidebarMenuItem" data-component-path="src/component
------------------------------------------------------------
Element 38:
  page_name:      customers
  tag_name:       a
  text:           Loans
  id:             
  class:          peer/menu-button flex w-full items-center gap-2 overflow-hidden rounded-md p-2 text-left outline-none ring-sidebar-ring transition-[width,height,padding] focus-visible:ring-2 active:bg-sidebar-accent active:text-sidebar-accent-foreground disabled:pointer-events-none disabled:opacity-50 group-has-[[data-sidebar=menu-action]]/menu-item:pr-8 aria-disabled:pointer-events-none aria-disabled:opacity-50 data-[active=true]:bg-sidebar-accent data-[active=true]:font-medium data-[active=true]:text-sidebar-accent-foreground data-[state=open]:hover:bg-sidebar-accent data-[state=open]:hover:text-sidebar-accent-foreground group-data-[collapsible=icon]:!size-8 group-data-[collapsible=icon]:!p-2 [&>span:last-child]:truncate [&>svg]:size-4 [&>svg]:shrink-0 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground h-8 text-sm w-full justify-start transition-colors hover:bg-sidebar-accent hover:text-sidebar-accent-foreground
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/components/AppSidebar.tsx:81:20', 'data-lov-name': 'NavLink', 'data-component-path': 'src/components/AppSidebar.tsx', 'data-component-line': '81', 'data-component-file': 'AppSidebar.tsx', 'data-component-name': 'NavLink', 'data-component-content': '%7B%7D', 'data-sidebar': 'menu-button', 'data-size': 'default', 'data-active': 'false', 'class': 'peer/menu-button flex w-full items-center gap-2 overflow-hidden rounded-md p-2 text-left outline-none ring-sidebar-ring transition-[width,height,padding] focus-visible:ring-2 active:bg-sidebar-accent active:text-sidebar-accent-foreground disabled:pointer-events-none disabled:opacity-50 group-has-[[data-sidebar=menu-action]]/menu-item:pr-8 aria-disabled:pointer-events-none aria-disabled:opacity-50 data-[active=true]:bg-sidebar-accent data-[active=true]:font-medium data-[active=true]:text-sidebar-accent-foreground data-[state=open]:hover:bg-sidebar-accent data-[state=open]:hover:text-sidebar-accent-foreground group-data-[collapsible=icon]:!size-8 group-data-[collapsible=icon]:!p-2 [&>span:last-child]:truncate [&>svg]:size-4 [&>svg]:shrink-0 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground h-8 text-sm w-full justify-start transition-colors hover:bg-sidebar-accent hover:text-sidebar-accent-foreground', 'href': '/loans'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     NavLink
  HTML:           <a data-lov-id="src/components/AppSidebar.tsx:81:20" data-lov-name="NavLink" data-component-path="src/components/AppSide
------------------------------------------------------------
Element 39:
  page_name:      customers
  tag_name:       svg
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'xmlns': 'http://www.w3.org/2000/svg', 'width': '24', 'height': '24', 'viewBox': '0 0 24 24', 'fill': 'none', 'stroke': 'currentColor', 'stroke-width': '2', 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'class': 'lucide lucide-dollar-sign w-4 h-4', 'data-lov-id': 'src/components/AppSidebar.tsx:82:22', 'data-lov-name': 'item.icon', 'data-component-path': 'src/components/AppSidebar.tsx', 'data-component-line': '82', 'data-component-file': 'AppSidebar.tsx', 'data-component-name': 'item.icon', 'data-component-content': '%7B%22className%22%3A%22w-4%20h-4%22%7D'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     item.icon
  HTML:           <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" str
------------------------------------------------------------
Element 40:
  page_name:      customers
  tag_name:       line
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'x1': '12', 'x2': '12', 'y1': '2', 'y2': '22'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <line x1="12" x2="12" y1="2" y2="22"></line>
------------------------------------------------------------
Element 41:
  page_name:      customers
  tag_name:       path
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'d': 'M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"></path>
------------------------------------------------------------
Element 42:
  page_name:      customers
  tag_name:       span
  text:           Loans
  id:             
  class:          
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/components/AppSidebar.tsx:83:39', 'data-lov-name': 'span', 'data-component-path': 'src/components/AppSidebar.tsx', 'data-component-line': '83', 'data-component-file': 'AppSidebar.tsx', 'data-component-name': 'span', 'data-component-content': '%7B%7D'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     span
  HTML:           <span data-lov-id="src/components/AppSidebar.tsx:83:39" data-lov-name="span" data-component-path="src/components/AppSide
------------------------------------------------------------
Element 43:
  page_name:      customers
  tag_name:       li
  text:           Transactions
  id:             
  class:          group/menu-item relative
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/components/AppSidebar.tsx:79:16', 'data-lov-name': 'SidebarMenuItem', 'data-component-path': 'src/components/AppSidebar.tsx', 'data-component-line': '79', 'data-component-file': 'AppSidebar.tsx', 'data-component-name': 'SidebarMenuItem', 'data-component-content': '%7B%7D', 'data-sidebar': 'menu-item', 'class': 'group/menu-item relative'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     SidebarMenuItem
  HTML:           <li data-lov-id="src/components/AppSidebar.tsx:79:16" data-lov-name="SidebarMenuItem" data-component-path="src/component
------------------------------------------------------------
Element 44:
  page_name:      customers
  tag_name:       a
  text:           Transactions
  id:             
  class:          peer/menu-button flex w-full items-center gap-2 overflow-hidden rounded-md p-2 text-left outline-none ring-sidebar-ring transition-[width,height,padding] focus-visible:ring-2 active:bg-sidebar-accent active:text-sidebar-accent-foreground disabled:pointer-events-none disabled:opacity-50 group-has-[[data-sidebar=menu-action]]/menu-item:pr-8 aria-disabled:pointer-events-none aria-disabled:opacity-50 data-[active=true]:bg-sidebar-accent data-[active=true]:font-medium data-[active=true]:text-sidebar-accent-foreground data-[state=open]:hover:bg-sidebar-accent data-[state=open]:hover:text-sidebar-accent-foreground group-data-[collapsible=icon]:!size-8 group-data-[collapsible=icon]:!p-2 [&>span:last-child]:truncate [&>svg]:size-4 [&>svg]:shrink-0 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground h-8 text-sm w-full justify-start transition-colors hover:bg-sidebar-accent hover:text-sidebar-accent-foreground
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/components/AppSidebar.tsx:81:20', 'data-lov-name': 'NavLink', 'data-component-path': 'src/components/AppSidebar.tsx', 'data-component-line': '81', 'data-component-file': 'AppSidebar.tsx', 'data-component-name': 'NavLink', 'data-component-content': '%7B%7D', 'data-sidebar': 'menu-button', 'data-size': 'default', 'data-active': 'false', 'class': 'peer/menu-button flex w-full items-center gap-2 overflow-hidden rounded-md p-2 text-left outline-none ring-sidebar-ring transition-[width,height,padding] focus-visible:ring-2 active:bg-sidebar-accent active:text-sidebar-accent-foreground disabled:pointer-events-none disabled:opacity-50 group-has-[[data-sidebar=menu-action]]/menu-item:pr-8 aria-disabled:pointer-events-none aria-disabled:opacity-50 data-[active=true]:bg-sidebar-accent data-[active=true]:font-medium data-[active=true]:text-sidebar-accent-foreground data-[state=open]:hover:bg-sidebar-accent data-[state=open]:hover:text-sidebar-accent-foreground group-data-[collapsible=icon]:!size-8 group-data-[collapsible=icon]:!p-2 [&>span:last-child]:truncate [&>svg]:size-4 [&>svg]:shrink-0 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground h-8 text-sm w-full justify-start transition-colors hover:bg-sidebar-accent hover:text-sidebar-accent-foreground', 'href': '/transactions'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     NavLink
  HTML:           <a data-lov-id="src/components/AppSidebar.tsx:81:20" data-lov-name="NavLink" data-component-path="src/components/AppSide
------------------------------------------------------------
Element 45:
  page_name:      customers
  tag_name:       svg
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'xmlns': 'http://www.w3.org/2000/svg', 'width': '24', 'height': '24', 'viewBox': '0 0 24 24', 'fill': 'none', 'stroke': 'currentColor', 'stroke-width': '2', 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'class': 'lucide lucide-credit-card w-4 h-4', 'data-lov-id': 'src/components/AppSidebar.tsx:82:22', 'data-lov-name': 'item.icon', 'data-component-path': 'src/components/AppSidebar.tsx', 'data-component-line': '82', 'data-component-file': 'AppSidebar.tsx', 'data-component-name': 'item.icon', 'data-component-content': '%7B%22className%22%3A%22w-4%20h-4%22%7D'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     item.icon
  HTML:           <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" str
------------------------------------------------------------
Element 46:
  page_name:      customers
  tag_name:       rect
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'width': '20', 'height': '14', 'x': '2', 'y': '5', 'rx': '2'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <rect width="20" height="14" x="2" y="5" rx="2"></rect>
------------------------------------------------------------
Element 47:
  page_name:      customers
  tag_name:       line
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'x1': '2', 'x2': '22', 'y1': '10', 'y2': '10'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <line x1="2" x2="22" y1="10" y2="10"></line>
------------------------------------------------------------
Element 48:
  page_name:      customers
  tag_name:       span
  text:           Transactions
  id:             
  class:          
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/components/AppSidebar.tsx:83:39', 'data-lov-name': 'span', 'data-component-path': 'src/components/AppSidebar.tsx', 'data-component-line': '83', 'data-component-file': 'AppSidebar.tsx', 'data-component-name': 'span', 'data-component-content': '%7B%7D'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     span
  HTML:           <span data-lov-id="src/components/AppSidebar.tsx:83:39" data-lov-name="span" data-component-path="src/components/AppSide
------------------------------------------------------------
Element 49:
  page_name:      customers
  tag_name:       li
  text:           Tasks
  id:             
  class:          group/menu-item relative
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/components/AppSidebar.tsx:79:16', 'data-lov-name': 'SidebarMenuItem', 'data-component-path': 'src/components/AppSidebar.tsx', 'data-component-line': '79', 'data-component-file': 'AppSidebar.tsx', 'data-component-name': 'SidebarMenuItem', 'data-component-content': '%7B%7D', 'data-sidebar': 'menu-item', 'class': 'group/menu-item relative'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     SidebarMenuItem
  HTML:           <li data-lov-id="src/components/AppSidebar.tsx:79:16" data-lov-name="SidebarMenuItem" data-component-path="src/component
------------------------------------------------------------
Element 50:
  page_name:      customers
  tag_name:       a
  text:           Tasks
  id:             
  class:          peer/menu-button flex w-full items-center gap-2 overflow-hidden rounded-md p-2 text-left outline-none ring-sidebar-ring transition-[width,height,padding] focus-visible:ring-2 active:bg-sidebar-accent active:text-sidebar-accent-foreground disabled:pointer-events-none disabled:opacity-50 group-has-[[data-sidebar=menu-action]]/menu-item:pr-8 aria-disabled:pointer-events-none aria-disabled:opacity-50 data-[active=true]:bg-sidebar-accent data-[active=true]:font-medium data-[active=true]:text-sidebar-accent-foreground data-[state=open]:hover:bg-sidebar-accent data-[state=open]:hover:text-sidebar-accent-foreground group-data-[collapsible=icon]:!size-8 group-data-[collapsible=icon]:!p-2 [&>span:last-child]:truncate [&>svg]:size-4 [&>svg]:shrink-0 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground h-8 text-sm w-full justify-start transition-colors hover:bg-sidebar-accent hover:text-sidebar-accent-foreground
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/components/AppSidebar.tsx:81:20', 'data-lov-name': 'NavLink', 'data-component-path': 'src/components/AppSidebar.tsx', 'data-component-line': '81', 'data-component-file': 'AppSidebar.tsx', 'data-component-name': 'NavLink', 'data-component-content': '%7B%7D', 'data-sidebar': 'menu-button', 'data-size': 'default', 'data-active': 'false', 'class': 'peer/menu-button flex w-full items-center gap-2 overflow-hidden rounded-md p-2 text-left outline-none ring-sidebar-ring transition-[width,height,padding] focus-visible:ring-2 active:bg-sidebar-accent active:text-sidebar-accent-foreground disabled:pointer-events-none disabled:opacity-50 group-has-[[data-sidebar=menu-action]]/menu-item:pr-8 aria-disabled:pointer-events-none aria-disabled:opacity-50 data-[active=true]:bg-sidebar-accent data-[active=true]:font-medium data-[active=true]:text-sidebar-accent-foreground data-[state=open]:hover:bg-sidebar-accent data-[state=open]:hover:text-sidebar-accent-foreground group-data-[collapsible=icon]:!size-8 group-data-[collapsible=icon]:!p-2 [&>span:last-child]:truncate [&>svg]:size-4 [&>svg]:shrink-0 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground h-8 text-sm w-full justify-start transition-colors hover:bg-sidebar-accent hover:text-sidebar-accent-foreground', 'href': '/tasks'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     NavLink
  HTML:           <a data-lov-id="src/components/AppSidebar.tsx:81:20" data-lov-name="NavLink" data-component-path="src/components/AppSide
------------------------------------------------------------
Element 51:
  page_name:      customers
  tag_name:       svg
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'xmlns': 'http://www.w3.org/2000/svg', 'width': '24', 'height': '24', 'viewBox': '0 0 24 24', 'fill': 'none', 'stroke': 'currentColor', 'stroke-width': '2', 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'class': 'lucide lucide-square-check-big w-4 h-4', 'data-lov-id': 'src/components/AppSidebar.tsx:82:22', 'data-lov-name': 'item.icon', 'data-component-path': 'src/components/AppSidebar.tsx', 'data-component-line': '82', 'data-component-file': 'AppSidebar.tsx', 'data-component-name': 'item.icon', 'data-component-content': '%7B%22className%22%3A%22w-4%20h-4%22%7D'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     item.icon
  HTML:           <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" str
------------------------------------------------------------
Element 52:
  page_name:      customers
  tag_name:       path
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'d': 'M21 10.5V19a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h12.5'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <path d="M21 10.5V19a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h12.5"></path>
------------------------------------------------------------
Element 53:
  page_name:      customers
  tag_name:       path
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'d': 'm9 11 3 3L22 4'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <path d="m9 11 3 3L22 4"></path>
------------------------------------------------------------
Element 54:
  page_name:      customers
  tag_name:       span
  text:           Tasks
  id:             
  class:          
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/components/AppSidebar.tsx:83:39', 'data-lov-name': 'span', 'data-component-path': 'src/components/AppSidebar.tsx', 'data-component-line': '83', 'data-component-file': 'AppSidebar.tsx', 'data-component-name': 'span', 'data-component-content': '%7B%7D'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     span
  HTML:           <span data-lov-id="src/components/AppSidebar.tsx:83:39" data-lov-name="span" data-component-path="src/components/AppSide
------------------------------------------------------------
Element 55:
  page_name:      customers
  tag_name:       li
  text:           Reports
  id:             
  class:          group/menu-item relative
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/components/AppSidebar.tsx:79:16', 'data-lov-name': 'SidebarMenuItem', 'data-component-path': 'src/components/AppSidebar.tsx', 'data-component-line': '79', 'data-component-file': 'AppSidebar.tsx', 'data-component-name': 'SidebarMenuItem', 'data-component-content': '%7B%7D', 'data-sidebar': 'menu-item', 'class': 'group/menu-item relative'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     SidebarMenuItem
  HTML:           <li data-lov-id="src/components/AppSidebar.tsx:79:16" data-lov-name="SidebarMenuItem" data-component-path="src/component
------------------------------------------------------------
Element 56:
  page_name:      customers
  tag_name:       a
  text:           Reports
  id:             
  class:          peer/menu-button flex w-full items-center gap-2 overflow-hidden rounded-md p-2 text-left outline-none ring-sidebar-ring transition-[width,height,padding] focus-visible:ring-2 active:bg-sidebar-accent active:text-sidebar-accent-foreground disabled:pointer-events-none disabled:opacity-50 group-has-[[data-sidebar=menu-action]]/menu-item:pr-8 aria-disabled:pointer-events-none aria-disabled:opacity-50 data-[active=true]:bg-sidebar-accent data-[active=true]:font-medium data-[active=true]:text-sidebar-accent-foreground data-[state=open]:hover:bg-sidebar-accent data-[state=open]:hover:text-sidebar-accent-foreground group-data-[collapsible=icon]:!size-8 group-data-[collapsible=icon]:!p-2 [&>span:last-child]:truncate [&>svg]:size-4 [&>svg]:shrink-0 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground h-8 text-sm w-full justify-start transition-colors hover:bg-sidebar-accent hover:text-sidebar-accent-foreground
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/components/AppSidebar.tsx:81:20', 'data-lov-name': 'NavLink', 'data-component-path': 'src/components/AppSidebar.tsx', 'data-component-line': '81', 'data-component-file': 'AppSidebar.tsx', 'data-component-name': 'NavLink', 'data-component-content': '%7B%7D', 'data-sidebar': 'menu-button', 'data-size': 'default', 'data-active': 'false', 'class': 'peer/menu-button flex w-full items-center gap-2 overflow-hidden rounded-md p-2 text-left outline-none ring-sidebar-ring transition-[width,height,padding] focus-visible:ring-2 active:bg-sidebar-accent active:text-sidebar-accent-foreground disabled:pointer-events-none disabled:opacity-50 group-has-[[data-sidebar=menu-action]]/menu-item:pr-8 aria-disabled:pointer-events-none aria-disabled:opacity-50 data-[active=true]:bg-sidebar-accent data-[active=true]:font-medium data-[active=true]:text-sidebar-accent-foreground data-[state=open]:hover:bg-sidebar-accent data-[state=open]:hover:text-sidebar-accent-foreground group-data-[collapsible=icon]:!size-8 group-data-[collapsible=icon]:!p-2 [&>span:last-child]:truncate [&>svg]:size-4 [&>svg]:shrink-0 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground h-8 text-sm w-full justify-start transition-colors hover:bg-sidebar-accent hover:text-sidebar-accent-foreground', 'href': '/reports'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     NavLink
  HTML:           <a data-lov-id="src/components/AppSidebar.tsx:81:20" data-lov-name="NavLink" data-component-path="src/components/AppSide
------------------------------------------------------------
Element 57:
  page_name:      customers
  tag_name:       svg
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'xmlns': 'http://www.w3.org/2000/svg', 'width': '24', 'height': '24', 'viewBox': '0 0 24 24', 'fill': 'none', 'stroke': 'currentColor', 'stroke-width': '2', 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'class': 'lucide lucide-file-text w-4 h-4', 'data-lov-id': 'src/components/AppSidebar.tsx:82:22', 'data-lov-name': 'item.icon', 'data-component-path': 'src/components/AppSidebar.tsx', 'data-component-line': '82', 'data-component-file': 'AppSidebar.tsx', 'data-component-name': 'item.icon', 'data-component-content': '%7B%22className%22%3A%22w-4%20h-4%22%7D'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     item.icon
  HTML:           <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" str
------------------------------------------------------------
Element 58:
  page_name:      customers
  tag_name:       path
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'d': 'M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"></path>
------------------------------------------------------------
Element 59:
  page_name:      customers
  tag_name:       path
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'d': 'M14 2v4a2 2 0 0 0 2 2h4'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <path d="M14 2v4a2 2 0 0 0 2 2h4"></path>
------------------------------------------------------------
Element 60:
  page_name:      customers
  tag_name:       path
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'d': 'M10 9H8'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <path d="M10 9H8"></path>
------------------------------------------------------------
Element 61:
  page_name:      customers
  tag_name:       path
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'d': 'M16 13H8'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <path d="M16 13H8"></path>
------------------------------------------------------------
Element 62:
  page_name:      customers
  tag_name:       path
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'d': 'M16 17H8'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <path d="M16 17H8"></path>
------------------------------------------------------------
Element 63:
  page_name:      customers
  tag_name:       span
  text:           Reports
  id:             
  class:          
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/components/AppSidebar.tsx:83:39', 'data-lov-name': 'span', 'data-component-path': 'src/components/AppSidebar.tsx', 'data-component-line': '83', 'data-component-file': 'AppSidebar.tsx', 'data-component-name': 'span', 'data-component-content': '%7B%7D'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     span
  HTML:           <span data-lov-id="src/components/AppSidebar.tsx:83:39" data-lov-name="span" data-component-path="src/components/AppSide
------------------------------------------------------------
Element 64:
  page_name:      customers
  tag_name:       li
  text:           Analytics
  id:             
  class:          group/menu-item relative
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/components/AppSidebar.tsx:79:16', 'data-lov-name': 'SidebarMenuItem', 'data-component-path': 'src/components/AppSidebar.tsx', 'data-component-line': '79', 'data-component-file': 'AppSidebar.tsx', 'data-component-name': 'SidebarMenuItem', 'data-component-content': '%7B%7D', 'data-sidebar': 'menu-item', 'class': 'group/menu-item relative'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     SidebarMenuItem
  HTML:           <li data-lov-id="src/components/AppSidebar.tsx:79:16" data-lov-name="SidebarMenuItem" data-component-path="src/component
------------------------------------------------------------
Element 65:
  page_name:      customers
  tag_name:       a
  text:           Analytics
  id:             
  class:          peer/menu-button flex w-full items-center gap-2 overflow-hidden rounded-md p-2 text-left outline-none ring-sidebar-ring transition-[width,height,padding] focus-visible:ring-2 active:bg-sidebar-accent active:text-sidebar-accent-foreground disabled:pointer-events-none disabled:opacity-50 group-has-[[data-sidebar=menu-action]]/menu-item:pr-8 aria-disabled:pointer-events-none aria-disabled:opacity-50 data-[active=true]:bg-sidebar-accent data-[active=true]:font-medium data-[active=true]:text-sidebar-accent-foreground data-[state=open]:hover:bg-sidebar-accent data-[state=open]:hover:text-sidebar-accent-foreground group-data-[collapsible=icon]:!size-8 group-data-[collapsible=icon]:!p-2 [&>span:last-child]:truncate [&>svg]:size-4 [&>svg]:shrink-0 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground h-8 text-sm w-full justify-start transition-colors hover:bg-sidebar-accent hover:text-sidebar-accent-foreground
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/components/AppSidebar.tsx:81:20', 'data-lov-name': 'NavLink', 'data-component-path': 'src/components/AppSidebar.tsx', 'data-component-line': '81', 'data-component-file': 'AppSidebar.tsx', 'data-component-name': 'NavLink', 'data-component-content': '%7B%7D', 'data-sidebar': 'menu-button', 'data-size': 'default', 'data-active': 'false', 'class': 'peer/menu-button flex w-full items-center gap-2 overflow-hidden rounded-md p-2 text-left outline-none ring-sidebar-ring transition-[width,height,padding] focus-visible:ring-2 active:bg-sidebar-accent active:text-sidebar-accent-foreground disabled:pointer-events-none disabled:opacity-50 group-has-[[data-sidebar=menu-action]]/menu-item:pr-8 aria-disabled:pointer-events-none aria-disabled:opacity-50 data-[active=true]:bg-sidebar-accent data-[active=true]:font-medium data-[active=true]:text-sidebar-accent-foreground data-[state=open]:hover:bg-sidebar-accent data-[state=open]:hover:text-sidebar-accent-foreground group-data-[collapsible=icon]:!size-8 group-data-[collapsible=icon]:!p-2 [&>span:last-child]:truncate [&>svg]:size-4 [&>svg]:shrink-0 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground h-8 text-sm w-full justify-start transition-colors hover:bg-sidebar-accent hover:text-sidebar-accent-foreground', 'href': '/analytics'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     NavLink
  HTML:           <a data-lov-id="src/components/AppSidebar.tsx:81:20" data-lov-name="NavLink" data-component-path="src/components/AppSide
------------------------------------------------------------
Element 66:
  page_name:      customers
  tag_name:       svg
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'xmlns': 'http://www.w3.org/2000/svg', 'width': '24', 'height': '24', 'viewBox': '0 0 24 24', 'fill': 'none', 'stroke': 'currentColor', 'stroke-width': '2', 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'class': 'lucide lucide-chart-column w-4 h-4', 'data-lov-id': 'src/components/AppSidebar.tsx:82:22', 'data-lov-name': 'item.icon', 'data-component-path': 'src/components/AppSidebar.tsx', 'data-component-line': '82', 'data-component-file': 'AppSidebar.tsx', 'data-component-name': 'item.icon', 'data-component-content': '%7B%22className%22%3A%22w-4%20h-4%22%7D'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     item.icon
  HTML:           <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" str
------------------------------------------------------------
Element 67:
  page_name:      customers
  tag_name:       path
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'d': 'M3 3v16a2 2 0 0 0 2 2h16'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <path d="M3 3v16a2 2 0 0 0 2 2h16"></path>
------------------------------------------------------------
Element 68:
  page_name:      customers
  tag_name:       path
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'d': 'M18 17V9'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <path d="M18 17V9"></path>
------------------------------------------------------------
Element 69:
  page_name:      customers
  tag_name:       path
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'d': 'M13 17V5'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <path d="M13 17V5"></path>
------------------------------------------------------------
Element 70:
  page_name:      customers
  tag_name:       path
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'d': 'M8 17v-3'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <path d="M8 17v-3"></path>
------------------------------------------------------------
Element 71:
  page_name:      customers
  tag_name:       span
  text:           Analytics
  id:             
  class:          
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/components/AppSidebar.tsx:83:39', 'data-lov-name': 'span', 'data-component-path': 'src/components/AppSidebar.tsx', 'data-component-line': '83', 'data-component-file': 'AppSidebar.tsx', 'data-component-name': 'span', 'data-component-content': '%7B%7D'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     span
  HTML:           <span data-lov-id="src/components/AppSidebar.tsx:83:39" data-lov-name="span" data-component-path="src/components/AppSide
------------------------------------------------------------
Element 72:
  page_name:      customers
  tag_name:       li
  text:           Settings
  id:             
  class:          group/menu-item relative
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/components/AppSidebar.tsx:79:16', 'data-lov-name': 'SidebarMenuItem', 'data-component-path': 'src/components/AppSidebar.tsx', 'data-component-line': '79', 'data-component-file': 'AppSidebar.tsx', 'data-component-name': 'SidebarMenuItem', 'data-component-content': '%7B%7D', 'data-sidebar': 'menu-item', 'class': 'group/menu-item relative'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     SidebarMenuItem
  HTML:           <li data-lov-id="src/components/AppSidebar.tsx:79:16" data-lov-name="SidebarMenuItem" data-component-path="src/component
------------------------------------------------------------
Element 73:
  page_name:      customers
  tag_name:       a
  text:           Settings
  id:             
  class:          peer/menu-button flex w-full items-center gap-2 overflow-hidden rounded-md p-2 text-left outline-none ring-sidebar-ring transition-[width,height,padding] focus-visible:ring-2 active:bg-sidebar-accent active:text-sidebar-accent-foreground disabled:pointer-events-none disabled:opacity-50 group-has-[[data-sidebar=menu-action]]/menu-item:pr-8 aria-disabled:pointer-events-none aria-disabled:opacity-50 data-[active=true]:bg-sidebar-accent data-[active=true]:font-medium data-[active=true]:text-sidebar-accent-foreground data-[state=open]:hover:bg-sidebar-accent data-[state=open]:hover:text-sidebar-accent-foreground group-data-[collapsible=icon]:!size-8 group-data-[collapsible=icon]:!p-2 [&>span:last-child]:truncate [&>svg]:size-4 [&>svg]:shrink-0 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground h-8 text-sm w-full justify-start transition-colors hover:bg-sidebar-accent hover:text-sidebar-accent-foreground
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/components/AppSidebar.tsx:81:20', 'data-lov-name': 'NavLink', 'data-component-path': 'src/components/AppSidebar.tsx', 'data-component-line': '81', 'data-component-file': 'AppSidebar.tsx', 'data-component-name': 'NavLink', 'data-component-content': '%7B%7D', 'data-sidebar': 'menu-button', 'data-size': 'default', 'data-active': 'false', 'class': 'peer/menu-button flex w-full items-center gap-2 overflow-hidden rounded-md p-2 text-left outline-none ring-sidebar-ring transition-[width,height,padding] focus-visible:ring-2 active:bg-sidebar-accent active:text-sidebar-accent-foreground disabled:pointer-events-none disabled:opacity-50 group-has-[[data-sidebar=menu-action]]/menu-item:pr-8 aria-disabled:pointer-events-none aria-disabled:opacity-50 data-[active=true]:bg-sidebar-accent data-[active=true]:font-medium data-[active=true]:text-sidebar-accent-foreground data-[state=open]:hover:bg-sidebar-accent data-[state=open]:hover:text-sidebar-accent-foreground group-data-[collapsible=icon]:!size-8 group-data-[collapsible=icon]:!p-2 [&>span:last-child]:truncate [&>svg]:size-4 [&>svg]:shrink-0 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground h-8 text-sm w-full justify-start transition-colors hover:bg-sidebar-accent hover:text-sidebar-accent-foreground', 'href': '/settings'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     NavLink
  HTML:           <a data-lov-id="src/components/AppSidebar.tsx:81:20" data-lov-name="NavLink" data-component-path="src/components/AppSide
------------------------------------------------------------
Element 74:
  page_name:      customers
  tag_name:       svg
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'xmlns': 'http://www.w3.org/2000/svg', 'width': '24', 'height': '24', 'viewBox': '0 0 24 24', 'fill': 'none', 'stroke': 'currentColor', 'stroke-width': '2', 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'class': 'lucide lucide-settings w-4 h-4', 'data-lov-id': 'src/components/AppSidebar.tsx:82:22', 'data-lov-name': 'item.icon', 'data-component-path': 'src/components/AppSidebar.tsx', 'data-component-line': '82', 'data-component-file': 'AppSidebar.tsx', 'data-component-name': 'item.icon', 'data-component-content': '%7B%22className%22%3A%22w-4%20h-4%22%7D'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     item.icon
  HTML:           <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" str
------------------------------------------------------------
Element 75:
  page_name:      customers
  tag_name:       path
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'d': 'M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0
------------------------------------------------------------
Element 76:
  page_name:      customers
  tag_name:       circle
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'cx': '12', 'cy': '12', 'r': '3'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <circle cx="12" cy="12" r="3"></circle>
------------------------------------------------------------
Element 77:
  page_name:      customers
  tag_name:       span
  text:           Settings
  id:             
  class:          
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/components/AppSidebar.tsx:83:39', 'data-lov-name': 'span', 'data-component-path': 'src/components/AppSidebar.tsx', 'data-component-line': '83', 'data-component-file': 'AppSidebar.tsx', 'data-component-name': 'span', 'data-component-content': '%7B%7D'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     span
  HTML:           <span data-lov-id="src/components/AppSidebar.tsx:83:39" data-lov-name="span" data-component-path="src/components/AppSide
------------------------------------------------------------
Element 78:
  page_name:      customers
  tag_name:       div
  text:           Toggle SidebarJohn DoeCustomersManage your customer relationships and accountsExportAdd CustomerFiltersCustomer List3 customers foundCustomerAccount TypeBalanceStatusJoin DateActionsSJSarah Johnsonsarah.johnson@email.comPremium$145,000Active2023-01-15MCMichael Chenmichael.chen@email.comStandard$52,000Active2023-03-22EDEmma Davisemma.davis@email.comPremium$89,000Active2022-11-08
  id:             
  class:          flex-1 flex flex-col
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/components/Layout.tsx:12:8', 'data-lov-name': 'div', 'data-component-path': 'src/components/Layout.tsx', 'data-component-line': '12', 'data-component-file': 'Layout.tsx', 'data-component-name': 'div', 'data-component-content': '%7B%22className%22%3A%22flex-1%20flex%20flex-col%22%7D', 'class': 'flex-1 flex flex-col'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     div
  HTML:           <div data-lov-id="src/components/Layout.tsx:12:8" data-lov-name="div" data-component-path="src/components/Layout.tsx" da
------------------------------------------------------------
Element 79:
  page_name:      customers
  tag_name:       header
  text:           Toggle SidebarJohn Doe
  id:             
  class:          border-b bg-white px-6 py-4
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/components/Header.tsx:18:4', 'data-lov-name': 'header', 'data-component-path': 'src/components/Header.tsx', 'data-component-line': '18', 'data-component-file': 'Header.tsx', 'data-component-name': 'header', 'data-component-content': '%7B%22className%22%3A%22border-b%20bg-white%20px-6%20py-4%22%7D', 'class': 'border-b bg-white px-6 py-4'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     header
  HTML:           <header data-lov-id="src/components/Header.tsx:18:4" data-lov-name="header" data-component-path="src/components/Header.t
------------------------------------------------------------
Element 80:
  page_name:      customers
  tag_name:       div
  text:           Toggle SidebarJohn Doe
  id:             
  class:          flex items-center justify-between
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/components/Header.tsx:19:6', 'data-lov-name': 'div', 'data-component-path': 'src/components/Header.tsx', 'data-component-line': '19', 'data-component-file': 'Header.tsx', 'data-component-name': 'div', 'data-component-content': '%7B%22className%22%3A%22flex%20items-center%20justify-between%22%7D', 'class': 'flex items-center justify-between'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     div
  HTML:           <div data-lov-id="src/components/Header.tsx:19:6" data-lov-name="div" data-component-path="src/components/Header.tsx" da
------------------------------------------------------------
Element 81:
  page_name:      customers
  tag_name:       div
  text:           Toggle Sidebar
  id:             
  class:          flex items-center gap-4
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/components/Header.tsx:20:8', 'data-lov-name': 'div', 'data-component-path': 'src/components/Header.tsx', 'data-component-line': '20', 'data-component-file': 'Header.tsx', 'data-component-name': 'div', 'data-component-content': '%7B%22className%22%3A%22flex%20items-center%20gap-4%22%7D', 'class': 'flex items-center gap-4'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     div
  HTML:           <div data-lov-id="src/components/Header.tsx:20:8" data-lov-name="div" data-component-path="src/components/Header.tsx" da
------------------------------------------------------------
Element 82:
  page_name:      customers
  tag_name:       button
  text:           Toggle Sidebar
  id:             
  class:          inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0 hover:bg-accent hover:text-accent-foreground h-7 w-7
  value:          
  placeholder:    
  type:           submit
  attributes:     {'data-lov-id': 'src/components/Header.tsx:21:10', 'data-lov-name': 'SidebarTrigger', 'data-component-path': 'src/components/Header.tsx', 'data-component-line': '21', 'data-component-file': 'Header.tsx', 'data-component-name': 'SidebarTrigger', 'data-component-content': '%7B%7D', 'class': 'inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0 hover:bg-accent hover:text-accent-foreground h-7 w-7', 'data-sidebar': 'trigger'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     Toggle Sidebar
  HTML:           <button data-lov-id="src/components/Header.tsx:21:10" data-lov-name="SidebarTrigger" data-component-path="src/components
------------------------------------------------------------
Element 83:
  page_name:      customers
  tag_name:       svg
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'xmlns': 'http://www.w3.org/2000/svg', 'width': '24', 'height': '24', 'viewBox': '0 0 24 24', 'fill': 'none', 'stroke': 'currentColor', 'stroke-width': '2', 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'class': 'lucide lucide-panel-left', 'data-lov-id': 'src/components/ui/sidebar.tsx:279:6', 'data-lov-name': 'PanelLeft', 'data-component-path': 'src/components/ui/sidebar.tsx', 'data-component-line': '279', 'data-component-file': 'sidebar.tsx', 'data-component-name': 'PanelLeft', 'data-component-content': '%7B%7D'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     PanelLeft
  HTML:           <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" str
------------------------------------------------------------
Element 84:
  page_name:      customers
  tag_name:       rect
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'width': '18', 'height': '18', 'x': '3', 'y': '3', 'rx': '2'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <rect width="18" height="18" x="3" y="3" rx="2"></rect>
------------------------------------------------------------
Element 85:
  page_name:      customers
  tag_name:       path
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'d': 'M9 3v18'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <path d="M9 3v18"></path>
------------------------------------------------------------
Element 86:
  page_name:      customers
  tag_name:       span
  text:           Toggle Sidebar
  id:             
  class:          sr-only
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/components/ui/sidebar.tsx:280:6', 'data-lov-name': 'span', 'data-component-path': 'src/components/ui/sidebar.tsx', 'data-component-line': '280', 'data-component-file': 'sidebar.tsx', 'data-component-name': 'span', 'data-component-content': '%7B%22text%22%3A%22Toggle%20Sidebar%22%2C%22className%22%3A%22sr-only%22%7D', 'class': 'sr-only'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     span
  HTML:           <span data-lov-id="src/components/ui/sidebar.tsx:280:6" data-lov-name="span" data-component-path="src/components/ui/side
------------------------------------------------------------
Element 87:
  page_name:      customers
  tag_name:       div
  text:           John Doe
  id:             
  class:          flex items-center gap-4
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/components/Header.tsx:24:8', 'data-lov-name': 'div', 'data-component-path': 'src/components/Header.tsx', 'data-component-line': '24', 'data-component-file': 'Header.tsx', 'data-component-name': 'div', 'data-component-content': '%7B%22className%22%3A%22flex%20items-center%20gap-4%22%7D', 'class': 'flex items-center gap-4'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     div
  HTML:           <div data-lov-id="src/components/Header.tsx:24:8" data-lov-name="div" data-component-path="src/components/Header.tsx" da
------------------------------------------------------------
Element 88:
  page_name:      customers
  tag_name:       button
  text:           
  id:             
  class:          inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0 hover:bg-accent hover:text-accent-foreground h-10 w-10 relative
  value:          
  placeholder:    
  type:           submit
  attributes:     {'data-lov-id': 'src/components/Header.tsx:25:10', 'data-lov-name': 'Button', 'data-component-path': 'src/components/Header.tsx', 'data-component-line': '25', 'data-component-file': 'Header.tsx', 'data-component-name': 'Button', 'data-component-content': '%7B%22className%22%3A%22relative%22%7D', 'class': 'inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0 hover:bg-accent hover:text-accent-foreground h-10 w-10 relative'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     Button
  HTML:           <button data-lov-id="src/components/Header.tsx:25:10" data-lov-name="Button" data-component-path="src/components/Header.
------------------------------------------------------------
Element 89:
  page_name:      customers
  tag_name:       svg
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'xmlns': 'http://www.w3.org/2000/svg', 'width': '24', 'height': '24', 'viewBox': '0 0 24 24', 'fill': 'none', 'stroke': 'currentColor', 'stroke-width': '2', 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'class': 'lucide lucide-bell w-4 h-4', 'data-lov-id': 'src/components/Header.tsx:26:12', 'data-lov-name': 'Bell', 'data-component-path': 'src/components/Header.tsx', 'data-component-line': '26', 'data-component-file': 'Header.tsx', 'data-component-name': 'Bell', 'data-component-content': '%7B%22className%22%3A%22w-4%20h-4%22%7D'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     Bell
  HTML:           <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" str
------------------------------------------------------------
Element 90:
  page_name:      customers
  tag_name:       path
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'d': 'M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"></path>
------------------------------------------------------------
Element 91:
  page_name:      customers
  tag_name:       path
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'d': 'M10.3 21a1.94 1.94 0 0 0 3.4 0'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"></path>
------------------------------------------------------------
Element 92:
  page_name:      customers
  tag_name:       span
  text:           
  id:             
  class:          absolute -top-1 -right-1 w-2 h-2 bg-red-500 rounded-full
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/components/Header.tsx:27:12', 'data-lov-name': 'span', 'data-component-path': 'src/components/Header.tsx', 'data-component-line': '27', 'data-component-file': 'Header.tsx', 'data-component-name': 'span', 'data-component-content': '%7B%22className%22%3A%22absolute%20-top-1%20-right-1%20w-2%20h-2%20bg-red-500%20rounded-full%22%7D', 'class': 'absolute -top-1 -right-1 w-2 h-2 bg-red-500 rounded-full'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     span
  HTML:           <span data-lov-id="src/components/Header.tsx:27:12" data-lov-name="span" data-component-path="src/components/Header.tsx"
------------------------------------------------------------
Element 93:
  page_name:      customers
  tag_name:       button
  text:           John Doe
  id:             radix-:r0:
  class:          justify-center whitespace-nowrap rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0 hover:bg-accent hover:text-accent-foreground h-10 px-4 py-2 flex items-center gap-2
  value:          
  placeholder:    
  type:           button
  attributes:     {'data-lov-id': 'src/components/Header.tsx:32:14', 'data-lov-name': 'Button', 'data-component-path': 'src/components/Header.tsx', 'data-component-line': '32', 'data-component-file': 'Header.tsx', 'data-component-name': 'Button', 'data-component-content': '%7B%22className%22%3A%22flex%20items-center%20gap-2%22%7D', 'class': 'justify-center whitespace-nowrap rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0 hover:bg-accent hover:text-accent-foreground h-10 px-4 py-2 flex items-center gap-2', 'type': 'button', 'id': 'radix-:r0:', 'aria-haspopup': 'menu', 'aria-expanded': 'false', 'data-state': 'closed'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     John Doe
  HTML:           <button data-lov-id="src/components/Header.tsx:32:14" data-lov-name="Button" data-component-path="src/components/Header.
------------------------------------------------------------
Element 94:
  page_name:      customers
  tag_name:       span
  text:           
  id:             
  class:          relative flex shrink-0 overflow-hidden rounded-full w-8 h-8
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/components/Header.tsx:33:16', 'data-lov-name': 'Avatar', 'data-component-path': 'src/components/Header.tsx', 'data-component-line': '33', 'data-component-file': 'Header.tsx', 'data-component-name': 'Avatar', 'data-component-content': '%7B%22className%22%3A%22w-8%20h-8%22%7D', 'class': 'relative flex shrink-0 overflow-hidden rounded-full w-8 h-8'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     Avatar
  HTML:           <span data-lov-id="src/components/Header.tsx:33:16" data-lov-name="Avatar" data-component-path="src/components/Header.ts
------------------------------------------------------------
Element 95:
  page_name:      customers
  tag_name:       img
  text:           
  id:             
  class:          aspect-square h-full w-full
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/components/Header.tsx:34:18', 'data-lov-name': 'AvatarImage', 'data-component-path': 'src/components/Header.tsx', 'data-component-line': '34', 'data-component-file': 'Header.tsx', 'data-component-name': 'AvatarImage', 'data-component-content': '%7B%7D', 'class': 'aspect-square h-full w-full', 'src': 'https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=32&h=32&fit=crop&crop=face'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     AvatarImage
  HTML:           <img data-lov-id="src/components/Header.tsx:34:18" data-lov-name="AvatarImage" data-component-path="src/components/Heade
------------------------------------------------------------
Element 96:
  page_name:      customers
  tag_name:       span
  text:           John Doe
  id:             
  class:          hidden md:inline
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/components/Header.tsx:37:16', 'data-lov-name': 'span', 'data-component-path': 'src/components/Header.tsx', 'data-component-line': '37', 'data-component-file': 'Header.tsx', 'data-component-name': 'span', 'data-component-content': '%7B%22text%22%3A%22John%20Doe%22%2C%22className%22%3A%22hidden%20md%3Ainline%22%7D', 'class': 'hidden md:inline'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     span
  HTML:           <span data-lov-id="src/components/Header.tsx:37:16" data-lov-name="span" data-component-path="src/components/Header.tsx"
------------------------------------------------------------
Element 97:
  page_name:      customers
  tag_name:       main
  text:           CustomersManage your customer relationships and accountsExportAdd CustomerFiltersCustomer List3 customers foundCustomerAccount TypeBalanceStatusJoin DateActionsSJSarah Johnsonsarah.johnson@email.comPremium$145,000Active2023-01-15MCMichael Chenmichael.chen@email.comStandard$52,000Active2023-03-22EDEmma Davisemma.davis@email.comPremium$89,000Active2022-11-08
  id:             
  class:          flex-1 p-6
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/components/Layout.tsx:14:10', 'data-lov-name': 'main', 'data-component-path': 'src/components/Layout.tsx', 'data-component-line': '14', 'data-component-file': 'Layout.tsx', 'data-component-name': 'main', 'data-component-content': '%7B%22className%22%3A%22flex-1%20p-6%22%7D', 'class': 'flex-1 p-6'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     main
  HTML:           <main data-lov-id="src/components/Layout.tsx:14:10" data-lov-name="main" data-component-path="src/components/Layout.tsx"
------------------------------------------------------------
Element 98:
  page_name:      customers
  tag_name:       div
  text:           CustomersManage your customer relationships and accountsExportAdd CustomerFiltersCustomer List3 customers foundCustomerAccount TypeBalanceStatusJoin DateActionsSJSarah Johnsonsarah.johnson@email.comPremium$145,000Active2023-01-15MCMichael Chenmichael.chen@email.comStandard$52,000Active2023-03-22EDEmma Davisemma.davis@email.comPremium$89,000Active2022-11-08
  id:             
  class:          space-y-6
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Customers.tsx:163:4', 'data-lov-name': 'div', 'data-component-path': 'src/pages/Customers.tsx', 'data-component-line': '163', 'data-component-file': 'Customers.tsx', 'data-component-name': 'div', 'data-component-content': '%7B%22className%22%3A%22space-y-6%22%7D', 'class': 'space-y-6'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     div
  HTML:           <div data-lov-id="src/pages/Customers.tsx:163:4" data-lov-name="div" data-component-path="src/pages/Customers.tsx" data-
------------------------------------------------------------
Element 99:
  page_name:      customers
  tag_name:       div
  text:           CustomersManage your customer relationships and accountsExportAdd Customer
  id:             
  class:          flex justify-between items-center
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Customers.tsx:164:6', 'data-lov-name': 'div', 'data-component-path': 'src/pages/Customers.tsx', 'data-component-line': '164', 'data-component-file': 'Customers.tsx', 'data-component-name': 'div', 'data-component-content': '%7B%22className%22%3A%22flex%20justify-between%20items-center%22%7D', 'class': 'flex justify-between items-center'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     div
  HTML:           <div data-lov-id="src/pages/Customers.tsx:164:6" data-lov-name="div" data-component-path="src/pages/Customers.tsx" data-
------------------------------------------------------------
Element 100:
  page_name:      customers
  tag_name:       div
  text:           CustomersManage your customer relationships and accounts
  id:             
  class:          
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Customers.tsx:165:8', 'data-lov-name': 'div', 'data-component-path': 'src/pages/Customers.tsx', 'data-component-line': '165', 'data-component-file': 'Customers.tsx', 'data-component-name': 'div', 'data-component-content': '%7B%7D'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     div
  HTML:           <div data-lov-id="src/pages/Customers.tsx:165:8" data-lov-name="div" data-component-path="src/pages/Customers.tsx" data-
------------------------------------------------------------
Element 101:
  page_name:      customers
  tag_name:       h1
  text:           Customers
  id:             
  class:          text-3xl font-bold text-gray-900
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Customers.tsx:166:10', 'data-lov-name': 'h1', 'data-component-path': 'src/pages/Customers.tsx', 'data-component-line': '166', 'data-component-file': 'Customers.tsx', 'data-component-name': 'h1', 'data-component-content': '%7B%22text%22%3A%22Customers%22%2C%22className%22%3A%22text-3xl%20font-bold%20text-gray-900%22%7D', 'class': 'text-3xl font-bold text-gray-900'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     h1
  HTML:           <h1 data-lov-id="src/pages/Customers.tsx:166:10" data-lov-name="h1" data-component-path="src/pages/Customers.tsx" data-c
------------------------------------------------------------
Element 102:
  page_name:      customers
  tag_name:       p
  text:           Manage your customer relationships and accounts
  id:             
  class:          text-gray-600 mt-2
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Customers.tsx:167:10', 'data-lov-name': 'p', 'data-component-path': 'src/pages/Customers.tsx', 'data-component-line': '167', 'data-component-file': 'Customers.tsx', 'data-component-name': 'p', 'data-component-content': '%7B%22text%22%3A%22Manage%20your%20customer%20relationships%20and%20accounts%22%2C%22className%22%3A%22text-gray-600%20mt-2%22%7D', 'class': 'text-gray-600 mt-2'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     p
  HTML:           <p data-lov-id="src/pages/Customers.tsx:167:10" data-lov-name="p" data-component-path="src/pages/Customers.tsx" data-com
------------------------------------------------------------
Element 103:
  page_name:      customers
  tag_name:       div
  text:           ExportAdd Customer
  id:             
  class:          flex gap-2
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Customers.tsx:169:8', 'data-lov-name': 'div', 'data-component-path': 'src/pages/Customers.tsx', 'data-component-line': '169', 'data-component-file': 'Customers.tsx', 'data-component-name': 'div', 'data-component-content': '%7B%22className%22%3A%22flex%20gap-2%22%7D', 'class': 'flex gap-2'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     div
  HTML:           <div data-lov-id="src/pages/Customers.tsx:169:8" data-lov-name="div" data-component-path="src/pages/Customers.tsx" data-
------------------------------------------------------------
Element 104:
  page_name:      customers
  tag_name:       button
  text:           Export
  id:             
  class:          justify-center whitespace-nowrap rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0 border border-input bg-background hover:bg-accent hover:text-accent-foreground h-10 px-4 py-2 flex items-center gap-2
  value:          
  placeholder:    
  type:           submit
  attributes:     {'data-lov-id': 'src/pages/Customers.tsx:170:10', 'data-lov-name': 'Button', 'data-component-path': 'src/pages/Customers.tsx', 'data-component-line': '170', 'data-component-file': 'Customers.tsx', 'data-component-name': 'Button', 'data-component-content': '%7B%22text%22%3A%22Export%22%2C%22className%22%3A%22flex%20items-center%20gap-2%22%7D', 'class': 'justify-center whitespace-nowrap rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0 border border-input bg-background hover:bg-accent hover:text-accent-foreground h-10 px-4 py-2 flex items-center gap-2'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     Export
  HTML:           <button data-lov-id="src/pages/Customers.tsx:170:10" data-lov-name="Button" data-component-path="src/pages/Customers.tsx
------------------------------------------------------------
Element 105:
  page_name:      customers
  tag_name:       svg
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'xmlns': 'http://www.w3.org/2000/svg', 'width': '24', 'height': '24', 'viewBox': '0 0 24 24', 'fill': 'none', 'stroke': 'currentColor', 'stroke-width': '2', 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'class': 'lucide lucide-download w-4 h-4', 'data-lov-id': 'src/pages/Customers.tsx:171:12', 'data-lov-name': 'Download', 'data-component-path': 'src/pages/Customers.tsx', 'data-component-line': '171', 'data-component-file': 'Customers.tsx', 'data-component-name': 'Download', 'data-component-content': '%7B%22className%22%3A%22w-4%20h-4%22%7D'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     Download
  HTML:           <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" str
------------------------------------------------------------
Element 106:
  page_name:      customers
  tag_name:       path
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'d': 'M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
------------------------------------------------------------
Element 107:
  page_name:      customers
  tag_name:       polyline
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'points': '7 10 12 15 17 10'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <polyline points="7 10 12 15 17 10"></polyline>
------------------------------------------------------------
Element 108:
  page_name:      customers
  tag_name:       line
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'x1': '12', 'x2': '12', 'y1': '15', 'y2': '3'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <line x1="12" x2="12" y1="15" y2="3"></line>
------------------------------------------------------------
Element 109:
  page_name:      customers
  tag_name:       button
  text:           Add Customer
  id:             
  class:          justify-center whitespace-nowrap rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0 bg-primary text-primary-foreground hover:bg-primary/90 h-10 px-4 py-2 flex items-center gap-2
  value:          
  placeholder:    
  type:           button
  attributes:     {'data-lov-id': 'src/pages/Customers.tsx:176:14', 'data-lov-name': 'Button', 'data-component-path': 'src/pages/Customers.tsx', 'data-component-line': '176', 'data-component-file': 'Customers.tsx', 'data-component-name': 'Button', 'data-component-content': '%7B%22text%22%3A%22Add%20Customer%22%2C%22className%22%3A%22flex%20items-center%20gap-2%22%7D', 'class': 'justify-center whitespace-nowrap rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0 bg-primary text-primary-foreground hover:bg-primary/90 h-10 px-4 py-2 flex items-center gap-2', 'type': 'button', 'aria-haspopup': 'dialog', 'aria-expanded': 'false', 'aria-controls': 'radix-:r2:', 'data-state': 'closed'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     Add Customer
  HTML:           <button data-lov-id="src/pages/Customers.tsx:176:14" data-lov-name="Button" data-component-path="src/pages/Customers.tsx
------------------------------------------------------------
Element 110:
  page_name:      customers
  tag_name:       svg
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'xmlns': 'http://www.w3.org/2000/svg', 'width': '24', 'height': '24', 'viewBox': '0 0 24 24', 'fill': 'none', 'stroke': 'currentColor', 'stroke-width': '2', 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'class': 'lucide lucide-plus w-4 h-4', 'data-lov-id': 'src/pages/Customers.tsx:177:16', 'data-lov-name': 'Plus', 'data-component-path': 'src/pages/Customers.tsx', 'data-component-line': '177', 'data-component-file': 'Customers.tsx', 'data-component-name': 'Plus', 'data-component-content': '%7B%22className%22%3A%22w-4%20h-4%22%7D'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     Plus
  HTML:           <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" str
------------------------------------------------------------
Element 111:
  page_name:      customers
  tag_name:       path
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'d': 'M5 12h14'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <path d="M5 12h14"></path>
------------------------------------------------------------
Element 112:
  page_name:      customers
  tag_name:       path
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'d': 'M12 5v14'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <path d="M12 5v14"></path>
------------------------------------------------------------
Element 113:
  page_name:      customers
  tag_name:       div
  text:           Filters
  id:             
  class:          rounded-lg border bg-card text-card-foreground shadow-sm
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Customers.tsx:198:6', 'data-lov-name': 'Card', 'data-component-path': 'src/pages/Customers.tsx', 'data-component-line': '198', 'data-component-file': 'Customers.tsx', 'data-component-name': 'Card', 'data-component-content': '%7B%7D', 'class': 'rounded-lg border bg-card text-card-foreground shadow-sm'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     Card
  HTML:           <div data-lov-id="src/pages/Customers.tsx:198:6" data-lov-name="Card" data-component-path="src/pages/Customers.tsx" data
------------------------------------------------------------
Element 114:
  page_name:      customers
  tag_name:       div
  text:           Filters
  id:             
  class:          p-6 pt-6
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Customers.tsx:199:8', 'data-lov-name': 'CardContent', 'data-component-path': 'src/pages/Customers.tsx', 'data-component-line': '199', 'data-component-file': 'Customers.tsx', 'data-component-name': 'CardContent', 'data-component-content': '%7B%22className%22%3A%22pt-6%22%7D', 'class': 'p-6 pt-6'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     CardContent
  HTML:           <div data-lov-id="src/pages/Customers.tsx:199:8" data-lov-name="CardContent" data-component-path="src/pages/Customers.ts
------------------------------------------------------------
Element 115:
  page_name:      customers
  tag_name:       div
  text:           Filters
  id:             
  class:          flex gap-4
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Customers.tsx:200:10', 'data-lov-name': 'div', 'data-component-path': 'src/pages/Customers.tsx', 'data-component-line': '200', 'data-component-file': 'Customers.tsx', 'data-component-name': 'div', 'data-component-content': '%7B%22className%22%3A%22flex%20gap-4%22%7D', 'class': 'flex gap-4'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     div
  HTML:           <div data-lov-id="src/pages/Customers.tsx:200:10" data-lov-name="div" data-component-path="src/pages/Customers.tsx" data
------------------------------------------------------------
Element 116:
  page_name:      customers
  tag_name:       div
  text:           
  id:             
  class:          relative flex-1
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Customers.tsx:201:12', 'data-lov-name': 'div', 'data-component-path': 'src/pages/Customers.tsx', 'data-component-line': '201', 'data-component-file': 'Customers.tsx', 'data-component-name': 'div', 'data-component-content': '%7B%22className%22%3A%22relative%20flex-1%22%7D', 'class': 'relative flex-1'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     div
  HTML:           <div data-lov-id="src/pages/Customers.tsx:201:12" data-lov-name="div" data-component-path="src/pages/Customers.tsx" data
------------------------------------------------------------
Element 117:
  page_name:      customers
  tag_name:       svg
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'xmlns': 'http://www.w3.org/2000/svg', 'width': '24', 'height': '24', 'viewBox': '0 0 24 24', 'fill': 'none', 'stroke': 'currentColor', 'stroke-width': '2', 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'class': 'lucide lucide-search absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground w-4 h-4', 'data-lov-id': 'src/pages/Customers.tsx:202:14', 'data-lov-name': 'Search', 'data-component-path': 'src/pages/Customers.tsx', 'data-component-line': '202', 'data-component-file': 'Customers.tsx', 'data-component-name': 'Search', 'data-component-content': '%7B%22className%22%3A%22absolute%20left-3%20top-1%2F2%20transform%20-translate-y-1%2F2%20text-muted-foreground%20w-4%20h-4%22%7D'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     Search
  HTML:           <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" str
------------------------------------------------------------
Element 118:
  page_name:      customers
  tag_name:       circle
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'cx': '11', 'cy': '11', 'r': '8'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <circle cx="11" cy="11" r="8"></circle>
------------------------------------------------------------
Element 119:
  page_name:      customers
  tag_name:       path
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'d': 'm21 21-4.3-4.3'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <path d="m21 21-4.3-4.3"></path>
------------------------------------------------------------
Element 120:
  page_name:      customers
  tag_name:       input
  text:           
  id:             
  class:          flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-base ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium file:text-foreground placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 md:text-sm pl-10
  value:          
  placeholder:    Search customers...
  type:           text
  attributes:     {'data-lov-id': 'src/pages/Customers.tsx:203:14', 'data-lov-name': 'Input', 'data-component-path': 'src/pages/Customers.tsx', 'data-component-line': '203', 'data-component-file': 'Customers.tsx', 'data-component-name': 'Input', 'data-component-content': '%7B%22placeholder%22%3A%22Search%20customers...%22%2C%22className%22%3A%22pl-10%22%7D', 'class': 'flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-base ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium file:text-foreground placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 md:text-sm pl-10', 'placeholder': 'Search customers...', 'value': ''}
  enable?         True
  visible?        True
  editable?       True
  label_text:     Search customers...
  HTML:           <input data-lov-id="src/pages/Customers.tsx:203:14" data-lov-name="Input" data-component-path="src/pages/Customers.tsx" 
------------------------------------------------------------
Element 121:
  page_name:      customers
  tag_name:       button
  text:           Filters
  id:             
  class:          justify-center whitespace-nowrap rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0 border border-input bg-background hover:bg-accent hover:text-accent-foreground h-10 px-4 py-2 flex items-center gap-2
  value:          
  placeholder:    
  type:           submit
  attributes:     {'data-lov-id': 'src/pages/Customers.tsx:210:12', 'data-lov-name': 'Button', 'data-component-path': 'src/pages/Customers.tsx', 'data-component-line': '210', 'data-component-file': 'Customers.tsx', 'data-component-name': 'Button', 'data-component-content': '%7B%22text%22%3A%22Filters%22%2C%22className%22%3A%22flex%20items-center%20gap-2%22%7D', 'class': 'justify-center whitespace-nowrap rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0 border border-input bg-background hover:bg-accent hover:text-accent-foreground h-10 px-4 py-2 flex items-center gap-2'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     Filters
  HTML:           <button data-lov-id="src/pages/Customers.tsx:210:12" data-lov-name="Button" data-component-path="src/pages/Customers.tsx
------------------------------------------------------------
Element 122:
  page_name:      customers
  tag_name:       svg
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'xmlns': 'http://www.w3.org/2000/svg', 'width': '24', 'height': '24', 'viewBox': '0 0 24 24', 'fill': 'none', 'stroke': 'currentColor', 'stroke-width': '2', 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'class': 'lucide lucide-filter w-4 h-4', 'data-lov-id': 'src/pages/Customers.tsx:211:14', 'data-lov-name': 'Filter', 'data-component-path': 'src/pages/Customers.tsx', 'data-component-line': '211', 'data-component-file': 'Customers.tsx', 'data-component-name': 'Filter', 'data-component-content': '%7B%22className%22%3A%22w-4%20h-4%22%7D'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     Filter
  HTML:           <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" str
------------------------------------------------------------
Element 123:
  page_name:      customers
  tag_name:       polygon
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'points': '22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"></polygon>
------------------------------------------------------------
Element 124:
  page_name:      customers
  tag_name:       div
  text:           Customer List3 customers foundCustomerAccount TypeBalanceStatusJoin DateActionsSJSarah Johnsonsarah.johnson@email.comPremium$145,000Active2023-01-15MCMichael Chenmichael.chen@email.comStandard$52,000Active2023-03-22EDEmma Davisemma.davis@email.comPremium$89,000Active2022-11-08
  id:             
  class:          rounded-lg border bg-card text-card-foreground shadow-sm
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Customers.tsx:219:6', 'data-lov-name': 'Card', 'data-component-path': 'src/pages/Customers.tsx', 'data-component-line': '219', 'data-component-file': 'Customers.tsx', 'data-component-name': 'Card', 'data-component-content': '%7B%7D', 'class': 'rounded-lg border bg-card text-card-foreground shadow-sm'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     Card
  HTML:           <div data-lov-id="src/pages/Customers.tsx:219:6" data-lov-name="Card" data-component-path="src/pages/Customers.tsx" data
------------------------------------------------------------
Element 125:
  page_name:      customers
  tag_name:       div
  text:           Customer List3 customers found
  id:             
  class:          flex flex-col space-y-1.5 p-6
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Customers.tsx:220:8', 'data-lov-name': 'CardHeader', 'data-component-path': 'src/pages/Customers.tsx', 'data-component-line': '220', 'data-component-file': 'Customers.tsx', 'data-component-name': 'CardHeader', 'data-component-content': '%7B%7D', 'class': 'flex flex-col space-y-1.5 p-6'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     CardHeader
  HTML:           <div data-lov-id="src/pages/Customers.tsx:220:8" data-lov-name="CardHeader" data-component-path="src/pages/Customers.tsx
------------------------------------------------------------
Element 126:
  page_name:      customers
  tag_name:       h3
  text:           Customer List
  id:             
  class:          text-2xl font-semibold leading-none tracking-tight
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Customers.tsx:221:10', 'data-lov-name': 'CardTitle', 'data-component-path': 'src/pages/Customers.tsx', 'data-component-line': '221', 'data-component-file': 'Customers.tsx', 'data-component-name': 'CardTitle', 'data-component-content': '%7B%22text%22%3A%22Customer%20List%22%7D', 'class': 'text-2xl font-semibold leading-none tracking-tight'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     CardTitle
  HTML:           <h3 data-lov-id="src/pages/Customers.tsx:221:10" data-lov-name="CardTitle" data-component-path="src/pages/Customers.tsx"
------------------------------------------------------------
Element 127:
  page_name:      customers
  tag_name:       p
  text:           3 customers found
  id:             
  class:          text-sm text-muted-foreground
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Customers.tsx:222:10', 'data-lov-name': 'CardDescription', 'data-component-path': 'src/pages/Customers.tsx', 'data-component-line': '222', 'data-component-file': 'Customers.tsx', 'data-component-name': 'CardDescription', 'data-component-content': '%7B%22text%22%3A%22customers%20found%22%7D', 'class': 'text-sm text-muted-foreground'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     CardDescription
  HTML:           <p data-lov-id="src/pages/Customers.tsx:222:10" data-lov-name="CardDescription" data-component-path="src/pages/Customers
------------------------------------------------------------
Element 128:
  page_name:      customers
  tag_name:       div
  text:           CustomerAccount TypeBalanceStatusJoin DateActionsSJSarah Johnsonsarah.johnson@email.comPremium$145,000Active2023-01-15MCMichael Chenmichael.chen@email.comStandard$52,000Active2023-03-22EDEmma Davisemma.davis@email.comPremium$89,000Active2022-11-08
  id:             
  class:          p-6 pt-0
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Customers.tsx:226:8', 'data-lov-name': 'CardContent', 'data-component-path': 'src/pages/Customers.tsx', 'data-component-line': '226', 'data-component-file': 'Customers.tsx', 'data-component-name': 'CardContent', 'data-component-content': '%7B%7D', 'class': 'p-6 pt-0'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     CardContent
  HTML:           <div data-lov-id="src/pages/Customers.tsx:226:8" data-lov-name="CardContent" data-component-path="src/pages/Customers.ts
------------------------------------------------------------
Element 129:
  page_name:      customers
  tag_name:       div
  text:           CustomerAccount TypeBalanceStatusJoin DateActionsSJSarah Johnsonsarah.johnson@email.comPremium$145,000Active2023-01-15MCMichael Chenmichael.chen@email.comStandard$52,000Active2023-03-22EDEmma Davisemma.davis@email.comPremium$89,000Active2022-11-08
  id:             
  class:          relative w-full overflow-auto
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/components/ui/table.tsx:9:2', 'data-lov-name': 'div', 'data-component-path': 'src/components/ui/table.tsx', 'data-component-line': '9', 'data-component-file': 'table.tsx', 'data-component-name': 'div', 'data-component-content': '%7B%22className%22%3A%22relative%20w-full%20overflow-auto%22%7D', 'class': 'relative w-full overflow-auto'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     div
  HTML:           <div data-lov-id="src/components/ui/table.tsx:9:2" data-lov-name="div" data-component-path="src/components/ui/table.tsx"
------------------------------------------------------------
Element 130:
  page_name:      customers
  tag_name:       table
  text:           CustomerAccount TypeBalanceStatusJoin DateActionsSJSarah Johnsonsarah.johnson@email.comPremium$145,000Active2023-01-15MCMichael Chenmichael.chen@email.comStandard$52,000Active2023-03-22EDEmma Davisemma.davis@email.comPremium$89,000Active2022-11-08
  id:             
  class:          w-full caption-bottom text-sm
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Customers.tsx:227:10', 'data-lov-name': 'Table', 'data-component-path': 'src/pages/Customers.tsx', 'data-component-line': '227', 'data-component-file': 'Customers.tsx', 'data-component-name': 'Table', 'data-component-content': '%7B%7D', 'class': 'w-full caption-bottom text-sm'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     Table
  HTML:           <table data-lov-id="src/pages/Customers.tsx:227:10" data-lov-name="Table" data-component-path="src/pages/Customers.tsx" 
------------------------------------------------------------
Element 131:
  page_name:      customers
  tag_name:       thead
  text:           CustomerAccount TypeBalanceStatusJoin DateActions
  id:             
  class:          [&_tr]:border-b
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Customers.tsx:228:12', 'data-lov-name': 'TableHeader', 'data-component-path': 'src/pages/Customers.tsx', 'data-component-line': '228', 'data-component-file': 'Customers.tsx', 'data-component-name': 'TableHeader', 'data-component-content': '%7B%7D', 'class': '[&_tr]:border-b'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     TableHeader
  HTML:           <thead data-lov-id="src/pages/Customers.tsx:228:12" data-lov-name="TableHeader" data-component-path="src/pages/Customers
------------------------------------------------------------
Element 132:
  page_name:      customers
  tag_name:       tr
  text:           CustomerAccount TypeBalanceStatusJoin DateActions
  id:             
  class:          border-b transition-colors hover:bg-muted/50 data-[state=selected]:bg-muted
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Customers.tsx:229:14', 'data-lov-name': 'TableRow', 'data-component-path': 'src/pages/Customers.tsx', 'data-component-line': '229', 'data-component-file': 'Customers.tsx', 'data-component-name': 'TableRow', 'data-component-content': '%7B%7D', 'class': 'border-b transition-colors hover:bg-muted/50 data-[state=selected]:bg-muted'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     TableRow
  HTML:           <tr data-lov-id="src/pages/Customers.tsx:229:14" data-lov-name="TableRow" data-component-path="src/pages/Customers.tsx" 
------------------------------------------------------------
Element 133:
  page_name:      customers
  tag_name:       th
  text:           Customer
  id:             
  class:          h-12 px-4 text-left align-middle font-medium text-muted-foreground [&:has([role=checkbox])]:pr-0
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Customers.tsx:230:16', 'data-lov-name': 'TableHead', 'data-component-path': 'src/pages/Customers.tsx', 'data-component-line': '230', 'data-component-file': 'Customers.tsx', 'data-component-name': 'TableHead', 'data-component-content': '%7B%22text%22%3A%22Customer%22%7D', 'class': 'h-12 px-4 text-left align-middle font-medium text-muted-foreground [&:has([role=checkbox])]:pr-0'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     TableHead
  HTML:           <th data-lov-id="src/pages/Customers.tsx:230:16" data-lov-name="TableHead" data-component-path="src/pages/Customers.tsx"
------------------------------------------------------------
Element 134:
  page_name:      customers
  tag_name:       th
  text:           Account Type
  id:             
  class:          h-12 px-4 text-left align-middle font-medium text-muted-foreground [&:has([role=checkbox])]:pr-0
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Customers.tsx:231:16', 'data-lov-name': 'TableHead', 'data-component-path': 'src/pages/Customers.tsx', 'data-component-line': '231', 'data-component-file': 'Customers.tsx', 'data-component-name': 'TableHead', 'data-component-content': '%7B%22text%22%3A%22Account%20Type%22%7D', 'class': 'h-12 px-4 text-left align-middle font-medium text-muted-foreground [&:has([role=checkbox])]:pr-0'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     TableHead
  HTML:           <th data-lov-id="src/pages/Customers.tsx:231:16" data-lov-name="TableHead" data-component-path="src/pages/Customers.tsx"
------------------------------------------------------------
Element 135:
  page_name:      customers
  tag_name:       th
  text:           Balance
  id:             
  class:          h-12 px-4 text-left align-middle font-medium text-muted-foreground [&:has([role=checkbox])]:pr-0
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Customers.tsx:232:16', 'data-lov-name': 'TableHead', 'data-component-path': 'src/pages/Customers.tsx', 'data-component-line': '232', 'data-component-file': 'Customers.tsx', 'data-component-name': 'TableHead', 'data-component-content': '%7B%22text%22%3A%22Balance%22%7D', 'class': 'h-12 px-4 text-left align-middle font-medium text-muted-foreground [&:has([role=checkbox])]:pr-0'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     TableHead
  HTML:           <th data-lov-id="src/pages/Customers.tsx:232:16" data-lov-name="TableHead" data-component-path="src/pages/Customers.tsx"
------------------------------------------------------------
Element 136:
  page_name:      customers
  tag_name:       th
  text:           Status
  id:             
  class:          h-12 px-4 text-left align-middle font-medium text-muted-foreground [&:has([role=checkbox])]:pr-0
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Customers.tsx:233:16', 'data-lov-name': 'TableHead', 'data-component-path': 'src/pages/Customers.tsx', 'data-component-line': '233', 'data-component-file': 'Customers.tsx', 'data-component-name': 'TableHead', 'data-component-content': '%7B%22text%22%3A%22Status%22%7D', 'class': 'h-12 px-4 text-left align-middle font-medium text-muted-foreground [&:has([role=checkbox])]:pr-0'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     TableHead
  HTML:           <th data-lov-id="src/pages/Customers.tsx:233:16" data-lov-name="TableHead" data-component-path="src/pages/Customers.tsx"
------------------------------------------------------------
Element 137:
  page_name:      customers
  tag_name:       th
  text:           Join Date
  id:             
  class:          h-12 px-4 text-left align-middle font-medium text-muted-foreground [&:has([role=checkbox])]:pr-0
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Customers.tsx:234:16', 'data-lov-name': 'TableHead', 'data-component-path': 'src/pages/Customers.tsx', 'data-component-line': '234', 'data-component-file': 'Customers.tsx', 'data-component-name': 'TableHead', 'data-component-content': '%7B%22text%22%3A%22Join%20Date%22%7D', 'class': 'h-12 px-4 text-left align-middle font-medium text-muted-foreground [&:has([role=checkbox])]:pr-0'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     TableHead
  HTML:           <th data-lov-id="src/pages/Customers.tsx:234:16" data-lov-name="TableHead" data-component-path="src/pages/Customers.tsx"
------------------------------------------------------------
Element 138:
  page_name:      customers
  tag_name:       th
  text:           Actions
  id:             
  class:          h-12 px-4 text-left align-middle font-medium text-muted-foreground [&:has([role=checkbox])]:pr-0
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Customers.tsx:235:16', 'data-lov-name': 'TableHead', 'data-component-path': 'src/pages/Customers.tsx', 'data-component-line': '235', 'data-component-file': 'Customers.tsx', 'data-component-name': 'TableHead', 'data-component-content': '%7B%22text%22%3A%22Actions%22%7D', 'class': 'h-12 px-4 text-left align-middle font-medium text-muted-foreground [&:has([role=checkbox])]:pr-0'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     TableHead
  HTML:           <th data-lov-id="src/pages/Customers.tsx:235:16" data-lov-name="TableHead" data-component-path="src/pages/Customers.tsx"
------------------------------------------------------------
Element 139:
  page_name:      customers
  tag_name:       tbody
  text:           SJSarah Johnsonsarah.johnson@email.comPremium$145,000Active2023-01-15MCMichael Chenmichael.chen@email.comStandard$52,000Active2023-03-22EDEmma Davisemma.davis@email.comPremium$89,000Active2022-11-08
  id:             
  class:          [&_tr:last-child]:border-0
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Customers.tsx:238:12', 'data-lov-name': 'TableBody', 'data-component-path': 'src/pages/Customers.tsx', 'data-component-line': '238', 'data-component-file': 'Customers.tsx', 'data-component-name': 'TableBody', 'data-component-content': '%7B%7D', 'class': '[&_tr:last-child]:border-0'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     TableBody
  HTML:           <tbody data-lov-id="src/pages/Customers.tsx:238:12" data-lov-name="TableBody" data-component-path="src/pages/Customers.t
------------------------------------------------------------
Element 140:
  page_name:      customers
  tag_name:       tr
  text:           SJSarah Johnsonsarah.johnson@email.comPremium$145,000Active2023-01-15
  id:             
  class:          border-b transition-colors hover:bg-muted/50 data-[state=selected]:bg-muted
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Customers.tsx:240:16', 'data-lov-name': 'TableRow', 'data-component-path': 'src/pages/Customers.tsx', 'data-component-line': '240', 'data-component-file': 'Customers.tsx', 'data-component-name': 'TableRow', 'data-component-content': '%7B%7D', 'class': 'border-b transition-colors hover:bg-muted/50 data-[state=selected]:bg-muted'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     TableRow
  HTML:           <tr data-lov-id="src/pages/Customers.tsx:240:16" data-lov-name="TableRow" data-component-path="src/pages/Customers.tsx" 
------------------------------------------------------------
Element 141:
  page_name:      customers
  tag_name:       td
  text:           SJSarah Johnsonsarah.johnson@email.com
  id:             
  class:          p-4 align-middle [&:has([role=checkbox])]:pr-0 flex items-center gap-3
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Customers.tsx:241:18', 'data-lov-name': 'TableCell', 'data-component-path': 'src/pages/Customers.tsx', 'data-component-line': '241', 'data-component-file': 'Customers.tsx', 'data-component-name': 'TableCell', 'data-component-content': '%7B%22className%22%3A%22flex%20items-center%20gap-3%22%7D', 'class': 'p-4 align-middle [&:has([role=checkbox])]:pr-0 flex items-center gap-3'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     TableCell
  HTML:           <td data-lov-id="src/pages/Customers.tsx:241:18" data-lov-name="TableCell" data-component-path="src/pages/Customers.tsx"
------------------------------------------------------------
Element 142:
  page_name:      customers
  tag_name:       span
  text:           SJ
  id:             
  class:          relative flex h-10 w-10 shrink-0 overflow-hidden rounded-full
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Customers.tsx:242:20', 'data-lov-name': 'Avatar', 'data-component-path': 'src/pages/Customers.tsx', 'data-component-line': '242', 'data-component-file': 'Customers.tsx', 'data-component-name': 'Avatar', 'data-component-content': '%7B%7D', 'class': 'relative flex h-10 w-10 shrink-0 overflow-hidden rounded-full'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     Avatar
  HTML:           <span data-lov-id="src/pages/Customers.tsx:242:20" data-lov-name="Avatar" data-component-path="src/pages/Customers.tsx" 
------------------------------------------------------------
Element 143:
  page_name:      customers
  tag_name:       span
  text:           SJ
  id:             
  class:          flex h-full w-full items-center justify-center rounded-full bg-muted
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Customers.tsx:244:22', 'data-lov-name': 'AvatarFallback', 'data-component-path': 'src/pages/Customers.tsx', 'data-component-line': '244', 'data-component-file': 'Customers.tsx', 'data-component-name': 'AvatarFallback', 'data-component-content': '%7B%7D', 'class': 'flex h-full w-full items-center justify-center rounded-full bg-muted'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     AvatarFallback
  HTML:           <span data-lov-id="src/pages/Customers.tsx:244:22" data-lov-name="AvatarFallback" data-component-path="src/pages/Custome
------------------------------------------------------------
Element 144:
  page_name:      customers
  tag_name:       div
  text:           Sarah Johnsonsarah.johnson@email.com
  id:             
  class:          
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Customers.tsx:248:20', 'data-lov-name': 'div', 'data-component-path': 'src/pages/Customers.tsx', 'data-component-line': '248', 'data-component-file': 'Customers.tsx', 'data-component-name': 'div', 'data-component-content': '%7B%7D'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     div
  HTML:           <div data-lov-id="src/pages/Customers.tsx:248:20" data-lov-name="div" data-component-path="src/pages/Customers.tsx" data
------------------------------------------------------------
Element 145:
  page_name:      customers
  tag_name:       p
  text:           Sarah Johnson
  id:             
  class:          font-medium
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Customers.tsx:249:22', 'data-lov-name': 'p', 'data-component-path': 'src/pages/Customers.tsx', 'data-component-line': '249', 'data-component-file': 'Customers.tsx', 'data-component-name': 'p', 'data-component-content': '%7B%22className%22%3A%22font-medium%22%7D', 'class': 'font-medium'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     p
  HTML:           <p data-lov-id="src/pages/Customers.tsx:249:22" data-lov-name="p" data-component-path="src/pages/Customers.tsx" data-com
------------------------------------------------------------
Element 146:
  page_name:      customers
  tag_name:       p
  text:           sarah.johnson@email.com
  id:             
  class:          text-sm text-gray-500
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Customers.tsx:250:22', 'data-lov-name': 'p', 'data-component-path': 'src/pages/Customers.tsx', 'data-component-line': '250', 'data-component-file': 'Customers.tsx', 'data-component-name': 'p', 'data-component-content': '%7B%22className%22%3A%22text-sm%20text-gray-500%22%7D', 'class': 'text-sm text-gray-500'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     p
  HTML:           <p data-lov-id="src/pages/Customers.tsx:250:22" data-lov-name="p" data-component-path="src/pages/Customers.tsx" data-com
------------------------------------------------------------
Element 147:
  page_name:      customers
  tag_name:       td
  text:           Premium
  id:             
  class:          p-4 align-middle [&:has([role=checkbox])]:pr-0
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Customers.tsx:253:18', 'data-lov-name': 'TableCell', 'data-component-path': 'src/pages/Customers.tsx', 'data-component-line': '253', 'data-component-file': 'Customers.tsx', 'data-component-name': 'TableCell', 'data-component-content': '%7B%7D', 'class': 'p-4 align-middle [&:has([role=checkbox])]:pr-0'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     TableCell
  HTML:           <td data-lov-id="src/pages/Customers.tsx:253:18" data-lov-name="TableCell" data-component-path="src/pages/Customers.tsx"
------------------------------------------------------------
Element 148:
  page_name:      customers
  tag_name:       div
  text:           Premium
  id:             
  class:          inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 border-transparent hover:bg-primary/80 bg-purple-100 text-purple-800
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Customers.tsx:254:20', 'data-lov-name': 'Badge', 'data-component-path': 'src/pages/Customers.tsx', 'data-component-line': '254', 'data-component-file': 'Customers.tsx', 'data-component-name': 'Badge', 'data-component-content': '%7B%7D', 'class': 'inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 border-transparent hover:bg-primary/80 bg-purple-100 text-purple-800'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     Badge
  HTML:           <div data-lov-id="src/pages/Customers.tsx:254:20" data-lov-name="Badge" data-component-path="src/pages/Customers.tsx" da
------------------------------------------------------------
Element 149:
  page_name:      customers
  tag_name:       td
  text:           $145,000
  id:             
  class:          p-4 align-middle [&:has([role=checkbox])]:pr-0 font-medium
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Customers.tsx:258:18', 'data-lov-name': 'TableCell', 'data-component-path': 'src/pages/Customers.tsx', 'data-component-line': '258', 'data-component-file': 'Customers.tsx', 'data-component-name': 'TableCell', 'data-component-content': '%7B%22text%22%3A%22%24%22%2C%22className%22%3A%22font-medium%22%7D', 'class': 'p-4 align-middle [&:has([role=checkbox])]:pr-0 font-medium'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     TableCell
  HTML:           <td data-lov-id="src/pages/Customers.tsx:258:18" data-lov-name="TableCell" data-component-path="src/pages/Customers.tsx"
------------------------------------------------------------
Element 150:
  page_name:      customers
  tag_name:       td
  text:           Active
  id:             
  class:          p-4 align-middle [&:has([role=checkbox])]:pr-0
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Customers.tsx:261:18', 'data-lov-name': 'TableCell', 'data-component-path': 'src/pages/Customers.tsx', 'data-component-line': '261', 'data-component-file': 'Customers.tsx', 'data-component-name': 'TableCell', 'data-component-content': '%7B%7D', 'class': 'p-4 align-middle [&:has([role=checkbox])]:pr-0'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     TableCell
  HTML:           <td data-lov-id="src/pages/Customers.tsx:261:18" data-lov-name="TableCell" data-component-path="src/pages/Customers.tsx"
------------------------------------------------------------
Element 151:
  page_name:      customers
  tag_name:       div
  text:           Active
  id:             
  class:          inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 border-transparent hover:bg-primary/80 bg-green-100 text-green-800
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Customers.tsx:262:20', 'data-lov-name': 'Badge', 'data-component-path': 'src/pages/Customers.tsx', 'data-component-line': '262', 'data-component-file': 'Customers.tsx', 'data-component-name': 'Badge', 'data-component-content': '%7B%7D', 'class': 'inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 border-transparent hover:bg-primary/80 bg-green-100 text-green-800'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     Badge
  HTML:           <div data-lov-id="src/pages/Customers.tsx:262:20" data-lov-name="Badge" data-component-path="src/pages/Customers.tsx" da
------------------------------------------------------------
Element 152:
  page_name:      customers
  tag_name:       td
  text:           2023-01-15
  id:             
  class:          p-4 align-middle [&:has([role=checkbox])]:pr-0
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Customers.tsx:266:18', 'data-lov-name': 'TableCell', 'data-component-path': 'src/pages/Customers.tsx', 'data-component-line': '266', 'data-component-file': 'Customers.tsx', 'data-component-name': 'TableCell', 'data-component-content': '%7B%7D', 'class': 'p-4 align-middle [&:has([role=checkbox])]:pr-0'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     TableCell
  HTML:           <td data-lov-id="src/pages/Customers.tsx:266:18" data-lov-name="TableCell" data-component-path="src/pages/Customers.tsx"
------------------------------------------------------------
Element 153:
  page_name:      customers
  tag_name:       td
  text:           
  id:             
  class:          p-4 align-middle [&:has([role=checkbox])]:pr-0
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Customers.tsx:267:18', 'data-lov-name': 'TableCell', 'data-component-path': 'src/pages/Customers.tsx', 'data-component-line': '267', 'data-component-file': 'Customers.tsx', 'data-component-name': 'TableCell', 'data-component-content': '%7B%7D', 'class': 'p-4 align-middle [&:has([role=checkbox])]:pr-0'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     TableCell
  HTML:           <td data-lov-id="src/pages/Customers.tsx:267:18" data-lov-name="TableCell" data-component-path="src/pages/Customers.tsx"
------------------------------------------------------------
Element 154:
  page_name:      customers
  tag_name:       div
  text:           
  id:             
  class:          flex items-center gap-2
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Customers.tsx:268:20', 'data-lov-name': 'div', 'data-component-path': 'src/pages/Customers.tsx', 'data-component-line': '268', 'data-component-file': 'Customers.tsx', 'data-component-name': 'div', 'data-component-content': '%7B%22className%22%3A%22flex%20items-center%20gap-2%22%7D', 'class': 'flex items-center gap-2'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     div
  HTML:           <div data-lov-id="src/pages/Customers.tsx:268:20" data-lov-name="div" data-component-path="src/pages/Customers.tsx" data
------------------------------------------------------------
Element 155:
  page_name:      customers
  tag_name:       button
  text:           
  id:             
  class:          inline-flex items-center justify-center gap-2 whitespace-nowrap text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0 hover:bg-accent hover:text-accent-foreground h-9 rounded-md px-3
  value:          
  placeholder:    
  type:           button
  attributes:     {'data-lov-id': 'src/pages/Customers.tsx:271:26', 'data-lov-name': 'Button', 'data-component-path': 'src/pages/Customers.tsx', 'data-component-line': '271', 'data-component-file': 'Customers.tsx', 'data-component-name': 'Button', 'data-component-content': '%7B%7D', 'class': 'inline-flex items-center justify-center gap-2 whitespace-nowrap text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0 hover:bg-accent hover:text-accent-foreground h-9 rounded-md px-3', 'type': 'button', 'aria-haspopup': 'dialog', 'aria-expanded': 'false', 'aria-controls': 'radix-:r5:', 'data-state': 'closed'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     Button
  HTML:           <button data-lov-id="src/pages/Customers.tsx:271:26" data-lov-name="Button" data-component-path="src/pages/Customers.tsx
------------------------------------------------------------
Element 156:
  page_name:      customers
  tag_name:       svg
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'xmlns': 'http://www.w3.org/2000/svg', 'width': '24', 'height': '24', 'viewBox': '0 0 24 24', 'fill': 'none', 'stroke': 'currentColor', 'stroke-width': '2', 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'class': 'lucide lucide-eye w-4 h-4', 'data-lov-id': 'src/pages/Customers.tsx:276:28', 'data-lov-name': 'Eye', 'data-component-path': 'src/pages/Customers.tsx', 'data-component-line': '276', 'data-component-file': 'Customers.tsx', 'data-component-name': 'Eye', 'data-component-content': '%7B%22className%22%3A%22w-4%20h-4%22%7D'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     Eye
  HTML:           <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" str
------------------------------------------------------------
Element 157:
  page_name:      customers
  tag_name:       path
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'d': 'M2.062 12.348a1 1 0 0 1 0-.696 10.75 10.75 0 0 1 19.876 0 1 1 0 0 1 0 .696 10.75 10.75 0 0 1-19.876 0'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <path d="M2.062 12.348a1 1 0 0 1 0-.696 10.75 10.75 0 0 1 19.876 0 1 1 0 0 1 0 .696 10.75 10.75 0 0 1-19.876 0"></path>
------------------------------------------------------------
Element 158:
  page_name:      customers
  tag_name:       circle
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'cx': '12', 'cy': '12', 'r': '3'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <circle cx="12" cy="12" r="3"></circle>
------------------------------------------------------------
Element 159:
  page_name:      customers
  tag_name:       button
  text:           
  id:             
  class:          inline-flex items-center justify-center gap-2 whitespace-nowrap text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0 hover:bg-accent hover:text-accent-foreground h-9 rounded-md px-3
  value:          
  placeholder:    
  type:           submit
  attributes:     {'data-lov-id': 'src/pages/Customers.tsx:414:22', 'data-lov-name': 'Button', 'data-component-path': 'src/pages/Customers.tsx', 'data-component-line': '414', 'data-component-file': 'Customers.tsx', 'data-component-name': 'Button', 'data-component-content': '%7B%7D', 'class': 'inline-flex items-center justify-center gap-2 whitespace-nowrap text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0 hover:bg-accent hover:text-accent-foreground h-9 rounded-md px-3'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     Button
  HTML:           <button data-lov-id="src/pages/Customers.tsx:414:22" data-lov-name="Button" data-component-path="src/pages/Customers.tsx
------------------------------------------------------------
Element 160:
  page_name:      customers
  tag_name:       svg
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'xmlns': 'http://www.w3.org/2000/svg', 'width': '24', 'height': '24', 'viewBox': '0 0 24 24', 'fill': 'none', 'stroke': 'currentColor', 'stroke-width': '2', 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'class': 'lucide lucide-square-pen w-4 h-4', 'data-lov-id': 'src/pages/Customers.tsx:415:24', 'data-lov-name': 'Edit', 'data-component-path': 'src/pages/Customers.tsx', 'data-component-line': '415', 'data-component-file': 'Customers.tsx', 'data-component-name': 'Edit', 'data-component-content': '%7B%22className%22%3A%22w-4%20h-4%22%7D'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     Edit
  HTML:           <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" str
------------------------------------------------------------
Element 161:
  page_name:      customers
  tag_name:       path
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'d': 'M12 3H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <path d="M12 3H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
------------------------------------------------------------
Element 162:
  page_name:      customers
  tag_name:       path
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'d': 'M18.375 2.625a1 1 0 0 1 3 3l-9.013 9.014a2 2 0 0 1-.853.505l-2.873.84a.5.5 0 0 1-.62-.62l.84-2.873a2 2 0 0 1 .506-.852z'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <path d="M18.375 2.625a1 1 0 0 1 3 3l-9.013 9.014a2 2 0 0 1-.853.505l-2.873.84a.5.5 0 0 1-.62-.62l.84-2.873a2 2 0 0 1 .5
------------------------------------------------------------
Element 163:
  page_name:      customers
  tag_name:       tr
  text:           MCMichael Chenmichael.chen@email.comStandard$52,000Active2023-03-22
  id:             
  class:          border-b transition-colors hover:bg-muted/50 data-[state=selected]:bg-muted
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Customers.tsx:240:16', 'data-lov-name': 'TableRow', 'data-component-path': 'src/pages/Customers.tsx', 'data-component-line': '240', 'data-component-file': 'Customers.tsx', 'data-component-name': 'TableRow', 'data-component-content': '%7B%7D', 'class': 'border-b transition-colors hover:bg-muted/50 data-[state=selected]:bg-muted'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     TableRow
  HTML:           <tr data-lov-id="src/pages/Customers.tsx:240:16" data-lov-name="TableRow" data-component-path="src/pages/Customers.tsx" 
------------------------------------------------------------
Element 164:
  page_name:      customers
  tag_name:       td
  text:           MCMichael Chenmichael.chen@email.com
  id:             
  class:          p-4 align-middle [&:has([role=checkbox])]:pr-0 flex items-center gap-3
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Customers.tsx:241:18', 'data-lov-name': 'TableCell', 'data-component-path': 'src/pages/Customers.tsx', 'data-component-line': '241', 'data-component-file': 'Customers.tsx', 'data-component-name': 'TableCell', 'data-component-content': '%7B%22className%22%3A%22flex%20items-center%20gap-3%22%7D', 'class': 'p-4 align-middle [&:has([role=checkbox])]:pr-0 flex items-center gap-3'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     TableCell
  HTML:           <td data-lov-id="src/pages/Customers.tsx:241:18" data-lov-name="TableCell" data-component-path="src/pages/Customers.tsx"
------------------------------------------------------------
Element 165:
  page_name:      customers
  tag_name:       span
  text:           MC
  id:             
  class:          relative flex h-10 w-10 shrink-0 overflow-hidden rounded-full
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Customers.tsx:242:20', 'data-lov-name': 'Avatar', 'data-component-path': 'src/pages/Customers.tsx', 'data-component-line': '242', 'data-component-file': 'Customers.tsx', 'data-component-name': 'Avatar', 'data-component-content': '%7B%7D', 'class': 'relative flex h-10 w-10 shrink-0 overflow-hidden rounded-full'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     Avatar
  HTML:           <span data-lov-id="src/pages/Customers.tsx:242:20" data-lov-name="Avatar" data-component-path="src/pages/Customers.tsx" 
------------------------------------------------------------
Element 166:
  page_name:      customers
  tag_name:       span
  text:           MC
  id:             
  class:          flex h-full w-full items-center justify-center rounded-full bg-muted
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Customers.tsx:244:22', 'data-lov-name': 'AvatarFallback', 'data-component-path': 'src/pages/Customers.tsx', 'data-component-line': '244', 'data-component-file': 'Customers.tsx', 'data-component-name': 'AvatarFallback', 'data-component-content': '%7B%7D', 'class': 'flex h-full w-full items-center justify-center rounded-full bg-muted'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     AvatarFallback
  HTML:           <span data-lov-id="src/pages/Customers.tsx:244:22" data-lov-name="AvatarFallback" data-component-path="src/pages/Custome
------------------------------------------------------------
Element 167:
  page_name:      customers
  tag_name:       div
  text:           Michael Chenmichael.chen@email.com
  id:             
  class:          
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Customers.tsx:248:20', 'data-lov-name': 'div', 'data-component-path': 'src/pages/Customers.tsx', 'data-component-line': '248', 'data-component-file': 'Customers.tsx', 'data-component-name': 'div', 'data-component-content': '%7B%7D'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     div
  HTML:           <div data-lov-id="src/pages/Customers.tsx:248:20" data-lov-name="div" data-component-path="src/pages/Customers.tsx" data
------------------------------------------------------------
Element 168:
  page_name:      customers
  tag_name:       p
  text:           Michael Chen
  id:             
  class:          font-medium
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Customers.tsx:249:22', 'data-lov-name': 'p', 'data-component-path': 'src/pages/Customers.tsx', 'data-component-line': '249', 'data-component-file': 'Customers.tsx', 'data-component-name': 'p', 'data-component-content': '%7B%22className%22%3A%22font-medium%22%7D', 'class': 'font-medium'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     p
  HTML:           <p data-lov-id="src/pages/Customers.tsx:249:22" data-lov-name="p" data-component-path="src/pages/Customers.tsx" data-com
------------------------------------------------------------
Element 169:
  page_name:      customers
  tag_name:       p
  text:           michael.chen@email.com
  id:             
  class:          text-sm text-gray-500
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Customers.tsx:250:22', 'data-lov-name': 'p', 'data-component-path': 'src/pages/Customers.tsx', 'data-component-line': '250', 'data-component-file': 'Customers.tsx', 'data-component-name': 'p', 'data-component-content': '%7B%22className%22%3A%22text-sm%20text-gray-500%22%7D', 'class': 'text-sm text-gray-500'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     p
  HTML:           <p data-lov-id="src/pages/Customers.tsx:250:22" data-lov-name="p" data-component-path="src/pages/Customers.tsx" data-com
------------------------------------------------------------
Element 170:
  page_name:      customers
  tag_name:       td
  text:           Standard
  id:             
  class:          p-4 align-middle [&:has([role=checkbox])]:pr-0
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Customers.tsx:253:18', 'data-lov-name': 'TableCell', 'data-component-path': 'src/pages/Customers.tsx', 'data-component-line': '253', 'data-component-file': 'Customers.tsx', 'data-component-name': 'TableCell', 'data-component-content': '%7B%7D', 'class': 'p-4 align-middle [&:has([role=checkbox])]:pr-0'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     TableCell
  HTML:           <td data-lov-id="src/pages/Customers.tsx:253:18" data-lov-name="TableCell" data-component-path="src/pages/Customers.tsx"
------------------------------------------------------------
Element 171:
  page_name:      customers
  tag_name:       div
  text:           Standard
  id:             
  class:          inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 border-transparent hover:bg-primary/80 bg-blue-100 text-blue-800
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Customers.tsx:254:20', 'data-lov-name': 'Badge', 'data-component-path': 'src/pages/Customers.tsx', 'data-component-line': '254', 'data-component-file': 'Customers.tsx', 'data-component-name': 'Badge', 'data-component-content': '%7B%7D', 'class': 'inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 border-transparent hover:bg-primary/80 bg-blue-100 text-blue-800'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     Badge
  HTML:           <div data-lov-id="src/pages/Customers.tsx:254:20" data-lov-name="Badge" data-component-path="src/pages/Customers.tsx" da
------------------------------------------------------------
Element 172:
  page_name:      customers
  tag_name:       td
  text:           $52,000
  id:             
  class:          p-4 align-middle [&:has([role=checkbox])]:pr-0 font-medium
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Customers.tsx:258:18', 'data-lov-name': 'TableCell', 'data-component-path': 'src/pages/Customers.tsx', 'data-component-line': '258', 'data-component-file': 'Customers.tsx', 'data-component-name': 'TableCell', 'data-component-content': '%7B%22text%22%3A%22%24%22%2C%22className%22%3A%22font-medium%22%7D', 'class': 'p-4 align-middle [&:has([role=checkbox])]:pr-0 font-medium'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     TableCell
  HTML:           <td data-lov-id="src/pages/Customers.tsx:258:18" data-lov-name="TableCell" data-component-path="src/pages/Customers.tsx"
------------------------------------------------------------
Element 173:
  page_name:      customers
  tag_name:       td
  text:           Active
  id:             
  class:          p-4 align-middle [&:has([role=checkbox])]:pr-0
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Customers.tsx:261:18', 'data-lov-name': 'TableCell', 'data-component-path': 'src/pages/Customers.tsx', 'data-component-line': '261', 'data-component-file': 'Customers.tsx', 'data-component-name': 'TableCell', 'data-component-content': '%7B%7D', 'class': 'p-4 align-middle [&:has([role=checkbox])]:pr-0'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     TableCell
  HTML:           <td data-lov-id="src/pages/Customers.tsx:261:18" data-lov-name="TableCell" data-component-path="src/pages/Customers.tsx"
------------------------------------------------------------
Element 174:
  page_name:      customers
  tag_name:       div
  text:           Active
  id:             
  class:          inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 border-transparent hover:bg-primary/80 bg-green-100 text-green-800
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Customers.tsx:262:20', 'data-lov-name': 'Badge', 'data-component-path': 'src/pages/Customers.tsx', 'data-component-line': '262', 'data-component-file': 'Customers.tsx', 'data-component-name': 'Badge', 'data-component-content': '%7B%7D', 'class': 'inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 border-transparent hover:bg-primary/80 bg-green-100 text-green-800'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     Badge
  HTML:           <div data-lov-id="src/pages/Customers.tsx:262:20" data-lov-name="Badge" data-component-path="src/pages/Customers.tsx" da
------------------------------------------------------------
Element 175:
  page_name:      customers
  tag_name:       td
  text:           2023-03-22
  id:             
  class:          p-4 align-middle [&:has([role=checkbox])]:pr-0
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Customers.tsx:266:18', 'data-lov-name': 'TableCell', 'data-component-path': 'src/pages/Customers.tsx', 'data-component-line': '266', 'data-component-file': 'Customers.tsx', 'data-component-name': 'TableCell', 'data-component-content': '%7B%7D', 'class': 'p-4 align-middle [&:has([role=checkbox])]:pr-0'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     TableCell
  HTML:           <td data-lov-id="src/pages/Customers.tsx:266:18" data-lov-name="TableCell" data-component-path="src/pages/Customers.tsx"
------------------------------------------------------------
Element 176:
  page_name:      customers
  tag_name:       td
  text:           
  id:             
  class:          p-4 align-middle [&:has([role=checkbox])]:pr-0
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Customers.tsx:267:18', 'data-lov-name': 'TableCell', 'data-component-path': 'src/pages/Customers.tsx', 'data-component-line': '267', 'data-component-file': 'Customers.tsx', 'data-component-name': 'TableCell', 'data-component-content': '%7B%7D', 'class': 'p-4 align-middle [&:has([role=checkbox])]:pr-0'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     TableCell
  HTML:           <td data-lov-id="src/pages/Customers.tsx:267:18" data-lov-name="TableCell" data-component-path="src/pages/Customers.tsx"
------------------------------------------------------------
Element 177:
  page_name:      customers
  tag_name:       div
  text:           
  id:             
  class:          flex items-center gap-2
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Customers.tsx:268:20', 'data-lov-name': 'div', 'data-component-path': 'src/pages/Customers.tsx', 'data-component-line': '268', 'data-component-file': 'Customers.tsx', 'data-component-name': 'div', 'data-component-content': '%7B%22className%22%3A%22flex%20items-center%20gap-2%22%7D', 'class': 'flex items-center gap-2'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     div
  HTML:           <div data-lov-id="src/pages/Customers.tsx:268:20" data-lov-name="div" data-component-path="src/pages/Customers.tsx" data
------------------------------------------------------------
Element 178:
  page_name:      customers
  tag_name:       button
  text:           
  id:             
  class:          inline-flex items-center justify-center gap-2 whitespace-nowrap text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0 hover:bg-accent hover:text-accent-foreground h-9 rounded-md px-3
  value:          
  placeholder:    
  type:           button
  attributes:     {'data-lov-id': 'src/pages/Customers.tsx:271:26', 'data-lov-name': 'Button', 'data-component-path': 'src/pages/Customers.tsx', 'data-component-line': '271', 'data-component-file': 'Customers.tsx', 'data-component-name': 'Button', 'data-component-content': '%7B%7D', 'class': 'inline-flex items-center justify-center gap-2 whitespace-nowrap text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0 hover:bg-accent hover:text-accent-foreground h-9 rounded-md px-3', 'type': 'button', 'aria-haspopup': 'dialog', 'aria-expanded': 'false', 'aria-controls': 'radix-:r8:', 'data-state': 'closed'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     Button
  HTML:           <button data-lov-id="src/pages/Customers.tsx:271:26" data-lov-name="Button" data-component-path="src/pages/Customers.tsx
------------------------------------------------------------
Element 179:
  page_name:      customers
  tag_name:       svg
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'xmlns': 'http://www.w3.org/2000/svg', 'width': '24', 'height': '24', 'viewBox': '0 0 24 24', 'fill': 'none', 'stroke': 'currentColor', 'stroke-width': '2', 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'class': 'lucide lucide-eye w-4 h-4', 'data-lov-id': 'src/pages/Customers.tsx:276:28', 'data-lov-name': 'Eye', 'data-component-path': 'src/pages/Customers.tsx', 'data-component-line': '276', 'data-component-file': 'Customers.tsx', 'data-component-name': 'Eye', 'data-component-content': '%7B%22className%22%3A%22w-4%20h-4%22%7D'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     Eye
  HTML:           <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" str
------------------------------------------------------------
Element 180:
  page_name:      customers
  tag_name:       path
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'d': 'M2.062 12.348a1 1 0 0 1 0-.696 10.75 10.75 0 0 1 19.876 0 1 1 0 0 1 0 .696 10.75 10.75 0 0 1-19.876 0'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <path d="M2.062 12.348a1 1 0 0 1 0-.696 10.75 10.75 0 0 1 19.876 0 1 1 0 0 1 0 .696 10.75 10.75 0 0 1-19.876 0"></path>
------------------------------------------------------------
Element 181:
  page_name:      customers
  tag_name:       circle
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'cx': '12', 'cy': '12', 'r': '3'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <circle cx="12" cy="12" r="3"></circle>
------------------------------------------------------------
Element 182:
  page_name:      customers
  tag_name:       button
  text:           
  id:             
  class:          inline-flex items-center justify-center gap-2 whitespace-nowrap text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0 hover:bg-accent hover:text-accent-foreground h-9 rounded-md px-3
  value:          
  placeholder:    
  type:           submit
  attributes:     {'data-lov-id': 'src/pages/Customers.tsx:414:22', 'data-lov-name': 'Button', 'data-component-path': 'src/pages/Customers.tsx', 'data-component-line': '414', 'data-component-file': 'Customers.tsx', 'data-component-name': 'Button', 'data-component-content': '%7B%7D', 'class': 'inline-flex items-center justify-center gap-2 whitespace-nowrap text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0 hover:bg-accent hover:text-accent-foreground h-9 rounded-md px-3'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     Button
  HTML:           <button data-lov-id="src/pages/Customers.tsx:414:22" data-lov-name="Button" data-component-path="src/pages/Customers.tsx
------------------------------------------------------------
Element 183:
  page_name:      customers
  tag_name:       svg
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'xmlns': 'http://www.w3.org/2000/svg', 'width': '24', 'height': '24', 'viewBox': '0 0 24 24', 'fill': 'none', 'stroke': 'currentColor', 'stroke-width': '2', 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'class': 'lucide lucide-square-pen w-4 h-4', 'data-lov-id': 'src/pages/Customers.tsx:415:24', 'data-lov-name': 'Edit', 'data-component-path': 'src/pages/Customers.tsx', 'data-component-line': '415', 'data-component-file': 'Customers.tsx', 'data-component-name': 'Edit', 'data-component-content': '%7B%22className%22%3A%22w-4%20h-4%22%7D'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     Edit
  HTML:           <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" str
------------------------------------------------------------
Element 184:
  page_name:      customers
  tag_name:       path
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'d': 'M12 3H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <path d="M12 3H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
------------------------------------------------------------
Element 185:
  page_name:      customers
  tag_name:       path
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'d': 'M18.375 2.625a1 1 0 0 1 3 3l-9.013 9.014a2 2 0 0 1-.853.505l-2.873.84a.5.5 0 0 1-.62-.62l.84-2.873a2 2 0 0 1 .506-.852z'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <path d="M18.375 2.625a1 1 0 0 1 3 3l-9.013 9.014a2 2 0 0 1-.853.505l-2.873.84a.5.5 0 0 1-.62-.62l.84-2.873a2 2 0 0 1 .5
------------------------------------------------------------
Element 186:
  page_name:      customers
  tag_name:       tr
  text:           EDEmma Davisemma.davis@email.comPremium$89,000Active2022-11-08
  id:             
  class:          border-b transition-colors hover:bg-muted/50 data-[state=selected]:bg-muted
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Customers.tsx:240:16', 'data-lov-name': 'TableRow', 'data-component-path': 'src/pages/Customers.tsx', 'data-component-line': '240', 'data-component-file': 'Customers.tsx', 'data-component-name': 'TableRow', 'data-component-content': '%7B%7D', 'class': 'border-b transition-colors hover:bg-muted/50 data-[state=selected]:bg-muted'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     TableRow
  HTML:           <tr data-lov-id="src/pages/Customers.tsx:240:16" data-lov-name="TableRow" data-component-path="src/pages/Customers.tsx" 
------------------------------------------------------------
Element 187:
  page_name:      customers
  tag_name:       td
  text:           EDEmma Davisemma.davis@email.com
  id:             
  class:          p-4 align-middle [&:has([role=checkbox])]:pr-0 flex items-center gap-3
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Customers.tsx:241:18', 'data-lov-name': 'TableCell', 'data-component-path': 'src/pages/Customers.tsx', 'data-component-line': '241', 'data-component-file': 'Customers.tsx', 'data-component-name': 'TableCell', 'data-component-content': '%7B%22className%22%3A%22flex%20items-center%20gap-3%22%7D', 'class': 'p-4 align-middle [&:has([role=checkbox])]:pr-0 flex items-center gap-3'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     TableCell
  HTML:           <td data-lov-id="src/pages/Customers.tsx:241:18" data-lov-name="TableCell" data-component-path="src/pages/Customers.tsx"
------------------------------------------------------------
Element 188:
  page_name:      customers
  tag_name:       span
  text:           ED
  id:             
  class:          relative flex h-10 w-10 shrink-0 overflow-hidden rounded-full
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Customers.tsx:242:20', 'data-lov-name': 'Avatar', 'data-component-path': 'src/pages/Customers.tsx', 'data-component-line': '242', 'data-component-file': 'Customers.tsx', 'data-component-name': 'Avatar', 'data-component-content': '%7B%7D', 'class': 'relative flex h-10 w-10 shrink-0 overflow-hidden rounded-full'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     Avatar
  HTML:           <span data-lov-id="src/pages/Customers.tsx:242:20" data-lov-name="Avatar" data-component-path="src/pages/Customers.tsx" 
------------------------------------------------------------
Element 189:
  page_name:      customers
  tag_name:       span
  text:           ED
  id:             
  class:          flex h-full w-full items-center justify-center rounded-full bg-muted
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Customers.tsx:244:22', 'data-lov-name': 'AvatarFallback', 'data-component-path': 'src/pages/Customers.tsx', 'data-component-line': '244', 'data-component-file': 'Customers.tsx', 'data-component-name': 'AvatarFallback', 'data-component-content': '%7B%7D', 'class': 'flex h-full w-full items-center justify-center rounded-full bg-muted'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     AvatarFallback
  HTML:           <span data-lov-id="src/pages/Customers.tsx:244:22" data-lov-name="AvatarFallback" data-component-path="src/pages/Custome
------------------------------------------------------------
Element 190:
  page_name:      customers
  tag_name:       div
  text:           Emma Davisemma.davis@email.com
  id:             
  class:          
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Customers.tsx:248:20', 'data-lov-name': 'div', 'data-component-path': 'src/pages/Customers.tsx', 'data-component-line': '248', 'data-component-file': 'Customers.tsx', 'data-component-name': 'div', 'data-component-content': '%7B%7D'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     div
  HTML:           <div data-lov-id="src/pages/Customers.tsx:248:20" data-lov-name="div" data-component-path="src/pages/Customers.tsx" data
------------------------------------------------------------
Element 191:
  page_name:      customers
  tag_name:       p
  text:           Emma Davis
  id:             
  class:          font-medium
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Customers.tsx:249:22', 'data-lov-name': 'p', 'data-component-path': 'src/pages/Customers.tsx', 'data-component-line': '249', 'data-component-file': 'Customers.tsx', 'data-component-name': 'p', 'data-component-content': '%7B%22className%22%3A%22font-medium%22%7D', 'class': 'font-medium'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     p
  HTML:           <p data-lov-id="src/pages/Customers.tsx:249:22" data-lov-name="p" data-component-path="src/pages/Customers.tsx" data-com
------------------------------------------------------------
Element 192:
  page_name:      customers
  tag_name:       p
  text:           emma.davis@email.com
  id:             
  class:          text-sm text-gray-500
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Customers.tsx:250:22', 'data-lov-name': 'p', 'data-component-path': 'src/pages/Customers.tsx', 'data-component-line': '250', 'data-component-file': 'Customers.tsx', 'data-component-name': 'p', 'data-component-content': '%7B%22className%22%3A%22text-sm%20text-gray-500%22%7D', 'class': 'text-sm text-gray-500'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     p
  HTML:           <p data-lov-id="src/pages/Customers.tsx:250:22" data-lov-name="p" data-component-path="src/pages/Customers.tsx" data-com
------------------------------------------------------------
Element 193:
  page_name:      customers
  tag_name:       td
  text:           Premium
  id:             
  class:          p-4 align-middle [&:has([role=checkbox])]:pr-0
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Customers.tsx:253:18', 'data-lov-name': 'TableCell', 'data-component-path': 'src/pages/Customers.tsx', 'data-component-line': '253', 'data-component-file': 'Customers.tsx', 'data-component-name': 'TableCell', 'data-component-content': '%7B%7D', 'class': 'p-4 align-middle [&:has([role=checkbox])]:pr-0'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     TableCell
  HTML:           <td data-lov-id="src/pages/Customers.tsx:253:18" data-lov-name="TableCell" data-component-path="src/pages/Customers.tsx"
------------------------------------------------------------
Element 194:
  page_name:      customers
  tag_name:       div
  text:           Premium
  id:             
  class:          inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 border-transparent hover:bg-primary/80 bg-purple-100 text-purple-800
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Customers.tsx:254:20', 'data-lov-name': 'Badge', 'data-component-path': 'src/pages/Customers.tsx', 'data-component-line': '254', 'data-component-file': 'Customers.tsx', 'data-component-name': 'Badge', 'data-component-content': '%7B%7D', 'class': 'inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 border-transparent hover:bg-primary/80 bg-purple-100 text-purple-800'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     Badge
  HTML:           <div data-lov-id="src/pages/Customers.tsx:254:20" data-lov-name="Badge" data-component-path="src/pages/Customers.tsx" da
------------------------------------------------------------
Element 195:
  page_name:      customers
  tag_name:       td
  text:           $89,000
  id:             
  class:          p-4 align-middle [&:has([role=checkbox])]:pr-0 font-medium
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Customers.tsx:258:18', 'data-lov-name': 'TableCell', 'data-component-path': 'src/pages/Customers.tsx', 'data-component-line': '258', 'data-component-file': 'Customers.tsx', 'data-component-name': 'TableCell', 'data-component-content': '%7B%22text%22%3A%22%24%22%2C%22className%22%3A%22font-medium%22%7D', 'class': 'p-4 align-middle [&:has([role=checkbox])]:pr-0 font-medium'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     TableCell
  HTML:           <td data-lov-id="src/pages/Customers.tsx:258:18" data-lov-name="TableCell" data-component-path="src/pages/Customers.tsx"
------------------------------------------------------------
Element 196:
  page_name:      customers
  tag_name:       td
  text:           Active
  id:             
  class:          p-4 align-middle [&:has([role=checkbox])]:pr-0
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Customers.tsx:261:18', 'data-lov-name': 'TableCell', 'data-component-path': 'src/pages/Customers.tsx', 'data-component-line': '261', 'data-component-file': 'Customers.tsx', 'data-component-name': 'TableCell', 'data-component-content': '%7B%7D', 'class': 'p-4 align-middle [&:has([role=checkbox])]:pr-0'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     TableCell
  HTML:           <td data-lov-id="src/pages/Customers.tsx:261:18" data-lov-name="TableCell" data-component-path="src/pages/Customers.tsx"
------------------------------------------------------------
Element 197:
  page_name:      customers
  tag_name:       div
  text:           Active
  id:             
  class:          inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 border-transparent hover:bg-primary/80 bg-green-100 text-green-800
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Customers.tsx:262:20', 'data-lov-name': 'Badge', 'data-component-path': 'src/pages/Customers.tsx', 'data-component-line': '262', 'data-component-file': 'Customers.tsx', 'data-component-name': 'Badge', 'data-component-content': '%7B%7D', 'class': 'inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 border-transparent hover:bg-primary/80 bg-green-100 text-green-800'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     Badge
  HTML:           <div data-lov-id="src/pages/Customers.tsx:262:20" data-lov-name="Badge" data-component-path="src/pages/Customers.tsx" da
------------------------------------------------------------
Element 198:
  page_name:      customers
  tag_name:       td
  text:           2022-11-08
  id:             
  class:          p-4 align-middle [&:has([role=checkbox])]:pr-0
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Customers.tsx:266:18', 'data-lov-name': 'TableCell', 'data-component-path': 'src/pages/Customers.tsx', 'data-component-line': '266', 'data-component-file': 'Customers.tsx', 'data-component-name': 'TableCell', 'data-component-content': '%7B%7D', 'class': 'p-4 align-middle [&:has([role=checkbox])]:pr-0'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     TableCell
  HTML:           <td data-lov-id="src/pages/Customers.tsx:266:18" data-lov-name="TableCell" data-component-path="src/pages/Customers.tsx"
------------------------------------------------------------
Element 199:
  page_name:      customers
  tag_name:       td
  text:           
  id:             
  class:          p-4 align-middle [&:has([role=checkbox])]:pr-0
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Customers.tsx:267:18', 'data-lov-name': 'TableCell', 'data-component-path': 'src/pages/Customers.tsx', 'data-component-line': '267', 'data-component-file': 'Customers.tsx', 'data-component-name': 'TableCell', 'data-component-content': '%7B%7D', 'class': 'p-4 align-middle [&:has([role=checkbox])]:pr-0'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     TableCell
  HTML:           <td data-lov-id="src/pages/Customers.tsx:267:18" data-lov-name="TableCell" data-component-path="src/pages/Customers.tsx"
------------------------------------------------------------
Element 200:
  page_name:      customers
  tag_name:       div
  text:           
  id:             
  class:          flex items-center gap-2
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Customers.tsx:268:20', 'data-lov-name': 'div', 'data-component-path': 'src/pages/Customers.tsx', 'data-component-line': '268', 'data-component-file': 'Customers.tsx', 'data-component-name': 'div', 'data-component-content': '%7B%22className%22%3A%22flex%20items-center%20gap-2%22%7D', 'class': 'flex items-center gap-2'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     div
  HTML:           <div data-lov-id="src/pages/Customers.tsx:268:20" data-lov-name="div" data-component-path="src/pages/Customers.tsx" data
------------------------------------------------------------
Element 201:
  page_name:      customers
  tag_name:       button
  text:           
  id:             
  class:          inline-flex items-center justify-center gap-2 whitespace-nowrap text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0 hover:bg-accent hover:text-accent-foreground h-9 rounded-md px-3
  value:          
  placeholder:    
  type:           button
  attributes:     {'data-lov-id': 'src/pages/Customers.tsx:271:26', 'data-lov-name': 'Button', 'data-component-path': 'src/pages/Customers.tsx', 'data-component-line': '271', 'data-component-file': 'Customers.tsx', 'data-component-name': 'Button', 'data-component-content': '%7B%7D', 'class': 'inline-flex items-center justify-center gap-2 whitespace-nowrap text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0 hover:bg-accent hover:text-accent-foreground h-9 rounded-md px-3', 'type': 'button', 'aria-haspopup': 'dialog', 'aria-expanded': 'false', 'aria-controls': 'radix-:rb:', 'data-state': 'closed'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     Button
  HTML:           <button data-lov-id="src/pages/Customers.tsx:271:26" data-lov-name="Button" data-component-path="src/pages/Customers.tsx
------------------------------------------------------------
Element 202:
  page_name:      customers
  tag_name:       svg
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'xmlns': 'http://www.w3.org/2000/svg', 'width': '24', 'height': '24', 'viewBox': '0 0 24 24', 'fill': 'none', 'stroke': 'currentColor', 'stroke-width': '2', 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'class': 'lucide lucide-eye w-4 h-4', 'data-lov-id': 'src/pages/Customers.tsx:276:28', 'data-lov-name': 'Eye', 'data-component-path': 'src/pages/Customers.tsx', 'data-component-line': '276', 'data-component-file': 'Customers.tsx', 'data-component-name': 'Eye', 'data-component-content': '%7B%22className%22%3A%22w-4%20h-4%22%7D'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     Eye
  HTML:           <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" str
------------------------------------------------------------
Element 203:
  page_name:      customers
  tag_name:       path
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'d': 'M2.062 12.348a1 1 0 0 1 0-.696 10.75 10.75 0 0 1 19.876 0 1 1 0 0 1 0 .696 10.75 10.75 0 0 1-19.876 0'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <path d="M2.062 12.348a1 1 0 0 1 0-.696 10.75 10.75 0 0 1 19.876 0 1 1 0 0 1 0 .696 10.75 10.75 0 0 1-19.876 0"></path>
------------------------------------------------------------
Element 204:
  page_name:      customers
  tag_name:       circle
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'cx': '12', 'cy': '12', 'r': '3'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <circle cx="12" cy="12" r="3"></circle>
------------------------------------------------------------
Element 205:
  page_name:      customers
  tag_name:       button
  text:           
  id:             
  class:          inline-flex items-center justify-center gap-2 whitespace-nowrap text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0 hover:bg-accent hover:text-accent-foreground h-9 rounded-md px-3
  value:          
  placeholder:    
  type:           submit
  attributes:     {'data-lov-id': 'src/pages/Customers.tsx:414:22', 'data-lov-name': 'Button', 'data-component-path': 'src/pages/Customers.tsx', 'data-component-line': '414', 'data-component-file': 'Customers.tsx', 'data-component-name': 'Button', 'data-component-content': '%7B%7D', 'class': 'inline-flex items-center justify-center gap-2 whitespace-nowrap text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0 hover:bg-accent hover:text-accent-foreground h-9 rounded-md px-3'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     Button
  HTML:           <button data-lov-id="src/pages/Customers.tsx:414:22" data-lov-name="Button" data-component-path="src/pages/Customers.tsx
------------------------------------------------------------
Element 206:
  page_name:      customers
  tag_name:       svg
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'xmlns': 'http://www.w3.org/2000/svg', 'width': '24', 'height': '24', 'viewBox': '0 0 24 24', 'fill': 'none', 'stroke': 'currentColor', 'stroke-width': '2', 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'class': 'lucide lucide-square-pen w-4 h-4', 'data-lov-id': 'src/pages/Customers.tsx:415:24', 'data-lov-name': 'Edit', 'data-component-path': 'src/pages/Customers.tsx', 'data-component-line': '415', 'data-component-file': 'Customers.tsx', 'data-component-name': 'Edit', 'data-component-content': '%7B%22className%22%3A%22w-4%20h-4%22%7D'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     Edit
  HTML:           <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" str
------------------------------------------------------------
Element 207:
  page_name:      customers
  tag_name:       path
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'d': 'M12 3H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <path d="M12 3H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
------------------------------------------------------------
Element 208:
  page_name:      customers
  tag_name:       path
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'d': 'M18.375 2.625a1 1 0 0 1 3 3l-9.013 9.014a2 2 0 0 1-.853.505l-2.873.84a.5.5 0 0 1-.62-.62l.84-2.873a2 2 0 0 1 .506-.852z'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <path d="M18.375 2.625a1 1 0 0 1 3 3l-9.013 9.014a2 2 0 0 1-.853.505l-2.873.84a.5.5 0 0 1-.62-.62l.84-2.873a2 2 0 0 1 .5
------------------------------------------------------------
Element 209:
  page_name:      customers
  tag_name:       script
  text:           
  id:             
  class:          
  value:          
  placeholder:    
  type:           module
  attributes:     {'src': 'https://cdn.gpteng.co/lovable.js', 'type': 'module'}
  enable?         True
  visible?        False
  editable?       False
  label_text:     
  HTML:           <script src="https://cdn.gpteng.co/lovable.js" type="module"></script>
------------------------------------------------------------
Element 210:
  page_name:      customers
  tag_name:       a
  text:           Edit with 






















































	×
  id:             lovable-badge
  class:          
  value:          
  placeholder:    
  type:           
  attributes:     {'id': 'lovable-badge', 'target': '_blank', 'href': 'https://lovable.dev/projects/6b5a94f5-dd17-46dd-8f84-e0942fda5a0d?utm_source=lovable-badge'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <a id="lovable-badge" target="_blank" href="https://lovable.dev/projects/6b5a94f5-dd17-46dd-8f84-e0942fda5a0d?utm_source
------------------------------------------------------------
Element 211:
  page_name:      customers
  tag_name:       span
  text:           Edit with
  id:             
  class:          
  value:          
  placeholder:    
  type:           
  attributes:     {'style': 'color: #A1A1AA;'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <span style="color: #A1A1AA;">Edit with</span>
------------------------------------------------------------
Element 212:
  page_name:      customers
  tag_name:       svg
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'width': '60', 'height': '12', 'viewBox': '0 0 116 22', 'fill': 'none', 'xmlns': 'http://www.w3.org/2000/svg'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <svg width="60" height="12" viewBox="0 0 116 22" fill="none" xmlns="http://www.w3.org/2000/svg">
<path d="M109.108 21.11
------------------------------------------------------------
Element 213:
  page_name:      customers
  tag_name:       path
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'d': 'M109.108 21.115C107.649 21.115 106.381 20.8369 105.306 20.2807C104.23 19.7154 103.391 18.8675 102.789 17.7369C102.196 16.6063 101.9 15.2068 101.9 13.5382C101.9 11.9518 102.21 10.5841 102.83 9.4353C103.45 8.27736 104.307 7.3975 105.401 6.79574C106.495 6.19398 107.74 5.89309 109.135 5.89309C110.475 5.89309 111.665 6.18486 112.705 6.76839C113.744 7.35192 114.551 8.19986 115.125 9.31221C115.709 10.4246 116.001 11.7557 116.001 13.3057C116.001 13.8619 115.996 14.3041 115.987 14.6324H105.087V11.7603H113.347L111.788 12.2937C111.788 11.546 111.679 10.9215 111.46 10.42C111.25 9.90941 110.94 9.52647 110.53 9.27118C110.12 9.01588 109.623 8.88824 109.039 8.88824C108.428 8.88824 107.89 9.03868 107.425 9.33956C106.97 9.63133 106.614 10.069 106.359 10.6525C106.112 11.236 105.989 11.9381 105.989 12.7587V14.1674C105.989 15.0062 106.117 15.7174 106.372 16.3009C106.628 16.8844 106.992 17.3266 107.466 17.6275C107.941 17.9193 108.501 18.0651 109.149 18.0651C109.86 18.0651 110.448 17.8828 110.913 17.5181C111.378 17.1443 111.67 16.62 111.788 15.9453H115.932C115.805 17.0029 115.444 17.9193 114.852 18.6943C114.268 19.4693 113.489 20.0665 112.513 20.4859C111.537 20.9053 110.402 21.115 109.108 21.115Z', 'fill': '#FCFBF8'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <path d="M109.108 21.115C107.649 21.115 106.381 20.8369 105.306 20.2807C104.23 19.7154 103.391 18.8675 102.789 17.7369C1
------------------------------------------------------------
Element 214:
  page_name:      customers
  tag_name:       path
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'d': 'M96.5167 1.1061H100.661V20.7181H96.5167V1.1061Z', 'fill': '#FCFBF8'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <path d="M96.5167 1.1061H100.661V20.7181H96.5167V1.1061Z" fill="#FCFBF8"></path>
------------------------------------------------------------
Element 215:
  page_name:      customers
  tag_name:       path
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'d': 'M89.4649 21.1148C88.6808 21.1148 87.9788 20.978 87.3588 20.7045C86.7479 20.4309 86.2282 20.0207 85.7996 19.4736C85.3711 18.9174 85.052 18.2336 84.8423 17.4221L85.2799 17.5452V20.7182H81.177V6.28948H85.321V9.51713L84.856 9.59919C85.0657 8.82419 85.3848 8.16316 85.8133 7.6161C86.251 7.05992 86.7844 6.63595 87.4135 6.34419C88.0426 6.04331 88.7492 5.89287 89.5333 5.89287C90.7095 5.89287 91.7307 6.19831 92.5968 6.80919C93.463 7.42007 94.1286 8.29992 94.5936 9.44875C95.0586 10.5885 95.2911 11.9424 95.2911 13.5107C95.2911 15.0698 95.054 16.4237 94.5799 17.5726C94.1058 18.7123 93.4265 19.5876 92.5421 20.1984C91.6668 20.8093 90.6411 21.1148 89.4649 21.1148ZM88.1794 17.9555C88.7994 17.9555 89.3191 17.7732 89.7385 17.4084C90.167 17.0437 90.4861 16.5286 90.6958 15.863C90.9146 15.1974 91.0241 14.4133 91.0241 13.5107C91.0241 12.608 90.9146 11.8239 90.6958 11.1583C90.4861 10.4927 90.167 9.97757 89.7385 9.61286C89.3191 9.23904 88.7994 9.05213 88.1794 9.05213C87.5685 9.05213 87.0442 9.23904 86.6066 9.61286C86.178 9.97757 85.8544 10.4973 85.6355 11.172C85.4167 11.8376 85.3073 12.6171 85.3073 13.5107C85.3073 14.4133 85.4167 15.1974 85.6355 15.863C85.8544 16.5286 86.178 17.0437 86.6066 17.4084C87.0442 17.7732 87.5685 17.9555 88.1794 17.9555ZM81.177 1.1061H85.321V6.28948H81.177V1.1061Z', 'fill': '#FCFBF8'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <path d="M89.4649 21.1148C88.6808 21.1148 87.9788 20.978 87.3588 20.7045C86.7479 20.4309 86.2282 20.0207 85.7996 19.4736
------------------------------------------------------------
Element 216:
  page_name:      customers
  tag_name:       path
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'d': 'M70.7749 21.115C69.8723 21.115 69.0608 20.9372 68.3405 20.5816C67.6293 20.226 67.0686 19.72 66.6583 19.0635C66.2571 18.3979 66.0565 17.6229 66.0565 16.7385C66.0565 15.3891 66.4531 14.3588 67.2464 13.6476C68.0396 12.9274 69.1839 12.4578 70.6792 12.239L73.182 11.8834C73.6834 11.8104 74.08 11.7193 74.3718 11.6099C74.6636 11.5004 74.8778 11.3546 75.0146 11.1722C75.1514 10.9807 75.2197 10.7391 75.2197 10.4474C75.2197 10.1465 75.1377 9.87294 74.9736 9.62677C74.8186 9.37147 74.5815 9.17088 74.2624 9.025C73.9524 8.87 73.574 8.7925 73.1272 8.7925C72.4161 8.7925 71.8462 8.97941 71.4177 9.35324C70.9892 9.71794 70.7567 10.2194 70.7202 10.8576H66.4395C66.4759 9.89118 66.7677 9.03412 67.3148 8.28647C67.8709 7.52971 68.6414 6.94162 69.6261 6.52221C70.6108 6.1028 71.7505 5.89309 73.0452 5.89309C74.4037 5.89309 75.5525 6.11648 76.4917 6.56324C77.4308 7.00089 78.1374 7.63 78.6115 8.45059C79.0947 9.27118 79.3364 10.2513 79.3364 11.391V17.4087C79.3364 18.056 79.382 18.6578 79.4731 19.214C79.5734 19.761 79.7147 20.1075 79.8971 20.2534V20.7184H75.589C75.4887 20.3263 75.4112 19.8841 75.3565 19.3918C75.3018 18.8994 75.2699 18.3797 75.2608 17.8326L75.9309 17.5454C75.7577 18.1928 75.4386 18.79 74.9736 19.3371C74.5177 19.875 73.9296 20.3081 73.2093 20.6363C72.4981 20.9554 71.6867 21.115 70.7749 21.115ZM72.3067 18.0788C72.8902 18.0788 73.4053 17.9512 73.8521 17.6959C74.2989 17.4315 74.6408 17.0668 74.8778 16.6018C75.124 16.1368 75.2471 15.6079 75.2471 15.0153V13.1279L75.589 13.3194C75.3702 13.6112 75.0967 13.8346 74.7684 13.9896C74.4493 14.1446 74.0162 14.2768 73.4692 14.3862L72.4161 14.5913C71.714 14.7281 71.1852 14.9378 70.8296 15.2204C70.4831 15.5031 70.3099 15.8997 70.3099 16.4103C70.3099 16.9209 70.4968 17.3266 70.8706 17.6275C71.2445 17.9284 71.7231 18.0788 72.3067 18.0788Z', 'fill': '#FCFBF8'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <path d="M70.7749 21.115C69.8723 21.115 69.0608 20.9372 68.3405 20.5816C67.6293 20.226 67.0686 19.72 66.6583 19.0635C66.
------------------------------------------------------------
Element 217:
  page_name:      customers
  tag_name:       path
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'d': 'M51.962 6.28958H56.3659L60.1542 18.6668H58.8276L62.4656 6.28958H66.7463L61.7544 20.7182H57.1454L51.962 6.28958Z', 'fill': '#FCFBF8'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <path d="M51.962 6.28958H56.3659L60.1542 18.6668H58.8276L62.4656 6.28958H66.7463L61.7544 20.7182H57.1454L51.962 6.28958Z
------------------------------------------------------------
Element 218:
  page_name:      customers
  tag_name:       path
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'d': 'M45.4846 21.115C44.0531 21.115 42.7949 20.805 41.7099 20.185C40.634 19.565 39.7997 18.6806 39.2071 17.5318C38.6236 16.3829 38.3318 15.0381 38.3318 13.4972C38.3318 11.9563 38.6236 10.616 39.2071 9.47633C39.7997 8.3275 40.634 7.44309 41.7099 6.82309C42.7949 6.20309 44.0531 5.89309 45.4846 5.89309C46.916 5.89309 48.1697 6.20309 49.2456 6.82309C50.3215 7.44309 51.1512 8.3275 51.7347 9.47633C52.3274 10.616 52.6237 11.9563 52.6237 13.4972C52.6237 15.0381 52.3274 16.3829 51.7347 17.5318C51.1512 18.6806 50.3215 19.565 49.2456 20.185C48.1697 20.805 46.916 21.115 45.4846 21.115ZM45.4846 17.9421C46.0863 17.9421 46.6015 17.7779 47.03 17.4497C47.4585 17.1123 47.7868 16.6154 48.0147 15.959C48.2427 15.2934 48.3566 14.4728 48.3566 13.4972C48.3566 12.0475 48.1059 10.9488 47.6044 10.2012C47.103 9.44441 46.3963 9.06603 45.4846 9.06603C44.8828 9.06603 44.3631 9.23471 43.9255 9.57206C43.4969 9.9003 43.1687 10.3972 42.9408 11.0628C42.7128 11.7193 42.5988 12.5307 42.5988 13.4972C42.5988 14.4637 42.7128 15.2797 42.9408 15.9453C43.1687 16.6109 43.4969 17.1123 43.9255 17.4497C44.3631 17.7779 44.8828 17.9421 45.4846 17.9421Z', 'fill': '#FCFBF8'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <path d="M45.4846 21.115C44.0531 21.115 42.7949 20.805 41.7099 20.185C40.634 19.565 39.7997 18.6806 39.2071 17.5318C38.6
------------------------------------------------------------
Element 219:
  page_name:      customers
  tag_name:       path
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'d': 'M26.2195 1.10631H30.514V17.6623L29.7481 16.7734C29.7481 16.7734 31.8751 16.7734 35.534 16.7734C39.1928 16.7734 38.6925 20.7184 38.6925 20.7184H26.2195V1.10631Z', 'fill': '#FCFBF8'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <path d="M26.2195 1.10631H30.514V17.6623L29.7481 16.7734C29.7481 16.7734 31.8751 16.7734 35.534 16.7734C39.1928 16.7734 
------------------------------------------------------------
Element 220:
  page_name:      customers
  tag_name:       mask
  text:           
  id:             mask0_19703_15608
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'id': 'mask0_19703_15608', 'style': 'mask-type:alpha', 'maskUnits': 'userSpaceOnUse', 'x': '0', 'y': '0', 'width': '20', 'height': '21'}
  enable?         True
  visible?        False
  editable?       False
  label_text:     
  HTML:           <mask id="mask0_19703_15608" style="mask-type:alpha" maskUnits="userSpaceOnUse" x="0" y="0" width="20" height="21">
<pat
------------------------------------------------------------
Element 221:
  page_name:      customers
  tag_name:       path
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'fill-rule': 'evenodd', 'clip-rule': 'evenodd', 'd': 'M5.90405 0.885124C9.16477 0.885124 11.8081 3.53543 11.8081 6.80474V9.05456H13.773C17.0337 9.05456 19.677 11.7049 19.677 14.9742C19.677 18.2435 17.0337 20.8938 13.773 20.8938H0V6.80474C0 3.53543 2.64333 0.885124 5.90405 0.885124Z', 'fill': 'url(#paint0_linear_19703_15608)'}
  enable?         True
  visible?        False
  editable?       False
  label_text:     
  HTML:           <path fill-rule="evenodd" clip-rule="evenodd" d="M5.90405 0.885124C9.16477 0.885124 11.8081 3.53543 11.8081 6.80474V9.05
------------------------------------------------------------
Element 222:
  page_name:      customers
  tag_name:       g
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'mask': 'url(#mask0_19703_15608)'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <g mask="url(#mask0_19703_15608)">
<g filter="url(#filter0_f_19703_15608)">
<circle cx="8.63157" cy="11.5658" r="13.3199
------------------------------------------------------------
Element 223:
  page_name:      customers
  tag_name:       g
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'filter': 'url(#filter0_f_19703_15608)'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <g filter="url(#filter0_f_19703_15608)">
<circle cx="8.63157" cy="11.5658" r="13.3199" fill="#4B73FF"></circle>
</g>
------------------------------------------------------------
Element 224:
  page_name:      customers
  tag_name:       circle
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'cx': '8.63157', 'cy': '11.5658', 'r': '13.3199', 'fill': '#4B73FF'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <circle cx="8.63157" cy="11.5658" r="13.3199" fill="#4B73FF"></circle>
------------------------------------------------------------
Element 225:
  page_name:      customers
  tag_name:       g
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'filter': 'url(#filter1_f_19703_15608)'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <g filter="url(#filter1_f_19703_15608)">
<ellipse cx="10.0949" cy="4.25612" rx="17.0591" ry="13.3199" fill="#FF66F4"></e
------------------------------------------------------------
Element 226:
  page_name:      customers
  tag_name:       ellipse
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'cx': '10.0949', 'cy': '4.25612', 'rx': '17.0591', 'ry': '13.3199', 'fill': '#FF66F4'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <ellipse cx="10.0949" cy="4.25612" rx="17.0591" ry="13.3199" fill="#FF66F4"></ellipse>
------------------------------------------------------------
Element 227:
  page_name:      customers
  tag_name:       g
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'filter': 'url(#filter2_f_19703_15608)'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <g filter="url(#filter2_f_19703_15608)">
<ellipse cx="12.8775" cy="1.74957" rx="13.3199" ry="11.6977" fill="#FF0105"></e
------------------------------------------------------------
Element 228:
  page_name:      customers
  tag_name:       ellipse
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'cx': '12.8775', 'cy': '1.74957', 'rx': '13.3199', 'ry': '11.6977', 'fill': '#FF0105'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <ellipse cx="12.8775" cy="1.74957" rx="13.3199" ry="11.6977" fill="#FF0105"></ellipse>
------------------------------------------------------------
Element 229:
  page_name:      customers
  tag_name:       g
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'filter': 'url(#filter3_f_19703_15608)'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <g filter="url(#filter3_f_19703_15608)">
<circle cx="10.3319" cy="4.25254" r="8.01052" fill="#FE7B02"></circle>
</g>
------------------------------------------------------------
Element 230:
  page_name:      customers
  tag_name:       circle
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'cx': '10.3319', 'cy': '4.25254', 'r': '8.01052', 'fill': '#FE7B02'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <circle cx="10.3319" cy="4.25254" r="8.01052" fill="#FE7B02"></circle>
------------------------------------------------------------
Element 231:
  page_name:      customers
  tag_name:       defs
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {}
  enable?         True
  visible?        False
  editable?       False
  label_text:     
  HTML:           <defs>
<filter id="filter0_f_19703_15608" x="-10.6577" y="-7.72354" width="38.5786" height="38.5786" filterUnits="userSp
------------------------------------------------------------
Element 232:
  page_name:      customers
  tag_name:       filter
  text:           
  id:             filter0_f_19703_15608
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'id': 'filter0_f_19703_15608', 'x': '-10.6577', 'y': '-7.72354', 'width': '38.5786', 'height': '38.5786', 'filterUnits': 'userSpaceOnUse', 'color-interpolation-filters': 'sRGB'}
  enable?         True
  visible?        False
  editable?       False
  label_text:     
  HTML:           <filter id="filter0_f_19703_15608" x="-10.6577" y="-7.72354" width="38.5786" height="38.5786" filterUnits="userSpaceOnUs
------------------------------------------------------------
Element 233:
  page_name:      customers
  tag_name:       feflood
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'flood-opacity': '0', 'result': 'BackgroundImageFix'}
  enable?         True
  visible?        False
  editable?       False
  label_text:     
  HTML:           <feFlood flood-opacity="0" result="BackgroundImageFix"></feFlood>
------------------------------------------------------------
Element 234:
  page_name:      customers
  tag_name:       feblend
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'mode': 'normal', 'in': 'SourceGraphic', 'in2': 'BackgroundImageFix', 'result': 'shape'}
  enable?         True
  visible?        False
  editable?       False
  label_text:     
  HTML:           <feBlend mode="normal" in="SourceGraphic" in2="BackgroundImageFix" result="shape"></feBlend>
------------------------------------------------------------
Element 235:
  page_name:      customers
  tag_name:       fegaussianblur
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'stdDeviation': '2.98472', 'result': 'effect1_foregroundBlur_19703_15608'}
  enable?         True
  visible?        False
  editable?       False
  label_text:     
  HTML:           <feGaussianBlur stdDeviation="2.98472" result="effect1_foregroundBlur_19703_15608"></feGaussianBlur>
------------------------------------------------------------
Element 236:
  page_name:      customers
  tag_name:       filter
  text:           
  id:             filter1_f_19703_15608
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'id': 'filter1_f_19703_15608', 'x': '-12.9337', 'y': '-15.0332', 'width': '46.057', 'height': '38.5786', 'filterUnits': 'userSpaceOnUse', 'color-interpolation-filters': 'sRGB'}
  enable?         True
  visible?        False
  editable?       False
  label_text:     
  HTML:           <filter id="filter1_f_19703_15608" x="-12.9337" y="-15.0332" width="46.057" height="38.5786" filterUnits="userSpaceOnUse
------------------------------------------------------------
Element 237:
  page_name:      customers
  tag_name:       feflood
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'flood-opacity': '0', 'result': 'BackgroundImageFix'}
  enable?         True
  visible?        False
  editable?       False
  label_text:     
  HTML:           <feFlood flood-opacity="0" result="BackgroundImageFix"></feFlood>
------------------------------------------------------------
Element 238:
  page_name:      customers
  tag_name:       feblend
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'mode': 'normal', 'in': 'SourceGraphic', 'in2': 'BackgroundImageFix', 'result': 'shape'}
  enable?         True
  visible?        False
  editable?       False
  label_text:     
  HTML:           <feBlend mode="normal" in="SourceGraphic" in2="BackgroundImageFix" result="shape"></feBlend>
------------------------------------------------------------
Element 239:
  page_name:      customers
  tag_name:       fegaussianblur
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'stdDeviation': '2.98472', 'result': 'effect1_foregroundBlur_19703_15608'}
  enable?         True
  visible?        False
  editable?       False
  label_text:     
  HTML:           <feGaussianBlur stdDeviation="2.98472" result="effect1_foregroundBlur_19703_15608"></feGaussianBlur>
------------------------------------------------------------
Element 240:
  page_name:      customers
  tag_name:       filter
  text:           
  id:             filter2_f_19703_15608
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'id': 'filter2_f_19703_15608', 'x': '-6.41182', 'y': '-15.9176', 'width': '38.5786', 'height': '35.3342', 'filterUnits': 'userSpaceOnUse', 'color-interpolation-filters': 'sRGB'}
  enable?         True
  visible?        False
  editable?       False
  label_text:     
  HTML:           <filter id="filter2_f_19703_15608" x="-6.41182" y="-15.9176" width="38.5786" height="35.3342" filterUnits="userSpaceOnUs
------------------------------------------------------------
Element 241:
  page_name:      customers
  tag_name:       feflood
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'flood-opacity': '0', 'result': 'BackgroundImageFix'}
  enable?         True
  visible?        False
  editable?       False
  label_text:     
  HTML:           <feFlood flood-opacity="0" result="BackgroundImageFix"></feFlood>
------------------------------------------------------------
Element 242:
  page_name:      customers
  tag_name:       feblend
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'mode': 'normal', 'in': 'SourceGraphic', 'in2': 'BackgroundImageFix', 'result': 'shape'}
  enable?         True
  visible?        False
  editable?       False
  label_text:     
  HTML:           <feBlend mode="normal" in="SourceGraphic" in2="BackgroundImageFix" result="shape"></feBlend>
------------------------------------------------------------
Element 243:
  page_name:      customers
  tag_name:       fegaussianblur
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'stdDeviation': '2.98472', 'result': 'effect1_foregroundBlur_19703_15608'}
  enable?         True
  visible?        False
  editable?       False
  label_text:     
  HTML:           <feGaussianBlur stdDeviation="2.98472" result="effect1_foregroundBlur_19703_15608"></feGaussianBlur>
------------------------------------------------------------
Element 244:
  page_name:      customers
  tag_name:       filter
  text:           
  id:             filter3_f_19703_15608
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'id': 'filter3_f_19703_15608', 'x': '-3.64803', 'y': '-9.72742', 'width': '27.9599', 'height': '27.9599', 'filterUnits': 'userSpaceOnUse', 'color-interpolation-filters': 'sRGB'}
  enable?         True
  visible?        False
  editable?       False
  label_text:     
  HTML:           <filter id="filter3_f_19703_15608" x="-3.64803" y="-9.72742" width="27.9599" height="27.9599" filterUnits="userSpaceOnUs
------------------------------------------------------------
Element 245:
  page_name:      customers
  tag_name:       feflood
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'flood-opacity': '0', 'result': 'BackgroundImageFix'}
  enable?         True
  visible?        False
  editable?       False
  label_text:     
  HTML:           <feFlood flood-opacity="0" result="BackgroundImageFix"></feFlood>
------------------------------------------------------------
Element 246:
  page_name:      customers
  tag_name:       feblend
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'mode': 'normal', 'in': 'SourceGraphic', 'in2': 'BackgroundImageFix', 'result': 'shape'}
  enable?         True
  visible?        False
  editable?       False
  label_text:     
  HTML:           <feBlend mode="normal" in="SourceGraphic" in2="BackgroundImageFix" result="shape"></feBlend>
------------------------------------------------------------
Element 247:
  page_name:      customers
  tag_name:       fegaussianblur
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'stdDeviation': '2.98472', 'result': 'effect1_foregroundBlur_19703_15608'}
  enable?         True
  visible?        False
  editable?       False
  label_text:     
  HTML:           <feGaussianBlur stdDeviation="2.98472" result="effect1_foregroundBlur_19703_15608"></feGaussianBlur>
------------------------------------------------------------
Element 248:
  page_name:      customers
  tag_name:       lineargradient
  text:           
  id:             paint0_linear_19703_15608
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'id': 'paint0_linear_19703_15608', 'x1': '6.62168', 'y1': '4.40129', 'x2': '12.6165', 'y2': '20.8863', 'gradientUnits': 'userSpaceOnUse'}
  enable?         True
  visible?        False
  editable?       False
  label_text:     
  HTML:           <linearGradient id="paint0_linear_19703_15608" x1="6.62168" y1="4.40129" x2="12.6165" y2="20.8863" gradientUnits="userSp
------------------------------------------------------------
Element 249:
  page_name:      customers
  tag_name:       stop
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'offset': '0.025', 'stop-color': '#FF8E63'}
  enable?         True
  visible?        False
  editable?       False
  label_text:     
  HTML:           <stop offset="0.025" stop-color="#FF8E63"></stop>
------------------------------------------------------------
Element 250:
  page_name:      customers
  tag_name:       stop
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'offset': '0.56', 'stop-color': '#FF7EB0'}
  enable?         True
  visible?        False
  editable?       False
  label_text:     
  HTML:           <stop offset="0.56" stop-color="#FF7EB0"></stop>
------------------------------------------------------------
Element 251:
  page_name:      customers
  tag_name:       stop
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'offset': '0.95', 'stop-color': '#4B73FF'}
  enable?         True
  visible?        False
  editable?       False
  label_text:     
  HTML:           <stop offset="0.95" stop-color="#4B73FF"></stop>
------------------------------------------------------------
Element 252:
  page_name:      customers
  tag_name:       button
  text:           ×
  id:             lovable-badge-close
  class:          
  value:          
  placeholder:    
  type:           submit
  attributes:     {'id': 'lovable-badge-close', 'style': 'position: absolute; top: -2px; right: 5px; cursor: pointer; font-size: 14px; color: #A1A1AA;'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     ×
  HTML:           <button id="lovable-badge-close" style="position: absolute; top: -2px; right: 5px; cursor: pointer; font-size: 14px; col
------------------------------------------------------------
Element 253:
  page_name:      customers
  tag_name:       script
  text:           // Don't show the lovable-badge if the page is in an iframe or if it's being rendered by puppeteer (screenshot service)
	if (window.self !== window.top || navigator.userAgent.includes('puppeteer')) {
		// the page is in an iframe
		var badge = document.getElementById('lovable-badge');
		if (badge) {
			badge.style.display = 'none';
		}
	}

	// Add click event listener to close button
	var closeButton = document.getElementById('lovable-badge-close');
	if (closeButton) {
		closeButton.addEventListener('click', function(event) {
			event.preventDefault();
			event.stopPropagation();
			var badge = document.getElementById('lovable-badge');
			if (badge) {
				badge.style.display = 'none';
			}
		});
	}
  id:             
  class:          
  value:          
  placeholder:    
  type:           
  attributes:     {}
  enable?         True
  visible?        False
  editable?       False
  label_text:     
  HTML:           <script>
	// Don't show the lovable-badge if the page is in an iframe or if it's being rendered by puppeteer (screenshot
------------------------------------------------------------
Element 254:
  page_name:      customers
  tag_name:       span
  text:           0
  id:             recharts_measurement_span
  class:          
  value:          
  placeholder:    
  type:           
  attributes:     {'id': 'recharts_measurement_span', 'aria-hidden': 'true', 'style': 'position: absolute; top: -20000px; left: 0px; padding: 0px; margin: 0px; border: none; white-space: pre; font-size: 16px; letter-spacing: normal;'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <span id="recharts_measurement_span" aria-hidden="true" style="position: absolute; top: -20000px; left: 0px; padding: 0p
------------------------------------------------------------


# === FILE: generated_runs\src\ocr-dom-metadata\dom_elements_dashboard.txt ===
All DOM elements
Element 1:
  page_name:      dashboard
  tag_name:       div
  text:           Bank CRMNavigationDashboardCustomersLoansTransactionsTasksReportsAnalyticsSettingsToggle SidebarJohn DoeDashboardWelcome back! Here's your banking overview.Export ReportTotal Customers2,847+12.5% from last monthActive Loans$45.2M+8.2% from last monthMonthly Transactions18,394+15.3% from last monthRevenue Growth23.4%+2.1% from last monthLoan Portfolio TrendMonthly loan disbursements over the last 6 monthsJanFebMarAprMayJun01500000300000045000006000000Customer DistributionCustomer segments by account typePremium 35%Standard 45%Basic 20%Recent ActivitiesLatest customer interactions and transactionsSarah JohnsonLoan Application Approved$250,0002 hours agoMichael ChenAccount Verification Pending-4 hours agoEmma DavisLarge Transaction Alert$75,0006 hours agoRobert WilsonMonthly Payment Received$3,2008 hours ago
  id:             root
  class:          
  value:          
  placeholder:    
  type:           
  attributes:     {'id': 'root'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <div id="root"><div role="region" aria-label="Notifications (F8)" tabindex="-1" style="pointer-events: none;"><ol tabind
------------------------------------------------------------
Element 2:
  page_name:      dashboard
  tag_name:       div
  text:           
  id:             
  class:          
  value:          
  placeholder:    
  type:           
  attributes:     {'role': 'region', 'aria-label': 'Notifications (F8)', 'tabindex': '-1', 'style': 'pointer-events: none;'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     Notifications (F8)
  HTML:           <div role="region" aria-label="Notifications (F8)" tabindex="-1" style="pointer-events: none;"><ol tabindex="-1" data-lo
------------------------------------------------------------
Element 3:
  page_name:      dashboard
  tag_name:       ol
  text:           
  id:             
  class:          fixed top-0 z-[100] flex max-h-screen w-full flex-col-reverse p-4 sm:bottom-0 sm:right-0 sm:top-auto sm:flex-col md:max-w-[420px]
  value:          
  placeholder:    
  type:           
  attributes:     {'tabindex': '-1', 'data-lov-id': 'src/components/ui/toaster.tsx:30:6', 'data-lov-name': 'ToastViewport', 'data-component-path': 'src/components/ui/toaster.tsx', 'data-component-line': '30', 'data-component-file': 'toaster.tsx', 'data-component-name': 'ToastViewport', 'data-component-content': '%7B%7D', 'class': 'fixed top-0 z-[100] flex max-h-screen w-full flex-col-reverse p-4 sm:bottom-0 sm:right-0 sm:top-auto sm:flex-col md:max-w-[420px]'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     ToastViewport
  HTML:           <ol tabindex="-1" data-lov-id="src/components/ui/toaster.tsx:30:6" data-lov-name="ToastViewport" data-component-path="sr
------------------------------------------------------------
Element 4:
  page_name:      dashboard
  tag_name:       div
  text:           Bank CRMNavigationDashboardCustomersLoansTransactionsTasksReportsAnalyticsSettingsToggle SidebarJohn DoeDashboardWelcome back! Here's your banking overview.Export ReportTotal Customers2,847+12.5% from last monthActive Loans$45.2M+8.2% from last monthMonthly Transactions18,394+15.3% from last monthRevenue Growth23.4%+2.1% from last monthLoan Portfolio TrendMonthly loan disbursements over the last 6 monthsJanFebMarAprMayJun01500000300000045000006000000Customer DistributionCustomer segments by account typePremium 35%Standard 45%Basic 20%Recent ActivitiesLatest customer interactions and transactionsSarah JohnsonLoan Application Approved$250,0002 hours agoMichael ChenAccount Verification Pending-4 hours agoEmma DavisLarge Transaction Alert$75,0006 hours agoRobert WilsonMonthly Payment Received$3,2008 hours ago
  id:             
  class:          group/sidebar-wrapper flex min-h-svh w-full has-[[data-variant=inset]]:bg-sidebar
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/components/Layout.tsx:9:4', 'data-lov-name': 'SidebarProvider', 'data-component-path': 'src/components/Layout.tsx', 'data-component-line': '9', 'data-component-file': 'Layout.tsx', 'data-component-name': 'SidebarProvider', 'data-component-content': '%7B%7D', 'class': 'group/sidebar-wrapper flex min-h-svh w-full has-[[data-variant=inset]]:bg-sidebar', 'style': '--sidebar-width: 16rem; --sidebar-width-icon: 3rem;'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     SidebarProvider
  HTML:           <div data-lov-id="src/components/Layout.tsx:9:4" data-lov-name="SidebarProvider" data-component-path="src/components/Lay
------------------------------------------------------------
Element 5:
  page_name:      dashboard
  tag_name:       div
  text:           Bank CRMNavigationDashboardCustomersLoansTransactionsTasksReportsAnalyticsSettingsToggle SidebarJohn DoeDashboardWelcome back! Here's your banking overview.Export ReportTotal Customers2,847+12.5% from last monthActive Loans$45.2M+8.2% from last monthMonthly Transactions18,394+15.3% from last monthRevenue Growth23.4%+2.1% from last monthLoan Portfolio TrendMonthly loan disbursements over the last 6 monthsJanFebMarAprMayJun01500000300000045000006000000Customer DistributionCustomer segments by account typePremium 35%Standard 45%Basic 20%Recent ActivitiesLatest customer interactions and transactionsSarah JohnsonLoan Application Approved$250,0002 hours agoMichael ChenAccount Verification Pending-4 hours agoEmma DavisLarge Transaction Alert$75,0006 hours agoRobert WilsonMonthly Payment Received$3,2008 hours ago
  id:             
  class:          min-h-screen flex w-full bg-gray-50
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/components/Layout.tsx:10:6', 'data-lov-name': 'div', 'data-component-path': 'src/components/Layout.tsx', 'data-component-line': '10', 'data-component-file': 'Layout.tsx', 'data-component-name': 'div', 'data-component-content': '%7B%22className%22%3A%22min-h-screen%20flex%20w-full%20bg-gray-50%22%7D', 'class': 'min-h-screen flex w-full bg-gray-50'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     div
  HTML:           <div data-lov-id="src/components/Layout.tsx:10:6" data-lov-name="div" data-component-path="src/components/Layout.tsx" da
------------------------------------------------------------
Element 6:
  page_name:      dashboard
  tag_name:       div
  text:           Bank CRMNavigationDashboardCustomersLoansTransactionsTasksReportsAnalyticsSettings
  id:             
  class:          group peer hidden md:block text-sidebar-foreground
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/components/ui/sidebar.tsx:214:6', 'data-lov-name': 'div', 'data-component-path': 'src/components/ui/sidebar.tsx', 'data-component-line': '214', 'data-component-file': 'sidebar.tsx', 'data-component-name': 'div', 'data-component-content': '%7B%22className%22%3A%22group%20peer%20hidden%20md%3Ablock%20text-sidebar-foreground%22%7D', 'class': 'group peer hidden md:block text-sidebar-foreground', 'data-state': 'expanded', 'data-collapsible': '', 'data-variant': 'sidebar', 'data-side': 'left'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     div
  HTML:           <div data-lov-id="src/components/ui/sidebar.tsx:214:6" data-lov-name="div" data-component-path="src/components/ui/sideba
------------------------------------------------------------
Element 7:
  page_name:      dashboard
  tag_name:       div
  text:           
  id:             
  class:          duration-200 relative h-svh w-[--sidebar-width] bg-transparent transition-[width] ease-linear group-data-[collapsible=offcanvas]:w-0 group-data-[side=right]:rotate-180 group-data-[collapsible=icon]:w-[--sidebar-width-icon]
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/components/ui/sidebar.tsx:223:8', 'data-lov-name': 'div', 'data-component-path': 'src/components/ui/sidebar.tsx', 'data-component-line': '223', 'data-component-file': 'sidebar.tsx', 'data-component-name': 'div', 'data-component-content': '%7B%7D', 'class': 'duration-200 relative h-svh w-[--sidebar-width] bg-transparent transition-[width] ease-linear group-data-[collapsible=offcanvas]:w-0 group-data-[side=right]:rotate-180 group-data-[collapsible=icon]:w-[--sidebar-width-icon]'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     div
  HTML:           <div data-lov-id="src/components/ui/sidebar.tsx:223:8" data-lov-name="div" data-component-path="src/components/ui/sideba
------------------------------------------------------------
Element 8:
  page_name:      dashboard
  tag_name:       div
  text:           Bank CRMNavigationDashboardCustomersLoansTransactionsTasksReportsAnalyticsSettings
  id:             
  class:          duration-200 fixed inset-y-0 z-10 hidden h-svh w-[--sidebar-width] transition-[left,right,width] ease-linear md:flex left-0 group-data-[collapsible=offcanvas]:left-[calc(var(--sidebar-width)*-1)] group-data-[collapsible=icon]:w-[--sidebar-width-icon] group-data-[side=left]:border-r group-data-[side=right]:border-l border-r bg-sidebar
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/components/AppSidebar.tsx:57:4', 'data-lov-name': 'Sidebar', 'data-component-path': 'src/components/AppSidebar.tsx', 'data-component-line': '57', 'data-component-file': 'AppSidebar.tsx', 'data-component-name': 'Sidebar', 'data-component-content': '%7B%22className%22%3A%22border-r%20bg-sidebar%22%7D', 'class': 'duration-200 fixed inset-y-0 z-10 hidden h-svh w-[--sidebar-width] transition-[left,right,width] ease-linear md:flex left-0 group-data-[collapsible=offcanvas]:left-[calc(var(--sidebar-width)*-1)] group-data-[collapsible=icon]:w-[--sidebar-width-icon] group-data-[side=left]:border-r group-data-[side=right]:border-l border-r bg-sidebar'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     Sidebar
  HTML:           <div data-lov-id="src/components/AppSidebar.tsx:57:4" data-lov-name="Sidebar" data-component-path="src/components/AppSid
------------------------------------------------------------
Element 9:
  page_name:      dashboard
  tag_name:       div
  text:           Bank CRMNavigationDashboardCustomersLoansTransactionsTasksReportsAnalyticsSettings
  id:             
  class:          flex h-full w-full flex-col bg-sidebar group-data-[variant=floating]:rounded-lg group-data-[variant=floating]:border group-data-[variant=floating]:border-sidebar-border group-data-[variant=floating]:shadow
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/components/ui/sidebar.tsx:247:10', 'data-lov-name': 'div', 'data-component-path': 'src/components/ui/sidebar.tsx', 'data-component-line': '247', 'data-component-file': 'sidebar.tsx', 'data-component-name': 'div', 'data-component-content': '%7B%22className%22%3A%22flex%20h-full%20w-full%20flex-col%20bg-sidebar%20group-data-%5Bvariant%3Dfloating%5D%3Arounded-lg%20group-data-%5Bvariant%3Dfloating%5D%3Aborder%20group-data-%5Bvariant%3Dfloating%5D%3Aborder-sidebar-border%20group-data-%5Bvariant%3Dfloating%5D%3Ashadow%22%7D', 'data-sidebar': 'sidebar', 'class': 'flex h-full w-full flex-col bg-sidebar group-data-[variant=floating]:rounded-lg group-data-[variant=floating]:border group-data-[variant=floating]:border-sidebar-border group-data-[variant=floating]:shadow'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     div
  HTML:           <div data-lov-id="src/components/ui/sidebar.tsx:247:10" data-lov-name="div" data-component-path="src/components/ui/sideb
------------------------------------------------------------
Element 10:
  page_name:      dashboard
  tag_name:       div
  text:           Bank CRMNavigationDashboardCustomersLoansTransactionsTasksReportsAnalyticsSettings
  id:             
  class:          flex min-h-0 flex-1 flex-col gap-2 overflow-auto group-data-[collapsible=icon]:overflow-hidden bg-sidebar
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/components/AppSidebar.tsx:58:6', 'data-lov-name': 'SidebarContent', 'data-component-path': 'src/components/AppSidebar.tsx', 'data-component-line': '58', 'data-component-file': 'AppSidebar.tsx', 'data-component-name': 'SidebarContent', 'data-component-content': '%7B%22className%22%3A%22bg-sidebar%22%7D', 'data-sidebar': 'content', 'class': 'flex min-h-0 flex-1 flex-col gap-2 overflow-auto group-data-[collapsible=icon]:overflow-hidden bg-sidebar'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     SidebarContent
  HTML:           <div data-lov-id="src/components/AppSidebar.tsx:58:6" data-lov-name="SidebarContent" data-component-path="src/components
------------------------------------------------------------
Element 11:
  page_name:      dashboard
  tag_name:       div
  text:           Bank CRM
  id:             
  class:          p-6
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/components/AppSidebar.tsx:59:8', 'data-lov-name': 'div', 'data-component-path': 'src/components/AppSidebar.tsx', 'data-component-line': '59', 'data-component-file': 'AppSidebar.tsx', 'data-component-name': 'div', 'data-component-content': '%7B%22className%22%3A%22p-6%22%7D', 'class': 'p-6'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     div
  HTML:           <div data-lov-id="src/components/AppSidebar.tsx:59:8" data-lov-name="div" data-component-path="src/components/AppSidebar
------------------------------------------------------------
Element 12:
  page_name:      dashboard
  tag_name:       div
  text:           Bank CRM
  id:             
  class:          flex items-center gap-2
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/components/AppSidebar.tsx:60:10', 'data-lov-name': 'div', 'data-component-path': 'src/components/AppSidebar.tsx', 'data-component-line': '60', 'data-component-file': 'AppSidebar.tsx', 'data-component-name': 'div', 'data-component-content': '%7B%22className%22%3A%22flex%20items-center%20gap-2%22%7D', 'class': 'flex items-center gap-2'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     div
  HTML:           <div data-lov-id="src/components/AppSidebar.tsx:60:10" data-lov-name="div" data-component-path="src/components/AppSideba
------------------------------------------------------------
Element 13:
  page_name:      dashboard
  tag_name:       div
  text:           
  id:             
  class:          w-8 h-8 bg-white rounded-lg flex items-center justify-center
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/components/AppSidebar.tsx:61:12', 'data-lov-name': 'div', 'data-component-path': 'src/components/AppSidebar.tsx', 'data-component-line': '61', 'data-component-file': 'AppSidebar.tsx', 'data-component-name': 'div', 'data-component-content': '%7B%22className%22%3A%22w-8%20h-8%20bg-white%20rounded-lg%20flex%20items-center%20justify-center%22%7D', 'class': 'w-8 h-8 bg-white rounded-lg flex items-center justify-center'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     div
  HTML:           <div data-lov-id="src/components/AppSidebar.tsx:61:12" data-lov-name="div" data-component-path="src/components/AppSideba
------------------------------------------------------------
Element 14:
  page_name:      dashboard
  tag_name:       svg
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'xmlns': 'http://www.w3.org/2000/svg', 'width': '24', 'height': '24', 'viewBox': '0 0 24 24', 'fill': 'none', 'stroke': 'currentColor', 'stroke-width': '2', 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'class': 'lucide lucide-dollar-sign w-5 h-5 text-primary', 'data-lov-id': 'src/components/AppSidebar.tsx:62:14', 'data-lov-name': 'DollarSign', 'data-component-path': 'src/components/AppSidebar.tsx', 'data-component-line': '62', 'data-component-file': 'AppSidebar.tsx', 'data-component-name': 'DollarSign', 'data-component-content': '%7B%22className%22%3A%22w-5%20h-5%20text-primary%22%7D'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     DollarSign
  HTML:           <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" str
------------------------------------------------------------
Element 15:
  page_name:      dashboard
  tag_name:       line
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'x1': '12', 'x2': '12', 'y1': '2', 'y2': '22'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <line x1="12" x2="12" y1="2" y2="22"></line>
------------------------------------------------------------
Element 16:
  page_name:      dashboard
  tag_name:       path
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'d': 'M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"></path>
------------------------------------------------------------
Element 17:
  page_name:      dashboard
  tag_name:       div
  text:           Bank CRM
  id:             
  class:          text-sidebar-foreground
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/components/AppSidebar.tsx:65:14', 'data-lov-name': 'div', 'data-component-path': 'src/components/AppSidebar.tsx', 'data-component-line': '65', 'data-component-file': 'AppSidebar.tsx', 'data-component-name': 'div', 'data-component-content': '%7B%22className%22%3A%22text-sidebar-foreground%22%7D', 'class': 'text-sidebar-foreground'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     div
  HTML:           <div data-lov-id="src/components/AppSidebar.tsx:65:14" data-lov-name="div" data-component-path="src/components/AppSideba
------------------------------------------------------------
Element 18:
  page_name:      dashboard
  tag_name:       h2
  text:           Bank CRM
  id:             
  class:          font-bold text-lg
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/components/AppSidebar.tsx:66:16', 'data-lov-name': 'h2', 'data-component-path': 'src/components/AppSidebar.tsx', 'data-component-line': '66', 'data-component-file': 'AppSidebar.tsx', 'data-component-name': 'h2', 'data-component-content': '%7B%22text%22%3A%22Bank%20CRM%22%2C%22className%22%3A%22font-bold%20text-lg%22%7D', 'class': 'font-bold text-lg'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     h2
  HTML:           <h2 data-lov-id="src/components/AppSidebar.tsx:66:16" data-lov-name="h2" data-component-path="src/components/AppSidebar.
------------------------------------------------------------
Element 19:
  page_name:      dashboard
  tag_name:       div
  text:           NavigationDashboardCustomersLoansTransactionsTasksReportsAnalyticsSettings
  id:             
  class:          relative flex w-full min-w-0 flex-col p-2
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/components/AppSidebar.tsx:72:8', 'data-lov-name': 'SidebarGroup', 'data-component-path': 'src/components/AppSidebar.tsx', 'data-component-line': '72', 'data-component-file': 'AppSidebar.tsx', 'data-component-name': 'SidebarGroup', 'data-component-content': '%7B%7D', 'data-sidebar': 'group', 'class': 'relative flex w-full min-w-0 flex-col p-2'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     SidebarGroup
  HTML:           <div data-lov-id="src/components/AppSidebar.tsx:72:8" data-lov-name="SidebarGroup" data-component-path="src/components/A
------------------------------------------------------------
Element 20:
  page_name:      dashboard
  tag_name:       div
  text:           Navigation
  id:             
  class:          duration-200 flex h-8 shrink-0 items-center rounded-md px-2 text-xs font-medium outline-none ring-sidebar-ring transition-[margin,opa] ease-linear focus-visible:ring-2 [&>svg]:size-4 [&>svg]:shrink-0 group-data-[collapsible=icon]:-mt-8 group-data-[collapsible=icon]:opacity-0 text-sidebar-foreground/70
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/components/AppSidebar.tsx:73:10', 'data-lov-name': 'SidebarGroupLabel', 'data-component-path': 'src/components/AppSidebar.tsx', 'data-component-line': '73', 'data-component-file': 'AppSidebar.tsx', 'data-component-name': 'SidebarGroupLabel', 'data-component-content': '%7B%22className%22%3A%22text-sidebar-foreground%2F70%22%7D', 'data-sidebar': 'group-label', 'class': 'duration-200 flex h-8 shrink-0 items-center rounded-md px-2 text-xs font-medium outline-none ring-sidebar-ring transition-[margin,opa] ease-linear focus-visible:ring-2 [&>svg]:size-4 [&>svg]:shrink-0 group-data-[collapsible=icon]:-mt-8 group-data-[collapsible=icon]:opacity-0 text-sidebar-foreground/70'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     SidebarGroupLabel
  HTML:           <div data-lov-id="src/components/AppSidebar.tsx:73:10" data-lov-name="SidebarGroupLabel" data-component-path="src/compon
------------------------------------------------------------
Element 21:
  page_name:      dashboard
  tag_name:       div
  text:           DashboardCustomersLoansTransactionsTasksReportsAnalyticsSettings
  id:             
  class:          w-full text-sm
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/components/AppSidebar.tsx:76:10', 'data-lov-name': 'SidebarGroupContent', 'data-component-path': 'src/components/AppSidebar.tsx', 'data-component-line': '76', 'data-component-file': 'AppSidebar.tsx', 'data-component-name': 'SidebarGroupContent', 'data-component-content': '%7B%7D', 'data-sidebar': 'group-content', 'class': 'w-full text-sm'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     SidebarGroupContent
  HTML:           <div data-lov-id="src/components/AppSidebar.tsx:76:10" data-lov-name="SidebarGroupContent" data-component-path="src/comp
------------------------------------------------------------
Element 22:
  page_name:      dashboard
  tag_name:       ul
  text:           DashboardCustomersLoansTransactionsTasksReportsAnalyticsSettings
  id:             
  class:          flex w-full min-w-0 flex-col gap-1
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/components/AppSidebar.tsx:77:12', 'data-lov-name': 'SidebarMenu', 'data-component-path': 'src/components/AppSidebar.tsx', 'data-component-line': '77', 'data-component-file': 'AppSidebar.tsx', 'data-component-name': 'SidebarMenu', 'data-component-content': '%7B%7D', 'data-sidebar': 'menu', 'class': 'flex w-full min-w-0 flex-col gap-1'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     SidebarMenu
  HTML:           <ul data-lov-id="src/components/AppSidebar.tsx:77:12" data-lov-name="SidebarMenu" data-component-path="src/components/Ap
------------------------------------------------------------
Element 23:
  page_name:      dashboard
  tag_name:       li
  text:           Dashboard
  id:             
  class:          group/menu-item relative
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/components/AppSidebar.tsx:79:16', 'data-lov-name': 'SidebarMenuItem', 'data-component-path': 'src/components/AppSidebar.tsx', 'data-component-line': '79', 'data-component-file': 'AppSidebar.tsx', 'data-component-name': 'SidebarMenuItem', 'data-component-content': '%7B%7D', 'data-sidebar': 'menu-item', 'class': 'group/menu-item relative'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     SidebarMenuItem
  HTML:           <li data-lov-id="src/components/AppSidebar.tsx:79:16" data-lov-name="SidebarMenuItem" data-component-path="src/component
------------------------------------------------------------
Element 24:
  page_name:      dashboard
  tag_name:       a
  text:           Dashboard
  id:             
  class:          peer/menu-button flex w-full items-center gap-2 overflow-hidden rounded-md p-2 text-left outline-none ring-sidebar-ring transition-[width,height,padding] focus-visible:ring-2 active:bg-sidebar-accent active:text-sidebar-accent-foreground disabled:pointer-events-none disabled:opacity-50 group-has-[[data-sidebar=menu-action]]/menu-item:pr-8 aria-disabled:pointer-events-none aria-disabled:opacity-50 data-[active=true]:bg-sidebar-accent data-[active=true]:font-medium data-[active=true]:text-sidebar-accent-foreground data-[state=open]:hover:bg-sidebar-accent data-[state=open]:hover:text-sidebar-accent-foreground group-data-[collapsible=icon]:!size-8 group-data-[collapsible=icon]:!p-2 [&>span:last-child]:truncate [&>svg]:size-4 [&>svg]:shrink-0 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground h-8 text-sm w-full justify-start transition-colors bg-sidebar-accent text-sidebar-accent-foreground active
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/components/AppSidebar.tsx:81:20', 'data-lov-name': 'NavLink', 'data-component-path': 'src/components/AppSidebar.tsx', 'data-component-line': '81', 'data-component-file': 'AppSidebar.tsx', 'data-component-name': 'NavLink', 'data-component-content': '%7B%7D', 'data-sidebar': 'menu-button', 'data-size': 'default', 'data-active': 'false', 'aria-current': 'page', 'class': 'peer/menu-button flex w-full items-center gap-2 overflow-hidden rounded-md p-2 text-left outline-none ring-sidebar-ring transition-[width,height,padding] focus-visible:ring-2 active:bg-sidebar-accent active:text-sidebar-accent-foreground disabled:pointer-events-none disabled:opacity-50 group-has-[[data-sidebar=menu-action]]/menu-item:pr-8 aria-disabled:pointer-events-none aria-disabled:opacity-50 data-[active=true]:bg-sidebar-accent data-[active=true]:font-medium data-[active=true]:text-sidebar-accent-foreground data-[state=open]:hover:bg-sidebar-accent data-[state=open]:hover:text-sidebar-accent-foreground group-data-[collapsible=icon]:!size-8 group-data-[collapsible=icon]:!p-2 [&>span:last-child]:truncate [&>svg]:size-4 [&>svg]:shrink-0 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground h-8 text-sm w-full justify-start transition-colors bg-sidebar-accent text-sidebar-accent-foreground active', 'href': '/'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     NavLink
  HTML:           <a data-lov-id="src/components/AppSidebar.tsx:81:20" data-lov-name="NavLink" data-component-path="src/components/AppSide
------------------------------------------------------------
Element 25:
  page_name:      dashboard
  tag_name:       svg
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'xmlns': 'http://www.w3.org/2000/svg', 'width': '24', 'height': '24', 'viewBox': '0 0 24 24', 'fill': 'none', 'stroke': 'currentColor', 'stroke-width': '2', 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'class': 'lucide lucide-house w-4 h-4', 'data-lov-id': 'src/components/AppSidebar.tsx:82:22', 'data-lov-name': 'item.icon', 'data-component-path': 'src/components/AppSidebar.tsx', 'data-component-line': '82', 'data-component-file': 'AppSidebar.tsx', 'data-component-name': 'item.icon', 'data-component-content': '%7B%22className%22%3A%22w-4%20h-4%22%7D'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     item.icon
  HTML:           <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" str
------------------------------------------------------------
Element 26:
  page_name:      dashboard
  tag_name:       path
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'d': 'M15 21v-8a1 1 0 0 0-1-1h-4a1 1 0 0 0-1 1v8'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <path d="M15 21v-8a1 1 0 0 0-1-1h-4a1 1 0 0 0-1 1v8"></path>
------------------------------------------------------------
Element 27:
  page_name:      dashboard
  tag_name:       path
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'d': 'M3 10a2 2 0 0 1 .709-1.528l7-5.999a2 2 0 0 1 2.582 0l7 5.999A2 2 0 0 1 21 10v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <path d="M3 10a2 2 0 0 1 .709-1.528l7-5.999a2 2 0 0 1 2.582 0l7 5.999A2 2 0 0 1 21 10v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z">
------------------------------------------------------------
Element 28:
  page_name:      dashboard
  tag_name:       span
  text:           Dashboard
  id:             
  class:          
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/components/AppSidebar.tsx:83:39', 'data-lov-name': 'span', 'data-component-path': 'src/components/AppSidebar.tsx', 'data-component-line': '83', 'data-component-file': 'AppSidebar.tsx', 'data-component-name': 'span', 'data-component-content': '%7B%7D'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     span
  HTML:           <span data-lov-id="src/components/AppSidebar.tsx:83:39" data-lov-name="span" data-component-path="src/components/AppSide
------------------------------------------------------------
Element 29:
  page_name:      dashboard
  tag_name:       li
  text:           Customers
  id:             
  class:          group/menu-item relative
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/components/AppSidebar.tsx:79:16', 'data-lov-name': 'SidebarMenuItem', 'data-component-path': 'src/components/AppSidebar.tsx', 'data-component-line': '79', 'data-component-file': 'AppSidebar.tsx', 'data-component-name': 'SidebarMenuItem', 'data-component-content': '%7B%7D', 'data-sidebar': 'menu-item', 'class': 'group/menu-item relative'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     SidebarMenuItem
  HTML:           <li data-lov-id="src/components/AppSidebar.tsx:79:16" data-lov-name="SidebarMenuItem" data-component-path="src/component
------------------------------------------------------------
Element 30:
  page_name:      dashboard
  tag_name:       a
  text:           Customers
  id:             
  class:          peer/menu-button flex w-full items-center gap-2 overflow-hidden rounded-md p-2 text-left outline-none ring-sidebar-ring transition-[width,height,padding] focus-visible:ring-2 active:bg-sidebar-accent active:text-sidebar-accent-foreground disabled:pointer-events-none disabled:opacity-50 group-has-[[data-sidebar=menu-action]]/menu-item:pr-8 aria-disabled:pointer-events-none aria-disabled:opacity-50 data-[active=true]:bg-sidebar-accent data-[active=true]:font-medium data-[active=true]:text-sidebar-accent-foreground data-[state=open]:hover:bg-sidebar-accent data-[state=open]:hover:text-sidebar-accent-foreground group-data-[collapsible=icon]:!size-8 group-data-[collapsible=icon]:!p-2 [&>span:last-child]:truncate [&>svg]:size-4 [&>svg]:shrink-0 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground h-8 text-sm w-full justify-start transition-colors hover:bg-sidebar-accent hover:text-sidebar-accent-foreground
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/components/AppSidebar.tsx:81:20', 'data-lov-name': 'NavLink', 'data-component-path': 'src/components/AppSidebar.tsx', 'data-component-line': '81', 'data-component-file': 'AppSidebar.tsx', 'data-component-name': 'NavLink', 'data-component-content': '%7B%7D', 'data-sidebar': 'menu-button', 'data-size': 'default', 'data-active': 'false', 'class': 'peer/menu-button flex w-full items-center gap-2 overflow-hidden rounded-md p-2 text-left outline-none ring-sidebar-ring transition-[width,height,padding] focus-visible:ring-2 active:bg-sidebar-accent active:text-sidebar-accent-foreground disabled:pointer-events-none disabled:opacity-50 group-has-[[data-sidebar=menu-action]]/menu-item:pr-8 aria-disabled:pointer-events-none aria-disabled:opacity-50 data-[active=true]:bg-sidebar-accent data-[active=true]:font-medium data-[active=true]:text-sidebar-accent-foreground data-[state=open]:hover:bg-sidebar-accent data-[state=open]:hover:text-sidebar-accent-foreground group-data-[collapsible=icon]:!size-8 group-data-[collapsible=icon]:!p-2 [&>span:last-child]:truncate [&>svg]:size-4 [&>svg]:shrink-0 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground h-8 text-sm w-full justify-start transition-colors hover:bg-sidebar-accent hover:text-sidebar-accent-foreground', 'href': '/customers'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     NavLink
  HTML:           <a data-lov-id="src/components/AppSidebar.tsx:81:20" data-lov-name="NavLink" data-component-path="src/components/AppSide
------------------------------------------------------------
Element 31:
  page_name:      dashboard
  tag_name:       svg
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'xmlns': 'http://www.w3.org/2000/svg', 'width': '24', 'height': '24', 'viewBox': '0 0 24 24', 'fill': 'none', 'stroke': 'currentColor', 'stroke-width': '2', 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'class': 'lucide lucide-users w-4 h-4', 'data-lov-id': 'src/components/AppSidebar.tsx:82:22', 'data-lov-name': 'item.icon', 'data-component-path': 'src/components/AppSidebar.tsx', 'data-component-line': '82', 'data-component-file': 'AppSidebar.tsx', 'data-component-name': 'item.icon', 'data-component-content': '%7B%22className%22%3A%22w-4%20h-4%22%7D'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     item.icon
  HTML:           <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" str
------------------------------------------------------------
Element 32:
  page_name:      dashboard
  tag_name:       path
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'d': 'M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"></path>
------------------------------------------------------------
Element 33:
  page_name:      dashboard
  tag_name:       circle
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'cx': '9', 'cy': '7', 'r': '4'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <circle cx="9" cy="7" r="4"></circle>
------------------------------------------------------------
Element 34:
  page_name:      dashboard
  tag_name:       path
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'d': 'M22 21v-2a4 4 0 0 0-3-3.87'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <path d="M22 21v-2a4 4 0 0 0-3-3.87"></path>
------------------------------------------------------------
Element 35:
  page_name:      dashboard
  tag_name:       path
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'d': 'M16 3.13a4 4 0 0 1 0 7.75'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <path d="M16 3.13a4 4 0 0 1 0 7.75"></path>
------------------------------------------------------------
Element 36:
  page_name:      dashboard
  tag_name:       span
  text:           Customers
  id:             
  class:          
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/components/AppSidebar.tsx:83:39', 'data-lov-name': 'span', 'data-component-path': 'src/components/AppSidebar.tsx', 'data-component-line': '83', 'data-component-file': 'AppSidebar.tsx', 'data-component-name': 'span', 'data-component-content': '%7B%7D'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     span
  HTML:           <span data-lov-id="src/components/AppSidebar.tsx:83:39" data-lov-name="span" data-component-path="src/components/AppSide
------------------------------------------------------------
Element 37:
  page_name:      dashboard
  tag_name:       li
  text:           Loans
  id:             
  class:          group/menu-item relative
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/components/AppSidebar.tsx:79:16', 'data-lov-name': 'SidebarMenuItem', 'data-component-path': 'src/components/AppSidebar.tsx', 'data-component-line': '79', 'data-component-file': 'AppSidebar.tsx', 'data-component-name': 'SidebarMenuItem', 'data-component-content': '%7B%7D', 'data-sidebar': 'menu-item', 'class': 'group/menu-item relative'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     SidebarMenuItem
  HTML:           <li data-lov-id="src/components/AppSidebar.tsx:79:16" data-lov-name="SidebarMenuItem" data-component-path="src/component
------------------------------------------------------------
Element 38:
  page_name:      dashboard
  tag_name:       a
  text:           Loans
  id:             
  class:          peer/menu-button flex w-full items-center gap-2 overflow-hidden rounded-md p-2 text-left outline-none ring-sidebar-ring transition-[width,height,padding] focus-visible:ring-2 active:bg-sidebar-accent active:text-sidebar-accent-foreground disabled:pointer-events-none disabled:opacity-50 group-has-[[data-sidebar=menu-action]]/menu-item:pr-8 aria-disabled:pointer-events-none aria-disabled:opacity-50 data-[active=true]:bg-sidebar-accent data-[active=true]:font-medium data-[active=true]:text-sidebar-accent-foreground data-[state=open]:hover:bg-sidebar-accent data-[state=open]:hover:text-sidebar-accent-foreground group-data-[collapsible=icon]:!size-8 group-data-[collapsible=icon]:!p-2 [&>span:last-child]:truncate [&>svg]:size-4 [&>svg]:shrink-0 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground h-8 text-sm w-full justify-start transition-colors hover:bg-sidebar-accent hover:text-sidebar-accent-foreground
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/components/AppSidebar.tsx:81:20', 'data-lov-name': 'NavLink', 'data-component-path': 'src/components/AppSidebar.tsx', 'data-component-line': '81', 'data-component-file': 'AppSidebar.tsx', 'data-component-name': 'NavLink', 'data-component-content': '%7B%7D', 'data-sidebar': 'menu-button', 'data-size': 'default', 'data-active': 'false', 'class': 'peer/menu-button flex w-full items-center gap-2 overflow-hidden rounded-md p-2 text-left outline-none ring-sidebar-ring transition-[width,height,padding] focus-visible:ring-2 active:bg-sidebar-accent active:text-sidebar-accent-foreground disabled:pointer-events-none disabled:opacity-50 group-has-[[data-sidebar=menu-action]]/menu-item:pr-8 aria-disabled:pointer-events-none aria-disabled:opacity-50 data-[active=true]:bg-sidebar-accent data-[active=true]:font-medium data-[active=true]:text-sidebar-accent-foreground data-[state=open]:hover:bg-sidebar-accent data-[state=open]:hover:text-sidebar-accent-foreground group-data-[collapsible=icon]:!size-8 group-data-[collapsible=icon]:!p-2 [&>span:last-child]:truncate [&>svg]:size-4 [&>svg]:shrink-0 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground h-8 text-sm w-full justify-start transition-colors hover:bg-sidebar-accent hover:text-sidebar-accent-foreground', 'href': '/loans'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     NavLink
  HTML:           <a data-lov-id="src/components/AppSidebar.tsx:81:20" data-lov-name="NavLink" data-component-path="src/components/AppSide
------------------------------------------------------------
Element 39:
  page_name:      dashboard
  tag_name:       svg
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'xmlns': 'http://www.w3.org/2000/svg', 'width': '24', 'height': '24', 'viewBox': '0 0 24 24', 'fill': 'none', 'stroke': 'currentColor', 'stroke-width': '2', 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'class': 'lucide lucide-dollar-sign w-4 h-4', 'data-lov-id': 'src/components/AppSidebar.tsx:82:22', 'data-lov-name': 'item.icon', 'data-component-path': 'src/components/AppSidebar.tsx', 'data-component-line': '82', 'data-component-file': 'AppSidebar.tsx', 'data-component-name': 'item.icon', 'data-component-content': '%7B%22className%22%3A%22w-4%20h-4%22%7D'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     item.icon
  HTML:           <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" str
------------------------------------------------------------
Element 40:
  page_name:      dashboard
  tag_name:       line
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'x1': '12', 'x2': '12', 'y1': '2', 'y2': '22'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <line x1="12" x2="12" y1="2" y2="22"></line>
------------------------------------------------------------
Element 41:
  page_name:      dashboard
  tag_name:       path
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'d': 'M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"></path>
------------------------------------------------------------
Element 42:
  page_name:      dashboard
  tag_name:       span
  text:           Loans
  id:             
  class:          
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/components/AppSidebar.tsx:83:39', 'data-lov-name': 'span', 'data-component-path': 'src/components/AppSidebar.tsx', 'data-component-line': '83', 'data-component-file': 'AppSidebar.tsx', 'data-component-name': 'span', 'data-component-content': '%7B%7D'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     span
  HTML:           <span data-lov-id="src/components/AppSidebar.tsx:83:39" data-lov-name="span" data-component-path="src/components/AppSide
------------------------------------------------------------
Element 43:
  page_name:      dashboard
  tag_name:       li
  text:           Transactions
  id:             
  class:          group/menu-item relative
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/components/AppSidebar.tsx:79:16', 'data-lov-name': 'SidebarMenuItem', 'data-component-path': 'src/components/AppSidebar.tsx', 'data-component-line': '79', 'data-component-file': 'AppSidebar.tsx', 'data-component-name': 'SidebarMenuItem', 'data-component-content': '%7B%7D', 'data-sidebar': 'menu-item', 'class': 'group/menu-item relative'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     SidebarMenuItem
  HTML:           <li data-lov-id="src/components/AppSidebar.tsx:79:16" data-lov-name="SidebarMenuItem" data-component-path="src/component
------------------------------------------------------------
Element 44:
  page_name:      dashboard
  tag_name:       a
  text:           Transactions
  id:             
  class:          peer/menu-button flex w-full items-center gap-2 overflow-hidden rounded-md p-2 text-left outline-none ring-sidebar-ring transition-[width,height,padding] focus-visible:ring-2 active:bg-sidebar-accent active:text-sidebar-accent-foreground disabled:pointer-events-none disabled:opacity-50 group-has-[[data-sidebar=menu-action]]/menu-item:pr-8 aria-disabled:pointer-events-none aria-disabled:opacity-50 data-[active=true]:bg-sidebar-accent data-[active=true]:font-medium data-[active=true]:text-sidebar-accent-foreground data-[state=open]:hover:bg-sidebar-accent data-[state=open]:hover:text-sidebar-accent-foreground group-data-[collapsible=icon]:!size-8 group-data-[collapsible=icon]:!p-2 [&>span:last-child]:truncate [&>svg]:size-4 [&>svg]:shrink-0 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground h-8 text-sm w-full justify-start transition-colors hover:bg-sidebar-accent hover:text-sidebar-accent-foreground
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/components/AppSidebar.tsx:81:20', 'data-lov-name': 'NavLink', 'data-component-path': 'src/components/AppSidebar.tsx', 'data-component-line': '81', 'data-component-file': 'AppSidebar.tsx', 'data-component-name': 'NavLink', 'data-component-content': '%7B%7D', 'data-sidebar': 'menu-button', 'data-size': 'default', 'data-active': 'false', 'class': 'peer/menu-button flex w-full items-center gap-2 overflow-hidden rounded-md p-2 text-left outline-none ring-sidebar-ring transition-[width,height,padding] focus-visible:ring-2 active:bg-sidebar-accent active:text-sidebar-accent-foreground disabled:pointer-events-none disabled:opacity-50 group-has-[[data-sidebar=menu-action]]/menu-item:pr-8 aria-disabled:pointer-events-none aria-disabled:opacity-50 data-[active=true]:bg-sidebar-accent data-[active=true]:font-medium data-[active=true]:text-sidebar-accent-foreground data-[state=open]:hover:bg-sidebar-accent data-[state=open]:hover:text-sidebar-accent-foreground group-data-[collapsible=icon]:!size-8 group-data-[collapsible=icon]:!p-2 [&>span:last-child]:truncate [&>svg]:size-4 [&>svg]:shrink-0 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground h-8 text-sm w-full justify-start transition-colors hover:bg-sidebar-accent hover:text-sidebar-accent-foreground', 'href': '/transactions'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     NavLink
  HTML:           <a data-lov-id="src/components/AppSidebar.tsx:81:20" data-lov-name="NavLink" data-component-path="src/components/AppSide
------------------------------------------------------------
Element 45:
  page_name:      dashboard
  tag_name:       svg
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'xmlns': 'http://www.w3.org/2000/svg', 'width': '24', 'height': '24', 'viewBox': '0 0 24 24', 'fill': 'none', 'stroke': 'currentColor', 'stroke-width': '2', 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'class': 'lucide lucide-credit-card w-4 h-4', 'data-lov-id': 'src/components/AppSidebar.tsx:82:22', 'data-lov-name': 'item.icon', 'data-component-path': 'src/components/AppSidebar.tsx', 'data-component-line': '82', 'data-component-file': 'AppSidebar.tsx', 'data-component-name': 'item.icon', 'data-component-content': '%7B%22className%22%3A%22w-4%20h-4%22%7D'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     item.icon
  HTML:           <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" str
------------------------------------------------------------
Element 46:
  page_name:      dashboard
  tag_name:       rect
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'width': '20', 'height': '14', 'x': '2', 'y': '5', 'rx': '2'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <rect width="20" height="14" x="2" y="5" rx="2"></rect>
------------------------------------------------------------
Element 47:
  page_name:      dashboard
  tag_name:       line
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'x1': '2', 'x2': '22', 'y1': '10', 'y2': '10'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <line x1="2" x2="22" y1="10" y2="10"></line>
------------------------------------------------------------
Element 48:
  page_name:      dashboard
  tag_name:       span
  text:           Transactions
  id:             
  class:          
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/components/AppSidebar.tsx:83:39', 'data-lov-name': 'span', 'data-component-path': 'src/components/AppSidebar.tsx', 'data-component-line': '83', 'data-component-file': 'AppSidebar.tsx', 'data-component-name': 'span', 'data-component-content': '%7B%7D'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     span
  HTML:           <span data-lov-id="src/components/AppSidebar.tsx:83:39" data-lov-name="span" data-component-path="src/components/AppSide
------------------------------------------------------------
Element 49:
  page_name:      dashboard
  tag_name:       li
  text:           Tasks
  id:             
  class:          group/menu-item relative
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/components/AppSidebar.tsx:79:16', 'data-lov-name': 'SidebarMenuItem', 'data-component-path': 'src/components/AppSidebar.tsx', 'data-component-line': '79', 'data-component-file': 'AppSidebar.tsx', 'data-component-name': 'SidebarMenuItem', 'data-component-content': '%7B%7D', 'data-sidebar': 'menu-item', 'class': 'group/menu-item relative'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     SidebarMenuItem
  HTML:           <li data-lov-id="src/components/AppSidebar.tsx:79:16" data-lov-name="SidebarMenuItem" data-component-path="src/component
------------------------------------------------------------
Element 50:
  page_name:      dashboard
  tag_name:       a
  text:           Tasks
  id:             
  class:          peer/menu-button flex w-full items-center gap-2 overflow-hidden rounded-md p-2 text-left outline-none ring-sidebar-ring transition-[width,height,padding] focus-visible:ring-2 active:bg-sidebar-accent active:text-sidebar-accent-foreground disabled:pointer-events-none disabled:opacity-50 group-has-[[data-sidebar=menu-action]]/menu-item:pr-8 aria-disabled:pointer-events-none aria-disabled:opacity-50 data-[active=true]:bg-sidebar-accent data-[active=true]:font-medium data-[active=true]:text-sidebar-accent-foreground data-[state=open]:hover:bg-sidebar-accent data-[state=open]:hover:text-sidebar-accent-foreground group-data-[collapsible=icon]:!size-8 group-data-[collapsible=icon]:!p-2 [&>span:last-child]:truncate [&>svg]:size-4 [&>svg]:shrink-0 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground h-8 text-sm w-full justify-start transition-colors hover:bg-sidebar-accent hover:text-sidebar-accent-foreground
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/components/AppSidebar.tsx:81:20', 'data-lov-name': 'NavLink', 'data-component-path': 'src/components/AppSidebar.tsx', 'data-component-line': '81', 'data-component-file': 'AppSidebar.tsx', 'data-component-name': 'NavLink', 'data-component-content': '%7B%7D', 'data-sidebar': 'menu-button', 'data-size': 'default', 'data-active': 'false', 'class': 'peer/menu-button flex w-full items-center gap-2 overflow-hidden rounded-md p-2 text-left outline-none ring-sidebar-ring transition-[width,height,padding] focus-visible:ring-2 active:bg-sidebar-accent active:text-sidebar-accent-foreground disabled:pointer-events-none disabled:opacity-50 group-has-[[data-sidebar=menu-action]]/menu-item:pr-8 aria-disabled:pointer-events-none aria-disabled:opacity-50 data-[active=true]:bg-sidebar-accent data-[active=true]:font-medium data-[active=true]:text-sidebar-accent-foreground data-[state=open]:hover:bg-sidebar-accent data-[state=open]:hover:text-sidebar-accent-foreground group-data-[collapsible=icon]:!size-8 group-data-[collapsible=icon]:!p-2 [&>span:last-child]:truncate [&>svg]:size-4 [&>svg]:shrink-0 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground h-8 text-sm w-full justify-start transition-colors hover:bg-sidebar-accent hover:text-sidebar-accent-foreground', 'href': '/tasks'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     NavLink
  HTML:           <a data-lov-id="src/components/AppSidebar.tsx:81:20" data-lov-name="NavLink" data-component-path="src/components/AppSide
------------------------------------------------------------
Element 51:
  page_name:      dashboard
  tag_name:       svg
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'xmlns': 'http://www.w3.org/2000/svg', 'width': '24', 'height': '24', 'viewBox': '0 0 24 24', 'fill': 'none', 'stroke': 'currentColor', 'stroke-width': '2', 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'class': 'lucide lucide-square-check-big w-4 h-4', 'data-lov-id': 'src/components/AppSidebar.tsx:82:22', 'data-lov-name': 'item.icon', 'data-component-path': 'src/components/AppSidebar.tsx', 'data-component-line': '82', 'data-component-file': 'AppSidebar.tsx', 'data-component-name': 'item.icon', 'data-component-content': '%7B%22className%22%3A%22w-4%20h-4%22%7D'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     item.icon
  HTML:           <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" str
------------------------------------------------------------
Element 52:
  page_name:      dashboard
  tag_name:       path
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'d': 'M21 10.5V19a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h12.5'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <path d="M21 10.5V19a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h12.5"></path>
------------------------------------------------------------
Element 53:
  page_name:      dashboard
  tag_name:       path
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'d': 'm9 11 3 3L22 4'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <path d="m9 11 3 3L22 4"></path>
------------------------------------------------------------
Element 54:
  page_name:      dashboard
  tag_name:       span
  text:           Tasks
  id:             
  class:          
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/components/AppSidebar.tsx:83:39', 'data-lov-name': 'span', 'data-component-path': 'src/components/AppSidebar.tsx', 'data-component-line': '83', 'data-component-file': 'AppSidebar.tsx', 'data-component-name': 'span', 'data-component-content': '%7B%7D'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     span
  HTML:           <span data-lov-id="src/components/AppSidebar.tsx:83:39" data-lov-name="span" data-component-path="src/components/AppSide
------------------------------------------------------------
Element 55:
  page_name:      dashboard
  tag_name:       li
  text:           Reports
  id:             
  class:          group/menu-item relative
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/components/AppSidebar.tsx:79:16', 'data-lov-name': 'SidebarMenuItem', 'data-component-path': 'src/components/AppSidebar.tsx', 'data-component-line': '79', 'data-component-file': 'AppSidebar.tsx', 'data-component-name': 'SidebarMenuItem', 'data-component-content': '%7B%7D', 'data-sidebar': 'menu-item', 'class': 'group/menu-item relative'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     SidebarMenuItem
  HTML:           <li data-lov-id="src/components/AppSidebar.tsx:79:16" data-lov-name="SidebarMenuItem" data-component-path="src/component
------------------------------------------------------------
Element 56:
  page_name:      dashboard
  tag_name:       a
  text:           Reports
  id:             
  class:          peer/menu-button flex w-full items-center gap-2 overflow-hidden rounded-md p-2 text-left outline-none ring-sidebar-ring transition-[width,height,padding] focus-visible:ring-2 active:bg-sidebar-accent active:text-sidebar-accent-foreground disabled:pointer-events-none disabled:opacity-50 group-has-[[data-sidebar=menu-action]]/menu-item:pr-8 aria-disabled:pointer-events-none aria-disabled:opacity-50 data-[active=true]:bg-sidebar-accent data-[active=true]:font-medium data-[active=true]:text-sidebar-accent-foreground data-[state=open]:hover:bg-sidebar-accent data-[state=open]:hover:text-sidebar-accent-foreground group-data-[collapsible=icon]:!size-8 group-data-[collapsible=icon]:!p-2 [&>span:last-child]:truncate [&>svg]:size-4 [&>svg]:shrink-0 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground h-8 text-sm w-full justify-start transition-colors hover:bg-sidebar-accent hover:text-sidebar-accent-foreground
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/components/AppSidebar.tsx:81:20', 'data-lov-name': 'NavLink', 'data-component-path': 'src/components/AppSidebar.tsx', 'data-component-line': '81', 'data-component-file': 'AppSidebar.tsx', 'data-component-name': 'NavLink', 'data-component-content': '%7B%7D', 'data-sidebar': 'menu-button', 'data-size': 'default', 'data-active': 'false', 'class': 'peer/menu-button flex w-full items-center gap-2 overflow-hidden rounded-md p-2 text-left outline-none ring-sidebar-ring transition-[width,height,padding] focus-visible:ring-2 active:bg-sidebar-accent active:text-sidebar-accent-foreground disabled:pointer-events-none disabled:opacity-50 group-has-[[data-sidebar=menu-action]]/menu-item:pr-8 aria-disabled:pointer-events-none aria-disabled:opacity-50 data-[active=true]:bg-sidebar-accent data-[active=true]:font-medium data-[active=true]:text-sidebar-accent-foreground data-[state=open]:hover:bg-sidebar-accent data-[state=open]:hover:text-sidebar-accent-foreground group-data-[collapsible=icon]:!size-8 group-data-[collapsible=icon]:!p-2 [&>span:last-child]:truncate [&>svg]:size-4 [&>svg]:shrink-0 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground h-8 text-sm w-full justify-start transition-colors hover:bg-sidebar-accent hover:text-sidebar-accent-foreground', 'href': '/reports'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     NavLink
  HTML:           <a data-lov-id="src/components/AppSidebar.tsx:81:20" data-lov-name="NavLink" data-component-path="src/components/AppSide
------------------------------------------------------------
Element 57:
  page_name:      dashboard
  tag_name:       svg
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'xmlns': 'http://www.w3.org/2000/svg', 'width': '24', 'height': '24', 'viewBox': '0 0 24 24', 'fill': 'none', 'stroke': 'currentColor', 'stroke-width': '2', 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'class': 'lucide lucide-file-text w-4 h-4', 'data-lov-id': 'src/components/AppSidebar.tsx:82:22', 'data-lov-name': 'item.icon', 'data-component-path': 'src/components/AppSidebar.tsx', 'data-component-line': '82', 'data-component-file': 'AppSidebar.tsx', 'data-component-name': 'item.icon', 'data-component-content': '%7B%22className%22%3A%22w-4%20h-4%22%7D'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     item.icon
  HTML:           <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" str
------------------------------------------------------------
Element 58:
  page_name:      dashboard
  tag_name:       path
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'d': 'M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"></path>
------------------------------------------------------------
Element 59:
  page_name:      dashboard
  tag_name:       path
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'d': 'M14 2v4a2 2 0 0 0 2 2h4'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <path d="M14 2v4a2 2 0 0 0 2 2h4"></path>
------------------------------------------------------------
Element 60:
  page_name:      dashboard
  tag_name:       path
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'d': 'M10 9H8'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <path d="M10 9H8"></path>
------------------------------------------------------------
Element 61:
  page_name:      dashboard
  tag_name:       path
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'d': 'M16 13H8'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <path d="M16 13H8"></path>
------------------------------------------------------------
Element 62:
  page_name:      dashboard
  tag_name:       path
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'d': 'M16 17H8'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <path d="M16 17H8"></path>
------------------------------------------------------------
Element 63:
  page_name:      dashboard
  tag_name:       span
  text:           Reports
  id:             
  class:          
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/components/AppSidebar.tsx:83:39', 'data-lov-name': 'span', 'data-component-path': 'src/components/AppSidebar.tsx', 'data-component-line': '83', 'data-component-file': 'AppSidebar.tsx', 'data-component-name': 'span', 'data-component-content': '%7B%7D'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     span
  HTML:           <span data-lov-id="src/components/AppSidebar.tsx:83:39" data-lov-name="span" data-component-path="src/components/AppSide
------------------------------------------------------------
Element 64:
  page_name:      dashboard
  tag_name:       li
  text:           Analytics
  id:             
  class:          group/menu-item relative
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/components/AppSidebar.tsx:79:16', 'data-lov-name': 'SidebarMenuItem', 'data-component-path': 'src/components/AppSidebar.tsx', 'data-component-line': '79', 'data-component-file': 'AppSidebar.tsx', 'data-component-name': 'SidebarMenuItem', 'data-component-content': '%7B%7D', 'data-sidebar': 'menu-item', 'class': 'group/menu-item relative'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     SidebarMenuItem
  HTML:           <li data-lov-id="src/components/AppSidebar.tsx:79:16" data-lov-name="SidebarMenuItem" data-component-path="src/component
------------------------------------------------------------
Element 65:
  page_name:      dashboard
  tag_name:       a
  text:           Analytics
  id:             
  class:          peer/menu-button flex w-full items-center gap-2 overflow-hidden rounded-md p-2 text-left outline-none ring-sidebar-ring transition-[width,height,padding] focus-visible:ring-2 active:bg-sidebar-accent active:text-sidebar-accent-foreground disabled:pointer-events-none disabled:opacity-50 group-has-[[data-sidebar=menu-action]]/menu-item:pr-8 aria-disabled:pointer-events-none aria-disabled:opacity-50 data-[active=true]:bg-sidebar-accent data-[active=true]:font-medium data-[active=true]:text-sidebar-accent-foreground data-[state=open]:hover:bg-sidebar-accent data-[state=open]:hover:text-sidebar-accent-foreground group-data-[collapsible=icon]:!size-8 group-data-[collapsible=icon]:!p-2 [&>span:last-child]:truncate [&>svg]:size-4 [&>svg]:shrink-0 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground h-8 text-sm w-full justify-start transition-colors hover:bg-sidebar-accent hover:text-sidebar-accent-foreground
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/components/AppSidebar.tsx:81:20', 'data-lov-name': 'NavLink', 'data-component-path': 'src/components/AppSidebar.tsx', 'data-component-line': '81', 'data-component-file': 'AppSidebar.tsx', 'data-component-name': 'NavLink', 'data-component-content': '%7B%7D', 'data-sidebar': 'menu-button', 'data-size': 'default', 'data-active': 'false', 'class': 'peer/menu-button flex w-full items-center gap-2 overflow-hidden rounded-md p-2 text-left outline-none ring-sidebar-ring transition-[width,height,padding] focus-visible:ring-2 active:bg-sidebar-accent active:text-sidebar-accent-foreground disabled:pointer-events-none disabled:opacity-50 group-has-[[data-sidebar=menu-action]]/menu-item:pr-8 aria-disabled:pointer-events-none aria-disabled:opacity-50 data-[active=true]:bg-sidebar-accent data-[active=true]:font-medium data-[active=true]:text-sidebar-accent-foreground data-[state=open]:hover:bg-sidebar-accent data-[state=open]:hover:text-sidebar-accent-foreground group-data-[collapsible=icon]:!size-8 group-data-[collapsible=icon]:!p-2 [&>span:last-child]:truncate [&>svg]:size-4 [&>svg]:shrink-0 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground h-8 text-sm w-full justify-start transition-colors hover:bg-sidebar-accent hover:text-sidebar-accent-foreground', 'href': '/analytics'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     NavLink
  HTML:           <a data-lov-id="src/components/AppSidebar.tsx:81:20" data-lov-name="NavLink" data-component-path="src/components/AppSide
------------------------------------------------------------
Element 66:
  page_name:      dashboard
  tag_name:       svg
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'xmlns': 'http://www.w3.org/2000/svg', 'width': '24', 'height': '24', 'viewBox': '0 0 24 24', 'fill': 'none', 'stroke': 'currentColor', 'stroke-width': '2', 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'class': 'lucide lucide-chart-column w-4 h-4', 'data-lov-id': 'src/components/AppSidebar.tsx:82:22', 'data-lov-name': 'item.icon', 'data-component-path': 'src/components/AppSidebar.tsx', 'data-component-line': '82', 'data-component-file': 'AppSidebar.tsx', 'data-component-name': 'item.icon', 'data-component-content': '%7B%22className%22%3A%22w-4%20h-4%22%7D'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     item.icon
  HTML:           <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" str
------------------------------------------------------------
Element 67:
  page_name:      dashboard
  tag_name:       path
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'d': 'M3 3v16a2 2 0 0 0 2 2h16'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <path d="M3 3v16a2 2 0 0 0 2 2h16"></path>
------------------------------------------------------------
Element 68:
  page_name:      dashboard
  tag_name:       path
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'d': 'M18 17V9'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <path d="M18 17V9"></path>
------------------------------------------------------------
Element 69:
  page_name:      dashboard
  tag_name:       path
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'d': 'M13 17V5'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <path d="M13 17V5"></path>
------------------------------------------------------------
Element 70:
  page_name:      dashboard
  tag_name:       path
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'d': 'M8 17v-3'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <path d="M8 17v-3"></path>
------------------------------------------------------------
Element 71:
  page_name:      dashboard
  tag_name:       span
  text:           Analytics
  id:             
  class:          
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/components/AppSidebar.tsx:83:39', 'data-lov-name': 'span', 'data-component-path': 'src/components/AppSidebar.tsx', 'data-component-line': '83', 'data-component-file': 'AppSidebar.tsx', 'data-component-name': 'span', 'data-component-content': '%7B%7D'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     span
  HTML:           <span data-lov-id="src/components/AppSidebar.tsx:83:39" data-lov-name="span" data-component-path="src/components/AppSide
------------------------------------------------------------
Element 72:
  page_name:      dashboard
  tag_name:       li
  text:           Settings
  id:             
  class:          group/menu-item relative
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/components/AppSidebar.tsx:79:16', 'data-lov-name': 'SidebarMenuItem', 'data-component-path': 'src/components/AppSidebar.tsx', 'data-component-line': '79', 'data-component-file': 'AppSidebar.tsx', 'data-component-name': 'SidebarMenuItem', 'data-component-content': '%7B%7D', 'data-sidebar': 'menu-item', 'class': 'group/menu-item relative'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     SidebarMenuItem
  HTML:           <li data-lov-id="src/components/AppSidebar.tsx:79:16" data-lov-name="SidebarMenuItem" data-component-path="src/component
------------------------------------------------------------
Element 73:
  page_name:      dashboard
  tag_name:       a
  text:           Settings
  id:             
  class:          peer/menu-button flex w-full items-center gap-2 overflow-hidden rounded-md p-2 text-left outline-none ring-sidebar-ring transition-[width,height,padding] focus-visible:ring-2 active:bg-sidebar-accent active:text-sidebar-accent-foreground disabled:pointer-events-none disabled:opacity-50 group-has-[[data-sidebar=menu-action]]/menu-item:pr-8 aria-disabled:pointer-events-none aria-disabled:opacity-50 data-[active=true]:bg-sidebar-accent data-[active=true]:font-medium data-[active=true]:text-sidebar-accent-foreground data-[state=open]:hover:bg-sidebar-accent data-[state=open]:hover:text-sidebar-accent-foreground group-data-[collapsible=icon]:!size-8 group-data-[collapsible=icon]:!p-2 [&>span:last-child]:truncate [&>svg]:size-4 [&>svg]:shrink-0 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground h-8 text-sm w-full justify-start transition-colors hover:bg-sidebar-accent hover:text-sidebar-accent-foreground
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/components/AppSidebar.tsx:81:20', 'data-lov-name': 'NavLink', 'data-component-path': 'src/components/AppSidebar.tsx', 'data-component-line': '81', 'data-component-file': 'AppSidebar.tsx', 'data-component-name': 'NavLink', 'data-component-content': '%7B%7D', 'data-sidebar': 'menu-button', 'data-size': 'default', 'data-active': 'false', 'class': 'peer/menu-button flex w-full items-center gap-2 overflow-hidden rounded-md p-2 text-left outline-none ring-sidebar-ring transition-[width,height,padding] focus-visible:ring-2 active:bg-sidebar-accent active:text-sidebar-accent-foreground disabled:pointer-events-none disabled:opacity-50 group-has-[[data-sidebar=menu-action]]/menu-item:pr-8 aria-disabled:pointer-events-none aria-disabled:opacity-50 data-[active=true]:bg-sidebar-accent data-[active=true]:font-medium data-[active=true]:text-sidebar-accent-foreground data-[state=open]:hover:bg-sidebar-accent data-[state=open]:hover:text-sidebar-accent-foreground group-data-[collapsible=icon]:!size-8 group-data-[collapsible=icon]:!p-2 [&>span:last-child]:truncate [&>svg]:size-4 [&>svg]:shrink-0 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground h-8 text-sm w-full justify-start transition-colors hover:bg-sidebar-accent hover:text-sidebar-accent-foreground', 'href': '/settings'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     NavLink
  HTML:           <a data-lov-id="src/components/AppSidebar.tsx:81:20" data-lov-name="NavLink" data-component-path="src/components/AppSide
------------------------------------------------------------
Element 74:
  page_name:      dashboard
  tag_name:       svg
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'xmlns': 'http://www.w3.org/2000/svg', 'width': '24', 'height': '24', 'viewBox': '0 0 24 24', 'fill': 'none', 'stroke': 'currentColor', 'stroke-width': '2', 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'class': 'lucide lucide-settings w-4 h-4', 'data-lov-id': 'src/components/AppSidebar.tsx:82:22', 'data-lov-name': 'item.icon', 'data-component-path': 'src/components/AppSidebar.tsx', 'data-component-line': '82', 'data-component-file': 'AppSidebar.tsx', 'data-component-name': 'item.icon', 'data-component-content': '%7B%22className%22%3A%22w-4%20h-4%22%7D'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     item.icon
  HTML:           <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" str
------------------------------------------------------------
Element 75:
  page_name:      dashboard
  tag_name:       path
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'d': 'M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0
------------------------------------------------------------
Element 76:
  page_name:      dashboard
  tag_name:       circle
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'cx': '12', 'cy': '12', 'r': '3'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <circle cx="12" cy="12" r="3"></circle>
------------------------------------------------------------
Element 77:
  page_name:      dashboard
  tag_name:       span
  text:           Settings
  id:             
  class:          
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/components/AppSidebar.tsx:83:39', 'data-lov-name': 'span', 'data-component-path': 'src/components/AppSidebar.tsx', 'data-component-line': '83', 'data-component-file': 'AppSidebar.tsx', 'data-component-name': 'span', 'data-component-content': '%7B%7D'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     span
  HTML:           <span data-lov-id="src/components/AppSidebar.tsx:83:39" data-lov-name="span" data-component-path="src/components/AppSide
------------------------------------------------------------
Element 78:
  page_name:      dashboard
  tag_name:       div
  text:           Toggle SidebarJohn DoeDashboardWelcome back! Here's your banking overview.Export ReportTotal Customers2,847+12.5% from last monthActive Loans$45.2M+8.2% from last monthMonthly Transactions18,394+15.3% from last monthRevenue Growth23.4%+2.1% from last monthLoan Portfolio TrendMonthly loan disbursements over the last 6 monthsJanFebMarAprMayJun01500000300000045000006000000Customer DistributionCustomer segments by account typePremium 35%Standard 45%Basic 20%Recent ActivitiesLatest customer interactions and transactionsSarah JohnsonLoan Application Approved$250,0002 hours agoMichael ChenAccount Verification Pending-4 hours agoEmma DavisLarge Transaction Alert$75,0006 hours agoRobert WilsonMonthly Payment Received$3,2008 hours ago
  id:             
  class:          flex-1 flex flex-col
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/components/Layout.tsx:12:8', 'data-lov-name': 'div', 'data-component-path': 'src/components/Layout.tsx', 'data-component-line': '12', 'data-component-file': 'Layout.tsx', 'data-component-name': 'div', 'data-component-content': '%7B%22className%22%3A%22flex-1%20flex%20flex-col%22%7D', 'class': 'flex-1 flex flex-col'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     div
  HTML:           <div data-lov-id="src/components/Layout.tsx:12:8" data-lov-name="div" data-component-path="src/components/Layout.tsx" da
------------------------------------------------------------
Element 79:
  page_name:      dashboard
  tag_name:       header
  text:           Toggle SidebarJohn Doe
  id:             
  class:          border-b bg-white px-6 py-4
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/components/Header.tsx:18:4', 'data-lov-name': 'header', 'data-component-path': 'src/components/Header.tsx', 'data-component-line': '18', 'data-component-file': 'Header.tsx', 'data-component-name': 'header', 'data-component-content': '%7B%22className%22%3A%22border-b%20bg-white%20px-6%20py-4%22%7D', 'class': 'border-b bg-white px-6 py-4'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     header
  HTML:           <header data-lov-id="src/components/Header.tsx:18:4" data-lov-name="header" data-component-path="src/components/Header.t
------------------------------------------------------------
Element 80:
  page_name:      dashboard
  tag_name:       div
  text:           Toggle SidebarJohn Doe
  id:             
  class:          flex items-center justify-between
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/components/Header.tsx:19:6', 'data-lov-name': 'div', 'data-component-path': 'src/components/Header.tsx', 'data-component-line': '19', 'data-component-file': 'Header.tsx', 'data-component-name': 'div', 'data-component-content': '%7B%22className%22%3A%22flex%20items-center%20justify-between%22%7D', 'class': 'flex items-center justify-between'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     div
  HTML:           <div data-lov-id="src/components/Header.tsx:19:6" data-lov-name="div" data-component-path="src/components/Header.tsx" da
------------------------------------------------------------
Element 81:
  page_name:      dashboard
  tag_name:       div
  text:           Toggle Sidebar
  id:             
  class:          flex items-center gap-4
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/components/Header.tsx:20:8', 'data-lov-name': 'div', 'data-component-path': 'src/components/Header.tsx', 'data-component-line': '20', 'data-component-file': 'Header.tsx', 'data-component-name': 'div', 'data-component-content': '%7B%22className%22%3A%22flex%20items-center%20gap-4%22%7D', 'class': 'flex items-center gap-4'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     div
  HTML:           <div data-lov-id="src/components/Header.tsx:20:8" data-lov-name="div" data-component-path="src/components/Header.tsx" da
------------------------------------------------------------
Element 82:
  page_name:      dashboard
  tag_name:       button
  text:           Toggle Sidebar
  id:             
  class:          inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0 hover:bg-accent hover:text-accent-foreground h-7 w-7
  value:          
  placeholder:    
  type:           submit
  attributes:     {'data-lov-id': 'src/components/Header.tsx:21:10', 'data-lov-name': 'SidebarTrigger', 'data-component-path': 'src/components/Header.tsx', 'data-component-line': '21', 'data-component-file': 'Header.tsx', 'data-component-name': 'SidebarTrigger', 'data-component-content': '%7B%7D', 'class': 'inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0 hover:bg-accent hover:text-accent-foreground h-7 w-7', 'data-sidebar': 'trigger'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     Toggle Sidebar
  HTML:           <button data-lov-id="src/components/Header.tsx:21:10" data-lov-name="SidebarTrigger" data-component-path="src/components
------------------------------------------------------------
Element 83:
  page_name:      dashboard
  tag_name:       svg
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'xmlns': 'http://www.w3.org/2000/svg', 'width': '24', 'height': '24', 'viewBox': '0 0 24 24', 'fill': 'none', 'stroke': 'currentColor', 'stroke-width': '2', 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'class': 'lucide lucide-panel-left', 'data-lov-id': 'src/components/ui/sidebar.tsx:279:6', 'data-lov-name': 'PanelLeft', 'data-component-path': 'src/components/ui/sidebar.tsx', 'data-component-line': '279', 'data-component-file': 'sidebar.tsx', 'data-component-name': 'PanelLeft', 'data-component-content': '%7B%7D'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     PanelLeft
  HTML:           <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" str
------------------------------------------------------------
Element 84:
  page_name:      dashboard
  tag_name:       rect
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'width': '18', 'height': '18', 'x': '3', 'y': '3', 'rx': '2'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <rect width="18" height="18" x="3" y="3" rx="2"></rect>
------------------------------------------------------------
Element 85:
  page_name:      dashboard
  tag_name:       path
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'d': 'M9 3v18'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <path d="M9 3v18"></path>
------------------------------------------------------------
Element 86:
  page_name:      dashboard
  tag_name:       span
  text:           Toggle Sidebar
  id:             
  class:          sr-only
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/components/ui/sidebar.tsx:280:6', 'data-lov-name': 'span', 'data-component-path': 'src/components/ui/sidebar.tsx', 'data-component-line': '280', 'data-component-file': 'sidebar.tsx', 'data-component-name': 'span', 'data-component-content': '%7B%22text%22%3A%22Toggle%20Sidebar%22%2C%22className%22%3A%22sr-only%22%7D', 'class': 'sr-only'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     span
  HTML:           <span data-lov-id="src/components/ui/sidebar.tsx:280:6" data-lov-name="span" data-component-path="src/components/ui/side
------------------------------------------------------------
Element 87:
  page_name:      dashboard
  tag_name:       div
  text:           John Doe
  id:             
  class:          flex items-center gap-4
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/components/Header.tsx:24:8', 'data-lov-name': 'div', 'data-component-path': 'src/components/Header.tsx', 'data-component-line': '24', 'data-component-file': 'Header.tsx', 'data-component-name': 'div', 'data-component-content': '%7B%22className%22%3A%22flex%20items-center%20gap-4%22%7D', 'class': 'flex items-center gap-4'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     div
  HTML:           <div data-lov-id="src/components/Header.tsx:24:8" data-lov-name="div" data-component-path="src/components/Header.tsx" da
------------------------------------------------------------
Element 88:
  page_name:      dashboard
  tag_name:       button
  text:           
  id:             
  class:          inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0 hover:bg-accent hover:text-accent-foreground h-10 w-10 relative
  value:          
  placeholder:    
  type:           submit
  attributes:     {'data-lov-id': 'src/components/Header.tsx:25:10', 'data-lov-name': 'Button', 'data-component-path': 'src/components/Header.tsx', 'data-component-line': '25', 'data-component-file': 'Header.tsx', 'data-component-name': 'Button', 'data-component-content': '%7B%22className%22%3A%22relative%22%7D', 'class': 'inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0 hover:bg-accent hover:text-accent-foreground h-10 w-10 relative'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     Button
  HTML:           <button data-lov-id="src/components/Header.tsx:25:10" data-lov-name="Button" data-component-path="src/components/Header.
------------------------------------------------------------
Element 89:
  page_name:      dashboard
  tag_name:       svg
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'xmlns': 'http://www.w3.org/2000/svg', 'width': '24', 'height': '24', 'viewBox': '0 0 24 24', 'fill': 'none', 'stroke': 'currentColor', 'stroke-width': '2', 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'class': 'lucide lucide-bell w-4 h-4', 'data-lov-id': 'src/components/Header.tsx:26:12', 'data-lov-name': 'Bell', 'data-component-path': 'src/components/Header.tsx', 'data-component-line': '26', 'data-component-file': 'Header.tsx', 'data-component-name': 'Bell', 'data-component-content': '%7B%22className%22%3A%22w-4%20h-4%22%7D'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     Bell
  HTML:           <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" str
------------------------------------------------------------
Element 90:
  page_name:      dashboard
  tag_name:       path
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'d': 'M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"></path>
------------------------------------------------------------
Element 91:
  page_name:      dashboard
  tag_name:       path
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'d': 'M10.3 21a1.94 1.94 0 0 0 3.4 0'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"></path>
------------------------------------------------------------
Element 92:
  page_name:      dashboard
  tag_name:       span
  text:           
  id:             
  class:          absolute -top-1 -right-1 w-2 h-2 bg-red-500 rounded-full
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/components/Header.tsx:27:12', 'data-lov-name': 'span', 'data-component-path': 'src/components/Header.tsx', 'data-component-line': '27', 'data-component-file': 'Header.tsx', 'data-component-name': 'span', 'data-component-content': '%7B%22className%22%3A%22absolute%20-top-1%20-right-1%20w-2%20h-2%20bg-red-500%20rounded-full%22%7D', 'class': 'absolute -top-1 -right-1 w-2 h-2 bg-red-500 rounded-full'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     span
  HTML:           <span data-lov-id="src/components/Header.tsx:27:12" data-lov-name="span" data-component-path="src/components/Header.tsx"
------------------------------------------------------------
Element 93:
  page_name:      dashboard
  tag_name:       button
  text:           John Doe
  id:             radix-:r0:
  class:          justify-center whitespace-nowrap rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0 hover:bg-accent hover:text-accent-foreground h-10 px-4 py-2 flex items-center gap-2
  value:          
  placeholder:    
  type:           button
  attributes:     {'data-lov-id': 'src/components/Header.tsx:32:14', 'data-lov-name': 'Button', 'data-component-path': 'src/components/Header.tsx', 'data-component-line': '32', 'data-component-file': 'Header.tsx', 'data-component-name': 'Button', 'data-component-content': '%7B%22className%22%3A%22flex%20items-center%20gap-2%22%7D', 'class': 'justify-center whitespace-nowrap rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0 hover:bg-accent hover:text-accent-foreground h-10 px-4 py-2 flex items-center gap-2', 'type': 'button', 'id': 'radix-:r0:', 'aria-haspopup': 'menu', 'aria-expanded': 'false', 'data-state': 'closed'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     John Doe
  HTML:           <button data-lov-id="src/components/Header.tsx:32:14" data-lov-name="Button" data-component-path="src/components/Header.
------------------------------------------------------------
Element 94:
  page_name:      dashboard
  tag_name:       span
  text:           
  id:             
  class:          relative flex shrink-0 overflow-hidden rounded-full w-8 h-8
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/components/Header.tsx:33:16', 'data-lov-name': 'Avatar', 'data-component-path': 'src/components/Header.tsx', 'data-component-line': '33', 'data-component-file': 'Header.tsx', 'data-component-name': 'Avatar', 'data-component-content': '%7B%22className%22%3A%22w-8%20h-8%22%7D', 'class': 'relative flex shrink-0 overflow-hidden rounded-full w-8 h-8'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     Avatar
  HTML:           <span data-lov-id="src/components/Header.tsx:33:16" data-lov-name="Avatar" data-component-path="src/components/Header.ts
------------------------------------------------------------
Element 95:
  page_name:      dashboard
  tag_name:       img
  text:           
  id:             
  class:          aspect-square h-full w-full
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/components/Header.tsx:34:18', 'data-lov-name': 'AvatarImage', 'data-component-path': 'src/components/Header.tsx', 'data-component-line': '34', 'data-component-file': 'Header.tsx', 'data-component-name': 'AvatarImage', 'data-component-content': '%7B%7D', 'class': 'aspect-square h-full w-full', 'src': 'https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=32&h=32&fit=crop&crop=face'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     AvatarImage
  HTML:           <img data-lov-id="src/components/Header.tsx:34:18" data-lov-name="AvatarImage" data-component-path="src/components/Heade
------------------------------------------------------------
Element 96:
  page_name:      dashboard
  tag_name:       span
  text:           John Doe
  id:             
  class:          hidden md:inline
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/components/Header.tsx:37:16', 'data-lov-name': 'span', 'data-component-path': 'src/components/Header.tsx', 'data-component-line': '37', 'data-component-file': 'Header.tsx', 'data-component-name': 'span', 'data-component-content': '%7B%22text%22%3A%22John%20Doe%22%2C%22className%22%3A%22hidden%20md%3Ainline%22%7D', 'class': 'hidden md:inline'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     span
  HTML:           <span data-lov-id="src/components/Header.tsx:37:16" data-lov-name="span" data-component-path="src/components/Header.tsx"
------------------------------------------------------------
Element 97:
  page_name:      dashboard
  tag_name:       main
  text:           DashboardWelcome back! Here's your banking overview.Export ReportTotal Customers2,847+12.5% from last monthActive Loans$45.2M+8.2% from last monthMonthly Transactions18,394+15.3% from last monthRevenue Growth23.4%+2.1% from last monthLoan Portfolio TrendMonthly loan disbursements over the last 6 monthsJanFebMarAprMayJun01500000300000045000006000000Customer DistributionCustomer segments by account typePremium 35%Standard 45%Basic 20%Recent ActivitiesLatest customer interactions and transactionsSarah JohnsonLoan Application Approved$250,0002 hours agoMichael ChenAccount Verification Pending-4 hours agoEmma DavisLarge Transaction Alert$75,0006 hours agoRobert WilsonMonthly Payment Received$3,2008 hours ago
  id:             
  class:          flex-1 p-6
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/components/Layout.tsx:14:10', 'data-lov-name': 'main', 'data-component-path': 'src/components/Layout.tsx', 'data-component-line': '14', 'data-component-file': 'Layout.tsx', 'data-component-name': 'main', 'data-component-content': '%7B%22className%22%3A%22flex-1%20p-6%22%7D', 'class': 'flex-1 p-6'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     main
  HTML:           <main data-lov-id="src/components/Layout.tsx:14:10" data-lov-name="main" data-component-path="src/components/Layout.tsx"
------------------------------------------------------------
Element 98:
  page_name:      dashboard
  tag_name:       div
  text:           DashboardWelcome back! Here's your banking overview.Export ReportTotal Customers2,847+12.5% from last monthActive Loans$45.2M+8.2% from last monthMonthly Transactions18,394+15.3% from last monthRevenue Growth23.4%+2.1% from last monthLoan Portfolio TrendMonthly loan disbursements over the last 6 monthsJanFebMarAprMayJun01500000300000045000006000000Customer DistributionCustomer segments by account typePremium 35%Standard 45%Basic 20%Recent ActivitiesLatest customer interactions and transactionsSarah JohnsonLoan Application Approved$250,0002 hours agoMichael ChenAccount Verification Pending-4 hours agoEmma DavisLarge Transaction Alert$75,0006 hours agoRobert WilsonMonthly Payment Received$3,2008 hours ago
  id:             
  class:          space-y-6
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Dashboard.tsx:109:4', 'data-lov-name': 'div', 'data-component-path': 'src/pages/Dashboard.tsx', 'data-component-line': '109', 'data-component-file': 'Dashboard.tsx', 'data-component-name': 'div', 'data-component-content': '%7B%22className%22%3A%22space-y-6%22%7D', 'class': 'space-y-6'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     div
  HTML:           <div data-lov-id="src/pages/Dashboard.tsx:109:4" data-lov-name="div" data-component-path="src/pages/Dashboard.tsx" data-
------------------------------------------------------------
Element 99:
  page_name:      dashboard
  tag_name:       div
  text:           DashboardWelcome back! Here's your banking overview.Export Report
  id:             
  class:          flex justify-between items-center
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Dashboard.tsx:110:6', 'data-lov-name': 'div', 'data-component-path': 'src/pages/Dashboard.tsx', 'data-component-line': '110', 'data-component-file': 'Dashboard.tsx', 'data-component-name': 'div', 'data-component-content': '%7B%22className%22%3A%22flex%20justify-between%20items-center%22%7D', 'class': 'flex justify-between items-center'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     div
  HTML:           <div data-lov-id="src/pages/Dashboard.tsx:110:6" data-lov-name="div" data-component-path="src/pages/Dashboard.tsx" data-
------------------------------------------------------------
Element 100:
  page_name:      dashboard
  tag_name:       div
  text:           DashboardWelcome back! Here's your banking overview.
  id:             
  class:          
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Dashboard.tsx:111:8', 'data-lov-name': 'div', 'data-component-path': 'src/pages/Dashboard.tsx', 'data-component-line': '111', 'data-component-file': 'Dashboard.tsx', 'data-component-name': 'div', 'data-component-content': '%7B%7D'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     div
  HTML:           <div data-lov-id="src/pages/Dashboard.tsx:111:8" data-lov-name="div" data-component-path="src/pages/Dashboard.tsx" data-
------------------------------------------------------------
Element 101:
  page_name:      dashboard
  tag_name:       h1
  text:           Dashboard
  id:             
  class:          text-3xl font-bold text-gray-900
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Dashboard.tsx:112:10', 'data-lov-name': 'h1', 'data-component-path': 'src/pages/Dashboard.tsx', 'data-component-line': '112', 'data-component-file': 'Dashboard.tsx', 'data-component-name': 'h1', 'data-component-content': '%7B%22text%22%3A%22Dashboard%22%2C%22className%22%3A%22text-3xl%20font-bold%20text-gray-900%22%7D', 'class': 'text-3xl font-bold text-gray-900'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     h1
  HTML:           <h1 data-lov-id="src/pages/Dashboard.tsx:112:10" data-lov-name="h1" data-component-path="src/pages/Dashboard.tsx" data-c
------------------------------------------------------------
Element 102:
  page_name:      dashboard
  tag_name:       p
  text:           Welcome back! Here's your banking overview.
  id:             
  class:          text-gray-600 mt-2
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Dashboard.tsx:113:10', 'data-lov-name': 'p', 'data-component-path': 'src/pages/Dashboard.tsx', 'data-component-line': '113', 'data-component-file': 'Dashboard.tsx', 'data-component-name': 'p', 'data-component-content': "%7B%22text%22%3A%22Welcome%20back!%20Here's%20your%20banking%20overview.%22%2C%22className%22%3A%22text-gray-600%20mt-2%22%7D", 'class': 'text-gray-600 mt-2'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     p
  HTML:           <p data-lov-id="src/pages/Dashboard.tsx:113:10" data-lov-name="p" data-component-path="src/pages/Dashboard.tsx" data-com
------------------------------------------------------------
Element 103:
  page_name:      dashboard
  tag_name:       button
  text:           Export Report
  id:             
  class:          justify-center whitespace-nowrap rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0 bg-primary text-primary-foreground hover:bg-primary/90 h-10 px-4 py-2 flex items-center gap-2
  value:          
  placeholder:    
  type:           submit
  attributes:     {'data-lov-id': 'src/pages/Dashboard.tsx:115:8', 'data-lov-name': 'Button', 'data-component-path': 'src/pages/Dashboard.tsx', 'data-component-line': '115', 'data-component-file': 'Dashboard.tsx', 'data-component-name': 'Button', 'data-component-content': '%7B%22text%22%3A%22Export%20Report%22%2C%22className%22%3A%22flex%20items-center%20gap-2%22%7D', 'class': 'justify-center whitespace-nowrap rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0 bg-primary text-primary-foreground hover:bg-primary/90 h-10 px-4 py-2 flex items-center gap-2'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     Export Report
  HTML:           <button data-lov-id="src/pages/Dashboard.tsx:115:8" data-lov-name="Button" data-component-path="src/pages/Dashboard.tsx"
------------------------------------------------------------
Element 104:
  page_name:      dashboard
  tag_name:       svg
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'xmlns': 'http://www.w3.org/2000/svg', 'width': '24', 'height': '24', 'viewBox': '0 0 24 24', 'fill': 'none', 'stroke': 'currentColor', 'stroke-width': '2', 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'class': 'lucide lucide-download w-4 h-4', 'data-lov-id': 'src/pages/Dashboard.tsx:116:10', 'data-lov-name': 'Download', 'data-component-path': 'src/pages/Dashboard.tsx', 'data-component-line': '116', 'data-component-file': 'Dashboard.tsx', 'data-component-name': 'Download', 'data-component-content': '%7B%22className%22%3A%22w-4%20h-4%22%7D'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     Download
  HTML:           <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" str
------------------------------------------------------------
Element 105:
  page_name:      dashboard
  tag_name:       path
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'d': 'M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
------------------------------------------------------------
Element 106:
  page_name:      dashboard
  tag_name:       polyline
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'points': '7 10 12 15 17 10'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <polyline points="7 10 12 15 17 10"></polyline>
------------------------------------------------------------
Element 107:
  page_name:      dashboard
  tag_name:       line
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'x1': '12', 'x2': '12', 'y1': '15', 'y2': '3'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <line x1="12" x2="12" y1="15" y2="3"></line>
------------------------------------------------------------
Element 108:
  page_name:      dashboard
  tag_name:       div
  text:           Total Customers2,847+12.5% from last monthActive Loans$45.2M+8.2% from last monthMonthly Transactions18,394+15.3% from last monthRevenue Growth23.4%+2.1% from last month
  id:             
  class:          grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Dashboard.tsx:122:6', 'data-lov-name': 'div', 'data-component-path': 'src/pages/Dashboard.tsx', 'data-component-line': '122', 'data-component-file': 'Dashboard.tsx', 'data-component-name': 'div', 'data-component-content': '%7B%22className%22%3A%22grid%20grid-cols-1%20md%3Agrid-cols-2%20lg%3Agrid-cols-4%20gap-6%22%7D', 'class': 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     div
  HTML:           <div data-lov-id="src/pages/Dashboard.tsx:122:6" data-lov-name="div" data-component-path="src/pages/Dashboard.tsx" data-
------------------------------------------------------------
Element 109:
  page_name:      dashboard
  tag_name:       div
  text:           Total Customers2,847+12.5% from last month
  id:             
  class:          rounded-lg border bg-card text-card-foreground shadow-sm metric-card
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Dashboard.tsx:124:10', 'data-lov-name': 'Card', 'data-component-path': 'src/pages/Dashboard.tsx', 'data-component-line': '124', 'data-component-file': 'Dashboard.tsx', 'data-component-name': 'Card', 'data-component-content': '%7B%22className%22%3A%22metric-card%22%7D', 'class': 'rounded-lg border bg-card text-card-foreground shadow-sm metric-card'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     Card
  HTML:           <div data-lov-id="src/pages/Dashboard.tsx:124:10" data-lov-name="Card" data-component-path="src/pages/Dashboard.tsx" dat
------------------------------------------------------------
Element 110:
  page_name:      dashboard
  tag_name:       div
  text:           Total Customers
  id:             
  class:          p-6 flex flex-row items-center justify-between space-y-0 pb-2
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Dashboard.tsx:125:12', 'data-lov-name': 'CardHeader', 'data-component-path': 'src/pages/Dashboard.tsx', 'data-component-line': '125', 'data-component-file': 'Dashboard.tsx', 'data-component-name': 'CardHeader', 'data-component-content': '%7B%22className%22%3A%22flex%20flex-row%20items-center%20justify-between%20space-y-0%20pb-2%22%7D', 'class': 'p-6 flex flex-row items-center justify-between space-y-0 pb-2'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     CardHeader
  HTML:           <div data-lov-id="src/pages/Dashboard.tsx:125:12" data-lov-name="CardHeader" data-component-path="src/pages/Dashboard.ts
------------------------------------------------------------
Element 111:
  page_name:      dashboard
  tag_name:       h3
  text:           Total Customers
  id:             
  class:          tracking-tight text-sm font-medium text-gray-600
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Dashboard.tsx:126:14', 'data-lov-name': 'CardTitle', 'data-component-path': 'src/pages/Dashboard.tsx', 'data-component-line': '126', 'data-component-file': 'Dashboard.tsx', 'data-component-name': 'CardTitle', 'data-component-content': '%7B%22className%22%3A%22text-sm%20font-medium%20text-gray-600%22%7D', 'class': 'tracking-tight text-sm font-medium text-gray-600'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     CardTitle
  HTML:           <h3 data-lov-id="src/pages/Dashboard.tsx:126:14" data-lov-name="CardTitle" data-component-path="src/pages/Dashboard.tsx"
------------------------------------------------------------
Element 112:
  page_name:      dashboard
  tag_name:       svg
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'xmlns': 'http://www.w3.org/2000/svg', 'width': '24', 'height': '24', 'viewBox': '0 0 24 24', 'fill': 'none', 'stroke': 'currentColor', 'stroke-width': '2', 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'class': 'lucide lucide-users h-4 w-4 text-primary', 'data-lov-id': 'src/pages/Dashboard.tsx:129:14', 'data-lov-name': 'metric.icon', 'data-component-path': 'src/pages/Dashboard.tsx', 'data-component-line': '129', 'data-component-file': 'Dashboard.tsx', 'data-component-name': 'metric.icon', 'data-component-content': '%7B%22className%22%3A%22h-4%20w-4%20text-primary%22%7D'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     metric.icon
  HTML:           <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" str
------------------------------------------------------------
Element 113:
  page_name:      dashboard
  tag_name:       path
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'d': 'M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"></path>
------------------------------------------------------------
Element 114:
  page_name:      dashboard
  tag_name:       circle
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'cx': '9', 'cy': '7', 'r': '4'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <circle cx="9" cy="7" r="4"></circle>
------------------------------------------------------------
Element 115:
  page_name:      dashboard
  tag_name:       path
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'d': 'M22 21v-2a4 4 0 0 0-3-3.87'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <path d="M22 21v-2a4 4 0 0 0-3-3.87"></path>
------------------------------------------------------------
Element 116:
  page_name:      dashboard
  tag_name:       path
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'d': 'M16 3.13a4 4 0 0 1 0 7.75'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <path d="M16 3.13a4 4 0 0 1 0 7.75"></path>
------------------------------------------------------------
Element 117:
  page_name:      dashboard
  tag_name:       div
  text:           2,847+12.5% from last month
  id:             
  class:          p-6 pt-0
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Dashboard.tsx:131:12', 'data-lov-name': 'CardContent', 'data-component-path': 'src/pages/Dashboard.tsx', 'data-component-line': '131', 'data-component-file': 'Dashboard.tsx', 'data-component-name': 'CardContent', 'data-component-content': '%7B%7D', 'class': 'p-6 pt-0'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     CardContent
  HTML:           <div data-lov-id="src/pages/Dashboard.tsx:131:12" data-lov-name="CardContent" data-component-path="src/pages/Dashboard.t
------------------------------------------------------------
Element 118:
  page_name:      dashboard
  tag_name:       div
  text:           2,847
  id:             
  class:          text-2xl font-bold text-gray-900
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Dashboard.tsx:132:14', 'data-lov-name': 'div', 'data-component-path': 'src/pages/Dashboard.tsx', 'data-component-line': '132', 'data-component-file': 'Dashboard.tsx', 'data-component-name': 'div', 'data-component-content': '%7B%22className%22%3A%22text-2xl%20font-bold%20text-gray-900%22%7D', 'class': 'text-2xl font-bold text-gray-900'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     div
  HTML:           <div data-lov-id="src/pages/Dashboard.tsx:132:14" data-lov-name="div" data-component-path="src/pages/Dashboard.tsx" data
------------------------------------------------------------
Element 119:
  page_name:      dashboard
  tag_name:       p
  text:           +12.5% from last month
  id:             
  class:          text-xs text-green-600 flex items-center mt-1
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Dashboard.tsx:133:14', 'data-lov-name': 'p', 'data-component-path': 'src/pages/Dashboard.tsx', 'data-component-line': '133', 'data-component-file': 'Dashboard.tsx', 'data-component-name': 'p', 'data-component-content': '%7B%22text%22%3A%22from%20last%20month%22%2C%22className%22%3A%22text-xs%20text-green-600%20flex%20items-center%20mt-1%22%7D', 'class': 'text-xs text-green-600 flex items-center mt-1'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     p
  HTML:           <p data-lov-id="src/pages/Dashboard.tsx:133:14" data-lov-name="p" data-component-path="src/pages/Dashboard.tsx" data-com
------------------------------------------------------------
Element 120:
  page_name:      dashboard
  tag_name:       svg
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'xmlns': 'http://www.w3.org/2000/svg', 'width': '24', 'height': '24', 'viewBox': '0 0 24 24', 'fill': 'none', 'stroke': 'currentColor', 'stroke-width': '2', 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'class': 'lucide lucide-trending-up w-3 h-3 mr-1', 'data-lov-id': 'src/pages/Dashboard.tsx:134:16', 'data-lov-name': 'TrendingUp', 'data-component-path': 'src/pages/Dashboard.tsx', 'data-component-line': '134', 'data-component-file': 'Dashboard.tsx', 'data-component-name': 'TrendingUp', 'data-component-content': '%7B%22className%22%3A%22w-3%20h-3%20mr-1%22%7D'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     TrendingUp
  HTML:           <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" str
------------------------------------------------------------
Element 121:
  page_name:      dashboard
  tag_name:       polyline
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'points': '22 7 13.5 15.5 8.5 10.5 2 17'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <polyline points="22 7 13.5 15.5 8.5 10.5 2 17"></polyline>
------------------------------------------------------------
Element 122:
  page_name:      dashboard
  tag_name:       polyline
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'points': '16 7 22 7 22 13'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <polyline points="16 7 22 7 22 13"></polyline>
------------------------------------------------------------
Element 123:
  page_name:      dashboard
  tag_name:       div
  text:           Active Loans$45.2M+8.2% from last month
  id:             
  class:          rounded-lg border bg-card text-card-foreground shadow-sm metric-card
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Dashboard.tsx:124:10', 'data-lov-name': 'Card', 'data-component-path': 'src/pages/Dashboard.tsx', 'data-component-line': '124', 'data-component-file': 'Dashboard.tsx', 'data-component-name': 'Card', 'data-component-content': '%7B%22className%22%3A%22metric-card%22%7D', 'class': 'rounded-lg border bg-card text-card-foreground shadow-sm metric-card'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     Card
  HTML:           <div data-lov-id="src/pages/Dashboard.tsx:124:10" data-lov-name="Card" data-component-path="src/pages/Dashboard.tsx" dat
------------------------------------------------------------
Element 124:
  page_name:      dashboard
  tag_name:       div
  text:           Active Loans
  id:             
  class:          p-6 flex flex-row items-center justify-between space-y-0 pb-2
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Dashboard.tsx:125:12', 'data-lov-name': 'CardHeader', 'data-component-path': 'src/pages/Dashboard.tsx', 'data-component-line': '125', 'data-component-file': 'Dashboard.tsx', 'data-component-name': 'CardHeader', 'data-component-content': '%7B%22className%22%3A%22flex%20flex-row%20items-center%20justify-between%20space-y-0%20pb-2%22%7D', 'class': 'p-6 flex flex-row items-center justify-between space-y-0 pb-2'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     CardHeader
  HTML:           <div data-lov-id="src/pages/Dashboard.tsx:125:12" data-lov-name="CardHeader" data-component-path="src/pages/Dashboard.ts
------------------------------------------------------------
Element 125:
  page_name:      dashboard
  tag_name:       h3
  text:           Active Loans
  id:             
  class:          tracking-tight text-sm font-medium text-gray-600
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Dashboard.tsx:126:14', 'data-lov-name': 'CardTitle', 'data-component-path': 'src/pages/Dashboard.tsx', 'data-component-line': '126', 'data-component-file': 'Dashboard.tsx', 'data-component-name': 'CardTitle', 'data-component-content': '%7B%22className%22%3A%22text-sm%20font-medium%20text-gray-600%22%7D', 'class': 'tracking-tight text-sm font-medium text-gray-600'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     CardTitle
  HTML:           <h3 data-lov-id="src/pages/Dashboard.tsx:126:14" data-lov-name="CardTitle" data-component-path="src/pages/Dashboard.tsx"
------------------------------------------------------------
Element 126:
  page_name:      dashboard
  tag_name:       svg
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'xmlns': 'http://www.w3.org/2000/svg', 'width': '24', 'height': '24', 'viewBox': '0 0 24 24', 'fill': 'none', 'stroke': 'currentColor', 'stroke-width': '2', 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'class': 'lucide lucide-dollar-sign h-4 w-4 text-primary', 'data-lov-id': 'src/pages/Dashboard.tsx:129:14', 'data-lov-name': 'metric.icon', 'data-component-path': 'src/pages/Dashboard.tsx', 'data-component-line': '129', 'data-component-file': 'Dashboard.tsx', 'data-component-name': 'metric.icon', 'data-component-content': '%7B%22className%22%3A%22h-4%20w-4%20text-primary%22%7D'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     metric.icon
  HTML:           <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" str
------------------------------------------------------------
Element 127:
  page_name:      dashboard
  tag_name:       line
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'x1': '12', 'x2': '12', 'y1': '2', 'y2': '22'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <line x1="12" x2="12" y1="2" y2="22"></line>
------------------------------------------------------------
Element 128:
  page_name:      dashboard
  tag_name:       path
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'d': 'M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"></path>
------------------------------------------------------------
Element 129:
  page_name:      dashboard
  tag_name:       div
  text:           $45.2M+8.2% from last month
  id:             
  class:          p-6 pt-0
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Dashboard.tsx:131:12', 'data-lov-name': 'CardContent', 'data-component-path': 'src/pages/Dashboard.tsx', 'data-component-line': '131', 'data-component-file': 'Dashboard.tsx', 'data-component-name': 'CardContent', 'data-component-content': '%7B%7D', 'class': 'p-6 pt-0'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     CardContent
  HTML:           <div data-lov-id="src/pages/Dashboard.tsx:131:12" data-lov-name="CardContent" data-component-path="src/pages/Dashboard.t
------------------------------------------------------------
Element 130:
  page_name:      dashboard
  tag_name:       div
  text:           $45.2M
  id:             
  class:          text-2xl font-bold text-gray-900
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Dashboard.tsx:132:14', 'data-lov-name': 'div', 'data-component-path': 'src/pages/Dashboard.tsx', 'data-component-line': '132', 'data-component-file': 'Dashboard.tsx', 'data-component-name': 'div', 'data-component-content': '%7B%22className%22%3A%22text-2xl%20font-bold%20text-gray-900%22%7D', 'class': 'text-2xl font-bold text-gray-900'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     div
  HTML:           <div data-lov-id="src/pages/Dashboard.tsx:132:14" data-lov-name="div" data-component-path="src/pages/Dashboard.tsx" data
------------------------------------------------------------
Element 131:
  page_name:      dashboard
  tag_name:       p
  text:           +8.2% from last month
  id:             
  class:          text-xs text-green-600 flex items-center mt-1
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Dashboard.tsx:133:14', 'data-lov-name': 'p', 'data-component-path': 'src/pages/Dashboard.tsx', 'data-component-line': '133', 'data-component-file': 'Dashboard.tsx', 'data-component-name': 'p', 'data-component-content': '%7B%22text%22%3A%22from%20last%20month%22%2C%22className%22%3A%22text-xs%20text-green-600%20flex%20items-center%20mt-1%22%7D', 'class': 'text-xs text-green-600 flex items-center mt-1'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     p
  HTML:           <p data-lov-id="src/pages/Dashboard.tsx:133:14" data-lov-name="p" data-component-path="src/pages/Dashboard.tsx" data-com
------------------------------------------------------------
Element 132:
  page_name:      dashboard
  tag_name:       svg
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'xmlns': 'http://www.w3.org/2000/svg', 'width': '24', 'height': '24', 'viewBox': '0 0 24 24', 'fill': 'none', 'stroke': 'currentColor', 'stroke-width': '2', 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'class': 'lucide lucide-trending-up w-3 h-3 mr-1', 'data-lov-id': 'src/pages/Dashboard.tsx:134:16', 'data-lov-name': 'TrendingUp', 'data-component-path': 'src/pages/Dashboard.tsx', 'data-component-line': '134', 'data-component-file': 'Dashboard.tsx', 'data-component-name': 'TrendingUp', 'data-component-content': '%7B%22className%22%3A%22w-3%20h-3%20mr-1%22%7D'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     TrendingUp
  HTML:           <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" str
------------------------------------------------------------
Element 133:
  page_name:      dashboard
  tag_name:       polyline
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'points': '22 7 13.5 15.5 8.5 10.5 2 17'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <polyline points="22 7 13.5 15.5 8.5 10.5 2 17"></polyline>
------------------------------------------------------------
Element 134:
  page_name:      dashboard
  tag_name:       polyline
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'points': '16 7 22 7 22 13'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <polyline points="16 7 22 7 22 13"></polyline>
------------------------------------------------------------
Element 135:
  page_name:      dashboard
  tag_name:       div
  text:           Monthly Transactions18,394+15.3% from last month
  id:             
  class:          rounded-lg border bg-card text-card-foreground shadow-sm metric-card
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Dashboard.tsx:124:10', 'data-lov-name': 'Card', 'data-component-path': 'src/pages/Dashboard.tsx', 'data-component-line': '124', 'data-component-file': 'Dashboard.tsx', 'data-component-name': 'Card', 'data-component-content': '%7B%22className%22%3A%22metric-card%22%7D', 'class': 'rounded-lg border bg-card text-card-foreground shadow-sm metric-card'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     Card
  HTML:           <div data-lov-id="src/pages/Dashboard.tsx:124:10" data-lov-name="Card" data-component-path="src/pages/Dashboard.tsx" dat
------------------------------------------------------------
Element 136:
  page_name:      dashboard
  tag_name:       div
  text:           Monthly Transactions
  id:             
  class:          p-6 flex flex-row items-center justify-between space-y-0 pb-2
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Dashboard.tsx:125:12', 'data-lov-name': 'CardHeader', 'data-component-path': 'src/pages/Dashboard.tsx', 'data-component-line': '125', 'data-component-file': 'Dashboard.tsx', 'data-component-name': 'CardHeader', 'data-component-content': '%7B%22className%22%3A%22flex%20flex-row%20items-center%20justify-between%20space-y-0%20pb-2%22%7D', 'class': 'p-6 flex flex-row items-center justify-between space-y-0 pb-2'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     CardHeader
  HTML:           <div data-lov-id="src/pages/Dashboard.tsx:125:12" data-lov-name="CardHeader" data-component-path="src/pages/Dashboard.ts
------------------------------------------------------------
Element 137:
  page_name:      dashboard
  tag_name:       h3
  text:           Monthly Transactions
  id:             
  class:          tracking-tight text-sm font-medium text-gray-600
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Dashboard.tsx:126:14', 'data-lov-name': 'CardTitle', 'data-component-path': 'src/pages/Dashboard.tsx', 'data-component-line': '126', 'data-component-file': 'Dashboard.tsx', 'data-component-name': 'CardTitle', 'data-component-content': '%7B%22className%22%3A%22text-sm%20font-medium%20text-gray-600%22%7D', 'class': 'tracking-tight text-sm font-medium text-gray-600'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     CardTitle
  HTML:           <h3 data-lov-id="src/pages/Dashboard.tsx:126:14" data-lov-name="CardTitle" data-component-path="src/pages/Dashboard.tsx"
------------------------------------------------------------
Element 138:
  page_name:      dashboard
  tag_name:       svg
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'xmlns': 'http://www.w3.org/2000/svg', 'width': '24', 'height': '24', 'viewBox': '0 0 24 24', 'fill': 'none', 'stroke': 'currentColor', 'stroke-width': '2', 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'class': 'lucide lucide-credit-card h-4 w-4 text-primary', 'data-lov-id': 'src/pages/Dashboard.tsx:129:14', 'data-lov-name': 'metric.icon', 'data-component-path': 'src/pages/Dashboard.tsx', 'data-component-line': '129', 'data-component-file': 'Dashboard.tsx', 'data-component-name': 'metric.icon', 'data-component-content': '%7B%22className%22%3A%22h-4%20w-4%20text-primary%22%7D'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     metric.icon
  HTML:           <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" str
------------------------------------------------------------
Element 139:
  page_name:      dashboard
  tag_name:       rect
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'width': '20', 'height': '14', 'x': '2', 'y': '5', 'rx': '2'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <rect width="20" height="14" x="2" y="5" rx="2"></rect>
------------------------------------------------------------
Element 140:
  page_name:      dashboard
  tag_name:       line
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'x1': '2', 'x2': '22', 'y1': '10', 'y2': '10'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <line x1="2" x2="22" y1="10" y2="10"></line>
------------------------------------------------------------
Element 141:
  page_name:      dashboard
  tag_name:       div
  text:           18,394+15.3% from last month
  id:             
  class:          p-6 pt-0
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Dashboard.tsx:131:12', 'data-lov-name': 'CardContent', 'data-component-path': 'src/pages/Dashboard.tsx', 'data-component-line': '131', 'data-component-file': 'Dashboard.tsx', 'data-component-name': 'CardContent', 'data-component-content': '%7B%7D', 'class': 'p-6 pt-0'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     CardContent
  HTML:           <div data-lov-id="src/pages/Dashboard.tsx:131:12" data-lov-name="CardContent" data-component-path="src/pages/Dashboard.t
------------------------------------------------------------
Element 142:
  page_name:      dashboard
  tag_name:       div
  text:           18,394
  id:             
  class:          text-2xl font-bold text-gray-900
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Dashboard.tsx:132:14', 'data-lov-name': 'div', 'data-component-path': 'src/pages/Dashboard.tsx', 'data-component-line': '132', 'data-component-file': 'Dashboard.tsx', 'data-component-name': 'div', 'data-component-content': '%7B%22className%22%3A%22text-2xl%20font-bold%20text-gray-900%22%7D', 'class': 'text-2xl font-bold text-gray-900'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     div
  HTML:           <div data-lov-id="src/pages/Dashboard.tsx:132:14" data-lov-name="div" data-component-path="src/pages/Dashboard.tsx" data
------------------------------------------------------------
Element 143:
  page_name:      dashboard
  tag_name:       p
  text:           +15.3% from last month
  id:             
  class:          text-xs text-green-600 flex items-center mt-1
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Dashboard.tsx:133:14', 'data-lov-name': 'p', 'data-component-path': 'src/pages/Dashboard.tsx', 'data-component-line': '133', 'data-component-file': 'Dashboard.tsx', 'data-component-name': 'p', 'data-component-content': '%7B%22text%22%3A%22from%20last%20month%22%2C%22className%22%3A%22text-xs%20text-green-600%20flex%20items-center%20mt-1%22%7D', 'class': 'text-xs text-green-600 flex items-center mt-1'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     p
  HTML:           <p data-lov-id="src/pages/Dashboard.tsx:133:14" data-lov-name="p" data-component-path="src/pages/Dashboard.tsx" data-com
------------------------------------------------------------
Element 144:
  page_name:      dashboard
  tag_name:       svg
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'xmlns': 'http://www.w3.org/2000/svg', 'width': '24', 'height': '24', 'viewBox': '0 0 24 24', 'fill': 'none', 'stroke': 'currentColor', 'stroke-width': '2', 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'class': 'lucide lucide-trending-up w-3 h-3 mr-1', 'data-lov-id': 'src/pages/Dashboard.tsx:134:16', 'data-lov-name': 'TrendingUp', 'data-component-path': 'src/pages/Dashboard.tsx', 'data-component-line': '134', 'data-component-file': 'Dashboard.tsx', 'data-component-name': 'TrendingUp', 'data-component-content': '%7B%22className%22%3A%22w-3%20h-3%20mr-1%22%7D'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     TrendingUp
  HTML:           <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" str
------------------------------------------------------------
Element 145:
  page_name:      dashboard
  tag_name:       polyline
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'points': '22 7 13.5 15.5 8.5 10.5 2 17'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <polyline points="22 7 13.5 15.5 8.5 10.5 2 17"></polyline>
------------------------------------------------------------
Element 146:
  page_name:      dashboard
  tag_name:       polyline
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'points': '16 7 22 7 22 13'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <polyline points="16 7 22 7 22 13"></polyline>
------------------------------------------------------------
Element 147:
  page_name:      dashboard
  tag_name:       div
  text:           Revenue Growth23.4%+2.1% from last month
  id:             
  class:          rounded-lg border bg-card text-card-foreground shadow-sm metric-card
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Dashboard.tsx:124:10', 'data-lov-name': 'Card', 'data-component-path': 'src/pages/Dashboard.tsx', 'data-component-line': '124', 'data-component-file': 'Dashboard.tsx', 'data-component-name': 'Card', 'data-component-content': '%7B%22className%22%3A%22metric-card%22%7D', 'class': 'rounded-lg border bg-card text-card-foreground shadow-sm metric-card'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     Card
  HTML:           <div data-lov-id="src/pages/Dashboard.tsx:124:10" data-lov-name="Card" data-component-path="src/pages/Dashboard.tsx" dat
------------------------------------------------------------
Element 148:
  page_name:      dashboard
  tag_name:       div
  text:           Revenue Growth
  id:             
  class:          p-6 flex flex-row items-center justify-between space-y-0 pb-2
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Dashboard.tsx:125:12', 'data-lov-name': 'CardHeader', 'data-component-path': 'src/pages/Dashboard.tsx', 'data-component-line': '125', 'data-component-file': 'Dashboard.tsx', 'data-component-name': 'CardHeader', 'data-component-content': '%7B%22className%22%3A%22flex%20flex-row%20items-center%20justify-between%20space-y-0%20pb-2%22%7D', 'class': 'p-6 flex flex-row items-center justify-between space-y-0 pb-2'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     CardHeader
  HTML:           <div data-lov-id="src/pages/Dashboard.tsx:125:12" data-lov-name="CardHeader" data-component-path="src/pages/Dashboard.ts
------------------------------------------------------------
Element 149:
  page_name:      dashboard
  tag_name:       h3
  text:           Revenue Growth
  id:             
  class:          tracking-tight text-sm font-medium text-gray-600
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Dashboard.tsx:126:14', 'data-lov-name': 'CardTitle', 'data-component-path': 'src/pages/Dashboard.tsx', 'data-component-line': '126', 'data-component-file': 'Dashboard.tsx', 'data-component-name': 'CardTitle', 'data-component-content': '%7B%22className%22%3A%22text-sm%20font-medium%20text-gray-600%22%7D', 'class': 'tracking-tight text-sm font-medium text-gray-600'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     CardTitle
  HTML:           <h3 data-lov-id="src/pages/Dashboard.tsx:126:14" data-lov-name="CardTitle" data-component-path="src/pages/Dashboard.tsx"
------------------------------------------------------------
Element 150:
  page_name:      dashboard
  tag_name:       svg
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'xmlns': 'http://www.w3.org/2000/svg', 'width': '24', 'height': '24', 'viewBox': '0 0 24 24', 'fill': 'none', 'stroke': 'currentColor', 'stroke-width': '2', 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'class': 'lucide lucide-trending-up h-4 w-4 text-primary', 'data-lov-id': 'src/pages/Dashboard.tsx:129:14', 'data-lov-name': 'metric.icon', 'data-component-path': 'src/pages/Dashboard.tsx', 'data-component-line': '129', 'data-component-file': 'Dashboard.tsx', 'data-component-name': 'metric.icon', 'data-component-content': '%7B%22className%22%3A%22h-4%20w-4%20text-primary%22%7D'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     metric.icon
  HTML:           <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" str
------------------------------------------------------------
Element 151:
  page_name:      dashboard
  tag_name:       polyline
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'points': '22 7 13.5 15.5 8.5 10.5 2 17'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <polyline points="22 7 13.5 15.5 8.5 10.5 2 17"></polyline>
------------------------------------------------------------
Element 152:
  page_name:      dashboard
  tag_name:       polyline
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'points': '16 7 22 7 22 13'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <polyline points="16 7 22 7 22 13"></polyline>
------------------------------------------------------------
Element 153:
  page_name:      dashboard
  tag_name:       div
  text:           23.4%+2.1% from last month
  id:             
  class:          p-6 pt-0
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Dashboard.tsx:131:12', 'data-lov-name': 'CardContent', 'data-component-path': 'src/pages/Dashboard.tsx', 'data-component-line': '131', 'data-component-file': 'Dashboard.tsx', 'data-component-name': 'CardContent', 'data-component-content': '%7B%7D', 'class': 'p-6 pt-0'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     CardContent
  HTML:           <div data-lov-id="src/pages/Dashboard.tsx:131:12" data-lov-name="CardContent" data-component-path="src/pages/Dashboard.t
------------------------------------------------------------
Element 154:
  page_name:      dashboard
  tag_name:       div
  text:           23.4%
  id:             
  class:          text-2xl font-bold text-gray-900
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Dashboard.tsx:132:14', 'data-lov-name': 'div', 'data-component-path': 'src/pages/Dashboard.tsx', 'data-component-line': '132', 'data-component-file': 'Dashboard.tsx', 'data-component-name': 'div', 'data-component-content': '%7B%22className%22%3A%22text-2xl%20font-bold%20text-gray-900%22%7D', 'class': 'text-2xl font-bold text-gray-900'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     div
  HTML:           <div data-lov-id="src/pages/Dashboard.tsx:132:14" data-lov-name="div" data-component-path="src/pages/Dashboard.tsx" data
------------------------------------------------------------
Element 155:
  page_name:      dashboard
  tag_name:       p
  text:           +2.1% from last month
  id:             
  class:          text-xs text-green-600 flex items-center mt-1
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Dashboard.tsx:133:14', 'data-lov-name': 'p', 'data-component-path': 'src/pages/Dashboard.tsx', 'data-component-line': '133', 'data-component-file': 'Dashboard.tsx', 'data-component-name': 'p', 'data-component-content': '%7B%22text%22%3A%22from%20last%20month%22%2C%22className%22%3A%22text-xs%20text-green-600%20flex%20items-center%20mt-1%22%7D', 'class': 'text-xs text-green-600 flex items-center mt-1'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     p
  HTML:           <p data-lov-id="src/pages/Dashboard.tsx:133:14" data-lov-name="p" data-component-path="src/pages/Dashboard.tsx" data-com
------------------------------------------------------------
Element 156:
  page_name:      dashboard
  tag_name:       svg
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'xmlns': 'http://www.w3.org/2000/svg', 'width': '24', 'height': '24', 'viewBox': '0 0 24 24', 'fill': 'none', 'stroke': 'currentColor', 'stroke-width': '2', 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'class': 'lucide lucide-trending-up w-3 h-3 mr-1', 'data-lov-id': 'src/pages/Dashboard.tsx:134:16', 'data-lov-name': 'TrendingUp', 'data-component-path': 'src/pages/Dashboard.tsx', 'data-component-line': '134', 'data-component-file': 'Dashboard.tsx', 'data-component-name': 'TrendingUp', 'data-component-content': '%7B%22className%22%3A%22w-3%20h-3%20mr-1%22%7D'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     TrendingUp
  HTML:           <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" str
------------------------------------------------------------
Element 157:
  page_name:      dashboard
  tag_name:       polyline
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'points': '22 7 13.5 15.5 8.5 10.5 2 17'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <polyline points="22 7 13.5 15.5 8.5 10.5 2 17"></polyline>
------------------------------------------------------------
Element 158:
  page_name:      dashboard
  tag_name:       polyline
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'points': '16 7 22 7 22 13'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <polyline points="16 7 22 7 22 13"></polyline>
------------------------------------------------------------
Element 159:
  page_name:      dashboard
  tag_name:       div
  text:           Loan Portfolio TrendMonthly loan disbursements over the last 6 monthsJanFebMarAprMayJun01500000300000045000006000000Customer DistributionCustomer segments by account typePremium 35%Standard 45%Basic 20%
  id:             
  class:          grid grid-cols-1 lg:grid-cols-2 gap-6
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Dashboard.tsx:142:6', 'data-lov-name': 'div', 'data-component-path': 'src/pages/Dashboard.tsx', 'data-component-line': '142', 'data-component-file': 'Dashboard.tsx', 'data-component-name': 'div', 'data-component-content': '%7B%22className%22%3A%22grid%20grid-cols-1%20lg%3Agrid-cols-2%20gap-6%22%7D', 'class': 'grid grid-cols-1 lg:grid-cols-2 gap-6'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     div
  HTML:           <div data-lov-id="src/pages/Dashboard.tsx:142:6" data-lov-name="div" data-component-path="src/pages/Dashboard.tsx" data-
------------------------------------------------------------
Element 160:
  page_name:      dashboard
  tag_name:       div
  text:           Loan Portfolio TrendMonthly loan disbursements over the last 6 monthsJanFebMarAprMayJun01500000300000045000006000000
  id:             
  class:          rounded-lg border bg-card text-card-foreground shadow-sm
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Dashboard.tsx:144:8', 'data-lov-name': 'Card', 'data-component-path': 'src/pages/Dashboard.tsx', 'data-component-line': '144', 'data-component-file': 'Dashboard.tsx', 'data-component-name': 'Card', 'data-component-content': '%7B%7D', 'class': 'rounded-lg border bg-card text-card-foreground shadow-sm'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     Card
  HTML:           <div data-lov-id="src/pages/Dashboard.tsx:144:8" data-lov-name="Card" data-component-path="src/pages/Dashboard.tsx" data
------------------------------------------------------------
Element 161:
  page_name:      dashboard
  tag_name:       div
  text:           Loan Portfolio TrendMonthly loan disbursements over the last 6 months
  id:             
  class:          flex flex-col space-y-1.5 p-6
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Dashboard.tsx:145:10', 'data-lov-name': 'CardHeader', 'data-component-path': 'src/pages/Dashboard.tsx', 'data-component-line': '145', 'data-component-file': 'Dashboard.tsx', 'data-component-name': 'CardHeader', 'data-component-content': '%7B%7D', 'class': 'flex flex-col space-y-1.5 p-6'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     CardHeader
  HTML:           <div data-lov-id="src/pages/Dashboard.tsx:145:10" data-lov-name="CardHeader" data-component-path="src/pages/Dashboard.ts
------------------------------------------------------------
Element 162:
  page_name:      dashboard
  tag_name:       h3
  text:           Loan Portfolio Trend
  id:             
  class:          text-2xl font-semibold leading-none tracking-tight
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Dashboard.tsx:146:12', 'data-lov-name': 'CardTitle', 'data-component-path': 'src/pages/Dashboard.tsx', 'data-component-line': '146', 'data-component-file': 'Dashboard.tsx', 'data-component-name': 'CardTitle', 'data-component-content': '%7B%22text%22%3A%22Loan%20Portfolio%20Trend%22%7D', 'class': 'text-2xl font-semibold leading-none tracking-tight'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     CardTitle
  HTML:           <h3 data-lov-id="src/pages/Dashboard.tsx:146:12" data-lov-name="CardTitle" data-component-path="src/pages/Dashboard.tsx"
------------------------------------------------------------
Element 163:
  page_name:      dashboard
  tag_name:       p
  text:           Monthly loan disbursements over the last 6 months
  id:             
  class:          text-sm text-muted-foreground
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Dashboard.tsx:147:12', 'data-lov-name': 'CardDescription', 'data-component-path': 'src/pages/Dashboard.tsx', 'data-component-line': '147', 'data-component-file': 'Dashboard.tsx', 'data-component-name': 'CardDescription', 'data-component-content': '%7B%22text%22%3A%22Monthly%20loan%20disbursements%20over%20the%20last%206%20months%22%7D', 'class': 'text-sm text-muted-foreground'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     CardDescription
  HTML:           <p data-lov-id="src/pages/Dashboard.tsx:147:12" data-lov-name="CardDescription" data-component-path="src/pages/Dashboard
------------------------------------------------------------
Element 164:
  page_name:      dashboard
  tag_name:       div
  text:           JanFebMarAprMayJun01500000300000045000006000000
  id:             
  class:          p-6 pt-0
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Dashboard.tsx:149:10', 'data-lov-name': 'CardContent', 'data-component-path': 'src/pages/Dashboard.tsx', 'data-component-line': '149', 'data-component-file': 'Dashboard.tsx', 'data-component-name': 'CardContent', 'data-component-content': '%7B%7D', 'class': 'p-6 pt-0'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     CardContent
  HTML:           <div data-lov-id="src/pages/Dashboard.tsx:149:10" data-lov-name="CardContent" data-component-path="src/pages/Dashboard.t
------------------------------------------------------------
Element 165:
  page_name:      dashboard
  tag_name:       div
  text:           JanFebMarAprMayJun01500000300000045000006000000
  id:             
  class:          recharts-responsive-container
  value:          
  placeholder:    
  type:           
  attributes:     {'class': 'recharts-responsive-container', 'style': 'width: 100%; height: 300px; min-width: 0px;'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <div class="recharts-responsive-container" style="width: 100%; height: 300px; min-width: 0px;"><div class="recharts-wrap
------------------------------------------------------------
Element 166:
  page_name:      dashboard
  tag_name:       div
  text:           JanFebMarAprMayJun01500000300000045000006000000
  id:             
  class:          recharts-wrapper
  value:          
  placeholder:    
  type:           
  attributes:     {'class': 'recharts-wrapper', 'style': 'position: relative; cursor: default; width: 419px; height: 300px;'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <div class="recharts-wrapper" style="position: relative; cursor: default; width: 419px; height: 300px;"><svg class="rech
------------------------------------------------------------
Element 167:
  page_name:      dashboard
  tag_name:       svg
  text:           JanFebMarAprMayJun01500000300000045000006000000
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'class': 'recharts-surface', 'width': '419', 'height': '300', 'viewBox': '0 0 419 300', 'style': 'width: 100%; height: 100%;'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <svg class="recharts-surface" width="419" height="300" viewBox="0 0 419 300" style="width: 100%; height: 100%;"><title><
------------------------------------------------------------
Element 168:
  page_name:      dashboard
  tag_name:       title
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {}
  enable?         True
  visible?        False
  editable?       False
  label_text:     
  HTML:           <title></title>
------------------------------------------------------------
Element 169:
  page_name:      dashboard
  tag_name:       desc
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {}
  enable?         True
  visible?        False
  editable?       False
  label_text:     
  HTML:           <desc></desc>
------------------------------------------------------------
Element 170:
  page_name:      dashboard
  tag_name:       defs
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {}
  enable?         True
  visible?        False
  editable?       False
  label_text:     
  HTML:           <defs><clipPath id="recharts1-clip"><rect x="65" y="5" height="260" width="349"></rect></clipPath></defs>
------------------------------------------------------------
Element 171:
  page_name:      dashboard
  tag_name:       clippath
  text:           
  id:             recharts1-clip
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'id': 'recharts1-clip'}
  enable?         True
  visible?        False
  editable?       False
  label_text:     
  HTML:           <clipPath id="recharts1-clip"><rect x="65" y="5" height="260" width="349"></rect></clipPath>
------------------------------------------------------------
Element 172:
  page_name:      dashboard
  tag_name:       rect
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'x': '65', 'y': '5', 'height': '260', 'width': '349'}
  enable?         True
  visible?        False
  editable?       False
  label_text:     
  HTML:           <rect x="65" y="5" height="260" width="349"></rect>
------------------------------------------------------------
Element 173:
  page_name:      dashboard
  tag_name:       g
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'class': 'recharts-cartesian-grid'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <g class="recharts-cartesian-grid"><g class="recharts-cartesian-grid-horizontal"><line stroke-dasharray="3 3" stroke="#c
------------------------------------------------------------
Element 174:
  page_name:      dashboard
  tag_name:       g
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'class': 'recharts-cartesian-grid-horizontal'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <g class="recharts-cartesian-grid-horizontal"><line stroke-dasharray="3 3" stroke="#ccc" fill="none" x="65" y="5" width=
------------------------------------------------------------
Element 175:
  page_name:      dashboard
  tag_name:       line
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'stroke-dasharray': '3 3', 'stroke': '#ccc', 'fill': 'none', 'x': '65', 'y': '5', 'width': '349', 'height': '260', 'x1': '65', 'y1': '265', 'x2': '414', 'y2': '265'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <line stroke-dasharray="3 3" stroke="#ccc" fill="none" x="65" y="5" width="349" height="260" x1="65" y1="265" x2="414" y
------------------------------------------------------------
Element 176:
  page_name:      dashboard
  tag_name:       line
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'stroke-dasharray': '3 3', 'stroke': '#ccc', 'fill': 'none', 'x': '65', 'y': '5', 'width': '349', 'height': '260', 'x1': '65', 'y1': '200', 'x2': '414', 'y2': '200'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <line stroke-dasharray="3 3" stroke="#ccc" fill="none" x="65" y="5" width="349" height="260" x1="65" y1="200" x2="414" y
------------------------------------------------------------
Element 177:
  page_name:      dashboard
  tag_name:       line
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'stroke-dasharray': '3 3', 'stroke': '#ccc', 'fill': 'none', 'x': '65', 'y': '5', 'width': '349', 'height': '260', 'x1': '65', 'y1': '135', 'x2': '414', 'y2': '135'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <line stroke-dasharray="3 3" stroke="#ccc" fill="none" x="65" y="5" width="349" height="260" x1="65" y1="135" x2="414" y
------------------------------------------------------------
Element 178:
  page_name:      dashboard
  tag_name:       line
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'stroke-dasharray': '3 3', 'stroke': '#ccc', 'fill': 'none', 'x': '65', 'y': '5', 'width': '349', 'height': '260', 'x1': '65', 'y1': '70', 'x2': '414', 'y2': '70'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <line stroke-dasharray="3 3" stroke="#ccc" fill="none" x="65" y="5" width="349" height="260" x1="65" y1="70" x2="414" y2
------------------------------------------------------------
Element 179:
  page_name:      dashboard
  tag_name:       line
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'stroke-dasharray': '3 3', 'stroke': '#ccc', 'fill': 'none', 'x': '65', 'y': '5', 'width': '349', 'height': '260', 'x1': '65', 'y1': '5', 'x2': '414', 'y2': '5'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <line stroke-dasharray="3 3" stroke="#ccc" fill="none" x="65" y="5" width="349" height="260" x1="65" y1="5" x2="414" y2=
------------------------------------------------------------
Element 180:
  page_name:      dashboard
  tag_name:       g
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'class': 'recharts-cartesian-grid-vertical'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <g class="recharts-cartesian-grid-vertical"><line stroke-dasharray="3 3" stroke="#ccc" fill="none" x="65" y="5" width="3
------------------------------------------------------------
Element 181:
  page_name:      dashboard
  tag_name:       line
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'stroke-dasharray': '3 3', 'stroke': '#ccc', 'fill': 'none', 'x': '65', 'y': '5', 'width': '349', 'height': '260', 'x1': '94.08333333333333', 'y1': '5', 'x2': '94.08333333333333', 'y2': '265'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <line stroke-dasharray="3 3" stroke="#ccc" fill="none" x="65" y="5" width="349" height="260" x1="94.08333333333333" y1="
------------------------------------------------------------
Element 182:
  page_name:      dashboard
  tag_name:       line
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'stroke-dasharray': '3 3', 'stroke': '#ccc', 'fill': 'none', 'x': '65', 'y': '5', 'width': '349', 'height': '260', 'x1': '152.25', 'y1': '5', 'x2': '152.25', 'y2': '265'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <line stroke-dasharray="3 3" stroke="#ccc" fill="none" x="65" y="5" width="349" height="260" x1="152.25" y1="5" x2="152.
------------------------------------------------------------
Element 183:
  page_name:      dashboard
  tag_name:       line
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'stroke-dasharray': '3 3', 'stroke': '#ccc', 'fill': 'none', 'x': '65', 'y': '5', 'width': '349', 'height': '260', 'x1': '210.41666666666666', 'y1': '5', 'x2': '210.41666666666666', 'y2': '265'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <line stroke-dasharray="3 3" stroke="#ccc" fill="none" x="65" y="5" width="349" height="260" x1="210.41666666666666" y1=
------------------------------------------------------------
Element 184:
  page_name:      dashboard
  tag_name:       line
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'stroke-dasharray': '3 3', 'stroke': '#ccc', 'fill': 'none', 'x': '65', 'y': '5', 'width': '349', 'height': '260', 'x1': '268.5833333333333', 'y1': '5', 'x2': '268.5833333333333', 'y2': '265'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <line stroke-dasharray="3 3" stroke="#ccc" fill="none" x="65" y="5" width="349" height="260" x1="268.5833333333333" y1="
------------------------------------------------------------
Element 185:
  page_name:      dashboard
  tag_name:       line
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'stroke-dasharray': '3 3', 'stroke': '#ccc', 'fill': 'none', 'x': '65', 'y': '5', 'width': '349', 'height': '260', 'x1': '326.74999999999994', 'y1': '5', 'x2': '326.74999999999994', 'y2': '265'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <line stroke-dasharray="3 3" stroke="#ccc" fill="none" x="65" y="5" width="349" height="260" x1="326.74999999999994" y1=
------------------------------------------------------------
Element 186:
  page_name:      dashboard
  tag_name:       line
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'stroke-dasharray': '3 3', 'stroke': '#ccc', 'fill': 'none', 'x': '65', 'y': '5', 'width': '349', 'height': '260', 'x1': '384.91666666666663', 'y1': '5', 'x2': '384.91666666666663', 'y2': '265'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <line stroke-dasharray="3 3" stroke="#ccc" fill="none" x="65" y="5" width="349" height="260" x1="384.91666666666663" y1=
------------------------------------------------------------
Element 187:
  page_name:      dashboard
  tag_name:       line
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'stroke-dasharray': '3 3', 'stroke': '#ccc', 'fill': 'none', 'x': '65', 'y': '5', 'width': '349', 'height': '260', 'x1': '65', 'y1': '5', 'x2': '65', 'y2': '265'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <line stroke-dasharray="3 3" stroke="#ccc" fill="none" x="65" y="5" width="349" height="260" x1="65" y1="5" x2="65" y2="
------------------------------------------------------------
Element 188:
  page_name:      dashboard
  tag_name:       line
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'stroke-dasharray': '3 3', 'stroke': '#ccc', 'fill': 'none', 'x': '65', 'y': '5', 'width': '349', 'height': '260', 'x1': '414', 'y1': '5', 'x2': '414', 'y2': '265'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <line stroke-dasharray="3 3" stroke="#ccc" fill="none" x="65" y="5" width="349" height="260" x1="414" y1="5" x2="414" y2
------------------------------------------------------------
Element 189:
  page_name:      dashboard
  tag_name:       g
  text:           JanFebMarAprMayJun
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'class': 'recharts-layer recharts-cartesian-axis recharts-xAxis xAxis'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <g class="recharts-layer recharts-cartesian-axis recharts-xAxis xAxis"><line orientation="bottom" width="349" height="30
------------------------------------------------------------
Element 190:
  page_name:      dashboard
  tag_name:       line
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'orientation': 'bottom', 'width': '349', 'height': '30', 'x': '65', 'y': '265', 'class': 'recharts-cartesian-axis-line', 'stroke': '#666', 'fill': 'none', 'x1': '65', 'y1': '265', 'x2': '414', 'y2': '265'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <line orientation="bottom" width="349" height="30" x="65" y="265" class="recharts-cartesian-axis-line" stroke="#666" fil
------------------------------------------------------------
Element 191:
  page_name:      dashboard
  tag_name:       g
  text:           JanFebMarAprMayJun
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'class': 'recharts-cartesian-axis-ticks'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <g class="recharts-cartesian-axis-ticks"><g class="recharts-layer recharts-cartesian-axis-tick"><line orientation="botto
------------------------------------------------------------
Element 192:
  page_name:      dashboard
  tag_name:       g
  text:           Jan
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'class': 'recharts-layer recharts-cartesian-axis-tick'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <g class="recharts-layer recharts-cartesian-axis-tick"><line orientation="bottom" width="349" height="30" x="65" y="265"
------------------------------------------------------------
Element 193:
  page_name:      dashboard
  tag_name:       line
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'orientation': 'bottom', 'width': '349', 'height': '30', 'x': '65', 'y': '265', 'class': 'recharts-cartesian-axis-tick-line', 'stroke': '#666', 'fill': 'none', 'x1': '94.08333333333333', 'y1': '271', 'x2': '94.08333333333333', 'y2': '265'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <line orientation="bottom" width="349" height="30" x="65" y="265" class="recharts-cartesian-axis-tick-line" stroke="#666
------------------------------------------------------------
Element 194:
  page_name:      dashboard
  tag_name:       text
  text:           Jan
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'orientation': 'bottom', 'width': '349', 'height': '30', 'stroke': 'none', 'x': '94.08333333333333', 'y': '273', 'class': 'recharts-text recharts-cartesian-axis-tick-value', 'text-anchor': 'middle', 'fill': '#666'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <text orientation="bottom" width="349" height="30" stroke="none" x="94.08333333333333" y="273" class="recharts-text rech
------------------------------------------------------------
Element 195:
  page_name:      dashboard
  tag_name:       tspan
  text:           Jan
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'x': '94.08333333333333', 'dy': '0.71em'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <tspan x="94.08333333333333" dy="0.71em">Jan</tspan>
------------------------------------------------------------
Element 196:
  page_name:      dashboard
  tag_name:       g
  text:           Feb
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'class': 'recharts-layer recharts-cartesian-axis-tick'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <g class="recharts-layer recharts-cartesian-axis-tick"><line orientation="bottom" width="349" height="30" x="65" y="265"
------------------------------------------------------------
Element 197:
  page_name:      dashboard
  tag_name:       line
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'orientation': 'bottom', 'width': '349', 'height': '30', 'x': '65', 'y': '265', 'class': 'recharts-cartesian-axis-tick-line', 'stroke': '#666', 'fill': 'none', 'x1': '152.25', 'y1': '271', 'x2': '152.25', 'y2': '265'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <line orientation="bottom" width="349" height="30" x="65" y="265" class="recharts-cartesian-axis-tick-line" stroke="#666
------------------------------------------------------------
Element 198:
  page_name:      dashboard
  tag_name:       text
  text:           Feb
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'orientation': 'bottom', 'width': '349', 'height': '30', 'stroke': 'none', 'x': '152.25', 'y': '273', 'class': 'recharts-text recharts-cartesian-axis-tick-value', 'text-anchor': 'middle', 'fill': '#666'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <text orientation="bottom" width="349" height="30" stroke="none" x="152.25" y="273" class="recharts-text recharts-cartes
------------------------------------------------------------
Element 199:
  page_name:      dashboard
  tag_name:       tspan
  text:           Feb
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'x': '152.25', 'dy': '0.71em'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <tspan x="152.25" dy="0.71em">Feb</tspan>
------------------------------------------------------------
Element 200:
  page_name:      dashboard
  tag_name:       g
  text:           Mar
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'class': 'recharts-layer recharts-cartesian-axis-tick'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <g class="recharts-layer recharts-cartesian-axis-tick"><line orientation="bottom" width="349" height="30" x="65" y="265"
------------------------------------------------------------
Element 201:
  page_name:      dashboard
  tag_name:       line
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'orientation': 'bottom', 'width': '349', 'height': '30', 'x': '65', 'y': '265', 'class': 'recharts-cartesian-axis-tick-line', 'stroke': '#666', 'fill': 'none', 'x1': '210.41666666666666', 'y1': '271', 'x2': '210.41666666666666', 'y2': '265'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <line orientation="bottom" width="349" height="30" x="65" y="265" class="recharts-cartesian-axis-tick-line" stroke="#666
------------------------------------------------------------
Element 202:
  page_name:      dashboard
  tag_name:       text
  text:           Mar
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'orientation': 'bottom', 'width': '349', 'height': '30', 'stroke': 'none', 'x': '210.41666666666666', 'y': '273', 'class': 'recharts-text recharts-cartesian-axis-tick-value', 'text-anchor': 'middle', 'fill': '#666'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <text orientation="bottom" width="349" height="30" stroke="none" x="210.41666666666666" y="273" class="recharts-text rec
------------------------------------------------------------
Element 203:
  page_name:      dashboard
  tag_name:       tspan
  text:           Mar
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'x': '210.41666666666666', 'dy': '0.71em'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <tspan x="210.41666666666666" dy="0.71em">Mar</tspan>
------------------------------------------------------------
Element 204:
  page_name:      dashboard
  tag_name:       g
  text:           Apr
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'class': 'recharts-layer recharts-cartesian-axis-tick'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <g class="recharts-layer recharts-cartesian-axis-tick"><line orientation="bottom" width="349" height="30" x="65" y="265"
------------------------------------------------------------
Element 205:
  page_name:      dashboard
  tag_name:       line
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'orientation': 'bottom', 'width': '349', 'height': '30', 'x': '65', 'y': '265', 'class': 'recharts-cartesian-axis-tick-line', 'stroke': '#666', 'fill': 'none', 'x1': '268.5833333333333', 'y1': '271', 'x2': '268.5833333333333', 'y2': '265'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <line orientation="bottom" width="349" height="30" x="65" y="265" class="recharts-cartesian-axis-tick-line" stroke="#666
------------------------------------------------------------
Element 206:
  page_name:      dashboard
  tag_name:       text
  text:           Apr
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'orientation': 'bottom', 'width': '349', 'height': '30', 'stroke': 'none', 'x': '268.5833333333333', 'y': '273', 'class': 'recharts-text recharts-cartesian-axis-tick-value', 'text-anchor': 'middle', 'fill': '#666'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <text orientation="bottom" width="349" height="30" stroke="none" x="268.5833333333333" y="273" class="recharts-text rech
------------------------------------------------------------
Element 207:
  page_name:      dashboard
  tag_name:       tspan
  text:           Apr
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'x': '268.5833333333333', 'dy': '0.71em'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <tspan x="268.5833333333333" dy="0.71em">Apr</tspan>
------------------------------------------------------------
Element 208:
  page_name:      dashboard
  tag_name:       g
  text:           May
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'class': 'recharts-layer recharts-cartesian-axis-tick'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <g class="recharts-layer recharts-cartesian-axis-tick"><line orientation="bottom" width="349" height="30" x="65" y="265"
------------------------------------------------------------
Element 209:
  page_name:      dashboard
  tag_name:       line
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'orientation': 'bottom', 'width': '349', 'height': '30', 'x': '65', 'y': '265', 'class': 'recharts-cartesian-axis-tick-line', 'stroke': '#666', 'fill': 'none', 'x1': '326.74999999999994', 'y1': '271', 'x2': '326.74999999999994', 'y2': '265'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <line orientation="bottom" width="349" height="30" x="65" y="265" class="recharts-cartesian-axis-tick-line" stroke="#666
------------------------------------------------------------
Element 210:
  page_name:      dashboard
  tag_name:       text
  text:           May
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'orientation': 'bottom', 'width': '349', 'height': '30', 'stroke': 'none', 'x': '326.74999999999994', 'y': '273', 'class': 'recharts-text recharts-cartesian-axis-tick-value', 'text-anchor': 'middle', 'fill': '#666'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <text orientation="bottom" width="349" height="30" stroke="none" x="326.74999999999994" y="273" class="recharts-text rec
------------------------------------------------------------
Element 211:
  page_name:      dashboard
  tag_name:       tspan
  text:           May
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'x': '326.74999999999994', 'dy': '0.71em'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <tspan x="326.74999999999994" dy="0.71em">May</tspan>
------------------------------------------------------------
Element 212:
  page_name:      dashboard
  tag_name:       g
  text:           Jun
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'class': 'recharts-layer recharts-cartesian-axis-tick'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <g class="recharts-layer recharts-cartesian-axis-tick"><line orientation="bottom" width="349" height="30" x="65" y="265"
------------------------------------------------------------
Element 213:
  page_name:      dashboard
  tag_name:       line
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'orientation': 'bottom', 'width': '349', 'height': '30', 'x': '65', 'y': '265', 'class': 'recharts-cartesian-axis-tick-line', 'stroke': '#666', 'fill': 'none', 'x1': '384.91666666666663', 'y1': '271', 'x2': '384.91666666666663', 'y2': '265'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <line orientation="bottom" width="349" height="30" x="65" y="265" class="recharts-cartesian-axis-tick-line" stroke="#666
------------------------------------------------------------
Element 214:
  page_name:      dashboard
  tag_name:       text
  text:           Jun
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'orientation': 'bottom', 'width': '349', 'height': '30', 'stroke': 'none', 'x': '384.91666666666663', 'y': '273', 'class': 'recharts-text recharts-cartesian-axis-tick-value', 'text-anchor': 'middle', 'fill': '#666'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <text orientation="bottom" width="349" height="30" stroke="none" x="384.91666666666663" y="273" class="recharts-text rec
------------------------------------------------------------
Element 215:
  page_name:      dashboard
  tag_name:       tspan
  text:           Jun
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'x': '384.91666666666663', 'dy': '0.71em'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <tspan x="384.91666666666663" dy="0.71em">Jun</tspan>
------------------------------------------------------------
Element 216:
  page_name:      dashboard
  tag_name:       g
  text:           01500000300000045000006000000
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'class': 'recharts-layer recharts-cartesian-axis recharts-yAxis yAxis'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <g class="recharts-layer recharts-cartesian-axis recharts-yAxis yAxis"><line orientation="left" width="60" height="260" 
------------------------------------------------------------
Element 217:
  page_name:      dashboard
  tag_name:       line
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'orientation': 'left', 'width': '60', 'height': '260', 'x': '5', 'y': '5', 'class': 'recharts-cartesian-axis-line', 'stroke': '#666', 'fill': 'none', 'x1': '65', 'y1': '5', 'x2': '65', 'y2': '265'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <line orientation="left" width="60" height="260" x="5" y="5" class="recharts-cartesian-axis-line" stroke="#666" fill="no
------------------------------------------------------------
Element 218:
  page_name:      dashboard
  tag_name:       g
  text:           01500000300000045000006000000
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'class': 'recharts-cartesian-axis-ticks'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <g class="recharts-cartesian-axis-ticks"><g class="recharts-layer recharts-cartesian-axis-tick"><line orientation="left"
------------------------------------------------------------
Element 219:
  page_name:      dashboard
  tag_name:       g
  text:           0
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'class': 'recharts-layer recharts-cartesian-axis-tick'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <g class="recharts-layer recharts-cartesian-axis-tick"><line orientation="left" width="60" height="260" x="5" y="5" clas
------------------------------------------------------------
Element 220:
  page_name:      dashboard
  tag_name:       line
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'orientation': 'left', 'width': '60', 'height': '260', 'x': '5', 'y': '5', 'class': 'recharts-cartesian-axis-tick-line', 'stroke': '#666', 'fill': 'none', 'x1': '59', 'y1': '265', 'x2': '65', 'y2': '265'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <line orientation="left" width="60" height="260" x="5" y="5" class="recharts-cartesian-axis-tick-line" stroke="#666" fil
------------------------------------------------------------
Element 221:
  page_name:      dashboard
  tag_name:       text
  text:           0
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'orientation': 'left', 'width': '60', 'height': '260', 'stroke': 'none', 'x': '57', 'y': '265', 'class': 'recharts-text recharts-cartesian-axis-tick-value', 'text-anchor': 'end', 'fill': '#666'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <text orientation="left" width="60" height="260" stroke="none" x="57" y="265" class="recharts-text recharts-cartesian-ax
------------------------------------------------------------
Element 222:
  page_name:      dashboard
  tag_name:       tspan
  text:           0
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'x': '57', 'dy': '0.355em'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <tspan x="57" dy="0.355em">0</tspan>
------------------------------------------------------------
Element 223:
  page_name:      dashboard
  tag_name:       g
  text:           1500000
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'class': 'recharts-layer recharts-cartesian-axis-tick'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <g class="recharts-layer recharts-cartesian-axis-tick"><line orientation="left" width="60" height="260" x="5" y="5" clas
------------------------------------------------------------
Element 224:
  page_name:      dashboard
  tag_name:       line
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'orientation': 'left', 'width': '60', 'height': '260', 'x': '5', 'y': '5', 'class': 'recharts-cartesian-axis-tick-line', 'stroke': '#666', 'fill': 'none', 'x1': '59', 'y1': '200', 'x2': '65', 'y2': '200'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <line orientation="left" width="60" height="260" x="5" y="5" class="recharts-cartesian-axis-tick-line" stroke="#666" fil
------------------------------------------------------------
Element 225:
  page_name:      dashboard
  tag_name:       text
  text:           1500000
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'orientation': 'left', 'width': '60', 'height': '260', 'stroke': 'none', 'x': '57', 'y': '200', 'class': 'recharts-text recharts-cartesian-axis-tick-value', 'text-anchor': 'end', 'fill': '#666'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <text orientation="left" width="60" height="260" stroke="none" x="57" y="200" class="recharts-text recharts-cartesian-ax
------------------------------------------------------------
Element 226:
  page_name:      dashboard
  tag_name:       tspan
  text:           1500000
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'x': '57', 'dy': '0.355em'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <tspan x="57" dy="0.355em">1500000</tspan>
------------------------------------------------------------
Element 227:
  page_name:      dashboard
  tag_name:       g
  text:           3000000
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'class': 'recharts-layer recharts-cartesian-axis-tick'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <g class="recharts-layer recharts-cartesian-axis-tick"><line orientation="left" width="60" height="260" x="5" y="5" clas
------------------------------------------------------------
Element 228:
  page_name:      dashboard
  tag_name:       line
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'orientation': 'left', 'width': '60', 'height': '260', 'x': '5', 'y': '5', 'class': 'recharts-cartesian-axis-tick-line', 'stroke': '#666', 'fill': 'none', 'x1': '59', 'y1': '135', 'x2': '65', 'y2': '135'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <line orientation="left" width="60" height="260" x="5" y="5" class="recharts-cartesian-axis-tick-line" stroke="#666" fil
------------------------------------------------------------
Element 229:
  page_name:      dashboard
  tag_name:       text
  text:           3000000
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'orientation': 'left', 'width': '60', 'height': '260', 'stroke': 'none', 'x': '57', 'y': '135', 'class': 'recharts-text recharts-cartesian-axis-tick-value', 'text-anchor': 'end', 'fill': '#666'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <text orientation="left" width="60" height="260" stroke="none" x="57" y="135" class="recharts-text recharts-cartesian-ax
------------------------------------------------------------
Element 230:
  page_name:      dashboard
  tag_name:       tspan
  text:           3000000
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'x': '57', 'dy': '0.355em'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <tspan x="57" dy="0.355em">3000000</tspan>
------------------------------------------------------------
Element 231:
  page_name:      dashboard
  tag_name:       g
  text:           4500000
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'class': 'recharts-layer recharts-cartesian-axis-tick'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <g class="recharts-layer recharts-cartesian-axis-tick"><line orientation="left" width="60" height="260" x="5" y="5" clas
------------------------------------------------------------
Element 232:
  page_name:      dashboard
  tag_name:       line
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'orientation': 'left', 'width': '60', 'height': '260', 'x': '5', 'y': '5', 'class': 'recharts-cartesian-axis-tick-line', 'stroke': '#666', 'fill': 'none', 'x1': '59', 'y1': '70', 'x2': '65', 'y2': '70'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <line orientation="left" width="60" height="260" x="5" y="5" class="recharts-cartesian-axis-tick-line" stroke="#666" fil
------------------------------------------------------------
Element 233:
  page_name:      dashboard
  tag_name:       text
  text:           4500000
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'orientation': 'left', 'width': '60', 'height': '260', 'stroke': 'none', 'x': '57', 'y': '70', 'class': 'recharts-text recharts-cartesian-axis-tick-value', 'text-anchor': 'end', 'fill': '#666'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <text orientation="left" width="60" height="260" stroke="none" x="57" y="70" class="recharts-text recharts-cartesian-axi
------------------------------------------------------------
Element 234:
  page_name:      dashboard
  tag_name:       tspan
  text:           4500000
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'x': '57', 'dy': '0.355em'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <tspan x="57" dy="0.355em">4500000</tspan>
------------------------------------------------------------
Element 235:
  page_name:      dashboard
  tag_name:       g
  text:           6000000
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'class': 'recharts-layer recharts-cartesian-axis-tick'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <g class="recharts-layer recharts-cartesian-axis-tick"><line orientation="left" width="60" height="260" x="5" y="5" clas
------------------------------------------------------------
Element 236:
  page_name:      dashboard
  tag_name:       line
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'orientation': 'left', 'width': '60', 'height': '260', 'x': '5', 'y': '5', 'class': 'recharts-cartesian-axis-tick-line', 'stroke': '#666', 'fill': 'none', 'x1': '59', 'y1': '5', 'x2': '65', 'y2': '5'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <line orientation="left" width="60" height="260" x="5" y="5" class="recharts-cartesian-axis-tick-line" stroke="#666" fil
------------------------------------------------------------
Element 237:
  page_name:      dashboard
  tag_name:       text
  text:           6000000
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'orientation': 'left', 'width': '60', 'height': '260', 'stroke': 'none', 'x': '57', 'y': '12', 'class': 'recharts-text recharts-cartesian-axis-tick-value', 'text-anchor': 'end', 'fill': '#666'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <text orientation="left" width="60" height="260" stroke="none" x="57" y="12" class="recharts-text recharts-cartesian-axi
------------------------------------------------------------
Element 238:
  page_name:      dashboard
  tag_name:       tspan
  text:           6000000
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'x': '57', 'dy': '0.355em'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <tspan x="57" dy="0.355em">6000000</tspan>
------------------------------------------------------------
Element 239:
  page_name:      dashboard
  tag_name:       g
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'class': 'recharts-layer recharts-bar'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <g class="recharts-layer recharts-bar"><g class="recharts-layer recharts-bar-rectangles"><g class="recharts-layer"><g cl
------------------------------------------------------------
Element 240:
  page_name:      dashboard
  tag_name:       g
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'class': 'recharts-layer recharts-bar-rectangles'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <g class="recharts-layer recharts-bar-rectangles"><g class="recharts-layer"><g class="recharts-layer recharts-bar-rectan
------------------------------------------------------------
Element 241:
  page_name:      dashboard
  tag_name:       g
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'class': 'recharts-layer'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <g class="recharts-layer"><g class="recharts-layer recharts-bar-rectangle"><path x="70.81666666666666" y="70" width="46"
------------------------------------------------------------
Element 242:
  page_name:      dashboard
  tag_name:       g
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'class': 'recharts-layer recharts-bar-rectangle'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <g class="recharts-layer recharts-bar-rectangle"><path x="70.81666666666666" y="70" width="46" height="195" radius="0" f
------------------------------------------------------------
Element 243:
  page_name:      dashboard
  tag_name:       path
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'x': '70.81666666666666', 'y': '70', 'width': '46', 'height': '195', 'radius': '0', 'fill': 'hsl(220 100% 45%)', 'class': 'recharts-rectangle', 'd': 'M 70.81666666666666,70 h 46 v 195 h -46 Z'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <path x="70.81666666666666" y="70" width="46" height="195" radius="0" fill="hsl(220 100% 45%)" class="recharts-rectangle
------------------------------------------------------------
Element 244:
  page_name:      dashboard
  tag_name:       g
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'class': 'recharts-layer recharts-bar-rectangle'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <g class="recharts-layer recharts-bar-rectangle"><path x="128.98333333333332" y="57" width="46" height="208" radius="0" 
------------------------------------------------------------
Element 245:
  page_name:      dashboard
  tag_name:       path
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'x': '128.98333333333332', 'y': '57', 'width': '46', 'height': '208', 'radius': '0', 'fill': 'hsl(220 100% 45%)', 'class': 'recharts-rectangle', 'd': 'M 128.98333333333332,57 h 46 v 208 h -46 Z'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <path x="128.98333333333332" y="57" width="46" height="208" radius="0" fill="hsl(220 100% 45%)" class="recharts-rectangl
------------------------------------------------------------
Element 246:
  page_name:      dashboard
  tag_name:       g
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'class': 'recharts-layer recharts-bar-rectangle'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <g class="recharts-layer recharts-bar-rectangle"><path x="187.14999999999998" y="83" width="46" height="182" radius="0" 
------------------------------------------------------------
Element 247:
  page_name:      dashboard
  tag_name:       path
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'x': '187.14999999999998', 'y': '83', 'width': '46', 'height': '182', 'radius': '0', 'fill': 'hsl(220 100% 45%)', 'class': 'recharts-rectangle', 'd': 'M 187.14999999999998,83 h 46 v 182 h -46 Z'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <path x="187.14999999999998" y="83" width="46" height="182" radius="0" fill="hsl(220 100% 45%)" class="recharts-rectangl
------------------------------------------------------------
Element 248:
  page_name:      dashboard
  tag_name:       g
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'class': 'recharts-layer recharts-bar-rectangle'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <g class="recharts-layer recharts-bar-rectangle"><path x="245.31666666666666" y="44" width="46" height="221" radius="0" 
------------------------------------------------------------
Element 249:
  page_name:      dashboard
  tag_name:       path
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'x': '245.31666666666666', 'y': '44', 'width': '46', 'height': '221', 'radius': '0', 'fill': 'hsl(220 100% 45%)', 'class': 'recharts-rectangle', 'd': 'M 245.31666666666666,44 h 46 v 221 h -46 Z'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <path x="245.31666666666666" y="44" width="46" height="221" radius="0" fill="hsl(220 100% 45%)" class="recharts-rectangl
------------------------------------------------------------
Element 250:
  page_name:      dashboard
  tag_name:       g
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'class': 'recharts-layer recharts-bar-rectangle'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <g class="recharts-layer recharts-bar-rectangle"><path x="303.4833333333333" y="52.666666666666686" width="46" height="2
------------------------------------------------------------
Element 251:
  page_name:      dashboard
  tag_name:       path
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'x': '303.4833333333333', 'y': '52.666666666666686', 'width': '46', 'height': '212.33333333333331', 'radius': '0', 'fill': 'hsl(220 100% 45%)', 'class': 'recharts-rectangle', 'd': 'M 303.4833333333333,52.666666666666686 h 46 v 212.33333333333331 h -46 Z'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <path x="303.4833333333333" y="52.666666666666686" width="46" height="212.33333333333331" radius="0" fill="hsl(220 100% 
------------------------------------------------------------
Element 252:
  page_name:      dashboard
  tag_name:       g
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'class': 'recharts-layer recharts-bar-rectangle'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <g class="recharts-layer recharts-bar-rectangle"><path x="361.65" y="35.33333333333334" width="46" height="229.666666666
------------------------------------------------------------
Element 253:
  page_name:      dashboard
  tag_name:       path
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'x': '361.65', 'y': '35.33333333333334', 'width': '46', 'height': '229.66666666666666', 'radius': '0', 'fill': 'hsl(220 100% 45%)', 'class': 'recharts-rectangle', 'd': 'M 361.65,35.33333333333334 h 46 v 229.66666666666666 h -46 Z'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <path x="361.65" y="35.33333333333334" width="46" height="229.66666666666666" radius="0" fill="hsl(220 100% 45%)" class=
------------------------------------------------------------
Element 254:
  page_name:      dashboard
  tag_name:       g
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'class': 'recharts-layer'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <g class="recharts-layer"></g>
------------------------------------------------------------
Element 255:
  page_name:      dashboard
  tag_name:       div
  text:           
  id:             
  class:          recharts-tooltip-wrapper recharts-tooltip-wrapper-right recharts-tooltip-wrapper-bottom
  value:          
  placeholder:    
  type:           
  attributes:     {'tabindex': '-1', 'class': 'recharts-tooltip-wrapper recharts-tooltip-wrapper-right recharts-tooltip-wrapper-bottom', 'style': 'visibility: hidden; pointer-events: none; position: absolute; top: 0px; left: 0px; transform: translate(65px, 10px);'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <div tabindex="-1" class="recharts-tooltip-wrapper recharts-tooltip-wrapper-right recharts-tooltip-wrapper-bottom" style
------------------------------------------------------------
Element 256:
  page_name:      dashboard
  tag_name:       div
  text:           
  id:             
  class:          recharts-default-tooltip
  value:          
  placeholder:    
  type:           
  attributes:     {'class': 'recharts-default-tooltip', 'style': 'margin: 0px; padding: 10px; background-color: rgb(255, 255, 255); border: 1px solid rgb(204, 204, 204); white-space: nowrap;'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <div class="recharts-default-tooltip" style="margin: 0px; padding: 10px; background-color: rgb(255, 255, 255); border: 1
------------------------------------------------------------
Element 257:
  page_name:      dashboard
  tag_name:       p
  text:           
  id:             
  class:          recharts-tooltip-label
  value:          
  placeholder:    
  type:           
  attributes:     {'class': 'recharts-tooltip-label', 'style': 'margin: 0px;'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <p class="recharts-tooltip-label" style="margin: 0px;"></p>
------------------------------------------------------------
Element 258:
  page_name:      dashboard
  tag_name:       div
  text:           Customer DistributionCustomer segments by account typePremium 35%Standard 45%Basic 20%
  id:             
  class:          rounded-lg border bg-card text-card-foreground shadow-sm
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Dashboard.tsx:165:8', 'data-lov-name': 'Card', 'data-component-path': 'src/pages/Dashboard.tsx', 'data-component-line': '165', 'data-component-file': 'Dashboard.tsx', 'data-component-name': 'Card', 'data-component-content': '%7B%7D', 'class': 'rounded-lg border bg-card text-card-foreground shadow-sm'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     Card
  HTML:           <div data-lov-id="src/pages/Dashboard.tsx:165:8" data-lov-name="Card" data-component-path="src/pages/Dashboard.tsx" data
------------------------------------------------------------
Element 259:
  page_name:      dashboard
  tag_name:       div
  text:           Customer DistributionCustomer segments by account type
  id:             
  class:          flex flex-col space-y-1.5 p-6
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Dashboard.tsx:166:10', 'data-lov-name': 'CardHeader', 'data-component-path': 'src/pages/Dashboard.tsx', 'data-component-line': '166', 'data-component-file': 'Dashboard.tsx', 'data-component-name': 'CardHeader', 'data-component-content': '%7B%7D', 'class': 'flex flex-col space-y-1.5 p-6'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     CardHeader
  HTML:           <div data-lov-id="src/pages/Dashboard.tsx:166:10" data-lov-name="CardHeader" data-component-path="src/pages/Dashboard.ts
------------------------------------------------------------
Element 260:
  page_name:      dashboard
  tag_name:       h3
  text:           Customer Distribution
  id:             
  class:          text-2xl font-semibold leading-none tracking-tight
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Dashboard.tsx:167:12', 'data-lov-name': 'CardTitle', 'data-component-path': 'src/pages/Dashboard.tsx', 'data-component-line': '167', 'data-component-file': 'Dashboard.tsx', 'data-component-name': 'CardTitle', 'data-component-content': '%7B%22text%22%3A%22Customer%20Distribution%22%7D', 'class': 'text-2xl font-semibold leading-none tracking-tight'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     CardTitle
  HTML:           <h3 data-lov-id="src/pages/Dashboard.tsx:167:12" data-lov-name="CardTitle" data-component-path="src/pages/Dashboard.tsx"
------------------------------------------------------------
Element 261:
  page_name:      dashboard
  tag_name:       p
  text:           Customer segments by account type
  id:             
  class:          text-sm text-muted-foreground
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Dashboard.tsx:168:12', 'data-lov-name': 'CardDescription', 'data-component-path': 'src/pages/Dashboard.tsx', 'data-component-line': '168', 'data-component-file': 'Dashboard.tsx', 'data-component-name': 'CardDescription', 'data-component-content': '%7B%22text%22%3A%22Customer%20segments%20by%20account%20type%22%7D', 'class': 'text-sm text-muted-foreground'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     CardDescription
  HTML:           <p data-lov-id="src/pages/Dashboard.tsx:168:12" data-lov-name="CardDescription" data-component-path="src/pages/Dashboard
------------------------------------------------------------
Element 262:
  page_name:      dashboard
  tag_name:       div
  text:           Premium 35%Standard 45%Basic 20%
  id:             
  class:          p-6 pt-0
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Dashboard.tsx:170:10', 'data-lov-name': 'CardContent', 'data-component-path': 'src/pages/Dashboard.tsx', 'data-component-line': '170', 'data-component-file': 'Dashboard.tsx', 'data-component-name': 'CardContent', 'data-component-content': '%7B%7D', 'class': 'p-6 pt-0'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     CardContent
  HTML:           <div data-lov-id="src/pages/Dashboard.tsx:170:10" data-lov-name="CardContent" data-component-path="src/pages/Dashboard.t
------------------------------------------------------------
Element 263:
  page_name:      dashboard
  tag_name:       div
  text:           Premium 35%Standard 45%Basic 20%
  id:             
  class:          recharts-responsive-container
  value:          
  placeholder:    
  type:           
  attributes:     {'class': 'recharts-responsive-container', 'style': 'width: 100%; height: 300px; min-width: 0px;'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <div class="recharts-responsive-container" style="width: 100%; height: 300px; min-width: 0px;"><div class="recharts-wrap
------------------------------------------------------------
Element 264:
  page_name:      dashboard
  tag_name:       div
  text:           Premium 35%Standard 45%Basic 20%
  id:             
  class:          recharts-wrapper
  value:          
  placeholder:    
  type:           
  attributes:     {'class': 'recharts-wrapper', 'style': 'position: relative; cursor: default; width: 419px; height: 300px;'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <div class="recharts-wrapper" style="position: relative; cursor: default; width: 419px; height: 300px;"><svg cx="50%" cy
------------------------------------------------------------
Element 265:
  page_name:      dashboard
  tag_name:       svg
  text:           Premium 35%Standard 45%Basic 20%
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'cx': '50%', 'cy': '50%', 'class': 'recharts-surface', 'width': '419', 'height': '300', 'viewBox': '0 0 419 300', 'style': 'width: 100%; height: 100%;'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <svg cx="50%" cy="50%" class="recharts-surface" width="419" height="300" viewBox="0 0 419 300" style="width: 100%; heigh
------------------------------------------------------------
Element 266:
  page_name:      dashboard
  tag_name:       title
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {}
  enable?         True
  visible?        False
  editable?       False
  label_text:     
  HTML:           <title></title>
------------------------------------------------------------
Element 267:
  page_name:      dashboard
  tag_name:       desc
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {}
  enable?         True
  visible?        False
  editable?       False
  label_text:     
  HTML:           <desc></desc>
------------------------------------------------------------
Element 268:
  page_name:      dashboard
  tag_name:       defs
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {}
  enable?         True
  visible?        False
  editable?       False
  label_text:     
  HTML:           <defs><clipPath id="recharts4-clip"><rect x="5" y="5" height="290" width="409"></rect></clipPath></defs>
------------------------------------------------------------
Element 269:
  page_name:      dashboard
  tag_name:       clippath
  text:           
  id:             recharts4-clip
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'id': 'recharts4-clip'}
  enable?         True
  visible?        False
  editable?       False
  label_text:     
  HTML:           <clipPath id="recharts4-clip"><rect x="5" y="5" height="290" width="409"></rect></clipPath>
------------------------------------------------------------
Element 270:
  page_name:      dashboard
  tag_name:       rect
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'x': '5', 'y': '5', 'height': '290', 'width': '409'}
  enable?         True
  visible?        False
  editable?       False
  label_text:     
  HTML:           <rect x="5" y="5" height="290" width="409"></rect>
------------------------------------------------------------
Element 271:
  page_name:      dashboard
  tag_name:       g
  text:           Premium 35%Standard 45%Basic 20%
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'class': 'recharts-layer recharts-pie', 'tabindex': '0'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <g class="recharts-layer recharts-pie" tabindex="0"><g class="recharts-layer"><g class="recharts-layer recharts-pie-sect
------------------------------------------------------------
Element 272:
  page_name:      dashboard
  tag_name:       g
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'class': 'recharts-layer'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <g class="recharts-layer"><g class="recharts-layer recharts-pie-sector" tabindex="-1"><path cx="209.5" cy="150" name="Pr
------------------------------------------------------------
Element 273:
  page_name:      dashboard
  tag_name:       g
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'class': 'recharts-layer recharts-pie-sector', 'tabindex': '-1'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <g class="recharts-layer recharts-pie-sector" tabindex="-1"><path cx="209.5" cy="150" name="Premium" stroke="#fff" fill=
------------------------------------------------------------
Element 274:
  page_name:      dashboard
  tag_name:       path
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'cx': '209.5', 'cy': '150', 'name': 'Premium', 'stroke': '#fff', 'fill': '#0ea5e9', 'color': '#0ea5e9', 'tabindex': '-1', 'class': 'recharts-sector', 'd': 'M 289.5,150\n    A 80,80,0,\n    0,0,\n    162.47717981660216,85.2786404500042\n  L 209.5,150 Z', 'role': 'img'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <path cx="209.5" cy="150" name="Premium" stroke="#fff" fill="#0ea5e9" color="#0ea5e9" tabindex="-1" class="recharts-sect
------------------------------------------------------------
Element 275:
  page_name:      dashboard
  tag_name:       g
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'class': 'recharts-layer recharts-pie-sector', 'tabindex': '-1'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <g class="recharts-layer recharts-pie-sector" tabindex="-1"><path cx="209.5" cy="150" name="Standard" stroke="#fff" fill
------------------------------------------------------------
Element 276:
  page_name:      dashboard
  tag_name:       path
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'cx': '209.5', 'cy': '150', 'name': 'Standard', 'stroke': '#fff', 'fill': '#3b82f6', 'color': '#3b82f6', 'tabindex': '-1', 'class': 'recharts-sector', 'd': 'M 162.47717981660216,85.2786404500042\n    A 80,80,0,\n    0,0,\n    234.22135954999578,226.0845213036123\n  L 209.5,150 Z', 'role': 'img'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <path cx="209.5" cy="150" name="Standard" stroke="#fff" fill="#3b82f6" color="#3b82f6" tabindex="-1" class="recharts-sec
------------------------------------------------------------
Element 277:
  page_name:      dashboard
  tag_name:       g
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'class': 'recharts-layer recharts-pie-sector', 'tabindex': '-1'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <g class="recharts-layer recharts-pie-sector" tabindex="-1"><path cx="209.5" cy="150" name="Basic" stroke="#fff" fill="#
------------------------------------------------------------
Element 278:
  page_name:      dashboard
  tag_name:       path
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'cx': '209.5', 'cy': '150', 'name': 'Basic', 'stroke': '#fff', 'fill': '#1e40af', 'color': '#1e40af', 'tabindex': '-1', 'class': 'recharts-sector', 'd': 'M 234.22135954999578,226.0845213036123\n    A 80,80,0,\n    0,0,\n    289.5,150.00000000000003\n  L 209.5,150 Z', 'role': 'img'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <path cx="209.5" cy="150" name="Basic" stroke="#fff" fill="#1e40af" color="#1e40af" tabindex="-1" class="recharts-sector
------------------------------------------------------------
Element 279:
  page_name:      dashboard
  tag_name:       g
  text:           Premium 35%Standard 45%Basic 20%
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'class': 'recharts-layer recharts-pie-labels'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <g class="recharts-layer recharts-pie-labels"><g class="recharts-layer"><text cx="209.5" cy="150" stroke="none" name="Pr
------------------------------------------------------------
Element 280:
  page_name:      dashboard
  tag_name:       g
  text:           Premium 35%
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'class': 'recharts-layer'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <g class="recharts-layer"><text cx="209.5" cy="150" stroke="none" name="Premium" color="#0ea5e9" alignment-baseline="mid
------------------------------------------------------------
Element 281:
  page_name:      dashboard
  tag_name:       text
  text:           Premium 35%
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'cx': '209.5', 'cy': '150', 'stroke': 'none', 'name': 'Premium', 'color': '#0ea5e9', 'alignment-baseline': 'middle', 'x': '254.89904997395467', 'y': '60.89934758116323', 'class': 'recharts-text recharts-pie-label-text', 'text-anchor': 'start', 'fill': '#0ea5e9'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <text cx="209.5" cy="150" stroke="none" name="Premium" color="#0ea5e9" alignment-baseline="middle" x="254.89904997395467
------------------------------------------------------------
Element 282:
  page_name:      dashboard
  tag_name:       tspan
  text:           Premium 35%
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'x': '254.89904997395467', 'dy': '0em'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <tspan x="254.89904997395467" dy="0em">Premium 35%</tspan>
------------------------------------------------------------
Element 283:
  page_name:      dashboard
  tag_name:       g
  text:           Standard 45%
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'class': 'recharts-layer'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <g class="recharts-layer"><text cx="209.5" cy="150" stroke="none" name="Standard" color="#3b82f6" alignment-baseline="mi
------------------------------------------------------------
Element 284:
  page_name:      dashboard
  tag_name:       text
  text:           Standard 45%
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'cx': '209.5', 'cy': '150', 'stroke': 'none', 'name': 'Standard', 'color': '#3b82f6', 'alignment-baseline': 'middle', 'x': '120.39934758116321', 'y': '195.39904997395467', 'class': 'recharts-text recharts-pie-label-text', 'text-anchor': 'end', 'fill': '#3b82f6'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <text cx="209.5" cy="150" stroke="none" name="Standard" color="#3b82f6" alignment-baseline="middle" x="120.3993475811632
------------------------------------------------------------
Element 285:
  page_name:      dashboard
  tag_name:       tspan
  text:           Standard 45%
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'x': '120.39934758116321', 'dy': '0em'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <tspan x="120.39934758116321" dy="0em">Standard 45%</tspan>
------------------------------------------------------------
Element 286:
  page_name:      dashboard
  tag_name:       g
  text:           Basic 20%
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'class': 'recharts-layer'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <g class="recharts-layer"><text cx="209.5" cy="150" stroke="none" name="Basic" color="#1e40af" alignment-baseline="middl
------------------------------------------------------------
Element 287:
  page_name:      dashboard
  tag_name:       text
  text:           Basic 20%
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'cx': '209.5', 'cy': '150', 'stroke': 'none', 'name': 'Basic', 'color': '#1e40af', 'alignment-baseline': 'middle', 'x': '290.4016994374947', 'y': '208.77852522924735', 'class': 'recharts-text recharts-pie-label-text', 'text-anchor': 'start', 'fill': '#1e40af'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <text cx="209.5" cy="150" stroke="none" name="Basic" color="#1e40af" alignment-baseline="middle" x="290.4016994374947" y
------------------------------------------------------------
Element 288:
  page_name:      dashboard
  tag_name:       tspan
  text:           Basic 20%
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'x': '290.4016994374947', 'dy': '0em'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <tspan x="290.4016994374947" dy="0em">Basic 20%</tspan>
------------------------------------------------------------
Element 289:
  page_name:      dashboard
  tag_name:       div
  text:           
  id:             
  class:          recharts-tooltip-wrapper recharts-tooltip-wrapper-right recharts-tooltip-wrapper-bottom
  value:          
  placeholder:    
  type:           
  attributes:     {'tabindex': '-1', 'class': 'recharts-tooltip-wrapper recharts-tooltip-wrapper-right recharts-tooltip-wrapper-bottom', 'style': 'visibility: hidden; pointer-events: none; position: absolute; top: 0px; left: 0px; transform: translate(10px, 10px);'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <div tabindex="-1" class="recharts-tooltip-wrapper recharts-tooltip-wrapper-right recharts-tooltip-wrapper-bottom" style
------------------------------------------------------------
Element 290:
  page_name:      dashboard
  tag_name:       div
  text:           
  id:             
  class:          recharts-default-tooltip
  value:          
  placeholder:    
  type:           
  attributes:     {'class': 'recharts-default-tooltip', 'style': 'margin: 0px; padding: 10px; background-color: rgb(255, 255, 255); border: 1px solid rgb(204, 204, 204); white-space: nowrap;'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <div class="recharts-default-tooltip" style="margin: 0px; padding: 10px; background-color: rgb(255, 255, 255); border: 1
------------------------------------------------------------
Element 291:
  page_name:      dashboard
  tag_name:       p
  text:           
  id:             
  class:          recharts-tooltip-label
  value:          
  placeholder:    
  type:           
  attributes:     {'class': 'recharts-tooltip-label', 'style': 'margin: 0px;'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <p class="recharts-tooltip-label" style="margin: 0px;"></p>
------------------------------------------------------------
Element 292:
  page_name:      dashboard
  tag_name:       div
  text:           Recent ActivitiesLatest customer interactions and transactionsSarah JohnsonLoan Application Approved$250,0002 hours agoMichael ChenAccount Verification Pending-4 hours agoEmma DavisLarge Transaction Alert$75,0006 hours agoRobert WilsonMonthly Payment Received$3,2008 hours ago
  id:             
  class:          rounded-lg border bg-card text-card-foreground shadow-sm
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Dashboard.tsx:195:6', 'data-lov-name': 'Card', 'data-component-path': 'src/pages/Dashboard.tsx', 'data-component-line': '195', 'data-component-file': 'Dashboard.tsx', 'data-component-name': 'Card', 'data-component-content': '%7B%7D', 'class': 'rounded-lg border bg-card text-card-foreground shadow-sm'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     Card
  HTML:           <div data-lov-id="src/pages/Dashboard.tsx:195:6" data-lov-name="Card" data-component-path="src/pages/Dashboard.tsx" data
------------------------------------------------------------
Element 293:
  page_name:      dashboard
  tag_name:       div
  text:           Recent ActivitiesLatest customer interactions and transactions
  id:             
  class:          flex flex-col space-y-1.5 p-6
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Dashboard.tsx:196:8', 'data-lov-name': 'CardHeader', 'data-component-path': 'src/pages/Dashboard.tsx', 'data-component-line': '196', 'data-component-file': 'Dashboard.tsx', 'data-component-name': 'CardHeader', 'data-component-content': '%7B%7D', 'class': 'flex flex-col space-y-1.5 p-6'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     CardHeader
  HTML:           <div data-lov-id="src/pages/Dashboard.tsx:196:8" data-lov-name="CardHeader" data-component-path="src/pages/Dashboard.tsx
------------------------------------------------------------
Element 294:
  page_name:      dashboard
  tag_name:       h3
  text:           Recent Activities
  id:             
  class:          text-2xl font-semibold leading-none tracking-tight
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Dashboard.tsx:197:10', 'data-lov-name': 'CardTitle', 'data-component-path': 'src/pages/Dashboard.tsx', 'data-component-line': '197', 'data-component-file': 'Dashboard.tsx', 'data-component-name': 'CardTitle', 'data-component-content': '%7B%22text%22%3A%22Recent%20Activities%22%7D', 'class': 'text-2xl font-semibold leading-none tracking-tight'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     CardTitle
  HTML:           <h3 data-lov-id="src/pages/Dashboard.tsx:197:10" data-lov-name="CardTitle" data-component-path="src/pages/Dashboard.tsx"
------------------------------------------------------------
Element 295:
  page_name:      dashboard
  tag_name:       p
  text:           Latest customer interactions and transactions
  id:             
  class:          text-sm text-muted-foreground
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Dashboard.tsx:198:10', 'data-lov-name': 'CardDescription', 'data-component-path': 'src/pages/Dashboard.tsx', 'data-component-line': '198', 'data-component-file': 'Dashboard.tsx', 'data-component-name': 'CardDescription', 'data-component-content': '%7B%22text%22%3A%22Latest%20customer%20interactions%20and%20transactions%22%7D', 'class': 'text-sm text-muted-foreground'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     CardDescription
  HTML:           <p data-lov-id="src/pages/Dashboard.tsx:198:10" data-lov-name="CardDescription" data-component-path="src/pages/Dashboard
------------------------------------------------------------
Element 296:
  page_name:      dashboard
  tag_name:       div
  text:           Sarah JohnsonLoan Application Approved$250,0002 hours agoMichael ChenAccount Verification Pending-4 hours agoEmma DavisLarge Transaction Alert$75,0006 hours agoRobert WilsonMonthly Payment Received$3,2008 hours ago
  id:             
  class:          p-6 pt-0
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Dashboard.tsx:200:8', 'data-lov-name': 'CardContent', 'data-component-path': 'src/pages/Dashboard.tsx', 'data-component-line': '200', 'data-component-file': 'Dashboard.tsx', 'data-component-name': 'CardContent', 'data-component-content': '%7B%7D', 'class': 'p-6 pt-0'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     CardContent
  HTML:           <div data-lov-id="src/pages/Dashboard.tsx:200:8" data-lov-name="CardContent" data-component-path="src/pages/Dashboard.ts
------------------------------------------------------------
Element 297:
  page_name:      dashboard
  tag_name:       div
  text:           Sarah JohnsonLoan Application Approved$250,0002 hours agoMichael ChenAccount Verification Pending-4 hours agoEmma DavisLarge Transaction Alert$75,0006 hours agoRobert WilsonMonthly Payment Received$3,2008 hours ago
  id:             
  class:          space-y-4
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Dashboard.tsx:201:10', 'data-lov-name': 'div', 'data-component-path': 'src/pages/Dashboard.tsx', 'data-component-line': '201', 'data-component-file': 'Dashboard.tsx', 'data-component-name': 'div', 'data-component-content': '%7B%22className%22%3A%22space-y-4%22%7D', 'class': 'space-y-4'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     div
  HTML:           <div data-lov-id="src/pages/Dashboard.tsx:201:10" data-lov-name="div" data-component-path="src/pages/Dashboard.tsx" data
------------------------------------------------------------
Element 298:
  page_name:      dashboard
  tag_name:       div
  text:           Sarah JohnsonLoan Application Approved$250,0002 hours ago
  id:             
  class:          flex items-center justify-between p-4 border rounded-lg
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Dashboard.tsx:203:14', 'data-lov-name': 'div', 'data-component-path': 'src/pages/Dashboard.tsx', 'data-component-line': '203', 'data-component-file': 'Dashboard.tsx', 'data-component-name': 'div', 'data-component-content': '%7B%22className%22%3A%22flex%20items-center%20justify-between%20p-4%20border%20rounded-lg%22%7D', 'class': 'flex items-center justify-between p-4 border rounded-lg'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     div
  HTML:           <div data-lov-id="src/pages/Dashboard.tsx:203:14" data-lov-name="div" data-component-path="src/pages/Dashboard.tsx" data
------------------------------------------------------------
Element 299:
  page_name:      dashboard
  tag_name:       div
  text:           Sarah JohnsonLoan Application Approved
  id:             
  class:          flex items-center gap-4
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Dashboard.tsx:204:16', 'data-lov-name': 'div', 'data-component-path': 'src/pages/Dashboard.tsx', 'data-component-line': '204', 'data-component-file': 'Dashboard.tsx', 'data-component-name': 'div', 'data-component-content': '%7B%22className%22%3A%22flex%20items-center%20gap-4%22%7D', 'class': 'flex items-center gap-4'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     div
  HTML:           <div data-lov-id="src/pages/Dashboard.tsx:204:16" data-lov-name="div" data-component-path="src/pages/Dashboard.tsx" data
------------------------------------------------------------
Element 300:
  page_name:      dashboard
  tag_name:       div
  text:           
  id:             
  class:          w-10 h-10 rounded-full flex items-center justify-center bg-green-100
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Dashboard.tsx:205:18', 'data-lov-name': 'div', 'data-component-path': 'src/pages/Dashboard.tsx', 'data-component-line': '205', 'data-component-file': 'Dashboard.tsx', 'data-component-name': 'div', 'data-component-content': '%7B%7D', 'class': 'w-10 h-10 rounded-full flex items-center justify-center bg-green-100'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     div
  HTML:           <div data-lov-id="src/pages/Dashboard.tsx:205:18" data-lov-name="div" data-component-path="src/pages/Dashboard.tsx" data
------------------------------------------------------------
Element 301:
  page_name:      dashboard
  tag_name:       svg
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'xmlns': 'http://www.w3.org/2000/svg', 'width': '24', 'height': '24', 'viewBox': '0 0 24 24', 'fill': 'none', 'stroke': 'currentColor', 'stroke-width': '2', 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'class': 'lucide lucide-circle-check-big w-5 h-5 text-green-600', 'data-lov-id': 'src/pages/Dashboard.tsx:211:22', 'data-lov-name': 'CheckCircle', 'data-component-path': 'src/pages/Dashboard.tsx', 'data-component-line': '211', 'data-component-file': 'Dashboard.tsx', 'data-component-name': 'CheckCircle', 'data-component-content': '%7B%22className%22%3A%22w-5%20h-5%20text-green-600%22%7D'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     CheckCircle
  HTML:           <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" str
------------------------------------------------------------
Element 302:
  page_name:      dashboard
  tag_name:       path
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'d': 'M21.801 10A10 10 0 1 1 17 3.335'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <path d="M21.801 10A10 10 0 1 1 17 3.335"></path>
------------------------------------------------------------
Element 303:
  page_name:      dashboard
  tag_name:       path
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'d': 'm9 11 3 3L22 4'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <path d="m9 11 3 3L22 4"></path>
------------------------------------------------------------
Element 304:
  page_name:      dashboard
  tag_name:       div
  text:           Sarah JohnsonLoan Application Approved
  id:             
  class:          
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Dashboard.tsx:218:18', 'data-lov-name': 'div', 'data-component-path': 'src/pages/Dashboard.tsx', 'data-component-line': '218', 'data-component-file': 'Dashboard.tsx', 'data-component-name': 'div', 'data-component-content': '%7B%7D'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     div
  HTML:           <div data-lov-id="src/pages/Dashboard.tsx:218:18" data-lov-name="div" data-component-path="src/pages/Dashboard.tsx" data
------------------------------------------------------------
Element 305:
  page_name:      dashboard
  tag_name:       p
  text:           Sarah Johnson
  id:             
  class:          font-medium text-gray-900
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Dashboard.tsx:219:20', 'data-lov-name': 'p', 'data-component-path': 'src/pages/Dashboard.tsx', 'data-component-line': '219', 'data-component-file': 'Dashboard.tsx', 'data-component-name': 'p', 'data-component-content': '%7B%22className%22%3A%22font-medium%20text-gray-900%22%7D', 'class': 'font-medium text-gray-900'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     p
  HTML:           <p data-lov-id="src/pages/Dashboard.tsx:219:20" data-lov-name="p" data-component-path="src/pages/Dashboard.tsx" data-com
------------------------------------------------------------
Element 306:
  page_name:      dashboard
  tag_name:       p
  text:           Loan Application Approved
  id:             
  class:          text-sm text-gray-600
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Dashboard.tsx:220:20', 'data-lov-name': 'p', 'data-component-path': 'src/pages/Dashboard.tsx', 'data-component-line': '220', 'data-component-file': 'Dashboard.tsx', 'data-component-name': 'p', 'data-component-content': '%7B%22className%22%3A%22text-sm%20text-gray-600%22%7D', 'class': 'text-sm text-gray-600'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     p
  HTML:           <p data-lov-id="src/pages/Dashboard.tsx:220:20" data-lov-name="p" data-component-path="src/pages/Dashboard.tsx" data-com
------------------------------------------------------------
Element 307:
  page_name:      dashboard
  tag_name:       div
  text:           $250,0002 hours ago
  id:             
  class:          text-right
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Dashboard.tsx:223:16', 'data-lov-name': 'div', 'data-component-path': 'src/pages/Dashboard.tsx', 'data-component-line': '223', 'data-component-file': 'Dashboard.tsx', 'data-component-name': 'div', 'data-component-content': '%7B%22className%22%3A%22text-right%22%7D', 'class': 'text-right'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     div
  HTML:           <div data-lov-id="src/pages/Dashboard.tsx:223:16" data-lov-name="div" data-component-path="src/pages/Dashboard.tsx" data
------------------------------------------------------------
Element 308:
  page_name:      dashboard
  tag_name:       p
  text:           $250,000
  id:             
  class:          font-medium text-gray-900
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Dashboard.tsx:224:18', 'data-lov-name': 'p', 'data-component-path': 'src/pages/Dashboard.tsx', 'data-component-line': '224', 'data-component-file': 'Dashboard.tsx', 'data-component-name': 'p', 'data-component-content': '%7B%22className%22%3A%22font-medium%20text-gray-900%22%7D', 'class': 'font-medium text-gray-900'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     p
  HTML:           <p data-lov-id="src/pages/Dashboard.tsx:224:18" data-lov-name="p" data-component-path="src/pages/Dashboard.tsx" data-com
------------------------------------------------------------
Element 309:
  page_name:      dashboard
  tag_name:       p
  text:           2 hours ago
  id:             
  class:          text-sm text-gray-500
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Dashboard.tsx:225:18', 'data-lov-name': 'p', 'data-component-path': 'src/pages/Dashboard.tsx', 'data-component-line': '225', 'data-component-file': 'Dashboard.tsx', 'data-component-name': 'p', 'data-component-content': '%7B%22className%22%3A%22text-sm%20text-gray-500%22%7D', 'class': 'text-sm text-gray-500'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     p
  HTML:           <p data-lov-id="src/pages/Dashboard.tsx:225:18" data-lov-name="p" data-component-path="src/pages/Dashboard.tsx" data-com
------------------------------------------------------------
Element 310:
  page_name:      dashboard
  tag_name:       div
  text:           Michael ChenAccount Verification Pending-4 hours ago
  id:             
  class:          flex items-center justify-between p-4 border rounded-lg
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Dashboard.tsx:203:14', 'data-lov-name': 'div', 'data-component-path': 'src/pages/Dashboard.tsx', 'data-component-line': '203', 'data-component-file': 'Dashboard.tsx', 'data-component-name': 'div', 'data-component-content': '%7B%22className%22%3A%22flex%20items-center%20justify-between%20p-4%20border%20rounded-lg%22%7D', 'class': 'flex items-center justify-between p-4 border rounded-lg'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     div
  HTML:           <div data-lov-id="src/pages/Dashboard.tsx:203:14" data-lov-name="div" data-component-path="src/pages/Dashboard.tsx" data
------------------------------------------------------------
Element 311:
  page_name:      dashboard
  tag_name:       div
  text:           Michael ChenAccount Verification Pending
  id:             
  class:          flex items-center gap-4
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Dashboard.tsx:204:16', 'data-lov-name': 'div', 'data-component-path': 'src/pages/Dashboard.tsx', 'data-component-line': '204', 'data-component-file': 'Dashboard.tsx', 'data-component-name': 'div', 'data-component-content': '%7B%22className%22%3A%22flex%20items-center%20gap-4%22%7D', 'class': 'flex items-center gap-4'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     div
  HTML:           <div data-lov-id="src/pages/Dashboard.tsx:204:16" data-lov-name="div" data-component-path="src/pages/Dashboard.tsx" data
------------------------------------------------------------
Element 312:
  page_name:      dashboard
  tag_name:       div
  text:           
  id:             
  class:          w-10 h-10 rounded-full flex items-center justify-center bg-yellow-100
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Dashboard.tsx:205:18', 'data-lov-name': 'div', 'data-component-path': 'src/pages/Dashboard.tsx', 'data-component-line': '205', 'data-component-file': 'Dashboard.tsx', 'data-component-name': 'div', 'data-component-content': '%7B%7D', 'class': 'w-10 h-10 rounded-full flex items-center justify-center bg-yellow-100'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     div
  HTML:           <div data-lov-id="src/pages/Dashboard.tsx:205:18" data-lov-name="div" data-component-path="src/pages/Dashboard.tsx" data
------------------------------------------------------------
Element 313:
  page_name:      dashboard
  tag_name:       svg
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'xmlns': 'http://www.w3.org/2000/svg', 'width': '24', 'height': '24', 'viewBox': '0 0 24 24', 'fill': 'none', 'stroke': 'currentColor', 'stroke-width': '2', 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'class': 'lucide lucide-triangle-alert w-5 h-5 text-yellow-600', 'data-lov-id': 'src/pages/Dashboard.tsx:213:22', 'data-lov-name': 'AlertTriangle', 'data-component-path': 'src/pages/Dashboard.tsx', 'data-component-line': '213', 'data-component-file': 'Dashboard.tsx', 'data-component-name': 'AlertTriangle', 'data-component-content': '%7B%22className%22%3A%22w-5%20h-5%20text-yellow-600%22%7D'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     AlertTriangle
  HTML:           <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" str
------------------------------------------------------------
Element 314:
  page_name:      dashboard
  tag_name:       path
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'d': 'm21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3"></path>
------------------------------------------------------------
Element 315:
  page_name:      dashboard
  tag_name:       path
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'d': 'M12 9v4'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <path d="M12 9v4"></path>
------------------------------------------------------------
Element 316:
  page_name:      dashboard
  tag_name:       path
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'d': 'M12 17h.01'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <path d="M12 17h.01"></path>
------------------------------------------------------------
Element 317:
  page_name:      dashboard
  tag_name:       div
  text:           Michael ChenAccount Verification Pending
  id:             
  class:          
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Dashboard.tsx:218:18', 'data-lov-name': 'div', 'data-component-path': 'src/pages/Dashboard.tsx', 'data-component-line': '218', 'data-component-file': 'Dashboard.tsx', 'data-component-name': 'div', 'data-component-content': '%7B%7D'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     div
  HTML:           <div data-lov-id="src/pages/Dashboard.tsx:218:18" data-lov-name="div" data-component-path="src/pages/Dashboard.tsx" data
------------------------------------------------------------
Element 318:
  page_name:      dashboard
  tag_name:       p
  text:           Michael Chen
  id:             
  class:          font-medium text-gray-900
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Dashboard.tsx:219:20', 'data-lov-name': 'p', 'data-component-path': 'src/pages/Dashboard.tsx', 'data-component-line': '219', 'data-component-file': 'Dashboard.tsx', 'data-component-name': 'p', 'data-component-content': '%7B%22className%22%3A%22font-medium%20text-gray-900%22%7D', 'class': 'font-medium text-gray-900'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     p
  HTML:           <p data-lov-id="src/pages/Dashboard.tsx:219:20" data-lov-name="p" data-component-path="src/pages/Dashboard.tsx" data-com
------------------------------------------------------------
Element 319:
  page_name:      dashboard
  tag_name:       p
  text:           Account Verification Pending
  id:             
  class:          text-sm text-gray-600
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Dashboard.tsx:220:20', 'data-lov-name': 'p', 'data-component-path': 'src/pages/Dashboard.tsx', 'data-component-line': '220', 'data-component-file': 'Dashboard.tsx', 'data-component-name': 'p', 'data-component-content': '%7B%22className%22%3A%22text-sm%20text-gray-600%22%7D', 'class': 'text-sm text-gray-600'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     p
  HTML:           <p data-lov-id="src/pages/Dashboard.tsx:220:20" data-lov-name="p" data-component-path="src/pages/Dashboard.tsx" data-com
------------------------------------------------------------
Element 320:
  page_name:      dashboard
  tag_name:       div
  text:           -4 hours ago
  id:             
  class:          text-right
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Dashboard.tsx:223:16', 'data-lov-name': 'div', 'data-component-path': 'src/pages/Dashboard.tsx', 'data-component-line': '223', 'data-component-file': 'Dashboard.tsx', 'data-component-name': 'div', 'data-component-content': '%7B%22className%22%3A%22text-right%22%7D', 'class': 'text-right'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     div
  HTML:           <div data-lov-id="src/pages/Dashboard.tsx:223:16" data-lov-name="div" data-component-path="src/pages/Dashboard.tsx" data
------------------------------------------------------------
Element 321:
  page_name:      dashboard
  tag_name:       p
  text:           -
  id:             
  class:          font-medium text-gray-900
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Dashboard.tsx:224:18', 'data-lov-name': 'p', 'data-component-path': 'src/pages/Dashboard.tsx', 'data-component-line': '224', 'data-component-file': 'Dashboard.tsx', 'data-component-name': 'p', 'data-component-content': '%7B%22className%22%3A%22font-medium%20text-gray-900%22%7D', 'class': 'font-medium text-gray-900'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     p
  HTML:           <p data-lov-id="src/pages/Dashboard.tsx:224:18" data-lov-name="p" data-component-path="src/pages/Dashboard.tsx" data-com
------------------------------------------------------------
Element 322:
  page_name:      dashboard
  tag_name:       p
  text:           4 hours ago
  id:             
  class:          text-sm text-gray-500
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Dashboard.tsx:225:18', 'data-lov-name': 'p', 'data-component-path': 'src/pages/Dashboard.tsx', 'data-component-line': '225', 'data-component-file': 'Dashboard.tsx', 'data-component-name': 'p', 'data-component-content': '%7B%22className%22%3A%22text-sm%20text-gray-500%22%7D', 'class': 'text-sm text-gray-500'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     p
  HTML:           <p data-lov-id="src/pages/Dashboard.tsx:225:18" data-lov-name="p" data-component-path="src/pages/Dashboard.tsx" data-com
------------------------------------------------------------
Element 323:
  page_name:      dashboard
  tag_name:       div
  text:           Emma DavisLarge Transaction Alert$75,0006 hours ago
  id:             
  class:          flex items-center justify-between p-4 border rounded-lg
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Dashboard.tsx:203:14', 'data-lov-name': 'div', 'data-component-path': 'src/pages/Dashboard.tsx', 'data-component-line': '203', 'data-component-file': 'Dashboard.tsx', 'data-component-name': 'div', 'data-component-content': '%7B%22className%22%3A%22flex%20items-center%20justify-between%20p-4%20border%20rounded-lg%22%7D', 'class': 'flex items-center justify-between p-4 border rounded-lg'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     div
  HTML:           <div data-lov-id="src/pages/Dashboard.tsx:203:14" data-lov-name="div" data-component-path="src/pages/Dashboard.tsx" data
------------------------------------------------------------
Element 324:
  page_name:      dashboard
  tag_name:       div
  text:           Emma DavisLarge Transaction Alert
  id:             
  class:          flex items-center gap-4
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Dashboard.tsx:204:16', 'data-lov-name': 'div', 'data-component-path': 'src/pages/Dashboard.tsx', 'data-component-line': '204', 'data-component-file': 'Dashboard.tsx', 'data-component-name': 'div', 'data-component-content': '%7B%22className%22%3A%22flex%20items-center%20gap-4%22%7D', 'class': 'flex items-center gap-4'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     div
  HTML:           <div data-lov-id="src/pages/Dashboard.tsx:204:16" data-lov-name="div" data-component-path="src/pages/Dashboard.tsx" data
------------------------------------------------------------
Element 325:
  page_name:      dashboard
  tag_name:       div
  text:           
  id:             
  class:          w-10 h-10 rounded-full flex items-center justify-center bg-red-100
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Dashboard.tsx:205:18', 'data-lov-name': 'div', 'data-component-path': 'src/pages/Dashboard.tsx', 'data-component-line': '205', 'data-component-file': 'Dashboard.tsx', 'data-component-name': 'div', 'data-component-content': '%7B%7D', 'class': 'w-10 h-10 rounded-full flex items-center justify-center bg-red-100'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     div
  HTML:           <div data-lov-id="src/pages/Dashboard.tsx:205:18" data-lov-name="div" data-component-path="src/pages/Dashboard.tsx" data
------------------------------------------------------------
Element 326:
  page_name:      dashboard
  tag_name:       svg
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'xmlns': 'http://www.w3.org/2000/svg', 'width': '24', 'height': '24', 'viewBox': '0 0 24 24', 'fill': 'none', 'stroke': 'currentColor', 'stroke-width': '2', 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'class': 'lucide lucide-triangle-alert w-5 h-5 text-red-600', 'data-lov-id': 'src/pages/Dashboard.tsx:215:22', 'data-lov-name': 'AlertTriangle', 'data-component-path': 'src/pages/Dashboard.tsx', 'data-component-line': '215', 'data-component-file': 'Dashboard.tsx', 'data-component-name': 'AlertTriangle', 'data-component-content': '%7B%22className%22%3A%22w-5%20h-5%20text-red-600%22%7D'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     AlertTriangle
  HTML:           <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" str
------------------------------------------------------------
Element 327:
  page_name:      dashboard
  tag_name:       path
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'d': 'm21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3"></path>
------------------------------------------------------------
Element 328:
  page_name:      dashboard
  tag_name:       path
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'d': 'M12 9v4'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <path d="M12 9v4"></path>
------------------------------------------------------------
Element 329:
  page_name:      dashboard
  tag_name:       path
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'d': 'M12 17h.01'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <path d="M12 17h.01"></path>
------------------------------------------------------------
Element 330:
  page_name:      dashboard
  tag_name:       div
  text:           Emma DavisLarge Transaction Alert
  id:             
  class:          
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Dashboard.tsx:218:18', 'data-lov-name': 'div', 'data-component-path': 'src/pages/Dashboard.tsx', 'data-component-line': '218', 'data-component-file': 'Dashboard.tsx', 'data-component-name': 'div', 'data-component-content': '%7B%7D'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     div
  HTML:           <div data-lov-id="src/pages/Dashboard.tsx:218:18" data-lov-name="div" data-component-path="src/pages/Dashboard.tsx" data
------------------------------------------------------------
Element 331:
  page_name:      dashboard
  tag_name:       p
  text:           Emma Davis
  id:             
  class:          font-medium text-gray-900
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Dashboard.tsx:219:20', 'data-lov-name': 'p', 'data-component-path': 'src/pages/Dashboard.tsx', 'data-component-line': '219', 'data-component-file': 'Dashboard.tsx', 'data-component-name': 'p', 'data-component-content': '%7B%22className%22%3A%22font-medium%20text-gray-900%22%7D', 'class': 'font-medium text-gray-900'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     p
  HTML:           <p data-lov-id="src/pages/Dashboard.tsx:219:20" data-lov-name="p" data-component-path="src/pages/Dashboard.tsx" data-com
------------------------------------------------------------
Element 332:
  page_name:      dashboard
  tag_name:       p
  text:           Large Transaction Alert
  id:             
  class:          text-sm text-gray-600
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Dashboard.tsx:220:20', 'data-lov-name': 'p', 'data-component-path': 'src/pages/Dashboard.tsx', 'data-component-line': '220', 'data-component-file': 'Dashboard.tsx', 'data-component-name': 'p', 'data-component-content': '%7B%22className%22%3A%22text-sm%20text-gray-600%22%7D', 'class': 'text-sm text-gray-600'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     p
  HTML:           <p data-lov-id="src/pages/Dashboard.tsx:220:20" data-lov-name="p" data-component-path="src/pages/Dashboard.tsx" data-com
------------------------------------------------------------
Element 333:
  page_name:      dashboard
  tag_name:       div
  text:           $75,0006 hours ago
  id:             
  class:          text-right
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Dashboard.tsx:223:16', 'data-lov-name': 'div', 'data-component-path': 'src/pages/Dashboard.tsx', 'data-component-line': '223', 'data-component-file': 'Dashboard.tsx', 'data-component-name': 'div', 'data-component-content': '%7B%22className%22%3A%22text-right%22%7D', 'class': 'text-right'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     div
  HTML:           <div data-lov-id="src/pages/Dashboard.tsx:223:16" data-lov-name="div" data-component-path="src/pages/Dashboard.tsx" data
------------------------------------------------------------
Element 334:
  page_name:      dashboard
  tag_name:       p
  text:           $75,000
  id:             
  class:          font-medium text-gray-900
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Dashboard.tsx:224:18', 'data-lov-name': 'p', 'data-component-path': 'src/pages/Dashboard.tsx', 'data-component-line': '224', 'data-component-file': 'Dashboard.tsx', 'data-component-name': 'p', 'data-component-content': '%7B%22className%22%3A%22font-medium%20text-gray-900%22%7D', 'class': 'font-medium text-gray-900'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     p
  HTML:           <p data-lov-id="src/pages/Dashboard.tsx:224:18" data-lov-name="p" data-component-path="src/pages/Dashboard.tsx" data-com
------------------------------------------------------------
Element 335:
  page_name:      dashboard
  tag_name:       p
  text:           6 hours ago
  id:             
  class:          text-sm text-gray-500
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Dashboard.tsx:225:18', 'data-lov-name': 'p', 'data-component-path': 'src/pages/Dashboard.tsx', 'data-component-line': '225', 'data-component-file': 'Dashboard.tsx', 'data-component-name': 'p', 'data-component-content': '%7B%22className%22%3A%22text-sm%20text-gray-500%22%7D', 'class': 'text-sm text-gray-500'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     p
  HTML:           <p data-lov-id="src/pages/Dashboard.tsx:225:18" data-lov-name="p" data-component-path="src/pages/Dashboard.tsx" data-com
------------------------------------------------------------
Element 336:
  page_name:      dashboard
  tag_name:       div
  text:           Robert WilsonMonthly Payment Received$3,2008 hours ago
  id:             
  class:          flex items-center justify-between p-4 border rounded-lg
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Dashboard.tsx:203:14', 'data-lov-name': 'div', 'data-component-path': 'src/pages/Dashboard.tsx', 'data-component-line': '203', 'data-component-file': 'Dashboard.tsx', 'data-component-name': 'div', 'data-component-content': '%7B%22className%22%3A%22flex%20items-center%20justify-between%20p-4%20border%20rounded-lg%22%7D', 'class': 'flex items-center justify-between p-4 border rounded-lg'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     div
  HTML:           <div data-lov-id="src/pages/Dashboard.tsx:203:14" data-lov-name="div" data-component-path="src/pages/Dashboard.tsx" data
------------------------------------------------------------
Element 337:
  page_name:      dashboard
  tag_name:       div
  text:           Robert WilsonMonthly Payment Received
  id:             
  class:          flex items-center gap-4
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Dashboard.tsx:204:16', 'data-lov-name': 'div', 'data-component-path': 'src/pages/Dashboard.tsx', 'data-component-line': '204', 'data-component-file': 'Dashboard.tsx', 'data-component-name': 'div', 'data-component-content': '%7B%22className%22%3A%22flex%20items-center%20gap-4%22%7D', 'class': 'flex items-center gap-4'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     div
  HTML:           <div data-lov-id="src/pages/Dashboard.tsx:204:16" data-lov-name="div" data-component-path="src/pages/Dashboard.tsx" data
------------------------------------------------------------
Element 338:
  page_name:      dashboard
  tag_name:       div
  text:           
  id:             
  class:          w-10 h-10 rounded-full flex items-center justify-center bg-green-100
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Dashboard.tsx:205:18', 'data-lov-name': 'div', 'data-component-path': 'src/pages/Dashboard.tsx', 'data-component-line': '205', 'data-component-file': 'Dashboard.tsx', 'data-component-name': 'div', 'data-component-content': '%7B%7D', 'class': 'w-10 h-10 rounded-full flex items-center justify-center bg-green-100'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     div
  HTML:           <div data-lov-id="src/pages/Dashboard.tsx:205:18" data-lov-name="div" data-component-path="src/pages/Dashboard.tsx" data
------------------------------------------------------------
Element 339:
  page_name:      dashboard
  tag_name:       svg
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'xmlns': 'http://www.w3.org/2000/svg', 'width': '24', 'height': '24', 'viewBox': '0 0 24 24', 'fill': 'none', 'stroke': 'currentColor', 'stroke-width': '2', 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'class': 'lucide lucide-circle-check-big w-5 h-5 text-green-600', 'data-lov-id': 'src/pages/Dashboard.tsx:211:22', 'data-lov-name': 'CheckCircle', 'data-component-path': 'src/pages/Dashboard.tsx', 'data-component-line': '211', 'data-component-file': 'Dashboard.tsx', 'data-component-name': 'CheckCircle', 'data-component-content': '%7B%22className%22%3A%22w-5%20h-5%20text-green-600%22%7D'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     CheckCircle
  HTML:           <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" str
------------------------------------------------------------
Element 340:
  page_name:      dashboard
  tag_name:       path
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'d': 'M21.801 10A10 10 0 1 1 17 3.335'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <path d="M21.801 10A10 10 0 1 1 17 3.335"></path>
------------------------------------------------------------
Element 341:
  page_name:      dashboard
  tag_name:       path
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'d': 'm9 11 3 3L22 4'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <path d="m9 11 3 3L22 4"></path>
------------------------------------------------------------
Element 342:
  page_name:      dashboard
  tag_name:       div
  text:           Robert WilsonMonthly Payment Received
  id:             
  class:          
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Dashboard.tsx:218:18', 'data-lov-name': 'div', 'data-component-path': 'src/pages/Dashboard.tsx', 'data-component-line': '218', 'data-component-file': 'Dashboard.tsx', 'data-component-name': 'div', 'data-component-content': '%7B%7D'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     div
  HTML:           <div data-lov-id="src/pages/Dashboard.tsx:218:18" data-lov-name="div" data-component-path="src/pages/Dashboard.tsx" data
------------------------------------------------------------
Element 343:
  page_name:      dashboard
  tag_name:       p
  text:           Robert Wilson
  id:             
  class:          font-medium text-gray-900
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Dashboard.tsx:219:20', 'data-lov-name': 'p', 'data-component-path': 'src/pages/Dashboard.tsx', 'data-component-line': '219', 'data-component-file': 'Dashboard.tsx', 'data-component-name': 'p', 'data-component-content': '%7B%22className%22%3A%22font-medium%20text-gray-900%22%7D', 'class': 'font-medium text-gray-900'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     p
  HTML:           <p data-lov-id="src/pages/Dashboard.tsx:219:20" data-lov-name="p" data-component-path="src/pages/Dashboard.tsx" data-com
------------------------------------------------------------
Element 344:
  page_name:      dashboard
  tag_name:       p
  text:           Monthly Payment Received
  id:             
  class:          text-sm text-gray-600
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Dashboard.tsx:220:20', 'data-lov-name': 'p', 'data-component-path': 'src/pages/Dashboard.tsx', 'data-component-line': '220', 'data-component-file': 'Dashboard.tsx', 'data-component-name': 'p', 'data-component-content': '%7B%22className%22%3A%22text-sm%20text-gray-600%22%7D', 'class': 'text-sm text-gray-600'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     p
  HTML:           <p data-lov-id="src/pages/Dashboard.tsx:220:20" data-lov-name="p" data-component-path="src/pages/Dashboard.tsx" data-com
------------------------------------------------------------
Element 345:
  page_name:      dashboard
  tag_name:       div
  text:           $3,2008 hours ago
  id:             
  class:          text-right
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Dashboard.tsx:223:16', 'data-lov-name': 'div', 'data-component-path': 'src/pages/Dashboard.tsx', 'data-component-line': '223', 'data-component-file': 'Dashboard.tsx', 'data-component-name': 'div', 'data-component-content': '%7B%22className%22%3A%22text-right%22%7D', 'class': 'text-right'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     div
  HTML:           <div data-lov-id="src/pages/Dashboard.tsx:223:16" data-lov-name="div" data-component-path="src/pages/Dashboard.tsx" data
------------------------------------------------------------
Element 346:
  page_name:      dashboard
  tag_name:       p
  text:           $3,200
  id:             
  class:          font-medium text-gray-900
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Dashboard.tsx:224:18', 'data-lov-name': 'p', 'data-component-path': 'src/pages/Dashboard.tsx', 'data-component-line': '224', 'data-component-file': 'Dashboard.tsx', 'data-component-name': 'p', 'data-component-content': '%7B%22className%22%3A%22font-medium%20text-gray-900%22%7D', 'class': 'font-medium text-gray-900'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     p
  HTML:           <p data-lov-id="src/pages/Dashboard.tsx:224:18" data-lov-name="p" data-component-path="src/pages/Dashboard.tsx" data-com
------------------------------------------------------------
Element 347:
  page_name:      dashboard
  tag_name:       p
  text:           8 hours ago
  id:             
  class:          text-sm text-gray-500
  value:          
  placeholder:    
  type:           
  attributes:     {'data-lov-id': 'src/pages/Dashboard.tsx:225:18', 'data-lov-name': 'p', 'data-component-path': 'src/pages/Dashboard.tsx', 'data-component-line': '225', 'data-component-file': 'Dashboard.tsx', 'data-component-name': 'p', 'data-component-content': '%7B%22className%22%3A%22text-sm%20text-gray-500%22%7D', 'class': 'text-sm text-gray-500'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     p
  HTML:           <p data-lov-id="src/pages/Dashboard.tsx:225:18" data-lov-name="p" data-component-path="src/pages/Dashboard.tsx" data-com
------------------------------------------------------------
Element 348:
  page_name:      dashboard
  tag_name:       script
  text:           
  id:             
  class:          
  value:          
  placeholder:    
  type:           module
  attributes:     {'src': 'https://cdn.gpteng.co/lovable.js', 'type': 'module'}
  enable?         True
  visible?        False
  editable?       False
  label_text:     
  HTML:           <script src="https://cdn.gpteng.co/lovable.js" type="module"></script>
------------------------------------------------------------
Element 349:
  page_name:      dashboard
  tag_name:       a
  text:           Edit with 






















































	×
  id:             lovable-badge
  class:          
  value:          
  placeholder:    
  type:           
  attributes:     {'id': 'lovable-badge', 'target': '_blank', 'href': 'https://lovable.dev/projects/6b5a94f5-dd17-46dd-8f84-e0942fda5a0d?utm_source=lovable-badge'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <a id="lovable-badge" target="_blank" href="https://lovable.dev/projects/6b5a94f5-dd17-46dd-8f84-e0942fda5a0d?utm_source
------------------------------------------------------------
Element 350:
  page_name:      dashboard
  tag_name:       span
  text:           Edit with
  id:             
  class:          
  value:          
  placeholder:    
  type:           
  attributes:     {'style': 'color: #A1A1AA;'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <span style="color: #A1A1AA;">Edit with</span>
------------------------------------------------------------
Element 351:
  page_name:      dashboard
  tag_name:       svg
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'width': '60', 'height': '12', 'viewBox': '0 0 116 22', 'fill': 'none', 'xmlns': 'http://www.w3.org/2000/svg'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <svg width="60" height="12" viewBox="0 0 116 22" fill="none" xmlns="http://www.w3.org/2000/svg">
<path d="M109.108 21.11
------------------------------------------------------------
Element 352:
  page_name:      dashboard
  tag_name:       path
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'d': 'M109.108 21.115C107.649 21.115 106.381 20.8369 105.306 20.2807C104.23 19.7154 103.391 18.8675 102.789 17.7369C102.196 16.6063 101.9 15.2068 101.9 13.5382C101.9 11.9518 102.21 10.5841 102.83 9.4353C103.45 8.27736 104.307 7.3975 105.401 6.79574C106.495 6.19398 107.74 5.89309 109.135 5.89309C110.475 5.89309 111.665 6.18486 112.705 6.76839C113.744 7.35192 114.551 8.19986 115.125 9.31221C115.709 10.4246 116.001 11.7557 116.001 13.3057C116.001 13.8619 115.996 14.3041 115.987 14.6324H105.087V11.7603H113.347L111.788 12.2937C111.788 11.546 111.679 10.9215 111.46 10.42C111.25 9.90941 110.94 9.52647 110.53 9.27118C110.12 9.01588 109.623 8.88824 109.039 8.88824C108.428 8.88824 107.89 9.03868 107.425 9.33956C106.97 9.63133 106.614 10.069 106.359 10.6525C106.112 11.236 105.989 11.9381 105.989 12.7587V14.1674C105.989 15.0062 106.117 15.7174 106.372 16.3009C106.628 16.8844 106.992 17.3266 107.466 17.6275C107.941 17.9193 108.501 18.0651 109.149 18.0651C109.86 18.0651 110.448 17.8828 110.913 17.5181C111.378 17.1443 111.67 16.62 111.788 15.9453H115.932C115.805 17.0029 115.444 17.9193 114.852 18.6943C114.268 19.4693 113.489 20.0665 112.513 20.4859C111.537 20.9053 110.402 21.115 109.108 21.115Z', 'fill': '#FCFBF8'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <path d="M109.108 21.115C107.649 21.115 106.381 20.8369 105.306 20.2807C104.23 19.7154 103.391 18.8675 102.789 17.7369C1
------------------------------------------------------------
Element 353:
  page_name:      dashboard
  tag_name:       path
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'d': 'M96.5167 1.1061H100.661V20.7181H96.5167V1.1061Z', 'fill': '#FCFBF8'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <path d="M96.5167 1.1061H100.661V20.7181H96.5167V1.1061Z" fill="#FCFBF8"></path>
------------------------------------------------------------
Element 354:
  page_name:      dashboard
  tag_name:       path
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'d': 'M89.4649 21.1148C88.6808 21.1148 87.9788 20.978 87.3588 20.7045C86.7479 20.4309 86.2282 20.0207 85.7996 19.4736C85.3711 18.9174 85.052 18.2336 84.8423 17.4221L85.2799 17.5452V20.7182H81.177V6.28948H85.321V9.51713L84.856 9.59919C85.0657 8.82419 85.3848 8.16316 85.8133 7.6161C86.251 7.05992 86.7844 6.63595 87.4135 6.34419C88.0426 6.04331 88.7492 5.89287 89.5333 5.89287C90.7095 5.89287 91.7307 6.19831 92.5968 6.80919C93.463 7.42007 94.1286 8.29992 94.5936 9.44875C95.0586 10.5885 95.2911 11.9424 95.2911 13.5107C95.2911 15.0698 95.054 16.4237 94.5799 17.5726C94.1058 18.7123 93.4265 19.5876 92.5421 20.1984C91.6668 20.8093 90.6411 21.1148 89.4649 21.1148ZM88.1794 17.9555C88.7994 17.9555 89.3191 17.7732 89.7385 17.4084C90.167 17.0437 90.4861 16.5286 90.6958 15.863C90.9146 15.1974 91.0241 14.4133 91.0241 13.5107C91.0241 12.608 90.9146 11.8239 90.6958 11.1583C90.4861 10.4927 90.167 9.97757 89.7385 9.61286C89.3191 9.23904 88.7994 9.05213 88.1794 9.05213C87.5685 9.05213 87.0442 9.23904 86.6066 9.61286C86.178 9.97757 85.8544 10.4973 85.6355 11.172C85.4167 11.8376 85.3073 12.6171 85.3073 13.5107C85.3073 14.4133 85.4167 15.1974 85.6355 15.863C85.8544 16.5286 86.178 17.0437 86.6066 17.4084C87.0442 17.7732 87.5685 17.9555 88.1794 17.9555ZM81.177 1.1061H85.321V6.28948H81.177V1.1061Z', 'fill': '#FCFBF8'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <path d="M89.4649 21.1148C88.6808 21.1148 87.9788 20.978 87.3588 20.7045C86.7479 20.4309 86.2282 20.0207 85.7996 19.4736
------------------------------------------------------------
Element 355:
  page_name:      dashboard
  tag_name:       path
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'d': 'M70.7749 21.115C69.8723 21.115 69.0608 20.9372 68.3405 20.5816C67.6293 20.226 67.0686 19.72 66.6583 19.0635C66.2571 18.3979 66.0565 17.6229 66.0565 16.7385C66.0565 15.3891 66.4531 14.3588 67.2464 13.6476C68.0396 12.9274 69.1839 12.4578 70.6792 12.239L73.182 11.8834C73.6834 11.8104 74.08 11.7193 74.3718 11.6099C74.6636 11.5004 74.8778 11.3546 75.0146 11.1722C75.1514 10.9807 75.2197 10.7391 75.2197 10.4474C75.2197 10.1465 75.1377 9.87294 74.9736 9.62677C74.8186 9.37147 74.5815 9.17088 74.2624 9.025C73.9524 8.87 73.574 8.7925 73.1272 8.7925C72.4161 8.7925 71.8462 8.97941 71.4177 9.35324C70.9892 9.71794 70.7567 10.2194 70.7202 10.8576H66.4395C66.4759 9.89118 66.7677 9.03412 67.3148 8.28647C67.8709 7.52971 68.6414 6.94162 69.6261 6.52221C70.6108 6.1028 71.7505 5.89309 73.0452 5.89309C74.4037 5.89309 75.5525 6.11648 76.4917 6.56324C77.4308 7.00089 78.1374 7.63 78.6115 8.45059C79.0947 9.27118 79.3364 10.2513 79.3364 11.391V17.4087C79.3364 18.056 79.382 18.6578 79.4731 19.214C79.5734 19.761 79.7147 20.1075 79.8971 20.2534V20.7184H75.589C75.4887 20.3263 75.4112 19.8841 75.3565 19.3918C75.3018 18.8994 75.2699 18.3797 75.2608 17.8326L75.9309 17.5454C75.7577 18.1928 75.4386 18.79 74.9736 19.3371C74.5177 19.875 73.9296 20.3081 73.2093 20.6363C72.4981 20.9554 71.6867 21.115 70.7749 21.115ZM72.3067 18.0788C72.8902 18.0788 73.4053 17.9512 73.8521 17.6959C74.2989 17.4315 74.6408 17.0668 74.8778 16.6018C75.124 16.1368 75.2471 15.6079 75.2471 15.0153V13.1279L75.589 13.3194C75.3702 13.6112 75.0967 13.8346 74.7684 13.9896C74.4493 14.1446 74.0162 14.2768 73.4692 14.3862L72.4161 14.5913C71.714 14.7281 71.1852 14.9378 70.8296 15.2204C70.4831 15.5031 70.3099 15.8997 70.3099 16.4103C70.3099 16.9209 70.4968 17.3266 70.8706 17.6275C71.2445 17.9284 71.7231 18.0788 72.3067 18.0788Z', 'fill': '#FCFBF8'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <path d="M70.7749 21.115C69.8723 21.115 69.0608 20.9372 68.3405 20.5816C67.6293 20.226 67.0686 19.72 66.6583 19.0635C66.
------------------------------------------------------------
Element 356:
  page_name:      dashboard
  tag_name:       path
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'d': 'M51.962 6.28958H56.3659L60.1542 18.6668H58.8276L62.4656 6.28958H66.7463L61.7544 20.7182H57.1454L51.962 6.28958Z', 'fill': '#FCFBF8'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <path d="M51.962 6.28958H56.3659L60.1542 18.6668H58.8276L62.4656 6.28958H66.7463L61.7544 20.7182H57.1454L51.962 6.28958Z
------------------------------------------------------------
Element 357:
  page_name:      dashboard
  tag_name:       path
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'d': 'M45.4846 21.115C44.0531 21.115 42.7949 20.805 41.7099 20.185C40.634 19.565 39.7997 18.6806 39.2071 17.5318C38.6236 16.3829 38.3318 15.0381 38.3318 13.4972C38.3318 11.9563 38.6236 10.616 39.2071 9.47633C39.7997 8.3275 40.634 7.44309 41.7099 6.82309C42.7949 6.20309 44.0531 5.89309 45.4846 5.89309C46.916 5.89309 48.1697 6.20309 49.2456 6.82309C50.3215 7.44309 51.1512 8.3275 51.7347 9.47633C52.3274 10.616 52.6237 11.9563 52.6237 13.4972C52.6237 15.0381 52.3274 16.3829 51.7347 17.5318C51.1512 18.6806 50.3215 19.565 49.2456 20.185C48.1697 20.805 46.916 21.115 45.4846 21.115ZM45.4846 17.9421C46.0863 17.9421 46.6015 17.7779 47.03 17.4497C47.4585 17.1123 47.7868 16.6154 48.0147 15.959C48.2427 15.2934 48.3566 14.4728 48.3566 13.4972C48.3566 12.0475 48.1059 10.9488 47.6044 10.2012C47.103 9.44441 46.3963 9.06603 45.4846 9.06603C44.8828 9.06603 44.3631 9.23471 43.9255 9.57206C43.4969 9.9003 43.1687 10.3972 42.9408 11.0628C42.7128 11.7193 42.5988 12.5307 42.5988 13.4972C42.5988 14.4637 42.7128 15.2797 42.9408 15.9453C43.1687 16.6109 43.4969 17.1123 43.9255 17.4497C44.3631 17.7779 44.8828 17.9421 45.4846 17.9421Z', 'fill': '#FCFBF8'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <path d="M45.4846 21.115C44.0531 21.115 42.7949 20.805 41.7099 20.185C40.634 19.565 39.7997 18.6806 39.2071 17.5318C38.6
------------------------------------------------------------
Element 358:
  page_name:      dashboard
  tag_name:       path
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'d': 'M26.2195 1.10631H30.514V17.6623L29.7481 16.7734C29.7481 16.7734 31.8751 16.7734 35.534 16.7734C39.1928 16.7734 38.6925 20.7184 38.6925 20.7184H26.2195V1.10631Z', 'fill': '#FCFBF8'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <path d="M26.2195 1.10631H30.514V17.6623L29.7481 16.7734C29.7481 16.7734 31.8751 16.7734 35.534 16.7734C39.1928 16.7734 
------------------------------------------------------------
Element 359:
  page_name:      dashboard
  tag_name:       mask
  text:           
  id:             mask0_19703_15608
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'id': 'mask0_19703_15608', 'style': 'mask-type:alpha', 'maskUnits': 'userSpaceOnUse', 'x': '0', 'y': '0', 'width': '20', 'height': '21'}
  enable?         True
  visible?        False
  editable?       False
  label_text:     
  HTML:           <mask id="mask0_19703_15608" style="mask-type:alpha" maskUnits="userSpaceOnUse" x="0" y="0" width="20" height="21">
<pat
------------------------------------------------------------
Element 360:
  page_name:      dashboard
  tag_name:       path
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'fill-rule': 'evenodd', 'clip-rule': 'evenodd', 'd': 'M5.90405 0.885124C9.16477 0.885124 11.8081 3.53543 11.8081 6.80474V9.05456H13.773C17.0337 9.05456 19.677 11.7049 19.677 14.9742C19.677 18.2435 17.0337 20.8938 13.773 20.8938H0V6.80474C0 3.53543 2.64333 0.885124 5.90405 0.885124Z', 'fill': 'url(#paint0_linear_19703_15608)'}
  enable?         True
  visible?        False
  editable?       False
  label_text:     
  HTML:           <path fill-rule="evenodd" clip-rule="evenodd" d="M5.90405 0.885124C9.16477 0.885124 11.8081 3.53543 11.8081 6.80474V9.05
------------------------------------------------------------
Element 361:
  page_name:      dashboard
  tag_name:       g
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'mask': 'url(#mask0_19703_15608)'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <g mask="url(#mask0_19703_15608)">
<g filter="url(#filter0_f_19703_15608)">
<circle cx="8.63157" cy="11.5658" r="13.3199
------------------------------------------------------------
Element 362:
  page_name:      dashboard
  tag_name:       g
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'filter': 'url(#filter0_f_19703_15608)'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <g filter="url(#filter0_f_19703_15608)">
<circle cx="8.63157" cy="11.5658" r="13.3199" fill="#4B73FF"></circle>
</g>
------------------------------------------------------------
Element 363:
  page_name:      dashboard
  tag_name:       circle
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'cx': '8.63157', 'cy': '11.5658', 'r': '13.3199', 'fill': '#4B73FF'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <circle cx="8.63157" cy="11.5658" r="13.3199" fill="#4B73FF"></circle>
------------------------------------------------------------
Element 364:
  page_name:      dashboard
  tag_name:       g
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'filter': 'url(#filter1_f_19703_15608)'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <g filter="url(#filter1_f_19703_15608)">
<ellipse cx="10.0949" cy="4.25612" rx="17.0591" ry="13.3199" fill="#FF66F4"></e
------------------------------------------------------------
Element 365:
  page_name:      dashboard
  tag_name:       ellipse
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'cx': '10.0949', 'cy': '4.25612', 'rx': '17.0591', 'ry': '13.3199', 'fill': '#FF66F4'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <ellipse cx="10.0949" cy="4.25612" rx="17.0591" ry="13.3199" fill="#FF66F4"></ellipse>
------------------------------------------------------------
Element 366:
  page_name:      dashboard
  tag_name:       g
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'filter': 'url(#filter2_f_19703_15608)'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <g filter="url(#filter2_f_19703_15608)">
<ellipse cx="12.8775" cy="1.74957" rx="13.3199" ry="11.6977" fill="#FF0105"></e
------------------------------------------------------------
Element 367:
  page_name:      dashboard
  tag_name:       ellipse
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'cx': '12.8775', 'cy': '1.74957', 'rx': '13.3199', 'ry': '11.6977', 'fill': '#FF0105'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <ellipse cx="12.8775" cy="1.74957" rx="13.3199" ry="11.6977" fill="#FF0105"></ellipse>
------------------------------------------------------------
Element 368:
  page_name:      dashboard
  tag_name:       g
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'filter': 'url(#filter3_f_19703_15608)'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <g filter="url(#filter3_f_19703_15608)">
<circle cx="10.3319" cy="4.25254" r="8.01052" fill="#FE7B02"></circle>
</g>
------------------------------------------------------------
Element 369:
  page_name:      dashboard
  tag_name:       circle
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'cx': '10.3319', 'cy': '4.25254', 'r': '8.01052', 'fill': '#FE7B02'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <circle cx="10.3319" cy="4.25254" r="8.01052" fill="#FE7B02"></circle>
------------------------------------------------------------
Element 370:
  page_name:      dashboard
  tag_name:       defs
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {}
  enable?         True
  visible?        False
  editable?       False
  label_text:     
  HTML:           <defs>
<filter id="filter0_f_19703_15608" x="-10.6577" y="-7.72354" width="38.5786" height="38.5786" filterUnits="userSp
------------------------------------------------------------
Element 371:
  page_name:      dashboard
  tag_name:       filter
  text:           
  id:             filter0_f_19703_15608
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'id': 'filter0_f_19703_15608', 'x': '-10.6577', 'y': '-7.72354', 'width': '38.5786', 'height': '38.5786', 'filterUnits': 'userSpaceOnUse', 'color-interpolation-filters': 'sRGB'}
  enable?         True
  visible?        False
  editable?       False
  label_text:     
  HTML:           <filter id="filter0_f_19703_15608" x="-10.6577" y="-7.72354" width="38.5786" height="38.5786" filterUnits="userSpaceOnUs
------------------------------------------------------------
Element 372:
  page_name:      dashboard
  tag_name:       feflood
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'flood-opacity': '0', 'result': 'BackgroundImageFix'}
  enable?         True
  visible?        False
  editable?       False
  label_text:     
  HTML:           <feFlood flood-opacity="0" result="BackgroundImageFix"></feFlood>
------------------------------------------------------------
Element 373:
  page_name:      dashboard
  tag_name:       feblend
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'mode': 'normal', 'in': 'SourceGraphic', 'in2': 'BackgroundImageFix', 'result': 'shape'}
  enable?         True
  visible?        False
  editable?       False
  label_text:     
  HTML:           <feBlend mode="normal" in="SourceGraphic" in2="BackgroundImageFix" result="shape"></feBlend>
------------------------------------------------------------
Element 374:
  page_name:      dashboard
  tag_name:       fegaussianblur
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'stdDeviation': '2.98472', 'result': 'effect1_foregroundBlur_19703_15608'}
  enable?         True
  visible?        False
  editable?       False
  label_text:     
  HTML:           <feGaussianBlur stdDeviation="2.98472" result="effect1_foregroundBlur_19703_15608"></feGaussianBlur>
------------------------------------------------------------
Element 375:
  page_name:      dashboard
  tag_name:       filter
  text:           
  id:             filter1_f_19703_15608
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'id': 'filter1_f_19703_15608', 'x': '-12.9337', 'y': '-15.0332', 'width': '46.057', 'height': '38.5786', 'filterUnits': 'userSpaceOnUse', 'color-interpolation-filters': 'sRGB'}
  enable?         True
  visible?        False
  editable?       False
  label_text:     
  HTML:           <filter id="filter1_f_19703_15608" x="-12.9337" y="-15.0332" width="46.057" height="38.5786" filterUnits="userSpaceOnUse
------------------------------------------------------------
Element 376:
  page_name:      dashboard
  tag_name:       feflood
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'flood-opacity': '0', 'result': 'BackgroundImageFix'}
  enable?         True
  visible?        False
  editable?       False
  label_text:     
  HTML:           <feFlood flood-opacity="0" result="BackgroundImageFix"></feFlood>
------------------------------------------------------------
Element 377:
  page_name:      dashboard
  tag_name:       feblend
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'mode': 'normal', 'in': 'SourceGraphic', 'in2': 'BackgroundImageFix', 'result': 'shape'}
  enable?         True
  visible?        False
  editable?       False
  label_text:     
  HTML:           <feBlend mode="normal" in="SourceGraphic" in2="BackgroundImageFix" result="shape"></feBlend>
------------------------------------------------------------
Element 378:
  page_name:      dashboard
  tag_name:       fegaussianblur
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'stdDeviation': '2.98472', 'result': 'effect1_foregroundBlur_19703_15608'}
  enable?         True
  visible?        False
  editable?       False
  label_text:     
  HTML:           <feGaussianBlur stdDeviation="2.98472" result="effect1_foregroundBlur_19703_15608"></feGaussianBlur>
------------------------------------------------------------
Element 379:
  page_name:      dashboard
  tag_name:       filter
  text:           
  id:             filter2_f_19703_15608
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'id': 'filter2_f_19703_15608', 'x': '-6.41182', 'y': '-15.9176', 'width': '38.5786', 'height': '35.3342', 'filterUnits': 'userSpaceOnUse', 'color-interpolation-filters': 'sRGB'}
  enable?         True
  visible?        False
  editable?       False
  label_text:     
  HTML:           <filter id="filter2_f_19703_15608" x="-6.41182" y="-15.9176" width="38.5786" height="35.3342" filterUnits="userSpaceOnUs
------------------------------------------------------------
Element 380:
  page_name:      dashboard
  tag_name:       feflood
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'flood-opacity': '0', 'result': 'BackgroundImageFix'}
  enable?         True
  visible?        False
  editable?       False
  label_text:     
  HTML:           <feFlood flood-opacity="0" result="BackgroundImageFix"></feFlood>
------------------------------------------------------------
Element 381:
  page_name:      dashboard
  tag_name:       feblend
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'mode': 'normal', 'in': 'SourceGraphic', 'in2': 'BackgroundImageFix', 'result': 'shape'}
  enable?         True
  visible?        False
  editable?       False
  label_text:     
  HTML:           <feBlend mode="normal" in="SourceGraphic" in2="BackgroundImageFix" result="shape"></feBlend>
------------------------------------------------------------
Element 382:
  page_name:      dashboard
  tag_name:       fegaussianblur
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'stdDeviation': '2.98472', 'result': 'effect1_foregroundBlur_19703_15608'}
  enable?         True
  visible?        False
  editable?       False
  label_text:     
  HTML:           <feGaussianBlur stdDeviation="2.98472" result="effect1_foregroundBlur_19703_15608"></feGaussianBlur>
------------------------------------------------------------
Element 383:
  page_name:      dashboard
  tag_name:       filter
  text:           
  id:             filter3_f_19703_15608
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'id': 'filter3_f_19703_15608', 'x': '-3.64803', 'y': '-9.72742', 'width': '27.9599', 'height': '27.9599', 'filterUnits': 'userSpaceOnUse', 'color-interpolation-filters': 'sRGB'}
  enable?         True
  visible?        False
  editable?       False
  label_text:     
  HTML:           <filter id="filter3_f_19703_15608" x="-3.64803" y="-9.72742" width="27.9599" height="27.9599" filterUnits="userSpaceOnUs
------------------------------------------------------------
Element 384:
  page_name:      dashboard
  tag_name:       feflood
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'flood-opacity': '0', 'result': 'BackgroundImageFix'}
  enable?         True
  visible?        False
  editable?       False
  label_text:     
  HTML:           <feFlood flood-opacity="0" result="BackgroundImageFix"></feFlood>
------------------------------------------------------------
Element 385:
  page_name:      dashboard
  tag_name:       feblend
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'mode': 'normal', 'in': 'SourceGraphic', 'in2': 'BackgroundImageFix', 'result': 'shape'}
  enable?         True
  visible?        False
  editable?       False
  label_text:     
  HTML:           <feBlend mode="normal" in="SourceGraphic" in2="BackgroundImageFix" result="shape"></feBlend>
------------------------------------------------------------
Element 386:
  page_name:      dashboard
  tag_name:       fegaussianblur
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'stdDeviation': '2.98472', 'result': 'effect1_foregroundBlur_19703_15608'}
  enable?         True
  visible?        False
  editable?       False
  label_text:     
  HTML:           <feGaussianBlur stdDeviation="2.98472" result="effect1_foregroundBlur_19703_15608"></feGaussianBlur>
------------------------------------------------------------
Element 387:
  page_name:      dashboard
  tag_name:       lineargradient
  text:           
  id:             paint0_linear_19703_15608
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'id': 'paint0_linear_19703_15608', 'x1': '6.62168', 'y1': '4.40129', 'x2': '12.6165', 'y2': '20.8863', 'gradientUnits': 'userSpaceOnUse'}
  enable?         True
  visible?        False
  editable?       False
  label_text:     
  HTML:           <linearGradient id="paint0_linear_19703_15608" x1="6.62168" y1="4.40129" x2="12.6165" y2="20.8863" gradientUnits="userSp
------------------------------------------------------------
Element 388:
  page_name:      dashboard
  tag_name:       stop
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'offset': '0.025', 'stop-color': '#FF8E63'}
  enable?         True
  visible?        False
  editable?       False
  label_text:     
  HTML:           <stop offset="0.025" stop-color="#FF8E63"></stop>
------------------------------------------------------------
Element 389:
  page_name:      dashboard
  tag_name:       stop
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'offset': '0.56', 'stop-color': '#FF7EB0'}
  enable?         True
  visible?        False
  editable?       False
  label_text:     
  HTML:           <stop offset="0.56" stop-color="#FF7EB0"></stop>
------------------------------------------------------------
Element 390:
  page_name:      dashboard
  tag_name:       stop
  text:           
  id:             
  class:          {}
  value:          
  placeholder:    
  type:           
  attributes:     {'offset': '0.95', 'stop-color': '#4B73FF'}
  enable?         True
  visible?        False
  editable?       False
  label_text:     
  HTML:           <stop offset="0.95" stop-color="#4B73FF"></stop>
------------------------------------------------------------
Element 391:
  page_name:      dashboard
  tag_name:       button
  text:           ×
  id:             lovable-badge-close
  class:          
  value:          
  placeholder:    
  type:           submit
  attributes:     {'id': 'lovable-badge-close', 'style': 'position: absolute; top: -2px; right: 5px; cursor: pointer; font-size: 14px; color: #A1A1AA;'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     ×
  HTML:           <button id="lovable-badge-close" style="position: absolute; top: -2px; right: 5px; cursor: pointer; font-size: 14px; col
------------------------------------------------------------
Element 392:
  page_name:      dashboard
  tag_name:       script
  text:           // Don't show the lovable-badge if the page is in an iframe or if it's being rendered by puppeteer (screenshot service)
	if (window.self !== window.top || navigator.userAgent.includes('puppeteer')) {
		// the page is in an iframe
		var badge = document.getElementById('lovable-badge');
		if (badge) {
			badge.style.display = 'none';
		}
	}

	// Add click event listener to close button
	var closeButton = document.getElementById('lovable-badge-close');
	if (closeButton) {
		closeButton.addEventListener('click', function(event) {
			event.preventDefault();
			event.stopPropagation();
			var badge = document.getElementById('lovable-badge');
			if (badge) {
				badge.style.display = 'none';
			}
		});
	}
  id:             
  class:          
  value:          
  placeholder:    
  type:           
  attributes:     {}
  enable?         True
  visible?        False
  editable?       False
  label_text:     
  HTML:           <script>
	// Don't show the lovable-badge if the page is in an iframe or if it's being rendered by puppeteer (screenshot
------------------------------------------------------------
Element 393:
  page_name:      dashboard
  tag_name:       span
  text:           0
  id:             recharts_measurement_span
  class:          
  value:          
  placeholder:    
  type:           
  attributes:     {'id': 'recharts_measurement_span', 'aria-hidden': 'true', 'style': 'position: absolute; top: -20000px; left: 0px; padding: 0px; margin: 0px; border: none; white-space: pre; font-size: 16px; letter-spacing: normal;'}
  enable?         True
  visible?        True
  editable?       False
  label_text:     
  HTML:           <span id="recharts_measurement_span" aria-hidden="true" style="position: absolute; top: -20000px; left: 0px; padding: 0p
------------------------------------------------------------


# === FILE: generated_runs\src\pages\base_page.py ===
from services.page_enricher import enrich_page
from generated_runs.src.lib.smart_ai import patch_page_with_smartai
from services.chroma_service import get_chroma_collection

class BasePage:
    enriched_pages = set()
    shared_page = None  # Class-level page sharing

    def __init__(self, page=None, page_name="base", url=None):
        if page is not None:
            BasePage.shared_page = page
        elif BasePage.shared_page is None:
            raise ValueError("Playwright page instance must be provided at least once.")

        self.page = BasePage.shared_page
        self.page_name = page_name
        self.url = url

    def _fetch_metadata_from_chroma(self, page_name):
        collection = get_chroma_collection()
        all_metadata = collection.get(where={"page_name": page_name}).get("metadatas", [])
        return all_metadata

    async def goto(self, url=None):
        target_url = url or self.url
        if not target_url:
            raise ValueError(f"URL not set for {self.page_name}")
        await self.page.goto(target_url)

    async def enrich_once(self, force=False):
        if force or self.page_name not in BasePage.enriched_pages:
            await enrich_page(self.page, self.page_name)
            BasePage.enriched_pages.add(self.page_name)


# === FILE: generated_runs\src\pages\customers_page.py ===
from generated_runs.src.pages.base_page import BasePage
from services.page_enricher import enrich_page
from generated_runs.src.lib.smart_ai import patch_page_with_smartai
from utils.enrichment_status import is_enriched

class CustomersPage(BasePage):
    def __init__(self, page=None, page_name="customers"):
        super().__init__(page, page_name)
        self._enriched = False
        metadata = self._fetch_metadata_from_chroma(page_name)
        patch_page_with_smartai(self.page, metadata)

    async def _enrich_if_needed(self, force=False):
        if force or not is_enriched(self.page_name):
            await enrich_page(self.page, self.page_name)
            self._enriched = True


    async def enter_search_customers_loans_transactions(self, value):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_search_customers,_loans,_transactions..._textbox_search_be73039f')
        await locator.fill(value)


    async def click_dashboard(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_dashboard_button_navigation_fb22376c')
        await locator.click()


    async def click_customers(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_customers_button_navigation_62cd2bf8')
        await locator.click()


    async def click_loans(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_loans_button_navigation_f083cd47')
        await locator.click()


    async def click_transactions(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_transactions_button_navigation_bb833203')
        await locator.click()


    async def click_tasks(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_tasks_button_navigation_63e52ff9')
        await locator.click()


    async def click_reports(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_reports_button_navigation_1dc35b9f')
        await locator.click()


    async def click_analytics(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_analytics_button_navigation_8227d101')
        await locator.click()


    async def click_settings(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_settings_button_navigation_9de99b8a')
        await locator.click()


    async def verify_john_doe_visible(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_john_doe_label_user_info_64be4d99')
        assert await locator.is_visible()


    async def verify_customers_visible(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_customers_label_section_title_2ec8510a')
        assert await locator.is_visible()


    async def verify_manage_your_customer_relationships_and_accounts_visible(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_manage_your_customer_relationships_and_accounts_label_section_info_f20c0595')
        assert await locator.is_visible()


    async def enter_search_customers(self, value):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_search_customers..._textbox_search_85d3ce1f')
        await locator.fill(value)


    async def click_export(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_export_button_export_ec306f18')
        await locator.click()


    async def click_new_customer(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_+_new_customer_button_add_customer_e84a62b3')
        await locator.click()


    async def click_filters(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_filters_button_filter_4c0a3d63')
        await locator.click()


    async def verify_customer_list_visible(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_customer_list_label_section_title_ad47eb6a')
        assert await locator.is_visible()


    async def verify_3_customers_found_visible(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_3_customers_found_label_section_info_f58e240e')
        assert await locator.is_visible()


    async def verify_customer_visible(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_customer_label_column_header_cd74c3eb')
        assert await locator.is_visible()


    async def verify_account_type_visible(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_account_type_label_column_header_a712d19c')
        assert await locator.is_visible()


    async def verify_balance_visible(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_balance_label_column_header_d6648fd2')
        assert await locator.is_visible()


    async def verify_status_visible(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_status_label_column_header_57a06b20')
        assert await locator.is_visible()


    async def verify_join_date_visible(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_join_date_label_column_header_cb167d9a')
        assert await locator.is_visible()


    async def verify_actions_visible(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_actions_label_column_header_177ddb69')
        assert await locator.is_visible()


    async def verify_sarah_johnson_visible(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_sarah_johnson_label_customer_name_91134cc9')
        assert await locator.is_visible()


    async def verify_sarah_johnson_email_com_visible(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_sarah.johnson@email.com_label_customer_email_ea79968a')
        assert await locator.is_visible()


    async def verify_premium_visible(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_premium_label_account_type_c1ae4279')
        assert await locator.is_visible()


    async def verify_1_45_000_visible(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_$1,45,000_label_balance_dc74e6a8')
        assert await locator.is_visible()


    async def verify_active_visible(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_active_label_status_5fc1bbb1')
        assert await locator.is_visible()


    async def verify_2023_01_15_visible(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_2023-01-15_label_join_date_13b4a3e0')
        assert await locator.is_visible()


    async def click_view_action(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_button_view_action_cc60ce91')
        await locator.click()


    async def click_edit_action(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_button_edit_action_d3d0df61')
        await locator.click()


    async def verify_michael_chen_visible(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_michael_chen_label_customer_name_8dbd8345')
        assert await locator.is_visible()


    async def verify_michael_chen_email_com_visible(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_michael.chen@email.com_label_customer_email_8f50f16b')
        assert await locator.is_visible()


    async def verify_standard_visible(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_standard_label_account_type_ef9be216')
        assert await locator.is_visible()


    async def verify_52_000_visible(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_$52,000_label_balance_b6e2bd67')
        assert await locator.is_visible()


    async def verify_2023_03_22_visible(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_2023-03-22_label_join_date_363240e3')
        assert await locator.is_visible()


    async def verify_emma_davis_visible(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_emma_davis_label_customer_name_671b9ccd')
        assert await locator.is_visible()


    async def verify_emma_davis_email_com_visible(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_emma.davis@email.com_label_customer_email_1680f20b')
        assert await locator.is_visible()


    async def verify_89_000_visible(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_$89,000_label_balance_f3422319')
        assert await locator.is_visible()


    async def verify_2022_11_08_visible(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_2022-11-08_label_join_date_bcd7c000')
        assert await locator.is_visible()


    async def verify_edit_with_visible(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_edit_with_label_edit_info_0a420ebf')
        assert await locator.is_visible()


    async def click_lovable(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_lovable_button_edit_tool_efcb8fa0')
        await locator.click()


    async def verify_add_new_customer_visible(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_add_new_customer_label_form_title_2b3b0780')
        assert await locator.is_visible()


    async def verify_enter_the_customer_details_to_create_a_new_account_visible(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_enter_the_customer_details_to_create_a_new_account._label_form_instruction_4e368c65')
        assert await locator.is_visible()


    async def verify_full_name_visible(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_full_name_label_full_name_label_7fa7eb35')
        assert await locator.is_visible()


    async def enter_full_name_input(self, value):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_textbox_full_name_input_b5555c13')
        await locator.fill(value)


    async def verify_email_visible(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_email_label_email_label_1e22d7f0')
        assert await locator.is_visible()


    async def enter_email_input(self, value):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_textbox_email_input_b7f01675')
        await locator.fill(value)


    async def verify_phone_number_visible(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_phone_number_label_phone_number_label_03e465fd')
        assert await locator.is_visible()


    async def enter_phone_number_input(self, value):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_textbox_phone_number_input_bb72a72b')
        await locator.fill(value)


    async def select_select_account_type(self, value):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_select_account_type_select_account_type_select_739bf8ef')
        await locator.select_option(value)


    async def verify_address_visible(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_address_label_address_label_bfa99020')
        assert await locator.is_visible()


    async def enter_address_input(self, value):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_textbox_address_input_0da1bba0')
        await locator.fill(value)


    async def verify_occupation_visible(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_occupation_label_occupation_label_78041ebe')
        assert await locator.is_visible()


    async def enter_occupation_input(self, value):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_textbox_occupation_input_7c88216e')
        await locator.fill(value)


    async def verify_annual_income_visible(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_annual_income_label_annual_income_label_41327b0b')
        assert await locator.is_visible()


    async def enter_annual_income_input(self, value):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_textbox_annual_income_input_7b960691')
        await locator.fill(value)


    async def verify_initial_deposit_visible(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_initial_deposit_label_initial_deposit_label_a98dd99a')
        assert await locator.is_visible()


    async def enter_initial_deposit_input(self, value):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_textbox_initial_deposit_input_842f44e3')
        await locator.fill(value)


    async def click_cancel(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_cancel_button_cancel_71a3913d')
        await locator.click()


    async def click_add_customer(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('customers_add_customer_button_submit_bce56d38')
        await locator.click()


# === FILE: generated_runs\src\pages\dashboard_page.py ===
from generated_runs.src.pages.base_page import BasePage
from services.page_enricher import enrich_page
from generated_runs.src.lib.smart_ai import patch_page_with_smartai
from utils.enrichment_status import is_enriched

class DashboardPage(BasePage):
    def __init__(self, page=None, page_name="dashboard"):
        super().__init__(page, page_name)
        self._enriched = False
        metadata = self._fetch_metadata_from_chroma(page_name)
        patch_page_with_smartai(self.page, metadata)

    async def _enrich_if_needed(self, force=False):
        if force or not is_enriched(self.page_name):
            await enrich_page(self.page, self.page_name)
            self._enriched = True


    async def click_navigation(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('dashboard_button_navigation_34c032c8')
        await locator.click()


    async def enter_search_customers_loans_transactions(self, value):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('dashboard_search_customers,_loans,_transactions..._textbox_search_3310a968')
        await locator.fill(value)


    async def click_dashboard(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('dashboard_dashboard_button_navigation_83914516')
        await locator.click()


    async def click_customers(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('dashboard_customers_button_navigation_bb4303b6')
        await locator.click()


    async def click_loans(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('dashboard_loans_button_navigation_42436e2a')
        await locator.click()


    async def click_transactions(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('dashboard_transactions_button_navigation_f0479a72')
        await locator.click()


    async def click_tasks(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('dashboard_tasks_button_navigation_cde2a4d6')
        await locator.click()


    async def click_reports(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('dashboard_reports_button_navigation_578fb659')
        await locator.click()


    async def click_analytics(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('dashboard_analytics_button_navigation_49884ab5')
        await locator.click()


    async def click_settings(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('dashboard_settings_button_navigation_7a36fd5d')
        await locator.click()


    async def verify_dashboard_visible(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('dashboard_dashboard_label_page_title_a353b4f0')
        assert await locator.is_visible()


    async def verify_welcome_back_here_s_your_banking_overview_visible(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('dashboard_welcome_back!_heres_your_banking_overview._label_greeting_bd321dde')
        assert await locator.is_visible()


    async def verify_total_customers_visible(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('dashboard_total_customers_label_metric_title_9728f1cf')
        assert await locator.is_visible()


    async def verify_2_847_visible(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('dashboard_2,847_label_metric_value_fdec317c')
        assert await locator.is_visible()


    async def verify_active_loans_visible(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('dashboard_active_loans_label_metric_title_7b8dadc2')
        assert await locator.is_visible()


    async def verify_45_2m_visible(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('dashboard_$45.2m_label_metric_value_4a2ef93a')
        assert await locator.is_visible()


    async def verify_monthly_transactions_visible(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('dashboard_monthly_transactions_label_metric_title_12ed8182')
        assert await locator.is_visible()


    async def verify_18_394_visible(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('dashboard_18,394_label_metric_value_b6b442dd')
        assert await locator.is_visible()


    async def verify_revenue_growth_visible(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('dashboard_revenue_growth_label_metric_title_d1a487c9')
        assert await locator.is_visible()


    async def verify_4_visible(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('dashboard_4%_label_metric_value_316201d4')
        assert await locator.is_visible()


    async def click_export_report(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('dashboard_export_report_button_export_ed26f6d4')
        await locator.click()


    async def verify_loan_portfolio_trend_visible(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('dashboard_loan_portfolio_trend_label_section_title_32cf7d0c')
        assert await locator.is_visible()


    async def verify_monthly_loan_disbursements_over_the_last_6_months_visible(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('dashboard_monthly_loan_disbursements_over_the_last_6_months_label_section_info_790102ea')
        assert await locator.is_visible()


    async def verify_customer_distribution_visible(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('dashboard_customer_distribution_label_section_title_4bc10c83')
        assert await locator.is_visible()


    async def verify_customer_segments_by_account_type_visible(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('dashboard_customer_segments_by_account_type_label_section_info_e21a781f')
        assert await locator.is_visible()


    async def verify_premium_35_visible(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('dashboard_premium_35%_label_chart_info_e6423d22')
        assert await locator.is_visible()


    async def verify_standard_45_visible(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('dashboard_standard_45%_label_chart_info_d70c74e7')
        assert await locator.is_visible()


    async def verify_basic_20_visible(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('dashboard_basic_20%_label_chart_info_7bda856f')
        assert await locator.is_visible()


    async def verify_recent_activities_visible(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('dashboard_recent_activities_label_section_title_c5dd6139')
        assert await locator.is_visible()


    async def verify_latest_customer_interactions_and_transactions_visible(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('dashboard_latest_customer_interactions_and_transactions_label_section_info_5c741538')
        assert await locator.is_visible()


    async def verify_sarah_johnson_visible(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('dashboard_sarah_johnson_label_activity_user_309b9d18')
        assert await locator.is_visible()


    async def verify_loan_application_approved_visible(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('dashboard_loan_application_approved_label_activity_info_969d6763')
        assert await locator.is_visible()


    async def verify_michael_chen_visible(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('dashboard_michael_chen_label_activity_user_f041a3aa')
        assert await locator.is_visible()


    async def verify_250_000_visible(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('dashboard_$250,000_label_transaction_amount_14fd1f5f')
        assert await locator.is_visible()


    async def verify_2_hours_ago_visible(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('dashboard_2_hours_ago_label_transaction_time_a74efe28')
        assert await locator.is_visible()


    async def verify_edit_with_visible(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('dashboard_edit_with_label_edit_option_88c64fc9')
        assert await locator.is_visible()


    async def click_lovable(self):
        await self._enrich_if_needed()
        locator = await self.page.smartAI('dashboard_lovable_button_edit_tool_2de51406')
        await locator.click()


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
from generated_runs.src.pages.base_page import BasePage

from generated_runs.src.pages.customers_page import CustomersPage

from generated_runs.src.pages.dashboard_page import DashboardPage

import pytest
@pytest.mark.asyncio
async def test_add_customer(page):
    dashboard_page = DashboardPage(page, "dashboard")
    customers_page = CustomersPage(page, "customers")

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
    await customers_page.verify_john_doe_visible()


# === FILE: generated_runs\src\tests\ui_scripts_1.py ===
import asyncio
from playwright.async_api import async_playwright
from generated_runs.src.pages.base_page import BasePage
from generated_runs.src.pages.base_page import BasePage
from generated_runs.src.pages.customers_page import CustomersPage
from generated_runs.src.pages.dashboard_page import DashboardPage

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        base_page = BasePage(
            page, "base", url='https://preview--bank-buddy-crm-react.lovable.app/')
        await base_page.goto("https://preview--bank-buddy-crm-react.lovable.app/")

        # dashboard_page = DashboardPage(page, "dashboard")
        # customers_page = CustomersPage(page, "customers")
        dashboard_page = DashboardPage(page, 'dashboard')
        await dashboard_page.click_customers()
        customers_page = CustomersPage(page, 'customers')
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
        await customers_page.verify_john_doe_visible()


if __name__ == "__main__":
    asyncio.run(main())


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
import traceback

# 🔧 Embedding setup
embedding_fn = SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2")
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
    try:
        return np.sqrt((b1['x'] - b2['x'])**2 + (b1['y'] - b2['y'])**2)
    except Exception as e:
        print(f"[❌] Error computing bbox_distance: {e} | b1: {b1}, b2: {b2}")
        return float('inf')

# ✅ Text similarity


def text_similarity(t1: str, t2: str) -> float:
    try:
        vecs = text_model.encode([t1, t2], show_progress_bar=False)
        return float(cosine_similarity([vecs[0]], [vecs[1]])[0][0])
    except Exception as e:
        print(f"[❌] Error in text_similarity: {e} | t1: {t1} | t2: {t2}")
        traceback.print_exc()
        return 0.0

# ✅ Extract DOM metadata from page


async def extract_dom_metadata(page: Page, page_name: str) -> list:
    try:
        elements_data = await page.evaluate("""
        (pageName) => {
            const nodes = Array.from(document.querySelectorAll('body *:not(#ocrModal *):not(#ocrModal)'));
            return nodes.map((e, i) => {
                let bbox = {x: '', y: '', width: '', height: ''};
                try {
                    const b = e.getBoundingClientRect();
                    bbox = {x: b.x, y: b.y, width: b.width, height: b.height};
                } catch {}
                const attrs = {};
                for (const attr of e.attributes) {
                    attrs[attr.name] = attr.value;
                }
                let label = '';
                if (e.id) {
                    const labelElem = document.querySelector(`label[for="${e.id}"]`);
                    if (labelElem) label = labelElem.innerText.trim();
                }
                if (!label && e.getAttribute('aria-label')) label = e.getAttribute('aria-label');
                if (!label && e.placeholder) label = e.placeholder;
                if (!label && e.tagName.toLowerCase() === "button") label = e.textContent.trim();
                if (!label && e.getAttribute('data-lov-name')) label = e.getAttribute('data-lov-name');
                let editable = false;
                const tn = e.tagName.toLowerCase();
                if (["input", "textarea", "select"].includes(tn)) {
                    editable = !e.readOnly && !e.disabled;
                } else if (e.getAttribute('contenteditable') === "true") {
                    editable = true;
                }
                let visible = !!(e.offsetWidth || e.offsetHeight || e.getClientRects().length);
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
    except Exception as e:
        print(f"[❌] Failed to extract DOM metadata: {e}")
        traceback.print_exc()
        return []

    print(f"[DEBUG] Got {len(elements_data)} locator from dom except ocrModal")

    try:
        from pathlib import Path
        debug_metadata_dir = Path("generated_runs") / \
            "src" / "ocr-dom-metadata"
        debug_metadata_dir.mkdir(parents=True, exist_ok=True)
        out_file = debug_metadata_dir / f"dom_elements_{page_name}.txt"
        output_lines = ["All DOM elements"]
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
        with open(out_file, "w", encoding="utf-8") as f:
            f.write("\n".join(output_lines))
        print(f"[INFO] DOM extracted element data saved to {out_file}")
        print("[DEBUG] DOM DATA Length: ", len(elements_data))
    except Exception as e:
        print(f"[❌] Failed to write DOM debug info: {e}")
        traceback.print_exc()

    return elements_data


def clean_metadata(d):
    # Recursively clean all dict/list/set values in the dict d
    for k, v in list(d.items()):
        if isinstance(v, (dict, list, set)):
            d[k] = json.dumps(v)
        elif not isinstance(v, (str, int, float, bool)) and v is not None:
            d[k] = str(v)
    return d


def match_and_update(ocr_data, dom_data, collection, text_thresh=0.5, bbox_thresh=300):
    global LAST_MATCHED_RESULTS
    matched_records = []

    # Filter for dicts only
    dict_ocr_data = [r for r in ocr_data if isinstance(r, dict)]
    bad_ocr_data = [r for r in ocr_data if not isinstance(r, dict)]
    if bad_ocr_data:
        print(
            f"[WARNING] {len(bad_ocr_data)} OCR records were not dicts and will be skipped. Example: {bad_ocr_data[:1]}")

    print(
        f"[DEBUG] Matching {len(dict_ocr_data)} OCRs with {len(dom_data)} DOMs")
    dom_texts = []
    dom_candidates = []
    for dom in dom_data:
        if not isinstance(dom, dict):
            print(f"[WARNING] Skipping DOM record not a dict: {dom}")
            continue
        dom_text = dom.get("label_text", "") or dom.get(
            "text", "") or dom.get("placeholder", "") or dom.get("value", "")
        dom_texts.append(dom_text.lower())
        dom_candidates.append(dom)
    if dom_texts:
        try:
            dom_embeddings = text_model.encode(
                dom_texts, show_progress_bar=False)
        except Exception as e:
            print(f"[❌] Failed to embed DOM texts: {e}")
            traceback.print_exc()
            dom_embeddings = []
    else:
        dom_embeddings = []

    for ocr in dict_ocr_data:
        try:
            # ---- If label_text exists: optimized vectorized similarity search ----
            if ocr.get("label_text"):
                ocr_label = ocr["label_text"].lower()
                try:
                    ocr_embedding = text_model.encode([ocr_label])[0]
                except Exception as e:
                    print(f"[❌] Failed to embed OCR label: {ocr_label} | {e}")
                    traceback.print_exc()
                    continue
                if len(dom_embeddings) > 0:
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
                        updated["label_text"] = (
                            (best_match.get("label_text") or "").strip() or
                            (best_match.get("text") or "").strip() or
                            (best_match.get("placeholder") or "").strip() or
                            (best_match.get("value") or "").strip() or
                            ""
                        )
                        updated = clean_metadata(updated)
                        try:
                            collection.upsert(
                                ids=[updated.get("element_id")],
                                documents=[updated["label_text"]],
                                metadatas=[updated],
                            )
                        except Exception as e:
                            print(
                                f"[❌] Failed to upsert updated OCR record: {updated} | {e}")
                            traceback.print_exc()
                        matched_records.append(updated)

            # ---- If label_text not exists: fallback using ocr_type + intent (no change) ----
            elif not ocr.get("label_text"):
                ocr_type = ocr.get("ocr_type", "").lower()
                intent = ocr.get("intent", "").lower()
                best_match = None
                best_score = 0.0
                for dom in dom_candidates:
                    if not isinstance(dom, dict):
                        continue
                    dom_tag = (dom.get("tag_name") or "").lower()
                    dom_id = (dom.get("id") or "").lower()
                    dom_class = (dom.get("class") or "").lower()
                    dom_label = (dom.get("label_text") or "").strip()
                    if dom_label:
                        continue
                    if ocr_type == "textbox" and dom_tag in ("input", "textarea", "text"):
                        score = 0
                        if intent and (intent in dom_id or intent in dom_class):
                            score = 1.0
                        elif intent.split('_')[0] in dom_id or intent.split('_')[0] in dom_class:
                            score = 0.8
                        if score > best_score:
                            best_score = score
                            best_match = dom
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
                    updated["label_text"] = (
                        (best_match.get("label_text") or "").strip() or
                        (best_match.get("text") or "").strip() or
                        (best_match.get("placeholder") or "").strip() or
                        (best_match.get("value") or "").strip() or
                        ""
                    )
                    updated = clean_metadata(updated)
                    try:
                        collection.upsert(
                            ids=[updated.get("element_id")],
                            documents=[updated["label_text"]],
                            metadatas=[updated],
                        )
                    except Exception as e:
                        print(
                            f"[❌] Failed to upsert updated OCR record (intent fallback): {updated} | {e}")
                        traceback.print_exc()
                    matched_records.append(updated)
        except Exception as e:
            print(f"[❌] Error in matching OCR record: {ocr}\nException: {e}")
            traceback.print_exc()

    LAST_MATCHED_RESULTS = matched_records
    print(f"[✅] Matched {len(matched_records)} elements.")
    return matched_records



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


def get_chroma_collection():
    return collection


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


async def enrich_page(page, page_name):
    if is_enriched(page_name):
        return  # Already enriched

    # --- DOM Extraction ---
    dom_data = await extract_dom_metadata(page, page_name)

    # --- OCR Data Fetch (fetch valid dict records only) ---
    embedding_fn = SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2")
    client = PersistentClient(path="./data/chroma_db")
    collection = client.get_or_create_collection(
        name="element_metadata", embedding_function=embedding_fn
    )
    ocr_data = collection.get(where={"page_name": page_name}).get("metadatas", []) 
    # ocr_data = collection.get(where={"$and": [{"page_name": page_name}]}).get("metadatas", [])

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

# SYNC 
# SMART_AI_CODE = """import json
# import numpy as np
# from sentence_transformers import SentenceTransformer, util

# class SmartAILocatorError(Exception):
#     pass

# # 🟢 Minimal wrapper to handle select_option fallback automatically
# class SmartAIWrappedLocator:
#     def __init__(self, locator, page):
#         self._locator = locator
#         self._page = page

#     def __getattr__(self, name):
#         # Delegate all other methods/attributes to Playwright's locator
#         return getattr(self._locator, name)

#     def select_option(self, value):
#         try:
#             return self._locator.select_option(value)
#         except Exception as e:
#             print(f"[SmartAI][select_option fallback] Native select_option failed: {e}")
#             try:
#                 self._page.get_by_role("combobox").click()
#                 self._page.get_by_role("option", name=value).click()
#                 print(f"[SmartAI][select_option fallback] Selected '{value}' via combobox+option fallback")
#             except Exception as e2:
#                 print(f"[SmartAI][select_option fallback] Fallback also failed: {e2}")
#                 raise

# class SmartAISelfHealing:
#     def __init__(self, metadata):
#         self.metadata = metadata
#         self.model = SentenceTransformer("all-MiniLM-L6-v2")
#         # 1️⃣ Cache embeddings for all metadata elements for fast ML matching
#         self.embeddings = [
#             self.model.encode(self._element_to_string(e), convert_to_tensor=True, show_progress_bar=False)
#             for e in self.metadata
#         ]
#         # 10️⃣ Track failed locators (element unique_name → fail count)
#         self.locator_fail_count = {}

#     # 5️⃣ Single definition; all prioritization inside
#     def _try_all_locators(self, element, page):
#         strategies = []

#         # Highest priority: try by role and label_text (esp for button, input, etc)
#         if element.get("tag_name") and element.get("label_text"):
#             role = self._map_tag_to_role(element["tag_name"])
#             if role:
#                 strategies.append((lambda: page.get_by_role(
#                     role, name=element["label_text"]), f"get_by_role({role}, name={element['label_text']})"))

#         # Try by label (best for inputs)
#         if element.get("label_text"):
#             strategies.append((lambda: page.get_by_label(
#                 element["label_text"]), f"get_by_label({element['label_text']})"))

#         # Try by visible text (good for buttons, links, etc)
#         if element.get("label_text"):
#             strategies.append((lambda: page.get_by_text(
#                 element["label_text"], exact=True), f"get_by_text({element['label_text']}, exact=True)"))

#         # Try by placeholder (for textboxes/inputs)
#         if element.get("placeholder"):
#             strategies.append((lambda: page.get_by_placeholder(
#                 element["placeholder"]), f"get_by_placeholder({element['placeholder']})"))

#         # Try by sample value (displayed value in input)
#         if element.get("sample_value"):
#             strategies.append((lambda: page.get_by_display_value(
#                 element["sample_value"]), f"get_by_display_value({element['sample_value']})"))

#         # Data attributes (testid/qa)
#         data_attrs = element.get("data_attrs", {})
#         for k, v in data_attrs.items():
#             if "test" in k.lower() or "qa" in k.lower():
#                 strategies.append((lambda: page.get_by_test_id(v),
#                                 f"get_by_test_id({v}) for {k}"))

#         # By id (exact and partial)
#         if element.get("dom_id"):
#             id_value = element["dom_id"]
#             strategies.append((lambda: page.locator(
#                 f'#{id_value}'), f"locator(#{id_value}) [ID exact]"))
#             strategies.append((lambda: page.locator(
#                 f'[id*="{id_value}"]'), f'locator([id*="{id_value}"]) [ID partial]'))

#         # By class (exact and partial)
#         if element.get("dom_class"):
#             class_value = element["dom_class"]
#             class_sel = "." + ".".join(class_value.split())
#             strategies.append((lambda: page.locator(class_sel),
#                             f"locator({class_sel}) [class exact]"))
#             strategies.append((lambda: page.locator(
#                 f'[class*="{class_value}"]'), f'locator([class*="{class_value}"]) [class partial]'))

#         # By class_list
#         if element.get("class_list"):
#             sel = "." + ".".join(element["class_list"])
#             strategies.append((lambda: page.locator(
#                 sel), f"locator({sel}) [class_list]"))

#         # Custom CSS locator
#         if element.get("locator") and element["locator"].get("type") == "css":
#             strategies.append((lambda: page.locator(
#                 element["locator"]["value"]), f"locator({element['locator']['value']}) [custom css]"))
                
#         # Now try each strategy in order
#         for func, desc in strategies:
#             try:
#                 locator = func()
#                 if locator and locator.count() > 0:
#                     print(f"[SmartAI][Return] {desc} succeeded.")
#                     self.locator_fail_count[element.get("unique_name")] = 0
#                     return locator.last
#             except Exception as e:
#                 unique_name = element.get("unique_name", "")
#                 self.locator_fail_count[unique_name] = self.locator_fail_count.get(
#                     unique_name, 0) + 1
#                 print(f"[SmartAI][Skip] {desc} failed: {e}")

#         print("[SmartAI][Return] No locator found for element.")
#         return None

#     # def _try_all_locators(self, element, page):
#     #     # Tries various locator strategies in strict priority order.
#     #     # Enhancement: Prioritize, early return, minimal .count() checks.
#     #     # Enhancement: Penalize recently failing locators.
#     #     def should_skip(unique_name):
#     #         return self.locator_fail_count.get(unique_name, 0) >= 3

#     #     strategies = []

#     #     data_attrs = element.get("data_attrs", {})
#     #     for k, v in data_attrs.items():
#     #         if "test" in k.lower() or "qa" in k.lower():
#     #             strategies.append((lambda: page.get_by_test_id(v), f"get_by_test_id({v}) for {k}"))

#     #     if element.get("tag_name"):
#     #         role = self._map_tag_to_role(element["tag_name"])
#     #         if role and element.get("label_text"):
#     #             strategies.append((lambda: page.get_by_role(role, name=element["label_text"]), f"get_by_role({role}, name={element['label_text']})"))

#     #     if element.get("label_text"):
#     #         strategies.append((lambda: page.get_by_label(element["label_text"]), f"get_by_label({element['label_text']})"))

#     #     if element.get("placeholder"):
#     #         strategies.append((lambda: page.get_by_placeholder(element["placeholder"]), f"get_by_placeholder({element['placeholder']})"))

#     #     if element.get("label_text"):
#     #         strategies.append((lambda: page.get_by_text(element["label_text"], exact=True), f"get_by_text({element['label_text']}, exact=True)"))

#     #     if element.get("sample_value"):
#     #         strategies.append((lambda: page.get_by_display_value(element["sample_value"]), f"get_by_display_value({element['sample_value']})"))

#     #     if element.get("dom_id"):
#     #         id_value = element["dom_id"]
#     #         strategies.append((lambda: page.locator(f'#{id_value}'), f"locator(#{id_value}) [ID exact]"))
#     #         strategies.append((lambda: page.locator(f'[id*="{id_value}"]'), f'locator([id*="{id_value}"]) [ID partial]'))

#     #     if element.get("dom_class"):
#     #         class_value = element["dom_class"]
#     #         class_sel = "." + ".".join(class_value.split())
#     #         strategies.append((lambda: page.locator(class_sel), f"locator({class_sel}) [class exact]"))
#     #         strategies.append((lambda: page.locator(f'[class*="{class_value}"]'), f'locator([class*="{class_value}"]) [class partial]'))

#     #     if element.get("class_list"):
#     #         sel = "." + ".".join(element["class_list"])
#     #         strategies.append((lambda: page.locator(sel), f"locator({sel}) [class_list]"))

#     #     if element.get("locator") and element["locator"].get("type") == "css":
#     #         strategies.append((lambda: page.locator(element["locator"]["value"]), f"locator({element['locator']['value']}) [custom css]"))

#     #     # Attempt strategies in order, skipping if penalized
#     #     for func, desc in strategies:
#     #         try:
#     #             locator = func()
#     #             # 2️⃣ Only check .count() once per strategy, early return
#     #             if locator and locator.count() > 0:
#     #                 print(f"[SmartAI][Return] {desc} succeeded.")
#     #                 self.locator_fail_count[element.get("unique_name")] = 0  # Reset fail count
#     #                 return locator.last
#     #         except Exception as e:
#     #             # 10️⃣ Track fail count for this unique_name
#     #             unique_name = element.get("unique_name", "")
#     #             self.locator_fail_count[unique_name] = self.locator_fail_count.get(unique_name, 0) + 1
#     #             print(f"[SmartAI][Skip] {desc} failed: {e}")

#     #     print("[SmartAI][Return] No locator found for element.")
#     #     return None

#     def find_element(self, unique_name, page):
#         # Main entry for SmartAI: tries direct lookup, then ML self-healing, then heuristics.
#         element = self._find_by_unique_name(unique_name)
#         if element:
#             locator = self._try_all_locators(element, page)
#             if locator:
#                 print(f"[SmartAI] Element '{unique_name}' found using primary metadata.")
#                 return SmartAIWrappedLocator(locator, page)  # <--- PATCHED

#             print(f"[SmartAI] Primary methods failed for '{unique_name}', trying ML self-healing...")

#         # ML-based fallback
#         element_ml, ml_score = self._ml_self_heal(unique_name)
#         if element_ml:
#             locator_ml = self._try_all_locators(element_ml, page)
#             if locator_ml:
#                 print(f"[SmartAI] Healed element via ML ({ml_score:.2f}): '{element_ml.get('unique_name')}'")
#                 return SmartAIWrappedLocator(locator_ml, page)  # <--- PATCHED

#         # 9️⃣ Intent-aware fallback: try other elements with same intent
#         target_intent = element_ml.get("intent") if element_ml else None
#         if target_intent:
#             for e in self.metadata:
#                 if e.get("intent") == target_intent and e.get("unique_name") != unique_name:
#                     locator = self._try_all_locators(e, page)
#                     if locator:
#                         print(f"[SmartAI] Healed element by intent ('{target_intent}'): '{e.get('unique_name')}'")
#                         return SmartAIWrappedLocator(locator, page)  # <--- PATCHED

#         # 11️⃣ Visual/position fallback (commented for extension)
#         # print("[SmartAI] Trying fallback by position (not implemented)...")

#         raise SmartAILocatorError(f"Element '{unique_name}' not found and cannot self-heal.")

#     def _find_by_unique_name(self, unique_name):
#         return next((e for e in self.metadata if e.get("unique_name") == unique_name), None)

#     def _map_tag_to_role(self, tag):
#         tag_role_map = {
#             'button': 'button',
#             'input': 'textbox',
#             'select': 'combobox',
#             'textarea': 'textbox',
#             'checkbox': 'checkbox'
#         }
#         return tag_role_map.get(tag.lower(), None)

#     def _ml_self_heal(self, unique_name):
#         # Returns best-matched element and score.
#         # Enhancement: Uses pre-cached embeddings for performance!
#         # 3️⃣ Uses higher threshold for accuracy.
#         query_embedding = self.model.encode(unique_name, convert_to_tensor=True, show_progress_bar=False)
#         scores = [util.cos_sim(query_embedding, emb).item() for emb in self.embeddings]
#         best_idx = int(np.argmax(scores))
#         best_score = scores[best_idx]
#         print(f"[SmartAI] ML healed best match score: {best_score:.2f}")
#         # 3️⃣ Higher threshold (was 0.3, now 0.6)
#         return (self.metadata[best_idx], best_score) if best_score > 0.6 else (None, best_score)

#     def _element_to_string(self, element):
#         # Enhancement: Fast string construction, no json.dumps.
#         fields = [
#             element.get("unique_name", ""),
#             element.get("label_text", ""),
#             element.get("intent", ""),
#             element.get("ocr_type", ""),
#             element.get("element_type", ""),
#             element.get("tag_name", ""),
#             element.get("placeholder", ""),
#             " ".join(element.get("class_list", [])) if element.get("class_list") else "",
#             # 4️⃣ Fast join for data_attrs
#             " ".join(f"{k}:{v}" for k, v in (element.get("data_attrs", {}) or {}).items()),
#             element.get("sample_value", ""),
#         ]
#         return " ".join([str(f) for f in fields if f])

# # ====== PAGE PATCH ======
# def patch_page_with_smartai(page, metadata):
#     ai_healer = SmartAISelfHealing(metadata)
#     def smartAI(unique_name):
#         return ai_healer.find_element(unique_name, page)
#     page.smartAI = smartAI
#     return page
# """

# ASYNC
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
            print(
                f"[SmartAI][select_option fallback] Native select_option failed: {e}")
            try:
                self._page.get_by_role("combobox").click()
                self._page.get_by_role("option", name=value).click()
                print(
                    f"[SmartAI][select_option fallback] Selected '{value}' via combobox+option fallback")
            except Exception as e2:
                print(
                    f"[SmartAI][select_option fallback] Fallback also failed: {e2}")
                raise


class SmartAISelfHealing:
    def __init__(self, metadata):
        self.metadata = metadata
        self.model = SentenceTransformer("all-MiniLM-L6-v2")
        # 1️⃣ Cache embeddings for all metadata elements for fast ML matching
        self.embeddings = [
            self.model.encode(self._element_to_string(
                e), convert_to_tensor=True, show_progress_bar=False)
            for e in self.metadata
        ]
        # 10️⃣ Track failed locators (element unique_name → fail count)
        self.locator_fail_count = {}

    # 5️⃣ Single definition; all prioritization inside
    async def _try_all_locators(self, element, page):
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
                if locator and await locator.count() > 0:
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

    async def find_element(self, unique_name, page):
        # Main entry for SmartAI: tries direct lookup, then ML self-healing, then heuristics.
        element = self._find_by_unique_name(unique_name)
        if element:
            locator = await self._try_all_locators(element, page)
            if locator:
                print(
                    f"[SmartAI] Element '{unique_name}' found using primary metadata.")
                return SmartAIWrappedLocator(locator, page)  # <--- PATCHED

            print(
                f"[SmartAI] Primary methods failed for '{unique_name}', trying ML self-healing...")

        # ML-based fallback
        element_ml, ml_score = self._ml_self_heal(unique_name)
        if element_ml:
            locator_ml = await self._try_all_locators(element_ml, page)
            if locator_ml:
                print(
                    f"[SmartAI] Healed element via ML ({ml_score:.2f}): '{element_ml.get('unique_name')}'")
                return SmartAIWrappedLocator(locator_ml, page)  # <--- PATCHED

        # 9️⃣ Intent-aware fallback: try other elements with same intent
        target_intent = element_ml.get("intent") if element_ml else None
        if target_intent:
            for e in self.metadata:
                if e.get("intent") == target_intent and e.get("unique_name") != unique_name:
                    locator = await self._try_all_locators(e, page)
                    if locator:
                        print(
                            f"[SmartAI] Healed element by intent ('{target_intent}'): '{e.get('unique_name')}'")
                        # <--- PATCHED
                        return SmartAIWrappedLocator(locator, page)

        # 11️⃣ Visual/position fallback (commented for extension)
        # print("[SmartAI] Trying fallback by position (not implemented)...")

        raise SmartAILocatorError(
            f"Element '{unique_name}' not found and cannot self-heal.")

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
        query_embedding = self.model.encode(
            unique_name, convert_to_tensor=True, show_progress_bar=False)
        scores = [util.cos_sim(query_embedding, emb).item()
                  for emb in self.embeddings]
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
            " ".join(element.get("class_list", [])) if element.get(
                "class_list") else "",
            # 4️⃣ Fast join for data_attrs
            " ".join(f"{k}:{v}" for k, v in (
                element.get("data_attrs", {}) or {}).items()),
            element.get("sample_value", ""),
        ]
        return " ".join([str(f) for f in fields if f])


# ====== PAGE PATCH ======
def patch_page_with_smartai(page, metadata):
    ai_healer = SmartAISelfHealing(metadata)

    async def smartAI(unique_name):
        return await ai_healer.find_element(unique_name, page)
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

