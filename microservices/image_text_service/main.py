
from fastapi import APIRouter, UploadFile, File, HTTPException, Form, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import List
from PIL import Image
import os, zipfile, tempfile, json, logging
from dotenv import load_dotenv
from datetime import datetime
import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(title="Image Text Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Logging setup
os.makedirs("data", exist_ok=True)
file_handler = logging.FileHandler("upload_image_logs.txt", encoding="utf-8")
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.addHandler(file_handler)

# ChromaDB setup
# This will connect to the chromadb service running in docker-compose
chroma_client = chromadb.HttpClient(host=os.getenv("CHROMA_DB_HOST", "chromadb"), port=os.getenv("CHROMA_DB_PORT", "8000"))
embedding_function = SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
chroma_collection = chroma_client.get_or_create_collection(
    name="element_metadata",
    embedding_function=embedding_function
)

# Placeholder for DATA_PATH - will be handled by environment variable or config
DATA_PATH = os.getenv("DATA_PATH", "./data")

# Placeholder for imported functions - these files will be copied or refactored
# For now, we'll assume they are available in the same directory or via PYTHONPATH
# In a real microservice, these would be part of this service's codebase or a shared library.

# --- Start of copied functions/classes from backend/logic, services, utils, config ---
# These should ideally be moved to this service's directory or a shared library.
# For now, I'm putting them here as placeholders.

# From backend/logic/image_text_extractor.py
async def process_image_gpt(img, image_name, image_path, debug_log_path):
    # This is a placeholder. The actual implementation from image_text_extractor.py
    # needs to be copied here or refactored into a shared module.
    # For now, returning dummy data to allow the service to start.
    logger.warning("Using dummy process_image_gpt. Actual implementation needs to be copied.")
    return [{"id": f"{image_name}_dummy_id", "text": "dummy text", "metadata": {"image_name": image_name}}]

# From backend/services/graph_service.py
def build_dependency_graph(ordered_image_list, output_path):
    logger.warning("Using dummy build_dependency_graph. Actual implementation needs to be copied.")
    with open(output_path, "w") as f:
        json.dump({"graph": "dummy"}, f)

# From backend/utils/match_utils.py
def normalize_page_name(image_name):
    logger.warning("Using dummy normalize_page_name. Actual implementation needs to be copied.")
    return image_name.replace(".png", "").replace(".jpg", "")

# --- End of copied functions/classes ---


@app.post("/upload-image")
async def upload_image(
    images: List[UploadFile] = File(...),
    ordered_images: str = Form(None)
):
    os.makedirs(os.path.join(DATA_PATH, "regions"), exist_ok=True)
    os.makedirs(os.path.join(DATA_PATH, "images"), exist_ok=True)
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

                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                DEBUG_LOG_PATH = f"{DATA_PATH}/metadata_logs_{timestamp}.json"

                # GPT image extraction
                metadata_list = await process_image_gpt(
                    img, image_name,
                    image_path=permanent_image_path,
                    debug_log_path=DEBUG_LOG_PATH
                )

                all_raw_metadata.append({
                    "image_name": image_name,
                    "metadata": metadata_list
                })

                for metadata in metadata_list:
                    chroma_collection.add(
                        ids=[metadata["id"]],
                        documents=[metadata["text"]],
                        metadatas=[metadata]
                    )
                    results.append(metadata)

            image_file_map[image_name] = (image_path, normalize_page_name(image_name))
            actual_received_images.append(image_name)

        raw_data_file_path = os.path.join(DATA_PATH, "raw_data_from_gpt.json")
        with open(raw_data_file_path, "w", encoding="utf-8") as f:
            json.dump(all_raw_metadata, f, indent=2, ensure_ascii=False)
        logger.info(f"📝 Saved all raw GPT metadata to {raw_data_file_path}")

        # Step 5: Store dependency graph
        if ordered_image_list:
            build_dependency_graph(ordered_image_list, output_path=os.path.join(DATA_PATH, "dependency_graph.json"))
            logger.info("📄 Dependency graph stored in data/dependency_graph.json")

        # Step 6: Log order metadata
        order_json_path = os.path.join(DATA_PATH, "image_order.json")
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002) # Using a different port for the new service
