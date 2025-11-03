import io
import os
import zipfile
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from db.models import Project
from db.session import get_db

router = APIRouter()


class ProjectDetails(BaseModel):
    project_name: str
    framework: str
    language: str


class ProjectActivateRequest(BaseModel):
    project_name: str


def _project_root(project_name: str) -> Path:
    backend_root = Path(__file__).resolve().parents[1]
    return backend_root / project_name.strip()


def _ensure_project_structure(project_name: str) -> dict:
    project_root = _project_root(project_name)
    data_dir = project_root / "data"
    runs_dir = project_root / "generated_runs"
    runs_src = runs_dir / "src"

    data_dir.mkdir(parents=True, exist_ok=True)
    runs_dir.mkdir(parents=True, exist_ok=True)
    (runs_src / "metadata").mkdir(parents=True, exist_ok=True)
    (runs_src / "ocr-dom-metadata").mkdir(parents=True, exist_ok=True)
    (runs_src / "pages").mkdir(parents=True, exist_ok=True)
    (runs_src / "tests").mkdir(parents=True, exist_ok=True)

    return {
        "project_root": str(project_root.resolve()),
        "data_dir": str(data_dir.resolve()),
        "generated_runs": str(runs_dir.resolve()),
        "src_dir": str(runs_src.resolve()),
        "chroma_path": str((data_dir / "chroma_db").resolve()),
    }


def _activate_env(project_paths: dict) -> None:
    os.environ["SMARTAI_PROJECT_DIR"] = project_paths["project_root"]
    os.environ["SMARTAI_SRC_DIR"] = project_paths["src_dir"]
    os.environ["SMARTAI_CHROMA_PATH"] = project_paths["chroma_path"]


def _clear_env_if_active(project_root: Path) -> None:
    """Unset SMARTAI_* env vars if they point at the deleted project."""
    resolved = str(project_root.resolve())
    if os.environ.get("SMARTAI_PROJECT_DIR") == resolved:
        for key in ("SMARTAI_PROJECT_DIR", "SMARTAI_SRC_DIR", "SMARTAI_CHROMA_PATH"):
            os.environ.pop(key, None)


@router.post("/projects/save-details")
def save_project_details(details: ProjectDetails, db: Session = Depends(get_db)):
    try:
        project = Project(
            project_name=details.project_name.strip(),
            framework=details.framework.strip(),
            language=details.language.strip(),
        )
        db.add(project)
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail=f"Project '{details.project_name.strip()}' already exists",
        )
    except ValueError as ve:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(ve))
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(exc))

    project_paths = {}
    try:
        project_paths = _ensure_project_structure(project.project_name)
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to prepare project directories: {exc}") from exc

    try:
        _activate_env(project_paths)
    except Exception:
        # Environment activation is best-effort; failures shouldn't prevent API success.
        pass

    payload = {
        "status": "success",
        "project": project.to_dict(),
        **project_paths,
    }

    return payload


@router.get("/projects")
def list_projects(db: Session = Depends(get_db)):
    projects = (
        db.query(Project)
        .order_by(Project.created_at.desc())
        .all()
    )
    return {"projects": [p.to_dict() for p in projects]}


@router.post("/projects/activate")
def activate_project(req: ProjectActivateRequest, db: Session = Depends(get_db)):
    name = (req.project_name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="project_name is required")

    project_key = Project.normalized_key(name)
    project = (
        db.query(Project)
        .filter(Project.project_key == project_key)
        .first()
    )
    if not project:
        raise HTTPException(status_code=404, detail=f"Project '{name}' not found")

    project_paths = _ensure_project_structure(project.project_name)
    try:
        _activate_env(project_paths)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to activate project: {exc}") from exc

    return {
        "status": "activated",
        "project": project.to_dict(),
        **project_paths,
    }


@router.get("/projects/{project_id}")
def get_project(project_id: int, db: Session = Depends(get_db)):
    project = (
        db.query(Project)
        .filter(Project.id == project_id)
        .first()
    )
    if not project:
        raise HTTPException(status_code=404, detail=f"Project with id '{project_id}' not found")

    try:
        project_paths = _ensure_project_structure(project.project_name)
    except Exception:
        project_paths = {}

    return {
        "project": project.to_dict(),
        "paths": project_paths,
    }


@router.delete("/projects/{project_id}")
def delete_project(project_id: int, db: Session = Depends(get_db)):
    project = (
        db.query(Project)
        .filter(Project.id == project_id)
        .first()
    )
    if not project:
        raise HTTPException(status_code=404, detail=f"Project with id '{project_id}' not found")

    project_root = _project_root(project.project_name)

    try:
        db.delete(project)
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete project: {exc}")

    # Best-effort cleanup of environment variables if the deleted project was active
    try:
        _clear_env_if_active(project_root)
    except Exception:
        pass

    return {"status": "deleted", "project_id": project_id}


@router.get("/projects/{project_id}/download")
def download_project(project_id: int, db: Session = Depends(get_db)):
    project = (
        db.query(Project)
        .filter(Project.id == project_id)
        .first()
    )
    if not project:
        raise HTTPException(status_code=404, detail=f"Project with id '{project_id}' not found")

    project_root = _project_root(project.project_name).resolve()
    if not project_root.exists() or not project_root.is_dir():
        raise HTTPException(status_code=404, detail=f"Project directory for '{project.project_name}' not found")

    buffer = io.BytesIO()
    base_prefix = Path(project.slug or project.project_name.strip() or f"project_{project_id}")

    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
        for file_path in project_root.rglob("*"):
            if file_path.is_file():
                arcname = base_prefix / file_path.relative_to(project_root)
                zipf.write(str(file_path), arcname=str(arcname))

    buffer.seek(0)
    filename = f"{base_prefix}.zip"

    return StreamingResponse(
        buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        },
    )
