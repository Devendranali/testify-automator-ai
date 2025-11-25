
from fastapi import APIRouter, Query
from pathlib import Path
from typing import List, Tuple
import re
import json
from services.test_generation_utils import runtime_collection, filter_all_pages
from utils.match_utils import normalize_page_name
from utils.smart_ai_utils import ensure_smart_ai_module, get_smartai_src_dir
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


def _parse_functions(code: str) -> tuple[str, list[tuple[str, list[str]]]]:
    """
    Split module code into a header (before first def) and ordered list of (name, lines) blocks.
    Lightweight parser: assumes top-level functions start with 'def ' at column 0.
    """
    lines = code.splitlines(True)
    header: list[str] = []
    functions: list[tuple[str, list[str]]] = []

    current_name: str | None = None
    current_block: list[str] = []
    seen_def = False

    def flush():
        nonlocal current_name, current_block
        if current_name and current_block:
            functions.append((current_name, current_block))
        current_name, current_block = None, []

    for line in lines:
        if not seen_def and not line.lstrip().startswith("def "):
            header.append(line)
            continue
        if line.startswith("def "):
            seen_def = True
            flush()
            current_name = line.split("def ", 1)[1].split("(", 1)[0].strip()
            current_block = [line]
        else:
            if current_name is None:
                header.append(line)
            else:
                current_block.append(line)
    flush()
    return "".join(header), functions
 
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
    label_json = json.dumps(label_text or "")
    placeholder_json = json.dumps(placeholder or "")
    return (
        f"def assert_{method_name}(page, expected: str, timeout: int = 6000):\n"
        f"    exp = str(expected)\n"
        f"    # 1) Prefer SmartAI target\n"
        f"    try:\n"
        f"        locator = page.smartAI('{unique}')\n"
        f"        try:\n"
        f"            expect(locator).to_have_value(exp, timeout=timeout)\n"
        f"            return\n"
        f"        except Exception:\n"
        f"            actual = _safe_input_value(locator)\n"
        f"            if _values_match(actual, exp):\n"
        f"                return\n"
        f"    except Exception:\n"
        f"        pass\n"
        f"    # 2) Fallback: label\n"
        f"    lbl = {label_json}\n"
        f"    if lbl:\n"
        f"        try:\n"
        f"            locator = page.get_by_label(lbl)\n"
        f"            try:\n"
        f"                expect(locator).to_have_value(exp, timeout=timeout)\n"
        f"                return\n"
        f"            except Exception:\n"
        f"                actual = _safe_input_value(locator)\n"
        f"                if _values_match(actual, exp):\n"
        f"                    return\n"
        f"        except Exception:\n"
        f"            pass\n"
        f"    # 3) Fallback: placeholder\n"
        f"    ph = {placeholder_json}\n"
        f"    if ph:\n"
        f"        try:\n"
        f"            locator = page.get_by_placeholder(ph)\n"
        f"            try:\n"
        f"                expect(locator).to_have_value(exp, timeout=timeout)\n"
        f"                return\n"
        f"            except Exception:\n"
        f"                actual = _safe_input_value(locator)\n"
        f"                if _values_match(actual, exp):\n"
        f"                    return\n"
        f"        except Exception:\n"
        f"            pass\n"
        f"    # 4) Last resort: first textbox on page\n"
        f"    try:\n"
        f"        locator = page.get_by_role('textbox').first\n"
        f"        try:\n"
        f"            expect(locator).to_have_value(exp, timeout=timeout)\n"
        f"            return\n"
        f"        except Exception as e:\n"
        f"            actual = _safe_input_value(locator)\n"
        f"            if _values_match(actual, exp):\n"
        f"                return\n"
        f"            raise AssertionError(f\"Assertion failed for '{{lbl or ph or '{unique}'}}' expecting '{{exp}}' (actual '{{actual}}'): {{e}}\")\n"
        f"    except Exception as e:\n"
        f"        raise AssertionError(f\"Assertion failed for '{{lbl or ph or '{unique}'}}' expecting '{{exp}}': {{e}}\")\n"
    )
 
