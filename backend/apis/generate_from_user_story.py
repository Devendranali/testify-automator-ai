

# generate_user_story.py
from fastapi import APIRouter, HTTPException, Form, Body, UploadFile, File
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Set
import re, json, textwrap, pandas as pd, io, os

# Optional Chroma snapshot (safe if not installed)
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
RUN_DIR  = Path("generated_runs") / "src"
TESTS_DIR = RUN_DIR / "tests"
PAGES_DIR = RUN_DIR / "pages"
LOGS_DIR  = RUN_DIR / "logs"
META_DIR  = RUN_DIR / "metadata"

def _ensure_dirs():
    for d in (RUN_DIR, TESTS_DIR, PAGES_DIR, LOGS_DIR, META_DIR):
        d.mkdir(parents=True, exist_ok=True)
        if not (d / "__init__.py").exists():
            (d / "__init__.py").touch()

def _next_index() -> int:
    files = list(TESTS_DIR.glob("test_*.py"))
    nums = [int(m.group(1)) for f in files if (m := re.match(r"test_(\d+)\.py", f.name))]
    return max(nums, default=0) + 1

def _snapshot_chroma_before():
    if not _CHROMA_ENABLED:
        return
    try:
        chroma_path = os.environ.get("SMARTAI_CHROMA_PATH", "./data/chroma_db")
        collection_name = os.environ.get("SMARTAI_CHROMA_COLLECTION", "element_metadata")
        chroma_client = PersistentClient(path=chroma_path)
        collection = chroma_client.get_or_create_collection(name=collection_name)
        data = collection.get() or {}
        metas = data.get("metadatas", [])
        META_DIR.mkdir(parents=True, exist_ok=True)
        (META_DIR / "before_enrichment.json").write_text(json.dumps(metas, indent=2), encoding="utf-8")
    except Exception:
        pass

# =============================================================================
# Parsing (gherkin-ish)
# =============================================================================
URL_RE = re.compile(r'(https?://[^\s"\'\)]+)', re.I)

def _normalize_quotes(text: str) -> str:
    if not text: return text
    return (text
        .replace("\u201c", '"').replace("\u201d", '"')
        .replace("\u2018", '"').replace("\u2019", '"')
        .replace("“", '"').replace("”", '"')
        .replace("‘", '"').replace("’", '"')
    )

PATTERNS = {
    # Base nav
    "goto_named": re.compile(
        r'\b(?:given\s+i\s+open\s+the\s+browser\s+and\s+navigate\s+to|go\s+to|navigate\s+to|open)\s+"(https?://[^"]+)"',
        re.I
    ),
    "goto_am_on": re.compile(r'\bgiven\s+i\s+am\s+on\b.*?\bon\s+(https?://[^\s"\'\)]+)', re.I),

    # Upload (detect BEFORE generic clicks)
    "upload_click_and_select": re.compile(
        r'\b(?:and|when)?\s*i\s+click(?:\s+on)?\s+(?:the\s+)?"([^"]+)"\s+(?:button|link)\s+and\s+(?:choose|select|upload)\s+"([^"]+)"(?:\s+file|\s+from\s+my\s+local\s+system)?\b',
        re.I
    ),
    "upload_select_only": re.compile(
        r'\b(?:and|when)?\s*i\s+(?:choose|select|upload|attach)\s+(?:the\s+)?file\s+"([^"]+)"\b',
        re.I
    ),

    # ✅ Checkboxes (detect BEFORE generic clicks)
    "checkbox_check": re.compile(
        r'\b(?:and|when)?\s*i\s+(?:check|tick|enable|select|mark)\s+(?:the\s+)?"([^"]+)"\s+(?:checkbox|check\s*box)\b',
        re.I
    ),
    "checkbox_uncheck": re.compile(
        r'\b(?:and|when)?\s*i\s+(?:uncheck|untick|disable|deselect|unmark)\s+(?:the\s+)?"([^"]+)"\s+(?:checkbox|check\s*box)\b',
        re.I
    ),
    "checkbox_click": re.compile(
        r'\b(?:and|when)?\s*i\s+click(?:\s+on)?\s+(?:the\s+)?"([^"]+)"\s+(?:checkbox|check\s*box)\b',
        re.I
    ),

    # Generic clicks — allow trailing words after the quoted label
    "click_link":   re.compile(r'\b(?:and|when|then)?\s*i\s+click(?:\s+on)?\s+(?:the\s+)?"([^"]+)"\s+link\b.*$', re.I),
    "click_button": re.compile(r'\b(?:and|when|then)?\s*i\s+click(?:\s+on)?\s+(?:the\s+)?"([^"]+)"\s+button\b.*$', re.I),
    "click_plain":  re.compile(r'\b(?:and|when|then)?\s*i\s+click(?:\s+on)?\s+(?:the\s+)?"([^"]+)"(?!\s*(?:button|link)\b).*$',
                               re.I),

    # Sidebar/menu/tab phrased with "select the … option"
    "nav_select_sidebar": re.compile(
        r'\b(?:and|when)?\s*i\s+select\s+the\s+"([^"]+)"\s+option\s+(?:from\s+the\s+)?(?:side\s*bar|sidebar|menu|left\s+nav|navigation|nav|tab)\b.*$',
        re.I
    ),
    "nav_select_generic": re.compile(
        r'\b(?:and|when)?\s*i\s+select\s+the\s+"([^"]+)"\s+(?:option|item)\b.*$', re.I
    ),

    # Enter / Select / Radio / Date
    "enter_field_q":  re.compile(r'\b(?:and|when)?\s*i\s+enter\s+"([^"]+)"\s+in\s+the\s+"([^"]+)"\s+field\b', re.I),
    "enter_field_nq": re.compile(r'\b(?:and|when)?\s*i\s+enter\s+"([^"]+)"\s+in\s+the\s+([A-Za-z0-9 _\-]+)\s+field\b', re.I),

    "select_q":  re.compile(r'\b(?:and|when)?\s+i\s+select\s+"([^"]+)"\s+for\s+"([^"]+)"(?:\s+field)?\b', re.I),
    "select_nq": re.compile(r'\b(?:and|when)?\s+i\s+select\s+"([^"]+)"\s+for\s+(?:the\s+)?([A-Za-z0-9 _\-]+)(?:\s+field)?\b', re.I),
    "select_by_id":   re.compile(r'\b(?:and|when)?\s+i\s+select\s+"([^"]+)"\s+from\s+the\s+dropdown\s+with\s+id\s+"([^"]+)"\b', re.I),
    "select_by_name": re.compile(r'\b(?:and|when)?\s+i\s+select\s+"([^"]+)"\s+from\s+the\s+dropdown\s+with\s+name\s+"([^"]+)"\b', re.I),
    "select_dropdown_generic": re.compile(
        r'\b(?:and|when)?\s+i\s+(?:try\s+to\s+)?select\s+"([^"]+)"\s+from\s+(?:the\s+)?dropdown\b', re.I
    ),

    # Radio — many phrasings
    "radio_select_q": re.compile(
        r'\b(?:and|when)?\s+i\s+(?:select|choose|pick)\s+"([^"]+)"\s+(?:for|in|on)\s+"([^"]+)"\s+(?:radio|radio\s*button|radiogroup)\b',
        re.I
    ),
    "radio_select_q_val_unquoted": re.compile(
        r'\b(?:and|when)?\s+i\s+(?:select|choose|pick)\s+([A-Za-z0-9 _\-]+)\s+(?:for|in|on)\s+"([^"]+)"\s+(?:radio|radio\s*button|radiogroup)\b',
        re.I
    ),
    "radio_select_generic": re.compile(
        r'\b(?:and|when)?\s+i\s+(?:select|choose|pick)\s+the\s+"([^"]+)"\s+(?:radio|radio\s*button|radio\s*option)\b',
        re.I
    ),
    "radio_select_generic_unquoted": re.compile(
        r'\b(?:and|when)?\s+i\s+(?:select|choose|pick)\s+the\s+([A-Za-z0-9 _\-]+)\s+(?:radio|radio\s*button|radio\s*option)\b',
        re.I
    ),
    "radio_click_value": re.compile(
        r'\b(?:and|when|then)?\s*i\s+click(?:\s+on)?\s+the\s+"([^"]+)"\s+(?:radio|radio\s*button|radio\s*option)\b',
        re.I
    ),
    "radio_click_value_unquoted": re.compile(
        r'\b(?:and|when|then)?\s*i\s+click(?:\s+on)?\s+the\s+([A-Za-z0-9 _\-]+)\s+(?:radio|radio\s*button|radio\s*option)\b',
        re.I
    ),

    "pick_date": re.compile(
        r'\b(?:and|when)?\s*i\s+(?:select|choose|pick|set)\s+(?:the\s+)?(?:travel\s+|journey\s+|departure\s+|onward\s+|return\s+|date\s+of\s+journey\s+)?date(?:\s+(?:as|to|on))?\s+"([^"]+)"\b',
        re.I
    ),

    # Assertions (inline & block)
    "see_message_inline":  re.compile(r'\b(?:then|and)\s+i\s+should\s+see\s+(?:a\s+)?message\s+"([^"]+)"\b', re.I),
    "see_text_inline":     re.compile(r'\b(?:then|and)\s+i\s+should\s+see\s+"([^"]+)"\b', re.I),
    "see_text_inline_loose": re.compile(r'\b(?:then|and)\s+i\s+should\s+see\s+"([^"]+)"\b.*$', re.I),
    "see_message_displayed": re.compile(
        r'\b(?:then|and)\s+the\s+message\s+"([^"]+)"\s+should\s+be\s+(?:displayed|visible|shown)\b', re.I
    ),
    "see_quoted_displayed": re.compile(
        r'\b(?:then|and)\s+"([^"]+)"\s+should\s+be\s+(?:displayed|visible|shown)\b', re.I
    ),
    "radio_should_be_selected": re.compile(
        r'\b(?:then|and)\s+i\s+should\s+see\s+that\s+"([^"]+)"\s+is\s+selected\b', re.I
    ),

    # Assertions (block, triple quotes)
    "see_message_block_start": re.compile(r'\b(?:then|and)\s+i\s+should\s+see\s+the\s+message\s*:?\s*$', re.I),

    # Navigation confirmation (ignored for codegen)
    "on_page": re.compile(r'\b(?:then|and)\s+i\s+should\s+be\s+on\s+the\s+"([^"]+)"\s+page\b', re.I),
}

