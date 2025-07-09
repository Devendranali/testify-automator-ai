from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import re
import json
import ast
from pydantic import BaseModel, Field
from typing import List, Optional
import os
import textwrap
import subprocess
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = FastAPI(title="Test Generation Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Placeholder for ChromaDB client - assuming it's available as a separate service
# or that this service will connect to the main ChromaDB instance.
# For now, we'll assume a direct connection to the chromadb service.
import chromadb
chroma_client = chromadb.HttpClient(host=os.getenv("CHROMA_DB_HOST", "chromadb"), port=os.getenv("CHROMA_DB_PORT", "8000"))

try:
    collection = chroma_client.get_or_create_collection(name="element_metadata")
except Exception as e:
    print(f"Error connecting to ChromaDB or getting collection: {e}")
    collection = None # Handle case where ChromaDB is not available


# Placeholder for imported functions - these files will be copied or refactored
# For now, we'll assume they are available in the same directory or via PYTHONPATH
# In a real microservice, these would be part of this service's codebase or a shared library.

# From services/graph_service.py (assuming it's a shared utility or copied)
# For now, I'll put a dummy here. In a real scenario, this would be imported from a local copy.
def read_dependency_graph(input_path: str = "./data/navigation_graph.json") -> List[dict]:
    print("Using dummy read_dependency_graph.")
    return []

def get_adjacency_list(edges: List[dict]) -> dict:
    print("Using dummy get_adjacency_list.")
    return {}

def find_path(graph, start, end):
    print("Using dummy find_path.")
    return []

# From services/test_generation_utils.py
# This needs to be copied or refactored.
class OpenAIClient:
    def chat(self):
        return self
    def completions(self):
        return self
    def create(self, model, messages, max_tokens):
        print("Using dummy OpenAI client. Actual implementation needs to be copied.")
        # Dummy response for testing
        return type('obj', (object,), {'choices': [type('obj', (object,), {'message': type('obj', (object,), {'content': "def test_dummy():\n    pass"})})]})()

openai_client = OpenAIClient()

# From utils/match_utils.py
# This needs to be copied or refactored.
def normalize_page_name(input_string: str) -> str:
    print("Using dummy normalize_page_name.")
    return input_string.replace(".png", "").replace(".jpg", "").replace(".jpeg", "").replace(".bmp", "").replace(".gif", "").replace(".webp", "").lower()

# From utils/prompt_utils.py
# This needs to be copied or refactored.
def build_prompt(story_block, method_map, page_names, site_url, dynamic_steps):
    print("Using dummy build_prompt.")
    return "Dummy prompt"


class UserStoryRequest(BaseModel):
    user_story: str | List[str]
    site_url: Optional[str] = Field(default="https://www.saucedemo.com")

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
            m = re.match(r"def\s+([a-zA-Z_][a-zA-Z0-9_]*)\((", line)
            if m:
                method_names.append(m.group(1))
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
                dynamic_steps.append(f"    - Call `{method}(\"<"+param+">\")`")
            elif method.startswith("click_") or method.startswith("select_"):
                dynamic_steps.append(f"    - Call `{method}()`")
            elif method.startswith("verify_"):
                readable = method.replace(
                    "verify_", "").replace("_", " ").capitalize()
                dynamic_steps.append(
                    f"    - Assert `{method}()` → checks if **{readable}** is visible")
    user_story_clean = user_story.replace('"""', '"""')
    story_block = f'"""{user_story_clean}"""'

    # Storing the dynamic_steps.
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
    # Storing the prompts
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

    # Use the correct OpenAI client here!
    result = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=4096
    )

    # Clean the result text
    clean_output = re.sub(
        r"```(?:python)?|^\s*Here is.*?:",
        "",
        result.choices[0].message.content.strip(),
        flags=re.MULTILINE
    ).strip()

    # Store the output in test_output_<n>.py
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
    result = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=256,
    )
    output = result.choices[0].message.content.strip()
    try:
        inferred_pages = ast.literal_eval(output)
        return [p for p in inferred_pages if p in method_map_full]
    except Exception:
        return list(method_map_full.keys())

