"""Exercise the packaged macOS launcher, WebView, and owned backend lifecycle."""

import argparse
import base64
import errno
import json
import os
import plistlib
import re
import signal
import socket
import subprocess
import sys
import tempfile
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from urllib.request import ProxyHandler, Request, build_opener

DEFAULT_APP = (
    Path(__file__).resolve().parents[1]
    / "src-tauri"
    / "target"
    / "release"
    / "bundle"
    / "macos"
    / "Speech Guider.app"
)
DEFAULT_PORT = 7860
QUIT_APP = """
function run(args) {
    ObjC.import('AppKit');
    const application = $.NSRunningApplication.runningApplicationWithProcessIdentifier(Number(args[0]));
    if (!application || !application.terminate) throw Error('Could not request application quit');
}
"""


@dataclass(frozen=True)
class Session:
    process: subprocess.Popen[bytes]
    port: int
    backend_pid: int
    readiness: Path
    host_log: Path

    @property
    def base(self) -> str:
        return f"http://127.0.0.1:{self.port}"


def _request(
    base: str, path: str, data: dict[str, object] | None = None, timeout: float = 5
) -> bytes:
    request = Request(
        f"{base}{path}",
        data=json.dumps(data).encode() if data is not None else None,
        headers={"Content-Type": "application/json"} if data is not None else {},
    )
    with build_opener(ProxyHandler({})).open(request, timeout=timeout) as response:
        return bytes(response.read())


def _read_log(path: Path, offset: int = 0) -> str:
    if not path.is_file():
        return ""
    with path.open("rb") as stream:
        stream.seek(offset)
        return stream.read().decode(errors="replace")


def _child_owned(pid: int, parent: int) -> bool:
    completed = subprocess.run(
        ["/bin/ps", "-o", "ppid=", "-p", str(pid)],
        capture_output=True,
        text=True,
        check=False,
    )
    return completed.returncode == 0 and completed.stdout.strip() == str(parent)


def _wait_for_webview(
    process: subprocess.Popen[bytes], host_log: Path, backend_log: Path, offset: int
) -> Session:
    deadline = time.monotonic() + 65
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"Desktop host exited during startup ({process.returncode}).")
        native = _read_log(host_log)
        if "Speech Guider backend:" in native:
            raise RuntimeError("The desktop host reported a backend startup failure.")
        ready = re.search(r"backend ready at http://127\.0\.0\.1:(\d+)", native)
        requests = _read_log(backend_log, offset)
        if ready and all(
            f'GET {path} HTTP/1.1" 200' in requests
            for path in ("/", "/static/css/tailwind.min.css", "/static/js/app.js")
        ):
            # No HTTP probe has run yet; these requests came from the WebView.
            for directory in Path(tempfile.gettempdir()).glob(f"speech-guider-{process.pid}-*"):
                handshake = directory / "ready.json"
                if handshake.is_file():
                    result = json.loads(handshake.read_text(encoding="utf-8"))
                    port, pid = int(result["port"]), int(result["pid"])
                    if port == int(ready[1]) and _child_owned(pid, process.pid):
                        return Session(process, port, pid, handshake, host_log)
        time.sleep(0.1)
    raise TimeoutError("The packaged WebView did not load the local backend and its assets.")


def _quit(process: subprocess.Popen[bytes]) -> None:
    subprocess.run(
        ["/usr/bin/osascript", "-l", "JavaScript", "-e", QUIT_APP, str(process.pid)],
        check=True,
        timeout=10,
    )
    if process.wait(timeout=12) != 0:
        raise RuntimeError("Desktop host did not exit cleanly after macOS quit.")


def _verify_stopped(session: Session) -> None:
    if session.readiness.exists():
        raise RuntimeError("The backend readiness file survived shutdown.")
    try:
        os.kill(session.backend_pid, 0)
    except ProcessLookupError:
        return
    raise RuntimeError("The owned backend PID survived shutdown.")


@contextmanager
def _launch(executable: Path, scratch: Path, attempt: int) -> Iterator[Session]:
    data = scratch / "desktop state"
    native_log = scratch / f"host-{attempt}.log"
    backend_log = data / "logs" / "backend.log"
    offset = backend_log.stat().st_size if backend_log.is_file() else 0
    env = {
        "PATH": "/usr/bin:/bin",
        "SPEECH_GUIDER_DESKTOP_STATE_DIR": str(data),
    }
    # Match the host's native temporary directory without changing its location.
    if "TMPDIR" in os.environ:
        env["TMPDIR"] = os.environ["TMPDIR"]
    with native_log.open("wb") as output:
        process = subprocess.Popen(
            [str(executable)], cwd=scratch, env=env, stdout=output, stderr=subprocess.STDOUT
        )
    try:
        yield _wait_for_webview(process, native_log, backend_log, offset)
    except (OSError, RuntimeError, subprocess.SubprocessError, ValueError):
        print(_read_log(native_log), file=sys.stderr)
        print(_read_log(backend_log, offset), file=sys.stderr)
        raise
    finally:
        if process.poll() is None:
            try:
                _quit(process)
            except (OSError, RuntimeError, subprocess.SubprocessError):
                if process.poll() is None:
                    process.kill()
                process.wait(timeout=5)


