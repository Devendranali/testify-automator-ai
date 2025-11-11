import re
from playwright.sync_api import expect
 
def _ci(s):  # case-insensitive canonical
    return (s or "").strip().lower()
 
def _digits_only(s):
    return re.sub(r"\D+", "", (s or ""))
 
def _values_match(actual, expected):
    a = "" if actual is None else str(actual)
    e = "" if expected is None else str(expected)
    if _ci(a) == _ci(e):
        return True
    da = _digits_only(a)
    de = _digits_only(e)
    return bool(da and de and da == de)
 
def _safe_input_value(locator):
    if locator is None:
        return None
    getters = (
        lambda: locator.input_value(),
        lambda: locator.evaluate("el => el ? (el.value || el.innerText || el.textContent) : null"),
        lambda: locator.inner_text(),
    )
    for getter in getters:
        try:
            value = getter()
            if value is not None:
                return value
        except Exception:
            continue
    return None

from lib.smart_ai import patch_page_with_smartai

# Methods for page: dominos_pizza

def click_our_menu(page):
    page.smartAI('dominos_pizza_our_menu_link_our_menu_action_5731fa20').click()

def click_domino_s_stores(page):
    page.smartAI('dominos_pizza_dominos_stores_link_dominos_stores_action_b54670c2').click()

def click_gift_card(page):
    page.smartAI('dominos_pizza_gift_card_link_gift_card_action_7f025d00').click()

def click_corporate_enquiry(page):
    page.smartAI('dominos_pizza_corporate_enquiry_link_corporate_enquiry_action_31252895').click()

def click_contact(page):
    page.smartAI('dominos_pizza_contact_link_contact_action_02fdbd40').click()

def click_download_app(page):
    page.smartAI('dominos_pizza_download_app_button_download_app_action_f6ff9e02').click()

def click_order_online_now(page):
    page.smartAI('dominos_pizza_order_online_now_button_order_online_now_action_f4e0f5c3').click()

def click_home(page):
    page.smartAI('dominos_pizza_home_link_home_action_4efd27d4').click()

def click_chat_with_us(page):
    page.smartAI('dominos_pizza_chat_with_us_link_chat_with_us_action_90025dd6').click()

# ==== SmartAI methods & assertions ====

def verify_our_menu_visible(page):
    assert page.smartAI('dominos_pizza_our_menu_link_our_menu_action_5731fa20').is_visible()


def verify_domino_s_stores_visible(page):
    assert page.smartAI('dominos_pizza_dominos_stores_link_dominos_stores_action_b54670c2').is_visible()


def verify_gift_card_visible(page):
    assert page.smartAI('dominos_pizza_gift_card_link_gift_card_action_7f025d00').is_visible()


def verify_corporate_enquiry_visible(page):
    assert page.smartAI('dominos_pizza_corporate_enquiry_link_corporate_enquiry_action_31252895').is_visible()


def verify_contact_visible(page):
    assert page.smartAI('dominos_pizza_contact_link_contact_action_02fdbd40').is_visible()


def click_download_app(page):
    page.smartAI('dominos_pizza_download_app_button_download_app_action_f6ff9e02').click()


def click_order_online_now(page):
    page.smartAI('dominos_pizza_order_online_now_button_order_online_now_action_f4e0f5c3').click()


def verify_home_visible(page):
    assert page.smartAI('dominos_pizza_home_link_home_action_4efd27d4').is_visible()


def verify_chat_with_us_visible(page):
    assert page.smartAI('dominos_pizza_chat_with_us_link_chat_with_us_action_90025dd6').is_visible()

