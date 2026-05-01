# image_text_extractor.py
# ############################ Open AI Logic for Image API ############################

import os
import base64
import io
import uuid
from pathlib import Path
from dotenv import load_dotenv
import json
from datetime import datetime
import re
from typing import Optional
from PIL import Image
from sqlalchemy.orm import Session

from config.settings import get_region_path
from utils.file_utils import save_region, build_standard_metadata
from utils.match_utils import normalize_page_name
from services.chroma_service import upsert_text_record
from services.token_service import log_token_usage
from utils.openai_client import call_openai

# ------------------------------------------------------------------------------------
# Setup
# ------------------------------------------------------------------------------------
load_dotenv()

PROMPT_FILE_PATH = os.path.join(os.path.dirname(__file__), '..', 'prompts', 'image_text_extraction.txt')
with open(PROMPT_FILE_PATH, 'r') as f:
    PROMPT = f.read()

SUPPLEMENTAL_ICON_PROMPT = """You are extracting ONLY icon-only and image-only UI controls that are easy to miss in a full-screen scan.

Return ONE line per missed or small control using:
<label_text> - <ocr_type> - <intent>

Rules:
- Capture tiny header icons, sidebar icons, toolbar icons, badges, avatar/profile controls, mail icons, settings icons, notification icons, grid/launcher icons, hand/cursor icons, people/users icons, and three dots menus.
- Include only icon-only or image-only controls and badge numbers visible in this crop.
- If an icon has no visible text, use a short descriptive contextual name.
- If multiple similar icons exist, make the label unique using the nearest context or left/right position.
- Allowed ocr_type values: iconbutton, image, label
- Clickable icons must be iconbutton.
- Badge counts must be label.
- Do not output explanations or markdown.
"""

# ------------------------------------------------------------------------------------
# Helper normalization functions
# ------------------------------------------------------------------------------------

def _normalize_separators(s: str) -> str:
    """Normalize separators like ':' and '-', tidy spaces, remove bullets."""
    s = s.replace("–", "-").replace("—", "-")
    s = re.sub(r"^[\s>*•\-]+\s*", "", s)
    s = re.sub(r"\s*:\s*", " - ", s)
    s = re.sub(r"\s*-\s*", " - ", s)
    s = re.sub(r"\s{2,}", " ", s).strip()
    return s


def _clean_line(line: str) -> str:
    """Remove numbering/markdown and normalize separators."""
    line = re.sub(r"^\s*(\(?\d+\)?[.)]\s*)", "", line)
    line = re.sub(r"(\*\*|\*|`|__|_)", "", line)
    return _normalize_separators(line)


def _snake(s: str) -> str:
    """Convert arbitrary label text to lowercase_snake_case."""
    s = (s or "").strip()
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"[^A-Za-z0-9 ]+", "", s)
    s = s.lower().strip()
    return re.sub(r"\s+", "_", s)


def _normalize_icon_like_label(label_text: str, ocr_type: str) -> tuple[str, str]:
    label = (label_text or "").strip()
    kind = (ocr_type or "").strip().lower()
    lowered = label.lower()
    if not label:
        return label, kind

    if any(
        k in lowered
        for k in (
            "avatar",
            "profile picture",
            "profile photo",
            "user avatar",
            "user profile",
            "profile image",
        )
    ):
        label = "profile icon"
        if kind in ("image", "label"):
            kind = "iconbutton"
        return label, kind

    launcher_markers = (
        "app launcher",
        "launcher icon",
        "grid menu",
        "waffle menu",
        "9 dot",
        "9 dots",
        "dot menu",
        "dots menu",
        "apps menu",
        "apps icon",
    )
    if any(marker in lowered for marker in launcher_markers):
        label = "app launcher"
        if kind in ("image", "label", "button"):
            kind = "iconbutton"
        return label, kind

    if any(k in lowered for k in ("icon", "avatar", "profile", "launcher", "grid", "waffle")) and kind in ("image", "label"):
        kind = "iconbutton"
    return label, kind


def _append_clean_lines(target: list[str], seen: set[str], lines: list[str]) -> None:
    for line in lines:
        key = (line or "").strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        target.append(line)


