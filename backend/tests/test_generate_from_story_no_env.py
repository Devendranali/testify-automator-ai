import sys
from pathlib import Path


_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from apis.generate_from_story import (  # noqa: E402
    _generate_execution_script_for_category,
    _ensure_page_arg_for_pom_calls,
)


def test_generated_runner_does_not_set_project_dir_env(tmp_path):
    test_file = tmp_path / "test_example.py"
    test_file.write_text(
        "from playwright.sync_api import expect\n\n"
        "def test_example(page):\n"
        "    page.goto('https://example.com')\n",
        encoding="utf-8",
    )

    runner_path = _generate_execution_script_for_category(
        category="ui",
        target_dir=tmp_path,
        test_file_path=test_file,
        original_story="Then I should see the homepage",
        site_url="https://example.com",
        import_lines=["import pytest", "from playwright.sync_api import sync_playwright, expect"],
        method_map={},
        ts_index=1,
        fixed_script_name="ui_script_example.py",
        project_root=tmp_path,
    )

    assert runner_path is not None
    content = Path(runner_path).read_text(encoding="utf-8")
    assert 'os.environ["SMARTAI_PROJECT_DIR"]' not in content

def test_ensure_page_arg_for_pom_calls_normalizes_wrapper_style_calls():
    code = (
        "from pages.firrst_page_methods import *\n"
        "from pages.secnd_page_methods import *\n\n"
        "def test_feature(page):\n"
        "    check_delhi()\n"
        "    select_visit_time(\"Afternoon\")\n"
        "    click_proceed()\n"
        "    enter_name(\"abcd\")\n"
        "    enter_age(\"33\")\n"
    )
    method_map = {
        "firrst": [
            "def check_delhi(page)",
            "def select_visit_time(page, value)",
            "def click_proceed(page)",
        ],
        "secnd": [
            "def enter_name(page, value)",
            "def enter_age(page, value)",
        ],
    }

    updated = _ensure_page_arg_for_pom_calls(code, method_map)

    assert "check_delhi(page)" in updated
    assert 'select_visit_time(page, "Afternoon")' in updated
    assert "click_proceed(page)" in updated
    assert 'enter_name(page, "abcd")' in updated
    assert 'enter_age(page, "33")' in updated


def test_qualify_pom_method_calls_converts_page_object_calls_when_forced_to_page_methods_style():
    from apis.generate_from_story import _qualify_pom_method_calls

    code = (
        "def test_feature(page):\n"
        "    page.firrst.select_delhi(True)\n"
        "    page.firrst.select_visit_time(\"Afternoon\")\n"
        "    page.firrst.click_proceed()\n"
        "    page.secnd.enter_name(\"abcd\")\n"
    )
    method_map = {
        "firrst": [
            "def select_delhi(page, value)",
            "def select_visit_time(page, value)",
            "def click_proceed(page)",
        ],
        "secnd": [
            "def enter_name(page, value)",
        ],
    }

    updated = _qualify_pom_method_calls(
        code,
        method_map,
        force_page_methods_style=True,
    )

    assert "select_delhi(page, True)" in updated
    assert 'select_visit_time(page, "Afternoon")' in updated
    assert "click_proceed(page)" in updated
    assert 'enter_name(page, "abcd")' in updated
    assert "page.firrst." not in updated
    assert "page.secnd." not in updated


def test_generated_runner_uses_wrapper_style_page_methods(tmp_path):
    test_file = tmp_path / "test_example.py"
    test_file.write_text(
        "import pytest\n"
        "from pages.firrst_page_methods import *\n"
        "from pages.secnd_page_methods import *\n\n"
        "def test_example(page):\n"
        "    page.firrst.check_delhi()\n"
        "    page.firrst.select_visit_time(\"Afternoon\")\n"
        "    page.secnd.enter_name(\"abcd\")\n",
        encoding="utf-8",
    )

    runner_path = _generate_execution_script_for_category(
        category="ui",
        target_dir=tmp_path,
        test_file_path=test_file,
        original_story="Given I book a ticket",
        site_url="https://example.com",
        import_lines=[
            "import pytest",
            "from playwright.sync_api import sync_playwright, expect",
            "from pages.firrst_page_methods import *",
            "from pages.secnd_page_methods import *",
        ],
        method_map={
            "firrst": [
                "def check_delhi(page)",
                "def select_visit_time(page, value)",
            ],
            "secnd": [
                "def enter_name(page, value)",
            ],
        },
        ts_index=1,
        fixed_script_name="ui_script_example.py",
        project_root=tmp_path,
    )

    assert runner_path is not None
    content = Path(runner_path).read_text(encoding="utf-8")
    assert "check_delhi(page)" in content
    assert 'select_visit_time(page, "Afternoon")' in content
    assert 'enter_name(page, "abcd")' in content
    assert "page.firrst." not in content
    assert "page.secnd." not in content


