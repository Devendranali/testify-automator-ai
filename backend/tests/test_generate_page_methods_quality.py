import re
import sys
import types
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from apis import generate_page_methods  # noqa: E402


def _extract_class_methods(source: str, class_name: str) -> list[str]:
    in_class = False
    methods: list[str] = []
    for line in source.splitlines():
        if not in_class:
            if re.match(rf"^class\s+{re.escape(class_name)}\b", line):
                in_class = True
            continue
        if line.strip() and not line.startswith(" "):
            break
        match = re.match(r"^\s{4}def\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", line)
        if match:
            methods.append(match.group(1))
    return methods


def test_generate_page_methods_dedup_and_names():
    entries = [
        {"label_text": "Submit", "ocr_type": "button", "test_id": "submit-btn"},
        {"label_text": "Submit", "ocr_type": "button", "test_id": "submit-btn"},
    ]
    code, method_names, class_name, _ = generate_page_methods._generate_page_file("sample", entries)
    assert "click_submit" in method_names
    assert "click_submit_2" not in method_names
    class_methods = _extract_class_methods(code, class_name)
    assert len(class_methods) == len(set(class_methods))
    assert any(name.startswith("scroll_to_") for name in class_methods)
    assert class_name == "SamplePage"


def test_generate_page_methods_recovers_canonical_input_labels_from_neighbor_labels():
    entries = [
        {"label_text": "Email", "ocr_type": "label"},
        {
            "label_text": "Please Enter Email",
            "placeholder": "Please Enter Email",
            "ocr_type": "textbox",
            "unique_name": "zing_leave1_please_enter_email_textbox_please_enter_email_field",
        },
    ]
    annotated = generate_page_methods._annotate_legacy_input_labels(entries)
    code = generate_page_methods.build_method(annotated[1], {})
    assert "def enter_email(page, value):" in code
    assert "_enter_value(page, 'Email', value, placeholder='Please Enter Email')" in code


def test_generate_page_methods_recovers_description_from_placeholder_prompt():
    entries = [
        {"label_text": "Description", "ocr_type": "label"},
        {
            "label_text": "Enter your message here(max 500 characters)",
            "placeholder": "Enter your message here(max 500 characters)",
            "ocr_type": "textbox",
            "unique_name": "zing_wfh_enter_your_message_here_textbox",
        },
    ]
    annotated = generate_page_methods._annotate_legacy_input_labels(entries)
    code = generate_page_methods.build_method(annotated[1], {})
    assert "def enter_description(page, value):" in code
    assert "_enter_value(page, 'Description', value, placeholder='Enter your message here(max 500 characters)')" in code


def test_generate_page_methods_locator_priority():
    entries = [
        {
            "label_text": "Search",
            "get_by_text": "Search",
            "test_id": "search-input",
            "ocr_type": "input",
            "data_qa": "search-input-qa",
            "name": "search",
        }
    ]
    code, _, _, _ = generate_page_methods._generate_page_file("search", entries)
    test_id_idx = code.find("get_by_test_id")
    name_idx = code.find("[name=")
    data_qa_idx = code.find("[data-qa=")
    fallback_text_idx = code.find("_is_text_safe(text)")
    css_idx = code.find("css_selector")
    assert test_id_idx != -1
    assert name_idx != -1
    assert data_qa_idx != -1
    assert fallback_text_idx != -1
    assert css_idx != -1
    assert test_id_idx < name_idx
    assert name_idx < data_qa_idx
    assert data_qa_idx < fallback_text_idx
    assert css_idx < fallback_text_idx


def test_generate_page_methods_actions_and_exec():
    entries = [
        {"label_text": "Full Name", "ocr_type": "input", "placeholder": "Full Name"},
        {"label_text": "Account Type", "ocr_type": "select", "placeholder": "Account Type"},
        {"label_text": "Upload Document", "ocr_type": "upload", "test_id": "upload-doc"},
        {"label_text": "Drag Source", "ocr_type": "drag", "test_id": "drag-source", "is_draggable": True},
        {"label_text": "Create", "ocr_type": "button", "test_id": "create-btn"},
    ]
    code, method_names, _, _ = generate_page_methods._generate_page_file("forms", entries)
    assert any(name.startswith("fill_") for name in method_names)
    assert any(name.startswith("select_") for name in method_names)
    assert any(name.startswith("upload_") for name in method_names)
    assert any(name.startswith("drag_") for name in method_names)
    assert any(name.startswith("click_") for name in method_names)

    stub_lib = types.ModuleType("lib")
    stub_ui_actions = types.ModuleType("lib.ui_actions")

    def _safe_drag_and_drop(*_args, **_kwargs):
        return None

    stub_ui_actions.safe_drag_and_drop = _safe_drag_and_drop
    sys.modules.setdefault("lib", stub_lib)
    sys.modules["lib.ui_actions"] = stub_ui_actions

    compiled = compile(code, "<generated_page>", "exec")
    exec(compiled, {})


