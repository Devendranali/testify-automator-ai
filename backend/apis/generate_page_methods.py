from fastapi import APIRouter, Depends, Query
from pathlib import Path
import json
import os
import re
from contextlib import contextmanager
from typing import Any
from sqlalchemy.orm import Session

from services.test_generation_utils import runtime_collection, filter_all_pages
from utils.match_utils import normalize_page_name
from utils.project_context import filter_metadata_by_project
from utils.request_context import set_request_context, reset_request_context
from utils.smart_ai_utils import ensure_smart_ai_module
from database.project_storage import DatabaseBackedProjectStorage
from .projects_api import _ensure_project_structure, get_current_user, get_user_project
from database.models import User
from database.session import get_db

router = APIRouter()


@contextmanager
def _temporary_project_env(project_paths: dict, project_id: int):
    previous = {
        "SMARTAI_PROJECT_DIR": os.environ.get("SMARTAI_PROJECT_DIR"),
        "SMARTAI_SRC_DIR": os.environ.get("SMARTAI_SRC_DIR"),
        "SMARTAI_CHROMA_PATH": os.environ.get("SMARTAI_CHROMA_PATH"),
        "SMARTAI_PROJECT_ID": os.environ.get("SMARTAI_PROJECT_ID"),
    }

    os.environ["SMARTAI_PROJECT_DIR"] = project_paths["project_root"]
    os.environ["SMARTAI_SRC_DIR"] = project_paths["src_dir"]
    os.environ["SMARTAI_CHROMA_PATH"] = project_paths["chroma_path"]
    os.environ["SMARTAI_PROJECT_ID"] = str(project_id)

    tokens = set_request_context(
        project_id=project_id,
        project_dir=project_paths["project_root"],
        src_dir=project_paths["src_dir"],
        chroma_path=project_paths["chroma_path"],
    )
    try:
        yield
    finally:
        reset_request_context(tokens)
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def safe(value: str) -> str:
    return re.sub(r"\W+", "_", (value or "").lower()).strip("_") or "element"


def _clean_option_like_label(value: str) -> str:
    raw = (value or "").strip()
    if not raw:
        return ""
    parts = [p.strip() for p in re.split(r"\s*-\s*", raw) if p.strip()]
    if len(parts) >= 2:
        lowered = raw.lower()
        if any(token in lowered for token in ("radio", "option", "checkbox", "toggle", "switch", "select")):
            return parts[0]
    return raw


_INPUT_HINT_PREFIXES = (
    "please enter ",
    "enter ",
    "type ",
    "fill ",
    "input ",
    "provide ",
    "select ",
    "choose ",
    "pick ",
)


def _normalize_input_hint(value: str) -> str:
    text = re.sub(r"\s+", " ", str(value or "").strip())
    if not text:
        return ""
    lowered = text.lower()
    for prefix in _INPUT_HINT_PREFIXES:
        if lowered.startswith(prefix):
            text = text[len(prefix):].strip()
            lowered = text.lower()
            break
    text = re.sub(r"\s+(field|textbox|input|value|text|here)\s*$", "", text, flags=re.I).strip()
    return text


def _is_generic_input_prompt(value: str) -> bool:
    text = re.sub(r"\s+", " ", str(value or "").strip()).lower()
    if not text:
        return True
    if any(text.startswith(prefix) for prefix in _INPUT_HINT_PREFIXES):
        return True
    if text in {"dd/mm/yyyy", "hh:mm", "hh - mm", "mm/dd/yyyy", "yyyy-mm-dd"}:
        return True
    if "enter your message here" in text:
        return True
    return False


def _is_meaningful_field_label(value: str) -> bool:
    text = _clean_option_like_label(str(value or "").strip())
    if not text:
        return False
    lowered = text.lower()
    if _is_generic_input_prompt(lowered):
        return False
    if len(text) > 80:
        return False
    return True


