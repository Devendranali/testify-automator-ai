from fastapi import APIRouter, HTTPException, Form, Body, UploadFile, File
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Set
import re
import json
import textwrap
import pandas as pd

# Optional: Chroma metadata snapshot (skip if chromadb not installed)
try:
    from chromadb import PersistentClient
    _CHROMA_ENABLED = True
except Exception:
    _CHROMA_ENABLED = False

router = APIRouter(prefix="/rag", tags=["user-story"])
__all__ = ["router"]

# =============================================================================
# Paths
# =============================================================================
RUN_DIR   = Path("generated_runs") / "src"
TESTS_DIR = RUN_DIR / "tests"
PAGES_DIR = RUN_DIR / "pages"
LOGS_DIR  = RUN_DIR / "logs"
META_DIR  = RUN_DIR / "metadata"

# =============================================================================
# FS helpers
# =============================================================================
def _ensure_dirs():
    for d in (RUN_DIR, TESTS_DIR, PAGES_DIR, LOGS_DIR, META_DIR):
        d.mkdir(parents=True, exist_ok=True)
        # keep importable
        if d.name in {"src", "tests", "pages", "logs", "metadata"}:
            (d / "__init__.py").touch()

def _next_index() -> int:
    files = list(TESTS_DIR.glob("test_*.py"))
    nums = [int(m.group(1)) for f in files if (m := re.match(r"test_(\d+)\.py", f.name))]
    return max(nums, default=0) + 1

# =============================================================================
# Optional metadata snapshot
# =============================================================================
def _snapshot_chroma_before():
    if not _CHROMA_ENABLED:
        return
    try:
        chroma_client = PersistentClient(path="./data/chroma_db")
        collection = chroma_client.get_or_create_collection(name="element_metadata")
        all_chroma_data = collection.get()
        all_chroma_metadatas = all_chroma_data.get("metadatas", [])
        before_file = META_DIR / "before_enrichment.json"
        with open(before_file, "w", encoding="utf-8") as f:
            json.dump(all_chroma_metadatas, f, indent=2)
    except Exception:
        # Fail-soft: don't block generation if Chroma isn't ready
        pass

# =============================================================================
# Parsing: Gherkin-ish stories
# =============================================================================
URL_RE = re.compile(r'(https?://[^\s"\'\)]+)', re.I)

PATTERNS = {
    # Navigation
    "goto_named": re.compile(
        r'\b(?:given\s+i\s+open\s+the\s+browser\s+and\s+navigate\s+to|go\s+to|navigate\s+to|open)\s+"(https?://[^"]+)"',
        re.I
    ),
    "goto_am_on": re.compile(
        r'\bgiven\s+i\s+am\s+on\b.*?\bon\s+(https?://[^\s"\'\)]+)',
        re.I
    ),

    # Clicks (specific before generic)
    "click_link":   re.compile(r'\b(?:and|when|then)?\s*i\s+click(?:\s+on)?\s+the\s+"([^"]+)"\s+link\b', re.I),
    "click_button": re.compile(r'\b(?:and|when|then)?\s*i\s+click(?:\s+on)?\s+the\s+"([^"]+)"\s+button\b', re.I),
    # Tabs / menu items / generic text clicks (NOT followed by button/link word)
    "click_plain":  re.compile(r'\b(?:and|when|then)?\s*i\s+click(?:\s+on)?\s+the\s+"([^"]+)"\s*(?!\s*(?:button|link)\b)', re.I),

    # Enter (quoted and unquoted labels)
    "enter_field_q":  re.compile(r'\b(?:and|when)?\s*i\s+enter\s+"([^"]+)"\s+in\s+the\s+"([^"]+)"\s+field\b', re.I),
    "enter_field_nq": re.compile(r'\b(?:and|when)?\s*i\s+enter\s+"([^"]+)"\s+in\s+the\s+([A-Za-z0-9 _\-]+)\s+field\b', re.I),

    # Select (quoted and unquoted labels; optional "the"/"field")
    "select_q":  re.compile(r'\b(?:and|when)?\s*i\s+select\s+"([^"]+)"\s+for\s+"([^"]+)"(?:\s+field)?\b', re.I),
    "select_nq": re.compile(r'\b(?:and|when)?\s*i\s+select\s+"([^"]+)"\s+for\s+(?:the\s+)?([A-Za-z0-9 _\-]+)(?:\s+field)?\b', re.I),

    # Assertions (ignored for generation)
    "see_message":  re.compile(r'\b(?:then|and)\s+i\s+should\s+see\s+a\s+message\s+"([^"]+)"\b', re.I),
    "see_text":     re.compile(r'\b(?:then|and)\s+i\s+should\s+see\s+"([^"]+)"\b', re.I),
    "on_page":      re.compile(r'\b(?:then|and)\s+i\s+should\s+be\s+on\s+the\s+"([^"]+)"\s+page\b', re.I),
}