def test_generate_page_methods_label_following_order():
    entries = [
        {"label_text": "Account Type", "ocr_type": "select", "get_by_text": "Account Type"},
    ]
    code, _, _, _ = generate_page_methods._generate_page_file("forms", entries)
    select_idx = code.find("following::select[1]")
    combo_idx = code.find("following::*[@role='combobox'][1]")
    input_idx = code.find("following::input[1] | following::textarea[1]")
    assert select_idx != -1
    assert combo_idx != -1
    assert input_idx != -1
    assert select_idx < combo_idx < input_idx


def test_generate_page_methods_select_combobox_listbox_flow():
    helper = generate_page_methods.ASSERT_HELPER_BLOCK
    assert 'get_by_role("listbox")' in helper
    assert 'get_by_role("option", name=str(value), exact=True)' in helper
    assert 'get_by_role("menuitem", name=str(value), exact=True)' in helper
    assert 'get_by_role("listitem", name=str(value), exact=True)' in helper


def test_generate_page_methods_dedupe_by_action_and_locator():
    entries = [
        {"label_text": "Save", "ocr_type": "button", "test_id": "save-btn"},
        {"label_text": "Save Copy", "ocr_type": "button", "test_id": "save-btn"},
    ]
    _, method_names, _, _ = generate_page_methods._generate_page_file("sample", entries)
    assert "click_save" in method_names
    assert "click_save_copy" not in method_names


def test_merge_pom_code_replaces_autogen_block():
    entries = [{"label_text": "Submit", "ocr_type": "button", "test_id": "submit-btn"}]
    generated, _, class_name, _ = generate_page_methods._generate_page_file("sample", entries)
    existing = (
        "from __future__ import annotations\n"
        f"class {class_name}(object):\n"
        "    # --- AUTOGENERATED START ---\n"
        "    def stale_method(self):\n"
        "        return 1\n"
        "    # --- AUTOGENERATED END ---\n"
        "\n"
        "def custom_helper():\n"
        "    return 2\n"
    )
    merged = generate_page_methods._merge_pom_code(existing, generated, class_name)
    assert "stale_method" not in merged
    assert "custom_helper" in merged


def test_select_methods_prefer_label_fallback_before_smart_ai():
    code = generate_page_methods.build_method(
        {
            "label_text": "Visit Time",
            "ocr_type": "select",
            "unique_name": "firrst_visit_time_select_visit_time_select",
        },
        {},
    )
    assert "_select_by_label(page, 'Visit Time', value)" in code
    assert "page.smartAI('firrst_visit_time_select_visit_time_select').select_option(value)" in code
    assert code.find("_select_by_label(page, 'Visit Time', value)") < code.find(
        "page.smartAI('firrst_visit_time_select_visit_time_select').select_option(value)"
    )


def test_assert_helper_block_contains_stronger_select_fallbacks():
    helper = generate_page_methods.ASSERT_HELPER_BLOCK
    assert "def _find_frame_for_field(page, label=None, placeholder=None):" in helper
    assert "def _placeholder_variants(label, placeholder=None):" in helper
    assert "def _safe_locator_text(locator):" in helper
    assert "def _normalize_visible_text(text):" in helper
    assert "def _text_visibility_candidates(page, text):" in helper
    assert "def _dismiss_open_dropdowns(page):" in helper
    assert "target_page = _find_frame_for_field(page, label=label) or page" in helper
    assert "current_value = _safe_locator_text(locator)" in helper
    assert "_dismiss_open_dropdowns(page)" in helper
    assert 'get_by_role("combobox", name=exact_label_re)' in helper
    assert 'get_by_role("button", name=exact_label_re)' in helper
    assert "/following::*[self::select or self::button or @role='combobox' or @role='button' or @aria-haspopup='listbox' or @aria-haspopup='menu'][1]" in helper
    assert 'target_page.get_by_role("menuitem", name=option_re).first' in helper
    assert 'target_page.get_by_text(option_re).first' in helper


