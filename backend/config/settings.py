import os

from utils.request_context import get_project_context

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_PATH = os.path.abspath(os.path.join(BASE_DIR, ".."))

# Lazy path helpers; do not create folders at import-time
DATA_PATH = os.path.join(ROOT_PATH, "data")
REGION_PATH = os.path.join(DATA_PATH, "regions")
CHROMA_PATH = os.path.join(DATA_PATH, "chroma_db")

def get_data_path() -> str:
    ctx = get_project_context(required=True)
    return str(ctx.data_path)

def get_region_path() -> str:
    ctx = get_project_context(required=True)
    return os.path.join(str(ctx.data_path), "regions")

def get_chroma_path() -> str:
    ctx = get_project_context(required=True)
    return str(ctx.chroma_path)


def get_backend_public_base_url(default: str | None = None) -> str:
    configured = (os.getenv("BACKEND_PUBLIC_BASE_URL") or "").strip()
    base_url = configured or (default or "").strip()
    if not base_url:
        raise RuntimeError(
            "BACKEND_PUBLIC_BASE_URL is required for backend-generated external URLs."
        )
    return base_url.rstrip("/")


def get_allowed_jira_hosts() -> set[str]:
    raw = os.getenv("ALLOWED_JIRA_HOSTS", "")
    return {
        host.strip().lower()
        for host in raw.split(",")
        if host and host.strip()
    }
