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

# Methods for page: bank_dashboard

def verify_plaintext_visible(page):
    assert page.smartAI('bank_dashboard_plaintext_label_plaintext_info_2de9a6d5').is_visible()

def verify_bank_crm_visible(page):
    assert page.smartAI('bank_dashboard_bank_crm_label_bank_crm_info_ec07a87c').is_visible()

def enter_search_customers_loans_transactions(page, value):
    page.smartAI('bank_dashboard_search_customers,_loans,_transactions..._textbox_search_customers_loans_transactions_field_bea0510c').fill(value)

def click_dashboard(page):
    page.smartAI('bank_dashboard_dashboard_link_dashboard_action_31651140').click()

def click_customers(page):
    page.smartAI('bank_dashboard_customers_link_customers_action_e4fd6efd').click()

def click_loans(page):
    page.smartAI('bank_dashboard_loans_link_loans_action_6b119177').click()

def click_transactions(page):
    page.smartAI('bank_dashboard_transactions_link_transactions_action_c7fc5c78').click()

def click_tasks(page):
    page.smartAI('bank_dashboard_tasks_link_tasks_action_335f40ff').click()

def click_reports(page):
    page.smartAI('bank_dashboard_reports_link_reports_action_6ae6bfe4').click()

def click_analytics(page):
    page.smartAI('bank_dashboard_analytics_link_analytics_action_5cdab38a').click()

def click_settings(page):
    page.smartAI('bank_dashboard_settings_link_settings_action_762b14ed').click()

def click_export_report(page):
    page.smartAI('bank_dashboard_export_report_button_export_report_action_3d8e96b0').click()

def click_john_doe(page):
    page.smartAI('bank_dashboard_john_doe_link_john_doe_action_331978c5').click()

def click_edit_with_lovable(page):
    page.smartAI('bank_dashboard_edit_with_❤️_lovable_button_edit_with_lovable_action_ecf5b518').click()

# ==== SmartAI methods & assertions ====

def verify_plaintext_visible(page):
    assert page.smartAI('bank_dashboard_plaintext_label_plaintext_info_2de9a6d5').is_visible()


def verify_bank_crm_visible(page):
    assert page.smartAI('bank_dashboard_bank_crm_label_bank_crm_info_ec07a87c').is_visible()


def enter_search_customers_loans_transactions(page, value):
    # Prefer SmartAI locator
    try:
        loc = page.smartAI('bank_dashboard_search_customers,_loans,_transactions..._textbox_search_customers_loans_transactions_field_bea0510c')
        try: loc.focus(timeout=1000)
        except Exception: pass
        try: loc.fill("")
        except Exception: pass
        page.keyboard.press('Control+A'); page.keyboard.press('Backspace')
        loc.type(str(value), delay=30)
        return
    except Exception:
        pass

    _ph = "Search customers, loans, transactions..."
    _lbl = "Search customers, loans, transactions..."
    if _ph:
        try:
            loc = page.get_by_placeholder(_ph).first
            loc.click()
            try: loc.fill("")
            except Exception: pass
            page.keyboard.press('Control+A'); page.keyboard.press('Backspace')
            loc.type(str(value), delay=30)
            return
        except Exception: pass
    if _lbl:
        try:
            loc = page.get_by_label(_lbl).first
            loc.click()
            try: loc.fill("")
            except Exception: pass
            page.keyboard.press('Control+A'); page.keyboard.press('Backspace')
            loc.type(str(value), delay=30)
            return
        except Exception: pass
    try:
        if _lbl:
            loc = page.get_by_role('textbox', name=_lbl).first
            loc.click()
            try: loc.fill("")
            except Exception: pass
            page.keyboard.press('Control+A'); page.keyboard.press('Backspace')
            loc.type(str(value), delay=30)
            return
    except Exception: pass
    try:
        loc = page.get_by_role('textbox').first
        loc.click()
        try: loc.fill("")
        except Exception: pass
        page.keyboard.press('Control+A'); page.keyboard.press('Backspace')
        loc.type(str(value), delay=30)
        return
    except Exception as e:
        raise AssertionError(f"Unable to fill input for '{_lbl or _ph or 'bank_dashboard_search_customers,_loans,_transactions..._textbox_search_customers_loans_transactions_field_bea0510c'}': {e}")

