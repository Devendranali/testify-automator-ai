from fastapi import APIRouter, HTTPException, Depends
import os
import sys
import subprocess
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from pydantic import BaseModel
from sqlalchemy.orm import Session

from utils.smart_ai_utils import ensure_smart_ai_module
from database.project_storage import DatabaseBackedProjectStorage
from database.session import get_db
from database.models import Project

router = APIRouter()


class RunStoryTestRequest(BaseModel):
    project_id: Optional[int] = None


def _org_slug(name: str) -> str:
    normalized = (name or "").strip().lower()
    return re.sub(r"[^a-z0-9_-]+", "-", normalized) or "default"


def _project_dir_segment(project: Project) -> str:
    base_slug = (getattr(project, "slug", None) or Project.normalized_key(project.project_name)).strip()
    base_slug = re.sub(r"[^a-z0-9_-]+", "-", base_slug.lower()) or "project"
    if project.id:
        return f"{project.id}-{base_slug}"
    return base_slug


def _project_root_dir(project: Project) -> Path:
    backend_root = Path(__file__).resolve().parents[1]
    org_segment = _org_slug(project.organization)
    org_root = backend_root / "organizations" / org_segment
    desired = org_root / _project_dir_segment(project)
    legacy = org_root / (project.project_name or "project")
    if desired.exists() or not legacy.exists():
        return desired
    return legacy


def _ensure_project_dirs(project: Project) -> dict[str, Path]:
    root = _project_root_dir(project)
    data_dir = root / "data"
    runs_dir = root / "generated_runs"
    src_dir = runs_dir / "src"
    root.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)
    runs_dir.mkdir(parents=True, exist_ok=True)
    src_dir.mkdir(parents=True, exist_ok=True)
    (src_dir / "metadata").mkdir(parents=True, exist_ok=True)
    (src_dir / "ocr-dom-metadata").mkdir(parents=True, exist_ok=True)
    (src_dir / "pages").mkdir(parents=True, exist_ok=True)
    (src_dir / "tests").mkdir(parents=True, exist_ok=True)
    chroma_path = data_dir / "chroma_db"
    chroma_path.mkdir(parents=True, exist_ok=True)
    return {
        "project_root": root,
        "src_dir": src_dir,
        "chroma_path": chroma_path,
    }


def _activate_project_env(project: Project, dirs: dict[str, Path]) -> None:
    os.environ["SMARTAI_PROJECT_DIR"] = str(dirs["project_root"])
    os.environ["SMARTAI_SRC_DIR"] = str(dirs["src_dir"])
    os.environ["SMARTAI_CHROMA_PATH"] = str(dirs["chroma_path"])
    if project.id:
        os.environ["SMARTAI_PROJECT_ID"] = str(project.id)


def _project_src_dir(project: Project) -> Path:
    return _project_root_dir(project) / "generated_runs" / "src"


def _candidate_src_dirs(project: Optional[Project] = None) -> list[Path]:
    dirs: list[Path] = []
    if project:
        try:
            proj_dirs = _ensure_project_dirs(project)
            dirs.append(proj_dirs["src_dir"])
        except Exception:
            pass
    env_src = os.environ.get("SMARTAI_SRC_DIR")
    if env_src:
        p = Path(env_src)
        if p.exists():
            dirs.append(p)
    backend_root = Path(__file__).resolve().parents[1]
    for child in backend_root.iterdir():
        try:
            cand = child / "generated_runs" / "src"
            if cand.exists():
                dirs.append(cand)
        except Exception:
            continue
    org_root = backend_root / "organizations"
    if org_root.exists():
        for sub in org_root.rglob("generated_runs"):
            try:
                src_dir = sub / "src"
                if src_dir.exists():
                    dirs.append(src_dir)
            except Exception:
                continue
    legacy = backend_root / "generated_runs" / "src"
    if legacy.exists():
        dirs.append(legacy)
    seen = set()
    uniq: list[Path] = []
    for d in dirs:
        resolved = d.resolve()
        if resolved not in seen:
            uniq.append(d)
            seen.add(resolved)
    return uniq


def _get_active_project(db: Session, requested_project_id: Optional[int] = None) -> Project:
    if requested_project_id:
        project = (
            db.query(Project)
            .filter(Project.id == requested_project_id)
            .first()
        )
        if not project:
            raise HTTPException(status_code=404, detail=f"Project id {requested_project_id} not found")
        dirs = _ensure_project_dirs(project)
        _activate_project_env(project, dirs)
        return project

    project_id_value = os.environ.get("SMARTAI_PROJECT_ID")
    if project_id_value:
        try:
            project = (
                db.query(Project)
                .filter(Project.id == int(project_id_value))
                .first()
            )
            if project:
                dirs = _ensure_project_dirs(project)
                _activate_project_env(project, dirs)
                return project
        except ValueError:
            pass

    project_dir = os.environ.get("SMARTAI_PROJECT_DIR")
    if project_dir:
        segment = Path(project_dir).name
        if "-" in segment:
            maybe_id = segment.split("-", 1)[0]
            if maybe_id.isdigit():
                project = (
                    db.query(Project)
                    .filter(Project.id == int(maybe_id))
                    .first()
                )
                if project:
                    dirs = _ensure_project_dirs(project)
                    _activate_project_env(project, dirs)
                    return project

        normalized_slug = Project.normalized_key(segment.replace("-", " ").replace("_", " "))
        project = (
            db.query(Project)
            .filter(Project.project_key == normalized_slug)
            .order_by(Project.created_at.desc())
            .first()
        )
        if project:
            dirs = _ensure_project_dirs(project)
            _activate_project_env(project, dirs)
            return project

    project_src_map: dict[Path, Project] = _build_project_src_map(db)
    if project_src_map:
        candidates = _candidate_src_dirs()
        for src_dir in candidates:
            try:
                resolved_src = src_dir.resolve()
            except Exception:
                continue
            matched_project = project_src_map.get(resolved_src)
            if not matched_project:
                continue
            dirs = _ensure_project_dirs(matched_project)
            _activate_project_env(matched_project, dirs)
            return matched_project

    raise HTTPException(status_code=400, detail="Active project not found. Activate a project before running tests.")


