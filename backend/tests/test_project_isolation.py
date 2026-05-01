import os
import sys
import tempfile
from pathlib import Path

import pytest
import asyncio
from fastapi import HTTPException
from starlette.requests import Request


_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

_DB_DIR = Path(tempfile.mkdtemp())
_DB_PATH = _DB_DIR / "test.db"
os.environ["DATABASE_URL"] = f"sqlite:///{_DB_PATH}"

from database import session as db_session  # noqa: E402
from database.models import Organization, Project, User, OrganizationMember  # noqa: E402
from apis.projects_api import _ensure_project_structure  # noqa: E402
from apis.report_api import list_reports, report_assets  # noqa: E402
from apis.metrics_api import get_metrics_store  # noqa: E402
from apis.run_test_api import report as run_report  # noqa: E402
from apis.visualizer_api import _list_project_visualizations  # noqa: E402
from apis.enrichment_api import set_page_name as enrich_set_page  # noqa: E402
from apis.url_enrichment import set_page_name as url_set_page  # noqa: E402
from apis.manual_enrichment_api import set_page_name as manual_set_page  # noqa: E402
import auth  # noqa: E402


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


def _auth_token(user: User) -> str:
    return auth.create_access_token(
        data={"sub": user.email, "uid": user.id, "org": user.organization, "org_id": user.organization_id}
    )


def _request_with_bearer(token: str) -> Request:
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/reports",
        "headers": [(b"authorization", f"Bearer {token}".encode("utf-8"))],
        "query_string": b"",
        "scheme": "http",
        "root_path": "",
    }
    return Request(scope)


def test_reports_are_project_scoped(db):
    user = _create_user(db, "Org A", "user-a@example.com")
    project_a = _create_project(db, "Org A", "Project A", created_by=user.id)
    project_b = _create_project(db, "Org A", "Project B", created_by=user.id)

    paths_a = _ensure_project_structure(project_a)
    _ensure_project_structure(project_b)

    src_a = Path(paths_a["src_dir"])
    report_dir_a = src_a / "allure-report"
    report_dir_a.mkdir(parents=True, exist_ok=True)
    index_a = report_dir_a / "index.html"
    index_a.write_text("<html>A</html>", encoding="utf-8")

    token = _auth_token(user)
    request = _request_with_bearer(token)
    reports_a = list_reports(project_id=project_a.id, db=db, request=request)
    reports_b = list_reports(project_id=project_b.id, db=db, request=request)

    assert any(r["type"] == "allure" for r in reports_a["reports"])
    assert reports_b["reports"] == []
    assert f"{project_a.id}-" in reports_a["reports"][0]["path"]

    with pytest.raises(HTTPException) as exc:
        report_assets("index.html", project_id=project_b.id, db=db, request=request)
    assert exc.value.status_code in (403, 404)


def test_cross_org_project_access_blocked(db):
    user_a = _create_user(db, "Org A", "user-a2@example.com")
    user_b = _create_user(db, "Org B", "user-b2@example.com")
    project_b = _create_project(db, "Org B", "Project B 2", created_by=user_b.id)

    with pytest.raises(HTTPException) as exc:
        get_metrics_store(project_id=project_b.id, db=db, current_user=user_a)
    assert exc.value.status_code in (403, 404)

    with pytest.raises(HTTPException) as exc:
        run_report(project_id=project_b.id, db=db, current_user=user_a)
    assert exc.value.status_code in (403, 404)

    with pytest.raises(HTTPException) as exc:
        _list_project_visualizations(project_b.id, db, user_a)
    assert exc.value.status_code in (403, 404)


def test_enrichment_endpoints_reject_other_org(db):
    user_a = _create_user(db, "Org A", "user-a3@example.com")
    user_b = _create_user(db, "Org B", "user-b3@example.com")
    project_b = _create_project(db, "Org B", "Project B 3", created_by=user_b.id)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(enrich_set_page(req=type("Req", (), {"page_name": "x"})(), project_id=project_b.id, db=db, current_user=user_a))
    assert exc.value.status_code in (403, 404)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(url_set_page(req=type("Req", (), {"page_name": "x"})(), project_id=project_b.id, db=db, current_user=user_a))
    assert exc.value.status_code in (403, 404)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(manual_set_page(req=type("Req", (), {"page_name": "x"})(), project_id=project_b.id, db=db, current_user=user_a))
    assert exc.value.status_code in (403, 404)