def _extract_all_urls(text: str) -> List[str]:
    return [m.group(1).rstrip(".,);") for m in URL_RE.finditer(text or "")]

def _slug(s: str) -> str:
    s = (s or "").strip().lower()
    s = re.sub(r'[^a-z0-9]+', '_', s)
    return s.strip('_') or "x"

def _split_into_stories(text: str) -> List[str]:
    if not text or not text.strip():
        return []
    # Prefer "1) ... 2) ..." sections
    numbered = re.split(r'(?m)^\s*\d+\)\s*', text.strip())
    numbered = [s.strip() for s in numbered if s.strip()]
    if len(numbered) > 1:
        return numbered
    # Fallback: blank-line separated blocks
    blocks = re.split(r'\n\s*\n+', text.strip())
    blocks = [b.strip() for b in blocks if b.strip()]
    return blocks or [text.strip()]

def _parse_story_block(story: str) -> Tuple[str, List[Dict[str, str]]]:
    steps: List[Dict[str, str]] = []
    base_url = ""

    # URL
    m = PATTERNS["goto_named"].search(story) or PATTERNS["goto_am_on"].search(story)
    if m:
        base_url = m.group(1).rstrip('.,);')
        steps.append({"type": "goto", "url": base_url})
    else:
        urls = _extract_all_urls(story)
        if urls:
            base_url = urls[0]
            steps.append({"type": "goto", "url": base_url})

    # Actions (in order)
    for raw in story.splitlines():
        line = raw.strip()
        if not line:
            continue

        # clicks
        m = PATTERNS["click_button"].search(line)
        if m:
            steps.append({"type": "click_button", "name": m.group(1)})
            continue
        m = PATTERNS["click_link"].search(line)
        if m:
            steps.append({"type": "click_link", "name": m.group(1)})
            continue
        m = PATTERNS["click_plain"].search(line)
        if m:
            steps.append({"type": "click_plain", "name": m.group(1)})
            continue

        # enter
        m = PATTERNS["enter_field_q"].search(line) or PATTERNS["enter_field_nq"].search(line)
        if m:
            steps.append({"type": "enter_field", "value": m.group(1), "label": m.group(2)})
            continue

        # select
        m = PATTERNS["select_q"].search(line) or PATTERNS["select_nq"].search(line)
        if m:
            steps.append({"type": "select_field", "value": m.group(1), "label": m.group(2)})
            continue

        # ignore assertions
        if PATTERNS["see_message"].search(line): continue
        if PATTERNS["see_text"].search(line):    continue
        if PATTERNS["on_page"].search(line):     continue

    if not base_url:
        raise HTTPException(400, "No URL in story. Add a nav step or include a URL.")

    return base_url, _dedupe_steps(steps)

def _dedupe_steps(steps: List[Dict[str, str]]) -> List[Dict[str, str]]:
    out, last_sig = [], None
    for st in steps:
        if st["type"] in ("click_button", "click_link", "click_plain"):
            sig = (st["type"], st.get("name", ""))
        elif st["type"] in ("enter_field", "select_field"):
            sig = (st["type"], st.get("label", ""), st.get("value", ""))
        elif st["type"] == "goto":
            sig = (st["type"], st.get("url", ""))
        else:
            sig = (st["type"], tuple(sorted(st.items())))
        if sig == last_sig:
            continue
        out.append(st); last_sig = sig
    return out

# =============================================================================
# POM method naming
# =============================================================================
def _method_click(name: str) -> str:
    return f"click_{_slug(name)}"

def _method_enter(label: str) -> str:
    return f"enter_{_slug(label)}"

def _method_select(label: str) -> str:
    return f"select_{_slug(label)}"

def _suite_name(steps: List[Dict[str, str]], url: str) -> str:
    last = None
    for st in steps:
        if st["type"] in ("click_link", "click_button", "click_plain"):
            last = st["name"]
    if last:
        return _slug(last)
    return _slug(url.split("//", 1)[-1].split("/", 1)[0])

