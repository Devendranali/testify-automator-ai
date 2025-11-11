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

# Methods for page: detail

def verify_plaintext_visible(page):
    assert page.smartAI('detail_plaintext_label_plaintext_info_08e3f9eb').is_visible()

def verify_new_contact_visible(page):
    assert page.smartAI('detail_new_contact_label_new_contact_info_59b7ccad').is_visible()

def select_contact(page, value):
    page.smartAI('detail_contact_select_contact_select_a3347554').select_option(value)

def click_summary(page):
    page.smartAI('detail_summary_link_summary_action_10c47050').click()

def click_details(page):
    page.smartAI('detail_details_link_details_action_a0a659ae').click()

def click_insights(page):
    page.smartAI('detail_insights_link_insights_action_5845d771').click()

def select_gender(page, value):
    page.smartAI('detail_gender_select_gender_select_4efd93c1').select_option(value)

def select_marital_status(page, value):
    page.smartAI('detail_marital_status_select_marital_status_select_7dab01a6').select_option(value)

def enter_spouse_partner_name(page, value):
    page.smartAI('detail_spouse/partner_name_textbox_spousepartner_name_field_f4fb2f49').fill(value)

def select_currency(page, value):
    page.smartAI('detail_currency_select_currency_select_c24f7dc0').select_option(value)

def enter_credit_limit(page, value):
    page.smartAI('detail_credit_limit_textbox_credit_limit_field_d4c789a8').fill(value)

def verify_contact_point_preferences_visible(page):
    assert page.smartAI('detail_contact_point_preferences_label_contact_point_preferences_info_1e46a171').is_visible()

def select_shipping_method(page, value):
    page.smartAI('detail_shipping_method_select_shipping_method_select_86feada2').select_option(value)

def select_freight_terms(page, value):
    page.smartAI('detail_freight_terms_select_freight_terms_select_0bdb28e5').select_option(value)

def select_originating_lead(page, value):
    page.smartAI('detail_originating_lead_select_originating_lead_select_ab22a963').select_option(value)

def click_form_assist(page):
    page.smartAI('detail_form_assist_button_form_assist_action_767338c1').click()

# ==== SmartAI methods & assertions ====

def verify_plaintext_visible(page):
    assert page.smartAI('detail_plaintext_label_plaintext_info_08e3f9eb').is_visible()


def verify_new_contact_visible(page):
    assert page.smartAI('detail_new_contact_label_new_contact_info_59b7ccad').is_visible()


def select_contact(page, value: str):
    page.smartAI('detail_contact_select_contact_select_a3347554').select_option(value)

def assert_select_contact(page, expected: str, timeout: int = 6000):
    exp = str(expected)
    # 1) Native <select>: check value and selected label
    try:
        el = page.smartAI('detail_contact_select_contact_select_a3347554')
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
    lbl = "Contact"
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
    raise AssertionError(f"Assertion failed for select '{lbl or 'detail_contact_select_contact_select_a3347554'}' expecting '{exp}'.")


def verify_summary_visible(page):
    assert page.smartAI('detail_summary_link_summary_action_10c47050').is_visible()


def verify_details_visible(page):
    assert page.smartAI('detail_details_link_details_action_a0a659ae').is_visible()


def verify_insights_visible(page):
    assert page.smartAI('detail_insights_link_insights_action_5845d771').is_visible()


def select_gender(page, value: str):
    page.smartAI('detail_gender_select_gender_select_4efd93c1').select_option(value)

def assert_select_gender(page, expected: str, timeout: int = 6000):
    exp = str(expected)
    # 1) Native <select>: check value and selected label
    try:
        el = page.smartAI('detail_gender_select_gender_select_4efd93c1')
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
    lbl = "Gender"
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
    raise AssertionError(f"Assertion failed for select '{lbl or 'detail_gender_select_gender_select_4efd93c1'}' expecting '{exp}'.")


def select_marital_status(page, value: str):
    page.smartAI('detail_marital_status_select_marital_status_select_7dab01a6').select_option(value)

def assert_select_marital_status(page, expected: str, timeout: int = 6000):
    exp = str(expected)
    # 1) Native <select>: check value and selected label
    try:
        el = page.smartAI('detail_marital_status_select_marital_status_select_7dab01a6')
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
    lbl = "Marital Status"
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
    raise AssertionError(f"Assertion failed for select '{lbl or 'detail_marital_status_select_marital_status_select_7dab01a6'}' expecting '{exp}'.")


def enter_spouse_partner_name(page, value):
    # Prefer SmartAI locator
    try:
        loc = page.smartAI('detail_spouse/partner_name_textbox_spousepartner_name_field_f4fb2f49')
        try: loc.focus(timeout=1000)
        except Exception: pass
        try: loc.fill("")
        except Exception: pass
        page.keyboard.press('Control+A'); page.keyboard.press('Backspace')
        loc.type(str(value), delay=30)
        return
    except Exception:
        pass

    _ph = "Spouse/Partner Name"
    _lbl = "Spouse/Partner Name"
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
        raise AssertionError(f"Unable to fill input for '{_lbl or _ph or 'detail_spouse/partner_name_textbox_spousepartner_name_field_f4fb2f49'}': {e}")