# -------- Build one method from a metadata entry --------
def build_method(entry, used_names):
    ocr_type    = (entry.get("ocr_type") or "").lower()
    intent      = (entry.get("intent") or "").lower()
    interaction = (entry.get("interaction") or "").lower()
    label_text  = (entry.get("label_text") or intent or "element").strip()
    unique      = entry.get("unique_name")
    placeholder = entry.get("placeholder") or ""
 
    def stem(name):
        return safe(label_text or intent or name)
 
    code_blocks = []
    fn_names = []
 
    # ---------- HOVER ----------
    if interaction == "hover" or ocr_type == "hover" or intent.endswith("_hover"):
        fn = ensure_unique(f"hover_{stem('element')}", used_names)
        method_code = (
            f"def {fn}(page):\n"
            f"    page.smartAI('{unique}').hover()\n"
        )
        code_blocks.append(method_code)

    # ---------- TEXT INPUTS ----------
    elif ocr_type in ("textbox", "text", "input", "textarea", "email", "password",):
        fn = ensure_unique(f"enter_{stem('input')}", used_names)
        label_json = json.dumps(label_text)
        
        placeholder_json = json.dumps(placeholder)
        method_code = (
            f"def {fn}(page, value):\n"
            f"    # First: if the popup search input is already present, type there (avoid clicking magnifier)\n"
            f"    try:\n"
            f"        try:\n"
            f"            popup_inp = page.get_by_placeholder(re.compile(r\"Look for {label_text}\", re.I)).first\n"
            f"        except Exception:\n"
            f"            popup_inp = None\n"
            f"        if not popup_inp:\n"
            f"            try:\n"
            f"                popup_inp = page.get_by_placeholder(re.compile(r\"Look for\", re.I)).first\n"
            f"            except Exception:\n"
            f"                popup_inp = None\n"
            f"        if popup_inp:\n"
            f"            try:\n"
            f"                popup_inp.wait_for(state='visible', timeout=800)\n"
            f"                try: popup_inp.fill(\"\")\n"
            f"                except Exception: pass\n"
            f"                page.keyboard.press('Control+A'); page.keyboard.press('Backspace')\n"
            f"                popup_inp.type(str(value), delay=30)\n"
            f"                page.wait_for_timeout(300)\n"
            f"                try:\n"
            f"                    sel = page.get_by_role('treeitem', name=re.compile(re.escape(str(value)), re.I)).first\n"
            f"                    sel.wait_for(state='visible', timeout=1500)\n"
            f"                    sel.click()\n"
            f"                    return\n"
            f"                except Exception:\n"
            f"                    pass\n"
            f"                try:\n"
            f"                    sel = page.get_by_role('option', name=re.compile(re.escape(str(value)), re.I)).first\n"
            f"                    sel.wait_for(state='visible', timeout=1500)\n"
            f"                    sel.click()\n"
            f"                    return\n"
            f"                except Exception:\n"
            f"                    pass\n"
            f"                try:\n"
            f"                    row = page.locator(f\"li:has-text(\\\"{{value}}\\\")\").first\n"
            f"                    row.wait_for(state='visible', timeout=1500)\n"
            f"                    row.click()\n"
            f"                    return\n"
            f"                except Exception:\n"
            f"                    pass\n"
            f"            except Exception:\n"
            f"                pass\n"
            f"    except Exception:\n"
            f"        pass\n\n"
            f"    # Prefer SmartAI locator and handle opener-style lookup controls\n"
            f"    try:\n"
            f"        loc = page.smartAI('{unique}')\n"
            f"        # detect opener controls\n"
            f"        try:\n"
            f"            tag = loc.evaluate(\"el => el && el.tagName && el.tagName.toLowerCase()\")\n"
            f"        except Exception:\n"
            f"            tag = None\n"
            f"        try:\n"
            f"            role = loc.get_attribute('role')\n"
            f"        except Exception:\n"
            f"            role = None\n"
            f"        try:\n"
            f"            ah = loc.get_attribute('aria-haspopup')\n"
            f"        except Exception:\n"
            f"            ah = None\n\n"
            f"        is_opener = tag in ('button',) or (role and role.lower() in ('button', 'combobox')) or (ah is not None)\n\n"
            f"        if is_opener:\n"
            f"            # If the SmartAI target looks like a magnifier, try nearby input first\n"
            f"            try:\n"
            f"                title = loc.get_attribute('title') or ''\n"
            f"            except Exception:\n"
            f"                title = ''\n"
            f"            try:\n"
            f"                al = loc.get_attribute('aria-label') or ''\n"
            f"            except Exception:\n"
            f"                al = ''\n"
            f"            try:\n"
            f"                is_magnifier = tag in ('button',) and re.search(r\"(search|magnif|magnify|lookup|look up|advanced|find)\", (title + ' ' + al), re.I)\n"
            f"            except Exception:\n"
            f"                is_magnifier = False\n\n"
            f"            if is_magnifier:\n"
            f"                try:\n"
            f"                    parent = loc.locator('xpath=..').first\n"
            f"                    try:\n"
            f"                        inp = parent.locator(\"input, [role='combobox'], [role='searchbox']\").first\n"
            f"                    except Exception:\n"
            f"                        inp = None\n"
            f"                    if inp:\n"
            f"                        try:\n"
            f"                            inp.wait_for(state='visible', timeout=1200)\n"
            f"                            try: inp.fill(\"\")\n"
            f"                            except Exception: pass\n"
            f"                            page.keyboard.press('Control+A'); page.keyboard.press('Backspace')\n"
            f"                            inp.type(str(value), delay=30)\n"
            f"                            page.wait_for_timeout(300)\n"
            f"                            try:\n"
            f"                                sel = page.get_by_role('treeitem', name=re.compile(re.escape(str(value)), re.I)).first\n"
            f"                                sel.wait_for(state='visible', timeout=2000)\n"
            f"                                sel.click()\n"
            f"                                return\n"
            f"                            except Exception:\n"
            f"                                pass\n"
            f"                            try:\n"
            f"                                sel = page.get_by_role('option', name=re.compile(re.escape(str(value)), re.I)).first\n"
            f"                                sel.wait_for(state='visible', timeout=2000)\n"
            f"                                sel.click()\n"
            f"                                return\n"
            f"                            except Exception:\n"
            f"                                pass\n"
            f"                            try:\n"
            f"                                row = page.locator(f\"li:has-text(\\\"{{value}}\\\")\").first\n"
            f"                                row.wait_for(state='visible', timeout=2000)\n"
            f"                                row.click()\n"
            f"                                return\n"
            f"                            except Exception:\n"
            f"                                pass\n"
            f"                        except Exception:\n"
            f"                            pass\n"
            f"                except Exception:\n"
            f"                    pass\n\n"
            f"            # open popup (not a magnifier icon)\n"
            f"            try:\n"
            f"                loc.click()\n"
            f"            except Exception:\n"
            f"                try:\n"
            f"                    loc.focus()\n"
            f"                    page.keyboard.press('Enter')\n"
            f"                except Exception:\n"
            f"                    pass\n"
            f"            page.wait_for_timeout(300)\n\n"
            f"            # If popup has a searchable textbox, try placeholders used by Dynamics first\n"
            f"            popup_inputs = []\n"
            f"            try:\n"
            f"                popup_inputs.append(page.get_by_placeholder(re.compile(r\"Look for {label_text}\", re.I)).first)\n"
            f"            except Exception:\n"
            f"                pass\n"
            f"            try:\n"
            f"                popup_inputs.append(page.get_by_placeholder(re.compile(r\"Look for\", re.I)).first)\n"
            f"            except Exception:\n"
            f"                pass\n"
            f"            try:\n"
            f"                popup_inputs.append(page.locator(\"input[type='search']\").first)\n"
            f"            except Exception:\n"
            f"                pass\n"
            f"            try:\n"
            f"                popup_inputs.append(page.get_by_placeholder('Search').first)\n"
            f"            except Exception:\n"
            f"                pass\n"
            f"            try:\n"
            f"                popup_inputs.append(page.locator(\"input[role='searchbox']\").first)\n"
            f"            except Exception:\n"
            f"                pass\n\n"
            f"            for inp in popup_inputs:\n"
            f"                try:\n"
            f"                    inp.wait_for(state='visible', timeout=1000)\n"
            f"                    try: inp.fill(\"\")\n"
            f"                    except Exception: pass\n"
            f"                    page.keyboard.press('Control+A'); page.keyboard.press('Backspace')\n"
            f"                    inp.type(str(value), delay=30)\n"
            f"                    page.wait_for_timeout(300)\n"
            f"                    # Try treeitem / option / li / button selectors\n"
            f"                    try:\n"
            f"                        tree = page.get_by_role('treeitem', name=re.compile(re.escape(str(value)), re.I)).first\n"
            f"                        tree.wait_for(state='visible', timeout=2000)\n"
            f"                        tree.click()\n"
            f"                        return\n"
            f"                    except Exception:\n"
            f"                        pass\n"
            f"                    try:\n"
            f"                        opt = page.get_by_role('option', name=re.compile(re.escape(str(value)), re.I)).first\n"
            f"                        opt.wait_for(state='visible', timeout=2000)\n"
            f"                        opt.click()\n"
            f"                        return\n"
            f"                    except Exception:\n"
            f"                        pass\n"
        f"                    try:\n"
        f"                        item = page.locator(f\"li:has-text(\\\"{{value}}\\\")\").first\n"
        f"                        item.wait_for(state='visible', timeout=2000)\n"
        f"                        item.click()\n"
        f"                        return\n"
        f"                    except Exception:\n"
        f"                        pass\n"
        f"                except Exception:\n"
        f"                    continue\n"

            f"            try:\n"
            f"                tree = page.get_by_role('treeitem', name=re.compile(re.escape(str(value)), re.I)).first\n"
            f"                tree.wait_for(state='visible', timeout=1500)\n"
            f"                tree.click()\n"
            f"                return\n"
            f"            except Exception:\n"
            f"                pass\n"
            f"            try:\n"
            f"                any_tree = page.locator(f\"[role='tree'] >> text=\\\"{{value}}\\\"\").first\n"
            f"                any_tree.wait_for(state='visible', timeout=1500)\n"
            f"                any_tree.click()\n"
            f"                return\n"
            f"            except Exception:\n"
            f"                pass\n\n"
            f"            # As a last resort, type into the opener itself\n"
            f"            try:\n"
            f"                try:\n"
            f"                    loc.type(str(value), delay=30)\n"
            f"                except Exception:\n"
            f"                    try:\n"
            f"                        loc.fill(str(value))\n"
            f"                    except Exception:\n"
            f"                        pass\n"
            f"                page.wait_for_timeout(300)\n"
            f"                # retry clicking matching items\n"
            f"                try:\n"
            f"                    tree = page.get_by_role('treeitem', name=re.compile(re.escape(str(value)), re.I)).first\n"
            f"                    tree.wait_for(state='visible', timeout=1500)\n"
            f"                    tree.click()\n"
            f"                    return\n"
            f"                except Exception:\n"
            f"                    pass\n"
            f"                try:\n"
            f"                    opt = page.get_by_role('option', name=re.compile(re.escape(str(value)), re.I)).first\n"
            f"                    opt.wait_for(state='visible', timeout=1500)\n"
            f"                    opt.click()\n"
            f"                    return\n"
            f"                except Exception:\n"
            f"                    pass\n"
            f"            except Exception:\n"
            f"                pass\n\n"
            f"            return\n\n"
            f"        # Not an opener: treat as a normal input\n"
            f"        try: loc.focus(timeout=1000)\n"
            f"        except Exception: pass\n"
            f"        try: loc.fill(\"\")\n"
            f"        except Exception: pass\n"
            f"        page.keyboard.press('Control+A'); page.keyboard.press('Backspace')\n"
            f"        loc.type(str(value), delay=30)\n"
            f"        page.wait_for_timeout(300)\n"
            f"        # try selecting option/treeitem if it appears\n"
            f"        try:\n"
            f"            tree = page.get_by_role('treeitem', name=re.compile(re.escape(str(value)), re.I)).first\n"
            f"            tree.wait_for(state='visible', timeout=1500)\n"
            f"            tree.click()\n"
            f"            return\n"
            f"        except Exception:\n"
            f"            pass\n"
            f"        try:\n"
            f"            opt = page.get_by_role('option', name=re.compile(re.escape(str(value)), re.I)).first\n"
            f"            opt.wait_for(state='visible', timeout=1500)\n"
            f"            opt.click()\n"
            f"            return\n"
            f"        except Exception:\n"
            f"            pass\n"
            f"        try:\n"
            f"            item = page.locator(f\"li:has-text(\\\"{{value}}\\\")\").first\n"
            f"            item.wait_for(state='visible', timeout=1500)\n"
            f"            item.click()\n"
            f"            return\n"
            f"        except Exception:\n"
            f"            pass\n"
            f"        return\n"
            f"    except Exception:\n"
            f"        pass\n\n"
            f"    # Fallbacks by placeholder/label/role\n"
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
        code_blocks.append(method_code)
 
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
 
@router.post("/rag/generate-page-methods")
def generate_page_methods(pages: str | None = Query(None, description="Comma-separated page names to regenerate")):
    ensure_smart_ai_module()
    collection = runtime_collection()
    if pages:
        target_pages = [
            normalize_page_name(p.strip())
            for p in pages.split(",")
            if p.strip()
        ]
        target_pages = [p for p in target_pages if p]
    else:
        target_pages = filter_all_pages()
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
import webbrowser
import shutil
import subprocess
import sys


@pytest.fixture(scope="session", autouse=True)
def _open_allure_on_finish():
    """After the whole test session finishes, try to open the generated Allure
    report (or pytest-html fallback) in the local browser automatically.

    This runs on the same machine that executes the tests, so it will open
    the report for the user running pytest.
    """
    yield
    src_root = Path(__file__).resolve().parents[2]
    results_dir = src_root / "allure-results"
    allure_report_dir = src_root / "allure-report"
    html_fallback = src_root / "report.html"

    try:
        # If allure-results exists, try to generate HTML using Allure CLI.
        if results_dir.exists():
            allure_exe = shutil.which("allure")
            if allure_exe:
                try:
                    subprocess.run([allure_exe, "generate", str(results_dir), "-o", str(allure_report_dir), "--clean"], check=True)
                except Exception:
                    # generation failed, fall through to fallback handling
                    pass

        # Prefer the generated Allure index.html, otherwise fallback to report.html
        allure_index = allure_report_dir / "index.html"
        if allure_index.exists():
            webbrowser.open(allure_index.as_uri())
        elif html_fallback.exists():
            webbrowser.open(html_fallback.as_uri())
    except Exception:
        # Opening is best-effort; don't fail the session teardown if it fails.
        pass
 
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
        tests_dir = get_smartai_src_dir() / "tests"
        tests_dir.mkdir(parents=True, exist_ok=True)
        conftest_path = tests_dir / "conftest.py"
        conftest_path.write_text(conftest_content.strip())
 
    create_conftest_file()
 
    outdir = get_smartai_src_dir() / "pages"
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
        generated = payload["code"]
        generated = _ensure_assert_helper(generated)
 
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
 
        page_code = generated.rstrip() + "\n\n# ==== SmartAI methods & assertions ====\n\n" + "\n\n".join(blocks) + "\n"

        # Inject an Allure shim and auto-wrap for common action/assertion helpers
        # so that calls like `enter_full_name` appear as steps in the Allure UI.
        WRAPPER_BLOCK = '''
# ---- Allure step wrapper (added automatically) ----
try:
    import allure
except Exception:
    from contextlib import nullcontext
    class _AllureShim:
        def step(self, name):
            return nullcontext()
    allure = _AllureShim()

try:
    _step_prefixes = ('enter_', 'click_', 'select_')
    for _name, _obj in list(globals().items()):
        if callable(_obj) and any(_name.startswith(p) for p in _step_prefixes):
            def _make_wrapped(f, display_name=_name):
                def _wrapped(*a, **kw):
                    try:
                        dyn = getattr(allure, 'dynamic', None)
                        param_fn = None
                        if dyn and hasattr(dyn, 'parameter'):
                            param_fn = dyn.parameter
                        elif hasattr(allure, 'parameter'):
                            param_fn = allure.parameter
                        if param_fn:
                            start_idx = 1 if len(a) and getattr(a[0], '__class__', None) and getattr(a[0].__class__, '__name__', '').lower().find('page') != -1 else 0
                            for i, val in enumerate(a[start_idx:], start=1):
                                try:
                                    param_fn(f"{display_name}_arg{i}", str(val))
                                except Exception:
                                    pass
                            for k, v in kw.items():
                                try:
                                    param_fn(str(k), str(v))
                                except Exception:
                                    pass
                    except Exception:
                        pass
                    with allure.step(display_name):
                        return f(*a, **kw)
                return _wrapped
            globals()[_name] = _make_wrapped(_obj)
except Exception:
    pass
# ---- end wrapper ----
'''

        if 'Allure step wrapper' not in page_code:
            page_code = page_code + "\n" + WRAPPER_BLOCK

        filename = outdir / payload["filename"]

        # Merge with existing file: new definitions override by name; untouched funcs preserved.
        existing_header, existing_funcs = ("", [])
        if filename.exists():
            try:
                existing_header, existing_funcs = _parse_functions(filename.read_text(encoding="utf-8"))
            except Exception:
                existing_header, existing_funcs = ("", [])

        new_header, new_funcs = _parse_functions(page_code)

        existing_map = {name: block for name, block in existing_funcs}
        new_map = {name: block for name, block in new_funcs}

        merged_blocks: list[list[str]] = []

        # Preserve existing order, override with new implementations when present.
        # Drop functions that are not regenerated (stale definitions) to avoid duplicates.
        for name, block in existing_funcs:
            if name in new_map:
                merged_blocks.append(new_map[name])
            # else: skip stale functions

        # Append any brand-new functions in the order they appeared in the new code.
        for name, block in new_funcs:
            if name not in existing_map:
                merged_blocks.append(block)

        merged_header = new_header or existing_header
        final_code = merged_header + "".join("".join(block) for block in merged_blocks)

        with open(filename, "w", encoding="utf-8") as f:
            f.write(final_code)
 
        result[page] = {
            "filename": str(filename),
            "code": page_code
        }
 
    return result


