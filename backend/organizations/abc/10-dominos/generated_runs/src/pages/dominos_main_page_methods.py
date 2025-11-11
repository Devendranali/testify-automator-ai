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

# Methods for page: dominos_main

def click_give_us_your_exact_location(page):
    page.smartAI('dominos_main_give_us_your_exact_location_button_give_us_your_exact_location_action_6dda9406').click()

def click_detect_location(page):
    page.smartAI('dominos_main_detect_location_button_detect_location_action_20e0a246').click()

def select_delivery(page, value):
    page.smartAI('dominos_main_delivery_select_delivery_select_f274deb7').select_option(value)

def select_takeaway(page, value):
    page.smartAI('dominos_main_takeaway_select_takeaway_select_0524dea9').select_option(value)

def select_dine_in(page, value):
    page.smartAI('dominos_main_dine_-_in_select_dine_in_select_9e113140').select_option(value)

def click_get_30_off(page):
    page.smartAI('dominos_main_get_₹30_off_button_get_30_off_action_cd6f5e88').click()

def click_view(page):
    page.smartAI('dominos_main_view_button_view_action_28d05804').click()

def verify_top_10_bestsellers_visible(page):
    assert page.smartAI('dominos_main_top_10_bestsellers_label_top_10_bestsellers_info_b54ae143').is_visible()

def verify_in_bangalore_visible(page):
    assert page.smartAI('dominos_main_in_bangalore_label_in_bangalore_info_a7ee7b37').is_visible()

def click_menu(page):
    page.smartAI('dominos_main_menu_button_menu_action_795e0131').click()

def click_offers(page):
    page.smartAI('dominos_main_offers_button_offers_action_b9d069b6').click()

# ==== SmartAI methods & assertions ====

def click_give_us_your_exact_location(page):
    page.smartAI('dominos_main_give_us_your_exact_location_button_give_us_your_exact_location_action_6dda9406').click()


def click_detect_location(page):
    page.smartAI('dominos_main_detect_location_button_detect_location_action_20e0a246').click()


def select_delivery(page, value: str):
    page.smartAI('dominos_main_delivery_select_delivery_select_f274deb7').select_option(value)

def assert_select_delivery(page, expected: str, timeout: int = 6000):
    exp = str(expected)
    # 1) Native <select>: check value and selected label
    try:
        el = page.smartAI('dominos_main_delivery_select_delivery_select_f274deb7')
        try:
            expect(el).to_have_value(exp, timeout=timeout)
            return
        except Exception:
            pass
        try:
            sel_label = el.evaluate("el => el && el.options && el.selectedIndex>=0 ? (el.options[el.selectedIndex].label || el.options[el.selectedIndex].text || '') : ''")
            if _ci(sel_label) == _ci(exp):
                return
        except Exception:
            pass
        try:
            # Try option[selected] text or value if available
            opt = el.locator('option[selected]').first
            try:
                txt = opt.inner_text()
                if _ci(txt) == _ci(exp):
                    return
            except Exception:
                pass
            try:
                val = opt.get_attribute('value')
                if val is not None and _ci(val) == _ci(exp):
                    return
            except Exception:
                pass
        except Exception:
            pass
        try:
            txt = (el.inner_text() or '').strip()
            if txt and _ci(txt) == _ci(exp):
                return
        except Exception:
            pass
        try:
            expect(el).to_contain_text(exp, timeout=timeout)
            return
        except Exception:
            pass
    except Exception:
        pass
    # 2) Custom combobox: trigger text by label
    lbl = "Delivery"
    if lbl:
        try:
            cmb = page.get_by_role('combobox', name=re.compile(re.escape(lbl), re.I))
            expect(cmb).to_contain_text(exp, timeout=timeout)
            return
        except Exception:
            pass
    # 3) Fallback: selected option with aria-selected=true
    try:
        opt = page.locator("[role='option'][aria-selected='true']").first
        try:
            expect(opt).to_contain_text(exp, timeout=timeout)
            return
        except Exception:
            pass
    except Exception:
        pass
    # Final failure
    raise AssertionError(f"Assertion failed for select '{lbl or 'dominos_main_delivery_select_delivery_select_f274deb7'}' expecting '{exp}'.")


def select_takeaway(page, value: str):
    page.smartAI('dominos_main_takeaway_select_takeaway_select_0524dea9').select_option(value)

