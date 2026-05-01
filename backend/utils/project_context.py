from typing import Any, Iterable, List, Mapping, Optional

from fastapi import HTTPException

from utils.request_context import get_project_context


def current_project_id(required: bool = False, *, allow_env_fallback: bool = False) -> Optional[int]:
    """Return the active project id from request-scoped context."""
    ctx = get_project_context(required=required)
    if ctx is not None:
        return ctx.project_id
    if required:
        raise HTTPException(status_code=400, detail="project_id is required")
    return None


def _extract_project_id_from_meta(meta: Mapping[str, Any]) -> Optional[int]:
    pid = meta.get("project_id")
    if pid is None:
        return None
    try:
        return int(pid)
    except (TypeError, ValueError):
        return None


def metadata_matches_current_project(meta: Mapping[str, Any]) -> bool:
    pid = current_project_id()
    if pid is None:
        return False
    meta_pid = _extract_project_id_from_meta(meta)
    return meta_pid == pid


def filter_metadata_by_project(metas: Iterable[Mapping[str, Any]]) -> List[Mapping[str, Any]]:
    """Return only the metadata entries that belong to the active project."""
    pid = current_project_id(required=True)
    filtered = []
    for meta in metas:
        if not isinstance(meta, Mapping):
            continue
        if _extract_project_id_from_meta(meta) == pid:
            filtered.append(meta)
    return filtered
