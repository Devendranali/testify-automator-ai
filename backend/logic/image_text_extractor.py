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

from config.settings import DATA_PATH
from utils.file_utils import save_region, build_standard_metadata
from utils.match_utils import normalize_page_name
from services.chroma_service import upsert_text_record

# ------------------------------------------------------------------------------------
# Setup
# ------------------------------------------------------------------------------------
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Prompt: keep simple & consistent formatting; we will compute intent ourselves.
PROMPT = """You are an expert computer vision model using OpenAI's capabilities.

Your task is to analyze a given screenshot of a user interface (UI) and extract every visible UI element.

For EACH element, output exactly one line in one of the following formats:
  <label_text> - <ocr_type> - <intent>
  - <ocr_type> - <intent>            (if label_text is truly empty/absent)

Where:
- <label_text> is the exact on-screen text (preserve punctuation and case).
- <ocr_type> is one of: textbox, button, label, checkbox, select.
- <intent> is a short lowercase_snake_case token derived only from the element text (not from any fixed business taxonomy). If unsure, you may repeat the label in snake_case or leave it minimal.

Rules:
1) Extract ALL visible UI elements from top-left to bottom-right.
2) Do NOT paraphrase <label_text>.
3) Keep <intent> minimal; do not invent categories or business terms.
4) If the element has no text (pure icon), leave label empty and still output the line.
5) No extra commentary; just the lines.

Examples:
  Username - textbox - username
  Password - textbox - password
  Login - button - login
  Dashboard - button - dashboard
  secret_sauce - label - secret_sauce
"""

# ------------------------------------------------------------------------------------
# Robust parsing + deterministic intent (no hardcoded vocab)
# ------------------------------------------------------------------------------------

def _normalize_separators(s: str) -> str:
    """
    Normalize separators to canonical ' - ' and remove common noise:
      - convert en/em dashes to hyphen
      - support ':' as a separator
      - ensure single spaces around hyphens
      - collapse spaces
      - strip leading bullets/markers
    """
    s = s.replace("–", "-").replace("—", "-")
    s = re.sub(r"^[\s>*•\-]+\s*", "", s)         # leading bullets/markers
    s = re.sub(r"\s*:\s*", " - ", s)             # colon as separator
    s = re.sub(r"\s*-\s*", " - ", s)             # tidy hyphen spacing
    s = re.sub(r"\s{2,}", " ", s).strip()        # collapse spaces
    return s

def _clean_line(line: str) -> str:
    """Remove numbering/markdown, then normalize separators."""
    # Remove leading numbering like '1. ', '2) ', '(3) '
    line = re.sub(r"^\s*(\(?\d+\)?[.)]\s*)", "", line)
    # Strip markdown bold/italic/backticks/underscores (formatting only)
    line = re.sub(r"(\*\*|\*|`|__|_)", "", line)
    return _normalize_separators(line)

def _snake(s: str) -> str:
    """
    Convert arbitrary label text to lowercase_snake_case:
      - collapse whitespace
      - drop non-alphanumeric (except spaces)
      - convert spaces to underscores
    """
    s = (s or "").strip()
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"[^A-Za-z0-9 ]+", "", s)
    s = s.lower().strip()
    return re.sub(r"\s+", "_", s)

def build_intent(label_text: str, ocr_type: str) -> str:
    """
    Deterministic, taxonomy-free intent built only from (label_text, ocr_type).
    No hardcoded business lists or aliases.

    Rules:
      textbox   -> <label>_field      (or "field" if label empty)
      select    -> <label>_select     (or "select" if label empty)
      checkbox  -> <label>_checkbox   (or "checkbox" if label empty)
      button    -> <label>_action     (or "action" if label empty)
      link      -> <label>_action     (or "action" if label empty)
      label     -> <label>_info       (or "info" if label empty)
      unknown   -> <label> or "unknown" if both empty

    This ensures "Full Name" + textbox -> "full_name_field", etc.
    """
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
    # Fallback for unexpected types
    return base or "unknown"

# ------------------------------------------------------------------------------------
# Main entry
# ------------------------------------------------------------------------------------

async def process_image_gpt(
    image: Image.Image,
    filename: str,
    image_path: str = "",
    debug_log_path: str = None
) -> list:

    page_name = normalize_page_name(filename)

    # Convert image to base64 for OpenAI Vision API
    with open(image_path, "rb") as f:
        image_base64 = base64.b64encode(f.read()).decode("utf-8")

    # Call OpenAI Vision API with your prompt
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": PROMPT},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_base64}"}}
            ],
        }],
        max_tokens=1500,
        temperature=0
    )

    # Raw lines from model
    raw = (response.choices[0].message.content or "").strip()
    raw_lines = raw.splitlines() if raw else []

    # Clean & normalize lines
    clean_lines = []
    for line in raw_lines:
        if not line or not line.strip():
            continue
        line = _clean_line(line)
        if not line:
            continue
        clean_lines.append(line)

    # Persist raw and cleaned for audit
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

    # Parse each normalized line
    for orig in clean_lines:
        line = orig.strip()
        if not line:
            continue

        # Split with canonical ' - ' separator
        tokens = [t.strip() for t in line.split(" - ") if t and t.strip()]

        label_text = ""
        ocr_type = ""
        # We intentionally ignore the model-provided intent; we compute our own.

        if len(tokens) >= 3:
            # Take the LAST 3 tokens to tolerate extra dashes in label
            label_text, ocr_type = tokens[-3], tokens[-2]
            intent = build_intent(label_text, ocr_type)

        elif len(tokens) == 2:
            first, second = tokens[0], tokens[1]
            # Detect "no label" by looking at original (pre-split) line
            no_label = orig.lstrip().startswith("-")

            if no_label:
                # "- <ocr_type> - <intent>" after normalization becomes "<ocr_type> - <intent>"
                ocr_type = first
                label_text = ""  # don't fabricate labels
                intent = build_intent(label_text, ocr_type)
            else:
                # "<label> - <ocr_type>" (no intent given)
                label_text = first
                ocr_type = second
                intent = build_intent(label_text, ocr_type)
        else:
            # Not parseable; skip
            continue

        # Optional: warn on ultra-generic/unknown intents for later tuning
        if intent in ("unknown", "action", "field", "select", "checkbox", "info"):
            print(f"[INTENT-NOTE] Generic intent → label='{label_text}' type='{ocr_type}' line='{orig}'")

        # Dummy bbox (plug in detector later)
        unique_id = str(uuid.uuid4())
        x, y, w, h = 10, 10, 100, 40

        region_path = save_region(
            image, x, y, w, h,
            os.path.join(DATA_PATH, "regions"),
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
        }

        metadata = build_standard_metadata(
            element,
            page_name,
            image_path=region_path
        )
        metadata["id"] = unique_id
        metadata["ocr_id"] = unique_id
        metadata["get_by_text"] = label_text

        # Storing metadata in ChromaDB
        try:
            stored_metadata = upsert_text_record(metadata)
            results.append(stored_metadata)
        except Exception as e:
            print(f"[ERROR] Failed to upsert to ChromaDB for label='{label_text}': {e}")

        # Optional debug log file
        if debug_log_path:
            try:
                with open(debug_log_path, "a", encoding="utf-8") as log_file:
                    log_file.write(json.dumps(metadata, ensure_ascii=False) + "\n")
            except Exception:
                pass

    return results
