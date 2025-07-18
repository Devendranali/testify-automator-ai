# Auto-generated UI runner

from playwright.sync_api import sync_playwright
import json
from pathlib import Path
from pages.customer_page_methods import *
from pages.dashboard_page_methods import *
from lib.smart_ai import patch_page_with_smartai

def run_positive_add_new_customer():
    import time
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=300)
        page = browser.new_page()
        # Patch SmartAI
        metadata_path = Path(__file__).parent.parent / "metadata" / "after_enrichment.json"
        with open(metadata_path, "r") as f:
            actual_metadata = json.load(f)
        patch_page_with_smartai(page, actual_metadata)
        page.goto("https://preview--bank-buddy-crm-react.lovable.app/")
        click_customers(page)
        verify_add_customer_visible(page)
        click_add_customer(page)
        verify_full_name_visible(page)
        enter_full_name(page, "John Doe")
        verify_email_visible(page)
        enter_email(page, "john.doe@example.com")
        verify_phone_number_visible(page)
        enter_phone_number(page, "1234567890")
        verify_select_account_type_visible(page)
        select_select_account_type(page, "Standard")
        verify_address_visible(page)
        enter_address(page, "123 Main St, Anytown, USA")
        verify_occupation_visible(page)
        enter_occupation(page, "Software Engineer")
        verify_annual_income_visible(page)
        enter_annual_income(page, "75000")
        verify_initial_deposit_visible(page)
        enter_initial_deposit(page, "1000")
        click_add_customer(page)
        enter_search_customers(page, "John Doe")
        time.sleep(5)
        browser.close()

def run_negative_add_new_customer():
    import time
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=300)
        page = browser.new_page()
        # Patch SmartAI
        metadata_path = Path(__file__).parent.parent / "metadata" / "after_enrichment.json"
        with open(metadata_path, "r") as f:
            actual_metadata = json.load(f)
        patch_page_with_smartai(page, actual_metadata)
        page.goto("https://preview--bank-buddy-crm-react.lovable.app/")
        click_customers(page)
        verify_add_customer_visible(page)
        click_add_customer(page)
        verify_full_name_visible(page)
        enter_full_name(page, "John Doe")
        verify_email_visible(page)
        enter_email(page, "john.doe@example")
        verify_phone_number_visible(page)
        enter_phone_number(page, "1234567890")
        verify_select_account_type_visible(page)
        select_select_account_type(page, "Standard")
        verify_address_visible(page)
        enter_address(page, "123 Main St, Anytown, USA")
        verify_occupation_visible(page)
        enter_occupation(page, "Software Engineer")
        verify_annual_income_visible(page)
        enter_annual_income(page, "75000")
        verify_initial_deposit_visible(page)
        enter_initial_deposit(page, "1000")
        click_add_customer(page)
        time.sleep(5)
        browser.close()

def run_edge_add_new_customer():
    import time
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=300)
        page = browser.new_page()
        # Patch SmartAI
        metadata_path = Path(__file__).parent.parent / "metadata" / "after_enrichment.json"
        with open(metadata_path, "r") as f:
            actual_metadata = json.load(f)
        patch_page_with_smartai(page, actual_metadata)
        page.goto("https://preview--bank-buddy-crm-react.lovable.app/")
        click_customers(page)
        verify_add_customer_visible(page)
        click_add_customer(page)
        verify_full_name_visible(page)
        enter_full_name(page, "J" * 256)
        verify_email_visible(page)
        enter_email(page, "john.doe@example.com")
        verify_phone_number_visible(page)
        enter_phone_number(page, "1234567890")
        verify_select_account_type_visible(page)
        select_select_account_type(page, "Standard")
        verify_address_visible(page)
        enter_address(page, "123 Main St, Anytown, USA")
        verify_occupation_visible(page)
        enter_occupation(page, "Software Engineer")
        verify_annual_income_visible(page)
        enter_annual_income(page, "75000")
        verify_initial_deposit_visible(page)
        enter_initial_deposit(page, "1000")
        click_add_customer(page)
        time.sleep(5)
        browser.close()

if __name__ == '__main__':
    errors = []
    for func in [
        run_positive_add_new_customer,
        run_negative_add_new_customer,
        run_edge_add_new_customer,
    ]:
        try:
            func()
        except Exception as e:
            print(f"[ERROR] {func.__name__} failed: {e}")
            errors.append({'function': func.__name__, 'error': str(e)})
    if errors:
        print("\nSummary of failures:")
        for err in errors:
            print(f" - {err['function']} failed: {err['error']}")
    else:
        print("\nAll scenarios executed successfully!")
