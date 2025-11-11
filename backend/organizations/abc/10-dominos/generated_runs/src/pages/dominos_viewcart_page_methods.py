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

# Methods for page: dominos_viewcart

def click_veg_pizza(page):
    page.smartAI('dominos_viewcart_veg_pizza_link_veg_pizza_action_01959c17').click()

def click_non_veg_pizza(page):
    page.smartAI('dominos_viewcart_non_-_veg_pizza_link_non_veg_pizza_action_ae5159b2').click()

def click_cheese_volcano(page):
    page.smartAI('dominos_viewcart_cheese_volcano_link_cheese_volcano_action_3aedee8a').click()

def click_chicken_feast(page):
    page.smartAI('dominos_viewcart_chicken_feast_link_chicken_feast_action_c82509b9').click()

def click_pizza_mania(page):
    page.smartAI('dominos_viewcart_pizza_mania_link_pizza_mania_action_f145501f').click()

def click_garlic_breads_dips(page):
    page.smartAI('dominos_viewcart_garlic_breads_&_dips_link_garlic_breads_dips_action_cf71abae').click()

def click_beverages(page):
    page.smartAI('dominos_viewcart_beverages_link_beverages_action_86a8b510').click()

def click_desserts(page):
    page.smartAI('dominos_viewcart_desserts_link_desserts_action_3a42fc55').click()

def click_recommended(page):
    page.smartAI('dominos_viewcart_recommended_link_recommended_action_36c60400').click()

def click_new_launches(page):
    page.smartAI('dominos_viewcart_new_launches_link_new_launches_action_61ca5351').click()

def click_chicken_burst(page):
    page.smartAI('dominos_viewcart_chicken_burst_link_chicken_burst_action_09315e63').click()

def click_cheese_burst_pizza(page):
    page.smartAI('dominos_viewcart_cheese_burst_pizza_link_cheese_burst_pizza_action_8e926963').click()

def click_big_big_pizza(page):
    page.smartAI('dominos_viewcart_big_big_pizza_link_big_big_pizza_action_45b44860').click()

def click_hot_d(page):
    page.smartAI('dominos_viewcart_hot_d_link_hot_d_action_ae0d69a5').click()

def verify_regular_plus_cheese_volcano_visible(page):
    assert page.smartAI('dominos_viewcart_regular_plus_|_cheese_volcano_label_regular_plus_cheese_volcano_info_f48f0e7b').is_visible()

def click_add(page):
    page.smartAI('dominos_viewcart_add_+_button_add_action_2288a9b7').click()

def verify_garlic_breadsticks_beverage_visible(page):
    assert page.smartAI('dominos_viewcart_garlic_breadsticks_+_beverage_label_garlic_breadsticks_beverage_info_10b4f693').is_visible()

def select_all_garlic_breads_dips(page, value):
    page.smartAI('dominos_viewcart_all_garlic_breads_&_dips_select_all_garlic_breads_dips_select_7508837a').select_option(value)

def verify_garlic_breadsticks_visible(page):
    assert page.smartAI('dominos_viewcart_garlic_breadsticks_label_garlic_breadsticks_info_8cba09e5').is_visible()

def verify_coca_cola_475ml_visible(page):
    assert page.smartAI('dominos_viewcart_coca_cola_475ml_label_coca_cola_475ml_info_6aeb31bc').is_visible()

def select_all_beverages(page, value):
    page.smartAI('dominos_viewcart_all_beverages_select_all_beverages_select_685a5e3d').select_option(value)

def verify_1_item_visible(page):
    assert page.smartAI('dominos_viewcart_1_item_label_1_item_info_06a252a6').is_visible()

def click_view_cart(page):
    page.smartAI('dominos_viewcart_view_cart_button_view_cart_action_0d964350').click()

# ==== SmartAI methods & assertions ====

def verify_veg_pizza_visible(page):
    assert page.smartAI('dominos_viewcart_veg_pizza_link_veg_pizza_action_01959c17').is_visible()


def verify_non_veg_pizza_visible(page):
    assert page.smartAI('dominos_viewcart_non_-_veg_pizza_link_non_veg_pizza_action_ae5159b2').is_visible()


def verify_cheese_volcano_visible(page):
    assert page.smartAI('dominos_viewcart_cheese_volcano_link_cheese_volcano_action_3aedee8a').is_visible()


def verify_chicken_feast_visible(page):
    assert page.smartAI('dominos_viewcart_chicken_feast_link_chicken_feast_action_c82509b9').is_visible()


