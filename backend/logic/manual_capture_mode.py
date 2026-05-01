from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from typing import List, Dict, Any, Optional
from datetime import datetime
from playwright.async_api import Page
from utils.file_utils import build_standard_metadata
from utils.project_context import current_project_id
from utils.smart_ai_utils import get_smartai_src_dir
from utils.chroma_client import get_collection
from config.settings import get_chroma_path
import json
import traceback

# Embedding setup
embedding_fn = SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2")
text_model = SentenceTransformer("all-MiniLM-L6-v2")


# Persistent ChromaDB
def _collection():
    return get_collection(get_chroma_path(), "element_metadata", embedding_function=embedding_fn)


# Memory store
CURRENT_PAGE_NAME = None
LAST_MATCHED_RESULTS = []


def set_page_name(name: str):
    global CURRENT_PAGE_NAME
    CURRENT_PAGE_NAME = name
    print(f"Page name set to: {CURRENT_PAGE_NAME}")


def get_page_name() -> str:
    return CURRENT_PAGE_NAME


def set_last_match_result(data):
    global LAST_MATCHED_RESULTS
    LAST_MATCHED_RESULTS = data


def get_last_match_result():
    return LAST_MATCHED_RESULTS


# Normalize bbox input
def bbox_distance(b1, b2) -> float:
    if isinstance(b1, str):
        try:
            x, y, w, h = map(int, b1.split(','))
            b1 = {"x": x, "y": y, "width": w, "height": h}
        except Exception as e:
            print(f"[ERROR] Invalid bbox string: {b1} | Error: {e}")
            return float('inf')
    try:
        return np.sqrt((b1['x'] - b2['x'])**2 + (b1['y'] - b2['y'])**2)
    except Exception as e:
        print(f"[ERROR] Error computing bbox_distance: {e} | b1: {b1}, b2: {b2}")
        return float('inf')


# Text similarity
def text_similarity(t1: str, t2: str) -> float:
    try:
        vecs = text_model.encode([t1, t2], show_progress_bar=False)
        return float(cosine_similarity([vecs[0]], [vecs[1]])[0][0])
    except Exception as e:
        print(f"[ERROR] Error in text_similarity: {e} | t1: {t1} | t2: {t2}")
        traceback.print_exc()
        return 0.0


