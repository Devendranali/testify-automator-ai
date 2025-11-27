import os
import re
from contextlib import contextmanager
from typing import Generator, Optional

from sqlalchemy import create_engine, event, text, inspect
from sqlalchemy.engine import Engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session

Base = declarative_base()


def _normalized_slug(name: str) -> str:
    cleaned = re.sub(r"\s+", " ", name or "").strip().lower()
    cleaned = re.sub(r"[^a-z0-9_-]+", "-", cleaned)
    return cleaned or "org"


def _bootstrap_sqlite_schema(engine: Engine) -> None:
    """Ensure legacy SQLite databases have the latest critical columns."""
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    if not tables:
        return

    def _ensure_column(conn, table: str, column: str, ddl: str) -> None:
        cols = {col["name"] for col in inspector.get_columns(table)}
        if column not in cols:
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}"))

    def _ensure_org(conn, name: str) -> int:
        cleaned = (name or "default").strip() or "default"
        slug = _normalized_slug(cleaned)
        existing = conn.execute(
            text("SELECT id FROM organizations WHERE slug = :slug"),
            {"slug": slug},
        ).fetchone()
        if existing:
            return existing[0]
        result = conn.execute(
            text(
                "INSERT INTO organizations (name, slug, display_name, created_at, updated_at) "
                "VALUES (:name, :slug, :display, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            ),
            {"name": cleaned, "slug": slug, "display": cleaned},
        )
        return int(result.lastrowid)

    with engine.begin() as conn:
        if "organizations" not in tables:
            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS organizations (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name VARCHAR(255) NOT NULL,
                        slug VARCHAR(255) NOT NULL,
                        display_name VARCHAR(255) NOT NULL,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL
                    )
                    """
                )
            )
            conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS uq_organizations_name ON organizations (name)"))
            conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS uq_organizations_slug ON organizations (slug)"))
            tables.add("organizations")

        if "users" in tables:
            _ensure_column(conn, "users", "organization", "VARCHAR(255) DEFAULT ''")
            _ensure_column(conn, "users", "organization_id", "INTEGER")

        if "projects" in tables:
            _ensure_column(conn, "projects", "organization", "VARCHAR(255) DEFAULT ''")
            _ensure_column(conn, "projects", "organization_id", "INTEGER")

        if "users" in tables:
            rows = conn.execute(
                text(
                    "SELECT id, organization FROM users "
                    "WHERE organization IS NOT NULL AND organization != '' "
                    "AND (organization_id IS NULL OR organization_id = 0)"
                )
            )
            for row_id, org_name in rows:
                org_id = _ensure_org(conn, org_name)
                conn.execute(
                    text("UPDATE users SET organization_id = :org_id WHERE id = :row_id"),
                    {"org_id": org_id, "row_id": row_id},
                )

        if "projects" in tables:
            rows = conn.execute(
                text(
                    "SELECT id, organization FROM projects "
                    "WHERE organization IS NOT NULL AND organization != '' "
                    "AND (organization_id IS NULL OR organization_id = 0)"
                )
            )
            for row_id, org_name in rows:
                org_id = _ensure_org(conn, org_name)
                conn.execute(
                    text("UPDATE projects SET organization_id = :org_id WHERE id = :row_id"),
                    {"org_id": org_id, "row_id": row_id},
                )


def _build_engine() -> Engine:
    raw_url = os.getenv("DATABASE_URL")
    if not raw_url or not raw_url.strip():
        raise RuntimeError(
            "DATABASE_URL must be set (e.g., postgresql+psycopg://user:pass@host:5432/testify or "
            "sqlite:///absolute/path/to/db)."
        )
    url = raw_url.strip()

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
        @event.listens_for(engine, "connect")
        def _set_sqlite_pragma(dbapi_connection, connection_record):  # type: ignore[unused-ignore]
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL;")
            cursor.execute("PRAGMA foreign_keys=ON;")
            cursor.close()

        _bootstrap_sqlite_schema(engine)

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
