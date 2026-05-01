import importlib
import os
import sys
from pathlib import Path

import pytest
from fastapi import HTTPException


_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))


def _clear_modules(*names):
    for name in names:
        if name in sys.modules:
            del sys.modules[name]


def test_openai_related_modules_import_without_api_key(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.setitem(
        sys.modules,
        "utils.file_utils",
        type(
            "FileUtilsStub",
            (),
            {
                "save_region": staticmethod(lambda *_args, **_kwargs: {"path": "region.png"}),
                "build_standard_metadata": staticmethod(lambda *_args, **_kwargs: {}),
            },
        )(),
    )
    monkeypatch.setitem(
        sys.modules,
        "services.chroma_service",
        type(
            "ChromaServiceStub",
            (),
            {"upsert_text_record": staticmethod(lambda *_args, **_kwargs: {})},
        )(),
    )
    _clear_modules(
        "services.test_generation_utils",
        "logic.image_text_extractor",
        "utils.openai_client",
    )

    import services.test_generation_utils as test_generation_utils  # noqa: E402
    import logic.image_text_extractor as image_text_extractor  # noqa: E402

    importlib.reload(test_generation_utils)
    importlib.reload(image_text_extractor)


def test_get_openai_client_requires_api_key(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "")
    _clear_modules("utils.openai_client")

    import utils.openai_client as openai_client_utils  # noqa: E402
    importlib.reload(openai_client_utils)
    openai_client_utils.reset_openai_client()

    with pytest.raises(openai_client_utils.OpenAIConfigurationError, match="OPENAI_API_KEY is not set"):
        openai_client_utils.get_openai_client()


def test_get_openai_client_lazy_and_cached(monkeypatch):
    calls = {"init": 0}

    class DummyOpenAI:
        def __init__(self, api_key):
            calls["init"] += 1
            self.api_key = api_key

    monkeypatch.setenv("OPENAI_API_KEY", "unit-test-key")
    _clear_modules("utils.openai_client", "services.test_generation_utils")

    import utils.openai_client as openai_client_utils  # noqa: E402
    importlib.reload(openai_client_utils)
    openai_client_utils.reset_openai_client()
    monkeypatch.setattr(openai_client_utils, "OpenAI", DummyOpenAI)

    import services.test_generation_utils as test_generation_utils  # noqa: E402
    importlib.reload(test_generation_utils)

    assert calls["init"] == 0

    client_one = test_generation_utils.get_openai_client()
    client_two = test_generation_utils.get_openai_client()

    assert calls["init"] == 1
    assert client_one is client_two
    assert client_one.api_key == "unit-test-key"


def test_manual_testcase_api_returns_clear_error_without_api_key(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "")
    _clear_modules(
        "utils.openai_client",
        "services.test_generation_utils",
        "apis.generate_from_manual_testcases",
    )

    import utils.openai_client as openai_client_utils  # noqa: E402
    importlib.reload(openai_client_utils)
    openai_client_utils.reset_openai_client()

    import apis.generate_from_manual_testcases as manual_api  # noqa: E402
    importlib.reload(manual_api)

    req = manual_api.ManualTestcaseRequest(manual_testcase=["1. Open the login page"])
    with pytest.raises(HTTPException) as exc_info:
        manual_api.generate_from_manual_testcase(req)

    assert exc_info.value.status_code == 503
    assert "OPENAI_API_KEY is not set" in str(exc_info.value.detail)
