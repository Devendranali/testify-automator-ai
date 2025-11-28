#run_test_api.py
import os
import shutil
import subprocess
from pathlib import Path
from fastapi import APIRouter, HTTPException, Request

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

@router.get("/run")
def run_tests(request: Request):
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

        allure_results.mkdir(parents=True, exist_ok=True)
        allure_report.mkdir(parents=True, exist_ok=True)

        env = os.environ.copy()
        env["PYTHONPATH"] = str(src_dir)

        # 1) Run pytest to produce allure-results (allow failures to fall through)
        pytest_cmd = ["pytest", "tests", f"--alluredir={allure_results}"]
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

@router.get("/run")
def run_tests(request: Request):
    """
    Runs pytest and ALWAYS writes report into allure-report folder.
    Falls back to pytest-html but still serves from allure-report/index.html
    """
    try:
        src_dir = _resolve_latest_src_dir()
        allure_results = src_dir / "allure-results"
        allure_report = src_dir / "allure-report"

        # Clean previous
        if allure_results.exists():
            shutil.rmtree(allure_results)
        allure_results.mkdir(parents=True, exist_ok=True)

        if allure_report.exists():
            shutil.rmtree(allure_report)
        allure_report.mkdir(parents=True, exist_ok=True)

        env = os.environ.copy()
        env["PYTHONPATH"] = str(src_dir)

        # 1️⃣ Run pytest — ALWAYS generate allure-results
        pytest_cmd = ["pytest", "tests", f"--alluredir={allure_results}"]
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

        # 2️⃣ Prefer Allure CLI HTML
        allure_exe = shutil.which("allure")
        report_path = allure_report / "index.html"

        if allure_exe:
            try:
                subprocess.run(
                    [allure_exe, "generate", str(allure_results), "-o", str(allure_report), "--clean"],
                    cwd=src_dir,
                    check=True,
                )
            except Exception:
                # If CLI fails → fallback below
                pass

        # 3️⃣ Fallback → pytest-html but keep SAME target path for viewer compatibility
        if not report_path.exists():
            fallback_html = allure_report / "index.html"
            html_cmd = [
                "pytest",
                "tests",
                f"--html={fallback_html}",
                "--self-contained-html",
            ]
            subprocess.run(html_cmd, check=False, cwd=src_dir, env=env)

        if not report_path.exists():
            raise HTTPException(status_code=500, detail="Report generation failed")

        # Final viewer URL
        base = str(request.base_url).rstrip("/")
        report_url = f"{base}/reports/view"

        return {
            "status": status,
            "report_url": report_url,
            "stdout": pytest_result.stdout,
            "stderr": pytest_result.stderr,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
