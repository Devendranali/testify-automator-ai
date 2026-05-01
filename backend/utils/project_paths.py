from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from database.models import Organization, OrganizationMember, Project, User


@dataclass(frozen=True)
class ProjectContext:
    org_id: int
    project_id: int
    org_slug: str
    project_slug: Optional[str]
    project_dir: Path
    chroma_path: Path
    data_path: Path
    prompts_path: Path
    generated_src_dir: Path
    metadata_dir: Path
    logs_dir: Path


def _org_slug(name: str) -> str:
    normalized = (name or "").strip().lower()
    return re.sub(r"[^a-z0-9_-]+", "-", normalized) or "default"


def _project_dir_segment(project: Project) -> str:
    base_slug = (project.slug or Project.normalized_key(project.project_name)).strip()
    base_slug = re.sub(r"[^a-z0-9_-]+", "-", base_slug.lower()) or "project"
    if project.id:
        return f"{project.id}-{base_slug}"
    return base_slug


def _project_root(project: Project, org_slug: str) -> Path:
    backend_root = Path(__file__).resolve().parents[1]
    org_root = backend_root / "organizations" / org_slug
    desired = org_root / _project_dir_segment(project)

    legacy = org_root / project.project_name.strip()
    if legacy.exists() and not desired.exists():
        desired.parent.mkdir(parents=True, exist_ok=True)
        try:
            legacy.rename(desired)
        except Exception:
            return legacy
    return desired


def _context_from_project(project: Project, org_slug: str) -> ProjectContext:
    project_dir = _project_root(project, org_slug).resolve()
    data_path = project_dir / "data"
    generated_src_dir = project_dir / "generated_runs" / "src"
    prompts_path = generated_src_dir / "prompts"
    metadata_dir = generated_src_dir / "metadata"
    logs_dir = project_dir / "logs"
    chroma_path = data_path / "chroma_db"

    return ProjectContext(
        org_id=project.organization_id,
        project_id=project.id,
        org_slug=org_slug,
        project_slug=project.slug or Project.normalized_key(project.project_name),
        project_dir=project_dir,
        chroma_path=chroma_path,
        data_path=data_path,
        prompts_path=prompts_path,
        generated_src_dir=generated_src_dir,
        metadata_dir=metadata_dir,
        logs_dir=logs_dir,
    )


def build_project_context(user: User, project_id: int, db_session: Session) -> ProjectContext:
    if user is None or project_id is None:
        raise HTTPException(status_code=400, detail="User and project_id are required")
    org_ids = OrganizationMember.user_org_ids(db_session, user.id)
    if not org_ids:
        raise HTTPException(status_code=403, detail="Organization membership required")

    project = (
        db_session.query(Project)
        .filter(Project.id == int(project_id), Project.organization_id.in_(org_ids))
        .first()
    )
    if not project:
        raise HTTPException(status_code=403, detail="You do not have access to this project")

    org = db_session.query(Organization).filter(Organization.id == project.organization_id).first()
    org_slug = org.slug if org and org.slug else _org_slug(project.organization)

    return _context_from_project(project, org_slug)
