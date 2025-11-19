from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends
from pathlib import Path
from typing import List, Optional

import ast
import json
import os
import re
import textwrap

import pandas as pd
from sqlalchemy.orm import Session

# Kept for future use (silence linter if configured)
from services.graph_service import read_dependency_graph, get_adjacency_list, find_path  # noqa: F401
from services.test_generation_utils import openai_client
from utils.prompt_utils import build_prompt
from utils.chroma_client import get_collection
from utils.file_utils import generate_unique_name
from database.project_storage import DatabaseBackedProjectStorage
from database.session import get_db
from database.models import Project


router = APIRouter()


# ---------------- internal helpers to inject assertions ----------------

# Matches lines like: "    enter_username(page, value)" or "    select_country(page, value)"
METHOD_CALL_RE = re.compile(
    r'^(\s*)((?:enter_|fill_|select_)[a-zA-Z0-9_]+)\(s*page\s*,\s*(.+?)\s*\)\s*$'
)


def inject_assertions_after_actions(code: str) -> str:
    """
    For every line like: enter_xxx(page, <value>) or select_xxx(page, <value>)
    insert the next line: assert_enter_xxx(page, <value>) or assert_select_xxx(page, <value>)
    """
    out_lines: List[str] = []

    lines = code.splitlines(True)
    for line in lines:
        out_lines.append(line)
        m = METHOD_CALL_RE.match(line)
        if not m:
            continue
        indent, method_name, value_expr = m.groups()
        assert_name = f"assert_{method_name}"
        out_lines.append(f"{indent}{assert_name}(page, {value_expr})\n")

    return "".join(out_lines)


# ----------------------------------------------------------------------


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
        match = re.match(r"(?P<id>\d+)-", segment)
        if match:
            candidate_id = int(match.group("id"))
            project = (
                db.query(Project)
                .filter(Project.id == candidate_id)
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

    raise HTTPException(
        status_code=400,
        detail="Active project not found in database. Activate a project before generating stories.",
    )


def _persist_project_file(path: Path, content: str, storage: Optional[DatabaseBackedProjectStorage], encoding: str = "utf-8") -> None:
    if not storage:
        return
    try:
        relative = path.relative_to(storage.base_dir)
    except ValueError:
        return
    storage.write_file(relative.as_posix(), content, encoding)


def create_default_test_data(
    run_folder: Path,
    method_map_full: Optional[dict] = None,
    test_data_json: Optional[str] = None,
    storage: Optional[DatabaseBackedProjectStorage] = None,
) -> None:
    """
    Create or write test data for the run. If `test_data_json` is provided it will be used (must be JSON string).
    Otherwise a minimal scaffold is created by scanning method_map_full for common keys.
    """
    data = {}
    if test_data_json:
        try:
            data = json.loads(test_data_json)
        except Exception:
            data = {}
    else:
        if method_map_full:
            for page_key, _methods in method_map_full.items():
                data[page_key] = {}
        if not data:
            data = {"__meta__": {}}

    data_dir = Path(run_folder) / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "__init__.py").touch()
    target = data_dir / "test_data.json"
    json_text = json.dumps(data, indent=2)
    target.write_text(json_text, encoding="utf-8")
    _persist_project_file(target, json_text, storage)


def extract_method_names_from_file(file_path: Path) -> List[str]:
    method_names: List[str] = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            m = re.match(r"def\s+[a-zA-Z_][a-zA-Z0-9_]*\s*\([^)]*\):", line)
            if m:
                method_names.append(line.strip())
    return method_names


def get_all_page_methods(pages_dir: Path) -> dict:
    page_method_map = {}
    for py_file in Path(pages_dir).glob("*_page_methods.py"):
        page_name = py_file.stem.replace("_page_methods", "")
        page_method_map[page_name] = extract_method_names_from_file(py_file)
    return page_method_map


def next_index(target_dir: Path, pattern: str = "test_{}.py") -> int:
    files = list(target_dir.glob(pattern.format("*")))
    indices = [int(m.group(1)) for f in files if (m := re.match(r".*_(\d+)\.", f.name))]
    return max(indices, default=0) + 1


