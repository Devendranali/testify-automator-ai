import sys
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from database.models import Project  # noqa: E402


def test_project_created_by_model_matches_intended_schema():
    column = Project.__table__.c.created_by
    foreign_keys = list(column.foreign_keys)

    assert column.nullable is False
    assert len(foreign_keys) == 1
    assert foreign_keys[0].ondelete == "CASCADE"
