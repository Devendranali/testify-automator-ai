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

# Methods for page: dashbord

def verify_plaintext_visible(page):
    assert page.smartAI('dashbord_plaintext_label_plaintext_info_0ca5bcaf').is_visible()

def verify_dynamics_365_visible(page):
    assert page.smartAI('dashbord_dynamics_365_label_dynamics_365_info_d1bb43ec').is_visible()

def verify_customer_service_visible(page):
    assert page.smartAI('dashbord_customer_service_label_customer_service_info_b79dea7a').is_visible()

def click_save_as(page):
    page.smartAI('dashbord_save_as_button_save_as_action_055e6f90').click()

def click_new(page):
    page.smartAI('dashbord_new_button_new_action_ee10ba41').click()

def click_clear_default(page):
    page.smartAI('dashbord_clear_default_button_clear_default_action_a766831d').click()

def click_refresh_all(page):
    page.smartAI('dashbord_refresh_all_button_refresh_all_action_01f2effe').click()

def select_customer_service_representative_social_dashboard(page, value):
    page.smartAI('dashbord_customer_service_representative_social_dashboard_select_customer_service_representative_social_dashboard_select_9f6f9703').select_option(value)

def click_share(page):
    page.smartAI('dashbord_share_button_share_action_e9bbad69').click()

def click_home(page):
    page.smartAI('dashbord_home_link_home_action_277d6c81').click()

def click_recent(page):
    page.smartAI('dashbord_recent_link_recent_action_b7e8acb2').click()

def click_pinned(page):
    page.smartAI('dashbord_pinned_link_pinned_action_ab0a47aa').click()

def click_dashboards(page):
    page.smartAI('dashbord_dashboards_link_dashboards_action_1e2e53e0').click()

def click_activities(page):
    page.smartAI('dashbord_activities_link_activities_action_5ca17a00').click()

def click_accounts(page):
    page.smartAI('dashbord_accounts_link_accounts_action_b54b693f').click()

def click_contacts(page):
    page.smartAI('dashbord_contacts_link_contacts_action_52345649').click()

def click_social_profiles(page):
    page.smartAI('dashbord_social_profiles_link_social_profiles_action_730b88b4').click()

def click_cases(page):
    page.smartAI('dashbord_cases_link_cases_action_653ef201').click()

def click_queues(page):
    page.smartAI('dashbord_queues_link_queues_action_44410c06').click()

def verify_my_active_cases_visible(page):
    assert page.smartAI('dashbord_my_active_cases_label_my_active_cases_info_ffddee6c').is_visible()

def verify_all_cases_visible(page):
    assert page.smartAI('dashbord_all_cases_label_all_cases_info_4f544970').is_visible()

def verify_active_cases_visible(page):
    assert page.smartAI('dashbord_active_cases_label_active_cases_info_16c74c79').is_visible()

# ==== SmartAI methods & assertions ====

def verify_plaintext_visible(page):
    assert page.smartAI('dashbord_plaintext_label_plaintext_info_0ca5bcaf').is_visible()


def verify_dynamics_365_visible(page):
    assert page.smartAI('dashbord_dynamics_365_label_dynamics_365_info_d1bb43ec').is_visible()


def verify_customer_service_visible(page):
    assert page.smartAI('dashbord_customer_service_label_customer_service_info_b79dea7a').is_visible()


def click_save_as_submit(page):
    page.smartAI('dashbord_save_as_button_save_as_action_055e6f90').click()


def click_new_open(page):
    page.smartAI('dashbord_new_button_new_action_ee10ba41').click()
    try:
        page.locator("[role='dialog'], form").first.wait_for(state='visible', timeout=8000)
    except Exception: pass


def click_clear_default(page):
    page.smartAI('dashbord_clear_default_button_clear_default_action_a766831d').click()


def click_refresh_all(page):
    page.smartAI('dashbord_refresh_all_button_refresh_all_action_01f2effe').click()


def select_customer_service_representative_social_dashboard(page, value: str):
    page.smartAI('dashbord_customer_service_representative_social_dashboard_select_customer_service_representative_social_dashboard_select_9f6f9703').select_option(value)

def assert_select_customer_service_representative_social_dashboard(page, expected: str, timeout: int = 6000):
    exp = str(expected)
    # 1) Native <select>: check value and selected label
    try:
        el = page.smartAI('dashbord_customer_service_representative_social_dashboard_select_customer_service_representative_social_dashboard_select_9f6f9703')
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
    lbl = "Customer Service Representative Social Dashboard"
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
    raise AssertionError(f"Assertion failed for select '{lbl or 'dashbord_customer_service_representative_social_dashboard_select_customer_service_representative_social_dashboard_select_9f6f9703'}' expecting '{exp}'.")


def click_share(page):
    page.smartAI('dashbord_share_button_share_action_e9bbad69').click()


def verify_home_visible(page):
    assert page.smartAI('dashbord_home_link_home_action_277d6c81').is_visible()


def verify_recent_visible(page):
    assert page.smartAI('dashbord_recent_link_recent_action_b7e8acb2').is_visible()


def verify_pinned_visible(page):
    assert page.smartAI('dashbord_pinned_link_pinned_action_ab0a47aa').is_visible()


def verify_dashboards_visible(page):
    assert page.smartAI('dashbord_dashboards_link_dashboards_action_1e2e53e0').is_visible()


def verify_activities_visible(page):
    assert page.smartAI('dashbord_activities_link_activities_action_5ca17a00').is_visible()


def verify_accounts_visible(page):
    assert page.smartAI('dashbord_accounts_link_accounts_action_b54b693f').is_visible()


def verify_contacts_visible(page):
    assert page.smartAI('dashbord_contacts_link_contacts_action_52345649').is_visible()


def verify_social_profiles_visible(page):
    assert page.smartAI('dashbord_social_profiles_link_social_profiles_action_730b88b4').is_visible()


def verify_cases_visible(page):
    assert page.smartAI('dashbord_cases_link_cases_action_653ef201').is_visible()


def verify_queues_visible(page):
    assert page.smartAI('dashbord_queues_link_queues_action_44410c06').is_visible()


def verify_my_active_cases_visible(page):
    assert page.smartAI('dashbord_my_active_cases_label_my_active_cases_info_ffddee6c').is_visible()


def verify_all_cases_visible(page):
    assert page.smartAI('dashbord_all_cases_label_all_cases_info_4f544970').is_visible()


def verify_active_cases_visible(page):
    assert page.smartAI('dashbord_active_cases_label_active_cases_info_16c74c79').is_visible()