# =============================================================================
# Emitters
# =============================================================================
def _emit_positive(steps: List[Dict[str, str]]) -> List[str]:
    out: List[str] = []
    for st in steps:
        t = st["type"]
        if t == "goto":
            out.append(f'    page.goto("{st["url"]}")')
        elif t in ("click_button", "click_link", "click_plain"):
            out.append(f"    {_method_click(st['name'])}(page)")
        elif t == "enter_field":
            out.append(f'    {_method_enter(st["label"])}(page, "{st["value"]}")')
        elif t == "select_field":
            out.append(f'    {_method_select(st["label"])}(page, "{st["value"]}")')
    return out

def _emit_negative(steps: List[Dict[str, str]]) -> List[str]:
    out: List[str] = []
    for st in steps:
        t = st["type"]
        if t == "goto":
            out.append(f'    page.goto("{st["url"]}")')
        elif t in ("click_button", "click_link", "click_plain"):
            out.append(f"    {_method_click(st['name'])}(page)")
        elif t == "enter_field":
            bad = st["value"]
            if "@" in bad:
                bad = bad.replace("@", "")
            elif bad.isdigit():
                # bad = "abc"
                bad = st["value"]
            out.append(f'    {_method_enter(st["label"])}(page, "{bad}")')
        elif t == "select_field":
            out.append(f'    {_method_select(st["label"])}(page, "{st["value"]}")')
    return out

def _emit_edge(steps: List[Dict[str, str]]) -> List[str]:
    out: List[str] = []
    for st in steps:
        t = st["type"]
        if t == "goto":
            out.append(f'    page.goto("{st["url"]}")')
        elif t in ("click_button", "click_link", "click_plain"):
            out.append(f"    {_method_click(st['name'])}(page)")
        elif t == "enter_field":
            out.append(f'    {_method_enter(st["label"])}(page, "")')
        elif t == "select_field":
            out.append(f'    {_method_select(st["label"])}(page, "{st["value"]}")')
    return out

def _emit_tests_for_story(story_text: str) -> str:
    url, steps = _parse_story_block(story_text)
    name = _suite_name(steps, url) or "story"

    lines: List[str] = []
    lines.append(f"def test_positive_{name}(page):")
    lines.extend(_emit_positive(steps))
    lines.append("")
    lines.append(f"def test_negative_{name}(page):")
    lines.extend(_emit_negative(steps))
    lines.append("")
    lines.append(f"def test_edge_{name}(page):")
    lines.extend(_emit_edge(steps))
    lines.append("")
    return "\n".join(lines)

def _emit_tests_for_stories(stories: List[str]) -> str:
    uniq, seen = [], set()
    for s in stories:
        key = re.sub(r"\s+", " ", s.strip().lower())
        if key not in seen:
            seen.add(key); uniq.append(s)
    return "\n".join(_emit_tests_for_story(s) for s in uniq)

# =============================================================================
# UI script (SmartAI format) with robust select helper and env-based holds
# =============================================================================
_UI_HEADER = """# Auto-generated UI runner

import sys, os, json, re, time
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

# Ensure <repo>/generated_runs/src is importable when running this file directly
_THIS_FILE = Path(__file__).resolve()
_SRC_ROOT  = _THIS_FILE.parents[1]      # .../generated_runs/src
if str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))

# Also add the project root (the one that contains 'services') to sys.path
try:
    for p in _THIS_FILE.parents:
        if (p / "services").is_dir():
            _REPO_ROOT = p
            if str(_REPO_ROOT) not in sys.path:
                sys.path.insert(0, str(_REPO_ROOT))
            break
except Exception:
    pass

# Optional SmartAI (shim exists at lib/smart_ai.py)
from lib.smart_ai import patch_page_with_smartai
"""

