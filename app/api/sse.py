"""Discoverable progress jobs, bounded replay, and SSE broadcast subscriptions."""

import asyncio
import json
from collections.abc import AsyncGenerator
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Query
from sse_starlette.sse import EventSourceResponse

from app.services.jobs import (
    HISTORY_SIZE,
    TERMINAL_STATES,
    create_job,
    get_job,
)

router = APIRouter()


def create_job_id() -> str:
    """Compatibility helper for synchronous analysis submissions."""
    return create_job().job_id


async def send_progress_update(
    job_id: str, progress: float, message: str, step: str | None = None
) -> None:
    """Keep history even before a client subscribes."""
    try:
        job = get_job(job_id)
    except HTTPException:
        # Standalone pipeline callers need no HTTP job reservation.
        return
    if job.status not in TERMINAL_STATES:
        job.publish(progress, message, step)


async def progress_generator(job_id: str, after: int = 0) -> AsyncGenerator[dict[str, str], None]:
    """Replay recent events then broadcast independently to each subscriber.

    Subscriber queues are bounded. A slow subscriber receives the newest retained
    events; sequence IDs expose gaps. Reconnecting clients can replay via Last-Event-ID.
    """
    job = get_job(job_id)
    if after > job.sequence:
        after = 0  # Recover a cursor from a different/previous job.
    already_terminal = job.status in TERMINAL_STATES
    queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=HISTORY_SIZE)
    job.subscribers.add(queue)
    try:
        replay = [event for event in job.history if event["sequence"] > after]
        for event in replay:
            yield _serialize_event(event)
        if already_terminal:
            return
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=15.0)
            except TimeoutError:
                if job.status == "pending":
                    try:
                        get_job(job_id)
                    except HTTPException:
                        yield {"event": "expired", "data": json.dumps({"job_id": job_id})}
                        return
                yield {"event": "heartbeat", "data": json.dumps({"job_id": job_id})}
                continue
            yield _serialize_event(event)
            if event["status"] in TERMINAL_STATES:
                return
    finally:
        job.subscribers.discard(queue)


def _serialize_event(event: dict[str, Any]) -> dict[str, str]:
    status = event["status"]
    return {
        "id": str(event["sequence"]),
        "event": status if status in TERMINAL_STATES else "progress",
        "data": json.dumps(event),
    }


@router.post("/api/analysis-jobs", status_code=201)
async def reserve_analysis_job() -> dict[str, str]:
    job = create_job()
    return {"job_id": job.job_id, "events_url": f"/api/progress/{job.job_id}"}


@router.get("/api/analysis-jobs/{job_id}")
async def analysis_job_status(job_id: str) -> dict[str, Any]:
    job = get_job(job_id)
    return {"job_id": job.job_id, "status": job.status, "sequence": job.sequence}


@router.get("/api/progress/{job_id}")
async def progress_stream(
    job_id: str,
    last_event_id: str | None = Header(default=None),
    after: int = Query(default=0, ge=0),
) -> EventSourceResponse:
    get_job(job_id)  # Validate before sending streaming response headers.
    if last_event_id is not None:
        try:
            after = max(0, int(last_event_id))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid Last-Event-ID") from exc
    return EventSourceResponse(progress_generator(job_id, after))
