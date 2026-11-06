"""Regression coverage for backend waveform and resource ownership."""

import asyncio
import inspect
import io
import subprocess
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest
import soundfile as sf
from fastapi import HTTPException

from app.services import concurrency
from app.utils.audio import AudioConversionError, _convert_to_wav, load_audio_tensor


@pytest.fixture
def stereo_audio() -> io.BytesIO:
    """Generate stereo audio without external fixture files."""
    samples = np.column_stack((np.full(800, 0.25), np.full(800, 0.75)))
    buffer = io.BytesIO()
    sf.write(buffer, samples, 8000, format="WAV", subtype="FLOAT")
    buffer.seek(0)
    return buffer


def test_ssl_waveform_preprocessing(stereo_audio: io.BytesIO) -> None:
    waveform, rate = load_audio_tensor(stereo_audio, 16000)
    assert rate == 16000
    assert waveform.shape == (1600,)
    np.testing.assert_allclose(waveform.numpy(), 0.5, atol=1e-6)


@pytest.mark.asyncio
async def test_busy_rejection_closes_unstarted_coroutine() -> None:
    entered = asyncio.Event()
    release = asyncio.Event()

    async def operation() -> str:
        entered.set()
        await release.wait()
        return "complete"

    active = asyncio.create_task(concurrency.run_with_semaphore(operation()))
    await entered.wait()
    rejected = operation()
    try:
        with pytest.raises(HTTPException) as exc:
            await concurrency.run_with_semaphore(rejected)
        assert exc.value.status_code == 503
        assert inspect.getcoroutinestate(rejected) == inspect.CORO_CLOSED
        assert concurrency.is_server_busy()
    finally:
        release.set()
        assert await active == "complete"
    assert not concurrency.is_server_busy()


@pytest.mark.parametrize("timeout", [False, True])
def test_failed_conversion_removes_partial_output(tmp_path: Path, timeout: bool) -> None:
    source = tmp_path / "audio.webm"
    source.write_bytes(b"recording")
    output = source.with_suffix(".wav")

    def fail_conversion(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        output.write_bytes(b"partial wav")
        if timeout:
            raise subprocess.TimeoutExpired("ffmpeg", 30)
        return subprocess.CompletedProcess("ffmpeg", 1, stderr="invalid recording")

    with patch("app.utils.audio.subprocess.run", side_effect=fail_conversion):
        with pytest.raises(AudioConversionError):
            _convert_to_wav(str(source))
    assert not output.exists()
    assert source.read_bytes() == b"recording"


def test_main_template_renders_with_public_starlette_api() -> None:
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as client:
        response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "phoneme" in response.text.lower()