def generate_test_code_from_methods(
    user_story: str,
    method_map: dict,
    page_names: List[str],
    site_url: str,
    run_folder: Path,
    storage: Optional[DatabaseBackedProjectStorage] = None,
) -> str:
    # Summarize available methods into human-friendly steps; this feeds the prompt
    dynamic_steps: List[str] = []
    for methods in method_map.values():
        for method in methods:
            name = method.split("(")[0].replace("def ", "").strip()
            if name.startswith(("enter_", "fill_")):
                param = name.replace("enter_", "").replace("fill_", "")
                dynamic_steps.append(f'    - Call `{name}("<"+param+">")`')
            elif name.startswith(("click_", "select_")):
                if name.startswith("select_"):
                    dynamic_steps.append(f'    - Call `{name}("<value>")`')
                else:
                    dynamic_steps.append(f'    - Call `{name}()`')
            elif name.startswith("verify_"):
                readable = name.replace("verify_", "").replace("_", " ").capitalize()
                dynamic_steps.append(f"    - Assert `{name}()` checks if **{readable}** is visible")

    user_story_clean = user_story.replace('"""', '\"""')
    story_block = f'"""{user_story_clean}"""'

    # Save dynamic steps log
    output_dir = run_folder / "logs" / "dynamic_steps"
    output_dir.mkdir(parents=True, exist_ok=True)
    i = 1
    while True:
        output_file = output_dir / f"dynamic_steps_{i}.md"
        if not output_file.exists():
            break
        i += 1
    dynamic_steps_text = "# Dynamic Steps\n\n" + "\n".join(dynamic_steps) + ("\n" if dynamic_steps else "")
    output_file.write_text(dynamic_steps_text, encoding="utf-8")
    _persist_project_file(output_file, dynamic_steps_text, storage)

    # Build prompt
    prompt = build_prompt(
        story_block=story_block,
        method_map=method_map,
        page_names=page_names,
        site_url=site_url,
        dynamic_steps=dynamic_steps,
    )

    # Save prompt
    prompt_dir = run_folder / "logs" / "prompts"
    prompt_dir.mkdir(parents=True, exist_ok=True)
    i = 1
    while True:
        prompt_file = prompt_dir / f"prompt_{i}.md"
        if not prompt_file.exists():
            break
        i += 1
    prompt_file.write_text(prompt, encoding="utf-8")
    _persist_project_file(prompt_file, prompt, storage)

    # Call LLM to generate test code
    model_name = os.getenv("AI_MODEL_NAME", "gpt-4o")
    result = openai_client.chat.completions.create(
        model=model_name,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=int(os.getenv("AI_MAX_TOKENS", "4096")),
        temperature=float(os.getenv("AI_TEMPERATURE", "0")),
    )

    clean_output = re.sub(
        r"```(?:python)?|^\s*Here is.*?:",
        "",
        (result.choices[0].message.content or "").strip(),
        flags=re.MULTILINE,
    ).strip()

    # Inject method-specific assertions after enter_/fill_/select_ calls
    clean_output = inject_assertions_after_actions(clean_output)

    # If a site_url was provided, ensure any page.goto(...) uses it
    try:
        if site_url and str(site_url).strip():
            goto_literal = json.dumps(site_url)
            clean_output = re.sub(r"page\\.goto\\([^\\)]*\\)", f"page.goto({goto_literal})", clean_output)
    except Exception:
        pass

    # Save generated test code for debugging
    output_dir = run_folder / "logs" / "test_output"
    output_dir.mkdir(parents=True, exist_ok=True)
    i = 1
    while True:
        output_file = output_dir / f"test_output_{i}.py"
        if not output_file.exists():
            break
        i += 1
    output_file.write_text(clean_output, encoding="utf-8")
    _persist_project_file(output_file, clean_output, storage)

    return clean_output


def get_inferred_pages(user_story: str, method_map_full: dict, client) -> List[str]:
    page_list_str = "\n".join([f"{i+1}. {k.replace('_', ' ')}" for i, k in enumerate(method_map_full.keys())])
    story_block = f'"""{user_story}"""'
    prompt = f"""
You are an expert QA automation engineer.

Given the following available application pages:
{page_list_str}

Here is a user story:
{story_block}

Output ONLY a Python list (in order) of the page keys (use the keys exactly as shown) that must be visited for this story. Do not explain.
"""
    model_name = os.getenv("AI_INFER_MODEL", "gpt-4o")
    result = client.chat.completions.create(
        model=model_name,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=int(os.getenv("AI_MAX_TOKENS", "4096")),
        temperature=float(os.getenv("AI_TEMPERATURE", "0")),
    )

    output = (result.choices[0].message.content or "").strip()
    try:
        inferred_pages = ast.literal_eval(output)
        return [p for p in inferred_pages if p in method_map_full]
    except Exception:
        return list(method_map_full.keys())


