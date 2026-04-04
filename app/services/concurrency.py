"""Concurrency control for limiting concurrent ML operations."""

import asyncio
from typing import Any, Coroutine

from fastapi import HTTPException

# Only 1 analysis at a time to prevent OOM
currently_processing = False
_analysis_lock = asyncio.Lock()

# Warning message for busy server
BUSY_MESSAGE = "Server is currently processing another request. Please try again in a moment."


async def run_with_semaphore(coro: Coroutine[Any, Any, Any]) -> Any:
    """
    Run a coroutine with concurrency protection.

    Only allows one analysis at a time. Returns 503 if busy.

    Args:
        coro: The coroutine to execute

    Returns:
        Result of the coroutine

    Raises:
        HTTPException: 503 if server is busy with another request
    """
    global currently_processing

    if currently_processing:
        raise HTTPException(status_code=503, detail=BUSY_MESSAGE)

    async with _analysis_lock:
        currently_processing = True
        try:
            return await coro
        finally:
            currently_processing = False


def is_server_busy() -> bool:
    """Check if server is currently processing a request."""
    return currently_processing
