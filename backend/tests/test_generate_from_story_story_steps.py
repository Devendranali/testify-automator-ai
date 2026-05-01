import sys
from pathlib import Path


_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from apis.generate_from_story import (  # noqa: E402
    _test_filename_for_key,
    inject_missing_pom_fallbacks,
    _apply_markers_to_function_block,
    _extract_story_steps_structured,
    _clean_func_body_for_story,
    _replace_mismatched_input_methods,
    _map_generic_helpers_to_pom,
    _qualify_pom_method_calls,
    _simplify_page_method_alias_calls,
)
from apis import generate_from_story as generate_from_story_module  # noqa: E402
from database.session import session_scope  # noqa: E402


def test_unique_test_filename_is_deterministic():
    assert _test_filename_for_key(10, 1, "ui") == "test_10_001_ui.py"
    assert _test_filename_for_key(10, 1, "ui") == _test_filename_for_key(10, 1, "ui")


def test_missing_pom_fallbacks_add_marker():
    code = 'raise RuntimeError("Missing POM method for click \'Save\'")\n'
    rewritten, fallback_used = inject_missing_pom_fallbacks(code, "Then click Save")
    assert fallback_used is True
    assert "get_by_role" in rewritten
    with session_scope() as db:
        updated = _apply_markers_to_function_block(
            "def test_example(page):\n    assert True\n",
            "test_example",
            0,
            db,
            user_story="story",
            test_type="ui",
            fallback_used=True,
        )
    assert "@pytest.mark.fallback_used" in updated


def test_story_steps_extract_explicit_wait_for_page_load():
    steps = _extract_story_steps_structured(
        'When I click "Login" button\nAnd I wait till the page loaded\nThen I should see "Dashboard"'
    )
    assert [step.action for step in steps] == ["click", "wait_for_page_load", "verify_text"]


def test_story_steps_extract_unquoted_profile_icon_target():
    steps = _extract_story_steps_structured(
        "When I click Login button\nAnd I wait till the page loaded\nAnd I click on Profile Icon"
    )
    assert [step.action for step in steps] == ["click", "wait_for_page_load", "click"]
    assert steps[2].value == "Profile"


def test_story_steps_extract_wait_target_from_same_line():
    steps = _extract_story_steps_structured(
        'When I click "Login" button\nAnd I wait until page is loaded and "Close" button is visible in popup\nAnd I click on Profile Icon'
    )
    assert [step.action for step in steps] == ["click", "wait_for_page_load", "click"]
    assert steps[1].value == "Close"


def test_clean_func_body_injects_page_wait_only_when_story_requests_it():
    body = (
        'click_login(page)\n'
        'click_icon(page, "Close")\n'
        'click_profile_icon(page)\n'
    )
    story_with_wait = 'When I click "Login" button\nAnd I wait till the page loaded\nWhen I click "Close" button\nAnd I click "Profile" avatar'
    story_without_wait = 'When I click "Login" button\nWhen I click "Close" button\nAnd I click "Profile" avatar'

    with_wait = _clean_func_body_for_story(body, story_with_wait)
    without_wait = _clean_func_body_for_story(body, story_without_wait)

    assert '_wait_for_ui_ready(page, expected_texts=["Close", "Profile"])' in with_wait
    assert '_wait_for_ui_ready(page' not in without_wait


def test_clean_func_body_rewrites_raw_load_wait_to_ui_ready_wait():
    body = (
        'click_login(page)\n'
        'page.wait_for_load_state("load")\n'
        'click_icon(page, "Close")\n'
        'click_profile_icon(page)\n'
    )
    story_with_wait = 'When I click "Login" button\nAnd I wait till the page loaded\nWhen I click "Close" button\nAnd I click "Profile" avatar'

    rewritten = _clean_func_body_for_story(body, story_with_wait)

    assert 'page.wait_for_load_state("load")' not in rewritten
    assert '_wait_for_ui_ready(page, expected_texts=["Close", "Profile"])' in rewritten


def test_clean_func_body_uses_wait_target_from_same_line_and_next_step():
    body = (
        'click_login(page)\n'
        'click_icon(page, "Close")\n'
        'click_profile_icon(page)\n'
    )
    story = 'When I click "Login" button\nAnd I wait until page is loaded and "Close" button is visible in popup\nAnd I click on Profile Icon'

    rewritten = _clean_func_body_for_story(body, story)

    assert '_wait_for_ui_ready(page, expected_texts=["Close", "Profile"])' in rewritten


def test_clean_func_body_removes_duplicate_visibility_assertion_after_explicit_wait():
    body = (
        'click_login(page)\n'
        '_wait_for_ui_ready(page, expected_texts=["Close"])\n'
        'expect(page.get_by_role("button", name="Close")).to_be_visible()\n'
        'click_icon(page, "Close")\n'
    )
    story = 'When I click "Login" button\nAnd I wait until page is loaded and "Close" button is visible in popup\nAnd I click on "Close" button in popup'

    rewritten = _clean_func_body_for_story(body, story)

    assert '_wait_for_ui_ready(page, expected_texts=["Close"])' in rewritten
    assert 'expect(page.get_by_role("button", name="Close")).to_be_visible()' not in rewritten


