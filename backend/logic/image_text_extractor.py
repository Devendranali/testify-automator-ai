# image_text_extractor.py
# ############################ Open AI Logic for Image API ############################

from PIL import Image
from openai import OpenAI
import os
import base64
import uuid
from dotenv import load_dotenv
import json
from datetime import datetime
import re

from config.settings import get_data_path
from utils.file_utils import save_region, build_standard_metadata
from utils.match_utils import normalize_page_name
from services.chroma_service import upsert_text_record

# ------------------------------------------------------------------------------------
# Setup
# ------------------------------------------------------------------------------------
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Prompt: keep simple & consistent formatting; we will compute intent ourselves.
PROMPT = """You are an expert UI vision parser. You must extract *all* visible UI elements from this screenshot.

Output one line per element, using this exact format:
  <label_text> - <ocr_type> - <intent>

Rules:
1. <label_text> — The **visible label or text** closest to the interactive element.  
   - For input fields, use the *label* or *placeholder* ("Email", "Full Name", etc.).  
   - For buttons, use the button text ("Submit", "Save", "Cancel").  
   - For dropdowns or picklists (any field with ▼, chevron, or option list), use their label ("Country", "Account Type", "Time Zone").  
   - If the label appears above or beside the field, capture it.  
   - Never leave label_text blank unless nothing is visible nearby.

2. <ocr_type> — One of: textbox, button, label, checkbox, **select**, link, image.  
   - **Always classify dropdowns, picklists, comboboxes, or any field with an angle-down (▼) icon or down arrow symbol as `select`.**  
   - If the field displays a default or pre-selected value (for example, showing a word or option inside), but also has a dropdown indicator or opens a list of options, it must still be categorized as `select`.  
   - Fields with free text entry and no dropdown or arrow indicator → `textbox`.  
   - When in doubt, if the element visually includes a chevron, down-arrow, caret, or expandable menu indicator, treat it as a `select`.

3. <intent> — A concise snake_case token describing the element’s role.  
   - Derived directly from label_text. Examples:  
       "Email" → email_field  
       "Password" → password_field  
       "Login" → login_action  
       "Account Type" → account_type_select  
       "Primary Time Zone" → primary_time_zone_select  

4. Do NOT include any commentary, numbering, or blank lines.

5. Do NOT paraphrase label_text — use the **exact on-screen wording**.

6. Be exhaustive: every visible field, dropdown, or button must appear as one output line.

Examples:
  Username - textbox - username_field
  Password - textbox - password_field
  Login - button - login_action
  Remember Me - checkbox - remember_me_checkbox
  Account Type - select - account_type_select
  Preferred Method of Contact - select - preferred_method_of_contact_select
  Primary Time Zone - select - primary_time_zone_select

"""

# Stronger, ASCII-safe prompt to encourage exhaustive listing and consistent typing
PROMPT_EXHAUSTIVE = (
    "You are an expert UI vision parser. Extract ALL visible UI elements from this screenshot.\n\n"
    "Output EXACTLY one line per element, in this format:\n"
    "  <label_text> - <ocr_type> - <intent>\n\n"
    "Guidelines:\n"
    "1) <label_text>: the exact on-screen label or text nearest to the control.\n"
    "   - Inputs: label or placeholder (e.g., \"Email\").\n"
    "   - Buttons/links: the clickable text (e.g., \"Submit\", \"Cancel\").\n"
    "   - Dropdowns/comboboxes: the field label (e.g., \"Account Type\").\n"
    "   - If no label is visible, leave label_text empty only as a last resort.\n\n"
    "2) <ocr_type>: one of: textbox, button, label, checkbox, select, link, image, radio, toggle, textarea, date, time, file.\n"
    "   - If the control shows a chevron/down-arrow or opens a list of options, use select.\n"
    "   - Free text entry with no dropdown indicator is textbox (or textarea if clearly multi-line).\n\n"
    "3) <intent>: concise snake_case derived from the label_text and type (e.g., email_field, login_action, account_type_select).\n\n"
    "4) Exhaustive coverage required: list every visible control and descriptive label.\n"
    "   Do not summarize or group; do NOT combine multiple elements on one line. No commentary or numbering.\n\n"
    "Examples:\n"
    "  Username - textbox - username_field\n"
    "  Password - textbox - password_field\n"
    "  Login - button - login_action\n"
    "  Remember Me - checkbox - remember_me_checkbox\n"
    "  Account Type - select - account_type_select\n"
    "  Preferred Method of Contact - select - preferred_method_of_contact_select\n"
    "  Primary Time Zone - select - primary_time_zone_select\n"
)

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


