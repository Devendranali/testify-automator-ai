#main.py

import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import traceback
import json
import asyncio
import subprocess
import logging
import re
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from fastapi.responses import JSONResponse
from fastapi.requests import Request
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from jose import JWTError, jwt
from pydantic import BaseModel, EmailStr, ValidationError, field_validator
from sqlalchemy.exc import IntegrityError, OperationalError, ProgrammingError
from sqlalchemy.orm import Session
from sqlalchemy import inspect, text

try:
    from psycopg.errors import UndefinedTable as PsycopgUndefinedTable
except Exception:  # pragma: no cover - optional import guard
    PsycopgUndefinedTable = None

# Routers
from apis.image_text_api import router as image_router
from apis.chroma_debug_api import router as debug_chroma_export_router
from apis.enrichment_api import router as enrichment_router
from apis.url_enrichment import router as url_enrichment_router
from apis.rag_testcase_runner import router as rag_router
from apis.generate_from_story import router as generate_from_story_router
from apis.generate_page_methods import router as generate_page_methods_router
from apis.generate_from_manual_testcases import router as generate_from_manual_testcase_router
from apis.generate_testcases_from_methods import router as generate_test_code_from_methods_router
from apis.manual_add_metadata import router as manual_add_metadata
from apis.manual_enrichment_api import router as manual_enrichment_router  # from first file
from apis.manual_capture import router as manual_capture_router
from apis.projects_api import router as projects_router
from apis.testcases_api import router as testcases_router
from apis.run_test_api import router as run_tests_router
from apis.report_api import router as report_router
from apis.markers_api import router as markers_router  # from second file
from apis.metrics_api import router as metrics_router  # from second file
from apis.jira_api import router as jira_router
from apis.visualizer_api import router as visualizer_router
from apis.token_usage_api import router as token_usage_router

import auth
from database.models import Organization, User, Project, OrganizationMember
from database.session import engine, get_db, SessionLocal
from database.migration_runner import auto_migrate_enabled, run_migrations_if_needed
from utils.security import hash_password, verify_password
from utils.request_context import set_request_context, reset_request_context
from utils.project_paths import build_project_context
from utils.openai_client import OpenAIClientError
from apis.projects_api import TokenPayload


# -------------------------------------------------------
# DB STARTUP VALIDATION (NO RUNTIME DDL)
# -------------------------------------------------------
def _alembic_config():
    from alembic.config import Config

    backend_root = Path(__file__).resolve().parent
    alembic_ini = backend_root / "database" / "alembic.ini"
    migrations_dir = backend_root / "database" / "migrations"

    config = Config(str(alembic_ini))
    config.set_main_option("script_location", str(migrations_dir))
    db_url = (os.getenv("DATABASE_URL") or "").strip()
    if db_url:
        config.set_main_option("sqlalchemy.url", db_url)
    else:
        config.set_main_option("sqlalchemy.url", str(engine.url))
    return config


def _required_tables_exist() -> bool:
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    return {"organizations", "users", "projects"}.issubset(tables)


def _current_db_revision() -> str | None:
    inspector = inspect(engine)
    if "alembic_version" not in set(inspector.get_table_names()):
        return None
    with engine.connect() as conn:
        result = conn.execute(text("SELECT version_num FROM alembic_version"))
        row = result.first()
        return row[0] if row else None


def _alembic_head_revision() -> str:
    from alembic.script import ScriptDirectory

    script = ScriptDirectory.from_config(_alembic_config())
    heads = script.get_heads()
    if not heads:
        raise RuntimeError("Alembic head revision not found.")
    if len(heads) > 1:
        raise RuntimeError(f"Multiple Alembic heads detected: {heads}")
    return heads[0]


_startup_logger = logging.getLogger("startup")
_DEV_APP_ENVS = {"development", "dev", "local", "test"}


def _sanitize_database_url(url: str | None) -> str:
    if not url:
        return "<not set>"
    try:
        from sqlalchemy.engine import make_url

        return make_url(url).render_as_string(hide_password=True)
    except Exception:
        return "<invalid>"


def _validate_jwt_secret() -> None:
    secret = os.getenv("JWT_SECRET_KEY")
    if not secret or not secret.strip():
        _startup_logger.error("JWT_SECRET_KEY is not set. Refusing to start.")
        raise RuntimeError("JWT_SECRET_KEY is required for JWT signing and validation.")


def _app_env() -> str:
    return (os.getenv("APP_ENV") or "development").strip().lower()


