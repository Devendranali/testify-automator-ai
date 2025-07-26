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
