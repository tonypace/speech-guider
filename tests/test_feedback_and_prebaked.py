"""Tests for developer feedback packet export and pre-baked reference lookup."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from src.models.diagnostic_passages import DIAGNOSTIC_PASSAGES
from src.services.prebaked_references import (
    DEFAULT_PREBAKED_PATH,
    clear_prebaked_cache,
    get_prebaked_reference,
)


def test_export_feedback_writes_packet(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SPEECH_GUIDER_FEEDBACK_DIR", str(tmp_path))
    client = TestClient(app)

    resp = client.post(
        "/api/export-feedback",
        data={
            "tab": "analysis",
            "categories": json.dumps(["/t/ /d/ ends", "Timing"]),
            "note": "Dropped final /t/ on last word",
            "target_text": "bat bet",
            "payload": json.dumps({"status": "ok", "errors": []}),
        },
        files={"audio": ("student.wav", b"RIFF0000WAVEfmt ", "audio/wav")},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    packet_dir = Path(body["packet_dir"])
    assert packet_dir.is_dir()
    assert (packet_dir / "audio.wav").read_bytes() == b"RIFF0000WAVEfmt "
    assert "Dropped final /t/" in (packet_dir / "note.txt").read_text(encoding="utf-8")
    interaction = json.loads((packet_dir / "interaction.json").read_text(encoding="utf-8"))
    assert interaction["tab"] == "analysis"
    assert interaction["categories"] == ["/t/ /d/ ends", "Timing"]


def test_prebaked_references_cover_canned_texts_and_serve_without_inference() -> None:
    assert DEFAULT_PREBAKED_PATH.is_file(), f"Missing {DEFAULT_PREBAKED_PATH}"
    clear_prebaked_cache()

    for passage in DIAGNOSTIC_PASSAGES:
        entry = get_prebaked_reference(passage.text)
        assert entry is not None, f"Missing prebaked entry for passage {passage.id}"
        assert entry["audio_base64"]
        assert entry["frames"]

    client = TestClient(app)
    with patch(
        "app.api.comparison._generate_reference_asset",
        side_effect=AssertionError("should not synthesize"),
    ):
        resp = client.post(
            "/api/reference-animation", json={"target_text": DIAGNOSTIC_PASSAGES[0].text}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["cached"] is True
        assert data["audio_base64"]
        assert len(data["frames"]) > 0

    prosody_phrase = "I said FIFTEEN perCENT, not FIFty"
    with patch(
        "app.api.prosody_lab.generate_prosody_reference",
        side_effect=AssertionError("should not synthesize"),
    ):
        resp_p = client.post("/api/prosody-lab/reference", json={"target_text": prosody_phrase})
        assert resp_p.status_code == 200
        prosody_data = resp_p.json()
        assert prosody_data["audio_base64"]
        assert prosody_data["phrase"]
        assert prosody_data["analysis"]