def _iter_focus_regions(image: Image.Image) -> list[tuple[str, Image.Image]]:
    width, height = image.size
    if width <= 0 or height <= 0:
        return []

    def _crop(box: tuple[int, int, int, int]) -> Image.Image | None:
        left, top, right, bottom = box
        left = max(0, min(left, width))
        top = max(0, min(top, height))
        right = max(left, min(right, width))
        bottom = max(top, min(bottom, height))
        if right - left < 24 or bottom - top < 24:
            return None
        return image.crop((left, top, right, bottom))

    regions: list[tuple[str, Image.Image]] = []
    candidates = [
        ("top_header", (0, 0, width, max(int(height * 0.18), 120))),
        ("left_sidebar", (0, 0, max(int(width * 0.18), 120), height)),
        ("right_rail", (max(0, width - max(int(width * 0.22), 160)), 0, width, height)),
        ("top_right_cluster", (max(0, width - max(int(width * 0.32), 260)), 0, width, max(int(height * 0.20), 120))),
    ]
    for name, box in candidates:
        cropped = _crop(box)
        if cropped is not None:
            regions.append((name, cropped))
    return regions


def build_intent(label_text: str, ocr_type: str) -> str:
    """Deterministic, taxonomy-free intent built from label_text + ocr_type."""
    t = (ocr_type or "").strip().lower()
    base = _snake(label_text)
    if t == "textbox":
        return f"{base}_field" if base else "field"
    if t == "select":
        return f"{base}_select" if base else "select"
    if t == "checkbox":
        return f"{base}_checkbox" if base else "checkbox"
    if t in ("button", "link", "iconbutton"):
        return f"{base}_action" if base else "action"
    if t == "label":
        return f"{base}_info" if base else "info"
    return base or "unknown"


def detect_likely_select(orig_line: str, label_text: str, ocr_type: str) -> str:
    """Heuristic to detect dropdowns/selects that the LLM labelled as textbox/label.

    Looks for common keywords (select, dropdown, choose, option) and visual
    arrow characters often used in UI dropdowns. Returns a possibly-updated
    ocr_type (usually 'select' or the original).
    """
    try:
        s = (orig_line or "") + " " + (label_text or "")
        s_l = s.lower()
        # keywords indicating a select/dropdown
        kws = ("select", "dropdown", "choose", "choose an", "choose a", "pick", "option", "options")
        if any(k in s_l for k in kws):
            return "select"

        # common arrow glyphs used in dropdown UI elements
        arrows = set(["▾", "▿", "▼", "˅", "˄", "▸", "▶", "⌄", "˅", "ˇ"])
        if any(ch in (orig_line or "") for ch in arrows):
            return "select"

        # if LLM guessed 'label' or 'textbox' but the label contains 'option: ' patterns
        if ocr_type and ocr_type.lower() in ("textbox", "label") and "option" in s_l:
            return "select"

    except Exception:
        pass
    return ocr_type


