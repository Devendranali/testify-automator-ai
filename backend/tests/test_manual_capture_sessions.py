import os
import sys
import tempfile
from pathlib import Path
import asyncio
from types import SimpleNamespace

import pytest

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

_DB_DIR = Path(tempfile.mkdtemp())
_DB_PATH = _DB_DIR / "manual_capture_sessions.db"
os.environ["DATABASE_URL"] = f"sqlite:///{_DB_PATH}"

from database import session as db_session  # noqa: E402
from database.models import Organization, Project, User, OrganizationMember, ImageMetadata  # noqa: E402
from apis import manual_capture  # noqa: E402

Organization.__table__.create(db_session.engine, checkfirst=True)
Project.__table__.create(db_session.engine, checkfirst=True)
User.__table__.create(db_session.engine, checkfirst=True)
OrganizationMember.__table__.create(db_session.engine, checkfirst=True)
ImageMetadata.__table__.create(db_session.engine, checkfirst=True)


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


class DummyPage:
    def __init__(self, url: str = ""):
        self._closed = False
        self.url = url
        self._bindings = {}
        self._handlers = {}
        self.context = None

    async def goto(self, url: str, **_kwargs):
        self.url = url

    async def expose_binding(self, name, fn):
        self._bindings[name] = fn

    async def evaluate(self, js, *args):
        return None

    def on(self, event, handler):
        self._handlers.setdefault(event, []).append(handler)
        return None

    def is_closed(self):
        return self._closed

    async def close(self):
        self._closed = True
        for handler in self._handlers.get("close", []):
            outcome = handler()
            if asyncio.iscoroutine(outcome):
                await outcome


class DummyContext:
    def __init__(self):
        self.closed = False
        self.pages = []
        self._bindings = {}
        self._handlers = {}
        self._init_scripts = []

    async def new_page(self):
        page = DummyPage()
        page.context = self
        self.pages.append(page)
        return page

    async def expose_binding(self, name, fn):
        self._bindings[name] = fn

    async def add_init_script(self, js):
        self._init_scripts.append(js)

    def on(self, event, handler):
        self._handlers.setdefault(event, []).append(handler)

    async def emit_page(self, page: DummyPage):
        page.context = self
        self.pages.append(page)
        for handler in self._handlers.get("page", []):
            outcome = handler(page)
            if asyncio.iscoroutine(outcome):
                await outcome

    async def close(self):
        self.closed = True


class DummyBrowser:
    def __init__(self):
        self.closed = False
        self.context = None

    async def new_context(self, **_kwargs):
        self.context = DummyContext()
        return self.context

    def on(self, event, handler):
        return None

    async def close(self):
        self.closed = True


class DummyChromium:
    async def launch(self, headless=False, slow_mo=0):
        return DummyBrowser()


class DummyPlaywright:
    def __init__(self):
        self.chromium = DummyChromium()
        self.stopped = False

    async def stop(self):
        self.stopped = True


class DummyAsyncPlaywright:
    async def start(self):
        return DummyPlaywright()


def _patch_playwright(monkeypatch):
    monkeypatch.setattr(manual_capture, "async_playwright", lambda: DummyAsyncPlaywright())


