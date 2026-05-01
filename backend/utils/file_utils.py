import hashlib
import os
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from PIL import Image

from services.ocr_type_classifier import classify_ocr_type
from services.yolo_detector import detect_ui_elements_yolo
from utils.match_utils import assign_intent_semantic


def save_region(
    image: Image.Image,
    x: int,
    y: int,
    w: int,
    h: int,
    output_dir: str,
    page_name: str = "page",
    image_path: str = "",
) -> Dict[str, Any]:
    """
    Persist a cropped region to disk, leveraging YOLO to snap to the closest UI element.
    Returns metadata describing the saved region so downstream callers can reuse it.
    """
    detected_type = ""
    detected_confidence = 0.0

    if image_path and os.path.exists(image_path):
        try:
            x, y, w, h, detected_type, detected_confidence = detect_ui_elements_yolo(
                image_path, (x, y, w, h)
            )
        except Exception:
            detected_type = ""
            detected_confidence = 0.0

    # Clamp bounding box to image dimensions
    x = max(0, min(x, image.width - 1))
    y = max(0, min(y, image.height - 1))
    w = max(1, min(w, image.width - x))
    h = max(1, min(h, image.height - y))

    # Generate file name
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
    filename = f"{page_name}_{x}_{y}_{w}_{h}_{timestamp}.png"
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    region_path = output_path / filename

    # Crop and save
    cropped = image.crop((x, y, x + w, y + h))
    cropped.save(str(region_path))

    return {
        "path": str(region_path),
        "x": x,
        "y": y,
        "width": w,
        "height": h,
        "detected_type": detected_type,
        "detected_confidence": detected_confidence,
    }


def _slug(text: str) -> str:
    return re.sub(r"_+", "_", re.sub(r"[^\w]+", "_", (text or "").strip().lower())).strip("_")


_ICON_FAMILY_SYNONYMS = {
    "profile": {"profile", "avatar", "user", "account"},
    "calendar": {"calendar", "date", "datepicker"},
    "clock": {"clock", "time", "timer", "schedule"},
    "menu": {"menu", "kebab", "dots", "dot", "more", "ellipsis"},
    "launcher": {"launcher", "apps", "app", "grid", "waffle"},
    "search": {"search", "find", "lookup"},
    "notification": {"notification", "notifications", "bell", "alert"},
    "settings": {"settings", "gear", "cog"},
    "close": {"close", "cancel", "dismiss", "clear", "xmark", "cross"},
    "cart": {"cart", "basket", "shopping"},
    "download": {"download", "export"},
    "upload": {"upload", "attach", "paperclip"},
}

_GENERIC_ICON_WORDS = {
    "icon",
    "button",
    "action",
    "image",
    "click",
    "clickable",
}

_INPUT_LIKE_TYPES = {"textbox", "select", "dropdown", "combobox", "date"}
_INPUT_PREFIXES = (
    "enter ",
    "type ",
    "fill ",
    "input ",
    "select ",
    "choose ",
    "pick ",
    "search ",
    "add ",
    "provide ",
)
_INPUT_SUFFIXES = {
    "field",
    "textbox",
    "input",
    "value",
    "text",
    "here",
}


def _meaningful_text(*values: Any) -> str:
    for value in values:
        text = str(value or "").strip()
        if text:
            return text
    return ""


def _is_generic_icon_phrase(value: str) -> bool:
    text = _slug(value)
    if not text:
        return True
    tokens = [token for token in text.split("_") if token]
    if not tokens:
        return True
    return all(token in _GENERIC_ICON_WORDS for token in tokens)


