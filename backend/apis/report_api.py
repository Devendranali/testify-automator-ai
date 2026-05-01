#report_api.py 
from datetime import datetime, timedelta, timezone
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Response, Query, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from urllib.parse import urlparse
import mimetypes
import subprocess
import os

from sqlalchemy.orm import Session
from jose import JWTError, jwt
from pydantic import BaseModel, ValidationError

import auth
from .projects_api import _ensure_project_structure, get_project_by_projectId, TokenPayload
from database.models import OrganizationMember
from utils.allure_cli import build_allure_generate_cmd
from database.models import User
from database.session import get_db
from config.settings import get_backend_public_base_url

router = APIRouter()
_REPORT_SESSION_COOKIE = "report_session"
_REPORT_SESSION_EXPIRE_MINUTES = int(os.getenv("REPORT_SESSION_EXPIRE_MINUTES", "5"))


class ReportSessionPayload(BaseModel):
    sub: str
    uid: int
    org: str | None = None
    org_id: int | None = None
    pid: int
    typ: str
    exp: datetime

def _generate_allure_report_if_possible(src_dir: Path) -> tuple[bool, str | None]:
    results_dir = src_dir / "allure-results"
    report_dir = src_dir / "allure-report"
    if report_dir.exists() and (report_dir / "index.html").exists():
        return True, None
    if not results_dir.exists():
        return False, "Allure results directory not found."
    # Only attempt generation if there are result files.
    if not list(results_dir.glob("*-result.json")):
        return False, "No Allure result files found."
    report_dir.mkdir(parents=True, exist_ok=True)
    try:
        cmd = build_allure_generate_cmd(results_dir, report_dir)
    except FileNotFoundError:
        return False, "Allure CLI not found on PATH."
    result = subprocess.run(cmd, cwd=str(src_dir), text=True, capture_output=True)
    if (report_dir / "index.html").exists():
        return True, None
    detail = (result.stderr or result.stdout or "").strip()
    if detail:
        return False, detail
    return False, "Allure report generation failed."

def _extract_bearer_token(request: Request | None) -> str | None:
    if request is None:
        return None
    auth_header = request.headers.get("authorization") or ""
    if auth_header.lower().startswith("bearer "):
        return auth_header.split(" ", 1)[1].strip()
    query_token = request.query_params.get("token") or request.query_params.get("access_token")
    if query_token:
        return query_token
    return None


def _extract_report_session_token(request: Request | None) -> str | None:
    if request is None:
        return None
    return request.cookies.get(_REPORT_SESSION_COOKIE)


def _load_user_from_token_payload(db: Session, token_data: TokenPayload | ReportSessionPayload) -> User:
    credentials_exception = HTTPException(
        status_code=401,
        detail="Invalid authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    user = (
        db.query(User)
        .filter(User.id == token_data.uid, User.email == str(token_data.sub).lower())
        .first()
    )
    if not user:
        raise credentials_exception
    if (user.organization or "").strip().lower() != (token_data.org or "").strip().lower():
        raise credentials_exception
    if token_data.org_id is not None and user.organization_id != token_data.org_id:
        raise credentials_exception
    org_ids = OrganizationMember.user_org_ids(db, user.id)
    if not org_ids:
        raise credentials_exception
    if token_data.org_id is not None and token_data.org_id not in org_ids:
        raise credentials_exception
    return user


