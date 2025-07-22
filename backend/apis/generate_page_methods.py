# generate_page_methods.py

from fastapi import APIRouter
from pathlib import Path
import re
from services.test_generation_utils import collection, filter_all_pages
from utils.smart_ai_utils import ensure_smart_ai_module
from orchestrator.orchestrator import send_message

router = APIRouter()

def safe(s):
    return re.sub(r'\W+', '_', s.lower()).strip('_')

# New
def build_method(entry):
    ocr_type = (entry.get("ocr_type") or "").lower()
    intent = (entry.get("intent") or "").lower()
    label_text = entry.get("label_text", "")
    unique_name = entry.get("unique_name")

    def func(name):
        return safe(label_text or intent or name)

    # -- Text Inputs --
    if ocr_type in ("textbox", "text", "input"):
        func_name = f"enter_{func('textbox')}"
        code = (
            f"def {func_name}(page, value):\n"
            f"    page.smartAI('{unique_name}').fill(value)\n"
        )
    elif ocr_type == "textarea":
        func_name = f"enter_{func('textarea')}"
        code = (
            f"def {func_name}(page, value):\n"
            f"    page.smartAI('{unique_name}').fill(value)\n"
        )
    elif ocr_type == "password":
        func_name = f"enter_{func('password')}"
        code = (
            f"def {func_name}(page, value):\n"
            f"    page.smartAI('{unique_name}').fill(value)\n"
        )
    elif ocr_type == "email":
        func_name = f"enter_{func('email')}"
        code = (
            f"def {func_name}(page, value):\n"
            f"    page.smartAI('{unique_name}').fill(value)\n"
        )
    # -- Buttons, Links, Icons --
    elif ocr_type in ("button", "submit", "iconbutton"):
        func_name = f"click_{func('button')}"
        code = (
            f"def {func_name}(page):\n"
            f"    page.smartAI('{unique_name}').click()\n"
        )
    elif ocr_type in ("link", "anchor"):
        func_name = f"click_{func('link')}"
        code = (
            f"def {func_name}(page):\n"
            f"    page.smartAI('{unique_name}').click()\n"
        )
    elif ocr_type == "imagebutton":
        func_name = f"click_{func('imagebutton')}"
        code = (
            f"def {func_name}(page):\n"
            f"    page.smartAI('{unique_name}').click()\n"
        )
    # -- Selectors --
    elif ocr_type in ("select", "dropdown", "combobox"):
        func_name = f"select_{func('select')}"
        code = (
            f"def {func_name}(page, value):\n"
            f"    page.smartAI('{unique_name}').select_option(value)\n"
        )
    elif ocr_type == "multiselect":
        func_name = f"select_{func('multiselect')}_values"
        code = (
            f"def {func_name}(page, values):\n"
            f"    page.smartAI('{unique_name}').select_options(values)\n"
        )
    # -- Checkboxes, Radios, Toggles, Switches --
    elif ocr_type == "checkbox":
        func_name = f"toggle_{func('checkbox')}"
        code = (
            f"def {func_name}(page):\n"
            f"    page.smartAI('{unique_name}').click()\n"
        )
    elif ocr_type in ("radio", "radiogroup"):
        func_name = f"select_{func('radio')}_option"
        code = (
            f"def {func_name}(page, value):\n"
            f"    page.smartAI('{unique_name}').check(value)\n"
        )
    elif ocr_type in ("toggle", "switch"):
        func_name = f"toggle_{func('toggle')}"
        code = (
            f"def {func_name}(page):\n"
            f"    page.smartAI('{unique_name}').click()\n"
        )
    # -- Date/Time Pickers --
    elif ocr_type in ("date", "datepicker"):
        func_name = f"pick_{func('date')}"
        code = (
            f"def {func_name}(page, value):\n"
            f"    page.smartAI('{unique_name}').fill(value)\n"
        )
    elif ocr_type in ("time", "timepicker"):
        func_name = f"pick_{func('time')}"
        code = (
            f"def {func_name}(page, value):\n"
            f"    page.smartAI('{unique_name}').fill(value)\n"
        )
    # -- File Upload --
    elif ocr_type in ("file", "fileinput", "upload"):
        func_name = f"upload_{func('file')}"
        code = (
            f"def {func_name}(page, file_path):\n"
            f"    page.smartAI('{unique_name}').set_input_files(file_path)\n"
        )
    # -- Table/Grid/Data Grid --
    elif ocr_type in ("table", "datatable", "grid"):
        func_name = f"read_{func('table')}_data"
        code = (
            f"def {func_name}(page):\n"
            f"    return page.smartAI('{unique_name}').get_table_data()\n"
        )
    elif ocr_type in ("tablecell", "cell"):
        func_name = f"get_{func('cell')}_text"
        code = (
            f"def {func_name}(page, row, col):\n"
            f"    return page.smartAI('{unique_name}').get_cell_text(row, col)\n"
        )
    # -- Image --
    elif ocr_type == "image":
        func_name = f"verify_{func('image')}_visible"
        code = (
            f"def {func_name}(page):\n"
            f"    assert page.smartAI('{unique_name}').is_visible()\n"
        )
    # -- Slider/Range --
    elif ocr_type in ("slider", "range"):
        func_name = f"set_{func('slider')}_value"
        code = (
            f"def {func_name}(page, value):\n"
            f"    page.smartAI('{unique_name}').fill(value)\n"
        )
    # -- Progressbar --
    elif ocr_type == "progressbar":
        func_name = f"get_{func('progressbar')}_value"
        code = (
            f"def {func_name}(page):\n"
            f"    return page.smartAI('{unique_name}').get_attribute('value')\n"
        )
    # -- Alert/Dialog/Modal/Toast --
    elif ocr_type in ("alert", "dialog", "modal", "toast"):
        func_name = f"verify_{func('alert')}_visible"
        code = (
            f"def {func_name}(page):\n"
            f"    assert page.smartAI('{unique_name}').is_visible()\n"
        )
    # -- Tab/Accordion/Panel --
    elif ocr_type in ("tab", "tabpanel"):
        func_name = f"open_{func('tab')}"
        code = (
            f"def {func_name}(page):\n"
            f"    page.smartAI('{unique_name}').click()\n"
        )
    elif ocr_type in ("accordion", "panel"):
        func_name = f"expand_{func('accordion')}"
        code = (
            f"def {func_name}(page):\n"
            f"    page.smartAI('{unique_name}').click()\n"
        )
    # -- Tree/Treeview --
    elif ocr_type in ("tree", "treeview"):
        func_name = f"expand_{func('tree')}"
        code = (
            f"def {func_name}(page, node_label):\n"
            f"    page.smartAI('{unique_name}').expand_node(node_label)\n"
        )
    # -- Menu --
    elif ocr_type in ("menu", "menubar"):
        func_name = f"open_{func('menu')}"
        code = (
            f"def {func_name}(page):\n"
            f"    page.smartAI('{unique_name}').click()\n"
        )
    # -- Breadcrumb --
    elif ocr_type == "breadcrumb":
        func_name = f"navigate_{func('breadcrumb')}"
        code = (
            f"def {func_name}(page, crumb_label):\n"
            f"    page.smartAI('{unique_name}').click_crumb(crumb_label)\n"
        )
    # -- Badge/Chip/Tag --
    elif ocr_type in ("badge", "chip", "tag"):
        func_name = f"verify_{func('badge')}_visible"
        code = (
            f"def {func_name}(page):\n"
            f"    assert page.smartAI('{unique_name}').is_visible()\n"
        )
    # -- Avatar/Userpic --
    elif ocr_type in ("avatar", "userpic"):
        func_name = f"verify_{func('avatar')}_visible"
        code = (
            f"def {func_name}(page):\n"
            f"    assert page.smartAI('{unique_name}').is_visible()\n"
        )
    # -- Pagination --
    elif ocr_type == "pagination":
        func_name = f"goto_{func('page')}"
        code = (
            f"def {func_name}(page, page_number):\n"
            f"    page.smartAI('{unique_name}').goto_page(page_number)\n"
        )
    # -- Default/Fallback --
    else:
        func_name = f"verify_{func('element')}_visible"
        code = (
            f"def {func_name}(page):\n"
            f"    assert page.smartAI('{unique_name}').is_visible()\n"
        )
    return code


