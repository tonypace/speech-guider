"""Workflow cancellation cannot release resources beneath an active worker."""

import asyncio
import io
import threading
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException, UploadFile

from app.api.analyze import analyze_audio
from app.api.comparison import ReferenceAnimationRequest, generate_reference_animation
from app.api.prosody_lab import analyze_prosody_lab
from app.services.concurrency import is_server_busy, run_blocking


@pytest.mark.asyncio
async def test_cancelled_analysis_retains_gate_and_file_until_worker_finishes(
    tmp_path: Path,
) -> None:
    path = tmp_path / "owned.wav"
    path.write_bytes(b"audio")
    started = threading.Event()
    release = threading.Event()

    def worker() -> dict[str, bool]:
        started.set()
        assert release.wait(timeout=5)
        assert path.exists()
        return {"success": True}

    async def pipeline(*args: object) -> dict[str, bool]:
        return await run_blocking(worker)

    with (
        patch("app.api.analyze.save_upload_to_temp", AsyncMock(return_value=str(path))),
        patch("app.api.analyze._run_analysis_pipeline", pipeline),
        patch(
            "app.api.prosody_lab.save_upload_to_temp",
            AsyncMock(return_value=str(tmp_path / "other")),
        ),
    ):
        request = asyncio.create_task(
            analyze_audio(UploadFile(file=io.BytesIO(), filename="test.wav"), "hello", None)
        )
        while not started.is_set():
            await asyncio.sleep(0.001)
        request.cancel()
        await asyncio.sleep(0)
        request.cancel()  # Repeated cancellation must also preserve ownership.
        await asyncio.sleep(0)
        assert path.exists()
        assert is_server_busy()
        try:
            with pytest.raises(HTTPException) as reference:
                await generate_reference_animation(ReferenceAnimationRequest(target_text="hello"))
            assert reference.value.status_code == 503
            with pytest.raises(HTTPException) as prosody:
                await analyze_prosody_lab(UploadFile(file=io.BytesIO(), filename="test.wav"))
            assert prosody.value.status_code == 503
        finally:
            release.set()
            with pytest.raises(asyncio.CancelledError):
                await request
    assert not is_server_busy()
    assert not path.exists()


@pytest.mark.asyncio
async def test_upload_cancellation_discards_completed_worker_file(tmp_path: Path) -> None:
    from app.utils.audio import save_upload_to_temp

    path = tmp_path / "converted.wav"
    started = threading.Event()
    release = threading.Event()

    def convert(*args: object) -> str:
        path.write_bytes(b"converted")
        started.set()
        assert release.wait(timeout=5)
        return str(path)

    upload = UploadFile(file=io.BytesIO(), filename="test.webm")
    with patch.object(upload, "read", AsyncMock(return_value=b"recording")):
        with patch("app.utils.audio._save_contents_to_temp", convert):
            task = asyncio.create_task(save_upload_to_temp(upload))
            while not started.is_set():
                await asyncio.sleep(0.001)
            task.cancel()
            await asyncio.sleep(0)
            assert path.exists()
            release.set()
            with pytest.raises(asyncio.CancelledError):
                await task
    assert not path.exists()


@pytest.mark.asyncio
async def test_all_heavy_primary_stages_run_off_event_loop() -> None:
    import torch

    from app.api.analyze import _run_analysis_pipeline

    loop_thread = threading.get_ident()
    observed: list[int] = []

    def observe(result: object) -> object:
        observed.append(threading.get_ident())
        return result

    with (
        patch("src.audio.processor.AudioContext", side_effect=lambda path: observe(object())),
        patch(
            "app.api.analyze._load_and_preprocess_audio",
            side_effect=lambda path: observe((torch.zeros(16000), 16000)),
        ),
        patch(
            "app.api.analyze.try_primary_ssl_analysis",
            side_effect=lambda *args: observe((None, None, {})),
        ),
        patch("src.audio.processor.ProsodyAnalyzer") as analyzer,
    ):
        analyzer.return_value.analyze_complete.side_effect = lambda **kwargs: observe(None)
        result = await _run_analysis_pipeline("unused.wav", "hello", "standalone")
    assert result["success"]
    assert "prosody feedback only" in result["feedback"]
    assert len(observed) == 4
    assert all(thread != loop_thread for thread in observed)