@app.post("/rag/generate-from-story")
def generate_from_user_story(req: UserStoryRequest):
    run_folder = Path("generated_runs") / "src"
    pages_dir = run_folder / "pages"
    tests_dir = run_folder / "tests"
    logs_dir = run_folder / "logs"
    meta_dir = run_folder / "metadata"
    for d in [pages_dir, tests_dir, logs_dir, meta_dir]:
        d.mkdir(parents=True, exist_ok=True)
        (d / "__init__.py").touch()
    (run_folder / "__init__.py").touch()

    # Save all ChromaDB metadata as before_enrichment.json before running test generation
    all_chroma_data = collection.get()
    all_chroma_metadatas = all_chroma_data.get("metadatas", [])

    before_file = meta_dir / "before_enrichment.json"
    with open(before_file, "w", encoding="utf-8") as f:
        json.dump(all_chroma_metadatas, f, indent=2)

    method_map_full = get_all_page_methods(pages_dir)

    stories = req.user_story if isinstance(req.user_story, list) else [req.user_story]
    results, test_functions = [], []
    all_path_pages = []

    for story in stories:
        path_pages = get_inferred_pages(story, method_map_full, openai_client)
        if not path_pages:
            continue
        all_path_pages.extend(path_pages)
        sub_method_map = {p: method_map_full[p] for p in path_pages if p in method_map_full}
        code = generate_test_code_from_methods(story, sub_method_map, path_pages, req.site_url)
        test_functions.append(code)
        results.append({
            "Prompt": f" Prompt\n\n1. {story}\nExpected: Success",
            "auto_testcase": code,
        })

    test_idx = next_index(tests_dir, "test_{}.py")
    log_idx = next_index(logs_dir, "logs_{}.log")
    test_file = tests_dir / f"test_{test_idx}.py"
    log_file = logs_dir / f"logs_{log_idx}.log"

    page_method_files = sorted((pages_dir).glob("*_page_methods.py"))
    import_lines = ["from playwright.sync_api import sync_playwright"]
    for file in page_method_files:
        module_name = file.stem
        import_lines.append(f"from pages.{module_name} import *")

    test_file.write_text("\n\n".join(import_lines + test_functions), encoding="utf-8")

    if all_path_pages:
        log_file.write_text("\n".join(all_path_pages), encoding="utf-8")
    else:
        log_file.write_text("No stories were processed.", encoding="utf-8")

    meta_file = meta_dir / "metadata.json"
    if not meta_file.exists():
        metadata = {
            "timestamp": test_file.stat().st_mtime,
            "pages": all_path_pages,
            "test_files": [str(test_file.name)],
            "log_files": [str(log_file.name)],
        }
        json.dump(metadata, open(meta_file, "w"), indent=2)
    
    create_default_test_data(run_folder)

    # ================== ui_script.py generation block =======================

    test_files = sorted(tests_dir.glob("test_*.py"), key=lambda f: f.stat().st_mtime, reverse=True)
    if not test_files:
        print("No test_*.py files found in", tests_dir.resolve())
        print("Contents:", list(tests_dir.glob("*")))
    else:
        latest_test = test_files[0]

        # 2. Collect all page method imports
        page_imports = set()
        with open(latest_test, "r", encoding="utf-8") as f:
            for line in f:
                if re.match(r"from pages\.", line):
                    page_imports.add(line.rstrip())

        # 3. Parse all test functions and inline their bodies as run_* functions
        func_blocks = []
        with open(latest_test, "r", encoding="utf-8") as f:
            lines = f.readlines()

        func_name = None
        func_body = []
        in_func = False
        for i, line in enumerate(lines):
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
                if re.match(r"def [a-zA-Z_]", line) or (line.startswith(" ") and not line.startswith("    ")):
                    in_func = False
                    continue
                func_body.append(line)
        if func_name and func_body:
            body = ''.join(func_body)
            func_blocks.append((func_name, body))

        # 4. Compose one run_* function for each, dedenting and re-indenting properly
        wrapper_blocks = []
        runner_func_names = []
        for func_name, func_body in func_blocks:
            runner_name = "run_" + func_name.replace("test_", "")
            runner_func_names.append(runner_name)
            dedented = textwrap.dedent(func_body)
            step_lines = []
            for l in dedented.strip('\n').splitlines():
                step_lines.append("        " + l if l.strip() else "")
            steps = "\n".join(step_lines)
            wrapper_blocks.append(
f"""def {runner_name}():
    import time
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=300)
        page = browser.new_page()
        # Patch SmartAI
        metadata_path = Path(__file__).parent.parent / "metadata" / "after_enrichment.json"
        with open(metadata_path, "r") as f:
            actual_metadata = json.load(f)
        # Assuming patch_page_with_smartai is available in this service's context
        # from lib.smart_ai import patch_page_with_smartai
        # patch_page_with_smartai(page, actual_metadata)
        print("Patching page with SmartAI - placeholder")
{steps}
        time.sleep(5)
        browser.close()

""")

        # 5. Compose the file header (NO leading indentation!)
        header = "# Auto-generated UI runner\n\nfrom playwright.sync_api import sync_playwright\nimport json\nfrom pathlib import Path\n"
        if page_imports:
            header += "\n".join(page_imports) + "\n"
        # header += "from lib.smart_ai import patch_page_with_smartai\n\n" # Removed actual import
        header += "\n\n"

        # 6. Compose the main block using try/except and collect errors
        main_block = "if __name__ == '__main__':\n"
        main_block += "    errors = []\n"
        main_block += "    for func in [\n"
        for runner_name in runner_func_names:
            main_block += f"        {runner_name},\n"
        main_block += "    ]:\n"
        main_block += "        try:\n"
        main_block += "            func()\n"
        main_block += "        except Exception as e:\n"
        main_block += "            print(f\"[ERROR] {func.__name__} failed: {e}\")\n"
        main_block += "            errors.append({'function': func.__name__, 'error': str(e)})\n"
        main_block += "    if errors:\n"
        main_block += "        print("\\nSummary of failures:")\n"
        main_block += "        for err in errors:\n"
        main_block += "            print(f\" - {err['function']} failed: {err['error']}\")\n"
        main_block += "    else:\n"
        main_block += "        print("\\nAll scenarios executed successfully!")\n"

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

        print(f"✅ {ui_script_filename} generated with {len(wrapper_blocks)} runner(s) in {tests_dir}")

    # ================== End ui_script.py generation block ===================

    return {"results": results, "test_file": str(test_file), "log_file": str(log_file)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8006) # Using a different port for the new service
