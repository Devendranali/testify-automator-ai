# apis/generate_page_methods.py

from fastapi import APIRouter
from pathlib import Path
import re
import json
from services.test_generation_utils import collection, filter_all_pages
from utils.smart_ai_utils import ensure_smart_ai_module
from orchestrator.orchestrator import send_message

router = APIRouter()

def safe(s: str) -> str:
    return re.sub(r'\W+', '_', (s or '').lower()).strip('_') or 'element'

def ensure_unique(base_name: str, used: dict) -> str:
    """
    Ensures function names are unique by appending _2, _3, ... when needed.
    used: dict[name] = count (last number used)
    """
    name = base_name
    if name not in used:
        used[name] = 1
        return name
    used[name] += 1
    return f"{base_name}_{used[name]}"

# ---------- Helper block to prepend to every page file ----------
ASSERT_HELPER_BLOCK = """import re
from playwright.sync_api import expect

def _ci(s):  # case-insensitive canonical
    return (s or "").strip().lower()
"""

def _assert_method_for_input(unique: str, label_text: str, placeholder: str, method_name: str) -> str:
    """
    Emits: def assert_<method_name>(page, expected, timeout=...)
    """
    label_json = json.dumps(label_text or "")
    placeholder_json = json.dumps(placeholder or "")
    return (
        f"def assert_{method_name}(page, expected: str, timeout: int = 6000):\n"
        f"    exp = str(expected)\n"
        f"    # 1) Prefer SmartAI target\n"
        f"    try:\n"
        f"        expect(page.smartAI('{unique}')).to_have_value(exp, timeout=timeout)\n"
        f"        return\n"
        f"    except Exception:\n"
        f"        pass\n"
        f"    # 2) Fallback: label\n"
        f"    lbl = {label_json}\n"
        f"    if lbl:\n"
        f"        try:\n"
        f"            expect(page.get_by_label(lbl)).to_have_value(exp, timeout=timeout)\n"
        f"            return\n"
        f"        except Exception:\n"
        f"            pass\n"
        f"    # 3) Fallback: placeholder\n"
        f"    ph = {placeholder_json}\n"
        f"    if ph:\n"
        f"        try:\n"
        f"            expect(page.get_by_placeholder(ph)).to_have_value(exp, timeout=timeout)\n"
        f"            return\n"
        f"        except Exception:\n"
        f"            pass\n"
        f"    # 4) Last resort: first textbox on page\n"
        f"    try:\n"
        f"        expect(page.get_by_role('textbox').first).to_have_value(exp, timeout=timeout)\n"
        f"        return\n"
        f"    except Exception as e:\n"
        f"        raise AssertionError(f\"Assertion failed for '{{lbl or ph or '{unique}'}}' expecting '{{exp}}': {{e}}\")\n"
    )

def _assert_method_for_select(unique: str, label_text: str, method_name: str) -> str:
    """
    Emits: def assert_<method_name>(page, expected, timeout=...)
    Validates native <select> (value/label) and custom combobox text.
    """
    label_json = json.dumps(label_text or "")
    return (
        f"def assert_{method_name}(page, expected: str, timeout: int = 6000):\n"
        f"    exp = str(expected)\n"
        f"    # 1) Native <select>: check value and selected label\n"
        f"    try:\n"
        f"        el = page.smartAI('{unique}')\n"
        f"        try:\n"
        f"            expect(el).to_have_value(exp, timeout=timeout)\n"
        f"            return\n"
        f"        except Exception:\n"
        f"            pass\n"
        f"        try:\n"
        f"            sel_label = el.evaluate(\"el => el && el.options && el.selectedIndex>=0 ? (el.options[el.selectedIndex].label || el.options[el.selectedIndex].text || '') : ''\")\n"
        f"            if _ci(sel_label) == _ci(exp):\n"
        f"                return\n"
        f"        except Exception:\n"
        f"            pass\n"
        f"    except Exception:\n"
        f"        pass\n"
        f"    # 2) Custom combobox: trigger text by label\n"
        f"    lbl = {label_json}\n"
        f"    if lbl:\n"
        f"        try:\n"
        f"            cmb = page.get_by_role('combobox', name=re.compile(lbl, re.I))\n"
        f"            expect(cmb).to_contain_text(exp, timeout=timeout)\n"
        f"            return\n"
        f"        except Exception:\n"
        f"            pass\n"
        f"    # 3) Fallback: selected option with aria-selected=true\n"
        f"    try:\n"
        f"        opt = page.locator(\"[role='option'][aria-selected='true']\").first\n"
        f"        expect(opt).to_contain_text(exp, timeout=timeout)\n"
        f"        return\n"
        f"    except Exception as e:\n"
        f"        raise AssertionError(f\"Assertion failed for select '{{lbl or '{unique}'}}' expecting '{{exp}}': {{e}}\")\n"
    )

