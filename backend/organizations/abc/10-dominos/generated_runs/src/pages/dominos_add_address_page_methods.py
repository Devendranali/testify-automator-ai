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

# Methods for page: dominos_add_address

def verify_sure_here_are_the_extracted_ui_elements_visible(page):
    assert page.smartAI('dominos_add_address_sure,_here_are_the_extracted_ui_elements_-_label_sure_here_are_the_extracted_ui_elements_info_a6423055').is_visible()

def verify_cart_visible(page):
    assert page.smartAI('dominos_add_address_cart_label_cart_info_09613883').is_visible()

def verify_20_mins_visible(page):
    assert page.smartAI('dominos_add_address_20_mins_label_20_mins_info_fa0c6ba7').is_visible()

def click_add_address(page):
    page.smartAI('dominos_add_address_add_address_link_add_address_action_55192d19').click()

def click_know_more(page):
    page.smartAI('dominos_add_address_know_more_link_know_more_action_f3bc9a46').click()

def verify_cheese_volcano_peppy_paneer_visible(page):
    assert page.smartAI('dominos_add_address_cheese_volcano_peppy_paneer_label_cheese_volcano_peppy_paneer_info_22d1a5e1').is_visible()

def click_customise(page):
    page.smartAI('dominos_add_address_customise_link_customise_action_fad887dc').click()

def click_add_more_items(page):
    page.smartAI('dominos_add_address_add_more_items_link_add_more_items_action_58bb8b28').click()

def click_all(page):
    page.smartAI('dominos_add_address_all_button_all_action_09a9d31c').click()

def click_breads_more(page):
    page.smartAI('dominos_add_address_breads_&_more_button_breads_more_action_1e9432be').click()

def click_taco_treats(page):
    page.smartAI('dominos_add_address_taco_treats_button_taco_treats_action_b9c961e1').click()

def click_chicken_feast(page):
    page.smartAI('dominos_add_address_chicken_feast_button_chicken_feast_action_875d0cab').click()

def click_beverages(page):
    page.smartAI('dominos_add_address_beverages_button_beverages_action_f87584ad').click()

def click_desserts(page):
    page.smartAI('dominos_add_address_desserts_button_desserts_action_1375aa6e').click()

def click_dips(page):
    page.smartAI('dominos_add_address_dips_button_dips_action_70094b85').click()

def click_sourdough_garlic_bread(page):
    page.smartAI('dominos_add_address_sourdough_garlic_bread_button_sourdough_garlic_bread_action_eabaecb5').click()

def click_garlic_breadsticks_beverage(page):
    page.smartAI('dominos_add_address_garlic_breadsticks_+_beverage_button_garlic_breadsticks_beverage_action_e7896204').click()

def click_garlic_breadsticks(page):
    page.smartAI('dominos_add_address_garlic_breadsticks_button_garlic_breadsticks_action_6c01ead2').click()

def click_apply(page):
    page.smartAI('dominos_add_address_apply_button_apply_action_2d597812').click()

def select_taxes_charges(page, value):
    page.smartAI('dominos_add_address_taxes_&_charges_select_taxes_charges_select_ecbfa939').select_option(value)

def click_add_address(page):
    page.smartAI('dominos_add_address_add_address_button_add_address_action_2a32e997').click()

# ==== SmartAI methods & assertions ====

def verify_sure_here_are_the_extracted_ui_elements_visible(page):
    assert page.smartAI('dominos_add_address_sure,_here_are_the_extracted_ui_elements_-_label_sure_here_are_the_extracted_ui_elements_info_a6423055').is_visible()


def verify_cart_visible(page):
    assert page.smartAI('dominos_add_address_cart_label_cart_info_09613883').is_visible()


def verify_20_mins_visible(page):
    assert page.smartAI('dominos_add_address_20_mins_label_20_mins_info_fa0c6ba7').is_visible()


def verify_add_address_visible(page):
    assert page.smartAI('dominos_add_address_add_address_link_add_address_action_55192d19').is_visible()


def verify_know_more_visible(page):
    assert page.smartAI('dominos_add_address_know_more_link_know_more_action_f3bc9a46').is_visible()


def verify_cheese_volcano_peppy_paneer_visible(page):
    assert page.smartAI('dominos_add_address_cheese_volcano_peppy_paneer_label_cheese_volcano_peppy_paneer_info_22d1a5e1').is_visible()


def verify_customise_visible(page):
    assert page.smartAI('dominos_add_address_customise_link_customise_action_fad887dc').is_visible()


def verify_add_more_items_visible(page):
    assert page.smartAI('dominos_add_address_add_more_items_link_add_more_items_action_58bb8b28').is_visible()


def click_all(page):
    page.smartAI('dominos_add_address_all_button_all_action_09a9d31c').click()


def click_breads_more(page):
    page.smartAI('dominos_add_address_breads_&_more_button_breads_more_action_1e9432be').click()


def click_taco_treats(page):
    page.smartAI('dominos_add_address_taco_treats_button_taco_treats_action_b9c961e1').click()


def click_chicken_feast(page):
    page.smartAI('dominos_add_address_chicken_feast_button_chicken_feast_action_875d0cab').click()


def click_beverages(page):
    page.smartAI('dominos_add_address_beverages_button_beverages_action_f87584ad').click()


def click_desserts(page):
    page.smartAI('dominos_add_address_desserts_button_desserts_action_1375aa6e').click()


def click_dips(page):
    page.smartAI('dominos_add_address_dips_button_dips_action_70094b85').click()


def click_sourdough_garlic_bread(page):
    page.smartAI('dominos_add_address_sourdough_garlic_bread_button_sourdough_garlic_bread_action_eabaecb5').click()


def click_garlic_breadsticks_beverage(page):
    page.smartAI('dominos_add_address_garlic_breadsticks_+_beverage_button_garlic_breadsticks_beverage_action_e7896204').click()


def click_garlic_breadsticks(page):
    page.smartAI('dominos_add_address_garlic_breadsticks_button_garlic_breadsticks_action_6c01ead2').click()


def click_apply(page):
    page.smartAI('dominos_add_address_apply_button_apply_action_2d597812').click()


def select_taxes_charges(page, value: str):
    page.smartAI('dominos_add_address_taxes_&_charges_select_taxes_charges_select_ecbfa939').select_option(value)

def assert_select_taxes_charges(page, expected: str, timeout: int = 6000):
    exp = str(expected)
    # 1) Native <select>: check value and selected label
    try:
        el = page.smartAI('dominos_add_address_taxes_&_charges_select_taxes_charges_select_ecbfa939')
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
    lbl = "Taxes & Charges"
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
    raise AssertionError(f"Assertion failed for select '{lbl or 'dominos_add_address_taxes_&_charges_select_taxes_charges_select_ecbfa939'}' expecting '{exp}'.")


def click_add_address_open(page):
    page.smartAI('dominos_add_address_add_address_button_add_address_action_2a32e997').click()
    try:
        page.locator("[role='dialog'], form").first.wait_for(state='visible', timeout=8000)
    except Exception: pass

