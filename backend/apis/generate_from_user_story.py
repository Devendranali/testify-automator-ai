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



# generate_from_story.py
# FastAPI router to generate Playwright tests + a no-try/except async UI runner from user stories.

# from fastapi import APIRouter, HTTPException, Form, Body, UploadFile, File
# from pathlib import Path
# from typing import List, Dict, Tuple, Optional, Set
# import re
# import json
# import textwrap
# import pandas as pd
# import os
# import io
# from collections import defaultdict

# router = APIRouter(prefix="/rag", tags=["user-story"])
# __all__ = ["router"]

# # =============================================================================
# # Paths
# # =============================================================================
# RUN_DIR   = Path("generated_runs") / "src"
# TESTS_DIR = RUN_DIR / "tests"
# PAGES_DIR = RUN_DIR / "pages"
# LOGS_DIR  = RUN_DIR / "logs"
# META_DIR  = RUN_DIR / "metadata"
# DATA_DIR  = RUN_DIR / "data"

# # =============================================================================
# # FS helpers
# # =============================================================================
# def _ensure_dirs():
#     for d in (RUN_DIR, TESTS_DIR, PAGES_DIR, LOGS_DIR, META_DIR, DATA_DIR):
#         d.mkdir(parents=True, exist_ok=True)
#         # make importable
#         if d.name in {"src", "tests", "pages", "logs", "metadata", "data"}:
#             (d / "__init__.py").touch()

# def _next_index() -> int:
#     files = list(TESTS_DIR.glob("test_*.py"))
#     nums = [int(m.group(1)) for f in files if (m := re.match(r"test_(\d+)\.py", f.name))]
#     return max(nums, default=0) + 1

# # =============================================================================
# # Parsing: Gherkin-ish stories
# # =============================================================================
# URL_RE = re.compile(r'(https?://[^\s"\'\)]+)', re.I)

# PATTERNS = {
#     # Navigation
#     "goto_named": re.compile(
#         r'\b(?:given\s+i\s+open\s+the\s+browser\s+and\s+navigate\s+to|go\s+to|navigate\s+to|open)\s+"(https?://[^"]+)"',
#         re.I
#     ),
#     "goto_am_on": re.compile(
#         r'\bgiven\s+i\s+am\s+on\b.*?\bon\s+(https?://[^\s"\'\)]+)',
#         re.I
#     ),

#     # Clicks
#     "click_link":   re.compile(r'\b(?:and|when|then)?\s*i\s+click(?:\s+on)?\s+the\s+"([^"]+)"\s+link\b', re.I),
#     "click_button": re.compile(r'\b(?:and|when|then)?\s*i\s+click(?:\s+on)?\s+the\s+"([^"]+)"\s+button\b', re.I),
#     "click_plain":  re.compile(r'\b(?:and|when|then)?\s*i\s+click(?:\s+on)?\s+the\s+"([^"]+)"\s*(?!\s*(?:button|link)\b)', re.I),

#     # Enter (quoted and unquoted labels)
#     "enter_field_q":  re.compile(r'\b(?:and|when)?\s*i\s+enter\s+"([^"]+)"\s+in\s+the\s+"([^"]+)"\s+field\b', re.I),
#     "enter_field_nq": re.compile(r'\b(?:and|when)?\s*i\s+enter\s+"([^"]+)"\s+in\s+the\s+([A-Za-z0-9 _\-]+)\s+field\b', re.I),

#     # Select (quoted and unquoted labels)
#     "select_q":  re.compile(r'\b(?:and|when)?\s+i\s+select\s+"([^"]+)"\s+for\s+"([^"]+)"(?:\s+field)?\b', re.I),
#     "select_nq": re.compile(r'\b(?:and|when)?\s+i\s+select\s+"([^"]+)"\s+for\s+(?:the\s+)?([A-Za-z0-9 _\-]+)(?:\s+field)?\b', re.I),

#     # Radios
#     "radio_click_named": re.compile(
#         r'\b(?:and|when|then)?\s*i\s+(?:click|choose|select)\s+the\s+"([^"]+)"\s+radio(?:\s+button)?\b', re.I
#     ),
#     "radio_choose_for_label": re.compile(
#         r'\b(?:and|when|then)?\s*i\s+(?:choose|select)\s+"([^"]+)"\s+for\s+(?:the\s+)?(?:radio\s+)?("?[A-Za-z0-9 _\-]+"?)\b', re.I
#     ),

#     # Multiple add-to-cart
#     "add_multi_cart_count": re.compile(
#         r'\badd\s+(?:the\s+)?(\d+)\s+(?:items?|products?)\s+to\s+cart\b', re.I
#     ),
#     "add_multi_cart_plain": re.compile(
#         r'\b(?:multiple\s+add\s+to\s+cart|add\s+multiple\s+(?:items?|products?)\s+to\s+cart)\b', re.I
#     ),
#     "add_multi_cart_all": re.compile(
#         r'\b(?:add\s+all\s+(?:items?|products?)\s+to\s+cart|add\s+to\s+cart\s+all\s+(?:items?|products?))\b', re.I
#     ),

#     # Assertions (ignored for generation)
#     "see_message":  re.compile(r'\b(?:then|and)\s+i\s+should\s+see\s+a\s+message\s+"([^"]+)"\b', re.I),
#     "see_text":     re.compile(r'\b(?:then|and)\s+i\s+should\s+see\s+"([^"]+)"\b', re.I),
#     "on_page":      re.compile(r'\b(?:then|and)\s+i\s+should\s+be\s+on\s+the\s+"([^"]+)"\s+page\b', re.I),
# }

# def _extract_all_urls(text: str) -> List[str]:
#     return [m.group(1).rstrip(".,);") for m in URL_RE.finditer(text or "")]

# def _slug(s: str) -> str:
#     s = (s or "").strip().lower()
#     s = re.sub(r'[^a-z0-9]+', '_', s)
#     return s.strip('_') or "x"