# String literal: put plain comments inside to avoid escaping docstrings.
_UI_HELPERS = """
# ----------------------------
# Robust dropdown helpers
# ----------------------------
def _debug_dump_accessibility(page_or_frame, context="page", label_text=None):
    try:
        snap = page_or_frame.accessibility.snapshot()
        print(f"[UI-RUNNER][AX] Snapshot for {context} (label={label_text!r}):")
        def walk(node, depth=0):
            role = node.get("role")
            name = node.get("name")
            if role or name:
                print("  " * depth + f"- role={role!r} name={name!r}")
            for ch in node.get("children", []) or []:
                walk(ch, depth+1)
        walk(snap)
    except Exception as e:
        print(f"[UI-RUNNER][AX] snapshot failed for {context}: {e!r}")

def _select_dropdown_in_context(ctx, label_text: str, value: str) -> bool:
    # Supports native <select>, ARIA combobox/listbox, button[aria-haspopup], autocomplete textbox, and plain text menus.
    import re
    label_rx    = re.compile(label_text, re.I)
    value_exact = re.compile(rf"^{re.escape(value)}$", re.I)
    value_fuzzy = re.compile(value, re.I)

    if os.getenv("UI_RUNNER_DEBUG") == "1":
        try:
            ctx_url = None
            try:
                ctx_url = ctx.url
                if callable(ctx_url):
                    ctx_url = ctx_url()
            except Exception:
                ctx_url = "frame"
            _debug_dump_accessibility(ctx, context=str(ctx_url), label_text=label_text)
        except Exception:
            pass

    # 1) Native <select> by associated label
    try:
        sel = ctx.get_by_label(label_rx)
        try:
            sel.select_option(value=value); return True
        except Exception:
            pass
        try:
            sel.select_option(label=value); return True
        except Exception:
            pass
    except Exception:
        pass

    # 2) Nearby <select> relative to label
    try:
        near_select = ctx.locator(
            f"label:has-text('{label_text}') ~ select, "
            f"*:has(> label:has-text('{label_text}')) select"
        ).first
        if near_select.count() > 0:
            try:
                near_select.select_option(value=value); return True
            except Exception:
                pass
            try:
                near_select.select_option(label=value); return True
            except Exception:
                pass
    except Exception:
        pass

    # 3) ARIA combobox/listbox
    try:
        trigger = ctx.get_by_role("combobox", name=label_rx).first
        if trigger and trigger.count() > 0:
            trigger.click()
            try:
                ctx.get_by_role("option", name=value_exact).first.click(timeout=2000); return True
            except Exception:
                pass
            try:
                ctx.get_by_role("option", name=value_fuzzy).first.click(timeout=2000); return True
            except Exception:
                pass
            try:
                lb = ctx.get_by_role("listbox").first
                lb.get_by_role("option", name=value_fuzzy).first.click(timeout=2000); return True
            except Exception:
                pass
    except Exception:
        pass

    # 4) Button trigger (common in UI kits)
    try:
        btn = ctx.get_by_role("button", name=label_rx).first
        if btn and btn.count() > 0:
            btn.click()
            for role in ("option", "menuitem"):
                try:
                    ctx.get_by_role(role, name=value_exact).first.click(timeout=2000); return True
                except Exception:
                    pass
                try:
                    ctx.get_by_role(role, name=value_fuzzy).first.click(timeout=2000); return True
                except Exception:
                    pass
            try:
                ctx.get_by_text(value_exact).first.click(timeout=2000); return True
            except Exception:
                pass
            try:
                ctx.get_by_text(value_fuzzy).first.click(timeout=2000); return True
            except Exception:
                pass
    except Exception:
        pass

    # 5) Autocomplete textbox (aria-autocomplete)
    try:
        tb = ctx.get_by_label(label_rx).or_(ctx.get_by_role("textbox", name=label_rx)).first
        if tb.count() == 0:
            tb = ctx.locator(
                f"label:has-text('{label_text}') ~ * [role='textbox'], "
                f"*:has(> label:has-text('{label_text}')) [role='textbox']"
            ).first
        if tb.count() > 0:
            tb.click()
            tb.fill("")
            tb.type(value)
            try:
                ctx.get_by_role("option", name=value_fuzzy).first.click(timeout=1200); return True
            except Exception:
                pass
            try:
                tb.press("Enter"); return True
            except Exception:
                pass
    except Exception:
        pass

    # 6) Generic visible-text fallback
    try:
        ctx.get_by_text(label_rx).first.click()
        for role in ("option", "menuitem"):
            try:
                ctx.get_by_role(role, name=value_fuzzy).first.click(timeout=1500); return True
            except Exception:
                pass
        ctx.get_by_text(value_fuzzy).first.click(timeout=1500); return True
    except Exception:
        pass

    return False

def _select_dropdown(page, label_text: str, value: str) -> bool:
    # Try in page first
    try:
        if _select_dropdown_in_context(page, label_text, value):
            return True
    except Exception as e:
        print(f"[UI-RUNNER] select in page failed: {e!r}")

    # Try all frames
    try:
        for fr in page.frames:
            if fr is page.main_frame:
                continue
            if _select_dropdown_in_context(fr, label_text, value):
                return True
    except Exception as e:
        print(f"[UI-RUNNER] select in frames failed: {e!r}")

    # Optional debug screenshot (FIXED: avoid backslash in f-string expression)
    if os.getenv("UI_RUNNER_DEBUG") == "1":
        try:
            out = Path(os.getenv("UI_RUNNER_DEBUG_DIR", str(_SRC_ROOT / "logs")))
            out.mkdir(parents=True, exist_ok=True)
            safe_label = re.sub(r"\\W+", "_", label_text)
            timestamp = int(time.time())
            shot = out / f"dropdown_fail_{safe_label}_{timestamp}.png"
            page.screenshot(path=str(shot), full_page=True)
            print(f"[UI-RUNNER] Saved debug screenshot to {shot}")
        except Exception as e:
            print(f"[UI-RUNNER] screenshot failed: {e!r}")

    print(f"[UI-RUNNER] Could not select '{value}' for '{label_text}' using any strategy.")
    return False

def _maybe_select_account_type(page, value: str):
    # Try generated methods if present, else fallback + common label variants.
    g = globals()
    for fn_name in ("select_account_type", "select_select_account_type"):
        fn = g.get(fn_name)
        if callable(fn):
            return fn(page, value)
    if _select_dropdown(page, "Account Type", value): return
    if _select_dropdown(page, "Account", value): return
    if _select_dropdown(page, "Type", value): return

def _call_or_fallback(fn_name: str, page, *args):
    # Prefer generated page methods; else robust fallbacks.
    import re
    g = globals()
    fn = g.get(fn_name)
    if callable(fn):
        return fn(page, *args)

    try:
        if fn_name.startswith("click_"):
            label = fn_name[len("click_"):].replace("_", " ").strip()
            try:
                page.get_by_role("button", name=re.compile(label, re.I)).first.click(); return
            except Exception:
                pass
            try:
                page.get_by_role("link", name=re.compile(label, re.I)).first.click(); return
            except Exception:
                pass
            page.get_by_text(re.compile(label, re.I)).first.click(); return

        if fn_name.startswith("enter_"):
            label = fn_name[len("enter_"):].replace("_", " ").strip()
            value = args[0] if args else ""
            try:
                page.get_by_label(re.compile(label, re.I)).fill(value); return
            except Exception:
                pass
            try:
                page.get_by_placeholder(re.compile(label, re.I)).fill(value); return
            except Exception:
                pass
            page.get_by_role("textbox").first.fill(value); return

        if fn_name.startswith("select_"):
            label = fn_name[len("select_"):].replace("_", " ").strip()
            value = args[0] if args else ""
            if _select_dropdown(page, label, value): return
            for alt in (f"{label} Type", f"{label} Name", f"{label} Category", f"Select {label}"):
                if _select_dropdown(page, alt, value): return
            plain = re.sub(r"[\\*:\\-]+", " ", label).strip()
            if plain != label and _select_dropdown(page, plain, value): return
            return
    except Exception as e:
        print(f"[UI-RUNNER] Fallback failed for {fn_name}: {e!r}")
"""

