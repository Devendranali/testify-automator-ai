import os
from contextlib import contextmanager
from typing import Generator, Optional

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session

from config.settings import ROOT_PATH


def _sqlite_path() -> str:
    """Fallback path when DATABASE_URL is not provided."""
    default_db = os.path.join(ROOT_PATH, "database", "test.db")
    return f"sqlite:///{default_db.replace(os.sep, '/')}"


def _build_engine() -> Engine:
    raw_url = os.getenv("DATABASE_URL")
    url = raw_url.strip() if raw_url else _sqlite_path()

    connect_args = {}
    if url.startswith("sqlite"):
        connect_args = {"check_same_thread": False}

    engine = create_engine(
        url,
        echo=os.getenv("SQLALCHEMY_ECHO", "0") == "1",
        pool_pre_ping=True,
        connect_args=connect_args,
    )

    if url.startswith("sqlite"):
        # Ensure write-ahead logging for better concurrency.
        @event.listens_for(engine, "connect")
        def _set_sqlite_pragma(dbapi_connection, connection_record):  # type: ignore[unused-ignore]
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL;")
            cursor.execute("PRAGMA foreign_keys=ON;")
            cursor.close()

    return engine


engine: Engine = _build_engine()
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a database session."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@contextmanager
def session_scope(expire_on_commit: Optional[bool] = None) -> Generator[Session, None, None]:
    """Context manager for scripts/CLI usage."""
    session_options = {}
    if expire_on_commit is not None:
        session_options["expire_on_commit"] = expire_on_commit
    session_factory = sessionmaker(bind=engine, autocommit=False, autoflush=False, **session_options)
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