def _extract_all_urls(text: str) -> List[str]:
    return [m.group(1).rstrip(".,);") for m in URL_RE.finditer(text or "")]

def _slug(s: str) -> str:
    s = (s or "").strip().lower()
    s = re.sub(r'[^a-z0-9]+', '_', s)
    return s.strip('_') or "x"

def _split_into_stories(text: str) -> List[str]:
    if not text or not text.strip(): return []
    text = _normalize_quotes(text)
    numbered = re.split(r'(?m)^\s*\d+\)\s*', text.strip())
    numbered = [s.strip() for s in numbered if s.strip()]
    if len(numbered) > 1: return numbered
    blocks = re.split(r'\n\s*\n+', text.strip())
    blocks = [b.strip() for b in blocks if b.strip()]
    return blocks or [text.strip()]

def _dedupe_steps(steps: List[Dict[str, str]]) -> List[Dict[str, str]]:
    out, last_sig = [], None
    for st in steps:
        if st["type"] in ("click_button", "click_link", "click_plain"):
            sig = (st["type"], st.get("name", ""))
        elif st["type"] in ("enter_field", "select_field", "radio_field", "upload_file", "checkbox_field"):
            sig = (st["type"], st.get("label", ""), st.get("value", ""))
        elif st["type"] in ("goto", "pick_date", "assert_text", "assert_text_block", "assert_radio_selected"):
            sig = (st["type"], st.get("value", "") or st.get("url", ""))
        else:
            sig = (st["type"], tuple(sorted(st.items())))
        if sig == last_sig: continue
        out.append(st); last_sig = sig
    return out

def _method_click(name: str) -> str:      return f"click_{_slug(name)}"
def _method_enter(label: str) -> str:     return f"enter_{_slug(label)}"
def _method_select(label: str) -> str:    return f"select_{_slug(label)}"
def _method_radio(label: str) -> str:     return f"radio_{_slug(label or 'group')}"
def _method_checkbox(label: str) -> str:  return f"checkbox_{_slug(label or 'box')}"

def _suite_name(steps: List[Dict[str, str]], url: str) -> str:
    last = None
    for st in steps:
        if st["type"] in ("click_link", "click_button", "click_plain"): last = st["name"]
    return _slug(last) if last else _slug(url.split("//", 1)[-1].split("/", 1)[0])

def _py_literal_for_path(s: str) -> str:
    s = (s or "").strip().strip('"').strip("'")
    if not s.endswith("\\"):
        return f'r"{s}"'
    s2 = s.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{s2}"'