def test_assert_helper_block_strengthens_click_after_dropdowns():
    helper = generate_page_methods.ASSERT_HELPER_BLOCK
    assert '_dismiss_open_dropdowns(page)\n    strategies = (' in helper
    assert 'page.locator("button").filter(has_text=exact_re).first' in helper
    assert 'page.locator("text=/^\\\\s*" + re.escape(label) + "\\\\s*$/i").first' in helper


def test_assert_helper_block_strengthens_text_entry_fallbacks():
    helper = generate_page_methods.ASSERT_HELPER_BLOCK
    assert '_EDITABLE_SELECTOR = "input:not([type=\'hidden\']), textarea, [contenteditable=\'true\'], [role=\'textbox\']"' in helper
    assert "def _editable_locator(locator):" in helper
    assert "def _fill_locator(locator, value):" in helper
    assert "def _find_password_locator(page, label=\"Password\", placeholder=None):" in helper
    assert "input[type='password']" in helper
    assert 'target_page.locator("label").filter(has_text=exact_re).locator(' in helper
    assert "xpath=preceding::*[self::input or self::textarea or @contenteditable='true' or @role='textbox'][1]" in helper
    assert "target_page.get_by_text(label, exact=True).first.locator(_EDITABLE_SELECTOR).first" in helper


def test_assert_helper_block_strengthens_text_visibility_matching():
    helper = generate_page_methods.ASSERT_HELPER_BLOCK
    assert 'scope.get_by_text(label, exact=True).first' in helper
    assert 'scope.get_by_text(exact_re).first' in helper
    assert 'scope.get_by_text(partial_re).first' in helper
    assert 'scope.get_by_role(role, name=partial_re).first' in helper
    assert "contains(translate(normalize-space(.)," in helper
    assert 'raise AssertionError(f"Expected visible text not found: {label}")' in helper


def test_assert_helper_block_supports_launcher_grid_icons():
    helper = generate_page_methods.ASSERT_HELPER_BLOCK
    assert '"apps": ("app", "launcher", "menu", "grid", "waffle")' in helper
    assert 'def _looks_like_grid_launcher(page, locator):' in helper
    assert 'def _try_launcher_icon_candidate(page):' in helper
    assert 'if any(token in ("app", "apps", "launcher", "grid", "waffle", "menu", "dots") for token in tokens):' in helper


def test_assert_helper_block_prefers_active_modal_scopes():
    helper = generate_page_methods.ASSERT_HELPER_BLOCK
    assert "def _active_modal_scopes(page, label=None, placeholder=None):" in helper
    assert "[role='dialog']" in helper
    assert "def _interaction_scopes(page, label=None, placeholder=None):" in helper
    assert "modal_scopes = _active_modal_scopes(page)" in helper
    assert "return modal_scopes[0]" in helper


def test_assert_helper_block_exposes_generic_section_expansion_helpers():
    helper = generate_page_methods.ASSERT_HELPER_BLOCK
    assert "def _is_section_expanded(page, section_label, required_texts=None, required_placeholders=None):" in helper
    assert "def ensure_section_expanded(page, section_label, required_texts=None, required_placeholders=None, timeout_ms: int = 2000):" in helper
    assert 'raise RuntimeError(f"Section did not expand: {label}")' in helper


def test_assert_helper_block_exposes_calendar_surface_detection():
    helper = generate_page_methods.ASSERT_HELPER_BLOCK
    assert "def _is_day_number_label(value):" in helper
    assert "def _calendar_surface_scope(page, container_unique=None):" in helper


def test_assert_helper_block_scopes_icon_clicks_to_active_modal_first():
    helper = generate_page_methods.ASSERT_HELPER_BLOCK
    assert "for scope in _interaction_scopes(page, label=label):" in helper
    assert "locator = scope.locator(selector).first" in helper
    assert 'locator = scope.get_by_role("button", name=re.compile(re.escape(token), re.I)).first' in helper


