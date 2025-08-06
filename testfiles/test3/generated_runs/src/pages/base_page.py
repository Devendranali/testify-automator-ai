# base_page.py


from services.page_enricher import enrich_page
from generated_runs.src.lib.smart_ai import patch_page_with_smartai
from services.chroma_service import get_chroma_collection


class BasePage:
    enriched_pages = set()
    shared_page = None  # Class-level page sharing

    def __init__(self, page=None, page_name="base", url=None):
        if page is not None:
            BasePage.shared_page = page  # store shared page at class level
        elif BasePage.shared_page is None:
            raise ValueError(
                "Playwright page instance must be provided at least once.")

        self.page = BasePage.shared_page
        self.page_name = page_name
        self.url = url

    def _fetch_metadata_from_chroma(self, page_name):
        collection = get_chroma_collection()
        all_metadata = collection.get(
            where={"page_name": page_name}).get("metadatas", [])
        return all_metadata

    async def goto(self, url=None):
        target_url = url or self.url
        if not target_url:
            raise ValueError(f"URL not set for {self.page_name}")
        await self.page.goto(target_url)

    async def enrich_once(self, force=False):
        if force or self.page_name not in BasePage.enriched_pages:
            await enrich_page(self.page, self.page_name)
            BasePage.enriched_pages.add(self.page_name)