def _parse_ocr_line(line: str) -> tuple[str, str, str]:
    """
    Parse a vision line into (label_text, ocr_type, intent_raw).

    The LLM is instructed to output: <label_text> - <ocr_type> - <intent>
    but in practice we see variants such as:
      - extra separators: "Username - - textbox - usernamefield"
      - type token embedded in a longer token
      - unicode dash variants already normalized to "-"

    This parser is intentionally tolerant; it aims to recover the best label/type.
    """
    s = (line or "").strip()
    if not s:
        return "", "", ""

    known_types = ("textbox", "button", "iconbutton", "label", "checkbox", "select", "dropdown", "combobox", "link", "image")

    # Primary parse: strict-ish 3-part format.
    m = re.match(
        r"^(?P<label>.+?)\s*-\s*(?P<type>textbox|button|iconbutton|label|checkbox|select|dropdown|combobox|link|image)\s*-\s*(?P<intent>.+?)\s*$",
        s,
        flags=re.IGNORECASE,
    )
    if m:
        label = (m.group("label") or "").strip()
        ocr_type = (m.group("type") or "").strip().lower()
        intent = (m.group("intent") or "").strip()
        # Trim accidental trailing hyphens from label_text (e.g., "Username -" from "Username - - textbox - ...")
        label = re.sub(r"[\s-]+$", "", label).strip()
        return label, ocr_type, intent

    # Fallback parse: split on our canonical delimiter.
    tokens = [t.strip() for t in s.split(" - ") if t and t.strip()]
    if not tokens:
        return "", "", ""

    def _detect_type_token(token: str) -> str:
        t = (token or "").strip().lower()
        if t in known_types:
            return t
        compact = t.replace(" ", "").replace("_", "")
        # allow embedded matches, e.g. "username_textbox_usernamefield"
        for kt in known_types:
            if kt in compact:
                return kt
        return ""

    ocr_index = -1
    detected_type = ""
    for i, t in enumerate(tokens):
        dt = _detect_type_token(t)
        if dt:
            ocr_index = i
            detected_type = dt
            break

    if ocr_index != -1:
        label = " - ".join(tokens[:ocr_index]).strip()
        intent = " ".join(tokens[ocr_index + 1:]).strip() if ocr_index + 1 < len(tokens) else ""
        label = re.sub(r"[\s-]+$", "", label).strip()
        return label, detected_type, intent

    # Give up: treat whole line as a label.
    return s, "label", ""

# ------------------------------------------------------------------------------------
# Main image processor
# ------------------------------------------------------------------------------------

