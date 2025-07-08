# # ===================================  PADDLE OCR =============================================
# from paddleocr import PaddleOCR
# from PIL import Image
# import uuid
# import os
# import numpy as np
# import cv2
# from typing import List, Optional
# from utils.file_utils import save_region, build_standard_metadata
# from services.chroma_service import upsert_text_record
# from config.settings import DATA_PATH
# from utils.match_utils import normalize_page_name

# ocr_engine = PaddleOCR(
#     use_angle_cls=True,
#     lang='en',
#     det_db_thresh=0.5,
#     det_db_box_thresh=0.5,
#     det_db_unclip_ratio=1.6,
    
# )

# def enhance_contrast(image: Image.Image) -> Image.Image:
#     """
#     Preprocessing: Convert to grayscale and increase contrast, but avoid binary thresholding.
#     """
#     img = np.array(image.convert("RGB"))
#     lab = cv2.cvtColor(img, cv2.COLOR_RGB2LAB)
#     l, a, b = cv2.split(lab)
#     clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
#     cl = clahe.apply(l)
#     limg = cv2.merge((cl,a,b))
#     final = cv2.cvtColor(limg, cv2.COLOR_LAB2RGB)
#     return Image.fromarray(final)

# def draw_debug_boxes(image: Image.Image, ocr_result, save_path):
#     img = np.array(image.convert("RGB"))
#     try:
#         data = ocr_result[0]
#         rec_texts = data.get("rec_texts", [])
#         rec_polys = data.get("rec_polys", [])

#         for box, txt in zip(rec_polys, rec_texts):
#             points = np.array(box, np.int32).reshape((-1, 1, 2))
#             cv2.polylines(img, [points], True, (0, 255, 0), 2)
#             x, y = points[0][0]
#             cv2.putText(img, txt, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 
#                         0.5, (0, 0, 255), 1)

#         debug_img = Image.fromarray(img)
#         debug_img.save(save_path)

#     except Exception as e:
#         print(f"[ERROR] ❌ Failed to draw debug boxes: {e}")

# async def process_image_paddleocr(
#     image: Image.Image,
#     filename: str,
#     page_name: Optional[str] = None,
#     base_folder: Optional[str] = None
# ) -> List[dict]:
#     page_name = normalize_page_name(filename)
#     print(f"[DEBUG] Final OCR page_name = '{page_name}' (from filename='{filename}')")

#     # 🗂️ Setup folders
#     image_dir = os.path.join(DATA_PATH, "images")
#     regions_dir = os.path.join(DATA_PATH, "regions")
#     debug_dir = os.path.join(DATA_PATH, "debug")
#     os.makedirs(image_dir, exist_ok=True)
#     os.makedirs(regions_dir, exist_ok=True)
#     os.makedirs(debug_dir, exist_ok=True)

#     # 📷 Preprocess and save image
#     preprocessed = enhance_contrast(image)
#     image_save_path = os.path.join(image_dir, filename)
#     preprocessed.save(image_save_path)

#     # 🔍 Run OCR
#     result = ocr_engine.ocr(image_save_path)
#     print(f"[DEBUG] Raw PaddleOCR result: {result}")

#     if not result or not isinstance(result[0], dict):
#         print(f"[WARN] No OCR results found or unexpected format for {filename}")
#         return []

#     data = result[0]
#     rec_texts = data.get("rec_texts", [])
#     rec_polys = data.get("rec_polys", [])
#     rec_scores = data.get("rec_scores", [])

#     # 🖼️ Save debug image
#     draw_debug_boxes(preprocessed, result, os.path.join(debug_dir, f"debug_{filename}"))

#     results = []

#     for box, text, confidence in zip(rec_polys, rec_texts, rec_scores):
#         if not text.strip():
#             continue

#         print(f"[DEBUG] OCR Detected: '{text}' (confidence: {confidence:.2f})")

#         x_min = int(min([pt[0] for pt in box]))
#         y_min = int(min([pt[1] for pt in box]))
#         x_max = int(max([pt[0] for pt in box]))
#         y_max = int(max([pt[1] for pt in box]))
#         w, h = x_max - x_min, y_max - y_min

#         region_img_path = save_region(image, x_min, y_min, w, h, regions_dir, page_name)
#         unique_id = str(uuid.uuid4())



#         element = {
#             "label_text": text,
#             "ocr_type": "textbox" if confidence > 0.85 and len(text) > 1 else "label",
#             "intent": "",
#             "x": x_min,
#             "y": y_min,
#             "width": w,
#             "height": h,
#             "bbox": f"{x_min},{y_min},{w},{h}",
#             "confidence_score": float(confidence),
#             "intent": intent,
#         }

#         metadata = build_standard_metadata(
#             element=element,
#             page_name=page_name,
#             image_path=region_img_path
#         )
#         metadata["id"] = unique_id
#         metadata["ocr_id"] = unique_id
#         metadata["get_by_text"] = text

#         try:
#             upsert_text_record(metadata)
#             results.append(metadata)
#             print(f"[DEBUG] ✅ Inserted: '{text}' at {metadata['bbox']}")
#         except Exception as e:
#             print(f"[ERROR] Failed to insert OCR metadata: {e}")

#     if not results:
#         print(f"[DEBUG] ⚠️ OCR succeeded but no metadata inserted for {filename}")

