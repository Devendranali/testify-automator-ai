from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Optional
from uuid import uuid4

from sqlalchemy.orm import Session

from database.models import ProjectAllureResult

ALLURE_RESULT_SUFFIX = "-result.json"


def _extract_duration(payload: dict) -> Optional[float]:
    if not isinstance(payload, dict):
        return None
    duration = payload.get("duration")
    if isinstance(duration, (int, float)):
        return float(duration)
    time_meta = payload.get("time") or {}
    if isinstance(time_meta, dict):
        if isinstance(time_meta.get("duration"), (int, float)):
            return float(time_meta["duration"])
        start = time_meta.get("start")
        stop = time_meta.get("stop")
        if isinstance(start, (int, float)) and isinstance(stop, (int, float)) and stop >= start:
            return float(stop - start)
    start = payload.get("start")
    stop = payload.get("stop")
    if isinstance(start, (int, float)) and isinstance(stop, (int, float)) and stop >= start:
        return float(stop - start)
    return None


def store_allure_results(
    db: Session,
    project_id: int,
    results_dir: Path,
    run_id: Optional[str] = None,
) -> str:
    results_dir = Path(results_dir)
    if not results_dir.exists():
        return run_id or ""

    if not run_id:
        run_id = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{uuid4().hex[:8]}"

    rows = []
    for file_path in sorted(results_dir.glob(f"*{ALLURE_RESULT_SUFFIX}")):
        try:
            payload = json.loads(file_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        name = payload.get("name") or payload.get("fullName") or file_path.stem
        status = payload.get("status")
        duration = _extract_duration(payload)
        try:
            relative_path = file_path.relative_to(results_dir).as_posix()
        except ValueError:
            relative_path = file_path.as_posix()
        rows.append(
            ProjectAllureResult(
                project_id=project_id,
                run_id=run_id,
                file_name=file_path.name,
                relative_path=relative_path,
                test_name=name,
                status=status,
                duration=duration,
                payload=payload,
            )
        )

    if rows:
        db.add_all(rows)
        db.commit()

    return run_id

