from fastapi import APIRouter, HTTPException, Depends
from pathlib import Path
import os
import re
from typing import List, Tuple
from sqlalchemy.orm import Session

from apis.projects_api import _ensure_project_structure, get_current_user, get_user_project
from database.models import User
from database.session import get_db

router = APIRouter()


def next_test_index(tests_dir: Path) -> int:
    """Return the next test index for file naming."""
    test_files = list(tests_dir.glob("test_*.py"))
    if not test_files:
        return 1
    indices = []
    for f in test_files:
        match = re.match(r"test_(\d+)\.py", f.name)
        if match:
            indices.append(int(match.group(1)))
    return max(indices, default=0) + 1


def read_page_methods(page_method_path: Path) -> str:
    """Read the contents of a generated page methods file."""
    return page_method_path.read_text(encoding="utf-8")


_INVOKE_PREFIXES = (
    "enter_",
    "click_",
    "right_click_",
    "dblclick_",
    "hover_",
    "focus_",
    "press_",
    "type_",
    "clear_",
    "check_",
    "uncheck_",
    "select_",
    "select_option_",
    "toggle_",
    "upload_",
    "verify_",
    "assert_",
    "mouse_",
)


def _iter_callable_defs(source: str) -> List[Tuple[str, str]]:
    """Return list of (function_name, params_string) for top-level defs."""
    if not source:
        return []
    return re.findall(
        r"^def\s+([a-zA-Z_][a-zA-Z0-9_]*)\(([^)]*)\):",
        source,
        flags=re.MULTILINE,
    )


def _build_invocation(qualified_fn: str, params: str) -> str | None:
    """Build a best-effort invocation line for a generated method."""
    # qualified_fn is like "m0.click_login_button"
    fn_name = qualified_fn.split(".")[-1]
    if not fn_name or fn_name.startswith("_"):
        return None
    if not fn_name.startswith(_INVOKE_PREFIXES):
        return None

    # Skip pure page-level helpers by default.
    if fn_name in (
        "goto",
        "reload",
        "go_back",
        "go_forward",
        "wait_for_load_state",
        "wait_for_url",
        "expect_title",
        "screenshot",
        "trace_start",
        "trace_stop",
        "expect_download",
        "on_dialog",
        "wait_for_popup",
        "route",
        "wait_for_request",
        "wait_for_response",
    ):
        return None

    p = (params or "").replace(" ", "")
    if not p.startswith("page"):
        return None

    if "file_path" in p or "filepath" in p:
        return f"        {qualified_fn}(page, str(demo_file))"
    if "expected" in p:
        return f"        {qualified_fn}(page, 'demo_value')"
    if ",value" in p or p.endswith(",value") or "value:" in p:
        return f"        {qualified_fn}(page, 'demo_value')"
    if "key" in p:
        return f"        {qualified_fn}(page, 'Enter')"
    return f"        {qualified_fn}(page)"


@router.post("/rag/generate-from-method")
def generate_test_from_methods(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = get_user_project(db, project_id, current_user)
    project_paths = _ensure_project_structure(project)
    run_folder = Path(project_paths["src_dir"])
    pages_dir = run_folder / "pages"
    tests_dir = run_folder / "tests"

    tests_dir.mkdir(parents=True, exist_ok=True)
    pages_dir.mkdir(parents=True, exist_ok=True)

    method_files = sorted(pages_dir.glob("*_page_methods.py"))
    if not method_files:
        return {"error": "No page methods found. Please generate page methods first."}

    module_imports: List[str] = []
    invocations: List[str] = []
    for i, method_file in enumerate(method_files):
        module_name = method_file.stem  # e.g. login_page_methods
        alias = f"m{i}"
        module_imports.append(f"import pages.{module_name} as {alias}")

        methods_code = read_page_methods(method_file)
        for fn, params in _iter_callable_defs(methods_code):
            line = _build_invocation(f"{alias}.{fn}", params)
            if line:
                invocations.append(line)

    # Cap invocations so tests stay runnable and do not time out in CI.
    invocations = invocations[:60]

    script_lines: List[str] = []
    script_lines.append("import json")
    script_lines.append("from pathlib import Path")
    script_lines.append("")
    script_lines.append("from playwright.sync_api import sync_playwright")
    script_lines.append("from lib.smart_ai import patch_page_with_smartai")
    script_lines.append("")
    script_lines.extend(module_imports)
    script_lines.append("")
    script_lines.append("def _load_metadata(src_root: Path):")
    script_lines.append("    for name in ('after_enrichment.json', 'before_enrichment.json'):")
    script_lines.append("        path = src_root / 'metadata' / name")
    script_lines.append("        if not path.exists():")
    script_lines.append("            continue")
    script_lines.append("        try:")
    script_lines.append("            return json.loads(path.read_text(encoding='utf-8'))")
    script_lines.append("        except Exception:")
    script_lines.append("            continue")
    script_lines.append("    return []")
    script_lines.append("")
    script_lines.append("def test_generated():")
    script_lines.append("    src_root = Path(__file__).resolve().parents[1]")
    script_lines.append("    artifacts = src_root / 'artifacts'")
    script_lines.append("    artifacts.mkdir(parents=True, exist_ok=True)")
    script_lines.append("    video_dir = artifacts / 'video'")
    script_lines.append("    trace_path = artifacts / 'trace.zip'")
    script_lines.append("    screenshot_path = artifacts / 'failure.png'")
    script_lines.append("    demo_file = artifacts / 'demo_upload.txt'")
    script_lines.append("    demo_file.write_text('demo', encoding='utf-8')")
    script_lines.append("")
    script_lines.append("    with sync_playwright() as p:")
    script_lines.append("        browser = p.chromium.launch(headless=False)")
    script_lines.append("        context = browser.new_context(record_video_dir=str(video_dir))")
    script_lines.append("        context.tracing.start(screenshots=True, snapshots=True, sources=True)")
    script_lines.append("        page = context.new_page()")
    script_lines.append("        page.on('dialog', lambda d: d.accept())")
    script_lines.append("        metadata = _load_metadata(src_root)")
    script_lines.append("        if metadata:")
    script_lines.append("            patch_page_with_smartai(page, metadata)")
    script_lines.append("")
    script_lines.append("        try:")
    if invocations:
        script_lines.extend(["            " + line.strip() for line in invocations])
    else:
        script_lines.append("            # No invocations could be inferred from page methods.")
    script_lines.append("        except Exception:")
    script_lines.append("            try:")
    script_lines.append("                page.screenshot(path=str(screenshot_path), full_page=True)")
    script_lines.append("            except Exception:")
    script_lines.append("                pass")
    script_lines.append("            raise")
    script_lines.append("        finally:")
    script_lines.append("            try:")
    script_lines.append("                context.tracing.stop(path=str(trace_path))")
    script_lines.append("            except Exception:")
    script_lines.append("                pass")
    script_lines.append("            context.close()")
    script_lines.append("            browser.close()")

    script_content = "\n".join(script_lines) + "\n"

    idx = next_test_index(tests_dir)
    out_file = tests_dir / f"test_{idx}.py"
    out_file.write_text(script_content, encoding="utf-8")

    return {"filename": str(out_file), "status": "Test generated", "test_code": script_content}
