"""Process-local inference ownership, including cancellation-safe worker draining."""

import asyncio
from collections.abc import Callable, Coroutine
from threading import Lock
from typing import Any, TypeVar

from fastapi import HTTPException

T = TypeVar("T")
_inference_lock = Lock()
BUSY_MESSAGE = "Server is currently processing another request. Please try again in a moment."


async def await_owned(task: asyncio.Task[T], discard: Callable[[T], None] | None = None) -> T:
    """Keep resources alive until work ends; Python cannot stop a running thread.

    Cancellation is propagated only after the task has drained. Repeated cancels
    must not release an inference slot or remove files beneath a running worker.
    """
    try:
        return await asyncio.shield(task)
    except asyncio.CancelledError:
        while not task.done():
            try:
                await asyncio.shield(task)
            except asyncio.CancelledError:
                continue
            except Exception:
                break
        if not task.cancelled():
            error = task.exception()  # Retrieve errors even when caller abandoned work.
            if error is None and discard is not None:
                discard(task.result())
        raise


async def run_blocking(operation: Callable[..., T], *args: Any, **kwargs: Any) -> T:
    """Offload a blocking stage without abandoning its resource lifetime."""
    return await await_owned(asyncio.create_task(asyncio.to_thread(operation, *args, **kwargs)))


async def run_with_semaphore(coro: Coroutine[Any, Any, T]) -> T:
    """Admit one complete workflow, rejecting competing requests with HTTP 503.

    A threading lock also protects separate event loops in local TestClient uses.
    The gate is per process; production must use one inference worker process.
    """
    if not _inference_lock.acquire(blocking=False):
        coro.close()
        raise HTTPException(status_code=503, detail=BUSY_MESSAGE)
    try:
        return await await_owned(asyncio.create_task(coro))
    finally:
        _inference_lock.release()


async def run_inference(operation: Callable[..., T], *args: Any, **kwargs: Any) -> T:
    """Run a synchronous workflow through the same gate as primary analysis."""
    return await run_with_semaphore(run_blocking(operation, *args, **kwargs))


def is_server_busy() -> bool:
    """Return whether a workflow still owns inference resources."""
    return _inference_lock.locked()
