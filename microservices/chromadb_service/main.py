# microservices/chromadb_service/main.py

from fastapi import FastAPI, APIRouter, Query, HTTPException
from fastapi.responses import JSONResponse, FileResponse
import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from fastapi.concurrency import run_in_threadpool
import json
from pathlib import Path
import logging
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="ChromaDB Service")
router = APIRouter()

# ChromaDB setup
CHROMA_PATH = os.getenv("CHROMA_PATH", "./chroma_db_data") # Use environment variable or default
os.makedirs(CHROMA_PATH, exist_ok=True)

embedding_function = SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
client = chromadb.PersistentClient(path=CHROMA_PATH)
collection = client.get_or_create_collection(name="element_metadata", embedding_function=embedding_function)

# Logger
error_logger = logging.getLogger("chroma_upsert_errors")
error_logger.setLevel(logging.WARNING)
handler = logging.FileHandler("chroma_upsert_errors.log")
handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
error_logger.addHandler(handler)

# Helper function from original chroma_service.py
def _sanitize_metadata_value(value):
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value)
    return value

@router.post("/upsert-text-record")
async def upsert_text_record_endpoint(record: dict):
    bbox_values = record.get('bbox') or [0, 0, 0, 0]
    bbox_str = ",".join(map(str, bbox_values))

    metadata = {
        "element_id": _sanitize_metadata_value(record.get("id")),
        "page_name": _sanitize_metadata_value(record.get("page")),
        "intent": _sanitize_metadata_value(record.get("text")),
        "tag": "",
        "label_text": _sanitize_metadata_value(record.get("text")),
        "css_selector": "",
        "get_by_text": _sanitize_metadata_value(record.get("text")),
        "get_by_role": "",
        "xpath": "",
        "x": bbox_values[0],
        "y": bbox_values[1],
        "width": bbox_values[2],
        "height": bbox_values[3],
        "bbox": bbox_str,
        "position_relation": "",
        "html_snippet": "",
        "confidence_score": 0.0,
        "visibility_score": 0.0,
        "locator_stability_score": 0.0,
        "snapshot_id": "",
        "timestamp": "",
        "source_url": "",
        "used_in_tests": "",
        "last_tested": "",
        "healing_success_rate": 0.0,
        "region_image_path": _sanitize_metadata_value(record.get("region_image_path")),
        "locator": _sanitize_metadata_value(record.get("locator")),
        "ocr_type": _sanitize_metadata_value(record.get("ocr_type")), # ocr_type now comes from client
        "type": "ocr"
    }

    try:
        embedding_value = embedding_function([record["text"]])[0]
        collection.upsert(
            documents=[record["text"]],
            metadatas=[metadata],
            embeddings=[embedding_value],
            ids=[record["id"]]
        )
        return JSONResponse(content={"status": "success", "id": record["id"]})
    except Exception as e:
        error_logger.warning(f"upsert_text_record failed: {str(e)} | Record: {record}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/upsert-element-record")
async def upsert_element_record_endpoint(record: dict):
    document_content = record.get("html_snippet") or record.get("label_text") or record.get("intent")

    metadata = {
        "element_id": _sanitize_metadata_value(record.get("element_id")),
        "page_name": _sanitize_metadata_value(record.get("page_name")),
        "intent": _sanitize_metadata_value(record.get("intent")),
        "tag": _sanitize_metadata_value(record.get("tag")),
        "label_text": _sanitize_metadata_value(record.get("label_text")),
        "css_selector": _sanitize_metadata_value(record.get("css_selector")),
        "get_by_text": _sanitize_metadata_value(record.get("get_by_text")),
        "get_by_role": _sanitize_metadata_value(record.get("get_by_role")),
        "xpath": _sanitize_metadata_value(record.get("xpath")),
        "x": record.get("x") or 0,
        "y": record.get("y") or 0,
        "width": record.get("width") or 0,
        "height": record.get("height") or 0,
        "position_relation": _sanitize_metadata_value(record.get("position_relation")),
        "html_snippet": _sanitize_metadata_value(record.get("html_snippet")),
        "confidence_score": record.get("confidence_score") or 0.0,
        "visibility_score": record.get("visibility_score") or 0.0,
        "locator_stability_score": record.get("locator_stability_score") or 0.0,
        "snapshot_id": _sanitize_metadata_value(record.get("snapshot_id")),
        "timestamp": _sanitize_metadata_value(record.get("timestamp")),
        "source_url": _sanitize_metadata_value(record.get("source_url")),
        "used_in_tests": _sanitize_metadata_value(record.get("used_in_tests")),
        "last_tested": _sanitize_metadata_value(record.get("last_tested")),
        "healing_success_rate": record.get("healing_success_rate") or 0.0,
        "type": "locator"
    }

    try:
        embedding_value = record.get("combined_embedding") or record.get("text_embedding")
        if not embedding_value:
            embedding_value = embedding_function([document_content])[0]

        collection.upsert(
            documents=[document_content],
            metadatas=[metadata],
            embeddings=[embedding_value],
            ids=[record["element_id"]]
        )
        return JSONResponse(content={"status": "success", "id": record["element_id"]})
    except Exception as e:
        error_logger.warning(f"upsert_element_record failed: {str(e)} | Record: {record}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/fetch-ocr-entries")
async def fetch_ocr_entries_endpoint():
    try:
        results = collection.get(where={"type": "ocr"})
        ocr_entries = []
        for id_, doc, meta in zip(results["ids"], results["documents"], results["metadatas"]):
            ocr_entries.append({
                "id": id_,
                "text": doc,
                "page": meta.get("page_name", "")
            })
        return JSONResponse(content=ocr_entries)
    except Exception as e:
        error_logger.warning(f"fetch_ocr_entries failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/update-locator-by-text")
async def update_locator_by_text_endpoint(entry_id: str, locator: str):
    try:
        item = collection.get(ids=[entry_id])
        doc = item["documents"][0]
        meta = item["metadatas"][0]
        meta["locator"] = locator
        meta["source_type"] = "url"
        meta_sanitized = {k: _sanitize_metadata_value(v) for k, v in meta.items()}

        collection.upsert(
            documents=[doc],
            metadatas=[meta_sanitized],
            ids=[entry_id]
        )
        return JSONResponse(content={"status": "success", "id": entry_id})
    except Exception as e:
        error_logger.warning(f"_update_locator_by_text_sync failed: {str(e)} | ID: {entry_id}")
        raise HTTPException(status_code=500, detail=str(e))

EXPORT_PATH = Path("chromadb_export.json")

@router.get("/debug/export-chromadb")
async def export_chroma_data(
    record_type: str = Query(None, description="Filter by record type: 'ocr', 'locator', etc."),
    locator_null: bool = Query(False, description="Only include entries where locator is null"),
    page_name: str = Query(None, description="Filter by page name"),
    as_file: bool = Query(False, description="If true, return as downloadable JSON file")
):
    try:
        data = collection.get(include=["documents", "metadatas", "embeddings"])
        results = []

        for idx, meta in enumerate(data["metadatas"]):
            doc = data["documents"][idx]
            item = {"text": doc}
            item.update(meta)

            if record_type and item.get("type") != record_type:
                continue

            if locator_null and item.get("locator") not in [None, ""]:
                continue

            if page_name and item.get("page_name") != page_name:
                continue

            results.append(item)

        if as_file:
            with open(EXPORT_PATH, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            return FileResponse(EXPORT_PATH, filename="chromadb_export.json", media_type="application/json")

        return JSONResponse(content={"count": len(results), "data": results})

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

app.include_router(router)
