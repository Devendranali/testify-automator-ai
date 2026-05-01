import importlib
import sys
import types
from pathlib import Path

import pytest
from fastapi import APIRouter

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))


def _clear_modules(*names):
    for name in names:
        if name in sys.modules:
            del sys.modules[name]


def test_yolo_detector_lazy_init(monkeypatch):
    calls = {"init": 0}

    class DummyYOLO:
        def __init__(self, path):
            calls["init"] += 1
            self.names = {0: "button"}

        def predict(self, *args, **kwargs):
            return [types.SimpleNamespace(boxes=[])]

    dummy_ultralytics = types.SimpleNamespace(YOLO=DummyYOLO)
    sys.modules["ultralytics"] = dummy_ultralytics

    if "services.yolo_detector" in sys.modules:
        del sys.modules["services.yolo_detector"]
    import services.yolo_detector as yd  # noqa: E402
    importlib.reload(yd)

    assert yd._model is None
    assert calls["init"] == 0
    yd._get_model()
    assert calls["init"] == 1


def test_ocr_classifier_lazy_init(monkeypatch):
    _clear_modules("services.ocr_type_classifier")
    import services.ocr_type_classifier as oc  # noqa: E402
    importlib.reload(oc)

    assert oc._model is None

    class DummyModel:
        def __init__(self):
            self.last_channel = 1280
            self.classifier = {1: None}

        def eval(self):
            return self

        def load_state_dict(self, *_args, **_kwargs):
            return None

    monkeypatch.setattr(oc.models, "mobilenet_v2", lambda pretrained=False: DummyModel())
    monkeypatch.setattr(oc.torch, "load", lambda *args, **kwargs: {})
    monkeypatch.setattr(oc.torch.nn, "Linear", lambda *args, **kwargs: object())

    model = oc._get_model()
    assert model is not None


def test_match_utils_sentence_transformer_lazy_init(monkeypatch):
    calls = {"init": 0, "encode": 0}

    class DummySentenceTransformer:
        def __init__(self, model_name):
            calls["init"] += 1
            self.model_name = model_name

        def encode(self, values, **_kwargs):
            calls["encode"] += 1
            if isinstance(values, str):
                return [0.7]
            return [[0.1] for _ in values]

    class DummySimilarity:
        def max(self):
            return types.SimpleNamespace(item=lambda: 0.75)

    dummy_sentence_transformers = types.SimpleNamespace(
        SentenceTransformer=DummySentenceTransformer,
        util=types.SimpleNamespace(
            pytorch_cos_sim=lambda *_args, **_kwargs: DummySimilarity()
        ),
    )
    monkeypatch.setitem(sys.modules, "sentence_transformers", dummy_sentence_transformers)

    _clear_modules("utils.match_utils")
    import utils.match_utils as match_utils  # noqa: E402
    importlib.reload(match_utils)

    assert match_utils._intent_model is None
    assert match_utils._intent_embeddings is None
    assert calls["init"] == 0

    assert match_utils.assign_intent_semantic("username") == "fill_username"
    assert calls["init"] == 1
    first_encode_count = calls["encode"]
    assert first_encode_count == len(match_utils.INTENT_TEMPLATES) + 1
    assert match_utils._intent_embeddings is not None

    assert match_utils.assign_intent_semantic("password") == "fill_username"
    assert calls["init"] == 1
    assert calls["encode"] == first_encode_count + 1


