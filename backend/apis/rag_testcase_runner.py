from fastapi import APIRouter, HTTPException, Depends
import os, sys, subprocess, json
from datetime import datetime
from pathlib import Path
from typing import Optional

from utils.smart_ai_utils import ensure_smart_ai_module
from sqlalchemy.orm import Session

from database.project_storage import DatabaseBackedProjectStorage
from database.session import get_db
from database.models import Project

router = APIRouter()

def _candidate_src_dirs() -> list[Path]:
    dirs: list[Path] = []
    env_src = os.environ.get("SMARTAI_SRC_DIR")
    if env_src:
        p = Path(env_src)
        if p.exists():
            dirs.append(p)
    # Fallback: search under backend/*/generated_runs/src
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
    # Legacy repo-level path
    legacy = backend_root / "generated_runs" / "src"
    if legacy.exists():
        dirs.append(legacy)
    # De-dup while preserving order
    seen = set()
    uniq: list[Path] = []
    for d in dirs:
        if d.resolve() not in seen:
            uniq.append(d)
            seen.add(d.resolve())
    return uniq

def _get_active_project(db: Session) -> Project:
    project_id_value = os.environ.get("SMARTAI_PROJECT_ID")
    if project_id_value:
        try:
            project = (
                db.query(Project)
                .filter(Project.id == int(project_id_value))
                .first()
            )
            if project:
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
                    os.environ["SMARTAI_PROJECT_ID"] = str(project.id)
                    return project

        normalized_slug = Project.normalized_key(segment.replace("-", " ").replace("_", " "))
        project = (
            db.query(Project)
            .filter(Project.project_key == normalized_slug)
            .order_by(Project.created_at.desc())
            .first()
        )
        if project:
            os.environ["SMARTAI_PROJECT_ID"] = str(project.id)
            return project

    raise HTTPException(status_code=400, detail="Active project not found. Activate a project before running tests.")


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
def run_latest_generated_story_test(db: Session = Depends(get_db)):
    try:
        # 1. Locate latest ui_script_*.py across candidate src dirs
        candidates = _candidate_src_dirs()
        found: list[tuple[Path, Path]] = []  # (src_dir, ui_script_file)
        for src in candidates:
            tdir = src / "tests"
            if not tdir.exists():
                continue
            for f in tdir.glob("ui_script_*.py"):
                if f.is_file():
                    found.append((src, f))
        if not found:
            searched = ", ".join(str((d / 'tests').resolve()) for d in candidates) or "(no candidates)"
            raise HTTPException(status_code=404, detail=f"No generated ui_script_*.py files found. Searched: {searched}")
        # pick latest by mtime
        src_dir, latest_ui_script = sorted(found, key=lambda p: p[1].stat().st_mtime, reverse=True)[0]

        # Identify active project + storage for persistence
        project = _get_active_project(db)
        storage = DatabaseBackedProjectStorage(project, src_dir, db)

        # 2. Prepare logs and meta output under the same src dir
        logs_dir = src_dir / "logs"
        meta_dir = src_dir / "metadata"
        logs_dir.mkdir(parents=True, exist_ok=True)
        meta_dir.mkdir(parents=True, exist_ok=True)
        log_file = logs_dir / f"test_output_{latest_ui_script.stem}.log"
        meta_file = meta_dir / f"execution_metadata_{latest_ui_script.stem}.json"

        # Ensure SmartAI lib is present for this src_dir (so imports in ui_script/pages work)
        try:
            os.environ["SMARTAI_SRC_DIR"] = str(src_dir)
            ensure_smart_ai_module(storage)
        except Exception:
            pass

        # Ensure metadata file referenced by ui_script exists (fallback to before_enrichment or empty list)
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

        # 3. Run the script like: PYTHONPATH=<src_dir> python tests/ui_script_N.py
        env = os.environ.copy()
        env["PYTHONPATH"] = str(src_dir)
        result = subprocess.run(
            [sys.executable, f"tests/{latest_ui_script.name}"],
            cwd=src_dir,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        output = result.stdout + "\n" + result.stderr
        _write_with_storage(log_file, output, storage)
        status = "PASS" if result.returncode == 0 else "FAIL"

        # --- Parse error summary from output ---
        error_lines = []
        in_summary = False
        for line in output.splitlines():
            if "Summary of failures:" in line:
                in_summary = True
                continue
            if in_summary:
                if line.strip().startswith("- "):
                    error_lines.append(line.strip())
                # Optionally: stop at blank line or next heading
                if not line.strip():
                    break

        meta_payload = json.dumps(
            {"status": status, "timestamp": datetime.now().isoformat()},
            indent=2
        )
        _write_with_storage(meta_file, meta_payload, storage)

        return {
            "status": status,
            "log": output,
            "errors": error_lines,  # <-- errors summary lines!
            "executed_from": str(latest_ui_script),
            "log_file": str(log_file),
            "meta_file": str(meta_file),
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
