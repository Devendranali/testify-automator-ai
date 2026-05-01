from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass

import ast
import json
import os
import re
import textwrap
import hashlib

import pandas as pd

# Kept for future use (silence linter if configured)
from services.graph_service import read_dependency_graph, get_adjacency_list, find_path  # noqa: F401
from utils.prompt_utils import build_prompt, build_security_prompt, build_accessibility_prompt
from utils.chroma_client import get_collection
from utils.file_utils import generate_unique_name
from utils.match_utils import normalize_page_name
from utils.smart_ai_utils import analyze_test_case_content, get_smartai_src_dir
from services.token_service import log_token_usage
from utils.openai_client import call_openai
from utils.testcase_utils import (
    ensure_unique_display_name,
    generate_case_uuid,
    generate_display_name,
)
from utils.request_context import get_project_context
from database.models import Project, TestCaseMetadata, ImageMetadata, ImageUploadRun
from database.project_storage import DatabaseBackedProjectStorage
from database.session import session_scope, Session
from .projects_api import _ensure_project_structure, get_current_user, get_user_project
from database.models import User
from database.session import get_db
router = APIRouter()
PIPELINE_VERSION = "2026-03-15-prompt-driven-ui-6"


@dataclass(frozen=True)
class StoryStep:
    action: str
    target: str = ""
    value: str = ""
    raw: str = ""
    context: str = ""
    match: str = ""


_BDD_PREFIX_RE = re.compile(r"^(given|when|then|and|but)\b\s*", re.IGNORECASE)
_BULLET_PREFIX_RE = re.compile(r"^(\s*[-*]|\s*\d+[\.)])\s*")
_QUOTED_RE = re.compile(r"[\"']([^\"']+)[\"']")
_TEST_DEF_RE = re.compile(r"^\s*def\s+test_[A-Za-z0-9_]*\s*\(", re.MULTILINE)
_A11Y_DEF_RE = re.compile(r"^\s*def\s+test_a11y_[A-Za-z0-9_]*\s*\(", re.MULTILINE)
_STRAY_EXPLANATORY_RE = re.compile(
    r"^(?:"
    r"in these tests?:?|"
    r"in these test functions\b.*|"
    r"the positive test(?: follows)?\b.*|"
    r"the negative test(?: assumes)?\b.*|"
    r"the edge test(?: involves)?\b.*|"
    r"this code follows the strict priority model\b.*|"
    r".*followed the priority order by using existing pom methods.*|"
    r".*real playwright actions where necessary.*|"
    r".*structured to cover positive,\s*negative,\s*and edge cases.*|"
    r".*user story provided.*test case.*"
    r")$",
    re.IGNORECASE,
)


def _normalized_prose_line(text: str) -> str:
    return _BULLET_PREFIX_RE.sub("", (text or "").strip()).strip()


def _is_stray_explanatory_line(line: str) -> bool:
    normalized = _normalized_prose_line(line)
    if not normalized:
        return False
    return bool(_STRAY_EXPLANATORY_RE.search(normalized))


def _looks_like_python_code_line(line: str) -> bool:
    stripped = (line or "").strip()
    if not stripped:
        return False
    if re.match(
        r"^(def |class |from |import |@|if |elif |else:|for |while |with |try:|except\b|finally:|return\b|pass\b|raise\b|assert\b)",
        stripped,
    ):
        return True
    if re.match(
        r"^(page\.|browser\.|context\.|time\.|expect\(|click_|right_click_|dblclick_|tap_|hover_|fill_|enter_|type_|select_|check_|uncheck_|verify_|assert_|patch_page_with_smartai\b|set_current_page\b|run_allure_case\b|_)",
        stripped,
    ):
        return True
    return bool(re.match(r"^[A-Za-z_][A-Za-z0-9_]*\(", stripped))


def _iter_story_lines(story_text: str) -> list[str]:
    """
    Split story text into logical BDD steps, even if provided as a single line.
    Avoid splitting inside quoted text.
    """
    if not story_text:
        return []
    out: list[str] = []
    for raw in (story_text or "").splitlines():
        line = (raw or "").strip()
        if not line:
            continue
        segments: list[str] = []
        start = 0
        i = 0
        in_quote: Optional[str] = None
        lowered = line.lower()
        tokens = ("given", "when", "then", "and", "but")
        while i < len(line):
            ch = line[i]
            if ch in "\"'":
                if in_quote == ch:
                    in_quote = None
                elif in_quote is None:
                    in_quote = ch
                i += 1
                continue
            if in_quote is None:
                for token in tokens:
                    if lowered.startswith(token, i):
                        before = line[i - 1] if i > 0 else " "
                        after = line[i + len(token)] if i + len(token) < len(line) else " "
                        if (not before.isalnum()) and after.isspace():
                            if i != start:
                                seg = line[start:i].strip()
                                if seg:
                                    segments.append(seg)
                            start = i
                            break
            i += 1
        tail = line[start:].strip()
        if tail:
            segments.append(tail)
        if segments:
            out.extend(segments)
        else:
            out.append(line)
    return out


def _has_test_definition(code: str, require_a11y: bool = False) -> bool:
    if not code:
        return False
    if require_a11y:
        return bool(_A11Y_DEF_RE.search(code))
    return bool(_TEST_DEF_RE.search(code))


def _call_llm_with_retry(
    prompt: str,
    model_name: str,
    require_a11y: bool = False,
    db: Optional[Session] = None,
    project_id: Optional[int] = None,
    feature: str = "ui_generation",
) -> str:
    result = call_openai(
        model=model_name,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=int(os.getenv("AI_MAX_TOKENS", "4096")),
        temperature=float(os.getenv("AI_TEMPERATURE", "0")),
    )
    log_token_usage(
        db=db,
        project_id=project_id,
        feature=feature,
        usage=result.get("usage"),
        model=result.get("model"),
    )

    clean_output = re.sub(
        r"```(?:python)?|^\s*Here is.*?:",
        "",
        (result.get("content") or "").strip(),
        flags=re.MULTILINE,
    ).strip()
    # Remove LLM commentary lines that sometimes sneak into code output.
    clean_output = "\n".join(
        line
        for line in clean_output.splitlines()
        if not _is_stray_explanatory_line(line)
        and not re.search(
            r"^\s*Note:\s|negative test case assumes|Adjust the negative test case",
            line,
            re.IGNORECASE,
        )
    ).strip()

    if _has_test_definition(clean_output, require_a11y=require_a11y):
        return clean_output

    retry_prompt = (
        prompt
        + "\n\nSTRICT OUTPUT REQUIREMENT:\n"
        + "Return ONLY valid Python code with at least one function named def test_....\n"
        + "Do not include any explanations or markdown.\n"
    )
    retry_result = call_openai(
        model=model_name,
        messages=[{"role": "user", "content": retry_prompt}],
        max_tokens=int(os.getenv("AI_MAX_TOKENS", "4096")),
        temperature=0,
    )
    log_token_usage(
        db=db,
        project_id=project_id,
        feature="retry_fix",
        usage=retry_result.get("usage"),
        model=retry_result.get("model"),
    )

    retry_output = re.sub(
        r"```(?:python)?|^\s*Here is.*?:",
        "",
        (retry_result.get("content") or "").strip(),
        flags=re.MULTILINE,
    ).strip()
    retry_output = "\n".join(
        line
        for line in retry_output.splitlines()
        if not _is_stray_explanatory_line(line)
        and not re.search(
            r"^\s*Note:\s|negative test case assumes|Adjust the negative test case",
            line,
            re.IGNORECASE,
        )
    ).strip()
    return retry_output or clean_output


def _stable_hash(payload: str) -> str:
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _normalize_label_for_match(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "")).strip().lower()


def _find_unique_for_label(label: str, records: list[dict]) -> Optional[str]:
    target = _normalize_label_for_match(label)
    if not target:
        return None
    for entry in records or []:
        if not isinstance(entry, dict):
            continue
        unique = str(entry.get("unique_name") or "").strip()
        if not unique:
            continue
        for key in (
            "label_text",
            "text",
            "get_by_text",
            "placeholder",
            "aria_label",
            "title_text",
        ):
            val = entry.get(key)
            if not val:
                continue
            if _normalize_label_for_match(str(val)) == target:
                return unique
    return None


def _inject_calendar_unique_args(code: str, records: list[dict]) -> str:
    if not code or not records:
        return code

    def _rewrite(fn_name: str, text: str) -> str:
        pattern = re.compile(
            rf"{fn_name}\(\s*page\s*,\s*(['\"])(.*?)\1\s*\)",
            re.MULTILINE,
        )

        def repl(match):
            label = match.group(2)
            unique = _find_unique_for_label(label, records)
            if not unique:
                return match.group(0)
            return f"{fn_name}(page, {match.group(1)}{label}{match.group(1)}, \"{unique}\")"

        return pattern.sub(repl, text)

    code = _rewrite("click_calendar_month_header", code)
    code = _rewrite("select_calendar_month", code)
    code = _rewrite("select_calendar_date", code)
    return code


def _expand_icon_alias_tokens(tokens: list[str]) -> list[str]:
    mapping = {
        "mail": ("envelope", "email"),
        "envelope": ("mail", "email"),
        "email": ("mail", "envelope"),
        "bell": ("notification", "notifications"),
        "notification": ("bell", "notifications"),
        "notifications": ("bell", "notification"),
        "profile": ("avatar", "user", "account"),
        "avatar": ("profile", "user", "account"),
        "user": ("profile", "avatar", "account"),
        "account": ("profile", "avatar", "user"),
        "settings": ("gear", "cog"),
        "gear": ("settings", "cog"),
        "cog": ("settings", "gear"),
        "camera": ("photo", "image"),
        "photo": ("camera", "image"),
        "image": ("camera", "photo"),
        "heart": ("like", "favorite"),
        "favorite": ("heart", "star"),
        "bookmark": ("save",),
        "calendar": ("date",),
        "cart": ("shopping", "basket"),
        "shopping": ("cart", "basket"),
        "share": ("send",),
    }
    out: list[str] = []
    for raw in tokens or []:
        token = str(raw or "").strip().lower()
        if len(token) < 3:
            continue
        if token not in out:
            out.append(token)
        if token.endswith("s") and len(token) > 4:
            singular = token[:-1]
            if singular not in out:
                out.append(singular)
        for alias in mapping.get(token, ()):
            if alias not in out:
                out.append(alias)
    return out


def _tokenize_story(text: str) -> list[str]:
    raw = re.sub(r"[^a-zA-Z0-9]+", " ", (text or "").lower()).strip()
    if not raw:
        return []
    tokens = [t for t in raw.split() if len(t) >= 3]
    return list(dict.fromkeys(_expand_icon_alias_tokens(tokens)))


def _expand_input_alias_tokens(tokens: list[str]) -> list[str]:
    mapping = {
        "username": ("user", "name", "userid", "user_id", "login"),
        "userid": ("user", "username", "user_id", "login"),
        "user_id": ("user", "username", "userid", "login"),
        "loginid": ("login", "user", "username", "userid", "user_id"),
        "login": ("username", "userid", "user_id", "user"),
        "pwd": ("password", "pass"),
        "pass": ("password", "pwd"),
        "password": ("pass", "pwd"),
    }
    out: list[str] = []
    for raw in tokens or []:
        token = str(raw or "").strip().lower()
        if not token:
            continue
        if token not in out:
            out.append(token)
        for alias in mapping.get(token, ()):
            if alias not in out:
                out.append(alias)
    token_set = set(out)
    if "user" in token_set and "id" in token_set:
        for alias in ("username", "userid", "user_id", "login"):
            if alias not in out:
                out.append(alias)
    if "login" in token_set and "id" in token_set:
        for alias in ("username", "userid", "user_id", "user"):
            if alias not in out:
                out.append(alias)
    if "user" in token_set and "name" in token_set:
        if "username" not in out:
            out.append("username")
    return out


def _tokenize_label(label: str) -> list[str]:
    raw = re.sub(r"[^a-zA-Z0-9]+", " ", (label or "").lower()).strip()
    if not raw:
        return []
    tokens = [t for t in raw.split() if len(t) >= 3]
    expanded = []
    for t in tokens:
        expanded.append(t)
        if t.endswith("s") and len(t) > 3:
            expanded.append(t[:-1])
    return list(dict.fromkeys(expanded))


def _match_story_to_graph_nodes(story: str, graph: dict) -> tuple[list[str], list[str]]:
    """Return ordered matched node ids and unmatched tokens."""
    nodes = graph.get("nodes") or []
    edges = graph.get("edges") or []
    start_id = graph.get("start_screen_id")

    node_map = {}
    for node in nodes:
        node_id = node.get("id")
        name = node.get("name") or node_id
        if not node_id:
            continue
        node_map[node_id] = {
            "name": name,
            "tokens": _tokenize_label(name),
        }

    story_tokens = _tokenize_story(story)
    matched_ids = set()
    token_hits = {t: False for t in story_tokens}
    for node_id, meta in node_map.items():
        overlap = [t for t in story_tokens if t in meta["tokens"]]
        if overlap:
            matched_ids.add(node_id)
            for t in overlap:
                token_hits[t] = True

    # Build flow order from KG edges (BFS from start)
    adjacency = {}
    for edge in edges:
        src = edge.get("from") or edge.get("source")
        tgt = edge.get("to") or edge.get("target")
        if not src or not tgt:
            continue
        adjacency.setdefault(src, []).append(tgt)

    ordered = []
    seen = set()
    if start_id and start_id in node_map:
        queue = [start_id]
        while queue:
            current = queue.pop(0)
            if current in seen:
                continue
            seen.add(current)
            if current in matched_ids:
                ordered.append(current)
            for nxt in adjacency.get(current, []):
                if nxt not in seen:
                    queue.append(nxt)

    if not ordered:
        ordered = list(matched_ids)

    unmatched = [t for t, hit in token_hits.items() if not hit]
    return ordered, unmatched


def _normalize_method_map(method_map: dict) -> dict:
    normalized: dict[str, list[str]] = {}
    for key, methods in (method_map or {}).items():
        if methods is None:
            normalized[str(key)] = []
        elif isinstance(methods, list):
            normalized[str(key)] = [str(m) for m in methods]
        else:
            normalized[str(key)] = [str(m) for m in methods]
    return normalized


def _generation_cache_dir(run_folder: Path) -> Path:
    cache_dir = run_folder / "logs" / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def _generation_cache_key(
    *,
    user_story: str,
    test_type: str,
    site_url: str,
    method_map: dict,
    page_names: list[str],
    prompt: str,
    model_name: str,
) -> str:
    normalized_methods = _normalize_method_map(method_map)
    payload = {
        "pipeline_version": PIPELINE_VERSION,
        "story": user_story or "",
        "test_type": test_type or "",
        "site_url": site_url or "",
        "model": model_name or "",
        "page_names": page_names or [],
        "method_map": normalized_methods,
        "prompt_hash": _stable_hash(prompt or ""),
    }
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=True)
    return _stable_hash(raw)


def _load_cached_generation(cache_dir: Path, cache_key: str) -> Optional[str]:
    cache_file = cache_dir / f"{cache_key}.json"
    if not cache_file.exists():
        return None
    try:
        payload = json.loads(cache_file.read_text(encoding="utf-8"))
    except Exception:
        return None
    code = payload.get("code")
    return code if isinstance(code, str) and code.strip() else None


def _store_cached_generation(
    cache_dir: Path,
    cache_key: str,
    *,
    code: str,
    meta: dict,
) -> None:
    cache_file = cache_dir / f"{cache_key}.json"
    payload = {
        "meta": meta,
        "code": code,
    }
    try:
        cache_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    except Exception:
        pass

def _extract_first_url(text: str) -> str:
    match = re.search(r"https?://[^\s\"'<>]+", text or "")
    if not match:
        return ""
    return match.group(0).rstrip(").,")


def _format_markers_as_pytest_decorators(markers: List[str]) -> List[str]:
    """
    Convert marker strings into valid pytest decorator lines.

    Markers may contain whitespace or special characters; pytest marker attributes
    must be valid Python identifiers, so we sanitize them deterministically.
    """
    decorators: List[str] = []
    for marker in markers or []:
        raw = str(marker or "").strip()
        if not raw:
            continue
        safe = re.sub(r"[^a-zA-Z0-9_]+", "_", raw).strip("_")
        if not safe:
            continue
        if safe[0].isdigit():
            safe = f"m_{safe}"
        decorators.append(f"@pytest.mark.{safe}")
    # Deduplicate while preserving order.
    return list(dict.fromkeys(decorators))


def _story_header_line(story: str) -> str:
    cleaned = " ".join((story or "").split())
    return f"# USER_STORY: {cleaned}"


def _extract_first_test_function_block(code: str, target_name: Optional[str] = None) -> Optional[str]:
    if not code or not code.strip():
        return None
    try:
        tree = ast.parse(code)
    except Exception:
        return None

    func_node = None
    for node in tree.body:
        if not isinstance(node, ast.FunctionDef):
            continue
        if not node.name.startswith("test_"):
            continue
        if target_name and node.name != target_name:
            continue
        func_node = node
        break

    if func_node is None:
        return None

    start_line = func_node.lineno
    for deco in func_node.decorator_list:
        if getattr(deco, "lineno", None):
            start_line = min(start_line, deco.lineno)
    end_line = getattr(func_node, "end_lineno", None)
    if not end_line:
        return None

    lines = code.splitlines()
    return "\n".join(lines[start_line - 1 : end_line]).rstrip()


def _apply_markers_to_function_block(
    func_block: str,
    test_name: str,
    project_id_val: int,
    db: Session,
    user_story: Optional[str] = None,
    test_type: Optional[str] = None,
    fallback_used: bool = False,
) -> str:
    analysis = analyze_test_case_content(func_block)
    analyzed_tags = analysis.get("tags") or []
    analyzed_priority = analysis.get("priority") or "Low"

    record = None
    existing_markers: List[str] = []
    existing_tags: List[str] = []
    if project_id_val and test_name:
        try:
            record = (
                db.query(TestCaseMetadata)
                .filter(
                    TestCaseMetadata.project_id == project_id_val,
                    TestCaseMetadata.test_name == test_name,
                )
                .first()
            )
            if record:
                if isinstance(record.markers, list):
                    existing_markers = record.markers
                if isinstance(record.tags, list):
                    existing_tags = record.tags
        except Exception as e:
            print(f"Database query for metadata failed: {e}")

    combined_tags = list(dict.fromkeys(existing_tags + analyzed_tags))
    combined_markers = list(dict.fromkeys(existing_markers + combined_tags))
    if fallback_used and "fallback_used" not in combined_markers:
        combined_markers.append("fallback_used")

    if project_id_val and test_name:
        if record:
            # Backfill required identifiers if older rows exist (or partial inserts happened).
            if not getattr(record, "case_uuid", None):
                record.case_uuid = generate_case_uuid()
            if not getattr(record, "display_name", None):
                base_display = generate_display_name("ui", test_name, record.case_uuid)
                record.display_name = ensure_unique_display_name(db, project_id_val, base_display)
            if record.user_story is None:
                record.user_story = ""
            if user_story:
                record.user_story = user_story
            if record.auto_testcase is None:
                record.auto_testcase = ""
            if func_block:
                record.auto_testcase = func_block
            if record.test_type is None:
                record.test_type = test_type or "ui"
            elif test_type:
                record.test_type = test_type
            record.markers = combined_markers
            record.tags = combined_tags
            record.priority = analyzed_priority
        else:
            case_uuid = generate_case_uuid()
            base_display = generate_display_name(test_type or "ui", user_story or test_name, case_uuid)
            display_name = ensure_unique_display_name(db, project_id_val, base_display)
            record = TestCaseMetadata(
                project_id=project_id_val,
                case_uuid=case_uuid,
                display_name=display_name,
                test_name=test_name,
                user_story=user_story or "",
                auto_testcase=func_block or "",
                test_type=test_type or "ui",
                markers=combined_markers,
                tags=combined_tags,
                priority=analyzed_priority,
            )
            db.add(record)

    marker_decorators = _format_markers_as_pytest_decorators(combined_markers)
    updated_func_block = func_block.rstrip() + "\n"
    if marker_decorators:
        return f"{chr(10).join(marker_decorators)}\n{updated_func_block}"
    return updated_func_block


_SCROLL_RUNTIME_RE = re.compile(
    r'^(?P<indent>\s*)raise RuntimeError\("Missing POM method for (?P<action>scroll[^"]*)"\)\s*$',
    re.IGNORECASE,
)
_MISSING_POM_RE = re.compile(
    r'^(?P<indent>\s*)raise RuntimeError\("Missing POM method for (?P<action>[^"]+)"\)\s*$'
)


def inject_missing_pom_fallbacks(code: str, story_text: str) -> tuple[str, bool]:
    """
    Replace Missing-POM RuntimeErrors with direct Playwright actions.
    Currently supports click actions with quoted labels in the error text.
    """
    if not code:
        return code, False
    out_lines: list[str] = []
    fallback_used = False
    for line in code.splitlines(True):
        match = _MISSING_POM_RE.match(line.rstrip("\n"))
        if not match:
            out_lines.append(line)
            continue
        indent = match.group("indent") or ""
        action_text = (match.group("action") or "").lower()
        label = ""
        quoted = _extract_quoted_strings(match.group("action") or "")
        if quoted:
            label = (quoted[0] or "").strip()

        if any(k in action_text for k in ("right click", "right-click", "context click", "context-click", "context menu")) and label:
            out_lines.append(
                f"{indent}page.get_by_role(\"button\", name={json.dumps(label)}, exact=True).first.click(button=\"right\")\n"
            )
            fallback_used = True
            continue

        if any(k in action_text for k in ("double click", "double-click", "dblclick", "doubleclick")) and label:
            out_lines.append(
                f"{indent}page.get_by_role(\"button\", name={json.dumps(label)}, exact=True).first.dblclick()\n"
            )
            fallback_used = True
            continue

        if "click" in action_text and label and not any(k in action_text for k in ("icon", "avatar")):
            # Prefer button role for click actions, fallback to text.
            out_lines.append(
                f"{indent}page.get_by_role(\"button\", name={json.dumps(label)}, exact=True).first.click()\n"
            )
            fallback_used = True
            continue

        if "icon" in action_text or "avatar" in action_text:
            raw_action = match.group("action") or ""
            icon_label = ""
            if label:
                icon_label = label
            else:
                m = re.search(r"([A-Za-z0-9 _\\-]+)\\s+icon", raw_action, re.IGNORECASE)
                if m:
                    icon_label = (m.group(1) or "").strip()
                if not icon_label and "profile" in raw_action.lower():
                    icon_label = "profile"
                if not icon_label and "avatar" in raw_action.lower():
                    icon_label = "profile"
            if icon_label:
                icon_label = re.sub(
                    r"^(clicking|click|tap|tapping|press|pressing)\\s+(the\\s+)?",
                    "",
                    icon_label,
                    flags=re.IGNORECASE,
                ).strip()
            if icon_label:
                out_lines.append(f"{indent}click_icon(page, {json.dumps(icon_label)})\n")
                fallback_used = True
                continue

        if any(k in action_text for k in ("enter", "fill", "type", "input")):
            field = quoted[0] if quoted else ""
            value = quoted[1] if len(quoted) > 1 else (quoted[0] if quoted else "")
            target = field or "Field"
            out_lines.append(
                f"{indent}_smart_fill(page, {json.dumps(target)}, {json.dumps(value)})\n"
            )
            fallback_used = True
            continue

        if any(k in action_text for k in ("select", "choose", "pick")):
            field = quoted[0] if quoted else ""
            value = quoted[1] if len(quoted) > 1 else (quoted[0] if quoted else "")
            target = field or "Field"
            out_lines.append(
                f"{indent}page.get_by_label({json.dumps(target)}, exact=False).select_option({json.dumps(value)})\n"
            )
            fallback_used = True
            continue

        # If we can't infer a safe fallback, keep the original error.
        out_lines.append(line)
    return "".join(out_lines), fallback_used


def _resolve_project_test_path(src_dir: Path, relative_path: str) -> Path:
    if not relative_path:
        raise HTTPException(status_code=400, detail="test_file_path is required")
    raw = Path(str(relative_path))
    if raw.is_absolute():
        try:
            raw = raw.relative_to(src_dir)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid test_file_path")
    if raw.parts and raw.parts[0].lower() == "tests":
        raw = Path(*raw.parts[1:])
    candidate = (src_dir / "tests" / raw).resolve()
    tests_root = (src_dir / "tests").resolve()
    if not str(candidate).startswith(str(tests_root)):
        raise HTTPException(status_code=403, detail="test_file_path must be within tests directory")
    return candidate


def _resolve_category_from_test_path(test_path: Path) -> str:
    parent = test_path.parent.name.lower()
    if parent == "ui_scripts":
        return "ui"
    if parent == "security_tests":
        return "security"
    if parent == "accessibility_tests":
        return "accessibility"
    return "ui"


def _extract_test_function_names(content: str) -> list[str]:
    if not content:
        return []
    names = []
    pattern = re.compile(r"^\s*def\s+(test_[A-Za-z0-9_]+)\s*\(", re.MULTILINE)
    for match in pattern.finditer(content):
        names.append(match.group(1))
    return names


def _runner_name_from_test_path(test_path: Path, category: str, story: str) -> str:
    stem = test_path.stem
    if stem.startswith("test_"):
        stem = stem.replace("test_", "", 1)
    prefix = "ui_script_" if category == "ui" else f"{category}_script_"
    return f"{prefix}{stem}.py"


def _choose_submit_method(method_map: dict) -> Optional[str]:
    if not method_map:
        return None
    candidates = (
        "click_add_",
        "click_save",
        "click_submit",
        "click_create",
        "click_confirm",
    )
    for methods in method_map.values():
        for method_def in methods or []:
            name = method_def.split("(", 1)[0].replace("def ", "").strip()
            if not name:
                continue
            for prefix in candidates:
                if name.startswith(prefix):
                    return name
    return None


def _improve_negative_edge_scenario(func_block: str, submit_method: Optional[str]) -> str:
    if not func_block:
        return func_block

    lowered = func_block.lower()
    scenario = "positive"
    if "_negative" in lowered:
        scenario = "negative"
    elif "_edge" in lowered:
        scenario = "edge"

    def _replacement_value(method_name: str) -> str:
        name = (method_name or "").lower()
        if scenario == "negative":
            if "email" in name:
                return "invalid-email"
            if any(token in name for token in ("mobile", "phone", "contact")):
                return "123"
            if "age" in name:
                return "-1"
            if "cvv" in name:
                return "12"
            if "card" in name and "name" not in name:
                return "1234"
            if "name" in name:
                return "!"
            return "INVALID"
        if scenario == "edge":
            if "email" in name:
                return "edge.case+very.long@example.com"
            if any(token in name for token in ("mobile", "phone", "contact")):
                return "9999999999"
            if "age" in name:
                return "150"
            if "cvv" in name:
                return "999"
            if "name" in name:
                return "A" * 255
            return "EDGE_VALUE"
        return ""

    def _replace_blank_arg(match: re.Match) -> str:
        indent, method_name, quote = match.groups()
        replacement = _replacement_value(method_name)
        if not replacement:
            return match.group(0)
        return f'{indent}{method_name}(page, "{replacement}")'

    func_block = re.sub(
        r'^(\s*)([a-zA-Z_][a-zA-Z0-9_]*)\(page,\s*(["\'])\s*\3\s*\)',
        _replace_blank_arg,
        func_block,
        flags=re.MULTILINE,
    )
    return func_block


# ----------------------------------------------------------------------
# Merge helpers for incremental metadata updates
# ----------------------------------------------------------------------
def _is_blank_value(value) -> bool:
    if value is None:
        return True
    if isinstance(value, bool):
        return False
    if isinstance(value, str):
        stripped = value.strip().lower()
        return stripped == "" or stripped in {"[]", "{}"}
    if isinstance(value, (list, tuple, set, dict)):
        return len(value) == 0
    return False


def _record_identity(record: dict) -> str | None:
    if not isinstance(record, dict):
        return None
    page = (record.get("page_name") or "").strip().lower()
    intent = (record.get("intent") or "").strip().lower()
    ocr_type = (record.get("ocr_type") or "").strip().lower()
    if intent or ocr_type:
        return f"intent:{page}|{intent}|{ocr_type}"
    for key in ("ocr_id", "id", "unique_name", "element_id"):
        value = record.get(key)
        if isinstance(value, str) and value.strip():
            return f"{key}:{value.strip().lower()}"
    label = (record.get("label_text") or "").strip().lower()
    if any((label, intent, ocr_type)):
        return f"fallback:{label}|{intent}|{ocr_type}"
    bbox = record.get("bbox")
    if isinstance(bbox, str) and bbox.strip():
        return f"bbox:{bbox.strip().lower()}"
    return None


def _should_replace(old_value, new_value) -> bool:
    if isinstance(new_value, bool):
        return new_value and not bool(old_value)
    if _is_blank_value(new_value):
        return False
    return old_value is None or _is_blank_value(old_value)


def _merge_record(existing: dict, incoming: dict) -> dict:
    merged = dict(existing or {})
    prefer_new = {"label_text", "get_by_text", "placeholder", "unique_name"}
    for key, value in (incoming or {}).items():
        if key in prefer_new:
            if not _is_blank_value(value):
                merged[key] = value
            continue
        if key not in merged or _should_replace(merged.get(key), value):
            merged[key] = value
    return merged


def _normalize_metadata_records(records: list[dict] | None) -> list[dict]:
    normalized: list[dict] = []
    for record in records or []:
        flat_record = _normalize_chroma_meta(record)
        if isinstance(flat_record, dict) and flat_record:
            normalized.append(flat_record)
    return normalized


