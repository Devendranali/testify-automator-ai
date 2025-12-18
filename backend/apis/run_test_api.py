#run_test_api.py
import json
import os
import shutil
import subprocess
import sys
import mimetypes
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from database.models import ProjectAllureChart, ProjectAllureResult
from database.session import get_db
from utils.project_context import current_project_id

from metrics.collector import collect_run_summary
from metrics.store import MetricsStore

router = APIRouter()


def _candidate_src_dirs() -> list[Path]:
    """
    Mirror the search strategy from rag_testcase_runner so we resolve
    the same generated source directory the UI scripts live in.
    """
    dirs: list[Path] = []
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

def _resolve_latest_src_dir() -> Path:
    candidates = _candidate_src_dirs()
    found: list[tuple[Path, Path]] = []
    for src in candidates:
        tdir = src / "tests"
        if not tdir.exists():
            continue
        for pattern in ("ui_script_*.py", "ui_script.py", "ui_script*.py"):
            for f in tdir.glob(pattern):
                if f.is_file():
                    found.append((src, f))
    if not found:
        searched = ", ".join(str((d / "tests").resolve()) for d in candidates) or "(no candidates)"
        raise HTTPException(status_code=404, detail=f"No generated ui_script files found. Searched: {searched}")
    src_dir, _ = sorted(found, key=lambda item: item[1].stat().st_mtime, reverse=True)[0]
    return src_dir


def _generate_allure_visualizations(allure_results: Path):
    """Run the Allure visualizer script to populate `allure_reports/` after new JSON files land."""
    repo_root = Path(__file__).resolve().parents[2]
    visualizer_script = repo_root / "allure_reports" / "allure_visualizer.py"
    if not visualizer_script.exists():
        print(f"Allure visualizer script missing at {visualizer_script}")
        return

    try:
        subprocess.run(
            [
                sys.executable,
                str(visualizer_script),
                "--results-dir",
                str(allure_results),
                "--interactive",
            ],
            cwd=str(repo_root),
            check=True,
        )
        print("Allure visualizer completed successfully.")
    except subprocess.CalledProcessError as exc:
        print("Allure visualizer failed:", exc)
    except Exception as exc:
        print("Unexpected error running Allure visualizer:", exc)


def _record_run_metrics(allure_results: Path) -> Optional[Dict[str, Any]]:
    try:
        summary = collect_run_summary(allure_results)
        if summary:
            store = MetricsStore()
            store.record_run(summary)
            return summary
    except Exception as exc:
        print("Failed to record metrics:", exc)
    return None


_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
_HTML_EXTENSION = ".html"


def _chart_asset_type(path: Path) -> Optional[str]:
    suffix = path.suffix.lower()
    if suffix in _IMAGE_EXTENSIONS:
        return "image"
    if suffix == _HTML_EXTENSION:
        if path.name == "interactive_charts.html":
            return "dashboard"
        return "interactive"
    return None


def _friendly_chart_label(chart_key: str) -> str:
    if chart_key.lower() == "interactive_charts":
        return "Interactive Dashboard"
    return chart_key.replace("_", " ").strip().title()


def _sync_project_allure_charts(project_id: int, src_dir: Path, db: Session) -> None:
    charts_dir = src_dir / "allure_charts"
    if not charts_dir.is_dir():
        return
    project_root = src_dir.parent.parent if len(src_dir.parents) >= 2 else None
    project_root = project_root.resolve() if project_root else charts_dir.parent

    db.query(ProjectAllureChart).filter(ProjectAllureChart.project_id == project_id).delete(synchronize_session=False)
    db.flush()

    for asset in sorted(charts_dir.iterdir()):
        if not asset.is_file():
            continue
        asset_type = _chart_asset_type(asset)
        if not asset_type:
            continue
        try:
            relative_path = asset.relative_to(project_root).as_posix()
        except ValueError:
            relative_path = asset.as_posix()

        media_type, _ = mimetypes.guess_type(str(asset))
        media_type = media_type or "application/octet-stream"
        chart_key = asset.stem
        record = ProjectAllureChart(
            project_id=project_id,
            chart_key=chart_key,
            label=_friendly_chart_label(chart_key),
            asset_type=asset_type,
            relative_path=relative_path,
            media_type=media_type,
        )
        db.add(record)
    db.flush()


def _maybe_persist_allure_charts(src_dir: Path, db: Session) -> None:
    project_id = current_project_id()
    if not project_id:
        return
    try:
        _sync_project_allure_charts(project_id, src_dir, db)
    except Exception as exc:
        print(f"Failed to persist Allure charts for project {project_id}: {exc}")


def _extract_result_duration(payload: Dict[str, Any]) -> Optional[float]:
    duration_value = payload.get("duration")
    if isinstance(duration_value, (int, float)):
        return float(duration_value)
    start = payload.get("start")
    stop = payload.get("stop")
    if isinstance(start, (int, float)) and isinstance(stop, (int, float)) and stop >= start:
        return float(stop - start)
    return None


