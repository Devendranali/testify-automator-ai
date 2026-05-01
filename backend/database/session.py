import os
from contextlib import contextmanager
from typing import Generator, Optional

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session

Base = declarative_base()


def _build_database_url() -> str:
    raw_url = (os.getenv("DATABASE_URL") or "").strip()
    if raw_url:
        return raw_url

    db_host = (os.getenv("DB_HOST") or "").strip()
    db_port = (os.getenv("DB_PORT") or "5432").strip()
    db_name = (os.getenv("DB_NAME") or "postgres").strip()
    db_user = (os.getenv("DB_USER") or "").strip()
    db_password = (os.getenv("DB_PASSWORD") or "").strip()

    if all([db_host, db_user, db_password]):
        return (
            f"postgresql+psycopg://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
            "?sslmode=require"
        )

    raise RuntimeError(
        "Set DATABASE_URL or provide DB_HOST, DB_PORT, DB_NAME, DB_USER, and DB_PASSWORD."
    )


def _build_engine() -> Engine:
    url = _build_database_url()

    connect_args = {}
    if url.startswith("sqlite"):
        connect_args = {"check_same_thread": False}

    pool_size = int(os.getenv("DB_POOL_SIZE", "10"))
    max_overflow = int(os.getenv("DB_MAX_OVERFLOW", "20"))
    pool_timeout = int(os.getenv("DB_POOL_TIMEOUT", "30"))

    engine = create_engine(
        url,
        echo=os.getenv("SQLALCHEMY_ECHO", "0") == "1",
        pool_pre_ping=True,
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_timeout=pool_timeout,
        connect_args=connect_args,
    )

    if url.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def _set_sqlite_pragma(dbapi_connection, connection_record):  # type: ignore[unused-ignore]
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL;")
            cursor.execute("PRAGMA foreign_keys=ON;")
            cursor.close()

    return engine


engine: Engine = _build_engine()
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)


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


def get_db_optional() -> Generator[Optional[Session], None, None]:
    """Yield a database session when the connection is available; otherwise, yield None."""
    try:
        for session in get_db():
            yield session
    except RuntimeError:
        yield None