def _merge_metadata_records(existing_records: list[dict], new_records: list[dict]) -> list[dict]:
    """
    Merge records keyed by identity. Existing entries for pages present in the new set
    that are not in the new identities are dropped (authoritative replacement per page).
    Other pages are preserved.
    """
    existing_records = _normalize_metadata_records(existing_records)
    new_records = _normalize_metadata_records(new_records)
    merged: dict[str, dict] = {}
    order: list[str] = []
    counter = 0

    # Identify pages covered by this new snapshot
    new_pages = {
        normalize_page_name((r or {}).get("page_name") or "")
        for r in (new_records or [])
        if isinstance(r, dict)
    }
    new_identities = {_record_identity(r) for r in (new_records or [])}

    def _store(key: str, record: dict):
        if key not in order:
            order.append(key)
        merged[key] = dict(record or {})

    for record in existing_records or []:
        key = _record_identity(record)
        page = normalize_page_name((record or {}).get("page_name") or "")
        if page in new_pages:
            # Only keep existing entry if it is also present in the new set
            if key and key in new_identities:
                _store(key, record)
            # else drop it
        else:
            if not key:
                key = f"existing-{counter}"
                counter += 1
            _store(key, record)

    for record in new_records or []:
        key = _record_identity(record)
        if not key:
            key = f"new-{counter}"
            counter += 1
        if key in merged:
            merged[key] = _merge_record(merged[key], record)
        else:
            _store(key, record)

    return [merged[k] for k in order if k in merged]


def _latest_upload_snapshot(project_id: int) -> list[dict]:
    if not project_id:
        return []
    with session_scope() as db:
        latest_run = (
            db.query(ImageUploadRun)
            .filter(ImageUploadRun.project_id == project_id)
            .order_by(ImageUploadRun.created_at.desc())
            .first()
        )
        if not latest_run or not isinstance(latest_run.results, list):
            return []
        metadata_ids = [
            item.get("metadata_id")
            for item in latest_run.results
            if isinstance(item, dict) and item.get("metadata_id")
        ]
        if not metadata_ids:
            return []
        records = (
            db.query(ImageMetadata)
            .filter(ImageMetadata.project_id == project_id, ImageMetadata.id.in_(metadata_ids))
            .all()
        )
        payload: list[dict] = []
        for record in records:
            if isinstance(record.metadata_json, list):
                payload.extend([m for m in record.metadata_json if isinstance(m, dict)])
        return payload


# ----------------------------------------------------------------------
# Page selection + code normalization helpers
# ----------------------------------------------------------------------
def _select_story_pages(user_story: str, method_map_full: dict, max_pages: int = 5) -> list[str]:
    story_text = (user_story or "").lower()
    if not story_text:
        return list(method_map_full.keys())
    scored: list[tuple[int, str]] = []
    required_pages: dict[str, int] = {}
    for page, methods in method_map_full.items():
        score = 0
        page_tokens = [t for t in re.split(r"[_\W]+", page.lower()) if len(t) >= 3]
        if any(token in story_text for token in page_tokens):
            required_pages[page] = max(required_pages.get(page, 0), 1)
        for method in methods or []:
            name = method.split("(")[0].replace("def ", "").strip()
            base = name
            for prefix in ("enter_", "fill_", "select_", "click_", "right_click_", "dblclick_", "verify_", "assert_"):
                if base.startswith(prefix):
                    base = base[len(prefix) :]
                    break
            tokens = [t for t in re.split(r"[_\W]+", base) if len(t) >= 3]
            for token in tokens:
                if token in story_text:
                    score += 1
            if any(token in story_text for token in tokens):
                required_pages[page] = max(required_pages.get(page, 0), 1)
        if score:
            scored.append((score, page))
    if not scored:
        return list(method_map_full.keys())
    scored.sort(key=lambda item: item[0], reverse=True)
    max_score = scored[0][0]
    threshold = max_score * 0.3
    selected = [page for score, page in scored if score >= threshold]
    for _, page in scored:
        if page in required_pages and page not in selected:
            selected.append(page)
    if not selected:
        return [scored[0][1]]
    if len(selected) > max_pages:
        required = [page for page in selected if page in required_pages]
        extras = [page for page in selected if page not in required]
        selected = required + extras[: max(0, max_pages - len(required))]
    return selected


def _trim_method_map_for_prompt(
    story: str,
    method_map: dict,
    *,
    max_methods_per_page: Optional[int] = None,
    max_total_methods: Optional[int] = None,
) -> dict:
    """
    Reduce method lists to avoid overlong prompts.
    Prioritizes methods whose names match story tokens.
    """
    if not method_map:
        return {}
    if max_methods_per_page is None:
        max_methods_per_page = int(os.getenv("AI_MAX_METHODS_PER_PAGE", "200"))
    if max_total_methods is None:
        max_total_methods = int(os.getenv("AI_MAX_METHODS_TOTAL", "1000"))

    story_tokens = _tokenize_story(story)

    trimmed: dict[str, list[str]] = {}
    total = 0
    for page, methods in method_map.items():
        if not isinstance(methods, list):
            methods = list(methods or [])
        if max_methods_per_page and max_methods_per_page > 0:
            matched: list[str] = []
            unmatched: list[str] = []
            for m in methods:
                name = str(m).split("(", 1)[0].replace("def ", "").strip().lower()
                if any(t in name for t in story_tokens):
                    matched.append(m)
                else:
                    unmatched.append(m)
            methods = matched + unmatched
            methods = methods[:max_methods_per_page]
        if max_total_methods and max_total_methods > 0:
            if total >= max_total_methods:
                trimmed[page] = []
                continue
            remaining = max_total_methods - total
            methods = methods[:remaining]
        trimmed[page] = methods
        total += len(methods)
    return trimmed


def _extract_method_name(signature: str) -> str:
    return signature.split("(")[0].replace("def ", "").strip()


def _method_tokens(method_name: str) -> list[str]:
    base = method_name
    for prefix in ("enter_", "fill_", "select_", "click_", "right_click_", "dblclick_", "verify_", "assert_"):
        if base.startswith(prefix):
            base = base[len(prefix) :]
            break
    tokens = [t for t in re.split(r"[_\W]+", base.lower()) if len(t) >= 3]
    return list(dict.fromkeys(_expand_icon_alias_tokens(tokens)))


def _infer_value_for_method(method_name: str, story_text: str) -> Optional[str]:
    tokens = _method_tokens(method_name)
    if not tokens:
        return None
    for line in (story_text or "").splitlines():
        lower = line.lower()
        if any(token in lower for token in tokens):
            match = re.search(r"\"([^\"]+)\"", line)
            if match:
                return _normalize_inferred_value(method_name, match.group(1))
    return None


