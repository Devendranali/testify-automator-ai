# Auto-generated UI runner
import sys
from pathlib import Path as _Path
# Ensure generated_runs/src is on sys.path so 'from pages.*' imports work when running
# this script from the repository root or the backend folder.
_ROOT = _Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
from playwright.sync_api import sync_playwright
import json
from pathlib import Path
from pages.dominos_add_address_page_methods import *
from pages.dominos_add_page_methods import *
from pages.dominos_enter_address_page_methods import *
from pages.dominos_login_page_methods import *
from pages.dominos_main_page_methods import *
from pages.dominos_pizza_page_methods import *
from pages.dominos_viewcart_page_methods import *
from lib.smart_ai import patch_page_with_smartai
def run_positive_order_flow():
    import time
    import os
    from pathlib import Path as _Path
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=300)

        # Attempt to restore cookies / localStorage from a Playwright storage_state file.
        # Priority: UI_STORAGE_FILE env -> backend/storage/cookies.json (project-relative)
        storage_file = None
        env_sf = os.getenv("UI_STORAGE_FILE", "").strip()
        if env_sf:
            storage_file = _Path(env_sf)
        else:
            guessed = _Path(__file__).resolve().parents[3] / "backend" / "storage" / "cookies.json"
            if guessed.exists():
                storage_file = guessed

        if storage_file and storage_file.exists():
            try:
                context = browser.new_context(storage_state=str(storage_file))
                page = context.new_page()
                print(f"[ui_runner] Restored storage_state from: {storage_file}")
            except Exception as e:
                print(f"[ui_runner] Failed to restore storage_state: {e}")
                context = browser.new_context()
                page = context.new_page()
        else:
            context = browser.new_context()
            page = context.new_page()

        # Patch SmartAI
        metadata_path = Path(__file__).parent.parent / "metadata" / "after_enrichment.json"
        with open(metadata_path, "r") as f:
            actual_metadata = json.load(f)
        patch_page_with_smartai(page, actual_metadata)
        page.goto("https://www.dominos.co.in/")
        click_order_online_now(page)
        click_menu(page)
        click_add(page)
        click_view_cart(page)
        click_add_address(page)
        enter_building_house_flat_floor_no(page, "19 hoodi")
        assert_enter_building_house_flat_floor_no(page, "19 hoodi")
        enter_address(page, "Bangalore")
        assert_enter_address(page, "Bangalore")
        enter_your_name(page, "Manoj")
        assert_enter_your_name(page, "Manoj")
        enter_your_contact_number(page, "1234567890")
        assert_enter_your_contact_number(page, "1234567890")
        click_save_address(page)
        time.sleep(3)
        browser.close()

def run_negative_order_flow():
    import time
    import os
    from pathlib import Path as _Path
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=300)

        # Attempt to restore cookies / localStorage from a Playwright storage_state file.
        # Priority: UI_STORAGE_FILE env -> backend/storage/cookies.json (project-relative)
        storage_file = None
        env_sf = os.getenv("UI_STORAGE_FILE", "").strip()
        if env_sf:
            storage_file = _Path(env_sf)
        else:
            guessed = _Path(__file__).resolve().parents[3] / "backend" / "storage" / "cookies.json"
            if guessed.exists():
                storage_file = guessed

        if storage_file and storage_file.exists():
            try:
                context = browser.new_context(storage_state=str(storage_file))
                page = context.new_page()
                print(f"[ui_runner] Restored storage_state from: {storage_file}")
            except Exception as e:
                print(f"[ui_runner] Failed to restore storage_state: {e}")
                context = browser.new_context()
                page = context.new_page()
        else:
            context = browser.new_context()
            page = context.new_page()

        # Patch SmartAI
        metadata_path = Path(__file__).parent.parent / "metadata" / "after_enrichment.json"
        with open(metadata_path, "r") as f:
            actual_metadata = json.load(f)
        patch_page_with_smartai(page, actual_metadata)
        page.goto("https://www.dominos.co.in/")
        click_order_online_now(page)
        click_menu(page)
        click_add(page)
        click_view_cart(page)
        click_add_address(page)
        enter_building_house_flat_floor_no(page, "")
        assert_enter_building_house_flat_floor_no(page, "")
        enter_address(page, "")
        assert_enter_address(page, "")
        enter_your_name(page, "")
        assert_enter_your_name(page, "")
        enter_your_contact_number(page, "")
        assert_enter_your_contact_number(page, "")
        click_save_address(page)
        time.sleep(3)
        browser.close()

def run_edge_order_flow():
    import time
    import os
    from pathlib import Path as _Path
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=300)

        # Attempt to restore cookies / localStorage from a Playwright storage_state file.
        # Priority: UI_STORAGE_FILE env -> backend/storage/cookies.json (project-relative)
        storage_file = None
        env_sf = os.getenv("UI_STORAGE_FILE", "").strip()
        if env_sf:
            storage_file = _Path(env_sf)
        else:
            guessed = _Path(__file__).resolve().parents[3] / "backend" / "storage" / "cookies.json"
            if guessed.exists():
                storage_file = guessed

        if storage_file and storage_file.exists():
            try:
                context = browser.new_context(storage_state=str(storage_file))
                page = context.new_page()
                print(f"[ui_runner] Restored storage_state from: {storage_file}")
            except Exception as e:
                print(f"[ui_runner] Failed to restore storage_state: {e}")
                context = browser.new_context()
                page = context.new_page()
        else:
            context = browser.new_context()
            page = context.new_page()

        # Patch SmartAI
        metadata_path = Path(__file__).parent.parent / "metadata" / "after_enrichment.json"
        with open(metadata_path, "r") as f:
            actual_metadata = json.load(f)
        patch_page_with_smartai(page, actual_metadata)
        page.goto("https://www.dominos.co.in/")
        click_order_online_now(page)
        click_menu(page)
        click_add(page)
        click_view_cart(page)
        click_add_address(page)
        enter_building_house_flat_floor_no(page, "19 hoodi" * 50)
        assert_enter_building_house_flat_floor_no(page, "19 hoodi" * 50)
        enter_address(page, "Bangalore" * 50)
        assert_enter_address(page, "Bangalore" * 50)
        enter_your_name(page, "Manoj" * 50)
        assert_enter_your_name(page, "Manoj" * 50)
        enter_your_contact_number(page, "1234567890" * 5)
        assert_enter_your_contact_number(page, "1234567890" * 5)
        click_save_address(page)
        time.sleep(3)
        browser.close()


if __name__ == '__main__':
    run_positive_order_flow()
    run_negative_order_flow()
    run_edge_order_flow()