def _sanitize_label_text(s: str) -> str:
    """Clean LLM/OCR-extracted label text: remove generic tokens like 'textbox',
    'field', 'input', and collapse odd concatenations like 'Emailfield' -> 'Email'.
    Returns a human-friendly label (title-cased) or empty string if nothing meaningful.
    """
    if not s:
        return ""
    t = s.strip()
    # insert spaces for camelCase/concatenated words (e.g., EmailField -> Email Field)
    t = re.sub(r'([a-z])([A-Z])', r'\1 \2', t)
    t = t.replace('_', ' ')
    t = t.lower()
    # remove generic UI words
    generic = [r'\btextbox\b', r'\btext box\b', r'\binput\b', r'\bfield\b', r'\bcontrol\b']
    for pat in generic:
        t = re.sub(pat, ' ', t)
    # common concatenated tokens like 'emailfield' -> 'email'
    t = re.sub(r'email\s*field', 'email', t)
    t = re.sub(r'phone\s*number', 'phone number', t)
    # strip non-word characters except spaces
    t = re.sub(r'[^a-z0-9 ]+', ' ', t)
    t = re.sub(r'\s{2,}', ' ', t).strip()
    # prefer short labels: if multiple words but first is one of common nouns, keep full
    if not t:
        return ""
    # title-case for display
    return t.title()


# Map common symbol-only labels to semantic text and default types
SYMBOL_LABEL_MAP = {
    "×": {"label": "Close", "ocr_type": "button"},
    "✕": {"label": "Close", "ocr_type": "button"},
    "✖": {"label": "Close", "ocr_type": "button"},
    "❌": {"label": "Close", "ocr_type": "button"},
    "🗙": {"label": "Close", "ocr_type": "button"},
    "+": {"label": "Add", "ocr_type": "button"},
    "➕": {"label": "Add", "ocr_type": "button"},
    "🔍": {"label": "Search", "ocr_type": "button"},
    "≡": {"label": "Menu", "ocr_type": "button"},
    "☰": {"label": "Menu", "ocr_type": "button"},
    "⚙": {"label": "Settings", "ocr_type": "button"},
    "↻": {"label": "Refresh", "ocr_type": "button"},
    "🔄": {"label": "Refresh", "ocr_type": "button"},
    "⬇": {"label": "Download", "ocr_type": "button"},
    "⭳": {"label": "Download", "ocr_type": "button"},
}


def _is_value_like(text: str) -> bool:
    """Return True if text looks like a pure data value (price, number, percent),
    not a semantic UI label. Examples: "₹355.95", "$12.00", "12345", "45%".
    """
    if not text:
        return False
    t = (text or "").strip()
    # If it contains any letter, treat as not value-only
    if re.search(r"[A-Za-z]", t):
        return False
    # Accept common currency symbols and numeric punctuation
    return bool(re.fullmatch(r"[\s\u20B9\$\€\£\¥\+\-\.,%0-9]+", t))


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
    if t in ("button", "link"):
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

# ------------------------------------------------------------------------------------
# Main image processor
# ------------------------------------------------------------------------------------