def _normalize_inferred_value(method_name: str, value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    raw = str(value)
    name = (method_name or "").lower()
    tokens = set(_method_tokens(method_name))

    def _has(*keys: str) -> bool:
        for k in keys:
            if k in name or k in tokens:
                return True
        return False

    def _looks_email(v: str) -> bool:
        return bool(re.match(r"^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$", v))

    def _is_digits(v: str) -> bool:
        return bool(re.fullmatch(r"\\d+", v))

    if _has("id", "code", "customer", "account", "trade", "userid", "user_id"):
        if not _is_digits(raw):
            return "123456"

    if _has("phone", "mobile", "tel"):
        if not _is_digits(raw):
            return "9876543210"

    if _has("otp", "pin"):
        if not _is_digits(raw):
            return "123456"

    if _has("password", "pass"):
        if _looks_email(raw) or len(raw) < 8:
            return "P@ssw0rd123"

    if _has("email", "mail"):
        if not _looks_email(raw):
            return "john.doe@example.com"

    return raw


def _best_method_for_step(step_text: str, allowed_methods: list[str], desired_prefix: str) -> Optional[str]:
    tokens = _expand_icon_alias_tokens([t for t in re.split(r"[_\W]+", step_text.lower()) if len(t) >= 3])
    best_score = 0
    best_method = None
    for method in allowed_methods:
        if not method.startswith(desired_prefix):
            continue
        method_tokens = _method_tokens(method)
        score = sum(1 for t in method_tokens if t in tokens)
        if score > best_score:
            best_score = score
            best_method = method
    return best_method


def _best_input_method_for_step(step_text: str, allowed_methods: list[str]) -> Optional[str]:
    for prefix in ("enter_", "fill_", "type_"):
        method = _best_method_for_step(step_text, allowed_methods, prefix)
        if method:
            return method
    return None


def _extract_click_steps_from_story(story_text: str, allowed_methods: list[str]) -> list[str]:
    if not story_text:
        return []
    steps: list[str] = []
    click_re = re.compile(r'click(?:ed)?(?: the)?\s+"([^"]+)"', re.IGNORECASE)
    for line in story_text.splitlines():
        for match in click_re.finditer(line):
            label = match.group(1).strip()
            if not label:
                continue
            method = _best_method_for_step(label, allowed_methods, "click_")
            if not method:
                method = _best_method_for_step(line, allowed_methods, "click_")
            if method and method not in steps:
                steps.append(method)
    return steps


def _pick_submit_method(allowed_methods: list[str], story_text: str) -> Optional[str]:
    click_methods = [m for m in allowed_methods if m.startswith("click_")]
    if not click_methods:
        return None
    has_add = any("add_customer" in m for m in click_methods)
    has_create = any("create_customer" in m for m in click_methods)
    if has_add and has_create:
        return next((m for m in click_methods if "add_customer" in m), None)
    # Prefer obvious submit/save/add names if present
    for token in ("submit", "save", "add", "confirm", "create"):
        for m in click_methods:
            if token in m:
                return m
    # Fallback to last click step from story
    click_steps = _extract_click_steps_from_story(story_text, allowed_methods)
    return click_steps[-1] if click_steps else click_methods[-1]


def _inject_security_navigation_and_submit(code: str, method_map: dict, story_text: str) -> str:
    allowed_methods: list[str] = []
    for methods in (method_map or {}).values():
        for method in methods or []:
            allowed_methods.append(_extract_method_name(method))

    nav_steps = _extract_click_steps_from_story(story_text, allowed_methods)
    submit_method = _pick_submit_method(allowed_methods, story_text)

    if not nav_steps and not submit_method:
        return code

    lines = code.splitlines(True)
    out: list[str] = []
    in_func = False
    func_lines: list[str] = []
    func_indent = ""

    def _flush_func():
        nonlocal func_lines
        if not func_lines:
            return
        out.extend(_process_func_block(func_lines))
        func_lines = []

    def _process_func_block(block: list[str]) -> list[str]:
        text = "".join(block)
        missing_nav = [
            m
            for m in nav_steps
            if not re.search(rf"^\s*{re.escape(m)}\(\s*page", text, re.MULTILINE)
        ]
        injected = []
        inserted_nav = False
        for line in block:
            injected.append(line)
            if (not inserted_nav) and re.search(r"\bpage\.goto\(", line):
                indent = re.match(r"^(\s*)", line).group(1)
                for m in missing_nav:
                    injected.append(f"{indent}{m}(page)\n")
                inserted_nav = True

        if submit_method:
            injected = _inject_submit_in_loop(injected, submit_method)
        return injected

    def _inject_submit_in_loop(block: list[str], submit: str) -> list[str]:
        result: list[str] = []
        i = 0
        while i < len(block):
            line = block[i]
            result.append(line)
            loop_match = re.match(r"^(\s*)for\s+\w+\s+in\s+payloads\s*:\s*$", line)
            if not loop_match:
                i += 1
                continue
            loop_indent = loop_match.group(1)
            body_indent = None
            body_lines: list[str] = []
            j = i + 1
            while j < len(block):
                next_line = block[j]
                if body_indent is None:
                    if next_line.strip() == "":
                        body_lines.append(next_line)
                        j += 1
                        continue
                    body_indent = re.match(r"^(\s*)", next_line).group(1)
                if re.match(rf"^{re.escape(loop_indent)}\S", next_line):
                    break
                body_lines.append(next_line)
                j += 1

            body_text = "".join(body_lines)
            if not re.search(rf"^\s*{re.escape(submit)}\(\s*page", body_text, re.MULTILINE):
                if body_indent is None:
                    body_indent = loop_indent + "    "
                body_lines.append(f"{body_indent}{submit}(page)\n")
            result.extend(body_lines)
            i = j
            continue
        return result

    for line in lines:
        if re.match(r"^def\s+[A-Za-z0-9_]+\s*\(", line):
            _flush_func()
            in_func = True
            func_indent = re.match(r"^(\s*)", line).group(1)
            func_lines.append(line)
            continue
        if in_func:
            if line.strip() == "" and func_indent == "":
                func_lines.append(line)
            else:
                func_lines.append(line)
            continue
        out.append(line)
    _flush_func()
    return "".join(out)


def _sanitize_security_numeric_fields(code: str, method_map: dict) -> str:
    """
    Avoid injecting non-numeric payloads into number-only fields.
    """
    allowed_methods: list[str] = []
    for methods in (method_map or {}).values():
        for method in methods or []:
            allowed_methods.append(_extract_method_name(method))

    numeric_markers = ("income", "deposit", "amount", "balance", "number")
    numeric_methods = [m for m in allowed_methods if m.startswith("enter_") and any(k in m for k in numeric_markers)]
    if not numeric_methods:
        return code

    lines = code.splitlines(True)
    out: list[str] = []
    for line in lines:
        loop_match = re.match(r"^(\s*)for\s+\w+\s+in\s+payloads\s*:\s*$", line)
        out.append(line)
        if loop_match:
            indent = loop_match.group(1) + "    "
            out.append(f'{indent}numeric_payload = "123"\n')
        else:
            for m in numeric_methods:
                line = re.sub(
                    rf"^(\s*){re.escape(m)}\(\s*page\s*,\s*payload\s*\)\s*$",
                    rf"\1{m}(page, numeric_payload)",
                    line,
                )
            out[-1] = line
    return "".join(out)


def _split_inline_calls(code: str) -> str:
    """
    Ensure each helper call is on its own line.
    """
    out: list[str] = []
    call_prefix = r"(?:enter_|fill_|select_|click_|right_click_|verify_|assert_|type_|press_|upload_|hover_|focus_|dblclick_|toggle_|check_|uncheck_|goto_|wait_|page\.|expect\()"
    for line in code.splitlines(True):
        indent = re.match(r"^(\s*)", line).group(1)
        updated = line
        updated = re.sub(rf"\)\s+(?={call_prefix})", f")\n{indent}", updated)
        out.append(updated)
    return "".join(out)


def _remove_verification_lines(code: str) -> str:
    """
    Remove verification/assertion calls from generated tests.
    Targets verify_*/assert_* helpers and Playwright expect(...).to_* lines.
    """
    if not code:
        return code
    out_lines: list[str] = []
    verify_re = re.compile(r"^\s*(verify_|assert_)[A-Za-z0-9_]*\s*\(")
    expect_re = re.compile(r"^\s*expect\(.+\)\.to_[A-Za-z0-9_]+\(.+\)\s*$")
    for line in code.splitlines(True):
        if verify_re.match(line.strip()):
            continue
        if expect_re.match(line.strip()):
            continue
        out_lines.append(line)
    return "".join(out_lines)

def _normalize_expect_get_by_text(code: str) -> str:
    """
    Make expect(get_by_text(...)) strict-safe by adding exact=True and .first.
    """
    if not code:
        return code
    pattern = re.compile(
        r"expect\(\s*page\.get_by_text\(\s*(?P<q>['\"])(?P<text>.+?)(?P=q)\s*\)\s*\)\.to_be_visible\(\)\s*$"
    )
    out_lines: list[str] = []
    for line in code.splitlines(True):
        m = pattern.match(line.strip())
        if not m:
            out_lines.append(line)
            continue
        indent = re.match(r"^(\s*)", line).group(1)
        text = m.group("text")
        out_lines.append(
            f'{indent}expect(page.get_by_text("{text}", exact=True).first).to_be_visible()\n'
        )
    return "".join(out_lines)

def _normalize_generated_code(
    code: str,
    method_map: dict,
    story_text: str,
    steps: Optional[list[StoryStep]] = None,
    full_method_map: Optional[dict] = None,
) -> str:
    """
    Post-fix common LLM misses:
    - If it wrote '# Skipped step due to missing method:' try to map to closest allowed method.
    - If it called a non-existent method name, remap to best available with same prefix.
    """
    allowed_methods = []
    for methods in (method_map or {}).values():
        for method in methods or []:
            allowed_methods.append(_extract_method_name(method))
    for methods in (full_method_map or {}).values():
        for method in methods or []:
            allowed_methods.append(_extract_method_name(method))
    allowed_set = set(allowed_methods)
    wait_captcha_re = re.compile(r"^(\s*)(?:_?wait_for_captcha)\(\s*page(?:\s*,.*)?\)\s*$")

    def _playwright_fallback_lines(indent: str, name: str, args: Optional[str] = None) -> list[str]:
        raw_args = (args or "").strip()
        quoted_args = _extract_quoted_strings(raw_args)
        label = _label_from_generated_method(name) or "Element"
        lower_name = (name or "").lower()

        if lower_name.startswith(("enter_", "fill_", "type_")):
            value_expr = raw_args or json.dumps(_infer_value_for_method(name, story_text) or "value")
            return [f"{indent}fill_text(page, {json.dumps(label)}, {value_expr})\n"]

        if lower_name.startswith("select_"):
            value_expr = raw_args or json.dumps(_infer_value_for_method(name, story_text) or "value")
            return [f"{indent}select_dropdown(page, {json.dumps(label)}, {value_expr})\n"]

        if lower_name.startswith(("right_click_", "rightclick_", "context_click_")):
            return [
                f"{indent}page.get_by_text({json.dumps(label)}, exact=True).first.click(button=\"right\")\n"
            ]

        if lower_name.startswith(("click_", "tap_")):
            return [f"{indent}{_click_helper_for_label(label)}\n"]

        if lower_name.startswith("check_"):
            return [f"{indent}check_checkbox(page, {json.dumps(label)})\n"]

        if lower_name.startswith("uncheck_"):
            return [f"{indent}page.get_by_role(\"checkbox\", name={json.dumps(label)}, exact=True).uncheck()\n"]

        if lower_name.startswith(("verify_", "assert_")):
            target_text = quoted_args[0] if quoted_args else label
            method = _best_method_for_label(target_text, allowed_methods, ("assert_", "verify_"))
            if method:
                return [f"{indent}{method}(page)\n"]
            return [f"{indent}verify_text_visible(page, {json.dumps(target_text)})\n"]

        if lower_name.startswith("hover_"):
            return [f"{indent}page.get_by_text({json.dumps(label)}, exact=True).first.hover()\n"]

        if lower_name.startswith("focus_"):
            return [f"{indent}page.get_by_label({json.dumps(label)}).focus()\n"]

        if lower_name.startswith("press_"):
            key_expr = raw_args or json.dumps("Enter")
            return [f"{indent}page.keyboard.press({key_expr})\n"]

        if lower_name.startswith("upload_"):
            file_expr = raw_args or json.dumps("sample_upload.txt")
            return [f"{indent}page.locator('input[type=\"file\"]').first.set_input_files({file_expr})\n"]

        if lower_name.startswith(("dblclick_", "doubleclick_", "double_click_")):
            return [f"{indent}page.get_by_text({json.dumps(label)}, exact=True).first.dblclick()\n"]

        if lower_name.startswith("goto_"):
            url = _infer_value_for_method(name, story_text)
            if url and re.match(r"^https?://", url):
                return [f"{indent}page.goto({json.dumps(url)})\n"]

        if lower_name.startswith("wait_"):
            return [f"{indent}page.wait_for_load_state(\"domcontentloaded\")\n"]

        return []

    lines = code.splitlines(True)
    out_lines: list[str] = []
    toast_expect_re = re.compile(
        r"expect\(page\.get_by_text\((['\"])(.+?)\1\)\)\.(to_be_visible|not_to_be_visible)\(\)"
    )
    expect_visible_re = re.compile(
        r'^(?P<indent>\s*)expect\(page\.get_by_text\("(?P<text>.+?)", exact=True\)\.first\)\.to_be_visible\(\)\s*$'
    )
    for line in lines:
        wait_match = wait_captcha_re.match(line.strip())
        if wait_match:
            indent = re.match(r"^(\s*)", line).group(1)
            if "enter_captcha" in allowed_set:
                out_lines.append(
                    f"{indent}page.wait_for_timeout(int(os.getenv(\"SMARTAI_CAPTCHA_WAIT_MS\", \"15000\")))\n"
                )
                out_lines.append(
                    f"{indent}enter_captcha(page, timeout_ms=int(os.getenv(\"SMARTAI_CAPTCHA_TIMEOUT_MS\", \"20000\")))\n"
                )
                continue
        method_call = METHOD_CALL_RE.match(line)
        if method_call:
            indent, method_name, value_expr = method_call.groups()
            value_clean = value_expr.strip()
            literal_match = re.match(r"^(['\"])(.*)\\1$", value_clean)
            if literal_match:
                literal_value = literal_match.group(2)
                normalized = _normalize_inferred_value(method_name, literal_value)
                if normalized is not None and normalized != literal_value:
                    out_lines.append(f'{indent}{method_name}(page, "{normalized}")\\n')
                    continue

        m = toast_expect_re.search(line)
        if m:
            text = m.group(2)
            assert_fn = m.group(3)
            line = toast_expect_re.sub(
                rf'expect(page.get_by_text("{text}", exact=True).first).{assert_fn}()',
                line,
            )
        m_visible = expect_visible_re.match(line)
        if m_visible:
            indent = m_visible.group("indent")
            text = m_visible.group("text")
            method = _best_method_for_label(text, allowed_methods, ("assert_", "verify_"))
            if method:
                out_lines.append(f"{indent}{method}(page)\n")
            else:
                out_lines.append(f"{indent}verify_text_visible(page, {json.dumps(text)})\n")
            continue
        skip_match = re.match(r"^(\s*)#\s*Skipped step due to missing method:\s*(.+)$", line)
        if skip_match:
            indent, step = skip_match.groups()
            step_lower = step.lower()
            if "enter " in step_lower or "type " in step_lower or "fill " in step_lower:
                desired_prefix = "enter_"
            elif "select " in step_lower:
                desired_prefix = "select_"
            elif "double click" in step_lower or "dblclick" in step_lower or "double-click" in step_lower:
                desired_prefix = "dblclick_"
            elif "right click" in step_lower or "right-click" in step_lower or "context click" in step_lower:
                desired_prefix = "right_click_"
            elif "click " in step_lower:
                desired_prefix = "click_"
            elif "hover " in step_lower:
                desired_prefix = "hover_"
            elif "focus " in step_lower:
                desired_prefix = "focus_"
            elif "upload " in step_lower:
                desired_prefix = "upload_"
            elif "verify " in step_lower:
                desired_prefix = "verify_"
            else:
                desired_prefix = ""
            if desired_prefix:
                method = _best_method_for_step(step, allowed_methods, desired_prefix)
                if not method and desired_prefix == "enter_":
                    method = _best_input_method_for_step(step, allowed_methods)
                if method:
                    value = None
                    if method.startswith(("enter_", "fill_", "type_", "select_")):
                        value = _infer_value_for_method(method, story_text)
                    if value is not None:
                        out_lines.append(f'{indent}{method}(page, "{value}")\n')
                    else:
                        out_lines.append(f"{indent}{method}(page)\n")
                    continue

        call_match = re.match(r"^(\s*)([a-zA-Z_][a-zA-Z0-9_]*)\(page(?:,\s*(.*))?\)\s*$", line)
        if call_match:
            indent, name, args = call_match.groups()
            if name not in allowed_set:
                desired_prefix = ""
                for prefix in ("enter_", "fill_", "type_", "select_", "click_", "right_click_", "verify_", "assert_", "press_", "upload_", "hover_", "focus_", "dblclick_", "toggle_", "check_", "uncheck_", "goto_", "wait_"):
                    if name.startswith(prefix):
                        desired_prefix = prefix
                        break
                if desired_prefix:
                    method = _best_method_for_step(name, allowed_methods, desired_prefix)
                    if not method and desired_prefix in ("enter_", "fill_", "type_"):
                        method = _best_input_method_for_step(name, allowed_methods)
                    if method:
                        if method.startswith(("enter_", "fill_", "type_", "select_")) and (args is None or args.strip() in ("\"\"", "''")):
                            value = _infer_value_for_method(method, story_text)
                            if value is not None:
                                out_lines.append(f'{indent}{method}(page, "{value}")\n')
                                continue
                        replacement = f"{indent}{method}(page"
                        if args:
                            replacement += f", {args}"
                        replacement += ")\n"
                        out_lines.append(replacement)
                        continue
                fallback_lines = _playwright_fallback_lines(indent, name, args)
                if fallback_lines:
                    out_lines.extend(fallback_lines)
                    continue
                out_lines.append(f'{indent}raise RuntimeError("Missing automation path for {name}")\n')
                continue

        bare_call_match = re.match(r"^(\s*)([a-zA-Z_][a-zA-Z0-9_]*)\(\s*\)\s*$", line)
        if bare_call_match:
            indent, name = bare_call_match.groups()
            if name in allowed_set:
                out_lines.append(f"{indent}{name}(page)\n")
                continue
            fallback_lines = _playwright_fallback_lines(indent, name)
            if fallback_lines:
                out_lines.extend(fallback_lines)
                continue
            out_lines.append(f'{indent}raise RuntimeError("Missing automation path for {name}")\n')
            continue

        out_lines.append(line)
    return "".join(out_lines)

def _fix_try_block_indentation(code: str) -> str:
    """
    Ensure lines inside try blocks are indented at least one level deeper
    than the try line. Fixes common LLM indentation issues.
    """
    if not code:
        return code
    lines = code.splitlines()
    out: list[str] = []
    i = 0
    try_re = re.compile(r"^(\s*)try:\s*$")
    except_re = re.compile(r"^(\s*)(except|finally|else)\b")
    while i < len(lines):
        line = lines[i]
        out.append(line)
        m = try_re.match(line)
        if not m:
            i += 1
            continue
        base = m.group(1)
        block_indent = base + "    "
        j = i + 1
        while j < len(lines):
            l = lines[j]
            if except_re.match(l) and len(re.match(r"^(\s*)", l).group(1)) <= len(base):
                break
            if l.strip() == "":
                out.append(l)
                j += 1
                continue
            l_indent = re.match(r"^(\s*)", l).group(1)
            if len(l_indent) <= len(base):
                out.append(block_indent + l.lstrip())
            else:
                out.append(l)
            j += 1
        i = j
    return "\n".join(out)


def _fix_function_block_indentation(code: str) -> str:
    """
    Ensure statements inside top-level test functions are indented at least one level
    deeper than the function definition. This catches common LLM mistakes where a
    single action line is emitted at column 0 inside an otherwise valid test.
    """
    if not code:
        return code
    lines = code.splitlines()
    out: list[str] = []
    i = 0
    def_re = re.compile(r"^(\s*)def\s+test_[A-Za-z0-9_]*\s*\(")
    decorator_or_top_level_re = re.compile(r"^(\s*)(@|def\s+test_)")
    while i < len(lines):
        line = lines[i]
        out.append(line)
        m = def_re.match(line)
        if not m:
            i += 1
            continue
        base = m.group(1)
        block_indent = base + "    "
        j = i + 1
        while j < len(lines):
            current = lines[j]
            if current.strip() == "":
                out.append(current)
                j += 1
                continue
            current_indent = re.match(r"^(\s*)", current).group(1)
            if decorator_or_top_level_re.match(current) and len(current_indent) <= len(base):
                break
            if len(current_indent) <= len(base):
                stripped = current.lstrip()
                if stripped.startswith(("except ", "finally:", "elif ", "else:")):
                    out.append(current)
                else:
                    out.append(block_indent + stripped)
            else:
                out.append(current)
            j += 1
        i = j
    return "\n".join(out)


def _drop_stray_numeric_name_on_card(code: str) -> str:
    """
    Remove mis-mapped duplicate lines like fill_name_on_card_cvv(page, "123")
    which are usually CVV values mistakenly applied to name field.
    """
    if not code:
        return code
    out_lines: list[str] = []
    for line in code.splitlines(True):
        if re.match(r'^\s*fill_name_on_card_cvv\(\s*page\s*,\s*"\d+"\s*\)\s*$', line):
            continue
        out_lines.append(line)
    return "".join(out_lines)


def _tokenize_label_text(text: str) -> list[str]:
    raw = re.sub(r"[^a-zA-Z0-9]+", " ", (text or "").lower()).strip()
    if not raw:
        return []
    return [t for t in raw.split() if len(t) >= 2]


def _method_tokens_for_match(method_name: str) -> list[str]:
    base = method_name
    for prefix in ("enter_", "fill_", "type_", "select_", "click_", "right_click_", "dblclick_", "check_", "uncheck_"):
        if base.startswith(prefix):
            base = base[len(prefix) :]
            break
    noise = {
        "enter",
        "fill",
        "type",
        "select",
        "click",
        "check",
        "uncheck",
        "press",
        "field",
        "input",
        "text",
        "value",
        "option",
        "button",
    }
    tokens = [t for t in re.split(r"[_\W]+", base.lower()) if len(t) >= 2 and t not in noise]
    return list(dict.fromkeys(_expand_input_alias_tokens(tokens)))


def _important_label_tokens(label: str) -> list[str]:
    tokens = _tokenize_label_text(label)
    if not tokens:
        return []
    stopwords = {
        "on",
        "of",
        "the",
        "a",
        "an",
        "for",
        "to",
        "in",
        "and",
        "or",
        "by",
    }
    filtered = [t for t in tokens if t not in stopwords]
    return list(dict.fromkeys(_expand_input_alias_tokens(filtered)))


def _exact_method_for_label(
    label: str,
    allowed_methods: list[str],
    prefixes: tuple[str, ...],
) -> Optional[str]:
    label_tokens = _important_label_tokens(label)
    if not label_tokens:
        return None
    label_key = "_".join(label_tokens)
    for method in allowed_methods:
        if not method.startswith(prefixes):
            continue
        method_tokens = _method_tokens_for_match(method)
        if not method_tokens:
            continue
        if method_tokens == label_tokens or "_".join(method_tokens) == label_key:
            return method
    return None


def _method_match_score(method_name: str, label: str) -> int:
    label_tokens = _important_label_tokens(label)
    if not label_tokens:
        return 0
    method_tokens = _method_tokens_for_match(method_name)
    if not method_tokens:
        return 0
    if method_tokens == label_tokens:
        return 1000
    if len(label_tokens) == 1:
        token = label_tokens[0]
        if token not in method_tokens:
            return 0
        extras = len([item for item in method_tokens if item != token])
        return 120 - (extras * 10)
    if not all(token in method_tokens for token in label_tokens):
        return 0
    shared = sum(1 for token in label_tokens if token in method_tokens)
    extras = len([token for token in method_tokens if token not in label_tokens])
    ordered = 0
    start = 0
    for token in label_tokens:
        try:
            idx = method_tokens.index(token, start)
        except ValueError:
            ordered = 0
            break
        ordered += 1
        start = idx + 1
    return (shared * 100) + (ordered * 10) - (extras * 15)


def _method_matches_label(method_name: str, label: str) -> bool:
    return _method_match_score(method_name, label) > 0


def _label_alias_candidates(label: str) -> list[str]:
    normalized = str(label or "").strip().lower()
    if not normalized:
        return []
    aliases = {
        "description": ("message", "comment", "remarks", "notes", "characters"),
        "message": ("description", "comment", "remarks", "notes", "characters"),
        "comments": ("comment", "description", "message", "remarks", "notes"),
        "remarks": ("comment", "description", "message", "notes"),
        "notes": ("comment", "description", "message", "remarks"),
        "grid": ("launcher", "grid launcher", "apps", "app launcher", "menu"),
        "launcher": ("grid", "grid launcher", "apps", "app launcher", "menu"),
        "mail": ("email", "envelope"),
        "email": ("mail", "envelope"),
        "settings": ("theme setup", "preferences", "setup"),
        "notification": ("notifications", "bell", "see all notifications"),
        "notifications": ("notification", "bell", "see all notifications"),
        "profile": ("my profile", "avatar", "account", "user"),
        "avatar": ("profile", "my profile", "account", "user"),
    }
    out = [str(label).strip()]
    for alias in aliases.get(normalized, ()):
        if alias not in out:
            out.append(alias)
    return out


def _best_method_for_label(
    label: str,
    allowed_methods: list[str],
    prefixes: tuple[str, ...],
) -> Optional[str]:
    candidates = _label_alias_candidates(label) or [label]

    for candidate in candidates:
        exact = _exact_method_for_label(candidate, allowed_methods, prefixes)
        if exact:
            return exact

    best_score = 0
    best_method = None
    for candidate in candidates:
        for method in allowed_methods:
            if not method.startswith(prefixes):
                continue
            score = _method_match_score(method, candidate)
            if score <= 0:
                continue
            if score > best_score:
                best_score = score
                best_method = method
    return best_method if best_score > 0 else None


def _best_input_method_for_label(label: str, allowed_methods: list[str]) -> Optional[str]:
    for prefix in ("enter_", "fill_", "type_"):
        method = _best_method_for_label(label, allowed_methods, (prefix,))
        if method:
            return method
    return None


def _replace_mismatched_input_methods(code: str, story_text: str, method_map: dict) -> str:
    """
    If a fill/enter/type call uses a POM method that doesn't match the story field label,
    fall back to fill_text(page, "<Field>", value) or the best matching POM method.
    """
    if not code or not story_text:
        return code

    inputs = _extract_story_field_inputs(story_text)
    if not inputs:
        return code

    value_to_field: dict[str, str] = {}
    dup_values: set[str] = set()
    for item in inputs:
        if item.get("action") != "enter":
            continue
        value = (item.get("value") or "").strip()
        field = (item.get("field") or "").strip()
        if not value or not field:
            continue
        if value in value_to_field and value_to_field[value] != field:
            dup_values.add(value)
        else:
            value_to_field[value] = field
    for val in dup_values:
        value_to_field.pop(val, None)

    if not value_to_field:
        return code

    allowed_methods: list[str] = []
    for methods in (method_map or {}).values():
        for method in methods or []:
            name = _extract_method_name(method)
            if name:
                allowed_methods.append(name)

    out_lines: list[str] = []
    for line in code.splitlines(True):
        m = METHOD_CALL_RE.match(line)
        if not m:
            out_lines.append(line)
            continue
        indent, method_name, value_expr = m.groups()
        quoted = _extract_quoted_strings(value_expr)
        if not quoted:
            out_lines.append(line)
            continue
        value_literal = quoted[0]
        field = value_to_field.get(value_literal)
        if not field:
            out_lines.append(line)
            continue
        preferred_enter = _best_method_for_label(field, allowed_methods, ("enter_",))
        if preferred_enter and method_name != preferred_enter:
            out_lines.append(f"{indent}{preferred_enter}(page, {value_expr})\n")
            continue
        if _method_matches_label(method_name, field):
            out_lines.append(line)
            continue
        best = _best_input_method_for_label(field, allowed_methods)
        if best and _method_matches_label(best, field):
            out_lines.append(f"{indent}{best}(page, {value_expr})\n")
            continue
        out_lines.append(f"{indent}fill_text(page, {json.dumps(field)}, {value_expr})\n")
    return "".join(out_lines)


def _replace_mismatched_check_methods(code: str, story_text: str, method_map: dict) -> str:
    """
    If a generated check_* helper call does not match the checkbox label from the story,
    replace it with the best matching POM method or fall back to check_checkbox(...).
    """
    if not code or not story_text:
        return code

    check_fields = [
        (item.get("field") or "").strip()
        for item in _extract_story_field_inputs(story_text)
        if item.get("action") == "check" and (item.get("field") or "").strip()
    ]
    check_fields = list(dict.fromkeys(check_fields))
    if not check_fields:
        return code

    allowed_methods: list[str] = []
    for methods in (method_map or {}).values():
        for method in methods or []:
            name = _extract_method_name(method)
            if name:
                allowed_methods.append(name)

    check_call_re = re.compile(r"^(?P<indent>\s*)(?P<method>check_[A-Za-z0-9_]+)\(\s*page\s*\)\s*$")
    out_lines: list[str] = []
    for line in code.splitlines(True):
        match = check_call_re.match(line)
        if not match:
            out_lines.append(line)
            continue

        method_name = match.group("method")
        indent = match.group("indent")

        if any(_method_matches_label(method_name, field) for field in check_fields):
            out_lines.append(line)
            continue

        target_field = check_fields[0] if len(check_fields) == 1 else ""
        if not target_field:
            best_field = ""
            best_score = -1
            method_tokens = set(_method_tokens_for_match(method_name))
            for field in check_fields:
                label_tokens = set(_important_label_tokens(field))
                score = len(method_tokens.intersection(label_tokens))
                if score > best_score:
                    best_score = score
                    best_field = field
            target_field = best_field or check_fields[0]

        best = _best_method_for_label(target_field, allowed_methods, ("check_",))
        if best and _method_matches_label(best, target_field):
            out_lines.append(f"{indent}{best}(page)\n")
            continue

        out_lines.append(f"{indent}check_checkbox(page, {json.dumps(target_field)})\n")

    return "".join(out_lines)


def _replace_select_calls_for_story_checks(code: str, story_text: str, method_map: dict) -> str:
    """
    If the story says to check an option but the generated code emitted select_*(page, "<same value>"),
    convert that call to a matching check_* helper or the generic check_checkbox fallback.
    """
    if not code or not story_text:
        return code

    check_fields = [
        (item.get("field") or "").strip()
        for item in _extract_story_field_inputs(story_text)
        if item.get("action") == "check" and (item.get("field") or "").strip()
    ]
    check_fields = list(dict.fromkeys(check_fields))
    if not check_fields:
        return code

    allowed_methods: list[str] = []
    for methods in (method_map or {}).values():
        for method in methods or []:
            name = _extract_method_name(method)
            if name:
                allowed_methods.append(name)

    select_call_re = re.compile(
        r'^(?P<indent>\s*)(?P<method>select_[A-Za-z0-9_]+)\(\s*page\s*,\s*(?P<q>["\'])(?P<value>.+?)(?P=q)\s*\)\s*$'
    )
    out_lines: list[str] = []
    for line in code.splitlines(True):
        match = select_call_re.match(line)
        if not match:
            out_lines.append(line)
            continue

        value = (match.group("value") or "").strip()
        if value not in check_fields:
            out_lines.append(line)
            continue

        indent = match.group("indent")
        best = _best_method_for_label(value, allowed_methods, ("check_",))
        if best and _method_matches_label(best, value):
            out_lines.append(f"{indent}{best}(page)\n")
            continue

        out_lines.append(f"{indent}check_checkbox(page, {json.dumps(value)})\n")

    return "".join(out_lines)


def _map_generic_helpers_to_pom(code: str, method_map: dict) -> str:
    """
    Replace generic helper calls (fill_text/check_checkbox/select_dropdown/click_button)
    with matching POM methods using token-based matching (no hardcoding).
    """
    if not code or not method_map:
        return code

    allowed_methods: list[str] = []
    for methods in (method_map or {}).values():
        for method in methods or []:
            name = _extract_method_name(method)
            if name:
                allowed_methods.append(name)
    if not allowed_methods:
        return code

    def _pick(label: str, prefixes: tuple[str, ...]) -> Optional[str]:
        return _best_method_for_label(label, allowed_methods, prefixes)

    out_lines: list[str] = []
    fill_re = re.compile(
        r"^(?P<indent>\s*)fill_text\(\s*page\s*,\s*(?P<label>.+?)\s*,\s*(?P<value>.+?)\s*\)\s*(?:#.*)?$"
    )
    check_re = re.compile(
        r"^(?P<indent>\s*)check_checkbox\(\s*page\s*,\s*(?P<label>.+?)\s*\)\s*(?:#.*)?$"
    )
    select_re = re.compile(
        r"^(?P<indent>\s*)select_dropdown\(\s*page\s*,\s*(?P<label>.+?)\s*,\s*(?P<value>.+?)\s*\)\s*(?:#.*)?$"
    )
    click_re = re.compile(
        r"^(?P<indent>\s*)click_button\(\s*page\s*,\s*(?P<label>.+?)\s*\)\s*(?:#.*)?$"
    )

    def _first_quoted(text: str) -> str:
        vals = _extract_quoted_strings(text or "")
        return vals[0] if vals else ""

    for line in code.splitlines(True):
        stripped = line.rstrip("\n")
        m = fill_re.match(stripped)
        if m:
            label = _first_quoted(m.group("label"))
            value = m.group("value").strip()
            method = _best_input_method_for_label(label, allowed_methods)
            if method:
                out_lines.append(f"{m.group('indent')}{method}(page, {value})\n")
                continue
        m = check_re.match(stripped)
        if m:
            label = _first_quoted(m.group("label"))
            method = _pick(label, ("check_", "uncheck_"))
            if method:
                out_lines.append(f"{m.group('indent')}{method}(page)\n")
                continue
        m = select_re.match(stripped)
        if m:
            label = _first_quoted(m.group("label"))
            value = m.group("value").strip()
            method = _pick(label, ("select_",))
            if method:
                out_lines.append(f"{m.group('indent')}{method}(page, {value})\n")
                continue
        m = click_re.match(stripped)
        if m:
            label = _first_quoted(m.group("label"))
            method = _pick(label, ("click_",))
            if method:
                out_lines.append(f"{m.group('indent')}{method}(page)\n")
                continue
        out_lines.append(line)

    return "".join(out_lines)


def _page_attr_name(page_key: str) -> str:
    key = normalize_page_name(page_key or "").strip("_")
    if key.endswith("_page"):
        key = key[:-5]
    return key or "page_object"


def _page_class_name(page_key: str) -> str:
    key = normalize_page_name(page_key or "").strip("_")
    parts = [part for part in key.split("_") if part]
    return "".join(part[:1].upper() + part[1:] for part in parts)


def _page_module_alias_name(page_key: str) -> str:
    return f"_pm_{_page_attr_name(page_key)}"


def _inject_page_object_instances(code: str, method_map: dict) -> str:
    if not code or not method_map:
        return code
    if "_page_methods import *" in code:
        return code
    if "from pages." not in code or "_page import *" not in code:
        return code

    page_objects: list[tuple[str, str]] = []
    for page_key in method_map.keys():
        attr = _page_attr_name(page_key)
        cls = _page_class_name(page_key)
        if attr and cls:
            page_objects.append((attr, cls))
    if not page_objects:
        return code

    out_lines: list[str] = []
    attach_re = re.compile(r"^(?P<indent>\s*)_attach_page_helpers\(page\)\s*$")
    for line in code.splitlines(True):
        out_lines.append(line)
        match = attach_re.match(line.rstrip("\n"))
        if not match:
            continue
        indent = match.group("indent")
        for attr, cls in page_objects:
            instance_line = f"{indent}page.{attr} = {cls}(page)\n"
            if instance_line not in code:
                out_lines.append(instance_line)
    return "".join(out_lines)


def _qualify_pom_method_calls(
    code: str,
    method_map: dict,
    force_page_methods_style: Optional[bool] = None,
) -> str:
    if not code or not method_map:
        return code

    if force_page_methods_style is None:
        use_page_methods_style = "_page_methods import *" in code
    else:
        use_page_methods_style = force_page_methods_style

    valid_methods: set[str] = set()
    method_to_attr: dict[str, str] = {}
    method_to_module_alias: dict[str, str] = {}
    for page_key, methods in (method_map or {}).items():
        attr = _page_attr_name(page_key)
        module_alias = _page_module_alias_name(page_key)
        for method in methods or []:
            name = _extract_method_name(method)
            if name:
                valid_methods.add(name)
                method_to_attr.setdefault(name, attr)
                method_to_module_alias.setdefault(name, module_alias)
    if not valid_methods:
        return code

    out_lines: list[str] = []
    skip_prefixes = ("def ", "class ", "from ", "import ")
    for line in code.splitlines(True):
        stripped = line.lstrip()
        if stripped.startswith(skip_prefixes):
            out_lines.append(line)
            continue
        bare_call_match = re.match(
            r"^(?P<indent>\s*)(?P<method>[a-zA-Z_][a-zA-Z0-9_]*)\((?P<args>.*)\)\s*$",
            line.rstrip("\n"),
        )
        if bare_call_match:
            method = bare_call_match.group("method")
            args = bare_call_match.group("args").strip()
            if method in valid_methods:
                if use_page_methods_style:
                    module_alias = method_to_module_alias.get(method)
                    if module_alias:
                        cleaned_args = args
                        if cleaned_args.startswith("page,"):
                            cleaned_args = cleaned_args[5:].strip()
                        elif cleaned_args == "page":
                            cleaned_args = ""
                        replacement = f"{bare_call_match.group('indent')}{module_alias}.{method}(page"
                        if cleaned_args:
                            replacement += f", {cleaned_args}"
                        replacement += ")\n"
                        out_lines.append(replacement)
                        continue
                else:
                    attr = method_to_attr.get(method)
                    if attr:
                        cleaned_args = args
                        if cleaned_args.startswith("page,"):
                            cleaned_args = cleaned_args[5:].strip()
                        elif cleaned_args == "page":
                            cleaned_args = ""
                        replacement = f"{bare_call_match.group('indent')}page.{attr}.{method}("
                        if cleaned_args:
                            replacement += cleaned_args
                        replacement += ")\n"
                        out_lines.append(replacement)
                        continue

        page_obj_match = re.match(
            r"^(?P<indent>\s*)page\.(?P<obj>[a-zA-Z_][a-zA-Z0-9_]*)\.(?P<method>[a-zA-Z_][a-zA-Z0-9_]*)\((?P<args>.*)\)\s*$",
            line.rstrip("\n"),
        )
        if page_obj_match:
            method = page_obj_match.group("method")
            args = page_obj_match.group("args").strip()
            if method in valid_methods and use_page_methods_style:
                module_alias = method_to_module_alias.get(method)
                if module_alias:
                    cleaned_args = args
                    if cleaned_args.startswith("page,"):
                        cleaned_args = cleaned_args[5:].strip()
                    elif cleaned_args == "page":
                        cleaned_args = ""
                    replacement = f"{page_obj_match.group('indent')}{module_alias}.{method}(page"
                    if cleaned_args:
                        replacement += f", {cleaned_args}"
                    replacement += ")\n"
                    out_lines.append(replacement)
                    continue

        out_lines.append(line)
    return "".join(out_lines)


def _rewrite_calendar_popup_numeric_clicks(code: str) -> str:
    if not code:
        return code

    calendar_call_re = re.compile(
        r"^(?P<indent>\s*)(?:(?P<module>[a-zA-Z_][a-zA-Z0-9_]*)\.)?(?P<method>(?:click|open)_[a-zA-Z0-9_]*calendar[a-zA-Z0-9_]*)\(page(?:,\s*(?P<args>.*))?\)\s*$"
    )
    numeric_click_re = re.compile(
        r"^(?P<indent>\s*)(?:(?P<module>[a-zA-Z_][a-zA-Z0-9_]*)\.)?click_(?P<day>\d{1,2})\(page\)\s*$"
    )

    out_lines: list[str] = []
    pending_calendar_module: Optional[str] = None
    pending_calendar_indent: Optional[str] = None
    pending_calendar_ttl = 0

    for line in code.splitlines(True):
        stripped = line.strip()
        calendar_match = calendar_call_re.match(line.rstrip("\n"))
        if calendar_match:
            pending_calendar_module = calendar_match.group("module")
            pending_calendar_indent = calendar_match.group("indent")
            pending_calendar_ttl = 2
            out_lines.append(line)
            continue

        numeric_match = numeric_click_re.match(line.rstrip("\n"))
        if numeric_match and pending_calendar_ttl > 0:
            day = numeric_match.group("day")
            indent = numeric_match.group("indent")
            module = pending_calendar_module or numeric_match.group("module")
            replacement = f"{indent}{module + '.' if module else ''}select_calendar_date(page, {json.dumps(day)})\n"
            out_lines.append(replacement)
            pending_calendar_ttl = 0
            pending_calendar_module = None
            pending_calendar_indent = None
            continue

        out_lines.append(line)

        if not stripped or stripped.startswith("#"):
            continue

        if pending_calendar_ttl > 0:
            current_indent = re.match(r"^(\s*)", line).group(1)
            if pending_calendar_indent is not None and current_indent != pending_calendar_indent:
                pending_calendar_ttl = 0
                pending_calendar_module = None
                pending_calendar_indent = None
            else:
                pending_calendar_ttl -= 1
                if pending_calendar_ttl <= 0:
                    pending_calendar_module = None
                    pending_calendar_indent = None

    return "".join(out_lines)


def _rewrite_wfh_calendar_steps_for_runner(code: str) -> str:
    return code


def _rewrite_toggle_ensure_calls(code: str, method_map: Optional[dict] = None) -> str:
    if not code or not method_map:
        return code

    allowed_methods: list[str] = []
    for methods in (method_map or {}).values():
        for method in methods or []:
            name = _extract_method_name(method)
            if name:
                allowed_methods.append(name)
    if not allowed_methods:
        return code

    ensure_call_re = re.compile(
        r"^(?P<indent>\s*)(?:(?:page\.[A-Za-z_][A-Za-z0-9_]*|[A-Za-z_][A-Za-z0-9_]*)\.)?(?P<method>ensure_[A-Za-z0-9_]+)\((?P<args>.*)\)\s*$"
    )
    simple_call_re = re.compile(
        r"^(?P<indent>\s*)(?:(?:page\.[A-Za-z_][A-Za-z0-9_]*|[A-Za-z_][A-Za-z0-9_]*)\.)?(?P<method>[A-Za-z_][A-Za-z0-9_]*)\((?P<args>.*)\)\s*$"
    )

    lines = code.splitlines(True)
    out_lines: list[str] = []

    def _assertion_for_following_step(idx: int, indent: str) -> Optional[str]:
        for next_idx in range(idx + 1, len(lines)):
            raw = lines[next_idx]
            stripped = raw.strip()
            if not stripped or stripped.startswith("#"):
                continue
            next_indent = re.match(r"^(\s*)", raw).group(1)
            if next_indent != indent:
                return None
            call_match = simple_call_re.match(raw.rstrip("\n"))
            if not call_match:
                return None
            next_method = call_match.group("method")
            if next_method.startswith(("click_", "enter_", "fill_", "type_", "select_")):
                label = _label_from_generated_method(next_method) or next_method
                if "calendar icon" in label.lower():
                    trimmed = re.sub(r"\bcalendar icon\b", "", label, flags=re.I).strip(" _-")
                    if trimmed:
                        assertion = _best_method_for_label(trimmed, allowed_methods, ("assert_", "verify_"))
                        if assertion:
                            return f"{indent}{assertion}(page)\n"
                assertion = _best_method_for_label(label, allowed_methods, ("assert_", "verify_"))
                if assertion:
                    return f"{indent}{assertion}(page)\n"
            return None
        return None

    for idx, line in enumerate(lines):
        match = ensure_call_re.match(line.rstrip("\n"))
        if not match:
            out_lines.append(line)
            continue
        indent = match.group("indent")
        replacement = _assertion_for_following_step(idx, indent)
        if replacement:
            out_lines.append(replacement)
            continue
        out_lines.append(line)

    return "".join(out_lines)


def _ensure_page_arg_for_pom_calls(code: str, method_map: Optional[dict] = None) -> str:
    if not code:
        return code

    valid_methods: set[str] = set()
    for methods in (method_map or {}).values():
        for method in methods or []:
            name = _extract_method_name(method)
            if name:
                valid_methods.add(name)

    out_lines: list[str] = []
    known_runtime_helpers = {
        "fill_text",
        "check_checkbox",
        "select_dropdown",
        "click_button",
        "click_icon",
        "_dismiss_cookie_banner",
        "_safe_screenshot",
        "_attach_page_helpers",
        "_write_allure_environment",
        "patch_page_with_smartai",
        "set_current_page",
        "run_allure_case",
    }
    for line in code.splitlines(True):
        stripped = line.lstrip()
        if stripped.startswith(("def ", "class ", "from ", "import ", "@")):
            out_lines.append(line)
            continue
        match = re.match(
            r"^(?P<indent>\s*)(?P<method>[a-zA-Z_][a-zA-Z0-9_]*)\((?P<args>.*)\)(?P<suffix>\s*(?:#.*)?)$",
            line.rstrip("\n"),
        )
        if not match:
            out_lines.append(line)
            continue
        method = match.group("method")
        args = match.group("args").strip()
        if method in valid_methods and not args.startswith("page"):
            replacement = f"{match.group('indent')}{method}(page"
            if args:
                replacement += f", {args}"
            replacement += f"){match.group('suffix')}\n"
            out_lines.append(replacement)
            continue
        if (
            method not in known_runtime_helpers
            and method not in {"sync_playwright", "expect"}
            and re.match(r"^(check_|uncheck_|click_|enter_|fill_|select_|verify_|assert_)", method)
            and not args.startswith("page")
        ):
            replacement = f"{match.group('indent')}{method}(page"
            if args:
                replacement += f", {args}"
            replacement += f"){match.group('suffix')}\n"
            out_lines.append(replacement)
            continue
        out_lines.append(line)
    return "".join(out_lines)


def _remove_stray_explanatory_prose(code: str) -> str:
    if not code:
        return code
    filtered: list[str] = []
    drop_block = False
    for line in code.splitlines(True):
        stripped = line.strip()
        if not stripped:
            if drop_block:
                continue
            filtered.append(line)
            continue
        if _is_stray_explanatory_line(line):
            drop_block = True
            continue
        if stripped.startswith("# AI-analyzed tags:"):
            continue
        if drop_block:
            if _is_stray_explanatory_line(line):
                continue
            if not _looks_like_python_code_line(line):
                continue
            drop_block = False
        filtered.append(line)
    return "".join(filtered)


def _label_from_generated_method(method_name: str) -> str:
    base = re.sub(r"^(check_|uncheck_|fill_|enter_|type_|select_|click_|right_click_|dblclick_|assert_|verify_)", "", method_name or "")
    base = re.sub(r"_(checkbox|radio|button|link|input|select|dropdown|field)$", "", base)
    parts = [part for part in base.split("_") if part]
    return " ".join(part.capitalize() for part in parts)


_ICON_LABEL_TOKENS = {
    "calendar",
    "date",
    "settings",
    "gear",
    "cog",
    "bell",
    "notification",
    "notifications",
    "profile",
    "avatar",
    "user",
    "account",
    "camera",
    "photo",
    "image",
    "heart",
    "favorite",
    "bookmark",
    "cart",
    "shopping",
    "basket",
    "share",
    "send",
    "mail",
    "email",
    "envelope",
    "search",
    "filter",
    "menu",
    "hamburger",
    "kebab",
    "ellipsis",
    "dots",
    "more",
    "close",
    "delete",
    "trash",
    "download",
    "upload",
    "info",
    "help",
    "question",
    "link",
    "copy",
    "clipboard",
    "attachment",
    "paperclip",
    "tag",
    "flag",
    "star",
}


def _is_icon_like_label(label: str) -> bool:
    raw = (label or "").strip()
    if not raw:
        return False
    lowered = raw.lower()
    if "icon" in lowered:
        return True
    if lowered in {"...", "…", "⋯", "⋮", "⋱", "⋰", "×", "x", "✕", "✖"}:
        return True
    tokens = re.findall(r"[a-z0-9]+", lowered)
    if not tokens:
        return False
    if len(tokens) <= 2 and all(token in _ICON_LABEL_TOKENS for token in tokens):
        return True
    if len(tokens) == 1 and tokens[0] in _ICON_LABEL_TOKENS:
        return True
    return False


def _click_helper_for_label(label: str) -> str:
    quoted = json.dumps(label)
    if _is_icon_like_label(label):
        return f"click_icon(page, {quoted})"
    return f"click_button(page, {quoted})"


def _rewrite_missing_page_object_calls(code: str, method_map: dict) -> str:
    if not code:
        return code

    valid_methods: set[str] = set()
    for methods in (method_map or {}).values():
        for method in methods or []:
            name = _extract_method_name(method)
            if name:
                valid_methods.add(name)

    call_re = re.compile(r"^(?P<indent>\s*)page\.(?P<obj>[a-zA-Z_][a-zA-Z0-9_]*)\.(?P<method>[a-zA-Z_][a-zA-Z0-9_]*)\((?P<args>.*)\)\s*(?P<comment>#.*)?$")
    out_lines: list[str] = []
    for line in code.splitlines(True):
        match = call_re.match(line.rstrip("\n"))
        if not match:
            out_lines.append(line)
            continue
        method = match.group("method")
        if method in valid_methods:
            out_lines.append(line)
            continue
        indent = match.group("indent")
        label = _label_from_generated_method(method)
        if method.startswith("check_") and label:
            out_lines.append(
                f'{indent}page.get_by_role("checkbox", name={json.dumps(label)}).check()\n'
            )
            continue
        if method.startswith("uncheck_") and label:
            out_lines.append(
                f'{indent}page.get_by_role("checkbox", name={json.dumps(label)}).uncheck()\n'
            )
            continue
        if method.startswith(("fill_", "enter_", "type_")) and label:
            args = match.group("args").strip()
            out_lines.append(
                f'{indent}page.get_by_label({json.dumps(label)}, exact=False).fill({args})\n'
            )
            continue
        if method.startswith("select_") and label:
            args = match.group("args").strip()
            out_lines.append(
                f'{indent}page.get_by_label({json.dumps(label)}, exact=False).select_option({args})\n'
            )
            continue
        if method.startswith("click_") and label:
            out_lines.append(
                f'{indent}page.get_by_role("button", name={json.dumps(label)}).click()\n'
            )
            continue
        out_lines.append(line)
    return "".join(out_lines)


def _safe_slug(value: str, fallback: str = "story", max_len: int = 40) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", (value or "").lower()).strip("_")
    if slug:
        parts = [p for p in slug.split("_") if p]
        slug = "_".join(parts)
    if not slug:
        slug = fallback
    return slug[:max_len]


def _infer_script_slug(
    story: str,
    category: str,
    db: Optional[Session] = None,
    project_id: Optional[int] = None,
    feature: str = "hybrid_generation",
) -> str:
    """
    Use the LLM to propose a short, descriptive filename base for the story.
    Falls back to a sanitized story snippet when inference fails.
    """
    story_clean = (story or "").strip()
    if not story_clean:
        return "story"
    prompt = (
        "Create a short 3-6 word snake_case filename base that summarizes this user story. "
        "Only output the filename base (no extension, no quotes, no extra text).\n\n"
        f"Story:\n{story_clean}\n"
    )
    model_name = os.getenv("AI_INFER_MODEL", os.getenv("AI_MODEL_NAME", "gpt-4o"))
    try:
        result = call_openai(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=40,
            temperature=0,
        )
        log_token_usage(
            db=db,
            project_id=project_id,
            feature=feature,
            usage=result.get("usage"),
            model=result.get("model"),
        )
        raw = (result.get("content") or "").strip()
        raw = raw.splitlines()[0].strip().strip("\"'`")
        raw = re.sub(r"\.py$", "", raw, flags=re.IGNORECASE).strip()
        slug = _safe_slug(raw)
        if slug:
            return slug
    except Exception:
        pass
    return _safe_slug(" ".join(story_clean.split()[:6]))


def _strip_module_qualified_helpers(code: str, method_map: dict) -> str:
    """
    Replace module-qualified helper calls (e.g., bank_customer.click_x(page))
    with the plain helper name (click_x(page)).
    """
    helper_names = set()
    for methods in (method_map or {}).values():
        for method_def in methods:
            name = method_def.split("(", 1)[0].replace("def ", "").strip()
            if name:
                helper_names.add(name)
    if not helper_names:
        return code
    cleaned = code
    for helper_name in helper_names:
        module_pattern = rf"(?:[a-zA-Z_][a-zA-Z0-9_]*\.)+{re.escape(helper_name)}\("
        cleaned = re.sub(module_pattern, f"{helper_name}(", cleaned)
    return cleaned


def _simplify_page_method_alias_calls(code: str) -> tuple[str, list[str]]:
    """
    Keep explicit page-module routing internally, but avoid leaking module aliases
    into testcase bodies when a method name maps to only one page-method module
    within the generated script.
    """
    if not code or "_pm_" not in code:
        return code, []

    call_re = re.compile(r"(?P<alias>_pm_[A-Za-z0-9_]+)\.(?P<method>[A-Za-z_][A-Za-z0-9_]*)\(")
    method_to_aliases: dict[str, set[str]] = {}
    for line in code.splitlines():
        stripped = line.lstrip()
        if stripped.startswith(("def ", "class ", "from ", "import ")):
            continue
        for match in call_re.finditer(line):
            method_to_aliases.setdefault(match.group("method"), set()).add(match.group("alias"))

    safe_methods = {
        method: next(iter(aliases))
        for method, aliases in method_to_aliases.items()
        if len(aliases) == 1
    }
    if not safe_methods:
        return code, []

    rewritten = code
    for method, alias in sorted(safe_methods.items()):
        rewritten = re.sub(rf"\b{re.escape(alias)}\.{re.escape(method)}\(", f"{method}(", rewritten)
    return rewritten, []


# ----------------------------------------------------------------------
# Assertions injection
# ----------------------------------------------------------------------
METHOD_CALL_RE = re.compile(
    r"^(\s*)((?:enter_|fill_|type_)[a-zA-Z0-9_]+)\(\s*page\s*,\s*(.+?)\s*\)\s*(?:#.*)?$"
)
ASSERT_CALL_RE = re.compile(r"^(\s*)assert_([a-zA-Z0-9_]+)\(\s*page\s*,\s*(.+?)\s*\)\s*$")
_EMPTY_LITERAL_RE = re.compile(
    r"^(\s*)(?P<fn>(?:enter_|fill_|type_|assert_enter_)[a-zA-Z0-9_]+)\(\s*page\s*,\s*(?P<q>['\"])\s*(?P=q)\s*\)\s*(?:#.*)?$"
)


def _extract_quoted_strings(line: str) -> list[str]:
    values: list[str] = []
    if not line:
        return values
    patterns = (
        r'"([^"]+)"',
        r"'([^']+)'",
        r"“([^”]+)”",
        r"‘([^’]+)’",
    )
    for pat in patterns:
        for match in re.findall(pat, line):
            cleaned = (match or "").strip()
            if cleaned:
                values.append(cleaned)
    # Preserve order, drop dups.
    return list(dict.fromkeys(values))


def _normalize_story_target_label(value: str) -> str:
    text = " ".join((value or "").split()).strip()
    if not text:
        return ""
    text = re.sub(r"\bin\s+(popup|dialog|modal)\b", "", text, flags=re.I).strip()
    text = re.sub(r"\b(button|icon|avatar|link|tab|menu|option|field)\b", "", text, flags=re.I).strip()
    text = re.sub(r"\s{2,}", " ", text).strip(" -:")
    if re.fullmatch(r"[A-Za-z]", text):
        return text.upper()
    return text


def _infer_story_action_value(line: str, action: str, quoted: list[str]) -> str:
    if quoted:
        return _normalize_story_target_label(quoted[0])
    source = (line or "").strip()
    if not source:
        return ""
    patterns_by_action = {
        "click": [
            r"\bclick(?:\s+on)?\s+(.+)$",
            r"\btap(?:\s+on)?\s+(.+)$",
        ],
        "dblclick": [
            r"\b(?:double click|double-click|doubleclick|dblclick)(?:\s+on)?\s+(.+)$",
        ],
        "right_click": [
            r"\b(?:right click|right-click|rightclick|context click|context-click)(?:\s+on)?\s+(.+)$",
        ],
        "select": [
            r"\b(?:select|choose|pick)\s+(.+)$",
        ],
    }
    for pattern in patterns_by_action.get(action, []):
        match = re.search(pattern, source, re.I)
        if not match:
            continue
        candidate = (match.group(1) or "").strip()
        candidate = re.sub(r"^(?:the|a|an)\s+", "", candidate, flags=re.I).strip()
        normalized = _normalize_story_target_label(candidate)
        if normalized:
            return normalized
    return ""


def _extract_story_steps_structured(story_text: str) -> list[StoryStep]:
    if not story_text:
        return []
    steps: list[StoryStep] = []
    popup_active = False
    last_click_index: Optional[int] = None
    for raw_line in _iter_story_lines(story_text):
        line = (raw_line or "").strip()
        if not line:
            continue
        lowered = line.lower()
        quoted = _extract_quoted_strings(line)
        url_match = re.search(r"(https?://[^\s\"'<>]+)", line)

        if (
            steps
            and steps[-1].action == "wait_for_page_load"
            and "visible" in lowered
            and quoted
        ):
            last = steps[-1]
            updated_value = _normalize_story_target_label(quoted[0])
            steps[-1] = StoryStep(
                action=last.action,
                target=last.target,
                value=updated_value or last.value,
                raw=last.raw,
                context=last.context,
                match=last.match,
            )
            continue

        def _add_step(action: str, value: str = "", match: str = "equals", force_context: Optional[str] = None):
            context = force_context or ("popup" if popup_active else "main")
            steps.append(StoryStep(action=action, value=value, context=context, match=match))

        popup_window_intent = any(k in lowered for k in ("new tab", "new window", "open in new tab", "open in new window"))
        plain_popup_intent = any(k in lowered for k in ("popup", "pop-up")) and not (
            re.search(r"\bwait\b", lowered) and re.search(r"\bvisible\b", lowered)
        )
        if popup_window_intent or plain_popup_intent:
            _add_step("switch_window", value="popup")
            popup_active = True

        if "switch back" in lowered or "back to main" in lowered or "back to original" in lowered:
            popup_active = False
            _add_step("switch_window", value="main", force_context="main")

        if "close" in lowered and "window" in lowered:
            if not popup_active and last_click_index is not None:
                has_popup_switch = any(
                    s.action == "switch_window" and s.value == "popup"
                    for s in steps[last_click_index + 1 :]
                )
                if not has_popup_switch:
                    steps.insert(
                        last_click_index + 1,
                        StoryStep(action="switch_window", value="popup", context="popup"),
                    )
                    popup_active = True
            _add_step("close", value="window")
            popup_active = False

        def _looks_like_url_local(v: str) -> bool:
            t = (v or "").strip()
            if not t:
                return False
            if t.startswith(("http://", "https://", "/")):
                return True
            return "." in t and "/" in t

        nav_triggers = ("navigate to", "go to", "visit ", "redirected to", "should navigate to")
        has_nav_trigger = any(k in lowered for k in nav_triggers)
        has_open = "open " in lowered
        open_is_url = url_match is not None or any(_looks_like_url_local(q) for q in quoted)

        if has_nav_trigger or (has_open and open_is_url):
            if quoted:
                _add_step("navigate", quoted[0])
                if "should navigate to" in lowered or "redirected to" in lowered:
                    _add_step("verify_url", quoted[0], match="equals")
            elif url_match:
                _add_step("navigate", url_match.group(1))
                if "should navigate to" in lowered or "redirected to" in lowered:
                    _add_step("verify_url", url_match.group(1), match="equals")
            continue

        if re.search(r"\b(double click|double-click|doubleclick|dblclick)\b", lowered):
            _add_step("dblclick", _infer_story_action_value(line, "dblclick", quoted))
            last_click_index = len(steps) - 1
            continue

        if re.search(r"\b(right click|right-click|rightclick|context click|context-click|context menu)\b", lowered):
            _add_step("right_click", _infer_story_action_value(line, "right_click", quoted))
            last_click_index = len(steps) - 1
            continue

        if "click" in lowered:
            _add_step("click", _infer_story_action_value(line, "click", quoted))
            last_click_index = len(steps) - 1
            continue

        if any(k in lowered for k in ("enter ", "type ", "fill ", "input ")):
            value = quoted[0] if quoted else ""
            _add_step("enter", value)
            continue

        if any(k in lowered for k in ("select ", "choose ", "pick ")):
            value = _infer_story_action_value(line, "select", quoted)
            _add_step("select", value)
            continue

        if (
            re.search(r"\bwait\b", lowered)
            and re.search(r"\b(page|screen|application|app)\b", lowered)
            and re.search(r"\b(load|loaded|loads|loading)\b", lowered)
        ):
            wait_target = ""
            if quoted:
                wait_target = _normalize_story_target_label(quoted[0])
            else:
                visible_match = re.search(
                    r"\band\s+(.+?)\s+(?:is\s+)?visible\b",
                    line,
                    re.I,
                )
                if visible_match:
                    wait_target = _normalize_story_target_label(visible_match.group(1))
            _add_step("wait_for_page_load", value=wait_target)
            continue

        if "drag" in lowered:
            _add_step("drag", quoted[0] if quoted else "")
            continue

        if any(k in lowered for k in ("verify url", "validate url", "url should", "url contains", "redirected to")):
            value = quoted[0] if quoted else (url_match.group(1) if url_match else "")
            match = "contains" if "contains" in lowered else "equals"
            _add_step("verify_url", value, match=match)
            continue

        if any(k in lowered for k in ("verify title", "page title", "title should", "title contains", "verify the title")):
            value = quoted[0] if quoted else ""
            if not value:
                m = re.search(r"(?:verify title|page title should be|title should be|verify the title)\s+(.+)$", line, re.IGNORECASE)
                if m:
                    value = (m.group(1) or "").strip()
            if "contains" in lowered or ("verify title" in lowered and "should" not in lowered):
                match = "contains"
            else:
                match = "equals"
            _add_step("verify_title", value, match=match)
            continue

        if "scroll" in lowered:
            value = quoted[0] if quoted else ""
            _add_step("scroll", value)
            if "visible" in lowered:
                _add_step("verify_text", value, match="equals")
            continue

        # Handle "verify <text> ... visible" phrasing
        if "verify" in lowered and "visible" in lowered:
            value = quoted[0] if quoted else ""
            if value:
                _add_step("verify_text", value, match="equals")
                continue

        if any(k in lowered for k in ("check", "is visible")):
            value = quoted[0] if quoted else ""
            if value:
                _add_step("verify_text", value, match="equals")
                continue

        if any(k in lowered for k in ("should see", "should display", "should show", "verify text", "verify that", "then i should see")):
            value = quoted[0] if quoted else ""
            if not value:
                m = re.search(r"(?:should see|should display|should show|verify text|verify that)\s+(.+)$", line, re.IGNORECASE)
                if m:
                    value = (m.group(1) or "").strip()
            match = "contains" if "contains" in lowered else "equals"
            _add_step("verify_text", value, match=match)
            continue

    return steps


def _story_steps_to_prompt_lines(steps: list[StoryStep]) -> list[str]:
    if not steps:
        return []
    lines = []
    for step in steps:
        value = f' "{step.value}"' if step.value else ""
        match = f" ({step.match})" if step.match and step.action.startswith("verify_") else ""
        lines.append(f"    - [{step.context}] {step.action}{value}{match}")
    return lines


def _line_matches_story_step(line: str, step: StoryStep) -> bool:
    stripped = (line or "").strip()
    if not stripped or stripped.startswith("#"):
        return False
    action = (step.action or "").lower()
    value = (step.value or "").strip()
    lowered = stripped.lower()

    if action == "navigate":
        return "page.goto(" in stripped

    if action in {"click", "dblclick", "right_click"}:
        if stripped.startswith("assert_") or ".to_be_visible(" in stripped or "_visible(" in lowered:
            return False
        if ".click(" not in stripped and "click_" not in lowered and "click_button(" not in lowered and "click_icon(" not in lowered:
            return False
        if not value:
            return True
        return json.dumps(value) in stripped or value.lower() in lowered

    if action == "enter":
        if not any(token in lowered for token in ("enter_", "fill_", "type_", "fill_text(", ".fill(", "press_sequentially(")):
            return False
        if not value:
            return True
        return json.dumps(value) in stripped or value.lower() in lowered

    if action == "select":
        if not any(token in lowered for token in ("select_", "select_dropdown(", ".select_option(", ".select_options(")):
            return False
        if not value:
            return True
        return json.dumps(value) in stripped or value.lower() in lowered

    if action == "drag":
        return "drag_" in lowered or "safe_drag_and_drop(" in lowered or ".drag_to(" in lowered

    if action == "close":
        return ".close(" in lowered or "click_icon(page, \"close\")" in lowered or "click_button(page, \"close\")" in lowered

    return False


def _wait_expected_texts_for_story_step(steps: list[StoryStep], wait_idx: int, max_items: int = 2) -> list[str]:
    expected: list[str] = []
    wait_step = steps[wait_idx]
    wait_value = (wait_step.value or "").strip()
    if wait_value:
        expected.append(wait_value)
    for candidate in steps[wait_idx + 1 :]:
        action = (candidate.action or "").lower()
        value = (candidate.value or "").strip()
        if action == "wait_for_page_load":
            break
        if action in {"enter", "select", "drag", "navigate", "verify_url", "verify_title", "switch_window", "close"}:
            break
        if action in {"click", "verify_text"} and value:
            if value not in expected:
                expected.append(value)
            if len(expected) >= max_items:
                break
    return expected


def _is_wait_target_visibility_assertion(line: str, expected_texts: list[str]) -> bool:
    stripped = (line or "").strip()
    if ".to_be_visible(" not in stripped:
        return False
    lowered = stripped.lower()
    for text in expected_texts or []:
        value = (text or "").strip()
        if not value:
            continue
        if json.dumps(value) in stripped or value.lower() in lowered:
            return True
    return False


def _is_load_wait_line(line: str) -> bool:
    stripped = (line or "").strip()
    return bool(
        re.match(
            r"""^page\.wait_for_load_state\(\s*['"](?:domcontentloaded|load|networkidle)['"](?:\s*,.*)?\)\s*$""",
            stripped,
        )
    )


def _is_generated_wait_comment(line: str) -> bool:
    stripped = (line or "").strip().lower()
    return stripped.startswith("#") and "wait until page is loaded" in stripped


def _inject_explicit_page_load_waits(code: str, story_text: str) -> str:
    if not code or not story_text:
        return code
    steps = _extract_story_steps_structured(story_text)
    wait_indexes = [idx for idx, step in enumerate(steps) if step.action == "wait_for_page_load"]
    if not wait_indexes:
        return code

    lines = code.splitlines(True)
    search_start = 0

    for wait_idx in wait_indexes:
        prev_step = None
        for idx in range(wait_idx - 1, -1, -1):
            candidate = steps[idx]
            if candidate.action != "wait_for_page_load":
                prev_step = candidate
                break
        if prev_step is None:
            continue

        anchor_index = None
        for line_idx in range(search_start, len(lines)):
            if _line_matches_story_step(lines[line_idx], prev_step):
                anchor_index = line_idx
                break
        if anchor_index is None:
            continue

        next_nonempty = anchor_index + 1
        while next_nonempty < len(lines) and not lines[next_nonempty].strip():
            next_nonempty += 1

        indent = re.match(r"^(\s*)", lines[anchor_index]).group(1)
        expected_texts = _wait_expected_texts_for_story_step(steps, wait_idx)
        if expected_texts:
            injected = [f"{indent}_wait_for_ui_ready(page, expected_texts={json.dumps(expected_texts)})\n"]
        else:
            injected = [f"{indent}_wait_for_ui_ready(page)\n"]
        if next_nonempty < len(lines) and (
            _is_load_wait_line(lines[next_nonempty])
            or "_wait_for_ui_ready(page" in lines[next_nonempty]
        ):
            replace_end = next_nonempty + 1
            while replace_end < len(lines):
                current = lines[replace_end].strip()
                if (
                    _is_load_wait_line(current)
                    or current.startswith("_wait_for_ui_ready(page")
                ):
                    replace_end += 1
                    continue
                break
            lines[next_nonempty:replace_end] = injected
            search_start = next_nonempty + len(injected)
        else:
            lines[anchor_index + 1 : anchor_index + 1] = injected
            search_start = anchor_index + 1 + len(injected)

        cleanup_index = search_start
        while cleanup_index < len(lines):
            current = lines[cleanup_index].strip()
            if not current:
                cleanup_index += 1
                continue
            if _is_generated_wait_comment(current):
                del lines[cleanup_index]
                continue
            if _is_load_wait_line(current):
                del lines[cleanup_index]
                continue
            if _is_wait_target_visibility_assertion(lines[cleanup_index], expected_texts):
                del lines[cleanup_index]
                continue
            break

    return "".join(lines)


def _extract_story_scroll_targets(story_text: str) -> list[str]:
    if not story_text:
        return []
    collected: list[str] = []
    for line in (story_text or "").splitlines():
        lowered = (line or "").strip().lower()
        if not lowered:
            continue
        if "scroll" not in lowered:
            continue
        # If the line mentions scroll + visibility with quoted text, treat it as a scroll target.
        if "visible" in lowered and _extract_quoted_strings(line):
            collected.extend(_extract_quoted_strings(line))
            continue
        # Look for "scroll until/till ... visible" patterns.
        if ("until" in lowered or "till" in lowered) and "visible" in lowered:
            collected.extend(_extract_quoted_strings(line))
            continue
        # Fallback: "scroll to/upto ...", even without explicit visible
        if ("scroll to" in lowered or "scroll upto" in lowered or "scroll up to" in lowered) and _extract_quoted_strings(line):
            collected.extend(_extract_quoted_strings(line))
    return list(dict.fromkeys(collected))


def _extract_story_field_inputs(story_text: str) -> list[dict]:
    """
    Extract structured input actions from story text.
    Supports:
      - enter/type/fill "<value>" in the <Field> field
      - select "<value>" for <Field>
      - check <Field> checkbox
    Returns list of {"action": "enter"|"select", "field": str, "value": str}.
    """
    if not story_text:
        return []
    actions: list[dict] = []
    patterns = [
        (r'\bcheck\s+"([^"]+)"\s+in\s+"([^"]+)"\s+field\b', "check"),
        (r'\b(?:enter|type|fill)\s+"([^"]+)"\s+in\s+the\s+(.+?)\s+field\b', "enter"),
        (r'\bselect\s+"([^"]+)"\s+for\s+(.+?)\b', "select"),
        (r'\bcheck\s+(.+?)\s+checkbox\b', "check"),
    ]
    for line in (story_text or "").splitlines():
        raw = line.strip()
        for pat, action in patterns:
            m = re.search(pat, raw, flags=re.IGNORECASE)
            if not m:
                continue
            if action == "check":
                field = (m.group(1) or "").strip().strip('"').strip("'")
                if field:
                    actions.append({"action": action, "field": field, "value": ""})
                continue
            value = (m.group(1) or "").strip()
            field = (m.group(2) or "").strip().strip('"').strip("'")
            if value and field:
                actions.append({"action": action, "field": field, "value": value})
    # Deduplicate while preserving order.
    seen = set()
    deduped = []
    for item in actions:
        key = (item.get("action"), item.get("field"), item.get("value"))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped
def _extract_story_url_expectations(story_text: str) -> list[dict]:
    if not story_text:
        return []
    triggers = (
        "verify url",
        "validate url",
        "url contains",
        "url should contain",
        "should navigate to",
        "navigate to",
        "navigated to",
        "redirected to",
        "redirects to",
        "should redirect to",
    )
    collected: list[dict] = []
    for line in _iter_story_lines(story_text):
        raw = (line or "").strip()
        lowered = raw.lower()
        if not any(t in lowered for t in triggers):
            continue
        quoted = _extract_quoted_strings(raw)
        url_match = re.search(r"(https?://[^\s\"'<>]+)", raw)
        if quoted:
            for val in quoted:
                collected.append({"value": val})
        elif url_match:
            collected.append({"value": url_match.group(1)})
        else:
            m = re.search(r"\bto\s+([^\s,;]+)", raw, re.IGNORECASE)
            if m:
                collected.append({"value": m.group(1)})
    seen = set()
    deduped = []
    for item in collected:
        val = (item.get("value") or "").strip()
        if not val or val in seen:
            continue
        seen.add(val)
        deduped.append({"value": val})
    return deduped


def _extract_story_title_expectations(story_text: str) -> list[dict]:
    if not story_text:
        return []
    triggers = (
        "verify title",
        "page title should be",
        "title should be",
        "should have title",
        "title contains",
        "tittle contains",
        "check the title",
        "check the tittle",
    )
    collected: list[dict] = []
    for line in _iter_story_lines(story_text):
        raw = (line or "").strip()
        lowered = raw.lower()
        if "job title" in lowered or "title field" in lowered:
            continue
        if not any(t in lowered for t in triggers):
            continue
        quoted = _extract_quoted_strings(raw)
        contains_mode = "contains" in lowered
        if quoted:
            for val in quoted:
                collected.append({"value": val, "exact": not contains_mode})
        else:
            m = re.search(
                r"(?:title\s+should\s+be|verify\s+title|page\s+title\s+should\s+be)\s+(.+)$",
                raw,
                re.IGNORECASE,
            )
            if m:
                collected.append({"value": m.group(1).strip(), "exact": False})
    seen = set()
    deduped = []
    for item in collected:
        val = (item.get("value") or "").strip()
        if not val or val in seen:
            continue
        seen.add(val)
        deduped.append(item)
    return deduped


def reorder_scroll_and_expect_by_story(code: str, story_text: str) -> str:
    """
    Ensure any scroll_into_view_if_needed for a story target happens BEFORE
    the corresponding visibility expectation for the same text.
    """
    if not code or not story_text:
        return code
    targets = _extract_story_scroll_targets(story_text)
    if not targets:
        return code

    lines = code.splitlines(True)
    func_indices = [i for i, l in enumerate(lines) if re.match(r"^\s*def\s+test_[A-Za-z0-9_]+\s*\(", l)]
    if not func_indices:
        return code
    func_indices.append(len(lines))

    for f in range(len(func_indices) - 1):
        start = func_indices[f]
        end = func_indices[f + 1]
        block = lines[start:end]

        for target in targets:
            target_re = re.compile(
                rf"get_by_text\(\s*(['\"])({re.escape(target)})\1[^)]*\)",
                re.IGNORECASE,
            )
            scroll_idx = None
            expect_idx = None
            for i, line in enumerate(block):
                if scroll_idx is None and "scroll_into_view_if_needed" in line and target_re.search(line):
                    scroll_idx = i
                if expect_idx is None and "expect(" in line and target_re.search(line):
                    expect_idx = i
            if scroll_idx is None or expect_idx is None:
                continue
            if expect_idx < scroll_idx:
                scroll_line = block.pop(scroll_idx)
                block.insert(expect_idx, scroll_line)

        lines[start:end] = block

    return "".join(lines)


def remove_ai_analyzed_comments(code: str) -> str:
    if not code:
        return code
    out_lines = []
    for line in code.splitlines(True):
        if "AI-analyzed tags" in line:
            continue
        out_lines.append(line)
    return "".join(out_lines)


def _strip_step_comments(code: str) -> str:
    if not code:
        return code
    out_lines: list[str] = []
    for line in code.splitlines(True):
        if re.match(r"^\s*#\s*(click|right|double|verify|enter|fill|select|assert|expect|then|and|given)\b", line, re.IGNORECASE):
            continue
        out_lines.append(line)
    return "".join(out_lines)


def _action_stem(name: str) -> str:
    base = name or ""
    for prefix in ("enter_", "fill_", "type_", "select_"):
        if base.startswith(prefix):
            return base[len(prefix) :]
    return base


def _assert_stem(name: str) -> str:
    base = name or ""
    if base.startswith("assert_"):
        base = base[len("assert_") :]
    return _action_stem(base)


def remove_redundant_assertions(code: str) -> str:
    """
    Drop duplicate assert_* lines unless a new value was entered since the last assert.
    """
    out_lines: List[str] = []
    last_action_value: dict[str, str] = {}
    last_assert_value: dict[str, str] = {}

    for line in code.splitlines(True):
        enter_match = METHOD_CALL_RE.match(line)
        if enter_match:
            _, method_name, value_expr = enter_match.groups()
            value_key = value_expr.strip()
            stem = _action_stem(method_name)
            if stem:
                last_action_value[stem] = value_key
            out_lines.append(line)
            continue

        assert_match = ASSERT_CALL_RE.match(line)
        if assert_match:
            _, assert_target, value_expr = assert_match.groups()
            value_key = value_expr.strip()
            stem = _assert_stem(assert_target)
            if stem:
                # Only keep the first assert for the same value since the last action
                if last_assert_value.get(stem) == value_key:
                    continue
                if last_action_value.get(stem) == value_key:
                    last_assert_value[stem] = value_key
            out_lines.append(line)
            continue

        out_lines.append(line)

    return "".join(out_lines)


def remove_duplicate_assert_lines(code: str) -> str:
    """
    Drop duplicate assert_* lines even if separated by blank lines/comments.
    """
    out_lines: list[str] = []
    prev_assert = None
    for line in code.splitlines(True):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            out_lines.append(line)
            continue
        if stripped.startswith("assert_"):
            normalized = re.sub(r"\s+", "", stripped)
            if normalized == prev_assert:
                continue
            prev_assert = normalized
        else:
            prev_assert = None
        out_lines.append(line)
    return "".join(out_lines)


def remove_duplicate_expectation_calls(code: str) -> str:
    """
    Drop duplicate expectation-style lines within the same test block.
    Targets POM visibility calls and expect(...).to_* expectations.
    """
    if not code:
        return code

    lines = code.splitlines(True)
    func_indices = [i for i, l in enumerate(lines) if re.match(r"^\s*def\s+test_[A-Za-z0-9_]+\s*\(", l)]
    if not func_indices:
        return code
    func_indices.append(len(lines))

    is_visible_re = re.compile(r"^\s*is_[A-Za-z0-9_]+_visible\(\s*page\s*\)\s*$")
    expect_re = re.compile(r"^\s*expect\(.+\)\.to_[A-Za-z0-9_]+\(.+\)\s*$")

    for f in range(len(func_indices) - 1):
        start = func_indices[f]
        end = func_indices[f + 1]
        block = lines[start:end]
        seen: set[str] = set()
        new_block: list[str] = []
        for line in block:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                new_block.append(line)
                continue
            if is_visible_re.match(stripped) or expect_re.match(stripped):
                normalized = re.sub(r"\s+", "", stripped)
                if normalized in seen:
                    continue
                seen.add(normalized)
            new_block.append(line)
        lines[start:end] = new_block

    return "".join(lines)


def _remove_redundant_visibility_calls(code: str) -> str:
    if not code:
        return code
    out_lines: list[str] = []
    prev_nonempty = ""
    prev_assert_name = ""
    for line in code.splitlines(True):
        stripped = line.strip()
        if not stripped:
            out_lines.append(line)
            continue
        assert_match = re.match(r"assert\s+(is_[A-Za-z0-9_]+_visible)\(\s*page\s*\)", stripped)
        if assert_match:
            prev_assert_name = assert_match.group(1)
            prev_nonempty = stripped
            out_lines.append(line)
            continue
        call_match = re.match(r"(is_[A-Za-z0-9_]+_visible)\(\s*page\s*\)\s*$", stripped)
        if call_match and prev_assert_name and call_match.group(1) == prev_assert_name:
            continue
        if "to_be_visible" in stripped and prev_assert_name:
            if prev_nonempty.startswith("assert ") and prev_assert_name in prev_nonempty:
                continue
        prev_nonempty = stripped
        prev_assert_name = ""
        out_lines.append(line)
    return "".join(out_lines)


def _remove_generic_alert_status_expectations(code: str, story_text: str) -> str:
    if not code:
        return code
    lowered = (story_text or "").lower()
    if any(k in lowered for k in ("alert", "error", "invalid", "status", "warning", "fail", "failed")):
        return code
    out_lines: list[str] = []
    for line in code.splitlines(True):
        if "get_by_role(\"alert\"" in line or "get_by_role(\"status\"" in line:
            continue
        out_lines.append(line)
    return "".join(out_lines)


def _normalize_safe_drag_and_drop_calls(code: str) -> str:
    if not code or "safe_drag_and_drop" not in code:
        return code

    def _split_args(arg_str: str) -> list[str]:
        args: list[str] = []
        buf: list[str] = []
        depth = 0
        in_str = False
        str_ch = ""
        i = 0
        while i < len(arg_str):
            ch = arg_str[i]
            if in_str:
                buf.append(ch)
                if ch == str_ch and (i == 0 or arg_str[i - 1] != "\\"):
                    in_str = False
                i += 1
                continue
            if ch in ("'", "\""):
                in_str = True
                str_ch = ch
                buf.append(ch)
                i += 1
                continue
            if ch in "([{":
                depth += 1
                buf.append(ch)
                i += 1
                continue
            if ch in ")]}":
                depth = max(0, depth - 1)
                buf.append(ch)
                i += 1
                continue
            if ch == "," and depth == 0:
                args.append("".join(buf).strip())
                buf = []
                i += 1
                continue
            buf.append(ch)
            i += 1
        if buf:
            args.append("".join(buf).strip())
        return args

    def _looks_like_locator(expr: str) -> bool:
        expr = (expr or "").strip()
        if not expr:
            return False
        return any(
            token in expr
            for token in (
                ".locator(",
                "page.locator(",
                ".get_by_",
                "page.get_by_",
                ".first",
                ".nth(",
            )
        )

    out_lines: list[str] = []
    for line in code.splitlines(True):
        if "safe_drag_and_drop(" not in line:
            out_lines.append(line)
            continue
        indent = re.match(r"^(\s*)", line).group(1)
        call_match = re.search(r"safe_drag_and_drop\((.*)\)\s*$", line.strip())
        if not call_match:
            out_lines.append(line)
            continue
        raw_args = call_match.group(1)
        args = _split_args(raw_args)
        if len(args) < 2:
            out_lines.append(line)
            continue
        src = args[0]
        tgt = args[1]
        if not _looks_like_locator(src):
            src = f"page.get_by_text({src}, exact=True)"
        if not _looks_like_locator(tgt):
            tgt = f"page.get_by_text({tgt}, exact=True)"
        new_args = [src, tgt] + args[2:]
        out_lines.append(f"{indent}safe_drag_and_drop({', '.join(new_args)})\n")
    return "".join(out_lines)


def _clean_func_body_for_story(func_body: str, story_text: str, method_map: Optional[dict] = None) -> str:
    if not func_body:
        return func_body
    wrapped = "def test_tmp(page):\n" + textwrap.indent(textwrap.dedent(func_body), "    ")
    wrapped = _strip_step_comments(wrapped)
    wrapped = remove_ai_analyzed_comments(wrapped)
    if method_map:
        has_enter_captcha = False
        for methods in method_map.values():
            for method in methods or []:
                name = _extract_method_name(method)
                if name == "enter_captcha":
                    has_enter_captcha = True
                    break
            if has_enter_captcha:
                break
        if re.search(r"captcha", story_text or "", re.I):
            captcha_input_re = re.compile(r"^(\s*)input\(\s*([\"']).*captcha.*\2\s*\)\s*$", re.I)
            new_lines: list[str] = []
            for line in wrapped.splitlines(True):
                match = captcha_input_re.match(line.strip())
                if match:
                    indent = re.match(r"^(\s*)", line).group(1)
                    new_lines.append(
                        f"{indent}page.wait_for_timeout(int(os.getenv(\"SMARTAI_CAPTCHA_WAIT_MS\", \"15000\")))\n"
                    )
                    if has_enter_captcha:
                        new_lines.append(
                            f"{indent}enter_captcha(page, timeout_ms=int(os.getenv(\"SMARTAI_CAPTCHA_TIMEOUT_MS\", \"15000\")))\n"
                        )
                    continue
                new_lines.append(line)
            wrapped = "".join(new_lines)
            captcha_assert_re = re.compile(r"^(\s*)assert_.*captcha.*_visible\s*\(\s*page\s*\)\s*$", re.I)
            new_lines = []
            for line in wrapped.splitlines(True):
                if captcha_assert_re.match(line.strip()):
                    indent = re.match(r"^(\s*)", line).group(1)
                    new_lines.append(
                        f"{indent}page.wait_for_timeout(int(os.getenv(\"SMARTAI_CAPTCHA_WAIT_MS\", \"15000\")))\n"
                    )
                    if has_enter_captcha:
                        new_lines.append(
                            f"{indent}enter_captcha(page, timeout_ms=int(os.getenv(\"SMARTAI_CAPTCHA_TIMEOUT_MS\", \"15000\")))\n"
                        )
                    continue
                new_lines.append(line)
            wrapped = "".join(new_lines)
        if has_enter_captcha:
            new_lines: list[str] = []
            wait_re = re.compile(r"^_?wait_for_captcha\(\s*page(?:\s*,.*)?\)\s*$")
            for line in wrapped.splitlines(True):
                if wait_re.match(line.strip()):
                    indent = re.match(r"^(\s*)", line).group(1)
                    new_lines.append(
                        f"{indent}page.wait_for_timeout(int(os.getenv(\"SMARTAI_CAPTCHA_WAIT_MS\", \"15000\")))\n"
                    )
                    new_lines.append(
                        f"{indent}enter_captcha(page, timeout_ms=int(os.getenv(\"SMARTAI_CAPTCHA_TIMEOUT_MS\", \"20000\")))\n"
                    )
                else:
                    new_lines.append(line)
            wrapped = "".join(new_lines)
        if has_enter_captcha and re.search(r"captcha", story_text or "", re.I):
            if not re.search(r"\benter_captcha\(", wrapped) and not re.search(
                r"\bwait_for_captcha\(", wrapped
            ) and not re.search(r"_wait_for_captcha\(", wrapped):
                lines = wrapped.splitlines(True)
                insert_at = None
                for i, line in enumerate(lines):
                    if re.search(r"\bclick_sign_in\(", line):
                        insert_at = i
                        break
                if insert_at is None:
                    for i, line in enumerate(lines):
                        if re.search(r"\benter_password\(", line):
                            insert_at = i + 1
                if insert_at is None:
                    for i, line in enumerate(lines):
                        if re.search(r"\benter_[a-zA-Z0-9_]*\(", line):
                            insert_at = i + 1
                if insert_at is None:
                    insert_at = len(lines)
                indent = "    "
                if lines:
                    if insert_at < len(lines):
                        indent = re.match(r"^(\s*)", lines[insert_at]).group(1)
                    else:
                        indent = re.match(r"^(\s*)", lines[-1]).group(1)
                lines.insert(
                    insert_at,
                    f"{indent}enter_captcha(page)\n",
                )
                wrapped = "".join(lines)
    wrapped = reorder_scroll_and_expect_by_story(wrapped, story_text)
    wrapped = _inject_explicit_page_load_waits(wrapped, story_text)
    wrapped = _normalize_safe_drag_and_drop_calls(wrapped)
    wrapped = remove_duplicate_assert_lines(wrapped)
    wrapped = remove_duplicate_expectation_calls(wrapped)
    wrapped = remove_redundant_assertions(wrapped)
    wrapped = _remove_redundant_visibility_calls(wrapped)
    wrapped = _remove_generic_alert_status_expectations(wrapped, story_text)
    if not _extract_story_title_expectations(story_text):
        wrapped = "\n".join(
            line for line in wrapped.splitlines() if "to_have_title(" not in line
        ) + ("\n" if wrapped.endswith("\n") else "")
    if not _extract_story_url_expectations(story_text):
        wrapped = "\n".join(
            line for line in wrapped.splitlines() if "to_have_url(" not in line
        ) + ("\n" if wrapped.endswith("\n") else "")
    check_fields = [item.get("field") for item in _extract_story_field_inputs(story_text) if item.get("action") == "check"]
    if check_fields:
        new_lines: list[str] = []
        for line in wrapped.splitlines(True):
            replaced = False
            for field in check_fields:
                if not field:
                    continue
                if "select_" in line and json.dumps(field) in line:
                    indent = re.match(r"^(\s*)", line).group(1)
                    new_lines.append(f"{indent}page.get_by_label({json.dumps(field)}, exact=True).check()\n")
                    replaced = True
                    break
                if ".select_option" in line and json.dumps(field) in line:
                    indent = re.match(r"^(\s*)", line).group(1)
                    new_lines.append(f"{indent}page.get_by_label({json.dumps(field)}, exact=True).check()\n")
                    replaced = True
                    break
            if not replaced:
                new_lines.append(line)
        wrapped = "".join(new_lines)
    if method_map:
        wrapped = _map_generic_helpers_to_pom(wrapped, method_map)
        wrapped = _rewrite_toggle_ensure_calls(wrapped, method_map)
        wrapped = _qualify_pom_method_calls(wrapped, method_map)
        wrapped = _rewrite_calendar_popup_numeric_clicks(wrapped)
        wrapped = _ensure_page_arg_for_pom_calls(wrapped, method_map)
        wrapped = _remove_stray_explanatory_prose(wrapped)
    block = _extract_first_test_function_block(wrapped)
    if not block:
        return func_body
    lines = block.splitlines()
    if lines and lines[0].lstrip().startswith("def "):
        lines = lines[1:]
    cleaned = textwrap.dedent("\n".join(lines)).strip("\n")
    if func_body.endswith("\n"):
        return cleaned + "\n"
    return cleaned


# ----------------------------------------------------------------------
# Split generated tests by category
# ----------------------------------------------------------------------
def _split_generated_tests_by_category(code: str) -> dict[str, list[str]]:
    """
    Partition generated test code into UI, security, and accessibility buckets.
    Only named test functions (def test_*(...):) are considered.
    """
    functions: List[tuple[str, str]] = []
    current_name: Optional[str] = None
    current_lines: List[str] = []

    for line in code.splitlines(True):
        m = re.match(r"^def\s+(test_[a-zA-Z0-9_]+)\(([^)]*)\)\s*:", line)
        if m:
            if current_name and current_lines:
                functions.append((current_name, "".join(current_lines)))
            current_name = m.group(1)
            current_lines = [line]
            continue
        if current_name:
            current_lines.append(line)

    if current_name and current_lines:
        functions.append((current_name, "".join(current_lines)))

    grouped = {"ui": [], "security": [], "accessibility": []}
    for name, body in functions:
        if name.startswith("test_security"):
            grouped["security"].append(body)
        elif name.startswith("test_accessibility") or name.startswith("test_a11y"):
            grouped["accessibility"].append(body)
        else:
            grouped["ui"].append(body)
    return grouped


# ----------------------------------------------------------------------
# File / DB helpers
# ----------------------------------------------------------------------
def create_default_test_data(
    run_folder: Path,
    method_map_full: Optional[dict] = None,
    test_data_json: Optional[str] = None,
) -> None:
    """
    Create or write test data for the run. If `test_data_json` is provided it will be used (must be JSON string).
    Otherwise a minimal scaffold is created by scanning method_map_full for common keys.
    """
    data = {}
    if test_data_json:
        try:
            data = json.loads(test_data_json)
        except Exception:
            data = {}
    else:
        if method_map_full:
            for page_key, _methods in method_map_full.items():
                data[page_key] = {}
        if not data:
            data = {"__meta__": {}}

    data_dir = Path(run_folder) / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "__init__.py").touch()
    with open(data_dir / "test_data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def _persist_directory_to_db(
    src_dir: Path,
    target_dir: Path,
    project_id: int,
    organization_id: int,
) -> None:
    if not target_dir.exists() or not target_dir.is_dir():
        return

    with session_scope() as db:
        project = (
            db.query(Project)
            .filter(
                Project.id == project_id,
                Project.organization_id == organization_id,
            )
            .first()
        )
        if not project:
            return
        storage = DatabaseBackedProjectStorage(project, src_dir, db)
        for path in sorted(target_dir.rglob("*.py")):
            if not path.is_file():
                continue
            try:
                relative = path.relative_to(src_dir).as_posix()
            except ValueError:
                continue
            try:
                content = path.read_text(encoding="utf-8")
            except Exception:
                continue
            storage.write_file(relative, content, "utf-8")


