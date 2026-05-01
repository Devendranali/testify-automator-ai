import asyncio
from pathlib import Path

import pytest

from database import session as db_session
from database.models import Organization, Project, User, OrganizationMember
from apis.projects_api import _ensure_project_structure
from apis import enrichment_api as enrichment


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
        email=f"{_unique_suffix()}_{email}",
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
        project_name=f"{project_name} {_unique_suffix()}",
        project_key=Project.normalized_key(project_name),
        framework="Playwright",
        language="Python",
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def test_enrichment_sessions_isolated_per_user(db, tmp_path):
    user1 = _create_user(db, "Org Enrich", "user1@example.com")
    user2 = _create_user(db, "Org Enrich", "user2@example.com")
    project = _create_project(db, "Org Enrich", "Enrich Project", user1.id)

    src_dir = tmp_path / "src"
    chroma_dir = tmp_path / "chroma"
    src_dir.mkdir(parents=True, exist_ok=True)
    chroma_dir.mkdir(parents=True, exist_ok=True)

    s1 = asyncio.run(
        enrichment._create_or_reset_session(project.id, user1.id, src_dir, chroma_dir)
    )
    s2 = asyncio.run(
        enrichment._create_or_reset_session(project.id, user2.id, src_dir, chroma_dir)
    )

    assert s1 is not s2
    assert s1.user_id != s2.user_id

    async def _set_states():
        async with s1.lock:
            s1.current_page_name = "page_user1"
        async with s2.lock:
            s2.current_page_name = "page_user2"

    asyncio.run(_set_states())
    assert s1.current_page_name == "page_user1"
    assert s2.current_page_name == "page_user2"


def test_concurrent_capture_does_not_crash(db, tmp_path, monkeypatch):
    user = _create_user(db, "Org Enrich", "runner@example.com")
    project = _create_project(db, "Org Enrich", "Enrich Project", user.id)
    project_paths = _ensure_project_structure(project)

    class DummyPage:
        def is_closed(self):
            return False

    dummy_page = DummyPage()

    async def _noop(*_args, **_kwargs):
        return None

    async def _fake_run(*_args, **_kwargs):
        return {"status": "success", "message": "ok", "count": 0}

    monkeypatch.setattr(enrichment, "_refresh_target", _noop)
    monkeypatch.setattr(enrichment, "__snapshot_if_blank", _noop)
    monkeypatch.setattr(enrichment, "_progressive_autoscroll", _noop)
    async def _fake_page_name(_p):
        return "page1"

    monkeypatch.setattr(enrichment, "_derive_page_name", _fake_page_name)
    monkeypatch.setattr(enrichment, "_run_enrichment_for", _fake_run)

    src_dir = Path(project_paths["src_dir"])
    chroma_dir = Path(project_paths["chroma_path"])

    session = asyncio.run(
        enrichment._create_or_reset_session(project.id, user.id, src_dir, chroma_dir)
    )

    async def _prime_session():
        async with session.lock:
            session.page = dummy_page
            session.target = dummy_page
            session.src_directory = src_dir
            session.chroma_path = chroma_dir
            session.current_page_name = "page1"

    asyncio.run(_prime_session())

    async def _run_capture():
        local_db = db_session.SessionLocal()
        try:
            return await enrichment.capture_from_keyboard(
                enrichment.CaptureRequest(),
                project_id=project.id,
                db=local_db,
                current_user=user,
            )
        finally:
            local_db.close()

    async def _run_both():
        return await asyncio.gather(_run_capture(), _run_capture())

    results = asyncio.run(_run_both())
    assert all(r["status"] == "success" for r in results)