def test_manual_capture_sentence_transformer_lazy_init(monkeypatch):
    calls = {"init": 0, "encode": 0}

    class DummySentenceTransformer:
        def __init__(self, model_name):
            calls["init"] += 1
            self.model_name = model_name

        def encode(self, values, **_kwargs):
            calls["encode"] += 1
            return [[1.0], [1.0]]

    class DummyEmbeddingFunction:
        def __init__(self, model_name):
            self.model_name = model_name

    monkeypatch.setitem(
        sys.modules,
        "sentence_transformers",
        types.SimpleNamespace(SentenceTransformer=DummySentenceTransformer),
    )
    monkeypatch.setitem(
        sys.modules,
        "chromadb.utils.embedding_functions",
        types.SimpleNamespace(SentenceTransformerEmbeddingFunction=DummyEmbeddingFunction),
    )
    monkeypatch.setitem(
        sys.modules,
        "sklearn.metrics.pairwise",
        types.SimpleNamespace(cosine_similarity=lambda *_args, **_kwargs: [[1.0]]),
    )
    monkeypatch.setitem(
        sys.modules,
        "playwright.async_api",
        types.SimpleNamespace(Page=object),
    )
    monkeypatch.setitem(
        sys.modules,
        "utils.file_utils",
        types.SimpleNamespace(build_standard_metadata=lambda *_args, **_kwargs: {}),
    )
    monkeypatch.setitem(
        sys.modules,
        "utils.project_context",
        types.SimpleNamespace(current_project_id=lambda: None),
    )
    monkeypatch.setitem(
        sys.modules,
        "utils.smart_ai_utils",
        types.SimpleNamespace(get_smartai_src_dir=lambda: Path(".")),
    )
    monkeypatch.setitem(
        sys.modules,
        "utils.chroma_client",
        types.SimpleNamespace(get_collection=lambda *_args, **_kwargs: object()),
    )
    monkeypatch.setitem(
        sys.modules,
        "config.settings",
        types.SimpleNamespace(get_chroma_path=lambda: "chroma"),
    )

    _clear_modules("backend.logic.manual_capture_mode", "logic.manual_capture_mode")
    import logic.manual_capture_mode as manual_capture_mode  # noqa: E402
    importlib.reload(manual_capture_mode)

    assert manual_capture_mode._text_model is None
    assert manual_capture_mode._embedding_fn is None
    assert calls["init"] == 0

    embedding_fn = manual_capture_mode.get_sentence_transformer_embedding_function()
    assert embedding_fn is not None
    assert manual_capture_mode._embedding_fn is embedding_fn
    assert calls["init"] == 0

    assert manual_capture_mode.text_similarity("a", "b") == 1.0
    assert calls["init"] == 1
    assert calls["encode"] == 1

    assert manual_capture_mode.text_similarity("c", "d") == 1.0
    assert calls["init"] == 1
    assert calls["encode"] == 2


def test_chroma_service_embedding_function_lazy_init(monkeypatch):
    calls = {"init": 0}

    class DummyEmbeddingFunction:
        def __init__(self, model_name):
            calls["init"] += 1
            self.model_name = model_name

        def __call__(self, values):
            return [[0.1] for _ in values]

    monkeypatch.setitem(
        sys.modules,
        "chromadb.utils.embedding_functions",
        types.SimpleNamespace(SentenceTransformerEmbeddingFunction=DummyEmbeddingFunction),
    )
    monkeypatch.setitem(
        sys.modules,
        "utils.chroma_client",
        types.SimpleNamespace(get_collection=lambda *_args, **_kwargs: types.SimpleNamespace(get=lambda **_k: {"metadatas": [], "ids": []})),
    )
    monkeypatch.setitem(
        sys.modules,
        "utils.project_context",
        types.SimpleNamespace(current_project_id=lambda: None),
    )
    monkeypatch.setitem(
        sys.modules,
        "utils.request_context",
        types.SimpleNamespace(get_project_context=lambda required=True: types.SimpleNamespace(chroma_path="chroma")),
    )
    monkeypatch.setitem(
        sys.modules,
        "services.ocr_type_classifier",
        types.SimpleNamespace(classify_ocr_type=lambda *_args, **_kwargs: "ocr"),
    )

    _clear_modules("services.chroma_service")
    import services.chroma_service as chroma_service  # noqa: E402
    importlib.reload(chroma_service)

    assert chroma_service._embedding_function is None
    assert calls["init"] == 0

    embedding_function = chroma_service.get_sentence_transformer_embedding_function()
    assert embedding_function is not None
    assert calls["init"] == 1

    again = chroma_service.get_sentence_transformer_embedding_function()
    assert again is embedding_function
    assert calls["init"] == 1


