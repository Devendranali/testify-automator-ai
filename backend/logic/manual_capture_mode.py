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
import json

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

# # ✅ OLD CODE Extract DOM metadata from page with smart label association
# async def extract_dom_metadata(page: Page, page_name: str) -> List[Dict[str, Any]]:
#     if page.is_closed():
#         print("[❌] Attempted to access a closed page.")
#         return []

#     # 1. Build a mapping from input IDs to label texts (for smart association)
#     label_for_map = {}
#     label_elems = await page.query_selector_all("label[for]")
#     for label in label_elems:
#         label_for = await label.get_attribute("for")
#         label_text = (await label.inner_text()).strip()
#         if label_for and label_text:
#             label_for_map[label_for] = label_text

#     # 2. Collect all interactive fields and other elements except anything in ocrModal
#     elements = await page.locator("body *:not(#ocrModal *):not(#ocrModal)").all()
#     print(f"[DEBUG] Got {len(elements)} locator from dom except ocrModal")

#     output_lines = []
#     data = []
#     output_lines.append(f"All DOM elements")
#     for i, elem in enumerate(elements):
#         try:
#             if await elem.is_visible():
#                 tag = await elem.evaluate("e => e.tagName.toLowerCase()")
#                 text = await elem.evaluate("e => e.textContent") or ""
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

#                 # --- LABEL LOGIC ---
#                 label_text = ""
#                 if elem_id and elem_id in label_for_map:
#                     label_text = label_for_map[elem_id]
#                 elif await elem.get_attribute("aria-label"):
#                     label_text = await elem.get_attribute("aria-label")
#                 elif placeholder:
#                     label_text = placeholder
#                 elif tag in ("button",):
#                     label_text = text.strip()
#                 elif await elem.get_attribute("data-lov-name"):
#                     label_text = await elem.get_attribute("data-lov-name")

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
#                     f"  label_text:     {label_text or ''}",
#                     f"  HTML:           {outer_html[:120]}{'...' if outer_html and len(outer_html) > 120 else ''}",
#                     "-" * 60
#                 ]
#                 output_lines.extend(element_lines)

#                 # If none of these fields, skip
#                 if not (tag or text or placeholder or value):
#                     continue
#                 data.append({
#                     "page_name": page_name or "",
#                     "tag_name": tag or "",
#                     "text": text.strip() or "",
#                     "class": elem_class or "",
#                     "value": value or "",
#                     "placeholder": placeholder or "",
#                     "type": input_type or "",
#                     "enable": enable,        # bool (True/False) is fine!
#                     "visible": visible,      # bool (True/False) is fine!
#                     "editable": editable,    # bool (True/False) is fine!
#                     "label_text": label_text or "",
#                     "id": elem_id or "",
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

