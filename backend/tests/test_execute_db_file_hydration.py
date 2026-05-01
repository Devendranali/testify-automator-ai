import sys
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from apis.rag_testcase_runner import _collect_scripts_to_run
from database.models import (
    Organization,
    OrganizationMember,
    Project,
    ProjectFile,
    TestCaseMetadata as DBTestCaseMetadata,
    User,
)
from database.session import SessionLocal, engine


def test_collect_scripts_hydrates_missing_runner_and_test_files_from_db(tmp_path):
    for table in (
        Organization.__table__,
        User.__table__,
        Project.__table__,
        OrganizationMember.__table__,
        ProjectFile.__table__,
        DBTestCaseMetadata.__table__,
    ):
        table.create(bind=engine, checkfirst=True)
    session = SessionLocal()
    try:
        org = Organization(name="Acme", slug="acme", display_name="Acme")
        session.add(org)
        session.flush()

        user = User(
            organization="Acme",
            organization_id=org.id,
            email="user@example.com",
            password_hash="hashed-password",
        )
        session.add(user)
        session.flush()
        OrganizationMember.ensure_member(session, user.id, org.id, role="member")

        project = Project(
            organization="Acme",
            organization_id=org.id,
            created_by=user.id,
            project_name="Website",
            framework="playwright",
            language="python",
        )
        session.add(project)
        session.flush()

        runner_path = "tests/ui_scripts/ui_script_checkout.py"
        test_path = "tests/ui_scripts/test_checkout.py"
        page_methods_path = "pages/checkout_page_methods.py"
        session.add_all(
            [
                ProjectFile(
                    project_id=project.id,
                    path=runner_path,
                    encoding="utf-8",
                    content='RUN_TAGS = {"run_checkout": ["regression"]}\n\n\ndef run_checkout(page):\n    return True\n',
                ),
                ProjectFile(
                    project_id=project.id,
                    path=test_path,
                    encoding="utf-8",
                    content="def test_checkout(page):\n    assert True\n",
                ),
                ProjectFile(
                    project_id=project.id,
                    path=page_methods_path,
                    encoding="utf-8",
                    content="def click_checkout(page):\n    return True\n",
                ),
                DBTestCaseMetadata(
                    project_id=project.id,
                    case_uuid="case-1",
                    test_name="test_checkout",
                    display_name="Checkout",
                    user_story="Checkout story",
                    auto_testcase="1. Open page",
                    test_type="ui",
                    tags=["regression"],
                    markers=[],
                    priority="Low",
                    script_path=test_path,
                    runner_script_path=runner_path,
                ),
            ]
        )
        session.commit()

        scripts_to_run, selected_by_category = _collect_scripts_to_run(
            project=project,
            db=session,
            requested_tags={"ui": ["regression"]},
            use_test_plan=False,
        )

        assert selected_by_category["ui"] == ["regression"]
        assert len(scripts_to_run) == 1
        src_dir, script_file, category = scripts_to_run[0]
        assert category == "ui"
        assert script_file.name == "ui_script_checkout.py"
        assert (src_dir / runner_path).exists()
        assert (src_dir / test_path).exists()
        assert (src_dir / page_methods_path).exists()
    finally:
        session.close()
