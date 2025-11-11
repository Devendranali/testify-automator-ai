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

# Methods for page: dominos_enter_address

def verify_order_will_be_delivered_here_visible(page):
    assert page.smartAI('dominos_enter_address_order_will_be_delivered_here_label_order_will_be_delivered_here_info_ef9889b6').is_visible()

def click_login_to_fetch_saved_addresses(page):
    page.smartAI('dominos_enter_address_login_to_fetch_saved_addresses_button_login_to_fetch_saved_addresses_action_effce3fa').click()

def verify_your_location_visible(page):
    assert page.smartAI('dominos_enter_address_your_location_label_your_location_info_19afac8f').is_visible()

def click_change(page):
    page.smartAI('dominos_enter_address_change_link_change_action_a22bf4dd').click()

def enter_building_house_flat_floor_no(page, value):
    page.smartAI('dominos_enter_address_building_/_house_/_flat_/_floor_no_textbox_building_house_flat_floor_no_field_f9689ea5').fill(value)

def enter_address(page, value):
    page.smartAI('dominos_enter_address_address_textbox_address_field_3fd384b6').fill(value)

def click_home(page):
    page.smartAI('dominos_enter_address_home_button_home_action_e99de200').click()

def click_office(page):
    page.smartAI('dominos_enter_address_office_button_office_action_e7f45cc4').click()

def click_shankarapura(page):
    page.smartAI('dominos_enter_address_shankarapura_button_shankarapura_action_0bdb7c1a').click()

def enter_your_name(page, value):
    page.smartAI('dominos_enter_address_your_name_textbox_your_name_field_a36b9f2a').fill(value)

def enter_your_contact_number(page, value):
    page.smartAI('dominos_enter_address_your_contact_number_textbox_your_contact_number_field_1da3d8e3').fill(value)

def toggle_order_for_someone_else(page):
    page.smartAI('dominos_enter_address_order_for_someone_else_checkbox_order_for_someone_else_checkbox_bedc8bf5').click()

def click_save_address(page):
    page.smartAI('dominos_enter_address_save_address_button_save_address_action_1a2fcf4b').click()

# ==== SmartAI methods & assertions ====

def verify_order_will_be_delivered_here_visible(page):
    assert page.smartAI('dominos_enter_address_order_will_be_delivered_here_label_order_will_be_delivered_here_info_ef9889b6').is_visible()


def click_login_to_fetch_saved_addresses_submit(page):
    page.smartAI('dominos_enter_address_login_to_fetch_saved_addresses_button_login_to_fetch_saved_addresses_action_effce3fa').click()


def verify_your_location_visible(page):
    assert page.smartAI('dominos_enter_address_your_location_label_your_location_info_19afac8f').is_visible()


def verify_change_visible(page):
    assert page.smartAI('dominos_enter_address_change_link_change_action_a22bf4dd').is_visible()


def enter_building_house_flat_floor_no(page, value):
    # Prefer SmartAI locator
    try:
        loc = page.smartAI('dominos_enter_address_building_/_house_/_flat_/_floor_no_textbox_building_house_flat_floor_no_field_f9689ea5')
        try: loc.focus(timeout=1000)
        except Exception: pass
        try: loc.fill("")
        except Exception: pass
        page.keyboard.press('Control+A'); page.keyboard.press('Backspace')
        loc.type(str(value), delay=30)
        return
    except Exception:
        pass

    _ph = "Building / House / Flat / Floor No"
    _lbl = "Building / House / Flat / Floor No"
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
        raise AssertionError(f"Unable to fill input for '{_lbl or _ph or 'dominos_enter_address_building_/_house_/_flat_/_floor_no_textbox_building_house_flat_floor_no_field_f9689ea5'}': {e}")

def assert_enter_building_house_flat_floor_no(page, expected: str, timeout: int = 6000):
    exp = str(expected)
    # 1) Prefer SmartAI target
    try:
        locator = page.smartAI('dominos_enter_address_building_/_house_/_flat_/_floor_no_textbox_building_house_flat_floor_no_field_f9689ea5')
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
    lbl = "Building / House / Flat / Floor No"
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
    ph = "Building / House / Flat / Floor No"
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
            raise AssertionError(f"Assertion failed for '{lbl or ph or 'dominos_enter_address_building_/_house_/_flat_/_floor_no_textbox_building_house_flat_floor_no_field_f9689ea5'}' expecting '{exp}' (actual '{actual}'): {e}")
    except Exception as e:
        raise AssertionError(f"Assertion failed for '{lbl or ph or 'dominos_enter_address_building_/_house_/_flat_/_floor_no_textbox_building_house_flat_floor_no_field_f9689ea5'}' expecting '{exp}': {e}")


