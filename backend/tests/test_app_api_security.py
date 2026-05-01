import os
import sys
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

_DB_DIR = Path(tempfile.mkdtemp())
_DB_PATH = _DB_DIR / "app_api_security.db"
os.environ["DATABASE_URL"] = f"sqlite:///{_DB_PATH}"

from database import session as db_session  # noqa: E402
from database.models import Organization, Project, User, OrganizationMember  # noqa: E402
from apis.projects_api import _ensure_project_structure  # noqa: E402
import auth  # noqa: E402
from app.api import app  # noqa: E402


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


def _create_project(db, user: User, project_name: str) -> Project:
    org = Organization.get_or_create(db, user.organization)
    project = Project(
        organization=org.name,
        organization_id=org.id,
        created_by=user.id,
        project_name=_unique_project_name(project_name),
        project_key=Project.normalized_key(project_name),
        framework="Playwright",
        language="Python",
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def _auth_headers(user: User) -> dict:
    token = auth.create_access_token(
        data={"sub": user.email, "uid": user.id, "org": user.organization, "org_id": user.organization_id}
    )
    return {"Authorization": f"Bearer {token}"}


def test_generate_report_rejects_path_traversal(db, monkeypatch):
    user = _create_user(db, "Org A", "user@app.example.com")
    project = _create_project(db, user, "Project A")
    _ensure_project_structure(project)

    client = TestClient(app)

    def _fail_run(*args, **kwargs):
        raise AssertionError("subprocess.run should not be called for invalid paths")

    monkeypatch.setattr("app.api.subprocess.run", _fail_run)

    resp = client.get(
        "/tests/report",
        params={"project_id": project.id, "test": "../../etc/passwd"},
        headers=_auth_headers(user),
    )
    assert resp.status_code in (400, 403)


def test_generate_report_rejects_absolute_path(db, monkeypatch, tmp_path):
    user = _create_user(db, "Org A", "user2@app.example.com")
    project = _create_project(db, user, "Project B")
    _ensure_project_structure(project)

    client = TestClient(app)

    def _fail_run(*args, **kwargs):
        raise AssertionError("subprocess.run should not be called for invalid paths")

    monkeypatch.setattr("app.api.subprocess.run", _fail_run)

    abs_path = (tmp_path / "test_abs.py").resolve()
    resp = client.get(
        "/tests/report",
        params={"project_id": project.id, "test": str(abs_path)},
        headers=_auth_headers(user),
    )
    assert resp.status_code in (400, 403)


def test_generate_report_accepts_valid_test(db, monkeypatch):
    user = _create_user(db, "Org A", "user3@app.example.com")
    project = _create_project(db, user, "Project C")
    project_paths = _ensure_project_structure(project)
    src_root = Path(project_paths["src_dir"])
    tests_dir = src_root / "tests"
    tests_dir.mkdir(parents=True, exist_ok=True)
    test_file = tests_dir / "test_ok.py"
    test_file.write_text("def test_ok():\n    assert True\n", encoding="utf-8")

    def _fake_run(*args, **kwargs):
        class _Result:
            returncode = 0
            stdout = ""
            stderr = ""
        return _Result()

    monkeypatch.setattr("app.api.subprocess.run", _fake_run)
    monkeypatch.setattr("app.api.build_allure_generate_cmd", lambda results, out: ["allure", "generate"])

    client = TestClient(app)
    resp = client.get(
        "/tests/report",
        params={"project_id": project.id, "test": "tests/test_ok.py"},
        headers=_auth_headers(user),
    )
    assert resp.status_code == 200
    assert "report_url" in resp.json()


def test_run_all_tests_returns_report_url(db, monkeypatch):
    user = _create_user(db, "Org A", "user4@app.example.com")
    project = _create_project(db, user, "Project D")
    project_paths = _ensure_project_structure(project)
    src_root = Path(project_paths["src_dir"])
    tests_dir = src_root / "tests"
    tests_dir.mkdir(parents=True, exist_ok=True)
    (tests_dir / "test_ok.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")

    def _fake_run(*args, **kwargs):
        class _Result:
            returncode = 0
            stdout = ""
            stderr = ""
        return _Result()

    monkeypatch.setattr("app.api.subprocess.run", _fake_run)
    monkeypatch.setattr("app.api.build_allure_generate_cmd", lambda results, out: ["allure", "generate"])

    client = TestClient(app)
    resp = client.get(
        "/tests/run",
        params={"project_id": project.id},
        headers=_auth_headers(user),
    )
    assert resp.status_code == 200
    assert resp.json().get("report_url") == f"/reports/{project.id}/all/index.html"
