import os
import time
from pathlib import Path
from PIL import Image
from datetime import datetime
from utils.match_utils import assign_intent_semantic
from services.ocr_type_classifier import classify_ocr_type 
from services.yolo_detector import detect_ui_elements_yolo

def save_region(image: Image.Image, x: int, y: int, w: int, h: int, output_dir: str, page_name: str = "page", image_path: str = "") -> str:
    if image_path and os.path.exists(image_path):
        try:
            x, y, w, h = detect_ui_elements_yolo(image_path, (x, y, w, h))
        except Exception as e:
            # print(f"[YOLO FALLBACK] Using default bbox due to: {e}")
            pass

    # ✅ Clamp bounding box to image dimensions
    x = max(0, min(x, image.width - 1))
    y = max(0, min(y, image.height - 1))
    w = max(1, min(w, image.width - x))
    h = max(1, min(h, image.height - y))

    # Generate file name
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
    filename = f"{page_name}_{x}_{y}_{w}_{h}_{timestamp}.png"
    region_path = os.path.join(output_dir, filename)

    # Crop and save
    cropped = image.crop((x, y, x + w, y + h))
    cropped.save(region_path)
    return region_path
    
    
    
def build_standard_metadata(element: dict, page_name: str, image_path: str = "", source_url: str = "") -> dict:
    label_text = element.get("label_text", "")  
    ocr_type = element.get("ocr_type", "")
    intent = element.get("intent", "")
    
    unique_name = generate_unique_name(page_name, label_text, ocr_type, intent)

    return sanitize_metadata({
        "page_name": page_name,
        "label_text": label_text,
        "ocr_type": ocr_type,
        "intent": intent,
        "unique_name":unique_name,
        "external": False,
        "dom_matched": element.get("dom_matched", False), 
        
        "region_image_path": image_path,
        "source_url": source_url,
        "confidence_score": element.get("confidence_score", 1.0),
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
        "bbox": element.get("bbox", f"{element.get('x', 0)},{element.get('y', 0)},{element.get('width', 0)},{element.get('height', 0)}"),
        "position_relation": element.get("position_relation", {}),
        "tag_name": element.get("tag_name", ""),
        "xpath": element.get("xpath", ""),
        "get_by_text": element.get("get_by_text", ""),
        "get_by_role": element.get("get_by_role", ""),
        "html_snippet": element.get("html_snippet", ""),
        "placeholder": element.get("placeholder", ""),   
    })

# def generate_unique_name(page_name: str, intent: str, label_text: str, ocr_type: str) -> str:
#     label = label_text.lower().strip().replace(" ", "_")
#     return f"{page_name}_{intent}_{label}_{ocr_type}"

import hashlib
def generate_unique_name(page_name: str, label_text: str, ocr_type: str, intent: str) -> str:
    # Remove quotes from label_text
    cleaned_label = (label_text or "").replace("'", "").replace('"', "")
    # Lowercase and replace spaces with underscores
    label = cleaned_label.lower().strip().replace(" ", "_")
    # Truncate to 50 chars
    cleaned_label = cleaned_label[:50]
    # Define unique string to hash
    unique_str = f"{page_name}_{label}_{ocr_type}_{intent}"
    # Use SHA256, take the first 8 chars for brevity
    hash_part = hashlib.sha256(unique_str.encode("utf-8")).hexdigest()[:8]    
    # Assemble the final unique name
    if label_text:
        return f"{page_name}_{label}_{ocr_type}_{intent}_{hash_part}"
    else:
        return f"{page_name}_{ocr_type}_{intent}_{hash_part}"



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
                    # print(f"[CLEANUP] Deleted old file: {file}")
                except Exception as e:
                    print(f"[CLEANUP ERROR] Failed to delete {file}: {e}")

