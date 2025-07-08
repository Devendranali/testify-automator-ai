import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_PATH = os.path.abspath(os.path.join(BASE_DIR, ".."))
DATA_PATH = os.path.join(ROOT_PATH, "data")
REGION_PATH = os.path.join(DATA_PATH, "regions")
CHROMA_PATH = os.path.join(DATA_PATH, "chroma_db")

os.makedirs(DATA_PATH + "/images", exist_ok=True)
os.makedirs(REGION_PATH, exist_ok=True)
os.makedirs(CHROMA_PATH, exist_ok=True)