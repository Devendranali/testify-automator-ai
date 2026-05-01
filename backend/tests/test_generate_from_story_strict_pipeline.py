import sys
import re
from pathlib import Path
import asyncio

import pytest

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from database import session as db_session  # noqa: E402
from database.models import (  # noqa: E402
    Organization,
    Project,
    ProjectFile,
    TestCaseMetadata,
    User,
    OrganizationMember,
)
from utils.project_paths import build_project_context  # noqa: E402
from utils.request_context import set_request_context, reset_request_context  # noqa: E402
from apis.generate_from_story import (  # noqa: E402
    generate_test_code_from_methods,
    parse_user_story_to_steps,
    update_testcase,
)
from apis.projects_api import _ensure_project_structure  # noqa: E402
from fastapi import HTTPException  # noqa: E402

Organization.__table__.create(db_session.engine, checkfirst=True)
Project.__table__.create(db_session.engine, checkfirst=True)
User.__table__.create(db_session.engine, checkfirst=True)
OrganizationMember.__table__.create(db_session.engine, checkfirst=True)
ProjectFile.__table__.create(db_session.engine, checkfirst=True)
TestCaseMetadata.__table__.create(db_session.engine, checkfirst=True)


@pytest.fixture()
def db():
    session = db_session.SessionLocal()
    try:
        yield session
    finally:
        session.close()


def _unique_suffix() -> str:
    import uuid

    return uuid.uuid4().hex[:8]


def _unique_email(email: str) -> str:
    if "@" not in email:
        return f"{email}-{_unique_suffix()}@example.com"
    local, domain = email.split("@", 1)
    return f"{local}+{_unique_suffix()}@{domain}"


def _unique_project_name(project_name: str) -> str:
    return f"{project_name} {_unique_suffix()}"