# def _split_into_stories(text: str) -> List[str]:
#     if not text or not text.strip():
#         return []
#     numbered = re.split(r'(?m)^\s*\d+\)\s*', text.strip())
#     numbered = [s.strip() for s in numbered if s.strip()]
#     if len(numbered) > 1:
#         return numbered
#     blocks = re.split(r'\n\s*\n+', text.strip())
#     blocks = [b.strip() for b in blocks if b.strip()]
#     return blocks or [text.strip()]

# def _parse_story_block(story: str) -> Tuple[str, List[Dict[str, str]]]:
#     """
#     Returns (base_url, steps). Steps can contain:
#       - {"type": "goto", "url": ...}
#       - {"type": "click_button"|"click_link"|"click_plain", "name": "..."}
#       - {"type": "enter_field"|"select_field", "label": "...", "value": "..."}
#       - {"type": "click_radio", "value": "...", "label"?: "..."}
#       - {"type": "multi_add_to_cart", "count": int|'ALL'}
#     """
#     steps: List[Dict[str, str]] = []
#     base_url = ""

#     # URL
#     m = PATTERNS["goto_named"].search(story) or PATTERNS["goto_am_on"].search(story)
#     if m:
#         base_url = m.group(1).rstrip('.,);')
#         steps.append({"type": "goto", "url": base_url})
#     else:
#         urls = _extract_all_urls(story)
#         if urls:
#             base_url = urls[0]
#             steps.append({"type": "goto", "url": base_url})

#     # Actions (in order)
#     for raw in story.splitlines():
#         line = raw.strip()
#         if not line:
#             continue

#         # multiple add-to-cart
#         if PATTERNS["add_multi_cart_all"].search(line):
#             steps.append({"type": "multi_add_to_cart", "count": "ALL"})
#             continue
#         m = PATTERNS["add_multi_cart_count"].search(line)
#         if m:
#             steps.append({"type": "multi_add_to_cart", "count": int(m.group(1))})
#             continue
#         if PATTERNS["add_multi_cart_plain"].search(line):
#             steps.append({"type": "multi_add_to_cart", "count": 3})  # default 3
#             continue

#         # clicks
#         m = PATTERNS["click_button"].search(line)
#         if m:
#             steps.append({"type": "click_button", "name": m.group(1)})
#             continue
#         m = PATTERNS["click_link"].search(line)
#         if m:
#             steps.append({"type": "click_link", "name": m.group(1)})
#             continue
#         m = PATTERNS["click_plain"].search(line)
#         if m:
#             steps.append({"type": "click_plain", "name": m.group(1)})
#             continue

#         # radios
#         m = PATTERNS["radio_click_named"].search(line)
#         if m:
#             steps.append({"type": "click_radio", "value": m.group(1)})
#             continue
#         m = PATTERNS["radio_choose_for_label"].search(line)
#         if m:
#             raw_lbl = m.group(2).strip()
#             label = raw_lbl[1:-1] if (raw_lbl.startswith('"') and raw_lbl.endswith('"')) else raw_lbl
#             steps.append({"type": "click_radio", "value": m.group(1), "label": label})
#             continue

#         # enter
#         m = PATTERNS["enter_field_q"].search(line) or PATTERNS["enter_field_nq"].search(line)
#         if m:
#             steps.append({"type": "enter_field", "value": m.group(1), "label": m.group(2)})
#             continue

#         # select
#         m = PATTERNS["select_q"].search(line) or PATTERNS["select_nq"].search(line)
#         if m:
#             steps.append({"type": "select_field", "value": m.group(1), "label": m.group(2)})
#             continue

#         # ignore assertions
#         if PATTERNS["see_message"].search(line): continue
#         if PATTERNS["see_text"].search(line):    continue
#         if PATTERNS["on_page"].search(line):     continue

#     if not base_url:
#         raise HTTPException(400, "No URL in story. Add a nav step or include a URL.")

#     return base_url, _dedupe_steps(steps)

# def _dedupe_steps(steps: List[Dict[str, str]]) -> List[Dict[str, str]]:
#     """
#     Keep original order but remove immediate duplicates.
#     """
#     out, last_sig = [], None
#     for st in steps:
#         if st["type"] in ("click_button", "click_link", "click_plain"):
#             sig = (st["type"], st.get("name", ""))
#         elif st["type"] in ("enter_field", "select_field"):
#             sig = (st["type"], st.get("label", ""), st.get("value", ""))
#         elif st["type"] in ("multi_add_to_cart",):
#             sig = (st["type"], st.get("count"))
#         elif st["type"] == "click_radio":
#             sig = (st["type"], st.get("label", ""), st.get("value", ""))
#         elif st["type"] == "goto":
#             sig = (st["type"], st.get("url", ""))
#         else:
#             sig = (st["type"], tuple(sorted(st.items())))
#         if sig == last_sig:
#             continue
#         out.append(st); last_sig = sig
#     return out

# # =============================================================================
# # POM method naming
# # =============================================================================
# def _method_click(name: str) -> str:
#     return f"click_{_slug(name)}"

# def _method_enter(label: str) -> str:
#     return f"enter_{_slug(label)}"

# def _method_select(label: str) -> str:
#     return f"select_{_slug(label)}"

# def _suite_name(steps: List[Dict[str, str]], url: str) -> str:
#     last = None
#     for st in steps:
#         if st["type"] in ("click_link", "click_button", "click_plain"):
#             last = st["name"]
#     if last:
#         return _slug(last)
#     return _slug(url.split("//", 1)[-1].split("/", 1)[0])

# # =============================================================================
# # Duplicate indexing & emitters (adds nth= when same label/name repeats)
# # =============================================================================
# def _indexing_maps(steps: List[Dict[str, str]]) -> Tuple[Dict[str,int], Dict[str,int]]:
#     label_seen = defaultdict(int)
#     name_seen  = defaultdict(int)
#     return label_seen, name_seen

# def _emit_positive(steps: List[Dict[str, str]]) -> List[str]:
#     out: List[str] = []
#     label_seen, name_seen = _indexing_maps(steps)

