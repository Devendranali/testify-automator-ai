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

# Methods for page: contact

def click_dynamics_365(page):
    page.smartAI('contact_dynamics_365_link_dynamics_365_action_f618d382').click()

def click_customer_service(page):
    page.smartAI('contact_customer_service_link_customer_service_action_dc2ed35e').click()

def click_home(page):
    page.smartAI('contact_home_link_home_action_9bbc6ff3').click()

def click_recent(page):
    page.smartAI('contact_recent_link_recent_action_2378b78d').click()

def click_pinned(page):
    page.smartAI('contact_pinned_link_pinned_action_ba9df697').click()

def click_dashboards(page):
    page.smartAI('contact_dashboards_link_dashboards_action_27ce443f').click()

def click_activities(page):
    page.smartAI('contact_activities_link_activities_action_75b77975').click()

def click_accounts(page):
    page.smartAI('contact_accounts_link_accounts_action_d2228769').click()

def click_contacts(page):
    page.smartAI('contact_contacts_link_contacts_action_b59021d7').click()

def click_social_profiles(page):
    page.smartAI('contact_social_profiles_link_social_profiles_action_392d5b06').click()

def click_cases(page):
    page.smartAI('contact_cases_link_cases_action_11dd34e7').click()

def click_queues(page):
    page.smartAI('contact_queues_link_queues_action_be7feae2').click()

def click_products(page):
    page.smartAI('contact_products_link_products_action_2cd92053').click()

def click_service(page):
    page.smartAI('contact_service_link_service_action_6afa52a9').click()

def click_focused_view(page):
    page.smartAI('contact_focused_view_button_focused_view_action_b72250e1').click()

def click_show_chart(page):
    page.smartAI('contact_show_chart_button_show_chart_action_fd871030').click()

def click_new(page):
    page.smartAI('contact_new_button_new_action_2d7462e9').click()

def click_delete(page):
    page.smartAI('contact_delete_button_delete_action_3dc7ba3b').click()

def click_refresh(page):
    page.smartAI('contact_refresh_button_refresh_action_d3d87a45').click()

def click_visualize_this_view(page):
    page.smartAI('contact_visualize_this_view_button_visualize_this_view_action_bf348324').click()

def select_my_active_contacts(page, value):
    page.smartAI('contact_my_active_contacts_select_my_active_contacts_select_d545e2a9').select_option(value)

def select_full_name(page, value):
    page.smartAI('contact_full_name_select_full_name_select_69c1f780').select_option(value)

def select_email(page, value):
    page.smartAI('contact_email_select_email_select_05ab97c5').select_option(value)

def select_company_name(page, value):
    page.smartAI('contact_company_name_select_company_name_select_b51fe168').select_option(value)

def select_business_phone(page, value):
    page.smartAI('contact_business_phone_select_business_phone_select_33e5ea02').select_option(value)

def click_edit_columns(page):
    page.smartAI('contact_edit_columns_link_edit_columns_action_eaf3e508').click()

def click_edit_filters(page):
    page.smartAI('contact_edit_filters_link_edit_filters_action_0908d73c').click()

def enter_filter_by_keyword(page, value):
    page.smartAI('contact_filter_by_keyword_textbox_filter_by_keyword_field_92958cf2').fill(value)

# ==== SmartAI methods & assertions ====

def verify_dynamics_365_visible(page):
    assert page.smartAI('contact_dynamics_365_link_dynamics_365_action_f618d382').is_visible()


def verify_customer_service_visible(page):
    assert page.smartAI('contact_customer_service_link_customer_service_action_dc2ed35e').is_visible()


def verify_home_visible(page):
    assert page.smartAI('contact_home_link_home_action_9bbc6ff3').is_visible()


def verify_recent_visible(page):
    assert page.smartAI('contact_recent_link_recent_action_2378b78d').is_visible()


def verify_pinned_visible(page):
    assert page.smartAI('contact_pinned_link_pinned_action_ba9df697').is_visible()


def verify_dashboards_visible(page):
    assert page.smartAI('contact_dashboards_link_dashboards_action_27ce443f').is_visible()


def verify_activities_visible(page):
    assert page.smartAI('contact_activities_link_activities_action_75b77975').is_visible()


def verify_accounts_visible(page):
    assert page.smartAI('contact_accounts_link_accounts_action_d2228769').is_visible()


def verify_contacts_visible(page):
    assert page.smartAI('contact_contacts_link_contacts_action_b59021d7').is_visible()


def verify_social_profiles_visible(page):
    assert page.smartAI('contact_social_profiles_link_social_profiles_action_392d5b06').is_visible()


def verify_cases_visible(page):
    assert page.smartAI('contact_cases_link_cases_action_11dd34e7').is_visible()


def verify_queues_visible(page):
    assert page.smartAI('contact_queues_link_queues_action_be7feae2').is_visible()


def verify_products_visible(page):
    assert page.smartAI('contact_products_link_products_action_2cd92053').is_visible()


def verify_service_visible(page):
    assert page.smartAI('contact_service_link_service_action_6afa52a9').is_visible()


def click_focused_view(page):
    page.smartAI('contact_focused_view_button_focused_view_action_b72250e1').click()


def click_show_chart(page):
    page.smartAI('contact_show_chart_button_show_chart_action_fd871030').click()


