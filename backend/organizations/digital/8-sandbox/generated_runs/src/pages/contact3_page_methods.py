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

# Methods for page: contact3

def verify_i_m_unable_to_extract_text_from_images_directly_however_i_can_help_guide_you_on_how_to_identify_and_classify_ui_elements_based_on_the_rules_provided_if_you_can_describe_the_elements_or_provide_the_text_i_can_assist_in_formatting_them_according_to_your_specifications_visible(page):
    assert page.smartAI('contact3_im_unable_to_extract_text_from_images_directly._however,_i_can_help_guide_you_on_how_to_identify_and_classify_ui_elements_based_on_the_rules_provided._if_you_can_describe_the_elements_or_provide_the_text,_i_can_assist_in_formatting_them_according_to_your_specifications._label_im_unable_to_extract_text_from_images_directly_however_i_can_help_guide_you_on_how_to_identify_and_classify_ui_elements_based_on_the_rules_provided_if_you_can_describe_the_elements_or_provide_the_text_i_can_assist_in_formatting_them_according_to_your_specifications_info_62fec5e1').is_visible()

# ==== SmartAI methods & assertions ====

def verify_i_m_unable_to_extract_text_from_images_directly_however_i_can_help_guide_you_on_how_to_identify_and_classify_ui_elements_based_on_the_rules_provided_if_you_can_describe_the_elements_or_provide_the_text_i_can_assist_in_formatting_them_according_to_your_specifications_visible(page):
    assert page.smartAI('contact3_im_unable_to_extract_text_from_images_directly._however,_i_can_help_guide_you_on_how_to_identify_and_classify_ui_elements_based_on_the_rules_provided._if_you_can_describe_the_elements_or_provide_the_text,_i_can_assist_in_formatting_them_according_to_your_specifications._label_im_unable_to_extract_text_from_images_directly_however_i_can_help_guide_you_on_how_to_identify_and_classify_ui_elements_based_on_the_rules_provided_if_you_can_describe_the_elements_or_provide_the_text_i_can_assist_in_formatting_them_according_to_your_specifications_info_62fec5e1').is_visible()

