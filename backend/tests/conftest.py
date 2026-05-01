import os
import tempfile
from pathlib import Path

import pytest

# Ensure auth module can be imported during tests.
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret")
os.environ.setdefault("ALLOWED_ORIGINS", "http://localhost:3000")

# Provide a default sqlite database for tests that don't set DATABASE_URL.
_DEFAULT_DB_DIR = Path(tempfile.mkdtemp())
_DEFAULT_DB_PATH = _DEFAULT_DB_DIR / "tests.db"
os.environ.setdefault("DATABASE_URL", f"sqlite:///{_DEFAULT_DB_PATH}")


@pytest.fixture(autouse=True)
def _reset_db():
    if not os.getenv("DATABASE_URL"):
        yield
        return
    from database import models  # noqa: F401
    from sqlalchemy import inspect
    from database.session import Base, engine

    inspector = inspect(engine)
    with engine.begin() as connection:
        for table in reversed(Base.metadata.sorted_tables):
            if inspector.has_table(table.name):
                connection.execute(table.delete())
    yield
