# manual_capture_mode.py

# from chromadb import PersistentClient
# from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
# from sentence_transformers import SentenceTransformer
# from sklearn.metrics.pairwise import cosine_similarity
# import numpy as np
# from typing import List, Dict, Any
# from datetime import datetime
# from playwright.async_api import Page
# from utils.file_utils import build_standard_metadata
 
 
 
# # 🔧 Embedding setup
# embedding_fn = SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
# text_model = SentenceTransformer("all-MiniLM-L6-v2")
 
# # 🔧 Persistent ChromaDB
# client = PersistentClient(path="./data/chroma_db")
# collection = client.get_or_create_collection(
#     name="element_metadata",
#     embedding_function=embedding_fn
# )
 
# # 🧠 Memory store
# CURRENT_PAGE_NAME = None
# LAST_MATCHED_RESULTS = []
 
# def set_page_name(name: str):
#     global CURRENT_PAGE_NAME
#     CURRENT_PAGE_NAME = name
#     print(f"✅ Page name set to: {CURRENT_PAGE_NAME}")
 
# def get_page_name() -> str:
#     return CURRENT_PAGE_NAME
 
# def set_last_match_result(data):
#     global LAST_MATCHED_RESULTS
#     LAST_MATCHED_RESULTS = data
 
# def get_last_match_result():
#     return LAST_MATCHED_RESULTS
 
# # ✅ Normalize bbox input
# def bbox_distance(b1, b2) -> float:
#     if isinstance(b1, str):
#         try:
#             x, y, w, h = map(int, b1.split(','))
#             b1 = {"x": x, "y": y, "width": w, "height": h}
#         except Exception as e:
#             print(f"[❌] Invalid bbox string: {b1} — Error: {e}")
#             return float('inf')
#     return np.sqrt((b1['x'] - b2['x'])**2 + (b1['y'] - b2['y'])**2)
 
# # ✅ Text similarity
# def text_similarity(t1: str, t2: str) -> float:
#     vecs = text_model.encode([t1, t2], show_progress_bar=False)
#     return float(cosine_similarity([vecs[0]], [vecs[1]])[0][0])
 
# # ✅ Extract DOM metadata from page
# async def extract_dom_metadata(page: Page, page_name: str) -> List[Dict[str, Any]]:
#     if page.is_closed():
#         print("[❌] Attempted to access a closed page.")
#         return []

#     # elements = await page.locator("body *").all()
#     # This selector matches all elements under <body> EXCEPT anything inside #ocrModal
#     elements = await page.locator("body *:not(#ocrModal *):not(#ocrModal)").all()

#     print(f"[DEBUG] Got {len(elements)} locator from dom except ocrModal")
    
#     output_lines = []
#     data = []
#     output_lines.append(f"All DOM elements")
#     for i, elem in enumerate(elements):
#         try:
#             if await elem.is_visible():            
#                 tag = await elem.evaluate("e => e.tagName.toLowerCase()")
#                 text = await elem.evaluate("e => e.textContent.toLowerCase()")
#                 elem_id = await elem.get_attribute("id")
#                 elem_class = await elem.get_attribute("class")
#                 placeholder = await elem.get_attribute("placeholder")
#                 input_type = await elem.get_attribute("type") if tag and tag.lower() == "input" else ""
#                 attrs = await elem.evaluate("e => { let a = {}; for (let attr of e.attributes) { a[attr.name] = attr.value; } return a; }")
#                 value = attrs.get('value', "")
#                 outer_html = await elem.evaluate("e => e.outerHTML")
#                 visible = await elem.is_visible()
#                 enable = await elem.is_enabled()

#                 editable = False
#                 if tag and tag.lower() in ("input", "textarea", "select"):
#                     editable = await elem.is_editable()
#                 else:
#                     contenteditable = await elem.get_attribute("contenteditable")
#                     if contenteditable == "true":
#                         editable = await elem.is_editable()
#                 bounding_box = await elem.bounding_box()

#                 element_lines = [
#                     f"Element {i+1}:",
#                     f"  page_name:      {page_name}",
#                     f"  tag_name:       {tag or ''}",
#                     f"  text:           {text.strip() if text else ''}",
#                     f"  id:             {elem_id or ''}",
#                     f"  class:          {elem_class or ''}",
#                     f"  value:          {value or ''}",
#                     f"  placeholder:    {placeholder or ''}",
#                     f"  type:           {input_type or ''}",
#                     f"  attributes:     {attrs or ''}",
#                     f"  enable?         {enable or ''}",
#                     f"  visible?        {visible or ''}",
#                     f"  editable?       {editable or ''}",
#                     f"  HTML:           {outer_html[:120]}{'...' if outer_html and len(outer_html) > 120 else ''}",
#                     "-" * 60
#                 ]
#                 output_lines.extend(element_lines)