def _build_project_src_map(db: Session) -> dict[Path, Project]:
    mapping: dict[Path, Project] = {}
    projects = (
        db.query(Project)
        .order_by(Project.created_at.desc())
        .all()
    )
    for project in projects:
        candidate = _project_src_dir(project)
        if not candidate.exists():
            continue
        try:
            resolved = candidate.resolve()
        except Exception:
            continue
        if resolved not in mapping:
            mapping[resolved] = project
    return mapping


def _write_with_storage(path: Path, content: str, storage: Optional[DatabaseBackedProjectStorage], encoding: str = "utf-8") -> None:
    path.write_text(content, encoding=encoding)
    if not storage:
        return
    try:
        relative = path.relative_to(storage.base_dir)
    except ValueError:
        return
    storage.write_file(relative.as_posix(), content, encoding)


@router.post("/rag/run-generated-story-test")
def run_latest_generated_story_test(
    payload: Optional[RunStoryTestRequest] = None,
    db: Session = Depends(get_db),
):
    try:
        requested_project_id = payload.project_id if payload else None
        project = _get_active_project(db, requested_project_id=requested_project_id)

        candidates = _candidate_src_dirs(project)
        found: list[tuple[Path, Path]] = []
        for src in candidates:
            tdir = src / "tests"
            if not tdir.exists():
                continue
            # Recursively find all runnable scripts in subdirectories
            for pattern in ("*_script_*.py", "*_script.py"):
                for f in tdir.rglob(pattern):
                    if f.is_file():
                        found.append((src, f))
        if not found:
            for src in candidates:
                tdir = src / "tests"
                if not tdir.exists():
                    continue
                # Fallback to test files if no runnable scripts are found
                for f in sorted(tdir.rglob("test_*.py")):
                    if f.is_file():
                        found.append((src, f))
            if not found:
                searched = ", ".join(str((d / "tests").resolve()) for d in candidates) or "(no candidates)"
                raise HTTPException(status_code=404, detail=f"No generated script files (*_script_*.py, test_*.py) found. Searched: {searched}")

        src_dir, latest_ui_script = sorted(found, key=lambda p: p[1].stat().st_mtime, reverse=True)[0]

        storage = DatabaseBackedProjectStorage(project, src_dir, db)

        logs_dir = src_dir / "logs"
        meta_dir = src_dir / "metadata"
        logs_dir.mkdir(parents=True, exist_ok=True)
        meta_dir.mkdir(parents=True, exist_ok=True)
        log_file = logs_dir / f"test_output_{latest_ui_script.stem}.log"
        meta_file = meta_dir / f"execution_metadata_{latest_ui_script.stem}.json"

        try:
            os.environ["SMARTAI_SRC_DIR"] = str(src_dir)
            ensure_smart_ai_module(storage)
        except Exception:
            pass

        try:
            after_meta = meta_dir / "after_enrichment.json"
            before_meta = meta_dir / "before_enrichment.json"
            if not after_meta.exists():
                content_to_write = "[]"
                if before_meta.exists():
                    try:
                        content_to_write = before_meta.read_text(encoding="utf-8")
                    except Exception:
                        content_to_write = "[]"
                _write_with_storage(after_meta, content_to_write, storage)
        except Exception:
            pass

        env = os.environ.copy()
        env["PYTHONPATH"] = str(src_dir)
        
        # Correctly determine the relative path of the script for execution
        script_to_run = latest_ui_script.relative_to(src_dir)
        
        result = subprocess.run(
            [sys.executable, str(script_to_run)],
            cwd=src_dir,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        output = result.stdout + "\n" + result.stderr
        _write_with_storage(log_file, output, storage)
        status = "PASS" if result.returncode == 0 else "FAIL"

        error_lines = []
        in_summary = False
        for line in output.splitlines():
            if "Summary of failures:" in line:
                in_summary = True
                continue
            if in_summary:
                if line.strip().startswith("- "):
                    error_lines.append(line.strip())
                if not line.strip():
                    break

        meta_payload = json.dumps(
            {"status": status, "timestamp": datetime.now().isoformat()},
            indent=2,
        )
        _write_with_storage(meta_file, meta_payload, storage)

        return {
            "status": status,
            "log": output,
            "errors": error_lines,
            "executed_from": str(latest_ui_script),
            "log_file": str(log_file),
            "meta_file": str(meta_file),
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))