def _generate_ui_script_for_test_file(test_path: Path):
    # 1) gather page imports (any .py under pages/, except __init__.py)
    page_imports = []
    for py in sorted(PAGES_DIR.glob("*.py")):
        if py.name == "__init__.py":
            continue
        module_name = py.stem
        page_imports.append(f"from pages.{module_name} import *")

    # 2) read the test file
    with test_path.open("r", encoding="utf-8") as f:
        test_src = f.read()

    # 3) extract test functions and their bodies
    funcs = []
    lines = test_src.splitlines(True)
    cur_name, cur_body, in_func = None, [], False
    for line in lines:
        m = re.match(r"def (test_[a-zA-Z0-9_]+)\(page\):", line)
        if m:
            if cur_name and cur_body:
                funcs.append((cur_name, "".join(cur_body)))
            cur_name = m.group(1)
            cur_body = []
            in_func = True
            continue
        if in_func:
            if re.match(r"def [a-zA-Z_]", line) or (line and not line.startswith("    ")):
                in_func = False
                continue
            cur_body.append(line)
    if cur_name and cur_body:
        funcs.append((cur_name, "".join(cur_body)))

    # 4) header
    header = _UI_HEADER + "\n".join(page_imports) + "\n" + _UI_HELPERS

    # 5) wrap each test_* into run_* with helpers and substitutions
    wrapper_blocks = []
    for fname, fbody in funcs:
        runner = "run_" + fname.replace("test_", "")
        dedented = textwrap.dedent(fbody).strip("\n")

        # Map special select-account-type to the robust helper
        dedented = re.sub(
            r'\bselect_(?:select_)?account_type\(\s*page\s*,\s*(".*?"|\'.*?\')\s*\)',
            r'_maybe_select_account_type(page, \1)',
            dedented
        )
        # Replace clicks/enters/selects with resilient dispatcher
        dedented = re.sub(
            r'\b(click_[a-z0-9_]+)\(\s*page\s*\)',
            r'_call_or_fallback("\1", page)',
            dedented,
            flags=re.I
        )
        dedented = re.sub(
            r'\b(enter_[a-z0-9_]+)\(\s*page\s*,\s*(".*?"|\'.*?\')\s*\)',
            r'_call_or_fallback("\1", page, \2)',
            dedented,
            flags=re.I
        )
        dedented = re.sub(
            r'\b(select_[a-z0-9_]+)\(\s*page\s*,\s*(".*?"|\'.*?\')\s*\)',
            r'_call_or_fallback("\1", page, \2)',
            dedented,
            flags=re.I
        )

        step_lines = [("        " + l) if l.strip() else "" for l in dedented.splitlines()]
        steps = "\n".join(step_lines)

        block = f"""def {runner}():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=int(os.getenv("UI_RUNNER_SLOWMO", "300")))
        context = browser.new_context()
        page = context.new_page()

        # Attach SmartAI if present
        metadata_path = _SRC_ROOT / "metadata" / "after_enrichment.json"
        if metadata_path.exists():
            try:
                patch_page_with_smartai(page, json.loads(metadata_path.read_text(encoding="utf-8")))
            except Exception as e:
                print(f"[UI-RUNNER] SmartAI patch skipped: {{e!r}}")

        page.set_default_timeout(15000)
        page.set_default_navigation_timeout(30000)

{steps}

        hold_secs = int(os.getenv("UI_RUNNER_HOLD", "20"))
        print(f"[UI-RUNNER] Holding browser open for {{hold_secs}}s (set UI_RUNNER_HOLD env to change)...")
        time.sleep(hold_secs)
        if os.getenv("UI_RUNNER_PAUSE") == "1":
            input("\\n[UI-RUNNER] Press Enter to close the browser...")
        if os.getenv("UI_RUNNER_AUTOCLOSE") == "1":
            context.close()
            browser.close()

"""
        wrapper_blocks.append(block)

    main_block = "\nif __name__ == '__main__':\n"
    for fname, _ in funcs:
        main_block += f"    run_{fname.replace('test_', '')}()\n"

    m = re.match(r"test_(\d+)\.py$", test_path.name)
    ui_name = f"ui_script_{m.group(1)}.py" if m else "ui_script.py"
    ui_path = TESTS_DIR / ui_name
    ui_path.write_text(header + "\n".join(wrapper_blocks) + main_block, encoding="utf-8")
    return str(ui_path)

