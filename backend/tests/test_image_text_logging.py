import os
import sys
import tempfile
from pathlib import Path

import pytest

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

_DB_DIR = Path(tempfile.mkdtemp())
_DB_PATH = _DB_DIR / "image_text_logging.db"
os.environ["DATABASE_URL"] = f"sqlite:///{_DB_PATH}"

from database import session as db_session  # noqa: E402
from database.models import Organization, Project, User, OrganizationMember  # noqa: E402
from apis.projects_api import _ensure_project_structure  # noqa: E402
from utils.project_paths import build_project_context  # noqa: E402
from apis import image_text_api  # noqa: E402


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


def _flush_handlers():
    for handler in list(image_text_api.logger.handlers):
        try:
            handler.flush()
        except Exception:
            pass


def test_project_scoped_logs_are_separate(db):
    user = _create_user(db, "Org A", "logs@example.com")
    project_a = _create_project(db, "Org A", "Project A", created_by=user.id)
    project_b = _create_project(db, "Org A", "Project B", created_by=user.id)

    _ensure_project_structure(project_a)
    _ensure_project_structure(project_b)

    ctx_a = build_project_context(user, project_a.id, db)
    ctx_b = build_project_context(user, project_b.id, db)

    path_a = image_text_api._ensure_project_logger(ctx_a)
    path_b = image_text_api._ensure_project_logger(ctx_b)

    image_text_api.logger.info("log A")
    image_text_api.logger.info("log B")
    _flush_handlers()

    assert path_a != path_b
    assert path_a.exists()
    assert path_b.exists()
