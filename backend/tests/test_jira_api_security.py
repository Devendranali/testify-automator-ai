import importlib
import sys
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))


def _clear_modules(*names):
    for name in names:
        if name in sys.modules:
            del sys.modules[name]


def _load_jira_api(monkeypatch, tmp_path, allowed_hosts="jira.example.com"):
    monkeypatch.setenv("JWT_SECRET_KEY", "test-jwt-secret")
    db_path = tmp_path / "jira-security.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    monkeypatch.setenv("ALLOWED_JIRA_HOSTS", allowed_hosts)
    _clear_modules("apis.jira_api", "database.session", "auth")
    import apis.jira_api as jira_api  # noqa: E402

    return importlib.reload(jira_api)


def _build_client(jira_api, authenticated=False):
    app = FastAPI()
    app.include_router(jira_api.router)
    if authenticated:
        app.dependency_overrides[jira_api.require_current_user] = lambda: {"id": 1}
    return TestClient(app)


def _payload(base_url):
    return {
        "base_url": base_url,
        "email": "jira-user@example.com",
        "api_token": "jira-token",
        "project_key": "TEST",
    }


def test_jira_import_rejects_unauthenticated_access(monkeypatch, tmp_path):
    jira_api = _load_jira_api(monkeypatch, tmp_path)
    client = _build_client(jira_api, authenticated=False)

    response = client.post("/jira/import", json=_payload("https://jira.example.com"))

    assert response.status_code == 401


@pytest.mark.parametrize(
    "jira_base_url",
    [
        "https://localhost",
        "https://127.0.0.1",
        "https://10.0.0.5",
        "https://jira.internal",
    ],
)
def test_jira_import_rejects_local_private_or_internal_hosts(monkeypatch, tmp_path, jira_base_url):
    jira_api = _load_jira_api(monkeypatch, tmp_path)
    client = _build_client(jira_api, authenticated=True)
    calls = {"count": 0}

    def _unexpected_request(*args, **kwargs):
        calls["count"] += 1
        return {"issues": []}

    monkeypatch.setattr(jira_api, "_jira_request", _unexpected_request)

    response = client.post("/jira/import", json=_payload(jira_base_url))

    assert response.status_code == 403
    assert calls["count"] == 0


def test_jira_import_rejects_untrusted_public_host(monkeypatch, tmp_path):
    jira_api = _load_jira_api(monkeypatch, tmp_path, allowed_hosts="jira.example.com")
    client = _build_client(jira_api, authenticated=True)
    calls = {"count": 0}

    def _unexpected_request(*args, **kwargs):
        calls["count"] += 1
        return {"issues": []}

    monkeypatch.setattr(jira_api, "_jira_request", _unexpected_request)

    response = client.post("/jira/import", json=_payload("https://evil.example.com"))

    assert response.status_code == 403
    assert calls["count"] == 0


def test_jira_import_accepts_trusted_configured_host(monkeypatch, tmp_path):
    jira_api = _load_jira_api(monkeypatch, tmp_path, allowed_hosts="jira.example.com")
    client = _build_client(jira_api, authenticated=True)
    captured = {"urls": []}

    def _fake_jira_request(url, email, api_token, method="GET", body=None):
        captured["urls"].append(url)
        assert email == "jira-user@example.com"
        assert api_token == "jira-token"
        return {
            "issues": [
                {
                    "key": "TEST-1",
                    "fields": {
                        "summary": "Trusted Jira story",
                        "description": "Given a trusted Jira story",
                    },
                }
            ]
        }

    monkeypatch.setattr(jira_api, "_jira_request", _fake_jira_request)

    response = client.post("/jira/import", json=_payload("https://jira.example.com"))

    assert response.status_code == 200
    assert captured["urls"]
    assert all(url.startswith("https://jira.example.com/") for url in captured["urls"])
    assert response.json()["stories"] == ["Given a trusted Jira story"]
