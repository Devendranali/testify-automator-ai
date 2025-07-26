import json
from pathlib import Path

STATUS_FILE = Path("generated_runs/src/metadata/enrichment_status.json")


def load_status():
    if STATUS_FILE.exists():
        return json.loads(STATUS_FILE.read_text())
    return {}


def save_status(status):
    STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATUS_FILE.write_text(json.dumps(status, indent=2))


def is_enriched(page_name):
    status = load_status()
    return status.get(page_name, False)


def set_enriched(page_name, value=True):
    status = load_status()
    status[page_name] = value
    save_status(status)


def reset_enriched(page_name):
    status = load_status()
    if page_name in status:
        del status[page_name]
        save_status(status)
