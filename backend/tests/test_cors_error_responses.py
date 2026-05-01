import importlib
import os
import sys
import types
from pathlib import Path

from fastapi import APIRouter
from fastapi.testclient import TestClient

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))


_ROUTER_MODULES = [
    "apis.image_text_api",
    "apis.chroma_debug_api",
    "apis.enrichment_api",
    "apis.url_enrichment",
    "apis.rag_testcase_runner",
    "apis.generate_from_story",
    "apis.generate_page_methods",
    "apis.generate_from_manual_testcases",
    "apis.generate_testcases_from_methods",
    "apis.manual_add_metadata",
    "apis.manual_enrichment_api",
    "apis.manual_capture",
    "apis.projects_api",
    "apis.testcases_api",
    "apis.run_test_api",
    "apis.report_api",
    "apis.markers_api",
    "apis.metrics_api",
    "apis.jira_api",
    "apis.visualizer_api",
]


def _build_router_module(route_path: str = "/health") -> types.ModuleType:
    module = types.ModuleType("router_stub")
    router = APIRouter()

    @router.get(route_path)
    def _route():
        return {"ok": True}

    module.router = router
    return module


def _build_projects_module() -> types.ModuleType:
    module = _build_router_module("/projects")

    class TokenPayload:
        def __init__(self, **kwargs):
            self.sub = kwargs.get("sub")
            self.uid = kwargs.get("uid")
            self.org = kwargs.get("org")
            self.org_id = kwargs.get("org_id")

    module.TokenPayload = TokenPayload
    return module


def _install_router_stubs():
    for module_name in _ROUTER_MODULES:
        if module_name == "apis.projects_api":
            sys.modules[module_name] = _build_projects_module()
        elif module_name == "apis.visualizer_api":
            sys.modules[module_name] = _build_router_module("/images")
        else:
            sys.modules[module_name] = _build_router_module()


def _reload_main_with_origins(origins: str):
    os.environ["ALLOWED_ORIGINS"] = origins
    os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret")
    _install_router_stubs()
    if "main" in sys.modules:
        del sys.modules["main"]
    import main  # noqa: F401
    return importlib.reload(sys.modules["main"])


def test_allowed_origin_gets_valid_cors_headers_on_500():
    main = _reload_main_with_origins("http://localhost:3000")

    @main.app.get("/__test_crash")
    def _crash():
        raise RuntimeError("boom")

    client = TestClient(main.app, raise_server_exceptions=False)
    resp = client.get("/__test_crash", headers={"Origin": "http://localhost:3000"})

    assert resp.status_code == 500
    assert resp.json()["detail"] == "Internal server error"
    assert resp.headers.get("access-control-allow-origin") == "http://localhost:3000"
    assert resp.headers.get("access-control-allow-credentials") == "true"


def test_allowed_origin_gets_valid_cors_headers_on_normal_response():
    main = _reload_main_with_origins("http://localhost:3000")

    client = TestClient(main.app, raise_server_exceptions=False)
    resp = client.options(
        "/login",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert resp.status_code == 200
    assert resp.headers.get("access-control-allow-origin") == "http://localhost:3000"
    assert resp.headers.get("access-control-allow-credentials") == "true"


def test_disallowed_origin_gets_no_cors_headers_on_500():
    main = _reload_main_with_origins("http://localhost:3000")

    @main.app.get("/__test_crash_blocked")
    def _crash():
        raise RuntimeError("boom")

    client = TestClient(main.app, raise_server_exceptions=False)
    resp = client.get("/__test_crash_blocked", headers={"Origin": "https://evil.example.com"})

    assert resp.status_code == 500
    assert resp.headers.get("access-control-allow-origin") is None