def click_new_open(page):
    page.smartAI('contact_new_button_new_action_2d7462e9').click()
    try:
        page.locator("[role='dialog'], form").first.wait_for(state='visible', timeout=8000)
    except Exception: pass


def click_delete(page):
    page.smartAI('contact_delete_button_delete_action_3dc7ba3b').click()


def click_refresh(page):
    page.smartAI('contact_refresh_button_refresh_action_d3d87a45').click()


def click_visualize_this_view(page):
    page.smartAI('contact_visualize_this_view_button_visualize_this_view_action_bf348324').click()


def select_my_active_contacts(page, value: str):
    page.smartAI('contact_my_active_contacts_select_my_active_contacts_select_d545e2a9').select_option(value)

def assert_select_my_active_contacts(page, expected: str, timeout: int = 6000):
    exp = str(expected)
    # 1) Native <select>: check value and selected label
    try:
        el = page.smartAI('contact_my_active_contacts_select_my_active_contacts_select_d545e2a9')
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
    lbl = "My Active Contacts"
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
    raise AssertionError(f"Assertion failed for select '{lbl or 'contact_my_active_contacts_select_my_active_contacts_select_d545e2a9'}' expecting '{exp}'.")


def select_full_name(page, value: str):
    page.smartAI('contact_full_name_select_full_name_select_69c1f780').select_option(value)

def assert_select_full_name(page, expected: str, timeout: int = 6000):
    exp = str(expected)
    # 1) Native <select>: check value and selected label
    try:
        el = page.smartAI('contact_full_name_select_full_name_select_69c1f780')
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
    lbl = "Full Name"
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
    raise AssertionError(f"Assertion failed for select '{lbl or 'contact_full_name_select_full_name_select_69c1f780'}' expecting '{exp}'.")


def select_email(page, value: str):
    page.smartAI('contact_email_select_email_select_05ab97c5').select_option(value)

def assert_select_email(page, expected: str, timeout: int = 6000):
    exp = str(expected)
    # 1) Native <select>: check value and selected label
    try:
        el = page.smartAI('contact_email_select_email_select_05ab97c5')
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
    lbl = "Email"
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
    raise AssertionError(f"Assertion failed for select '{lbl or 'contact_email_select_email_select_05ab97c5'}' expecting '{exp}'.")


def select_company_name(page, value: str):
    page.smartAI('contact_company_name_select_company_name_select_b51fe168').select_option(value)

def assert_select_company_name(page, expected: str, timeout: int = 6000):
    exp = str(expected)
    # 1) Native <select>: check value and selected label
    try:
        el = page.smartAI('contact_company_name_select_company_name_select_b51fe168')
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
    lbl = "Company Name"
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
    raise AssertionError(f"Assertion failed for select '{lbl or 'contact_company_name_select_company_name_select_b51fe168'}' expecting '{exp}'.")


def select_business_phone(page, value: str):
    page.smartAI('contact_business_phone_select_business_phone_select_33e5ea02').select_option(value)

def assert_select_business_phone(page, expected: str, timeout: int = 6000):
    exp = str(expected)
    # 1) Native <select>: check value and selected label
    try:
        el = page.smartAI('contact_business_phone_select_business_phone_select_33e5ea02')
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
    lbl = "Business Phone"
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
    raise AssertionError(f"Assertion failed for select '{lbl or 'contact_business_phone_select_business_phone_select_33e5ea02'}' expecting '{exp}'.")


def verify_edit_columns_visible(page):
    assert page.smartAI('contact_edit_columns_link_edit_columns_action_eaf3e508').is_visible()


def verify_edit_filters_visible(page):
    assert page.smartAI('contact_edit_filters_link_edit_filters_action_0908d73c').is_visible()


def enter_filter_by_keyword(page, value):
    # Prefer SmartAI locator
    try:
        loc = page.smartAI('contact_filter_by_keyword_textbox_filter_by_keyword_field_92958cf2')
        try: loc.focus(timeout=1000)
        except Exception: pass
        try: loc.fill("")
        except Exception: pass
        page.keyboard.press('Control+A'); page.keyboard.press('Backspace')
        loc.type(str(value), delay=30)
        return
    except Exception:
        pass

    _ph = "Filter by keyword"
    _lbl = "Filter by keyword"
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
        raise AssertionError(f"Unable to fill input for '{_lbl or _ph or 'contact_filter_by_keyword_textbox_filter_by_keyword_field_92958cf2'}': {e}")

def assert_enter_filter_by_keyword(page, expected: str, timeout: int = 6000):
    exp = str(expected)
    # 1) Prefer SmartAI target
    try:
        locator = page.smartAI('contact_filter_by_keyword_textbox_filter_by_keyword_field_92958cf2')
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
    lbl = "Filter by keyword"
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
    ph = "Filter by keyword"
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
            raise AssertionError(f"Assertion failed for '{lbl or ph or 'contact_filter_by_keyword_textbox_filter_by_keyword_field_92958cf2'}' expecting '{exp}' (actual '{actual}'): {e}")
    except Exception as e:
        raise AssertionError(f"Assertion failed for '{lbl or ph or 'contact_filter_by_keyword_textbox_filter_by_keyword_field_92958cf2'}' expecting '{exp}': {e}")