def _sync_project_allure_results(
    project_id: int,
    run_id: str,
    src_dir: Path,
    results_dir: Path,
    db: Session,
) -> None:
    if not results_dir.is_dir():
        return
    files = sorted(results_dir.glob("*-result.json"))
    if not files:
        return
    project_root = src_dir.parent.parent if len(src_dir.parents) >= 2 else None
    project_root = project_root.resolve() if project_root else results_dir.parent

    db.query(ProjectAllureResult).filter(
        ProjectAllureResult.project_id == project_id,
        ProjectAllureResult.run_id == run_id,
    ).delete(synchronize_session=False)
    db.flush()

    for asset in files:
        if not asset.is_file():
            continue
        try:
            payload = json.loads(asset.read_text(encoding="utf-8"))
        except Exception:
            continue
        try:
            relative_path = asset.relative_to(project_root).as_posix()
        except ValueError:
            relative_path = asset.as_posix()

        record = ProjectAllureResult(
            project_id=project_id,
            run_id=run_id,
            file_name=asset.name,
            relative_path=relative_path,
            test_name=payload.get("name") or payload.get("fullName"),
            status=payload.get("status"),
            duration=_extract_result_duration(payload),
            payload=payload,
        )
        db.add(record)
    db.flush()


def _maybe_persist_allure_results(
    src_dir: Path,
    allure_results: Path,
    run_id: Optional[str],
    db: Session,
) -> None:
    project_id = current_project_id()
    if not (project_id and run_id):
        return
    try:
        _sync_project_allure_results(project_id, run_id, src_dir, allure_results, db)
    except Exception as exc:
        print(f"Failed to persist Allure results for project {project_id}: {exc}")

