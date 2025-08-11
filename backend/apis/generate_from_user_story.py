# from fastapi import APIRouter, HTTPException, UploadFile, File, Form
# from pathlib import Path
# import re
# import json
# import ast
# import pandas as pd
# from pydantic import BaseModel, Field
# from typing import List, Optional
# import textwrap
# from chromadb import PersistentClient
# import io

# from services.test_generation_utils import openai_client
# from utils.prompt_utils import build_prompt
# from utils.match_utils import normalize_page_name
# from services.graph_service import read_dependency_graph, get_adjacency_list, find_path

# router = APIRouter()
# chroma_client = PersistentClient(path="./data/chroma_db")
# collection = chroma_client.get_or_create_collection(name="element_metadata")


# def create_default_test_data(run_folder):
#     data = {
#         "login": {"username": "standard_user", "password": "secret_sauce"},
#         "checkout": {"first_name": "John", "last_name": "Doe", "zip_code": "12345"},
#         "product": {"name": "Sauce Labs Backpack"}
#     }
#     data_dir = Path(run_folder) / "data"
#     data_dir.mkdir(parents=True, exist_ok=True)
#     (data_dir / "__init__.py").touch()
#     with open(data_dir / "test_data.json", "w", encoding="utf-8") as f:
#         json.dump(data, f, indent=2)


# def extract_method_names_from_file(file_path):
#     method_names = []
#     with open(file_path, "r", encoding="utf-8") as f:
#         lines = f.readlines()
#     for line in lines:
#         stripped = line.strip()
#         if stripped.startswith("async def "):
#             m = re.match(
#                 r"async def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(", stripped)
#             if m:
#                 method_names.append(m.group(1))
#     return method_names


# def get_all_page_methods(pages_dir):
#     page_method_map = {}
#     for py_file in Path(pages_dir).glob("*_page.py"):
#         page_name = py_file.stem.replace("_page", "")
#         method_list = extract_method_names_from_file(py_file)
#         print(f"📄 {page_name}: {len(method_list)} methods")
#         page_method_map[page_name] = method_list
#     return page_method_map


# def next_index(target_dir, pattern="test_{}.py"):
#     files = list(target_dir.glob(pattern.format("*")))
#     indices = [int(m.group(1))
#                for f in files if (m := re.match(r".*_(\d+)\.", f.name))]
#     return max(indices, default=0) + 1


# def to_pascal_case(name: str) -> str:
#     return ''.join(word.capitalize() for word in name.split('_')) + "Page"


# def generate_test_code_from_methods(user_story, method_map, page_names, site_url):
#     dynamic_steps = []
#     for page, methods in method_map.items():
#         for method in methods:
#             if method.startswith("enter_"):
#                 param = method.replace("enter_", "")
#                 dynamic_steps.append(
#                     f"    - Call `await {page}_page.{method}(\"<{param}>\")`")
#             elif method.startswith("click_") or method.startswith("select_"):
#                 dynamic_steps.append(
#                     f"    - Call `await {page}_page.{method}()`")

#     story_block = f'"""{user_story.strip()}"""'
#     method_prompt_block = json.dumps(
#         {f"{page}_page": methods for page, methods in method_map.items()}, indent=2)

#     prompt = f"""
# You are an expert QA automation engineer.

# You are given the following:
# - A user story.
# - A set of page classes with available async methods.
# - Each page is initialized like `customers_page = CustomersPage(page)`
# - Method calls are in the form: `await page_name.method_name()` or `await page_name.method_name(value)`

# Using only the available methods, generate a full Playwright async test case that fulfills the story.

# Constraints:
# - Use only the provided method names.
# - Do not generate selectors or locators.
# - Use `async def` test function.
# - Use `await` before all page method calls.
# - Do not explain anything. Output code only.

# User Story:
# {story_block}

# Pages and Methods:
# {method_prompt_block}

# URL: {site_url}
# """

#     result = openai_client.chat.completions.create(
#         model="gpt-4o",
#         messages=[{"role": "user", "content": prompt}],
#         max_tokens=4096,
#         temperature=0
#     )

