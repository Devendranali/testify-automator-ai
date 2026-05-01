"""
Utility helpers for generating and managing test case metadata identifiers.
"""

from __future__ import annotations

import re
import uuid
from typing import Optional

from sqlalchemy.orm import Session

from database.models import TestCaseMetadata


def _sanitize_display_part(value: Optional[str]) -> str:
    tokens = re.findall(r"[A-Za-z0-9]+", (value or "").strip())
    if not tokens:
        return "STORY"
    return "_".join(tokens[:3]).upper()


def generate_case_uuid(preferred: Optional[str] = None) -> str:
    cleaned = (preferred or "").strip()
    if cleaned:
        return cleaned
    return str(uuid.uuid4())


def generate_display_name(test_type: Optional[str], user_story: Optional[str], case_uuid: str) -> str:
    prefix = (test_type or "TC").upper()
    story_part = _sanitize_display_part(user_story)
    suffix = case_uuid.replace("-", "")[:8].upper()
    return f"{prefix}_{story_part}_{suffix}"


def normalize_test_name(value: Optional[str], fallback: Optional[str]) -> str:
    base = (value or fallback or "").strip()
    base = re.sub(r"[^\w]+", "_", base)
    base = re.sub(r"_+", "_", base).strip("_")
    if not base:
        base = "test_case"
    if not base.lower().startswith("test_"):
        base = f"test_{base}"
    if base[0].isdigit():
        base = f"test_{base}"
    return base.lower()


def ensure_unique_test_name(db: Session, project_id: int, base_name: str) -> str:
    candidate = base_name
    counter = 1
    while (
        db.query(TestCaseMetadata)
        .filter(TestCaseMetadata.project_id == project_id, TestCaseMetadata.test_name == candidate)
        .first()
    ):
        counter += 1
        candidate = f"{base_name}_{counter}"
    return candidate


def ensure_unique_display_name(db: Session, project_id: int, base_name: str) -> str:
    candidate = base_name
    counter = 1
    while (
        db.query(TestCaseMetadata)
        .filter(TestCaseMetadata.project_id == project_id, TestCaseMetadata.display_name == candidate)
        .first()
    ):
        counter += 1
        candidate = f"{base_name}_{counter}"
    return candidate