# # ✅ NEW CODE Extract DOM metadata from page with smart label association
async def extract_dom_metadata(page: Page, page_name: str) -> list:
    """
    Extracts DOM metadata for all elements except those inside #ocrModal,
    using a single, fast JS evaluation. The return format matches your existing logic.
    """
    elements_data = await page.evaluate("""
    (pageName) => {
        // Query all elements except those inside #ocrModal
        const nodes = Array.from(document.querySelectorAll('body *:not(#ocrModal *):not(#ocrModal)'));
        return nodes.map((e, i) => {
            // Bounding box
            let bbox = {x: '', y: '', width: '', height: ''};
            try {
                const b = e.getBoundingClientRect();
                bbox = {x: b.x, y: b.y, width: b.width, height: b.height};
            } catch {}
            // Attributes dict
            const attrs = {};
            for (const attr of e.attributes) {
                attrs[attr.name] = attr.value;
            }
            // Label logic
            let label = '';
            if (e.id) {
                const labelElem = document.querySelector(`label[for="${e.id}"]`);
                if (labelElem) label = labelElem.innerText.trim();
            }
            if (!label && e.getAttribute('aria-label')) label = e.getAttribute('aria-label');
            if (!label && e.placeholder) label = e.placeholder;
            if (!label && e.tagName.toLowerCase() === "button") label = e.textContent.trim();
            if (!label && e.getAttribute('data-lov-name')) label = e.getAttribute('data-lov-name');
            // Editable
            let editable = false;
            const tn = e.tagName.toLowerCase();
            if (["input", "textarea", "select"].includes(tn)) {
                editable = !e.readOnly && !e.disabled;
            } else if (e.getAttribute('contenteditable') === "true") {
                editable = true;
            }
            // Visible
            let visible = !!(e.offsetWidth || e.offsetHeight || e.getClientRects().length);
            // Enabled
            let enable = !e.disabled;

            return {
                page_name: pageName || "",
                tag_name: tn,
                text: (e.textContent || "").trim(),
                class: e.className || "",
                id: e.id || "",
                value: (typeof e.value === "string" ? e.value : "") || "",
                placeholder: e.placeholder || "",
                type: e.type || "",
                enable: enable,
                visible: visible,
                editable: editable,
                label_text: label || "",
                x: bbox.x,
                y: bbox.y,
                width: bbox.width,
                height: bbox.height,
                attributes: attrs,
                outer_html: (e.outerHTML || "").slice(0, 120)
            };
        });
    }
    """, page_name)

    # No further async calls needed! You can filter/process in Python if needed.
    print(f"[DEBUG] Got {len(elements_data)} locator from dom except ocrModal")

    output_lines = []
    output_lines.append(f"All DOM elements")
    for i, elem in enumerate(elements_data):
        element_lines = [
            f"Element {i+1}:",
            f"  page_name:      {elem.get('page_name', '')}",
            f"  tag_name:       {elem.get('tag_name', '')}",
            f"  text:           {elem.get('text', '')}",
            f"  id:             {elem.get('id', '')}",
            f"  class:          {elem.get('class', '')}",
            f"  value:          {elem.get('value', '')}",
            f"  placeholder:    {elem.get('placeholder', '')}",
            f"  type:           {elem.get('type', '')}",
            f"  attributes:     {elem.get('attributes', '')}",
            f"  enable?         {elem.get('enable', '')}",
            f"  visible?        {elem.get('visible', '')}",
            f"  editable?       {elem.get('editable', '')}",
            f"  label_text:     {elem.get('label_text', '')}",
            f"  HTML:           {elem.get('outer_html', '')}{'...' if elem.get('outer_html') and len(elem.get('outer_html')) > 120 else ''}",
            "-" * 60
        ]
        output_lines.extend(element_lines)

    # Write all info to a file (exactly as before)
    from pathlib import Path
    debug_metadata_dir = Path("generated_runs") / "src" / "ocr-dom-metadata"
    debug_metadata_dir.mkdir(parents=True, exist_ok=True)
    out_file = debug_metadata_dir / f"dom_elements_{page_name}.txt"
    with open(out_file, "w", encoding="utf-8") as f:
        f.write("\n".join(output_lines))

    print(f"[INFO] DOM extracted element data saved to {out_file}")
    print("[DEBUG] DOM DATA Length: ", len(elements_data))

    return elements_data

def build_ocr_context_string(ocr):
    fields = [
        ocr.get("label_text", ""),
        ocr.get("placeholder", ""),
        ocr.get("intent", ""),
        ocr.get("ocr_type", ""),
        ocr.get("role", ""),
        ocr.get("aria_label", ""),
        ocr.get("page_name", ""),
        ocr.get("unique_name", ""),
    ]
    return " ".join([str(f) for f in fields if f]).strip().lower()

def build_dom_context_string(dom):
    fields = [
        dom.get("label_text", ""),
        dom.get("placeholder", ""),
        dom.get("text", ""),
        dom.get("value", ""),
        dom.get("tag_name", ""),
        dom.get("title", ""),
        dom.get("id", "") or dom.get("dom-id", ""),
        dom.get("class", "") or dom.get("dom_class", ""),
        dom.get("ocr_type", ""),
        dom.get("intent", ""),
        dom.get("role", ""),
        dom.get("aria_label", ""),
        dom.get("page_name", ""),
        dom.get("unique_name", ""),
    ]
    return " ".join([str(f) for f in fields if f]).strip().lower()


def clean_metadata(d):
    # Recursively clean all dict/list/set values in the dict d
    for k, v in list(d.items()):
        if isinstance(v, (dict, list, set)):
            # Convert dict/list/set (even empty) to string
            d[k] = json.dumps(v)
        elif not isinstance(v, (str, int, float, bool)) and v is not None:
            d[k] = str(v)
    return d


