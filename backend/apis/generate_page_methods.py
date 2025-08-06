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
