from mcp.protocol import MCPAgentBase, MCPResponse
import re
import json

def safe_ts(s):
    # Remove quotes, keep only alphanumerics/underscore, limit to 50 chars
    return re.sub(r'\W+', '_', s.replace("'", "").replace('"', "").lower())[:50].strip('_')

KEY_NAME_MAP = {
    "tab": "Tab",
    "enter": "Enter",
    "return": "Enter",
    "esc": "Escape",
    "escape": "Escape",
    "space": "Space",
    "backspace": "Backspace",
    "delete": "Delete",
    "del": "Delete",
    "arrowleft": "ArrowLeft",
    "left": "ArrowLeft",
    "arrowright": "ArrowRight",
    "right": "ArrowRight",
    "arrowup": "ArrowUp",
    "up": "ArrowUp",
    "arrowdown": "ArrowDown",
    "down": "ArrowDown",
    "pagedown": "PageDown",
    "pageup": "PageUp",
    "home": "Home",
    "end": "End",
}

MOUSE_ACTION_TOKENS = (
    ("wheel", "wheel"),
    ("scroll", "wheel"),
    ("drag", "drag"),
    ("move", "move"),
    ("hover", "move"),
    ("down", "down"),
    ("up", "up"),
)


def _resolve_playwright_key(entry):
    candidates = [
        entry.get("value"),
        entry.get("intent"),
        entry.get("label_text"),
    ]
    for candidate in candidates:
        if not candidate:
            continue
        normalized = str(candidate).strip()
        low = normalized.lower()
        mapped = KEY_NAME_MAP.get(low.replace(" ", ""))
        if mapped:
            return mapped
        return normalized
    return "Enter"


def _mouse_position_block_ts(unique: str) -> str:
    return (
        f"    const locator = page.smartAI('{unique}');\n"
        "    let bbox;\n"
        "    try {\n"
        "        bbox = locator.boundingBox();\n"
        "    } catch {\n"
        "        bbox = null;\n"
        "    }\n"
        "    let x = 0;\n"
        "    let y = 0;\n"
        "    if (bbox) {\n"
        "        x = (bbox.x || 0) + ((bbox.width || 0) / 2);\n"
        "        y = (bbox.y || 0) + ((bbox.height || 0) / 2);\n"
        "    }\n"
    )


def _detect_mouse_action(entry):
    text = " ".join(
        v for v in (
            entry.get("intent", ""),
            entry.get("label_text", ""),
            entry.get("value", ""),
        )
        if v
    ).lower()
    for token, action in MOUSE_ACTION_TOKENS:
        if token in text:
            return action
    return "move"

