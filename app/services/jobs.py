"""Bounded, process-local progress history with independent subscribers."""

import asyncio
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from typing import Any

from fastapi import HTTPException

TERMINAL_STATES = frozenset({"complete", "failed", "cancelled"})
JOB_TTL_SECONDS = 300.0
MAX_JOBS = 256
HISTORY_SIZE = 64


@dataclass
class AnalysisJob:
    """Retain recent progress, never audio or analysis payloads."""

    job_id: str
    status: str = "pending"
    updated_at: float = field(default_factory=time.monotonic)
    sequence: int = 0
    history: deque[dict[str, Any]] = field(default_factory=lambda: deque(maxlen=HISTORY_SIZE))
    subscribers: set[asyncio.Queue[dict[str, Any]]] = field(default_factory=set)

    def publish(self, progress: float, message: str, step: str | None = None) -> None:
        self.sequence += 1
        self.updated_at = time.monotonic()
        event = {
            "job_id": self.job_id,
            "progress": progress,
            "message": message,
            "step": step,
            "status": self.status,
            "sequence": self.sequence,
        }
        self.history.append(event)
        for subscriber in self.subscribers:
            if subscriber.full():
                subscriber.get_nowait()
            subscriber.put_nowait(event)


_jobs: dict[str, AnalysisJob] = {}


def expire_jobs() -> None:
    """Expire idle reservations and finished jobs, retaining running ownership."""
    cutoff = time.monotonic() - JOB_TTL_SECONDS
    for key, job in list(_jobs.items()):
        if job.status != "running" and job.updated_at < cutoff:
            del _jobs[key]


def create_job() -> AnalysisJob:
    """Reserve an ID before upload so progress is discoverable immediately."""
    expire_jobs()
    if len(_jobs) >= MAX_JOBS:
        raise HTTPException(
            status_code=503, detail="Too many retained analysis jobs. Try again later."
        )
    job = AnalysisJob(str(uuid.uuid4()))
    _jobs[job.job_id] = job
    job.publish(0.0, "Ready for upload", "pending")
    return job


def get_job(job_id: str) -> AnalysisJob:
    expire_jobs()
    job = _jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Analysis job not found or expired.")
    return job


def claim_job(job_id: str) -> AnalysisJob:
    """A reservation can be submitted exactly once, including failed attempts."""
    job = get_job(job_id)
    if job.status != "pending":
        raise HTTPException(status_code=409, detail="Analysis job has already been submitted.")
    job.status = "running"
    job.publish(0.0, "Preparing audio", "upload")
    return job


def finish_job(job: AnalysisJob, status: str, message: str) -> None:
    if job.status in TERMINAL_STATES:
        return
    if status not in TERMINAL_STATES:
        raise ValueError("Job must finish in a terminal state")
    job.status = status
    job.publish(1.0 if status == "complete" else 0.0, message, status)
