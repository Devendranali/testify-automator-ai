# microservices/image_ml_service/main.py

from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.responses import JSONResponse
from typing import List
from PIL import Image
import os, zipfile, tempfile, json, logging
from dotenv import load_dotenv
from datetime import datetime

# Local imports - these files will be moved into this service
from logic.image_text_extractor import process_image_gpt
# Assuming yolo_detector and ocr_type_classifier are used internally by image_text_extractor
# from services.yolo_detector import YOLODetector
# from services.ocr_type_classifier import OCRTypeClassifier
from utils.match_utils import normalize_page_name

load_dotenv()

app = FastAPI(title="Image ML Service")

# Logging
os.makedirs("data", exist_ok=True)
file_handler = logging.FileHandler("upload_image_logs.txt", encoding="utf-8")
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.addHandler(file_handler)

# Define DATA_PATH locally for this service
DATA_PATH = "./data"
os.makedirs(os.path.join(DATA_PATH, "images"), exist_ok=True)
os.makedirs(os.path.join(DATA_PATH, "regions"), exist_ok=True)


@app.post("/upload-image")
async def upload_image(
    images: List[UploadFile] = File(...),
    ordered_images: str = Form(None)
):
    results = []
    ordered_image_list = []

    # Step 1: Parse frontend ordering
    if ordered_images:
        try:
            parsed_json = json.loads(ordered_images)
            ordered_image_list = parsed_json.get("ordered_images", [])
            ordered_image_list = [os.path.basename(f) for f in ordered_image_list]
            logger.info(f"🟢 Ordered images from frontend: {ordered_image_list}")
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
        extracted_images = [f for f in os.listdir(temp_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp'))]
        image_names = ordered_image_list if ordered_image_list else sorted(extracted_images)

        all_raw_metadata = []

        # Step 4: Process images in order using GPT-4o
        for image_name in image_names:
            image_path = os.path.join(temp_dir, image_name)
            if not os.path.exists(image_path):
                logger.warning(f"⚠️ Skipping missing image: {image_name}")
                continue

            with Image.open(image_path) as img:
                logger.debug(f"📷 Processing image: {image_name}")

                permanent_image_path = os.path.join(DATA_PATH, "images", image_name)
                img.save(permanent_image_path)

                # GPT image extraction
                metadata_list = await process_image_gpt(
                    img, image_name,
                    image_path=permanent_image_path,
                    debug_log_path=os.path.join(DATA_PATH, f"metadata_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json") # Adjusted path
                )

                all_raw_metadata.append({
                    "image_name": image_name,
                    "metadata": metadata_list
                })

                # NOTE: ChromaDB integration will be handled by a separate service.
                # For now, we'll just return the metadata.
                results.extend(metadata_list) # Use extend as metadata_list is already a list of dicts

            image_file_map[image_name] = (image_path, normalize_page_name(image_name))
            actual_received_images.append(image_name)

        # Save raw GPT data to a single file
        raw_data_file_path = os.path.join(DATA_PATH, "raw_data_from_gpt.json")
        with open(raw_data_file_path, "w", encoding="utf-8") as f:
            json.dump(all_raw_metadata, f, indent=2, ensure_ascii=False)
        logger.info(f"📝 Saved all raw GPT metadata to {raw_data_file_path}")

        # NOTE: Dependency graph and image order logging will be handled by the orchestrator/API Gateway.
        # For now, we'll omit them from this service.

        return JSONResponse(content={"status": "success", "data": results})

    except Exception as e:
        logger.error("❌ Error in upload_image", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