def _get_current_user_from_request(
    request: Request,
    db: Session,
    project_id: int,
) -> User:
    bearer_token = _extract_bearer_token(request)
    if bearer_token:
        try:
            payload = jwt.decode(bearer_token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
            token_data = TokenPayload(**payload)
        except (JWTError, ValidationError) as exc:
            raise HTTPException(
                status_code=401,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc
        return _load_user_from_token_payload(db, token_data)

    report_session = _extract_report_session_token(request)
    if not report_session:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(report_session, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
        token_data = ReportSessionPayload(**payload)
    except (JWTError, ValidationError) as exc:
        raise HTTPException(status_code=401, detail="Invalid report session") from exc
    if token_data.typ != "report_session" or token_data.pid != project_id:
        raise HTTPException(status_code=401, detail="Invalid report session")
    return _load_user_from_token_payload(db, token_data)


def _report_root_path(request: Request | None) -> str:
    default_base = None
    if request is not None:
        try:
            default_base = str(request.base_url).rstrip("/")
        except Exception:
            default_base = None
    try:
        public_base = get_backend_public_base_url(default_base)
    except Exception:
        public_base = default_base or ""
    if public_base:
        try:
            public_path = urlparse(public_base).path or ""
        except Exception:
            public_path = ""
        if public_path and public_path != "/":
            return "/" + public_path.strip("/")

    root = ""
    if request is not None:
        try:
            root = request.scope.get("root_path") or ""
        except Exception:
            root = ""
        if not root:
            forwarded_prefix = (request.headers.get("x-forwarded-prefix") or "").split(",")[0].strip()
            if forwarded_prefix:
                root = forwarded_prefix

    root = "/" + root.strip("/")
    if root == "/":
        root = ""
    return root


def _report_cookie_path(request: Request | None) -> str:
    return f"{_report_root_path(request)}/reports"


def _report_cookie_secure(request: Request | None) -> bool:
    override = (os.getenv("REPORT_COOKIE_SECURE") or "").strip().lower()
    if override in {"1", "true", "yes", "on"}:
        return True
    if override in {"0", "false", "no", "off"}:
        return False
    if request is None:
        return False
    forwarded_proto = (request.headers.get("x-forwarded-proto") or "").split(",")[0].strip().lower()
    scheme = forwarded_proto or (request.url.scheme or "").lower()
    return scheme == "https"


def _build_report_session_token(user: User, project_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=_REPORT_SESSION_EXPIRE_MINUTES)
    payload = {
        "sub": user.email,
        "uid": user.id,
        "org": user.organization,
        "org_id": user.organization_id,
        "pid": project_id,
        "typ": "report_session",
        "exp": expire,
    }
    return jwt.encode(payload, auth.SECRET_KEY, algorithm=auth.ALGORITHM)


def _set_report_cookie(response: Response, session_token: str, request: Request | None = None) -> None:
    secure_cookie = _report_cookie_secure(request)
    response.set_cookie(
        key=_REPORT_SESSION_COOKIE,
        value=session_token,
        httponly=True,
        samesite="none" if secure_cookie else "lax",
        secure=secure_cookie,
        path=_report_cookie_path(request),
        max_age=_REPORT_SESSION_EXPIRE_MINUTES * 60,
    )


@router.post("/session/{project_id}")
def create_report_session(
    project_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    current_user = _get_current_user_from_request(request, db, project_id)
    get_project_by_projectId(db, project_id, current_user)
    session_token = _build_report_session_token(current_user, project_id)
    report_base = _report_cookie_path(request)
    response = JSONResponse(content={"report_url": f"{report_base}/view/{project_id}/"})
    _set_report_cookie(response, session_token, request)
    return response


@router.get("/session/{project_id}")
def create_report_session_redirect(
    project_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """Create a short-lived report session and redirect to the report view.
    Accepts an access token via query string for popup navigations.
    """
    current_user = _get_current_user_from_request(request, db, project_id)
    get_project_by_projectId(db, project_id, current_user)
    session_token = _build_report_session_token(current_user, project_id)
    report_base = _report_cookie_path(request)
    response = RedirectResponse(url=f"{report_base}/view/{project_id}/", status_code=302)
    _set_report_cookie(response, session_token, request)
    return response


@router.get("/latest")
def get_latest_report(
    project_id: int = Query(..., description="Project ID to scope the report to"),
    request: Request = None,
    db: Session = Depends(get_db),
):
    """
    Return the latest available report HTML.
    Prefers Allure HTML at generated_runs/src/allure-report/index.html,
    otherwise falls back to generated_runs/src/report.html.
    """
    current_user = _get_current_user_from_request(request, db, project_id)
    project = get_project_by_projectId(db, project_id, current_user)
    project_paths = _ensure_project_structure(project)
    src_dir = Path(project_paths["src_dir"])
    ok, detail = _generate_allure_report_if_possible(src_dir)
    allure_index = src_dir / "allure-report" / "index.html"
    html_fallback = src_dir / "index.html"

    # Keep this endpoint for compatibility but prefer the HTML-serving endpoints below.
    if allure_index.exists():
        html = allure_index.read_text(encoding="utf-8")
        return Response(content=html, media_type="text/html")
    if html_fallback.exists():
        html = html_fallback.read_text(encoding="utf-8")
        return Response(content=html, media_type="text/html")

    if detail:
        raise HTTPException(status_code=500, detail=detail)
    return {"error": "No report found. Run tests first."}


def _get_report_dir(project_id: int, db: Session, current_user: User) -> Path:
    """Return the directory that should be served for report assets.
    Prefers `allure-report` inside generated src; otherwise uses src root (for pytest-html fallback).
    """
    project = get_project_by_projectId(db, project_id, current_user)
    project_paths = _ensure_project_structure(project)
    src_dir = Path(project_paths["src_dir"])
    allure_dir = src_dir / "allure-report"
    if allure_dir.exists():
        return allure_dir
    return src_dir

@router.get("/view/{project_id}/{path:path}")
def serve_allure_report(
    project_id: int,
    path: str = "",
    request: Request = None,
    db: Session = Depends(get_db),
):
    current_user = _get_current_user_from_request(request, db, project_id)
    project = get_project_by_projectId(db, project_id, current_user)
    project_paths = _ensure_project_structure(project)

    src_dir = Path(project_paths["src_dir"])
    ok, detail = _generate_allure_report_if_possible(src_dir)
    report_dir = src_dir / "allure-report"

    if not path or path.endswith("/"):
        path = "index.html"

    file_path = report_dir / path

    if not file_path.exists() or not file_path.is_file():
        if detail:
            raise HTTPException(status_code=500, detail=detail)
        raise HTTPException(status_code=404, detail="Allure report file not found")

    if file_path.suffix.lower() in {".html", ".htm"}:
        html = file_path.read_text(encoding="utf-8")
        return Response(content=html, media_type="text/html")
    return FileResponse(file_path)


@router.get("/{asset_path:path}")
def report_assets(
    asset_path: str,
    project_id: int = Query(..., description="Project ID to scope the report assets to"),
    request: Request = None,
    db: Session = Depends(get_db),
):
    """Serve static assets referenced by the report (styles, js, images).
    This catches requests like `/reports/static/js/app.js` and resolves them
    relative to the selected report directory.
    """
    current_user = _get_current_user_from_request(request, db, project_id)
    report_dir = _get_report_dir(project_id, db, current_user)
    # Prevent path traversal by resolving and ensuring under report_dir
    candidate = (report_dir / asset_path).resolve()
    try:
        report_dir_resolved = report_dir.resolve()
    except Exception:
        raise HTTPException(status_code=404, detail="Invalid report directory")
    if not str(candidate).startswith(str(report_dir_resolved)):
        raise HTTPException(status_code=403, detail="Forbidden")
    if not candidate.exists():
        raise HTTPException(status_code=404, detail="Asset not found")
    mime, _ = mimetypes.guess_type(str(candidate))
    return FileResponse(candidate, media_type=mime or "application/octet-stream")

@router.get("/all")
def list_reports(
    project_id: int = Query(..., description="Project ID to scope the reports to"),
    request: Request = None,
    db: Session = Depends(get_db),
):
    """
    List available report artifacts under generated_runs/src.
    """
    current_user = _get_current_user_from_request(request, db, project_id)
    project = get_project_by_projectId(db, project_id, current_user)
    project_paths = _ensure_project_structure(project)
    src_dir = Path(project_paths["src_dir"])
    allure_report = src_dir / "allure-report" / "index.html"
    html_fallback = src_dir / "index.html"

    reports = []
    if allure_report.exists():
        reports.append({"type": "allure", "path": str(allure_report)})
    if html_fallback.exists():
        reports.append({"type": "html", "path": str(html_fallback)})

    return {"reports": reports}