# New Optimized match_and_update
def match_and_update(ocr_data, dom_data, collection, text_thresh=0.5, bbox_thresh=300):
    global LAST_MATCHED_RESULTS
    matched_records = []

    print(f"[DEBUG] Matching {len(ocr_data)} OCRs with {len(dom_data)} DOMs")

    # --- Precompute DOM text features and embeddings for text-based matching ---
    dom_texts = []
    dom_candidates = []
    for dom in dom_data:
        dom_text = dom.get("label_text", "") or dom.get(
            "text", "") or dom.get("placeholder", "") or dom.get("value", "")
        dom_texts.append(dom_text.lower())
        # dom_text = build_dom_context_string(dom)
        # dom_texts.append(dom_text)

        dom_candidates.append(dom)
    if dom_texts:
        dom_embeddings = text_model.encode(dom_texts, show_progress_bar=False)
    else:
        dom_embeddings = []

    for ocr in ocr_data:
        if not ocr.get("external"):
            # ---- If label_text exists: optimized vectorized similarity search ----
            if ocr.get("label_text"):
                ocr_label = ocr["label_text"].lower()
                ocr_embedding = text_model.encode([ocr_label])[0]
                # ocr_context = build_ocr_context_string(ocr)
                # ocr_embedding = text_model.encode([ocr_context])[0]

                if len(dom_embeddings) > 0:  # <-- FIXED ambiguous check
                    sims = cosine_similarity(
                        [ocr_embedding], dom_embeddings)[0]
                    best_idx = int(np.argmax(sims))
                    best_score = float(sims[best_idx])
                    if best_score >= text_thresh:
                        best_match = dom_candidates[best_idx]
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
                        # PATCH: Ensure attributes is a string
                        # ... Inside your match/update logic, before collection.upsert:
                        updated = clean_metadata(updated)
                        collection.upsert(
                            ids=[updated.get("element_id")],
                            documents=[updated["label_text"]],
                            metadatas=[updated],
                        )
                        matched_records.append(updated)

            # ---- If label_text not exists: fallback using ocr_type + intent (no change) ----
            elif not ocr.get("label_text"):
                ocr_type = ocr.get("ocr_type", "").lower()
                intent = ocr.get("intent", "").lower()
                best_match = None
                best_score = 0.0
                for dom in dom_data:
                    dom_tag = (dom.get("tag_name") or "").lower()
                    dom_id = (dom.get("id") or "").lower()
                    dom_class = (dom.get("class") or "").lower()
                    dom_label = (dom.get("label_text") or "").strip()
                    if dom_label:
                        continue
                    # Match ocr_type to allowed tag names
                    if ocr_type == "textbox" and dom_tag in ("input", "textarea", "text"):
                        score = 0
                        if intent and (intent in dom_id or intent in dom_class):
                            score = 1.0
                        elif intent.split('_')[0] in dom_id or intent.split('_')[0] in dom_class:
                            score = 0.8
                        if score > best_score:
                            best_score = score
                            best_match = dom
                    # Add more type-intent/tag logic here as needed!
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
                    # PATCH: Ensure attributes is a string
                    # ... Inside your match/update logic, before collection.upsert:
                    updated = clean_metadata(updated)
                    collection.upsert(
                        ids=[updated.get("element_id")],
                        documents=[updated["label_text"]],
                        metadatas=[updated],
                    )
                    matched_records.append(updated)

    LAST_MATCHED_RESULTS = matched_records
    print(f"[✅] Matched {len(matched_records)} elements.")
    return matched_records


# Old code
# def match_and_update(ocr_data, dom_data, collection, text_thresh=0.5, bbox_thresh=300):
#     global LAST_MATCHED_RESULTS
#     matched_records = []

#     print(f"[DEBUG] Matching {len(ocr_data)} OCRs with {len(dom_data)} DOMs")

#     for ocr in ocr_data:
#         if not ocr.get("external"):
            
#             # If label_text exists
#             if ocr.get("label_text"):
#                 best_match = None
#                 best_score = 0.0

#                 for dom in dom_data:            
#                     dom_text = dom.get("label_text", "") or dom.get("text", "") or dom.get("placeholder", "") or dom.get("value")
#                     if not dom_text:
#                         continue

#                     sim = text_similarity(ocr["label_text"].lower(), dom_text.lower())

#                     if sim >= text_thresh and sim > best_score:
#                         best_match = dom
#                         best_score = sim                

