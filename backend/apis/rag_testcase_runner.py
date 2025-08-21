
from fastapi import APIRouter, HTTPException
import os, sys, subprocess, json
from datetime import datetime
from pathlib import Path

router = APIRouter()

project_root = Path(__file__).resolve().parents[1]
generated_runs_dir = project_root / "generated_runs" / "src"
tests_dir = generated_runs_dir / "tests"
logs_dir = generated_runs_dir / "logs"
meta_dir = generated_runs_dir / "metadata"

@router.post("/rag/run-generated-story-test")
def run_latest_generated_story_test():
    try:
        # 1. Find the latest ui_script_*.py in generated_runs/src/tests/
        ui_script_files = sorted(
            [f for f in tests_dir.glob("ui_script_*.py") if f.is_file()],
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )
        if not ui_script_files:
            raise HTTPException(
                status_code=404,
                detail=f"No generated ui_script_*.py files found in {tests_dir.resolve()}"
            )
        latest_ui_script = ui_script_files[0]

        # 2. Prepare logs and meta output
        logs_dir.mkdir(parents=True, exist_ok=True)
        meta_dir.mkdir(parents=True, exist_ok=True)
        log_file = logs_dir / f"test_output_{latest_ui_script.stem}.log"
        meta_file = meta_dir / f"execution_metadata_{latest_ui_script.stem}.json"

        # 3. Run the script like: PYTHONPATH=. python tests/ui_script_N.py
        env = os.environ.copy()
        env["PYTHONPATH"] = str(generated_runs_dir)  # Set to "generated_runs/src"

        # Note: Run from generated_runs/src, so `tests/ui_script_N.py` exists relative to cwd
        result = subprocess.run(
            [sys.executable, f"tests/{latest_ui_script.name}"],
            cwd=generated_runs_dir,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        output = result.stdout + "\n" + result.stderr
        log_file.write_text(output, encoding="utf-8")
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

        json.dump(
            {"status": status, "timestamp": datetime.now().isoformat()},
            open(meta_file, "w"),
            indent=2
        )

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