def _create_user(db, org_name: str, email: str) -> User:
    org = Organization.get_or_create(db, org_name)
    user = User(
        organization=org.name,
        organization_id=org.id,
        email=_unique_email(email),
        password_hash="test-hash",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    OrganizationMember.ensure_member(db, user.id, org.id)
    return user


def _create_project(db, org_name: str, project_name: str, created_by: int) -> Project:
    org = Organization.get_or_create(db, org_name)
    project = Project(
        organization=org.name,
        organization_id=org.id,
        created_by=created_by,
        project_name=_unique_project_name(project_name),
        project_key=Project.normalized_key(project_name),
        framework="Playwright",
        language="Python",
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def test_generate_from_story_strict_steps_fundsgenie_order(tmp_path):
    story = """
Given I navigate to https://fundsgenie.com
When I click "What is FundsGenie?"
Then I should see "What is FundsGenie"
And I click "How it works?"
Then I should see "The friendliest way to buy Mutual Funds online"
And I scroll to "Top Rated Funds"
And I click "FAQ"
And I scroll to "Disclaimer: Mutual fund investments are subject to market risks"
Then I should see "Disclaimer: Mutual fund investments are subject to market risks"
""".strip()

    run_folder = tmp_path / "src"
    (run_folder / "pages").mkdir(parents=True, exist_ok=True)
    code, _ = generate_test_code_from_methods(
        user_story=story,
        method_map={},
        page_names=[],
        site_url="",
        run_folder=run_folder,
        project_src_dir=run_folder,
        strict_story_only=True,
        allow_direct_selectors=True,
    )

    assert "def test_story_positive" in code
    assert "def test_story_negative" in code
    assert "def test_story_edge" in code
    assert "assert_enter_" not in code

    def _block(name: str) -> str:
        start = code.find(f"def {name}(")
        assert start != -1
        rest = code[start:]
        end = rest.find("\ndef ", 1)
        if end == -1:
            return rest
        return rest[:end]

    positive = _block("test_story_positive")
    negative = _block("test_story_negative")
    edge = _block("test_story_edge")

    snippets = [
        'page.goto("https://fundsgenie.com")',
        'page.get_by_text("What is FundsGenie?", exact=True).click()',
        'expect(page.get_by_text("What is FundsGenie", exact=True)).to_be_visible()',
        'page.get_by_text("How it works?", exact=True).click()',
        'expect(page.get_by_text("The friendliest way to buy Mutual Funds online", exact=True)).to_be_visible()',
        'page.get_by_text("Top Rated Funds", exact=True).scroll_into_view_if_needed()',
        'page.get_by_text("FAQ", exact=True).click()',
        'page.get_by_text("Disclaimer: Mutual fund investments are subject to market risks", exact=True).scroll_into_view_if_needed()',
        'expect(page.get_by_text("Disclaimer: Mutual fund investments are subject to market risks", exact=True)).to_be_visible()',
    ]

    idx = -1
    for snippet in snippets:
        new_idx = positive.find(snippet)
        assert new_idx != -1
        assert new_idx > idx
        idx = new_idx

    def _normalize_actions(block: str) -> list[str]:
        lines = [l.strip() for l in block.splitlines() if l.strip().startswith(("page.", "expect(", "popup."))]
        normalized = [re.sub(r'"[^"]*"', '""', l) for l in lines]
        return normalized

    assert _normalize_actions(positive) == _normalize_actions(negative)
    assert _normalize_actions(positive) == _normalize_actions(edge)


def test_generate_from_story_strict_rejects_unparseable_line():
    story_line = "This line cannot be parsed by the rules."
    with pytest.raises(HTTPException) as exc:
        parse_user_story_to_steps(story_line, strict=True)
    assert exc.value.status_code == 400
    assert story_line in exc.value.detail


def test_generate_from_story_drag_and_drop_emits_drag_to(tmp_path):
    story = 'When I drag "Item A" to "Bucket B"'
    run_folder = tmp_path / "src"
    (run_folder / "pages").mkdir(parents=True, exist_ok=True)
    code, _ = generate_test_code_from_methods(
        user_story=story,
        method_map={},
        page_names=[],
        site_url="",
        run_folder=run_folder,
        project_src_dir=run_folder,
        strict_story_only=True,
        allow_direct_selectors=True,
    )
    assert ".drag_to(" in code
    assert "Item A" in code
    assert "Bucket B" in code


def test_update_testcase_strict_overwrites_and_matches_story(db):
    user = _create_user(db, "Test Org Strict", "strict@example.com")
    project = _create_project(db, "Test Org Strict", "Strict Project", user.id)
    project_paths = _ensure_project_structure(project)
    run_folder = Path(project_paths["src_dir"])

    ctx = build_project_context(user, project.id, db)
    tokens = set_request_context(project_context=ctx)
    try:
        tests_dir = run_folder / "tests" / "ui_scripts"
        tests_dir.mkdir(parents=True, exist_ok=True)
        test_path = tests_dir / "test_update.py"
        test_path.write_text(
            "def test_update(page):\n    page.get_by_text(\"Old Step\", exact=True).click()\n",
            encoding="utf-8",
        )

        new_story = """
Given I navigate to https://example.com
When I click "First"
And I click "Second"
Then I should see "Second"
""".strip()

        result = asyncio.run(
            update_testcase(
                project_id=project.id,
                test_name="test_update",
                test_file_path="tests/ui_scripts/test_update.py",
                user_story=new_story,
                site_url=None,
                ai_model=None,
                infer_pages=False,
                strict_story_only=True,
                test_type="ui",
                jira_key=None,
                acceptance_criteria=None,
                target_runner_script_path=None,
                db=db,
                current_user=user,
            )
        )
        assert result["status"] == "updated"

        updated_content = test_path.read_text(encoding="utf-8")
        assert "Old Step" not in updated_content
        assert "def test_update_positive" in updated_content
        assert "def test_update_negative" in updated_content
        assert "def test_update_edge" in updated_content
        assert "assert_enter_" not in updated_content
    finally:
        reset_request_context(tokens)
