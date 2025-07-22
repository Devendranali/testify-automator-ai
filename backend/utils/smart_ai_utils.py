from pathlib import Path

SMART_AI_CODE = """import json
import numpy as np
from sentence_transformers import SentenceTransformer, util

class SmartAILocatorError(Exception):
    pass

# 🟢 Minimal wrapper to handle select_option fallback automatically
class SmartAIWrappedLocator:
    def __init__(self, locator, page):
        self._locator = locator
        self._page = page

    def __getattr__(self, name):
        # Delegate all other methods/attributes to Playwright's locator
        return getattr(self._locator, name)

    def select_option(self, value):
        try:
            return self._locator.select_option(value)
        except Exception as e:
            print(f"[SmartAI][select_option fallback] Native select_option failed: {e}")
            try:
                self._page.get_by_role("combobox").click()
                self._page.get_by_role("option", name=value).click()
                print(f"[SmartAI][select_option fallback] Selected '{value}' via combobox+option fallback")
            except Exception as e2:
                print(f"[SmartAI][select_option fallback] Fallback also failed: {e2}")
                raise

class SmartAISelfHealing:
    def __init__(self, metadata):
        self.metadata = metadata
        self.model = SentenceTransformer("all-MiniLM-L6-v2")
        # 1️⃣ Cache embeddings for all metadata elements for fast ML matching
        self.embeddings = [
            self.model.encode(self._element_to_string(e), convert_to_tensor=True, show_progress_bar=False)
            for e in self.metadata
        ]
        # 10️⃣ Track failed locators (element unique_name → fail count)
        self.locator_fail_count = {}

    # 5️⃣ Single definition; all prioritization inside
    def _try_all_locators(self, element, page):
        strategies = []

        # Highest priority: try by role and label_text (esp for button, input, etc)
        if element.get("tag_name") and element.get("label_text"):
            role = self._map_tag_to_role(element["tag_name"])
            if role:
                strategies.append((lambda: page.get_by_role(
                    role, name=element["label_text"]), f"get_by_role({role}, name={element['label_text']})"))

        # Try by label (best for inputs)
        if element.get("label_text"):
            strategies.append((lambda: page.get_by_label(
                element["label_text"]), f"get_by_label({element['label_text']})"))

        # Try by visible text (good for buttons, links, etc)
        if element.get("label_text"):
            strategies.append((lambda: page.get_by_text(
                element["label_text"], exact=True), f"get_by_text({element['label_text']}, exact=True)"))

        # Try by placeholder (for textboxes/inputs)
        if element.get("placeholder"):
            strategies.append((lambda: page.get_by_placeholder(
                element["placeholder"]), f"get_by_placeholder({element['placeholder']})"))

        # Try by sample value (displayed value in input)
        if element.get("sample_value"):
            strategies.append((lambda: page.get_by_display_value(
                element["sample_value"]), f"get_by_display_value({element['sample_value']})"))

        # Data attributes (testid/qa)
        data_attrs = element.get("data_attrs", {})
        for k, v in data_attrs.items():
            if "test" in k.lower() or "qa" in k.lower():
                strategies.append((lambda: page.get_by_test_id(v),
                                f"get_by_test_id({v}) for {k}"))

        # By id (exact and partial)
        if element.get("dom_id"):
            id_value = element["dom_id"]
            strategies.append((lambda: page.locator(
                f'#{id_value}'), f"locator(#{id_value}) [ID exact]"))
            strategies.append((lambda: page.locator(
                f'[id*="{id_value}"]'), f'locator([id*="{id_value}"]) [ID partial]'))

        # By class (exact and partial)
        if element.get("dom_class"):
            class_value = element["dom_class"]
            class_sel = "." + ".".join(class_value.split())
            strategies.append((lambda: page.locator(class_sel),
                            f"locator({class_sel}) [class exact]"))
            strategies.append((lambda: page.locator(
                f'[class*="{class_value}"]'), f'locator([class*="{class_value}"]) [class partial]'))

        # By class_list
        if element.get("class_list"):
            sel = "." + ".".join(element["class_list"])
            strategies.append((lambda: page.locator(
                sel), f"locator({sel}) [class_list]"))

        # Custom CSS locator
        if element.get("locator") and element["locator"].get("type") == "css":
            strategies.append((lambda: page.locator(
                element["locator"]["value"]), f"locator({element['locator']['value']}) [custom css]"))
                
        # Now try each strategy in order
        for func, desc in strategies:
            try:
                locator = func()
                if locator and locator.count() > 0:
                    print(f"[SmartAI][Return] {desc} succeeded.")
                    self.locator_fail_count[element.get("unique_name")] = 0
                    return locator.last
            except Exception as e:
                unique_name = element.get("unique_name", "")
                self.locator_fail_count[unique_name] = self.locator_fail_count.get(
                    unique_name, 0) + 1
                print(f"[SmartAI][Skip] {desc} failed: {e}")

        print("[SmartAI][Return] No locator found for element.")
        return None

    # def _try_all_locators(self, element, page):
    #     # Tries various locator strategies in strict priority order.
    #     # Enhancement: Prioritize, early return, minimal .count() checks.
    #     # Enhancement: Penalize recently failing locators.
    #     def should_skip(unique_name):
    #         return self.locator_fail_count.get(unique_name, 0) >= 3

    #     strategies = []

    #     data_attrs = element.get("data_attrs", {})
    #     for k, v in data_attrs.items():
    #         if "test" in k.lower() or "qa" in k.lower():
    #             strategies.append((lambda: page.get_by_test_id(v), f"get_by_test_id({v}) for {k}"))

    #     if element.get("tag_name"):
    #         role = self._map_tag_to_role(element["tag_name"])
    #         if role and element.get("label_text"):
    #             strategies.append((lambda: page.get_by_role(role, name=element["label_text"]), f"get_by_role({role}, name={element['label_text']})"))

    #     if element.get("label_text"):
    #         strategies.append((lambda: page.get_by_label(element["label_text"]), f"get_by_label({element['label_text']})"))

    #     if element.get("placeholder"):
    #         strategies.append((lambda: page.get_by_placeholder(element["placeholder"]), f"get_by_placeholder({element['placeholder']})"))

    #     if element.get("label_text"):
    #         strategies.append((lambda: page.get_by_text(element["label_text"], exact=True), f"get_by_text({element['label_text']}, exact=True)"))

    #     if element.get("sample_value"):
    #         strategies.append((lambda: page.get_by_display_value(element["sample_value"]), f"get_by_display_value({element['sample_value']})"))

    #     if element.get("dom_id"):
    #         id_value = element["dom_id"]
    #         strategies.append((lambda: page.locator(f'#{id_value}'), f"locator(#{id_value}) [ID exact]"))
    #         strategies.append((lambda: page.locator(f'[id*="{id_value}"]'), f'locator([id*="{id_value}"]) [ID partial]'))

    #     if element.get("dom_class"):
    #         class_value = element["dom_class"]
    #         class_sel = "." + ".".join(class_value.split())
    #         strategies.append((lambda: page.locator(class_sel), f"locator({class_sel}) [class exact]"))
    #         strategies.append((lambda: page.locator(f'[class*="{class_value}"]'), f'locator([class*="{class_value}"]) [class partial]'))

    #     if element.get("class_list"):
    #         sel = "." + ".".join(element["class_list"])
    #         strategies.append((lambda: page.locator(sel), f"locator({sel}) [class_list]"))

    #     if element.get("locator") and element["locator"].get("type") == "css":
    #         strategies.append((lambda: page.locator(element["locator"]["value"]), f"locator({element['locator']['value']}) [custom css]"))

    #     # Attempt strategies in order, skipping if penalized
    #     for func, desc in strategies:
    #         try:
    #             locator = func()
    #             # 2️⃣ Only check .count() once per strategy, early return
    #             if locator and locator.count() > 0:
    #                 print(f"[SmartAI][Return] {desc} succeeded.")
    #                 self.locator_fail_count[element.get("unique_name")] = 0  # Reset fail count
    #                 return locator.last
    #         except Exception as e:
    #             # 10️⃣ Track fail count for this unique_name
    #             unique_name = element.get("unique_name", "")
    #             self.locator_fail_count[unique_name] = self.locator_fail_count.get(unique_name, 0) + 1
    #             print(f"[SmartAI][Skip] {desc} failed: {e}")

    #     print("[SmartAI][Return] No locator found for element.")
    #     return None

    def find_element(self, unique_name, page):
        # Main entry for SmartAI: tries direct lookup, then ML self-healing, then heuristics.
        element = self._find_by_unique_name(unique_name)
        if element:
            locator = self._try_all_locators(element, page)
            if locator:
                print(f"[SmartAI] Element '{unique_name}' found using primary metadata.")
                return SmartAIWrappedLocator(locator, page)  # <--- PATCHED

            print(f"[SmartAI] Primary methods failed for '{unique_name}', trying ML self-healing...")

        # ML-based fallback
        element_ml, ml_score = self._ml_self_heal(unique_name)
        if element_ml:
            locator_ml = self._try_all_locators(element_ml, page)
            if locator_ml:
                print(f"[SmartAI] Healed element via ML ({ml_score:.2f}): '{element_ml.get('unique_name')}'")
                return SmartAIWrappedLocator(locator_ml, page)  # <--- PATCHED

        # 9️⃣ Intent-aware fallback: try other elements with same intent
        target_intent = element_ml.get("intent") if element_ml else None
        if target_intent:
            for e in self.metadata:
                if e.get("intent") == target_intent and e.get("unique_name") != unique_name:
                    locator = self._try_all_locators(e, page)
                    if locator:
                        print(f"[SmartAI] Healed element by intent ('{target_intent}'): '{e.get('unique_name')}'")
                        return SmartAIWrappedLocator(locator, page)  # <--- PATCHED

        # 11️⃣ Visual/position fallback (commented for extension)
        # print("[SmartAI] Trying fallback by position (not implemented)...")

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
        # Enhancement: Uses pre-cached embeddings for performance!
        # 3️⃣ Uses higher threshold for accuracy.
        query_embedding = self.model.encode(unique_name, convert_to_tensor=True, show_progress_bar=False)
        scores = [util.cos_sim(query_embedding, emb).item() for emb in self.embeddings]
        best_idx = int(np.argmax(scores))
        best_score = scores[best_idx]
        print(f"[SmartAI] ML healed best match score: {best_score:.2f}")
        # 3️⃣ Higher threshold (was 0.3, now 0.6)
        return (self.metadata[best_idx], best_score) if best_score > 0.6 else (None, best_score)

    def _element_to_string(self, element):
        # Enhancement: Fast string construction, no json.dumps.
        fields = [
            element.get("unique_name", ""),
            element.get("label_text", ""),
            element.get("intent", ""),
            element.get("ocr_type", ""),
            element.get("element_type", ""),
            element.get("tag_name", ""),
            element.get("placeholder", ""),
            " ".join(element.get("class_list", [])) if element.get("class_list") else "",
            # 4️⃣ Fast join for data_attrs
            " ".join(f"{k}:{v}" for k, v in (element.get("data_attrs", {}) or {}).items()),
            element.get("sample_value", ""),
        ]
        return " ".join([str(f) for f in fields if f])

# ====== PAGE PATCH ======
def patch_page_with_smartai(page, metadata):
    ai_healer = SmartAISelfHealing(metadata)
    def smartAI(unique_name):
        return ai_healer.find_element(unique_name, page)
    page.smartAI = smartAI
    return page
"""

def ensure_smart_ai_module():
    lib_path = Path("generated_runs/src/lib")
    lib_path.mkdir(parents=True, exist_ok=True)
    # --- ADD THIS LINE! ---
    (lib_path / "__init__.py").touch()
    # ----------------------
    smart_ai_file = lib_path / "smart_ai.py"
    if not smart_ai_file.exists():
        smart_ai_file.write_text(SMART_AI_CODE, encoding="utf-8")