def test_generated_runner_click_button_handles_readonly_value_controls(tmp_path):
    test_file = tmp_path / "test_example.py"
    test_file.write_text(
        "import pytest\n"
        "def test_example(page):\n"
        "    page.goto('https://example.com')\n",
        encoding="utf-8",
    )

    runner_path = _generate_execution_script_for_category(
        category="ui",
        target_dir=tmp_path,
        test_file_path=test_file,
        original_story='When I click "March 2026" button',
        site_url="https://example.com",
        import_lines=["import pytest", "from playwright.sync_api import sync_playwright, expect"],
        method_map={},
        ts_index=1,
        fixed_script_name="ui_script_example.py",
        project_root=tmp_path,
    )

    content = Path(runner_path).read_text(encoding="utf-8")
    assert '@value=" + _xpath_literal(label) + " and (' in content
    assert "@readonly or @role='button' or @aria-haspopup" in content
    assert "contains(translate(@style,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'cursor: pointer')" in content


def test_generated_runner_click_button_still_prefers_role_buttons(tmp_path):
    test_file = tmp_path / "test_example.py"
    test_file.write_text(
        "import pytest\n"
        "def test_example(page):\n"
        "    page.goto('https://example.com')\n",
        encoding="utf-8",
    )

    runner_path = _generate_execution_script_for_category(
        category="ui",
        target_dir=tmp_path,
        test_file_path=test_file,
        original_story='When I click "Submit" button',
        site_url="https://example.com",
        import_lines=["import pytest", "from playwright.sync_api import sync_playwright, expect"],
        method_map={},
        ts_index=1,
        fixed_script_name="ui_script_example.py",
        project_root=tmp_path,
    )

    content = Path(runner_path).read_text(encoding="utf-8")
    role_idx = content.find('loc = page.get_by_role("button", name=label, exact=True)')
    readonly_idx = content.find('@value=" + _xpath_literal(label) + " and (')
    assert role_idx != -1
    assert readonly_idx != -1
    assert role_idx < readonly_idx


def test_generated_runner_includes_ui_ready_wait_helper_only_when_story_requests_load_wait(tmp_path):
    test_file = tmp_path / "test_example.py"
    test_file.write_text(
        "import pytest\n"
        "def test_example(page):\n"
        "    click_login(page)\n"
        "    click_icon(page, \"Close\")\n"
        "    click_profile_icon(page)\n",
        encoding="utf-8",
    )

    runner_path = _generate_execution_script_for_category(
        category="ui",
        target_dir=tmp_path,
        test_file_path=test_file,
        original_story='When I click "Login" button\nAnd I wait till the page loaded\nWhen I click "Close" button\nAnd I click "Profile" avatar',
        site_url="https://example.com",
        import_lines=["import pytest", "from playwright.sync_api import sync_playwright, expect"],
        method_map={},
        ts_index=1,
        fixed_script_name="ui_script_example.py",
        project_root=tmp_path,
    )

    content = Path(runner_path).read_text(encoding="utf-8")
    assert "def _wait_for_ui_ready(page, expected_texts=None, timeout_ms=None):" in content
    assert "def _expected_target_ready(page, text):" in content
    assert '_wait_for_ui_ready(page, expected_texts=["Close", "Profile"])' in content


def test_generated_runner_omits_ui_ready_wait_helper_when_story_has_no_load_wait(tmp_path):
    test_file = tmp_path / "test_example.py"
    test_file.write_text(
        "import pytest\n"
        "def test_example(page):\n"
        "    click_login(page)\n"
        "    click_icon(page, \"Close\")\n",
        encoding="utf-8",
    )

    runner_path = _generate_execution_script_for_category(
        category="ui",
        target_dir=tmp_path,
        test_file_path=test_file,
        original_story='When I click "Login" button\nWhen I click "Close" button',
        site_url="https://example.com",
        import_lines=["import pytest", "from playwright.sync_api import sync_playwright, expect"],
        method_map={},
        ts_index=1,
        fixed_script_name="ui_script_example.py",
        project_root=tmp_path,
    )

    content = Path(runner_path).read_text(encoding="utf-8")
    assert "def _wait_for_ui_ready(page, expected_texts=None, timeout_ms=None):" not in content
    assert "_wait_for_ui_ready(page" not in content