def _parse_story_block(story: str) -> Tuple[str, List[Dict[str, str]]]:
    story = _normalize_quotes(story)
    steps: List[Dict[str, str]] = []
    base_url = ""

    m = PATTERNS["goto_named"].search(story) or PATTERNS["goto_am_on"].search(story)
    if m:
        base_url = m.group(1).rstrip('.,);')
        steps.append({"type": "goto", "url": base_url})
    else:
        urls = _extract_all_urls(story)
        if urls:
            base_url = urls[0]
            steps.append({"type": "goto", "url": base_url})

    raw_lines = story.splitlines()
    i, n = 0, len(raw_lines)
    while i < n:
        line = _normalize_quotes(raw_lines[i].strip())
        if not line:
            i += 1; continue

        # Upload
        m = PATTERNS["upload_click_and_select"].search(line)
        if m:
            steps.append({"type": "click_plain", "name": m.group(1)})
            steps.append({"type": "upload_file", "value": _py_literal_for_path(m.group(2))})
            i += 1; continue
        m = PATTERNS["upload_select_only"].search(line)
        if m:
            steps.append({"type": "upload_file", "value": _py_literal_for_path(m.group(1))})
            i += 1; continue

        # Checkboxes
        m = PATTERNS["checkbox_check"].search(line)
        if m:
            steps.append({"type": "checkbox_field", "label": m.group(1), "value": "check"}); i += 1; continue
        m = PATTERNS["checkbox_uncheck"].search(line)
        if m:
            steps.append({"type": "checkbox_field", "label": m.group(1), "value": "uncheck"}); i += 1; continue
        m = PATTERNS["checkbox_click"].search(line)
        if m:
            steps.append({"type": "checkbox_field", "label": m.group(1), "value": "toggle"}); i += 1; continue

        # Clicks
        m = PATTERNS["click_button"].search(line)
        if m: steps.append({"type": "click_button", "name": m.group(1)}); i += 1; continue
        m = PATTERNS["click_link"].search(line)
        if m: steps.append({"type": "click_link", "name": m.group(1)}); i += 1; continue
        m = PATTERNS["click_plain"].search(line)
        if m: steps.append({"type": "click_plain", "name": m.group(1)}); i += 1; continue

        # Menu phrasing mapped to click
        m = PATTERNS["nav_select_sidebar"].search(line) or PATTERNS["nav_select_generic"].search(line)
        if m:
            steps.append({"type": "click_plain", "name": m.group(1)}); i += 1; continue

        # Inputs/Select
        m = PATTERNS["enter_field_q"].search(line) or PATTERNS["enter_field_nq"].search(line)
        if m:
            steps.append({"type": "enter_field", "value": m.group(1), "label": m.group(2)}); i += 1; continue
        m = PATTERNS["select_q"].search(line) or PATTERNS["select_nq"].search(line)
        if m:
            steps.append({"type": "select_field", "value": m.group(1), "label": m.group(2)}); i += 1; continue
        m = PATTERNS["select_by_id"].search(line)
        if m:
            steps.append({"type": "select_field", "value": m.group(1), "label": m.group(2)}); i += 1; continue
        m = PATTERNS["select_by_name"].search(line)
        if m:
            steps.append({"type": "select_field", "value": m.group(1), "label": m.group(2)}); i += 1; continue
        m = PATTERNS["select_dropdown_generic"].search(line)
        if m:
            steps.append({"type": "select_field", "value": m.group(1), "label": "dropdown"}); i += 1; continue

        # Radios
        m = PATTERNS["radio_select_q"].search(line)
        if m:
            steps.append({"type": "radio_field", "value": m.group(1), "label": m.group(2)}); i += 1; continue
        m = PATTERNS["radio_select_q_val_unquoted"].search(line)
        if m:
            steps.append({"type": "radio_field", "value": m.group(1).strip(), "label": m.group(2)}); i += 1; continue
        m = PATTERNS["radio_select_generic"].search(line)
        if m:
            steps.append({"type": "radio_field", "value": m.group(1), "label": ""}); i += 1; continue
        m = PATTERNS["radio_select_generic_unquoted"].search(line)
        if m:
            steps.append({"type": "radio_field", "value": m.group(1).strip(), "label": ""}); i += 1; continue
        m = PATTERNS["radio_click_value"].search(line) or PATTERNS["radio_click_value_unquoted"].search(line)
        if m:
            steps.append({"type": "radio_field", "value": m.group(1).strip(), "label": ""}); i += 1; continue

        m = PATTERNS["pick_date"].search(line)
        if m:
            steps.append({"type": "pick_date", "value": m.group(1)}); i += 1; continue

        # Assertions
        m = PATTERNS["radio_should_be_selected"].search(line)
        if m:
            steps.append({"type": "assert_radio_selected", "value": m.group(1)}); i += 1; continue

        m = PATTERNS["see_message_inline"].search(line)
        if m:
            steps.append({"type": "assert_text", "value": m.group(1)}); i += 1; continue
        m = PATTERNS["see_text_inline"].search(line)
        if m:
            steps.append({"type": "assert_text", "value": m.group(1)}); i += 1; continue
        m = PATTERNS["see_text_inline_loose"].search(line)
        if m:
            steps.append({"type": "assert_text", "value": m.group(1)}); i += 1; continue
        m = PATTERNS["see_message_displayed"].search(line)
        if m:
            steps.append({"type": "assert_text", "value": m.group(1)}); i += 1; continue
        m = PATTERNS["see_quoted_displayed"].search(line)
        if m:
            steps.append({"type": "assert_text", "value": m.group(1)}); i += 1; continue

        # Block message
        if PATTERNS["see_message_block_start"].search(line):
            j = i + 1
            while j < n and (raw_lines[j].strip() == ""):
                j += 1
            if j < n and (('"""' in raw_lines[j]) or ("'''" in raw_lines[j])):
                delim = '"""' if '"""' in raw_lines[j] else "'''"
                j += 1
                collected: List[str] = []
                while j < n and (delim not in raw_lines[j]):
                    collected.append(_normalize_quotes(raw_lines[j].rstrip("\n")))
                    j += 1
                block_text = "\n".join(collected).strip()
                if block_text:
                    steps.append({"type": "assert_text_block", "value": block_text})
                i = min(j + 1, n)
                continue
            else:
                i += 1
                continue

        # Ignore navigation confirmations
        if PATTERNS["on_page"].search(line):
            i += 1; continue

        i += 1

    if not base_url:
        raise HTTPException(400, "No URL in story. Add a nav step or include a URL.")
    return base_url, _dedupe_steps(steps)

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
        elif t == "radio_field":
            out.append(f'    {_method_radio(st["label"])}(page, "{st["value"]}")')
        elif t == "checkbox_field":
            out.append(f'    {_method_checkbox(st["label"])}(page, "{st["value"]}")')
        elif t == "pick_date":
            out.append(f'    pick_date(page, "{st["value"]}")')
        elif t == "upload_file":
            out.append(f'    upload_file(page, {st["value"]})')
        elif t == "assert_text":
            out.append(f'    assert_text_contains(page, "{st["value"]}")')
        elif t == "assert_text_block":
            block = textwrap.indent(st["value"], "    ")
            out.append('    assert_text_block(page, """\\\n' + block + '    """)')
        elif t == "assert_radio_selected":
            out.append(f'    assert_radio_selected(page, "{st["value"]}")')
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
            if "@" in bad: bad = bad.replace("@", "")
            elif bad.isdigit(): bad = st["value"]
            out.append(f'    {_method_enter(st["label"])}(page, "{bad}")')
        elif t == "select_field":
            out.append(f'    {_method_select(st["label"])}(page, "{st["value"]}")')
        elif t == "radio_field":
            out.append(f'    {_method_radio(st["label"])}(page, "{st["value"]}")')
        elif t == "checkbox_field":
            out.append(f'    {_method_checkbox(st["label"])}(page, "{st["value"]}")')
        elif t == "pick_date":
            out.append(f'    pick_date(page, "{st["value"]}")')
        elif t == "upload_file":
            out.append(f'    upload_file(page, {st["value"]})')
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
        elif t == "radio_field":
            out.append(f'    {_method_radio(st["label"])}(page, "{st["value"]}")')
        elif t == "checkbox_field":
            out.append(f'    {_method_checkbox(st["label"])}(page, "{st["value"]}")')
        elif t == "pick_date":
            out.append(f'    pick_date(page, "{st["value"]}")')
        elif t == "upload_file":
            out.append(f'    upload_file(page, {st["value"]})')
    return out

def _emit_tests_for_story(story_text: str) -> str:
    url, steps = _parse_story_block(story_text)
    name = _suite_name(steps, url) or "story"
    lines: List[str] = []
    lines.append(f"def test_positive_{name}(page):")
    lines.extend(_emit_positive(steps)); lines.append("")
    lines.append(f"def test_negative_{name}(page):")
    lines.extend(_emit_negative(steps)); lines.append("")
    lines.append(f"def test_edge_{name}(page):")
    lines.extend(_emit_edge(steps)); lines.append("")
    return "\n".join(lines)

def _emit_tests_for_stories(stories: List[str]) -> str:
    uniq, seen = [], set()
    for s in stories:
        key = re.sub(r"\s+", " ", s.strip().lower())
        if key not in seen:
            seen.add(key); uniq.append(s)
    return "\n".join(_emit_tests_for_story(s) for s in uniq)