#     print("\n📤 Prompt sent to LLM:\n", prompt)
#     print("\n📥 LLM raw response:\n", result.choices[0].message.content)

#     clean_output = re.sub(r"```(?:python)?|^\s*Here is.*?:", "",
#                           result.choices[0].message.content.strip(), flags=re.MULTILINE).strip()
#     return clean_output


# def get_inferred_pages(user_story: str, method_map_full: dict):
#     page_list_str = "\n".join(
#         [f"{i+1}. {k.replace('_', ' ')}" for i, k in enumerate(method_map_full.keys())])
#     prompt = f"""
# You are an expert QA automation engineer.
# Given the following available application pages:
# {page_list_str}

# Here is a user story:
# \"\"\"{user_story}\"\"\"

# Output ONLY a Python list (in order) of the page keys (use the keys exactly as shown) that must be visited for this story. Do not explain.
# """
#     result = openai_client.chat.completions.create(
#         model="gpt-4o",
#         messages=[{"role": "user", "content": prompt}],
#         max_tokens=2000,
#         temperature=0
#     )
#     try:
#         output = result.choices[0].message.content.strip()
#         return [p for p in ast.literal_eval(output) if p in method_map_full]
#     except Exception:
#         return list(method_map_full.keys())


# def fix_page_object_initialization(code, page_names):
#     """
#     Replace FooPage(page) with FooPage(page, "foo") for all FooPage classes.
#     page_names: Dict[class_name -> page_name], e.g., {'LoginPage': 'login', ...}
#     """
#     for class_name, page_name in page_names.items():
#         code = re.sub(
#             rf"{class_name}\s*\(\s*page\s*\)",
#             f'{class_name}(page, "{page_name}")',
#             code
#         )
#     return code


# @router.post("/rag/generate-from-story")
# async def generate_from_user_story(
#     user_story: Optional[str] = Form(None),
#     site_url: Optional[str] = Form(
#         "https://preview--bank-buddy-crm-react.lovable.app/"),
#     file: Optional[UploadFile] = File(None)
# ):
#     run_folder = Path("generated_runs") / "src"
#     pages_dir = run_folder / "pages"
#     tests_dir = run_folder / "tests"
#     for d in [pages_dir, tests_dir]:
#         d.mkdir(parents=True, exist_ok=True)
#         (d / "__init__.py").touch()

#     stories = []
#     if file:
#         content = await file.read()
#         if file.filename.endswith((".xls", ".xlsx")):
#             xls = pd.ExcelFile(io.BytesIO(content))
#             df = pd.read_excel(io.BytesIO(content), sheet_name="User Stories")
#         elif file.filename.endswith(".csv"):
#             df = pd.read_csv(io.StringIO(content.decode()))
#         else:
#             raise HTTPException(
#                 status_code=400, detail="Unsupported file type")

#         column_map = {col.strip().lower(): col for col in df.columns}
#         if "user story" not in column_map:
#             raise HTTPException(
#                 status_code=400, detail="Column 'User Story' not found")

#         column_name = column_map["user story"]
#         stories = df[column_name].dropna().astype(str).tolist()

#     elif user_story:
#         stories = [user_story]
#     else:
#         raise HTTPException(
#             status_code=400, detail="Provide user_story or file")

#     all_chroma_data = collection.get()
#     all_chroma_metadatas = all_chroma_data.get("metadatas", [])
#     metadata_dir = run_folder / "metadata"
#     metadata_dir.mkdir(exist_ok=True)
#     with open(metadata_dir / "before_enrichment.json", "w", encoding="utf-8") as f:
#         json.dump(all_chroma_metadatas, f, indent=2)

#     method_map_full = get_all_page_methods(pages_dir)
#     test_functions = []
#     ui_scripts = []