#     for st in steps:
#         t = st["type"]
#         if t == "goto":
#             out.append(f'    page.goto("{st["url"]}", wait_until="domcontentloaded")')
#             out.append('    page.wait_for_load_state("networkidle", timeout=10000)')
#         elif t in ("click_button", "click_link", "click_plain"):
#             name = st["name"]; idx = name_seen[name]; name_seen[name] += 1
#             nth = f", nth={idx}" if idx > 0 else ""
#             out.append(f'    {_method_click(name)}(page{nth})  # target="{name}"{", duplicate index" if idx>0 else ""}')
#         elif t == "enter_field":
#             label = st["label"]; idx = label_seen[label]; label_seen[label] += 1
#             nth = f", nth={idx}" if idx > 0 else ""
#             out.append(f'    {_method_enter(label)}(page, "{st["value"]}"{nth}, label="{label}")')
#         elif t == "select_field":
#             label = st["label"]; idx = label_seen[label]; label_seen[label] += 1
#             nth = f", nth={idx}" if idx > 0 else ""
#             out.append(f'    {_method_select(label)}(page, "{st["value"]}"{nth}, label="{label}")')
#         elif t == "click_radio":
#             key = st.get("label") or st.get("value", "radio"); idx = name_seen[key]; name_seen[key] += 1
#             nth = f", nth={idx}" if idx > 0 else ""
#             if st.get("label"):
#                 out.append(f'    click_radio(page, value="{st["value"]}", label="{st["label"]}"{nth})')
#             else:
#                 out.append(f'    click_radio(page, value="{st["value"]}"{nth})')
#         elif t == "multi_add_to_cart":
#             if st["count"] == "ALL":
#                 out.append(f'    add_to_cart_all(page)')
#             else:
#                 out.append(f'    add_to_cart_multiple(page, {st["count"]})')
#     return out

# def _emit_negative(steps: List[Dict[str, str]]) -> List[str]:
#     # same sequence as positive (assertions would differ in real projects)
#     return _emit_positive(steps)

# def _emit_edge(steps: List[Dict[str, str]]) -> List[str]:
#     out: List[str] = []
#     label_seen, name_seen = _indexing_maps(steps)

#     for st in steps:
#         t = st["type"]
#         if t == "goto":
#             out.append(f'    page.goto("{st["url"]}", wait_until="domcontentloaded")')
#             out.append('    page.wait_for_load_state("networkidle", timeout=10000)')
#         elif t in ("click_button", "click_link", "click_plain"):
#             name = st["name"]; idx = name_seen[name]; name_seen[name] += 1
#             nth = f", nth={idx}" if idx > 0 else ""
#             out.append(f'    {_method_click(name)}(page{nth})')
#         elif t == "enter_field":
#             label = st["label"]; idx = label_seen[label]; label_seen[label] += 1
#             nth = f", nth={idx}" if idx > 0 else ""
#             out.append(f'    {_method_enter(label)}(page, ""{nth}, label="{label}")')  # blank values for edge
#         elif t == "select_field":
#             label = st["label"]; idx = label_seen[label]; label_seen[label] += 1
#             nth = f", nth={idx}" if idx > 0 else ""
#             out.append(f'    {_method_select(label)}(page, "{st["value"]}"{nth}, label="{st["label"]}")')
#         elif t == "click_radio":
#             key = st.get("label") or st.get("value", "radio"); idx = name_seen[key]; name_seen[key] += 1
#             nth = f", nth={idx}" if idx > 0 else ""
#             if st.get("label"):
#                 out.append(f'    click_radio(page, value="{st["value"]}", label="{st["label"]}"{nth})')
#             else:
#                 out.append(f'    click_radio(page, value="{st["value"]}"{nth})')
#         elif t == "multi_add_to_cart":
#             if st["count"] == "ALL":
#                 out.append(f'    add_to_cart_all(page)')
#             else:
#                 out.append(f'    add_to_cart_multiple(page, {st["count"]})')
#     return out

# # ===== Collect referenced method names so we can generate stubs =====
# def _collect_methods_from_steps(steps: List[Dict[str, str]]) -> Set[str]:
#     needed: Set[str] = set()
#     for st in steps:
#         t = st["type"]
#         if t in ("click_button", "click_link", "click_plain"):
#             needed.add(_method_click(st["name"]))
#         elif t == "enter_field":
#             needed.add(_method_enter(st["label"]))
#         elif t == "select_field":
#             needed.add(_method_select(st["label"]))
#     return needed

# def _emit_tests_for_story(story_text: str) -> Tuple[str, Set[str]]:
#     url, steps = _parse_story_block(story_text)
#     name = _suite_name(steps, url) or "story"
#     needed = _collect_methods_from_steps(steps)

#     lines: List[str] = []
#     lines.append(_TEST_FILE_HEADER)
#     lines.append("from pages.auto_stubs import *")
#     lines.append("")
#     lines.append(f"def test_positive_{name}(page):")
#     lines.extend(_emit_positive(steps))
#     lines.append("")
#     lines.append(f"def test_negative_{name}(page):")
#     lines.extend(_emit_negative(steps))
#     lines.append("")
#     lines.append(f"def test_edge_{name}(page):")
#     lines.extend(_emit_edge(steps))
#     lines.append("")
#     return "\n".join(lines), needed

# def _emit_tests_for_stories(stories: List[str]) -> Tuple[str, Set[str]]:
#     uniq, seen = [], set()
#     for s in stories:
#         key = re.sub(r"\s+", " ", s.strip().lower())
#         if key not in seen:
#             seen.add(key); uniq.append(s)
#     all_needed: Set[str] = set()
#     blocks: List[str] = []
#     for s in uniq:
#         code, needed = _emit_tests_for_story(s)
#         blocks.append(code)
#         all_needed |= needed
#     return "\n\n".join(blocks), all_needed

# # =============================================================================
# # UI script (Async) helpers: no try/except + dynamic values only
# # =============================================================================
# _UI_HEADER_NO_TRY = """# Auto-generated UI runner (async) — no try/except

# import sys, os, json, re, asyncio, inspect
# from pathlib import Path
# from playwright.async_api import async_playwright

