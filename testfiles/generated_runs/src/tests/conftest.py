import pytest
import json
from pathlib import Path
from lib.smart_ai import patch_page_with_smartai

@pytest.fixture(autouse=True)
def smartai_page(page):    
    # Get the path to THIS FILE's directory
    script_dir = Path(__file__).parent
    # Go up one to 'src', then into 'metadata'
    metadata_path = (script_dir.parent / "metadata" / "after_enrichment.json").resolve()

    # print("Loading:", metadata_path)  # Debug, can remove

    with open(metadata_path, "r") as f:
        actual_metadata = json.load(f)
    patch_page_with_smartai(page, actual_metadata)
    return page