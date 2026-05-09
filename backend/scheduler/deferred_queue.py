from __future__ import annotations
import uuid
from collections import deque
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Optional


@dataclass
class DeferredJob:
    job_id: str
    prompt: str
    system_prompt: Optional[str]
    queued_at: str               # ISO-8601 UTC
    defer_until: str             # ISO-8601 UTC
    carbon_intensity_at_queue: float
    status: str                  # "queued" | "processing" | "done"
    result: Optional[str]

    def to_dict(self) -> dict:
        return asdict(self)


_queue: deque[DeferredJob] = deque(maxlen=100)


def enqueue(
    prompt: str,
    system_prompt: Optional[str],
    defer_until: str,
    carbon_intensity: float,
) -> str:
    job = DeferredJob(
        job_id=str(uuid.uuid4()),
        prompt=prompt,
        system_prompt=system_prompt,
        queued_at=datetime.now(timezone.utc).isoformat(),
        defer_until=defer_until,
        carbon_intensity_at_queue=carbon_intensity,
        status="queued",
        result=None,
    )
    _queue.append(job)
    return job.job_id


def get_all_jobs() -> list[DeferredJob]:
    return list(_queue)


def get_ready_jobs() -> list[DeferredJob]:
    """Queued jobs whose defer_until has passed — ready to run now."""
    now = datetime.now(timezone.utc)
    return [
        j for j in _queue
        if j.status == "queued" and datetime.fromisoformat(j.defer_until) <= now
    ]


def mark_processing(job_id: str) -> bool:
    for j in _queue:
        if j.job_id == job_id:
            j.status = "processing"
            return True
    return False


def mark_done(job_id: str, result: str) -> bool:
    for j in _queue:
        if j.job_id == job_id:
            j.status = "done"
            j.result = result
            return True
    return False