# =============================================================================
# Page method discovery (optional; used for header imports in tests)
# =============================================================================
def get_all_page_methods(pages_dir: Path) -> Dict[str, List[str]]:
    page_method_map: Dict[str, List[str]] = {}
    for py_file in pages_dir.glob("*.py"):
        if py_file.name == "__init__.py":
            continue
        page_name = py_file.stem
        method_names = []
        with open(py_file, "r", encoding="utf-8") as f:
            for line in f:
                if re.match(r"def\s+[a-zA-Z_]\w*\s*\([^\)]*\):", line):
                    method_names.append(line.strip())
        page_method_map[page_name] = method_names
    return page_method_map

# =============================================================================
# Collect called methods & generate stubs (with robust select fallback)
# =============================================================================
CALL_RE_CLICK  = re.compile(r'\b(click_[a-z0-9_]+)\(\s*page\s*\)', re.I)
CALL_RE_ENTER  = re.compile(r'\b(enter_[a-z0-9_]+)\(\s*page\s*,\s*(".*?"|\'.*?\')\s*\)', re.I)
CALL_RE_SELECT = re.compile(r'\b(select_[a-z0-9_]+)\(\s*page\s*,\s*(".*?"|\'.*?\')\s*\)', re.I)

def _collect_called_methods(code: str) -> Set[str]:
    names: Set[str] = set()
    names |= {m.group(1) for m in CALL_RE_CLICK.finditer(code)}
    names |= {m.group(1) for m in CALL_RE_ENTER.finditer(code)}
    names |= {m.group(1) for m in CALL_RE_SELECT.finditer(code)}
    return names

