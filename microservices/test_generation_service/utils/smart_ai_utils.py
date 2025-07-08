from pathlib import Path

SMART_AI_CODE = """
import json
import time
from sentence_transformers import SentenceTransformer, util
from playwright.sync_api import sync_playwright
from pathlib import Path

# ====== SMART AI SELF-HEALER CORE ======

class SmartAILocatorError(Exception):
    pass

class SmartAISelfHealing:
    def __init__(self, metadata):
        self.metadata = metadata
        self.model = SentenceTransformer("all-MiniLM-L6-v2")

    def find_element(self, unique_name, page):
        # element = self._find_by_unique_name(unique_name)
        # if element:
        #     locator = self._try_all_locators(element, page)
        #     if locator:
        #         print(f"[SmartAI] Element '{unique_name}' found using standard locator methods.")
        #         return locator
        #     print(f"[SmartAI] Standard methods failed for '{unique_name}'. ML self-healing in progress...")
        # else:
            # print(f"[SmartAI] Unique_name '{unique_name}' not found. ML self-healing in progress...")

        element_ml = self._ml_self_heal(unique_name)
        if element_ml:
            locator_ml = self._try_all_locators(element_ml, page)
            if locator_ml:
                print(f"[SmartAI] Healed element found via ML matching: '{element_ml.get('unique_name')}'")
                return locator_ml

        raise SmartAILocatorError(f"Element '{unique_name}' not found and cannot self-heal.")

    def _find_by_unique_name(self, unique_name):
        for element in self.metadata:
            if element.get("unique_name") == unique_name:
                return element
        return None

    def _map_tag_to_role(self, tag):
        tag_role_map = {
            'button': 'button',
            'input': 'textbox',
            'select': 'combobox',
            'textarea': 'textbox',
            'checkbox': 'checkbox'
        }
        return tag_role_map.get(tag.lower(), None)

    # Our working order:
    def _try_all_locators(self, element, page):
        '''Order Is:
                # 1. Placeholder
                # 2. Label (label, then text)
                # 3. Role + label
                # 4. Test ID (data-qa, data-test)
                # 5. Display value (sample_value)
                # 6. CSS selector (custom locator)
                # 7. ID (exact, then partial)
                # 8. Class (exact, then partial)
                # 9. Class list
        '''
        try_methods = []

        if element.get("placeholder"):
            try_methods.append(lambda: page.get_by_placeholder(element["placeholder"]))

        if element.get("label_text"):
            try_methods.append(lambda: page.get_by_label(element["label_text"]))
            try_methods.append(lambda: page.get_by_text(element["label_text"], exact=True))

        if element.get("tag_name"):
            role = self._map_tag_to_role(element["tag_name"])
            if role:
                try_methods.append(lambda: page.get_by_role(role, name=element.get("label_text", None)))

        data_attrs = element.get("data_attrs", {})
        for k, v in data_attrs.items():
            if "test" in k.lower() or "qa" in k.lower():
                try_methods.append(lambda: page.get_by_test_id(v))

        if element.get("sample_value"):
            try_methods.append(lambda: page.get_by_display_value(element["sample_value"]))

        if element.get("locator") and element["locator"].get("type") == "css":
            try_methods.append(lambda: page.locator(element["locator"]["value"]))

        # ✅ NEW: Try by id (string), before dom_class
        if element.get("dom_id"):
            id_value = element["dom_id"]
            # Exact match
            try_methods.append(lambda: page.locator(f'#{id_value}'))
            # Partial match (robustness)
            try_methods.append(lambda: page.locator(f'[id*="{id_value}"]'))


        # ✅ NEW: Try by class (string)
        if element.get("dom_class"):
            # Exact class match (e.g., class="shopping_cart_link")
            class_value = element["dom_class"]
            class_sel = "." + ".".join(class_value.split())
            try_methods.append(lambda: page.locator(class_sel))
            # Optional: partial match for robustness
            try_methods.append(lambda: page.locator(f'[class*="{class_value}"]'))

        # Existing: class_list (list of classes)
        if element.get("class_list"):
            sel = "." + ".".join(element["class_list"])
            try_methods.append(lambda: page.locator(sel))
            
        for method in try_methods:
            try:
                locator = method()
                if locator.count() > 0:
                    return locator.first
            except Exception:
                continue

        return None

    # Standard order:
    def _try_all_locators(self, element, page):
        '''
            # 1. Test ID
            # 2. Role + Name
            # 3. Label Text
            # 4. Placeholder
            # 5. Text Content (exact)
            # 6. Display Value
            # 7. ID (exact)
            # 8. ID (partial)
            # 9. Class (exact)
            # 10. Class (partial)
            # 11. Class list (composite)
            # 12. CSS Selector (custom/fallback)
        '''
        try_methods = []
        descriptions = []

        # 1. data-testid/data-test/data-qa
        data_attrs = element.get("data_attrs", {})
        for k, v in data_attrs.items():
            if "test" in k.lower() or "qa" in k.lower():
                print(f"[SmartAI][Add] get_by_test_id({v}) for attribute {k}")
                try_methods.append(lambda: page.get_by_test_id(v))
                descriptions.append(f"get_by_test_id({v}) for attribute {k}")

        # 2. role + label
        if element.get("tag_name"):
            role = self._map_tag_to_role(element["tag_name"])
            if role and element.get("label_text"):
                print(f"[SmartAI][Add] get_by_role({role}, name={element['label_text']})")
                try_methods.append(lambda: page.get_by_role(role, name=element["label_text"]))
                descriptions.append(f"get_by_role({role}, name={element['label_text']})")

        # 3. label text
        if element.get("label_text"):
            print(f"[SmartAI][Add] get_by_label({element['label_text']})")
            try_methods.append(lambda: page.get_by_label(element["label_text"]))
            descriptions.append(f"get_by_label({element['label_text']})")

        # 4. placeholder
        if element.get("placeholder"):
            print(f"[SmartAI][Add] get_by_placeholder({element['placeholder']})")
            try_methods.append(lambda: page.get_by_placeholder(element["placeholder"]))
            descriptions.append(f"get_by_placeholder({element['placeholder']})")

        # 5. text content (exact)
        if element.get("label_text"):
            print(f"[SmartAI][Add] get_by_text({element['label_text']}, exact=True)")
            try_methods.append(lambda: page.get_by_text(element["label_text"], exact=True))
            descriptions.append(f"get_by_text({element['label_text']}, exact=True)")

        # 6. display value
        if element.get("sample_value"):
            print(f"[SmartAI][Add] get_by_display_value({element['sample_value']})")
            try_methods.append(lambda: page.get_by_display_value(element["sample_value"]))
            descriptions.append(f"get_by_display_value({element['sample_value']})")

        # 7. id (exact)
        if element.get("dom_id"):
            id_value = element["dom_id"]
            print(f"[SmartAI][Add] locator(#{id_value}) [ID exact]")
            try_methods.append(lambda: page.locator(f'#{id_value}'))
            descriptions.append(f"locator(#{id_value}) [ID exact]")
            # 8. id (partial)
            print(f'[SmartAI][Add] locator([id*="{id_value}"]) [ID partial]')
            try_methods.append(lambda: page.locator(f'[id*="{id_value}"]'))
            descriptions.append(f'locator([id*="{id_value}"]) [ID partial]')

        # 9. class (exact)
        if element.get("dom_class"):
            class_value = element["dom_class"]
            class_sel = "." + ".".join(class_value.split())
            print(f"[SmartAI][Add] locator({class_sel}) [class exact]")
            try_methods.append(lambda: page.locator(class_sel))
            descriptions.append(f"locator({class_sel}) [class exact]")
            # 10. class (partial)
            print(f'[SmartAI][Add] locator([class*="{class_value}"]) [class partial]')
            try_methods.append(lambda: page.locator(f'[class*="{class_value}"]'))
            descriptions.append(f'locator([class*="{class_value}"]) [class partial]')

        # 11. class list (composite)
        if element.get("class_list"):
            sel = "." + ".".join(element["class_list"])
            print(f"[SmartAI][Add] locator({sel}) [class_list]")
            try_methods.append(lambda: page.locator(sel))
            descriptions.append(f"locator({sel}) [class_list]")

        # 12. custom css selector (if provided)
        if element.get("locator") and element["locator"].get("type") == "css":
            print(f"[SmartAI][Add] locator({element['locator']['value']}) [custom css]")
            try_methods.append(lambda: page.locator(element["locator"]["value"]))
            descriptions.append(f"locator({element['locator']['value']}) [custom css]")

        for idx, method in enumerate(try_methods):
            try:
                locator = method()
                if locator.count() > 0:
                    print(f"[SmartAI][Return] {descriptions[idx]} succeeded and returned a locator.")
                    return locator.first
            except Exception as e:
                print(f"[SmartAI][Skip] {descriptions[idx]} failed due to: {e}")
                continue

        print("[SmartAI][Return] No locator found for element.")
        return None

    def _ml_self_heal(self, unique_name):
        query_embedding = self.model.encode(unique_name, convert_to_tensor=True, show_progress_bar=False)
        best_score = -1
        best_element = None
        for element in self.metadata:
            attr_str = self._element_to_string(element)
            attr_embedding = self.model.encode(attr_str, convert_to_tensor=True, show_progress_bar=False)
            score = util.cos_sim(query_embedding, attr_embedding).item()
            if score > best_score:
                best_score = score
                best_element = element

        print(f"[SmartAI] Best healed match score: {best_score}")
        return best_element if best_score > 0.3 else None

    def _element_to_string(self, element):
        fields = [
            element.get("unique_name", ""),
            element.get("label_text", ""),
            element.get("intent", ""),
            element.get("ocr_type", ""),
            element.get("element_type", ""),
            element.get("tag_name", ""),
            element.get("placeholder", ""),
            " ".join(element.get("class_list", [])) if element.get("class_list") else "",
            json.dumps(element.get("data_attrs", {})),
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

# ====== SAMPLE METADATA + USAGE ======

if __name__ == "__main__":
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto("https://www.saucedemo.com/")

        script_dir = Path(__file__).parent
        metadata_path = (script_dir.parent / "metadata" / "after_enrichment.json").resolve()

        with open(metadata_path, "r") as f:
            actual_metadata = json.load(f)

        patch_page_with_smartai(page, actual_metadata)

        # ------------------------------- login
        # try:
        #     page.smartAI('saucedemo_login_title_swag_labs_label').is_visible()
        #     print("saucedemo_login_title_swag_labs_label is visible ")
        # except Exception as e:
        #     print(f"saucedemo_login_title_swag_labs_label error: {e}")
        # time.sleep(1)
        
        try:
            page.smartAI('saucedemo_login_username_username_textbox').fill('standard_user')
            print("Username filled successfully. ")
        except Exception as e:
            print(f"Username fill error: {e}", "")
        # time.sleep(1)

        try:
            page.smartAI('saucedemo_login_password_password_textbox').fill('secret_sauce')
            print("Password filled successfully. ")
        except Exception as e:
            print(f"Password fill error: {e}", "")
        # time.sleep(1)

        try:
            page.smartAI('saucedemo_login_login_login_button').click()
            print("Login button clicked. ")
        except Exception as e:
            print(f"Login click error: {e}", "")
        # time.sleep(1)
        # ----------------------------- inventory
        try:
            assert page.smartAI('saucedemo_inventory_product_list_products_label').is_visible()
            print("Product verified. ")
        except Exception as e:
            print("Product verified error.", e, "")
        # time.sleep(1)
        
        try:            
            assert page.smartAI('saucedemo_inventory_product_name_sauce_labs_backpack_label').is_visible()
            print("SauceLab Backpack verified. ")
        except Exception as e:
            print("SauceLab Backpack verified error.", e, "")
        # time.sleep(1)
        
        try:
            page.smartAI('saucedemo_inventory_add_to_cart_add_to_cart_button').click()
            print("Add-To-Cart is clicked. ")
        except Exception as e:
            print("Add-To-Cart is clicked error.", e, "")
        # time.sleep(1)
        
        try:
            page.smartAI('saucedemo_inventory_go_to_cart_shopping_cart_link_button').click()
            print("Shopping Cart is clicked. ")
        except Exception as e:
            print("Shopping Cart is clicked error.", e, "")
        # time.sleep(1)
        # ----------------------------- cart             
        try:
            assert page.smartAI('saucedemo_cart_header_your_cart_label').is_visible()
            print("Your Cart Label verified. ")
        except Exception as e:
            print("Your Cart Label verified error.", e, "")
        # time.sleep(1)

        try:
            page.smartAI('saucedemo_cart_proceed_checkout_checkout_button').click()
            print("Checkout clicked. ")
        except Exception as e:
            print("Checkout clicked error.", e, "")
        # time.sleep(1)
        
        # ----------------------------- checkout-info
        try:
            assert page.smartAI('saucedemo_checkout_info_instructions_checkout:_your_information_label').is_visible()
            print("Checkout Info verified. ")
        except Exception as e:
            print("Checkout Info verified error.", e, "")
        # time.sleep(1)
        
        try:
            page.smartAI('saucedemo_checkout_info_first_name_first_name_textbox').fill('John')
            print("First name filled. ")
        except Exception as e:
            print("First name filled error.", e, "")
        # time.sleep(1)
        
        try:
            page.smartAI('saucedemo_checkout_info_last_name_last_name_textbox').fill('Doe')
            print("Last name filled. ")
        except Exception as e:
            print("Last name filled error.", e, "")
        # time.sleep(1)
        
        try:
            page.smartAI('saucedemo_checkout_info_zip_code_zip/postal_code_textbox').fill('123456')
            print("zip code filled. ")
        except Exception as e:
            print("zip code filled error.", e, "")
        # time.sleep(1)
        
        try:
            page.smartAI('saucedemo_checkout_info_continue_continue_button').click()
            print("Continue button clicked. ")
        except Exception as e:
            print("Continue button not clicked.", e, "")
        # time.sleep(1)
        
        # ------------------------------- checkout-overview
        try:
            assert page.smartAI('saucedemo_checkout_overview_page_title_checkout:_overview_label').is_visible()
            print("Checkout Overview verified. ")
        except Exception as e:
            print("Checkout Overview verified error.", e, "")
        # time.sleep(1)
        
        try:
            page.smartAI('saucedemo_checkout_overview_finish_finish_button').click()
            print("Finish button clicked.")
        except Exception as e:
            print("Finish button not clicked.", e, "")
        # time.sleep(1)
        



        time.sleep(5)
        browser.close()

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

if __name__ == "__main__":
    ensure_smart_ai_module()
    print("smart_ai.py ensured in generated_runs/src/lib/")