# Extract DOM metadata from page
async def extract_dom_metadata(page: Page, page_name: str) -> list:
    try:
        elements_data = await page.evaluate("""
        (pageName) => {
            const nodes = Array.from(document.querySelectorAll('body *:not(#ocrModal *):not(#ocrModal)'));
            return nodes.map((e, i) => {
                let bbox = {x: '', y: '', width: '', height: ''};
                try {
                    const b = e.getBoundingClientRect();
                    bbox = {x: b.x, y: b.y, width: b.width, height: b.height};
                } catch {}
                const attrs = {};
                for (const attr of e.attributes) {
                    attrs[attr.name] = attr.value;
                }
            const attr = (name) => e.getAttribute ? (e.getAttribute(name) || "") : "";
            const hasAttr = (name) => e.getAttribute && e.getAttribute(name) !== null;
            const cls = (e.className || "").toString().toLowerCase();
            const idText = (id) => {
                if (!id) return "";
                const el = document.getElementById(id);
                if (!el) return "";
                return (el.innerText || el.textContent || "").trim();
            };
            const isMeaningfulClass = (c) => {
                if (!c) return false;
                if (!/[a-z]/i.test(c)) return false;
                if (c.length < 3) return false;
                if (/^(w|h|p|m|mt|mb|ml|mr|pt|pb|pl|pr|px|py|text|bg|border|rounded|flex|grid|items|justify|gap|space|shadow|ring|font|leading|tracking|z|top|left|right|bottom|min|max|col|row)-/.test(c)) return false;
                return true;
            };
            const semanticClass = (() => {
                const parts = cls.split(/\\s+/).filter(Boolean);
                for (const p of parts) {
                    if (isMeaningfulClass(p)) return p;
                }
                return "";
            })();
            const semanticId = (() => {
                if (!e.id) return "";
                const cleaned = e.id.toString().toLowerCase();
                return cleaned;
            })();
            let label = '';
            if (e.id) {
                const labelElem = document.querySelector(`label[for="${e.id}"]`);
                if (labelElem) label = labelElem.innerText.trim();
            }
            if (!label && e.getAttribute('aria-label')) label = e.getAttribute('aria-label');
            if (!label && e.getAttribute('aria-labelledby')) {
                label = e.getAttribute('aria-labelledby').split(/\\s+/).map(idText).join(' ').trim();
            }
            if (!label && e.placeholder) label = e.placeholder;
            if (!label && e.getAttribute('title')) label = e.getAttribute('title');
            if (!label && e.getAttribute('alt')) label = e.getAttribute('alt');
            if (!label && e.tagName.toLowerCase() === "button") label = e.textContent.trim();
            if (!label && e.getAttribute('data-lov-name')) label = e.getAttribute('data-lov-name');
            if (!label) {
                const tn = e.tagName.toLowerCase();
                const role = (e.getAttribute("role") || "").toLowerCase();
                const isImageLike = tn === "img" || tn === "svg" || role === "img";
                if (isImageLike) {
                    const clickable = e.closest("button,a,[role='button'],[onclick]");
                    if (clickable) {
                        label = (clickable.getAttribute("aria-label")
                            || clickable.getAttribute("title")
                            || clickable.getAttribute("alt")
                            || clickable.textContent
                            || "").trim();
                    }
                }
            }
            if (!label) {
                const tn = e.tagName.toLowerCase();
                const role = (e.getAttribute("role") || "").toLowerCase();
                const isImageLike = tn === "img" || tn === "svg" || role === "img";
                const key = `${semanticId} ${cls}`.toLowerCase();
                const isAvatarish = /\\b(avatar|profile|user|account|headshot|photo)\\b/.test(key);
                let isRound = false;
                try {
                    const cs = getComputedStyle(e);
                    const br = cs.borderRadius || "";
                    if (br.includes("%")) {
                        const pct = parseFloat(br);
                        if (!isNaN(pct) && pct >= 45) isRound = true;
                    }
                    if (!isRound) {
                        const val = parseFloat(br);
                        if (!isNaN(val)) {
                            const min = Math.min(e.offsetWidth || 0, e.offsetHeight || 0);
                            if (min && val >= min * 0.45) isRound = true;
                        }
                    }
                } catch {}
                if (isImageLike && (isAvatarish || isRound)) {
                    label = "profile icon";
                }
            }
            let cssSelector = "";
            try {
                const clickable = e.closest("button,a,[role='button'],[onclick]");
                if (clickable && clickable.id) {
                    cssSelector = `#${clickable.id}`;
                } else if (clickable && clickable.className) {
                    const ccls = (clickable.className || "").toString().toLowerCase();
                    const parts = ccls.split(/\\s+/).filter(Boolean);
                    const sc = parts.find(p => isMeaningfulClass(p)) || "";
                    if (sc) {
                        cssSelector = `${(clickable.tagName || "").toLowerCase()}.${sc}`;
                    }
                }
                if (!cssSelector) {
                    if (e.id) {
                        cssSelector = `#${e.id}`;
                    } else if (semanticClass) {
                        cssSelector = `${(e.tagName || "").toLowerCase()}.${semanticClass}`;
                    }
                }
            } catch {}
                let editable = false;
                const tn = e.tagName.toLowerCase();
                if (["input", "textarea", "select"].includes(tn)) {
                    editable = !e.readOnly && !e.disabled;
                } else if (e.getAttribute('contenteditable') === "true") {
                    editable = true;
                }
                let visible = !!(e.offsetWidth || e.offsetHeight || e.getClientRects().length);
                let enable = !e.disabled;
                const isDraggable = (() => {
                    try {
                        if (e.draggable === true || attr("draggable") === "true") return true;
                        if (attr("aria-grabbed") === "true") return true;
                        if (hasAttr("data-rbd-draggable-id") || hasAttr("data-rbd-drag-handle-draggable-id")) return true;
                        if (hasAttr("data-dnd-kit-draggable-id") || hasAttr("data-dnd-kit-drag-handle")) return true;
                        if (cls.includes("draggable") || cls.includes("drag-handle") || cls.includes("drag-item")) return true;
                        const style = window.getComputedStyle(e);
                        if (style && (style.cursor === "grab" || style.cursor === "grabbing" || style.cursor === "move")) return true;
                    } catch {}
                    return false;
                })();
                const isDroppable = (() => {
                    try {
                        if (hasAttr("ondrop") || hasAttr("ondragover") || hasAttr("ondragenter")) return true;
                        if (hasAttr("data-rbd-droppable-id") || hasAttr("data-dropzone") || hasAttr("data-droppable") || hasAttr("data-drop-target")) return true;
                        if (hasAttr("data-dnd-kit-droppable-id") || hasAttr("data-dnd-kit-droppable")) return true;
                        if (cls.includes("dropzone") || cls.includes("droppable") || cls.includes("drop-target")) return true;
                        const role = (e.getAttribute("role") || "").toLowerCase();
                        if (["listbox", "grid", "tree", "table"].includes(role)) return true;
                    } catch {}
                    return false;
                })();
                const clickType = (() => {
                    try {
                        const data = [
                            attr("data-action"),
                            attr("data-click"),
                            attr("data-event"),
                            attr("data-handler"),
                            attr("data-action-type"),
                            attr("contextmenu")
                        ].join(" ").toLowerCase();
                        const hasContext = hasAttr("oncontextmenu") || hasAttr("contextmenu") || /contextmenu|rightclick|right_click/.test(data);
                        const hasDouble = hasAttr("ondblclick") || /dblclick|doubleclick/.test(data);
                        if (hasContext && hasDouble) return "right,double";
                        if (hasContext) return "right";
                        if (hasDouble) return "double";
                    } catch {}
                    return "";
                })();
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
                    aria_label: e.getAttribute && e.getAttribute("aria-label") || "",
                    title_text: e.getAttribute && e.getAttribute("title") || "",
                    alt_text: e.getAttribute && e.getAttribute("alt") || "",
                    role: e.getAttribute && e.getAttribute("role") || "",
                    data_testid: attr("data-testid") || attr("data-test-id") || "",
                    data_qa: attr("data-qa") || "",
                    data_cy: attr("data-cy") || "",
                    data_test: attr("data-test") || "",
                    is_draggable: isDraggable,
                    is_droppable: isDroppable,
                    click_type: clickType,
                    x: bbox.x,
                    y: bbox.y,
                    width: bbox.width,
                    height: bbox.height,
                    attributes: attrs,
                    outer_html: (e.outerHTML || "").slice(0, 120),
                    css_selector: cssSelector
                };
            });
        }
        """, page_name)
    except Exception as e:
        print(f"[ERROR] Failed to extract DOM metadata: {e}")
        traceback.print_exc()
        return []

    print(f"[DEBUG] Got {len(elements_data)} locator from dom except ocrModal")

    try:
        debug_metadata_dir = get_smartai_src_dir() / "ocr-dom-metadata"
        debug_metadata_dir.mkdir(parents=True, exist_ok=True)
        out_file = debug_metadata_dir / f"dom_elements_{page_name}.txt"
        output_lines = ["All DOM elements"]
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
        with open(out_file, "w", encoding="utf-8") as f:
            f.write("\n".join(output_lines))
        print(f"[INFO] DOM extracted element data saved to {out_file}")
        print("[DEBUG] DOM DATA Length: ", len(elements_data))
    except Exception as e:
        print(f"[ERROR] Failed to write DOM debug info: {e}")
        traceback.print_exc()

    return elements_data


