import importlib
import sys
import types
from pathlib import Path

import pytest
from fastapi import APIRouter

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


def _install_router_stubs(monkeypatch):
    for module_name in _ROUTER_MODULES:
        if module_name == "apis.projects_api":
            stub = _build_projects_module()
        elif module_name == "apis.visualizer_api":
            stub = _build_router_module("/images")
        else:
            stub = _build_router_module()
        monkeypatch.setitem(sys.modules, module_name, stub)


def _reload_main(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    _install_router_stubs(monkeypatch)
    if "main" in sys.modules:
        del sys.modules["main"]
    import main  # noqa: F401
    return importlib.reload(sys.modules["main"])


def test_validate_database_schema_runs_migrations_when_auto_migrate_enabled(monkeypatch):
    main = _reload_main(monkeypatch)
    calls = {"migrate": 0}

    monkeypatch.setattr(main, "auto_migrate_enabled", lambda: True)
    monkeypatch.setattr(
        main,
        "run_migrations_if_needed",
        lambda *_args, **_kwargs: calls.__setitem__("migrate", calls["migrate"] + 1),
    )
    monkeypatch.setattr(main, "_required_tables_exist", lambda: True)
    monkeypatch.setattr(main, "_current_db_revision", lambda: "head-rev")
    monkeypatch.setattr(main, "_alembic_head_revision", lambda: "head-rev")

    main._validate_database_schema()

    assert calls["migrate"] == 1


def test_validate_database_schema_skips_migrations_when_auto_migrate_disabled(monkeypatch):
    main = _reload_main(monkeypatch)
    calls = {"migrate": 0}

    monkeypatch.setattr(main, "auto_migrate_enabled", lambda: False)
    monkeypatch.setattr(
        main,
        "run_migrations_if_needed",
        lambda *_args, **_kwargs: calls.__setitem__("migrate", calls["migrate"] + 1),
    )
    monkeypatch.setattr(main, "_required_tables_exist", lambda: True)
    monkeypatch.setattr(main, "_current_db_revision", lambda: "head-rev")
    monkeypatch.setattr(main, "_alembic_head_revision", lambda: "head-rev")

    main._validate_database_schema()

    assert calls["migrate"] == 0


def test_validate_database_schema_still_fails_when_out_of_sync_and_auto_migrate_disabled(monkeypatch):
    main = _reload_main(monkeypatch)

    monkeypatch.setattr(main, "auto_migrate_enabled", lambda: False)
    monkeypatch.setattr(main, "run_migrations_if_needed", lambda *_args, **_kwargs: pytest.fail("should not migrate"))
    monkeypatch.setattr(main, "_required_tables_exist", lambda: False)
    monkeypatch.setattr(main, "_current_db_revision", lambda: None)
    monkeypatch.setattr(main, "_alembic_head_revision", lambda: "head-rev")

    with pytest.raises(RuntimeError, match="Database schema out of sync"):
        main._validate_database_schema()
