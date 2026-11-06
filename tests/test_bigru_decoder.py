"""Tests for the Haskins layer-12 BiGRU decoder and combined AAI prediction."""

from pathlib import Path
from typing import Any, cast

import pytest
import torch

REPO_ROOT = Path("/Users/tonypace/Documents/Code/speech-guider")
BIGRU_WEIGHTS = REPO_ROOT / "external" / "aai_haskins_bigru" / "best_bigru.weights.pt"
BIGRU_META = REPO_ROOT / "AAI" / "AAI Files Models Documentation" / "best_composite.pt"
MLP_CHECKPOINT = REPO_ROOT / "external" / "aai_portable0.1" / "best_model.pt"


def test_bigru_decoder_imports():
    from src.models.bigru_decoder import BIGRU_TV_ORDER, BiGRUTVDecoder

    assert BiGRUTVDecoder is not None
    assert BIGRU_TV_ORDER == ("LP", "LA", "TTCL", "TTCD", "TBCL", "TBCD")


def test_bigru_state_dict_key_layout():
    """Decoder submodule names must load the released checkpoint strictly."""

    from src.models.bigru_decoder import BiGRUTVDecoder

    decoder = BiGRUTVDecoder()
    observed = {key for key in decoder.state_dict().keys()}

    # Released keys: input_net.0/3 (Linear), gru (2-layer BiGRU), output_net.0/3/6
    for key in [
        "input_net.0.weight",
        "input_net.0.bias",
        "input_net.3.weight",
        "input_net.3.bias",
        "gru.weight_ih_l0",
        "gru.weight_ih_l0_reverse",
        "gru.weight_ih_l1",
        "gru.weight_ih_l1_reverse",
        "gru.bias_ih_l1_reverse",
        "output_net.0.weight",
        "output_net.3.weight",
        "output_net.6.weight",
        "output_net.6.bias",
    ]:
        assert key in observed, f"Missing expected decoder key: {key}"


def test_bigru_forward_shape_channels():
    from src.models.bigru_decoder import BIGRU_OUTPUT_CHANNELS, BiGRUTVDecoder

    decoder = BiGRUTVDecoder().eval()
    with torch.inference_mode():
        # 2D single-utterance input -> (T, 6)
        out_2d = decoder(torch.randn(10, 768), lengths=None)
        # 3D batched input -> (B, T, 6)
        out_3d = decoder(torch.randn(2, 10, 768), lengths=None)
    assert out_2d.shape == (10, BIGRU_OUTPUT_CHANNELS), out_2d.shape
    assert out_3d.shape == (2, 10, BIGRU_OUTPUT_CHANNELS), out_3d.shape


def test_bigru_display_clamp_telemetry():
    from src.models.bigru_decoder import clamp_display, tongue_confidence_tier

    raw = torch.tensor([-0.2, 0.5, 1.5, 0.3, 0.1, 0.9])
    clipped, clip_fraction = clamp_display(raw)
    assert torch.equal(clipped, torch.tensor([-0.1, 0.5, 1.1, 0.3, 0.1, 0.9]))
    assert 0.0 < clip_fraction < 1.0

    # Tier boundary mapping
    assert tongue_confidence_tier(0.0) == "usable"
    assert tongue_confidence_tier(0.1) == "needs_caution"
    assert tongue_confidence_tier(0.5) == "do_not_trust_tongue_contact"


def test_bigru_default_checkpoint_path():
    from src.models.bigru_decoder import _get_default_bigru_checkpoint_path

    path = _get_default_bigru_checkpoint_path()
    assert path.name == "best_bigru.weights.pt"
    assert path.parent.name == "aai_haskins_bigru"


@pytest.mark.skipif(
    not MLP_CHECKPOINT.exists() or not BIGRU_WEIGHTS.exists(),
    reason="Checkpoints not available",
)
def test_predictor_loads_bigru_decoder() -> None:
    from src.models.legacy_aai_predictor import SSLAAIPredictor

    predictor = SSLAAIPredictor()
    predictor.load()
    assert predictor._bigru_decoder is not None
    predictor.cleanup()


def _load_meta_args() -> dict[str, Any]:
    metadata = torch.load(BIGRU_META, map_location="cpu", weights_only=False)
    return cast(dict[str, Any], metadata["args"])