def _extract_class_methods_from_page_text(source: str) -> List[str]:
    methods: List[str] = []
    current_class = None
    property_pending = False
    class_re = re.compile(r"^\s*class\s+([A-Za-z_][A-Za-z0-9_]*)\b")
    def_re = re.compile(r"^\s*def\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(([^)]*)\)\s*:")
    for line in source.splitlines():
        class_match = class_re.match(line)
        if class_match:
            name = class_match.group(1)
            if name == "BasePage" or not name.endswith("Page"):
                current_class = None
            else:
                current_class = name
            property_pending = False
            continue
        if current_class is None:
            continue
        if line.strip().startswith("@property"):
            property_pending = True
            continue
        def_match = def_re.match(line)
        if not def_match:
            continue
        if property_pending:
            property_pending = False
            continue
        method_name = def_match.group(1)
        if method_name in ("__init__", "open", "goto") or method_name.startswith("_"):
            continue
        params = def_match.group(2).strip()
        methods.append(f"def {method_name}({params}):")
        property_pending = False
    return methods


def extract_method_names_from_file(file_path: Path) -> List[str]:
    try:
        source = file_path.read_text(encoding="utf-8")
    except Exception:
        return []
    if file_path.name.endswith("_page.py") or file_path.name.endswith("_page_methods.py"):
        try:
            tree = ast.parse(source)
        except Exception:
            return _extract_class_methods_from_page_text(source)
        methods: List[str] = []
        for node in tree.body:
            if not isinstance(node, ast.ClassDef):
                continue
            if node.name == "BasePage" or not node.name.endswith("Page"):
                continue
            for item in node.body:
                if not isinstance(item, ast.FunctionDef):
                    continue
                if item.name in ("__init__", "open", "goto") or item.name.startswith("_"):
                    continue
                is_property = any(
                    isinstance(dec, ast.Name) and dec.id == "property"
                    for dec in item.decorator_list
                )
                if is_property:
                    continue
                arg_names = [a.arg for a in item.args.args]
                signature = ", ".join(arg_names)
                methods.append(f"def {item.name}({signature}):")
        if methods:
            return methods
        if file_path.name.endswith("_page_methods.py"):
            method_names: List[str] = []
            for line in source.splitlines():
                m = re.match(r"def\s+[a-zA-Z_][a-zA-Z0-9_]*\s*\([^\)]*\):", line)
                if m:
                    name = line.strip().split("(", 1)[0].replace("def ", "").strip()
                    if name.startswith("_"):
                        continue
                    method_names.append(line.strip())
            return method_names
        return methods

    method_names: List[str] = []
    for line in source.splitlines():
        m = re.match(r"def\s+[a-zA-Z_][a-zA-Z0-9_]*\s*\([^\)]*\):", line)
        if m:
            name = line.strip().split("(", 1)[0].replace("def ", "").strip()
            if name.startswith("_"):
                continue
            method_names.append(line.strip())
    return method_names


