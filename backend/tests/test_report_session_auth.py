import os
import sys
import tempfile
from http.cookies import SimpleCookie
from pathlib import Path

import pytest
from fastapi import HTTPException
from starlette.requests import Request

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

_DB_DIR = Path(tempfile.mkdtemp())
_DB_PATH = _DB_DIR / "report_session.db"
os.environ["DATABASE_URL"] = f"sqlite:///{_DB_PATH}"

from database import session as db_session  # noqa: E402
from database.models import Organization, Project, User, OrganizationMember  # noqa: E402
from apis.report_api import (  # noqa: E402
    _REPORT_SESSION_COOKIE,
    _get_current_user_from_request,
    create_report_session,
)
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


def _create_user(db, org_name: str, email: str) -> User:
    org = Organization.get_or_create(db, org_name)
    user = User(
        organization=org.name,
        organization_id=org.id,
        email=f"{email.split('@', 1)[0]}+{_unique_suffix()}@{email.split('@', 1)[1]}",
        password_hash="test-hash",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    OrganizationMember.ensure_member(db, user.id, org.id)
    return user


def _create_project(db, user: User, project_name: str) -> Project:
    org = Organization.get_or_create(db, user.organization)
    project = Project(
        organization=org.name,
        organization_id=org.id,
        created_by=user.id,
        project_name=f"{project_name} {_unique_suffix()}",
        project_key=Project.normalized_key(project_name),
        framework="Playwright",
        language="Python",
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def _access_token(user: User) -> str:
    return auth.create_access_token(
        data={"sub": user.email, "uid": user.id, "org": user.organization, "org_id": user.organization_id}
    )


def _request(path: str, *, headers: dict[str, str] | None = None, cookies: dict[str, str] | None = None, scheme: str = "http") -> Request:
    raw_headers = []
    for key, value in (headers or {}).items():
        raw_headers.append((key.lower().encode("utf-8"), value.encode("utf-8")))
    if cookies:
        cookie_header = "; ".join(f"{key}={value}" for key, value in cookies.items())
        raw_headers.append((b"cookie", cookie_header.encode("utf-8")))
    scope = {
        "type": "http",
        "method": "GET",
        "path": path,
        "headers": raw_headers,
        "query_string": b"",
        "scheme": scheme,
        "root_path": "",
    }
    return Request(scope)


def _cookie_value(set_cookie_header: str, name: str) -> str:
    cookie = SimpleCookie()
    cookie.load(set_cookie_header)
    return cookie[name].value


def test_create_report_session_sets_secure_cookie_on_https(db):
    user = _create_user(db, "Org A", "reporter@example.com")
    project = _create_project(db, user, "Report Project")
    token = _access_token(user)
    request = _request(
        f"/reports/session/{project.id}",
        headers={
            "authorization": f"Bearer {token}",
            "x-forwarded-proto": "https",
        },
        scheme="http",
    )

    response = create_report_session(project.id, request=request, db=db)

    set_cookie = response.headers["set-cookie"]
    assert f"{_REPORT_SESSION_COOKIE}=" in set_cookie
    assert "HttpOnly" in set_cookie
    assert "Secure" in set_cookie
    assert "SameSite=none" in set_cookie
    assert response.body == b'{"report_url":"/reports/view/%d/"}' % project.id


def test_report_session_cookie_auth_succeeds_for_matching_project(db):
    user = _create_user(db, "Org A", "reporter2@example.com")
    project = _create_project(db, user, "Report Project Two")
    token = _access_token(user)
    create_request = _request(
        f"/reports/session/{project.id}",
        headers={"authorization": f"Bearer {token}"},
    )

    response = create_report_session(project.id, request=create_request, db=db)
    session_cookie = _cookie_value(response.headers["set-cookie"], _REPORT_SESSION_COOKIE)
    report_request = _request(
        f"/reports/view/{project.id}/",
        cookies={_REPORT_SESSION_COOKIE: session_cookie},
    )

    current_user = _get_current_user_from_request(report_request, db, project.id)

    assert current_user.id == user.id


def test_report_session_cookie_rejects_wrong_project(db):
    user = _create_user(db, "Org A", "reporter3@example.com")
    project = _create_project(db, user, "Report Project Three")
    other_project = _create_project(db, user, "Other Project")
    token = _access_token(user)
    create_request = _request(
        f"/reports/session/{project.id}",
        headers={"authorization": f"Bearer {token}"},
    )

    response = create_report_session(project.id, request=create_request, db=db)
    session_cookie = _cookie_value(response.headers["set-cookie"], _REPORT_SESSION_COOKIE)
    report_request = _request(
        f"/reports/view/{other_project.id}/",
        cookies={_REPORT_SESSION_COOKIE: session_cookie},
    )

    with pytest.raises(HTTPException, match="Invalid report session"):
        _get_current_user_from_request(report_request, db, other_project.id)