def build_method_ts(entry, language="typescript"):
    ocr_type = (entry.get("ocr_type") or "").lower()
    intent = (entry.get("intent") or "").lower()
    label_text = entry.get("label_text", "")
    unique_name = entry.get("unique_name")

    def func(name):
        label = (label_text or intent or name).replace("'", "").replace('"', "")
        if len(label) > 50:
            label = label[:50]
        return safe_ts(label)

    # --- Text Inputs ---
    if ocr_type in ("textbox", "text", "input"):
        func_name = f"enter_{func('textbox')}"
        code = (
            f"export function {func_name}(page, value) {{\n"
            f"    page.smartAI('{unique_name}').fill(value);\n"
            f"}}\n"
        )
    elif ocr_type == "textarea":
        func_name = f"enter_{func('textarea')}"
        code = (
            f"export function {func_name}(page, value) {{\n"
            f"    page.smartAI('{unique_name}').fill(value);\n"
            f"}}\n"
        )
    elif ocr_type == "password":
        func_name = f"enter_{func('password')}"
        code = (
            f"export function {func_name}(page, value) {{\n"
            f"    page.smartAI('{unique_name}').fill(value);\n"
            f"}}\n"
        )
    elif ocr_type == "email":
        func_name = f"enter_{func('email')}"
        code = (
            f"export function {func_name}(page, value) {{\n"
            f"    page.smartAI('{unique_name}').fill(value);\n"
            f"}}\n"
        )
    elif ocr_type in ("keyboard", "shortcut", "hotkey"):
        key_text = _resolve_playwright_key(entry)
        func_name = f"press_{func(key_text)}"
        code = (
            f"export function {func_name}(page) {{\n"
            f"    page.keyboard.press({json.dumps(key_text)});\n"
            f"}}\n"
        )
    elif ocr_type in ("type", "keyboard_type", "typeahead"):
        default_text = entry.get("value") or entry.get("label_text") or ""
        func_name = f"type_{func('text')}"
        code = (
            f"export function {func_name}(page, value = {json.dumps(str(default_text))}) {{\n"
            f"    page.keyboard.type(value);\n"
            f"}}\n"
        )
    # --- Buttons, Links, Icons ---
    elif ocr_type in ("button", "submit", "iconbutton"):
        func_name = f"click_{func('button')}"
        code = (
            f"export function {func_name}(page) {{\n"
            f"    page.smartAI('{unique_name}').click();\n"
            f"}}\n"
        )
    elif ocr_type in ("link", "anchor"):
        func_name = f"click_{func('link')}"
        code = (
            f"export function {func_name}(page) {{\n"
            f"    page.smartAI('{unique_name}').click();\n"
            f"}}\n"
        )
    elif ocr_type == "imagebutton":
        func_name = f"click_{func('imagebutton')}"
        code = (
            f"export function {func_name}(page) {{\n"
            f"    page.smartAI('{unique_name}').click();\n"
            f"}}\n"
        )
    # --- Selectors ---
    elif ocr_type in ("select", "dropdown", "combobox"):
        func_name = f"select_{func('select')}"
        code = (
            f"export function {func_name}(page, value) {{\n"
            f"    page.smartAI('{unique_name}').selectOption(value);\n"
            f"}}\n"
        )
    elif ocr_type == "multiselect":
        func_name = f"select_{func('multiselect')}_values"
        code = (
            f"export function {func_name}(page, values) {{\n"
            f"    page.smartAI('{unique_name}').selectOptions(values);\n"
            f"}}\n"
        )
    elif ocr_type in ("mouse", "mouse_move", "mouse_wheel", "mouse_down", "mouse_up", "mouse_drag", "scroll", "hover"):
        action = _detect_mouse_action(entry)
        func_name = f"mouse_{action}_{func('element')}"
        pos_block = _mouse_position_block_ts(unique_name)
        if action == "wheel":
            code = (
                f"export function {func_name}(page) {{\n"
                f"{pos_block}"
                "    page.mouse.move(x, y);\n"
                "    page.mouse.wheel(0, 120);\n"
                f"}}\n"
            )
        elif action == "down":
            code = (
                f"export function {func_name}(page) {{\n"
                f"{pos_block}"
                "    page.mouse.move(x, y);\n"
                "    page.mouse.down();\n"
                f"}}\n"
            )
        elif action == "up":
            code = (
                f"export function {func_name}(page) {{\n"
                f"{pos_block}"
                "    page.mouse.move(x, y);\n"
                "    page.mouse.up();\n"
                f"}}\n"
            )
        elif action == "drag":
            code = (
                f"export function {func_name}(page) {{\n"
                f"{pos_block}"
                "    page.mouse.move(x, y);\n"
                "    page.mouse.down();\n"
                "    page.mouse.move(x + 50, y);\n"
                "    page.mouse.up();\n"
                f"}}\n"
            )
        else:
            code = (
                f"export function {func_name}(page) {{\n"
                f"{pos_block}"
                "    page.mouse.move(x, y);\n"
                f"}}\n"
            )
    # --- Checkboxes, Radios, Toggles, Switches ---
    elif ocr_type == "checkbox":
        func_name = f"toggle_{func('checkbox')}"
        code = (
            f"export function {func_name}(page) {{\n"
            f"    page.smartAI('{unique_name}').click();\n"
            f"}}\n"
        )
    elif ocr_type in ("radio", "radiogroup"):
        func_name = f"select_{func('radio')}_option"
        code = (
            f"export function {func_name}(page, value) {{\n"
            f"    page.smartAI('{unique_name}').check(value);\n"
            f"}}\n"
        )
    elif ocr_type in ("toggle", "switch"):
        func_name = f"toggle_{func('toggle')}"
        code = (
            f"export function {func_name}(page) {{\n"
            f"    page.smartAI('{unique_name}').click();\n"
            f"}}\n"
        )
    # --- Date/Time Pickers ---
    elif ocr_type in ("date", "datepicker"):
        func_name = f"pick_{func('date')}"
        code = (
            f"export function {func_name}(page, value) {{\n"
            f"    page.smartAI('{unique_name}').fill(value);\n"
            f"}}\n"
        )
    elif ocr_type in ("time", "timepicker"):
        func_name = f"pick_{func('time')}"
        code = (
            f"export function {func_name}(page, value) {{\n"
            f"    page.smartAI('{unique_name}').fill(value);\n"
            f"}}\n"
        )
    # --- File Upload ---
    elif ocr_type in ("file", "fileinput", "upload"):
        func_name = f"upload_{func('file')}"
        code = (
            f"export function {func_name}(page, filePath) {{\n"
            f"    page.smartAI('{unique_name}').setInputFiles(filePath);\n"
            f"}}\n"
        )
    # --- Table/Grid/Data Grid ---
    elif ocr_type in ("table", "datatable", "grid"):
        func_name = f"read_{func('table')}_data"
        code = (
            f"export function {func_name}(page) {{\n"
            f"    return page.smartAI('{unique_name}').getTableData();\n"
            f"}}\n"
        )
    elif ocr_type in ("tablecell", "cell"):
        func_name = f"get_{func('cell')}_text"
        code = (
            f"export function {func_name}(page, row, col) {{\n"
            f"    return page.smartAI('{unique_name}').getCellText(row, col);\n"
            f"}}\n"
        )
    # --- Image ---
    elif ocr_type == "image":
        func_name = f"verify_{func('image')}_visible"
        code = (
            f"export async function {func_name}(page) {{\n"
            f"    if (!(await page.smartAI('{unique_name}').isVisible())) throw new Error('Element not visible');\n"
            f"}}\n"
        )
    # --- Slider/Range ---
    elif ocr_type in ("slider", "range"):
        func_name = f"set_{func('slider')}_value"
        code = (
            f"export function {func_name}(page, value) {{\n"
            f"    page.smartAI('{unique_name}').fill(value);\n"
            f"}}\n"
        )
    # --- Progressbar ---
    elif ocr_type == "progressbar":
        func_name = f"get_{func('progressbar')}_value"
        code = (
            f"export function {func_name}(page) {{\n"
            f"    return page.smartAI('{unique_name}').getAttribute('value');\n"
            f"}}\n"
        )
    # --- Alert/Dialog/Modal/Toast ---
    elif ocr_type in ("alert", "dialog", "modal", "toast"):
        func_name = f"verify_{func('alert')}_visible"
        code = (
            f"export async function {func_name}(page) {{\n"
            f"    if (!(await page.smartAI('{unique_name}').isVisible())) throw new Error('Element not visible');\n"
            f"}}\n"
        )
    # --- Tab/Accordion/Panel ---
    elif ocr_type in ("tab", "tabpanel"):
        func_name = f"open_{func('tab')}"
        code = (
            f"export function {func_name}(page) {{\n"
            f"    page.smartAI('{unique_name}').click();\n"
            f"}}\n"
        )
    elif ocr_type in ("accordion", "panel"):
        func_name = f"expand_{func('accordion')}"
        code = (
            f"export function {func_name}(page) {{\n"
            f"    page.smartAI('{unique_name}').click();\n"
            f"}}\n"
        )
    # --- Tree/Treeview ---
    elif ocr_type in ("tree", "treeview"):
        func_name = f"expand_{func('tree')}"
        code = (
            f"export function {func_name}(page, nodeLabel) {{\n"
            f"    page.smartAI('{unique_name}').expandNode(nodeLabel);\n"
            f"}}\n"
        )
    # --- Menu ---
    elif ocr_type in ("menu", "menubar"):
        func_name = f"open_{func('menu')}"
        code = (
            f"export function {func_name}(page) {{\n"
            f"    page.smartAI('{unique_name}').click();\n"
            f"}}\n"
        )
    # --- Breadcrumb ---
    elif ocr_type == "breadcrumb":
        func_name = f"navigate_{func('breadcrumb')}"
        code = (
            f"export function {func_name}(page, crumbLabel) {{\n"
            f"    page.smartAI('{unique_name}').clickCrumb(crumbLabel);\n"
            f"}}\n"
        )
    # --- Badge/Chip/Tag ---
    elif ocr_type in ("badge", "chip", "tag"):
        func_name = f"verify_{func('badge')}_visible"
        code = (
            f"export async function {func_name}(page) {{\n"
            f"    if (!(await page.smartAI('{unique_name}').isVisible())) throw new Error('Element not visible');\n"
            f"}}\n"
        )
    # --- Avatar/Userpic ---
    elif ocr_type in ("avatar", "userpic"):
        func_name = f"verify_{func('avatar')}_visible"
        code = (
            f"export async function {func_name}(page) {{\n"
            f"    if (!(await page.smartAI('{unique_name}').isVisible())) throw new Error('Element not visible');\n"
            f"}}\n"
        )
    # --- Pagination ---
    elif ocr_type == "pagination":
        func_name = f"goto_{func('page')}"
        code = (
            f"export function {func_name}(page, pageNumber) {{\n"
            f"    page.smartAI('{unique_name}').gotoPage(pageNumber);\n"
            f"}}\n"
        )
    # --- Default/Fallback ---
    else:
        func_name = f"verify_{func('element')}_visible"
        code = (
            f"export async function {func_name}(page) {{\n"
            f"    if (!(await page.smartAI('{unique_name}').isVisible())) throw new Error('Element not visible');\n"
            f"}}\n"
        )
    return code

class PlaywrightTypescriptAgent(MCPAgentBase):
    def generate_method(self, element_spec):
        code = build_method_ts(element_spec)
        return MCPResponse(True, code)

    def generate_test(self, test_case_spec):
        steps = "\n    ".join(test_case_spec.get("steps", []))
        code = (
            "import { test } from '@playwright/test';\n"
            "import * as methods from './page_methods';\n\n"
            "test('Generated Test', async ({ page }) => {\n"
            f"    {steps}\n"
            "});\n"
        )
        return MCPResponse(True, code)

    def generate_page_file(self, payload):
        entries = payload["entries"]
        page_name = payload.get("page_name", "page")
        header = (
            "// SmartAI Patch Import here if needed\n"
            f"// Methods for page: {page_name}\n\n"
        )
        methods = [self.generate_method(e).payload for e in entries]
        filename = f"{page_name}_page_methods.ts"  # TypeScript agent returns .ts
        code = header + "\n".join(methods)
        return MCPResponse(True, {"filename": filename, "code": code})