@router.post("/rag/generate-page-methods")
def generate_page_methods():
    ensure_smart_ai_module()
    target_pages = filter_all_pages()
    print("apis.generate_page_methods.py | target_pages = ", target_pages)
    result = {}

    # Setting the path and content for conftest.py 
    def create_conftest_file():
        conftest_content = '''import pytest
import json
from pathlib import Path
from lib.smart_ai import patch_page_with_smartai

@pytest.fixture(autouse=True)
def smartai_page(page):    
    # Get the path to THIS FILE's directory
    script_dir = Path(__file__).parent
    # Go up one to 'src', then into 'metadata'
    metadata_path = (script_dir.parent / "metadata" / "after_enrichment.json").resolve()

    # print("Loading:", metadata_path)  # Debug, can remove

    with open(metadata_path, "r") as f:
        actual_metadata = json.load(f)
    patch_page_with_smartai(page, actual_metadata)
    return page
'''

        # Navigate from /apis/ to /generated_runs/src/tests
        tests_dir = Path(__file__).parent.parent / "generated_runs" / "src" / "tests"
        tests_dir.mkdir(parents=True, exist_ok=True)

        conftest_path = tests_dir / "conftest.py"
        conftest_path.write_text(conftest_content.strip())
        # print(f"✅ conftest.py created at: {conftest_path}")
    # Creating conftest.py
    create_conftest_file()


    for page in target_pages:
        page_data = collection.get(where={"page_name": page})
        entries = [r for r in page_data.get("metadatas", [])]
        # entries = page_data.get("documents", [])

        # Use agent to generate code and filename
        response = send_message("python", "generate_page_file", {"entries": entries, "page_name": page})
        payload = response.payload   # This is a dict: {"filename": ..., "code": ...}

        outdir = Path("generated_runs") / "src" / "pages"
        outdir.mkdir(parents=True, exist_ok=True)
        filename = outdir / payload["filename"]
        with open(filename, "w", encoding="utf-8") as f:
            f.write(payload["code"])

        result[page] = {
            "filename": str(filename),
            "code": payload["code"]
        }

    return result