#     return results





# ===================================  GPT OCR =============================================

import pytesseract
from PIL import Image
import uuid
from utils.file_utils import save_region
from services.chroma_service import upsert_text_record
from config.settings import DATA_PATH
from typing import List, Optional
import os
from utils.match_utils import normalize_page_name

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

def sanitize_metadata(record: dict) -> dict:
    return {k: (str(v) if v is not None and not isinstance(v, (dict, list)) else "" if v is None else str(v)) for k, v in record.items()}

async def process_image(image: Image.Image, filename: str, page_name: Optional[str] = None, base_folder: Optional[str] = None) -> List[dict]:
    """
    Patched function to enforce same page_name as locators!
    Now explicitly accepts `page_name`, fallback to filename if not provided.
    """
    page_name = normalize_page_name(filename)  

    # if page_name is None:
    #     page_name = os.path.splitext(os.path.basename(filename))[0]
    
    # ✅ normalize page_name to match locator naming convention
    # if not page_name.startswith("www_"):
    #     page_name = f"www_{page_name}"

    # print(f"[DEBUG] Final OCR page_name = '{page_name}' (from filename='{filename}')")

    image_dir = os.path.join(DATA_PATH, "images")
    os.makedirs(image_dir, exist_ok=True)
    image_save_path = os.path.join(image_dir, filename)
    image.save(image_save_path)

    regions_dir = os.path.join(DATA_PATH, "regions")
    os.makedirs(regions_dir, exist_ok=True)

    data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
    results = []

    for i in range(len(data['text'])):
        text = data['text'][i].strip()
        if not text:
            continue

        x, y, w, h = data['left'][i], data['top'][i], data['width'][i], data['height'][i]

        region_img_path = save_region(image=image, x=x, y=y, w=w, h=h, output_dir=regions_dir, page_name=page_name, )

        unique_id = str(uuid.uuid4())

        record = {
            "id": unique_id,
            "ocr_id": unique_id,
            "type": "ocr",
            "page_name": page_name,   # ✅ key point → normalized page_name
            "source_type": "image",
            "text": text,
            "placeholder": text,
            "bbox": f"{x},{y},{w},{h}",
            "region_image_path": region_img_path,
            "xpath": "",
            "get_by_text": "",
            "get_by_role": "",
            "intent": "",
            "html_snippet": "",
            "x": x,
            "y": y,
            "width": w,
            "height": h,
            "confidence_score": 1.0,
            "visibility_score": 1.0,
            "locator_stability_score": 1.0,
            "used_in_tests": "[]",
            "last_tested": "",
            "healing_success_rate": 0.0,
            "snapshot_id": "",
            "match_timestamp": ""
        }

        sanitized_record = sanitize_metadata(record)

        try:
            upsert_text_record(sanitized_record)
            results.append(sanitized_record)
            # print(f"[DEBUG] Inserted OCR record for text='{text}', page_name='{page_name}', id='{unique_id}'")
        except Exception as e:
            print(f"⚠️ Skipping {filename} entry {unique_id}: {e}")

    return results


# ############################ Open AI Logic for Image API ############################


from PIL import Image
from openai import OpenAI
import os
import base64
import uuid
from dotenv import load_dotenv
import json
from datetime import datetime

from config.settings import DATA_PATH
from utils.file_utils import save_region, build_standard_metadata
from utils.match_utils import normalize_page_name,assign_intent_semantic
from services.chroma_service import upsert_text_record  

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

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

3. Format:
   - Each element on its own line:
     <label text> - <element type> - <intent>

4. Rules:
   - Do NOT rephrase or skip lines.
   - Preserve punctuation, line breaks.
   - Traverse from top-left to bottom-right.

5. Only output newline-separated lines like:
   Username - textbox - login
   Login - button - login
   secret_sauce - label - password_info
"""

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
        max_tokens=1500
    )

    raw_lines = response.choices[0].message.content.strip().splitlines()
    results = []

    for line in raw_lines:
        line = line.strip()
        if not line or " - " not in line:
            continue

        # Handle both 3-part and 2-part formats
        parts = line.rsplit(" - ", 2)
        if len(parts) == 3:
            label_text, ocr_type, intent = [p.strip() for p in parts]
            if not intent:
                intent = assign_intent_semantic(label_text)
        elif len(parts) == 2:
            label_text, ocr_type = [p.strip() for p in parts]
            intent = assign_intent_semantic(label_text)
        else:
            continue

        unique_id = str(uuid.uuid4())
        x, y, w, h = 10, 10, 100, 40  # Dummy values; plug in YOLO here if needed

        region_path = save_region(
            image, x, y, w, h,
            os.path.join(os.path.dirname(image_path), "regions"), # Use image_path to derive regions path
            page_name,
            image_path=image_path
        )

        element = {
            "label_text": label_text,
            "ocr_type": ocr_type,
            "intent": intent,
            "placeholder": "",
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

        try:
            upsert_text_record(metadata)
        except Exception as e:
            print(f"[ERROR] Failed to upsert to ChromaDB for label='{label_text}': {e}")

        if debug_log_path:
            with open(debug_log_path, "a", encoding="utf-8") as log_file:
                log_file.write(json.dumps(metadata, ensure_ascii=False) + "\n")

        results.append(metadata)

    return results
