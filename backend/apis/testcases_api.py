from __future__ import annotations

from typing import List, Optional

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Path as PathParam, status
from pydantic import BaseModel, Field, validator
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, load_only

from database.models import Project, TestCaseMetadata, User
from database.session import get_db
from .projects_api import _ensure_project_structure, get_current_user, get_user_project
from utils.testcase_utils import (
    ensure_unique_display_name,
    ensure_unique_test_name,
    generate_case_uuid,
    generate_display_name,
    normalize_test_name,
)

router = APIRouter()


class StepPayload(BaseModel):
    action: str
    data: dict = Field(default_factory=dict)

    @validator("action")
    def action_required(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("action is required for each step")
        return value.strip()

    @validator("data")
    def validate_drag_and_drop(cls, data, values):
        action = (values.get("action") or "").strip().upper()
        data = data or {}
        if action == "DRAG_AND_DROP":
            source = data.get("source") or {}
            target = data.get("target") or {}
            if not isinstance(source, dict) or not isinstance(target, dict):
                raise ValueError("DRAG_AND_DROP requires source and target objects")
            if not source.get("selector") or not source.get("selector_type"):
                raise ValueError("DRAG_AND_DROP source requires selector and selector_type")
            if not target.get("selector") or not target.get("selector_type"):
                raise ValueError("DRAG_AND_DROP target requires selector and selector_type")
        return data


class TestCasePayload(BaseModel):
    test_name: Optional[str] = Field(None, max_length=1024)
    user_story: str
    auto_testcase: str
    steps: Optional[List[StepPayload]] = None
    tags: Optional[List[str]] = Field(default_factory=list)
    markers: Optional[List[str]] = Field(default_factory=list)
    priority: Optional[str]
    test_type: Optional[str] = Field(None, max_length=32)
    case_uuid: Optional[str] = None
    script_path: Optional[str] = None
    runner_script_path: Optional[str] = None

    @validator("user_story", "auto_testcase")
    def must_not_be_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("Value must not be blank")
        return value.strip()


class TestCaseCreatePayload(TestCasePayload):
    case_uuid: Optional[str] = Field(default=None)


class TestCaseUpdatePayload(TestCasePayload):
    pass


def _ensure_project_testcase(
    db: Session,
    project_id: int,
    payload: TestCasePayload,
    case_uuid: Optional[str] = None,
    script_path: Optional[str] = None,
    runner_script_path: Optional[str] = None,
) -> TestCaseMetadata:
    case_uuid = generate_case_uuid(case_uuid)
    base_display_name = generate_display_name(payload.test_type, payload.user_story, case_uuid)
    display_name = ensure_unique_display_name(db, project_id, base_display_name)
    normalized_test_name = normalize_test_name(payload.test_name, display_name)
    unique_test_name = ensure_unique_test_name(db, project_id, normalized_test_name)

    record = TestCaseMetadata(
        project_id=project_id,
        case_uuid=case_uuid,
        test_name=unique_test_name,
        display_name=display_name,
            user_story=payload.user_story,
            auto_testcase=payload.auto_testcase,
            steps_json=[step.dict() for step in (payload.steps or [])] if payload.steps else None,
            test_type=payload.test_type or "ui",
                tags=[t.strip() for t in (payload.tags or []) if t and t.strip()],
                markers=[t.strip() for t in (payload.markers or []) if t and t.strip()],
                priority=payload.priority or "Low",
                script_path=script_path,
                runner_script_path=runner_script_path,
            )
    return record


def _normalize_script_path(project_src_dir: str, script_path: Optional[str]) -> Optional[str]:
    if not script_path:
        return None
    base_dir = Path(project_src_dir).resolve()
    candidate = Path(script_path)
    if not candidate.is_absolute():
        candidate = (base_dir / script_path).resolve()
    try:
        relative = candidate.relative_to(base_dir)
    except ValueError:
        return None
    return relative.as_posix()


def _ensure_project_exists(
    db: Session,
    project_id: int,
    current_user: User,
) -> Project:
    project = get_user_project(db, project_id, current_user)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    return project


@router.get("/projects/{project_id}/testcases")
def list_test_cases(
    project_id: int = PathParam(..., ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = _ensure_project_exists(db, project_id, current_user)
    records = (
        db.query(TestCaseMetadata)
        .options(
            load_only(
                TestCaseMetadata.id,
                TestCaseMetadata.project_id,
                TestCaseMetadata.case_uuid,
                TestCaseMetadata.test_name,
                TestCaseMetadata.display_name,
                TestCaseMetadata.user_story,
                TestCaseMetadata.auto_testcase,
                TestCaseMetadata.test_type,
                TestCaseMetadata.markers,
                TestCaseMetadata.tags,
                TestCaseMetadata.priority,
                TestCaseMetadata.script_path,
                TestCaseMetadata.runner_script_path,
                TestCaseMetadata.created_at,
                TestCaseMetadata.updated_at,
            )
        )
        .filter(TestCaseMetadata.project_id == project.id)
        .order_by(TestCaseMetadata.updated_at.desc())
        .all()
    )
    return {"testcases": [record.to_dict() for record in records]}


@router.get("/projects/{project_id}/testcases/{case_uuid}")
def get_test_case(
    project_id: int = PathParam(..., ge=1),
    case_uuid: str = PathParam(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = _ensure_project_exists(db, project_id, current_user)
    record = (
        db.query(TestCaseMetadata)
        .options(
            load_only(
                TestCaseMetadata.id,
                TestCaseMetadata.project_id,
                TestCaseMetadata.case_uuid,
                TestCaseMetadata.test_name,
                TestCaseMetadata.display_name,
                TestCaseMetadata.user_story,
                TestCaseMetadata.auto_testcase,
                TestCaseMetadata.test_type,
                TestCaseMetadata.markers,
                TestCaseMetadata.tags,
                TestCaseMetadata.priority,
                TestCaseMetadata.script_path,
                TestCaseMetadata.runner_script_path,
                TestCaseMetadata.created_at,
                TestCaseMetadata.updated_at,
            )
        )
        .filter(TestCaseMetadata.project_id == project.id, TestCaseMetadata.case_uuid == case_uuid)
        .first()
    )
    if not record:
        raise HTTPException(status_code=404, detail="Test case not found.")
    return {"testcase": record.to_dict()}


@router.post("/projects/{project_id}/testcases", status_code=status.HTTP_201_CREATED)
def create_test_case(
    payload: TestCaseCreatePayload,
    project_id: int = PathParam(..., ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = _ensure_project_exists(db, project_id, current_user)
    project_paths = _ensure_project_structure(project)
    script_path_value = _normalize_script_path(project_paths["src_dir"], payload.script_path)
    if payload.script_path and not script_path_value:
        raise HTTPException(status_code=400, detail="Invalid script_path value.")
    runner_script_path_value = _normalize_script_path(project_paths["src_dir"], payload.runner_script_path)
    record = _ensure_project_testcase(
        db,
        project.id,
        payload,
        payload.case_uuid,
        script_path=script_path_value,
        runner_script_path=runner_script_path_value,
    )
    try:
        db.add(record)
        db.flush()
    except IntegrityError as err:
        db.rollback()
        raise HTTPException(status_code=409, detail="Unable to save test case.") from err
    db.refresh(record)
    return {"testcase": record.to_dict()}


@router.put("/projects/{project_id}/testcases/{case_uuid}")
def update_test_case(
    payload: TestCaseUpdatePayload,
    project_id: int = PathParam(..., ge=1),
    case_uuid: str = PathParam(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = _ensure_project_exists(db, project_id, current_user)
    project_paths = _ensure_project_structure(project)
    script_path_value = _normalize_script_path(project_paths["src_dir"], payload.script_path)
    runner_script_path_value = _normalize_script_path(project_paths["src_dir"], payload.runner_script_path)
    if payload.script_path and not script_path_value:
        raise HTTPException(status_code=400, detail="Invalid script_path value.")
    record = (
        db.query(TestCaseMetadata)
        .filter(TestCaseMetadata.project_id == project.id, TestCaseMetadata.case_uuid == case_uuid)
        .first()
    )
    if not record:
        raise HTTPException(status_code=404, detail="Test case not found.")
    record.user_story = payload.user_story
    record.auto_testcase = payload.auto_testcase
    record.steps_json = [step.dict() for step in (payload.steps or [])] if payload.steps else None
    record.test_type = payload.test_type or record.test_type
    record.tags = [t.strip() for t in (payload.tags or []) if t and t.strip()]
    record.markers = [t.strip() for t in (payload.markers or []) if t and t.strip()]
    if payload.test_name:
        record.test_name = payload.test_name
    if payload.priority:
        record.priority = payload.priority
    if script_path_value:
        record.script_path = script_path_value
    if runner_script_path_value:
        record.runner_script_path = runner_script_path_value
    try:
        db.flush()
    except IntegrityError as err:
        db.rollback()
        raise HTTPException(status_code=409, detail="Unable to update test case.") from err
    db.refresh(record)
    return {"testcase": record.to_dict()}
