import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import traceback
import asyncio
import subprocess
import logging

from dotenv import load_dotenv

load_dotenv()

from fastapi.responses import JSONResponse
from fastapi.requests import Request
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from apis.image_text_api import router as image_router
from apis.chroma_debug_api import router as debug_chroma_export_router
from apis.enrichment_api import router as enrichment_router
from apis.rag_testcase_runner import router as rag_router
from apis.generate_from_story import router as generate_from_story_router
from apis.generate_page_methods import router as generate_page_methods_router
from apis.generate_from_manual_testcases import router as generate_from_manual_testcase_router
from apis.generate_testcases_from_methods import router as generate_test_code_from_methods_router
from apis.manual_add_metadata import router as manual_add_metadata
# from apis.manual_enrichment_api import router as manual_enrichment_router
from apis.projects_api import router as projects_router
from apis.run_test_api import router as run_tests_router
from apis.metrics_api import router as metrics_router
from apis.report_api import router as report_router
from apis.visualizer_api import router as visualizer_router
import auth
from db.models import User
from db.session import Base, engine, get_db
from utils.security import hash_password, verify_password

# Ensure schema exists before handling traffic (Alembic should manage in production).
if os.getenv("SQLALCHEMY_SKIP_AUTO_INIT", "0") not in {"1", "true", "True"}:
    # Only auto-create tables for SQLite (Postgres should rely on Alembic/migrations).
    backend_name = getattr(getattr(engine, "url", None), "get_backend_name", lambda: None)()
    if backend_name == "sqlite":
        try:
            Base.metadata.create_all(bind=engine)
        except Exception as db_init_err:
            print("Database initialization failed:", db_init_err)
    else:
        print("Skipping SQLAlchemy auto-creation for non-SQLite database; run Alembic migrations instead.")

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "0"
    try:
        subprocess.run(["playwright", "install", "chromium"], check=True)
    except Exception as e:
        print("Playwright install failed:", e)

# ✅ FastAPI app initialization
app = FastAPI(title="AI Test Extractor")

# Note: static reports are not mounted here — frontend opens generated_reports directly via file:// URIs.


# origins = [
#     "http://localhost:3000",
#     "https://www.saucedemo.com",
#     "http://localhost:3001",
#     "http://localhost:3001",
# ]


app.add_middleware(
    CORSMiddleware,
    # allow_origins=origins,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
        return str(self.email).lower()

    def normalized_org(self) -> str:
        return self.organization.strip().lower()


class SignupRequest(_AuthBase):
    pass


class LoginRequest(_AuthBase):
    pass


@app.post("/signup", status_code=status.HTTP_201_CREATED)
def signup_user(payload: SignupRequest, db: Session = Depends(get_db)):
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
        organization=payload.organization.strip(),
        email=payload.normalized_email(),
        password_hash=password_hash,
    )
    try:
        db.add(user)
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists.",
        )
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    db.refresh(user)
    return {"status": "created", "user": user.to_dict()}


@app.post("/login")
def login_for_access_token(payload: LoginRequest, db: Session = Depends(get_db)):
    email = payload.normalized_email()
    organization = payload.normalized_org()

    user = (
        db.query(User)
        .filter(User.email == email)
        .first()
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect credentials.",
        )

    stored_org = (user.organization or "").strip().lower()
    if stored_org != organization or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect credentials.",
        )

    access_token = auth.create_access_token(
        data={"sub": user.email, "uid": user.id, "org": user.organization}
    )
    return {"access_token": access_token, "token_type": "bearer"}


# ✅ Global exception handler with CORS headers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    print("❌ Unhandled Exception:")
    traceback.print_exc()

    
    headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Credentials": "true",
    }

    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)},
        headers=headers
    )

# ✅ Include API routers
app.include_router(image_router)
app.include_router(generate_from_story_router)
app.include_router(enrichment_router)
app.include_router(rag_router)
app.include_router(debug_chroma_export_router)
app.include_router(generate_from_manual_testcase_router)
app.include_router(generate_page_methods_router)
app.include_router(generate_test_code_from_methods_router)
app.include_router(manual_add_metadata)
# app.include_router(manual_enrichment_router)
app.include_router(projects_router)
app.include_router(run_tests_router, prefix="/tests")
app.include_router(report_router, prefix="/reports")
app.include_router(visualizer_router, prefix="/visualizer")
app.include_router(metrics_router, prefix="/metrics")



# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run("main:app", host="127.0.0.1", port=8001, reload=False)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,  # 👈 Show only INFO and above
        format="%(levelname)s: %(message)s"
    )    
    # Reduce noise from third-party libraries
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("chromadb").setLevel(logging.WARNING)
    logging.getLogger("PIL").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("python_multipart").setLevel(logging.WARNING)
    # logging.getLogger("uvicorn").setLevel(logging.INFO)            # Default server logs
    # logging.getLogger("uvicorn.access").setLevel(logging.WARNING)  # Access logs
    # logging.getLogger("httpcore").setLevel(logging.WARNING)        # HTTP-level logs
    logging.getLogger("watchfiles").setLevel(logging.ERROR)
    logging.getLogger("tqdm").setLevel(logging.WARNING)

    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8001, reload=False, log_level="info")
