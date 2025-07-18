from playwright.sync_api import sync_playwright

from pages.customer_page_methods import *

from pages.dashboard_page_methods import *

def test_positive_add_new_customer(page):
    page.goto("https://preview--bank-buddy-crm-react.lovable.app/")
    click_customers(page)
    enter_textbox_under_full_name(page, "John Doe")
    enter_textbox_under_email(page, "john.doe@example.com")
    enter_textbox_under_phone_number(page, "1234567890")
    select_dropdown_under_account_type(page)
    enter_text_area_under_address(page, "123 Main St, Anytown, USA")
    enter_textbox_under_occupation(page, "Software Engineer")
    enter_textbox_under_annual_income(page, "75000")
    enter_textbox_under_initial_deposit(page, "1000")
    click_add_customer(page)
    verify_add_new_customer_visible(page)

def test_negative_add_new_customer(page):
    page.goto("https://preview--bank-buddy-crm-react.lovable.app/")
    click_customers(page)
    enter_textbox_under_full_name(page, "")
    enter_textbox_under_email(page, "john.doe@invalid")
    enter_textbox_under_phone_number(page, "123abc")
    select_dropdown_under_account_type(page)
    enter_text_area_under_address(page, "Invalid Address")
    enter_textbox_under_occupation(page, "")
    enter_textbox_under_annual_income(page, "-1")
    enter_textbox_under_initial_deposit(page, "invalid")
    click_add_customer(page)

def test_edge_add_new_customer(page):
    page.goto("https://preview--bank-buddy-crm-react.lovable.app/")
    click_customers(page)
    enter_textbox_under_full_name(page, "A" * 256)
    enter_textbox_under_email(page, "john.doe@example.com")
    enter_textbox_under_phone_number(page, "")
    select_dropdown_under_account_type(page)
    enter_text_area_under_address(page, "#$%^&*!@#")
    enter_textbox_under_occupation(page, "1234567890")
    enter_textbox_under_annual_income(page, "")
    enter_textbox_under_initial_deposit(page, "0")
    click_add_customer(page)