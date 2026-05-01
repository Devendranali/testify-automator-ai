import importlib
import os
import sys
from pathlib import Path

import pytest
from jose import jwt

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))


def _reload_auth():
    if "auth" in sys.modules:
        del sys.modules["auth"]
    import auth  # noqa: F401
    return importlib.reload(sys.modules["auth"])


def test_jwt_secret_missing_raises(monkeypatch):
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
    with pytest.raises(RuntimeError):
        _reload_auth()


def test_jwt_secret_encode_decode(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", "unit-test-secret")
    auth = _reload_auth()
    token = auth.create_access_token({"sub": "user@example.com", "uid": 1, "org": "Acme"})
    decoded = jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
    assert decoded["sub"] == "user@example.com"
    assert decoded["uid"] == 1
    assert decoded["org"] == "Acme"


def test_startup_validation_fails_when_missing(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", "ok-secret")
    if "main" in sys.modules:
        del sys.modules["main"]
    import main  # noqa: F401
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
    with pytest.raises(RuntimeError):
        main._validate_jwt_secret()
