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

# Methods for page: dominos_login

def verify_domino_s_visible(page):
    assert page.smartAI('dominos_login_dominos_label_dominos_info_6c5099f0').is_visible()

def click_skip(page):
    page.smartAI('dominos_login_skip_link_skip_action_eedcad71').click()

def verify_personalized_offers_visible(page):
    assert page.smartAI('dominos_login_personalized_offers_label_personalized_offers_info_3484a796').is_visible()

def verify_loyalty_rewards_visible(page):
    assert page.smartAI('dominos_login_loyalty_rewards_label_loyalty_rewards_info_3ebf06e1').is_visible()

def verify_easy_payments_visible(page):
    assert page.smartAI('dominos_login_easy_payments_label_easy_payments_info_a42eca10').is_visible()

def enter_mobile_number(page, value):
    page.smartAI('dominos_login_mobile_number_textbox_mobile_number_field_5df778df').fill(value)

def click_send_otp(page):
    page.smartAI('dominos_login_send_otp_button_send_otp_action_9284957a').click()

def click_terms_conditions(page):
    page.smartAI('dominos_login_terms_&_conditions_link_terms_conditions_action_9f19d920').click()

# ==== SmartAI methods & assertions ====

def verify_domino_s_visible(page):
    assert page.smartAI('dominos_login_dominos_label_dominos_info_6c5099f0').is_visible()


def verify_skip_visible(page):
    assert page.smartAI('dominos_login_skip_link_skip_action_eedcad71').is_visible()


def verify_personalized_offers_visible(page):
    assert page.smartAI('dominos_login_personalized_offers_label_personalized_offers_info_3484a796').is_visible()


def verify_loyalty_rewards_visible(page):
    assert page.smartAI('dominos_login_loyalty_rewards_label_loyalty_rewards_info_3ebf06e1').is_visible()


def verify_easy_payments_visible(page):
    assert page.smartAI('dominos_login_easy_payments_label_easy_payments_info_a42eca10').is_visible()


def enter_mobile_number(page, value):
    # Prefer SmartAI locator
    try:
        loc = page.smartAI('dominos_login_mobile_number_textbox_mobile_number_field_5df778df')
        try: loc.focus(timeout=1000)
        except Exception: pass
        try: loc.fill("")
        except Exception: pass
        page.keyboard.press('Control+A'); page.keyboard.press('Backspace')
        loc.type(str(value), delay=30)
        return
    except Exception:
        pass

    _ph = "Mobile Number"
    _lbl = "Mobile Number"
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
        raise AssertionError(f"Unable to fill input for '{_lbl or _ph or 'dominos_login_mobile_number_textbox_mobile_number_field_5df778df'}': {e}")

def assert_enter_mobile_number(page, expected: str, timeout: int = 6000):
    exp = str(expected)
    # 1) Prefer SmartAI target
    try:
        locator = page.smartAI('dominos_login_mobile_number_textbox_mobile_number_field_5df778df')
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
    lbl = "Mobile Number"
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
    ph = "Mobile Number"
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
            raise AssertionError(f"Assertion failed for '{lbl or ph or 'dominos_login_mobile_number_textbox_mobile_number_field_5df778df'}' expecting '{exp}' (actual '{actual}'): {e}")
    except Exception as e:
        raise AssertionError(f"Assertion failed for '{lbl or ph or 'dominos_login_mobile_number_textbox_mobile_number_field_5df778df'}' expecting '{exp}': {e}")


def click_send_otp(page):
    page.smartAI('dominos_login_send_otp_button_send_otp_action_9284957a').click()


def verify_terms_conditions_visible(page):
    assert page.smartAI('dominos_login_terms_&_conditions_link_terms_conditions_action_9f19d920').is_visible()

