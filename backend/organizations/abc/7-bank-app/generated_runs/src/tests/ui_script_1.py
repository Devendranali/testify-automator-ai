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
from pages.bank_add_customer_page_methods import *
from pages.bank_customer_page_methods import *
from pages.bank_dashboard_page_methods import *
from lib.smart_ai import patch_page_with_smartai
def run_positive_add_customer():
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
        page.goto("https://bank-buddy-crm-react.lovable.app/")
        click_customers(page)
        click_add_new_customer(page)
        enter_full_name(page, "John Doe")
        assert_enter_full_name(page, "John Doe")
        enter_email(page, "john.doe@example.com")
        assert_enter_email(page, "john.doe@example.com")
        enter_phone_number(page, "1234567890")
        assert_enter_phone_number(page, "1234567890")
        select_account_type(page, "Standard")
        # assert_select_account_type(page, "Standard")
        enter_address(page, "123 Main St, Anytown, USA")
        assert_enter_address(page, "123 Main St, Anytown, USA")
        enter_occupation(page, "Software Engineer")
        assert_enter_occupation(page, "Software Engineer")
        enter_annual_income(page, "75000")
        # assert_enter_annual_income(page, "75000")
        enter_initial_deposit(page, "1000")
        # assert_enter_initial_deposit(page, "1000")
        click_add_customer(page)
        verify_john_doe_visible(page)
        time.sleep(3)
        browser.close()

def run_negative_add_customer():
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
        page.goto("https://bank-buddy-crm-react.lovable.app/")
        click_customers(page)
        click_add_new_customer(page)
        enter_full_name(page, "John Doe")
        assert_enter_full_name(page, "John Doe")
        enter_email(page, "invalid-email")
        assert_enter_email(page, "invalid-email")
        enter_phone_number(page, "1234567890")
        assert_enter_phone_number(page, "1234567890")
        select_account_type(page, "Standard")
        # assert_select_account_type(page, "Standard")
        enter_address(page, "123 Main St, Anytown, USA")
        assert_enter_address(page, "123 Main St, Anytown, USA")
        enter_occupation(page, "Software Engineer")
        assert_enter_occupation(page, "Software Engineer")
        enter_annual_income(page, "75000")
        assert_enter_annual_income(page, "75000")
        enter_initial_deposit(page, "1000")
        assert_enter_initial_deposit(page, "1000")
        click_add_customer(page)
        # Assuming there is a method to verify error message, which is not listed
        time.sleep(3)
        browser.close()

def run_edge_add_customer():
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
        page.goto("https://bank-buddy-crm-react.lovable.app/")
        click_customers(page)
        click_add_new_customer(page)
        enter_full_name(page, "J" * 256)  # Very long name
        enter_email(page, "john.doe@example.com")
        assert_enter_email(page, "john.doe@example.com")
        enter_phone_number(page, "1234567890")
        assert_enter_phone_number(page, "1234567890")
        select_account_type(page, "Standard")
        # assert_select_account_type(page, "Standard")
        enter_address(page, "123 Main St, Anytown, USA")
        assert_enter_address(page, "123 Main St, Anytown, USA")
        enter_occupation(page, "Software Engineer")
        assert_enter_occupation(page, "Software Engineer")
        enter_annual_income(page, "75000")
        assert_enter_annual_income(page, "75000")
        enter_initial_deposit(page, "1000")
        assert_enter_initial_deposit(page, "1000")
        click_add_customer(page)
        # Assuming there is a method to verify error message, which is not listed
        time.sleep(3)
        browser.close()


if __name__ == '__main__':
    run_positive_add_customer()
    run_negative_add_customer()
    run_edge_add_customer()