def test_image_text_api_embedding_function_lazy_init(monkeypatch):
    calls = {"init": 0}

    class DummyEmbeddingFunction:
        def __init__(self, model_name):
            calls["init"] += 1
            self.model_name = model_name

    monkeypatch.setitem(
        sys.modules,
        "chromadb.utils.embedding_functions",
        types.SimpleNamespace(SentenceTransformerEmbeddingFunction=DummyEmbeddingFunction),
    )
    monkeypatch.setitem(
        sys.modules,
        "logic.image_text_extractor",
        types.SimpleNamespace(process_image_gpt=lambda *_args, **_kwargs: []),
    )
    monkeypatch.setitem(
        sys.modules,
        "services.graph_service",
        types.SimpleNamespace(build_dependency_graph=lambda *_args, **_kwargs: {}),
    )
    monkeypatch.setitem(
        sys.modules,
        "utils.match_utils",
        types.SimpleNamespace(normalize_page_name=lambda value: value),
    )
    monkeypatch.setitem(
        sys.modules,
        "utils.chroma_client",
        types.SimpleNamespace(get_collection=lambda *_args, **_kwargs: object()),
    )
    monkeypatch.setitem(
        sys.modules,
        "database.session",
        types.SimpleNamespace(get_db=lambda: None),
    )
    monkeypatch.setitem(
        sys.modules,
        "database.models",
        types.SimpleNamespace(Project=object, ImageMetadata=object, ImageUploadRun=object, User=object, OrganizationMember=types.SimpleNamespace(user_org_ids=lambda *_args, **_kwargs: [])),
    )
    monkeypatch.setitem(
        sys.modules,
        "database.project_storage",
        types.SimpleNamespace(DatabaseBackedProjectStorage=object),
    )
    monkeypatch.setitem(
        sys.modules,
        "apis.projects_api",
        types.SimpleNamespace(
            _ensure_project_structure=lambda *_args, **_kwargs: {},
            _project_root=lambda *_args, **_kwargs: Path("."),
            get_current_user=lambda *_args, **_kwargs: None,
            get_user_project=lambda *_args, **_kwargs: None,
        ),
    )
    monkeypatch.setitem(
        sys.modules,
        "utils.request_context",
        types.SimpleNamespace(
            set_request_context=lambda **_kwargs: {},
            reset_request_context=lambda *_args, **_kwargs: None,
            get_project_context=lambda required=True: types.SimpleNamespace(project_id=1),
        ),
    )
    monkeypatch.setitem(
        sys.modules,
        "utils.project_paths",
        types.SimpleNamespace(build_project_context=lambda *_args, **_kwargs: None, ProjectContext=object),
    )

    _clear_modules("apis.image_text_api")
    import apis.image_text_api as image_text_api  # noqa: E402
    importlib.reload(image_text_api)

    assert image_text_api._embedding_function is None
    assert calls["init"] == 0

    embedding_function = image_text_api.get_sentence_transformer_embedding_function()
    assert embedding_function is not None
    assert calls["init"] == 1


def test_main_import_does_not_install_playwright_on_windows(monkeypatch):
    router_names = [
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

    def _router_module():
        return types.SimpleNamespace(router=APIRouter())

    for name in router_names:
        if name == "apis.projects_api":
            monkeypatch.setitem(
                sys.modules,
                name,
                types.SimpleNamespace(router=APIRouter(), TokenPayload=type("TokenPayload", (), {})),
            )
        else:
            monkeypatch.setitem(sys.modules, name, _router_module())

    monkeypatch.setitem(sys.modules, "auth", types.SimpleNamespace(SECRET_KEY="secret", ALGORITHM="HS256"))
    monkeypatch.setitem(
        sys.modules,
        "database.models",
        types.SimpleNamespace(Organization=object, User=object, Project=object, OrganizationMember=types.SimpleNamespace(user_org_ids=lambda *_args, **_kwargs: [])),
    )
    monkeypatch.setitem(
        sys.modules,
        "database.session",
        types.SimpleNamespace(engine=object(), get_db=lambda: None, SessionLocal=lambda: None),
    )
    monkeypatch.setitem(
        sys.modules,
        "database.migration_runner",
        types.SimpleNamespace(auto_migrate_enabled=lambda: False, run_migrations_if_needed=lambda *_args, **_kwargs: None),
    )
    monkeypatch.setitem(sys.modules, "utils.security", types.SimpleNamespace(hash_password=lambda value: value, verify_password=lambda *_args, **_kwargs: True))
    monkeypatch.setitem(sys.modules, "utils.request_context", types.SimpleNamespace(set_request_context=lambda **_kwargs: {}, reset_request_context=lambda *_args, **_kwargs: None))
    monkeypatch.setitem(sys.modules, "utils.project_paths", types.SimpleNamespace(build_project_context=lambda *_args, **_kwargs: None))
    monkeypatch.setitem(sys.modules, "utils.openai_client", types.SimpleNamespace(OpenAIClientError=RuntimeError))
    monkeypatch.setattr(sys, "platform", "win32")

    def _fail_run(*_args, **_kwargs):
        raise AssertionError("subprocess.run should not execute during module import")

    monkeypatch.setattr("subprocess.run", _fail_run)

    _clear_modules("main")
    import main  # noqa: E402
    importlib.reload(main)