def _is_dev_like_env() -> bool:
    return _app_env() in _DEV_APP_ENVS


def _root_path() -> str:
    configured = (os.getenv("ROOT_PATH") or "").strip()
    if configured:
        return configured
    if _is_dev_like_env():
        return ""
    return "/api"


def _default_allowed_origins() -> list[str]:
    if _is_dev_like_env():
        return ["http://localhost:3000"]
    return []


def _configured_allowed_origins() -> list[str]:
    raw = os.getenv("ALLOWED_ORIGINS", "")
    origins = [o.strip() for o in raw.split(",") if o and o.strip()]
    if origins:
        return origins
    return _default_allowed_origins()


def _validate_allowed_origins() -> None:
    origins = _configured_allowed_origins()
    if not origins:
        _startup_logger.error("ALLOWED_ORIGINS is not set. Refusing to start.")
        raise RuntimeError(
            "ALLOWED_ORIGINS is required in production and must list the allowed frontend origin(s)."
        )
    if "*" in origins and not _is_dev_like_env():
        _startup_logger.error("ALLOWED_ORIGINS contains '*' in a non-development environment. Refusing to start.")
        raise RuntimeError("ALLOWED_ORIGINS cannot contain '*' outside development-like environments.")
    if "*" in origins:
        _startup_logger.warning("ALLOWED_ORIGINS contains '*'; credentials will be disabled for CORS responses.")
    elif os.getenv("ALLOWED_ORIGINS", "").strip() == "" and _is_dev_like_env():
        _startup_logger.warning(
            "ALLOWED_ORIGINS not set; using development default origin http://localhost:3000."
        )


def _validate_database_schema() -> None:
    if auto_migrate_enabled():
        _startup_logger.warning("AUTO_MIGRATE enabled; applying pending Alembic migrations at startup.")
        run_migrations_if_needed(engine, _alembic_config(), _startup_logger)
    else:
        _startup_logger.info("AUTO_MIGRATE disabled; startup will not run database migrations.")
    required_missing = not _required_tables_exist()
    current = _current_db_revision()
    head = _alembic_head_revision()
    out_of_sync = required_missing or not current or current != head

    if out_of_sync:
        db_url = _sanitize_database_url(str(engine.url))
        _startup_logger.error(
            "Database schema out of sync. current=%s head=%s db=%s required_tables_missing=%s",
            current,
            head,
            db_url,
            required_missing,
        )
        raise RuntimeError("Database schema out of sync. Run Alembic migrations.")


def _configure_windows_playwright_runtime() -> None:
    if sys.platform != "win32":
        return
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "0"
    try:
        subprocess.run(["playwright", "install", "chromium"], check=True)
    except Exception as e:
        print("Playwright install failed:", e)


# -------------------------------------------------------
# FASTAPI INITIALIZATION
# -------------------------------------------------------
@asynccontextmanager
async def _lifespan(app: FastAPI):
    try:
        _validate_jwt_secret()
        _validate_allowed_origins()
        _validate_database_schema()
    except RuntimeError:
        raise SystemExit(1)
    yield


def _parse_allowed_origins() -> list[str]:
    return _configured_allowed_origins()


def _cors_headers_for_request(request: Request) -> dict[str, str]:
    origin = (request.headers.get("Origin") or "").strip()
    if not origin:
        return {}

    allow_origin = None
    if "*" in _allowed_origins and not _allow_credentials:
        allow_origin = "*"
    elif origin in _allowed_origins:
        allow_origin = origin
    elif _origin_regex and re.fullmatch(_origin_regex, origin):
        allow_origin = origin

    if not allow_origin:
        return {}

    headers = {
        "Access-Control-Allow-Origin": allow_origin,
        "Vary": "Origin",
    }
    if _allow_credentials and allow_origin != "*":
        headers["Access-Control-Allow-Credentials"] = "true"
    return headers


app = FastAPI(
    title="AI Test Extractor",
    lifespan=_lifespan,
    root_path=_root_path(),
    docs_url="/docs",
    openapi_url="/openapi.json",
)

_allowed_origins = _parse_allowed_origins()
_allow_credentials = bool(_allowed_origins)
_origin_regex = os.getenv("ALLOWED_ORIGIN_REGEX", "").strip() or None
if "*" in _allowed_origins:
    # Starlette rejects '*' when credentials are allowed; disable credentials in that case.
    _allow_credentials = False