def test_clean_func_body_removes_single_quoted_networkidle_and_following_visibility_assertion():
    body = (
        'click_login(page)\n'
        '_wait_for_ui_ready(page, expected_texts=["Close"])\n'
        "page.wait_for_load_state('networkidle')\n"
        'expect(page.get_by_role("button", name="Close")).to_be_visible()\n'
        'click_icon(page, "Close")\n'
    )
    story = 'When I click "Login" button\nAnd I wait until page is loaded and "Close" button is visible in popup\nAnd I click on "Close" button in popup'

    rewritten = _clean_func_body_for_story(body, story)

    assert "_wait_for_ui_ready(page, expected_texts=[\"Close\"])" in rewritten
    assert "page.wait_for_load_state('networkidle')" not in rewritten
    assert 'expect(page.get_by_role("button", name="Close")).to_be_visible()' not in rewritten


def test_clean_func_body_removes_generated_wait_comment_and_following_wait_sequence():
    body = (
        'click_login(page)\n'
        '_wait_for_ui_ready(page, expected_texts=["Close"])\n'
        '# Wait until page is loaded and "Close" button is visible in popup\n'
        'page.wait_for_load_state("networkidle")\n'
        'expect(page.get_by_role("button", name="Close")).to_be_visible()\n'
        'click_icon(page, "Close")\n'
    )
    story = 'When I click "Login" button\nAnd I wait until page is loaded and "Close" button is visible in popup\nAnd I click on "Close" button in popup'

    rewritten = _clean_func_body_for_story(body, story)

    assert '_wait_for_ui_ready(page, expected_texts=["Close"])' in rewritten
    assert '# Wait until page is loaded and "Close" button is visible in popup' not in rewritten
    assert 'page.wait_for_load_state("networkidle")' not in rewritten
    assert 'expect(page.get_by_role("button", name="Close")).to_be_visible()' not in rewritten


def test_generated_runner_click_button_routes_launcher_labels_to_click_icon_first():
    source = Path(generate_from_story_module.__file__).read_text(encoding="utf-8")
    assert 'launcher_tokens = ("9 dot", "9 dots", "dot menu", "dots menu", "app launcher", "launcher", "grid menu", "waffle menu")' in source


def test_replace_mismatched_input_methods_prefers_exact_story_field_over_broader_email_match():
    story = 'And I enter "user@example.com" in the Email field'
    code = '    enter_alternative_email(page, "user@example.com")\n'
    method_map = {
        "profile": [
            "def enter_email(page, value):",
            "def enter_alternative_email(page, value):",
        ]
    }

    rewritten = _replace_mismatched_input_methods(code, story, method_map)

    assert 'enter_email(page, "user@example.com")' in rewritten
    assert "enter_alternative_email" not in rewritten


def test_map_generic_helpers_to_pom_does_not_drift_email_to_alternative_email():
    code = '    fill_text(page, "Email", "user@example.com")\n'
    method_map = {
        "profile": [
            "def enter_email(page, value):",
            "def enter_alternative_email(page, value):",
        ]
    }

    rewritten = _map_generic_helpers_to_pom(code, method_map)

    assert 'enter_email(page, "user@example.com")' in rewritten
    assert "enter_alternative_email" not in rewritten


def test_map_generic_helpers_to_pom_keeps_generic_fill_when_only_broader_email_method_exists():
    code = '    fill_text(page, "Email", "user@example.com")\n'
    method_map = {
        "profile": [
            "def enter_alternative_email(page, value):",
        ]
    }

    rewritten = _map_generic_helpers_to_pom(code, method_map)

    assert 'fill_text(page, "Email", "user@example.com")' in rewritten
    assert "enter_alternative_email" not in rewritten





def test_generated_runner_fill_text_prefers_active_modal_scopes_before_page():
    source = Path(generate_from_story_module.__file__).read_text(encoding="utf-8")
    assert "dialog[open], [role='dialog'], [role='alertdialog'], [aria-modal='true'], aside[aria-modal='true']" in source
    assert "scope.get_by_role(\"textbox\", name=label, exact=True).count() > 0" in source
    assert "target = _find_frame_for_field(page, label=label) or page" in source


