# # apis/generate_page_methods.py


import os
import re
import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from services.test_generation_utils import runtime_collection, filter_all_pages
from utils.match_utils import normalize_page_name
from utils.smart_ai_utils import ensure_smart_ai_module, get_smartai_src_dir
from orchestrator.orchestrator import send_message
from database.project_storage import DatabaseBackedProjectStorage
from database.session import get_db
from database.models import Project

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
 
def _digits_only(s):
    return re.sub(r"\\D+", "", (s or ""))
 
def _values_match(actual, expected):
    a = "" if actual is None else str(actual)
    e = "" if expected is None else str(expected)
    if _ci(a) == _ci(e):
        return True
    da = _digits_only(a)
    de = _digits_only(e)
    return bool(da and de and da == de)
 
def _safe_input_value(locator):
    if locator is None:
        return None
    getters = (
        lambda: locator.input_value(),
        lambda: locator.evaluate("el => el ? (el.value || el.innerText || el.textContent) : null"),
        lambda: locator.inner_text(),
    )
    for getter in getters:
        try:
            value = getter()
            if value is not None:
                return value
        except Exception:
            continue
    return None
"""
 
def _assert_method_for_input(unique: str, label_text: str, placeholder: str, method_name: str) -> str:
    """
    Emits: def assert_<method_name>(page, expected, timeout=...)
    """
    field_name = label_text or placeholder or unique or "field"
    return (
        f"def assert_{method_name}(page, expected: str, timeout: int = 6000):\n"
        f"    exp = str(expected)\n"
        f"    locator = page.smartAI('{unique}')\n"
        f"    try:\n"
        f"        expect(locator).to_have_value(exp, timeout=timeout)\n"
        f"    except Exception as exc:\n"
        f"        actual = _safe_input_value(locator)\n"
        f"        raise AssertionError(f\"[ASSERT] Expected '{{exp}}' for '{field_name}' (actual '{{actual}}')\") from exc\n"
    )

def _assert_method_for_select(unique: str, label_text: str, method_name: str) -> str:
    """
    Emits: def assert_<method_name>(page, expected, timeout=...)
    """
    field_name = label_text or unique or "select"
    return (
        f"def assert_{method_name}(page, expected: str, timeout: int = 6000):\n"
        f"    exp = str(expected)\n"
        f"    locator = page.smartAI('{unique}')\n"
        f"    try:\n"
        f"        expect(locator).to_have_value(exp, timeout=timeout)\n"
        f"    except Exception as exc:\n"
        f"        try:\n"
        f"            actual_text = locator.inner_text()\n"
        f"        except Exception:\n"
        f"            actual_text = _safe_input_value(locator)\n"
        f"        raise AssertionError(f\"[ASSERT] Expected option '{{exp}}' for '{field_name}' (actual '{{actual_text}}')\") from exc\n"
    )

def build_method(entry, used_names):
    ocr_type    = (entry.get("ocr_type") or "").lower()
    intent      = (entry.get("intent") or "").lower()
    label_text  = (entry.get("label_text") or intent or "element").strip()
    unique      = entry.get("unique_name")
    placeholder = entry.get("placeholder") or ""
 
    def stem(name):
        return safe(label_text or intent or name)
 
    code_blocks = []
    fn_names = []
 
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
        fn_names += [fn, f"assert_{fn}"]
 
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
 
    return "\n".join(code_blocks), fn_names
 
def _ensure_assert_helper(code: str) -> str:
    if "def _ci(" not in code:
        code = ASSERT_HELPER_BLOCK + "\n" + code
    elif "from playwright.sync_api import expect" not in code:
        code = "from playwright.sync_api import expect\n" + code
    return code


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
        detail="Active project not found in database. Activate a project before generating methods.",
    )


def _persist_project_file(path: Path, content: str, storage: DatabaseBackedProjectStorage, encoding: str = "utf-8") -> None:
    try:
        relative = path.relative_to(storage.base_dir)
    except ValueError:
        return
    storage.write_file(relative.as_posix(), content, encoding)
 
@router.post("/rag/generate-page-methods")
def generate_page_methods(db: Session = Depends(get_db)):
    project = _get_active_project(db)
    src_dir = Path(get_smartai_src_dir())
    storage = DatabaseBackedProjectStorage(project, src_dir, db)
    ensure_smart_ai_module(storage)
    target_pages = filter_all_pages()
    collection = runtime_collection()
    print("apis.generate_page_methods.py | target_pages = ", target_pages)
    result = {}

    # Build a lookup of page metadata keyed by multiple normalized variants so
    # we don't miss pages whose stored page_name differs by case/formatting.
    records = collection.get()
    page_entries = {}
    for meta in records.get("metadatas", []):
        original = (meta.get("page_name") or "").strip()
        keys = {normalize_page_name(original)}
        if original:
            keys.add(original)
            keys.add(original.lower())
        keys.discard("")
        for key in keys:
            page_entries.setdefault(key, []).append(meta)
 
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
        tests_dir = src_dir / "tests"
        tests_dir.mkdir(parents=True, exist_ok=True)
        conftest_path = tests_dir / "conftest.py"
        conftest_text = conftest_content.strip()
        conftest_path.write_text(conftest_text)
        _persist_project_file(conftest_path, conftest_text, storage)

    create_conftest_file()

    outdir = src_dir / "pages"
    outdir.mkdir(parents=True, exist_ok=True)
 
    for page in target_pages:
        entries = list(page_entries.get(page, []))
        if not entries:
            # Fallback to exact lookups for edge cases and keep existing behaviour.
            page_data = collection.get(where={"page_name": page})
            entries = [r for r in page_data.get("metadatas", [])]
 
        response = send_message("python", "generate_page_file", {"entries": entries, "page_name": page})
        payload = response.payload   # {"filename": ..., "code": ...}
 
        # Inject assertion helper + keep generated code, then append our SmartAI-aware methods+asserts
        generated_base = payload["code"]
        generated_base = _ensure_assert_helper(generated_base)
 
        # Append SmartAI method implementations (built from metadata)
        used = {}
        blocks = []
        created = set()  # track function names already added for this page
        for e in entries:
            try:
                code, names = build_method(e, used)
                # skip if any of the function names were already created
                if any(n in created for n in names):
                    # avoid duplicate definitions; skip or only include new parts
                    new_names = [n for n in names if n not in created]
                    if not new_names:
                        continue
                    # If some names are new, include full code block but filter created set
                blocks.append(code)
                for n in names:
                    created.add(n)
            except Exception:
                continue
 
        existing_prefix = ""
        marker = "# ==== SmartAI methods & assertions ===="
        filename = outdir / payload["filename"]
        if filename.exists():
            existing_text = filename.read_text(encoding="utf-8")
            marker_index = existing_text.find(marker)
            if marker_index != -1:
                existing_prefix = existing_text[:marker_index].rstrip()
            else:
                existing_prefix = existing_text.rstrip()
            existing_prefix = _ensure_assert_helper(existing_prefix or "")
        else:
            existing_prefix = generated_base.rstrip()

        smartai_section = "\n\n".join(blocks)
        page_code = f"{existing_prefix}\n\n{marker}\n\n{smartai_section}\n"
 
        with open(filename, "w", encoding="utf-8") as f:
            f.write(page_code)
        _persist_project_file(filename, page_code, storage)
 
        result[page] = {
            "filename": str(filename),
            "code": page_code
        }
 
    return result 