def _annotate_legacy_input_labels(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    annotated: list[dict[str, Any]] = []
    recent_labels: list[str] = []

    def _remember_label(candidate: str) -> None:
        cleaned = _clean_option_like_label(candidate)
        if not _is_meaningful_field_label(cleaned):
            return
        if recent_labels and recent_labels[-1].lower() == cleaned.lower():
            return
        recent_labels.append(cleaned)
        if len(recent_labels) > 5:
            recent_labels.pop(0)

    for entry in entries:
        if not isinstance(entry, dict):
            continue
        updated = dict(entry)
        action_type = _action_type(updated)
        label_text = str(updated.get("label_text") or "").strip()
        placeholder = str(updated.get("placeholder") or "").strip()

        if action_type == "input" and not str(updated.get("canonical_label_text") or "").strip():
            candidate_label = ""
            normalized_current = _normalize_input_hint(label_text or placeholder)

            if _is_meaningful_field_label(label_text) and not _is_generic_input_prompt(label_text):
                candidate_label = label_text
            elif recent_labels:
                if normalized_current:
                    for prior in reversed(recent_labels):
                        if _normalize_input_hint(prior).lower() == normalized_current.lower():
                            candidate_label = prior
                            break
                if not candidate_label and (_is_generic_input_prompt(label_text) or _is_generic_input_prompt(placeholder) or normalized_current):
                    candidate_label = recent_labels[-1]

            if candidate_label:
                updated["canonical_label_text"] = candidate_label
                updated.setdefault("field_context_label", candidate_label)

        if action_type == "input":
            source_label = (
                updated.get("canonical_label_text")
                or updated.get("field_context_label")
                or label_text
            )
            _remember_label(str(source_label or ""))
        elif (updated.get("ocr_type") or "").lower() == "label":
            _remember_label(label_text)

        annotated.append(updated)
    return annotated


def ensure_unique(base_name: str, used: dict[str, int]) -> str:
    name = base_name
    if name not in used:
        used[name] = 1
        return name
    used[name] += 1
    return f"{base_name}_{used[name]}"


def _load_json_list(path: Path) -> list:
    try:
        data = json.loads(path.read_text(encoding="utf-8") or "[]")
    except Exception:
        return []
    return data if isinstance(data, list) else []


def _page_entries_from_enrichment(meta_dir: Path, prefix: str) -> dict[str, list[dict[str, Any]]]:
    page_entries: dict[str, list[dict[str, Any]]] = {}
    pattern = f"{prefix}_*.json"

    for f in meta_dir.glob(pattern):
        if f.name == f"{prefix}.json":
            continue

        page_key = f.stem[len(prefix) + 1 :]
        entries = _load_json_list(f)
        if not entries:
            continue

        keys = {normalize_page_name(page_key)}
        if page_key:
            keys.add(page_key)
            keys.add(page_key.lower())
        keys.discard("")

        for key in keys:
            page_entries.setdefault(key, []).extend(
                [{**e, "__smartai_source_prefix": prefix} for e in entries if isinstance(e, dict)]
            )

    if page_entries:
        return page_entries

    aggregate_path = meta_dir / f"{prefix}.json"
    aggregate_entries = _load_json_list(aggregate_path)

    for entry in aggregate_entries:
        if not isinstance(entry, dict):
            continue

        page_name = (entry.get("page_name") or entry.get("page") or "").strip()
        if not page_name:
            continue

        keys = {normalize_page_name(page_name), page_name, page_name.lower()}
        keys.discard("")

        for key in keys:
            page_entries.setdefault(key, []).append({**entry, "__smartai_source_prefix": prefix})

    return page_entries


def _bbox_from_entry(entry: dict) -> dict[str, Any]:
    bbox = entry.get("bbox") or {}
    if isinstance(bbox, str):
        try:
            parsed = json.loads(bbox.replace("'", '"'))
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            return {}
    return bbox if isinstance(bbox, dict) else {}


def _is_generic_container_selector(value: Any) -> bool:
    selector = str(value or "").strip().lower()
    if not selector:
        return False
    if any(token in selector for token in ("button", "[role=", "input", "textarea", "select", "a", "svg", "img")):
        return False
    if selector in {"div", "span", "section", "article"}:
        return True
    if selector.startswith(("div.", "span.", "section.", "article.")):
        return True
    generic_prefixes = (".mui", ".mat", ".ant-", ".chakra")
    return selector.startswith(generic_prefixes)


def _has_strong_locator(entry: dict) -> bool:
    css_selector = entry.get("css_selector")
    return bool(
        (entry.get("test_id") or entry.get("data_testid") or entry.get("data_test_id"))
        or entry.get("id")
        or entry.get("dom_id")
        or entry.get("data_qa")
        or entry.get("data-qa")
        or entry.get("name")
        or entry.get("get_by_role")
        or entry.get("get_by_label")
        or entry.get("placeholder")
        or (css_selector and not _is_generic_container_selector(css_selector))
        or entry.get("xpath")
    )


def _icon_hint_values(entry: dict[str, Any]) -> list[str]:
    values: list[str] = []
    for key in (
        "disambiguation_key",
        "field_context_label",
        "related_input_label",
        "dom_accessible_name",
        "container_context",
        "icon_family",
        "icon_variant",
        "get_by_text",
        "placeholder",
        "variant_text",
        "label_text",
        "aria_label",
        "aria-label",
        "alt_text",
        "alt",
        "title_text",
        "title",
        "intent",
        "unique_name",
        "name",
        "css_selector",
    ):
        value = str(entry.get(key) or "").strip()
        if not value:
            continue
        if value not in values:
            values.append(value)
    return values


def _icon_context_label(entry: dict[str, Any]) -> str:
    field_context = str(entry.get("field_context_label") or entry.get("related_input_label") or "").strip()
    family = str(entry.get("icon_family") or "").strip().replace("_", " ")
    if field_context and family and family.lower() not in field_context.lower():
        return f"{field_context} {family}".strip()
    if field_context:
        return field_context
    if family:
        return family
    disambiguation = str(entry.get("disambiguation_key") or "").strip().replace("_", " ")
    if disambiguation:
        return disambiguation
    return ""


def _icon_display_label(entry: dict[str, Any]) -> str:
    for key in (
        "field_context_label",
        "related_input_label",
        "dom_accessible_name",
        "disambiguation_key",
        "icon_family",
        "get_by_text",
        "placeholder",
        "variant_text",
        "label_text",
        "alt_text",
        "alt",
        "title_text",
        "title",
        "aria_label",
        "aria-label",
        "intent",
    ):
        value = str(entry.get(key) or "").strip()
        if value:
            return value
    return ""


def _calendar_related_input_candidates(entry: dict[str, Any]) -> list[str]:
    intent = str(entry.get("intent") or "").strip().lower()
    ocr_type = str(entry.get("ocr_type") or "").strip().lower()
    if "calendar" not in intent and "date" not in intent and ocr_type not in {"iconbutton", "imagebutton"}:
        return []
    values: list[str] = []
    for key in ("related_input_label", "field_context_label", "placeholder"):
        value = str(entry.get(key) or "").strip()
        if value and value not in values:
            values.append(value)
    lowered = " ".join(
        str(entry.get(key) or "").strip().lower()
        for key in ("label_text", "get_by_text", "variant_text", "intent", "icon_family")
        if str(entry.get(key) or "").strip()
    )
    if any(token in lowered for token in ("calendar", "date", "from", "to")):
        for fallback in ("dd/mm/yyyy", "mm/dd/yyyy", "yyyy-mm-dd"):
            if fallback not in values:
                values.append(fallback)
    if any(token in lowered for token in ("clock", "time", "hour", "minute")):
        for fallback in ("hh:mm", "hh - mm"):
            if fallback not in values:
                values.append(fallback)
    return values


def _icon_field_anchor_candidates(entry: dict[str, Any]) -> list[str]:
    values: list[str] = []

    def _add(value: str) -> None:
        text = re.sub(r"\s+", " ", str(value or "").strip())
        if not text:
            return
        lowered = text.lower()
        if lowered in {"calendar", "clock", "icon", "button", "action"}:
            return
        if len(text) > 40:
            return
        if text not in values:
            values.append(text)

    for key in ("field_context_label", "disambiguation_key"):
        _add(str(entry.get(key) or ""))

    for key in ("get_by_text", "variant_text"):
        raw = str(entry.get(key) or "").strip()
        if not raw:
            continue
        cleaned = re.sub(r"\b(calendar|clock)\s+icon\b", "", raw, flags=re.I)
        cleaned = re.sub(r"\bicon\b", "", cleaned, flags=re.I)
        cleaned = re.sub(r"\s+", " ", cleaned).strip(" -_:")
        _add(cleaned)

    intent = str(entry.get("intent") or "").strip().lower()
    if intent:
        for suffix in (
            "_calendar_icon_action",
            "_clock_icon_action",
            "_time_icon_action",
            "_icon_action",
            "_action",
        ):
            if intent.endswith(suffix):
                base = intent[: -len(suffix)].strip("_")
                cleaned = " ".join(part for part in base.split("_") if part and part not in {"icon", "button"})
                _add(cleaned.title())
                break

    unique_name = str(entry.get("unique_name") or "").strip().lower()
    if unique_name:
        match = re.search(
            r"(?:^|_)(from|to|in_time|out_time|start_date|end_date|start_time|end_time)"
            r"(?:_calendar_icon_action|_clock_icon_action|_time_icon_action|_icon_action|_action)\b",
            unique_name,
        )
        if match:
            cleaned = " ".join(part for part in match.group(1).split("_") if part)
            _add(cleaned.title())

    return values


def _prefer_icon_heuristics_before_smartai(entry: dict[str, Any]) -> bool:
    if not _is_icon_like_entry(entry):
        return False
    css_selector = str(entry.get("css_selector") or "").strip()
    if css_selector and _is_generic_container_selector(css_selector) and not _has_strong_locator({**entry, "css_selector": ""}):
        return True
    family = str(entry.get("icon_family") or "").strip().lower()
    intent = str(entry.get("intent") or "").strip().lower()
    expected_text = " ".join(
        str(entry.get(key) or "").strip().lower()
        for key in ("get_by_text", "variant_text", "field_context_label", "related_input_label", "intent")
        if str(entry.get(key) or "").strip()
    )
    actual_text = " ".join(
        str(entry.get(key) or "").strip().lower()
        for key in ("label_text", "canonical_label_text", "dom_accessible_name", "aria_label", "aria-label")
        if str(entry.get(key) or "").strip()
    )
    try:
        y = float(entry.get("y", 0) or 0)
    except Exception:
        y = 0.0

    if family == "calendar" or ("calendar" in intent and "icon" in intent):
        expects_calendar_trigger = any(token in expected_text for token in ("from calendar", "to calendar", "calendar icon"))
        actual_looks_like_calendar = any(token in actual_text for token in ("calendar", "date", "from", "to"))
        if expects_calendar_trigger and not actual_looks_like_calendar:
            return True
        if expects_calendar_trigger and y < 0:
            return True
    return False


def _icon_hint_text(entry: dict[str, Any]) -> str:
    hints = _icon_hint_values(entry)
    return hints[0] if hints else ""


def _is_icon_like_entry(entry: dict[str, Any]) -> bool:
    ocr_type = str(entry.get("ocr_type") or "").strip().lower()
    if ocr_type in {"iconbutton", "imagebutton"}:
        return True
    if ocr_type != "image":
        return False
    joined = " ".join(v.lower() for v in _icon_hint_values(entry))
    if any(token in joined for token in ("icon", "avatar", "profile")):
        return True
    role = str(entry.get("role") or entry.get("aria_role") or "").strip().lower()
    if role in {"button", "link", "menuitem", "tab", "switch"}:
        return True
    attrs = entry.get("attributes") or {}
    if isinstance(attrs, dict):
        attr_role = str(attrs.get("role") or "").strip().lower()
        if attr_role in {"button", "link", "menuitem", "tab", "switch"}:
            return True
        if "onclick" in attrs:
            return True
        try:
            tabindex = str(attrs.get("tabindex") or "").strip()
            if tabindex and tabindex != "-1":
                return True
        except Exception:
            pass
    label = (
        entry.get("label_text")
        or entry.get("get_by_text")
        or entry.get("aria_label")
        or entry.get("aria-label")
        or entry.get("title")
        or ""
    )
    label = str(label).strip()
    if label and len(label) <= 32 and (
        entry.get("aria_label")
        or entry.get("aria-label")
        or entry.get("title")
        or entry.get("data_testid")
        or entry.get("data-testid")
    ):
        return True
    return False


def _is_profile_icon_entry(entry: dict[str, Any]) -> bool:
    if not _is_icon_like_entry(entry):
        return False
    joined = " ".join(v.lower() for v in _icon_hint_values(entry))
    return any(token in joined for token in ("profile", "avatar", "user", "account"))


def _is_captcha_entry(entry: dict[str, Any]) -> bool:
    for key in (
        "label_text",
        "placeholder",
        "get_by_text",
        "intent",
        "unique_name",
        "aria_label",
        "aria-label",
        "name",
        "id",
        "dom_id",
        "data_testid",
        "data-testid",
        "css_selector",
    ):
        value = str(entry.get(key) or "").strip().lower()
        if "captcha" in value:
            return True
    return False


def _is_password_entry(entry: dict[str, Any]) -> bool:
    for key in (
        "label_text",
        "placeholder",
        "get_by_text",
        "intent",
        "unique_name",
        "aria_label",
        "aria-label",
        "name",
        "id",
        "dom_id",
        "input_type",
        "element_type",
        "type",
        "css_selector",
    ):
        value = str(entry.get(key) or "").strip().lower()
        if any(token in value for token in ("password", "passwd", "pwd")):
            return True
    return False


def _action_type(entry: dict) -> str:
    ocr_type = (entry.get("ocr_type") or "").lower()
    tag = (entry.get("tag_name") or entry.get("tag") or "").lower()

    hint_fields = (
        "input_type",
        "element_type",
        "detected_type",
        "role",
        "aria_role",
        "intent",
        "unique_name",
        "tag_name",
    )
    for key in hint_fields:
        val = (entry.get(key) or "").lower()
        if any(k in val for k in ("checkbox", "radio", "toggle", "switch")):
            return "check"

    if ocr_type in {
        "textbox",
        "text",
        "input",
        "textarea",
        "email",
        "password",
        "date",
        "datepicker",
        "time",
        "timepicker",
    }:
        return "input"

    if ocr_type in {"select", "dropdown", "combobox"}:
        return "select"

    if ocr_type in {"file", "fileinput", "upload"}:
        return "upload"

    if ocr_type in {"checkbox", "radio", "radiogroup", "toggle", "switch"}:
        return "check"

    if ocr_type in {"drag", "draggable"}:
        return "drag"

    if entry.get("is_draggable") is True:
        if ocr_type in {"button", "link", "anchor", "menu", "menubar"} or tag in {"a", "button"}:
            return "click"
        drag_handle = (entry.get("drag_handle_selector") or "").strip()
        return "drag" if drag_handle else "click"

    if _is_icon_like_entry(entry):
        return "click"

    if ocr_type in {
        "button",
        "submit",
        "iconbutton",
        "link",
        "anchor",
        "imagebutton",
        "tab",
        "tabpanel",
        "accordion",
        "panel",
        "menu",
        "menubar",
    }:
        return "click"

    if tag in {"button", "a"}:
        return "click"

    if tag in {"input", "textarea"}:
        return "input"

    if tag == "select":
        return "select"

    return "static"


def _click_modes(entry: dict[str, Any]) -> set[str]:
    raw = str(
        entry.get("click_type")
        or entry.get("click_action")
        or entry.get("action_hint")
        or ""
    ).lower()
    modes: set[str] = set()
    def _add_from(text: str) -> None:
        if not text:
            return
        if re.search(r"\b(double click|double-click|doubleclick|dblclick)\b", text):
            modes.add("double")
        if re.search(r"\b(right click|right-click|rightclick|context click|context-click|context menu)\b", text):
            modes.add("right")

    if raw:
        _add_from(raw)
    if not raw or not modes:
        candidate = " ".join(
            str(entry.get(k) or "")
            for k in (
                "label_text",
                "text",
                "get_by_text",
                "intent",
                "unique_name",
                "name",
            )
        ).lower()
        _add_from(candidate)
    if not modes:
        return set()
    raw = re.sub(r"[\\[\\]\"'()]", " ", raw)
    tokens = re.split(r"[,\s]+", raw)
    for token in tokens:
        if token in {"right", "rightclick", "right_click", "context", "contextmenu"}:
            modes.add("right")
        if token in {"double", "dbl", "dblclick", "doubleclick", "double_click", "dbl_click"}:
            modes.add("double")
    return modes


def _is_noisy_entry(entry: dict, action_type: str) -> bool:
    tag = (entry.get("tag_name") or entry.get("tag") or "").lower()
    label = (
        entry.get("label_text")
        or entry.get("text")
        or entry.get("get_by_text")
        or entry.get("placeholder")
        or ""
    ).strip()
    label_lc = label.lower()
    is_icon_like = _is_icon_like_entry(entry)
    icon_hint = _icon_hint_text(entry)

    if tag in {"html", "body"}:
        return True

    bbox = _bbox_from_entry(entry)
    try:
        width = float(bbox.get("width", 0) or 0)
        height = float(bbox.get("height", 0) or 0)
    except Exception:
        width, height = 0.0, 0.0

    if width >= 1200 and height >= 800:
        return True

    if "manual enrich" in label_lc and "close browser" in label_lc:
        return True

    if len(label) > 160:
        return True

    if action_type == "static":
        return True

    if action_type in {"click", "check", "input", "select", "upload", "drag"}:
        if not label and not _has_strong_locator(entry):
            if not (is_icon_like and icon_hint):
                return True
        if len(label) > 80 and not _has_strong_locator(entry):
            return True

    if tag in {"div", "span", "section", "article", "app-navbar", "app-home-page"} and not _has_strong_locator(entry):
        if len(label) > 40:
            return True

    return False


def _entry_score(entry: dict) -> int:
    score = 0
    if entry.get("test_id") or entry.get("data_testid") or entry.get("data_test_id"):
        score += 100
    if entry.get("id") or entry.get("dom_id"):
        score += 90
    if entry.get("name"):
        score += 80
    if entry.get("get_by_role"):
        score += 70
    if entry.get("get_by_label"):
        score += 60
    placeholder = str(entry.get("placeholder") or "").strip()
    label = (
        entry.get("label_text")
        or entry.get("text")
        or entry.get("get_by_text")
        or ""
    ).strip()
    if placeholder:
        # Prefer real input hints like "Enter Name" over placeholders that just repeat the label.
        if placeholder.lower() == label.lower():
            score += 10
        else:
            score += 50
            if re.match(r"^(enter|type|select)\b", placeholder.strip(), re.I):
                score += 15
    if entry.get("data_qa") or entry.get("data-qa"):
        score += 40
    css_selector = entry.get("css_selector")
    if css_selector:
        if _is_generic_container_selector(css_selector):
            score -= 25
        else:
            score += 20
    if entry.get("xpath"):
        score += 10
    if entry.get("dom_matched") is True:
        score += 25

    bbox = _bbox_from_entry(entry)
    try:
        width = float(bbox.get("width", 0) or 0)
        height = float(bbox.get("height", 0) or 0)
    except Exception:
        width, height = 0.0, 0.0
    if width > 0 and height > 0:
        score += 10

    label = (
        entry.get("label_text")
        or entry.get("text")
        or entry.get("get_by_text")
        or entry.get("placeholder")
        or ""
    ).strip()
    if label:
        score += 5
        if len(label) > 80:
            score -= 5

    return score


def _entry_locator_key(entry: dict) -> tuple:
    def _clean(value: Any) -> str:
        return str(value or "").strip().lower()

    test_id = _clean(entry.get("test_id") or entry.get("data_testid") or entry.get("data_test_id"))
    if test_id:
        return ("test_id", test_id)

    dom_id = _clean(entry.get("id") or entry.get("dom_id"))
    if dom_id:
        return ("dom_id", dom_id)

    name_attr = _clean(entry.get("name"))
    if name_attr:
        return ("name", name_attr)

    role = entry.get("get_by_role")
    if isinstance(role, dict):
        role_name = _clean(role.get("role"))
        accessible_name = _clean(role.get("name"))
        if role_name and accessible_name:
            return ("role", role_name, accessible_name)

    label = _clean(entry.get("get_by_label") or entry.get("label_text") or entry.get("placeholder"))
    if label:
        return ("label", label)

    css = _clean(entry.get("css_selector"))
    if css:
        return ("css", css)

    xpath = _clean(entry.get("xpath"))
    if xpath:
        return ("xpath", xpath)

    unique_name = _clean(entry.get("unique_name"))
    return ("unique", unique_name)


def _dedupe_entries(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    best: dict[tuple, dict[str, Any]] = {}
    for entry in entries:
        key = (_action_type(entry), _entry_locator_key(entry))
        if key not in best or _entry_score(entry) > _entry_score(best[key]):
            best[key] = entry
    return list(best.values())


def _best_entries_by_unique_name(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    best: dict[str, dict[str, Any]] = {}
    passthrough: list[dict[str, Any]] = []
    for entry in entries:
        unique_name = str(entry.get("unique_name") or "").strip()
        if not unique_name:
            passthrough.append(entry)
            continue
        current = best.get(unique_name)
        if current is None or _entry_score(entry) >= _entry_score(current):
            best[unique_name] = entry
    return list(best.values()) + passthrough


def _intent_tokens(intent: str) -> list[str]:
    raw = str(intent or "").strip().lower()
    if not raw:
        return []
    for suffix in (
        "_action",
        "_icon_action",
        "_button_action",
        "_link_action",
        "_iconbutton_action",
    ):
        if raw.endswith(suffix):
            raw = raw[: -len(suffix)]
            break
    return [part for part in raw.split("_") if part and part not in {"icon", "button", "link", "action"}]


def _icon_semantic_score(entry: dict[str, Any]) -> int:
    score = _entry_score(entry)
    intent = str(entry.get("intent") or "").strip().lower()
    if not intent:
        return score
    tokens = _intent_tokens(intent)
    if not tokens:
        return score
    haystack = " ".join(
        str(entry.get(key) or "").strip().lower()
        for key in (
            "label_text",
            "canonical_label_text",
            "raw_label_text",
            "get_by_text",
            "variant_text",
            "field_context_label",
            "related_input_label",
            "disambiguation_key",
            "dom_accessible_name",
            "unique_name",
        )
        if str(entry.get(key) or "").strip()
    )
    for token in tokens:
        if token in haystack:
            score += 35
    label = str(entry.get("label_text") or entry.get("canonical_label_text") or "").strip().lower()
    if label:
        normalized_label = "_".join(part for part in re.split(r"[^a-z0-9]+", label) if part)
        normalized_intent = "_".join(tokens)
        if normalized_label == normalized_intent:
            score += 80
    if _entry_source_prefix(entry) == "before_enrichment":
        score += 25
    return score


def _best_icon_entries_by_intent(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    best: dict[tuple[str, str], dict[str, Any]] = {}
    passthrough: list[dict[str, Any]] = []
    for entry in entries:
        intent = str(entry.get("intent") or "").strip().lower()
        if _action_type(entry) != "click" or not _is_icon_like_entry(entry) or not intent:
            passthrough.append(entry)
            continue
        key = (intent, str(entry.get("ocr_type") or "").strip().lower())
        current = best.get(key)
        if current is None or _icon_semantic_score(entry) >= _icon_semantic_score(current):
            best[key] = entry
    return list(best.values()) + passthrough


def _entry_source_prefix(entry: dict[str, Any]) -> str:
    return str(entry.get("__smartai_source_prefix") or "").strip().lower()


def _should_keep_entry_for_page_methods(entry: dict[str, Any], action_type: str) -> bool:
    source_prefix = _entry_source_prefix(entry)
    if source_prefix == "before_enrichment":
        if str(entry.get("unique_name") or "").strip():
            return True
        if _has_strong_locator(entry):
            return True
        label = (
            entry.get("label_text")
            or entry.get("text")
            or entry.get("get_by_text")
            or entry.get("placeholder")
            or entry.get("intent")
            or ""
        )
        if str(label).strip():
            return True
        return False
    return not _is_noisy_entry(entry, action_type)


ASSERT_HELPER_BLOCK = """import re
import os
import time
from datetime import date, timedelta
from playwright.sync_api import expect
 
def _ci(s):  # case-insensitive canonical
    return (s or "").strip().lower()
 
def _digits_only(s):
    return re.sub(r"\\D+", "", (s or ""))

def _is_day_number_label(value):
    label = str(value or "").strip()
    if not label.isdigit():
        return False
    try:
        day = int(label)
    except Exception:
        return False
    return 1 <= day <= 31
 
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

def _active_modal_scopes(page, label=None, placeholder=None):
    selectors = (
        "dialog[open], [role='dialog'], [role='alertdialog'], [aria-modal='true'], aside[aria-modal='true']",
        ".modal:visible, .drawer:visible, .popup:visible, .offcanvas.show, .ant-drawer-content, .MuiDrawer-paper",
    )
    scopes = []
    seen = set()

    def _contains_target(scope):
        if scope is None:
            return False
        checks = []
        if label:
            exact_re = re.compile(r"^\\s*" + re.escape(label) + r"\\s*$", re.I)
            checks.extend(
                (
                    lambda: scope.get_by_label(label, exact=True).count() > 0,
                    lambda: scope.get_by_label(exact_re).count() > 0,
                    lambda: scope.get_by_role("textbox", name=label, exact=True).count() > 0,
                    lambda: scope.get_by_role("button", name=label, exact=True).count() > 0,
                    lambda: scope.get_by_text(label, exact=True).count() > 0,
                    lambda: scope.get_by_text(exact_re).count() > 0,
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

    for selector in selectors:
        try:
            locator = page.locator(selector)
            count = min(locator.count(), 8)
        except Exception:
            count = 0
        for idx in range(count):
            try:
                scope = locator.nth(idx)
                if not scope.is_visible(timeout=150):
                    continue
                box = scope.bounding_box() or {}
                if float(box.get("width") or 0) < 180 or float(box.get("height") or 0) < 120:
                    continue
                key = repr(scope)
                if key in seen:
                    continue
                seen.add(key)
                if _contains_target(scope):
                    scopes.insert(0, scope)
                else:
                    scopes.append(scope)
            except Exception:
                continue
    return scopes

def _interaction_scopes(page, label=None, placeholder=None):
    scopes = []
    seen = set()

    def _add(scope):
        if scope is None:
            return
        key = repr(scope)
        if key in seen:
            return
        seen.add(key)
        scopes.append(scope)

    for scope in _active_modal_scopes(page, label=label, placeholder=placeholder):
        _add(scope)
    _add(page)
    for frame in getattr(page, "frames", []) or []:
        _add(frame)
    return scopes

def _is_section_expanded(page, section_label, required_texts=None, required_placeholders=None):
    label = str(section_label or "").strip()
    if not label:
        return False
    text_patterns = [
        re.compile(r"^\\s*" + re.escape(str(text).strip()) + r"\\s*\\*?\\s*$", re.I)
        for text in (required_texts or [])
        if str(text or "").strip()
    ]
    placeholder_values = [
        str(value).strip()
        for value in (required_placeholders or [])
        if str(value or "").strip()
    ]
    for scope in _active_modal_scopes(page, label=label) or [page]:
        for pattern in text_patterns:
            try:
                if scope.get_by_text(pattern).count() > 0:
                    return True
            except Exception:
                continue
        for placeholder in placeholder_values:
            try:
                if scope.get_by_placeholder(placeholder).count() > 0:
                    return True
            except Exception:
                continue
    return False

def ensure_section_expanded(page, section_label, required_texts=None, required_placeholders=None, timeout_ms: int = 2000):
    label = str(section_label or "").strip()
    if not label:
        raise RuntimeError("Section label is required")
    try:
        timeout_s = max(int(timeout_ms), 250) / 1000.0
    except Exception:
        timeout_s = 2.0
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if _is_section_expanded(page, label, required_texts=required_texts, required_placeholders=required_placeholders):
            return
        try:
            page.wait_for_timeout(150)
        except Exception:
            time.sleep(0.15)
    if _is_section_expanded(page, label, required_texts=required_texts, required_placeholders=required_placeholders):
        return
    exact_re = re.compile(r"^\\s*" + re.escape(label) + r"\\s*$", re.I)
    scopes = _active_modal_scopes(page, label=label) or [page]
    for scope in scopes:
        candidates = []
        strategies = (
            lambda: scope.get_by_role("button", name=exact_re).first,
            lambda: scope.get_by_text(exact_re).first,
            lambda: scope.locator("[role='button']").filter(has_text=exact_re).first,
            lambda: scope.locator("div,button,span").filter(has_text=exact_re).first,
        )
        for factory in strategies:
            try:
                locator = factory()
                if locator.count() > 0:
                    candidates.append(locator.first)
            except Exception:
                continue

        for locator in candidates:
            targets = [locator]
            try:
                clickable = locator.locator(
                    "xpath=ancestor-or-self::*[self::button or @role='button' or contains(@class,'MuiButtonBase-root') or @onclick or @tabindex='0'][1]"
                ).first
                if clickable.count() > 0:
                    targets.insert(0, clickable)
            except Exception:
                pass
            try:
                row = locator.locator(
                    "xpath=ancestor-or-self::*[self::div or self::section][.//*[normalize-space()="
                    + _xpath_literal(label)
                    + "]][1]"
                ).first
                if row.count() > 0:
                    targets.append(row)
                    try:
                        chevron = row.locator(
                            "xpath=.//*[self::button or @role='button' or self::svg or self::span][last()]"
                        ).first
                        if chevron.count() > 0:
                            targets.append(chevron)
                    except Exception:
                        pass
            except Exception:
                pass

            for target in targets:
                try:
                    if target.count() == 0:
                        continue
                except Exception:
                    continue
                try:
                    target.scroll_into_view_if_needed(timeout=1000)
                except Exception:
                    pass
                click_attempts = (
                    lambda: target.click(timeout=2000),
                    lambda: target.click(timeout=2000, force=True),
                    lambda: target.evaluate("el => el && el.click && el.click()"),
                    lambda: target.press("Enter"),
                    lambda: target.press("Space"),
                )
                for attempt in click_attempts:
                    try:
                        attempt()
                    except Exception:
                        continue
                    try:
                        page.wait_for_timeout(350)
                    except Exception:
                        time.sleep(0.35)
                    settle_deadline = time.time() + 1.5
                    while time.time() < settle_deadline:
                        if _is_section_expanded(page, label, required_texts=required_texts, required_placeholders=required_placeholders):
                            return
                        try:
                            page.wait_for_timeout(150)
                        except Exception:
                            time.sleep(0.15)
    if not _is_section_expanded(page, label, required_texts=required_texts, required_placeholders=required_placeholders):
        raise RuntimeError(f"Section did not expand: {label}")

def _check_by_label(page, label, checked=True):
    exact_re = re.compile(r"^\\s*" + re.escape(label) + r"\\s*$", re.I)
    for scope in _interaction_scopes(page, label=label):
        strategies = (
            lambda: scope.get_by_label(label, exact=True).first,
            lambda: scope.get_by_role("radio", name=label, exact=True).first,
            lambda: scope.get_by_role("checkbox", name=label, exact=True).first,
            lambda: scope.get_by_text(label, exact=True).first,
            lambda: scope.locator("label").filter(has_text=exact_re).locator(
                "input[type='checkbox'], input[type='radio'], [role='checkbox'], [role='radio']"
            ).first,
        )
        for factory in strategies:
            try:
                locator = factory()
                if locator.count() == 0:
                    continue
                try:
                    locator.scroll_into_view_if_needed(timeout=1000)
                except Exception:
                    pass
                try:
                    if checked:
                        locator.check()
                    else:
                        locator.uncheck()
                    return
                except Exception:
                    locator.click()
                    return
            except Exception:
                continue
    raise RuntimeError(f"Unable to {'check' if checked else 'uncheck'} option: {label}")

def _find_frame_for_field(page, label=None, placeholder=None):
    for scope in _active_modal_scopes(page, label=label, placeholder=placeholder):
        return scope
    frames = getattr(page, "frames", []) or []
    for frame in frames:
        if label:
            try:
                locator = frame.get_by_label(label)
                if locator.count() > 0:
                    return frame
            except Exception:
                pass
            try:
                locator = frame.get_by_label(re.compile(r"^\\s*" + re.escape(label) + r"\\s*$", re.I))
                if locator.count() > 0:
                    return frame
            except Exception:
                pass
        if placeholder:
            try:
                locator = frame.get_by_placeholder(placeholder)
                if locator.count() > 0:
                    return frame
            except Exception:
                pass
    return None

def _safe_locator_text(locator):
    if locator is None:
        return None
    getters = (
        lambda: _safe_input_value(locator),
        lambda: locator.text_content(),
        lambda: locator.inner_text(),
        lambda: locator.evaluate("el => el ? (el.innerText || el.textContent || el.value) : null"),
    )
    for getter in getters:
        try:
            value = getter()
            if value is not None:
                return value
        except Exception:
            continue
    return None

def _normalize_visible_text(text):
    return re.sub(r"\s+", " ", str(text or "")).strip()

def _text_visibility_candidates(page, text):
    label = _normalize_visible_text(text)
    if not label:
        return []
    exact_re = re.compile(r"^\s*" + re.escape(label) + r"\s*$", re.I)
    partial_re = re.compile(re.escape(label), re.I)
    candidates = []
    scopes = _interaction_scopes(page, label=label)
    seen = set()

    def _add(locator):
        if locator is None:
            return
        key = repr(locator)
        if key in seen:
            return
        seen.add(key)
        candidates.append(locator)

    for scope in scopes:
        try:
            _add(scope.get_by_text(label, exact=True).first)
        except Exception:
            pass
        try:
            _add(scope.get_by_text(exact_re).first)
        except Exception:
            pass
        try:
            _add(scope.get_by_text(partial_re).first)
        except Exception:
            pass
        for role in ("heading", "button", "link", "tab", "cell", "row", "option", "menuitem", "listitem", "status", "alert"):
            try:
                _add(scope.get_by_role(role, name=exact_re).first)
            except Exception:
                pass
            try:
                _add(scope.get_by_role(role, name=partial_re).first)
            except Exception:
                pass
        try:
            _add(
                scope.locator(
                    "xpath=(//*[contains(translate(normalize-space(.), "
                    "'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), "
                    + _xpath_literal(label.lower())
                    + ")])[1]"
                ).first
            )
        except Exception:
            pass
    return candidates

def verify_text_visible(page, text, timeout: int = 6000):
    label = _normalize_visible_text(text)
    if not label:
        raise AssertionError("Text to verify cannot be empty")
    deadline = time.time() + max(int(timeout), 250) / 1000.0
    last_error = None
    while time.time() < deadline:
        for locator in _text_visibility_candidates(page, label):
            try:
                if locator.count() > 0 and locator.first.is_visible(timeout=250):
                    return
            except Exception as exc:
                last_error = exc
                continue
        try:
            page.wait_for_timeout(200)
        except Exception:
            time.sleep(0.2)
    try:
        expect(page.get_by_text(re.compile(re.escape(label), re.I)).first).to_be_visible(timeout=500)
        return
    except Exception as exc:
        last_error = exc
    raise AssertionError(f"Expected visible text not found: {label}") from last_error

def _dismiss_open_dropdowns(page):
    try:
        listbox = page.get_by_role("listbox").first
        if listbox.count() > 0 and listbox.is_visible(timeout=500):
            try:
                page.keyboard.press("Escape")
            except Exception:
                pass
    except Exception:
        pass

def _wait_for_captcha(page, label=None, placeholder=None, timeout_ms=None):
    try:
        timeout_ms = int(timeout_ms) if timeout_ms is not None else int(os.getenv("SMARTAI_CAPTCHA_TIMEOUT_MS", "60000"))
    except Exception:
        timeout_ms = 300000
    try:
        poll_ms = int(os.getenv("SMARTAI_CAPTCHA_POLL_MS", "500"))
    except Exception:
        poll_ms = 500
    target_page = _find_frame_for_field(page, label=label, placeholder=placeholder) or page
    exact_re = None
    if label:
        try:
            exact_re = re.compile(r"^\\s*" + re.escape(label) + r"\\s*$", re.I)
        except Exception:
            exact_re = None
    locators = []
    if label:
        try:
            locators.append(target_page.get_by_label(label, exact=True).first)
        except Exception:
            pass
        if exact_re is not None:
            try:
                locators.append(target_page.get_by_label(exact_re).first)
            except Exception:
                pass
        try:
            locators.append(target_page.get_by_role("textbox", name=label, exact=True).first)
        except Exception:
            pass
        if exact_re is not None:
            try:
                locators.append(target_page.get_by_role("textbox", name=exact_re).first)
            except Exception:
                pass
    if placeholder:
        try:
            locators.append(target_page.get_by_placeholder(placeholder).first)
        except Exception:
            pass
    try:
        locators.append(
            target_page.locator(
                "input[name*='captcha' i], input[id*='captcha' i],"
                " input[placeholder*='captcha' i], input[class*='captcha' i]"
            ).first
        )
    except Exception:
        pass
    locator = None
    for candidate in locators:
        try:
            if not candidate or candidate.count() == 0:
                continue
        except Exception:
            continue
        try:
            editable = candidate.locator(_EDITABLE_SELECTOR).first
            if editable.count() > 0:
                locator = editable
                break
        except Exception:
            pass
        try:
            is_editable = candidate.evaluate(
                "el => !!(el && ((el.tagName && (el.tagName.toLowerCase()==='input' || el.tagName.toLowerCase()==='textarea')) || el.isContentEditable || (el.getAttribute && el.getAttribute('role')==='textbox')))"
            )
        except Exception:
            is_editable = False
        if is_editable:
            locator = candidate
            break
    if locator is None:
        try:
            locator = target_page.locator(
                "input[name*='captcha' i], input[id*='captcha' i],"
                " input[placeholder*='captcha' i], input[class*='captcha' i]"
            ).first
            locator.wait_for(timeout=timeout_ms)
        except Exception:
            pass
    if locator is None:
        raise RuntimeError("Captcha input not found")
    try:
        locator.scroll_into_view_if_needed(timeout=1000)
    except Exception:
        pass
    try:
        expect(locator).to_have_value(re.compile(r".+"), timeout=timeout_ms)
        return
    except Exception:
        pass
    start = time.time()
    while (time.time() - start) * 1000 < timeout_ms:
        try:
            current = _safe_input_value(locator)
            if current is not None and str(current).strip():
                return
        except Exception:
            pass
        try:
            time.sleep(max(poll_ms, 100) / 1000.0)
        except Exception:
            pass
    raise RuntimeError("Captcha was not entered before timeout")

def _icon_aliases(token):
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
        "apps": ("app", "launcher", "menu", "grid", "waffle"),
        "app": ("apps", "launcher", "menu", "grid", "waffle"),
        "launcher": ("app", "apps", "menu", "grid", "waffle"),
        "waffle": ("grid", "launcher", "app", "apps", "menu"),
        "grid": ("waffle", "launcher", "app", "apps", "menu"),
        "menu": ("launcher", "app", "apps", "grid", "waffle"),
        "dots": ("grid", "launcher", "menu", "waffle"),
    }
    out = []
    base = (token or "").strip().lower()
    if not base:
        return out
    out.append(base)
    if base.endswith("s") and len(base) > 4:
        singular = base[:-1]
        if singular not in out:
            out.append(singular)
    for alias in mapping.get(base, ()):
        if alias not in out:
            out.append(alias)
    return out

def _icon_tokens(label, intent=None, hints=None):
    out = []
    noise = {"icon", "button", "action", "alt"}

    def _add(token):
        text = (token or "").strip().lower()
        if len(text) < 3 or text in noise:
            return
        for alias in _icon_aliases(text):
            if alias not in out:
                out.append(alias)

    for raw in [label, intent] + list(hints or []):
        if not raw:
            continue
        base = str(raw).strip()
        cleaned = re.sub(r"\\b(icon|button|action)\\b", " ", base, flags=re.I).strip()
        for part in re.split(r"[_\\W]+", cleaned):
            _add(part)
        lowered = base.lower()
        if "profile" in lowered or "avatar" in lowered:
            for extra in ("profile", "avatar", "user", "account"):
                _add(extra)
    return out

def _click_icon_target(locator):
    try:
        target = locator.first
    except Exception:
        target = locator
    try:
        anc = target.locator(
            "xpath=ancestor-or-self::*[self::button or self::a or @role='button' or @onclick][1]"
        )
        if anc.count() > 0:
            target = anc.first
    except Exception:
        pass
    try:
        target.scroll_into_view_if_needed(timeout=1000)
    except Exception:
        pass
    target.click()
    return True

def _looks_like_grid_launcher(page, locator):
    try:
        target = locator.first
    except Exception:
        target = locator
    try:
        if not target.is_visible(timeout=200):
            return False
    except Exception:
        return False
    try:
        box = target.bounding_box()
    except Exception:
        box = None
    if not box:
        return False
    try:
        viewport = page.viewport_size or {}
    except Exception:
        viewport = {}
    viewport_width = float(viewport.get("width") or 1280)
    viewport_height = float(viewport.get("height") or 720)
    x = float(box.get("x", 0) or 0)
    y = float(box.get("y", 0) or 0)
    w = float(box.get("width", 0) or 0)
    h = float(box.get("height", 0) or 0)
    if x > viewport_width * 0.35 or y > max(180.0, viewport_height * 0.35):
        return False
    if w < 16 or h < 16 or w > 90 or h > 90:
        return False
    details = []
    try:
        details.append(target.inner_text() or "")
    except Exception:
        pass
    for attr in ("aria-label", "title", "alt", "id", "class", "data-testid", "data-test"):
        try:
            details.append(target.get_attribute(attr) or "")
        except Exception:
            pass
    haystack = " | ".join(part for part in details if part).lower()
    launcher_markers = ("app", "apps", "launcher", "grid", "waffle", "menu", "dot", "tile", "module")
    if any(marker in haystack for marker in launcher_markers):
        return True
    try:
        cell_count = target.locator(
            "xpath=.//*[self::svg or self::rect or self::circle or self::path or self::span or self::i]"
        ).count()
        if 4 <= cell_count <= 18:
            return True
    except Exception:
        pass
    return False

def _try_launcher_icon_candidate(page):
    selector = (
        "[aria-label*='app' i], [title*='app' i], [data-testid*='app' i], [data-test*='app' i], "
        "[aria-label*='launcher' i], [title*='launcher' i], [data-testid*='launcher' i], "
        "[aria-label*='grid' i], [title*='grid' i], [data-testid*='grid' i], [data-test*='grid' i], "
        "[aria-label*='menu' i], [title*='menu' i], [data-testid*='menu' i], [data-test*='menu' i], "
        "[class*='app' i], [class*='launcher' i], [class*='grid' i], [class*='menu' i], "
        "button, a, [role='button'], [role='link'], svg, img, span, div"
    )
    try:
        candidates = page.locator(selector)
        best = None
        best_score = -1
        cap = min(candidates.count(), 80)
        for i in range(cap):
            locator = candidates.nth(i)
            if not _looks_like_grid_launcher(page, locator):
                continue
            try:
                box = locator.bounding_box() or {}
            except Exception:
                box = {}
            score = 0.0
            x = float(box.get("x", 0) or 0)
            y = float(box.get("y", 0) or 0)
            score += max(0.0, 220.0 - x)
            score += max(0.0, 180.0 - y)
            try:
                target = locator.first
            except Exception:
                target = locator
            attrs = []
            for attr in ("aria-label", "title", "alt", "id", "class", "data-testid", "data-test"):
                try:
                    attrs.append(target.get_attribute(attr) or "")
                except Exception:
                    pass
            haystack = " | ".join(part for part in attrs if part).lower()
            if any(marker in haystack for marker in ("app", "apps", "launcher", "grid", "waffle", "menu")):
                score += 180
            try:
                anc = target.locator(
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
            _click_icon_target(best)
            return True
    except Exception:
        pass
    return False

def _click_icon(page, label, intent=None, hints=None):
    _dismiss_open_dropdowns(page)
    tokens = _icon_tokens(label, intent, hints=hints)
    if len(tokens) > 6:
        tokens = tokens[:6]
    if any(token in ("app", "apps", "launcher", "grid", "waffle", "menu", "dots") for token in tokens):
        if _try_launcher_icon_candidate(page):
            return True
    for token in tokens:
        safe = token.replace('"', '\\"')
        selectors = (
            f"button:has(svg[class*='{safe}' i])",
            f"[role='button']:has(svg[class*='{safe}' i])",
            f"a:has(svg[class*='{safe}' i])",
            f"button:has([data-lucide*='{safe}' i])",
            f"[role='button']:has([data-lucide*='{safe}' i])",
            f"a:has([data-lucide*='{safe}' i])",
            f"svg[class*='lucide-{safe}' i]",
            f"svg[class*='{safe}' i]",
            f"[data-lucide*='{safe}' i]",
            f"img[alt*='{safe}' i]",
            f"[aria-label*='{safe}' i]",
            f"[title*='{safe}' i]",
            f"[data-testid*='{safe}' i]",
            f"[data-test*='{safe}' i]",
        )
        for scope in _interaction_scopes(page, label=label):
            for selector in selectors:
                try:
                    locator = scope.locator(selector).first
                    if locator.count() > 0:
                        _click_icon_target(locator)
                        return True
                except Exception:
                    pass
            try:
                locator = scope.locator(
                    f"[aria-label*='{safe}' i], [title*='{safe}' i],"
                    f" [data-testid*='{safe}' i], [data-test*='{safe}' i],"
                    f" [class*='{safe}' i], img[alt*='{safe}' i],"
                    f" svg[aria-label*='{safe}' i], button[aria-label*='{safe}' i],"
                    f" a[aria-label*='{safe}' i]"
                ).first
                if locator.count() > 0:
                    _click_icon_target(locator)
                    return True
            except Exception:
                pass
            try:
                locator = scope.get_by_role("button", name=re.compile(re.escape(token), re.I)).first
                if locator.count() > 0:
                    _click_icon_target(locator)
                    return True
            except Exception:
                pass
            try:
                locator = scope.get_by_role("link", name=re.compile(re.escape(token), re.I)).first
                if locator.count() > 0:
                    _click_icon_target(locator)
                    return True
            except Exception:
                pass
            try:
                txt = scope.get_by_text(token)
                if txt.count() > 0:
                    anc = txt.first.locator(
                        "xpath=ancestor-or-self::*[self::button or self::a or @role='button' or @onclick][1]"
                    )
                    if anc.count() > 0:
                        _click_icon_target(anc.first)
                        return True
            except Exception:
                pass
    return False

def _try_profile_icon_candidate(page):
    selector = (
        "a.anchor, "
        "[aria-label*='profile' i], [title*='profile' i], img[alt*='profile' i], "
        "[aria-label*='avatar' i], [title*='avatar' i], img[alt*='avatar' i], "
        "[aria-label*='account' i], [title*='account' i], "
        "[class*='avatar' i], [class*='account' i], [class*='user' i], "
        "a, button, [role='button'], img, svg, span"
    )
    banned = (
        "my profile",
        "view full profile",
        "update details",
        "contact details",
        "save corrections",
        "cancel",
        "organogram",
    )
    try:
        viewport = page.viewport_size or {}
    except Exception:
        viewport = {}
    try:
        viewport_width = float(viewport.get("width") or 1280)
        viewport_height = float(viewport.get("height") or 720)
        candidates = page.locator(selector)
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
            for attr in ("aria-label", "title", "alt", "id", "class", "src"):
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
            if any(bad in haystack for bad in banned):
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
            if x >= viewport_width * 0.88:
                score += 120
            if y <= max(150.0, viewport_height * 0.25):
                score += 45
            if clickable:
                score += 35
            if "anchor" in haystack:
                score += 25
            if any(token in haystack for token in ("profile", "avatar", "account", "user")):
                score += 120
            if len(text) == 1 and text.isalpha():
                score += 180
            if abs(w - h) <= 10 and w >= 24 and h >= 24:
                score += 70
            if any(token in haystack for token in ("group", "organogram", "people", "users", "team")):
                score -= 220
            if "svg" in haystack and len(text) <= 1:
                score -= 80
            elif x >= viewport_width * 0.75 and y <= 100 and 2 <= len(text) <= 40:
                score += 45
            if score > best_score:
                best_score = score
                best = locator
        if best is not None and best_score >= 120:
            _click_icon_target(best)
            return True
    except Exception:
        pass
    return False

def _placeholder_variants(label, placeholder=None):
    values = []
    if placeholder:
        values.append(placeholder)
    base = (label or "").replace("*", "").strip()
    if base:
        values.append(base)
        values.append(f"Enter {base}")
        values.append(f"Enter {base.lower()}")
        values.append(f"Enter {base.title()}")
        words = [w for w in re.split(r"\\s+", base) if w]
        if words:
            values.append(f"Enter {words[0]}")
            values.append(f"Enter {words[0].lower()}")
            values.append(f"Enter {words[0].title()}")
        if " on " in base.lower():
            first_chunk = re.split(r"\\bon\\b", base, flags=re.I)[0].strip()
            if first_chunk:
                values.append(first_chunk)
                values.append(f"Enter {first_chunk}")
    seen = set()
    out = []
    for item in values:
        key = (item or "").strip()
        if not key:
            continue
        norm = key.lower()
        if norm in seen:
            continue
        seen.add(norm)
        out.append(key)
    return out

def _select_label_variants(label):
    values = []
    raw = str(label or "").strip()
    if raw:
        values.append(raw)
    base = re.sub(r"[\*\:]+$", "", raw).strip()
    if base:
        values.extend(
            [
                base,
                base.lower(),
                base.title(),
                f"Select {base}",
                f"Select {base.lower()}",
                f"Select {base.title()}",
            ]
        )
    seen = set()
    out = []
    for item in values:
        key = str(item or "").strip()
        if not key:
            continue
        norm = key.lower()
        if norm in seen:
            continue
        seen.add(norm)
        out.append(key)
    return out

def _select_option_candidates(value):
    raw = str(value or "").strip()
    if not raw:
        return []
    values = [raw]
    lowered = raw.lower()
    if lowered != raw:
        values.append(lowered)
    title_cased = raw.title()
    if title_cased.lower() != lowered:
        values.append(title_cased)
    seen = set()
    out = []
    for item in values:
        norm = item.strip().lower()
        if not norm or norm in seen:
            continue
        seen.add(norm)
        out.append(item)
    return out

def _select_option_on_locator(locator, value, timeout_ms=None):
    timeout = timeout_ms if timeout_ms is not None else _select_timeout_ms()
    raw_value = str(value or "").strip()
    if not raw_value:
        raise RuntimeError("Select value is required")

    attempts = []
    for candidate in _select_option_candidates(raw_value):
        attempts.extend(
            [
                ("label", candidate),
                ("value", candidate),
                ("plain", candidate),
            ]
        )

    targets = [locator]
    for selector in ("xpath=.//select[1]", "xpath=following::select[1]"):
        try:
            candidate = locator.locator(selector).first
            if candidate.count() > 0:
                targets.append(candidate)
        except Exception:
            continue

    for target in targets:
        for mode, candidate in attempts:
            try:
                if mode == "label":
                    target.select_option(label=candidate, timeout=timeout)
                elif mode == "value":
                    target.select_option(value=candidate, timeout=timeout)
                else:
                    target.select_option(candidate, timeout=timeout)
                return
            except Exception:
                continue
    raise RuntimeError(f"Unable to select {raw_value!r}")

_EDITABLE_SELECTOR = "input:not([type='hidden']), textarea, [contenteditable='true'], [role='textbox']"

def _editable_locator(locator):
    if locator is None:
        return locator
    candidates = []
    try:
        candidates.append(locator.locator(_EDITABLE_SELECTOR).first)
    except Exception:
        pass
    candidates.append(locator)
    for candidate in candidates:
        try:
            if candidate.count() > 0:
                return candidate
        except Exception:
            continue
    return locator

def _fill_locator(locator, value):
    text = str(value)
    target = _editable_locator(locator)
    attempts = [target]
    if target is not locator:
        attempts.append(locator)
    for candidate in attempts:
        try:
            try:
                wait_ms = int(os.getenv("SMARTAI_LOCATOR_WAIT_MS", "3000"))
            except Exception:
                wait_ms = 3000
            try:
                candidate.first.wait_for(state="attached", timeout=wait_ms)
            except Exception:
                pass
            if candidate.count() == 0:
                continue
            try:
                candidate.scroll_into_view_if_needed(timeout=1000)
            except Exception:
                pass
            try:
                candidate.click()
            except Exception:
                pass
            try:
                candidate.clear()
            except Exception:
                try:
                    candidate.press("Control+A")
                    candidate.press("Delete")
                except Exception:
                    pass
            try:
                candidate.fill(text)
                return
            except Exception:
                pass
            try:
                candidate.press_sequentially(text)
                return
            except Exception:
                pass
            try:
                candidate.evaluate(
                    '(el, val) => {'
                    'if (!el) { throw new Error("Missing element"); }'
                    'if ("value" in el) {'
                    '  el.focus();'
                    '  el.value = val;'
                    '} else if (el.isContentEditable) {'
                    '  el.focus();'
                    '  el.textContent = val;'
                    '} else {'
                    '  throw new Error("Element is not editable");'
                    '}'
                    'el.dispatchEvent(new Event("input", { bubbles: true }));'
                    'el.dispatchEvent(new Event("change", { bubbles: true }));'
                    '}',
                    text,
                )
                return
            except Exception:
                pass
        except Exception:
            continue
    raise RuntimeError("Unable to type into located element")

def _find_password_locator(page, label="Password", placeholder=None):
    target_page = _find_frame_for_field(page, label=label, placeholder=placeholder) or page
    search_pages = [target_page]
    if target_page is not page:
        search_pages.append(page)
    password_re = re.compile(r"^\\s*" + re.escape(label) + r"\\s*$", re.I)
    password_like_re = re.compile(r"password|passwd|pwd", re.I)
    label_tokens = [
        token
        for token in re.split(r"[^a-z0-9]+", str(label or "").lower())
        if token and token not in {"password", "passwd", "pwd", "field"}
    ]
    for scoped_page in search_pages:
        precise_candidates = []
        try:
            precise_candidates.append(scoped_page.get_by_label(label, exact=True).first)
        except Exception:
            pass
        try:
            precise_candidates.append(scoped_page.get_by_label(password_re).first)
        except Exception:
            pass
        if placeholder:
            try:
                precise_candidates.append(scoped_page.get_by_placeholder(placeholder).first)
            except Exception:
                pass
        try:
            text_locator = scoped_page.get_by_text(label, exact=True).first
            precise_candidates.append(
                text_locator.locator(
                    "xpath=following::*[self::input or self::textarea or @contenteditable='true' or @role='textbox'][1]"
                ).first
            )
        except Exception:
            pass
        try:
            precise_candidates.append(
                scoped_page.locator("label").filter(has_text=password_re).locator(
                    "xpath=following::*[self::input or self::textarea or @contenteditable='true' or @role='textbox'][1]"
                ).first
            )
        except Exception:
            pass
        try:
            precise_candidates.append(
                scoped_page.locator("label").filter(has_text=password_re).locator(
                    "xpath=preceding::*[self::input or self::textarea or @contenteditable='true' or @role='textbox'][1]"
                ).first
            )
        except Exception:
            pass
        for candidate in precise_candidates:
            try:
                target = _editable_locator(candidate)
                if target.count() == 0:
                    continue
                try:
                    input_type = target.first.get_attribute("type") or ""
                except Exception:
                    input_type = ""
                if input_type.lower() == "password":
                    return target
                for attr in ("name", "id", "placeholder", "aria-label", "autocomplete"):
                    try:
                        attr_value = target.first.get_attribute(attr) or ""
                    except Exception:
                        attr_value = ""
                    if attr_value and password_like_re.search(attr_value):
                        return target
            except Exception:
                continue
        generic_candidates = []
        for selector in (
            "input[autocomplete='current-password']",
            "input[autocomplete='new-password']",
            "input[type='password']",
            "input[name*='password' i]",
            "input[id*='password' i]",
            "input[placeholder*='password' i]",
            "input[aria-label*='password' i]",
        ):
            try:
                generic_candidates.append(scoped_page.locator(selector))
            except Exception:
                pass
        for locator_list in generic_candidates:
            try:
                count = min(locator_list.count(), 10)
            except Exception:
                count = 0
            for idx in range(count):
                try:
                    target = _editable_locator(locator_list.nth(idx))
                    if target.count() == 0:
                        continue
                except Exception:
                    continue
                try:
                    haystack = target.first.evaluate(
                        '''el => {
                            const labelText = (el.labels && el.labels.length ? Array.from(el.labels).map(l => l.innerText || l.textContent || "").join(" | ") : "");
                            const attrs = [
                                labelText,
                                el.getAttribute("name") || "",
                                el.getAttribute("id") || "",
                                el.getAttribute("placeholder") || "",
                                el.getAttribute("aria-label") || "",
                                el.getAttribute("autocomplete") || "",
                                el.getAttribute("class") || "",
                            ];
                            return attrs.filter(Boolean).join(" | ").toLowerCase();
                        }'''
                    ) or ""
                except Exception:
                    haystack = ""
                if label_tokens and not any(token in haystack for token in label_tokens):
                    continue
                try:
                    input_type = target.first.get_attribute("type") or ""
                except Exception:
                    input_type = ""
                if input_type.lower() == "password":
                    return target
                if haystack and password_like_re.search(haystack):
                    return target
    return None

def _xpath_literal(text):
    value = str(text or "")
    if "'" not in value:
        return "'" + value + "'"
    if '"' not in value:
        return '"' + value + '"'
    parts = value.split("'")
    items = []
    for index, part in enumerate(parts):
        items.append("'" + part + "'")
        if index != len(parts) - 1:
            items.append('"\\'"')
    return "concat(" + ", ".join(items) + ")"

def _select_timeout_ms():
    try:
        return int(os.getenv("SMARTAI_SELECT_TIMEOUT_MS", "2000"))
    except Exception:
        return 2000

def _select_fast_mode():
    return os.getenv("SMARTAI_SELECT_FAST", "").strip().lower() in ("1", "true", "yes", "y", "on")

def _select_by_label(page, label, value):
    label_text = str(label or "").strip()
    label_variants = _select_label_variants(label_text)
    primary_label = label_variants[0] if label_variants else label_text
    target_page = _find_frame_for_field(page, label=primary_label) or page
    exact_label_re = re.compile(r"^\\s*" + re.escape(primary_label) + r"\\s*\\*?\\s*$", re.I)
    option_re = re.compile(r"^\\s*" + re.escape(str(value)) + r"\\s*$", re.I)
    x_label = _xpath_literal(primary_label)
    opened_dropdown = False
    timeout_ms = _select_timeout_ms()
    fast_mode = _select_fast_mode()
    primary_placeholder = next(
        (variant for variant in label_variants if variant.lower().startswith("select ")),
        f"Select {primary_label.lower()}".strip(),
    )
    direct_targets = []
    scopes = []
    seen_scopes = set()
    for scope in _interaction_scopes(page, label=primary_label, placeholder=primary_placeholder) + [target_page]:
        key = repr(scope)
        if key in seen_scopes:
            continue
        seen_scopes.add(key)
        scopes.append(scope)

    for scope in scopes:
        for variant in label_variants:
            variant_re = re.compile(r"^\\s*" + re.escape(variant) + r"\\s*\\*?\\s*$", re.I)
            try:
                direct_targets.append(scope.get_by_label(variant, exact=True).first)
            except Exception:
                pass
            try:
                direct_targets.append(scope.get_by_label(variant_re).first)
            except Exception:
                pass
            try:
                direct_targets.append(scope.get_by_role("combobox", name=variant, exact=True).first)
            except Exception:
                pass
            try:
                direct_targets.append(scope.get_by_role("combobox", name=variant_re).first)
            except Exception:
                pass
            try:
                direct_targets.append(scope.get_by_role("button", name=variant, exact=True).first)
            except Exception:
                pass
            try:
                direct_targets.append(scope.get_by_role("button", name=variant_re).first)
            except Exception:
                pass
        if not fast_mode:
            for ph in _placeholder_variants(primary_label, primary_placeholder):
                try:
                    direct_targets.append(scope.get_by_placeholder(ph).first)
                except Exception:
                    pass
                try:
                    direct_targets.append(scope.get_by_role("combobox", name=ph, exact=True).first)
                except Exception:
                    pass
                try:
                    direct_targets.append(scope.get_by_role("button", name=ph, exact=True).first)
                except Exception:
                    pass
            try:
                direct_targets.append(
                    scope.locator(
                        "xpath=//*[normalize-space()=" + x_label + " or normalize-space()=" + _xpath_literal(primary_label + ' *') + "]"
                        "/following::*[self::select or self::button or @role='combobox' or @role='button' or @aria-haspopup='listbox' or @aria-haspopup='menu'][1]"
                    ).first
                )
            except Exception:
                pass
            try:
                direct_targets.append(
                    scope.locator(
                        "xpath=//*[contains(translate(normalize-space(.),"
                        "'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),"
                        + _xpath_literal(primary_label.lower()) + ")]"
                        "/following::*[self::select or self::button or @role='combobox' or @role='button' or @aria-haspopup='listbox' or @aria-haspopup='menu'][1]"
                    ).first
                )
            except Exception:
                pass

    for locator in direct_targets:
        try:
            if locator.count() == 0:
                continue
            current_value = _safe_locator_text(locator)
            if _values_match(current_value, str(value)):
                _dismiss_open_dropdowns(page)
                return
            try:
                locator.scroll_into_view_if_needed(timeout=min(1000, timeout_ms))
            except Exception:
                pass
            try:
                _select_option_on_locator(locator, value, timeout_ms=timeout_ms)
                _dismiss_open_dropdowns(page)
                return
            except Exception:
                pass
            if opened_dropdown:
                continue
            try:
                locator.click(timeout=timeout_ms)
                opened_dropdown = True
            except Exception:
                pass
        except Exception:
            continue

    if fast_mode:
        option_strategies = (
            lambda: target_page.get_by_role("option", name=str(value), exact=True).first,
            lambda: target_page.get_by_role("option", name=option_re).first,
            lambda: target_page.get_by_role("menuitem", name=str(value), exact=True).first,
            lambda: target_page.get_by_role("listitem", name=str(value), exact=True).first,
        )
    else:
        option_strategies = (
            lambda: target_page.get_by_role("option", name=str(value), exact=True).first,
            lambda: target_page.get_by_role("option", name=option_re).first,
            lambda: target_page.get_by_role("menuitem", name=str(value), exact=True).first,
            lambda: target_page.get_by_role("menuitem", name=option_re).first,
            lambda: target_page.get_by_role("listitem", name=str(value), exact=True).first,
            lambda: target_page.get_by_role("listitem", name=option_re).first,
            lambda: target_page.get_by_role("button", name=str(value), exact=True).first,
            lambda: target_page.get_by_role("radio", name=str(value), exact=True).first,
            lambda: target_page.get_by_role("checkbox", name=str(value), exact=True).first,
            lambda: target_page.get_by_label(str(value), exact=True).first,
            lambda: target_page.get_by_text(str(value), exact=True).first,
            lambda: target_page.get_by_text(option_re).first,
            lambda: target_page.locator(
                "xpath=(//*[normalize-space()=" + x_label + "]"
                "/following::*[normalize-space()=" + _xpath_literal(str(value)) + "])[1]"
            ).first,
        )
    for factory in option_strategies:
        try:
            locator = factory()
            if locator.count() == 0:
                continue
            try:
                locator.scroll_into_view_if_needed(timeout=min(1000, timeout_ms))
            except Exception:
                pass
            try:
                locator.check(timeout=timeout_ms)
                _dismiss_open_dropdowns(page)
                return
            except Exception:
                pass
            locator.click(timeout=timeout_ms)
            _dismiss_open_dropdowns(page)
            return
        except Exception:
            continue
    raise RuntimeError(f"Unable to select {value!r} for {label!r}")

def _click_by_label(page, label):
    exact_re = re.compile(r"^\\s*" + re.escape(label) + r"\\s*$", re.I)
    _dismiss_open_dropdowns(page)
    for scope in _interaction_scopes(page, label=label):
        strategies = (
            lambda: scope.get_by_role("button", name=label, exact=True).first,
            lambda: scope.locator("button").filter(has_text=exact_re).first,
            lambda: scope.get_by_role("link", name=label, exact=True).first,
            lambda: scope.get_by_text(label, exact=True).first,
            lambda: scope.get_by_text(exact_re).first,
            lambda: scope.locator("text=/^\\\\s*" + re.escape(label) + "\\\\s*$/i").first,
        )
        for factory in strategies:
            try:
                locator = factory()
                if locator.count() == 0:
                    continue
                try:
                    locator.scroll_into_view_if_needed(timeout=1000)
                except Exception:
                    pass
                locator.click()
                return
            except Exception:
                continue
    try:
        if _click_icon(page, label, intent=label, hints=[label]):
            return
    except Exception:
        pass
    try:
        if _is_day_number_label(label) and _calendar_surface_scope(page) is not None:
            select_calendar_date(page, label)
            return
    except Exception:
        pass
    raise RuntimeError(f"Unable to click action: {label}")

def _right_click_by_label(page, label):
    exact_re = re.compile(r"^\\s*" + re.escape(label) + r"\\s*$", re.I)
    _dismiss_open_dropdowns(page)
    strategies = (
        lambda: page.get_by_role("button", name=label, exact=True).first,
        lambda: page.locator("button").filter(has_text=exact_re).first,
        lambda: page.get_by_role("link", name=label, exact=True).first,
        lambda: page.get_by_text(label, exact=True).first,
        lambda: page.get_by_text(exact_re).first,
        lambda: page.locator("text=/^\\\\s*" + re.escape(label) + "\\\\s*$/i").first,
    )
    for factory in strategies:
        try:
            locator = factory()
            if locator.count() == 0:
                continue
            try:
                locator.scroll_into_view_if_needed(timeout=1000)
            except Exception:
                pass
            locator.click(button="right")
            return
        except Exception:
            continue
    raise RuntimeError(f"Unable to right-click action: {label}")

def _dblclick_by_label(page, label):
    exact_re = re.compile(r"^\\s*" + re.escape(label) + r"\\s*$", re.I)
    _dismiss_open_dropdowns(page)
    strategies = (
        lambda: page.get_by_role("button", name=label, exact=True).first,
        lambda: page.locator("button").filter(has_text=exact_re).first,
        lambda: page.get_by_role("link", name=label, exact=True).first,
        lambda: page.get_by_text(label, exact=True).first,
        lambda: page.get_by_text(exact_re).first,
        lambda: page.locator("text=/^\\\\s*" + re.escape(label) + "\\\\s*$/i").first,
    )
    for factory in strategies:
        try:
            locator = factory()
            if locator.count() == 0:
                continue
            try:
                locator.scroll_into_view_if_needed(timeout=1000)
            except Exception:
                pass
            locator.dblclick()
            return
        except Exception:
            continue
    raise RuntimeError(f"Unable to double-click action: {label}")

def _flex_text_pattern(label):
    parts = [p for p in re.split(r"\\s+", str(label or "").strip()) if p]
    if not parts:
        return re.compile(r"^\\s*$", re.I)
    pattern = r"^\\s*" + r"\\s+".join(re.escape(p) for p in parts) + r"\\s*$"
    return re.compile(pattern, re.I)

def _calendar_scope(page, container_unique=None):
    surface = _calendar_surface_scope(page, container_unique)
    if surface is not None:
        return surface
    if container_unique:
        try:
            return page.smartAI(container_unique)
        except Exception:
            pass
    try:
        modal_scopes = _active_modal_scopes(page)
    except Exception:
        modal_scopes = []
    if modal_scopes:
        return modal_scopes[0]
    return page

def _calendar_surface_scope(page, container_unique=None):
    if container_unique:
        try:
            target = page.smartAI(container_unique)
            if target.count() > 0:
                return target
        except Exception:
            pass
    try:
        modal_scopes = _active_modal_scopes(page)
    except Exception:
        modal_scopes = []
    calendar_markers = (
        "[role='grid']",
        "[role='gridcell']",
        "[aria-label*='calendar' i]",
        "[class*='calendar' i]",
        "[class*='datepicker' i]",
        "[class*='date-picker' i]",
    )
    for scope in list(modal_scopes) + [page]:
        try:
            for marker in calendar_markers:
                locator = scope.locator(marker)
                if locator.count() > 0:
                    return scope
        except Exception:
            continue
    return None

def _calendar_header_timeout_ms():
    try:
        return int(os.getenv("SMARTAI_CALENDAR_HEADER_TIMEOUT_MS", "6000"))
    except Exception:
        return 6000

def _try_click_calendar_month_header(page, month_year, container_unique=None):
    label = str(month_year or "").strip()
    if not label:
        return False
    _dismiss_open_dropdowns(page)
    timeout_ms = _calendar_header_timeout_ms()
    if container_unique:
        try:
            target = page.smartAI(container_unique)
            if target.count() > 0:
                try:
                    target.scroll_into_view_if_needed(timeout=min(1000, timeout_ms))
                except Exception:
                    pass
                target.click(timeout=timeout_ms)
                return True
        except Exception:
            pass
    scope = _calendar_scope(page, container_unique)
    exact_re = _flex_text_pattern(label)
    strategies = (
        lambda: scope.get_by_role("button", name=exact_re).first,
        lambda: scope.get_by_role("link", name=exact_re).first,
        lambda: scope.get_by_text(exact_re).first,
        lambda: scope.get_by_label(exact_re).first,
    )
    for factory in strategies:
        try:
            locator = factory()
            if locator.count() == 0:
                continue
            try:
                if not locator.is_visible(timeout=min(500, timeout_ms)):
                    continue
            except Exception:
                pass
            try:
                locator.scroll_into_view_if_needed(timeout=min(1000, timeout_ms))
            except Exception:
                pass
            try:
                anc = locator.locator(
                    "xpath=ancestor-or-self::*[self::button or self::a or "
                    "@role='button' or @onclick or @tabindex='0'][1]"
                )
                if anc.count() > 0:
                    anc.first.click(timeout=timeout_ms)
                    return True
            except Exception:
                pass
            locator.click(timeout=timeout_ms)
            return True
        except Exception:
            continue
    try:
        inputs = scope.locator("input")
        if inputs.count() > 0:
            normalized = re.sub(r"\\s+", " ", label).strip().lower()
            clicked = inputs.evaluate_all(
                "(els, target) => {"
                "const norm = s => (s || '').replace(/\\s+/g, ' ').trim().toLowerCase();"
                "for (const el of els) {"
                "const v = norm(el.value);"
                "const p = norm(el.getAttribute('placeholder'));"
                "const a = norm(el.getAttribute('aria-label'));"
                "if (v === target || p === target || a === target) { el.click(); return true; }"
                "}"
                "return false;"
                "}",
                normalized,
            )
            if clicked:
                return True
    except Exception:
        pass
    return False

def click_calendar_month_header(page, month_year, container_unique=None):
    label = str(month_year or "").strip()
    if not label:
        raise RuntimeError("Month/year label is required")
    if _try_click_calendar_month_header(page, label, container_unique=container_unique):
        return
    raise RuntimeError("Calendar month header not found: " + label)

def select_calendar_month(page, month_name, container_unique=None):
    label = str(month_name or "").strip()
    if not label:
        raise RuntimeError("Month name is required")
    _dismiss_open_dropdowns(page)
    if container_unique:
        try:
            target = page.smartAI(container_unique)
            if target.count() > 0:
                try:
                    target.scroll_into_view_if_needed(timeout=1000)
                except Exception:
                    pass
                target.click()
                _dismiss_open_dropdowns(page)
                return
        except Exception:
            pass
    scope = _calendar_scope(page, container_unique)
    exact_re = _flex_text_pattern(label)
    scopes = [scope]
    if scope is not page:
        scopes.append(page)
    for current_scope in scopes:
        strategies = (
            lambda: current_scope.get_by_role("option", name=exact_re).first,
            lambda: current_scope.get_by_role("button", name=exact_re).first,
            lambda: current_scope.get_by_text(exact_re).first,
        )
        for factory in strategies:
            try:
                locator = factory()
                if locator.count() == 0:
                    continue
                try:
                    locator.scroll_into_view_if_needed(timeout=1000)
                except Exception:
                    pass
                locator.click()
                _dismiss_open_dropdowns(page)
                return
            except Exception:
                continue
    raise RuntimeError("Calendar month not found: " + label)

def select_calendar_date(page, day, container_unique=None):
    label = str(day or "").strip()
    if not label:
        raise RuntimeError("Date value is required")
    _dismiss_open_dropdowns(page)
    if container_unique:
        try:
            target = page.smartAI(container_unique)
            if target.count() > 0:
                try:
                    target.scroll_into_view_if_needed(timeout=1000)
                except Exception:
                    pass
                target.click()
                _dismiss_open_dropdowns(page)
                return
        except Exception:
            pass
    scope = _calendar_scope(page, container_unique)
    exact_re = _flex_text_pattern(label)
    scopes = [scope]
    if scope is not page:
        scopes.append(page)
    for current_scope in scopes:
        strategies = (
            lambda: current_scope.get_by_role("gridcell", name=exact_re).first,
            lambda: current_scope.get_by_role("button", name=exact_re).first,
            lambda: current_scope.get_by_text(exact_re).first,
        )
        for factory in strategies:
            try:
                locator = factory()
                if locator.count() == 0:
                    continue
                try:
                    locator.scroll_into_view_if_needed(timeout=1000)
                except Exception:
                    pass
                locator.click()
                _dismiss_open_dropdowns(page)
                return
            except Exception:
                continue
    raise RuntimeError("Calendar date not found: " + label)

def select_calendar_date_offset(page, offset_days, container_unique=None):
    try:
        offset = int(offset_days)
    except Exception:
        offset = 0
    target = date.today() + timedelta(days=offset)
    # Best-effort month/year switch (silent; avoids extra report steps)
    _try_click_calendar_month_header(page, target.strftime("%b %Y"), container_unique=container_unique)
    # Try selecting the day; if month picker opened, select month then day
    try:
        select_calendar_date(page, str(target.day), container_unique=container_unique)
        return
    except Exception:
        try:
            select_calendar_month(page, target.strftime("%b"), container_unique=container_unique)
        except Exception:
            pass
        select_calendar_date(page, str(target.day), container_unique=container_unique)

def _enter_value(page, label, value, placeholder=None):
    locators = []
    target_page = _find_frame_for_field(page, label=label, placeholder=placeholder) or page
    exact_re = re.compile(r"^\\s*" + re.escape(label) + r"\\s*$", re.I)
    x_label = _xpath_literal(label)
    search_pages = [target_page]
    if target_page is not page:
        search_pages.append(page)
    for scoped_page in search_pages:
        try:
            locators.append(scoped_page.get_by_role("textbox", name=label, exact=True).first)
        except Exception:
            pass
        try:
            locators.append(scoped_page.get_by_role("textbox", name=exact_re).first)
        except Exception:
            pass
    try:
        locators.append(target_page.get_by_label(label, exact=True).first)
    except Exception:
        pass
    try:
        locators.append(target_page.get_by_label(exact_re).first)
    except Exception:
        pass
    try:
        locators.append(
            target_page.locator("label").filter(has_text=exact_re).locator(
                "xpath=preceding::*[self::input or self::textarea or @contenteditable='true' or @role='textbox'][1]"
            ).first
        )
    except Exception:
        pass
    try:
        locators.append(
            target_page.locator("label").filter(has_text=exact_re).locator(
                "xpath=following::*[self::input or self::textarea or @contenteditable='true' or @role='textbox'][1]"
            ).first
        )
    except Exception:
        pass
    for ph in _placeholder_variants(label, placeholder):
        try:
            scoped_page = _find_frame_for_field(page, placeholder=ph) or page
            locators.append(scoped_page.get_by_placeholder(ph).first)
        except Exception:
            pass
    try:
        locators.append(target_page.get_by_text(label, exact=True).first.locator(_EDITABLE_SELECTOR).first)
    except Exception:
        pass
    try:
        locators.append(
            target_page.get_by_text(label, exact=True).first.locator(
                "xpath=ancestor::*[self::div or self::section or self::article or self::td or self::th or self::li][1]"
            ).locator(_EDITABLE_SELECTOR).first
        )
    except Exception:
        pass
    try:
        locators.append(
            target_page.locator(
                "xpath=(//*[normalize-space()=" + x_label + "]/preceding::*[self::input or self::textarea or @contenteditable='true' or @role='textbox'][1])[1]"
            ).first
        )
    except Exception:
        pass
    try:
        locators.append(
            target_page.locator(
                "xpath=(//*[normalize-space()=" + x_label + "]/following::*[self::input or self::textarea or @contenteditable='true' or @role='textbox'][1])[1]"
            ).first
        )
    except Exception:
        pass
    for locator in locators:
        try:
            _fill_locator(locator, value)
            return
        except Exception:
            continue
    raise RuntimeError(f"Unable to enter value for: {label}")
"""

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
    from lib.ui_actions import dismiss_cookie_banner as _dismiss_cookie_banner
except Exception:
    def _dismiss_cookie_banner(_page):
        return False

try:
    _step_prefixes = ('enter_', 'click_', 'right_click_', 'dblclick_', 'select_', 'verify_', 'toggle_', 'hover_', 'upload_', 'check_', 'uncheck_', 'drag_', 'assert_')
    for _name, _obj in list(globals().items()):
        if callable(_obj) and any(_name.startswith(p) for p in _step_prefixes):
            def _make_wrapped(f, display_name=_name):
                def _wrapped(*a, **kw):
                    step_name = display_name
                    detail_msg = None
                    try:
                        def _first_param():
                            start_idx = 1 if len(a) and getattr(a[0], '__class__', None) and getattr(a[0].__class__, '__name__', '').lower().find('page') != -1 else 0
                            if len(a) > start_idx:
                                return a[start_idx]
                            return None
                        def _mask_if_sensitive(name, value):
                            if value is None:
                                return value
                            lowered = (name or "").lower()
                            if any(k in lowered for k in ("password", "passwd", "pwd", "captcha", "otp", "token", "secret", "pin")):
                                return "***"
                            return value
                        def _label_from_name(name):
                            for p in ("enter_", "select_", "click_", "right_click_", "dblclick_", "verify_", "assert_", "check_", "uncheck_", "upload_", "drag_", "hover_", "focus_", "press_", "toggle_"):
                                if name.startswith(p):
                                    name = name[len(p):]
                                    break
                            return name.replace("_", " ").strip()
                        if display_name.startswith("enter_"):
                            val = _mask_if_sensitive(display_name, _first_param())
                            label = _label_from_name(display_name)
                            if val is not None:
                                detail_msg = f"entered {val} in the {label} field"
                        elif display_name.startswith("select_"):
                            val = _first_param()
                            label = _label_from_name(display_name)
                            if val is not None:
                                detail_msg = f"selected {val} in {label}"
                        elif display_name.startswith("click_"):
                            label = _label_from_name(display_name)
                            detail_msg = f"clicked {label}"
                        elif display_name.startswith("right_click_"):
                            label = _label_from_name(display_name)
                            detail_msg = f"right clicked {label}"
                        elif display_name.startswith("dblclick_"):
                            label = _label_from_name(display_name)
                            detail_msg = f"double clicked {label}"
                        elif display_name.startswith(("verify_", "assert_")):
                            val = _first_param()
                            if val is not None:
                                detail_msg = f"verified {val} is visible"
                    except Exception:
                        pass
                    try:
                        page_arg = None
                        if len(a) and getattr(a[0], '__class__', None) and getattr(a[0].__class__, '__name__', '').lower().find('page') != -1:
                            page_arg = a[0]
                        if page_arg is not None:
                            _dismiss_cookie_banner(page_arg)
                    except Exception:
                        pass
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
                    with allure.step(step_name):
                        try:
                            attach = getattr(allure, 'attach', None)
                            atype = getattr(allure, 'attachment_type', None)
                            if attach and detail_msg:
                                if atype is not None and hasattr(atype, 'TEXT'):
                                    attach(detail_msg, name="details", attachment_type=atype.TEXT)
                                else:
                                    attach(detail_msg, name="details")
                        except Exception:
                            pass
                        return f(*a, **kw)
                return _wrapped
            globals()[_name] = _make_wrapped(_obj)
except Exception:
    pass
# ---- end wrapper ----
'''


def _assert_method_for_input(unique: str, method_name: str, *, password_label: str | None = None, password_placeholder: str | None = None) -> str:
    if password_label:
        return (
            f"def assert_{method_name}(page, expected: str, timeout: int = 6000):\n"
            f"    locator = _find_password_locator(page, {password_label!r}, placeholder={password_placeholder!r})\n"
            f"    if locator is None:\n"
            f"        locator = page.smartAI('{unique}')\n"
            f"    target = _editable_locator(locator)\n"
            f"    try:\n"
            f"        expect(target).to_have_value(str(expected), timeout=timeout)\n"
            f"    except Exception as e:\n"
            f"        actual = _safe_input_value(target)\n"
            f"        if not _values_match(actual, str(expected)):\n"
            f"            raise AssertionError(f\"Assertion failed for '{unique}' expecting '{{str(expected)}}' but got '{{actual}}': {{e}}\")\n"
        )
    return (
        f"def assert_{method_name}(page, expected: str, timeout: int = 6000):\n"
        f"    locator = page.smartAI('{unique}')\n"
        f"    target = _editable_locator(locator)\n"
        f"    try:\n"
        f"        expect(target).to_have_value(str(expected), timeout=timeout)\n"
        f"    except Exception as e:\n"
        f"        actual = _safe_input_value(target)\n"
        f"        if not _values_match(actual, str(expected)):\n"
        f"            raise AssertionError(f\"Assertion failed for '{unique}' expecting '{{str(expected)}}' but got '{{actual}}': {{e}}\")\n"
    )


def _assert_method_visible(unique: str, method_name: str, *, password_label: str | None = None, password_placeholder: str | None = None) -> str:
    if password_label:
        return (
            f"def assert_{method_name}_visible(page, timeout: int = 6000):\n"
            f"    locator = _find_password_locator(page, {password_label!r}, placeholder={password_placeholder!r})\n"
            f"    if locator is None:\n"
            f"        locator = page.smartAI('{unique}')\n"
            f"    expect(locator).to_be_visible(timeout=timeout)\n"
        )
    return (
        f"def assert_{method_name}_visible(page, timeout: int = 6000):\n"
        f"    expect(page.smartAI('{unique}')).to_be_visible(timeout=timeout)\n"
    )


def _assert_method_checked(unique: str, method_name: str) -> str:
    return (
        f"def assert_{method_name}_checked(page, timeout: int = 6000):\n"
        f"    expect(page.smartAI('{unique}')).to_be_checked(timeout=timeout)\n"
    )


def _assert_method_unchecked(unique: str, method_name: str) -> str:
    return (
        f"def assert_{method_name}_unchecked(page, timeout: int = 6000):\n"
        f"    expect(page.smartAI('{unique}')).not_to_be_checked(timeout=timeout)\n"
    )


def build_method(entry: dict[str, Any], used_names: dict[str, int]) -> str:
    action_type = _action_type(entry)
    is_icon_like = _is_icon_like_entry(entry)
    is_profile_icon = _is_profile_icon_entry(entry)
    prefer_icon_heuristics_first = _prefer_icon_heuristics_before_smartai(entry)
    is_captcha = _is_captcha_entry(entry)
    is_password = _is_password_entry(entry)
    label_source = (
        entry.get("canonical_label_text")
        or entry.get("field_context_label")
        or entry.get("label_text")
        or entry.get("intent")
        or entry.get("text")
        or "element"
    ).strip()
    if is_icon_like:
        label_source = _icon_context_label(entry) or _icon_display_label(entry) or label_source
    label_text = _clean_option_like_label(label_source)
    placeholder = (entry.get("placeholder") or "").strip()
    icon_hints = _icon_hint_values(entry)
    icon_intent = str(entry.get("intent") or "").strip()
    calendar_related_inputs = _calendar_related_input_candidates(entry)
    icon_field_anchors = _icon_field_anchor_candidates(entry)
    unique = entry.get("unique_name")

    if not unique:
        return ""

    def stem(default_name: str) -> str:
        return safe(label_text or default_name)

    code_blocks: list[str] = []

    if action_type == "input":
        fn_name = ensure_unique(f"enter_{stem('input')}", used_names)
        if is_captcha:
            method_lines = [
                f"def {fn_name}(page, value=None, timeout_ms: int | None = None):",
                f"    _wait_for_captcha(page, {label_text!r}, placeholder={placeholder!r}, timeout_ms=timeout_ms)",
            ]
        elif is_password:
            method_lines = [
                f"def {fn_name}(page, value):",
                f"    try:",
                f"        locator = _find_password_locator(page, {label_text!r}, placeholder={placeholder!r})",
                f"        if locator is not None:",
                f"            _fill_locator(locator, value)",
                f"            return",
                f"    except Exception:",
                f"        pass",
                f"    try:",
                f"        locator = page.smartAI('{unique}')",
                f"        _fill_locator(locator, value)",
                f"        return",
                f"    except Exception:",
                f"        pass",
                f"    try:",
                f"        _enter_value(page, {label_text!r}, value, placeholder={placeholder!r})",
                f"        return",
                f"    except Exception:",
                f"        pass",
                f"    raise RuntimeError(f\"Unable to enter value for: {label_text!r}\")",
            ]
        else:
            # Prefer smartAI locator first to avoid slow heuristic fallback.
            method_lines = [
                f"def {fn_name}(page, value):",
                f"    try:",
                f"        locator = page.smartAI('{unique}')",
                f"        _fill_locator(locator, value)",
                f"        return",
                f"    except Exception:",
                f"        pass",
                f"    try:",
                f"        _enter_value(page, {label_text!r}, value, placeholder={placeholder!r})",
                f"        return",
                f"    except Exception:",
                f"        pass",
                f"    raise RuntimeError(f\"Unable to enter value for: {label_text!r}\")",
            ]
        method_code = "\n".join(method_lines)
        code_blocks.extend(
            [
                method_code,
                _assert_method_for_input(
                    unique,
                    fn_name,
                    password_label=label_text if is_password else None,
                    password_placeholder=placeholder if is_password else None,
                ),
                _assert_method_visible(
                    unique,
                    fn_name,
                    password_label=label_text if is_password else None,
                    password_placeholder=placeholder if is_password else None,
                ),
            ]
        )

    elif action_type == "select":
        fn_name = ensure_unique(f"select_{stem('option')}", used_names)
        method_code = (
            f"def {fn_name}(page, value):\n"
            f"    try:\n"
            f"        _select_by_label(page, {label_text!r}, value)\n"
            f"        return\n"
            f"    except Exception:\n"
            f"        pass\n"
            f"    try:\n"
            f"        _select_option_on_locator(page.smartAI('{unique}'), value, timeout_ms=_select_timeout_ms())\n"
            f"        return\n"
            f"    except Exception:\n"
            f"        pass\n"
            f"    raise RuntimeError(f\"Unable to select {{value!r}} for: {label_text!r}\")"
        )
        code_blocks.extend(
            [
                method_code,
                _assert_method_visible(unique, fn_name),
            ]
        )

    elif action_type == "check":
        check_name = ensure_unique(f"check_{stem('option')}", used_names)
        uncheck_name = ensure_unique(f"uncheck_{stem('option')}", used_names)

        check_code = (
            f"def {check_name}(page):\n"
            f"    try:\n"
            f"        page.smartAI('{unique}').check()\n"
            f"        return\n"
            f"    except Exception:\n"
            f"        pass\n"
            f"    _check_by_label(page, {label_text!r}, checked=True)"
        )
        uncheck_code = (
            f"def {uncheck_name}(page):\n"
            f"    try:\n"
            f"        page.smartAI('{unique}').uncheck()\n"
            f"        return\n"
            f"    except Exception:\n"
            f"        pass\n"
            f"    _check_by_label(page, {label_text!r}, checked=False)"
        )

        code_blocks.extend(
            [
                check_code,
                uncheck_code,
                _assert_method_visible(unique, check_name),
                _assert_method_checked(unique, check_name),
                _assert_method_unchecked(unique, uncheck_name),
            ]
        )

    elif action_type == "upload":
        fn_name = ensure_unique(f"upload_{stem('file')}", used_names)
        method_code = (
            f"def {fn_name}(page, file_path):\n"
            f"    page.smartAI('{unique}').set_input_files(file_path)"
        )
        code_blocks.extend(
            [
                method_code,
                _assert_method_visible(unique, fn_name),
            ]
        )

    elif action_type == "drag":
        fn_name = ensure_unique(f"drag_{stem('item')}_to", used_names)
        method_code = (
            f"def {fn_name}(page, target):\n"
            f"    page.smartAI('{unique}').drag_to(target)"
        )
        code_blocks.extend(
            [
                method_code,
                _assert_method_visible(unique, fn_name),
            ]
        )

    elif action_type == "click":
        click_modes = _click_modes(entry)

        def _build_click_method(fn_name: str, click_kind: str, include_icon: bool) -> str:
            if click_kind == "right":
                role_click = "locator.click(timeout=2000, button=\"right\")"
                smartai_click = "locator.right_click(timeout=2000)"
                label_fallback = f"_right_click_by_label(page, {label_text!r})"
            elif click_kind == "double":
                role_click = "locator.dblclick(timeout=2000)"
                smartai_click = "locator.dblclick(timeout=2000)"
                label_fallback = f"_dblclick_by_label(page, {label_text!r})"
            else:
                role_click = "locator.click(timeout=2000)"
                smartai_click = "locator.click(timeout=2000)"
                label_fallback = f"_click_by_label(page, {label_text!r})"

            method_lines = [
                f"def {fn_name}(page):",
            ]
            if click_kind == "left" and str(label_text or "").strip().isdigit():
                method_lines.extend(
                    [
                        f"    try:",
                        f"        if _is_day_number_label({label_text!r}) and _calendar_surface_scope(page) is not None:",
                        f"            select_calendar_date(page, {label_text!r})",
                        f"            return",
                        f"    except Exception:",
                        f"        pass",
                    ]
                )
            if click_kind == "left" and is_icon_like and (calendar_related_inputs or icon_field_anchors):
                method_lines.extend(
                    [
                        f"    try:",
                        f"        candidates = []",
                    ]
                )
                for anchor_label in icon_field_anchors:
                    escaped_anchor = anchor_label.replace("\\", "\\\\").replace("'", "\\'")
                    method_lines.extend(
                        [
                            f"        try:",
                            f"            target_page = _find_frame_for_field(page, label={anchor_label!r}) or page",
                            f"            anchor = target_page.get_by_text(re.compile(r'^\\\\s*{escaped_anchor}\\\\s*\\\\*?\\\\s*$', re.I)).first",
                            f"            candidates.append(_editable_locator(anchor.locator(\"xpath=following::*[self::input or self::textarea or @contenteditable='true' or @role='textbox'][1]\").first))",
                            f"        except Exception:",
                            f"            pass",
                        ]
                    )
                for calendar_related_input in calendar_related_inputs:
                    method_lines.extend(
                        [
                            f"        try:",
                            f"            target_page = _find_frame_for_field(page, placeholder={calendar_related_input!r}) or page",
                            f"            candidates.append(_editable_locator(target_page.get_by_placeholder({calendar_related_input!r}).first))",
                            f"        except Exception:",
                            f"            pass",
                            f"        try:",
                            f"            target_page = _find_frame_for_field(page, placeholder={calendar_related_input!r}) or page",
                            f"            candidates.append(_editable_locator(target_page.get_by_label({calendar_related_input!r}, exact=True).first))",
                            f"        except Exception:",
                            f"            pass",
                        ]
                    )
                method_lines.extend(
                    [
                        f"        for locator in candidates:",
                        f"            try:",
                        f"                if locator.count() == 0:",
                        f"                    continue",
                        f"            except Exception:",
                        f"                continue",
                        f"            try:",
                        f"                locator.scroll_into_view_if_needed(timeout=1000)",
                        f"            except Exception:",
                        f"                pass",
                        f"            open_attempts = (",
                        f"                lambda: locator.click(timeout=2000),",
                        f"                lambda: locator.press(\"Enter\"),",
                        f"                lambda: locator.press(\"ArrowDown\"),",
                        f"            )",
                        f"            for attempt in open_attempts:",
                        f"                try:",
                        f"                    attempt()",
                        f"                except Exception:",
                        f"                    continue",
                        f"                try:",
                        f"                    page.wait_for_timeout(250)",
                        f"                except Exception:",
                        f"                    time.sleep(0.25)",
                        f"                if _calendar_surface_scope(page) is not None:",
                        f"                    return",
                        f"    except Exception:",
                        f"        pass",
                    ]
                )
            method_lines.extend(
                [
                    f"    try:",
                    f"        locator = page.get_by_role(\"button\", name={label_text!r}, exact=True).first",
                    f"        if locator.count() > 0:",
                    f"            try:",
                    f"                locator.scroll_into_view_if_needed(timeout=1000)",
                    f"            except Exception:",
                    f"                pass",
                    f"            {role_click}",
                    f"            return",
                ]
            )
            method_lines.extend(
                [
                    f"    except Exception:",
                    f"        pass",
                    f"    try:",
                    f"        locator = page.get_by_role(\"link\", name={label_text!r}, exact=True).first",
                    f"        if locator.count() > 0:",
                    f"            try:",
                    f"                locator.scroll_into_view_if_needed(timeout=1000)",
                    f"            except Exception:",
                    f"                pass",
                    f"            {role_click}",
                    f"            return",
                    f"    except Exception:",
                    f"        pass",
                ]
            )

            if not is_profile_icon and not prefer_icon_heuristics_first:
                method_lines.extend(
                    [
                        f"    try:",
                        f"        locator = page.smartAI('{unique}')",
                        f"        if locator.count() > 0:",
                        f"            try:",
                        f"                locator.scroll_into_view_if_needed(timeout=1000)",
                        f"            except Exception:",
                        f"                pass",
                        f"            {smartai_click}",
                        f"            return",
                        f"    except Exception:",
                        f"        pass",
                    ]
                )

            if include_icon:
                if is_profile_icon:
                    method_lines.extend(
                        [
                            f"    try:",
                            f"        if _try_profile_icon_candidate(page):",
                            f"            return",
                            f"    except Exception:",
                            f"        pass",
                        ]
                    )
                if is_icon_like:
                    contextual_icon_label = _icon_context_label(entry) or label_text
                    click_icon_label = "profile avatar" if is_profile_icon else contextual_icon_label
                    click_icon_hints = (
                        ["profile avatar", "account avatar", "user avatar", "profile icon", "My Profile", "profile_icon_action"]
                        if is_profile_icon
                        else list(dict.fromkeys([contextual_icon_label, *icon_hints]))
                    )
                    method_lines.extend(
                        [
                            f"    try:",
                            f"        if _click_icon(page, {click_icon_label!r}, intent={icon_intent!r}, hints={click_icon_hints!r}):",
                            f"            return",
                            f"    except Exception:",
                            f"        pass",
                        ]
                    )

            if not is_profile_icon and prefer_icon_heuristics_first:
                method_lines.extend(
                    [
                        f"    try:",
                        f"        locator = page.smartAI('{unique}')",
                        f"        if locator.count() > 0:",
                        f"            try:",
                        f"                locator.scroll_into_view_if_needed(timeout=1000)",
                        f"            except Exception:",
                        f"                pass",
                        f"            {smartai_click}",
                        f"            return",
                        f"    except Exception:",
                        f"        pass",
                    ]
                )

            if is_profile_icon and click_kind == "left":
                label_fallback = "_click_by_label(page, 'profile avatar')"
            method_lines.append(f"    {label_fallback}")
            return "\n".join(method_lines)

        if "right" in click_modes and "double" not in click_modes:
            base_kind = "right"
        elif "double" in click_modes and "right" not in click_modes:
            base_kind = "double"
        else:
            base_kind = "left"

        base_name = ensure_unique(f"click_{stem('button')}", used_names)
        code_blocks.extend(
            [
                _build_click_method(base_name, base_kind, include_icon=True),
                _assert_method_visible(unique, base_name),
            ]
        )

        if "right" in click_modes:
            right_name = ensure_unique(f"right_click_{stem('button')}", used_names)
            code_blocks.extend(
                [
                    _build_click_method(right_name, "right", include_icon=False),
                    _assert_method_visible(unique, right_name),
                ]
            )

        if "double" in click_modes:
            dbl_name = ensure_unique(f"dblclick_{stem('button')}", used_names)
            code_blocks.extend(
                [
                    _build_click_method(dbl_name, "double", include_icon=False),
                    _assert_method_visible(unique, dbl_name),
                ]
            )

    else:
        fn_name = ensure_unique(f"verify_{stem('element')}_visible", used_names)
        method_code = (
            f"def {fn_name}(page):\n"
            f"    expect(page.smartAI('{unique}')).to_be_visible()"
        )
        code_blocks.append(method_code)

    return "\n\n".join(code_blocks)


@router.post("/{project_id}/rag/generate-page-methods")
def generate_page_methods(
    project_id: int,
    pages: str | None = Query(None, description="Comma-separated page names to regenerate"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = get_user_project(db, project_id, current_user)
    project_paths = _ensure_project_structure(project)
    project_src_dir = project_paths["src_dir"]

    run_folder = Path(project_src_dir)
    pages_dir = run_folder / "pages"
    meta_dir = run_folder / "metadata"
    project_chroma_path = project_paths["chroma_path"]

    storage = DatabaseBackedProjectStorage(project, run_folder, db)
    with _temporary_project_env(project_paths, project.id):
        ensure_smart_ai_module(storage)
        collection = runtime_collection(project_chroma_path)

    if pages:
        target_pages = [normalize_page_name(p.strip()) for p in pages.split(",") if p.strip()]
        target_pages = [p for p in target_pages if p]
    else:
        target_pages = []

    result: dict[str, dict[str, str]] = {}
    records = collection.get()
    page_entries: dict[str, list[dict[str, Any]]] = {}

    for meta in filter_metadata_by_project(records.get("metadatas", [])):
        if not isinstance(meta, dict):
            continue

        original = (meta.get("page_name") or "").strip()
        keys = {normalize_page_name(original)}
        if original:
            keys.add(original)
            keys.add(original.lower())
        keys.discard("")

        for key in keys:
            page_entries.setdefault(key, []).append(meta)

    after_entries = _page_entries_from_enrichment(meta_dir, "after_enrichment")
    before_entries = _page_entries_from_enrichment(meta_dir, "before_enrichment")

    for key, entries in after_entries.items():
        page_entries.setdefault(key, []).extend(entries)
    for key, entries in before_entries.items():
        page_entries.setdefault(key, []).extend(entries)

    discovered_pages = [p for p in sorted(page_entries.keys()) if p]
    chroma_pages = [normalize_page_name(p) for p in filter_all_pages(project_chroma_path) if normalize_page_name(p)]
    if target_pages:
        seen_pages = set()
        target_pages = [p for p in target_pages if not (p in seen_pages or seen_pages.add(p))]
    else:
        seen_pages = set()
        target_pages = []
        for page_name in discovered_pages + chroma_pages:
            if page_name and page_name not in seen_pages:
                seen_pages.add(page_name)
                target_pages.append(page_name)

    pages_dir.mkdir(parents=True, exist_ok=True)

    for page in target_pages:
        entries = list(page_entries.get(page, []))

        if not entries:
            direct_file = meta_dir / f"after_enrichment_{page}.json"
            if direct_file.exists():
                entries = _load_json_list(direct_file)

        if not entries:
            direct_file = meta_dir / f"before_enrichment_{page}.json"
            if direct_file.exists():
                entries = _load_json_list(direct_file)

        if not entries:
            continue

        entries = _annotate_legacy_input_labels(entries)
        filtered: list[dict[str, Any]] = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue

            action_type = _action_type(entry)
            if not _should_keep_entry_for_page_methods(entry, action_type):
                continue

            filtered.append(entry)

        entries = _best_entries_by_unique_name(filtered)
        entries = _best_icon_entries_by_intent(entries)
        entries = _dedupe_entries(entries)
        if not entries:
            continue

        page_slug = safe(page)
        filename = pages_dir / f"{page_slug}_page_methods.py"

        all_methods_code = [ASSERT_HELPER_BLOCK]
        used_names: dict[str, int] = {}

        for entry in entries:
            method_code = build_method(entry, used_names)
            if method_code:
                all_methods_code.append(method_code)

        final_code = "\n\n".join(all_methods_code)
        final_code += "\n\n" + WRAPPER_BLOCK

        filename.write_text(final_code, encoding="utf-8")
        storage.write_file(filename.relative_to(run_folder).as_posix(), final_code, "utf-8")

        result[page] = {
            "methods_file": str(filename),
        }

    return result