def clean_metadata(d):
    # Recursively clean all dict/list/set values in the dict d
    for k, v in list(d.items()):
        if isinstance(v, (dict, list, set)):
            d[k] = json.dumps(v)
        elif not isinstance(v, (str, int, float, bool)) and v is not None:
            d[k] = str(v)
    return d


def _is_meaningful_label(s: str) -> bool:
    if not s:
        return False
    s = str(s).strip()
    if len(s) < 2:
        return False
    return any(c.isalnum() for c in s)


def _token_overlap_ratio(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    import re
    ta = set(re.findall(r"\w+", a.lower()))
    tb = set(re.findall(r"\w+", b.lower()))
    if not ta or not tb:
        return 0.0
    inter = ta.intersection(tb)
    return len(inter) / max(len(ta), 1)


def _choose_label(dom_candidate: str, ocr: dict) -> str:
    """Choose between a DOM-derived label and OCR-derived get_by_text/label_text.
    Heuristics:
      - If DOM label is empty/unmeaningful -> prefer OCR
      - If both present: if token overlap is low and DOM label is long or numeric-heavy -> prefer OCR
      - Otherwise prefer DOM (it's more specific)
    """
    dom_label = (dom_candidate or "").strip()
    ocr_get_by = (ocr.get("get_by_text") or "").strip()
    ocr_label = (ocr.get("label_text") or "").strip()
    ocr_type = (ocr.get("ocr_type") or "").lower()

    # Special-case: for icon buttons prefer DOM label if it exists
    # (aria-label/title/alt are often better than "cart icon" OCR tokens).
    if ocr_type == "iconbutton" and _is_meaningful_label(dom_label):
        return dom_label

    # Special-case: for select inputs prefer the OCR-captured label (what user sees)
    # unless the DOM label exactly matches the OCR text. Selects often have verbose
    # nearby descriptions (e.g. "Customer segments by account type") which should
    # not replace the control label "Account Type".
    if ocr_type == "select" and _is_meaningful_label(ocr_get_by):
        if dom_label.lower() != ocr_get_by.lower():
            return ocr_get_by
    # If OCR captured something meaningful and DOM label is empty/unmeaningful -> prefer OCR
    if _is_meaningful_label(ocr_get_by) and not _is_meaningful_label(dom_label):
        return ocr_get_by

    # If both DOM and OCR suggestions exist, prefer OCR by default unless they strongly agree
    if dom_label and (ocr_get_by or ocr_label):
        ref = ocr_get_by or ocr_label
        overlap = _token_overlap_ratio(dom_label, ref)
        digit_fraction = sum(c.isdigit() for c in dom_label) / max(len(dom_label), 1)

        # If DOM and OCR strongly agree (high token overlap) -> prefer DOM (they match)
        if overlap > 0.6:
            return dom_label

        # If OCR tokens are largely a subset of DOM tokens -> DOM is likely just a superset, prefer DOM
        if _token_overlap_ratio(ref, dom_label) > 0.6:
            return dom_label

        # If DOM looks like a numeric/chart dump (many digits) and overlap is low -> prefer OCR
        if overlap < 0.3 and (len(dom_label) > 40 or digit_fraction > 0.25):
            return ref

        # Otherwise OCR is usually the captured, user-visible label - prefer it
        return ref

    # Fallbacks: prefer OCR captures if available
    if _is_meaningful_label(ocr_get_by):
        return ocr_get_by
    if _is_meaningful_label(ocr_label):
        return ocr_label
    if _is_meaningful_label(dom_label):
        return dom_label

    return dom_label or ocr_get_by or ocr_label


def _slug_token(value: str) -> str:
    import re

    return re.sub(r"_+", "_", re.sub(r"[^\w]+", "_", (value or "").strip().lower())).strip("_")


def _icon_family_from_text(*values: str) -> str:
    mapping = {
        "profile": {"profile", "avatar", "user", "account"},
        "calendar": {"calendar", "date", "datepicker"},
        "clock": {"clock", "time", "timer", "schedule"},
        "menu": {"menu", "dots", "kebab", "ellipsis", "more"},
        "launcher": {"launcher", "apps", "app", "grid", "waffle"},
        "search": {"search", "find", "lookup"},
        "notification": {"notification", "notifications", "bell", "alert"},
        "settings": {"settings", "gear", "cog"},
        "close": {"close", "cancel", "dismiss", "clear"},
    }
    haystack = " ".join(str(value or "").strip().lower() for value in values if str(value or "").strip())
    parts = set(_slug_token(haystack).split("_"))
    for family, aliases in mapping.items():
        if parts.intersection(aliases):
            return family
    return ""


def _clean_context_label(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    text = " ".join(text.split())
    lowered = text.lower()
    if lowered in {"icon", "button", "image", "action", "profile icon"}:
        return ""
    return text


def _derive_icon_context(best_match: dict, ocr: dict, chosen_label: str) -> dict:
    accessible_name = (
        best_match.get("aria_label")
        or best_match.get("title_text")
        or best_match.get("alt_text")
        or best_match.get("label_text")
        or best_match.get("text")
        or ""
    )
    family = _icon_family_from_text(
        chosen_label,
        accessible_name,
        ocr.get("label_text"),
        ocr.get("intent"),
        ocr.get("variant_text"),
    )
    field_context_label = _clean_context_label(
        best_match.get("label_text")
        or best_match.get("placeholder")
        or best_match.get("value")
        or ""
    )
    if field_context_label.lower() == str(chosen_label or "").strip().lower():
        field_context_label = ""
    related_input_label = _clean_context_label(best_match.get("placeholder") or field_context_label)
    container_context = _clean_context_label(
        best_match.get("css_selector")
        or best_match.get("id")
        or best_match.get("role")
        or best_match.get("tag_name")
        or ""
    )
    try:
        position_context = f"x{int(float(best_match.get('x') or 0))}_y{int(float(best_match.get('y') or 0))}"
    except Exception:
        position_context = ""
    disambiguation_parts = [part for part in (field_context_label, family or chosen_label) if part]
    return {
        "icon_family": family,
        "dom_accessible_name": str(accessible_name or "").strip(),
        "field_context_label": field_context_label,
        "related_input_label": related_input_label,
        "container_context": container_context,
        "position_context": position_context,
        "disambiguation_key": _slug_token(" ".join(disambiguation_parts)),
        "icon_source": "ocr+dom",
    }


def _attach_project_id(metadata: dict, project_id: Optional[int]) -> None:
    if project_id is not None:
        metadata["project_id"] = project_id


def match_and_update(ocr_data, dom_data, collection, text_thresh=0.25, bbox_thresh=300):
    global LAST_MATCHED_RESULTS
    matched_records = []
    project_id = current_project_id()

    # Filter for dicts only
    dict_ocr_data = [r for r in ocr_data if isinstance(r, dict)]
    bad_ocr_data = [r for r in ocr_data if not isinstance(r, dict)]
    if bad_ocr_data:
        print(
            f"[WARNING] {len(bad_ocr_data)} OCR records were not dicts and will be skipped. Example: {bad_ocr_data[:1]}")

    print(
        f"[DEBUG] Matching {len(dict_ocr_data)} OCRs with {len(dom_data)} DOMs")
    dom_texts = []
    dom_candidates = []
    for dom in dom_data:
        if not isinstance(dom, dict):
            print(f"[WARNING] Skipping DOM record not a dict: {dom}")
            continue
        dom_text = (
            dom.get("label_text", "")
            or dom.get("text", "")
            or dom.get("aria_label", "")
            or dom.get("title_text", "")
            or dom.get("alt_text", "")
            or dom.get("placeholder", "")
            or dom.get("value", "")
        )
        dom_texts.append(dom_text.lower())
        dom_candidates.append(dom)
    if dom_texts:
        try:
            dom_embeddings = text_model.encode(
                dom_texts, show_progress_bar=False)
        except Exception as e:
            print(f"[ERROR] Failed to embed DOM texts: {e}")
            traceback.print_exc()
            dom_embeddings = []
    else:
        dom_embeddings = []

    for ocr in dict_ocr_data:
        try:
            # If label_text exists: optimized vectorized similarity search
            if ocr.get("label_text"):
                ocr_label = ocr["label_text"].lower()
                try:
                    ocr_embedding = text_model.encode([ocr_label])[0]
                except Exception as e:
                    print(f"[ERROR] Failed to embed OCR label: {ocr_label} | {e}")
                    traceback.print_exc()
                    continue
                if len(dom_embeddings) > 0:
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
                            "aria_label": best_match.get("aria_label", ""),
                            "title_text": best_match.get("title_text") or best_match.get("title") or "",
                            "alt_text": best_match.get("alt_text") or best_match.get("alt") or "",
                            "role": best_match.get("role", ""),
                            "data_testid": best_match.get("data_testid", ""),
                            "data_qa": best_match.get("data_qa", ""),
                            "data_cy": best_match.get("data_cy", ""),
                            "data_test": best_match.get("data_test", ""),
                            "css_selector": best_match.get("css_selector", ""),
                            "is_draggable": best_match.get("is_draggable", False),
                            "is_droppable": best_match.get("is_droppable", False),
                            "click_type": best_match.get("click_type", ""),
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
                        dom_candidate = (
                            best_match.get("label_text")
                            or best_match.get("text")
                            or best_match.get("aria_label")
                            or best_match.get("title_text")
                            or best_match.get("alt_text")
                            or best_match.get("placeholder")
                            or best_match.get("value")
                            or ""
                        )
                        chosen_label = _choose_label(dom_candidate, ocr)
                        updated["label_text"] = chosen_label
                        if (ocr.get("ocr_type") or "").lower() == "iconbutton":
                            ocr_label = (ocr.get("label_text") or "").strip()
                            if _is_meaningful_label(ocr_label) and ocr_label.lower() != chosen_label.lower():
                                updated["variant_text"] = ocr_label
                            updated.update(_derive_icon_context(best_match, ocr, chosen_label))
                        updated = clean_metadata(updated)
                        _attach_project_id(updated, project_id)
                        try:
                            collection.upsert(
                                ids=[updated.get("element_id")],
                                documents=[updated["label_text"]],
                                metadatas=[updated],
                            )
                        except Exception as e:
                            print(
                                f"[ERROR] Failed to upsert updated OCR record: {updated} | {e}")
                            traceback.print_exc()
                        matched_records.append(updated)

            # If label_text not exists: fallback using ocr_type + intent
            elif not ocr.get("label_text"):
                ocr_type = ocr.get("ocr_type", "").lower()
                intent = ocr.get("intent", "").lower()
                best_match = None
                best_score = 0.0
                for dom in dom_candidates:
                    if not isinstance(dom, dict):
                        continue
                    dom_tag = (dom.get("tag_name") or "").lower()
                    dom_id = (dom.get("id") or "").lower()
                    dom_class = (dom.get("class") or "").lower()
                    dom_label = (dom.get("label_text") or "").strip()
                    if dom_label:
                        continue
                    if ocr_type == "textbox" and dom_tag in ("input", "textarea", "text"):
                        score = 0
                        if intent and (intent in dom_id or intent in dom_class):
                            score = 1.0
                        elif intent.split('_')[0] in dom_id or intent.split('_')[0] in dom_class:
                            score = 0.8
                        if score > best_score:
                            best_score = score
                            best_match = dom
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
                        "aria_label": best_match.get("aria_label", ""),
                        "title_text": best_match.get("title_text") or best_match.get("title") or "",
                        "alt_text": best_match.get("alt_text") or best_match.get("alt") or "",
                        "role": best_match.get("role", ""),
                        "data_testid": best_match.get("data_testid", ""),
                        "data_qa": best_match.get("data_qa", ""),
                        "data_cy": best_match.get("data_cy", ""),
                        "data_test": best_match.get("data_test", ""),
                        "css_selector": best_match.get("css_selector", ""),
                        "is_draggable": best_match.get("is_draggable", False),
                        "is_droppable": best_match.get("is_droppable", False),
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
                    dom_candidate = (
                        best_match.get("label_text")
                        or best_match.get("text")
                        or best_match.get("aria_label")
                        or best_match.get("title_text")
                        or best_match.get("alt_text")
                        or best_match.get("placeholder")
                        or best_match.get("value")
                        or ""
                    )
                    chosen_label = _choose_label(dom_candidate, ocr)
                    updated["label_text"] = chosen_label
                    if (ocr.get("ocr_type") or "").lower() == "iconbutton":
                        ocr_label = (ocr.get("label_text") or "").strip()
                        if _is_meaningful_label(ocr_label) and ocr_label.lower() != chosen_label.lower():
                            updated["variant_text"] = ocr_label
                        updated.update(_derive_icon_context(best_match, ocr, chosen_label))
                    updated = clean_metadata(updated)
                    _attach_project_id(updated, project_id)
                    try:
                        collection.upsert(
                            ids=[updated.get("element_id")],
                            documents=[updated["label_text"]],
                            metadatas=[updated],
                        )
                    except Exception as e:
                        print(
                            f"[ERROR] Failed to upsert updated OCR record (intent fallback): {updated} | {e}")
                        traceback.print_exc()
                    matched_records.append(updated)
        except Exception as e:
            print(f"[ERROR] Error in matching OCR record: {ocr}\nException: {e}")
            traceback.print_exc()

    LAST_MATCHED_RESULTS = matched_records
    print(f"[OK] Matched {len(matched_records)} elements.")
    return matched_records