async def process_image_gpt(
    image: Image.Image,
    filename: str,
    image_path: str = "",
    debug_log_path: str = None
) -> list:

    page_name = normalize_page_name(filename)

    # Convert image to base64 for OpenAI Vision API (robust: support missing path)
    image_base64 = None
    try:
        if image_path and os.path.exists(image_path):
            with open(image_path, "rb") as f:
                image_base64 = base64.b64encode(f.read()).decode("utf-8")
    except Exception:
        image_base64 = None
    if not image_base64:
        import io as _io
        buf = _io.BytesIO()
        try:
            image.save(buf, format="PNG")
        except Exception:
            try:
                image.convert("RGB").save(buf, format="PNG")
            except Exception:
                pass
        image_base64 = base64.b64encode(buf.getvalue()).decode("utf-8")

    # Call OpenAI Vision API with your prompt
    response = client.chat.completions.create(
        model=os.getenv("AI_VISION_MODEL", "gpt-4o"),
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": PROMPT_EXHAUSTIVE},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_base64}"}}
            ],
        }],
        max_tokens=int(os.getenv("AI_IMG_MAX_TOKENS", "3500")),
        temperature=float(os.getenv("AI_IMG_TEMPERATURE", "0"))
    )

    raw = (response.choices[0].message.content or "").strip()
    raw_lines = raw.splitlines() if raw else []

    # Clean and normalize
    clean_lines = []
    for line in raw_lines:
        if not line.strip():
            continue
        line = _clean_line(line)
        if line:
            clean_lines.append(line)

    # Save audit logs
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = os.path.splitext(os.path.basename(filename))[0]
        file_name = f"{timestamp}_{base_name}.txt"
        folder = os.path.join(get_data_path(), "openai_response")
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
    known_types = {
        "textbox", "text", "input", "textarea", "email", "password", "phone",
        "button", "submit", "imagebutton", "iconbutton",
        "label", "checkbox", "radio", "radiogroup", "toggle", "switch",
        "select", "dropdown", "combobox", "link", "date", "time", "file", "upload", "image"
    }

    # ---------------------------------------------------------------
    # Robust parsing with type detection (handles hyphens and colons)
    # ---------------------------------------------------------------
    # Expand lines that may contain multiple items separated by common delimiters
    expanded_lines = []
    for _line in clean_lines:
        if any(sep in _line for sep in [';', '•', ' · ', ' | ', ',']) and (' - ' in _line):
            for piece in re.split(r"[;•|]|\s[·]\s|,", _line):
                piece = (piece or '').strip()
                if piece:
                    expanded_lines.append(piece)
        else:
            expanded_lines.append(_line)

    seen_triplets = set()

    for orig in expanded_lines:
        line = (orig or '').strip()
        if not line:
            continue

        line = _clean_line(line)
        tokens = [t.strip() for t in line.split(" - ") if t and t.strip()]
        if not tokens:
            continue

        label_text, ocr_type, intent = "", "", ""

        # Detect type position dynamically
        ocr_index = next((i for i, t in enumerate(tokens) if t.lower() in known_types), -1)

        if ocr_index != -1:
            label_text = " - ".join(tokens[:ocr_index]).strip()
            ocr_type = tokens[ocr_index].lower()
            intent_part = tokens[ocr_index + 1:] if ocr_index + 1 < len(tokens) else []
            intent = " ".join(intent_part).strip()
        else:
            # Fallback: guess structure if no known type
            if len(tokens) == 2:
                label_text, ocr_type = tokens
            elif len(tokens) == 1:
                label_text = tokens[0]
                # Infer action-like labels as button, else default to label
                ocr_type = "button" if re.search(r"\b(login|submit|save|search|next|continue|add|create|ok|place order|checkout)\b", label_text, re.I) else "label"
            else:
                continue

        # Clean fake labels only when label equals type or is a generic control word
        generic_words = {
            "textbox", "button", "label", "checkbox", "select", "link", "image",
            "radio", "toggle", "textarea", "date", "time", "file", "upload"
        }
        if label_text:
            lt = label_text.strip().lower()
            ot = (ocr_type or "").strip().lower()
            if lt == ot or lt in generic_words:
                label_text = ""

        ocr_type = ocr_type.lower().strip()
        label_text = label_text.strip()

        # Heuristic: some dropdowns are mislabelled by the LLM. Detect and fix.
        new_type = detect_likely_select(orig, label_text, ocr_type)
        if new_type and new_type != ocr_type:
            ocr_type = new_type

        # Heuristic: CTA/link-like text should be treated as button
        try:
            lt_low = (label_text or "").strip().lower()
            if ocr_type in ("label", "link", "image"):
                if re.search(r"\b(add|create|new|export|save|submit|continue|next|upload|import|filter|search|apply|reset|edit|update|delete|remove|open)\b", lt_low):
                    ocr_type = "button"
        except Exception:
            pass

        # Heuristic: map symbol-only labels (×, +, 🔍, etc.) to semantic text
        try:
            sym = (label_text or "").strip()
            if sym in SYMBOL_LABEL_MAP:
                mapped = SYMBOL_LABEL_MAP[sym]
                # if original label is just a symbol, replace with semantic text
                if len(sym) <= 2:
                    label_text = mapped.get("label", label_text)
                # coerce type to button if prior type is weak
                if (ocr_type or "") in ("label", "link", "image", ""):
                    ocr_type = mapped.get("ocr_type", ocr_type or "button")
        except Exception:
            pass

        # Heuristic: if label_text is purely a value (price/number), do not keep it as label text
        try:
            if _is_value_like(label_text):
                # Only blank it for non-interactive types; interactive elements may legitimately
                # display numeric values (e.g., number inputs). Keep those.
                if (ocr_type or "").lower() not in (
                    "textbox", "input", "textarea", "select", "combobox", "checkbox", "radio", "button", "link"
                ):
                    label_text = ""
        except Exception:
            pass

        # Normalize overly specific input types to a generic textbox/input
        try:
            t = (ocr_type or "").strip().lower()
            if t in ("text", "input", "email", "password", "phone", "textarea", "number", "url"):
                ocr_type = "textbox"
        except Exception:
            pass

        # If label_text is still empty, derive from the LLM-provided intent tokens when available
        try:
            if not (label_text or "").strip() and intent:
                # strip trailing role suffixes and prettify
                tmp = intent.strip()
                tmp = re.sub(r"_(field|action|select|checkbox|info)$", "", tmp)
                tmp = re.sub(r"[_\s]+", " ", tmp).strip()
                if tmp:
                    label_text = tmp.title()
        except Exception:
            pass

        # Sanitize the label text to remove generic tokens like 'textbox' or 'field'
        try:
            label_text = _sanitize_label_text(label_text)
        except Exception:
            pass

        # Deterministic intent
        intent = build_intent(label_text, ocr_type)

        if intent in ("unknown", "action", "field", "select", "checkbox", "info"):
            print(f"[INTENT-NOTE] Generic intent → label='{label_text}' type='{ocr_type}' line='{orig}'")

        # Dummy bounding box (placeholder until detector)
        unique_id = str(uuid.uuid4())
        x, y, w, h = 10, 10, 100, 40

        region_path = save_region(
            image, x, y, w, h,
            os.path.join(get_data_path(), "regions"),
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

        metadata = build_standard_metadata(
            element,
            page_name,
            image_path=region_path
        )
        metadata["id"] = unique_id
        metadata["ocr_id"] = unique_id
        # Ensure element_id mirrors the primary id for downstream consumers
        try:
            metadata["element_id"] = metadata.get("element_id") or unique_id
        except Exception:
            metadata["element_id"] = unique_id
        metadata["get_by_text"] = label_text

        # Store metadata, avoiding duplicates of (label, type, intent)
        trip = (metadata.get("label_text", ""), metadata.get("ocr_type", ""), metadata.get("intent", ""))
        if trip in seen_triplets:
            continue
        seen_triplets.add(trip)
        try:
            stored_metadata = upsert_text_record(metadata)
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


# Convenience: process multiple images without skipping any on error
async def process_images_gpt(items: list) -> list:
    """Process a sequence of images and aggregate results.

    Each item can be:
      - (image: PIL.Image.Image, filename: str, image_path: str)
      - dict with keys: image, filename, image_path, debug_log_path (optional)

    Returns a flat list of stored metadata entries. Errors on one image are
    logged and skipped so that subsequent images still process.
    """
    aggregated = []
    for it in items or []:
        try:
            if isinstance(it, dict):
                img = it.get("image")
                fname = it.get("filename", "image.png")
                ipath = it.get("image_path", "")
                dlog = it.get("debug_log_path")
            else:
                # assume tuple-like
                img, fname, ipath = it[0], it[1], (it[2] if len(it) > 2 else "")
                dlog = None
            res = await process_image_gpt(img, fname, image_path=ipath, debug_log_path=dlog)
            aggregated.extend(res or [])
        except Exception as e:
            print(f"[IMAGE-PARSE] Failed to process '{getattr(it, 'filename', None) or (it[1] if isinstance(it, (list, tuple)) and len(it)>1 else 'unknown') }': {e}")
            continue
    return aggregated