#                 # If any of these fields are present, append the data
#                 if not (tag or text or placeholder or value):
#                     continue
#                 data.append({
#                     "page_name": page_name or "",
#                     "tag_name": tag or "",
#                     "text": text or "",
#                     "class": elem_class or "",
#                     "value": value or "",
#                     "placeholder": placeholder or "",
#                     "type": input_type or "",
#                     "enable": enable,        # bool (True/False) is fine!
#                     "visible": visible,      # bool (True/False) is fine!
#                     "editable": editable,    # bool (True/False) is fine!
#                     "x": bounding_box["x"] if bounding_box and bounding_box.get("x") is not None else "",
#                     "y": bounding_box["y"] if bounding_box and bounding_box.get("y") is not None else "",
#                     "width": bounding_box["width"] if bounding_box and bounding_box.get("width") is not None else "",
#                     "height": bounding_box["height"] if bounding_box and bounding_box.get("height") is not None else "",
#                 })

#         except Exception as e:
#             print(f"[⚠️] Skipping element {i+1} due to error: {e}")
#             output_lines.append(f"[⚠️] Skipping element {i+1} due to error: {e}")
#             continue

#     # Write all info to a file
#     from pathlib import Path
#     debug_metadata_dir = Path("generated_runs") / "src" / "ocr-dom-metadata"
#     debug_metadata_dir.mkdir(parents=True, exist_ok=True)
#     out_file = debug_metadata_dir / f"dom_elements_{page_name}.txt"
#     with open(out_file, "w", encoding="utf-8") as f:
#         f.write("\n".join(output_lines))
        
#     print(f"[INFO] DOM extracted element data saved to {out_file}")    
#     print("[DEBUG] DOM DATA Length: ", len(data))

#     return data


# def match_and_update(ocr_data, dom_data, collection, text_thresh=0.5, bbox_thresh=300):
#     global LAST_MATCHED_RESULTS
#     matched_records = []

#     print(f"[DEBUG] Matching {len(ocr_data)} OCRs with {len(dom_data)} DOMs")

#     for ocr in ocr_data:
#         if not ocr.get("external"):
#             if not ocr.get("label_text") or not ocr.get("bbox"):
#                 print(f"[SKIP] OCR missing label_text or bbox: {ocr}")
#                 continue

#             best_match = None
#             best_score = 0.0

#             for dom in dom_data:            
#                 dom_text = dom.get("text", "") or dom.get("placeholder", "") or dom.get("value")
#                 if not dom_text:
#                     continue

#                 sim = text_similarity(ocr["text"].lower(), dom_text.lower())

#                 if sim >= text_thresh and sim > best_score:
#                     best_match = dom
#                     best_score = sim                

#             if best_match:
#                 updated = ocr.copy()
#                 updated.update({
#                     "tag_name": best_match.get("tag_name", ""),
#                     "label_text": best_match.get("text") or best_match.get("placeholder") or best_match.get("value") or "",
#                     "dom-id": best_match.get("id", ""),
#                     "dom_class": best_match.get("class", ""),
#                     "value": best_match.get("value", ""),
#                     "placeholder": best_match.get("placeholder", ""),
#                     "type": best_match.get("type", ""),
#                     # "attributes": best_match.get("attributes", ""),
#                     "enable": best_match.get("enable", ""),
#                     "visible": best_match.get("visible", ""),
#                     "editable": best_match.get("editable", ""),
                    
#                     "x": best_match.get("x", ""),
#                     "y": best_match.get("y", ""),
#                     "width": best_match.get("width", ""),
#                     "height": best_match.get("height", ""),
#                     "dom_matched": True,
#                     "match_timestamp": datetime.utcnow().isoformat()
#                 })
#                 # Set label_text with your preferred fallback order
#                 updated["label_text"] = (
#                     (best_match.get("text")).strip() or
#                     (best_match.get("placeholder")).strip() or
#                     (best_match.get("value")).strip() or
#                     ""
#                 )

#                 collection.upsert(
#                     ids=[updated["id"]],
#                     documents=[updated["label_text"]],
#                     metadatas=[updated],
#                 )
#                 matched_records.append(updated)

#     LAST_MATCHED_RESULTS = matched_records
#     print(f"[✅] Matched {len(matched_records)} elements.")
#     return matched_records

# ==================================== NEW CODE =============================

# manual_capture_mode.py

