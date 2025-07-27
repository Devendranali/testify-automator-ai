import re
from mcp.protocol import MCPAgentBase, MCPResponse
from utils.match_utils import normalize_page_name


def safe(name: str) -> str:
    return re.sub(r'\W+', '_', name.lower()).strip('_')


class PlaywrightPythonAgent(MCPAgentBase):
    def generate_method(self, element_spec):
        return MCPResponse(False, error="generate_method is now part of generate_page_file")

    def generate_test(self, test_case_spec):
        page_imports = test_case_spec["imports"]  # e.g. ['from pages.dashboard_page import DashboardPage']
        method_calls = test_case_spec["calls"]    # e.g. ['await page.enter_username("standard_user")', ...]

        code = "\n".join([
            *page_imports,
            "\n\nasync def test_generated_flow(smartai_page):",
            "    page = DashboardPage(smartai_page)",
            *["    " + line for line in method_calls]
        ])
        return MCPResponse(True, code)

    def generate_page_file(self, payload):
        entries = payload["entries"]
        page_name = normalize_page_name(payload.get("page_name", "page"))
        class_name = f"{''.join([word.capitalize() for word in page_name.split('_')])}Page"

        import_block = (
            "import asyncio\n"
            "from services.page_enricher import enrich_page\n"
            "from utils.enrichment_status import is_enriched\n"
        )

        class_header = (
            f"\n\nclass {class_name}(BasePage):\n"
            f"    def __init__(self, page, page_name=\"{page_name}\"):\n"
            f"        super().__init__(page, page_name)\n"
            f"        self._enriched = False\n\n"
            f"    async def _enrich_if_needed(self, force=False):\n"
            f"        if force or not is_enriched(self.page_name):\n"
            f"            await enrich_page(self.page, self.page_name)\n"
            f"            self._enriched = True\n"
        )

        method_blocks = []
        seen_method_names = set()

        ignored_types = {}

        for entry in entries:
            ocr_type = (entry.get("ocr_type") or "").lower()
            label = entry.get("label_text", "") or entry.get(
                "intent", "") or "element"
            smartai_name = entry.get("unique_name", "")
            base_name = safe(label)

            if ocr_type in ignored_types:
                continue  # Skip passive elements

            # --- Map ocr_type to method template ---
            if ocr_type in ("textbox", "text", "textarea", "password", "email", "input"):
                method_name = f"enter_{base_name}"
                block = (
                    f"    async def {method_name}(self, value):\n"
                    f"        await self._enrich_if_needed()\n"
                    f"        await self.page.smartAI('{smartai_name}').fill(value)\n"
                )

            elif ocr_type in ("button", "submit", "link", "iconbutton", "imagebutton", "tab", "panel", "accordion", "menu", "breadcrumb"):
                method_name = f"click_{base_name}"
                block = (
                    f"    async def {method_name}(self):\n"
                    f"        await self._enrich_if_needed()\n"
                    f"        await self.page.smartAI('{smartai_name}').click()\n"
                )

            elif ocr_type in ("select", "dropdown", "combobox"):
                method_name = f"select_{base_name}"
                block = (
                    f"    async def {method_name}(self, value):\n"
                    f"        await self._enrich_if_needed()\n"
                    f"        await self.page.smartAI('{smartai_name}').select_option(value)\n"
                )

            elif ocr_type == "multiselect":
                method_name = f"select_{base_name}_values"
                block = (
                    f"    async def {method_name}(self, values):\n"
                    f"        await self._enrich_if_needed()\n"
                    f"        await self.page.smartAI('{smartai_name}').select_options(values)\n"
                )

            elif ocr_type in ("checkbox", "switch", "toggle"):
                method_name = f"toggle_{base_name}"
                block = (
                    f"    async def {method_name}(self):\n"
                    f"        await self._enrich_if_needed()\n"
                    f"        await self.page.smartAI('{smartai_name}').click()\n"
                )

            elif ocr_type in ("date", "datepicker", "time", "timepicker", "slider", "range"):
                method_name = f"set_{base_name}"
                block = (
                    f"    async def {method_name}(self, value):\n"
                    f"        await self._enrich_if_needed()\n"
                    f"        await self.page.smartAI('{smartai_name}').fill(value)\n"
                )

            elif ocr_type in ("image", "avatar", "userpic", "badge", "chip", "tag", "alert", "modal", "toast", "dialog", "label"):
                method_name = f"verify_{base_name}_visible"
                block = (
                    f"    async def {method_name}(self):\n"
                    f"        await self._enrich_if_needed()\n"
                    f"        assert await self.page.smartAI('{smartai_name}').is_visible()\n"
                )

            elif ocr_type == "pagination":
                method_name = f"goto_{base_name}"
                block = (
                    f"    async def {method_name}(self, page_number):\n"
                    f"        await self._enrich_if_needed()\n"
                    f"        await self.page.smartAI('{smartai_name}').goto_page(page_number)\n"
                )

            elif ocr_type in ("table", "grid", "datatable"):
                method_name = f"read_{base_name}_data"
                block = (
                    f"    async def {method_name}(self):\n"
                    f"        await self._enrich_if_needed()\n"
                    f"        return await self.page.smartAI('{smartai_name}').get_table_data()\n"
                )

            elif ocr_type in ("file", "upload", "fileinput"):
                method_name = f"upload_{base_name}"
                block = (
                    f"    async def {method_name}(self, file_path):\n"
                    f"        await self._enrich_if_needed()\n"
                    f"        await self.page.smartAI('{smartai_name}').set_input_files(file_path)\n"
                )

            else:
                method_name = f"interact_{base_name}"
                block = (
                    f"    async def {method_name}(self):\n"
                    f"        await self._enrich_if_needed()\n"
                    f"        # TODO: Define behavior for '{ocr_type}'\n"
                )

            # Avoid duplicates
            if method_name in seen_method_names:
                continue
            seen_method_names.add(method_name)
            method_blocks.append(block)

        # Assemble file
        code = import_block + "\n\n" + class_header + "\n".join(method_blocks)
        filename = f"{page_name}_page.py"

        return MCPResponse(True, {
            "page_file": filename,
            "code": code
        })
