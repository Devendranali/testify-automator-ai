from fastapi import APIRouter, HTTPException
import os, sys, subprocess, json
from datetime import datetime
from pathlib import Path
from utils.smart_ai_utils import ensure_smart_ai_module

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

@router.post("/rag/run-generated-story-test")
def run_latest_generated_story_test():
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
            ensure_smart_ai_module()
        except Exception:
            pass

        # Ensure metadata file referenced by ui_script exists (fallback to before_enrichment or empty list)
        try:
            after_meta = meta_dir / "after_enrichment.json"
            before_meta = meta_dir / "before_enrichment.json"
            if not after_meta.exists():
                if before_meta.exists():
                    try:
                        after_meta.write_text(before_meta.read_text(encoding="utf-8"), encoding="utf-8")
                    except Exception:
                        after_meta.write_text("[]", encoding="utf-8")
                else:
                    after_meta.write_text("[]", encoding="utf-8")
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