def _extract_project_id_from_request(request: Request) -> int | None:
    try:
        raw = request.query_params.get("project_id")
        if raw and raw.isdigit():
            return int(raw)
    except Exception:
        pass

    path = request.url.path or ""
    for pattern in (
        r"/projects/(?P<pid>\d+)",
        r"/reports/view/(?P<pid>\d+)",
        r"^/(?P<pid>\d+)(?:/|$)",
    ):
        match = re.search(pattern, path)
        if match:
            try:
                return int(match.group("pid"))
            except Exception:
                return None
    return None


def _resolve_user_from_request(request: Request) -> User | None:
    auth_header = request.headers.get("Authorization") or ""
    if not auth_header.startswith("Bearer "):
        return None
    token = auth_header.split(" ", 1)[1].strip()
    if not token:
        return None
    db = SessionLocal()
    try:
        payload = jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
        token_data = TokenPayload(**payload)
        user = (
            db.query(User)
            .filter(User.id == token_data.uid, User.email == str(token_data.sub).lower())
            .first()
        )
        if not user:
            return None
        if (user.organization or "").strip().lower() != (token_data.org or "").strip().lower():
            return None
        if token_data.org_id is not None and user.organization_id != token_data.org_id:
            return None
        org_ids = OrganizationMember.user_org_ids(db, user.id)
        if not org_ids:
            return None
        if token_data.org_id is not None and token_data.org_id not in org_ids:
            return None
        return user
    except (JWTError, ValidationError):
        return None
    finally:
        db.close()


class RequestContextMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive=receive)
        pid = _extract_project_id_from_request(request)
        tokens = {}
        if pid is not None:
            user = _resolve_user_from_request(request)
            if user:
                with SessionLocal() as db:
                    org_ids = OrganizationMember.user_org_ids(db, user.id)
                    if not org_ids:
                        response = JSONResponse(
                            status_code=403,
                            content={"detail": "Organization membership required"},
                        )
                        await response(scope, receive, send)
                        return
                    project = (
                        db.query(Project)
                        .filter(Project.id == pid, Project.organization_id.in_(org_ids))
                        .first()
                    )
                    if not project:
                        response = JSONResponse(
                            status_code=403,
                            content={"detail": "You do not have access to this project"},
                        )
                        await response(scope, receive, send)
                        return
                    project_context = build_project_context(user, project.id, db)
                tokens = set_request_context(project_context=project_context)
        try:
            await self.app(scope, receive, send)
        finally:
            if tokens:
                reset_request_context(tokens)

app.add_middleware(RequestContextMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_origin_regex=_origin_regex,
    allow_credentials=_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -------------------------------------------------------
# AUTH MODELS
# -------------------------------------------------------
class _AuthBase(BaseModel):
    organization: str
    email: EmailStr
    password: str

    @field_validator("organization")
    @classmethod
    def _organization_not_empty(cls, value: str) -> str:
        cleaned = (value or "").strip()
        if not cleaned:
            raise ValueError("Organization is required.")
        return cleaned

    @field_validator("password")
    @classmethod
    def _password_min_length(cls, value: str) -> str:
        if not value or len(value) < 8:
            raise ValueError("Password must be at least 8 characters long.")
        return value

    def normalized_email(self) -> str:
        return str(self.email).strip().lower()

    def normalized_org(self) -> str:
        return (self.organization or "").strip().lower()


class SignupRequest(_AuthBase):
    pass


class LoginRequest(_AuthBase):
    pass


def _is_schema_missing_error(exc: Exception) -> bool:
    if PsycopgUndefinedTable and isinstance(getattr(exc, "orig", None), PsycopgUndefinedTable):
        return True
    message = str(exc).lower()
    return "relation" in message and "does not exist" in message


# -------------------------------------------------------
# SIGNUP
# -------------------------------------------------------
@app.post("/signup", status_code=status.HTTP_201_CREATED)
def signup_user(payload: SignupRequest, db: Session = Depends(get_db)):
    try:
        org = Organization.get_or_create(db, payload.organization)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except (ProgrammingError, OperationalError) as exc:
        if _is_schema_missing_error(exc):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database schema out of sync. Run Alembic migrations.",
            ) from exc
        raise
    except Exception as exc:
        if _is_schema_missing_error(exc):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database schema out of sync. Run Alembic migrations.",
            ) from exc
        raise

    try:
        password_hash = hash_password(payload.password)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:  # Defensive: ensure callers see a clean error.
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to process password securely.",
        ) from exc

    user = User(
        organization=org.display_name,
        organization_id=org.id,
        email=payload.normalized_email(),
        password_hash=password_hash,
    )

    try:
        db.add(user)
        db.flush()
        OrganizationMember.ensure_member(db, user.id, org.id, role="member")
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists.",
        )
    except (ProgrammingError, OperationalError) as exc:
        db.rollback()
        if _is_schema_missing_error(exc):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database schema out of sync. Run Alembic migrations.",
            ) from exc
        raise
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    db.refresh(user)
    return {"status": "created", "user": user.to_dict()}


