
import numpy as np
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))
import json
import orjson
from utils.match_utils import normalize_page_name
from chromadb import PersistentClient

chroma_client = PersistentClient(path="data/chroma_db")
collection = chroma_client.get_or_create_collection("element_metadata")

# Helper function
def convert_np(obj):
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, (np.float32, np.float64)):
        return float(obj)
    if isinstance(obj, (np.int32, np.int64)):
        return int(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


page1_data = collection.get(where={"page_name": 'login'})
page2_data = collection.get(where={"page_name": 'inventory'})

# Ensure 'apis' folder exists!
Path("apis").mkdir(parents=True, exist_ok=True)

# Save to 'page1_data.json' in the current folder
with open("apis/login.json", "w", encoding="utf-8") as f:
    json.dump(page1_data, f, indent=4, ensure_ascii=False, default=convert_np)

# Save to 'page2_data.json' in the current folder
with open("apis/inventory.json", "w", encoding="utf-8") as f:
    json.dump(page2_data, f, indent=4, ensure_ascii=False, default=convert_np)

# # Save to 'data.json' in the current folder
# with open("apis/data.json", "wb") as f:
#     f.write(orjson.dumps(page_data, option=orjson.OPT_INDENT_2))

# print(page_data)