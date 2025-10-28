# image_text_api.py

import numpy as np
from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from fastapi.responses import JSONResponse
from typing import List
from PIL import Image
import os
import zipfile
import tempfile
import json
import logging
from dotenv import load_dotenv
from logic.image_text_extractor import process_image_gpt
from services.graph_service import build_dependency_graph
from utils.match_utils import normalize_page_name
from config.settings import get_data_path, get_chroma_path
import chromadb
from datetime import datetime
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
import re

load_dotenv()

router = APIRouter()

# Logging (project-scoped)
log_path = os.path.join(get_data_path(), "upload_image_logs.txt")
os.makedirs(os.path.dirname(log_path), exist_ok=True)
file_handler = logging.FileHandler(log_path, encoding="utf-8")
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.addHandler(file_handler)

# ChromaDB setup
embedding_function = SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
chroma_client = chromadb.PersistentClient(path=get_chroma_path())
chroma_collection = chroma_client.get_or_create_collection(name="element_metadata", embedding_function=embedding_function)


@router.post("/upload-image")
async def upload_image(
    images: List[UploadFile] = File(...),
    ordered_images: str = Form(None)
):
    # Require an active project so we don't write to repo-level defaults
    if not os.environ.get("SMARTAI_PROJECT_DIR") or not os.environ.get("SMARTAI_SRC_DIR"):
        raise HTTPException(status_code=400, detail="No active project. Start a project first (POST /projects/save-details).")
    dp = get_data_path()
    os.makedirs(os.path.join(dp, "regions"), exist_ok=True)
    os.makedirs(os.path.join(dp, "images"), exist_ok=True)
    results = []
    ordered_image_list = []

    # Step 1: Parse frontend ordering
    if ordered_images:
        try:
            parsed_json = json.loads(ordered_images)
            ordered_image_list = parsed_json.get("ordered_images", [])
            ordered_image_list = [os.path.basename(
                f) for f in ordered_image_list]
            logger.info(
                f"🟢 Ordered images from frontend: {ordered_image_list}")
        except Exception as parse_err:
            logger.warning(f"⚠️ Failed to parse ordered_images: {parse_err}")
            ordered_image_list = []

    # Step 2: Extract uploaded files
    temp_dir = tempfile.mkdtemp()
    image_file_map = {}
    actual_received_images = []

    try:
        for file in images:
            filename = file.filename.lower()
            if filename.endswith(".zip"):
                with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp_zip:
                    tmp_zip.write(await file.read())
                    tmp_zip_path = tmp_zip.name
                with zipfile.ZipFile(tmp_zip_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_dir)
            else:
                if filename.endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp')):
                    file_path = os.path.join(temp_dir, filename)
                    with open(file_path, "wb") as out_file:
                        out_file.write(await file.read())

        # Step 3: Final image order
        extracted_images = [f for f in os.listdir(temp_dir) if f.lower().endswith(
            ('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp'))]
        image_names = ordered_image_list if ordered_image_list else sorted(
            extracted_images)

        # Group images by normalized page_name
        page_images = {}
        for image_name in image_names:
            page_name = normalize_page_name(image_name)
            page_images.setdefault(page_name, []).append(image_name)

        # For saving all raw metadata
        # all_raw_metadata = []

        # Step 4: Process images grouped by logical page
        for page_name, image_group in page_images.items():
            # Fetch existing label_texts for this page from chroma
            try:
                existing = chroma_collection.get(
                    where={"page_name": page_name})
                existing_label_texts = set(
                    m["label_text"].strip().lower()
                    for m in (existing["metadatas"] or [])
                    if m and m.get("label_text")
                )
            except Exception as fetch_err:
                logger.warning(
                    f"⚠️ Failed to fetch existing metadatas for {page_name}: {fetch_err}")
                existing_label_texts = set()

            # For each image for this logical page
            for image_name in image_group:
                image_path = os.path.join(temp_dir, image_name)
                if not os.path.exists(image_path):
                    logger.warning(f"⚠️ Skipping missing image: {image_name}")
                    continue

                with Image.open(image_path) as img:
                    logger.debug(f"📷 Processing image: {image_name}")

                    permanent_image_path = os.path.join(
                        get_data_path(), "images", image_name)
                    img.save(permanent_image_path)

                    # timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    # DEBUG_LOG_PATH = f"./data/metadata_logs_{timestamp}.json"

                    # GPT image extraction
                    metadata_list = await process_image_gpt(
                        img, image_name,
                        image_path=permanent_image_path,
                        # debug_log_path=DEBUG_LOG_PATH
                    )                    

                    # Save per-image metadata to data/stored/timestamp_imageName.json
                    def to_serializable(obj):
                        if isinstance(obj, np.ndarray):
                            return obj.tolist()
                        if isinstance(obj, (set,)):
                            return list(obj)
                        return obj
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    base_image_name = os.path.splitext(os.path.basename(image_name))[0]
                    os.makedirs(os.path.join(get_data_path(), "stored"), exist_ok=True)
                    out_file = os.path.join(
                        get_data_path(), "stored", f"{timestamp}_{base_image_name}.json")
                    with open(out_file, "w", encoding="utf-8") as f:
                        json.dump(metadata_list, f, indent=4, ensure_ascii=False, default=to_serializable)

                    
                    
                    
                    # all_raw_metadata.append({
                    #     "image_name": image_name,
                    #     "metadata": metadata_list
                    # })

                    # # Only add new label_texts for this logical page
                    # for metadata in metadata_list:
                    #     original_label_text = metadata.get("label_text", "")
                    #     cleaned_label_text = clean_label_text(
                    #         original_label_text)
                    #     # Overwrite with cleaned version
                    #     metadata["label_text"] = cleaned_label_text
                    #     if cleaned_label_text and cleaned_label_text not in existing_label_texts:
                    #         chroma_collection.add(
                    #             ids=[metadata["id"]],
                    #             documents=[metadata["text"]],
                    #             metadatas=[metadata]
                    #         )
                    #         results.append(metadata)
                    #         existing_label_texts.add(cleaned_label_text)

                image_file_map[image_name] = (image_path, page_name)
                actual_received_images.append(image_name)

        # # Save all raw GPT metadata to a single file
        # raw_data_file_path = os.path.join("data", "raw_data_from_gpt.json")
        # with open(raw_data_file_path, "w", encoding="utf-8") as f:
        #     json.dump(all_raw_metadata, f, indent=2, ensure_ascii=False)
        # logger.info(f"📝 Saved all raw GPT metadata to {raw_data_file_path}")

        # Step 5: Store dependency graph
        if ordered_image_list:
            build_dependency_graph(
                ordered_image_list, output_path=os.path.join(get_data_path(), "dependency_graph.json"))
            logger.info(
                "📄 Dependency graph stored in data/dependency_graph.json")

        # Step 6: Log order metadata
        order_json_path = os.path.join(get_data_path(), "image_order.json")
        with open(order_json_path, "w") as f:
            json.dump({
                "ordered_from_frontend": ordered_image_list,
                "processed_order": actual_received_images
            }, f, indent=2)
        logger.info("📄 Ordered images logged to data/image_order.json")

        return JSONResponse(content={"status": "success", "data": results})

    except Exception as e:
        logger.error("❌ Error in upload_image", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))



def clean_label_text(text: str) -> str:
    # Remove leading/trailing numbers, dots, dashes, and spaces
    cleaned = re.sub(r"^[\s\W\d_]+|[\s\W\d_]+$", "", text, flags=re.UNICODE)
    return cleaned