@router.post("/rag/generate-from-story")
async def generate_from_user_story(
    user_story: Optional[str] = Form(None),
    site_url: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    ai_model: Optional[str] = Form(None),
    infer_pages: Optional[bool] = Form(False),
    test_data_json: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    src_env = os.environ.get("SMARTAI_SRC_DIR")
    if not src_env:
        raise HTTPException(status_code=400, detail="No active project. Start a project first (SMARTAI_SRC_DIR not set).")

    project = _get_active_project(db)
    run_folder = Path(src_env)
    storage = DatabaseBackedProjectStorage(project, run_folder, db)
    pages_dir = run_folder / "pages"
    tests_dir = run_folder / "tests"
    logs_dir = run_folder / "logs"
    meta_dir = run_folder / "metadata"
    for d in [pages_dir, tests_dir, logs_dir, meta_dir]:
        d.mkdir(parents=True, exist_ok=True)
        (d / "__init__.py").touch()
    (run_folder / "__init__.py").touch()

    # Parse incoming user stories
    stories: List[str] = []
    if file:
        import io
        content = await file.read()
        if file.filename.endswith((".xls", ".xlsx")):
            try:
                xls = pd.ExcelFile(io.BytesIO(content))
                if "User Stories" not in xls.sheet_names:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Sheet 'User Stories' not found. Sheets present: {xls.sheet_names}",
                    )
                df = pd.read_excel(io.BytesIO(content), sheet_name="User Stories")
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Failed to read 'User Stories' sheet from Excel: {str(e)}")
        elif file.filename.endswith(".csv"):
            df = pd.read_csv(io.StringIO(content.decode()))
        else:
            raise HTTPException(status_code=400, detail="Unsupported file type")

        column_map = {col.strip().lower(): col for col in df.columns}
        if "user story" not in column_map:
            raise HTTPException(
                status_code=400,
                detail=f"Column 'User Story' not found in sheet. Columns present: {list(column_map.keys())}",
            )
        column_name = column_map["user story"]
        stories = df[column_name].dropna().astype(str).tolist()
    elif user_story:
        stories = [user_story]
    else:
        raise HTTPException(status_code=400, detail="Either 'user_story' or 'file' must be provided")

    # Snapshot current chroma metadata (include stable identifiers for OCR entries)
    collection = get_collection("element_metadata")
    all_chroma_data = collection.get()
    ids = all_chroma_data.get("ids", []) or []
    metas = all_chroma_data.get("metadatas", []) or []

    all_chroma_metadatas: list[dict] = []
    for _id, m in zip(ids, metas):
        if (m or {}).get("type") == "ocr":
            page = (m or {}).get("page_name") or ""
            label = (m or {}).get("label_text") or ""
            otype = (m or {}).get("ocr_type") or ""
            intent_val = (m or {}).get("intent") or ""
            uname = (m or {}).get("unique_name") or generate_unique_name(page, label, otype, intent_val)
            elem_id = (m or {}).get("element_id") or _id or (m or {}).get("ocr_id") or uname
            all_chroma_metadatas.append({
                "page_name": page,
                "label_text": label,
                "get_by_text": (m or {}).get("get_by_text") or label,
                "placeholder": (m or {}).get("placeholder") or label,
                "ocr_type": otype,
                "intent": intent_val,
                "dom_matched": bool((m or {}).get("dom_matched")) if (m or {}).get("dom_matched") is not None else False,
                "external": bool((m or {}).get("external")) if (m or {}).get("external") is not None else False,
                "type": "ocr",
                "unique_name": uname,
                "element_id": elem_id,
            })
        else:
            all_chroma_metadatas.append(m)
    before_file = meta_dir / "before_enrichment.json"
    before_text = json.dumps(all_chroma_metadatas, indent=2)
    before_file.write_text(before_text, encoding="utf-8")
    _persist_project_file(before_file, before_text, storage)

    method_map_full = get_all_page_methods(pages_dir)

    results: List[dict] = []
    test_functions: List[str] = []
    all_path_pages: List[str] = []

    # Determine site_url: param -> env -> empty
    if not site_url:
        site_url = os.getenv("SITE_URL", "")

    # Optional: set AI model for this request
    if ai_model:
        os.environ["AI_MODEL_NAME"] = ai_model

    for story in stories:
        # Optionally use LLM-inferred path
        if infer_pages or os.getenv("AI_INFER_PAGES", "false").lower() in ("1", "true", "yes"):
            path_pages = get_inferred_pages(story, method_map_full, openai_client)
        else:
            path_pages = list(method_map_full.keys())
        if not path_pages:
            continue
        all_path_pages.extend(path_pages)
        sub_method_map = {p: method_map_full[p] for p in path_pages if p in method_map_full}
        code = generate_test_code_from_methods(story, sub_method_map, path_pages, site_url, run_folder, storage)
        test_functions.append(code)
        results.append({
            "Prompt": f" Prompt\n\n1. {story}\nExpected: Success",
            "auto_testcase": code,
        })

    test_idx = next_index(tests_dir, "test_{}.py")
    log_idx = next_index(logs_dir, "logs_{}.log")
    test_file = tests_dir / f"test_{test_idx}.py"
    log_file = logs_dir / f"logs_{log_idx}.log"

    page_method_files = sorted(pages_dir.glob("*_page_methods.py"))
    import_lines = [
        "from playwright.sync_api import sync_playwright",
        "import json",
        "from pathlib import Path",
        "from lib.smart_ai import patch_page_with_smartai",
    ]
    for f in page_method_files:
        module_name = f.stem
        import_lines.append(f"from pages.{module_name} import *")

    # Write the raw test(s) as produced by LLM
    test_content = "\n\n".join(import_lines + test_functions)
    test_file.write_text(test_content, encoding="utf-8")
    _persist_project_file(test_file, test_content, storage)

    if all_path_pages:
        log_content = "\n".join(all_path_pages)
    else:
        log_content = "No stories were processed."
    log_file.write_text(log_content, encoding="utf-8")
    _persist_project_file(log_file, log_content, storage)

    create_default_test_data(run_folder, method_map_full=method_map_full, test_data_json=test_data_json, storage=storage)

    # ================== ui_script.py generation block =======================
    test_files = sorted(tests_dir.glob("test_*.py"), key=lambda f: f.stat().st_mtime, reverse=True)
    if test_files:
        latest_test = test_files[0]

        # Parse all test functions and inline their bodies as run_* functions
        func_blocks: List[tuple[str, str]] = []
        lines = latest_test.read_text(encoding="utf-8").splitlines(True)

        func_name: Optional[str] = None
        func_body: List[str] = []
        in_func = False
        for line in lines:
            m = re.match(r"def (test_[a-zA-Z0-9_]+)\(page\):", line)
            if m:
                if func_name and func_body:
                    body = ''.join(func_body)
                    func_blocks.append((func_name, body))
                func_name = m.group(1)
                func_body = []
                in_func = True
                continue
            if in_func:
                if not line.startswith("    "):
                    in_func = False
                    continue
                func_body.append(line)
        if func_name and func_body:
            body = ''.join(func_body)
            func_blocks.append((func_name, body))

        # Collect optional storage_state override from story text
        storage_override_js = None
        try:
            storage_override = None
            for s in stories:
                m = re.search(r'storage state\s*"([^"]+)"', s, re.I)
                if m:
                    storage_override = m.group(1)
                    break
            if storage_override:
                storage_override_js = json.dumps(storage_override)
        except Exception:
            storage_override_js = None

        wrapper_blocks: List[str] = []
        for func_name, func_body in func_blocks:
            runner_name = "run_" + func_name.replace("test_", "")
            dedented = textwrap.dedent(func_body)
            step_lines = ["        " + l if l.strip() else "" for l in dedented.strip('\n').splitlines()]
            steps = "\n".join(step_lines)

            if storage_override_js:
                storage_snippet = (
                    f"""        try:\n            context = browser.new_context(storage_state={storage_override_js})\n            page = context.new_page()\n            print(f"[ui_runner] Restored storage_state from provided path")\n        except Exception as e:\n            print(f"[ui_runner] Failed to restore provided storage_state: {{e}}}}")\n            context = browser.new_context()\n            page = context.new_page()\n"""
                )
            else:
                storage_snippet = (
                    """        # Attempt to restore cookies / localStorage from a Playwright storage_state file.\n        # Priority: UI_STORAGE_FILE env -> backend/storage/cookies.json (project-relative)\n        storage_file = None\n        env_sf = os.getenv("UI_STORAGE_FILE", "").strip()\n        if env_sf:\n            storage_file = _Path(env_sf)\n        else:\n            guessed = _Path(__file__).resolve().parents[3] / "backend" / "storage" / "cookies.json"\n            if guessed.exists():\n                storage_file = guessed\n\n        if storage_file and storage_file.exists():\n            try:\n                context = browser.new_context(storage_state=str(storage_file))\n                page = context.new_page()\n                print(f"[ui_runner] Restored storage_state from: {storage_file}")\n            except Exception as e:\n                print(f"[ui_runner] Failed to restore storage_state: {e}")\n                context = browser.new_context()\n                page = context.new_page()\n        else:\n            context = browser.new_context()\n            page = context.new_page()\n"""
                )

            goto_line = ""
            try:
                if site_url and str(site_url).strip():
                    goto_line = f"        page.goto({json.dumps(site_url)})\n"
            except Exception:
                goto_line = ""

            runner_block = f"""def {runner_name}():\n    import time\n    import os\n    from pathlib import Path as _Path\n    with sync_playwright() as p:\n        browser = p.chromium.launch(headless=False, slow_mo=300)\n\n{storage_snippet}\n        # Patch SmartAI\n        metadata_path = Path(__file__).parent.parent / "metadata" / "after_enrichment.json"\n        with open(metadata_path, "r") as f:\n            actual_metadata = json.load(f)\n{goto_line}        patch_page_with_smartai(page, actual_metadata)\n{steps}\n        time.sleep(3)\n        browser.close()\n\n"""
            wrapper_blocks.append(runner_block)

        header = """# Auto-generated UI runner\nimport sys\nfrom pathlib import Path as _Path\n# Ensure generated_runs/src is on sys.path so 'from pages.*' imports work when running\n# this script from the repository root or the backend folder.\n_ROOT = _Path(__file__).resolve().parents[1]\nif str(_ROOT) not in sys.path:\n    sys.path.insert(0, str(_ROOT))\nfrom playwright.sync_api import sync_playwright\nimport json\nfrom pathlib import Path\n{page_imports}\nfrom lib.smart_ai import patch_page_with_smartai\n""".format(page_imports="\n".join([ln for ln in import_lines if ln.startswith("from pages.")]))

        main_lines = [
            "",
            "if __name__ == '__main__':",
            "    failures = []",
        ]
        for func_name, _ in func_blocks:
            runner_name = "run_" + func_name.replace("test_", "")
            main_lines.append("    try:")
            main_lines.append(f"        {runner_name}()")
            main_lines.append("    except Exception as exc:")
            main_lines.append(f"        failures.append((\"{runner_name}\", str(exc)))")
        main_lines.append("    if failures:")
        main_lines.append("        print(\"\\n[Test Runner] Failures detected:\")")
        main_lines.append("        for name, err in failures:")
        main_lines.append(f"            print(f\" - {{name}}: {{err}}\")")
        main_lines.append("        raise SystemExit(1)")
        main_lines.append("    print(\"\\n[Test Runner] All generated flows completed without fatal errors.\")")
        main_block = "\n".join(main_lines) + "\n"

        m = re.search(r"test_(\d+)\\.py$", latest_test.name)
        ui_script_filename = f"ui_script_{m.group(1)}.py" if m else "ui_script.py"
        ui_script_path = tests_dir / ui_script_filename
        ui_script_content = [header]
        ui_script_content.extend(wrapper_blocks)
        ui_script_content.append(main_block)
        final_script = "\n".join(ui_script_content)
        ui_script_path.write_text(final_script, encoding="utf-8")
        _persist_project_file(ui_script_path, final_script, storage)
        print(f"{ui_script_filename} generated with {len(wrapper_blocks)} runner(s) in {tests_dir}")
    # ================== End ui_script.py generation block ===================

    return {
        "results": results,
        "test_file": str(test_file),
        "log_file": str(log_file),
    }