def get_all_page_methods(pages_dir: Path) -> dict:
    page_method_map: dict = {}
    method_files = list(Path(pages_dir).glob("*_page_methods.py"))
    if method_files:
        for py_file in method_files:
            page_name = py_file.stem.replace("_page_methods", "")
            page_method_map[page_name] = extract_method_names_from_file(py_file)
        return page_method_map

    for py_file in Path(pages_dir).glob("*_page.py"):
        page_name = py_file.stem.replace("_page", "")
        page_method_map.setdefault(page_name, [])
        page_method_map[page_name].extend(extract_method_names_from_file(py_file))
    return page_method_map


def next_index(target_dir: Path, pattern: str = "test_{}.py") -> int:
    files = list(target_dir.glob(pattern.format("*")))
    indices = [int(m.group(1)) for f in files if (m := re.match(r".*_(\d+)\.", f.name))]
    return max(indices, default=0) + 1


def _extract_ts_index_from_names(names: list[str]) -> Optional[int]:
    for name in names or []:
        m = re.search(r"\bTS_(\d{3})\b", name or "")
        if m:
            return int(m.group(1))
    return None


def _next_ts_index_for_project(project_id: int) -> int:
    try:
        with session_scope() as db:
            rows = (
                db.query(TestCaseMetadata.test_name)
                .filter(TestCaseMetadata.project_id == project_id)
                .all()
            )
            distinct_story_count = (
                db.query(TestCaseMetadata.user_story)
                .filter(TestCaseMetadata.project_id == project_id)
                .filter(TestCaseMetadata.user_story.isnot(None))
                .filter(TestCaseMetadata.user_story != "")
                .distinct()
                .count()
            )
    except Exception:
        return 1
    max_idx = 0
    for (name,) in rows or []:
        m = re.search(r"\bTS_(\d{3})\b", name or "")
        if m:
            max_idx = max(max_idx, int(m.group(1)))
    if max_idx:
        return max_idx + 1
    if distinct_story_count:
        return distinct_story_count + 1
    return 1


def _test_filename_for_key(
    story: str,
    story_index: int,
    category: str,
    db: Optional[Session] = None,
    project_id: Optional[int] = None,
) -> str:
    if not isinstance(story, str):
        try:
            legacy_id = int(story)
            return f"test_{legacy_id}_{story_index:03d}_{category}.py"
        except Exception:
            story = str(story)
    slug = _infer_script_slug(story, category, db=db, project_id=project_id)
    if category == "ui":
        base = f"test_{slug}"
    else:
        base = f"test_{slug}_{category}"
    if story_index > 1:
        base = f"{base}_{story_index:03d}"
    return f"{base}.py"


# ----------------------------------------------------------------------
# Chroma normalization: IMPORTANT FIX
# Ensures we always write FLAT metadata objects into before_enrichment.json
# (not {"id":..., "document":..., "metadata": {...}}).
# ----------------------------------------------------------------------
def _normalize_chroma_meta(meta: object, fallback_id: Optional[str] = None) -> dict:
    """
    Chroma metadata can arrive in multiple shapes:
    1) dict with the real metadata directly
    2) dict like {"id":..., "document":..., "metadata": {...}}
    3) list/tuple where one item is a dict

    We ALWAYS return the FLAT metadata dict (the inner "metadata" if present),
    and strip noisy keys so before_enrichment.json is stable and clean.
    """
    # Unwrap list/tuple shapes
    if isinstance(meta, (list, tuple)):
        for item in meta:
            if isinstance(item, dict):
                meta = item
                break

    if not isinstance(meta, dict):
        return {}

    # Unwrap export shape: {"id":..., "document":..., "metadata": {...}}
    if "metadata" in meta and isinstance(meta.get("metadata"), dict):
        meta = meta["metadata"]

    if not isinstance(meta, dict):
        return {}

    # Remove noisy/unstable keys (optional but recommended)
    drop_keys = {"project_id", "id", "document", "embedding", "distance", "score"}
    cleaned = {k: v for k, v in meta.items() if k not in drop_keys}

    # Ensure element_id is always present
    if fallback_id and not cleaned.get("element_id"):
        cleaned["element_id"] = fallback_id

    return cleaned


# ----------------------------------------------------------------------
# LLM generation functions
# ----------------------------------------------------------------------
def generate_security_test_code_from_methods(
    user_story: str,
    method_map: dict,
    page_names: List[str],
    site_url: str,
    run_folder: Path,
    project_src_dir: Path,
    db: Optional[Session] = None,
    project_id: Optional[int] = None,
) -> str:
    story_steps = _extract_story_steps_structured(user_story)
    dynamic_steps = _story_steps_to_prompt_lines(story_steps)
    prompt = build_security_prompt(
        story_block=user_story,
        method_map=method_map,
        page_names=page_names,
        site_url=site_url,
        project_src_dir=project_src_dir,
        dynamic_steps=dynamic_steps,
    )
    model_name = os.getenv("AI_MODEL_NAME", "gpt-4o")
    cache_dir = _generation_cache_dir(run_folder)
    cache_key = _generation_cache_key(
        user_story=user_story,
        test_type="security",
        site_url=site_url,
        method_map=method_map,
        page_names=page_names,
        prompt=prompt,
        model_name=model_name,
    )
    cached_output = _load_cached_generation(cache_dir, cache_key)

    prompt_dir = run_folder / "logs" / "prompts"
    prompt_dir.mkdir(parents=True, exist_ok=True)
    i = 1
    while True:
        prompt_file = prompt_dir / f"security_prompt_{i}.md"
        if not prompt_file.exists():
            break
        i += 1
    prompt_file.write_text(prompt, encoding="utf-8")

    output_dir = run_folder / "logs" / "test_output"
    output_dir.mkdir(parents=True, exist_ok=True)
    i = 1
    while True:
        output_file = output_dir / f"security_test_output_{i}.py"
        if not output_file.exists():
            break
        i += 1

    if cached_output:
        clean_output = cached_output
    else:
        clean_output = _call_llm_with_retry(
            prompt,
            model_name,
            db=db,
            project_id=project_id,
            feature="api_generation",
        )

        try:
            if site_url and str(site_url).strip():
                goto_literal = json.dumps(site_url)
                clean_output = re.sub(r"page\.goto\([^\)]*\)", f"page.goto({goto_literal})", clean_output)
        except Exception:
            pass
        clean_output = _inject_security_navigation_and_submit(clean_output, method_map, user_story)
        clean_output = _sanitize_security_numeric_fields(clean_output, method_map)
        clean_output = _split_inline_calls(clean_output)
        _store_cached_generation(
            cache_dir,
            cache_key,
            code=clean_output,
            meta={
                "story": user_story,
                "test_type": "security",
                "site_url": site_url,
                "model": model_name,
                "method_map_hash": _stable_hash(
                    json.dumps(_normalize_method_map(method_map), sort_keys=True, ensure_ascii=True)
                ),
                "prompt_hash": _stable_hash(prompt or ""),
            },
        )

    output_file.write_text(clean_output, encoding="utf-8")
    return clean_output


def generate_accessibility_test_code_from_methods(
    user_story: str,
    method_map: dict,
    page_names: List[str],
    site_url: str,
    run_folder: Path,
    project_src_dir: Path,
    db: Optional[Session] = None,
    project_id: Optional[int] = None,
) -> str:
    story_steps = _extract_story_steps_structured(user_story)
    dynamic_steps = _story_steps_to_prompt_lines(story_steps)
    prompt = build_accessibility_prompt(
        story_block=user_story,
        method_map=method_map,
        page_names=page_names,
        site_url=site_url,
        project_src_dir=project_src_dir,
        dynamic_steps=dynamic_steps,
    )
    model_name = os.getenv("AI_MODEL_NAME", "gpt-4o")
    cache_dir = _generation_cache_dir(run_folder)
    cache_key = _generation_cache_key(
        user_story=user_story,
        test_type="accessibility",
        site_url=site_url,
        method_map=method_map,
        page_names=page_names,
        prompt=prompt,
        model_name=model_name,
    )
    cached_output = _load_cached_generation(cache_dir, cache_key)

    prompt_dir = run_folder / "logs" / "prompts"
    prompt_dir.mkdir(parents=True, exist_ok=True)
    i = 1
    while True:
        prompt_file = prompt_dir / f"accessibility_prompt_{i}.md"
        if not prompt_file.exists():
            break
        i += 1
    prompt_file.write_text(prompt, encoding="utf-8")

    if cached_output:
        clean_output = cached_output
    else:
        clean_output = _call_llm_with_retry(
            prompt,
            model_name,
            require_a11y=True,
            db=db,
            project_id=project_id,
            feature="hybrid_generation",
        )

        try:
            if site_url and str(site_url).strip():
                goto_literal = json.dumps(site_url)
                clean_output = re.sub(r"page\.goto\([^\)]*\)", f"page.goto({goto_literal})", clean_output)
        except Exception:
            pass
        _store_cached_generation(
            cache_dir,
            cache_key,
            code=clean_output,
            meta={
                "story": user_story,
                "test_type": "accessibility",
                "site_url": site_url,
                "model": model_name,
                "method_map_hash": _stable_hash(
                    json.dumps(_normalize_method_map(method_map), sort_keys=True, ensure_ascii=True)
                ),
                "prompt_hash": _stable_hash(prompt or ""),
            },
        )

    output_dir = run_folder / "logs" / "test_output"
    output_dir.mkdir(parents=True, exist_ok=True)
    i = 1
    while True:
        output_file = output_dir / f"accessibility_test_output_{i}.py"
        if not output_file.exists():
            break
        i += 1
    output_file.write_text(clean_output, encoding="utf-8")
    return clean_output


def generate_test_code_from_methods(
    user_story: str,
    method_map: dict,
    page_names: List[str],
    site_url: str,
    run_folder: Path,
    project_src_dir: Path,
    strict_story_only: Optional[bool] = None,
    allow_direct_selectors: Optional[bool] = None,
    post_method_map: Optional[dict] = None,
    db: Optional[Session] = None,
    project_id: Optional[int] = None,
) -> tuple[str, bool]:
    def _force_site_url(code: str, url: str) -> str:
        if not url:
            return code
        goto_literal = json.dumps(url)
        return re.sub(r"page\.goto\([^\)]*\)", f"page.goto({goto_literal})", code)

    def _rewrite_helpers(code: str) -> str:
        code = re.sub(
            r'^\s*page\.get_by_role\("(?:checkbox|radio)",\s*name="([^"]+)"(?:,\s*exact=True)?\)(?:\.first)?\.scroll_into_view_if_needed\(\)\s*$',
            "",
            code,
            flags=re.MULTILINE,
        )
        code = re.sub(
            r"page\.get_by_label\(\"([^\"]+)\"\)\.check\(\)",
            r'check_checkbox(page, "\1")',
            code,
        )
        code = re.sub(
            r"page\.get_by_text\(\"([^\"]+)\"\)\.check\(\)",
            r'check_checkbox(page, "\1")',
            code,
        )
        code = re.sub(
            r"page\.get_by_role\(\"checkbox\", name=\"([^\"]+)\"\)\.check\(\)",
            r'check_checkbox(page, "\1")',
            code,
        )
        code = re.sub(
            r'page\.get_by_role\("(checkbox|radio)",\s*name="([^"]+)"(?:,\s*exact=True)?\)(?:\.first)?\.click\(\)',
            r'check_checkbox(page, "\2")',
            code,
        )
        code = re.sub(
            r"page\.get_by_label\(\"([^\"]+)\"\)\.select_option\(\"([^\"]+)\"\)",
            r'select_dropdown(page, "\1", "\2")',
            code,
        )
        code = re.sub(
            r"page\.get_by_label\(\"([^\"]+)\"\)\.fill\(\"([^\"]*)\"\)",
            r'fill_text(page, "\1", "\2")',
            code,
        )
        code = re.sub(
            r"page\.get_by_placeholder\(\"([^\"]+)\"\)\.fill\(\"([^\"]*)\"\)",
            r'fill_text(page, "\1", "\2")',
            code,
        )
        code = re.sub(
            r"page\.get_by_role\(\"textbox\", name=\"([^\"]+)\"\)\.fill\(\"([^\"]*)\"\)",
            r'fill_text(page, "\1", "\2")',
            code,
        )
        code = re.sub(
            r"page\.get_by_role\(\"button\", name=\"([^\"]+)\"\)\.click\(\)",
            lambda match: _click_helper_for_label(match.group(1)),
            code,
        )
        code = re.sub(
            r"page\.get_by_text\(\"([^\"]+)\"\)\.click\(\)",
            lambda match: _click_helper_for_label(match.group(1)),
            code,
        )
        code = re.sub(
            r"^(?P<indent>\s*)click_button\(\s*page\s*,\s*(?P<label>.+?)\s*\)\s*$",
            lambda match: (
                f"{match.group('indent')}{_click_helper_for_label(_extract_quoted_strings(match.group('label'))[0])}"
                if _extract_quoted_strings(match.group("label"))
                and _is_icon_like_label(_extract_quoted_strings(match.group("label"))[0])
                else match.group(0)
            ),
            code,
            flags=re.MULTILINE,
        )
        return code

    # Keep prompt focused on the exact user story and make every actionable step
    # explicit so the model does not silently skip lines.
    method_map = dict(method_map or {})
    page_names = list(page_names or [])
    story_steps = _extract_story_steps_structured(user_story)
    dynamic_steps = _story_steps_to_prompt_lines(story_steps)

    prompt = build_prompt(
        story_block=user_story,
        method_map=method_map,
        page_names=page_names,
        site_url=site_url,
        dynamic_steps=dynamic_steps,
        project_src_dir=project_src_dir,
    )

    model_name = os.getenv("AI_MODEL_NAME", "gpt-4o")
    cache_dir = _generation_cache_dir(run_folder)
    cache_key = _generation_cache_key(
        user_story=user_story,
        test_type="ui",
        site_url=site_url,
        method_map=method_map,
        page_names=page_names,
        prompt=prompt,
        model_name=model_name,
    )
    cached_output = _load_cached_generation(cache_dir, cache_key)

    prompt_dir = run_folder / "logs" / "prompts"
    prompt_dir.mkdir(parents=True, exist_ok=True)
    i = 1
    while True:
        prompt_file = prompt_dir / f"ui_prompt_{i}.md"
        if not prompt_file.exists():
            break
        i += 1
    prompt_file.write_text(prompt, encoding="utf-8")

    output_dir = run_folder / "logs" / "test_output"
    output_dir.mkdir(parents=True, exist_ok=True)
    i = 1
    while True:
        output_file = output_dir / f"test_output_{i}.py"
        if not output_file.exists():
            break
        i += 1

    if cached_output:
        clean_output = cached_output
    else:
        clean_output = _call_llm_with_retry(
            prompt,
            model_name,
            db=db,
            project_id=project_id,
            feature="ui_generation",
        )

    # Always apply post-processing, even when cached output is used.
    clean_output = _force_site_url(clean_output, site_url)
    clean_output = _rewrite_helpers(clean_output)
    clean_output = _split_inline_calls(clean_output)
    post_map = post_method_map or method_map
    clean_output = _replace_mismatched_input_methods(clean_output, user_story, post_map)
    clean_output = _replace_mismatched_check_methods(clean_output, user_story, post_map)
    clean_output = _replace_select_calls_for_story_checks(clean_output, user_story, post_map)
    clean_output = _map_generic_helpers_to_pom(clean_output, post_map)
    clean_output = _rewrite_toggle_ensure_calls(clean_output, post_map)
    clean_output = _inject_page_object_instances(clean_output, method_map)
    clean_output = _qualify_pom_method_calls(clean_output, method_map)
    clean_output = _rewrite_calendar_popup_numeric_clicks(clean_output)
    clean_output = _ensure_page_arg_for_pom_calls(clean_output, method_map)
    clean_output = _rewrite_missing_page_object_calls(clean_output, method_map)
    clean_output = _remove_stray_explanatory_prose(clean_output)
    clean_output = _normalize_expect_get_by_text(clean_output)
    clean_output = _remove_verification_lines(clean_output)
    clean_output = _fix_try_block_indentation(clean_output)
    clean_output = _fix_function_block_indentation(clean_output)
    clean_output = _drop_stray_numeric_name_on_card(clean_output)

    if not cached_output:
        _store_cached_generation(
            cache_dir,
            cache_key,
            code=clean_output,
            meta={
                "story": user_story,
                "test_type": "ui",
                "site_url": site_url,
                "model": model_name,
                "method_map_hash": _stable_hash(
                    json.dumps(_normalize_method_map(method_map), sort_keys=True, ensure_ascii=True)
                ),
                "prompt_hash": _stable_hash(prompt or ""),
            },
        )

    output_file.write_text(clean_output, encoding="utf-8")
    return clean_output, False


def get_inferred_pages(
    user_story: str,
    method_map_full: dict,
    db: Optional[Session] = None,
    project_id: Optional[int] = None,
    feature: str = "hybrid_generation",
) -> List[str]:
    page_list_str = "\n".join([f"{i+1}. {k.replace('_', ' ')}" for i, k in enumerate(method_map_full.keys())])
    story_block = f'"""{user_story}"""'
    prompt = f"""
You are an expert QA automation engineer.

Given the following available application pages:
{page_list_str}

Here is a user story:
{story_block}

Output ONLY a Python list (in order) of the page keys (use the keys exactly as shown) that must be visited for this story. Do not explain.
"""
    model_name = os.getenv("AI_INFER_MODEL", "gpt-4o")
    result = call_openai(
        model=model_name,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=int(os.getenv("AI_MAX_TOKENS", "4096")),
        temperature=float(os.getenv("AI_TEMPERATURE", "0")),
    )
    log_token_usage(
        db=db,
        project_id=project_id,
        feature=feature,
        usage=result.get("usage"),
        model=result.get("model"),
    )

    output = (result.get("content") or "").strip()
    try:
        inferred_pages = ast.literal_eval(output)
        return [p for p in inferred_pages if p in method_map_full]
    except Exception:
        return list(method_map_full.keys())


