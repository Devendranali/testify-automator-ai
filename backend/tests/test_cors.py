import importlib
import os
import sys
from pathlib import Path

from fastapi.testclient import TestClient

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))


def _reload_main_with_origins(origins: str):
    os.environ["ALLOWED_ORIGINS"] = origins
    if "main" in sys.modules:
        del sys.modules["main"]
    import main  # noqa: F401
    return importlib.reload(sys.modules["main"])


def test_cors_allows_configured_origin():
    main = _reload_main_with_origins("http://localhost:3000,https://prod.example.com")
    client = TestClient(main.app)
    resp = client.options(
        "/login",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert resp.headers.get("access-control-allow-origin") == "http://localhost:3000"
    assert resp.headers.get("access-control-allow-credentials") == "true"


def test_cors_blocks_disallowed_origin():
    main = _reload_main_with_origins("http://localhost:3000")
    client = TestClient(main.app)
    resp = client.options(
        "/login",
        headers={
            "Origin": "https://evil.example.com",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert resp.headers.get("access-control-allow-origin") is None
