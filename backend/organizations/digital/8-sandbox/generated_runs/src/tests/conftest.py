import pytest
import json
from pathlib import Path
from lib.smart_ai import patch_page_with_smartai
 
@pytest.fixture(scope="session")
def browser_type_launch_args(browser_type_launch_args):
    # Force headed + visible speed for local debug
    return {**browser_type_launch_args, "headless": False, "slow_mo": 300}
 
@pytest.fixture(autouse=True)
def smartai_page(page):
    script_dir = Path(__file__).parent
    # Try after_enrichment first, then before_enrichment, else empty
    for name in ("after_enrichment.json", "before_enrichment.json"):
        p = (script_dir.parent / "metadata" / name).resolve()
        if p.exists():
            with open(p, "r") as f:
                meta = json.load(f)
            break
    else:
        meta = []
    patch_page_with_smartai(page, meta)
    return page