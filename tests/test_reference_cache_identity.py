"""Provider and model revisions must partition generated reference assets."""

import base64
from pathlib import Path
from unittest.mock import Mock, patch

import torch
from fastapi.testclient import TestClient

from app.api.comparison import _generate_reference_asset
from app.main import app
from src.audio.reference_tts import OmniVoiceTTSProvider
from src.services.comparison_cache import ComparisonCache, ReferenceAsset


def test_provider_file_and_language_identity_changes(tmp_path: Path) -> None:
    binary, model, codec = (tmp_path / name for name in ("binary", "model", "codec"))
    for path in (binary, model, codec):
        path.write_bytes(b"asset")
    provider = OmniVoiceTTSProvider(str(binary), str(model), str(codec), "English")
    original = provider.cache_identity()
    model.write_bytes(b"updated model")
    assert provider.cache_identity() != original
    provider.language = "French"
    assert provider.cache_identity()["language"] == "French"


def test_reference_cache_partitions_provider_and_model_revisions() -> None:
    provider = Mock()
    provider.cache_identity.return_value = {"language": "English"}
    provider.synthesize.return_value = Mock(
        audio_bytes=b"new audio", sample_rate=8000, duration_seconds=1.0, format="ogg"
    )
    predictor = Mock()
    predictor.predict_with_metadata.return_value = {"tvs": torch.zeros((2, 9))}
    cache = ComparisonCache(use_temp_files=True)
    try:
        with (
            patch("app.api.comparison.TTSProviderFactory.create", return_value=provider),
            patch("app.api.comparison.get_ssl_predictor", return_value=predictor),
            patch(
                "app.api.comparison._prepare_reference_audio_tensor",
                return_value=torch.zeros(16000),
            ),
            patch(
                "app.api.comparison.get_ssl_cache_identity", return_value={"model": "r4-v1"}
            ) as model,
        ):
            first, hit = _generate_reference_asset("Hello!", cache=cache)
            assert not hit
            assert first.audio_bytes == b"new audio"
            assert _generate_reference_asset("Hello!", cache=cache)[1]
            provider.cache_identity.return_value = {"language": "French"}
            assert not _generate_reference_asset("Hello!", cache=cache)[1]
            model.return_value = {"model": "r4-v2"}
            assert not _generate_reference_asset("Hello!", cache=cache)[1]
            model.side_effect = lambda contact_enabled: {
                "model": "r4-v2",
                "contact": contact_enabled,
            }
            assert not _generate_reference_asset("Hello!", cache=cache, contact_enabled=True)[1]
            assert not _generate_reference_asset("Hello!", cache=cache, contact_enabled=False)[1]
            assert _generate_reference_asset("Hello!", cache=cache, contact_enabled=True)[1]
            assert provider.synthesize.call_count == 5
    finally:
        cache.clear()


def test_reference_animation_endpoint_validates_and_returns_frames() -> None:
    client = TestClient(app)

    blank = client.post("/api/reference-animation", json={"target_text": "   "})
    assert blank.status_code == 400
    assert "reference text" in blank.json()["detail"].lower()

    sample_frame = {
        "lip_aperture": 0.2,
        "lip_protrusion": 0.1,
        "tongue_tip_constriction_location": 0.5,
        "tongue_tip_constriction_degree": 0.3,
        "lateral_tongue_drop": 0.0,
        "velic_aperture": 0.0,
        "tongue_body_constriction_location": 0.4,
        "tongue_body_constriction_degree": 0.35,
        "glottal_aperture": 0.1,
    }
    asset = ReferenceAsset(
        text_key="hello world",
        audio_bytes=b"OGG_DATA",
        audio_sample_rate=8000,
        audio_duration=0.4,
        audio_format="ogg",
        frame_rate=50,
        frames=[sample_frame],
        frame_count=1,
        created_at=1.0,
    )
    with patch("app.api.comparison._generate_reference_asset", return_value=(asset, True)):
        resp = client.post(
            "/api/reference-animation",
            json={"target_text": "Hello world", "tts_provider": "omnivoice"},
        )

    assert resp.status_code == 200
    payload = resp.json()
    assert base64.b64decode(payload["audio_base64"]) == b"OGG_DATA"
    assert payload["audio_sample_rate"] == 8000
    assert payload["audio_format"] == "ogg"
    assert payload["frame_count"] == 1
    assert payload["cached"] is True
    assert payload["frames"][0]["lip_aperture"] == 0.2
