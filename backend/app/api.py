# app/api.py

from fastapi import FastAPI, Body, HTTPException, Depends, Query
from fastapi.staticfiles import StaticFiles
from orchestrator.orchestrator import send_message

import subprocess
import sys
import shutil
from pathlib import Path
from sqlalchemy.orm import Session

from apis.projects_api import _ensure_project_structure, get_current_user, get_project_by_projectId
from apis.run_test_api import _resolve_requested_script_path
from utils.allure_cli import build_allure_generate_cmd
from database.models import User
from database.session import get_db

app = FastAPI()

# Directory where generated HTML reports will be placed and served from
reports_dir = Path(__file__).resolve().parent.parent / "static_reports"
reports_dir.mkdir(parents=True, exist_ok=True)
app.mount("/reports", StaticFiles(directory=str(reports_dir)), name="reports")

def _resolve_safe_test_path(src_root: Path, test: str) -> Path:
    tests_dir = src_root / "tests"
    if not tests_dir.is_dir():
        raise HTTPException(status_code=404, detail="Tests directory not found.")
    requested = Path(test or "")
    if requested.is_absolute():
        raise HTTPException(status_code=400, detail="Invalid test path.")
    if ".." in requested.parts:
        raise HTTPException(status_code=400, detail="Invalid test path.")
    try:
        resolved = _resolve_requested_script_path(tests_dir, test)
    except HTTPException:
        raise HTTPException(status_code=403, detail="Invalid test path.")
    if not resolved.exists():
        raise HTTPException(status_code=404, detail="Test file not found.")
    return resolved

@app.post("/mcp/")
def mcp_endpoint(language: str = Body(...), action: str = Body(...), payload: dict = Body(...)):
    resp = send_message(language, action, payload)
    return resp.__dict__


@app.get("/tests/report")
def generate_test_report(
    project_id: int = Query(..., description="Project ID to scope the run to."),
    test: str = "tests/test_1.py",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate an Allure HTML report for a single test file and return a URL to view it.

    The function runs pytest for the requested `test` inside `generated_runs/src`,
    collects Allure results, generates HTML using the `allure` CLI and places the
    generated HTML under `backend/static_reports/{test_name}` which is served at
    `/reports/{test_name}/index.html`.
    """
    # Resolve paths
    project = get_project_by_projectId(db, project_id, current_user)
    project_paths = _ensure_project_structure(project)
    src_root = Path(project_paths["src_dir"])
    if not src_root.exists():
        raise HTTPException(status_code=404, detail="Source dir not found.")

    results_dir = src_root / "allure-results-temp"
    if results_dir.exists():
        shutil.rmtree(results_dir)
    results_dir.mkdir(parents=True, exist_ok=True)

    resolved_test = _resolve_safe_test_path(src_root, test)
    try:
        test_path = resolved_test.relative_to(src_root).as_posix()
    except ValueError:
        raise HTTPException(status_code=403, detail="Invalid test path.")
    test_name = resolved_test.stem
    html_out = reports_dir / str(project_id) / test_name
    if html_out.exists():
        shutil.rmtree(html_out)
    html_out.mkdir(parents=True, exist_ok=True)

    pytest_cmd = [sys.executable, "-m", "pytest", test_path, f"--alluredir={results_dir}"]
    try:
        subprocess.run(pytest_cmd, cwd=src_root, check=False)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to run pytest: {e}")

    # Require Allure CLI to be available
    try:
        gen_cmd = build_allure_generate_cmd(results_dir, html_out)
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="Allure CLI not found on PATH. Install it and ensure `allure` is available.")
    try:
        subprocess.run(gen_cmd, cwd=src_root, check=True)
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"Allure generate failed: {e}")

    report_url = f"/reports/{project_id}/{test_name}/index.html"
    return {"report_url": report_url}


@app.get("/tests/run")
def run_all_tests(
    project_id: int = Query(..., description="Project ID to scope the run to."),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Run all tests under `generated_runs/src/tests` and return aggregated report URL."""
    project = get_project_by_projectId(db, project_id, current_user)
    project_paths = _ensure_project_structure(project)
    src_root = Path(project_paths["src_dir"])
    if not src_root.exists():
        raise HTTPException(status_code=404, detail="Source dir not found.")

    results_dir = src_root / "allure-results"
    if results_dir.exists():
        shutil.rmtree(results_dir)
    results_dir.mkdir(parents=True, exist_ok=True)

    pytest_cmd = [sys.executable, "-m", "pytest", "tests", f"--alluredir={results_dir}"]
    try:
        subprocess.run(pytest_cmd, cwd=src_root, check=False)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to run pytest: {e}")

    html_out = reports_dir / str(project_id) / "all"
    if html_out.exists():
        shutil.rmtree(html_out)
    html_out.mkdir(parents=True, exist_ok=True)
    try:
        gen_cmd = build_allure_generate_cmd(results_dir, html_out)
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="Allure CLI not found on PATH. Install it and ensure `allure` is available.")

    try:
        subprocess.run(gen_cmd, cwd=src_root, check=True)
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"Allure generate failed: {e}")

    return {"report_url": f"/reports/{project_id}/all/index.html"}
