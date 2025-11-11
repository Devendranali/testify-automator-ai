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

# Methods for page: bank_customer

def verify_bank_crm_visible(page):
    assert page.smartAI('bank_customer_bank_crm_label_bank_crm_info_e81414fe').is_visible()

def enter_search_customers_loans_transactions(page, value):
    page.smartAI('bank_customer_search_customers,_loans,_transactions..._textbox_search_customers_loans_transactions_field_00b5deeb').fill(value)

def verify_customers_visible(page):
    assert page.smartAI('bank_customer_customers_label_customers_info_89afecf2').is_visible()

def enter_search_customers(page, value):
    page.smartAI('bank_customer_search_customers..._textbox_search_customers_field_4073572f').fill(value)

def click_export(page):
    page.smartAI('bank_customer_export_button_export_action_30d6b1cb').click()

def click_add_new_customer(page):
    page.smartAI('bank_customer_add_new_customer_button_add_new_customer_action_62f3d845').click()

def click_filters(page):
    page.smartAI('bank_customer_filters_button_filters_action_16b8862e').click()

def click_edit_with_lovable(page):
    page.smartAI('bank_customer_edit_with_lovable_button_edit_with_lovable_action_c8e810be').click()

# ==== SmartAI methods & assertions ====

def verify_bank_crm_visible(page):
    assert page.smartAI('bank_customer_bank_crm_label_bank_crm_info_e81414fe').is_visible()


def enter_search_customers_loans_transactions(page, value):
    # Prefer SmartAI locator
    try:
        loc = page.smartAI('bank_customer_search_customers,_loans,_transactions..._textbox_search_customers_loans_transactions_field_00b5deeb')
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
        raise AssertionError(f"Unable to fill input for '{_lbl or _ph or 'bank_customer_search_customers,_loans,_transactions..._textbox_search_customers_loans_transactions_field_00b5deeb'}': {e}")

def assert_enter_search_customers_loans_transactions(page, expected: str, timeout: int = 6000):
    exp = str(expected)
    # 1) Prefer SmartAI target
    try:
        locator = page.smartAI('bank_customer_search_customers,_loans,_transactions..._textbox_search_customers_loans_transactions_field_00b5deeb')
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
            raise AssertionError(f"Assertion failed for '{lbl or ph or 'bank_customer_search_customers,_loans,_transactions..._textbox_search_customers_loans_transactions_field_00b5deeb'}' expecting '{exp}' (actual '{actual}'): {e}")
    except Exception as e:
        raise AssertionError(f"Assertion failed for '{lbl or ph or 'bank_customer_search_customers,_loans,_transactions..._textbox_search_customers_loans_transactions_field_00b5deeb'}' expecting '{exp}': {e}")


def verify_customers_visible(page):
    assert page.smartAI('bank_customer_customers_label_customers_info_89afecf2').is_visible()


def enter_search_customers(page, value):
    # Prefer SmartAI locator
    try:
        loc = page.smartAI('bank_customer_search_customers..._textbox_search_customers_field_4073572f')
        try: loc.focus(timeout=1000)
        except Exception: pass
        try: loc.fill("")
        except Exception: pass
        page.keyboard.press('Control+A'); page.keyboard.press('Backspace')
        loc.type(str(value), delay=30)
        return
    except Exception:
        pass

    _ph = "Search customers..."
    _lbl = "Search customers..."
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
        raise AssertionError(f"Unable to fill input for '{_lbl or _ph or 'bank_customer_search_customers..._textbox_search_customers_field_4073572f'}': {e}")

def assert_enter_search_customers(page, expected: str, timeout: int = 6000):
    exp = str(expected)
    # 1) Prefer SmartAI target
    try:
        locator = page.smartAI('bank_customer_search_customers..._textbox_search_customers_field_4073572f')
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
    lbl = "Search customers..."
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
    ph = "Search customers..."
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
            raise AssertionError(f"Assertion failed for '{lbl or ph or 'bank_customer_search_customers..._textbox_search_customers_field_4073572f'}' expecting '{exp}' (actual '{actual}'): {e}")
    except Exception as e:
        raise AssertionError(f"Assertion failed for '{lbl or ph or 'bank_customer_search_customers..._textbox_search_customers_field_4073572f'}' expecting '{exp}': {e}")


def click_export(page):
    page.smartAI('bank_customer_export_button_export_action_30d6b1cb').click()


def click_add_new_customer_open(page):
    page.smartAI('bank_customer_add_new_customer_button_add_new_customer_action_62f3d845').click()
    try:
        page.locator("[role='dialog'], form").first.wait_for(state='visible', timeout=8000)
    except Exception: pass


def click_filters(page):
    page.smartAI('bank_customer_filters_button_filters_action_16b8862e').click()


def click_edit_with_lovable(page):
    page.smartAI('bank_customer_edit_with_lovable_button_edit_with_lovable_action_c8e810be').click()

