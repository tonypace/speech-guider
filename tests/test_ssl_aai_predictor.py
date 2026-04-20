"""Tests for SSL AAI predictor module."""

import tempfile
from pathlib import Path

import numpy as np
import pytest
import torch


def test_predictor_module_imports():
    """SSL AAI predictor module should import without errors."""

    from src.models.ssl_aai_predictor import AAIHead, SSLAAIPredictor

    assert SSLAAIPredictor is not None
    assert AAIHead is not None


def test_aai_head_shape():
    """AAIHead should produce correct output shape."""

    from src.models.ssl_aai_predictor import AAIHead

    head = AAIHead()
    # Simulate SSL features: (batch=1, time=10, hidden=768)
    features = torch.randn(1, 10, 768)
    output = head(features)

    assert output.shape == (1, 10, 9), f"Expected (1, 10, 9), got {output.shape}"


def test_predictor_default_checkpoint_path():
    """Predictor should have correct default checkpoint path."""

    from src.models.ssl_aai_predictor import _get_default_checkpoint_path

    path = _get_default_checkpoint_path()
    expected_suffix = Path("external/aai_portable0.1/best_model.pt")
    assert path.name == "best_model.pt"
    assert expected_suffix.parts[-3:] == path.parts[-3:]


def test_predictor_initialization():
    """Predictor should initialize with correct defaults."""

    from src.models.ssl_aai_predictor import SSLAAIPredictor

    predictor = SSLAAIPredictor()

    assert predictor.checkpoint_path.name == "best_model.pt"
    assert predictor.device in ["cpu", "cuda", "mps"]
    assert not predictor._loaded


def test_predictor_unloaded_raises():
    """Predictor should raise if predict called before load."""

    from src.models.ssl_aai_predictor import SSLAAIPredictor

    predictor = SSLAAIPredictor()
    dummy_audio = torch.zeros(16000)

    with pytest.raises(RuntimeError, match="Predictor not loaded"):
        predictor.predict(dummy_audio, sample_rate=16000)


@pytest.mark.skipif(
    not Path(
        "/Users/tonypace/Documents/Code/speech-guider/external/aai_portable0.1/best_model.pt"
    ).exists(),
    reason="Checkpoint not available",
)
def test_predictor_loads_checkpoint():
    """Predictor should load checkpoint successfully."""

    from src.models.ssl_aai_predictor import SSLAAIPredictor

    predictor = SSLAAIPredictor()
    predictor.load()

    assert predictor._loaded
    assert predictor._ssl_model is not None
    assert predictor._predictor_head is not None
    assert predictor._feature_extractor is not None

    predictor.cleanup()
    assert not predictor._loaded


@pytest.mark.skipif(
    not Path(
        "/Users/tonypace/Documents/Code/speech-guider/external/aai_portable0.1/best_model.pt"
    ).exists(),
    reason="Checkpoint not available",
)
def test_predictor_produces_valid_output():
    """Predictor should produce valid (T, 9) output from audio."""

    import scipy.io.wavfile

    from src.models.ssl_aai_predictor import SSLAAIPredictor

    predictor = SSLAAIPredictor()
    predictor.load()

    # Create a dummy 16kHz audio file
    duration = 1.0  # 1 second
    sample_rate = 16000
    t = np.linspace(0, duration, int(sample_rate * duration))
    audio = np.sin(2 * np.pi * 440 * t).astype(np.float32)  # 440Hz sine wave

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        scipy.io.wavfile.write(f.name, sample_rate, (audio * 32767).astype(np.int16))
        wav_path = f.name

    try:
        # Load and predict
        sample_rate_loaded, audio_data = scipy.io.wavfile.read(wav_path)
        if audio_data.dtype == np.int16:
            audio_data = audio_data.astype(np.float32) / 32768.0

        audio_tensor = torch.from_numpy(audio_data).float()
        output = predictor.predict(audio_tensor, sample_rate_loaded)

        # Validate output
        assert output.ndim == 2, f"Expected 2D output, got {output.ndim}D"
        assert output.shape[1] == 9, f"Expected 9 channels, got {output.shape[1]}"
        assert output.shape[0] > 0, "Expected at least one time frame"
        assert torch.isfinite(output).all(), "Output contains NaN or Inf"

        # Check values look robust_01 normalized (roughly [0, 1] range)
        output_np = output.numpy()
        for i in range(9):
            channel = output_np[:, i]
            assert channel.min() >= 0.0, f"Channel {i} below [0,1]: {channel.min()}"
            assert channel.max() <= 1.0, f"Channel {i} above [0,1]: {channel.max()}"

    finally:
        predictor.cleanup()
        Path(wav_path).unlink(missing_ok=True)


def test_predictor_adapter_integration():
    """Predictor output should work with AAI adapter."""

    from src.models.aai_adapter import (
        AAIConversionMetadata,
        aai_to_canonical_state,
        decode_aai_row,
    )

    # Simulate predictor output: (T, 9) robust_01 normalized values (uniform [0,1])
    tvs_robust = torch.rand(10, 9)  # 10 frames, 9 channels

    # Decode first frame
    first_frame = tvs_robust[0].tolist()
    tract_vars = decode_aai_row(first_frame)

    # Verify field order
    assert tract_vars.lp == first_frame[0]  # LP
    assert tract_vars.la == first_frame[1]  # LA
    assert tract_vars.ttcl == first_frame[2]  # TTCL
    assert tract_vars.ttcd == first_frame[3]  # TTCD
    assert tract_vars.tbcl == first_frame[4]  # TBCL
    assert tract_vars.tbcd == first_frame[5]  # TBCD
    assert tract_vars.vel == first_frame[6]  # VEL
    assert tract_vars.glo == first_frame[7]  # GLO
    assert tract_vars.lat == first_frame[8]  # LAT

    # Convert to canonical state
    metadata = AAIConversionMetadata(normalization="robust_01")
    canonical = aai_to_canonical_state(tract_vars, metadata=metadata)

    # Verify canonical fields present
    expected_fields = [
        "lip_aperture",
        "lip_protrusion",
        "tongue_tip_constriction_location",
        "tongue_tip_constriction_degree",
        "lateral_tongue_drop",
        "velic_aperture",
        "tongue_body_constriction_location",
        "tongue_body_constriction_degree",
        "glottal_aperture",
    ]
    for field in expected_fields:
        assert field in canonical, f"Missing canonical field: {field}"
        assert isinstance(canonical[field], float), f"Field {field} should be float"
        assert 0.0 <= canonical[field] <= 1.0, f"Field {field} should be normalized"


def test_aai_tv_order_matches_training():
    """AAI TV order must match training contract."""

    from src.models.ssl_aai_predictor import AAI_TV_ORDER

    expected = ("LP", "LA", "TTCL", "TTCD", "TBCL", "TBCD", "VEL", "GLO", "LAT")
    assert AAI_TV_ORDER == expected, f"AAI_TV_ORDER mismatch: {AAI_TV_ORDER}"


def test_predictor_cleanup_frees_memory():
    """Predictor cleanup should free model resources."""

    from src.models.ssl_aai_predictor import SSLAAIPredictor

    predictor = SSLAAIPredictor()

    # Mock loaded state
    predictor._ssl_model = object()
    predictor._predictor_head = object()
    predictor._feature_extractor = object()
    predictor._loaded = True

    predictor.cleanup()

    assert not predictor._loaded
    assert predictor._ssl_model is None
    assert predictor._predictor_head is None
    assert predictor._feature_extractor is None
