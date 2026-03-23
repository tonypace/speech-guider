"""Server-Sent Events for progress updates during analysis."""

import asyncio
import json
import uuid
from typing import Dict, Any
from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse

router = APIRouter()

# In-memory storage for progress queues (job_id -> asyncio.Queue)
progress_queues: Dict[str, asyncio.Queue] = {}


def create_job_id() -> str:
    """Generate a unique job ID for tracking progress."""
    return str(uuid.uuid4())


def get_progress_queue(job_id: str) -> asyncio.Queue:
    """Get or create a progress queue for a job."""
    if job_id not in progress_queues:
        progress_queues[job_id] = asyncio.Queue()
    return progress_queues[job_id]


async def send_progress_update(job_id: str, progress: float, message: str, step: str = None):
    """
    Send a progress update to a specific job.

    Args:
        job_id: The job ID
        progress: Progress value between 0.0 and 1.0
        message: Human-readable progress message
        step: Optional step identifier
    """
    if job_id not in progress_queues:
        return

    update = {"job_id": job_id, "progress": progress, "message": message, "step": step}

    await progress_queues[job_id].put(update)


def cleanup_progress_queue(job_id: str):
    """Remove a progress queue after job completion."""
    if job_id in progress_queues:
        del progress_queues[job_id]


async def progress_generator(job_id: str):
    """
    SSE generator for progress updates.

    Yields events until the job completes (progress >= 1.0).
    """
    queue = get_progress_queue(job_id)

    try:
        while True:
            # Wait for progress update with timeout
            try:
                update = await asyncio.wait_for(queue.get(), timeout=60.0)
            except asyncio.TimeoutError:
                # Send keepalive heartbeat
                yield {
                    "event": "heartbeat",
                    "data": json.dumps({"job_id": job_id, "status": "alive"}),
                }
                continue

            # Yield the progress update
            yield {"event": "progress", "data": json.dumps(update)}

            # Check if job is complete
            if update.get("progress", 0) >= 1.0:
                break

    finally:
        cleanup_progress_queue(job_id)


@router.get("/api/progress/{job_id}")
async def progress_stream(job_id: str):
    """
    SSE endpoint for progress updates.

    Args:
        job_id: Unique job identifier returned by /api/analyze

    Returns:
        EventSourceResponse streaming progress updates
    """
    return EventSourceResponse(progress_generator(job_id))
