# utils/metadata_io.py

import os
import json
from pathlib import Path

METADATA_DIR = Path("generated_runs/src/metadata")


def ensure_metadata_dir():
    METADATA_DIR.mkdir(parents=True, exist_ok=True)


def get_metadata_filepath(page_name):
    ensure_metadata_dir()
    return METADATA_DIR / f"{page_name}_enriched.json"


def save_metadata(page_name, metadata):
    path = get_metadata_filepath(page_name)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)


def load_metadata(page_name):
    path = get_metadata_filepath(page_name)
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None