#     # ----- Prepare imports for both test and UI script
#     import_lines = [
#         "import asyncio",
#         "from playwright.async_api import async_playwright",
#     ]
#     # Always sort for consistency
#     page_imports = [
#         f"from pages.{page}_page import {to_pascal_case(page)}"
#         for page in sorted(method_map_full.keys())
#     ]
#     import_lines.extend(page_imports)
#     import_block = "\n".join(import_lines)

#     for story in stories:
#         path_pages = get_inferred_pages(story, method_map_full)
#         sub_method_map = {p: method_map_full[p]
#                           for p in path_pages if p in method_map_full}
#         code = generate_test_code_from_methods(
#             story, sub_method_map, path_pages, site_url)
#         # 👇 Ensure all async test functions are decorated and import is present
#         pattern = r'(?m)^(async def test_)'
#         code = re.sub(pattern, '@pytest.mark.asyncio\n\\1', code)
#         if 'import pytest' not in code:
#             code = 'import pytest\n' + code
#         # Remove _enrich_if_needed calls (if present)
#         code = re.sub(
#             r'await\s+\w+_page\._enrich_if_needed\([^\)]*\)\s*\n', '', code)
#         test_functions.append(code)

#         # --------- UI Script Generation (Standalone, Playwright, NO pytest marker) ---------
#         # Remove pytest decorator and import
#         ui_code = re.sub(r'import pytest\n?', '', code)
#         ui_code = re.sub(r'@pytest\.mark\.asyncio\n?', '', ui_code)
#         # Rename test_user_story/page to main
#         ui_code = re.sub(r'async def test_\w+\(page\):',
#                          'async def main():', ui_code)
#         ui_code = re.sub(r'async def test_user_story\(page\):',
#                          'async def main():', ui_code)

#         # Patch page object initializations to include page_name
#         page_names_map = {to_pascal_case(
#             page): page for page in method_map_full}
#         ui_code = fix_page_object_initialization(ui_code, page_names_map)

#         # Split into lines, remove function def
#         ui_lines = ui_code.splitlines()
#         inside_main = False
#         main_body_lines = []
#         for line in ui_lines:
#             if line.strip().startswith("async def main():"):
#                 inside_main = True
#                 continue
#             if inside_main:
#                 main_body_lines.append(line)
#         # Remove dedent from original generated code
#         main_body = "\n".join(line.lstrip()
#                               for line in main_body_lines if line.strip())

#         # Remove any lines that instantiate page objects to avoid duplicates
#         page_obj_init_pattern = re.compile(
#             r'^\s*\w+_page\s*=\s*\w+Page\(.*\)', re.MULTILINE)
#         main_body_clean = page_obj_init_pattern.sub('', main_body)

#         # Build the required page object instantiations (always all, order same as import)
#         page_vars = []
#         for page in sorted(method_map_full.keys()):
#             class_name = to_pascal_case(page)
#             page_var = f"{page}_page"
#             page_vars.append(
#                 f"        {page_var} = {class_name}(page, \"{page}\")")

#         # Compose the main()
#         main_def = [
#             "async def main():",
#             "    async with async_playwright() as p:",
#             "        browser = await p.chromium.launch(headless=False)",
#             "        page = await browser.new_page()",
#         ]
#         main_def.extend(page_vars)
#         # Add an empty line for readability before main_body
#         if main_body_clean.strip():
#             main_def.append("")
#             # indent all lines in main_body by 2 indents (8 spaces)
#             for code_line in main_body_clean.splitlines():
#                 if code_line.strip():  # skip empty lines
#                     main_def.append("        " + code_line.lstrip())

#         main_code_block = "\n".join(main_def)

#         # Compose full script
#         script_full = (
#             f"{import_block}\n\n{main_code_block}\n\nif __name__ == \"__main__\":\n    asyncio.run(main())\n"
#         )

#         ui_scripts.append(script_full)
#         # --------- END UI Script Generation ----------

#     idx = next_index(tests_dir, "test_{}.py")
#     test_file = tests_dir / f"test_{idx}.py"
#     ui_file = tests_dir / f"ui_scripts_{idx}.py"