#                 if best_match:
#                     updated = ocr.copy()
#                     updated.update({
#                         "tag_name": best_match.get("tag_name", ""),
#                         "label_text": best_match.get("label_text") or best_match.get("text") or best_match.get("placeholder") or best_match.get("value") or "",
#                         "dom-id": best_match.get("id", ""),
#                         "dom_class": best_match.get("class", ""),
#                         "value": best_match.get("value", ""),
#                         "placeholder": best_match.get("placeholder", ""),
#                         "type": best_match.get("type", ""),
#                         "enable": best_match.get("enable", ""),
#                         "visible": best_match.get("visible", ""),
#                         "editable": best_match.get("editable", ""),
#                         "x": best_match.get("x", ""),
#                         "y": best_match.get("y", ""),
#                         "width": best_match.get("width", ""),
#                         "height": best_match.get("height", ""),
#                         "dom_matched": True,
#                         "match_timestamp": datetime.utcnow().isoformat()
#                     })
#                     # Use label_text with best fallback
#                     updated["label_text"] = (
#                         (best_match.get("label_text") or "").strip() or
#                         (best_match.get("text") or "").strip() or
#                         (best_match.get("placeholder") or "").strip() or
#                         (best_match.get("value") or "").strip() or
#                         ""
#                     )

#                     collection.upsert(
#                         ids=[updated["element_id"]],
#                         documents=[updated["label_text"]],
#                         metadatas=[updated],
#                     )
#                     matched_records.append(updated)

#             # If label_text not exists
#             elif not ocr.get("label_text"):
#                 # --- Fallback using ocr_type + intent ---
#                 ocr_type = ocr.get("ocr_type", "").lower()
#                 intent = ocr.get("intent", "").lower()

#                 best_match = None
#                 best_score = 0.0

#                 for dom in dom_data:
#                     dom_tag = (dom.get("tag_name") or "").lower()
#                     dom_id = (dom.get("id") or "").lower()
#                     dom_class = (dom.get("class") or "").lower()
#                     dom_label = (dom.get("label_text") or "").strip()

#                     # Only consider DOM elements without label_text (unlabeled fields)
#                     if dom_label:
#                         continue

#                     # Match ocr_type to allowed tag names
#                     if ocr_type == "textbox" and dom_tag in ("input", "textarea", "text"):
#                         score = 0
#                         # Simple semantic: intent in dom_id/class
#                         if intent and (intent in dom_id or intent in dom_class):
#                             score = 1.0
#                         elif intent.split('_')[0] in dom_id or intent.split('_')[0] in dom_class:
#                             score = 0.8
#                         # You can add more heuristics (partial match, synonyms, etc.)
#                         if score > best_score:
#                             best_score = score
#                             best_match = dom
#                     # (Repeat similar mapping logic for buttons, selects, etc.)
#                 if best_match:
#                     updated = ocr.copy()
#                     updated.update({
#                         "tag_name": best_match.get("tag_name", ""),
#                         "label_text": best_match.get("label_text") or best_match.get("text") or best_match.get("placeholder") or best_match.get("value") or "",
#                         "dom-id": best_match.get("id", ""),
#                         "dom_class": best_match.get("class", ""),
#                         "value": best_match.get("value", ""),
#                         "placeholder": best_match.get("placeholder", ""),
#                         "type": best_match.get("type", ""),
#                         "enable": best_match.get("enable", ""),
#                         "visible": best_match.get("visible", ""),
#                         "editable": best_match.get("editable", ""),
#                         "x": best_match.get("x", ""),
#                         "y": best_match.get("y", ""),
#                         "width": best_match.get("width", ""),
#                         "height": best_match.get("height", ""),
#                         "dom_matched": True,
#                         "match_timestamp": datetime.utcnow().isoformat()
#                     })
#                     # Use label_text with best fallback
#                     updated["label_text"] = (
#                         (best_match.get("label_text") or "").strip() or
#                         (best_match.get("text") or "").strip() or
#                         (best_match.get("placeholder") or "").strip() or
#                         (best_match.get("value") or "").strip() or
#                         ""
#                     )

#                     collection.upsert(
#                         ids=[updated["element_id"]],
#                         documents=[updated["label_text"]],
#                         metadatas=[updated],
#                     )
#                     matched_records.append(updated)

#     LAST_MATCHED_RESULTS = matched_records
#     print(f"[✅] Matched {len(matched_records)} elements.")
#     return matched_records




