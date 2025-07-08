import os
import re
from pathlib import Path
from dotenv import load_dotenv
from chromadb import PersistentClient
from openai import OpenAI
from utils.match_utils import normalize_page_name

load_dotenv()

project_root = Path(__file__).resolve().parents[1]
chroma_client = PersistentClient(path=str(project_root / "data" / "chroma_db"))
collection = chroma_client.get_or_create_collection("element_metadata")
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
openai_client = client  # <-- Add this line

def get_class_name(page_name: str) -> str:
    return f"Saucedemo_{page_name}Page"

def filter_all_pages():
    records = collection.get()
    return list(set(normalize_page_name(meta.get("page_name", "unknown")) for meta in records.get("metadatas", [])))

__all__ = ["openai_client", "collection", "filter_all_pages", "get_class_name"]