# _THIS_FILE = Path(__file__).resolve()
# _TESTS_DIR = _THIS_FILE.parent            # .../generated_runs/src/tests
# _SRC_ROOT  = _TESTS_DIR.parent            # .../generated_runs/src
# _PROJECT_ROOT = _TESTS_DIR.parents[2]     # .../backend

# for path in (str(_SRC_ROOT), str(_PROJECT_ROOT)):
#     if path not in sys.path:
#         sys.path.insert(0, path)

# # Optional SmartAI (import directly; ensure available, or comment next line if not used)
# from lib.smart_ai import patch_page_with_smartai

# # POMs (generated generic stubs)
# from pages.auto_stubs import *
# """

# _UI_HELPERS_NO_TRY = r"""
# # ---- dynamic data resolver (no hard-coding) ----
# def __slug(s: str) -> str:
#     s = (s or "").strip().lower()
#     s = re.sub(r'[^a-z0-9]+', '_', s)
#     return s.strip('_') or "x"

# def __flatten(d, prefix=""):
#     out = {}
#     if isinstance(d, dict):
#         for k, v in d.items():
#             nk = f"{prefix}.{k}" if prefix else k
#             out.update(__flatten(v, nk))
#     else:
#         out[prefix] = d
#     return out

# def __load_data():
#     dpath = Path(__file__).resolve().parents[1] / "data" / "test_data.json"
#     if dpath.exists():
#         return json.loads(dpath.read_text(encoding="utf-8"))
#     return {}

# _DATA = __load_data()
# _DATA_FLAT = __flatten(_DATA)

# def resolve_value(label: str, provided: str):
#     key_env = f"VAL_{__slug(label).upper()}"
#     env_val = os.getenv(key_env, "").strip()
#     if env_val:
#         return env_val

#     l = (label or "").lower()
#     want_keys = []
#     if "email" in l:      want_keys += ["email", "username", "user"]
#     if "name" in l and "first" in l:  want_keys += ["first_name", "firstname", "given"]
#     if "name" in l and "last" in l:   want_keys += ["last_name", "lastname", "family"]
#     if l.strip() == "name":           want_keys += ["name", "full_name"]
#     if "password" in l:  want_keys += ["password", "pass"]
#     if "zip" in l or "postal" in l:   want_keys += ["zip", "zip_code", "postal"]
#     if "city" in l:      want_keys += ["city"]
#     if "state" in l:     want_keys += ["state", "province", "region"]
#     if "address" in l:   want_keys += ["address", "address1", "addr1"]
#     if "mobile" in l or "phone" in l: want_keys += ["mobile", "phone", "phone_number"]

#     for k, v in _DATA_FLAT.items():
#         kk = k.lower()
#         for w in want_keys:
#             if kk.endswith(w) and isinstance(v, str) and v != "":
#                 return v
#     return provided

# # ---- scrolling & selection helpers ----
# async def __stabilize_scroll(page):
#     await page.evaluate("document.documentElement.style.scrollBehavior='auto'")
#     await page.evaluate("document.body && (document.body.style.scrollBehavior='auto')")

# async def __scroll_into_view(locator):
#     await locator.scroll_into_view_if_needed(timeout=5000)

# __last_click_hint = ""
# def __set_click_hint(txt: str):
#     global __last_click_hint
#     __last_click_hint = (txt or "").lower().strip()

# def __get_click_hint() -> str:
#     return __last_click_hint

# async def __choose_best_index(locs):
#     count = await locs.count()
#     for i in range(count):
#         el = locs.nth(i)
#         vis = await el.is_visible()
#         en = await el.is_enabled()
#         val = await el.evaluate("(n) => (n && 'value' in n and n.value) ? n.value : ''")
#         empty = (str(val).strip() == "")
#         if vis and en and empty:
#             return i
#     return 0

# async def __prefer_by_context(page, locs, label: str):
#     count = await locs.count()
#     if count <= 1:
#         return 0

#     lower_label = (label or "").lower()

#     if "email" in lower_label:
#         for i in range(count):
#             el = locs.nth(i)
#             t = (await el.get_attribute("type")) or ""
#             if t.lower() == "email":
#                 return i

#     hint = __get_click_hint()
#     keywords = []
#     if any(k in hint for k in ["signup", "sign up", "register", "new user", "create account"]):
#         keywords = ["signup", "sign up", "register", "new user", "create account"]
#     elif any(k in hint for k in ["login", "log in", "signin", "sign in"]):
#         keywords = ["login", "log in", "signin", "sign in"]

#     if keywords:
#         for i in range(count):
#             el = locs.nth(i)
#             form = el.locator("xpath=ancestor::form[1]")
#             if await form.count():
#                 text = (await form.inner_text()).lower()
#                 if any(k in text for k in keywords):
#                     return i

#     return await __choose_best_index(locs)

# async def safe_goto(page, url: str):
#     await page.goto(url, wait_until="domcontentloaded")
#     await page.wait_for_load_state("networkidle", timeout=10000)

# async def _enter_with_index_or_fallback(page, method_name: str, label: str, value: str, idx=None):
#     g = globals()
#     fn = g.get(method_name)
#     value = resolve_value(label, value)

#     if callable(fn):
#         if inspect.iscoroutinefunction(fn):
#             if idx is None:
#                 return await fn(page, value, label=label)
#             else:
#                 return await fn(page, value, nth=idx, label=label)
#         else:
#             if idx is None:
#                 return fn(page, value, label=label)
#             else:
#                 return fn(page, value, nth=idx, label=label)

#     await __stabilize_scroll(page)
#     locator_builders = [
#         lambda: page.get_by_label(label),
#         lambda: page.get_by_placeholder(label),
#         lambda: page.get_by_role("textbox", name=label),
#         lambda: page.locator(f'input[name="{label}"]'),
#         lambda: page.locator(f'[aria-label="{label}"]'),
#         lambda: page.locator(f'input[placeholder*="{label}"], textarea[placeholder*="{label}"]'),
#         lambda: page.locator(f'input[aria-label*="{label}"], textarea[aria-label*="{label}"]'),
#         lambda: page.locator(f'input[name*="{label}"], textarea[name*="{label}"]'),
#     ]

