from fastapi import APIRouter, Query, Depends, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from utils.chroma_client import get_collection
import json
from pathlib import Path
from sqlalchemy.orm import Session

from database.session import get_db
from apis.projects_api import _ensure_project_structure, get_current_user, get_project_by_projectId
from database.models import User

router = APIRouter()

EXPORT_PATH = Path("chromadb_export.json")

@router.get("/debug/export-chromadb")
async def export_chroma_data(
    project_id: int = Query(..., description="Project ID to scope the export to"),
    record_type: str = Query(None, description="Filter by record type: 'ocr', 'locator', etc."),
    locator_null: bool = Query(False, description="Only include entries where locator is null"),
    page_name: str = Query(None, description="Filter by page name"),
    as_file: bool = Query(False, description="If true, return as downloadable JSON file"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        project = get_project_by_projectId(db, project_id, current_user)
        project_paths = _ensure_project_structure(project)
        chroma_collection = get_collection(project_paths["chroma_path"], "element_metadata")
        data = chroma_collection.get(
            where={"project_id": project_id},
            include=["documents", "metadatas", "embeddings"],
        )
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