def _write_auto_stubs(method_names: Set[str]):
    """
    Create pages/auto_stubs.py with stub functions that fall back to robust Playwright selectors.
    Real page methods (from other modules) will override these because tests import stubs FIRST.
    """
    PAGES_DIR.mkdir(parents=True, exist_ok=True)
    (PAGES_DIR / "__init__.py").touch()
    stub_file = PAGES_DIR / "auto_stubs.py"

    header = '''# Auto-generated stubs (do not edit by hand)
import re

def _select_dropdown(page, label_text: str, value: str) -> bool:
    """
    Robustly selects a dropdown value for either native <select> or custom dropdowns.
    """
    import re
    label_rx = re.compile(label_text, re.I)
    value_exact = re.compile(rf"^{re.escape(value)}$", re.I)
    value_fuzzy = re.compile(value, re.I)

    # Native <select> by label
    try:
        sel = page.get_by_label(label_rx)
        try:
            sel.select_option(value=value); return True
        except Exception: pass
        try:
            sel.select_option(label=value); return True
        except Exception: pass
        try:
            sel.select_option(index="0"); return True
        except Exception: pass
    except Exception:
        pass

    # Nearby select by DOM proximity
    try:
        near_select = page.locator(
            f"label:has-text('{label_text}') ~ select, "
            f"*:has(> label:has-text('{label_text}')) select"
        ).first
        if near_select.count() == 0:
            near_select = page.locator("select").first
        if near_select.count() > 0:
            try:
                near_select.select_option(value=value); return True
            except Exception: pass
            try:
                near_select.select_option(label=value); return True
            except Exception: pass
    except Exception:
        pass

    # ARIA combobox/listbox
    try:
        trigger = page.get_by_role("combobox", name=label_rx).first
        if trigger:
            trigger.click()
            try:
                page.get_by_role("option", name=value_exact).first.click(timeout=2000); return True
            except Exception: pass
            try:
                page.get_by_role("option", name=value_fuzzy).first.click(timeout=2000); return True
            except Exception: pass
            try:
                listbox = page.get_by_role("listbox").first
                listbox.get_by_role("option", name=value_fuzzy).first.click(timeout=2000); return True
            except Exception: pass
    except Exception:
        pass

    # Generic label->option click
    try:
        page.get_by_text(label_rx).first.click()
        try:
            page.get_by_role("option", name=value_exact).first.click(timeout=2000); return True
        except Exception: pass
        page.get_by_text(value_fuzzy).first.click(timeout=2000); return True
    except Exception:
        pass

    # Type-to-select
    try:
        page.keyboard.type(value)
        page.keyboard.press("Enter")
        return True
    except Exception:
        pass

    print(f"[AUTO-STUBS] Could not select '{value}' for '{label_text}'.")
    return False


def _fallback_call(fn_name, page, *args):
    try:
        if fn_name.startswith("click_"):
            label = fn_name[len("click_"):].replace("_", " ").strip()
            try:
                page.get_by_role("button", name=re.compile(label, re.I)).first.click(); return
            except Exception: pass
            try:
                page.get_by_role("link", name=re.compile(label, re.I)).first.click(); return
            except Exception: pass
            page.get_by_text(re.compile(label, re.I)).first.click(); return

        if fn_name.startswith("enter_"):
            label = fn_name[len("enter_"):].replace("_", " ").strip()
            value = args[0] if args else ""
            try:
                page.get_by_label(re.compile(label, re.I)).fill(value); return
            except Exception: pass
            try:
                page.get_by_placeholder(re.compile(label, re.I)).fill(value); return
            except Exception: pass
            page.get_by_role("textbox").first.fill(value); return

        if fn_name.startswith("select_"):
            label = fn_name[len("select_"):].replace("_", " ").strip()
            value = args[0] if args else ""
            if _select_dropdown(page, label, value): return
            for alt in (f"{label} Type", f"{label} Name", f"{label} Category"):
                if _select_dropdown(page, alt, value): return
            return
    except Exception as e:
        print(f"[AUTO-STUBS] Fallback failed for {fn_name}: {e!r}")
'''

    funcs = []
    for name in sorted(method_names):
        if name.startswith("click_"):
            funcs.append(f"def {name}(page):\n    return _fallback_call('{name}', page)\n")
        elif name.startswith("enter_") or name.startswith("select_"):
            funcs.append(f"def {name}(page, value):\n    return _fallback_call('{name}', page, value)\n")
        else:
            funcs.append(f"def {name}(*args, **kwargs):\n    return None\n")

    stub_file.write_text(header + "\n".join(funcs), encoding="utf-8")
    return str(stub_file)

# =============================================================================
# Test generation wrapper (deterministic)
# =============================================================================
def generate_test_code_from_methods(user_story: str) -> str:
    stories = _split_into_stories(user_story)
    return _emit_tests_for_stories(stories)