# =============================================================================
# Auto-stubs & conftest (robust, generic)
# =============================================================================
_AUTO_STUBS_HEADER = r'''# generated_runs/src/pages/auto_stubs.py (auto-generated)
from pathlib import Path
import os, re, time
from playwright.sync_api import expect

# Short, configurable timeout for fast interactions (ms)
_FAST_TIMEOUT = int(os.getenv("UI_FAST_TIMEOUT", "2500") or "2500")

# ----------- flicker/zoom guards -----------
def _disable_motion_and_zoom(page):
    try:
        page.add_init_script("""
            (() => {
              try {
                window.addEventListener('keydown', e => {
                  if ((e.ctrlKey || e.metaKey) && (e.key === '+' || e.key === '-' || e.key === '=')) e.preventDefault();
                }, {passive:false});
                window.addEventListener('wheel', e => { if (e.ctrlKey) e.preventDefault(); }, {passive:false});
              } catch {}
            })();
        """)
    except Exception: pass
    try:
        page.add_style_tag(content="""
          *, *::before, *::after { transition-duration:0s!important; transition-delay:0s!important; animation-duration:0s!important; animation-delay:0s!important; }
          html,body { scroll-behavior:auto!important; }
        """)
    except Exception: pass

def _viewport_metrics(page):
    try:
        return page.evaluate("""() => ({
            scale: (window.visualViewport && window.visualViewport.scale) || 1,
            w: document.documentElement.clientWidth,
            h: document.documentElement.clientHeight
        })""")
    except Exception:
        return {"scale":1,"w":0,"h":0}

def _wait_layout_stable(page, stable_ms=300, timeout_ms=None):
    if timeout_ms is None: timeout_ms = _FAST_TIMEOUT*4
    end = time.time() + timeout_ms/1000.0
    last = None; since = None
    while time.time() < end:
        cur = _viewport_metrics(page)
        if cur == last:
            if since is None: since = time.time()
            if (time.time()-since)*1000 >= stable_ms: return True
        else:
            last = cur; since = None
        time.sleep(0.05)
    return False

def _visible_first(loc):
    try:
        n = loc.count()
        for i in range(n):
            el = loc.nth(i)
            try:
                if el.is_visible():
                    return el
            except Exception: continue
    except Exception: pass
    return None

def _normalize_story_path(p_hint: str) -> str:
    p = (p_hint or "").strip().strip('"').strip("'")
    if not p: return ""
    try: return str(Path(p))
    except Exception: return p

def _ensure_upload_file(path_hint: str) -> str:
    p = _normalize_story_path(path_hint)
    if not p:
        envp = os.getenv("UI_UPLOAD_FILE", "").strip()
        p = _normalize_story_path(envp)
    if p and Path(p).exists(): return p
    import tempfile
    tmp = Path(tempfile.gettempdir()) / "auto_upload.txt"
    if not tmp.exists(): tmp.write_text("auto-generated file\n", encoding="utf-8")
    return str(tmp)

# ----------- generic text entry -----------
def _fill_text_like(ctx, label: str, value: str) -> bool:
    import re
    label = (label or "").strip()
    if not label: return False
    rx = re.compile(label, re.I)
    key = re.sub(r"[^a-z0-9]+", "", label.lower())

    # a11y
    try:
        el = ctx.get_by_label(rx).first
        if el and el.count()>0: el.fill(value, timeout=_FAST_TIMEOUT); return True
    except Exception: pass
    try:
        el = ctx.get_by_role("textbox", name=rx).first
        if el and el.count()>0: el.fill(value, timeout=_FAST_TIMEOUT); return True
    except Exception: pass
    try:
        el = ctx.get_by_placeholder(rx).first
        if el and el.count()>0: el.fill(value, timeout=_FAST_TIMEOUT); return True
    except Exception: pass

    # attributes
    candidates = [
        f"input#{key}", f"input[name='{key}']", f"input[id='{key}']",
        f"input[aria-label='{label}']", f"input[aria-labelledby*='{key}' i]",
        f"input[aria-label*='{label}' i]", f"input[id*='{key}' i]", f"input[name*='{key}' i]",
        f"input[placeholder*='{label}' i]", f"[data-test*='{key}' i]",
        f"[data-testid*='{key}' i]", f"[data-qa*='{key}' i]",
        "input[type='text']", "input:not([type]), input[type='search'], input[type='email'], input[type='tel']",
        "textarea",
    ]
    for sel in candidates:
        try:
            el = ctx.locator(sel).first
            if el and el.count()>0 and el.is_visible():
                el.fill(value, timeout=_FAST_TIMEOUT); return True
        except Exception: pass

    # proximity
    prox = (
        f"//label[normalize-space()='{label}']/following::input[1]",
        f"//*[normalize-space(text())='{label}']/following::input[1]",
        f"(//td[normalize-space()='{label}']/following::td)[1]//input[1]",
        f"//*[normalize-space(text())='{label}']/ancestor::*[self::div or self::li or self::td or self::section or self::form][1]//input[1]",
    )
    for xp in prox:
        try:
            el = ctx.locator('xpath='+xp).first
            if el and el.count()>0 and el.is_visible():
                el.fill(value, timeout=_FAST_TIMEOUT); return True
        except Exception: pass

    # last resort
    try:
        tbs = ctx.get_by_role("textbox")
        if tbs and tbs.count()>0:
            _el = _visible_first(tbs)
            if _el: _el.fill(value, timeout=_FAST_TIMEOUT); return True
    except Exception: pass
    return False

# ----------- click helpers -----------
def _click_attempt(page, el):
    try:
        _wait_layout_stable(page, stable_ms=200)
        try: el.scroll_into_view_if_needed()
        except Exception: pass
        try:
            with page.expect_navigation(timeout=_FAST_TIMEOUT*4):
                el.click(timeout=_FAST_TIMEOUT)
            _wait_layout_stable(page, stable_ms=200); return True
        except Exception: pass
        try:
            el.click(timeout=_FAST_TIMEOUT, force=True)
            try: page.wait_for_load_state("domcontentloaded", timeout=_FAST_TIMEOUT*2)
            except Exception: pass
            _wait_layout_stable(page, stable_ms=200); return True
        except Exception: pass
        try:
            el.dblclick(timeout=_FAST_TIMEOUT, force=True)
            _wait_layout_stable(page, stable_ms=200); return True
        except Exception: return False
    except Exception: return False

def _click_best(page, label: str) -> bool:
    _disable_motion_and_zoom(page)
    label = (label or "").strip()
    if not label: return False
    rx = re.compile(rf"^\s*{re.escape(label)}\s*$", re.I)
    rx_sw = re.compile(re.escape(label), re.I)

    for getter in (
        lambda: page.get_by_role("link", name=rx).first,
        lambda: page.get_by_role("button", name=rx).first,
        lambda: page.get_by_role("heading", name=rx).first,
    ):
        try:
            el = getter()
            if el and el.count()>0 and el.is_visible():
                if _click_attempt(page, el): return True
        except Exception: pass

    try:
        card = page.locator(f".card, .top-card").filter(has_text=rx_sw).first
        if card and card.count()>0 and card.is_visible():
            if _click_attempt(page, card): return True
    except Exception: pass
    try:
        h = page.locator("h1,h2,h3,h4,h5,h6").filter(has_text=rx).first
        if h and h.count()>0 and h.is_visible():
            anc = h.locator("xpath=ancestor::a[1]")
            if anc and anc.count()>0 and anc.is_visible():
                if _click_attempt(page, anc.first): return True
            anc2 = h.locator("xpath=ancestor::*[contains(@class,'card') or contains(@class,'top-card')][1]")
            if anc2 and anc2.count()>0 and anc2.is_visible():
                if _click_attempt(page, anc2.first): return True
            if _click_attempt(page, h): return True
    except Exception: pass

    for sel in (
        f".element-list .menu-list li:has-text('{label}')",
        f"li:has-text('{label}')", f"span:has-text('{label}')",
        f"a:has-text('{label}')", f"div:has-text('{label}')",
    ):
        try:
            el = page.locator(sel).first
            if el and el.count()>0 and el.is_visible():
                if _click_attempt(page, el): return True
        except Exception: pass

    try:
        node = page.locator(f"xpath=//*[normalize-space(text())='{label}']").first
        if node and node.count()>0 and node.is_visible():
            anc = node.locator("xpath=ancestor::a[1]")
            if anc and anc.count()>0 and anc.is_visible():
                if _click_attempt(page, anc.first): return True
            if _click_attempt(page, node): return True
    except Exception: pass

    try:
        el = page.get_by_text(rx_sw).first
        if el and el.count()>0 and el.is_visible():
            if _click_attempt(page, el): return True
    except Exception: pass

    return False

# ----------- dropdown helpers -----------
def _fast_try_select(sel, value: str) -> bool:
    try:
        sel.select_option(label=value, timeout=_FAST_TIMEOUT); return True
    except Exception: pass
    try:
        sel.select_option(value=value, timeout=_FAST_TIMEOUT); return True
    except Exception: return False

def _fast_pick_from_listbox(ctx, value: str) -> bool:
    ex = re.compile(rf"^\s*{re.escape(value)}\s*$", re.I)
    sw = re.compile(rf"^\s*{re.escape(value)}", re.I)
    for rx in (ex, sw):
        try:
            el = ctx.get_by_role("option", name=rx).first
            if el and el.count()>0 and el.is_visible():
                el.click(timeout=_FAST_TIMEOUT); return True
        except Exception: pass
    for rx in (ex, sw):
        try:
            el = ctx.locator("[role='option'], li, div").filter(has_text=rx).first
            if el and el.count()>0 and el.is_visible():
                el.click(timeout=_FAST_TIMEOUT); return True
        except Exception: pass
    return False

def _fast_select_dropdown(page, label_text: str, value: str) -> bool:
    label_text = (label_text or "").strip()
    if not value: return False
    try:
        sel = page.get_by_label(re.compile(label_text, re.I)).first
        if sel and sel.count()>0:
            if _fast_try_select(sel, value): return True
    except Exception: pass
    if label_text:
        try:
            sel = page.locator(f"select#{label_text}, select[name='{label_text}'], select[id='{label_text}']").first
            if sel and sel.count()>0:
                if _fast_try_select(sel, value): return True
        except Exception: pass
    if label_text:
        try:
            near = page.locator(
                f"label:has-text('{label_text}') ~ select, *:has(> label:has-text('{label_text}')) select"
            ).first
            if near and near.count()>0:
                if _fast_try_select(near, value): return True
        except Exception: pass
    if label_text:
        try:
            cb = page.get_by_role("combobox", name=re.compile(label_text, re.I)).first
            if cb and cb.count()>0:
                try: cb.click(timeout=_FAST_TIMEOUT)
                except Exception:
                    try: cb.click(force=True, timeout=_FAST_TIMEOUT)
                    except Exception: pass
                inner = None
                try:
                    inner = cb.locator("input, [contenteditable='true']").first
                    if inner and inner.count()>0 and inner.is_visible():
                        try: inner.fill("", timeout=_FAST_TIMEOUT)
                        except Exception: pass
                        try: inner.type(value, delay=0, timeout=_FAST_TIMEOUT)
                        except Exception: pass
                except Exception: pass
                if _fast_pick_from_listbox(page, value): return True
                try: (inner if inner and inner.count()>0 else cb).press("Enter", timeout=_FAST_TIMEOUT); return True
                except Exception: pass
        except Exception: pass
    try:
        tb = page.get_by_role("textbox", name=re.compile(label_text, re.I)).first
        if tb and tb.count()>0:
            try: tb.fill("", timeout=_FAST_TIMEOUT)
            except Exception: pass
            try: tb.type(value, delay=0, timeout=_FAST_TIMEOUT)
            except Exception: pass
            try: page.keyboard.press("Enter", timeout=_FAST_TIMEOUT); return True
            except Exception: pass
    except Exception: pass
    try:
        selects = page.locator("select")
        cnt = selects.count()
        for i in range(min(cnt, 4)):
            sel = selects.nth(i)
            if _fast_try_select(sel, value): return True
    except Exception: pass
    return False

# ----------- checkbox helpers -----------
_TRUE_SET  = {"1","true","yes","on","check","checked","tick","enable","enabled","select","mark"}
_FALSE_SET = {"0","false","no","off","uncheck","unchecked","untick","disable","disabled","deselect","unmark"}
_TOGGLE_SET= {"toggle","switch","flip"}

def _coerce_checkbox_value(v):
    s = ("" if v is None else str(v)).strip().lower()
    if s in _TRUE_SET: return True
    if s in _FALSE_SET: return False
    if s in _TOGGLE_SET: return None
    return True

def _set_checkbox_node(el, want) -> bool:
    try:
        if want is None:
            el.click(timeout=_FAST_TIMEOUT); return True
    except Exception: pass
    try:
        if want is True:
            try: el.check(timeout=_FAST_TIMEOUT); return True
            except Exception: pass
            try: el.click(timeout=_FAST_TIMEOUT); return True
            except Exception: pass
        else:
            try: el.uncheck(timeout=_FAST_TIMEOUT); return True
            except Exception: pass
            try: el.click(timeout=_FAST_TIMEOUT); return True
            except Exception: pass
    except Exception: pass
    try:
        el.evaluate("""(node, v) => {
            if (v === null) v = !node.checked;
            node.checked = !!v;
            node.dispatchEvent(new Event('input', {bubbles:true}));
            node.dispatchEvent(new Event('change', {bubbles:true}));
        }""", want)
        return True
    except Exception: return False

def _checkbox_try_in_context(ctx, label_text: str, want) -> bool:
    label_text = (label_text or "").strip()
    if not label_text: return False
    rx = re.compile(label_text, re.I)
    try:
        el = ctx.get_by_role("checkbox", name=rx).first
        if el and el.count()>0 and el.is_visible():
            if _set_checkbox_node(el, want): return True
    except Exception: pass
    try:
        host = ctx.locator(f"label:has-text('{label_text}')").first
        if host and host.count()>0:
            if want is None:
                host.click(timeout=_FAST_TIMEOUT); return True
            try: host.click(timeout=_FAST_TIMEOUT)
            except Exception: pass
            inp = host.locator("input[type='checkbox']").first
            if inp and inp.count()>0 and _set_checkbox_node(inp, want): return True
    except Exception: pass
    try:
        cand = ctx.locator(
            f"input[type='checkbox'][id*='{label_text}' i], "
            f"input[type='checkbox'][name*='{label_text}' i], "
            f"input[type='checkbox'][value*='{label_text}' i]"
        ).first
        if cand and cand.count()>0 and cand.is_visible():
            if _set_checkbox_node(cand, want): return True
    except Exception: pass
    try:
        lab = ctx.locator("label").filter(has_text=rx).first
        if lab and lab.count()>0:
            inp = lab.locator("xpath=./ancestor-or-self::*[1]/descendant::input[@type='checkbox'][1]").first
            if inp and inp.count()>0:
                if _set_checkbox_node(inp, want): return True
    except Exception: pass
    return False

def _set_checkbox(page, label_text: str, value):
    want = _coerce_checkbox_value(value)
    try:
        if _checkbox_try_in_context(page, label_text, want): return True
    except Exception: pass
    try:
        for fr in page.frames:
            if fr is page.main_frame: continue
            if _checkbox_try_in_context(fr, label_text, want): return True
    except Exception: pass
    print(f"[AUTO-STUBS] Could not set checkbox '{label_text}' to '{value}'.")
    return False

# ----------- radio helpers (generic & resilient) -----------
def _norm(s):
    import re
    return re.sub(r"[\s\u00A0]+", "", (s or "").strip().lower())

def _find_radio_like(ctx, value: str):
    """Return a Locator for the radio whose visible label or value matches `value` (space/case-insensitive)."""
    import re as _re
    target_norm = _norm(value)
    rx_val = _re.compile(rf"^\s*{_re.escape(value)}\s*$", _re.I)

    # 1) ARIA role by accessible name
    try:
        el = ctx.get_by_role("radio", name=rx_val).first
        if el and el.count()>0 and el.is_visible():
            return el
    except Exception: pass

    # 2) Iterate inputs and match by value/label/nearby text
    try:
        radios = ctx.locator("input[type='radio']")
        cnt = radios.count()
        for i in range(cnt):
            r = radios.nth(i)
            try:
                v = r.get_attribute("value") or ""
            except Exception:
                v = ""
            if _norm(v) == target_norm:
                return r

            # extract text from labels / next sibling / parent
            try:
                txt = r.evaluate("""(n) => {
                    let t = "";
                    try {
                      if (n.labels && n.labels.length) {
                        for (const L of n.labels) t += " " + (L.innerText || L.textContent || "");
                      }
                      if (!t && n.nextSibling) t += " " + (n.nextSibling.textContent || "");
                      const p = n.parentElement;
                      if (!t && p) t += " " + (p.innerText || p.textContent || "");
                    } catch {}
                    return t;
                }""") or ""
            except Exception:
                txt = ""
            if _norm(txt) == target_norm or target_norm in _norm(txt):
                return r
    except Exception: pass

    # 3) Label text → input relation
    try:
        lab = ctx.locator("label").filter(has_text=rx_val).first
        if lab and lab.count()>0 and lab.is_visible():
            # Prefer 'for' association
            try:
                fid = lab.get_attribute("for")
                if fid:
                    cand = ctx.locator(f"#{fid}").first
                    if cand and cand.count()>0 and cand.is_visible():
                        return cand
            except Exception: pass
            # Otherwise use nearest preceding input
            try:
                inp = lab.locator("xpath=preceding::input[@type='radio'][1]").first
                if inp and inp.count()>0 and inp.is_visible():
                    return inp
            except Exception: pass
    except Exception: pass

    # 4) Text node preceding/adjacent a radio
    try:
        el = ctx.locator(f"xpath=//*[normalize-space(text())='{value}']/preceding::input[@type='radio'][1]").first
        if el and el.count()>0 and el.is_visible():
            return el
    except Exception: pass

    return None

def _check_radio(page, group_label: str, value: str):
    _disable_motion_and_zoom(page)
    _wait_layout_stable(page, stable_ms=200)

    # If a group label was provided, restrict search to that container when possible.
    ctxs = [page]
    if group_label:
        try:
            rg = page.get_by_role("radiogroup", name=re.compile(group_label, re.I)).first
            if rg and rg.count()>0: ctxs = [rg]
        except Exception: pass
        if ctxs == [page]:
            try:
                cont = page.locator(f"section:has-text('{group_label}'), form:has-text('{group_label}'), div:has-text('{group_label}')").first
                if cont and cont.count()>0: ctxs = [cont]
            except Exception: pass

    # Search in page (or group) then frames.
    for ctx in ctxs:
        el = _find_radio_like(ctx, value)
        if el:
            try:
                el.check(timeout=_FAST_TIMEOUT)
            except Exception:
                el.click(timeout=_FAST_TIMEOUT)
            _wait_layout_stable(page, stable_ms=200)
            return True

    try:
        for fr in page.frames:
            if fr is page.main_frame: continue
            el = _find_radio_like(fr, value)
            if el:
                try: el.check(timeout=_FAST_TIMEOUT)
                except Exception: el.click(timeout=_FAST_TIMEOUT)
                _wait_layout_stable(page, stable_ms=200)
                return True
    except Exception: pass

    print(f"[AUTO-STUBS] Radio '{value}' not found (group='{group_label or ''}').")
    return False

def assert_radio_selected(page, value: str):
    """Assert that a radio with label/value `value` is checked."""
    el = _find_radio_like(page, value)
    if not el:
        # Try frames too
        try:
            for fr in page.frames:
                if fr is page.main_frame: continue
                el = _find_radio_like(fr, value)
                if el: break
        except Exception:
            pass
    if not el:
        raise AssertionError(f"Radio '{value}' not found to assert selection.")
    expect(el).to_be_checked(timeout=_FAST_TIMEOUT*4)

# ----------- assert helpers -----------
def _result_context(page):
    candidates = ["#result",".display-result","#output",".mt-3","p:has-text('You have selected')","div:has-text('You have selected')"]
    for sel in candidates:
        try:
            el = page.locator(sel).first
            if el and el.count()>0 and el.is_visible(): return el
        except Exception: pass
    return page.locator("body")

def _normalize_space(s: str) -> str:
    import re
    return re.sub(r"\s+", " ", (s or "").strip())

def assert_text_contains(page, value: str):
    el = _result_context(page)
    try:
        expect(el).to_contain_text(value, timeout=_FAST_TIMEOUT*4); return
    except Exception: pass
    try:
        txt = _normalize_space(el.inner_text()); val = _normalize_space(value)
        if val and val in txt: return
    except Exception: pass
    m = re.match(r"^(.*?selected)\s+(.*)$", (value or "").strip(), re.I)
    if m:
        part1, part2 = m.group(1).strip(), m.group(2).strip()
        if part1: expect(el).to_contain_text(part1, timeout=_FAST_TIMEOUT*2)
        if part2: expect(el).to_contain_text(part2, timeout=_FAST_TIMEOUT*2)
        return
    tokens = [t.strip() for t in re.split(r"[\s:]+", value or "") if len(t.strip()) >= 3]
    for t in tokens:
        expect(el).to_contain_text(t, timeout=_FAST_TIMEOUT)

def assert_text_block(page, text: str):
    lines = [ln.strip() for ln in (text or "").splitlines() if ln.strip()]
    for ln in lines:
        assert_text_contains(page, ln)

# ----------- upload helpers -----------
def click_file_upload(page):
    try:
        link = page.get_by_role("link", name=re.compile(r"^\s*File Upload\s*$", re.I)).first
        if link and link.count()>0:
            try:
                with page.expect_navigation(timeout=_FAST_TIMEOUT*4):
                    link.click(timeout=_FAST_TIMEOUT)
            except Exception:
                link.click(timeout=_FAST_TIMEOUT)
            return
    except Exception: pass
    try:
        b = page.get_by_role("button", name=re.compile(r"\bupload\b", re.I)).first
        if b and b.count()>0: b.click(timeout=_FAST_TIMEOUT); return
    except Exception: pass
    try:
        l = page.get_by_role("link", name=re.compile(r"\bupload\b", re.I)).first
        if l and l.count()>0:
            try:
                with page.expect_navigation(timeout=_FAST_TIMEOUT*4):
                    l.click(timeout=_FAST_TIMEOUT)
            except Exception:
                l.click(timeout=_FAST_TIMEOUT)
            return
    except Exception: pass
    try:
        t = page.get_by_text(re.compile(r"\bupload\b", re.I)).first
        if t and t.count()>0: t.click(timeout=_FAST_TIMEOUT); return
    except Exception: pass

def upload_file(page, value=""):
    try:
        page.locator("input#file-upload, input[type='file']").first.wait_for(state="attached", timeout=_FAST_TIMEOUT*4)
    except Exception: pass
    inp = None
    try:
        loc = page.locator("input[type='file']"); inp = _visible_first(loc)
    except Exception: pass
    if not inp:
        try:
            t = page.get_by_text(re.compile(r"^\s*File Upload\s*$", re.I)).first
            if t and t.count()>0:
                try:
                    with page.expect_navigation(timeout=_FAST_TIMEOUT*4):
                        t.click(timeout=_FAST_TIMEOUT)
                except Exception:
                    t.click(timeout=_FAST_TIMEOUT)
                loc = page.locator("input[type='file']"); inp = _visible_first(loc)
        except Exception: pass
    if not inp: raise AssertionError("No <input type='file'> found on the page.")
    path = _ensure_upload_file(value)
    try: inp.scroll_into_view_if_needed()
    except Exception: pass
    try: inp.set_input_files(path, timeout=_FAST_TIMEOUT*4)
    except Exception as e: raise AssertionError(f"set_input_files failed for '{path}': {e!r}")

def click_upload(page):
    try:
        btn = page.locator("#file-submit").first
        if btn and btn.count()>0: btn.click(timeout=_FAST_TIMEOUT); return
    except Exception: pass
    rx = re.compile(r"^\s*Upload\s*$", re.I)
    try:
        page.get_by_role("button", name=rx).first.click(timeout=_FAST_TIMEOUT); return
    except Exception: pass
    try:
        page.get_by_role("link", name=rx).first.click(timeout=_FAST_TIMEOUT); return
    except Exception: pass
    try:
        page.get_by_text(rx).first.click(timeout=_FAST_TIMEOUT); return
    except Exception: pass
    try:
        inp = page.locator("input[type='file']").first
        if inp:
            form = inp.locator("xpath=ancestor::form[1]")
            if form and form.count()>0:
                bf = form.locator("button, [role='button'], input[type='submit']").first
                if bf and bf.count()>0: bf.click(timeout=_FAST_TIMEOUT); return
    except Exception: pass
    raise AssertionError("Upload button not found.")

def assert_upload(page, expected_path=""):
    try: page.wait_for_load_state("domcontentloaded", timeout=_FAST_TIMEOUT*4)
    except Exception: pass
    try:
        h = page.locator("h3").first
        if not h or h.count()==0: raise AssertionError("Upload result header not found.")
        txt = (h.inner_text() or "").strip()
        if "File Uploaded!" not in txt: raise AssertionError(f"Expected 'File Uploaded!' but saw '{txt}'")
    except Exception as e:
        raise AssertionError(f"Upload success message missing: {e!r}")
    exp = Path(_normalize_story_path(expected_path)).name if expected_path else ""
    try:
        name_el = page.locator("#uploaded-files, #uploaded_file, .uploaded-file, .uploaded-files").first
        if name_el and name_el.count()>0:
            name = (name_el.inner_text() or "").strip()
            if exp and exp != name: raise AssertionError(f"Expected uploaded name '{exp}', got '{name}'")
    except Exception:
        if exp: raise

def linger_after_success(page):
    secs = int(os.getenv("UI_LINGER_SEC", "6") or "6")
    time.sleep(max(0, secs))

def _fallback_call(fn_name, page, *args):
    try:
        if fn_name.startswith("click_"):
            label = fn_name[len("click_"):].replace("_", " ").strip()
            _disable_motion_and_zoom(page); _wait_layout_stable(page, stable_ms=200)
            if _click_best(page, label): return
            try:
                for fr in page.frames:
                    if fr is page.main_frame: continue
                    el = fr.get_by_text(re.compile(re.escape(label), re.I)).first
                    if el and el.count()>0 and el.is_visible():
                        if _click_attempt(page, el): return
            except Exception: pass
            raise TimeoutError(f"Could not click '{label}'")

        if fn_name.startswith("enter_"):
            label = fn_name[len("enter_"):].replace("_", " ").strip()
            value = args[0] if args else ""
            if _fill_text_like(page, label, value): return
            try:
                for fr in page.frames:
                    if fr is page.main_frame: continue
                    if _fill_text_like(fr, label, value): return
            except Exception: pass
            try:
                tb = page.get_by_role("textbox")
                if tb.count()>0:
                    tb.nth(max(0, tb.count()-1)).fill(value, timeout=_FAST_TIMEOUT); return
            except Exception: pass

        if fn_name.startswith("select_"):
            label = fn_name[len("select_"):].replace("_", " ").strip()
            value = args[0] if args else ""
            if _fast_select_dropdown(page, label, value): return
            try:
                sel = page.get_by_label(re.compile(label, re.I))
                try: sel.select_option(label=value, timeout=_FAST_TIMEOUT); return
                except Exception: pass
                try: sel.select_option(value=value, timeout=_FAST_TIMEOUT); return
                except Exception: pass
            except Exception: pass
            try:
                page.get_by_role("combobox", name=re.compile(label, re.I)).first.click(timeout=_FAST_TIMEOUT)
                page.get_by_role("option", name=re.compile(value, re.I)).first.click(timeout=_FAST_TIMEOUT); return
            except Exception: pass
            try:
                sel = page.locator("select").first
                try: sel.select_option(label=value, timeout=_FAST_TIMEOUT); return
                except Exception: pass
                try: sel.select_option(value=value, timeout=_FAST_TIMEOUT); return
                except Exception: pass
            except Exception: pass

        if fn_name.startswith("radio_"):
            group = fn_name[len("radio_"):].replace("_", " ").strip()
            value = (args[0] if args else "") or ""
            _check_radio(page, group, value); return

        if fn_name.startswith("checkbox_"):
            label = fn_name[len("checkbox_"):].replace("_", " ").strip()
            value = args[0] if args else "check"
            _set_checkbox(page, label, value); return

        if fn_name in ("pick_date", "set_onward_date", "set_return_date"):
            return None
    except Exception as e:
        print(f"[AUTO-STUBS] Fallback failed for {fn_name}: {e!r}")
'''