#     for get in locator_builders:
#         locs = get()
#         count = await locs.count()
#         if count == 0:
#             continue
#         target_i = int(idx) if idx is not None else await __prefer_by_context(page, locs, label)
#         await __scroll_into_view(locs.nth(target_i))
#         return await locs.nth(target_i).fill(value, force=True)

#     print(f"[UI-RUNNER][enter fallback] Could not fill label='{label}' idx='{idx}' (value masked)")
#     return None

# async def _click_with_index_or_fallback(page, method_name: str, text: str, idx=None):
#     g = globals()
#     fn = g.get(method_name)
#     if callable(fn):
#         __set_click_hint(text)
#         if inspect.iscoroutinefunction(fn):
#             return await (fn(page) if idx is None else fn(page, nth=idx))
#         else:
#             return (fn(page) if idx is None else fn(page, nth=idx))

#     await __stabilize_scroll(page)

#     locs = page.get_by_role("button", name=re.compile(f"^{re.escape(text)}$", re.I))
#     count = await locs.count()
#     if count:
#         target_i = int(idx) if idx is not None else 0
#         await __scroll_into_view(locs.nth(target_i))
#         __set_click_hint(text)
#         return await locs.nth(target_i).click(force=True)

#     locs = page.get_by_text(text, exact=True)
#     count = await locs.count()
#     if count:
#         target_i = int(idx) if idx is not None else 0
#         await __scroll_into_view(locs.nth(target_i))
#         __set_click_hint(text)
#         return await locs.nth(target_i).click(force=True)

#     print(f"[UI-RUNNER][click fallback] text='{text}', idx='{idx}' failed")
#     return None

# async def click_radio(page, value: str, label: str=None, nth: int=None):
#     await __stabilize_scroll(page)

#     name = label or value
#     locs = page.get_by_role("radio", name=re.compile(re.escape(name), re.I))
#     count = await locs.count()
#     if count:
#         i = 0 if nth is None else int(nth)
#         await __scroll_into_view(locs.nth(i))
#         return await locs.nth(i).check(force=True)

#     lbl = page.get_by_text(name, exact=True)
#     if await lbl.count():
#         cand = lbl.nth(nth or 0).locator('xpath=..').locator('input[type="radio"]')
#         if await cand.count():
#             await __scroll_into_view(cand.nth(0))
#             return await cand.nth(0).check(force=True)

#     if label:
#         lab = page.get_by_label(label)
#         if await lab.count():
#             sel = lab.nth(0).locator("select")
#             if await sel.count():
#                 await sel.first.select_option(str(value))
#                 return True

#     if label:
#         page.get_by_role("combobox", name=re.compile(re.escape(label), re.I)).click()
#         await asyncio.sleep(0.1)
#         opt = page.get_by_role("option", name=re.compile(re.escape(str(value)), re.I))
#         if await opt.count():
#             await opt.first.click()
#             return True

#     css = f'input[type="radio"][value="{value}"]'
#     locs = page.locator(css)
#     if not await locs.count() and label:
#         locs = page.locator(f'input[type="radio"][name="{label}"]')
#     if await locs.count():
#         i = 0 if nth is None else int(nth)
#         await __scroll_into_view(locs.nth(i))
#         return await locs.nth(i).check(force=True)

#     print(f"[UI-RUNNER][radio/dropdown] Not found value='{value}' label='{label}' nth='{nth}'")
#     return None

# async def add_to_cart_multiple(page, count: int):
#     n = int(count) if isinstance(count, int) or (isinstance(count, str) and str(count).isdigit()) else 0
#     clicked = 0
#     names = re.compile(r'(add to cart|add to basket|buy now)', re.I)
#     btns = page.get_by_role("button", name=names)
#     total = await btns.count()
#     i = 0
#     while clicked < n and i < total:
#         b = btns.nth(i)
#         await __scroll_into_view(b)
#         await b.click()
#         clicked += 1
#         i += 1
#     return clicked >= n

# async def add_to_cart_all(page):
#     names = re.compile(r'(add to cart|add to basket|buy now|add)', re.I)
#     btns = page.get_by_role("button", name=names)
#     total = await btns.count()
#     for i in range(total):
#         b = btns.nth(i)
#         await __scroll_into_view(b)
#         await b.click()
#     return True
# """

# _TEST_FILE_HEADER = """import sys
# from pathlib import Path
# from typing import TYPE_CHECKING

# _THIS_FILE = Path(__file__).resolve()
# _TESTS_DIR = _THIS_FILE.parent            # .../generated_runs/src/tests
# _SRC_ROOT  = _TESTS_DIR.parent            # .../generated_runs/src
# _PROJECT_ROOT = _TESTS_DIR.parents[2]     # .../backend

# for path in (str(_SRC_ROOT), str(_PROJECT_ROOT)):
#     if path not in sys.path:
#         sys.path.insert(0, path)

# if TYPE_CHECKING:
#     from playwright.sync_api import Page
# """

# def _generate_ui_script_for_test_file(test_path: Path):
#     """
#     Reads the test_{N}.py, extracts test_*(page): bodies,
#     rewrites to async calls (await), and writes tests/ui_script_{N}.py (async_playwright).
#     No try/except is emitted in the runner.
#     """
#     # 1) read the test file
#     test_src = test_path.read_text(encoding="utf-8")

#     # 2) extract test functions and their bodies
#     funcs = []
#     lines = test_src.splitlines(True)
#     cur_name, cur_body, in_func = None, [], False
#     for line in lines:
#         m = re.match(r"def (test_[a-zA-Z0-9_]+)\(page\):", line)
#         if m:
#             if cur_name and cur_body:
#                 funcs.append((cur_name, "".join(cur_body)))
#             cur_name = m.group(1)
#             cur_body = []
#             in_func = True
#             continue
#         if in_func:
#             if re.match(r"def [a-zA-Z_]", line) or (line and not line.startswith("    ")):
#                 in_func = False
#                 continue
#             cur_body.append(line)
#     if cur_name and cur_body:
#         funcs.append((cur_name, "".join(cur_body)))