#     # --- Patch page object initializations in tests (not needed for ui_scripts, already done above)
#     page_names_map = {to_pascal_case(page): page for page in method_map_full}
#     test_functions = [fix_page_object_initialization(
#         code, page_names_map) for code in test_functions]

#     full_code = "\n\n".join(page_imports + test_functions)
#     test_file.write_text(full_code, encoding="utf-8")
#     create_default_test_data(run_folder)

#     # Write UI script with full imports and Playwright block
#     ui_code_full = "\n\n".join(ui_scripts)
#     ui_file.write_text(ui_code_full, encoding="utf-8")

#     return {"results": stories, "test_file": str(test_file), "ui_script": str(ui_file)}
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pathlib import Path
import re
import json
import ast
import io
import pandas as pd
from typing import List, Optional, Dict

from chromadb import PersistentClient
from services.test_generation_utils import openai_client
# from utils.prompt_utils import build_prompt  # (not needed)

router = APIRouter()

# ─────────────────────────────────────────────
# Stable Chroma location (independent of CWD)
# ─────────────────────────────────────────────
_REPO_ROOT = Path(__file__).resolve().parents[1]  # repo/
CHROMA_DIR = _REPO_ROOT / "generated_runs" / "src" / "data" / "chroma_db"
CHROMA_DIR.mkdir(parents=True, exist_ok=True)
_chroma_client = PersistentClient(path=str(CHROMA_DIR))
collection = _chroma_client.get_or_create_collection(name="element_metadata")


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────
def strip_code_fences(s: str) -> str:
    if not s:
        return ""
    s = s.strip()
    s = re.sub(r"^```(?:python)?\s*", "", s, flags=re.I)
    s = re.sub(r"\s*```$", "", s)
    return s.strip()

def to_pascal_case(name: str) -> str:
    return ''.join(word.capitalize() for word in name.split('_')) + "Page"

def extract_method_names_from_file(file_path: Path) -> List[str]:
    out = []
    with file_path.open("r", encoding="utf-8") as f:
        for line in f:
            t = line.strip()
            if t.startswith("async def "):
                m = re.match(r"async def\s+([A-Za-z_]\w*)\s*\(", t)
                if m:
                    out.append(m.group(1))
    return out

def get_all_page_methods(pages_dir: Path) -> Dict[str, List[str]]:
    page_method_map: Dict[str, List[str]] = {}
    for py_file in Path(pages_dir).glob("*_page.py"):
        page_name = py_file.stem.replace("_page", "")
        page_method_map[page_name] = extract_method_names_from_file(py_file)
    return page_method_map

def next_index(target_dir: Path, pattern="test_{}.py") -> int:
    files = list(target_dir.glob(pattern.format("*")))
    nums = [int(m.group(1)) for f in files if (m := re.match(r".*_(\d+)\.", f.name))]
    return max(nums, default=0) + 1

def fix_page_object_initialization(code: str, page_names: Dict[str, str]) -> str:
    # Replace FooPage(page) with FooPage(page, "foo") across code
    for class_name, page_name in page_names.items():
        code = re.sub(
            rf"{class_name}\s*\(\s*page\s*\)",
            f'{class_name}(page, "{page_name}")',
            code
        )
    return code

def _infer_pages_order(user_story: str, method_map_full: Dict[str, List[str]]) -> List[str]:
    """
    Try to infer page visit order from the story via LLM; fall back to all pages if parsing fails.
    """
    if not method_map_full:
        return []
    page_list_str = "\n".join([f"{i+1}. {k.replace('_', ' ')}" for i, k in enumerate(method_map_full.keys())])
    prompt = f"""
You are an expert QA automation engineer.
Given the following available application pages:
{page_list_str}

Here is a user story:
\"\"\"{user_story}\"\"\"

Output ONLY a Python list (in order) of the page keys (use the keys exactly as shown) that must be visited for this story. Do not explain.
"""
    try:
        result = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2000,
            temperature=0
        )
        out = result.choices[0].message.content.strip()
        pages = [p for p in ast.literal_eval(out) if p in method_map_full]
        return pages or list(method_map_full.keys())
    except Exception:
        return list(method_map_full.keys())