_CONFTEST_SOURCE = r'''import os, sys, platform, subprocess
from pathlib import Path
import pytest
from playwright.sync_api import sync_playwright

_THIS = Path(__file__).resolve()
_SRC_ROOT = _THIS.parents[1]  # generated_runs/src
if str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))

def _b(v, default=False):
    if v is None: return default
    return str(v).strip().lower() in ("1","true","yes","y","on")

def _ensure_browsers():
    try:
        subprocess.run([sys.executable, "-m", "playwright", "--version"],
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False, text=True)
    except Exception:
        pass
    args = [sys.executable, "-m", "playwright", "install", "chromium"]
    if platform.system() == "Linux": args.append("--with-deps")
    subprocess.run(args, check=False)

def _launch_browser(pw):
    headless_env = os.getenv("HEADLESS")
    if headless_env is not None:
        headless = _b(headless_env, default=True)
    else:
        headless = False  # headed by default so you see the UI
    slow_mo = int(os.getenv("UI_RUNNER_SLOWMO", "0") or "0")
    args = []
    try:
        is_root = hasattr(os, "geteuid") and os.geteuid() == 0
    except Exception:
        is_root = False
    if _b(os.getenv("PLAYWRIGHT_NO_SANDBOX"), default=is_root and platform.system()=="Linux"):
        args.extend(["--no-sandbox","--disable-setuid-sandbox"])

    try:
        browser = pw.chromium.launch(headless=headless, slow_mo=slow_mo, args=args)
        return browser
    except Exception:
        _ensure_browsers()
        browser = pw.chromium.launch(headless=headless, slow_mo=slow_mo, args=args)
        return browser

@pytest.fixture(scope="session")
def _pw():
    _ensure_browsers()
    with sync_playwright() as p:
        yield p

@pytest.fixture(scope="session")
def browser(_pw):
    browser = _launch_browser(_pw)
    try:
        yield browser
    finally:
        try: browser.close()
        except Exception: pass

@pytest.fixture(scope="function")
def page(browser):
    context = browser.new_context(
        viewport={"width": 1280, "height": 900},
        device_scale_factor=1.0,
        is_mobile=False,
        has_touch=False,
        reduced_motion="reduce",
        color_scheme="light",
        accept_downloads=True
    )
    pg = context.new_page()
    pg.set_default_timeout(int(os.getenv("UI_RUNNER_TIMEOUT","20000") or "20000"))
    pg.set_default_navigation_timeout(int(os.getenv("UI_RUNNER_NAV_TIMEOUT","30000") or "30000"))
    try:
        yield pg
    finally:
        try: context.close()
        except Exception: pass
'''