#     # 3) header (no shims, direct imports)
#     header = _UI_HEADER_NO_TRY + _UI_HELPERS_NO_TRY

#     # 4) transform calls (enter/click -> helper; add awaits for async API)
#     def _transform_body(dedented: str) -> str:
#         src = dedented

#         # enter_* with label & optional nth -> _enter_with_index_or_fallback
#         src = re.sub(
#             r'\b(enter_[a-z0-9_]+)\(\s*page\s*,\s*(".*?"|\'.*?\')\s*(?:,\s*nth\s*=\s*(\d+))?\s*,\s*label\s*=\s*(".*?"|\'.*?\')\s*\)',
#             r'await _enter_with_index_or_fallback(page, "\1", \4, \2, \3)',
#             src
#         )

#         # click_* with optional nth -> _click_with_index_or_fallback
#         def _click_sub(m):
#             method = m.group(1)
#             nth    = m.group(2)
#             text   = method.replace("click_", "").replace("_", " ").strip()
#             if nth:
#                 return f'await _click_with_index_or_fallback(page, "{method}", "{text}", {nth})'
#             else:
#                 return f'await _click_with_index_or_fallback(page, "{method}", "{text}")'

#         src = re.sub(
#             r'\b(click_[a-z0-9_]+)\(\s*page\s*(?:,\s*nth\s*=\s*(\d+))?\s*\)',
#             _click_sub,
#             src
#         )

#         # radio helper (already explicit)
#         src = re.sub(r'\b(__?click_radio|click_radio)\(', r'await click_radio(', src)

#         # add-to-cart helper
#         src = re.sub(r'\b(__?add_to_cart_multiple|add_to_cart_multiple)\(', r'await add_to_cart_multiple(', src)
#         src = re.sub(r'\b(__?add_to_cart_all|add_to_cart_all)\(', r'await add_to_cart_all(', src)

#         # page.goto -> await safe_goto(page, ...)
#         src = re.sub(r'(?<!await\s)page\.goto\(', r'await safe_goto(page, ', src)

#         # page.wait_for_load_state -> keep await form
#         src = src.replace("page.wait_for_load_state(", "await page.wait_for_load_state(")

#         return src

#     # 5) wrap each test_* into async run_* with async_playwright (no try/except)
#     wrapper_blocks = []
#     for fname, fbody in funcs:
#         runner = "run_" + fname.replace("test_", "")
#         dedented = textwrap.dedent(fbody).strip("\n")
#         dedented = _transform_body(dedented)

#         # indent steps with 8 spaces
#         step_lines = []
#         for l in dedented.splitlines():
#             step_lines.append(("        " + l) if l.strip() else "")
#         steps = "\n".join(step_lines)

#         block = f"""async def {runner}():
#     async with async_playwright() as p:
#         headless = os.getenv("UI_HEADLESS", "0") == "1"
#         slow_mo = int(os.getenv("UI_SLOW_MO", "250"))
#         browser = await p.chromium.launch(headless=headless, slow_mo=slow_mo)
#         context = await browser.new_context()
#         page = await context.new_page()

#         _SRC_ROOT = Path(__file__).resolve().parents[1]
#         metadata_path = _SRC_ROOT / "metadata" / "after_enrichment.json"
#         log_dir = _SRC_ROOT / "logs"
#         log_dir.mkdir(parents=True, exist_ok=True)

#         if metadata_path.exists():
#             await patch_page_with_smartai(page, json.loads(metadata_path.read_text(encoding="utf-8")))

#         page.set_default_timeout(int(os.getenv("UI_TIMEOUT", "20000")))
#         page.set_default_navigation_timeout(int(os.getenv("UI_NAV_TIMEOUT", "30000")))

# {steps}

#         pause = os.getenv("UI_RUNNER_PAUSE", "1") == "1"
#         autoclose = os.getenv("UI_RUNNER_AUTOCLOSE", "0") == "1"
#         hold_secs = int(os.getenv("UI_RUNNER_HOLD", "120"))

#         if pause:
#             import aioconsole
#             await aioconsole.ainput("\\n[UI-RUNNER] Press Enter to close the browser...")
#         else:
#             await asyncio.sleep(hold_secs)

#         if autoclose:
#             await context.close()
#             await browser.close()

# """
#         wrapper_blocks.append(block)

#     # 6) main block calls all run_* in order
#     main_block = "\nif __name__ == '__main__':\n"
#     main_block += "    async def _main():\n"
#     for fname, _ in funcs:
#         main_block += f"        await run_{fname.replace('test_', '')}()\n"
#     main_block += "    asyncio.run(_main())\n"

#     # 7) write ui_script_{N}.py
#     m = re.match(r"test_(\d+)\.py$", test_path.name)
#     ui_name = f"ui_script_{m.group(1)}.py" if m else "ui_script.py"
#     ui_path = TESTS_DIR / ui_name
#     ui_path.write_text(header + "\n".join(wrapper_blocks) + main_block, encoding="utf-8")
#     return str(ui_path)

# # =============================================================================
# # Optional seed data (dynamic only; no hard-coded values)
# # =============================================================================
# def _load_json_if_exists(path: Path) -> Optional[dict]:
#     if path.exists():
#         return json.loads(path.read_text(encoding="utf-8"))
#     return None

# def _env_or_empty(name: str) -> str:
#     return os.getenv(name, "")

# def create_default_test_data(run_folder: Path):
#     """
#     Writes generated_runs/src/data/test_data.json with NO hard-coded values.
#     Precedence:
#       1) If TEST_DATA_JSON env points to a JSON file, load it.
#       2) Else, if generated_runs/src/data/test_data.override.json exists, load it.
#       3) Else, construct from environment variables (empty strings if missing).
#     """
#     data_dir = run_folder / "data"
#     data_dir.mkdir(parents=True, exist_ok=True)
#     (data_dir / "__init__.py").touch()

