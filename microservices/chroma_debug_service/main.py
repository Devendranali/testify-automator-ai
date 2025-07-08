from fastapi import APIRouter, Query, FastAPI
from fastapi.responses import JSONResponse, FileResponse
import json
from pathlib import Path
import os
import chromadb
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Chroma Debug Service")

# ChromaDB setup
# This will connect to the chromadb service running in docker-compose
chroma_client = chromadb.HttpClient(host=os.getenv("CHROMA_DB_HOST", "chromadb"), port=os.getenv("CHROMA_DB_PORT", "8000"))

# Placeholder for collection - in a real scenario, this would be properly initialized
# or passed from a service layer.
# For now, we'll assume a default collection name.
# You might need to adjust this based on how your chroma_service.py initializes it.
# For simplicity, I'm using a direct get_or_create_collection here.
# In a more robust setup, you'd have a dedicated ChromaDB client/service module.

try:
    collection = chroma_client.get_or_create_collection(name="element_metadata")
except Exception as e:
    print(f"Error connecting to ChromaDB or getting collection: {e}")
    collection = None # Handle case where ChromaDB is not available


EXPORT_PATH = Path("chromadb_export.json")

@app.get("/debug/export-chromadb")
async def export_chroma_data(
    record_type: str = Query(None, description="Filter by record type: 'ocr', 'locator', etc."),
    locator_null: bool = Query(False, description="Only include entries where locator is null"),
    page_name: str = Query(None, description="Filter by page name"),
    as_file: bool = Query(False, description="If true, return as downloadable JSON file")
):
    if collection is None:
        return JSONResponse(status_code=500, content={"error": "ChromaDB collection not initialized."})

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003) # Using a different port for the new service