@pytest.mark.skipif(
    not MLP_CHECKPOINT.exists() or not BIGRU_WEIGHTS.exists() or not BIGRU_META.exists(),
    reason="Checkpoints not available",
)
def test_bigru_metadata_parity() -> None:
    """Released metadata args must match the decoder's fixed architecture."""

    from src.models.bigru_decoder import BiGRUTVDecoder

    args = _load_meta_args()
    assert args["architecture"] == "paper_bigru"
    assert args["smoothing_head"] == "none"
    assert args["dropout"] == 0.3
    assert args["hidden_size"] == 192  # retained training argument, unused by paper_bigru

    decoder = BiGRUTVDecoder()
    state = torch.load(BIGRU_WEIGHTS, map_location="cpu", weights_only=True)
    decoder.load_state_dict(state, strict=True)


def test_aai_tv_order_slices_bigru():
    from src.models.bigru_decoder import BIGRU_TV_ORDER
    from src.models.ssl_aai_predictor import AAI_TV_ORDER

    assert BIGRU_TV_ORDER == AAI_TV_ORDER[:6]


@pytest.mark.skipif(
    not MLP_CHECKPOINT.exists() or not BIGRU_WEIGHTS.exists(),
    reason="Checkpoints not available",
)
def test_predict_combined_merges_channels() -> None:
    """Combined prediction: first 6 from BiGRU, last 3 from MLP head."""

    import numpy as np

    from src.models.legacy_aai_predictor import SSLAAIPredictor

    predictor = SSLAAIPredictor()
    predictor.load()

    t = np.linspace(0, 1.0, 16000)
    audio = np.sin(2 * np.pi * 440 * t).astype(np.float32)

    try:
        result = predictor.predict_combined(torch.from_numpy(audio).float(), 16000)

        tvs = result["tvs"].numpy()
        oral = result["oral"].numpy()
        supra = result["suprasegmental"].numpy()

        assert tvs.shape[1] == 9
        assert oral.shape[1] == 6
        assert supra.shape[1] == 3
        # Mixed merger: manual channel check
        assert np.allclose(tvs[:, :6], oral)
        assert np.allclose(tvs[:, 6:], supra)
        assert torch.isfinite(result["tvs"]).all()

        # Display bounds: merged clamped to [0, 1]
        assert tvs.min() >= 0.0 and tvs.max() <= 1.0

        # Supra channels equal a pure MLP predict on the same audio
        mlp_tvs = predictor.predict(torch.from_numpy(audio).float(), 16000).numpy()
        assert np.allclose(tvs[:, 6:], mlp_tvs[:, 6:])

        assert result["confidence"] in (
            "usable",
            "needs_caution",
            "do_not_trust_tongue_contact",
        )
        assert 0.0 <= result["clip_fraction"] <= 1.0
    finally:
        predictor.cleanup()


def test_predict_combined_unloaded_raises() -> None:
    from src.models.legacy_aai_predictor import SSLAAIPredictor

    predictor = SSLAAIPredictor()
    with pytest.raises(RuntimeError, match="Predictor not loaded"):
        predictor.predict_combined(torch.zeros(16000), sample_rate=16000)


def test_adapter_speaker_z_normalized_is_unit_interval():
    """speaker_z_normalized must reuse the robust_01-style direct rig path."""

    import numpy as np

    from src.models.aai_adapter import (
        UNIT_INTERVAL_NORMALIZATIONS,
        AAIConversionMetadata,
        aai_to_canonical_state,
        decode_aai_row,
    )

    assert "speaker_z_normalized" in UNIT_INTERVAL_NORMALIZATIONS

    payload_array = np.full((3, 9), 0.5, dtype=np.float32)
    metadata = AAIConversionMetadata(normalization="speaker_z_normalized")

    from src.models.aai_adapter import representative_aai_pose

    pose = representative_aai_pose(payload_array, normalization="speaker_z_normalized")
    state = aai_to_canonical_state(pose, metadata=metadata)
    for field in state.values():
        assert isinstance(field, float)
        assert 0.0 <= field <= 1.0

    row = decode_aai_row(payload_array[0].tolist())
    state_row = aai_to_canonical_state(row, metadata=metadata)
    for field in state_row.values():
        assert isinstance(field, float)
        assert 0.0 <= field <= 1.0
