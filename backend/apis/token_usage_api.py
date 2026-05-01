from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from database.session import get_db
from database.models import TokenUsage, User
from .projects_api import get_current_user, get_user_project

router = APIRouter()


@router.get("/projects/{project_id}/usage")
def get_project_usage(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = get_user_project(db, project_id, current_user)

    total = (
        db.query(
            func.sum(TokenUsage.total_tokens),
            func.sum(TokenUsage.cost),
        )
        .filter(TokenUsage.project_id == project.id)
        .first()
    )

    breakdown = (
        db.query(
            TokenUsage.feature,
            func.sum(TokenUsage.total_tokens),
        )
        .filter(TokenUsage.project_id == project.id)
        .group_by(TokenUsage.feature)
        .all()
    )

    return {
        "total_tokens": total[0] or 0,
        "total_cost": total[1] or 0,
        "breakdown": {k: v for k, v in breakdown},
    }
