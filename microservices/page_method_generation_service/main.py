from fastapi import APIRouter, FastAPI, HTTPException
from pathlib import Path
import re
import json
import os
import chromadb
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Page Method Generation Service")

# ChromaDB setup
chroma_client = chromadb.HttpClient(host=os.getenv("CHROMA_DB_HOST", "chromadb"), port=os.getenv("CHROMA_DB_PORT", "8000"))

try:
    collection = chroma_client.get_or_create_collection(name="element_metadata")
except Exception as e:
    print(f"Error connecting to ChromaDB or getting collection: {e}")
    collection = None # Handle case where ChromaDB is not available

# Placeholder for imported functions
# These would ideally be part of this service's codebase or a shared library.

# From services.test_generation_utils
def filter_all_pages():
    if collection is None:
        return []
    records = collection.get()
    return list(set(meta.get("page_name", "unknown") for meta in records.get("metadatas", [])))

# From utils.smart_ai_utils
SMART_AI_CODE = """
import json
import time
from sentence_transformers import SentenceTransformer, util
from playwright.sync_api import sync_playwright
from pathlib import Path

# ====== SMART AI SELF-HEALER CORE ======

class SmartAILocatorError(Exception):
    pass

class SmartAISelfHealing:
    def __init__(self, metadata):
        self.metadata = metadata
        self.model = SentenceTransformer("all-MiniLM-L6-v2")

    def find_element(self, unique_name, page):
        element_ml = self._ml_self_heal(unique_name)
        if element_ml:
            locator_ml = self._try_all_locators(element_ml, page)
            if locator_ml:
                print(f"[SmartAI] Healed element found via ML matching: '{element_ml.get('unique_name')}'")
                return locator_ml

        raise SmartAILocatorError(f"Element '{unique_name}' not found and cannot self-heal.")

    def _find_by_unique_name(self, unique_name):
        for element in self.metadata:
            if element.get("unique_name") == unique_name:
                return element
        return None

    def _map_tag_to_role(self, tag):
        tag_role_map = {
            'button': 'button',
            'input': 'textbox',
            'select': 'combobox',
            'textarea': 'textbox',
            'checkbox': 'checkbox'
        }
        return tag_role_map.get(tag.lower(), None)

    def _try_all_locators(self, element, page):
        try_methods = []
        descriptions = []

        data_attrs = element.get("data_attrs", {})
        for k, v in data_attrs.items():
            if "test" in k.lower() or "qa" in k.lower():
                print(f"[SmartAI][Add] get_by_test_id({v}) for attribute {k}")
                try_methods.append(lambda: page.get_by_test_id(v))
                descriptions.append(f"get_by_test_id({v}) for attribute {k}")

        if element.get("tag_name"):
            role = self._map_tag_to_role(element["tag_name"])
            if role and element.get("label_text"):
                print(f"[SmartAI][Add] get_by_role({role}, name={element['label_text']})")
                try_methods.append(lambda: page.get_by_role(role, name=element["label_text"]))
                descriptions.append(f"get_by_role({role}, name={element['label_text']})")

        if element.get("label_text"):
            print(f"[SmartAI][Add] get_by_label({element['label_text']})")
            try_methods.append(lambda: page.get_by_label(element["label_text"]))
            descriptions.append(f"get_by_label({element['label_text']})")

        if element.get("placeholder"):
            print(f"[SmartAI][Add] get_by_placeholder({element['placeholder']})")
            try_methods.append(lambda: page.get_by_placeholder(element["placeholder"]))
            descriptions.append(f"get_by_placeholder({element['placeholder']})")

        if element.get("label_text"):
            print(f"[SmartAI][Add] get_by_text({element['label_text']}, exact=True)")
            try_methods.append(lambda: page.get_by_text(element["label_text"], exact=True))
            descriptions.append(f"get_by_text({element['label_text']}, exact=True)")

        if element.get("sample_value"):
            print(f"[SmartAI][Add] get_by_display_value({element['sample_value']})")
            try_methods.append(lambda: page.get_by_display_value(element["sample_value"]))
            descriptions.append(f"get_by_display_value({element['sample_value']})")

        if element.get("dom_id"):
            id_value = element["dom_id"]
            print(f"[SmartAI][Add] locator(#{id_value}) [ID exact]")
            try_methods.append(lambda: page.locator(f'#{id_value}'))
            descriptions.append(f"locator(#{id_value}) [ID exact]")
            print(f'[SmartAI][Add] locator([id*="{id_value}"]) [ID partial]')
            try_methods.append(lambda: page.locator(f'[id*="{id_value}"]'))
            descriptions.append(f'locator([id*="{id_value}"]) [ID partial]')

        if element.get("dom_class"):
            class_value = element["dom_class"]
            class_sel = "." + ".".join(class_value.split())
            print(f"[SmartAI][Add] locator({class_sel}) [class exact]")
            try_methods.append(lambda: page.locator(class_sel))
            descriptions.append(f"locator({class_sel}) [class exact]")
            print(f'[SmartAI][Add] locator([class*="{class_value}"]) [class partial]')
            try_methods.append(lambda: page.locator(f'[class*="{class_value}"]'))
            descriptions.append(f'locator([class*="{class_value}"]) [class partial]')

        if element.get("class_list"):
            sel = "." + ".".join(element["class_list"])
            print(f"[SmartAI][Add] locator({sel}) [class_list]")
            try_methods.append(lambda: page.locator(sel))
            descriptions.append(f"locator({sel}) [class_list]")

        if element.get("locator") and element["locator"].get("type") == "css":
            print(f"[SmartAI][Add] locator({element['locator']['value']}) [custom css]")
            try_methods.append(lambda: page.locator(element["locator"]["value"]))
            descriptions.append(f"locator({element['locator']['value']}) [custom css]")

        for idx, method in enumerate(try_methods):
            try:
                locator = method()
                if locator.count() > 0:
                    print(f"[SmartAI][Return] {descriptions[idx]} succeeded and returned a locator.")
                    return locator.first
            except Exception as e:
                print(f"[SmartAI][Skip] {descriptions[idx]} failed due to: {e}")
                continue

        print("[SmartAI][Return] No locator found for element.")
        return None

    def _ml_self_heal(self, unique_name):
        # Dummy implementation for now
        return None

    def _element_to_string(self, element):
        # Dummy implementation for now
        return ""

def ensure_smart_ai_module():
    lib_path = Path("generated_runs/src/lib")
    lib_path.mkdir(parents=True, exist_ok=True)
    (lib_path / "__init__.py").touch()
    smart_ai_file = lib_path / "smart_ai.py"
    if not smart_ai_file.exists():
        smart_ai_file.write_text(SMART_AI_CODE, encoding="utf-8")

# Orchestrator client
import httpx
ORCHESTRATOR_SERVICE_URL = os.getenv("ORCHESTRATOR_SERVICE_URL", "http://orchestrator_service:8007")

async def send_message(language, action, payload):
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{ORCHESTRATOR_SERVICE_URL}/send-message",
                json={
                    "language": language,
                    "action": action,
                    "payload": payload
                },
                timeout=None
            )
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as e:
            raise HTTPException(status_code=500, detail=f"Orchestrator proxy request failed: {e}")
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=f"Orchestrator responded with error: {e.response.text}")


def safe(s):
    return re.sub(r'\W+', '_', s.lower()).strip('_')

@app.post("/rag/generate-page-methods")
async def generate_page_methods():
    ensure_smart_ai_module()
    target_pages = filter_all_pages()
    print("page_method_generation_service | target_pages = ", target_pages)
    result = {}

    def create_conftest_file():
        conftest_content = '''import pytest
import json
from pathlib import Path
from lib.smart_ai import patch_page_with_smartai

@pytest.fixture(autouse=True)
def smartai_page(page):    
    script_dir = Path(__file__).parent
    metadata_path = (script_dir.parent / "metadata" / "after_enrichment.json").resolve()

    with open(metadata_path, "r") as f:
        actual_metadata = json.load(f)
    patch_page_with_smartai(page, actual_metadata)
    return page
'''

        tests_dir = Path("generated_runs") / "src" / "tests"
        tests_dir.mkdir(parents=True, exist_ok=True)

        conftest_path = tests_dir / "conftest.py"
        conftest_path.write_text(conftest_content.strip())

    create_conftest_file()

    for page in target_pages:
        page_data = collection.get(where={"page_name": page})
        entries = [r for r in page_data.get("metadatas", []) if r.get("label_text")]

        response = await send_message("python", "generate_page_file", {"entries": entries, "page_name": page})
        payload = response.get("payload")

        if not payload:
            raise HTTPException(status_code=500, detail=f"Agent did not return payload for page {page}")

        outdir = Path("generated_runs") / "src" / "pages"
        outdir.mkdir(parents=True, exist_ok=True)
        filename = outdir / payload["filename"]
        with open(filename, "w", encoding="utf-8") as f:
            f.write(payload["code"])

        result[page] = {
            "filename": str(filename),
            "code": payload["code"]
        }

    return result

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8008) # Using a different port for the new service