# =============================================================================
# UI runner generator (keeps multiline blocks)
# =============================================================================
def _generate_ui_script_for_test_file(test_path: Path) -> str:
    test_src = test_path.read_text(encoding="utf-8")

    funcs: List[Tuple[str, str]] = []
    lines = test_src.splitlines(True)
    cur_name, cur_body, in_func = None, [], False

    for line in lines:
        m = re.match(r"def (test_[a-zA-Z0-9_]+)\(page\):", line)
        if m:
            if cur_name is not None:
                funcs.append((cur_name, "".join(cur_body)))
            cur_name = m.group(1); cur_body = []; in_func = True; continue
        if in_func:
            cur_body.append(line)
    if cur_name is not None:
        funcs.append((cur_name, "".join(cur_body)))

    import_lines = ["import sys, os, time", "from pathlib import Path"]
    import_lines.append("from playwright.sync_api import sync_playwright")
    import_lines.append("")
    import_lines.append("_THIS = Path(__file__).resolve()")
    import_lines.append("_SRC_ROOT = _THIS.parents[1]")
    import_lines.append("if str(_SRC_ROOT) not in sys.path: sys.path.insert(0, str(_SRC_ROOT))")
    import_lines.append("from pages.auto_stubs import *")
    for py in sorted(PAGES_DIR.glob("*.py")):
        if py.stem in ("__init__", "auto_stubs"): continue
        import_lines.append(f"try:\n    from pages.{py.stem} import *\nexcept Exception:\n    pass")
    import_lines.append("")

    wrappers: List[str] = []
    for fname, fbody in funcs:
        runner = "run_" + fname.replace("test_", "")
        body = textwrap.dedent(fbody).rstrip("\n").splitlines()
        steps = "\n".join(("        " + l) if l.strip() else "" for l in body)
        block = f'''def {runner}():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=(os.getenv("UI_RUNNER_HEADLESS","false").lower()=="true"),
                                    slow_mo=int(os.getenv("UI_RUNNER_SLOWMO","0") or "0"))
        context = browser.new_context()
        page = context.new_page()
{steps}
        linger_after_success(page)
        if os.getenv("UI_RUNNER_AUTOCLOSE","1") == "1":
            context.close(); browser.close()
'''
        wrappers.append(block)

    main_block = "\nif __name__ == '__main__':\n"
    for fname, _ in funcs:
        main_block += f"    run_{fname.replace('test_', '')}()\n"

    m = re.match(r"test_(\d+)\.py$", test_path.name)
    ui_name = f"ui_script_{m.group(1)}.py" if m else "ui_script.py"
    ui_path = TESTS_DIR / ui_name
    ui_path.write_text("\n".join(import_lines) + "\n".join(wrappers) + main_block, encoding="utf-8")
    return str(ui_path)

