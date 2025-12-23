import os
import subprocess
import sys


def run_migrations() -> None:
    """
    Run Alembic migrations to ensure the database schema
    is up to date before the application starts.

    This is safe to run multiple times.
    Alembic will only apply pending migrations.
    """

    # Allow disabling migrations explicitly if ever needed
    if os.getenv("RUN_DB_MIGRATIONS", "1") not in {"1", "true", "True"}:
        print("⚠️ RUN_DB_MIGRATIONS is disabled — skipping migrations")
        return

    print("🛠️ Running database migrations (alembic upgrade head)...")

    try:
        subprocess.run(
            ["alembic", "upgrade", "head"],
            check=True,
            stdout=sys.stdout,
            stderr=sys.stderr,
        )
        print("✅ Database migrations completed")
    except subprocess.CalledProcessError as exc:
        print("❌ Database migration failed")
        raise RuntimeError("Database migration failed") from exc
