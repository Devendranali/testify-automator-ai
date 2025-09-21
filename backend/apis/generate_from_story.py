# rag_testcase_runner.py
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pathlib import Path
import re
import json
import ast
import pandas as pd
from pydantic import BaseModel, Field
from typing import List, Optional
from services.graph_service import read_dependency_graph, get_adjacency_list, find_path
from services.test_generation_utils import openai_client  # Make sure this is the OpenAI client!
from utils.match_utils import normalize_page_name
from utils.prompt_utils import build_prompt
import textwrap

from chromadb import PersistentClient

chroma_client = PersistentClient(path="./data/chroma_db")
collection = chroma_client.get_or_create_collection(name="element_metadata")

router = APIRouter()

def create_default_test_data(run_folder):
    data = {
        "login": {
            "username": "standard_user",
            "password": "secret_sauce"
        },
        "checkout": {
            "first_name": "John",
            "last_name": "Doe",
            "zip_code": "12345"
        },
        "product": {
            "name": "Sauce Labs Backpack"
        }
    }
    data_dir = Path(run_folder) / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "__init__.py").touch()
    with open(data_dir / "test_data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def extract_method_names_from_file(file_path):
    method_names = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            m = re.match(r"def\s+[a-zA-Z_][a-zA-Z0-9_]*\s*\([^\)]*\):", line)
            if m:
                # This grabs the whole signature line, e.g.:
                # 'def select_account_type(page, value):'
                method_names.append(line.strip())
    return method_names

def get_all_page_methods(pages_dir):
    page_method_map = {}
    for py_file in Path(pages_dir).glob("*_page_methods.py"):
        page_name = py_file.stem.replace("_page_methods", "")
        page_method_map[page_name] = extract_method_names_from_file(py_file)
    return page_method_map

def next_index(target_dir, pattern="test_{}.py"):
    files = list(target_dir.glob(pattern.format("*")))
    indices = [int(m.group(1)) for f in files if (m := re.match(r".*_(\d+)\.", f.name))]
    return max(indices, default=0) + 1

def generate_test_code_from_methods(user_story, method_map, page_names, site_url):
    dynamic_steps = []
    for methods in method_map.values():
        for method in methods:
            if method.startswith("fill_") or method.startswith("enter_"):
                param = method.replace("fill_", "").replace("enter_", "")
                dynamic_steps.append(f"    - Call `{method}(\"<{param}>\")`")
            elif method.startswith("click_") or method.startswith("select_"):
                dynamic_steps.append(f"    - Call `{method}()`")
            elif method.startswith("verify_"):
                readable = method.replace(
                    "verify_", "").replace("_", " ").capitalize()
                dynamic_steps.append(
                    f"    - Assert `{method}()` → checks if **{readable}** is visible")

    user_story_clean = user_story.replace('"""', '\"\"\"')
    story_block = f'"""{user_story_clean}"""'

    output_dir = Path("generated_runs/src/logs/dynamic_steps")
    output_dir.mkdir(parents=True, exist_ok=True)
    i = 1
    while True:
        output_file = output_dir / f"dynamic_steps_{i}.md"
        if not output_file.exists():
            break
        i += 1
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("# Dynamic Steps\n\n")
        for step in dynamic_steps:
            f.write(step + "\n")

    prompt = build_prompt(
        story_block=story_block,
        method_map=method_map,
        page_names=page_names,
        site_url=site_url,
        dynamic_steps=dynamic_steps
    )

    prompt_dir = Path("generated_runs/src/logs/prompts")
    prompt_dir.mkdir(parents=True, exist_ok=True)
    i = 1
    while True:
        prompt_file = prompt_dir / f"prompt_{i}.md"
        if not prompt_file.exists():
            break
        i += 1
    with open(prompt_file, "w", encoding="utf-8") as f:
        f.write(prompt)

    result = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=4096,
        temperature=0
    )

    clean_output = re.sub(
        r"```(?:python)?|^\s*Here is.*?:",
        "",
        result.choices[0].message.content.strip(),
        flags=re.MULTILINE
    ).strip()

    output_dir = Path("generated_runs/src/logs/test_output")
    output_dir.mkdir(parents=True, exist_ok=True)
    i = 1
    while True:
        output_file = output_dir / f"test_output_{i}.py"
        if not output_file.exists():
            break
        i += 1
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(clean_output)

    return clean_output

