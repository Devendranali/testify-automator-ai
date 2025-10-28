from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from pathlib import Path
from datetime import datetime
import json
import os

router = APIRouter()


class ProjectDetails(BaseModel):
    project_name: str
    framework: str
    language: str


def _data_file() -> Path:
    backend_root = Path(__file__).resolve().parents[1]
    data_dir = backend_root / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "projects.json"


@router.post("/projects/save-details")
def save_project_details(details: ProjectDetails):
    try:
        if not details.project_name.strip():
            raise HTTPException(status_code=400, detail="project_name is required")

        record = {
            "project_name": details.project_name.strip(),
            "framework": details.framework.strip(),
            "language": details.language.strip(),
            "created_at": datetime.utcnow().isoformat(),
        }

        df = _data_file()
        try:
            existing = json.loads(df.read_text(encoding="utf-8")) if df.exists() else []
            if not isinstance(existing, list):
                existing = []
        except Exception:
            existing = []

        # Validate duplicate project name (case-insensitive)
        desired = record["project_name"].lower()
        for e in existing:
            try:
                if (e or {}).get("project_name", "").strip().lower() == desired:
                    raise HTTPException(status_code=409, detail=f"Project '{record['project_name']}' already exists")
            except Exception:
                continue

        existing.append(record)
        df.write_text(json.dumps(existing, indent=2), encoding="utf-8")

        # Create per-project folder structure only now (on demand)
        backend_root = Path(__file__).resolve().parents[1]
        project_root = backend_root / details.project_name.strip()
        data_dir = project_root / "data"
        runs_dir = project_root / "generated_runs"
        runs_src = runs_dir / "src"
        try:
            data_dir.mkdir(parents=True, exist_ok=True)
            runs_dir.mkdir(parents=True, exist_ok=True)
            # Prepare common src subfolders used by enrichment/test flows
            (runs_src / "metadata").mkdir(parents=True, exist_ok=True)
            (runs_src / "ocr-dom-metadata").mkdir(parents=True, exist_ok=True)
            (runs_src / "pages").mkdir(parents=True, exist_ok=True)
            (runs_src / "tests").mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

        # Activate this project for the current process so subsequent endpoints write under it
        try:
            import os as _os
            _os.environ["SMARTAI_PROJECT_DIR"] = str(project_root.resolve())
            _os.environ["SMARTAI_SRC_DIR"] = str(runs_src.resolve())
            _os.environ["SMARTAI_CHROMA_PATH"] = str((data_dir / "chroma_db").resolve())
        except Exception:
            pass

        return {
            "status": "success",
            "project": record,
            "project_root": str(project_root.resolve()),
            "data_dir": str(data_dir.resolve()),
            "generated_runs": str(runs_dir.resolve()),
            "src_dir": str(runs_src.resolve()),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/projects")
def list_projects():
    """Return saved projects from backend/data/projects.json (if present)."""
    try:
        df = _data_file()
        if not df.exists():
            return {"projects": []}
        data = json.loads(df.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            data = []
        return {"projects": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class ProjectActivateRequest(BaseModel):
    project_name: str


@router.post("/projects/activate")
def activate_project(req: ProjectActivateRequest):
    """Activate an existing project so all subsequent endpoints use its paths.

    Sets SMARTAI_PROJECT_DIR, SMARTAI_SRC_DIR, SMARTAI_CHROMA_PATH based on the
    project folder layout created by /projects/save-details.
    """
    name = (req.project_name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="project_name is required")
    backend_root = Path(__file__).resolve().parents[1]
    project_root = backend_root / name
    data_dir = project_root / "data"
    runs_src = project_root / "generated_runs" / "src"

    if not project_root.exists() or not runs_src.exists():
        raise HTTPException(status_code=404, detail=f"Project '{name}' not found or not initialized")

    try:
        os.environ["SMARTAI_PROJECT_DIR"] = str(project_root.resolve())
        os.environ["SMARTAI_SRC_DIR"] = str(runs_src.resolve())
        os.environ["SMARTAI_CHROMA_PATH"] = str((data_dir / "chroma_db").resolve())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to activate project: {e}")

    return {
        "status": "activated",
        "project_name": name,
        "project_root": str(project_root.resolve()),
        "src_dir": str(runs_src.resolve()),
        "data_dir": str(data_dir.resolve()),
        "chroma_path": str((data_dir / "chroma_db").resolve()),
    }
