"""Desktop asset discovery, local origin, and persistence contracts."""

import asyncio
import json
import os
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.desktop_backend import _parent_exited, _publish_ready, _SameOrigin, _watch_parent
from app.main import app
from app.services import state
from src.audio.reference_tts import OmniVoiceTTSProvider
from src.services.desktop_assets import desktop_assets_missing


def test_desktop_resolves_installed_models_and_shows_missing_requirements(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SPEECH_GUIDER_ASSET_DIR", str(tmp_path))
    for name in (
        "SSL_AAI_BUNDLE_PATH",
        "SSL_AAI_CHECKPOINT_PATH",
        "OMNIVOICE_TTS_PATH",
        "OMNIVOICE_MODEL_PATH",
        "OMNIVOICE_CODEC_PATH",
    ):
        monkeypatch.delenv(name, raising=False)
    assert len(desktop_assets_missing()) == 2
    for relative in (
        "r4/weights/r4.pt",
        "r4/configs/nine_channel_v12_100ms.yaml",
        "r4/weights/contentvec/model.safetensors",
        "r4/weights/contentvec/config.json",
        "r4/weights/contentvec/preprocessor_config.json",
        "omnivoice/omnivoice-tts",
        "omnivoice/models/omnivoice-base-Q8_0.gguf",
        "omnivoice/models/omnivoice-tokenizer-F32.gguf",
    ):
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()
    binary = tmp_path / "omnivoice" / "omnivoice-tts"
    binary.chmod(0o755)
    assert desktop_assets_missing() == []
    assert OmniVoiceTTSProvider().tts_path == str(binary)
    other = tmp_path / "custom-tts"
    other.touch()
    monkeypatch.setenv("OMNIVOICE_TTS_PATH", str(other))
    assert OmniVoiceTTSProvider().tts_path == str(other)


def test_desktop_persists_history_and_settings_across_webview_origins(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SPEECH_GUIDER_DESKTOP", "1")
    monkeypatch.setenv("SPEECH_GUIDER_ASSET_DIR", str(tmp_path / "assets"))
    monkeypatch.setattr(state, "DATA_DIR", tmp_path)
    record: dict[str, Any] = {
        "recording_id": "saved-sample",
        "summary": {
            "duration_seconds": 1,
            "syllable_count": 1,
            "pause_count": 0,
            "rhythm_balance": 0.5,
            "mean_f0_hz": 220,
        },
        "pitch_track": [],
        "syllable_onsets": [0.2],
        "created_at": "2026-11-06T00:00:00Z",
    }
    saved_settings = {
        "contact_enabled": False,
        "microphone_enabled": True,
        "microphone_device_id": "mic-1",
        "microphone_label": "USB Mic",
    }
    with TestClient(app, base_url="http://127.0.0.1:49100") as first:
        assert (
            first.put("/api/desktop-history", json={"recordings": [record] * 4}).status_code == 422
        )
        assert (
            first.put(
                "/api/desktop-history", json={"recordings": [record], "student_id": "saved-sample"}
            ).status_code
            == 204
        )
        assert first.put("/api/settings", json=saved_settings).status_code == 200
    with TestClient(app, base_url="http://127.0.0.1:49101") as second:
        page = second.get("/").text
        assert "window.__SPEECH_GUIDER_DESKTOP__ = true" in page
        assert '"student_id": "saved-sample"' in page
        assert '"microphone_device_id": "mic-1"' in page
        assert '"microphone_label": "USB Mic"' in page
        assert '"contact_enabled": false' in page
        assert "desktop-asset-setup" in page
    monkeypatch.delenv("SPEECH_GUIDER_DESKTOP")
    with TestClient(app) as browser:
        assert browser.put("/api/desktop-history", json={}).status_code == 404
        assert "saved-sample" not in browser.get("/").text


def test_desktop_blocks_cross_origin_and_allows_owned_webview() -> None:
    origin = "http://127.0.0.1:49100"
    local = FastAPI()

    @local.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    local.add_middleware(_SameOrigin, origin=origin)
    with TestClient(local, base_url=origin) as client:
        assert client.get("/health").status_code == 200  # Native health probe.
        assert client.get("/health", headers={"Origin": origin}).status_code == 200
        assert (
            client.get("/health", headers={"Origin": "https://example.invalid"}).status_code == 403
        )
        assert client.get("/health", headers={"Sec-Fetch-Site": "cross-site"}).status_code == 403


def test_desktop_publish_ready_writes_port_and_pid(tmp_path: Path) -> None:
    ready_file = tmp_path / "ready.json"
    _publish_ready(ready_file, 49123)
    data = json.loads(ready_file.read_text(encoding="utf-8"))
    assert data == {"port": 49123, "pid": os.getpid()}


def test_desktop_parent_exited_checks_ppid(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(os, "getppid", lambda: 5000)
    assert _parent_exited(None) is False
    assert _parent_exited(5000) is False
    assert _parent_exited(4999) is True


def test_desktop_watch_parent_triggers_shutdown_on_parent_exit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    server: Any = SimpleNamespace(should_exit=False)
    monkeypatch.setattr(os, "getppid", lambda: 1)
    # Prevent os.killpg from firing against the test runner process group.
    monkeypatch.setattr(os, "getpgrp", lambda: -1)

    asyncio.run(_watch_parent(server, parent_pid=99999))
    assert server.should_exit is True
