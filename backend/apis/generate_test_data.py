from fastapi import APIRouter, HTTPException, Depends
from pathlib import Path
import json
from sqlalchemy.orm import Session

from apis.projects_api import _ensure_project_structure, get_current_user, get_user_project
from database.models import User
from database.session import get_db
from utils.chroma_client import get_collection

router = APIRouter()

@router.post("/generate-test-data-from-chromadb")
def generate_test_data_from_chromadb(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = get_user_project(db, project_id, current_user)
    project_paths = _ensure_project_structure(project)
    collection = get_collection(project_paths["chroma_path"], "element_metadata")
    # Query all metadata for this project only
    all_records = collection.get(where={"project_id": project.id})
    metadatas = all_records.get("metadatas", [])
    
    # Filter for textbox or select, and build test data dict
    test_data = {}
    for meta in metadatas:
        ocr_type = (meta.get("ocr_type") or "").lower()
        label = meta.get("label_text") or meta.get("intent") or ""
        label = label.strip().replace(" ", "_").lower()
        if ocr_type in {"textbox", "select"} and label:
            test_data[label] = "fakedata"
    
    # Directory and file path (project-scoped)
    data_dir = Path(project_paths["project_root"]) / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    test_data_file = data_dir / "test_data.json"
    
    # Write out the JSON
    with open(test_data_file, "w", encoding="utf-8") as f:
        json.dump(test_data, f, indent=2)
    
    return {"status": "success", "file": str(test_data_file), "test_data": test_data}