# -------- Build one method from a metadata entry --------
def build_method(entry, used_names):
    ocr_type    = (entry.get("ocr_type") or "").lower()
    intent      = (entry.get("intent") or "").lower()
    label_text  = (entry.get("label_text") or intent or "element").strip()
    unique      = entry.get("unique_name")
    placeholder = entry.get("placeholder") or ""

    def stem(name):
        return safe(label_text or intent or name)

    code_blocks = []

    # ---------- TEXT INPUTS ----------
    if ocr_type in ("textbox", "text", "input", "textarea", "email", "password"):
        fn = ensure_unique(f"enter_{stem('input')}", used_names)
        label_json = json.dumps(label_text)
        placeholder_json = json.dumps(placeholder)
        method_code = (
            f"def {fn}(page, value):\n"
            f"    # Prefer SmartAI locator\n"
            f"    try:\n"
            f"        loc = page.smartAI('{unique}')\n"
            f"        try: loc.focus(timeout=1000)\n"
            f"        except Exception: pass\n"
            f"        try: loc.fill(\"\")\n"
            f"        except Exception: pass\n"
            f"        page.keyboard.press('Control+A'); page.keyboard.press('Backspace')\n"
            f"        loc.type(str(value), delay=30)\n"
            f"        return\n"
            f"    except Exception:\n"
            f"        pass\n\n"
            f"    _ph = {placeholder_json}\n"
            f"    _lbl = {label_json}\n"
            f"    if _ph:\n"
            f"        try:\n"
            f"            loc = page.get_by_placeholder(_ph).first\n"
            f"            loc.click()\n"
            f"            try: loc.fill(\"\")\n"
            f"            except Exception: pass\n"
            f"            page.keyboard.press('Control+A'); page.keyboard.press('Backspace')\n"
            f"            loc.type(str(value), delay=30)\n"
            f"            return\n"
            f"        except Exception: pass\n"
            f"    if _lbl:\n"
            f"        try:\n"
            f"            loc = page.get_by_label(_lbl).first\n"
            f"            loc.click()\n"
            f"            try: loc.fill(\"\")\n"
            f"            except Exception: pass\n"
            f"            page.keyboard.press('Control+A'); page.keyboard.press('Backspace')\n"
            f"            loc.type(str(value), delay=30)\n"
            f"            return\n"
            f"        except Exception: pass\n"
            f"    try:\n"
            f"        if _lbl:\n"
            f"            loc = page.get_by_role('textbox', name=_lbl).first\n"
            f"            loc.click()\n"
            f"            try: loc.fill(\"\")\n"
            f"            except Exception: pass\n"
            f"            page.keyboard.press('Control+A'); page.keyboard.press('Backspace')\n"
            f"            loc.type(str(value), delay=30)\n"
            f"            return\n"
            f"    except Exception: pass\n"
            f"    try:\n"
            f"        loc = page.get_by_role('textbox').first\n"
            f"        loc.click()\n"
            f"        try: loc.fill(\"\")\n"
            f"        except Exception: pass\n"
            f"        page.keyboard.press('Control+A'); page.keyboard.press('Backspace')\n"
            f"        loc.type(str(value), delay=30)\n"
            f"        return\n"
            f"    except Exception as e:\n"
            f"        raise AssertionError(f\"Unable to fill input for '{{_lbl or _ph or '{unique}'}}': {{e}}\")\n"
        )
        # Emit method-specific assertion
        assert_code = _assert_method_for_input(unique, label_text, placeholder, fn)
        code_blocks += [method_code, assert_code]

    # ---------- BUTTONS ----------
    elif ocr_type in ("button", "submit", "iconbutton"):
        lbl = label_text.lower()
        is_submit_hint = any(k in lbl for k in ["submit", "save", "create", "confirm", "finish"]) or any(k in intent for k in ["submit", "save", "create", "confirm", "finish"])
        is_open_hint   = any(k in lbl for k in ["open", "add customer", "new", "add", "contact information"]) and not is_submit_hint
        if is_submit_hint:
            fn = ensure_unique(f"click_{stem('submit')}_submit", used_names)
            method_code = (
                f"def {fn}(page):\n"
                f"    page.smartAI('{unique}').click()\n"
            )
        elif is_open_hint:
            fn = ensure_unique(f"click_{stem('open')}_open", used_names)
            method_code = (
                f"def {fn}(page):\n"
                f"    page.smartAI('{unique}').click()\n"
                f"    try:\n"
                f"        page.locator(\"[role='dialog'], form\").first.wait_for(state='visible', timeout=8000)\n"
                f"    except Exception: pass\n"
            )
        else:
            fn = ensure_unique(f"click_{stem('button')}", used_names)
            method_code = (
                f"def {fn}(page):\n"
                f"    page.smartAI('{unique}').click()\n"
            )
        code_blocks.append(method_code)
        # (No per-button assertion added automatically)

    # ---------- COMBOBOX / DROPDOWN ----------
    elif ocr_type in ("select", "dropdown", "combobox"):
        fn = ensure_unique(f"select_{stem('option')}", used_names)
        method_code = (
            f"def {fn}(page, value: str):\n"
            f"    page.smartAI('{unique}').select_option(value)\n"
        )
        assert_code = _assert_method_for_select(unique, label_text, fn)
        code_blocks += [method_code, assert_code]

    # ---------- CHECKBOX / RADIO / TOGGLE ----------
    elif ocr_type == "checkbox":
        fn = ensure_unique(f"toggle_{stem('checkbox')}", used_names)
        method_code = (
            f"def {fn}(page):\n"
            f"    page.smartAI('{unique}').click()\n"
        )
        code_blocks.append(method_code)
    elif ocr_type in ("radio", "radiogroup"):
        fn = ensure_unique(f"select_{stem('radio')}_option", used_names)
        method_code = (
            f"def {fn}(page, value):\n"
            f"    page.smartAI('{unique}').click()\n"
            f"    try:\n"
            f"        page.get_by_role('radio', name=value, exact=True).check()\n"
            f"    except Exception:\n"
            f"        page.get_by_role('radio', name=value).check()\n"
        )
        code_blocks.append(method_code)
    elif ocr_type in ("toggle", "switch"):
        fn = ensure_unique(f"toggle_{stem('toggle')}", used_names)
        method_code = (
            f"def {fn}(page):\n"
            f"    page.smartAI('{unique}').click()\n"
        )
        code_blocks.append(method_code)

    # ---------- DATE/TIME ----------
    elif ocr_type in ("date", "datepicker", "time", "timepicker"):
        base = "date" if "date" in ocr_type else "time"
        fn = ensure_unique(f"pick_{stem(base)}", used_names)
        method_code = (
            f"def {fn}(page, value):\n"
            f"    page.smartAI('{unique}').fill(value)\n"
        )
        # Input-like assertion for date/time
        assert_code = _assert_method_for_input(unique, label_text, placeholder, fn)
        code_blocks += [method_code, assert_code]

    # ---------- FILE UPLOAD ----------
    elif ocr_type in ("file", "fileinput", "upload"):
        fn = ensure_unique(f"upload_{stem('file')}", used_names)
        method_code = (
            f"def {fn}(page, file_path):\n"
            f"    page.smartAI('{unique}').set_input_files(file_path)\n"
        )
        code_blocks.append(method_code)

    # ---------- DEFAULT/FALLBACK ----------
    else:
        fn = ensure_unique(f"verify_{stem('element')}_visible", used_names)
        method_code = (
            f"def {fn}(page):\n"
            f"    assert page.smartAI('{unique}').is_visible()\n"
        )
        code_blocks.append(method_code)

    return "\n".join(code_blocks)

