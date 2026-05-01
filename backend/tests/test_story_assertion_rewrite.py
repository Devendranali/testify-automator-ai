import os
import sys
import tempfile
from pathlib import Path


_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

# Ensure DB bootstrap doesn't crash on import in CI/dev.
_DB_DIR = Path(tempfile.mkdtemp())
_DB_PATH = _DB_DIR / "test.db"
os.environ.setdefault("DATABASE_URL", f"sqlite:///{_DB_PATH}")


from apis.generate_from_story import rewrite_pom_text_asserts_to_expect  # noqa: E402


def test_rewrites_heading_text_asserts_to_role_expect():
    story = (
        'When the user clicks on the “What is FundGenie?” menu,\n'
        'Then the page should display the heading “What is FundGenie” along with content.\n'
    )
    code = (
        "def test_positive_feature(page):\n"
        "    page.goto('https://fundsgenie.in/#/homepage')\n"
        "    click_what_is_fundsgenie(page)\n"
        "    assert_what_is_fundsgenie_text(page, 'What is FundGenie')\n"
    )
    rewritten = rewrite_pom_text_asserts_to_expect(code, story)
    assert "assert_what_is_fundsgenie_text" not in rewritten
    assert 'expect(page.get_by_role("heading", name="What is FundGenie")).to_be_visible()' in rewritten
