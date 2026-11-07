"""Single-process, loopback-only backend for the packaged desktop shell."""

import argparse
import asyncio
import json
import logging
import multiprocessing
import os
import signal
import socket
import sys
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from types import FrameType

import uvicorn
from starlette.datastructures import Headers
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.responses import PlainTextResponse
from starlette.types import ASGIApp, Receive, Scope, Send

logger = logging.getLogger(__name__)


class _DesktopServer(uvicorn.Server):
    @contextmanager
    def capture_signals(self) -> Iterator[None]:
        # Unlike the CLI, the owned process must remove its handshake before exiting.
        def request_exit(signum: int, frame: FrameType | None) -> None:
            if self.should_exit and signum == signal.SIGINT:
                self.force_exit = True
            self.should_exit = True

        previous = {
            sig: signal.signal(sig, request_exit) for sig in (signal.SIGINT, signal.SIGTERM)
        }
        try:
            yield
        finally:
            for sig, handler in previous.items():
                signal.signal(sig, handler)


class _SameOrigin:
    def __init__(self, app: ASGIApp, origin: str) -> None:
        self.app = app
        self.origin = origin

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http":
            headers = Headers(scope=scope)
            origin = headers.get("origin")
            if (origin is not None and origin != self.origin) or headers.get(
                "sec-fetch-site"
            ) == "cross-site":
                await PlainTextResponse("Cross-origin desktop request blocked", status_code=403)(
                    scope, receive, send
                )
                return
        await self.app(scope, receive, send)


def _publish_ready(path: Path, port: int) -> None:
    """The launcher must see either a complete handshake or no file."""
    with tempfile.NamedTemporaryFile(
        mode="w", dir=path.parent, encoding="utf-8", delete=False
    ) as f:
        temporary = Path(f.name)
        try:
            json.dump({"port": port, "pid": os.getpid()}, f)
            f.flush()
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)


def _parent_exited(parent_pid: int | None) -> bool:
    return parent_pid is not None and os.getppid() != parent_pid


async def _watch_parent(server: uvicorn.Server, parent_pid: int | None) -> None:
    while not server.should_exit:
        if _parent_exited(parent_pid):
            logger.info("Desktop host exited; stopping backend")
            server.should_exit = True
            # Native launcher isolates our group. On abrupt host death, stop any
            # active ffmpeg/TTS descendants too, without touching other processes.
            if hasattr(os, "killpg") and os.getpgrp() == os.getpid():
                os.killpg(os.getpgrp(), signal.SIGTERM)
            return
        await asyncio.sleep(0.25)


async def _serve(listener: socket.socket, ready_file: Path, parent_pid: int | None) -> int:
    os.environ["SPEECH_GUIDER_DESKTOP"] = "1"
    from app.main import app

    port = int(listener.getsockname()[1])
    app.add_middleware(_SameOrigin, origin=f"http://127.0.0.1:{port}")
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1"])

    server = _DesktopServer(
        uvicorn.Config(
            app,
            host="127.0.0.1",
            loop="asyncio",
            http="h11",
            ws="none",
            lifespan="on",
            proxy_headers=False,
            timeout_graceful_shutdown=3,
        )
    )
    watcher = asyncio.create_task(_watch_parent(server, parent_pid))
    worker = asyncio.create_task(server.serve(sockets=[listener]))
    published = False
    try:
        while not worker.done() and not server.started and not server.should_exit:
            await asyncio.sleep(0.02)
        if server.started and not server.should_exit:
            _publish_ready(ready_file, port)
            published = True
        await worker
        return 0 if published else 1
    finally:
        if not worker.done():
            server.should_exit = True
            await worker
        watcher.cancel()
        await asyncio.gather(watcher, return_exceptions=True)
        if published:
            ready_file.unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    """Bind an OS-selected port without a find-then-bind race."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ready-file", type=Path, required=True)
    parser.add_argument("--parent-pid", type=int)
    args = parser.parse_args(argv)
    if _parent_exited(args.parent_pid):
        parser.error("desktop host is no longer running")
    ready_file: Path = args.ready_file.expanduser().resolve()
    if ready_file.exists():
        parser.error("readiness path already exists")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        return asyncio.run(_serve(listener, ready_file, args.parent_pid))


if __name__ == "__main__":
    multiprocessing.freeze_support()
    sys.exit(main())