def enter_address(page, value):
    # Prefer SmartAI locator
    try:
        loc = page.smartAI('dominos_enter_address_address_textbox_address_field_3fd384b6')
        try: loc.focus(timeout=1000)
        except Exception: pass
        try: loc.fill("")
        except Exception: pass
        page.keyboard.press('Control+A'); page.keyboard.press('Backspace')
        loc.type(str(value), delay=30)
        return
    except Exception:
        pass

    _ph = "Address"
    _lbl = "Address"
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
        raise AssertionError(f"Unable to fill input for '{_lbl or _ph or 'dominos_enter_address_address_textbox_address_field_3fd384b6'}': {e}")

def assert_enter_address(page, expected: str, timeout: int = 6000):
    exp = str(expected)
    # 1) Prefer SmartAI target
    try:
        locator = page.smartAI('dominos_enter_address_address_textbox_address_field_3fd384b6')
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
    lbl = "Address"
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
    ph = "Address"
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
            raise AssertionError(f"Assertion failed for '{lbl or ph or 'dominos_enter_address_address_textbox_address_field_3fd384b6'}' expecting '{exp}' (actual '{actual}'): {e}")
    except Exception as e:
        raise AssertionError(f"Assertion failed for '{lbl or ph or 'dominos_enter_address_address_textbox_address_field_3fd384b6'}' expecting '{exp}': {e}")


def click_home(page):
    page.smartAI('dominos_enter_address_home_button_home_action_e99de200').click()


def click_office(page):
    page.smartAI('dominos_enter_address_office_button_office_action_e7f45cc4').click()


def click_shankarapura(page):
    page.smartAI('dominos_enter_address_shankarapura_button_shankarapura_action_0bdb7c1a').click()


def enter_your_name(page, value):
    # Prefer SmartAI locator
    try:
        loc = page.smartAI('dominos_enter_address_your_name_textbox_your_name_field_a36b9f2a')
        try: loc.focus(timeout=1000)
        except Exception: pass
        try: loc.fill("")
        except Exception: pass
        page.keyboard.press('Control+A'); page.keyboard.press('Backspace')
        loc.type(str(value), delay=30)
        return
    except Exception:
        pass

    _ph = "Your Name"
    _lbl = "Your Name"
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
        raise AssertionError(f"Unable to fill input for '{_lbl or _ph or 'dominos_enter_address_your_name_textbox_your_name_field_a36b9f2a'}': {e}")

def assert_enter_your_name(page, expected: str, timeout: int = 6000):
    exp = str(expected)
    # 1) Prefer SmartAI target
    try:
        locator = page.smartAI('dominos_enter_address_your_name_textbox_your_name_field_a36b9f2a')
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
    lbl = "Your Name"
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
    ph = "Your Name"
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
            raise AssertionError(f"Assertion failed for '{lbl or ph or 'dominos_enter_address_your_name_textbox_your_name_field_a36b9f2a'}' expecting '{exp}' (actual '{actual}'): {e}")
    except Exception as e:
        raise AssertionError(f"Assertion failed for '{lbl or ph or 'dominos_enter_address_your_name_textbox_your_name_field_a36b9f2a'}' expecting '{exp}': {e}")


def enter_your_contact_number(page, value):
    # Prefer SmartAI locator
    try:
        loc = page.smartAI('dominos_enter_address_your_contact_number_textbox_your_contact_number_field_1da3d8e3')
        try: loc.focus(timeout=1000)
        except Exception: pass
        try: loc.fill("")
        except Exception: pass
        page.keyboard.press('Control+A'); page.keyboard.press('Backspace')
        loc.type(str(value), delay=30)
        return
    except Exception:
        pass

    _ph = "Your Contact Number"
    _lbl = "Your Contact Number"
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
        raise AssertionError(f"Unable to fill input for '{_lbl or _ph or 'dominos_enter_address_your_contact_number_textbox_your_contact_number_field_1da3d8e3'}': {e}")

def assert_enter_your_contact_number(page, expected: str, timeout: int = 6000):
    exp = str(expected)
    # 1) Prefer SmartAI target
    try:
        locator = page.smartAI('dominos_enter_address_your_contact_number_textbox_your_contact_number_field_1da3d8e3')
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
    lbl = "Your Contact Number"
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
    ph = "Your Contact Number"
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
            raise AssertionError(f"Assertion failed for '{lbl or ph or 'dominos_enter_address_your_contact_number_textbox_your_contact_number_field_1da3d8e3'}' expecting '{exp}' (actual '{actual}'): {e}")
    except Exception as e:
        raise AssertionError(f"Assertion failed for '{lbl or ph or 'dominos_enter_address_your_contact_number_textbox_your_contact_number_field_1da3d8e3'}' expecting '{exp}': {e}")


def toggle_order_for_someone_else(page):
    page.smartAI('dominos_enter_address_order_for_someone_else_checkbox_order_for_someone_else_checkbox_bedc8bf5').click()


def click_save_address_submit(page):
    page.smartAI('dominos_enter_address_save_address_button_save_address_action_1a2fcf4b').click()

