from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pathlib import Path
import re
import json
import ast
import pandas as pd
from pydantic import BaseModel, Field
from typing import List, Optional
import textwrap
from chromadb import PersistentClient
import io

from services.test_generation_utils import openai_client
from utils.prompt_utils import build_prompt
from utils.match_utils import normalize_page_name
from services.graph_service import read_dependency_graph, get_adjacency_list, find_path

router = APIRouter()
chroma_client = PersistentClient(path="./data/chroma_db")
collection = chroma_client.get_or_create_collection(name="element_metadata")


def create_default_test_data(run_folder):
    data = {
        "login": {"username": "standard_user", "password": "secret_sauce"},
        "checkout": {"first_name": "John", "last_name": "Doe", "zip_code": "12345"},
        "product": {"name": "Sauce Labs Backpack"}
    }
    data_dir = Path(run_folder) / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "__init__.py").touch()
    with open(data_dir / "test_data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def extract_method_names_from_file(file_path):
    method_names = []
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("async def "):
            m = re.match(
                r"async def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(", stripped)
            if m:
                method_names.append(m.group(1))
    return method_names


def get_all_page_methods(pages_dir):
    page_method_map = {}
    for py_file in Path(pages_dir).glob("*_page.py"):
        page_name = py_file.stem.replace("_page", "")
        method_list = extract_method_names_from_file(py_file)
        print(f"📄 {page_name}: {len(method_list)} methods")
        page_method_map[page_name] = method_list
    return page_method_map


def next_index(target_dir, pattern="test_{}.py"):
    files = list(target_dir.glob(pattern.format("*")))
    indices = [int(m.group(1))
               for f in files if (m := re.match(r".*_(\d+)\.", f.name))]
    return max(indices, default=0) + 1


def to_pascal_case(name: str) -> str:
    return ''.join(word.capitalize() for word in name.split('_')) + "Page"


def generate_test_code_from_methods(user_story, method_map, page_names, site_url):
    story_block = f'"""{user_story.strip()}"""'
    method_prompt_block = json.dumps(
        {f"{page}_page": methods for page, methods in method_map.items()}, indent=2)

    prompt = f"""
You are an expert QA automation engineer.

You are given the following:
- A user story.
- A set of page classes with available async methods.
- Each page is initialized like `customers_page = CustomersPage(page)`
- Method calls are in the form: `await page_name.method_name()` or `await page_name.method_name(value)`

Using only the available methods, generate a full Playwright async test case that fulfills the story.

Constraints:
- Use only the provided method names.
- Do not generate selectors or locators.
- Use `async def` test function.
- Use `await` before all page method calls.
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

    print("\n📤 Prompt sent to LLM:\n", prompt)
    print("\n📥 LLM raw response:\n", result.choices[0].message.content)

    clean_output = re.sub(r"```(?:python)?|^\s*Here is.*?:", "",
                          result.choices[0].message.content.strip(), flags=re.MULTILINE).strip()
    return clean_output


def get_inferred_pages(user_story: str, method_map_full: dict):
    page_list_str = "\n".join(
        [f"{i+1}. {k.replace('_', ' ')}" for i, k in enumerate(method_map_full.keys())])
    prompt = f"""
You are an expert QA automation engineer.
Given the following available application pages:
{page_list_str}

Here is a user story:
\"\"\"{user_story}\"\"\"

Output ONLY a Python list (in order) of the page keys (use the keys exactly as shown) that must be visited for this story. Do not explain.
"""
    result = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=2000,
        temperature=0
    )
    try:
        output = result.choices[0].message.content.strip()
        return [p for p in ast.literal_eval(output) if p in method_map_full]
    except Exception:
        return list(method_map_full.keys())


def fix_page_object_initialization(code, page_names):
    for class_name, page_name in page_names.items():
        code = re.sub(
            rf"{class_name}\s*\(\s*page\s*\)",
            f'{class_name}(page, "{page_name}")',
            code
        )
    return code


@router.post("/rag/generate-from-story")
async def generate_from_user_story(
    user_story: Optional[str] = Form(None),
    site_url: Optional[str] = Form(
        "https://preview--bank-buddy-crm-react.lovable.app/"),
    file: Optional[UploadFile] = File(None)
):
    run_folder = Path("generated_runs") / "src"
    pages_dir = run_folder / "pages"
    tests_dir = run_folder / "tests"
    for d in [pages_dir, tests_dir]:
        d.mkdir(parents=True, exist_ok=True)
        (d / "__init__.py").touch()

    stories = []
    if file:
        content = await file.read()
        if file.filename.endswith((".xls", ".xlsx")):
            df = pd.read_excel(io.BytesIO(content), sheet_name="User Stories")
        elif file.filename.endswith(".csv"):
            df = pd.read_csv(io.StringIO(content.decode()))
        else:
            raise HTTPException(
                status_code=400, detail="Unsupported file type")

        column_map = {col.strip().lower(): col for col in df.columns}
        if "user story" not in column_map:
            raise HTTPException(
                status_code=400, detail="Column 'User Story' not found")

        column_name = column_map["user story"]
        stories = df[column_name].dropna().astype(str).tolist()

    elif user_story:
        stories = [user_story]
    else:
        raise HTTPException(
            status_code=400, detail="Provide user_story or file")

    all_chroma_data = collection.get()
    all_chroma_metadatas = all_chroma_data.get("metadatas", [])
    metadata_dir = run_folder / "metadata"
    metadata_dir.mkdir(exist_ok=True)
    with open(metadata_dir / "before_enrichment.json", "w", encoding="utf-8") as f:
        json.dump(all_chroma_metadatas, f, indent=2)

    method_map_full = get_all_page_methods(pages_dir)
    test_functions, ui_scripts = [], []

    page_names_map = {to_pascal_case(page): page for page in method_map_full}

    for story in stories:
        path_pages = get_inferred_pages(story, method_map_full)
        sub_method_map = {p: method_map_full[p]
                          for p in path_pages if p in method_map_full}
        code = generate_test_code_from_methods(
            story, sub_method_map, path_pages, site_url)

        # Test Code Adjustments
        code = re.sub(r'(?m)^(async def test_)',
                      '@pytest.mark.asyncio\n\\1', code)
        if 'import pytest' not in code:
            code = 'import pytest\n' + code
        code = re.sub(
            r'await\s+\w+_page\._enrich_if_needed\([^\)]*\)\s*\n', '', code)
        test_functions.append(
            fix_page_object_initialization(code, page_names_map))

        # UI Script Adjustments
        ui_code = re.sub(r'import pytest\n?', '', code)
        ui_code = re.sub(r'@pytest\.mark\.asyncio\n?', '', ui_code)
        ui_code = re.sub(r'async def test_\w+\(page\):',
                         'async def main():', ui_code)
        ui_code = fix_page_object_initialization(ui_code, page_names_map)

        main_body_match = re.search(
            r'async def main\(\):\n((?:.|\n)*)', ui_code)
        main_body_lines = main_body_match.group(
            1).splitlines() if main_body_match else []
        main_body_clean = [line.strip()
                           for line in main_body_lines if line.strip()]

        # Detect first usage and initialize exactly before that
        page_class_names = {page: to_pascal_case(
            page) for page in method_map_full}
        seen_pages = set()
        adjusted_main_body = []
        for line in main_body_clean:
            method_call_match = re.match(r'await\s+(\w+_page)\.', line)
            if method_call_match:
                page_var = method_call_match.group(1)
                page_key = page_var.replace("_page", "")
                if page_key not in seen_pages:
                    instantiation_line = f"{page_var} = {page_class_names[page_key]}(page, '{page_key}')"
                    adjusted_main_body.append(instantiation_line)
                    seen_pages.add(page_key)
            adjusted_main_body.append(line)

        # Compose UI script imports
        ui_imports = [
            "import asyncio",
            "from playwright.async_api import async_playwright",
            "from generated_runs.src.pages.base_page import BasePage",
        ] + [
            f"from generated_runs.src.pages.{page}_page import {to_pascal_case(page)}"
            for page in sorted(method_map_full)
        ]

        # Final UI Script
        ui_script_full = f"""{chr(10).join(ui_imports)}

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        base_page = BasePage(page, "base", url='{site_url}')
        await base_page.goto("{site_url}")

{"".join(f"        {line}\n" for line in adjusted_main_body)}

if __name__ == "__main__":
    asyncio.run(main())
""".strip()

        ui_scripts.append(ui_script_full)

    idx = next_index(tests_dir, "test_{}.py")
    test_file = tests_dir / f"test_{idx}.py"
    ui_file = tests_dir / f"ui_scripts_{idx}.py"

    full_test_code = "\n\n".join(
        [f"from generated_runs.src.pages.{page}_page import {to_pascal_case(page)}"
         for page in sorted(method_map_full)]
        + test_functions
    )
    test_file.write_text(full_test_code, encoding="utf-8")

    ui_code_full = "\n\n".join(ui_scripts)
    ui_file.write_text(ui_code_full, encoding="utf-8")

    create_default_test_data(run_folder)

    return {"results": stories, "test_file": str(test_file), "ui_script": str(ui_file)}