def assert_enter_search_customers_loans_transactions(page, expected: str, timeout: int = 6000):
    exp = str(expected)
    # 1) Prefer SmartAI target
    try:
        locator = page.smartAI('bank_dashboard_search_customers,_loans,_transactions..._textbox_search_customers_loans_transactions_field_bea0510c')
        try:
            expect(locator).to_have_value(exp, timeout=timeout)
            return
        except Exception:
            actual = _safe_input_value(locator)
            if _values_match(actual, exp):
                return
    except Exception:
        pass
    # 2) Fallback: label
    lbl = "Search customers, loans, transactions..."
    if lbl:
        try:
            locator = page.get_by_label(lbl)
            try:
                expect(locator).to_have_value(exp, timeout=timeout)
                return
            except Exception:
                actual = _safe_input_value(locator)
                if _values_match(actual, exp):
                    return
        except Exception:
            pass
    # 3) Fallback: placeholder
    ph = "Search customers, loans, transactions..."
    if ph:
        try:
            locator = page.get_by_placeholder(ph)
            try:
                expect(locator).to_have_value(exp, timeout=timeout)
                return
            except Exception:
                actual = _safe_input_value(locator)
                if _values_match(actual, exp):
                    return
        except Exception:
            pass
    # 4) Last resort: first textbox on page
    try:
        locator = page.get_by_role('textbox').first
        try:
            expect(locator).to_have_value(exp, timeout=timeout)
            return
        except Exception as e:
            actual = _safe_input_value(locator)
            if _values_match(actual, exp):
                return
            raise AssertionError(f"Assertion failed for '{lbl or ph or 'bank_dashboard_search_customers,_loans,_transactions..._textbox_search_customers_loans_transactions_field_bea0510c'}' expecting '{exp}' (actual '{actual}'): {e}")
    except Exception as e:
        raise AssertionError(f"Assertion failed for '{lbl or ph or 'bank_dashboard_search_customers,_loans,_transactions..._textbox_search_customers_loans_transactions_field_bea0510c'}' expecting '{exp}': {e}")


def verify_dashboard_visible(page):
    assert page.smartAI('bank_dashboard_dashboard_link_dashboard_action_31651140').is_visible()


def verify_customers_visible(page):
    assert page.smartAI('bank_dashboard_customers_link_customers_action_e4fd6efd').is_visible()


def verify_loans_visible(page):
    assert page.smartAI('bank_dashboard_loans_link_loans_action_6b119177').is_visible()


def verify_transactions_visible(page):
    assert page.smartAI('bank_dashboard_transactions_link_transactions_action_c7fc5c78').is_visible()


def verify_tasks_visible(page):
    assert page.smartAI('bank_dashboard_tasks_link_tasks_action_335f40ff').is_visible()


def verify_reports_visible(page):
    assert page.smartAI('bank_dashboard_reports_link_reports_action_6ae6bfe4').is_visible()


def verify_analytics_visible(page):
    assert page.smartAI('bank_dashboard_analytics_link_analytics_action_5cdab38a').is_visible()


def verify_settings_visible(page):
    assert page.smartAI('bank_dashboard_settings_link_settings_action_762b14ed').is_visible()


def click_export_report(page):
    page.smartAI('bank_dashboard_export_report_button_export_report_action_3d8e96b0').click()


def verify_john_doe_visible(page):
    assert page.smartAI('bank_dashboard_john_doe_link_john_doe_action_331978c5').is_visible()


def click_edit_with_lovable(page):
    page.smartAI('bank_dashboard_edit_with_❤️_lovable_button_edit_with_lovable_action_ecf5b518').click()