# ----------------------------------------------------------------------
# MAIN ENDPOINT (snapshot concept removed)
# ----------------------------------------------------------------------
@router.post("/{project_id}/rag/generate-from-story")
async def generate_from_user_story(
    project_id: int,
    user_story: Optional[str] = Form(None),
    site_url: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    ai_model: Optional[str] = Form(None),
    infer_pages: Optional[bool] = Form(False),
    test_data_json: Optional[str] = Form(None),
    test_type: Optional[str] = Form("ui"),
    include_negative_edge: Optional[bool] = Form(True),
    strict_story_only: Optional[bool] = Form(None),
    jira_key: Optional[str] = Form(None),
    acceptance_criteria: Optional[str] = Form(None),
    selection_mode: Optional[str] = Form(None),  # kept for compatibility (unused now)
    replace_existing: Optional[bool] = Form(False),
    target_script_path: Optional[str] = Form(None),
    target_runner_script_path: Optional[str] = Form(None),
    sheet_name: Optional[str] = Form(None),  
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    request_db = db
    # src_env = os.environ.get("SMARTAI_SRC_DIR")
    # if not src_env:
    #     raise HTTPException(status_code=400, detail="No active project. Start a project first (SMARTAI_SRC_DIR not set).")
    project = get_user_project(db, project_id, current_user)
    ctx = get_project_context(required=True)
    project_paths = _ensure_project_structure(project)
    projectChromaPath= project_paths["chroma_path"]
    run_folder =Path(project_paths["src_dir"])
    pages_dir = run_folder / "pages"
    tests_dir = run_folder / "tests"
    ui_tests_dir = tests_dir / "ui_scripts"
    security_tests_dir = tests_dir / "security_tests"
    accessibility_tests_dir = tests_dir / "accessibility_tests"
    logs_dir = run_folder / "logs"
    meta_dir = run_folder / "metadata"

    all_dirs = [
        pages_dir,
        tests_dir,
        ui_tests_dir,
        security_tests_dir,
        accessibility_tests_dir,
        logs_dir,
        meta_dir,
    ]
    for d in all_dirs:
        d.mkdir(parents=True, exist_ok=True)
        (d / "__init__.py").touch()
    
    # ---------------- Parse incoming user stories ----------------
    stories: List[str] = []
    if file:
        import io

        content = await file.read()
        if file.filename.endswith((".xls", ".xlsx")):
            try:
                xls = pd.ExcelFile(io.BytesIO(content))
                available_sheets = xls.sheet_names or []
                requested_sheet = (sheet_name or "").strip() if isinstance(sheet_name, str) else ""
                if not available_sheets:
                    raise HTTPException(
                        status_code=400,
                        detail="No sheets found in the uploaded Excel file.",
                    )
                if not requested_sheet:
                    sheet_name = available_sheets[0]
                elif requested_sheet.isdigit():
                    sheet_index = int(requested_sheet)
                    if 0 <= sheet_index < len(available_sheets):
                        sheet_name = available_sheets[sheet_index]
                    else:
                        raise HTTPException(
                            status_code=400,
                            detail=(
                                f"Sheet index '{requested_sheet}' out of range. "
                                f"Sheets present: {available_sheets}"
                            ),
                        )
                elif requested_sheet not in available_sheets:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Sheet '{requested_sheet}' not found. Sheets present: {available_sheets}",
                    )
                df = pd.read_excel(io.BytesIO(content), sheet_name=sheet_name)
            except Exception as e:
                raise HTTPException(
                    status_code=400,
                    detail=f"Failed to read '{sheet_name}' sheet from Excel: {str(e)}",
                )
        elif file.filename.endswith(".csv"):
            df = pd.read_csv(io.StringIO(content.decode()))
        else:
            raise HTTPException(status_code=400, detail="Unsupported file type")

        def _normalize_col(name: str) -> str:
            return re.sub(r"[^a-z0-9]+", "", (name or "").strip().lower())

        allowed_cols = {"userstory", "userstories", "story"}
        column_name = None
        for col in df.columns:
            if _normalize_col(str(col)) in allowed_cols:
                column_name = col
                break
        if not column_name and len(df.columns) == 1:
            column_name = df.columns[0]
        if not column_name:
            present = [str(c) for c in df.columns]
            raise HTTPException(
                status_code=400,
                detail=(
                    "Column 'User Story' not found in sheet. "
                    f"Columns present: {present}"
                ),
            )
        stories = df[column_name].dropna().astype(str).tolist()
    elif user_story:
        stories = [user_story]
    else:
        raise HTTPException(status_code=400, detail="Either 'user_story' or 'file' must be provided")

    # Determine site_url: param -> env -> story fallback
    if not site_url:
        site_url = os.getenv("SITE_URL", "")
    story_url = _extract_first_url(stories[0]) if stories else ""
    if story_url:
        site_url = story_url

    ac_list: List[str] = []
    if acceptance_criteria:
        try:
            parsed = json.loads(acceptance_criteria)
            if isinstance(parsed, list):
                ac_list = [str(item) for item in parsed if str(item).strip()]
        except Exception:
            ac_list = []

    inputs_payload: list[dict] = []
    for idx, story in enumerate(stories):
        inputs_payload.append(
            {
                "jira_key": jira_key if idx == 0 else None,
                "user_story": story,
                "acceptance_criteria": ac_list if idx == 0 else [],
                "site_url": site_url,
            }
        )
    inputs_path = meta_dir / "inputs.json"
    with open(inputs_path, "w", encoding="utf-8") as f:
        json.dump(inputs_payload if len(inputs_payload) > 1 else inputs_payload[0], f, indent=2)

    # Optional: set AI model for this request
    if ai_model:
        os.environ["AI_MODEL_NAME"] = ai_model

    # ---------------- Snapshot current chroma metadata -> before_enrichment.json (FLAT objects) ----------------
    collection = get_collection(projectChromaPath ,"element_metadata")
    all_chroma_data = collection.get()
    ids = all_chroma_data.get("ids", []) or []
    metas = all_chroma_data.get("metadatas", []) or []

    all_chroma_metadatas: list[dict] = []
    for _id, m in zip(ids, metas):
        m = _normalize_chroma_meta(m, fallback_id=_id)
        if not m:
            continue

        # Normalize OCR records into your required flat shape ALWAYS
        if (m.get("type") or "").lower() == "ocr":
            page = (m.get("page_name") or "")
            label = (m.get("label_text") or m.get("get_by_text") or "")
            otype = (m.get("ocr_type") or "")
            intent_val = (m.get("intent") or "")
            uname = (m.get("unique_name") or generate_unique_name(page, label, otype, intent_val))

            elem_id = (
                m.get("element_id")
                or _id
                or m.get("ocr_id")
                or uname
            )

            all_chroma_metadatas.append(
                {
                    "page_name": page,
                    "label_text": label,
                    "get_by_text": m.get("get_by_text") or label,
                    "placeholder": m.get("placeholder") or label,
                    "ocr_type": otype,
                    "intent": intent_val,
                    "dom_matched": bool(m.get("dom_matched")) if m.get("dom_matched") is not None else False,
                    "external": bool(m.get("external")) if m.get("external") is not None else False,
                    "type": "ocr",
                    "unique_name": uname,
                    "element_id": elem_id,
                }
            )
        else:
            # Non-OCR records: already flat now
            all_chroma_metadatas.append(m)

    before_file = meta_dir / "before_enrichment.json"
    existing_before = []
    if before_file.exists():
        try:
            existing_before = json.loads(before_file.read_text(encoding="utf-8")) or []
            if not isinstance(existing_before, list):
                existing_before = []
        except Exception:
            existing_before = []
    existing_before = _normalize_metadata_records(existing_before)

    # project_id = _resolve_active_project_id()
    latest_snapshot = _normalize_metadata_records(_latest_upload_snapshot(project_id))

    merged_before = _merge_metadata_records(existing_before, all_chroma_metadatas)
    if latest_snapshot:
        merged_before = _merge_metadata_records(merged_before, latest_snapshot)
    before_file.write_text(json.dumps(merged_before, indent=2), encoding="utf-8")
    # Write per-page before_enrichment_<page>.json snapshots for page-method generation.
    per_page_before: dict[str, list[dict]] = {}
    for record in merged_before:
        if not isinstance(record, dict):
            continue
        page_name = (record.get("page_name") or record.get("page") or "").strip()
        page_key = normalize_page_name(page_name)
        if not page_key:
            continue
        per_page_before.setdefault(page_key, []).append(record)
    for page_key, entries in per_page_before.items():
        try:
            (meta_dir / f"before_enrichment_{page_key}.json").write_text(
                json.dumps(entries, indent=2), encoding="utf-8"
            )
        except Exception:
            pass

    method_map_full = get_all_page_methods(pages_dir)
    project_src_dir = get_smartai_src_dir()
    active_graph = None
    graph_node_name = {}
    try:
        project_root = Path(project_paths["project_root"]).resolve()
        if active_graph:
            for node in active_graph.get("nodes") or []:
                node_id = node.get("id")
                name = node.get("name") or node_id
                if node_id:
                    graph_node_name[node_id] = name
    except Exception:
        active_graph = None

    results: List[dict] = []
    all_path_pages: List[str] = []
    test_file: Optional[Path] = None
    generated_test_names: list[str] = []
    kg_warnings: List[str] = []
 # Snapshot-based update logic removed. Keep simple behavior:
    update_existing_tests = False

    category_dirs = {
        "ui": ui_tests_dir,
        "security": security_tests_dir,
        "accessibility": accessibility_tests_dir,
    }

    if strict_story_only is None:
        strict_story_only = True
    # Normalize test type early (frontend already sends lower-case, but be safe).
    test_type = (test_type or "ui").strip().lower()

    # ---------------- Generate per story ----------------
    story_start_index = _next_ts_index_for_project(project.id)
    for offset, story in enumerate(stories, start=0):
        story_index = story_start_index + offset
        ui_strict_only = bool(strict_story_only) if test_type == "ui" else False
        # Skip KG/page inference: use all available page methods
        path_pages = list(method_map_full.keys())

        if not path_pages:
            continue

        all_path_pages.extend(path_pages)
        sub_method_map = {p: method_map_full[p] for p in path_pages if p in method_map_full}
        sub_method_map = _trim_method_map_for_prompt(story, sub_method_map)

        # generate code by type
        fallback_used = False
        if test_type == "security":
            code = generate_security_test_code_from_methods(
                story,
                sub_method_map,
                path_pages,
                site_url,
                run_folder,
                project_src_dir,
                db=request_db,
                project_id=project_id,
            )
        elif test_type == "accessibility":
            code = generate_accessibility_test_code_from_methods(
                story,
                sub_method_map,
                path_pages,
                site_url,
                run_folder,
                project_src_dir,
                db=request_db,
                project_id=project_id,
            )
        else:
            code, fallback_used = generate_test_code_from_methods(
                story,
                sub_method_map,
                path_pages,
                site_url,
                run_folder,
                project_src_dir,
                strict_story_only=False,
                allow_direct_selectors=(not method_map_full and not merged_before),
                post_method_map=method_map_full,
                db=request_db,
                project_id=project_id,
            )

        # post-fixes
        code = _strip_module_qualified_helpers(code, method_map_full)
        code = _inject_calendar_unique_args(code, merged_before)

        # imports
        page_method_files = sorted(pages_dir.glob("*_page_methods.py"))
        # imports
        page_method_files = sorted(pages_dir.glob("*_page_methods.py"))
        page_pom_files = [] if page_method_files else sorted(pages_dir.glob("*_page.py"))
        page_security_files = sorted(pages_dir.glob("*_security_methods.py"))
        page_accessibility_files = sorted(pages_dir.glob("*_accessibility_methods.py"))
        import_lines = [
            "import pytest",
            "from playwright.sync_api import sync_playwright, expect",
            "import json",
            "from pathlib import Path",
            "from lib.smart_ai import patch_page_with_smartai",
        ]
        for f in page_method_files + page_pom_files + page_security_files + page_accessibility_files:
            import_lines.append(f"from pages.{f.stem} import *")
            if f.stem.endswith("_page_methods"):
                page_key = normalize_page_name(f.stem.replace("_page_methods", ""))
                import_lines.append(f"from pages import {f.stem} as {_page_module_alias_name(page_key)}")

        grouped_tests = _split_generated_tests_by_category(code)

        # only process requested category
        categories_to_process = {test_type} if test_type in grouped_tests else set()
        for category, func_blocks in grouped_tests.items():
            if not func_blocks or category not in categories_to_process:
                continue

            target_dir = category_dirs.get(category)
            if not target_dir:
                continue

            stable_name = _test_filename_for_key(
                story,
                story_index,
                category,
                db=request_db,
                project_id=project_id,
            )

            # Path strategy (deterministic by project/story/category)
            if target_script_path and replace_existing:
                test_path = _resolve_project_test_path(run_folder, target_script_path)
            else:
                test_path = target_dir / stable_name

            processed_func_blocks: list[tuple[Optional[str], str]] = []

            project_id_val = project.id
            script_path_value = ""
            try:
                script_path_value = test_path.relative_to(run_folder).as_posix()
            except Exception:
                script_path_value = str(test_path)

            if func_blocks and not include_negative_edge:
                filtered_blocks = []
                for block in func_blocks:
                    header_match = re.search(
                        r"^\s*def\s+(test_[a-zA-Z0-9_]+)\s*\(",
                        block,
                        flags=re.MULTILINE,
                    )
                    header_name = header_match.group(1).lower() if header_match else ""
                    if "negative" in header_name or "edge" in header_name:
                        continue
                    filtered_blocks.append(block)
                func_blocks = filtered_blocks
            script_stem = test_path.stem if test_path else ""
            prefer_page_methods_style = any("_page_methods import *" in line for line in import_lines)
            with session_scope() as db:
                ts_id = f"TS_{story_index:03d}"
                for idx, func_block in enumerate(func_blocks, start=1):
                    test_name_match = re.search(
                        r"^\s*def\s+(test_[a-zA-Z0-9_]+)\s*\(\s*page\s*\)\s*:",
                        func_block,
                        flags=re.MULTILINE,
                    )
                    if not test_name_match:
                        processed_func_blocks.append((None, func_block))
                        continue

                    test_name = test_name_match.group(1)
                    lowered_name = test_name.lower()
                    scenario = None
                    if "positive" in lowered_name:
                        scenario = "positive"
                    elif "negative" in lowered_name:
                        scenario = "negative"
                    elif "edge" in lowered_name:
                        scenario = "edge"
                    case_index = idx
                    tc_id = f"TC_{case_index:03d}"
                    if script_stem:
                        base_name = f"test_{ts_id}_{tc_id}_{script_stem}"
                    else:
                        base_name = f"test_{ts_id}_{tc_id}_{category}"
                    if scenario:
                        deterministic_test_name = f"{base_name}_{scenario}"
                    else:
                        deterministic_test_name = base_name

                    if test_name != deterministic_test_name:
                        func_block = re.sub(
                            rf"^(\s*def\s+){re.escape(test_name)}(\s*\()",
                            rf"\1{deterministic_test_name}\2",
                            func_block,
                            count=1,
                            flags=re.MULTILINE,
                        )
                        test_name = deterministic_test_name

                    submit_method = _choose_submit_method(sub_method_map)
                    func_block = _improve_negative_edge_scenario(func_block, submit_method)
                    func_block = _map_generic_helpers_to_pom(func_block, method_map_full or sub_method_map)
                    func_block = _rewrite_toggle_ensure_calls(func_block, method_map_full or sub_method_map)
                    func_block = _qualify_pom_method_calls(
                        func_block,
                        sub_method_map,
                        force_page_methods_style=prefer_page_methods_style,
                    )
                    func_block = _rewrite_calendar_popup_numeric_clicks(func_block)
                    func_block = _ensure_page_arg_for_pom_calls(func_block, sub_method_map)
                    func_block = _rewrite_missing_page_object_calls(func_block, sub_method_map)

                    generated_test_names.append(test_name)

                    analysis = analyze_test_case_content(func_block)
                    analyzed_tags = analysis.get("tags") or []
                    analyzed_priority = analysis.get("priority") or "Low"

                    record = None
                    existing_markers: List[str] = []
                    existing_tags: List[str] = []
                    if project_id_val and test_name:
                        try:
                            record = (
                                db.query(TestCaseMetadata)
                                .filter(
                                    TestCaseMetadata.project_id == project_id_val,
                                    TestCaseMetadata.test_name == test_name,
                                )
                                .first()
                            )
                            if record:
                                if isinstance(record.markers, list):
                                    existing_markers = record.markers
                                if isinstance(record.tags, list):
                                    existing_tags = record.tags
                        except Exception as e:
                            print(f"Database query for metadata failed: {e}")

                    combined_tags = list(dict.fromkeys(existing_tags + analyzed_tags))
                    combined_markers = list(dict.fromkeys(existing_markers + combined_tags))
                    if fallback_used and "fallback_used" not in combined_markers:
                        combined_markers.append("fallback_used")

                    if project_id_val and test_name:
                        if record:
                            # Ensure required identifiers exist.
                            if not getattr(record, "case_uuid", None):
                                record.case_uuid = generate_case_uuid()
                            if not getattr(record, "display_name", None):
                                base_display = generate_display_name(category, story, record.case_uuid)
                                record.display_name = ensure_unique_display_name(db, project_id_val, base_display)
                            if replace_existing:
                                record.user_story = story or ""
                                record.auto_testcase = func_block or ""
                                record.test_type = category
                            else:
                                if record.user_story is None:
                                    record.user_story = story or ""
                                elif not record.user_story and story:
                                    record.user_story = story
                                if record.auto_testcase is None:
                                    record.auto_testcase = func_block or ""
                                if record.test_type is None:
                                    record.test_type = category
                            if script_path_value:
                                record.script_path = script_path_value
                            record.markers = combined_markers
                            record.tags = combined_tags
                            record.priority = analyzed_priority
                        else:
                            case_uuid = generate_case_uuid()
                            base_display = generate_display_name(category, story, case_uuid)
                            display_name = ensure_unique_display_name(db, project_id_val, base_display)
                            record = TestCaseMetadata(
                                project_id=project_id_val,
                                case_uuid=case_uuid,
                                display_name=display_name,
                                test_name=test_name,
                                user_story=story or "",
                                auto_testcase=func_block or "",
                                test_type=category,
                                markers=combined_markers,
                                tags=combined_tags,
                                priority=analyzed_priority,
                                script_path=script_path_value or None,
                            )
                            db.add(record)

                    marker_decorators = _format_markers_as_pytest_decorators(combined_markers)
                    updated_func_block = func_block.rstrip() + "\n"

                    if ui_strict_only:
                        if marker_decorators:
                            processed_func_blocks.append(
                                (test_name, f"{chr(10).join(marker_decorators)}\n{updated_func_block}")
                            )
                        else:
                            processed_func_blocks.append((test_name, updated_func_block))
                    elif marker_decorators:
                        processed_func_blocks.append(
                            (test_name, f"{chr(10).join(marker_decorators)}\n{updated_func_block}")
                        )
                    else:
                        processed_func_blocks.append((test_name, updated_func_block))

            function_code = "\n\n".join(block for _, block in processed_func_blocks).strip()
            if not function_code:
                continue
            test_names = [name for name, _block in processed_func_blocks if name]
            function_code, binding_lines = _simplify_page_method_alias_calls(function_code)
            if binding_lines:
                function_code = "\n".join(binding_lines + ["", function_code]).strip()

            category_imports = list(import_lines)
            if category == "accessibility":
                category_imports.append("import re")
                category_imports.append("from services.accessibility_test_utils import run_accessibility_scan")

            story_header = _story_header_line(story)
            content = "\n".join([story_header, "", "\n\n".join(category_imports + [function_code]).rstrip(), ""]).rstrip() + "\n"
            test_path.write_text(content, encoding="utf-8")

            fixed_runner_name = None
            if replace_existing and target_runner_script_path:
                try:
                    fixed_runner_name = Path(target_runner_script_path).name
                except Exception:
                    fixed_runner_name = None
            # Ensure runner name mirrors the test file slug.
            default_runner_name = _runner_name_from_test_path(test_path, category, story)
            runner_path = _generate_execution_script_for_category(
                category=category,
                target_dir=target_dir,
                test_file_path=test_path,
                original_story=story,
                site_url=site_url,
                import_lines=import_lines,
                method_map=method_map_full,
                ts_index=story_index,
                fixed_script_name=fixed_runner_name or default_runner_name,
                project_root=Path(ctx.project_dir).resolve(),
                strict_story_only=ui_strict_only,
                db=request_db,
                project_id=project_id,
            )
            runner_script_path_value = None
            try:
                if runner_path:
                    runner_script_path_value = runner_path.relative_to(run_folder).as_posix()
            except Exception:
                runner_script_path_value = str(runner_path) if runner_path else None

            if runner_script_path_value and project_id_val and test_names:
                try:
                    with session_scope() as runner_db:
                        (
                            runner_db.query(TestCaseMetadata)
                            .filter(
                                TestCaseMetadata.project_id == project_id_val,
                                TestCaseMetadata.test_name.in_(test_names),
                            )
                            .update(
                                {TestCaseMetadata.runner_script_path: runner_script_path_value},
                                synchronize_session=False,
                            )
                        )
                except Exception:
                    pass

            results.append(
                {
                    "Prompt": f" Prompt\n\n1. {story}\nExpected: Success",
                    "auto_testcase": function_code,
                    "test_file_path": str(test_path),
                    "runner_script_path": runner_script_path_value,
                    "original_story": story,
                    "user_story": story,
                    "test_type": category,
                    "test_name": test_names[0] if test_names else None,
                    "test_names": test_names,
                }
            )

            test_file = test_path

    # ---------------- Logs + defaults + persistence ----------------
    log_idx = next_index(logs_dir, "logs_{}.log")
    log_file = logs_dir / f"logs_{log_idx}.log"
    if all_path_pages:
        log_file.write_text("\n".join(all_path_pages), encoding="utf-8")
    else:
        log_file.write_text("No stories were processed.", encoding="utf-8")

    create_default_test_data(run_folder, method_map_full=method_map_full, test_data_json=test_data_json)
    _persist_directory_to_db(run_folder, tests_dir, project.id, project.organization_id)

    unique_generated = list(dict.fromkeys(generated_test_names))

    return {
        "results": results,
        "test_file": str(test_file) if test_file else "",
        "log_file": str(log_file),
        "updated_tests": unique_generated,
        "kg_warnings": kg_warnings,
        "count": len(results),
    }