#     cfg_path = os.getenv("TEST_DATA_JSON", "").strip()
#     if cfg_path:
#         p = Path(cfg_path)
#         cfg = _load_json_if_exists(p)
#         if cfg is not None:
#             (data_dir / "test_data.json").write_text(json.dumps(cfg, indent=2), encoding="utf-8")
#             return

#     local_override = data_dir / "test_data.override.json"
#     cfg = _load_json_if_exists(local_override)
#     if cfg is not None:
#         (data_dir / "test_data.json").write_text(json.dumps(cfg, indent=2), encoding="utf-8")
#         return

#     data = {
#         "login": {
#             "username": _env_or_empty("LOGIN_USERNAME"),
#             "password": _env_or_empty("LOGIN_PASSWORD"),
#         },
#         "checkout": {
#             "first_name": _env_or_empty("CHECKOUT_FIRST_NAME"),
#             "last_name": _env_or_empty("CHECKOUT_LAST_NAME"),
#             "zip_code": _env_or_empty("CHECKOUT_ZIP"),
#         },
#         "product": {
#             "name": _env_or_empty("PRODUCT_NAME"),
#         },
#     }

#     (data_dir / "test_data.json").write_text(json.dumps(data, indent=2), encoding="utf-8")

# # =============================================================================
# # Page method discovery (optional; used for header imports in tests)
# # =============================================================================
# def get_all_page_methods(pages_dir: Path) -> Dict[str, List[str]]:
#     """
#     Returns mapping of page module -> list of function def lines (simple scan).
#     Used only to build 'from pages.<module> import *' in test header.
#     """
#     page_method_map: Dict[str, List[str]] = {}
#     for py_file in pages_dir.glob("*.py"):
#         if py_file.name == "__init__.py":
#             continue
#         page_name = py_file.stem
#         method_names = []
#         with open(py_file, "r", encoding="utf-8") as f:
#             for line in f:
#                 if re.match(r"def\s+[a-zA-Z_]\w*\s*\([^\)]*\):", line):
#                     method_names.append(line.strip())
#         page_method_map[page_name] = method_names
#     return page_method_map

# # =============================================================================
# # Auto-stub writer (generic POM fallbacks)
# # =============================================================================
# def _write_auto_stubs(method_names: Set[str]):
#     """
#     Create generated_runs/src/pages/auto_stubs.py with basic Playwright sync implementations
#     for all referenced click_/enter_/select_ methods. Safe to overwrite each run.
#     """
#     if not method_names:
#         method_names = set()
#     stub_file = PAGES_DIR / "auto_stubs.py"
#     lines = [
#         "import re",
#         "from typing import Optional",
#         "from playwright.sync_api import Page",
#         "",
#         "# Auto-generated: generic fallbacks so tests & linters are happy.",
#         "",
#         "def _scroll_into_view(loc):",
#         "    loc.scroll_into_view_if_needed(timeout=5000)",
#         "",
#         "def click_radio(page: Page, value: str, label: Optional[str]=None, nth: Optional[int]=None):",
#         "    name = label or value",
#         "    locs = page.get_by_role('radio', name=re.compile(re.escape(name), re.I))",
#         "    cnt = locs.count()",
#         "    if cnt:",
#         "        idx = 0 if nth is None else int(nth)",
#         "        _scroll_into_view(locs.nth(idx)); return locs.nth(idx).check(force=True)",
#         "    lbl = page.get_by_text(name, exact=True)",
#         "    if lbl.count():",
#         "        idx = 0 if nth is None else int(nth)",
#         "        cand = lbl.nth(idx).locator('xpath=..').locator('input[type=\"radio\"]')",
#         "        if cand.count():",
#         "            _scroll_into_view(cand.nth(0)); return cand.nth(0).check(force=True)",
#         "    css = f'input[type=\"radio\"][value=\"{value}\"]'",
#         "    locs = page.locator(css)",
#         "    if not locs.count() and label:",
#         "        locs = page.locator(f'input[type=\"radio\"][name=\"{label}\"]')",
#         "    if locs.count():",
#         "        idx = 0 if nth is None else int(nth)",
#         "        _scroll_into_view(locs.nth(idx)); return locs.nth(idx).check(force=True)",
#         "    return None",
#         "",
#     ]
#     for name in sorted(method_names):
#         if name.startswith("click_"):
#             text = name.replace("click_", "").replace("_", " ")
#             lines += [
#                 f"def {name}(page: Page, nth: Optional[int]=None, label: Optional[str]=None):",
#                 f"    target = label or '{text}'",
#                 f"    pat = re.compile(r'^' + re.escape(target) + r'$' , re.I)",
#                 f"    locs = page.get_by_role('button', name=pat)",
#                 f"    count = locs.count()",
#                 f"    if count:",
#                 f"        idx = 0 if nth is None else int(nth)",
#                 f"        _scroll_into_view(locs.nth(idx)); return locs.nth(idx).click()",
#                 f"    locs = page.get_by_text(target, exact=True)",
#                 f"    if locs.count():",
#                 f"        idx = 0 if nth is None else int(nth)",
#                 f"        _scroll_into_view(locs.nth(idx)); return locs.nth(idx).click()",
#                 f"    return None",
#                 "",
#             ]
#         elif name.startswith("enter_"):
#             lines += [
#                 f"def {name}(page: Page, value: str, nth: Optional[int]=None, label: Optional[str]=None):",
#                 f"    target = label or '{name.replace('enter_', '').replace('_',' ').strip()}'",
#                 f"    strategies = [",
#                 f"        lambda: page.get_by_label(target),",
#                 f"        lambda: page.get_by_placeholder(target),",
#                 f"        lambda: page.get_by_role('textbox', name=target),",
#                 f"        lambda: page.locator(f'input[name=\"{{target}}\"]'),",
#                 f"        lambda: page.locator(f'[aria-label=\"{{target}}\"]'),",
#                 f"        lambda: page.locator(f'input[placeholder*=\"{{target}}\"], textarea[placeholder*=\"{{target}}\"]'),",
#                 f"        lambda: page.locator(f'input[aria-label*=\"{{target}}\"], textarea[aria-label*=\"{{target}}\"]'),",
#                 f"        lambda: page.locator(f'input[name*=\"{{target}}\"], textarea[name*=\"{{target}}\"]'),",
#                 f"    ]",
#                 f"    for get in strategies:",
#                 f"        locs = get()",
#                 f"        count = locs.count()",
#                 f"        if not count: continue",
#                 f"        idx = 0 if nth is None else int(nth)",
#                 f"        _scroll_into_view(locs.nth(idx)); return locs.nth(idx).fill(value, force=True)",
#                 f"    return None",
#                 "",
#             ]
#         elif name.startswith("select_"):
#             lines += [
#                 f"def {name}(page: Page, value: str, nth: Optional[int]=None, label: Optional[str]=None):",
#                 f"    target = label or '{name.replace('select_', '').replace('_',' ').strip()}'",
#                 f"    lab = page.get_by_label(target)",
#                 f"    if lab.count():",
#                 f"        sel = lab.nth(0).locator('select')",
#                 f"        if sel.count():",
#                 f"            return sel.first.select_option(value)",
#                 f"    page.get_by_role('combobox', name=re.compile(re.escape(target), re.I)).click()",
#                 f"    page.get_by_role('option', name=re.compile(re.escape(value), re.I)).click()",
#                 f"    return True",
#                 "",
#             ]
#         else:
#             lines += [f"def {name}(*args, **kwargs):", "    return None", ""]

