# Auto-generated UI runner

from playwright.sync_api import sync_playwright
import json
from pathlib import Path
from pages.saucedemo_login_page_methods import *
from pages.saucedemo_checkout_overview_page_methods import *
from pages.saucedemo_cart_page_methods import *
from pages.saucedemo_checkout_info_page_methods import *
from pages.saucedemo_inventory_page_methods import *
from lib.smart_ai import patch_page_with_smartai

def run_positive_end_to_end():
    import time
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=300)
        page = browser.new_page()
        # Patch SmartAI
        metadata_path = Path(__file__).parent.parent / "metadata" / "after_enrichment.json"
        with open(metadata_path, "r") as f:
            actual_metadata = json.load(f)
        patch_page_with_smartai(page, actual_metadata)
        page.goto("https://www.saucedemo.com")
        enter_username(page, "standard_user")
        enter_password(page, "secret_sauce")
        click_login(page)
        verify_products_visible(page)
        click_add_to_cart(page)
        click_shopping_cart(page)
        verify_1_your_cart_visible(page)
        click_10_checkout(page)
        verify_checkout_your_information_visible(page)
        enter_first_name(page, "John")
        enter_last_name(page, "Doe")
        enter_zip_postal_code(page, "12345")
        click_continue(page)
        verify_checkout_overview_visible(page)
        click_finish(page)
        time.sleep(5)
        browser.close()

def run_negative_end_to_end():
    import time
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=300)
        page = browser.new_page()
        # Patch SmartAI
        metadata_path = Path(__file__).parent.parent / "metadata" / "after_enrichment.json"
        with open(metadata_path, "r") as f:
            actual_metadata = json.load(f)
        patch_page_with_smartai(page, actual_metadata)
        page.goto("https://www.saucedemo.com")
        enter_username(page, "standard_user")
        enter_password(page, "")  # Empty password
        click_login(page)
        verify_error_user_visible(page)
        time.sleep(5)
        browser.close()

def run_edge_end_to_end():
    import time
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=300)
        page = browser.new_page()
        # Patch SmartAI
        metadata_path = Path(__file__).parent.parent / "metadata" / "after_enrichment.json"
        with open(metadata_path, "r") as f:
            actual_metadata = json.load(f)
        patch_page_with_smartai(page, actual_metadata)
        page.goto("https://www.saucedemo.com")
        enter_username(page, "standard_user")
        enter_password(page, "secret_sauce")
        click_login(page)
        verify_products_visible(page)
        click_add_to_cart(page)
        click_shopping_cart(page)
        verify_1_your_cart_visible(page)
        click_10_checkout(page)
        verify_checkout_your_information_visible(page)
        enter_first_name(page, "A" * 255)  # Very long first name
        enter_last_name(page, "B" * 255)  # Very long last name
        enter_zip_postal_code(page, "C" * 255)  # Very long zip code
        click_continue(page)
        verify_error_user_visible(page)
        time.sleep(5)
        browser.close()

if __name__ == '__main__':
    errors = []
    for func in [
        run_positive_end_to_end,
        run_negative_end_to_end,
        run_edge_end_to_end,
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
