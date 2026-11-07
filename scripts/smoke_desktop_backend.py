"""Check a frozen desktop backend from outside the repository working directory."""

import argparse
import io
import json
import math
import os
import signal
import struct
import subprocess
import tempfile
import time
import wave
from pathlib import Path
from typing import Any, cast
from urllib.request import ProxyHandler, Request, build_opener

DEFAULT_EXECUTABLE = (
    Path(__file__).resolve().parents[1]
    / "build"
    / "desktop-backend"
    / "speech-guider-backend"
    / "speech-guider-backend"
)


def _wav_upload(target_text: str | None = None) -> bytes:
    """Create one second of synthetic audio so the check needs no recording."""
    buffer = io.BytesIO()
    sample_rate = 16000
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        frames = [
            int(4096 * math.sin(2 * math.pi * 220 * sample / sample_rate))
            for sample in range(sample_rate)
        ]
        wav.writeframes(struct.pack(f"<{sample_rate}h", *frames))
    text_part = (
        (
            b'--desktop-smoke\r\nContent-Disposition: form-data; name="target_text"\r\n\r\n'
            + target_text.encode("utf-8")
            + b"\r\n"
        )
        if target_text
        else b""
    )
    return text_part + (
        b'--desktop-smoke\r\nContent-Disposition: form-data; name="audio"; filename="test.wav"\r\n'
        b"Content-Type: audio/wav\r\n\r\n" + buffer.getvalue() + b"\r\n--desktop-smoke--\r\n"
    )


def _wait_for_ready(process: subprocess.Popen[bytes], ready: Path) -> int:
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"Backend exited before startup: {process.returncode}")
        if ready.is_file():
            payload = json.loads(ready.read_text(encoding="utf-8"))
            port = int(payload["port"])
            if payload["pid"] != process.pid or not 1 <= port <= 65535:
                raise RuntimeError("Backend published an invalid readiness handshake")
            return port
        time.sleep(0.1)
    raise TimeoutError("Backend did not become ready within 60 seconds")


def _request(base: str, path: str, upload: bytes | None = None) -> bytes:
    headers = {"Content-Type": "multipart/form-data; boundary=desktop-smoke"} if upload else {}
    request = Request(f"{base}{path}", data=upload, headers=headers)
    opener = build_opener(ProxyHandler({}))
    with opener.open(request, timeout=20) as response:
        return cast(bytes, response.read())


def smoke(executable: Path, r4_bundle: Path | None = None) -> None:
    """Verify the frozen imports, HTML, static assets, and native audio stack."""
    with tempfile.TemporaryDirectory(prefix="speech guider smoke ") as directory:
        scratch = Path(directory).resolve()
        ready = scratch / "ready.json"
        log = scratch / "backend.log"
        env = {
            "PATH": "/usr/bin:/bin",
            "SPEECH_GUIDER_PRESETS_FILE": str(scratch / "presets.json"),
            "SPEECH_GUIDER_ASSET_DIR": str(scratch / "assets"),
        }
        if r4_bundle is not None:
            env["SSL_AAI_BUNDLE_PATH"] = str(r4_bundle.resolve(strict=True))
        with log.open("wb") as output:
            process = subprocess.Popen(
                [str(executable), "--ready-file", str(ready), "--parent-pid", str(os.getpid())],
                cwd=scratch,
                env=env,
                stdout=output,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
        try:
            base = f"http://127.0.0.1:{_wait_for_ready(process, ready)}"
            if json.loads(_request(base, "/health")).get("status") != "ok":
                raise RuntimeError("Health check failed")
            if b"Speech" not in _request(base, "/"):
                raise RuntimeError("Frozen backend did not render the app template")
            if not _request(base, "/static/js/app.js"):
                raise RuntimeError("Frozen backend did not serve the app module")
            data: dict[str, Any] = json.loads(
                _request(base, "/api/prosody-lab/analyze", _wav_upload())
            )
            if data.get("summary", {}).get("duration_seconds") != 1:
                raise RuntimeError("Synthetic WAV analysis failed in the frozen backend")
            if r4_bundle is not None:
                analysis = json.loads(_request(base, "/api/analyze", _wav_upload("Synthetic tone")))
                trajectory = analysis.get("ssl_trajectory") or {}
                if not trajectory.get("frames"):
                    raise RuntimeError("Frozen R4 inference did not produce animation frames")
        except (OSError, RuntimeError, ValueError):
            print(log.read_text(encoding="utf-8", errors="replace"))
            raise
        finally:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=8)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()
        if ready.exists():
            raise RuntimeError("Backend did not remove its readiness file on shutdown")
    print(f"Frozen backend smoke check passed: {executable}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("executable", nargs="?", type=Path, default=DEFAULT_EXECUTABLE)
    parser.add_argument("--r4-bundle", type=Path, help="Also run R4 on a generated one-second WAV")
    args = parser.parse_args()
    smoke(args.executable.resolve(strict=True), args.r4_bundle)