def get_inferred_pages(user_story: str, method_map_full: dict, openai_client):
    page_list_str = "\n".join(
        [f"{i+1}. {k.replace('_', ' ')}" for i, k in enumerate(method_map_full.keys())]
    )
    prompt = f"""
You are an expert QA automation engineer.

Given the following available application pages:
{page_list_str}

Here is a user story:
\"\"\"{user_story}\"\"\"

Output ONLY a Python list (in order) of the page keys (use the keys exactly as shown) that must be visited for this story. Do not explain.
"""
    
    print("DEBUG Prompt for OpenAI:", prompt)  # Debugging line
    result = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=256,
        temperature=0
    )
    output = result.choices[0].message.content.strip()
    try:
        inferred_pages = ast.literal_eval(output)
        print([p for p in inferred_pages if p in method_map_full])  # Debugging line
        return [p for p in inferred_pages if p in method_map_full]
    except Exception:
        return list(method_map_full.keys())

@router.post("/rag/generate-from-story")
async def generate_from_user_story(
    user_story: Optional[str] = Form(None),
    site_url: Optional[str] = Form("https://www.saucedemo.com"),
    file: Optional[UploadFile] = File(None)
):
    run_folder = Path("generated_runs") / "src"
    pages_dir = run_folder / "pages"
    tests_dir = run_folder / "tests"
    logs_dir = run_folder / "logs"
    meta_dir = run_folder / "metadata"
    for d in [pages_dir, tests_dir, logs_dir, meta_dir]:
        d.mkdir(parents=True, exist_ok=True)
        (d / "__init__.py").touch()
    (run_folder / "__init__.py").touch()

    stories = []
    print('1')
    if file:
        import io
        content = await file.read()
        # --- Handle Excel files: load only the 'User Stories' sheet
        if file.filename.endswith((".xls", ".xlsx")):
            try:
                xls = pd.ExcelFile(io.BytesIO(content))
                if "User Stories" not in xls.sheet_names:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Sheet 'User Stories' not found. Sheets present: {xls.sheet_names}"
                    )
                df = pd.read_excel(io.BytesIO(content),
                                   sheet_name="User Stories")
            except Exception as e:
                raise HTTPException(
                    status_code=400,
                    detail=f"Failed to read 'User Stories' sheet from Excel: {str(e)}"
                )
        # --- Handle CSV: just read as normal (no sheets in CSV)
        elif file.filename.endswith(".csv"):
            df = pd.read_csv(io.StringIO(content.decode()))
        else:
            raise HTTPException(
                status_code=400, detail="Unsupported file type"
            )

        # --- Always clean up column names for safe matching
        column_map = {col.strip().lower(): col for col in df.columns}
        print("DEBUG Columns found in selected sheet:", column_map)

        if "user story" not in column_map:
            raise HTTPException(
                status_code=400,
                detail=f"Column 'User Story' not found in sheet. Columns present: {list(column_map.keys())}"
            )

        column_name = column_map["user story"]
        stories = df[column_name].dropna().astype(str).tolist()

    elif user_story:
        stories = [user_story]

    else:
        raise HTTPException(
            status_code=400, detail="Either 'user_story' or 'file' must be provided"
        )
    print('2')
    all_chroma_data = collection.get()
    all_chroma_metadatas = all_chroma_data.get("metadatas", [])
    before_file = meta_dir / "before_enrichment.json"
    with open(before_file, "w", encoding="utf-8") as f:
        json.dump(all_chroma_metadatas, f, indent=2)

    method_map_full = get_all_page_methods(pages_dir)
    print('3')
    results, test_functions = [], []
    all_path_pages = []

    for story in stories:
        # print('3.1')
        # print('method_map_full:', method_map_full) 
        # path_pages = get_inferred_pages(story, method_map_full, openai_client)
        path_pages = [key for key in method_map_full.keys()]
        # print('path_pages:', path_pages)
        if not path_pages:
            continue
        # print('4')
        all_path_pages.extend(path_pages)
        # print('4.1')
        sub_method_map = {p: method_map_full[p]
                          for p in path_pages if p in method_map_full}
        # print('4.2')
        code = generate_test_code_from_methods(
            story, sub_method_map, path_pages, site_url
        )
        # print('5')
        test_functions.append(code)
        results.append({
            "Prompt": f" Prompt\n\n1. {story}\nExpected: Success",
            "auto_testcase": code,
        })
    # print('6')
    test_idx = next_index(tests_dir, "test_{}.py")
    log_idx = next_index(logs_dir, "logs_{}.log")
    test_file = tests_dir / f"test_{test_idx}.py"
    log_file = logs_dir / f"logs_{log_idx}.log"

    page_method_files = sorted(pages_dir.glob("*_page_methods.py"))
    import_lines = ["from playwright.sync_api import sync_playwright"]
    for file in page_method_files:
        module_name = file.stem
        import_lines.append(f"from pages.{module_name} import *")

    test_file.write_text("\n\n".join(
        import_lines + test_functions), encoding="utf-8")

    if all_path_pages:
        log_file.write_text("\n".join(all_path_pages), encoding="utf-8")
    else:
        log_file.write_text("No stories were processed.", encoding="utf-8")
    # print('7')
    create_default_test_data(run_folder)

    # ================== ui_script.py generation block =======================
    # Re-using your previous logic
    test_files = sorted(tests_dir.glob("test_*.py"),
                        key=lambda f: f.stat().st_mtime, reverse=True)
    if not test_files:
        print("No test_*.py files found in", tests_dir.resolve())
        print("Contents:", list(tests_dir.glob("*")))
        # Do NOT raise exception! Just skip generation and return as usual.
    else:
        latest_test = test_files[0]

        # 2. Collect all page method imports and all code outside functions
        page_imports = set()
        non_func_code = []
        with open(latest_test, "r", encoding="utf-8") as f:
            in_func = False
            for line in f:
                if re.match(r"from pages\.", line):
                    page_imports.add(line.rstrip())
                if not line.strip().startswith("def ") and not in_func and line.strip():
                    non_func_code.append(line.rstrip())
                if line.strip().startswith("def "):
                    in_func = True
                if in_func and not line.strip():
                    in_func = False

        # 3. Parse all test functions and inline their bodies as run_* functions
        func_blocks = []
        with open(latest_test, "r", encoding="utf-8") as f:
            lines = f.readlines()

        func_name = None
        func_body = []
        in_func = False
        for i, line in enumerate(lines):
            # Detect test function
            m = re.match(r"def (test_[a-zA-Z0-9_]+)\(page\):", line)
            if m:
                if func_name and func_body:
                    # Write previous function
                    body = ''.join(func_body)
                    func_blocks.append((func_name, body))
                func_name = m.group(1)
                func_body = []
                in_func = True
                continue
            # Capture indented body lines
            if in_func:
                # Stop if we hit another function or dedent
                if re.match(r"def [a-zA-Z_]", line) or (line.startswith(" ") and not line.startswith("    ")):
                    in_func = False
                    continue
                if line.strip() == "":
                    func_body.append(line)
                    continue
                # Only lines inside the function (skip docstrings)
                func_body.append(line)
        # Catch last one
        if func_name and func_body:
            body = ''.join(func_body)
            func_blocks.append((func_name, body))

        # 4. Compose one run_* function for each, dedenting and re-indenting properly
        wrapper_blocks = []
        for func_name, func_body in func_blocks:
            runner_name = "run_" + func_name.replace("test_", "")
            dedented = textwrap.dedent(func_body)
            # All step lines in the test function body are indented 2 levels (8 spaces)
            step_lines = []
            for l in dedented.strip('\n').splitlines():
                step_lines.append("        " + l if l.strip() else "")
            steps = "\n".join(step_lines)
            wrapper_blocks.append(
                f"""def {runner_name}():
    import time
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, slow_mo=300)
        page = browser.new_page()
        # Patch SmartAI
        metadata_path = Path(__file__).parent.parent / "metadata" / "after_enrichment.json"
        with open(metadata_path, "r") as f:
            actual_metadata = json.load(f)
        patch_page_with_smartai(page, actual_metadata)
{steps}
        time.sleep(3)
        browser.close()

""")

        # 5. Compose the file header
        header = """# Auto-generated UI runner

from playwright.sync_api import sync_playwright
import json
from pathlib import Path
{page_imports}
from lib.smart_ai import patch_page_with_smartai
"""

        header = header.format(page_imports="\n".join(page_imports))

        # 6. Compose the main block
        main_block = "\nif __name__ == '__main__':\n"
        for func_name, _ in func_blocks:
            runner_name = "run_" + func_name.replace("test_", "")
            main_block += f"    {runner_name}()\n"

        # 7. Write out the file (inside tests_dir, name: ui_script_N.py to match test_N.py)
        match = re.search(r"test_(\d+)\.py$", latest_test.name)
        if match:
            test_number = match.group(1)
            ui_script_filename = f"ui_script_{test_number}.py"
        else:
            ui_script_filename = "ui_script.py"
        ui_script_path = tests_dir / ui_script_filename
        with open(ui_script_path, "w", encoding="utf-8") as f:
            f.write(header)
            for block in wrapper_blocks:
                f.write(block)
            f.write(main_block)

        print(
            f"✅ {ui_script_filename} generated with {len(wrapper_blocks)} runner(s) in {tests_dir}")

    # ================== End ui_script.py generation block ===================

    return {
        "results": results,
        "test_file": str(test_file),
        "log_file": str(log_file)
    }





