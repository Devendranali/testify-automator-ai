from playwright.sync_api import sync_playwright

import json

from pathlib import Path

from lib.smart_ai import patch_page_with_smartai

from pages.bank_add_customer_page_methods import *

from pages.bank_customer_page_methods import *

from pages.bank_dashboard_page_methods import *

def test_positive_add_customer(page):
    page.goto("https://bank-buddy-crm-react.lovable.app/")
    verify_dashboard_visible(page)
    click_add_new_customer(page)
    enter_full_name(page, "John Doe")
    assert_enter_full_name(page, "John Doe")
    enter_email(page, "john.doe@example.com")
    assert_enter_email(page, "john.doe@example.com")
    enter_phone_number(page, "1234567890")
    assert_enter_phone_number(page, "1234567890")
    select_account_type(page, "Standard")
    assert_select_account_type(page, "Standard")
    enter_address(page, "123 Main St, Anytown, USA")
    assert_enter_address(page, "123 Main St, Anytown, USA")
    enter_occupation(page, "Software Engineer")
    assert_enter_occupation(page, "Software Engineer")
    enter_annual_income(page, "75000")
    assert_enter_annual_income(page, "75000")
    enter_initial_deposit(page, "1000")
    assert_enter_initial_deposit(page, "1000")
    click_add_customer(page)
    verify_john_doe_visible(page)

def test_negative_add_customer(page):
    page.goto("https://bank-buddy-crm-react.lovable.app/")
    verify_dashboard_visible(page)
    click_add_new_customer(page)
    enter_full_name(page, "")
    assert_enter_full_name(page, "")
    enter_email(page, "invalid-email")
    assert_enter_email(page, "invalid-email")
    enter_phone_number(page, "123")
    assert_enter_phone_number(page, "123")
    select_account_type(page, "Standard")
    assert_select_account_type(page, "Standard")
    enter_address(page, "")
    assert_enter_address(page, "")
    enter_occupation(page, "")
    assert_enter_occupation(page, "")
    enter_annual_income(page, "-100")
    assert_enter_annual_income(page, "-100")
    enter_initial_deposit(page, "-50")
    assert_enter_initial_deposit(page, "-50")
    click_add_customer(page)
    # Assuming there is a method to verify error messages, which is not listed

def test_edge_add_customer(page):
    page.goto("https://bank-buddy-crm-react.lovable.app/")
    verify_dashboard_visible(page)
    click_add_new_customer(page)
    enter_full_name(page, "A" * 256)  # Very long name
    enter_email(page, "john.doe@example.com")
    assert_enter_email(page, "john.doe@example.com")
    enter_phone_number(page, "1234567890")
    assert_enter_phone_number(page, "1234567890")
    select_account_type(page, "Standard")
    assert_select_account_type(page, "Standard")
    enter_address(page, "123 Main St, Anytown, USA")
    assert_enter_address(page, "123 Main St, Anytown, USA")
    enter_occupation(page, "Software Engineer")
    assert_enter_occupation(page, "Software Engineer")
    enter_annual_income(page, "75000")
    assert_enter_annual_income(page, "75000")
    enter_initial_deposit(page, "1000")
    assert_enter_initial_deposit(page, "1000")
    click_add_customer(page)
    # Assuming there is a method to verify handling of long input, which is not listed