# =============================================================================
# Page discovery (optional page imports)
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
# Collect called methods & generate stubs
# =============================================================================
CALL_RE_CLICK     = re.compile(r'\b(click_[a-z0-9_]+)\(\s*page\s*\)', re.I)
CALL_RE_ENTER     = re.compile(r'\b(enter_[a-z0-9_]+)\(\s*page\s*,\s*(".*?"|\'.*?\')\s*\)', re.I)
CALL_RE_SELECT    = re.compile(r'\b(select_[a-z0-9_]+)\(\s*page\s*,\s*(".*?"|\'.*?\')\s*\)', re.I)
CALL_RE_RADIO     = re.compile(r'\b(radio_[a-z0-9_]+)\(\s*page\s*,\s*(".*?"|\'.*?\')\s*\)', re.I)
CALL_RE_DATE      = re.compile(r'\b(pick_date|set_onward_date|set_return_date)\(\s*page\s*,\s*(".*?"|\'.*?\')\s*\)', re.I)
CALL_RE_CHECKBOX  = re.compile(r'\b(checkbox_[a-z0-9_]+)\(\s*page\s*,\s*(".*?"|\'.*?\')\s*\)', re.I)

def _collect_called_methods(code: str) -> Set[str]:
    names: Set[str] = set()
    names |= {m.group(1) for m in CALL_RE_CLICK.finditer(code)}
    names |= {m.group(1) for m in CALL_RE_ENTER.finditer(code)}
    names |= {m.group(1) for m in CALL_RE_SELECT.finditer(code)}
    names |= {m.group(1) for m in CALL_RE_RADIO.finditer(code)}
    names |= {m.group(1) for m in CALL_RE_DATE.finditer(code)}
    names |= {m.group(1) for m in CALL_RE_CHECKBOX.finditer(code)}
    return names