@pytest.mark.usefixtures("db")
def test_manual_capture_sessions_isolated(db, monkeypatch):
    user_a = _create_user(db, "Org A", "user-a@example.com")
    user_b = _create_user(db, "Org B", "user-b@example.com")

    project_a = _create_project(db, "Org A", "Project A", created_by=user_a.id)
    project_b = _create_project(db, "Org B", "Project B", created_by=user_b.id)

    _patch_playwright(monkeypatch)
    async def _fake_extract_dom_metadata(page, name):
        return []
    monkeypatch.setattr(manual_capture, "extract_dom_metadata", _fake_extract_dom_metadata)
    monkeypatch.setattr(manual_capture, "match_and_update", lambda ocr, dom, col: [])
    monkeypatch.setattr(manual_capture, "_collection", lambda: object())

    db.add(
        ImageMetadata(
            project_id=project_a.id,
            page_name="page_a",
            image_name="page_a.png",
            metadata_json=[{"metadata": {"label_text": "A"}}],
        )
    )
    db.add(
        ImageMetadata(
            project_id=project_b.id,
            page_name="page_b",
            image_name="page_b.png",
            metadata_json=[{"metadata": {"label_text": "B"}}],
        )
    )
    db.commit()
    request = SimpleNamespace(base_url="http://backend.local/")

    async def _run():
        await manual_capture.launch_browser(
            req=manual_capture.LaunchRequest(url="http://a.example", project_id=project_a.id),
            request=request,
            db=db,
            current_user=user_a,
        )
        await manual_capture.launch_browser(
            req=manual_capture.LaunchRequest(url="http://b.example", project_id=project_b.id),
            request=request,
            db=db,
            current_user=user_b,
        )

        await manual_capture.set_page_name(
            req=manual_capture.PageNameSetRequest(page_name="page_a"),
            project_id=project_a.id,
            db=db,
            current_user=user_a,
        )
        await manual_capture.set_page_name(
            req=manual_capture.PageNameSetRequest(page_name="page_b"),
            project_id=project_b.id,
            db=db,
            current_user=user_b,
        )

        await asyncio.gather(
            manual_capture.capture_from_keyboard(
                req=manual_capture.CaptureRequest(page_name="page_a", project_id=project_a.id),
                project_id=project_a.id,
                db=db,
                current_user=user_a,
            ),
            manual_capture.capture_from_keyboard(
                req=manual_capture.CaptureRequest(page_name="page_b", project_id=project_b.id),
                project_id=project_b.id,
                db=db,
                current_user=user_b,
            ),
        )

        session_a = await manual_capture._get_session(user_a.id, project_a.id)
        session_b = await manual_capture._get_session(user_b.id, project_b.id)

        assert session_a is not session_b
        assert session_a.page is not session_b.page
        assert session_a.current_page_name == "page_a"
        assert session_b.current_page_name == "page_b"
        assert session_a.current_app_domain == "a.example"
        assert session_b.current_app_domain == "b.example"

        await manual_capture.cleanup_session(project_id=project_a.id, db=db, current_user=user_a)
        await manual_capture.cleanup_session(project_id=project_b.id, db=db, current_user=user_b)

    asyncio.run(_run())


@pytest.mark.usefixtures("db")
def test_manual_capture_popup_uses_context_bindings_and_active_page(db, monkeypatch):
    user = _create_user(db, "Org Popup", "popup@example.com")
    project = _create_project(db, "Org Popup", "Popup Project", created_by=user.id)

    _patch_playwright(monkeypatch)
    extracted_urls = []

    async def _fake_extract_dom_metadata(page, name):
        extracted_urls.append((name, page.url))
        return []

    monkeypatch.setattr(manual_capture, "extract_dom_metadata", _fake_extract_dom_metadata)
    monkeypatch.setattr(manual_capture, "match_and_update", lambda ocr, dom, col: [])
    monkeypatch.setattr(manual_capture, "_collection", lambda: object())

    db.add(
        ImageMetadata(
            project_id=project.id,
            page_name="report_page",
            image_name="report_page.png",
            metadata_json=[{"metadata": {"label_text": "Report"}}],
        )
    )
    db.commit()

    request = SimpleNamespace(base_url="http://backend.local/")

    async def _run():
        await manual_capture.launch_browser(
            req=manual_capture.LaunchRequest(url="http://app.example/home", project_id=project.id),
            request=request,
            db=db,
            current_user=user,
        )

        session = await manual_capture._get_session(user.id, project.id)
        assert "getAvailablePages" in session.context._bindings
        assert "sendEnrichmentRequests" in session.context._bindings

        popup = DummyPage(url="http://reports.example/monthly")
        await session.context.emit_page(popup)
        await asyncio.sleep(0)

        source = SimpleNamespace(page=popup)
        result = await session.context._bindings["getAvailablePages"](source)
        assert '"pages": ["report_page"]' in result
        assert session.page is popup
        assert session.current_app_domain == "reports.example"

        await manual_capture.capture_from_keyboard(
            req=manual_capture.CaptureRequest(page_name="report_page", project_id=project.id),
            project_id=project.id,
            db=db,
            current_user=user,
        )

        assert extracted_urls[-1] == ("report_page", "http://reports.example/monthly")

        await manual_capture.cleanup_session(project_id=project.id, db=db, current_user=user)

    asyncio.run(_run())
