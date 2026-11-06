"""R4 migration regressions: replay timing, shared API path, strict load and parity."""

import importlib
import sys
from pathlib import Path
from typing import Any
from unittest.mock import Mock

import numpy as np
import pytest
import torch

from src.models.ssl_aai_predictor import DEFAULT_R4_BUNDLE, SSLAAIPredictor


@pytest.fixture
def waveform() -> torch.Tensor:
    """A non-hop-aligned clip exposes dropped tails and accumulated frame drift."""
    time = torch.arange(16037, dtype=torch.float32) / 16000
    return 0.2 * torch.sin(2 * torch.pi * 220 * time)


@pytest.fixture
def replay_predictor(monkeypatch: pytest.MonkeyPatch) -> SSLAAIPredictor:
    predictor = SSLAAIPredictor(device="cpu")
    predictor._loaded = True
    # Interior output deliberately exceeds renderer bounds; raw must survive.
    raw = torch.tensor([-0.1, 1.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]).repeat(5, 1)
    monkeypatch.setattr(predictor, "_predict_window", Mock(return_value=raw))
    return predictor


@pytest.mark.parametrize("samples", [1, 160, 320, 321, 1599, 1600, 1601, 16037])
def test_replay_flushes_tail_without_padding_frames(
    replay_predictor: SSLAAIPredictor, samples: int
) -> None:
    result = replay_predictor.predict_with_metadata(torch.zeros(samples))
    frames = (samples + 319) // 320
    assert result["tvs"].shape == (frames, 9)
    assert torch.equal(result["center_samples"], torch.arange(frames) * 320 + 160)
    assert result["tvs_raw"][0, 0] == pytest.approx(-0.1)
    assert result["tvs_raw"][0, 1] == pytest.approx(1.1)
    assert result["tvs"][0, 0] == 0.0
    assert result["tvs"][0, 1] == 1.0
    assert result["metadata"]["clip_fraction"] == pytest.approx(2 / 9)
    assert "confidence" not in result["metadata"]  # BiGRU tiers do not qualify R4.
    predict_window = replay_predictor._predict_window
    assert isinstance(predict_window, Mock)
    assert predict_window.call_count == (samples + 1599) // 1600


def test_replay_resets_rolling_context_between_clips(
    monkeypatch: pytest.MonkeyPatch, waveform: torch.Tensor
) -> None:
    predictor = SSLAAIPredictor(device="cpu")
    predictor._loaded = True
    seen: list[np.ndarray] = []

    def record(window: np.ndarray) -> torch.Tensor:
        seen.append(window.copy())
        return torch.full((5, 9), 0.5)

    monkeypatch.setattr(predictor, "_predict_window", record)
    predictor.predict(waveform)
    seen.clear()
    predictor.predict(torch.ones(100))
    assert np.all(seen[0][:-3200] == 0)
    assert np.all(seen[0][-3200:-3100] == 1)
    assert np.all(seen[0][-3100:] == 0)


@pytest.mark.parametrize(
    "audio", [torch.empty(0), torch.zeros(2, 10), torch.tensor([float("nan")])]
)
def test_invalid_audio_rejected(replay_predictor: SSLAAIPredictor, audio: torch.Tensor) -> None:
    with pytest.raises(ValueError):
        replay_predictor.predict(audio)


def test_cache_retries_failed_load(monkeypatch: pytest.MonkeyPatch) -> None:
    from src.services import model_cache

    monkeypatch.setattr(model_cache, "_cached_ssl_predictor", None)
    instance = Mock()
    instance.load.side_effect = [RuntimeError("load failed"), None]
    factory = Mock(return_value=instance)
    monkeypatch.setattr(model_cache, "SSLAAIPredictor", factory)
    with pytest.raises(RuntimeError, match="load failed"):
        model_cache.get_ssl_predictor()
    assert model_cache._cached_ssl_predictor is None
    assert model_cache.get_ssl_predictor() is instance
    assert instance.load.call_count == 2


def test_student_and_reference_use_identical_r4_frames(
    monkeypatch: pytest.MonkeyPatch, replay_predictor: SSLAAIPredictor, waveform: torch.Tensor
) -> None:
    from app.api import analyze, comparison
    from src.services.comparison_cache import ComparisonCache

    monkeypatch.setattr(analyze, "get_ssl_predictor", lambda: replay_predictor)
    monkeypatch.setattr(comparison, "get_ssl_predictor", lambda: replay_predictor)
    monkeypatch.setattr(comparison, "_prepare_reference_audio_tensor", lambda audio: waveform)
    audio = Mock(audio_bytes=b"audio", sample_rate=8000, duration_seconds=1.0, format="ogg")
    provider = Mock()
    provider.cache_identity.return_value = {"implementation": "test-provider"}
    monkeypatch.setattr(comparison, "get_ssl_cache_identity", lambda: {"model": "test-r4"})
    provider.synthesize.return_value = audio
    monkeypatch.setattr(comparison.TTSProviderFactory, "create", lambda name: provider)
    _, student_frames, metadata = analyze.try_primary_ssl_analysis(waveform, 16000, True)
    asset, cached = comparison._generate_reference_asset(
        "hello", cache=ComparisonCache(use_temp_files=False)
    )
    assert not cached
    assert asset.frames == student_frames
    assert metadata["decoder"] == "r4_bounded_v12"
    assert metadata["layers"] == [7]
    assert metadata["contact_augmentation"] == "disabled"