def verify_pizza_mania_visible(page):
    assert page.smartAI('dominos_viewcart_pizza_mania_link_pizza_mania_action_f145501f').is_visible()


def verify_garlic_breads_dips_visible(page):
    assert page.smartAI('dominos_viewcart_garlic_breads_&_dips_link_garlic_breads_dips_action_cf71abae').is_visible()


def verify_beverages_visible(page):
    assert page.smartAI('dominos_viewcart_beverages_link_beverages_action_86a8b510').is_visible()


def verify_desserts_visible(page):
    assert page.smartAI('dominos_viewcart_desserts_link_desserts_action_3a42fc55').is_visible()


def verify_recommended_visible(page):
    assert page.smartAI('dominos_viewcart_recommended_link_recommended_action_36c60400').is_visible()


def verify_new_launches_visible(page):
    assert page.smartAI('dominos_viewcart_new_launches_link_new_launches_action_61ca5351').is_visible()


def verify_chicken_burst_visible(page):
    assert page.smartAI('dominos_viewcart_chicken_burst_link_chicken_burst_action_09315e63').is_visible()


def verify_cheese_burst_pizza_visible(page):
    assert page.smartAI('dominos_viewcart_cheese_burst_pizza_link_cheese_burst_pizza_action_8e926963').is_visible()


def verify_big_big_pizza_visible(page):
    assert page.smartAI('dominos_viewcart_big_big_pizza_link_big_big_pizza_action_45b44860').is_visible()


def verify_hot_d_visible(page):
    assert page.smartAI('dominos_viewcart_hot_d_link_hot_d_action_ae0d69a5').is_visible()


def verify_regular_plus_cheese_volcano_visible(page):
    assert page.smartAI('dominos_viewcart_regular_plus_|_cheese_volcano_label_regular_plus_cheese_volcano_info_f48f0e7b').is_visible()


def click_add_open(page):
    page.smartAI('dominos_viewcart_add_+_button_add_action_2288a9b7').click()
    try:
        page.locator("[role='dialog'], form").first.wait_for(state='visible', timeout=8000)
    except Exception: pass


def verify_garlic_breadsticks_beverage_visible(page):
    assert page.smartAI('dominos_viewcart_garlic_breadsticks_+_beverage_label_garlic_breadsticks_beverage_info_10b4f693').is_visible()


def select_all_garlic_breads_dips(page, value: str):
    page.smartAI('dominos_viewcart_all_garlic_breads_&_dips_select_all_garlic_breads_dips_select_7508837a').select_option(value)

def assert_select_all_garlic_breads_dips(page, expected: str, timeout: int = 6000):
    exp = str(expected)
    # 1) Native <select>: check value and selected label
    try:
        el = page.smartAI('dominos_viewcart_all_garlic_breads_&_dips_select_all_garlic_breads_dips_select_7508837a')
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
    lbl = "All Garlic Breads & Dips"
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
    raise AssertionError(f"Assertion failed for select '{lbl or 'dominos_viewcart_all_garlic_breads_&_dips_select_all_garlic_breads_dips_select_7508837a'}' expecting '{exp}'.")


def verify_garlic_breadsticks_visible(page):
    assert page.smartAI('dominos_viewcart_garlic_breadsticks_label_garlic_breadsticks_info_8cba09e5').is_visible()


def verify_coca_cola_475ml_visible(page):
    assert page.smartAI('dominos_viewcart_coca_cola_475ml_label_coca_cola_475ml_info_6aeb31bc').is_visible()


def select_all_beverages(page, value: str):
    page.smartAI('dominos_viewcart_all_beverages_select_all_beverages_select_685a5e3d').select_option(value)

def assert_select_all_beverages(page, expected: str, timeout: int = 6000):
    exp = str(expected)
    # 1) Native <select>: check value and selected label
    try:
        el = page.smartAI('dominos_viewcart_all_beverages_select_all_beverages_select_685a5e3d')
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
    lbl = "All Beverages"
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
    raise AssertionError(f"Assertion failed for select '{lbl or 'dominos_viewcart_all_beverages_select_all_beverages_select_685a5e3d'}' expecting '{exp}'.")


def verify_1_item_visible(page):
    assert page.smartAI('dominos_viewcart_1_item_label_1_item_info_06a252a6').is_visible()


def click_view_cart(page):
    page.smartAI('dominos_viewcart_view_cart_button_view_cart_action_0d964350').click()

