from utils.enrichment_status import set_enriched, is_enriched
from utils.match_utils import normalize_page_name
from logic.manual_capture_mode import extract_dom_metadata, match_and_update
from chromadb import PersistentClient
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
import asyncio


async def enrich_page(page, page_name):
    if is_enriched(page_name):
        return  # Already enriched

    # --- DOM Extraction ---
    dom_data = await extract_dom_metadata(page, page_name)

    # --- OCR Data Fetch ---
    embedding_fn = SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2")
    client = PersistentClient(path="./data/chroma_db")
    collection = client.get_or_create_collection(
        name="element_metadata", embedding_function=embedding_fn)
    ocr_data = [r for r in collection.get(
        where={"page_name": page_name, "type": "ocr"}).get("metadatas", [])]

    # --- Match and Update ---
    match_and_update(ocr_data, dom_data, collection)

    set_enriched(page_name, True)
