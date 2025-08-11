# # 
# from fastapi import APIRouter, HTTPException
# import os, sys, subprocess, json
# from datetime import datetime
# from pathlib import Path

# router = APIRouter()

# project_root = Path(__file__).resolve().parents[1]
# generated_runs_dir = project_root / "generated_runs" / "src"
# tests_dir = generated_runs_dir / "tests"
# logs_dir = generated_runs_dir / "logs"
# meta_dir = generated_runs_dir / "metadata"

# @router.post("/rag/run-generated-story-test")
# def run_latest_generated_story_test():
#     # find latest ui_scripts_*.py (fallback to ui_script_*.py)
#     candidates = sorted([f for f in tests_dir.glob("ui_scripts_*.py") if f.is_file()],
#                         key=lambda x: x.stat().st_mtime, reverse=True)
#     if not candidates:
#         candidates = sorted([f for f in tests_dir.glob("ui_script_*.py") if f.is_file()],
#                             key=lambda x: x.stat().st_mtime, reverse=True)
#     if not candidates:
#         raise HTTPException(status_code=404, detail=f"No UI script files in {tests_dir.resolve()}")

#     latest_ui_script = candidates[0]

#     logs_dir.mkdir(parents=True, exist_ok=True)
#     meta_dir.mkdir(parents=True, exist_ok=True)
#     log_file = logs_dir / f"test_output_{latest_ui_script.stem}.log"
#     meta_file = meta_dir / f"execution_metadata_{latest_ui_script.stem}.json"

#     env = os.environ.copy()
#     existing_pp = env.get("PYTHONPATH", "")
#     env["PYTHONPATH"] = str(generated_runs_dir) if not existing_pp else \
#         f"{generated_runs_dir}{os.pathsep}{existing_pp}"

#     result = subprocess.run(
#         [sys.executable, f"tests/{latest_ui_script.name}"],
#         cwd=generated_runs_dir,
#         env=env,
#         stdout=subprocess.PIPE,
#         stderr=subprocess.PIPE,
#         text=True
#     )

#     output = (result.stdout or "") + ("\n" if result.stdout else "") + (result.stderr or "")
#     log_file.write_text(output, encoding="utf-8")
#     status = "PASS" if result.returncode == 0 else "FAIL"

#     errors = []
#     if status == "FAIL":
#         lines = output.splitlines()
#         tb_start_idx = None
#         for i, line in enumerate(lines):
#             if line.strip().startswith("Traceback (most recent call last):"):
#                 tb_start_idx = i
#         errors = lines[tb_start_idx:] if tb_start_idx is not None else lines[-25:]

#     meta = {
#         "status": status,
#         "timestamp": datetime.now().isoformat(),
#         "script": str(latest_ui_script),
#         "returncode": result.returncode,
#         "cwd": str(generated_runs_dir),
#     }
#     with meta_file.open("w", encoding="utf-8") as f:
#         json.dump(meta, f, indent=2)

#     return {
#         "status": status,
#         "executed_script": str(latest_ui_script),
#         "log_file": str(log_file),
#         "meta_file": str(meta_file),
#         "errors": errors,
#         "log": output,
#     }
# routes/run_latest_pytest.py
from fastapi import APIRouter, HTTPException
from pathlib import Path
import os, sys, subprocess, json
from datetime import datetime

router = APIRouter()

project_root = Path(__file__).resolve().parents[1]
generated_runs_dir = project_root / "generated_runs" / "src"
tests_dir = generated_runs_dir / "tests"
logs_dir = generated_runs_dir / "logs"
meta_dir = generated_runs_dir / "metadata"

@router.post("/rag/run-latest-pytest")
def run_latest_pytest():
    # find latest test_*.py
    tests = sorted([f for f in tests_dir.glob("test_*.py") if f.is_file()],
                   key=lambda x: x.stat().st_mtime, reverse=True)
    if not tests:
        raise HTTPException(status_code=404, detail=f"No pytest files found in {tests_dir.resolve()}")

    latest_test = tests[0]

    logs_dir.mkdir(parents=True, exist_ok=True)
    meta_dir.mkdir(parents=True, exist_ok=True)
    log_file = logs_dir / f"pytest_output_{latest_test.stem}.log"
    meta_file = meta_dir / f"execution_metadata_{latest_test.stem}.json"

    env = os.environ.copy()
    existing_pp = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = str(generated_runs_dir) if not existing_pp else \
        f"{generated_runs_dir}{os.pathsep}{existing_pp}"

    # run pytest on just the latest file; -q for concise output
    cmd = [sys.executable, "-m", "pytest", "-q", str(latest_test.relative_to(generated_runs_dir))]
    result = subprocess.run(
        cmd,
        cwd=generated_runs_dir,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    output = (result.stdout or "") + ("\n" if result.stdout else "") + (result.stderr or "")
    log_file.write_text(output, encoding="utf-8")
    status = "PASS" if result.returncode == 0 else "FAIL"

    # summarize failures if any
    errors = []
    if status == "FAIL":
        # grab last ~40 lines (pytest summary + tracebacks)
        lines = output.splitlines()
        errors = lines[-40:]

    meta = {
        "status": status,
        "timestamp": datetime.now().isoformat(),
        "test_file": str(latest_test),
        "returncode": result.returncode,
        "cwd": str(generated_runs_dir),
        "cmd": " ".join(cmd),
    }
    with meta_file.open("w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    return {
        "status": status,
        "executed_test": str(latest_test),
        "log_file": str(log_file),
        "meta_file": str(meta_file),
        "errors": errors,
        "log": output,
    }