from chromadb import PersistentClient
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from typing import List, Dict, Any
from datetime import datetime
from playwright.async_api import Page
from utils.file_utils import build_standard_metadata

# 🔧 Embedding setup
embedding_fn = SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
text_model = SentenceTransformer("all-MiniLM-L6-v2")

# 🔧 Persistent ChromaDB
client = PersistentClient(path="./data/chroma_db")
collection = client.get_or_create_collection(
    name="element_metadata",
    embedding_function=embedding_fn
)

# 🧠 Memory store
CURRENT_PAGE_NAME = None
LAST_MATCHED_RESULTS = []

def set_page_name(name: str):
    global CURRENT_PAGE_NAME
    CURRENT_PAGE_NAME = name
    print(f"✅ Page name set to: {CURRENT_PAGE_NAME}")

def get_page_name() -> str:
    return CURRENT_PAGE_NAME

def set_last_match_result(data):
    global LAST_MATCHED_RESULTS
    LAST_MATCHED_RESULTS = data

def get_last_match_result():
    return LAST_MATCHED_RESULTS

# ✅ Normalize bbox input
def bbox_distance(b1, b2) -> float:
    if isinstance(b1, str):
        try:
            x, y, w, h = map(int, b1.split(','))
            b1 = {"x": x, "y": y, "width": w, "height": h}
        except Exception as e:
            print(f"[❌] Invalid bbox string: {b1} — Error: {e}")
            return float('inf')
    return np.sqrt((b1['x'] - b2['x'])**2 + (b1['y'] - b2['y'])**2)

# ✅ Text similarity
def text_similarity(t1: str, t2: str) -> float:
    vecs = text_model.encode([t1, t2], show_progress_bar=False)
    return float(cosine_similarity([vecs[0]], [vecs[1]])[0][0])

# ✅ Extract DOM metadata from page with smart label association
async def extract_dom_metadata(page: Page, page_name: str) -> List[Dict[str, Any]]:
    if page.is_closed():
        print("[❌] Attempted to access a closed page.")
        return []

    # 1. Build a mapping from input IDs to label texts (for smart association)
    label_for_map = {}
    label_elems = await page.query_selector_all("label[for]")
    for label in label_elems:
        label_for = await label.get_attribute("for")
        label_text = (await label.inner_text()).strip()
        if label_for and label_text:
            label_for_map[label_for] = label_text

    # 2. Collect all interactive fields and other elements except anything in ocrModal
    elements = await page.locator("body *:not(#ocrModal *):not(#ocrModal)").all()
    print(f"[DEBUG] Got {len(elements)} locator from dom except ocrModal")

    output_lines = []
    data = []
    output_lines.append(f"All DOM elements")
    for i, elem in enumerate(elements):
        try:
            if await elem.is_visible():
                tag = await elem.evaluate("e => e.tagName.toLowerCase()")
                text = await elem.evaluate("e => e.textContent") or ""
                elem_id = await elem.get_attribute("id")
                elem_class = await elem.get_attribute("class")
                placeholder = await elem.get_attribute("placeholder")
                input_type = await elem.get_attribute("type") if tag and tag.lower() == "input" else ""
                attrs = await elem.evaluate("e => { let a = {}; for (let attr of e.attributes) { a[attr.name] = attr.value; } return a; }")
                value = attrs.get('value', "")
                outer_html = await elem.evaluate("e => e.outerHTML")
                visible = await elem.is_visible()
                enable = await elem.is_enabled()

                editable = False
                if tag and tag.lower() in ("input", "textarea", "select"):
                    editable = await elem.is_editable()
                else:
                    contenteditable = await elem.get_attribute("contenteditable")
                    if contenteditable == "true":
                        editable = await elem.is_editable()
                bounding_box = await elem.bounding_box()

                # --- LABEL LOGIC ---
                label_text = ""
                if elem_id and elem_id in label_for_map:
                    label_text = label_for_map[elem_id]
                elif await elem.get_attribute("aria-label"):
                    label_text = await elem.get_attribute("aria-label")
                elif placeholder:
                    label_text = placeholder
                elif tag in ("button",):
                    label_text = text.strip()
                elif await elem.get_attribute("data-lov-name"):
                    label_text = await elem.get_attribute("data-lov-name")

                element_lines = [
                    f"Element {i+1}:",
                    f"  page_name:      {page_name}",
                    f"  tag_name:       {tag or ''}",
                    f"  text:           {text.strip() if text else ''}",
                    f"  id:             {elem_id or ''}",
                    f"  class:          {elem_class or ''}",
                    f"  value:          {value or ''}",
                    f"  placeholder:    {placeholder or ''}",
                    f"  type:           {input_type or ''}",
                    f"  attributes:     {attrs or ''}",
                    f"  enable?         {enable or ''}",
                    f"  visible?        {visible or ''}",
                    f"  editable?       {editable or ''}",
                    f"  label_text:     {label_text or ''}",
                    f"  HTML:           {outer_html[:120]}{'...' if outer_html and len(outer_html) > 120 else ''}",
                    "-" * 60
                ]
                output_lines.extend(element_lines)

                # If none of these fields, skip
                if not (tag or text or placeholder or value):
                    continue
                data.append({
                    "page_name": page_name or "",
                    "tag_name": tag or "",
                    "text": text.strip() or "",
                    "class": elem_class or "",
                    "value": value or "",
                    "placeholder": placeholder or "",
                    "type": input_type or "",
                    "enable": enable,        # bool (True/False) is fine!
                    "visible": visible,      # bool (True/False) is fine!
                    "editable": editable,    # bool (True/False) is fine!
                    "label_text": label_text or "",
                    "id": elem_id or "",
                    "x": bounding_box["x"] if bounding_box and bounding_box.get("x") is not None else "",
                    "y": bounding_box["y"] if bounding_box and bounding_box.get("y") is not None else "",
                    "width": bounding_box["width"] if bounding_box and bounding_box.get("width") is not None else "",
                    "height": bounding_box["height"] if bounding_box and bounding_box.get("height") is not None else "",
                })

        except Exception as e:
            print(f"[⚠️] Skipping element {i+1} due to error: {e}")
            output_lines.append(f"[⚠️] Skipping element {i+1} due to error: {e}")
            continue

    # Write all info to a file
    from pathlib import Path
    debug_metadata_dir = Path("generated_runs") / "src" / "ocr-dom-metadata"
    debug_metadata_dir.mkdir(parents=True, exist_ok=True)
    out_file = debug_metadata_dir / f"dom_elements_{page_name}.txt"
    with open(out_file, "w", encoding="utf-8") as f:
        f.write("\n".join(output_lines))
        
    print(f"[INFO] DOM extracted element data saved to {out_file}")    
    print("[DEBUG] DOM DATA Length: ", len(data))

    return data