def assert_select_takeaway(page, expected: str, timeout: int = 6000):
    exp = str(expected)
    # 1) Native <select>: check value and selected label
    try:
        el = page.smartAI('dominos_main_takeaway_select_takeaway_select_0524dea9')
        try:
            expect(el).to_have_value(exp, timeout=timeout)
            return
        except Exception:
            pass
        try:
            sel_label = el.evaluate("el => el && el.options && el.selectedIndex>=0 ? (el.options[el.selectedIndex].label || el.options[el.selectedIndex].text || '') : ''")
            if _ci(sel_label) == _ci(exp):
                return
        except Exception:
            pass
        try:
            # Try option[selected] text or value if available
            opt = el.locator('option[selected]').first
            try:
                txt = opt.inner_text()
                if _ci(txt) == _ci(exp):
                    return
            except Exception:
                pass
            try:
                val = opt.get_attribute('value')
                if val is not None and _ci(val) == _ci(exp):
                    return
            except Exception:
                pass
        except Exception:
            pass
        try:
            txt = (el.inner_text() or '').strip()
            if txt and _ci(txt) == _ci(exp):
                return
        except Exception:
            pass
        try:
            expect(el).to_contain_text(exp, timeout=timeout)
            return
        except Exception:
            pass
    except Exception:
        pass
    # 2) Custom combobox: trigger text by label
    lbl = "Takeaway"
    if lbl:
        try:
            cmb = page.get_by_role('combobox', name=re.compile(re.escape(lbl), re.I))
            expect(cmb).to_contain_text(exp, timeout=timeout)
            return
        except Exception:
            pass
    # 3) Fallback: selected option with aria-selected=true
    try:
        opt = page.locator("[role='option'][aria-selected='true']").first
        try:
            expect(opt).to_contain_text(exp, timeout=timeout)
            return
        except Exception:
            pass
    except Exception:
        pass
    # Final failure
    raise AssertionError(f"Assertion failed for select '{lbl or 'dominos_main_takeaway_select_takeaway_select_0524dea9'}' expecting '{exp}'.")


def select_dine_in(page, value: str):
    page.smartAI('dominos_main_dine_-_in_select_dine_in_select_9e113140').select_option(value)

def assert_select_dine_in(page, expected: str, timeout: int = 6000):
    exp = str(expected)
    # 1) Native <select>: check value and selected label
    try:
        el = page.smartAI('dominos_main_dine_-_in_select_dine_in_select_9e113140')
        try:
            expect(el).to_have_value(exp, timeout=timeout)
            return
        except Exception:
            pass
        try:
            sel_label = el.evaluate("el => el && el.options && el.selectedIndex>=0 ? (el.options[el.selectedIndex].label || el.options[el.selectedIndex].text || '') : ''")
            if _ci(sel_label) == _ci(exp):
                return
        except Exception:
            pass
        try:
            # Try option[selected] text or value if available
            opt = el.locator('option[selected]').first
            try:
                txt = opt.inner_text()
                if _ci(txt) == _ci(exp):
                    return
            except Exception:
                pass
            try:
                val = opt.get_attribute('value')
                if val is not None and _ci(val) == _ci(exp):
                    return
            except Exception:
                pass
        except Exception:
            pass
        try:
            txt = (el.inner_text() or '').strip()
            if txt and _ci(txt) == _ci(exp):
                return
        except Exception:
            pass
        try:
            expect(el).to_contain_text(exp, timeout=timeout)
            return
        except Exception:
            pass
    except Exception:
        pass
    # 2) Custom combobox: trigger text by label
    lbl = "Dine - in"
    if lbl:
        try:
            cmb = page.get_by_role('combobox', name=re.compile(re.escape(lbl), re.I))
            expect(cmb).to_contain_text(exp, timeout=timeout)
            return
        except Exception:
            pass
    # 3) Fallback: selected option with aria-selected=true
    try:
        opt = page.locator("[role='option'][aria-selected='true']").first
        try:
            expect(opt).to_contain_text(exp, timeout=timeout)
            return
        except Exception:
            pass
    except Exception:
        pass
    # Final failure
    raise AssertionError(f"Assertion failed for select '{lbl or 'dominos_main_dine_-_in_select_dine_in_select_9e113140'}' expecting '{exp}'.")


def click_get_30_off(page):
    page.smartAI('dominos_main_get_₹30_off_button_get_30_off_action_cd6f5e88').click()


def click_view(page):
    page.smartAI('dominos_main_view_button_view_action_28d05804').click()


def verify_top_10_bestsellers_visible(page):
    assert page.smartAI('dominos_main_top_10_bestsellers_label_top_10_bestsellers_info_b54ae143').is_visible()


def verify_in_bangalore_visible(page):
    assert page.smartAI('dominos_main_in_bangalore_label_in_bangalore_info_a7ee7b37').is_visible()


def click_menu(page):
    page.smartAI('dominos_main_menu_button_menu_action_795e0131').click()


def click_offers(page):
    page.smartAI('dominos_main_offers_button_offers_action_b9d069b6').click()