def test_qualify_pom_method_calls_uses_module_aliases_for_page_methods():
    code = (
        "from pages.zing_wfh_page_methods import *\n"
        "from pages.zingboard1_page_methods import *\n"
        "\n"
        "click_from_calendar_icon(page)\n"
        "select_calendar_date_offset(page, 2)\n"
        "click_cancel(page)\n"
    )
    method_map = {
        "zing_wfh": [
            "def click_from_calendar_icon(page):",
            "def select_calendar_date_offset(page, offset_days, container_unique=None):",
            "def click_cancel(page):",
        ],
        "zingboard1": [
            "def click_apply_work_from_home(page):",
            "def select_calendar_date_offset(page, offset_days, container_unique=None):",
            "def click_cancel(page):",
        ],
    }

    rewritten = _qualify_pom_method_calls(code, method_map, force_page_methods_style=True)

    assert "_pm_zing_wfh.click_from_calendar_icon(page)" in rewritten
    assert "_pm_zing_wfh.select_calendar_date_offset(page, 2)" in rewritten
    assert "_pm_zing_wfh.click_cancel(page)" in rewritten


def test_rewrite_calendar_popup_numeric_click_uses_same_module_as_calendar_icon():
    code = (
        "_pm_zing_wfh.click_from_calendar_icon(page)\n"
        "_pm_zingboard1.click_5(page)\n"
        "_pm_zing_wfh.click_cancel(page)\n"
    )

    rewritten = generate_from_story_module._rewrite_calendar_popup_numeric_clicks(code)

    assert "_pm_zing_wfh.click_from_calendar_icon(page)" in rewritten
    assert "_pm_zing_wfh.select_calendar_date(page, \"5\")" in rewritten
    assert "_pm_zingboard1.click_5(page)" not in rewritten


def test_rewrite_wfh_calendar_steps_for_runner_keeps_calendar_click_steps():
    code = (
        "click_apply_work_from_home(page)\n"
        "click_from_calendar_icon(page)\n"
        "select_calendar_date(page, \"5\")\n"
        "click_cancel(page)\n"
    )

    rewritten = generate_from_story_module._rewrite_wfh_calendar_steps_for_runner(code)

    assert "click_from_calendar_icon(page)" in rewritten
    assert "select_calendar_date(page, \"5\")" in rewritten
    assert '# Normalized from story step: click "5" in the calendar popup' not in rewritten
    assert "ensure_work_from_home_section(page)" not in rewritten
    assert "enter_from(page, _calendar_day_string(\"5\"))" not in rewritten


def test_rewrite_toggle_ensure_calls_prefers_non_clicking_assertion_for_next_step():
    code = (
        "page.zing_board.click_apply_work_from_home()\n"
        "page.zing_board.ensure_work_from_home_section()\n"
        "page.zing_wfh.click_from_calendar_icon()\n"
    )
    method_map = {
        "zing_board": [
            "def click_apply_work_from_home(page):",
            "def ensure_work_from_home_section(page):",
        ],
        "zing_wfh": [
            "def click_from_calendar_icon(page):",
            "def assert_click_from_calendar_icon_visible(page, timeout: int = 6000):",
        ],
    }

    rewritten = generate_from_story_module._rewrite_toggle_ensure_calls(code, method_map)

    assert "ensure_work_from_home_section" not in rewritten
    assert "assert_click_from_calendar_icon_visible(page)" in rewritten


def test_rewrite_toggle_ensure_calls_prefers_field_assertion_before_calendar_icon():
    code = (
        "page.zing_board.click_apply_work_from_home()\n"
        "page.zing_board.ensure_work_from_home_section()\n"
        "page.zing_wfh.click_from_calendar_icon()\n"
    )
    method_map = {
        "zing_board": [
            "def click_apply_work_from_home(page):",
            "def ensure_work_from_home_section(page):",
        ],
        "zing_wfh": [
            "def click_from_calendar_icon(page):",
            "def assert_click_from_calendar_icon_visible(page, timeout: int = 6000):",
            "def assert_enter_from_visible(page, timeout: int = 6000):",
        ],
    }

    rewritten = generate_from_story_module._rewrite_toggle_ensure_calls(code, method_map)

    assert "ensure_work_from_home_section" not in rewritten
    assert "assert_enter_from_visible(page)" in rewritten
    assert "assert_click_from_calendar_icon_visible(page)" not in rewritten


def test_simplify_page_method_alias_calls_keeps_body_clean_when_method_owner_is_unique():
    code = (
        "_pm_zingboard1.verify_text_visible(page, \"Login\")\n"
        "_pm_zing_login.enter_company_code(page, \"Thousedemo\")\n"
        "_pm_zing_wfh.click_cancel(page)\n"
    )

    rewritten, bindings = _simplify_page_method_alias_calls(code)

    assert bindings == []
    assert 'verify_text_visible(page, "Login")' in rewritten
    assert 'enter_company_code(page, "Thousedemo")' in rewritten
    assert "click_cancel(page)" in rewritten
    assert "_pm_zing_wfh.click_cancel(page)" not in rewritten


def test_simplify_page_method_alias_calls_preserves_ambiguous_shared_method_names():
    code = (
        "_pm_zing_wfh.click_cancel(page)\n"
        "_pm_zing_pswd.click_cancel(page)\n"
    )

    rewritten, bindings = _simplify_page_method_alias_calls(code)

    assert bindings == []
    assert rewritten == code