@contextmanager
def _hold_port(port: int) -> Iterator[None]:
    """Keep the port busy, or preserve a listener that already owns it."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        try:
            listener.bind(("127.0.0.1", port))
        except OSError as exc:
            if exc.errno != errno.EADDRINUSE:
                raise
        else:
            listener.listen()
        yield


def smoke(bundle: Path) -> None:
    """Run two packaged launches and induce an owned backend crash."""
    if sys.platform != "darwin":
        raise SystemExit("Run this check in a macOS desktop session.")
    with (bundle / "Contents" / "Info.plist").open("rb") as stream:
        metadata = plistlib.load(stream)
    executable = bundle / "Contents" / "MacOS" / str(metadata["CFBundleExecutable"])
    if b"SPEECH_GUIDER_DESKTOP_STATE_DIR" not in executable.read_bytes():
        raise RuntimeError("Rebuild the app before testing; this launcher cannot isolate app data.")
    bundled_assets = (bundle / "Contents/Resources/assets").is_dir()
    with tempfile.TemporaryDirectory(prefix="speech guider app smoke ") as temp:
        scratch = Path(temp).resolve()
        with _hold_port(DEFAULT_PORT):
            with _launch(executable, scratch, 1) as first:
                if first.port == DEFAULT_PORT:
                    raise RuntimeError("The desktop backend reused the occupied development port.")
                if json.loads(_request(first.base, "/health")) != {
                    "status": "ok",
                    "service": "pronunciation-evaluator",
                }:
                    raise RuntimeError("Unexpected desktop health response.")
                root = _request(first.base, "/")
                if b"__SPEECH_GUIDER_DESKTOP__ = true" not in root:
                    raise RuntimeError("The desktop template is missing.")
                if (b"desktop-asset-setup" in root) == bundled_assets:
                    raise RuntimeError("Desktop asset discovery did not match the packaged assets.")
                if bundled_assets:
                    reference = json.loads(
                        _request(
                            first.base,
                            "/api/reference-animation",
                            {"target_text": "This is a short test."},
                            timeout=150,
                        )
                    )
                    audio = base64.b64decode(reference["audio_base64"], validate=True)
                    if not audio.startswith(b"OggS") or not reference.get("frames"):
                        raise RuntimeError(
                            "Bundled OmniVoice and R4 did not produce audio and frames."
                        )
                    print(
                        "Bundled OmniVoice and R4 produced reference audio and frames.", flush=True
                    )
                _request(
                    first.base, "/api/presets", {"phoneme": "i", "params": {"lip_aperture": 0.41}}
                )
                _quit(first.process)
                _verify_stopped(first)
            print(
                f"WebView loaded on {first.port} with port {DEFAULT_PORT} occupied; quit reaped backend.",
                flush=True,
            )

            with _hold_port(first.port), _launch(executable, scratch, 2) as second:
                if second.port in (DEFAULT_PORT, first.port):
                    raise RuntimeError("The relaunch reused an occupied port.")
                presets = json.loads(_request(second.base, "/api/presets"))
                if presets["phonemes"]["i"]["params"]["lip_aperture"] != 0.41:
                    raise RuntimeError("Saved preset did not survive the changed WebView origin.")
                if not _child_owned(second.backend_pid, second.process.pid):
                    raise RuntimeError("Backend PID no longer belongs to this launch.")
                os.kill(second.backend_pid, signal.SIGKILL)
                deadline = time.monotonic() + 8
                while "backend stopped unexpectedly" not in _read_log(second.host_log):
                    if time.monotonic() >= deadline or second.process.poll() is not None:
                        raise RuntimeError("The desktop host did not handle its backend crash.")
                    time.sleep(0.1)
                _verify_stopped(second)
                _quit(second.process)
            print(
                f"WebView relaunched on {second.port}; preset persisted; backend crash handled.",
                flush=True,
            )
    print(f"Packaged desktop smoke passed: {bundle}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("app", nargs="?", type=Path, default=DEFAULT_APP)
    smoke(parser.parse_args().app.resolve(strict=True))
