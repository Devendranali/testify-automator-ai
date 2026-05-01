from __future__ import annotations

from contextvars import ContextVar
from pathlib import Path
from typing import Optional

from utils.project_paths import ProjectContext


_project_id_var: ContextVar[Optional[int]] = ContextVar("smartai_project_id", default=None)
_project_dir_var: ContextVar[Optional[str]] = ContextVar("smartai_project_dir", default=None)
_src_dir_var: ContextVar[Optional[str]] = ContextVar("smartai_src_dir", default=None)
_chroma_path_var: ContextVar[Optional[str]] = ContextVar("smartai_chroma_path", default=None)
_project_context_var: ContextVar[Optional[ProjectContext]] = ContextVar("smartai_project_context", default=None)


def set_request_context(
    project_context: Optional[ProjectContext] = None,
    project_id: Optional[int] = None,
    project_dir: Optional[Path | str] = None,
    src_dir: Optional[Path | str] = None,
    chroma_path: Optional[Path | str] = None,
):
    tokens = {}
    if project_context is not None:
        tokens["project_context"] = _project_context_var.set(project_context)
    if project_id is not None:
        tokens["project_id"] = _project_id_var.set(project_id)
    if project_dir is not None:
        tokens["project_dir"] = _project_dir_var.set(str(project_dir))
    if src_dir is not None:
        tokens["src_dir"] = _src_dir_var.set(str(src_dir))
    if chroma_path is not None:
        tokens["chroma_path"] = _chroma_path_var.set(str(chroma_path))
    return tokens


def reset_request_context(tokens: dict) -> None:
    if not tokens:
        return
    if "project_context" in tokens:
        _project_context_var.reset(tokens["project_context"])
    if "project_id" in tokens:
        _project_id_var.reset(tokens["project_id"])
    if "project_dir" in tokens:
        _project_dir_var.reset(tokens["project_dir"])
    if "src_dir" in tokens:
        _src_dir_var.reset(tokens["src_dir"])
    if "chroma_path" in tokens:
        _chroma_path_var.reset(tokens["chroma_path"])


def get_project_context(required: bool = False) -> Optional[ProjectContext]:
    ctx = _project_context_var.get()
    if ctx is None and required:
        raise RuntimeError("ProjectContext is required for this operation but was not set.")
    return ctx


def get_project_id() -> Optional[int]:
    ctx = _project_context_var.get()
    if ctx is not None:
        return ctx.project_id
    return _project_id_var.get()


def get_project_dir() -> Optional[str]:
    ctx = _project_context_var.get()
    if ctx is not None:
        return str(ctx.project_dir)
    return _project_dir_var.get()


def get_src_dir() -> Optional[str]:
    ctx = _project_context_var.get()
    if ctx is not None:
        return str(ctx.generated_src_dir)
    return _src_dir_var.get()


def get_chroma_path() -> Optional[str]:
    ctx = _project_context_var.get()
    if ctx is not None:
        return str(ctx.chroma_path)
    return _chroma_path_var.get()
