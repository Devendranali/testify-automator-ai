import importlib
import os
import sys
from pathlib import Path

from fastapi.testclient import TestClient

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))


def _load_main():
    if "main" in sys.modules:
        del sys.modules["main"]
    import main  # noqa: F401
    return importlib.reload(sys.modules["main"])


def test_global_exception_handler_hides_details():
    os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret")
    main = _load_main()

    @main.app.get("/__test_crash")
    def _crash():
        raise RuntimeError("sensitive error details")

    client = TestClient(main.app, raise_server_exceptions=False)
    resp = client.get("/__test_crash")
    assert resp.status_code == 500
    body = resp.json()
    assert body.get("detail") == "Internal server error"
    assert "sensitive error details" not in resp.text