def test_icon_click_methods_prefer_smartai_before_generic_icon_heuristics():
    code = generate_page_methods.build_method(
        {
            "label_text": "From calendar icon",
            "ocr_type": "iconbutton",
            "intent": "from_calendar_icon_action",
            "unique_name": "zing_wfh_from_calendar_icon_iconbutton_from_calendar_icon_action",
        },
        {},
    )
    smartai_idx = code.find("locator = page.smartAI('zing_wfh_from_calendar_icon_iconbutton_from_calendar_icon_action')")
    icon_idx = code.find("if _click_icon(page, 'From calendar icon'")
    assert smartai_idx != -1
    assert icon_idx != -1
    assert smartai_idx < icon_idx


def test_suspicious_calendar_icon_methods_try_icon_heuristics_before_smartai():
    code = generate_page_methods.build_method(
        {
            "label_text": "Birthdays & Anniversaries",
            "ocr_type": "iconbutton",
            "intent": "from_calendar_icon_action",
            "unique_name": "zing_wfh_birthdays_anniversaries_iconbutton_from_calendar_icon_action",
            "get_by_text": "From calendar icon",
            "variant_text": "From calendar icon",
            "icon_family": "calendar",
            "dom_accessible_name": "Birthdays & Anniversaries",
            "y": -102.9,
        },
        {},
    )
    smartai_idx = code.find("locator = page.smartAI('zing_wfh_birthdays_anniversaries_iconbutton_from_calendar_icon_action')")
    icon_idx = code.find("if _click_icon(page,")
    assert smartai_idx != -1
    assert icon_idx != -1
    assert icon_idx < smartai_idx


def test_generic_container_calendar_icon_methods_try_icon_heuristics_before_smartai():
    code = generate_page_methods.build_method(
        {
            "label_text": "From calendar icon",
            "ocr_type": "iconbutton",
            "intent": "from_calendar_icon_action",
            "unique_name": "zing_wfh_from_calendar_icon_iconbutton_from_calendar_icon_action",
            "css_selector": "div.muigrid-root",
            "dom_accessible_name": "Birthdays & Anniversaries",
            "icon_family": "calendar",
        },
        {},
    )
    smartai_idx = code.find("locator = page.smartAI('zing_wfh_from_calendar_icon_iconbutton_from_calendar_icon_action')")
    icon_idx = code.find("if _click_icon(page,")
    assert smartai_idx != -1
    assert icon_idx != -1
    assert icon_idx < smartai_idx


def test_calendar_icon_methods_try_related_input_before_other_fallbacks():
    code = generate_page_methods.build_method(
        {
            "label_text": "From calendar icon",
            "ocr_type": "iconbutton",
            "intent": "from_calendar_icon_action",
            "unique_name": "zing_wfh_from_calendar_icon_iconbutton_from_calendar_icon_action",
            "related_input_label": "dd/mm/yyyy",
        },
        {},
    )
    input_idx = code.find("target_page = _find_frame_for_field(page, placeholder='dd/mm/yyyy') or page")
    role_idx = code.find('locator = page.get_by_role("button", name=')
    assert input_idx != -1
    assert role_idx != -1
    assert input_idx < role_idx


def test_calendar_icon_methods_fallback_to_standard_date_placeholders_when_related_input_missing():
    code = generate_page_methods.build_method(
        {
            "label_text": "From calendar icon",
            "ocr_type": "iconbutton",
            "intent": "from_calendar_icon_action",
            "unique_name": "zing_wfh_from_calendar_icon_iconbutton_from_calendar_icon_action",
            "icon_family": "calendar",
        },
        {},
    )
    assert "target_page = _find_frame_for_field(page, placeholder='dd/mm/yyyy') or page" in code
    assert "target_page = _find_frame_for_field(page, placeholder='mm/dd/yyyy') or page" in code


def test_numeric_click_methods_use_calendar_date_helper_when_calendar_is_open():
    code = generate_page_methods.build_method(
        {
            "label_text": "5",
            "ocr_type": "iconbutton",
            "intent": "5_action",
            "unique_name": "zingboard1_5_iconbutton_5_action",
        },
        {},
    )
    assert "if _is_day_number_label('5') and _calendar_surface_scope(page) is not None:" in code
    assert "select_calendar_date(page, '5')" in code


def test_input_methods_use_fill_locator_for_smart_ai_wrappers():
    code = generate_page_methods.build_method(
        {
            "label_text": "Password",
            "ocr_type": "input",
            "unique_name": "zing3_password_textbox_password_field",
        },
        {},
    )
    assert "_fill_locator(locator, value)" in code
    assert "target = _editable_locator(locator)" in generate_page_methods._assert_method_for_input(
        "zing3_password_textbox_password_field", "enter_password"
    )


