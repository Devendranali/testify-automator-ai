import sys
from pathlib import Path

import pytest

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from config.settings import get_backend_public_base_url


def test_backend_public_base_url_prefers_env(monkeypatch):
    monkeypatch.setenv("BACKEND_PUBLIC_BASE_URL", "https://api.example.com/")

    assert get_backend_public_base_url("https://fallback.example.com") == "https://api.example.com"


def test_backend_public_base_url_uses_default_when_env_missing(monkeypatch):
    monkeypatch.delenv("BACKEND_PUBLIC_BASE_URL", raising=False)

    assert get_backend_public_base_url("https://proxy.example.com/") == "https://proxy.example.com"


def test_backend_public_base_url_requires_value(monkeypatch):
    monkeypatch.delenv("BACKEND_PUBLIC_BASE_URL", raising=False)

    with pytest.raises(RuntimeError, match="BACKEND_PUBLIC_BASE_URL"):
        get_backend_public_base_url()