def _generate_test_code_from_methods(user_story: str, method_map: Dict[str, List[str]], site_url: str) -> str:
    # Prompt that asks the model to generate a single async pytest test using only given page methods
    story_block = f'"""{user_story.strip()}"""'
    method_prompt_block = json.dumps({f"{page}_page": methods for page, methods in method_map.items()}, indent=2)
    prompt = f"""
You are an expert QA automation engineer.

You are given the following:
- A user story.
- A set of page classes with available async methods.
- Each page is initialized like `customers_page = CustomersPage(page)`
- Method calls are in the form: `await page_var.method_name()` or `await page_var.method_name(value)`

Using only the available methods, generate a full Playwright async **pytest** test case that fulfills the story.

Constraints:
- Use only the provided method names.
- Do not generate selectors or locators.
- Use `async def` test function.
- Use `await` before all page method calls.
- Name the test function `test_user_story`.
- Do not explain anything. Output code only.

User Story:
{story_block}

Pages and Methods:
{method_prompt_block}

URL: {site_url}
"""
    result = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=4096,
        temperature=0
    )
    raw = result.choices[0].message.content
    code = strip_code_fences(raw)

    # Ensure pytest marker/imports
    if re.search(r"(?m)^\s*async def\s+test_", code):
        code = re.sub(r'(?m)^(async def test_)', '@pytest.mark.asyncio\n\\1', code)
    if 'import pytest' not in code:
        code = 'import pytest\n' + code

    # Remove any private enrich calls if the model added them
    code = re.sub(r'await\s+\w+_page\._enrich_if_needed\([^\)]*\)\s*\n', '', code)
    return code


