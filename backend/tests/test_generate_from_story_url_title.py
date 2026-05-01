import re
import sys
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from apis.generate_from_story import inject_url_title_expectations


def test_url_title_expectations_same_tab():
    story = (
        'Given I am on the dashboard\n'
        'Then I should navigate to "https://example.com/dashboard"\n'
        'And page title should be "Dashboard - Testify"\n'
    )
    code = (
        "from playwright.sync_api import expect\n\n"
        "def test_example(page):\n"
        "    page.goto(\"https://example.com\")\n"
        "    click_login(page)\n"
    )
    out = inject_url_title_expectations(code, story)
    assert 'expect(page).to_have_url("https://example.com/dashboard")' in out
    assert 'expect(page).to_have_title("Dashboard - Testify")' in out
    assert "active_page" not in out


def test_url_title_expectations_popup():
    story = (
        "When I click the report link in a new tab\n"
        "Then redirected to https://example.com/dashboard\n"
        "And verify title Dashboard\n"
    )
    code = (
        "from playwright.sync_api import expect\n\n"
        "def test_popup(page):\n"
        "    click_report_link(page)\n"
    )
    out = inject_url_title_expectations(code, story)
    assert "with page.context.expect_page()" in out
    assert "new_page = new_page_info.value" in out
    assert "active_page = new_page" in out
    assert "active_page.wait_for_load_state()" in out
    assert 'expect(active_page).to_have_url("https://example.com/dashboard")' in out
    assert "expect(active_page).to_have_title(re.compile(\"Dashboard\"))" in out
    assert re.search(r"^\s*import re\s*$", out, flags=re.MULTILINE)
