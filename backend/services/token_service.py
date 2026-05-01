from typing import Any, Optional

from sqlalchemy.orm import Session

from database.models import TokenUsage
from utils.token_utils import calculate_cost


def _get_usage_value(usage: Any, key: str) -> Optional[int]:
    if usage is None:
        return None
    if isinstance(usage, dict):
        return usage.get(key)
    return getattr(usage, key, None)


def log_token_usage(
    db: Optional[Session],
    project_id: Optional[int],
    feature: str,
    usage: Any,
    model: str,
) -> None:
    if not usage or not project_id or db is None:
        return

    prompt_tokens = _get_usage_value(usage, "prompt_tokens") or 0
    completion_tokens = _get_usage_value(usage, "completion_tokens") or 0
    total_tokens = _get_usage_value(usage, "total_tokens") or 0

    record = TokenUsage(
        project_id=project_id,
        feature=feature,
        model=model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        cost=calculate_cost(model, total_tokens),
    )

    try:
        db.add(record)
        db.commit()
    except Exception:
        db.rollback()