def _clean_context_label(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    text = re.sub(r"\s+", " ", text).strip()
    if _is_generic_icon_phrase(text):
        return ""
    return text


def _normalize_input_candidate(value: str) -> str:
    text = re.sub(r"\s+", " ", str(value or "").strip())
    if not text:
        return ""
    lower = text.lower()
    for prefix in _INPUT_PREFIXES:
        if lower.startswith(prefix):
            text = text[len(prefix) :].strip()
            lower = text.lower()
            break
    text = re.sub(r"^(please\s+)?(enter|type|fill|input|select|choose|pick|search|add|provide)\s+", "", text, flags=re.I)
    text = re.sub(r"\s+(field|textbox|input|value|text|here)\s*$", "", text, flags=re.I)
    text = re.sub(r"^[\s:*\-]+|[\s:*\-]+$", "", text).strip()
    return text


def _looks_placeholder_like(value: str) -> bool:
    text = re.sub(r"\s+", " ", str(value or "").strip()).lower()
    if not text:
        return False
    if any(text.startswith(prefix) for prefix in _INPUT_PREFIXES):
        return True
    tokens = [token for token in re.split(r"\s+", text) if token]
    if len(tokens) >= 2 and tokens[-1] in _INPUT_SUFFIXES:
        return True
    return False


def _derive_input_labels(element: dict, label_text: str, ocr_type: str) -> tuple[str, str, str]:
    placeholder = str(element.get("placeholder") or "").strip()
    raw_label_text = str(label_text or "").strip()
    if ocr_type not in _INPUT_LIKE_TYPES:
        return raw_label_text, placeholder, raw_label_text

    context_candidates = [
        element.get("field_context_label"),
        element.get("related_input_label"),
        element.get("nearby_label"),
        element.get("label"),
    ]
    canonical_label = ""
    for candidate in context_candidates:
        cleaned = _normalize_input_candidate(candidate)
        if cleaned and not _looks_placeholder_like(candidate):
            canonical_label = cleaned
            break

    if not canonical_label:
        cleaned_label = _normalize_input_candidate(raw_label_text)
        cleaned_placeholder = _normalize_input_candidate(placeholder)
        if raw_label_text and not _looks_placeholder_like(raw_label_text):
            canonical_label = cleaned_label or raw_label_text
        elif cleaned_label:
            canonical_label = cleaned_label
        elif cleaned_placeholder:
            canonical_label = cleaned_placeholder

    if raw_label_text and _looks_placeholder_like(raw_label_text) and not placeholder:
        placeholder = raw_label_text

    canonical_label = canonical_label or raw_label_text or _normalize_input_candidate(placeholder) or placeholder
    return canonical_label.strip(), placeholder, raw_label_text


def _infer_icon_family(*values: Any) -> str:
    joined = " ".join(str(value or "").strip().lower() for value in values if str(value or "").strip())
    if not joined:
        return ""
    compact = _slug(joined).replace("_", " ")
    for family, tokens in _ICON_FAMILY_SYNONYMS.items():
        if any(token in compact.split() for token in tokens) or any(f" {token} " in f" {compact} " for token in tokens):
            return family
    pieces = [piece for piece in _slug(joined).split("_") if piece and piece not in _GENERIC_ICON_WORDS]
    return pieces[0] if pieces else ""


def _infer_icon_variant(value: str, family: str) -> str:
    text = str(value or "").strip().lower()
    if not text:
        return ""
    if family == "menu" and ("three dots" in text or "kebab" in text or "ellipsis" in text):
        return "three_dots"
    if family == "launcher" and any(token in text for token in ("9 dot", "9 dots", "waffle", "grid")):
        return "grid"
    if "outline" in text:
        return "outline"
    if "filled" in text:
        return "filled"
    return ""


def _derive_icon_contexts(element: dict, label_text: str, ocr_type: str) -> dict[str, Any]:
    dom_accessible_name = _meaningful_text(
        element.get("dom_accessible_name"),
        element.get("aria_label"),
        element.get("aria-label"),
        element.get("title_text"),
        element.get("title"),
        element.get("alt_text"),
        element.get("alt"),
    )
    family = _infer_icon_family(
        element.get("icon_family"),
        label_text,
        dom_accessible_name,
        element.get("variant_text"),
        element.get("intent"),
        element.get("unique_name"),
    )
    field_context_label = _clean_context_label(
        _meaningful_text(
            element.get("field_context_label"),
            element.get("related_input_label"),
            element.get("input_context_label"),
        )
    )
    related_input_label = _clean_context_label(
        _meaningful_text(
            element.get("related_input_label"),
            field_context_label,
            element.get("placeholder"),
        )
    )
    container_context = _clean_context_label(
        _meaningful_text(
            element.get("container_context"),
            element.get("css_selector"),
            element.get("id"),
            element.get("dom-id"),
            element.get("tag_name"),
            element.get("role"),
        )
    )
    x = element.get("x", 0)
    y = element.get("y", 0)
    try:
        position_context = f"x{int(float(x))}_y{int(float(y))}"
    except Exception:
        position_context = ""

    confidence_score = float(element.get("confidence_score", element.get("detected_confidence", 1.0)) or 0.0)
    dom_confidence = 1.0 if element.get("dom_matched") else 0.0
    if dom_accessible_name:
        dom_confidence = max(dom_confidence, 0.9)
    final_confidence = round((confidence_score + dom_confidence) / 2.0, 3)

    disambiguation_base = _clean_context_label(
        _meaningful_text(
            element.get("disambiguation_key"),
            " ".join(part for part in (field_context_label, family or label_text) if part),
            label_text,
        )
    )
    disambiguation_key = _slug(disambiguation_base)

    is_clickable = bool(
        element.get("is_clickable")
        or ocr_type in {"button", "link", "iconbutton", "imagebutton", "select", "checkbox"}
        or str(element.get("role") or "").strip().lower() in {"button", "link", "menuitem", "tab", "switch"}
        or element.get("click_type")
    )

    return {
        "icon_family": family,
        "icon_variant": _infer_icon_variant(_meaningful_text(label_text, dom_accessible_name), family),
        "is_clickable": is_clickable,
        "dom_accessible_name": dom_accessible_name,
        "field_context_label": field_context_label,
        "container_context": container_context,
        "position_context": position_context,
        "related_input_label": related_input_label,
        "visual_confidence": round(confidence_score, 3),
        "dom_confidence": round(dom_confidence, 3),
        "final_confidence": final_confidence,
        "disambiguation_key": disambiguation_key,
        "instance_index": element.get("instance_index", ""),
        "is_decorative": bool(element.get("is_decorative", False)),
        "icon_source": element.get("icon_source") or ("ocr+dom" if element.get("dom_matched") else "ocr_only"),
    }


def _derive_intent(label_text: str, ocr_type: str, existing_intent: str) -> str:
    if existing_intent:
        return existing_intent

    semantic = assign_intent_semantic(label_text or "")
    if semantic:
        return semantic

    base = _slug(label_text)
    if not base:
        return ocr_type or "unknown"

    if ocr_type in ("textbox", "date"):
        return f"{base}_field"
    if ocr_type == "select":
        if base.startswith("select_") or base.endswith("_select"):
            return base
        return f"{base}_select"
    if ocr_type == "checkbox":
        return f"{base}_checkbox"
    if ocr_type in ("button", "link"):
        return f"{base}_action"
    return base


def build_standard_metadata(
    element: dict,
    page_name: str,
    image_path: str = "",
    source_url: str = "",
) -> dict:
    label_text = element.get("label_text") or element.get("text") or ""
    ocr_type = (element.get("ocr_type") or "").strip().lower()
    detected_type = (element.get("detected_type") or "").strip().lower()
    intent = (element.get("intent") or "").strip()
    raw_label_text = str(label_text or "").strip()

    if not ocr_type or ocr_type == "unknown":
        ocr_type = detected_type or ocr_type

    if (not ocr_type or ocr_type == "unknown") and image_path:
        classified = classify_ocr_type(image_path)
        if classified and classified != "unknown":
            ocr_type = classified

    label_text, placeholder_text, raw_label_text = _derive_input_labels(element, str(label_text or ""), ocr_type)

    intent = _derive_intent(label_text, ocr_type, intent)
    unique_name = generate_unique_name(page_name, label_text, ocr_type, intent)
    icon_metadata = {}
    if ocr_type in {"iconbutton", "imagebutton"} or _infer_icon_family(label_text, element.get("aria_label"), element.get("title_text"), element.get("alt_text")):
        icon_metadata = _derive_icon_contexts(element, label_text, ocr_type)

    metadata = {
        "page_name": page_name,
        "label_text": label_text,
        "canonical_label_text": label_text,
        "raw_label_text": raw_label_text,
        "ocr_type": ocr_type,
        "intent": intent,
        "unique_name": unique_name,
        "external": False,
        "dom_matched": element.get("dom_matched", False),
        "region_image_path": image_path,
        "source_url": source_url,
        "confidence_score": element.get("confidence_score", element.get("detected_confidence", 1.0)),
        "visibility_score": element.get("visibility_score", 1.0),
        "locator_stability_score": element.get("locator_stability_score", 1.0),
        "id": element.get("id") or element.get("ocr_id") or element.get("element_id", ""),
        "ocr_id": element.get("ocr_id") or element.get("id") or element.get("element_id", ""),
        "text": element.get("text") or label_text,
        "x": element.get("x", element.get("boundingBox", {}).get("x", 0)),
        "y": element.get("y", element.get("boundingBox", {}).get("y", 0)),
        "width": element.get("width", element.get("boundingBox", {}).get("width", 0)),
        "height": element.get("height", element.get("boundingBox", {}).get("height", 0)),
        "used_in_tests": element.get("used_in_tests", []),
        "last_tested": element.get("last_tested", ""),
        "healing_success_rate": element.get("healing_success_rate", 0.0),
        "snapshot_id": element.get("snapshot_id", ""),
        "match_timestamp": element.get("match_timestamp", ""),
        "bbox": element.get(
            "bbox",
            f"{element.get('x', 0)},{element.get('y', 0)},{element.get('width', 0)},{element.get('height', 0)}",
        ),
        "position_relation": element.get("position_relation", {}),
        "tag_name": element.get("tag_name", ""),
        "xpath": element.get("xpath", ""),
        "get_by_text": element.get("get_by_text", ""),
        "get_by_role": element.get("get_by_role", ""),
        "html_snippet": element.get("html_snippet", ""),
        "placeholder": placeholder_text,
        "aria_label": element.get("aria_label", element.get("aria-label", "")),
        "title_text": element.get("title_text", element.get("title", "")),
        "alt_text": element.get("alt_text", element.get("alt", "")),
        "variant_text": element.get("variant_text", ""),
        "role": element.get("role", ""),
        "data_testid": element.get("data_testid", element.get("data-testid", "")),
        "data_qa": element.get("data_qa", ""),
        "data_cy": element.get("data_cy", ""),
        "data_test": element.get("data_test", ""),
        "css_selector": element.get("css_selector", ""),
        "is_draggable": element.get("is_draggable", False),
        "is_droppable": element.get("is_droppable", False),
        "click_type": element.get("click_type", ""),
        "drag_handle_selector": element.get("drag_handle_selector", ""),
        "drag_handle_text": element.get("drag_handle_text", ""),
        "detected_type": detected_type,
        "detected_confidence": element.get("detected_confidence", 0.0),
    }
    metadata.update(icon_metadata)

    return sanitize_metadata(metadata)


def generate_unique_name(page_name: str, label_text: str, ocr_type: str, intent: str) -> str:
    slug_label = _slug(label_text)
    slug_intent = _slug(intent)
    slug_type = _slug(ocr_type)

    if slug_label:
        return "_".join(filter(None, (page_name, slug_label, slug_type, slug_intent)))

    unique_str = "_".join(filter(None, (page_name, slug_type, slug_intent)))
    digest = hashlib.sha256(unique_str.encode("utf-8")).hexdigest()[:8]
    return f"{unique_str}_{digest}"


def sanitize_metadata(metadata: dict) -> dict:
    def safe_convert(value):
        if isinstance(value, (str, int, float, bool)):
            return value
        if value is None:
            return ""
        if isinstance(value, (dict, list)):
            return str(value)
        return str(value)

    return {k: safe_convert(v) for k, v in metadata.items()}


def clean_old_files(directory: str, age_seconds: int = 3600):
    """
    Deletes files older than `age_seconds` from the given directory.
    """
    dir_path = Path(directory)
    if not dir_path.exists():
        return

    now = time.time()
    for file in dir_path.glob("*"):
        if file.is_file():
            file_age = now - file.stat().st_mtime
            if file_age > age_seconds:
                try:
                    file.unlink()
                except Exception as e:
                    print(f"[CLEANUP ERROR] Failed to delete {file}: {e}")