#     stub_file.write_text("\n".join(lines), encoding="utf-8")

# # =============================================================================
# # Test generation wrapper (deterministic)
# # =============================================================================
# def generate_test_code_from_methods(user_story: str) -> Tuple[str, Set[str]]:
#     """
#     Deterministically parse the story and emit test modules + set of needed method names.
#     """
#     stories = _split_into_stories(user_story)
#     return _emit_tests_for_stories(stories)

# # =============================================================================
# # Routes
# # =============================================================================
# @router.post("/generate-from-story")
# async def generate_from_user_story(
#     user_story: Optional[str] = Form(None),
#     site_url: Optional[str] = Form(None),  # kept for compatibility; not required
#     file: Optional[UploadFile] = File(None)
# ):
#     _ensure_dirs()

#     # --- ingest stories
#     stories: List[str] = []
#     if file:
#         content = await file.read()
#         if file.filename.endswith((".xls", ".xlsx")):
#             xls = pd.ExcelFile(io.BytesIO(content))
#             if "User Stories" not in xls.sheet_names:
#                 raise HTTPException(
#                     status_code=400,
#                     detail=f"Sheet 'User Stories' not found. Sheets present: {xls.sheet_names}"
#                 )
#             df = pd.read_excel(io.BytesIO(content), sheet_name="User Stories")
#         elif file.filename.endswith(".csv"):
#             df = pd.read_csv(io.StringIO(content.decode()))
#         else:
#             raise HTTPException(status_code=400, detail="Unsupported file type")

#         column_map = {col.strip().lower(): col for col in df.columns}
#         if "user story" not in column_map:
#             raise HTTPException(
#                 status_code=400,
#                 detail=f"Column 'User Story' not found in sheet. Columns present: {list(column_map.keys())}"
#             )
#         column_name = column_map["user story"]
#         stories = df[column_name].dropna().astype(str).tolist()
#     elif user_story:
#         stories = [user_story]
#     else:
#         raise HTTPException(status_code=400, detail="Either 'user_story' or 'file' must be provided")

#     # build test code (single file combining all stories)
#     code_blocks: List[str] = []
#     all_needed_methods: Set[str] = set()
#     results = []
#     for story in stories:
#         code, needed = generate_test_code_from_methods(story)
#         code_blocks.append(code)
#         all_needed_methods |= needed
#         results.append({
#             "Prompt": "Generated from user story",
#             "auto_testcase": code,
#         })

#     # Ensure stub methods exist so tests & linters are happy
#     _write_auto_stubs(all_needed_methods)

#     # write tests file
#     test_idx = _next_index()
#     test_file = TESTS_DIR / f"test_{test_idx}.py"
#     test_file.write_text("\n\n".join(code_blocks), encoding="utf-8")

#     # generate async ui_script_N.py (no try/except)
#     ui_script_path = _generate_ui_script_for_test_file(test_file)

#     # optional seed data (dynamic; no hard-coded values)
#     create_default_test_data(RUN_DIR)

#     # log file (pure text)
#     log_file = LOGS_DIR / f"logs_{test_idx}.log"
#     log_file.write_text("Generated from user stories.", encoding="utf-8")

#     return {
#         "results": results,
#         "test_file": str(test_file),
#         "ui_script": str(ui_script_path),
#         "log_file": str(log_file),
#     }

# # JSON variant
# @router.post("/generate-from-story-json")
# def generate_from_story_json(payload: dict = Body(...)):
#     story = payload.get("user_story") or payload.get("story")
#     if not story:
#         raise HTTPException(400, "Provide 'user_story' or 'story'.")
#     text = story
#     _ensure_dirs()

#     code, needed = generate_test_code_from_methods(text)
#     _write_auto_stubs(needed)

#     test_idx = _next_index()
#     test_file = TESTS_DIR / f"test_{test_idx}.py"
#     test_file.write_text(code, encoding="utf-8")
#     ui_script_path = _generate_ui_script_for_test_file(test_file)
#     create_default_test_data(RUN_DIR)

#     log_file = LOGS_DIR / f"logs_{test_idx}.log"
#     log_file.write_text("Generated from JSON story.", encoding="utf-8")

#     return {
#         "status": "ok",
#         "file": str(test_file),
#         "ui_script": str(ui_script_path),
#         "results": [{
#             "Prompt": "Generated POM tests (positive/negative/edge) from user stories with duplicate-field disambiguation + radios/combobox + add-to-cart (N/ALL)",
#             "auto_testcase": code,
#             "test_file": str(test_file),
#             "ui_script": str(ui_script_path),
#         }],
#         "stories_count": len(_split_into_stories(text)),
#     }

# @router.get("/ping")
# def ping():
#     return {"ok": True, "router": "generate_user_story"}
