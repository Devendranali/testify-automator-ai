from __future__ import annotations

import asyncio
import time
import uuid
from typing import Any, Awaitable, Callable, Dict, Optional


class AsyncJobManager:
    def __init__(self, namespace: str, *, ttl_seconds: int = 3600) -> None:
        self._namespace = namespace
        self._ttl = ttl_seconds
        self._jobs: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    def _now(self) -> float:
        return time.time()

    async def create(self, coro_factory: Callable[[], Awaitable[Any]]) -> Dict[str, Any]:
        job_id = f"{self._namespace}-{uuid.uuid4().hex}"
        job = {
            "id": job_id,
            "status": "queued",
            "created_at": self._now(),
            "started_at": None,
            "finished_at": None,
            "result": None,
            "error": None,
        }
        async with self._lock:
            self._jobs[job_id] = job
            self._prune_locked()

        async def _runner():
            job["status"] = "running"
            job["started_at"] = self._now()
            try:
                result = await coro_factory()
                job["result"] = result
                job["status"] = "completed"
            except Exception as exc:  # pragma: no cover - error path
                job["error"] = str(exc)
                job["status"] = "failed"
            finally:
                job["finished_at"] = self._now()

        asyncio.create_task(_runner())
        return job

    async def get(self, job_id: str) -> Optional[Dict[str, Any]]:
        async with self._lock:
            return self._jobs.get(job_id)

    def _prune_locked(self) -> None:
        cutoff = self._now() - self._ttl
        to_delete = [
            jid
            for jid, j in self._jobs.items()
            if (j.get("finished_at") or 0) and j.get("finished_at") < cutoff
        ]
        for jid in to_delete:
            self._jobs.pop(jid, None)
