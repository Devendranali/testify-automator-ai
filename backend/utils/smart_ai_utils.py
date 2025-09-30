# utils/smart_ai_utils.py
from pathlib import Path

SMART_AI_CODE = """import json
import numpy as np
from sentence_transformers import SentenceTransformer, util

class SmartAILocatorError(Exception):
    pass

# 🟢 Minimal wrapper to handle select_option fallback automatically + safe scroll
class SmartAIWrappedLocator:
    def __init__(self, locator, page):
        self._locator = locator
        self._page = page

    def __getattr__(self, name):
        # Delegate all other methods/attributes to Playwright's locator
        return getattr(self._locator, name)

    def _safe_scroll(self, timeout=2000):
        try:
            self._locator.scroll_into_view_if_needed(timeout=timeout)
        except Exception:
            pass

    def click(self, *args, **kwargs):
        self._safe_scroll()
        return self._locator.first.click(*args, **kwargs)

    def fill(self, *args, **kwargs):
        self._safe_scroll()
        return self._locator.first.fill(*args, **kwargs)

    def select_option(self, value, index: int | None = None, timeout: int = 5000, force: bool = False):
        '''
        Robust select handler:
        1) Try native select_option(label=...) then value=...
        2) If native fails, open combobox (optionally by index) and click an option with proper waits
        3) As a last resort on real <select>, map label->value case-insensitively via DOM
        '''
        self._safe_scroll()

        # --- Native fast-path for real <select> ---
        try:
            return self._locator.first.select_option(label=value)
        except Exception:
            try:
                return self._locator.first.select_option(value=value)
            except Exception:
                pass  # fall through to combobox flow

        # --- Combobox / custom dropdown flow with waits ---
        try:
            trigger = self._page.get_by_role("combobox")
            trigger = trigger.nth(index) if index is not None else trigger.first
            trigger.scroll_into_view_if_needed(timeout=timeout)
            trigger.click(timeout=timeout)

            # Wait for options to show up
            try:
                self._page.get_by_role("listbox").first.wait_for(state="visible", timeout=timeout)
            except Exception:
                self._page.wait_for_selector("[role='option']", timeout=timeout)

            # Exact name first
            try:
                self._page.get_by_role("option", name=value, exact=True).first.click(timeout=timeout, force=force)
                return
            except Exception:
                pass

            # Contains text
            try:
                self._page.locator("[role='option']", has_text=value).first.click(timeout=timeout, force=force)
                return
            except Exception:
                pass

            # Case-insensitive attempts
            for v in (value, str(value).strip(), str(value).capitalize(), str(value).title(), str(value).lower(), str(value).upper()):
                try:
                    self._page.get_by_role("option", name=v).first.click(timeout=timeout, force=force)
                    return
                except Exception:
                    continue

            # Final: iterate options and compare text
            opts = self._page.locator("[role='option']")
            n = opts.count()
            target_low = str(value).strip().lower()
            for i in range(n):
                try:
                    txt = opts.nth(i).inner_text().strip()
                    if txt.lower() == target_low:
                        opts.nth(i).click(timeout=timeout, force=force)
                        return
                except Exception:
                    continue

        except Exception as e:
            print(f"[SmartAI][select_option fallback] Combobox flow failed: {e}")

        # --- Last-resort: if this truly was a <select> with label/value mismatch, map by DOM ---
        try:
            opts = self._locator.first.evaluate(
                "el => Array.from(el.options).map(o => ({value:o.value, label:o.label || o.text}))"
            )
            if isinstance(opts, list) and opts:
                target = str(value).strip().lower()
                # try exact label match (case-insensitive)
                for o in opts:
                    if (o.get('label') or '').strip().lower() == target:
                        return self._locator.first.select_option(value=o.get('value'))
                # try value equals (case-insensitive)
                for o in opts:
                    if (o.get('value') or '').strip().lower() == target:
                        return self._locator.first.select_option(value=o.get('value'))
            print(f"[SmartAI][select_option fallback] Could not map '{value}' to an option value on native <select>.")
        except Exception as e3:
            print(f"[SmartAI][select_option fallback] Native <select> mapping failed: {e3}")

        raise Exception(f"SmartAI: unable to select option '{value}' (index={index})")

class SmartAISelfHealing:
    def __init__(self, metadata):
        self.metadata = metadata or []
        self.model = SentenceTransformer("all-MiniLM-L6-v2")
        # 1️⃣ Cache embeddings for all metadata elements for fast ML matching
        self.embeddings = [
            self.model.encode(self._element_to_string(e), convert_to_tensor=True, show_progress_bar=False)
            for e in self.metadata
        ]
        # Track failed locators (element unique_name → fail count)
        self.locator_fail_count = {}

    def _names_for_roles(self, element):
        '''Collect reasonable accessible names to try for role-based queries.'''
        names = []
        for key in ("label_text", "get_by_text", "placeholder"):
            v = (element.get(key) or "").strip()
            if v:
                names.append(v)
        # De-dup while preserving order
        seen = set()
        uniq = []
        for n in names:
            if n not in seen:
                uniq.append(n); seen.add(n)
        return uniq

    def _candidate_roles(self, element):
        ocr = (element.get("ocr_type") or "").lower()
        tag = (element.get("tag_name") or "").lower()
        roles = []
        # infer roles from ocr/tag
        if ocr in ("button", "submit", "iconbutton") or tag == "button":
            roles.append("button")
        if ocr in ("select", "dropdown", "combobox") or tag == "select":
            roles.append("combobox")
        if ocr in ("textbox", "text", "input", "email", "password") or tag in ("input", "textarea"):
            roles.append("textbox")
        if ocr in ("link", "anchor") or tag == "a":
            roles.append("link")
        # always include generic roles as fallbacks
        for r in ("button", "combobox", "textbox", "link"):
            if r not in roles:
                roles.append(r)
        return roles

    # Core locator strategy
    def _try_all_locators(self, element, page):
        strategies = []

        # Role-based queries using accessible names for multiple roles
        names = self._names_for_roles(element)
        if names:
            roles = self._candidate_roles(element)
            for nm in names:
                for role in roles:
                    strategies.append((lambda nm=nm, role=role: page.get_by_role(role, name=nm), f"get_by_role({role}, name={nm})"))

        # If we know the tag, try the mapped role with label_text
        if element.get("tag_name") and element.get("label_text"):
            role = self._map_tag_to_role(element["tag_name"])
            if role:
                strategies.append((lambda: page.get_by_role(role, name=element["label_text"]), f"get_by_role({role}, name={element['label_text']})"))

        # Try by label (best for inputs/selects with associated <label>)
        if element.get("label_text"):
            strategies.append((lambda: page.get_by_label(element["label_text"]), f"get_by_label({element['label_text']})"))

        # Try by exact visible text
        if element.get("label_text"):
            strategies.append((lambda: page.get_by_text(element["label_text"], exact=True), f"get_by_text({element['label_text']}, exact=True)"))

        # Try by placeholder
        if element.get("placeholder"):
            strategies.append((lambda: page.get_by_placeholder(element["placeholder"]), f"get_by_placeholder({element['placeholder']})"))

        # Try by sample value
        if element.get("sample_value"):
            strategies.append((lambda: page.get_by_display_value(element["sample_value"]), f"get_by_display_value({element['sample_value']})"))

        # Data attributes (testid/qa)
        data_attrs = element.get("data_attrs", {})
        for k, v in data_attrs.items():
            if "test" in k.lower() or "qa" in k.lower():
                strategies.append((lambda v=v: page.get_by_test_id(v), f"get_by_test_id({v}) for {k}"))

        # By id (exact and partial)
        if element.get("dom_id"):
            id_value = element["dom_id"]
            strategies.append((lambda id_value=id_value: page.locator(f'#{id_value}'), f"locator(#{id_value}) [ID exact]"))
            strategies.append((lambda id_value=id_value: page.locator(f'[id*="{id_value}"]'), f'locator([id*="{id_value}"]) [ID partial]'))

        # By class (exact and partial)
        if element.get("dom_class"):
            class_value = element["dom_class"]
            class_sel = "." + ".".join(class_value.split())
            strategies.append((lambda class_sel=class_sel: page.locator(class_sel), f"locator({class_sel}) [class exact]"))
            strategies.append((lambda class_value=class_value: page.locator(f'[class*="{class_value}"]'), f'locator([class*="{class_value}"]) [class partial]'))

        # By class_list
        if element.get("class_list"):
            sel = "." + ".".join(element["class_list"])
            strategies.append((lambda sel=sel: page.locator(sel), f"locator({sel}) [class_list]"))

        # Custom CSS locator
        if element.get("locator") and element["locator"].get("type") == "css":
            strategies.append((lambda css=element["locator"]["value"]: page.locator(css), f"locator({element['locator']['value']}) [custom css]"))

        # Attempt strategies in order
        for func, desc in strategies:
            try:
                locator = func()
                if locator and locator.count() > 0:
                    print(f"[SmartAI][Return] {desc} succeeded.")
                    self.locator_fail_count[element.get("unique_name")] = 0
                    return locator.first
            except Exception as e:
                unique_name = element.get("unique_name", "")
                self.locator_fail_count[unique_name] = self.locator_fail_count.get(unique_name, 0) + 1
                print(f"[SmartAI][Skip] {desc} failed: {e}")

        print("[SmartAI][Return] No locator found for element.")
        return None

    def find_element(self, unique_name, page):
        # Main entry for SmartAI: tries direct lookup, then ML self-healing, then heuristics.
        element = self._find_by_unique_name(unique_name)
        if element:
            locator = self._try_all_locators(element, page)
            if locator:
                print(f"[SmartAI] Element '{unique_name}' found using primary metadata.")
                return SmartAIWrappedLocator(locator, page)  # WRAPPED

            print(f"[SmartAI] Primary methods failed for '{unique_name}', trying ML self-healing...")

        # ML-based fallback
        element_ml, ml_score = self._ml_self_heal(unique_name)
        if element_ml:
            locator_ml = self._try_all_locators(element_ml, page)
            if locator_ml:
                print(f"[SmartAI] Healed element via ML ({ml_score:.2f}): '{element_ml.get('unique_name')}'")
                return SmartAIWrappedLocator(locator_ml, page)  # WRAPPED

        # Intent-aware fallback
        target_intent = element_ml.get("intent") if element_ml else None
        if target_intent:
            for e in self.metadata:
                if e.get("intent") == target_intent and e.get("unique_name") != unique_name:
                    locator = self._try_all_locators(e, page)
                    if locator:
                        print(f"[SmartAI] Healed element by intent ('{target_intent}'): '{e.get('unique_name')}'")
                        return SmartAIWrappedLocator(locator, page)  # WRAPPED

        raise SmartAILocatorError(f"Element '{unique_name}' not found and cannot self-heal.")

    def _find_by_unique_name(self, unique_name):
        return next((e for e in self.metadata if e.get("unique_name") == unique_name), None)

    def _map_tag_to_role(self, tag):
        tag_role_map = {
            'button': 'button',
            'input': 'textbox',
            'select': 'combobox',
            'textarea': 'textbox',
            'checkbox': 'checkbox'
        }
        return tag_role_map.get(tag.lower(), None)

    def _ml_self_heal(self, unique_name):
        # Returns best-matched element and score.
        query_embedding = self.model.encode(unique_name, convert_to_tensor=True, show_progress_bar=False)
        # NOTE: util.cos_sim expects 2-D tensors; we encoded each metadata element already
        scores = [util.cos_sim(query_embedding, emb).item() for emb in self.embeddings]
        best_idx = int(np.argmax(scores)) if scores else -1
        best_score = scores[best_idx] if best_idx >= 0 else 0.0
        print(f"[SmartAI] ML healed best match score: {best_score:.2f}")
        # Higher threshold for accuracy
        return (self.metadata[best_idx], best_score) if best_idx >= 0 and best_score > 0.6 else (None, best_score)

    def _element_to_string(self, element):
        # Enhancement: Fast string construction, no json.dumps.
        fields = [
            element.get('unique_name', ''),
            element.get('label_text', ''),
            element.get('intent', ''),
            element.get('ocr_type', ''),
            element.get('element_type', ''),
            element.get('tag_name', ''),
            element.get('placeholder', ''),
            ' '.join(element.get('class_list', []) or []),
            # Fast join for data_attrs
            ' '.join(f\"{k}:{v}\" for k, v in (element.get('data_attrs', {}) or {}).items()),
            element.get('sample_value', ''),
        ]
        return ' '.join([str(f) for f in fields if f])

# ====== PAGE PATCH ======
def patch_page_with_smartai(page, metadata):
    ai_healer = SmartAISelfHealing(metadata or [])
    def smartAI(unique_name):
        return ai_healer.find_element(unique_name, page)
    page.smartAI = smartAI
    return page
"""

def ensure_smart_ai_module():
    lib_path = Path("generated_runs/src/lib")
    lib_path.mkdir(parents=True, exist_ok=True)
    (lib_path / "__init__.py").touch()
    smart_ai_file = lib_path / "smart_ai.py"
    smart_ai_file.write_text(SMART_AI_CODE, encoding="utf-8")