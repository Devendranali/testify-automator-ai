from fastapi import APIRouter
from pathlib import Path
from services.test_generation_utils import collection, filter_all_pages
from utils.smart_ai_utils import ensure_smart_ai_module
from orchestrator.orchestrator import send_message

router = APIRouter()


@router.post("/rag/generate-page-methods")
def generate_page_methods():
    ensure_smart_ai_module()
    target_pages = filter_all_pages()
    result = {}

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
        (tests_dir / "conftest.py").write_text(conftest_content.strip())

    # ✅ Create conftest.py once
    create_conftest_file()

    for page in target_pages:
        page_data = collection.get(where={"page_name": page})
        entries = page_data.get("metadatas", [])

        page_spec = {
            "page_name": page,
            "entries": entries  # let agent handle all logic
        }

        response = send_message("python", "generate_page_file", page_spec)
        payload = response.payload

        outdir = Path("generated_runs") / "src" / "pages"
        outdir.mkdir(parents=True, exist_ok=True)
        filepath = outdir / payload["page_file"]
        filepath.write_text(payload["code"], encoding="utf-8")

        result[page] = {
            "filename": str(filepath),
            "code": payload["code"]
        }

    return result