def _ensure_assert_helper(code: str) -> str:
    if "def _ci(" not in code:
        code = ASSERT_HELPER_BLOCK + "\n" + code
    elif "from playwright.sync_api import expect" not in code:
        code = "from playwright.sync_api import expect\n" + code
    return code

@router.post("/rag/generate-page-methods")
def generate_page_methods():
    ensure_smart_ai_module()
    target_pages = filter_all_pages()
    print("apis.generate_page_methods.py | target_pages = ", target_pages)
    result = {}

    # Ensure SmartAI is auto-patched for pytest runs + force headed
    def create_conftest_file():
        conftest_content = '''import pytest
import json
from pathlib import Path
from lib.smart_ai import patch_page_with_smartai

@pytest.fixture(scope="session")
def browser_type_launch_args(browser_type_launch_args):
    # Force headed + visible speed for local debug
    return {**browser_type_launch_args, "headless": False, "slow_mo": 300}

@pytest.fixture(autouse=True)
def smartai_page(page):
    script_dir = Path(__file__).parent
    # Try after_enrichment first, then before_enrichment, else empty
    for name in ("after_enrichment.json", "before_enrichment.json"):
        p = (script_dir.parent / "metadata" / name).resolve()
        if p.exists():
            with open(p, "r") as f:
                meta = json.load(f)
            break
    else:
        meta = []
    patch_page_with_smartai(page, meta)
    return page
'''
        tests_dir = Path(__file__).parent.parent / "generated_runs" / "src" / "tests"
        tests_dir.mkdir(parents=True, exist_ok=True)
        conftest_path = tests_dir / "conftest.py"
        conftest_path.write_text(conftest_content.strip())

    create_conftest_file()

    outdir = Path("generated_runs") / "src" / "pages"
    outdir.mkdir(parents=True, exist_ok=True)

    for page in target_pages:
        page_data = collection.get(where={"page_name": page})
        entries = [r for r in page_data.get("metadatas", [])]

        response = send_message("python", "generate_page_file", {"entries": entries, "page_name": page})
        payload = response.payload   # {"filename": ..., "code": ...}

        # Inject assertion helper + keep generated code, then append our SmartAI-aware methods+asserts
        generated = payload["code"]
        generated = _ensure_assert_helper(generated)

        # Append SmartAI method implementations (built from metadata)
        used = {}
        blocks = []
        for e in entries:
            try:
                blocks.append(build_method(e, used))
            except Exception:
                continue

        page_code = generated.rstrip() + "\n\n# ==== SmartAI methods & assertions ====\n\n" + "\n\n".join(blocks) + "\n"

        filename = outdir / payload["filename"]
        with open(filename, "w", encoding="utf-8") as f:
            f.write(page_code)

        result[page] = {
            "filename": str(filename),
            "code": page_code
        }

    return result