# =============================================================================
# Routes
# =============================================================================
@router.post("/generate-from-story")
async def generate_from_user_story(
    user_story: Optional[str] = Form(None),
    site_url: Optional[str] = Form("https://www.saucedemo.com"),
    file: Optional[UploadFile] = File(None)
):
    _ensure_dirs()

    # --- ingest stories
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
                        detail=f"Sheet 'User Stories' not found. Sheets present: {xls.sheet_names}"
                    )
                df = pd.read_excel(io.BytesIO(content), sheet_name="User Stories")
            except Exception as e:
                raise HTTPException(
                    status_code=400,
                    detail=f"Failed to read 'User Stories' sheet from Excel: {str(e)}"
                )
        elif file.filename.endswith(".csv"):
            df = pd.read_csv(io.StringIO(content.decode()))
        else:
            raise HTTPException(status_code=400, detail="Unsupported file type")

        column_map = {col.strip().lower(): col for col in df.columns}
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
        raise HTTPException(status_code=400, detail="Either 'user_story' or 'file' must be provided")

    # optional snapshot of current metadata
    _snapshot_chroma_before()

    # gather page methods (for header imports in test file)
    method_map_full = get_all_page_methods(PAGES_DIR)

    # build test code (single file combining all stories)
    code_blocks: List[str] = []
    results = []
    for story in stories:
        code = generate_test_code_from_methods(story)
        code_blocks.append(code)
        results.append({"Prompt": "Generated from user story", "auto_testcase": code})

    # —— generate stubs for all called methods across all stories
    combined_code_for_parse = "\n\n".join(code_blocks)
    needed_methods = _collect_called_methods(combined_code_for_parse)
    stub_path = _write_auto_stubs(len(needed_methods) and needed_methods or set())

    # write tests file
    test_idx = _next_index()
    test_file = TESTS_DIR / f"test_{test_idx}.py"

    # header imports for tests — IMPORTANT ORDER:
    # 1) import stubs FIRST (so real methods imported later overwrite them)
    import_lines = ["from pages.auto_stubs import *"]
    for module_name in sorted(method_map_full.keys()):
        import_lines.append(f"from pages.{module_name} import *")

    test_file.write_text("\n\n".join(import_lines + code_blocks), encoding="utf-8")

    # generate ui_script_N.py
    ui_script_path = _generate_ui_script_for_test_file(test_file)

    # log file
    log_file = LOGS_DIR / f"logs_{test_idx}.log"
    log_file.write_text("Generated from user stories.", encoding="utf-8")

    return {
        "results": results,
        "test_file": str(test_file),
        "ui_script": str(ui_script_path),
        "log_file": str(log_file),
        "stubs_file": stub_path,
        "missing_methods_count": len(needed_methods),
    }

# JSON variant
@router.post("/generate-from-story-json")
def generate_from_story_json(payload: dict = Body(...)):
    story = payload.get("user_story") or payload.get("story")
    if not story:
        raise HTTPException(400, "Provide 'user_story' or 'story'.")
    text = story
    _ensure_dirs()
    _snapshot_chroma_before()

    method_map_full = get_all_page_methods(PAGES_DIR)
    code = generate_test_code_from_methods(text)

    # stubs for this one story
    needed_methods = _collect_called_methods(code)
    stub_path = _write_auto_stubs(len(needed_methods) and needed_methods or set())

    test_idx = _next_index()
    test_file = TESTS_DIR / f"test_{test_idx}.py"

    import_lines = ["from pages.auto_stubs import *"]
    for module_name in sorted(method_map_full.keys()):
        import_lines.append(f"from pages.{module_name} import *")

    test_file.write_text("\n\n".join(import_lines + [code]), encoding="utf-8")
    ui_script_path = _generate_ui_script_for_test_file(test_file)

    log_file = LOGS_DIR / f"logs_{test_idx}.log"
    log_file.write_text("Generated from JSON story.", encoding="utf-8")

    return {
        "status": "ok",
        "file": str(test_file),
        "ui_script": str(ui_script_path),
        "stubs_file": stub_path,
        "results": [{
            "Prompt": "Generated POM tests (positive/negative/edge) from user stories",
            "auto_testcase": code,
            "test_file": str(test_file),
            "ui_script": str(ui_script_path),
        }],
        "stories_count": len(_split_into_stories(text)),
        "missing_methods_count": len(needed_methods),
    }

@router.get("/ping")
def ping():
    return {"ok": True, "router": "generate_user_story"}