def _write_auto_stubs(method_names: Set[str]) -> str:
    PAGES_DIR.mkdir(parents=True, exist_ok=True)
    (PAGES_DIR / "__init__.py").touch()
    stub_file = PAGES_DIR / "auto_stubs.py"

    funcs = []
    for name in sorted(method_names):
        if name in {"click_file_upload", "click_upload", "upload_file"}:
            continue
        if name.startswith("click_"):
            funcs.append(f"def {name}(page):\n    return _fallback_call('{name}', page)\n")
        elif name.startswith(("enter_", "select_", "radio_", "checkbox_")) or name in ("pick_date", "set_onward_date", "set_return_date"):
            funcs.append(f"def {name}(page, value):\n    return _fallback_call('{name}', page, value)\n")
        else:
            funcs.append(f"def {name}(*args, **kwargs):\n    return None\n")

    stub_file.write_text(_AUTO_STUBS_HEADER + "\n".join(funcs), encoding="utf-8")
    return str(stub_file)

def _write_conftest() -> str:
    TESTS_DIR.mkdir(parents=True, exist_ok=True)
    (TESTS_DIR / "__init__.py").touch()
    cf = TESTS_DIR / "conftest.py"
    cf.write_text(_CONFTEST_SOURCE, encoding="utf-8")
    return str(cf)

# =============================================================================
# Codegen driver
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
    site_url: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None)
):
    _ensure_dirs()

    # collect stories
    stories: List[str] = []
    if file:
        content = await file.read()
        name = (file.filename or "").lower()
        if name.endswith((".xlsx", ".xls")):
            xls = pd.ExcelFile(io.BytesIO(content))
            sheet = next((s for s in xls.sheet_names if s.strip().lower() in {"user stories","stories","tests","test cases","scenarios"}), xls.sheet_names[0])
            df = pd.read_excel(xls, sheet_name=sheet)
            col = next((c for c in df.columns if str(c).strip().lower() in {"user story","story","stories","scenario"}), df.columns[0])
            stories = df[col].dropna().astype(str).tolist()
        elif name.endswith(".csv"):
            df = pd.read_csv(io.StringIO(content.decode("utf-8", errors="ignore")))
            col = next((c for c in df.columns if str(c).strip().lower() in {"user story","story","stories","scenario"}), df.columns[0])
            stories = df[col].dropna().astype(str).tolist()
        else:
            txt = content.decode("utf-8", errors="ignore")
            stories = _split_into_stories(txt)
    elif user_story:
        stories = [user_story]
    else:
        raise HTTPException(400, "Either 'user_story' or 'file' must be provided")

    _snapshot_chroma_before()

    code_blocks: List[str] = []
    for story in stories:
        code_blocks.append(generate_test_code_from_methods(story))

    combined = "\n\n".join(code_blocks)

    conftest_path = _write_conftest()
    needed = _collect_called_methods(combined)
    stubs_path = _write_auto_stubs(needed if len(needed) else set())

    test_idx = _next_index()
    test_file = TESTS_DIR / f"test_{test_idx}.py"

    import_lines = ["from pages.auto_stubs import *"]
    for py in sorted(PAGES_DIR.glob("*.py")):
        if py.stem in ("__init__", "auto_stubs"): continue
        import_lines.append(f"from pages.{py.stem} import *  # optional")

    test_file.write_text("\n\n".join(import_lines + [combined]), encoding="utf-8")

    ui_script_path = _generate_ui_script_for_test_file(test_file)

    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    (LOGS_DIR / f"logs_{test_idx}.log").write_text("Generated from user stories.", encoding="utf-8")

    return {
        "results": [{"Prompt": "Generated from user story", "auto_testcase": combined}],
        "test_file": str(test_file),
        "ui_script": str(ui_script_path),
        "log_file": str(LOGS_DIR / f"logs_{test_idx}.log"),
        "stubs_file": stubs_path,
        "conftest_file": str(conftest_path),
        "missing_methods_count": 0,
    }

@router.post("/generate-from-story-json")
def generate_from_story_json(payload: dict = Body(...)):
    story = payload.get("user_story") or payload.get("story")
    if not story:
        raise HTTPException(400, "Provide 'user_story' or 'story'.")
    _ensure_dirs()
    _snapshot_chroma_before()

    code = generate_test_code_from_methods(story)

    conftest_path = _write_conftest()

    needed = _collect_called_methods(code)
    stubs_path = _write_auto_stubs(needed if len(needed) else set())

    test_idx = _next_index()
    test_file = TESTS_DIR / f"test_{test_idx}.py"

    import_lines = ["from pages.auto_stubs import *"]
    for py in sorted(PAGES_DIR.glob("*.py")):
        if py.stem in ("__init__", "auto_stubs"): continue
        import_lines.append(f"from pages.{py.stem} import *  # optional")

    test_file.write_text("\n\n".join(import_lines + [code]), encoding="utf-8")

    ui_script_path = _generate_ui_script_for_test_file(test_file)

    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    (LOGS_DIR / f"logs_{test_idx}.log").write_text("Generated from JSON story.", encoding="utf-8")

    return {
        "status": "ok",
        "file": str(test_file),
        "ui_script": str(ui_script_path),
        "stubs_file": str(stubs_path),
        "conftest_file": str(conftest_path),
        "results": [{
            "Prompt": "Generated POM tests (positive/negative/edge) from user stories",
            "auto_testcase": code,
            "test_file": str(test_file),
            "ui_script": str(ui_script_path),
        }],
        "stories_count": len(_split_into_stories(story)),
        "missing_methods_count": 0,
    }

@router.get("/ping")
def ping():
    return {"ok": True, "router": "generate_user_story"}
