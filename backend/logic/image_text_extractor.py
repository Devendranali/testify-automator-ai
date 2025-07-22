# # image_text_extractor.py

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
from utils.match_utils import normalize_page_name,assign_intent_semantic
from services.chroma_service import upsert_text_record  

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
# OLD PROMPT
# PROMPT = """You are an expert computer vision model using OpenAI's capabilities.

# Your task is to analyze a given screenshot of a user interface (UI) and extract every visible UI element, accurately identifying its type and intent.

# 1. Element Extraction:
#    - Extract ALL visible UI text from the image, including:
#      • Input fields 
#      • Buttons
#      • Labels (including credentials, instructions)
#      • Dropdowns, checkboxes

# 2. Element Classification:
#    - For each element, output:
#      • Label text (exact as visible)
#      • Element type (one of: `textbox`, `button`, `label`, `checkbox`, `select`)
#      • Intent (like: `login`, `username`, `password`, `price_label`, `submit`, `add_to_cart`, `password_info`, `username_info`, etc.)

#    - For credentials or user types like `standard_user`, `secret_sauce`, assign type as `label` and use intent like `username_info`, `password_info`.

# 3. Format:
#    - Each element on its own line:
#      <label text> - <element type> - <intent>

# 4. Rules:
#    - Do NOT rephrase or skip lines.
#    - Preserve punctuation, line breaks.
#    - Traverse from top-left to bottom-right.

# 5. Only output newline-separated lines like:
#    Username - textbox - login
#    Login - button - login
#    secret_sauce - label - password_info
# """

PROMPT = """You are an expert computer vision model using OpenAI's capabilities.

Your task is to analyze a given screenshot of a user interface (UI) and extract every visible UI element, accurately identifying its type and intent.

1. Element Extraction:
   - Extract ALL visible UI text from the image, including:
     • Input fields
     • Buttons
     • Labels (including credentials, instructions)
     • Dropdowns, checkboxes

2. Element Classification:
   - For each element, output:
     • Label text (exact as visible)
     • Element type (one of: `textbox`, `button`, `label`, `checkbox`, `select`)
     • Intent (like: `login`, `username`, `password`, `price_label`, `submit`, `add_to_cart`, `password_info`, `username_info`, etc.)

   - For credentials or user types like `standard_user`, `secret_sauce`, assign type as `label` and use intent like `username_info`, `password_info`.

   - If the UI element appears as part of a vertical or horizontal navigation menu, always classify it as `button` or `link`.
   - If uncertain whether an element is clickable or navigational, prefer classifying it as a `button` over a `label`.

3. Format:
    - Each element on its own line:
    Always give response in the below format:
    Either
        <label_text> - <ocr_type> - <intent> => if label_text present 
    or 
        - <ocr_type> - <intent> => if label_text is empty 

4. Rules:
   - Do NOT rephrase or skip lines.
   - Preserve punctuation, line breaks.
   - Traverse from top-left to bottom-right.

5. Only output newline-separated lines like:
   Username - textbox - login
   Login - button - login
   secret_sauce - label - password_info
   Dashboard - button - navigation

"""

# PROMPT = """You are an expert computer vision model using OpenAI's capabilities.

# Your task is to analyze a given screenshot of a user interface (UI) and extract every visible UI element, accurately identifying its type and intent.

# 1. Element Extraction:
#    - Extract ALL visible UI text from the image, including:
#      • Input fields (textboxes), even if empty
#      • Buttons
#      • Labels (e.g. "Full Name", "Phone Number", etc.)
#      • Dropdowns, checkboxes

#    - For each input-related label, generate a corresponding textbox/select entry even if it has no typed value.

# 2. Element Classification:
#    - For each element, output:
#      • Label text (exact as visible)
#      • Element type (one of: `textbox`, `button`, `label`, `checkbox`, `select`)
#      • Intent — infer from label (e.g. "Full Name" → `fullname`, "Phone Number" → `phonenumber`, "Email" → `email`, etc.). Use lowercase and remove spaces/underscores.

#    - If the element is a textbox, dropdown, or select without filled values, still extract it using the label.

#    - Use generic fallback intent `valueinput` if unsure.

# 3. Format:
#    - Each element on its own line:
#      <label text> - <element type> - <intent>

# 4. Rules:
#    - Do NOT rephrase or skip lines.
#    - Preserve punctuation, line breaks.
#    - Traverse from top-left to bottom-right.
#    - Even if the textbox has no content, generate its label and input as two elements.

# 5. Examples:
#    Full Name - textbox - fullname
#    Email - textbox - email
#    Account Type - select - accounttype
#    Add Customer - button - submit
# """


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
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": PROMPT},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_base64}"}}
                ]
            }
        ],
        max_tokens=1500,
        temperature=0
    )

    raw_lines = response.choices[0].message.content.strip().splitlines()
    results = []    
    
    # raw_lines = ...   # (your OpenAI output as a list of strings)
    clean_lines = []
    for line in raw_lines:
        # Remove leading serial numbers (like '1. ')
        line = re.sub(r'^\d+\.\s*', '', line)
        # Remove markdown symbols
        line = re.sub(r'(\*\*|\*|`)', '', line)
        # Count dashes
        dash_count = line.count('-')
        if dash_count > 2:
            # Remove leading dash only if there are at least two ' - '
            line = re.sub(r'^\s*-\s*', '', line)

        clean_lines.append(line)


    # Timestamped file naming
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = os.path.splitext(os.path.basename(filename))[0]
    file_name = f"{timestamp}_{base}.txt"
    folder = "data/openai_response"
    os.makedirs(folder, exist_ok=True)
    out_file = os.path.join(folder, file_name)
    with open(out_file, "w", encoding="utf-8") as f:
        for line in raw_lines:
            f.write(line + "\n")
        f.write(f"{'-'*40} After Cleaning {'-'*40}\n")
        for line in clean_lines:
            f.write(line + "\n")

    # ====================
    for line in clean_lines:
        line = line.strip()
        if not line or " - " not in line:
            continue

        # Always split into parts from right
        parts = line.rsplit(" - ", 2)
        if len(parts) == 3:
            label_text, ocr_type, intent = [p.strip() for p in parts]
            if not intent:
                intent = assign_intent_semantic(label_text)
        elif len(parts) == 2:
            first, second = [p.strip() for p in parts]
            # If the first part is empty or looks like a type (starts with dash), treat accordingly
            if line.startswith("-") or not first:
                label_text = ""
                ocr_type = first.lstrip("-").strip()
                intent = second
            else:
                label_text = first
                ocr_type = second
                intent = assign_intent_semantic(label_text)
        else:
            continue

        # # Handle both 3-part and 2-part formats
        # parts = line.rsplit(" - ", 2)
        # if len(parts) == 3:
        #     label_text, ocr_type, intent = [p.strip() for p in parts]
        #     if not intent:
        #         intent = assign_intent_semantic(label_text)
        # elif len(parts) == 2:
        #     label_text, ocr_type = [p.strip() for p in parts]
        #     intent = assign_intent_semantic(label_text)
        # else:
        #     continue

        unique_id = str(uuid.uuid4())
        x, y, w, h = 10, 10, 100, 40  # Dummy values; plug in YOLO here if needed

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

        # if debug_log_path:
        #     with open(debug_log_path, "a", encoding="utf-8") as log_file:
        #         log_file.write(json.dumps(metadata, ensure_ascii=False) + "\n")

        
    return results