@router.post("/{project_id}/rag/update-testcase")
async def update_testcase(
    project_id: int,
    test_name: str = Form(...),
    test_file_path: str = Form(...),
    user_story: str = Form(...),
    site_url: Optional[str] = Form(None),
    ai_model: Optional[str] = Form(None),
    infer_pages: Optional[bool] = Form(False),
    strict_story_only: Optional[bool] = Form(None),
    test_type: Optional[str] = Form("ui"),
    jira_key: Optional[str] = Form(None),
    acceptance_criteria: Optional[str] = Form(None),
    target_runner_script_path: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    request_db = db
    project = get_user_project(db, project_id, current_user)
    ctx = get_project_context(required=True)
    project_paths = _ensure_project_structure(project)
    project_chroma_path = project_paths["chroma_path"]
    run_folder = Path(project_paths["src_dir"])
    pages_dir = run_folder / "pages"
    tests_dir = run_folder / "tests"
    logs_dir = run_folder / "logs"
    meta_dir = run_folder / "metadata"

    for d in (pages_dir, tests_dir, logs_dir, meta_dir):
        d.mkdir(parents=True, exist_ok=True)
        (d / "__init__.py").touch()

    if not test_name or not test_name.strip():
        raise HTTPException(status_code=400, detail="test_name is required")

    # Determine site_url: param -> env -> story fallback
    if not site_url:
        site_url = os.getenv("SITE_URL", "")
    story_url = _extract_first_url(user_story)
    if story_url:
        site_url = story_url

    # Optional: set AI model for this request
    if ai_model:
        os.environ["AI_MODEL_NAME"] = ai_model

    method_map_full = get_all_page_methods(pages_dir)
    project_src_dir = get_smartai_src_dir()
    if strict_story_only is None:
        strict_story_only = True
    ui_strict_only = bool(strict_story_only) if test_type == "ui" else False

    # Optional KG-based page selection
    active_graph = None
    graph_node_name = {}
    try:
        project_root = Path(project_paths["project_root"]).resolve()
        if active_graph:
            for node in active_graph.get("nodes") or []:
                node_id = node.get("id")
                name = node.get("name") or node_id
                if node_id:
                    graph_node_name[node_id] = name
    except Exception:
        active_graph = None

    path_pages = []
    if active_graph:
        matched_ids, _unmatched = _match_story_to_graph_nodes(user_story, active_graph)
        for node_id in matched_ids:
            name = graph_node_name.get(node_id, "")
            page_key = normalize_page_name(name)
            if page_key:
                path_pages.append(page_key)
    if not path_pages:
        if infer_pages or os.getenv("AI_INFER_PAGES", "false").lower() in ("1", "true", "yes"):
            path_pages = get_inferred_pages(
                user_story,
                method_map_full,
                db=request_db,
                project_id=project_id,
            )
        else:
            path_pages = _select_story_pages(user_story, method_map_full)

    if not path_pages:
        raise HTTPException(status_code=400, detail="No page methods found to generate updated testcase.")

    sub_method_map = {p: method_map_full[p] for p in path_pages if p in method_map_full}
    sub_method_map = _trim_method_map_for_prompt(user_story, sub_method_map)

    fallback_used = False
    if test_type == "security":
        code = generate_security_test_code_from_methods(
            user_story,
            sub_method_map,
            path_pages,
            site_url,
            run_folder,
            project_src_dir,
            db=request_db,
            project_id=project_id,
        )
    elif test_type == "accessibility":
        code = generate_accessibility_test_code_from_methods(
            user_story,
            sub_method_map,
            path_pages,
            site_url,
            run_folder,
            project_src_dir,
            db=request_db,
            project_id=project_id,
        )
    else:
        code, fallback_used = generate_test_code_from_methods(
            user_story,
            sub_method_map,
            path_pages,
            site_url,
            run_folder,
            project_src_dir,
            strict_story_only=ui_strict_only,
            allow_direct_selectors=(not method_map_full),
            post_method_map=method_map_full,
            db=request_db,
            project_id=project_id,
        )

    latest_records: list[dict] = []
    try:
        latest_records = _latest_upload_snapshot(project.id)
    except Exception:
        latest_records = []
    if not latest_records:
        for meta_name in ("after_enrichment.json", "before_enrichment.json"):
            meta_file = meta_dir / meta_name
            if not meta_file.exists():
                continue
            try:
                payload = json.loads(meta_file.read_text(encoding="utf-8")) or []
                if isinstance(payload, list):
                    latest_records = [entry for entry in payload if isinstance(entry, dict)]
            except Exception:
                latest_records = []
            if latest_records:
                break

    code = _strip_module_qualified_helpers(code, method_map_full)
    code = _normalize_generated_code(code, sub_method_map, user_story, full_method_map=method_map_full)
    code = _replace_mismatched_input_methods(code, user_story, sub_method_map)
    code = _map_generic_helpers_to_pom(code, method_map_full or sub_method_map)
    code = _rewrite_toggle_ensure_calls(code, method_map_full or sub_method_map)
    code = _inject_page_object_instances(code, sub_method_map)
    code = _qualify_pom_method_calls(code, sub_method_map)
    code = _rewrite_calendar_popup_numeric_clicks(code)
    code = _ensure_page_arg_for_pom_calls(code, sub_method_map)
    code = _rewrite_missing_page_object_calls(code, sub_method_map)
    code = _inject_calendar_unique_args(code, latest_records)
    code = _remove_stray_explanatory_prose(code)
    code, fallback_used = inject_missing_pom_fallbacks(code, user_story)

    test_path = _resolve_project_test_path(run_folder, test_file_path)
    if not test_path.exists():
        raise HTTPException(status_code=404, detail="Test file not found for update.")

    existing_content = test_path.read_text(encoding="utf-8")
    existing_names = _extract_test_function_names(existing_content)
    prefer_page_methods_style = "_page_methods import *" in existing_content

    grouped_tests = _split_generated_tests_by_category(code)
    category = _resolve_category_from_test_path(test_path)
    func_blocks = grouped_tests.get(category) or []
    if not func_blocks:
        raise HTTPException(status_code=400, detail="Generated code did not contain test functions for this category.")

    processed_func_blocks: list[tuple[Optional[str], str]] = []

    project_id_val = project.id

    with session_scope() as scoped_db:
        for idx, func_block in enumerate(func_blocks):
            match = re.search(
                r"^\s*def\s+(test_[A-Za-z0-9_]+)\s*\(\s*page\s*\)\s*:",
                func_block,
                flags=re.MULTILINE,
            )
            if not match:
                processed_func_blocks.append((None, func_block))
                continue

            generated_name = match.group(1)
            target_name = existing_names[idx] if idx < len(existing_names) else generated_name

            if target_name != generated_name:
                func_block = re.sub(
                    rf"^(\s*def\s+){re.escape(generated_name)}(\s*\()",
                    rf"\1{target_name}\2",
                    func_block,
                    count=1,
                    flags=re.MULTILINE,
                )

            func_block = _qualify_pom_method_calls(
                func_block,
                sub_method_map,
                force_page_methods_style=prefer_page_methods_style,
            )
            func_block = _rewrite_calendar_popup_numeric_clicks(func_block)
            func_block = _ensure_page_arg_for_pom_calls(func_block, sub_method_map)
            func_block = _rewrite_missing_page_object_calls(func_block, sub_method_map)
            func_block = _apply_markers_to_function_block(
                func_block,
                target_name,
                project_id_val,
                scoped_db,
                user_story=user_story,
                test_type=category,
                fallback_used=fallback_used,
            )
            processed_func_blocks.append((target_name, func_block))

    function_code = "\n\n".join(block for _name, block in processed_func_blocks).strip()
    if not function_code:
        raise HTTPException(status_code=400, detail="Failed to build updated test content.")
    # No app-specific hardcoded assertions.

    test_names = [name for name, _block in processed_func_blocks if name]

    page_method_files = sorted(pages_dir.glob("*_page_methods.py"))
    page_pom_files = [] if page_method_files else sorted(pages_dir.glob("*_page.py"))
    page_security_files = sorted(pages_dir.glob("*_security_methods.py"))
    page_accessibility_files = sorted(pages_dir.glob("*_accessibility_methods.py"))
    import_lines = [
        "import pytest",
        "from playwright.sync_api import sync_playwright, expect",
        "import json",
        "from pathlib import Path",
        "from lib.smart_ai import patch_page_with_smartai",
    ]
    for f in page_method_files + page_pom_files + page_security_files + page_accessibility_files:
        import_lines.append(f"from pages.{f.stem} import *")
        if f.stem.endswith("_page_methods"):
            page_key = normalize_page_name(f.stem.replace("_page_methods", ""))
            import_lines.append(f"from pages import {f.stem} as {_page_module_alias_name(page_key)}")

    function_code, binding_lines = _simplify_page_method_alias_calls(function_code)
    if binding_lines:
        function_code = "\n".join(binding_lines + ["", function_code]).strip()

    header = _story_header_line(user_story)
    updated = "\n".join([header, "", "\n\n".join(import_lines + [function_code]).rstrip(), ""]).rstrip() + "\n"
    test_path.write_text(updated, encoding="utf-8")

    # Persist to DB-backed storage
    try:
        storage = DatabaseBackedProjectStorage(project, run_folder, db)
        relative = test_path.relative_to(run_folder).as_posix()
        storage.write_file(relative, updated, "utf-8")
    except Exception:
        pass

    # Update corresponding runner script (ui_script_*.py)
    runner_dir = test_path.parent
    runner_name = None
    try:
        if test_path.name.startswith("test_"):
            if category == "ui":
                runner_name = test_path.name.replace("test_", "ui_script_", 1)
            else:
                runner_name = test_path.name.replace("test_", f"{category}_script_", 1)
        if runner_name and not runner_name.endswith(".py"):
            runner_name = f"{runner_name}.py"
    except Exception:
        runner_name = None
    if not runner_name:
        runner_name = _runner_name_from_test_path(test_path, category, user_story)
    fixed_runner_name = None
    if target_runner_script_path:
        try:
            fixed_runner_name = Path(target_runner_script_path).name
        except Exception:
            fixed_runner_name = None
    try:
        ts_index_for_runner = _extract_ts_index_from_names(test_names) or _next_ts_index_for_project(project.id)
        _generate_execution_script_for_category(
            category=category,
            target_dir=runner_dir,
            test_file_path=test_path,
            original_story=user_story,
            site_url=site_url,
            import_lines=import_lines,
            method_map=method_map_full,
            ts_index=ts_index_for_runner,
            fixed_script_name=fixed_runner_name or runner_name,
            project_root=Path(ctx.project_dir).resolve(),
            strict_story_only=ui_strict_only,
            db=request_db,
            project_id=project_id,
        )
    except Exception:
        pass

    return {
        "status": "updated",
        "test_name": test_names[0] if test_names else test_name.strip(),
        "test_file_path": str(test_path),
        "auto_testcase": function_code,
        "original_story": user_story,
        "user_story": user_story,
        "test_type": test_type or "ui",
        "test_names": test_names,
    }


# ----------------------------------------------------------------------
# Runner generator
# ----------------------------------------------------------------------
def _generate_execution_script_for_category(
    category: str,
    target_dir: Path,
    test_file_path: Path,
    original_story: str,
    site_url: Optional[str],
    import_lines: List[str],
    method_map: dict,
    ts_index: int,
    fixed_script_name: Optional[str] = None,
    project_root: Optional[Path] = None,
    strict_story_only: bool = False,
    db: Optional[Session] = None,
    project_id: Optional[int] = None,
) -> Optional[Path]:
    lines = test_file_path.read_text(encoding="utf-8").splitlines(True)
    func_blocks: List[tuple[str, str, List[str]]] = []
    current_name: Optional[str] = None
    current_body: List[str] = []
    current_markers: List[str] = []
    pending_markers: List[str] = []
    in_function = False

    def _commit_current():
        nonlocal current_name, current_body, current_markers, in_function
        if current_name and current_body:
            func_blocks.append((current_name, "".join(current_body), current_markers))
        current_name = None
        current_body = []
        current_markers = []
        in_function = False

    for line in lines:
        m = re.match(r"^\s*def (test_[a-zA-Z0-9_]+)\(page\):", line)
        marker_match = re.match(r"^\s*@pytest\.mark\.([a-zA-Z0-9_]+)\s*$", line)
        if in_function:
            if marker_match or m:
                _commit_current()
                if marker_match:
                    pending_markers.append(marker_match.group(1))
                    continue
                if m:
                    current_name = m.group(1)
                    current_body = []
                    current_markers = pending_markers
                    pending_markers = []
                    in_function = True
                    continue
            current_body.append(line)
            continue
        if marker_match:
            pending_markers.append(marker_match.group(1))
            continue
        if m:
            current_name = m.group(1)
            current_body = []
            current_markers = pending_markers
            pending_markers = []
            in_function = True
            continue

    if current_name and current_body:
        func_blocks.append((current_name, "".join(current_body), current_markers))
    if not func_blocks:
        return None

    story_text = original_story or ""
    story_steps = _extract_story_steps_structured(story_text)
    include_ui_ready_wait = category == "ui" and any(step.action == "wait_for_page_load" for step in story_steps)
    storage_override_js = None
    try:
        m = re.search(r'storage state\s*"([^"]+)"', story_text, re.I)
        if m:
            storage_override_js = json.dumps(m.group(1))
    except Exception:
        storage_override_js = None

    wrapper_blocks: List[str] = []
    shared_runner_setup_block = ""
    project_root_literal = json.dumps(str(project_root.resolve())) if project_root else '""'
    has_markers = any(markers for _, _, markers in func_blocks)
    story_slug = _infer_script_slug(original_story, category, db=db, project_id=project_id)
    ts_id = f"TS_{ts_index:03d}"
    run_tag_map: dict[str, list[str]] = {}
    runner_names: list[str] = []
    for idx, (func_name, func_body, func_markers) in enumerate(func_blocks, start=1):
        if category == "ui":
            func_body = _clean_func_body_for_story(func_body, story_text, method_map)
        base_name = func_name.replace("test_", "")
        tc_id = f"TC_{idx:03d}"
        if base_name.startswith("TS_"):
            runner_name = base_name
        else:
            runner_name = f"{ts_id}_{tc_id}_{story_slug}_{base_name}"
        runner_names.append(runner_name)
        run_tag_map[runner_name] = [
            str(marker).strip().lower()
            for marker in (func_markers or [])
            if str(marker).strip()
        ]

        dedented = textwrap.dedent(remove_ai_analyzed_comments(_strip_step_comments(func_body)))
        step_lines = []
        for line in dedented.strip("\n").splitlines():
            if not line.strip():
                continue
            step_lines.append("        " + line)
        if category == "accessibility":
            step_lines.append("        run_accessibility_scan(page)")
        steps = "\n".join(step_lines)
        if steps and not steps.endswith("\n"):
            steps += "\n"

        marker_prefix = ""
        if func_markers:
            marker_decorators = _format_markers_as_pytest_decorators(func_markers)
            if marker_decorators:
                marker_prefix = "\n".join(marker_decorators) + "\n"

        # Rewrite helper calls back to imported page-level functions
        prefer_page_methods_style = any("_page_methods import *" in line for line in import_lines)
        helper_names = set()
        for methods in (method_map or {}).values():
            for method_def in methods:
                name = method_def.split("(", 1)[0].replace("def ", "").strip()
                if name:
                    helper_names.add(name)

        for helper_name in helper_names:
            pattern = rf"(?<!\w)page\.{re.escape(helper_name)}\((.*?)\)"

            def repl(match, helper_name=helper_name):
                args_raw = match.group(1).strip()
                if not args_raw:
                    new_args = "page"
                elif args_raw.startswith("page"):
                    new_args = args_raw
                else:
                    new_args = f"page, {args_raw}"
                return f"{helper_name}({new_args})"

            steps = re.sub(pattern, repl, steps)
            module_pattern = rf"(?:[a-zA-Z_][a-zA-Z0-9_]*\.)+{re.escape(helper_name)}\("
            steps = re.sub(module_pattern, f"{helper_name}(", steps)
        steps = _qualify_pom_method_calls(
            steps,
            method_map,
            force_page_methods_style=prefer_page_methods_style,
        )
        steps = _rewrite_wfh_calendar_steps_for_runner(steps)
        steps = _ensure_page_arg_for_pom_calls(steps, method_map)

        if not shared_runner_setup_block:
            if storage_override_js:
                session_setup_snippet = f"""    restored_storage = False
    try:
        context = browser.new_context(storage_state={storage_override_js})
        page = context.new_page()
        print(f"[{category}_runner] Restored storage_state from provided path")
        restored_storage = True
    except Exception as e:
        print(f"[{category}_runner] Failed to restore provided storage_state: {{e}}")
        context = browser.new_context()
        page = context.new_page()
"""
            else:
                session_setup_snippet = f"""    # Attempt to restore cookies / localStorage from a Playwright storage_state file.
    # Priority: auth/storage.json
    storage_file = None
    restored_storage = False
    project_root = ""
    try:
        if _PROJECT_ROOT:
            project_root = str(_PROJECT_ROOT)
    except Exception:
        project_root = ""
    if not project_root:
        for parent in _Path(__file__).resolve().parents:
            if parent.name == "generated_runs":
                project_root = str(parent.parent)
                break
    if project_root:
        candidate = _Path(project_root) / "auth" / "storage.json"
        if candidate.exists():
            storage_file = candidate

    if storage_file and storage_file.exists():
        try:
            context = browser.new_context(storage_state=str(storage_file))
            page = context.new_page()
            print(f"[{category}_runner] Restored storage_state from: {{storage_file}}")
            restored_storage = True
        except Exception as e:
            print(f"[{category}_runner] Failed to restore storage_state: {{e}}")
            context = browser.new_context()
            page = context.new_page()
    else:
        expected = ""
        if project_root:
            expected = str(_Path(project_root) / "auth" / "storage.json")
        print(f"[{category}_runner] No storage_state file found. Expected: {{expected}}")
        context = browser.new_context()
        page = context.new_page()
"""

            shared_runner_setup_block = f"""
_SHARED_PLAYWRIGHT = None
_SHARED_BROWSER = None
_SHARED_METADATA = None


def _browser_slow_mo_ms():
    try:
        return int(os.getenv("SMARTAI_BROWSER_SLOW_MO", "0"))
    except Exception:
        return 0


def _ensure_shared_browser():
    global _SHARED_PLAYWRIGHT, _SHARED_BROWSER
    if _SHARED_PLAYWRIGHT is None:
        _SHARED_PLAYWRIGHT = sync_playwright().start()
    if _SHARED_BROWSER is None:
        _write_allure_environment()
        _SHARED_BROWSER = _SHARED_PLAYWRIGHT.chromium.launch(
            headless=False,
            slow_mo=_browser_slow_mo_ms(),
        )
    return _SHARED_BROWSER


def _load_shared_metadata():
    global _SHARED_METADATA
    if _SHARED_METADATA is None:
        metadata_path = _SRC_ROOT / "metadata" / "after_enrichment.json"
        with open(metadata_path, "r", encoding="utf-8") as f:
            _SHARED_METADATA = json.load(f)
    return _SHARED_METADATA


def _prepare_test_session():
    import os
    from pathlib import Path as _Path

    browser = _ensure_shared_browser()
{session_setup_snippet}
    set_current_page(page)
    _attach_page_helpers(page)
    actual_metadata = _load_shared_metadata()
    return context, page, actual_metadata, restored_storage


def _close_shared_browser():
    global _SHARED_BROWSER, _SHARED_PLAYWRIGHT
    if _SHARED_BROWSER is not None:
        try:
            _SHARED_BROWSER.close()
        except Exception:
            pass
        _SHARED_BROWSER = None
    if _SHARED_PLAYWRIGHT is not None:
        try:
            _SHARED_PLAYWRIGHT.stop()
        except Exception:
            pass
        _SHARED_PLAYWRIGHT = None
""".strip()

        goto_target = ""
        try:
            goto_target = (site_url or "").strip()
            if not goto_target:
                goto_target = os.getenv("SITE_URL", "").strip()
        except Exception:
            goto_target = ""

        goto_line = ""
        if strict_story_only:
            auth_guard = (
                "    page.wait_for_load_state(\"domcontentloaded\")\n"
                "    _dismiss_cookie_banner(page)\n"
            )
        else:
            auth_guard = (
                "    page.wait_for_load_state(\"domcontentloaded\")\n"
                "    _dismiss_cookie_banner(page)\n"
                "    auth_landing = os.getenv(\"SMARTAI_AUTH_LANDING_URL\", \"\").strip()\n"
                "    if not auth_landing:\n"
                "        project_root = \"\"\n"
                "        try:\n"
                "            if _PROJECT_ROOT:\n"
                "                project_root = str(_PROJECT_ROOT)\n"
                "        except Exception:\n"
                "            project_root = \"\"\n"
                "        if not project_root:\n"
                "            for parent in _Path(__file__).resolve().parents:\n"
                "                if parent.name == \"generated_runs\":\n"
                "                    project_root = str(parent.parent)\n"
                "                    break\n"
                "        if project_root:\n"
                "            landing_file = _Path(project_root) / \"auth\" / \"landing_url.txt\"\n"
                "            try:\n"
                "                if landing_file.exists():\n"
                "                    auth_landing = landing_file.read_text(encoding=\"utf-8\").strip()\n"
                "            except Exception:\n"
                "                auth_landing = \"\"\n"
                "    try:\n"
                "        current_url = page.url or \"\"\n"
                "    except Exception:\n"
                "        current_url = \"\"\n"
                "    if auth_landing:\n"
                "        page.goto(auth_landing)\n"
                "        page.wait_for_load_state(\"domcontentloaded\")\n"
                "        _dismiss_cookie_banner(page)\n"
                "        try:\n"
                "            current_url = page.url or \"\"\n"
                "        except Exception:\n"
                "            current_url = \"\"\n"
                "    if restored_storage and current_url and any(k in current_url.lower() for k in (\"login\", \"signin\", \"sign-in\", \"auth\")):\n"
                "        raise RuntimeError(\n"
                "            \"Session not authenticated (still on login page). \"\n"
                "            \"Refresh auth storage and re-run.\"\n"
                "        )\n"
            )
        if goto_target and not re.search(r"page\.goto\(", steps):
            goto_literal = json.dumps(goto_target)
            goto_line = f"    page.goto({goto_literal})\n{auth_guard}    patch_page_with_smartai(page, actual_metadata)\n"
            if not goto_line.endswith("\n"):
                goto_line += "\n"
        elif re.search(r"page\.goto\(", steps):
            def _inject_guard(match: re.Match[str]) -> str:
                indent = match.group(1) or ""
                guard = auth_guard.replace("    ", indent)
                patch = "    patch_page_with_smartai(page, actual_metadata)\n".replace("    ", indent)
                if not guard.endswith("\n"):
                    guard += "\n"
                return match.group(0) + guard + patch

            steps = re.sub(
                r"(^[ \t]*)page\.goto\([^\n]*\)\n",
                _inject_guard,
                steps,
                count=1,
                flags=re.MULTILINE,
            )
        story_literal = json.dumps(original_story or "")
        runner_block = f"""{marker_prefix}def {runner_name}():
    import time
    context, page, actual_metadata, restored_storage = _prepare_test_session()
    _allure_attach_text("story", {story_literal})
{goto_line}    try:
{steps}
    except Exception:
        _safe_screenshot(page, "failure")
        raise
    try:
        pause_s = float(os.getenv("SMARTAI_POST_RUN_PAUSE_SEC", "0"))
    except Exception:
        pause_s = 0
    if pause_s > 0:
        time.sleep(pause_s)
    try:
        context.close()
    except Exception:
        pass

"""
        wrapper_blocks.append(runner_block)
    function_code = "\n\n".join(
        [block for block in [shared_runner_setup_block, *wrapper_blocks] if block]
    ).strip()
    if not function_code:
        return None

    function_code, binding_lines = _simplify_page_method_alias_calls(function_code)
    if binding_lines:
        function_code = "\n".join(binding_lines + ["", function_code]).strip()

    page_imports = "\n".join(
        [
            ln
            for ln in import_lines
            if ln.startswith("from pages.")
            or (ln.startswith("from pages import ") and " as _pm_" in ln)
        ]
    )
    extra_imports = ""
    if category == "accessibility":
        extra_imports = "from services.accessibility_test_utils import run_accessibility_scan\n"
    pytest_import = "import pytest\n" if has_markers else ""

    if category == "ui":
        playwright_import = "from playwright.sync_api import sync_playwright, expect"
    else:
        playwright_import = "from playwright.sync_api import sync_playwright"

    ui_ready_helper_block = ""
    if include_ui_ready_wait:
        ui_ready_helper_block = """
def _wait_target_tokens(text):
    lowered = str(text or "").strip().lower()
    if not lowered:
        return []
    tokens = [token for token in re.findall(r"[a-z0-9]+", lowered) if token]
    noise = {"button", "icon", "link", "tab", "menu", "popup", "dialog", "modal", "visible", "is"}
    filtered = [token for token in tokens if token not in noise]
    return filtered or tokens

def _expected_target_ready(page, text):
    label = str(text or "").strip()
    if not label:
        return False
    try:
        if page.get_by_text(label, exact=True).first.is_visible(timeout=500):
            return True
    except Exception:
        pass
    for role in ("button", "link", "tab", "menuitem"):
        try:
            locator = page.get_by_role(role, name=label, exact=True).first
            if locator.is_visible(timeout=500):
                return True
        except Exception:
            pass
    try:
        locator = page.get_by_label(label, exact=True).first
        if locator.is_visible(timeout=500):
            return True
    except Exception:
        pass

    tokens = _wait_target_tokens(label)
    if not tokens:
        return False
    try:
        selector_parts = []
        for token in tokens[:3]:
            safe = token.replace("'", "\\'")
            selector_parts.extend(
                [
                    f"[aria-label*='{safe}' i]",
                    f"[title*='{safe}' i]",
                    f"[alt*='{safe}' i]",
                    f"[data-testid*='{safe}' i]",
                    f"[data-test*='{safe}' i]",
                    f"[class*='{safe}' i]",
                ]
            )
        locator = page.locator(", ".join(selector_parts)).first
        if locator.count() > 0 and locator.is_visible(timeout=500):
            return True
    except Exception:
        pass
    return False

def _wait_for_ui_ready(page, expected_texts=None, timeout_ms=None):
    try:
        timeout_ms = int(timeout_ms) if timeout_ms is not None else int(os.getenv("SMARTAI_UI_READY_TIMEOUT_MS", "45000"))
    except Exception:
        timeout_ms = 45000

    expected_texts = [str(item).strip() for item in (expected_texts or []) if str(item).strip()]
    deadline = time.time() + (timeout_ms / 1000.0)
    last_url = ""

    while time.time() < deadline:
        try:
            page.wait_for_load_state("domcontentloaded", timeout=1500)
        except Exception:
            pass
        try:
            page.wait_for_load_state("networkidle", timeout=1500)
        except Exception:
            pass
        try:
            last_url = page.url or ""
        except Exception:
            last_url = ""

        if not expected_texts:
            return

        for text in expected_texts:
            if _expected_target_ready(page, text):
                return

        time.sleep(1)

    detail = ", ".join(expected_texts) if expected_texts else "page readiness"
    if last_url:
        raise RuntimeError(f"UI not ready for expected elements: {detail} | last_url={last_url}")
    raise RuntimeError(f"UI not ready for expected elements: {detail}")
"""

    header = f"""# Auto-generated {category} runner
import sys
import os
import re
import time
from datetime import date, timedelta
from pathlib import Path as _Path

_PROJECT_ROOT = _Path({project_root_literal}) if {project_root_literal} else None

# Ensure src is on sys.path
_SCRIPT_PATH = _Path(__file__).resolve()
_ENV_SRC = os.getenv("SMARTAI_SRC_DIR", "").strip()
if _ENV_SRC:
    _SRC_ROOT = _Path(_ENV_SRC).resolve()
else:
    _SRC_ROOT = None
    for _parent in _SCRIPT_PATH.parents:
        if _parent.name == "src":
            _SRC_ROOT = _parent
            break
    if _SRC_ROOT is None:
        _SRC_ROOT = _SCRIPT_PATH.parents[2]

if str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))

# Add backend root to sys.path
_ENV_BACKEND = os.getenv("SMARTAI_BACKEND_ROOT", "").strip()
if _ENV_BACKEND:
    _BACKEND_ROOT = _Path(_ENV_BACKEND).resolve()
else:
    _BACKEND_ROOT = None
    for _parent in _SCRIPT_PATH.parents:
        if _parent.name == "backend":
            _BACKEND_ROOT = _parent
            break
    if _BACKEND_ROOT is None:
        _BACKEND_ROOT = _SCRIPT_PATH.parents[7]

if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

{playwright_import}
{pytest_import}import json
import inspect
import functools
from pathlib import Path
{page_imports}
{extra_imports}from lib.smart_ai import patch_page_with_smartai
from lib.ui_actions import safe_drag_and_drop
from lib.allure_runtime import run_allure_case, set_current_page

try:
    import allure  # type: ignore
    from allure_commons.types import AttachmentType  # type: ignore
except Exception:  # pragma: no cover
    allure = None
    AttachmentType = None

def _allure_attach_text(name, text):
    if not allure or not AttachmentType:
        return
    try:
        allure.attach(str(text), name=name, attachment_type=AttachmentType.TEXT)
    except Exception:
        pass

def _allure_attach_png(name, data):
    if not allure or not AttachmentType:
        return
    try:
        allure.attach(data, name=name, attachment_type=AttachmentType.PNG)
    except Exception:
        pass

def _attach_failure_context(page):
    try:
        url = page.url
    except Exception:
        url = ""
    if url:
        _allure_attach_text("page_url", url)

    action = getattr(page, "_last_action", None)
    if action:
        _allure_attach_text("last_action", action)

    locator = getattr(page, "_last_locator", None)
    if not locator:
        return

    meta = getattr(locator, "_element_meta", None)
    if meta:
        try:
            _allure_attach_text("last_element_meta", json.dumps(meta, indent=2))
        except Exception:
            pass

    try:
        target = locator.first if hasattr(locator, "first") else locator
    except Exception:
        target = locator

    try:
        outer_html = target.evaluate("el => (el && el.outerHTML) ? el.outerHTML : ''")
        if outer_html:
            _allure_attach_text("last_element_html", outer_html)
    except Exception:
        pass

    try:
        text = target.evaluate("el => (el && el.textContent) ? el.textContent : ''")
        if text:
            _allure_attach_text("last_element_text", text.strip())
    except Exception:
        pass

    try:
        bbox = target.bounding_box()
        if bbox:
            _allure_attach_text("last_element_bbox", json.dumps(bbox))
    except Exception:
        pass

def _safe_screenshot(page, name="failure"):
    try:
        _attach_failure_context(page)
        manager = getattr(page, "_visual_manager", None)
        if manager:
            manager.start_test(os.getenv("SMARTAI_VISUAL_TEST_NAME", "") or "unknown_test")
            manager.on_failure(label=name)
        try:
            locator = getattr(page, "_last_locator", None)
            if locator:
                target = locator.first if hasattr(locator, "first") else locator
                try:
                    target.scroll_into_view_if_needed(timeout=1000)
                except Exception:
                    pass
                try:
                    target.evaluate(
                        "el => {{ if (!el) return; el.setAttribute('data-smartai-highlight','1');"
                        "el.style.outline='3px solid #ff3b30'; el.style.outlineOffset='2px';"
                        "el.style.boxShadow='0 0 0 2px rgba(255,59,48,0.4)'; }}"
                    )
                except Exception:
                    pass
        except Exception:
            pass
        data = page.screenshot(full_page=False)
    except Exception:
        return
    _allure_attach_png(name, data)
{ui_ready_helper_block}

def _write_allure_environment():
    results_dir = os.getenv("ALLURE_RESULTS_DIR", "allure-results")
    try:
        project_dir = ""
        try:
            if _PROJECT_ROOT:
                project_dir = str(_PROJECT_ROOT)
        except Exception:
            project_dir = ""
        os.makedirs(results_dir, exist_ok=True)
        env_path = _Path(results_dir) / "environment.properties"
        lines = [
            "base_url=" + os.getenv("SITE_URL", ""),
            "project_id=" + os.getenv("SMARTAI_PROJECT_ID", ""),
            "project_dir=" + project_dir,
            "browser=chromium",
        ]
        env_path.write_text("\\n".join(lines) + "\\n", encoding="utf-8")
    except Exception:
        pass

def _date_offset_string(offset_days):
    try:
        offset = int(offset_days)
    except Exception:
        offset = 0
    target = date.today() + timedelta(days=offset)
    return target.strftime("%d/%m/%Y")

def _calendar_day_string(day_value):
    try:
        day = int(day_value)
    except Exception:
        day = 1
    day = max(1, min(31, day))
    today = date.today()
    target = today.replace(day=day)
    return target.strftime("%d/%m/%Y")

def _attach_page_helpers(target_page):
    for name, helper in globals().items():
        if not inspect.isfunction(helper):
            continue
        module = getattr(helper, "__module__", "")
        if not module.startswith("pages."):
            continue
        if name.startswith("_"):
            continue
        if hasattr(target_page, name):
            continue
        setattr(target_page, name, functools.partial(helper, target_page))

def _dismiss_cookie_banner(page):
    cookie_text = re.compile(r"(cookie|consent|gdpr|privacy|tracking)", re.I)
    decline_patterns = [
        r"decline",
        r"reject",
        r"disagree",
        r"deny",
        r"refuse",
        r"opt out",
        r"no thanks",
        r"not now",
        r"cancel",
        r"only necessary",
        r"essential only",
        r"manage preferences",
        r"settings",
    ]
    accept_patterns = [
        r"accept all",
        r"accept",
        r"i agree",
        r"agree",
        r"ok",
        r"okay",
        r"got it",
        r"continue",
        r"yes",
        r"close",
        r"dismiss",
        r"skip",
    ]
    banner_selectors = [
        "[id*='cookie' i]",
        "[class*='cookie' i]",
        "[data-testid*='cookie' i]",
        "[data-test*='cookie' i]",
        "[id*='consent' i]",
        "[class*='consent' i]",
        "[data-testid*='consent' i]",
        "[data-test*='consent' i]",
        "[id*='gdpr' i]",
        "[class*='gdpr' i]",
        "[id*='privacy' i]",
        "[class*='privacy' i]",
        "[aria-label*='cookie' i]",
        "[aria-label*='consent' i]",
    ]

    def _promote_container(candidate):
        try:
            container = candidate.locator(
                "xpath=ancestor-or-self::*[self::div or self::section or self::aside or self::dialog or @role='dialog' or @aria-modal='true'][1]"
            ).first
            if container.is_visible(timeout=600):
                return container
        except Exception:
            pass
        return candidate

    def _find_cookie_banner():
        for selector in banner_selectors:
            try:
                loc = page.locator(selector)
                try:
                    filtered = loc.filter(has_text=cookie_text).first
                    if filtered.is_visible(timeout=600):
                        return _promote_container(filtered)
                except Exception:
                    pass
                candidate = loc.first
                if candidate.is_visible(timeout=600):
                    return _promote_container(candidate)
            except Exception:
                continue
        try:
            text_loc = page.get_by_text(cookie_text).first
            if text_loc.is_visible(timeout=600):
                container = text_loc.locator(
                    "xpath=ancestor-or-self::*[self::div or self::section or self::aside or self::dialog or @role='dialog' or @aria-modal='true'][1]"
                ).first
                if container.is_visible(timeout=600):
                    return container
        except Exception:
            pass
        return None

    def _try_patterns(scope, patterns) -> bool:
        for pat in patterns:
            try:
                locator = scope.get_by_role("button", name=re.compile(pat, re.I)).first
                if locator.is_visible(timeout=800):
                    locator.click(timeout=1000)
                    return True
            except Exception:
                continue
        return False

    banner = _find_cookie_banner()
    if not banner:
        return False

    if _try_patterns(banner, decline_patterns):
        return True
    if _try_patterns(banner, accept_patterns):
        return True

    fallback_selectors = [
        "button[aria-label*='decline' i]",
        "button[aria-label*='reject' i]",
        "button[aria-label*='cancel' i]",
        "button[aria-label*='deny' i]",
        "button[aria-label*='accept' i]",
        "button[aria-label*='close' i]",
        "button:has-text('Accept all')",
        "button:has-text('Decline')",
        "button:has-text('Reject')",
        "button:has-text('Cancel')",
        "button:has-text('No thanks')",
        "button:has-text('Accept')",
        "button:has-text('I agree')",
        "button:has-text('Close')",
        "button:has-text('Not now')",
        "button:has-text('Skip')",
        "button:has-text('Only necessary')",
        "button:has-text('Essential only')",
        "button:has-text('Manage preferences')",
        "button:has-text('Settings')",
        "button:has-text('×')",
        "span:has-text('×')",
        "a:has-text('Accept')",
        "a:has-text('Accept all')",
        "a:has-text('I agree')",
        "a:has-text('Close')",
        "[aria-label*='accept' i]",
        "[aria-label*='close' i]",
        "[aria-label*='decline' i]",
        "[aria-label*='reject' i]",
        "[aria-label*='cancel' i]",
        "[data-testid*='cookie' i] button",
        "[id*='cookie' i] button",
        "[class*='cookie' i] button",
        "[id*='consent' i] button",
        "[class*='consent' i] button",
        "[data-testid*='consent' i] button",
        "[data-test*='consent' i] button",
        "[id*='gdpr' i] button",
        "[class*='gdpr' i] button",
        "[id*='privacy' i] button",
        "[class*='privacy' i] button",
    ]
    for selector in fallback_selectors:
        try:
            locator = banner.locator(selector).first
            if locator.is_visible(timeout=1000):
                locator.click(timeout=1000)
                return True
        except Exception:
            continue
    return False

def _find_frame_for_field(page, label=None, placeholder=None):
    def _contains_target(scope):
        if scope is None:
            return False
        checks = []
        if label:
            checks.extend(
                (
                    lambda: scope.get_by_label(label).count() > 0,
                    lambda: scope.get_by_role("textbox", name=label, exact=True).count() > 0,
                    lambda: scope.get_by_text(label, exact=True).count() > 0,
                )
            )
        if placeholder:
            checks.append(lambda: scope.get_by_placeholder(placeholder).count() > 0)
        for check in checks:
            try:
                if check():
                    return True
            except Exception:
                continue
        return False

    selectors = (
        "dialog[open], [role='dialog'], [role='alertdialog'], [aria-modal='true'], aside[aria-modal='true']",
        ".modal:visible, .drawer:visible, .popup:visible, .offcanvas.show, .ant-drawer-content, .MuiDrawer-paper",
    )
    for selector in selectors:
        try:
            locator = page.locator(selector)
            count = min(locator.count(), 8)
        except Exception:
            count = 0
        for idx in range(count):
            try:
                scope = locator.nth(idx)
                if not scope.is_visible(timeout=200):
                    continue
                if _contains_target(scope):
                    return scope
            except Exception:
                continue
    for fr in page.frames:
        try:
            if label:
                loc = fr.get_by_label(label)
                if loc.count() > 0:
                    return fr
        except Exception:
            pass
        try:
            if placeholder:
                loc = fr.get_by_placeholder(placeholder)
                if loc.count() > 0:
                    return fr
        except Exception:
            pass
    return None

def _smart_fill(page, label, value, placeholder=None):
    def _placeholder_variants(lbl, ph):
        variants = []
        if ph:
            variants.append(ph)
        if lbl:
            variants.append(lbl)
            variants.append(f"Enter {{lbl}}")
            variants.append(f"Enter {{lbl.lower()}}")
            variants.append(f"Enter {{lbl.title()}}")
            parts = [p for p in re.split(r"\\s+", lbl) if p]
            if parts:
                last = parts[-1]
                variants.append(f"Enter {{last}}")
                variants.append(f"Enter {{last.lower()}}")
                variants.append(f"Enter {{last.title()}}")
        # dedupe preserving order
        seen = set()
        out = []
        for v in variants:
            if v and v not in seen:
                seen.add(v)
                out.append(v)
        return out

    # Prefer an active modal/drawer scope before falling back to frames/page
    target = _find_frame_for_field(page, label=label) or page
    try:
        target.get_by_label(label).fill(value)
        return
    except Exception:
        pass
    try:
        target.get_by_role("textbox", name=label, exact=True).fill(value)
        return
    except Exception:
        pass

    # Try placeholder variants inside frames
    for ph in _placeholder_variants(label, placeholder):
        target = _find_frame_for_field(page, placeholder=ph) or page
        try:
            target.get_by_placeholder(ph).fill(value)
            return
        except Exception:
            continue

    # Last resort: main page label
    try:
        page.get_by_label(label).fill(value)
        return
    except Exception:
        pass
    page.get_by_role("textbox", name=label, exact=True).fill(value)

def fill_text(page, field_label, value):
    return _smart_fill(page, field_label, value)

def _xpath_literal(text):
    if "'" not in text:
        return "'" + text + "'"
    if '"' not in text:
        return '"' + text + '"'
    parts = text.split("'")
    items = []
    for index, part in enumerate(parts):
        items.append("'" + part + "'")
        if index != len(parts) - 1:
            items.append('"\\\'"')
    return "concat(" + ", ".join(items) + ")"

def _get_checkbox_locator(page, label):
    exact_re = re.compile(r"^\\s*" + re.escape(label) + r"\\s*$", re.I)
    exact_label = _xpath_literal(label)
    try:
        loc = page.get_by_label(label, exact=True)
        if loc.count() > 0:
            return loc.first
    except Exception:
        pass
    try:
        loc = page.get_by_label(re.compile(r"^" + re.escape(label) + r"$", re.I))
        if loc.count() > 0:
            return loc.first
    except Exception:
        pass
    try:
        loc = page.get_by_role("checkbox", name=label, exact=True)
        if loc.count() > 0:
            return loc.first
    except Exception:
        pass
    try:
        loc = page.get_by_role("checkbox", name=re.compile(r"^" + re.escape(label) + r"$", re.I))
        if loc.count() > 0:
            return loc.first
    except Exception:
        pass
    try:
        loc = page.locator("label").filter(has_text=exact_re).locator(
            "input[type='checkbox'], input[type='radio'], [role='checkbox'], [role='radio']"
        )
        if loc.count() > 0:
            return loc.first
    except Exception:
        pass
    try:
        xpath = (
            "//label[normalize-space(.)=" + exact_label + "]"
            "//input[@type='checkbox' or @type='radio']"
            " | //label[normalize-space(.)=" + exact_label + "]/preceding-sibling::input[@type='checkbox' or @type='radio'][1]"
            " | //label[normalize-space(.)=" + exact_label + "]/following-sibling::input[@type='checkbox' or @type='radio'][1]"
        )
        loc = page.locator("xpath=" + xpath)
        if loc.count() > 0:
            return loc.first
    except Exception:
        pass
    try:
        xpath = (
            "//*[self::div or self::li or self::td or self::tr or self::span]"
            "[normalize-space(.)=" + exact_label + "]"
            "/ancestor-or-self::*[self::div or self::li or self::td or self::tr][1]"
            "//*[self::input[@type='checkbox' or @type='radio'] or @role='checkbox' or @role='radio']"
        )
        loc = page.locator("xpath=" + xpath)
        if loc.count() > 0:
            return loc.first
    except Exception:
        pass
    return None

def check_checkbox(page, label):
    locator = _get_checkbox_locator(page, label)
    if not locator:
        raise RuntimeError("Checkbox not found for label: " + str(label))
    try:
        locator.scroll_into_view_if_needed(timeout=1000)
    except Exception:
        pass
    try:
        locator.check()
        return
    except Exception:
        pass
    locator.click()

def select_dropdown(page, field_label, value):
    locator = None
    try:
        locator = page.get_by_label(field_label, exact=True)
    except Exception:
        locator = None
    if not locator or locator.count() == 0:
        try:
            locator = page.get_by_label(re.compile(r"^" + re.escape(field_label) + r"$", re.I))
        except Exception:
            locator = None
    if not locator or locator.count() == 0:
        try:
            locator = page.get_by_role("combobox", name=field_label, exact=True)
        except Exception:
            locator = None
    if not locator or locator.count() == 0:
        try:
            locator = page.get_by_role("combobox", name=re.compile(r"^" + re.escape(field_label) + r"$", re.I))
        except Exception:
            locator = None
    if not locator or locator.count() == 0:
        try:
            locator = page.locator(
                "xpath=//*[normalize-space(.)='" + field_label + "']/following::*[self::select or @role='combobox'][1]"
            )
        except Exception:
            locator = None
    if not locator or locator.count() == 0:
        try:
            locator = page.locator(
                \"xpath=//*[contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),\"\
                \"'\" + field_label.lower() + \"')]/following::*[self::select or @role='combobox'][1]\"
            )
        except Exception:
            locator = None
    if not locator or locator.count() == 0:
        raise RuntimeError("Dropdown not found for label: " + str(field_label))

    target = locator.first
    try:
        target.scroll_into_view_if_needed(timeout=1000)
    except Exception:
        pass
    try:
        tag = target.evaluate(\"el => el && el.tagName ? el.tagName.toLowerCase() : ''\")
    except Exception:
        tag = \"\"
    if tag == \"select\":
        try:
            target.select_option(label=value)
            return
        except Exception:
            pass
    try:
        target.click()
    except Exception:
        pass
    try:
        opt = page.get_by_role(\"option\", name=value, exact=True)
        if opt.count() > 0:
            opt.first.click()
            return
    except Exception:
        pass
    try:
        opt = page.get_by_role("option", name=re.compile(r"^" + re.escape(value) + r"$", re.I))
        if opt.count() > 0:
            opt.first.click()
            return
    except Exception:
        pass
    try:
        page.get_by_text(value, exact=True).click()
        return
    except Exception:
        pass
    raise RuntimeError("Option not found: " + str(value) + " for dropdown " + str(field_label))

def click_button(page, label):
    label = str(label or "").strip()
    if not label:
        raise RuntimeError("Button label is required")
    launcher_tokens = ("9 dot", "9 dots", "dot menu", "dots menu", "app launcher", "launcher", "grid menu", "waffle menu")
    if any(token in label.lower() for token in launcher_tokens):
        try:
            click_icon(page, label)
            return
        except Exception:
            pass

    def _click_locator(locator):
        try:
            if not locator or locator.count() == 0:
                return False
            target = locator.first
        except Exception:
            return False
        try:
            target.scroll_into_view_if_needed(timeout=1000)
        except Exception:
            pass
        try:
            target.click()
            return True
        except Exception:
            return False

    try:
        loc = page.get_by_role(\"button\", name=label, exact=True)
        if _click_locator(loc):
            return
    except Exception:
        pass
    try:
        loc = page.get_by_role("button", name=re.compile(r"^" + re.escape(label) + r"$", re.I))
        if _click_locator(loc):
            return
    except Exception:
        pass
    try:
        loc = page.get_by_role("link", name=label, exact=True)
        if _click_locator(loc):
            return
    except Exception:
        pass
    try:
        loc = page.get_by_role("link", name=re.compile(r"^" + re.escape(label) + r"$", re.I))
        if _click_locator(loc):
            return
    except Exception:
        pass
    try:
        loc = page.locator(
            "xpath=(//*[self::input or self::textarea]["
            "@value=" + _xpath_literal(label) + " and ("
            "@readonly or @role='button' or @aria-haspopup or "
            "contains(translate(@style,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'cursor: pointer')"
            ")])[1]"
        )
        if _click_locator(loc):
            return
    except Exception:
        pass
    try:
        txt = page.get_by_text(label, exact=True)
        if txt.count() > 0:
            anc = txt.first.locator(
                "xpath=ancestor-or-self::*["
                "self::button or self::a or self::input or self::textarea or "
                "@role='button' or @onclick or @tabindex='0' or "
                "contains(translate(@style,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'cursor: pointer')"
                "][1]"
            )
            if _click_locator(anc):
                return
    except Exception:
        pass
    try:
        txt = page.get_by_text(label, exact=True)
        if _click_locator(txt):
            return
    except Exception:
        pass
    try:
        loc = page.get_by_role("link", name=re.compile(re.escape(label), re.I))
        if _click_locator(loc):
            return
    except Exception:
        pass
    try:
        loc = page.get_by_text(re.compile(re.escape(label), re.I))
        if _click_locator(loc):
            return
    except Exception:
        pass
    try:
        click_icon(page, label)
        return
    except Exception:
        pass
    raise RuntimeError("Button not found: " + str(label))

def click_icon(page, label):
    raw = str(label or "").strip()
    if not raw:
        raise RuntimeError("Icon label is required")
    tokens = []
    tokens.append(raw)
    cleaned = re.sub(r"\\b(icon|button|action)\\b", "", raw, flags=re.I).strip()
    if cleaned and cleaned not in tokens:
        tokens.append(cleaned)
    if "avatar" in raw.lower() and "profile" not in tokens:
        tokens.append("profile")
    if "_" in raw:
        parts = [p for p in re.split(r"[_\\s]+", raw) if p and p.lower() not in ("icon","button","action")]
        for p in parts:
            if p not in tokens:
                tokens.append(p)
    alias_tokens = []
    for token in tokens:
        alias_tokens.append(token)
        lowered = token.lower()
        if lowered == "mail":
            alias_tokens.extend(["envelope", "email"])
        elif lowered == "envelope":
            alias_tokens.extend(["mail", "email"])
        elif lowered == "email":
            alias_tokens.extend(["mail", "envelope"])
        elif lowered == "bell":
            alias_tokens.extend(["notification", "notifications"])
        elif lowered in ("notification", "notifications"):
            alias_tokens.extend(["bell", "notifications", "notification"])
        elif lowered in ("profile", "avatar", "user", "account"):
            alias_tokens.extend(["profile", "avatar", "user", "account"])
        elif lowered == "camera":
            alias_tokens.extend(["photo", "image"])
        elif lowered in ("photo", "image"):
            alias_tokens.extend(["camera", "photo", "image"])
        elif lowered == "settings":
            alias_tokens.extend(["gear", "cog"])
        elif lowered in ("gear", "cog"):
            alias_tokens.extend(["settings", "gear", "cog"])
        elif lowered == "cart":
            alias_tokens.extend(["shopping", "basket"])
        elif lowered == "shopping":
            alias_tokens.extend(["cart", "basket"])
        elif lowered in ("app", "apps", "launcher", "grid", "waffle", "menu", "dots"):
            alias_tokens.extend(["app", "apps", "launcher", "grid", "waffle", "menu", "dots"])
    tokens = []
    for token in alias_tokens:
        cleaned_token = str(token or "").strip()
        if len(cleaned_token) < 3:
            continue
        if cleaned_token.lower() in ("icon", "button", "action", "alt"):
            continue
        if cleaned_token not in tokens:
            tokens.append(cleaned_token)
    if any(token.lower() in ("profile", "user", "account", "avatar") for token in tokens):
        try:
            viewport = page.viewport_size or dict()
        except Exception:
            viewport = dict()
        try:
            viewport_width = float(viewport.get("width") or 1280)
            viewport_height = float(viewport.get("height") or 720)
            candidates = page.locator(
                "a.anchor, "
                "[aria-label*='profile' i], [title*='profile' i], img[alt*='profile' i], "
                "[aria-label*='avatar' i], [title*='avatar' i], img[alt*='avatar' i], "
                "[aria-label*='account' i], [title*='account' i], "
                "[class*='avatar' i], [class*='account' i], [class*='user' i], "
                "a, button, [role='button'], img, svg, span"
            )
            best = None
            best_score = -1
            seen = set()
            cap = min(candidates.count(), 60)
            for i in range(cap):
                locator = candidates.nth(i)
                try:
                    if not locator.is_visible(timeout=200):
                        continue
                except Exception:
                    continue
                try:
                    box = locator.bounding_box()
                except Exception:
                    box = None
                if not box:
                    continue
                w = float(box.get("width", 0) or 0)
                h = float(box.get("height", 0) or 0)
                x = float(box.get("x", 0) or 0)
                y = float(box.get("y", 0) or 0)
                if w < 16 or h < 12:
                    continue
                try:
                    text = (locator.inner_text() or "").strip()
                except Exception:
                    text = ""
                parts = [text]
                for attr in ("aria-label", "title", "alt", "id", "class"):
                    try:
                        value = locator.get_attribute(attr) or ""
                    except Exception:
                        value = ""
                    if value:
                        parts.append(str(value))
                haystack = " | ".join(part for part in parts if part).lower()
                if not haystack or haystack in seen:
                    continue
                seen.add(haystack)
                if any(
                    bad in haystack
                    for bad in (
                        "my profile",
                        "view full profile",
                        "update details",
                        "contact details",
                        "save corrections",
                        "cancel",
                        "organogram",
                    )
                ):
                    continue
                try:
                    anc = locator.locator(
                        "xpath=ancestor-or-self::*[self::button or self::a or @role='button' or @onclick][1]"
                    )
                    clickable = anc.count() > 0
                except Exception:
                    clickable = False
                score = 0.0
                if x >= viewport_width * 0.55:
                    score += 40
                if x >= viewport_width * 0.75:
                    score += 60
                if y <= max(150.0, viewport_height * 0.25):
                    score += 45
                if clickable:
                    score += 35
                if "anchor" in haystack:
                    score += 25
                if any(token in haystack for token in ("profile", "avatar", "account", "user")):
                    score += 120
                elif x >= viewport_width * 0.75 and y <= 100 and 2 <= len(text) <= 40:
                    score += 45
                if score > best_score:
                    best_score = score
                    best = locator
            if best is not None and best_score >= 70:
                try:
                    anc = best.locator(
                        "xpath=ancestor-or-self::*[self::button or self::a or @role='button' or @onclick][1]"
                    )
                    if anc.count() > 0:
                        anc.first.click()
                        return
                except Exception:
                    pass
                best.click()
                return
        except Exception:
            pass
    if any(token.lower() in ("app", "apps", "launcher", "grid", "waffle", "menu", "dots") for token in tokens):
        try:
            viewport = page.viewport_size or dict()
        except Exception:
            viewport = dict()
        try:
            viewport_width = float(viewport.get("width") or 1280)
            viewport_height = float(viewport.get("height") or 720)
            candidates = page.locator(
                "[aria-label*='app' i], [title*='app' i], [data-testid*='app' i], [data-test*='app' i], "
                "[aria-label*='launcher' i], [title*='launcher' i], [data-testid*='launcher' i], "
                "[aria-label*='grid' i], [title*='grid' i], [data-testid*='grid' i], [data-test*='grid' i], "
                "[aria-label*='menu' i], [title*='menu' i], [data-testid*='menu' i], [data-test*='menu' i], "
                "[class*='app' i], [class*='launcher' i], [class*='grid' i], [class*='menu' i], "
                "button, a, [role='button'], [role='link'], svg, img, span, div"
            )
            best = None
            best_score = -1
            cap = min(candidates.count(), 80)
            for i in range(cap):
                locator = candidates.nth(i)
                try:
                    if not locator.is_visible(timeout=200):
                        continue
                except Exception:
                    continue
                try:
                    box = locator.bounding_box()
                except Exception:
                    box = None
                if not box:
                    continue
                x = float(box.get("x", 0) or 0)
                y = float(box.get("y", 0) or 0)
                w = float(box.get("width", 0) or 0)
                h = float(box.get("height", 0) or 0)
                if x > viewport_width * 0.35 or y > max(180.0, viewport_height * 0.35):
                    continue
                if w < 16 or h < 16 or w > 90 or h > 90:
                    continue
                parts = []
                try:
                    parts.append(locator.inner_text() or "")
                except Exception:
                    pass
                for attr in ("aria-label", "title", "alt", "id", "class", "data-testid", "data-test"):
                    try:
                        parts.append(locator.get_attribute(attr) or "")
                    except Exception:
                        pass
                haystack = " | ".join(part for part in parts if part).lower()
                cell_count = 0
                try:
                    cell_count = locator.locator(
                        "xpath=.//*[self::svg or self::rect or self::circle or self::path or self::span or self::i]"
                    ).count()
                except Exception:
                    cell_count = 0
                if not any(marker in haystack for marker in ("app", "apps", "launcher", "grid", "waffle", "menu", "dot", "tile", "module")) and not (4 <= cell_count <= 18):
                    continue
                score = 0.0
                score += max(0.0, 220.0 - x)
                score += max(0.0, 180.0 - y)
                if any(marker in haystack for marker in ("app", "apps", "launcher", "grid", "waffle", "menu")):
                    score += 180
                try:
                    anc = locator.locator(
                        "xpath=ancestor-or-self::*[self::button or self::a or @role='button' or @onclick][1]"
                    )
                    if anc.count() > 0:
                        score += 80
                except Exception:
                    pass
                if score > best_score:
                    best_score = score
                    best = locator
            if best is not None and best_score >= 180:
                try:
                    anc = best.locator(
                        "xpath=ancestor-or-self::*[self::button or self::a or @role='button' or @onclick][1]"
                    )
                    if anc.count() > 0:
                        anc.first.click()
                        return
                except Exception:
                    pass
                best.click()
                return
        except Exception:
            pass
    for token in tokens:
        safe = token.replace('"', '\\"')
        selectors = (
            f"button:has(svg[class*='{{safe}}' i])",
            f"[role='button']:has(svg[class*='{{safe}}' i])",
            f"a:has(svg[class*='{{safe}}' i])",
            f"button:has([data-lucide*='{{safe}}' i])",
            f"[role='button']:has([data-lucide*='{{safe}}' i])",
            f"a:has([data-lucide*='{{safe}}' i])",
            f"svg[class*='lucide-{{safe}}' i]",
            f"svg[class*='{{safe}}' i]",
            f"[data-lucide*='{{safe}}' i]",
            f"img[alt*='{{safe}}' i]",
            f"[aria-label*='{{safe}}' i]",
            f"[title*='{{safe}}' i]",
            f"[data-testid*='{{safe}}' i]",
            f"[data-test*='{{safe}}' i]",
        )
        for selector in selectors:
            try:
                loc = page.locator(selector)
                if loc.count() > 0:
                    target = loc.first
                    try:
                        anc = target.locator(
                            "xpath=ancestor-or-self::*[self::button or self::a or @role='button' or @onclick][1]"
                        )
                        if anc.count() > 0:
                            anc.first.click()
                            return
                    except Exception:
                        pass
                    target.click()
                    return
            except Exception:
                pass
        try:
            loc = page.locator(
                f"[aria-label*='{{safe}}' i], [title*='{{safe}}' i],"
                f" [data-testid*='{{safe}}' i], [data-test*='{{safe}}' i],"
                f" [class*='{{safe}}' i], img[alt*='{{safe}}' i],"
                f" svg[aria-label*='{{safe}}' i], button[aria-label*='{{safe}}' i],"
                f" a[aria-label*='{{safe}}' i]"
            )
            if loc.count() > 0:
                loc.first.click()
                return
        except Exception:
            pass
        if token.lower() in ("profile", "user", "account", "avatar"):
            for extra in ("avatar", "profile", "user", "account"):
                safe2 = extra.replace('"', '\\"')
                try:
                    loc = page.locator(
                        f"[aria-label*='{{safe2}}' i], [title*='{{safe2}}' i],"
                        f" [data-testid*='{{safe2}}' i], [data-test*='{{safe2}}' i],"
                        f" [class*='{{safe2}}' i], img[alt*='{{safe2}}' i],"
                        f" svg[aria-label*='{{safe2}}' i], button[aria-label*='{{safe2}}' i],"
                        f" a[aria-label*='{{safe2}}' i]"
                    )
                    if loc.count() > 0:
                        loc.first.click()
                        return
                except Exception:
                    pass
            try:
                candidates = page.locator("img, svg, [role='img']")
                cap = min(candidates.count(), 40)
                best = None
                best_score = -1
                for i in range(cap):
                    el = candidates.nth(i)
                    try:
                        box = el.bounding_box()
                    except Exception:
                        box = None
                    if not box:
                        continue
                    w = box.get("width", 0)
                    h = box.get("height", 0)
                    if w < 32 or h < 32:
                        continue
                    if abs(w - h) > 8:
                        continue
                    try:
                        is_round = el.evaluate(
                            \"\"\"(node) => {{
                                try {{
                                    const cs = getComputedStyle(node);
                                    const br = cs.borderRadius || "";
                                    if (br.includes("%")) {{
                                        const pct = parseFloat(br);
                                        if (!isNaN(pct) && pct >= 45) return true;
                                    }}
                                    const val = parseFloat(br);
                                    if (!isNaN(val)) {{
                                        const min = Math.min(node.offsetWidth || 0, node.offsetHeight || 0);
                                        if (min && val >= min * 0.45) return true;
                                    }}
                                }} catch {{}}
                                return false;
                            }}\"\"\"
                        )
                    except Exception:
                        is_round = False
                    if not is_round:
                        continue
                    area = w * h
                    y = box.get("y", 0) or 0
                    score = area - (y * 5)
                    if score > best_score:
                        best_score = score
                        best = el
                if best is not None:
                    try:
                        anc = best.locator(
                            "xpath=ancestor-or-self::*[self::button or self::a or @role='button' or @onclick][1]"
                        )
                        if anc.count() > 0:
                            anc.first.click()
                            return
                    except Exception:
                        pass
                    try:
                        best.click()
                        return
                    except Exception:
                        pass
            except Exception:
                pass
            try:
                candidates = page.locator("div, span, a, button")
                cap = min(candidates.count(), 60)
                best = None
                best_score = -1
                for i in range(cap):
                    el = candidates.nth(i)
                    try:
                        box = el.bounding_box()
                    except Exception:
                        box = None
                    if not box:
                        continue
                    w = box.get("width", 0)
                    h = box.get("height", 0)
                    if w < 32 or h < 32:
                        continue
                    if abs(w - h) > 8:
                        continue
                    try:
                        has_bg = el.evaluate(
                            \"\"\"(node) => {{
                                try {{
                                    const cs = getComputedStyle(node);
                                    const bg = cs.backgroundImage || "";
                                    if (!bg || bg === "none") return false;
                                    return true;
                                }} catch {{}}
                                return false;
                            }}\"\"\"
                        )
                    except Exception:
                        has_bg = False
                    if not has_bg:
                        continue
                    try:
                        is_round = el.evaluate(
                            \"\"\"(node) => {{
                                try {{
                                    const cs = getComputedStyle(node);
                                    const br = cs.borderRadius || "";
                                    if (br.includes("%")) {{
                                        const pct = parseFloat(br);
                                        if (!isNaN(pct) && pct >= 45) return true;
                                    }}
                                    const val = parseFloat(br);
                                    if (!isNaN(val)) {{
                                        const min = Math.min(node.offsetWidth || 0, node.offsetHeight || 0);
                                        if (min && val >= min * 0.45) return true;
                                    }}
                                }} catch {{}}
                                return false;
                            }}\"\"\"
                        )
                    except Exception:
                        is_round = False
                    if not is_round:
                        continue
                    area = w * h
                    y = box.get("y", 0) or 0
                    score = area - (y * 5)
                    if score > best_score:
                        best_score = score
                        best = el
                if best is not None:
                    try:
                        anc = best.locator(
                            "xpath=ancestor-or-self::*[self::button or self::a or @role='button' or @onclick][1]"
                        )
                        if anc.count() > 0:
                            anc.first.click()
                            return
                    except Exception:
                        pass
                    try:
                        best.click()
                        return
                    except Exception:
                        pass
            except Exception:
                pass
            try:
                target = page.evaluate(
                    \"\"\"() => {{
                        const nodes = Array.from(document.querySelectorAll('img, svg, div, span, a, button'));
                        const isVisible = (el) => {{
                            const cs = getComputedStyle(el);
                            if (!cs || cs.display === 'none' || cs.visibility === 'hidden') return false;
                            if (parseFloat(cs.opacity || '1') <= 0.05) return false;
                            const r = el.getBoundingClientRect();
                            return r.width >= 32 && r.height >= 32;
                        }};
                        const isRound = (el) => {{
                            const cs = getComputedStyle(el);
                            const br = cs.borderRadius || '';
                            if (cs.clipPath && cs.clipPath.includes('circle')) return true;
                            if (br.includes('%')) {{
                                const pct = parseFloat(br);
                                return !isNaN(pct) && pct >= 45;
                            }}
                            const val = parseFloat(br);
                            if (!isNaN(val)) {{
                                const min = Math.min(el.offsetWidth || 0, el.offsetHeight || 0);
                                return min && val >= min * 0.45;
                            }}
                            return false;
                        }};
                        let best = null;
                        let bestScore = -1;
                        for (const el of nodes) {{
                            if (!isVisible(el)) continue;
                            const r = el.getBoundingClientRect();
                            const w = r.width, h = r.height;
                            if (Math.abs(w - h) > 10) continue;
                            if (!isRound(el)) continue;
                            const area = w * h;
                            const score = area - (r.y * 5);
                            if (score > bestScore) {{
                                bestScore = score;
                                best = r;
                            }}
                        }}
                        if (!best) return null;
                        return {{ x: best.x + best.width / 2, y: best.y + best.height / 2 }};
                    }}\"\"\"
                )
                if target and isinstance(target, dict) and target.get("x") is not None and target.get("y") is not None:
                    page.mouse.click(float(target["x"]), float(target["y"]))
                    return
            except Exception:
                pass
            try:
                candidates = page.locator("img, svg")
                cap = min(candidates.count(), 20)
                for i in range(cap):
                    el = candidates.nth(i)
                    try:
                        box = el.bounding_box()
                    except Exception:
                        box = None
                    if not box:
                        continue
                    if box.get("width", 0) < 28 or box.get("height", 0) < 28:
                        continue
                    try:
                        anc = el.locator("xpath=ancestor-or-self::*[self::button or self::a or @role='button' or @onclick][1]")
                        if anc.count() > 0:
                            anc.first.click()
                            return
                    except Exception:
                        pass
                    try:
                        el.click()
                        return
                    except Exception:
                        pass
            except Exception:
                pass
        try:
            loc = page.get_by_role("button", name=re.compile(re.escape(token), re.I))
            if loc.count() > 0:
                loc.first.click()
                return
        except Exception:
            pass
        try:
            loc = page.get_by_role("link", name=re.compile(re.escape(token), re.I))
            if loc.count() > 0:
                loc.first.click()
                return
        except Exception:
            pass
        try:
            txt = page.get_by_text(token)
            if txt.count() > 0:
                anc = txt.first.locator("xpath=ancestor-or-self::*[self::button or self::a or @role='button' or @onclick][1]")
                if anc.count() > 0:
                    anc.first.click()
                    return
        except Exception:
            pass
    raise RuntimeError("Icon not found: " + str(label))

"""

    run_tag_map_block = f"RUN_TAGS = {json.dumps(run_tag_map, indent=4)}\n\n"

    main_block = "\nif __name__ == '__main__':\n"
    main_block += "    import sys\n"
    main_block += "    import os\n"
    main_block += "    selected_tags = {t.strip().lower() for t in os.getenv('SMARTAI_RUN_TAGS', '').split(',') if t.strip()}\n"
    main_block += "    selected_names = {n.strip() for n in os.getenv('SMARTAI_RUN_FUNCTIONS', '').split(',') if n.strip()}\n"
    main_block += "    def _should_run(name):\n"
    main_block += "        if selected_names:\n"
    main_block += "            return name in selected_names\n"
    main_block += "        if not selected_tags:\n"
    main_block += "            return True\n"
    main_block += "        return any(tag in selected_tags for tag in RUN_TAGS.get(name, []))\n"
    main_block += "    failures = 0\n"

    for runner_name in runner_names:
        main_block += (
            f"    if _should_run('{runner_name}'):\n"
            f"        try:\n"
            f"            print(f'\\n[{category}_runner] Running test: {runner_name}...\\n')\n"
            f"            run_allure_case('{runner_name}', {runner_name})\n"
            f"            print(f'\\n[{category}_runner] {runner_name}: PASS\\n')\n"
            f"        except Exception as exc:\n"
            f"            failures += 1\n"
            f"            print(f'\\n[{category}_runner] {runner_name}: FAIL\\nDetails: {{exc}}\\n')\n"
            f"    else:\n"
            f"        print(f'\\n[{category}_runner] Skipping {runner_name} (tag filter)\\n')\n"
        )

    main_block += "    _close_shared_browser()\n"
    main_block += (
        "\n    if failures > 0:\n"
        "        print(f'\\n[" + category + "_runner] Summary: {failures} test(s) failed.')\n"
        "        sys.exit(1)\n"
        "    else:\n"
        "        print(f'\\n[" + category + "_runner] Summary: All tests passed.')\n"
        "        sys.exit(0)\n"
    )

    if fixed_script_name:
        script_name = fixed_script_name
    else:
        base_slug = _infer_script_slug(original_story, category, db=db, project_id=project_id)
        if category in {"ui", "security", "accessibility"}:
            if category == "ui":
                script_name = f"ui_script_{base_slug}.py"
            else:
                script_name = f"{category}_script_{base_slug}.py"
            if (target_dir / script_name).exists():
                suffix = 1
                while (
                    (target_dir / f"{'ui' if category == 'ui' else category}_script_{base_slug}_{suffix}.py").exists()
                ):
                    suffix += 1
                if category == "ui":
                    script_name = f"ui_script_{base_slug}_{suffix}.py"
                else:
                    script_name = f"{category}_script_{base_slug}_{suffix}.py"
        else:
            script_idx = next_index(target_dir, f"{category}_script_{{}}.py")
            script_name = f"{category}_script_{script_idx}.py"
    script_path = target_dir / script_name

    with open(script_path, "w", encoding="utf-8") as f:
        f.write(header)
        f.write(run_tag_map_block)
        f.write(function_code)
        if function_code and not function_code.endswith("\n"):
            f.write("\n")
        f.write(main_block)

    print(f"{script_name} generated with {len(wrapper_blocks)} runner(s) in {target_dir}")
    return script_path