@router.get("/run")
def run_tests(request: Request, db: Session = Depends(get_db)):
    """
    Runs pytest with Allure results and generates Allure HTML.
    Falls back to pytest-html if Allure CLI is unavailable.
    Returns a URL to the generated report.
    """
    try:
        src_dir = _resolve_latest_src_dir()
        allure_results = src_dir / "allure-results"
        allure_report = src_dir / "allure-report"
        html_fallback = src_dir / "report.html"

        # Clean old artifacts so each run starts with a fresh set of Allure JSON files
        if allure_results.exists():
            shutil.rmtree(allure_results)
        if allure_report.exists():
            shutil.rmtree(allure_report)
        if html_fallback.exists():
            html_fallback.unlink()

        allure_results.mkdir(parents=True, exist_ok=True)
        allure_report.mkdir(parents=True, exist_ok=True)

        env = os.environ.copy()
        env["PYTHONPATH"] = str(src_dir)

        # 1) Run pytest to produce allure-results (allow failures to fall through)
        pytest_cmd = [
            "pytest",
            "tests",
            f"--alluredir={allure_results}",
            "--clean-alluredir",
        ]
        pytest_result = subprocess.run(
            pytest_cmd,
            cwd=src_dir,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        status = "PASS" if pytest_result.returncode == 0 else "FAIL"

        _generate_allure_visualizations(allure_results)
        _maybe_persist_allure_charts(src_dir, db)
        summary = _record_run_metrics(allure_results)
        _maybe_persist_allure_results(src_dir, allure_results, summary.get("id") if summary else None, db)

        # 2) Try to build Allure HTML (preferred)
        allure_exe = shutil.which("allure")
        report_path = None
        if allure_exe:
            try:
                allure_cmd = [allure_exe, "generate", str(allure_results), "-o", str(allure_report), "--clean"]
                subprocess.run(allure_cmd, check=True, cwd=src_dir)
                report_path = allure_report / "index.html"
                if not report_path.exists():
                    raise HTTPException(status_code=500, detail="Allure report generation did not produce index.html")
            except subprocess.CalledProcessError:
                # Allure CLI failed for another reason; we'll fallback below
                report_path = None
        else:
            # Allure CLI not found
            report_path = None

        if report_path is None:
            # Fallback to pytest-html single file
            html_cmd = [
                "pytest",
                "tests",
                f"--html={html_fallback}",
                "--self-contained-html",
            ]
            subprocess.run(html_cmd, check=False, cwd=src_dir, env=env)
            report_path = html_fallback

        if not report_path.exists():
            raise HTTPException(status_code=500, detail="Report was not generated")

        # Build an absolute URL to the HTTP report view so frontend can open it in a tab.
        base = str(request.base_url).rstrip("/")
        report_url = f"{base}/reports/view"
        return {
            "status": status,
            "report_url": report_url,
            "report_uri": report_url,
            "stdout": pytest_result.stdout,
            "stderr": pytest_result.stderr,
        }


    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/open")
def open_existing_report(request: Request, test: str = "tests/test_1.py"):
    """Locate an existing allure-report/index.html under generated_runs/src for the latest candidate and return a file:// URI.

    This endpoint does NOT regenerate the report; it only locates an existing HTML report and returns its file URI
    so local browsers can open it directly when running the frontend locally.
    """
    try:
        candidates = _candidate_src_dirs()
        if not candidates:
            raise HTTPException(status_code=404, detail="No generated_runs/src candidates found")

        # Prefer candidate that contains the requested test file
        chosen = None
        for c in candidates:
            if (c / test).exists():
                chosen = c
                break
        if chosen is None:
            # fallback to latest resolved src dir
            chosen = _resolve_latest_src_dir()

        # Check allure-report index
        allure_index = chosen / "allure-report" / "index.html"
        html_fallback = chosen / "index.html"
        # Build HTTP viewer URL and also include local file:// URI when available.
        base = str(request.base_url).rstrip("/")
        report_url = f"{base}/reports/view"
        if allure_index.exists():
            return {
                "report_url": report_url,
                "report_uri": report_url,
                "file_uri": allure_index.resolve().as_uri(),
                "path": str(allure_index.resolve()),
            }
        if html_fallback.exists():
            return {
                "report_url": report_url,
                "report_uri": report_url,
                "file_uri": html_fallback.resolve().as_uri(),
                "path": str(html_fallback.resolve()),
            }

        # Not found
        raise HTTPException(status_code=404, detail=f"No report HTML found in {chosen}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/report")
def run_single_test(request: Request, test: str = "tests/test_1.py", db: Session = Depends(get_db)):
    """Run pytest for a single test file and generate an Allure (or fallback) report.
    Returns a URL to view the generated report via the `/reports/latest` endpoint.
    """
    try:
        # Find a candidate src dir that contains the requested test file
        candidates = _candidate_src_dirs()
        src_dir = None
        for c in candidates:
            if (c / test).exists():
                src_dir = c
                break
        if src_dir is None:
            # fallback to latest-resolved src (may raise HTTPException)
            src_dir = _resolve_latest_src_dir()

        allure_results = src_dir / "allure-results"
        allure_report = src_dir / "allure-report"
        html_fallback = src_dir / "index.html"

        # clean previous results
        if allure_results.exists():
            shutil.rmtree(allure_results)
        allure_results.mkdir(parents=True, exist_ok=True)
        if allure_report.exists():
            shutil.rmtree(allure_report)
        allure_report.mkdir(parents=True, exist_ok=True)

        env = os.environ.copy()
        env["PYTHONPATH"] = str(src_dir)

        # Run pytest for the specific test
        pytest_cmd = ["pytest", test, f"--alluredir={allure_results}"]
        pytest_result = subprocess.run(
            pytest_cmd,
            cwd=src_dir,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        status = "PASS" if pytest_result.returncode == 0 else "FAIL"

        _generate_allure_visualizations(allure_results)
        _maybe_persist_allure_charts(src_dir, db)
        summary = _record_run_metrics(allure_results)
        _maybe_persist_allure_results(src_dir, allure_results, summary.get("id") if summary else None, db)

        # Try to build Allure HTML (preferred)
        allure_exe = shutil.which("allure")
        report_path = None
        if allure_exe:
            try:
                allure_cmd = [allure_exe, "generate", str(allure_results), "-o", str(allure_report), "--clean"]
                subprocess.run(allure_cmd, check=True, cwd=src_dir)
                report_path = allure_report / "index.html"
                if not report_path.exists():
                    raise HTTPException(status_code=500, detail="Allure report generation did not produce index.html")
            except subprocess.CalledProcessError:
                report_path = None

        if report_path is None:
            # Fallback to pytest-html single file
            html_cmd = [
                "pytest",
                test,
                f"--html={html_fallback}",
                "--self-contained-html",
            ]
            subprocess.run(html_cmd, check=False, cwd=src_dir, env=env)
            report_path = html_fallback

        if not report_path.exists():
            raise HTTPException(status_code=500, detail="Report was not generated")

        # Return a file:// URI pointing to the generated report index.html (or single-file fallback).
        # If report_path is a directory, point to its index.html; if it's a file, return its file URI.
        if report_path.is_dir():
            index = report_path / "index.html"
        else:
            # If report_path is an index.html inside a folder, use it; otherwise use the file itself
            if report_path.name == "index.html":
                index = report_path
            else:
                index = report_path

        if not index.exists():
            raise HTTPException(status_code=500, detail="Report index file not found")

        # Also include the filesystem location of the generated report when available
        base = str(request.base_url).rstrip("/")
        report_url = f"{base}/reports/view"
        file_uri = None
        file_path = None
        # If we generated an Allure report folder, point to its index
        index_candidate = None
        if (allure_report / "index.html").exists():
            index_candidate = allure_report / "index.html"
        elif html_fallback.exists():
            index_candidate = html_fallback

        if index_candidate is not None and index_candidate.exists():
            file_uri = index_candidate.resolve().as_uri()
            file_path = str(index_candidate.resolve())

        return {
            "status": status,
            "report_url": report_url,
            "report_uri": report_url,
            "file_uri": file_uri,
            "path": file_path,
            "stdout": pytest_result.stdout,
            "stderr": pytest_result.stderr,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))