def test_prediction_failure_does_not_fall_back_to_legacy(
    monkeypatch: pytest.MonkeyPatch, replay_predictor: SSLAAIPredictor
) -> None:
    from app.api import analyze

    monkeypatch.setattr(analyze, "get_ssl_predictor", lambda: replay_predictor)
    monkeypatch.setattr(
        replay_predictor, "_predict_window", Mock(side_effect=RuntimeError("bad R4"))
    )
    assert analyze.try_primary_ssl_analysis(torch.ones(1600), 16000, True) == (None, None, {})


@pytest.fixture(scope="module")
def real_predictor() -> Any:
    if not (DEFAULT_R4_BUNDLE / "weights/r4.pt").is_file():
        pytest.skip("Local R4 evaluation bundle unavailable")
    predictor = SSLAAIPredictor(device="cpu")
    predictor.load()
    yield predictor
    predictor.cleanup()


@pytest.mark.integration
def test_bundled_runtime_parity(
    real_predictor: SSLAAIPredictor, waveform: torch.Tensor, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Compare application output with the unmodified released replay runtime."""
    before = set(sys.modules)
    monkeypatch.syspath_prepend(str(DEFAULT_R4_BUNDLE))
    try:
        contracts = importlib.import_module("aai_streaming.contracts")
        backend_module = importlib.import_module("aai_streaming.pytorch_backend")
        checkpoints = importlib.import_module("aai_streaming.successor_checkpoint")
        contract = contracts.load_streaming_contract(
            DEFAULT_R4_BUNDLE / "configs/nine_channel_v12_100ms.yaml"
        )
        model, _ = checkpoints.load_successor_checkpoint(DEFAULT_R4_BUNDLE / "weights/r4.pt", "cpu")
        backend = backend_module.ContentVecV12Backend(
            contract,
            contentvec=real_predictor._ssl_model,
            processor=real_predictor._feature_extractor,
            v12=model,
            device="cpu",
        )
        for samples in (waveform, waveform[:321], torch.zeros(1600)):
            values = samples.numpy()
            hops = (len(values) + 1599) // 1600
            padded = np.pad(values, (0, (hops + 1) * 1600 - len(values)))
            runtime = backend.streaming_runtime()
            packets = []
            for hop in padded.reshape(-1, 1600):
                packet = runtime.append_hop(hop)
                if packet is not None:
                    packets.append(packet)
            actual = real_predictor.predict_with_metadata(samples)
            count = len(actual["tvs"])
            expected = np.concatenate([p.values for p in packets])[:count]
            np.testing.assert_allclose(actual["tvs_raw"].numpy(), expected, atol=1e-5, rtol=1e-5)
            centers = np.concatenate([p.center_samples for p in packets])[:count]
            np.testing.assert_array_equal(actual["center_samples"].numpy(), centers)
    finally:
        # The kit uses top-level imports; never leave them in application state.
        for name in set(sys.modules) - before:
            module_file = getattr(sys.modules[name], "__file__", None)
            if module_file and Path(module_file).is_relative_to(DEFAULT_R4_BUNDLE):
                sys.modules.pop(name)


@pytest.fixture
def decoder_payload() -> dict[str, Any]:
    """Small saved model exercises strict loading without local release weights."""
    from src.models.aai_adapter import AAI_TV_ORDER
    from src.models.r4_decoder import R4Decoder

    config = {
        "model": {
            "superb": False,
            "predictor_architecture": "conv",
            "input_size": 768,
            "predictor_hidden_size": 8,
            "num_tvs": 9,
            "contentvec_layer": 7,
            "output_activation": "hardtanh",
            "domain_hidden_size": 4,
            "num_domains": 2,
            "extension_head": {"enabled": True, "architecture": "lat_temporal_v12_compat"},
        }
    }
    metadata = {
        "format_version": "nine_channel_streaming_successor_v1",
        "architecture": "bounded_v12",
        "streaming_contract_version": "nine_channel_streaming_v1",
        "channels": list(AAI_TV_ORDER),
        "context_allocation": {
            "base_right_context": [1, 1, 1, 1],
            "lat_right_context": [1, 0],
            "oral_future_context_frames": 4,
            "lat_future_context_frames": 5,
        },
        "contentvec": {"layer": 7, "feature_width": 768},
    }
    return {
        "config": config,
        "metadata": metadata,
        "state_dict": R4Decoder(config, metadata).state_dict(),
    }


@pytest.mark.parametrize(
    "mutation", ["legacy", "channels", "context", "architecture", "missing_tensor"]
)
def test_reject_incompatible_checkpoints(
    decoder_payload: dict[str, Any], tmp_path: Path, mutation: str
) -> None:
    from src.models.r4_decoder import load_r4_decoder

    if mutation == "legacy":
        decoder_payload.pop("metadata")
    elif mutation == "channels":
        decoder_payload["metadata"]["channels"].reverse()
    elif mutation == "context":
        decoder_payload["metadata"]["context_allocation"]["lat_right_context"] = [2, 0]
    elif mutation == "architecture":
        decoder_payload["config"]["model"]["predictor_architecture"] = "paper_bigru"
    else:
        decoder_payload["state_dict"].pop("scale_factor")
    path = tmp_path / "bad.pt"
    torch.save(decoder_payload, path)
    with pytest.raises((ValueError, RuntimeError)):
        load_r4_decoder(path, "cpu")


def test_reject_incompatible_bundle_contract(tmp_path: Path) -> None:
    config_dir = tmp_path / "configs"
    config_dir.mkdir()
    (config_dir / "nine_channel_v12_100ms.yaml").write_text("version: wrong\n")
    predictor = SSLAAIPredictor(bundle_path=tmp_path, device="cpu")
    with pytest.raises(ValueError, match="streaming contract"):
        predictor._validate_contract()
