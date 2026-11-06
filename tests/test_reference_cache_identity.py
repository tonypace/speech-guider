"""Provider and model revisions must partition generated reference assets."""

from pathlib import Path
from unittest.mock import Mock, patch

import torch

from app.api.comparison import _generate_reference_asset
from src.audio.reference_tts import OmniVoiceTTSProvider
from src.services.comparison_cache import ComparisonCache


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
    predictor.predict.return_value = torch.zeros((2, 9))
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
            assert provider.synthesize.call_count == 3
    finally:
        cache.clear()