# ─────────────────────────────────────────────
# API
# ─────────────────────────────────────────────
@router.post("/rag/generate-from-story")
async def generate_from_user_story(
    user_story: Optional[str] = Form(None),
    site_url: Optional[str] = Form("https://preview--bank-buddy-crm-react.lovable.app/"),
    file: Optional[UploadFile] = File(None)
):
    run_folder = Path("generated_runs") / "src"
    pages_dir = run_folder / "pages"
    tests_dir = run_folder / "tests"
    metadata_dir = run_folder / "metadata"

    # Ensure structure & packages
    for d in (run_folder, pages_dir, tests_dir, metadata_dir):
        d.mkdir(parents=True, exist_ok=True)
        if d.name in {"src", "pages", "tests"}:
            (d / "__init__.py").touch()

    # Collect stories (Excel/CSV or single)
    stories: List[str] = []
    if file:
        content = await file.read()
        if file.filename.endswith((".xls", ".xlsx")):
            df = pd.read_excel(io.BytesIO(content), sheet_name=0)
        elif file.filename.endswith(".csv"):
            df = pd.read_csv(io.StringIO(content.decode()))
        else:
            raise HTTPException(status_code=400, detail="Unsupported file type")

        lower_cols = {c.strip().lower(): c for c in df.columns}
        col = next((lower_cols[k] for k in ("user story", "user_story", "story", "scenario") if k in lower_cols), None)
        if not col:
            raise HTTPException(status_code=400, detail="No 'User Story' column found")
        stories = df[col].dropna().astype(str).tolist()
    elif user_story:
        stories = [user_story]
    else:
        raise HTTPException(status_code=400, detail="Provide user_story or upload a file")

    # Snapshot current metadatas (optional)
    all_chroma_data = collection.get()
    all_chroma_metadatas = all_chroma_data.get("metadatas", []) or []
    (metadata_dir / "before_enrichment.json").write_text(json.dumps(all_chroma_metadatas, indent=2), encoding="utf-8")

    # Discover available POM page methods
    method_map_full = get_all_page_methods(pages_dir)

    # ⚠️ Important: Fail clearly if no pages found (most common cause of “no test cases”)
    if not method_map_full:
        raise HTTPException(
            status_code=400,
            detail=f"No page classes found. Put async POM files like '{pages_dir}/<name>_page.py' with async methods."
        )

    # Build import block for UI script
    import_lines = [
        "import asyncio",
        "from playwright.async_api import async_playwright",
    ]
    page_imports = [
        f"from pages.{page}_page import {to_pascal_case(page)}"
        for page in sorted(method_map_full.keys())
    ]
    import_lines.extend(page_imports)
    import_block = "\n".join(import_lines)

    test_functions: List[str] = []
    ui_scripts: List[str] = []
    per_story_results: List[Dict] = []

    for story in stories:
        # Robust page inference with safe fallback
        path_pages = _infer_pages_order(story, method_map_full)
        sub_method_map = {p: method_map_full[p] for p in path_pages if p in method_map_full}

        # Generate pytest async POM test
        code = _generate_test_code_from_methods(story, sub_method_map, site_url)

        # Patch FooPage(page) → FooPage(page, "foo")
        page_names_map = {to_pascal_case(page): page for page in method_map_full}
        code = fix_page_object_initialization(code, page_names_map)
        test_functions.append(code)

        # Build standalone UI script (no pytest)
        ui_code = re.sub(r'(?m)^import pytest\n?', '', code)
        ui_code = re.sub(r'(?m)^@pytest\.mark\.asyncio\n?', '', ui_code)
        ui_code = re.sub(r'async def test_\w+\(page\):', 'async def main():', ui_code)
        ui_code = re.sub(r'async def test_user_story\(page\):', 'async def main():', ui_code)

        # Grab main() body
        lines = ui_code.splitlines()
        body_lines, inside = [], False
        for ln in lines:
            if ln.strip().startswith("async def main():"):
                inside = True
                continue
            if inside:
                body_lines.append(ln)
        main_body = "\n".join(l.lstrip() for l in body_lines if l.strip())

        # Strip any duplicate page instantiations in body
        main_body = re.sub(r'^\s*\w+_page\s*=\s*\w+Page\(.*\)\s*$', '', main_body, flags=re.M)

        page_vars = [
            f'        {page}_page = {to_pascal_case(page)}(page, "{page}")'
            for page in sorted(method_map_full.keys())
        ]

        main_def = [
            "async def main():",
            "    async with async_playwright() as p:",
            "        browser = await p.chromium.launch(headless=False)",
            "        page = await browser.new_page()",
            *page_vars
        ]
        if main_body.strip():
            main_def.append("")
            main_def.extend(["        " + ln.lstrip() for ln in main_body.splitlines() if ln.strip()])

        script_full = f"{import_block}\n\n" + "\n".join(main_def) + \
                      '\n\nif __name__ == "__main__":\n    asyncio.run(main())\n'
        ui_scripts.append(script_full)

        # NOTE: include legacy key 'auto_testcase' so your test2 frontend renders this
        per_story_results.append({
            "story": story,
            "test_code": code,         # test3 key
            "auto_testcase": code,     # legacy key expected by test2 UI
            "ui_code": script_full
        })

    # Write combined files (single test file + single ui script file)
    idx = next_index(tests_dir, "test_{}.py")
    test_file = tests_dir / f"test_{idx}.py"
    ui_file = tests_dir / f"ui_scripts_{idx}.py"

    full_test_code = "\n\n".join(
        [f"from pages.{p}_page import {to_pascal_case(p)}" for p in sorted(method_map_full.keys())] + test_functions
    )
    test_file.write_text(full_test_code, encoding="utf-8")

    full_ui_code = "\n\n".join(ui_scripts)
    ui_file.write_text(full_ui_code, encoding="utf-8")

    # Return both file paths and code so the frontend can render immediately
    for item in per_story_results:
        item["test_filename"] = str(test_file.relative_to(run_folder))
        item["ui_filename"] = str(ui_file.relative_to(run_folder))

    return {
        "status": "ok",
        "count": len(stories),
        "results": per_story_results,
        "paths": {"test_file": str(test_file), "ui_script": str(ui_file)}
    }