# -------------------------------------------------------
# LOGIN
# -------------------------------------------------------
@app.post("/login")
def login_for_access_token(payload: LoginRequest, db: Session = Depends(get_db)):
    email = payload.normalized_email()
    organization = payload.normalized_org()

    user = db.query(User).filter(User.email == email).first()

    if not user:
        raise HTTPException(status_code=401, detail="Incorrect credentials.")

    stored_org = (user.organization or "").strip().lower()

    if stored_org != organization or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect credentials.")
    org_ids = OrganizationMember.user_org_ids(db, user.id)
    if not org_ids or user.organization_id not in org_ids:
        raise HTTPException(status_code=403, detail="Organization membership required.")

    access_token = auth.create_access_token(
        data={"sub": user.email, "uid": user.id, "org": user.organization, "org_id": user.organization_id}
    )

    return {"access_token": access_token, "token_type": "bearer"}


# -------------------------------------------------------
# GLOBAL EXCEPTION HANDLER
# -------------------------------------------------------
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger = logging.getLogger("app")
    logger.exception("Unhandled exception", exc_info=exc)

    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
        headers=_cors_headers_for_request(request),
    )


@app.exception_handler(OpenAIClientError)
async def openai_client_exception_handler(request: Request, exc: OpenAIClientError):
    return JSONResponse(
        status_code=503,
        content={"detail": str(exc)},
        headers=_cors_headers_for_request(request),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    try:
        raw_body = await request.body()
        body_text = raw_body.decode("utf-8", errors="ignore")
    except Exception:
        body_text = "<unreadable>"

    if len(body_text) > 5000:
        body_text = body_text[:5000] + "...<truncated>"

    try:
        parsed = json.loads(body_text) if body_text and body_text.startswith(("{", "[")) else None
        if isinstance(parsed, dict):
            for key in ("password", "token", "access_token", "authorization"):
                if key in parsed:
                    parsed[key] = "<redacted>"
            body_text = json.dumps(parsed)
    except Exception:
        pass

    _startup_logger.warning(
        "Validation error on %s %s: %s | body=%s",
        request.method,
        request.url.path,
        exc.errors(),
        body_text,
    )

    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "message": "Request validation failed."},
        headers=_cors_headers_for_request(request),
    )


# -------------------------------------------------------
# ROUTERS
# -------------------------------------------------------
app.include_router(image_router)
app.include_router(generate_from_story_router)
app.include_router(manual_capture_router)
app.include_router(enrichment_router)
app.include_router(url_enrichment_router)
app.include_router(rag_router)
app.include_router(debug_chroma_export_router)
app.include_router(generate_from_manual_testcase_router)
app.include_router(generate_page_methods_router)
app.include_router(generate_test_code_from_methods_router)
app.include_router(manual_add_metadata)

# merged additions from both files
app.include_router(manual_enrichment_router)        # from first file
app.include_router(projects_router)
app.include_router(markers_router)                 # from second file
app.include_router(run_tests_router, prefix="/tests")
app.include_router(report_router, prefix="/reports")
app.include_router(metrics_router, prefix="/metrics")  # from second file
app.include_router(jira_router)
app.include_router(testcases_router)
app.include_router(visualizer_router, prefix="/visualizer")
app.include_router(token_usage_router)


# -------------------------------------------------------
# MAIN SERVER
# -------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s: %(message)s",
    )
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("chromadb").setLevel(logging.WARNING)
    logging.getLogger("PIL").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("python_multipart").setLevel(logging.WARNING)
    logging.getLogger("watchfiles").setLevel(logging.ERROR)
    logging.getLogger("tqdm").setLevel(logging.WARNING)

    import uvicorn
    _configure_windows_playwright_runtime()

    uvicorn.run(
        "main:app",
        host=os.getenv("APP_HOST", "127.0.0.1"),
        port=int(os.getenv("APP_PORT", "8001")),
        reload=False,
        log_level="info",
    )
