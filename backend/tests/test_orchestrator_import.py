import importlib
import sys
from pathlib import Path


_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))


def test_app_import_does_not_require_manifest():
    if "app.api" in sys.modules:
        del sys.modules["app.api"]
    import app.api  # noqa: F401
    importlib.reload(sys.modules["app.api"])