def test_password_input_methods_prefer_password_locator_before_smart_ai():
    code = generate_page_methods.build_method(
        {
            "label_text": "Password",
            "ocr_type": "input",
            "unique_name": "zing3_password_textbox_password_field",
        },
        {},
    )
    assert "_find_password_locator(page, 'Password', placeholder='')" in code
    assert "locator = page.smartAI('zing3_password_textbox_password_field')" in code
    assert code.find("_find_password_locator(page, 'Password', placeholder='')") < code.find(
        "locator = page.smartAI('zing3_password_textbox_password_field')"
    )
    assert "_enter_value(page, 'Password', value, placeholder='')" in code
    assert "_find_password_locator(page, 'Password', placeholder='')" in generate_page_methods._assert_method_for_input(
        "zing3_password_textbox_password_field",
        "enter_password",
        password_label="Password",
        password_placeholder="",
    )


def test_assert_helper_block_strengthens_password_field_disambiguation():
    helper = generate_page_methods.ASSERT_HELPER_BLOCK
    assert "label_tokens = [" in helper
    assert "precise_candidates = []" in helper
    assert 'scoped_page.locator("label").filter(has_text=password_re).locator(' in helper
    assert "generic_candidates = []" in helper
    assert 'if label_tokens and not any(token in haystack for token in label_tokens):' in helper
    assert 'el.getAttribute("autocomplete") || ""' in helper


def test_named_password_input_methods_use_shared_disambiguating_password_locator():
    code = generate_page_methods.build_method(
        {
            "label_text": "New Password",
            "ocr_type": "input",
            "unique_name": "zing_pswd_new_password_textbox_new_password_field",
        },
        {},
    )
    assert "_find_password_locator(page, 'New Password', placeholder='')" in code
    assert code.find("_find_password_locator(page, 'New Password', placeholder='')") < code.find(
        "locator = page.smartAI('zing_pswd_new_password_textbox_new_password_field')"
    )


def test_before_enrichment_static_entries_are_kept_for_page_method_generation():
    entry = {
        "label_text": "Contact Details",
        "ocr_type": "label",
        "unique_name": "zing_contact_contact_details_label_contact_details_info",
        "__smartai_source_prefix": "before_enrichment",
    }
    assert generate_page_methods._action_type(entry) == "static"
    assert generate_page_methods._should_keep_entry_for_page_methods(entry, "static") is True


def test_non_before_enrichment_noisy_static_entries_are_still_skipped():
    entry = {
        "label_text": "Contact Details",
        "ocr_type": "label",
        "unique_name": "zing_contact_contact_details_label_contact_details_info",
    }
    assert generate_page_methods._action_type(entry) == "static"
    assert generate_page_methods._should_keep_entry_for_page_methods(entry, "static") is False


def test_assert_helper_block_strengthens_profile_avatar_candidate_scoring():
    helper = generate_page_methods.ASSERT_HELPER_BLOCK
    assert "if x >= viewport_width * 0.88:" in helper
    assert "if len(text) == 1 and text.isalpha():" in helper
    assert "if abs(w - h) <= 10 and w >= 24 and h >= 24:" in helper
    assert 'if any(token in haystack for token in ("group", "organogram", "people", "users", "team")):' in helper
    assert 'if "svg" in haystack and len(text) <= 1:' in helper
    assert "if best is not None and best_score >= 120:" in helper


def test_profile_icon_methods_skip_smart_ai_and_use_avatar_fallbacks():
    code = generate_page_methods.build_method(
        {
            "label_text": "Profile Icon",
            "ocr_type": "iconbutton",
            "intent": "profile_icon_action",
            "aria_label": "Profile Icon",
            "unique_name": "zingboard1_profile_icon_iconbutton_profile_icon_action",
        },
        {},
    )
    click_method = code.split("def assert_click_profile_icon_visible", 1)[0]
    assert "if _try_profile_icon_candidate(page):" in click_method
    assert "_click_icon(page, 'profile avatar'" in click_method
    assert "_click_by_label(page, 'profile avatar')" in click_method
    assert "page.smartAI('zingboard1_profile_icon_iconbutton_profile_icon_action')" not in click_method
