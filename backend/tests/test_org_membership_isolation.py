import os
import sys
import tempfile
from pathlib import Path

import pytest
from fastapi import HTTPException


_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

_DB_DIR = Path(tempfile.mkdtemp())
_DB_PATH = _DB_DIR / "test_membership.db"
os.environ["DATABASE_URL"] = f"sqlite:///{_DB_PATH}"

from database import session as db_session  # noqa: E402
from database.models import Organization, Project, User, OrganizationMember  # noqa: E402
from apis import projects_api  # noqa: E402
from apis.testcases_api import list_test_cases  # noqa: E402


Organization.__table__.create(db_session.engine, checkfirst=True)
Project.__table__.create(db_session.engine, checkfirst=True)
User.__table__.create(db_session.engine, checkfirst=True)
OrganizationMember.__table__.create(db_session.engine, checkfirst=True)


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


def test_org_membership_blocks_cross_org_access(db):
    user_a = _create_user(db, "Org A", "user-a@example.com")
    user_b = _create_user(db, "Org B", "user-b@example.com")

    project_a = _create_project(db, "Org A", "Project A", created_by=user_a.id)
    project_b = _create_project(db, "Org B", "Project B", created_by=user_b.id)

    projects_a = projects_api.list_projects(db=db, current_user=user_a)
    assert [p["id"] for p in projects_a["projects"]] == [project_a.id]

    with pytest.raises(HTTPException) as exc:
        projects_api.get_project(project_b.id, db=db, current_user=user_a)
    assert exc.value.status_code in (403, 404)

    with pytest.raises(HTTPException) as exc:
        projects_api.delete_project(project_b.id, db=db, current_user=user_a)
    assert exc.value.status_code in (403, 404)

    with pytest.raises(HTTPException) as exc:
        list_test_cases(project_id=project_b.id, db=db, current_user=user_a)
    assert exc.value.status_code in (403, 404)

    projects_b = projects_api.list_projects(db=db, current_user=user_b)
    assert [p["id"] for p in projects_b["projects"]] == [project_b.id]
