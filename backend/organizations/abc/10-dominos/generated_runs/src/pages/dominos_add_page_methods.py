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

# Methods for page: dominos_add

def toggle_veg_only(page):
    page.smartAI('dominos_add_veg_only_checkbox_veg_only_checkbox_4a3b05a4').click()

def toggle_non_veg_only(page):
    page.smartAI('dominos_add_non_veg_only_checkbox_non_veg_only_checkbox_75b20f92').click()

def select_sort_by(page, value):
    page.smartAI('dominos_add_sort_by_select_sort_by_select_01abe5b3').select_option(value)

def click_veg_pizza(page):
    page.smartAI('dominos_add_veg_pizza_link_veg_pizza_action_e6a9467f').click()

def click_non_veg_pizza(page):
    page.smartAI('dominos_add_non_-_veg_pizza_link_non_veg_pizza_action_eee6e4fc').click()

def click_cheese_volcano(page):
    page.smartAI('dominos_add_cheese_volcano_link_cheese_volcano_action_e4292d12').click()

def click_chicken_feast(page):
    page.smartAI('dominos_add_chicken_feast_link_chicken_feast_action_a63efb44').click()

def click_pizza_mania(page):
    page.smartAI('dominos_add_pizza_mania_link_pizza_mania_action_23a6baa5').click()

def click_garlic_breads_dips(page):
    page.smartAI('dominos_add_garlic_breads_&_dips_link_garlic_breads_dips_action_f9018ab9').click()

def click_beverages(page):
    page.smartAI('dominos_add_beverages_link_beverages_action_0569000b').click()

def click_desserts(page):
    page.smartAI('dominos_add_desserts_link_desserts_action_bcb21e6a').click()

def click_recommended(page):
    page.smartAI('dominos_add_recommended_link_recommended_action_2c9f39d5').click()

def click_new_launches(page):
    page.smartAI('dominos_add_new_launches_link_new_launches_action_33728a91').click()

def click_chicken_burst(page):
    page.smartAI('dominos_add_chicken_burst_link_chicken_burst_action_0f900dbc').click()

def click_cheese_burst_pizza(page):
    page.smartAI('dominos_add_cheese_burst_pizza_link_cheese_burst_pizza_action_522642b5').click()

def click_big_big_pizza(page):
    page.smartAI('dominos_add_big_big_pizza_link_big_big_pizza_action_6cee4525').click()

def click_hot(page):
    page.smartAI('dominos_add_hot_link_hot_action_21b82dc9').click()

def click_customise(page):
    page.smartAI('dominos_add_customise_button_customise_action_f7489747').click()

def verify_cheese_volcano_peppy_paneer_visible(page):
    assert page.smartAI('dominos_add_cheese_volcano_peppy_paneer_label_cheese_volcano_peppy_paneer_info_36490ecd').is_visible()

def click_add(page):
    page.smartAI('dominos_add_add_+_button_add_action_272e9fef').click()

def verify_cheese_volcano_farmhouse_visible(page):
    assert page.smartAI('dominos_add_cheese_volcano_farmhouse_label_cheese_volcano_farmhouse_info_524d99d3').is_visible()

def verify_cheese_volcano_veg_paradise_visible(page):
    assert page.smartAI('dominos_add_cheese_volcano_veg_paradise_label_cheese_volcano_veg_paradise_info_4f9905cc').is_visible()

# ==== SmartAI methods & assertions ====

def toggle_veg_only(page):
    page.smartAI('dominos_add_veg_only_checkbox_veg_only_checkbox_4a3b05a4').click()


def toggle_non_veg_only(page):
    page.smartAI('dominos_add_non_veg_only_checkbox_non_veg_only_checkbox_75b20f92').click()


def select_sort_by(page, value: str):
    page.smartAI('dominos_add_sort_by_select_sort_by_select_01abe5b3').select_option(value)

def assert_select_sort_by(page, expected: str, timeout: int = 6000):
    exp = str(expected)
    # 1) Native <select>: check value and selected label
    try:
        el = page.smartAI('dominos_add_sort_by_select_sort_by_select_01abe5b3')
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
    lbl = "Sort by"
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
    raise AssertionError(f"Assertion failed for select '{lbl or 'dominos_add_sort_by_select_sort_by_select_01abe5b3'}' expecting '{exp}'.")


def verify_veg_pizza_visible(page):
    assert page.smartAI('dominos_add_veg_pizza_link_veg_pizza_action_e6a9467f').is_visible()


def verify_non_veg_pizza_visible(page):
    assert page.smartAI('dominos_add_non_-_veg_pizza_link_non_veg_pizza_action_eee6e4fc').is_visible()


def verify_cheese_volcano_visible(page):
    assert page.smartAI('dominos_add_cheese_volcano_link_cheese_volcano_action_e4292d12').is_visible()


def verify_chicken_feast_visible(page):
    assert page.smartAI('dominos_add_chicken_feast_link_chicken_feast_action_a63efb44').is_visible()


def verify_pizza_mania_visible(page):
    assert page.smartAI('dominos_add_pizza_mania_link_pizza_mania_action_23a6baa5').is_visible()


def verify_garlic_breads_dips_visible(page):
    assert page.smartAI('dominos_add_garlic_breads_&_dips_link_garlic_breads_dips_action_f9018ab9').is_visible()


def verify_beverages_visible(page):
    assert page.smartAI('dominos_add_beverages_link_beverages_action_0569000b').is_visible()


def verify_desserts_visible(page):
    assert page.smartAI('dominos_add_desserts_link_desserts_action_bcb21e6a').is_visible()


def verify_recommended_visible(page):
    assert page.smartAI('dominos_add_recommended_link_recommended_action_2c9f39d5').is_visible()


def verify_new_launches_visible(page):
    assert page.smartAI('dominos_add_new_launches_link_new_launches_action_33728a91').is_visible()


def verify_chicken_burst_visible(page):
    assert page.smartAI('dominos_add_chicken_burst_link_chicken_burst_action_0f900dbc').is_visible()


def verify_cheese_burst_pizza_visible(page):
    assert page.smartAI('dominos_add_cheese_burst_pizza_link_cheese_burst_pizza_action_522642b5').is_visible()


def verify_big_big_pizza_visible(page):
    assert page.smartAI('dominos_add_big_big_pizza_link_big_big_pizza_action_6cee4525').is_visible()


def verify_hot_visible(page):
    assert page.smartAI('dominos_add_hot_link_hot_action_21b82dc9').is_visible()


def click_customise(page):
    page.smartAI('dominos_add_customise_button_customise_action_f7489747').click()


def verify_cheese_volcano_peppy_paneer_visible(page):
    assert page.smartAI('dominos_add_cheese_volcano_peppy_paneer_label_cheese_volcano_peppy_paneer_info_36490ecd').is_visible()


def click_add_open(page):
    page.smartAI('dominos_add_add_+_button_add_action_272e9fef').click()
    try:
        page.locator("[role='dialog'], form").first.wait_for(state='visible', timeout=8000)
    except Exception: pass


def verify_cheese_volcano_farmhouse_visible(page):
    assert page.smartAI('dominos_add_cheese_volcano_farmhouse_label_cheese_volcano_farmhouse_info_524d99d3').is_visible()


def verify_cheese_volcano_veg_paradise_visible(page):
    assert page.smartAI('dominos_add_cheese_volcano_veg_paradise_label_cheese_volcano_veg_paradise_info_4f9905cc').is_visible()

