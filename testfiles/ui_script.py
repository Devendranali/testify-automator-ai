# ui_script.py

from playwright.sync_api import sync_playwright
import json
from pathlib import Path

# Import all your generated page methods (adjust the import paths as needed)
from pages.add_customer_page_methods import *
from pages.customerstab_page_methods import *
from pages.dashboard_page_methods import *

# If you have patch_page_with_smartai, import it here
from lib.smart_ai import patch_page_with_smartai

def run_add_customer():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=300)  # UI visible, slow actions
        page = browser.new_page()
        page.goto("https://preview--bank-buddy-crm-react.lovable.app")

        # Load metadata and patch page (if you use SmartAI)
        script_dir = Path(__file__).parent
        metadata_path = (script_dir.parent / "metadata" / "after_enrichment.json").resolve()
        with open(metadata_path, "r") as f:
            actual_metadata = json.load(f)
        patch_page_with_smartai(page, actual_metadata)

        # Now call your steps, e.g. positive scenario:
        click_customers(page)
        click_new_customer(page)
        enter_full_name(page, "John Doe")
        enter_email(page, "john.doe@example.com")
        enter_phone_number(page, "1234567890")
        page.get_by_role("combobox").click()
        page.get_by_role("option", name="Standard").click()
        enter_address(page, "123 Main St, Anytown, USA")
        enter_occupation(page, "Software Engineer")
        enter_annual_income(page, "75000")
        enter_initial_deposit(page, "1000")
        click_add_customer(page)
        verify_add_new_customer_visible(page)

        input("Press Enter to close browser...")
        browser.close()

def run_add_account():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=300)  # UI visible, slow actions
        page = browser.new_page()
        page.goto("https://preview--bank-buddy-crm-react.lovable.app")

        # Load metadata and patch page (if you use SmartAI)
        script_dir = Path(__file__).parent
        metadata_path = (script_dir.parent / "metadata" / "after_enrichment.json").resolve()
        with open(metadata_path, "r") as f:
            actual_metadata = json.load(f)
        patch_page_with_smartai(page, actual_metadata)

        # Now call your steps, e.g. positive scenario:
        click_customers(page)
        click_new_customer(page)
        enter_full_name(page, "John Doe")
        enter_email(page, "john.doe@example.com")
        enter_phone_number(page, "1234567890")
        page.get_by_role("combobox").click()
        page.get_by_role("option", name="Standard").click()
        enter_address(page, "123 Main St, Anytown, USA")
        enter_occupation(page, "Software Engineer")
        enter_annual_income(page, "75000")
        enter_initial_deposit(page, "1000")
        click_add_customer(page)
        verify_add_new_customer_visible(page)

        input("Press Enter to close browser...")
        browser.close()

if __name__ == "__main__":
    run_add_customer()
    run_add_account()