def assert_enter_spouse_partner_name(page, expected: str, timeout: int = 6000):
    exp = str(expected)
    # 1) Prefer SmartAI target
    try:
        locator = page.smartAI('detail_spouse/partner_name_textbox_spousepartner_name_field_f4fb2f49')
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
    lbl = "Spouse/Partner Name"
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
    ph = "Spouse/Partner Name"
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
            raise AssertionError(f"Assertion failed for '{lbl or ph or 'detail_spouse/partner_name_textbox_spousepartner_name_field_f4fb2f49'}' expecting '{exp}' (actual '{actual}'): {e}")
    except Exception as e:
        raise AssertionError(f"Assertion failed for '{lbl or ph or 'detail_spouse/partner_name_textbox_spousepartner_name_field_f4fb2f49'}' expecting '{exp}': {e}")


def select_currency(page, value: str):
    page.smartAI('detail_currency_select_currency_select_c24f7dc0').select_option(value)

def assert_select_currency(page, expected: str, timeout: int = 6000):
    exp = str(expected)
    # 1) Native <select>: check value and selected label
    try:
        el = page.smartAI('detail_currency_select_currency_select_c24f7dc0')
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
    lbl = "Currency"
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
    raise AssertionError(f"Assertion failed for select '{lbl or 'detail_currency_select_currency_select_c24f7dc0'}' expecting '{exp}'.")


def enter_credit_limit(page, value):
    # Prefer SmartAI locator
    try:
        loc = page.smartAI('detail_credit_limit_textbox_credit_limit_field_d4c789a8')
        try: loc.focus(timeout=1000)
        except Exception: pass
        try: loc.fill("")
        except Exception: pass
        page.keyboard.press('Control+A'); page.keyboard.press('Backspace')
        loc.type(str(value), delay=30)
        return
    except Exception:
        pass

    _ph = "Credit Limit"
    _lbl = "Credit Limit"
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
        raise AssertionError(f"Unable to fill input for '{_lbl or _ph or 'detail_credit_limit_textbox_credit_limit_field_d4c789a8'}': {e}")

def assert_enter_credit_limit(page, expected: str, timeout: int = 6000):
    exp = str(expected)
    # 1) Prefer SmartAI target
    try:
        locator = page.smartAI('detail_credit_limit_textbox_credit_limit_field_d4c789a8')
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
    lbl = "Credit Limit"
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
    ph = "Credit Limit"
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
            raise AssertionError(f"Assertion failed for '{lbl or ph or 'detail_credit_limit_textbox_credit_limit_field_d4c789a8'}' expecting '{exp}' (actual '{actual}'): {e}")
    except Exception as e:
        raise AssertionError(f"Assertion failed for '{lbl or ph or 'detail_credit_limit_textbox_credit_limit_field_d4c789a8'}' expecting '{exp}': {e}")


def verify_contact_point_preferences_visible(page):
    assert page.smartAI('detail_contact_point_preferences_label_contact_point_preferences_info_1e46a171').is_visible()


def select_shipping_method(page, value: str):
    page.smartAI('detail_shipping_method_select_shipping_method_select_86feada2').select_option(value)

def assert_select_shipping_method(page, expected: str, timeout: int = 6000):
    exp = str(expected)
    # 1) Native <select>: check value and selected label
    try:
        el = page.smartAI('detail_shipping_method_select_shipping_method_select_86feada2')
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
    lbl = "Shipping Method"
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
    raise AssertionError(f"Assertion failed for select '{lbl or 'detail_shipping_method_select_shipping_method_select_86feada2'}' expecting '{exp}'.")


def select_freight_terms(page, value: str):
    page.smartAI('detail_freight_terms_select_freight_terms_select_0bdb28e5').select_option(value)

def assert_select_freight_terms(page, expected: str, timeout: int = 6000):
    exp = str(expected)
    # 1) Native <select>: check value and selected label
    try:
        el = page.smartAI('detail_freight_terms_select_freight_terms_select_0bdb28e5')
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
    lbl = "Freight Terms"
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
    raise AssertionError(f"Assertion failed for select '{lbl or 'detail_freight_terms_select_freight_terms_select_0bdb28e5'}' expecting '{exp}'.")


def select_originating_lead(page, value: str):
    page.smartAI('detail_originating_lead_select_originating_lead_select_ab22a963').select_option(value)

def assert_select_originating_lead(page, expected: str, timeout: int = 6000):
    exp = str(expected)
    # 1) Native <select>: check value and selected label
    try:
        el = page.smartAI('detail_originating_lead_select_originating_lead_select_ab22a963')
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
    lbl = "Originating Lead"
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
    raise AssertionError(f"Assertion failed for select '{lbl or 'detail_originating_lead_select_originating_lead_select_ab22a963'}' expecting '{exp}'.")


def click_form_assist(page):
    page.smartAI('detail_form_assist_button_form_assist_action_767338c1').click()