def match_and_update(ocr_data, dom_data, collection, text_thresh=0.5, bbox_thresh=300):
    global LAST_MATCHED_RESULTS
    matched_records = []

    print(f"[DEBUG] Matching {len(ocr_data)} OCRs with {len(dom_data)} DOMs")

    for ocr in ocr_data:
        if not ocr.get("external"):
            if not ocr.get("label_text") or not ocr.get("bbox"):
                print(f"[SKIP] OCR missing label_text or bbox: {ocr}")
                continue

            best_match = None
            best_score = 0.0

            for dom in dom_data:            
                dom_text = dom.get("label_text", "") or dom.get("text", "") or dom.get("placeholder", "") or dom.get("value")
                if not dom_text:
                    continue

                sim = text_similarity(ocr["text"].lower(), dom_text.lower())

                if sim >= text_thresh and sim > best_score:
                    best_match = dom
                    best_score = sim                

            if best_match:
                updated = ocr.copy()
                updated.update({
                    "tag_name": best_match.get("tag_name", ""),
                    "label_text": best_match.get("label_text") or best_match.get("text") or best_match.get("placeholder") or best_match.get("value") or "",
                    "dom-id": best_match.get("id", ""),
                    "dom_class": best_match.get("class", ""),
                    "value": best_match.get("value", ""),
                    "placeholder": best_match.get("placeholder", ""),
                    "type": best_match.get("type", ""),
                    "enable": best_match.get("enable", ""),
                    "visible": best_match.get("visible", ""),
                    "editable": best_match.get("editable", ""),
                    "x": best_match.get("x", ""),
                    "y": best_match.get("y", ""),
                    "width": best_match.get("width", ""),
                    "height": best_match.get("height", ""),
                    "dom_matched": True,
                    "match_timestamp": datetime.utcnow().isoformat()
                })
                # Use label_text with best fallback
                updated["label_text"] = (
                    (best_match.get("label_text") or "").strip() or
                    (best_match.get("text") or "").strip() or
                    (best_match.get("placeholder") or "").strip() or
                    (best_match.get("value") or "").strip() or
                    ""
                )

                collection.upsert(
                    ids=[updated["id"]],
                    documents=[updated["label_text"]],
                    metadatas=[updated],
                )
                matched_records.append(updated)

    LAST_MATCHED_RESULTS = matched_records
    print(f"[✅] Matched {len(matched_records)} elements.")
    return matched_records