async def process_image_gpt(
    image: Image.Image,
    filename: str,
    image_path: str = "",
    regionsPath: str = "",
    projectChromaPath :str="",
    debug_log_path: str = None,
    db: Optional[Session] = None,
    project_id: Optional[int] = None,
) -> list:

    page_name = normalize_page_name(filename)

    def _call_vision(img: Image.Image, prompt_text: str = PROMPT) -> tuple[list[str], list[str]]:
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        image_base64 = base64.b64encode(buf.getvalue()).decode("utf-8")

        model_name = os.getenv("AI_OCR_VISION_MODEL", "gpt-4o")
        max_tokens = int(os.getenv("AI_OCR_MAX_TOKENS", "8000"))
        result = call_openai(
            model=model_name,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt_text},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_base64}", "detail": "high"}}
                ],
            }],
            max_tokens=max_tokens,
            temperature=0,
        )
        log_token_usage(
            db=db,
            project_id=project_id,
            feature="hybrid_generation",
            usage=result.get("usage"),
            model=result.get("model"),
        )

        raw = (result.get("content") or "").strip()
        raw_lines = raw.splitlines() if raw else []

        clean_lines: list[str] = []
        for line in raw_lines:
            if not line.strip():
                continue
            line = _clean_line(line)
            if line:
                clean_lines.append(line)
        return raw_lines, clean_lines

    # Use tiling for large images to avoid missing text on dense screens.
    tile_size = 1200
    overlap = 80
    w, h = image.size
    tiles: list[Image.Image] = []
    if w > tile_size or h > tile_size:
        step = max(1, tile_size - overlap)
        for y in range(0, h, step):
            for x in range(0, w, step):
                box = (x, y, min(x + tile_size, w), min(y + tile_size, h))
                tiles.append(image.crop(box))
    else:
        tiles.append(image)

    raw_lines: list[str] = []
    clean_lines: list[str] = []
    seen = set()
    for tile in tiles:
        raw_part, clean_part = _call_vision(tile)
        raw_lines.extend(raw_part)
        _append_clean_lines(clean_lines, seen, clean_part)

    # Supplemental pass for small icon-only controls that are often skipped in full-screen scans.
    icon_sweep_enabled = os.getenv("AI_ENABLE_ICON_SWEEP", "1").strip().lower() not in {"0", "false", "no"}
    if icon_sweep_enabled:
        upscale = max(1, int(os.getenv("AI_ICON_SWEEP_UPSCALE", "3")))
        max_region_size = int(os.getenv("AI_ICON_SWEEP_MAX_REGION", "2200"))
        for _region_name, region in _iter_focus_regions(image):
            working = region
            if upscale > 1:
                resized_width = min(region.size[0] * upscale, max_region_size)
                resized_height = min(region.size[1] * upscale, max_region_size)
                if resized_width > 0 and resized_height > 0:
                    working = region.resize((resized_width, resized_height), Image.Resampling.LANCZOS)
            raw_part, clean_part = _call_vision(working, prompt_text=SUPPLEMENTAL_ICON_PROMPT)
            raw_lines.extend(raw_part)
            _append_clean_lines(clean_lines, seen, clean_part)

    # Save audit logs
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = os.path.splitext(os.path.basename(filename))[0]
        file_name = f"{timestamp}_{base_name}.txt"
        folder = "data/openai_response"
        os.makedirs(folder, exist_ok=True)
        out_file = os.path.join(folder, file_name)
        with open(out_file, "w", encoding="utf-8") as f:
            f.write("---- RAW ----\n")
            for l in raw_lines:
                f.write((l or "") + "\n")
            f.write("\n---- CLEANED ----\n")
            for l in clean_lines:
                f.write((l or "") + "\n")
    except Exception:
        pass

    results = []
    known_types = {"textbox", "button", "iconbutton", "label", "checkbox", "select", "dropdown", "combobox", "link", "image"}
    regions_dir = Path(regionsPath)
    regions_dir.mkdir(parents=True, exist_ok=True)

    # ---------------------------------------------------------------
    # Robust parsing with type detection (handles hyphens and colons)
    # ---------------------------------------------------------------
    for orig in clean_lines:
        line = orig.strip()
        if not line:
            continue

        label_text, ocr_type, intent = _parse_ocr_line(line)
        if not label_text and ocr_type == "iconbutton":
            label_text = "icon_button"
        if not label_text:
            continue

        # Clean fake labels like 'textbox' or 'button'
        if label_text.lower() in known_types:
            label_text = ""

        ocr_type = ocr_type.lower().strip()
        label_text = label_text.strip()
        if label_text:
            label_text, ocr_type = _normalize_icon_like_label(label_text, ocr_type)

        # Heuristic: some dropdowns are mislabelled by the LLM. Detect and fix.
        new_type = detect_likely_select(orig, label_text, ocr_type)
        if new_type and new_type != ocr_type:
            ocr_type = new_type

        # Deterministic intent
        intent = build_intent(label_text, ocr_type)

        if intent in ("unknown", "action", "field", "select", "checkbox", "info"):
            print(f"[INTENT-NOTE] Generic intent → label='{label_text}' type='{ocr_type}' line='{orig}'")

        # Dummy bounding box (placeholder until detector)
        unique_id = str(uuid.uuid4())
        x, y, w, h = 10, 10, 100, 40

        region_path = save_region(
            image, x, y, w, h,
            str(regions_dir),
            page_name,
            image_path=image_path
        )

        element = {
            "label_text": label_text,
            "ocr_type": ocr_type,
            "intent": intent,
            "x": x,
            "y": y,
            "width": w,
            "height": h,
            "bbox": f"{x},{y},{w},{h}",
            "confidence_score": 1.0,
            "data_id" : "",
        }
        if ocr_type == "iconbutton":
            # Keep a secondary label without generic icon words for matching.
            variant = re.sub(r"\\b(icon|button)\\b", "", label_text, flags=re.I).strip()
            if variant and variant.lower() != label_text.lower():
                element["variant_text"] = variant

        metadata = build_standard_metadata(
            element,
            page_name,
            image_path=region_path
        )
        metadata["id"] = unique_id
        metadata["ocr_id"] = unique_id
        metadata["get_by_text"] = label_text

        # Store metadata
        try:
            stored_metadata = upsert_text_record(projectChromaPath , metadata)
            results.append(stored_metadata)
        except Exception as e:
            print(f"[ERROR] Failed to upsert to ChromaDB for label='{label_text}': {e}")

        # Optional debug log
        if debug_log_path:
            try:
                with open(debug_log_path, "a", encoding="utf-8") as log_file:
                    log_file.write(json.dumps(metadata, ensure_ascii=False) + "\n")
            except Exception:
                pass

    return results    
