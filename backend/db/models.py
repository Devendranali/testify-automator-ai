from datetime import datetime
import re
from typing import Optional

from sqlalchemy import Column, DateTime, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import validates

from .session import Base


def _normalize_project_name(name: str) -> str:
    """Normalize project names for uniqueness checks."""
    return re.sub(r"\s+", " ", name or "").strip().lower()


class Project(Base):
    __tablename__ = "projects"
    __table_args__ = (
        UniqueConstraint("project_key", name="uq_projects_project_key"),
    )

    id = Column(Integer, primary_key=True, index=True)
    project_name = Column(String(255), nullable=False)
    project_key = Column(String(255), nullable=False)
    framework = Column(String(100), nullable=False)
    language = Column(String(100), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    @validates("project_name")
    def _validate_project_name(self, key, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("project_name is required")
        normalized = _normalize_project_name(value)
        self.project_key = normalized
        return value.strip()

    @validates("framework")
    def _validate_framework(self, key, value: str) -> str:
        return (value or "").strip()

    @validates("language")
    def _validate_language(self, key, value: str) -> str:
        return (value or "").strip()

    @classmethod
    def normalized_key(cls, name: Optional[str]) -> str:
        return _normalize_project_name(name or "")

    @property
    def slug(self) -> str:
        return self.project_key.replace(" ", "_")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "project_name": self.project_name,
            "framework": self.framework,
            "language": self.language,
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
            "updated_at": self.updated_at.isoformat() if isinstance(self.updated_at, datetime) else self.updated_at,
        }
