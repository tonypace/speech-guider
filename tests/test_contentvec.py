"""Tests for SSL AAI predictor."""

import pytest
import torch


def create_sine_wave(
    duration: float = 1.0, sample_rate: int = 16000, frequency: float = 440.0
) -> torch.Tensor:
    """Create a simple sine wave for testing."""
    t = torch.linspace(0.0, duration, int(sample_rate * duration))
    waveform = torch.sin(2 * torch.pi * frequency * t).float()
    return waveform


class TestSSLAAIPredictor:
    """Tests for SSL AAI predictor with ContentVec-L7 + R4."""

    def test_ssl_predictor_initialization(self) -> None:
        """Test that SSL predictor can be initialized."""
        from src.models.ssl_aai_predictor import SSLAAIPredictor

        predictor = SSLAAIPredictor()

        assert predictor.MODEL_NAME == "lengyue233/content-vec-best"
        assert predictor.SAMPLE_RATE == 16000
        assert predictor.FEATURE_DIM == 768
        assert predictor.NUM_TVS == 9
        assert not predictor._loaded

    def test_ssl_predictor_not_loaded_raises(self) -> None:
        """Test that predict() raises if not loaded."""
        from src.models.ssl_aai_predictor import SSLAAIPredictor

        predictor = SSLAAIPredictor()
        audio_tensor = create_sine_wave(duration=1.0)

        with pytest.raises(RuntimeError, match="Predictor not loaded"):
            predictor.predict(audio_tensor)

    def test_ssl_predictor_checkpoint_not_found(self) -> None:
        """Test that load() raises FileNotFoundError for missing checkpoint."""
        from src.models.ssl_aai_predictor import SSLAAIPredictor

        predictor = SSLAAIPredictor(checkpoint_path="/nonexistent/path/model.pt")

        with pytest.raises(FileNotFoundError, match="checkpoint not found"):
            predictor.load()

    def test_ssl_predictor_invalid_sample_rate(self) -> None:
        """Test that predict() raises for wrong sample rate."""
        from src.models.ssl_aai_predictor import SSLAAIPredictor

        predictor = SSLAAIPredictor()
        audio_tensor = create_sine_wave(duration=1.0)

        # Mock loaded state
        predictor._loaded = True

        with pytest.raises(ValueError, match="sample rate must be 16000Hz"):
            predictor.predict(audio_tensor, sample_rate=22050)

    def test_ssl_predictor_output_validation(self) -> None:
        """Test output validation in predict()."""
        from src.models.ssl_aai_predictor import SSLAAIPredictor

        predictor = SSLAAIPredictor()

        # Test invalid output shapes
        with pytest.raises(ValueError, match="must be 2D"):
            predictor._validate_output(torch.randn(9))  # 1D

        with pytest.raises(ValueError, match="must have 9 channels"):
            predictor._validate_output(torch.randn(10, 5))  # Wrong channels

        with pytest.raises(ValueError, match="no time frames"):
            predictor._validate_output(torch.randn(0, 9))  # Empty

        # Test NaN values
        nan_output = torch.full((10, 9), float("nan"))
        with pytest.raises(ValueError, match="NaN or Inf"):
            predictor._validate_output(nan_output)

    def test_ssl_predictor_invalid_config_raises(self) -> None:
        """Test that SSLAAIPredictor rejects mismatched SSLFeatureConfig."""
        from src.models.ssl_aai_predictor import SSLAAIPredictor
        from src.models.ssl_common import SSLFeatureConfig

        bad_configs = [
            SSLFeatureConfig(sample_rate=22050),
            SSLFeatureConfig(target_layer=12),
            SSLFeatureConfig(feature_dim=512),
            SSLFeatureConfig(frame_rate=25),
        ]
        for config in bad_configs:
            with pytest.raises(ValueError, match="R4 requires 16 kHz"):
                SSLAAIPredictor(ssl_config=config)

    def test_ssl_predictor_input_audio_validation(self) -> None:
        """Test that predict() validates waveform dimensionality and finiteness."""
        from src.models.ssl_aai_predictor import SSLAAIPredictor

        predictor = SSLAAIPredictor()
        predictor._loaded = True

        with pytest.raises(ValueError, match="nonempty mono waveform"):
            predictor.predict(torch.zeros(0))

        with pytest.raises(ValueError, match="nonempty mono waveform"):
            predictor.predict(torch.zeros(2, 1600))

        bad_audio = torch.tensor([0.0, float("nan"), 0.1])
        with pytest.raises(ValueError, match="NaN or Inf"):
            predictor.predict(bad_audio)


class TestSSLCommonDeviceHelpers:
    """Tests for device selection and cache cleanup utilities."""

    def test_get_best_torch_device_prefers_mps_over_cuda(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Device priority must follow MPS > CUDA > CPU."""
        from src.models.ssl_common import get_best_torch_device

        monkeypatch.setattr(torch.backends.mps, "is_available", lambda: True)
        monkeypatch.setattr(torch.cuda, "is_available", lambda: True)
        assert get_best_torch_device() == "mps"

        monkeypatch.setattr(torch.backends.mps, "is_available", lambda: False)
        monkeypatch.setattr(torch.cuda, "is_available", lambda: True)
        assert get_best_torch_device() == "cuda"

        monkeypatch.setattr(torch.backends.mps, "is_available", lambda: False)
        monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
        assert get_best_torch_device() == "cpu"

    def test_clear_torch_device_cache_handles_none(self) -> None:
        """clear_torch_device_cache(None) must safely no-op."""
        from src.models.ssl_common import clear_torch_device_cache

        clear_torch_device_cache(None)


class TestAAIAdapter:
    """Tests for AAI adapter with robust_01 normalization."""

    def test_representative_aai_pose_robust_01(self) -> None:
        """Test representative pose with robust_01 normalization."""
        from src.models.aai_adapter import representative_aai_pose

        # Create frames with values in [0, 1] range
        frames = [
            [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9],
            [0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
            [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8],
        ]

        pose = representative_aai_pose(frames, normalization="robust_01")

        # Values should be clamped to [0, 1]
        assert 0.0 <= pose.lp <= 1.0
        assert 0.0 <= pose.la <= 1.0
        assert 0.0 <= pose.glo <= 1.0

    def test_representative_aai_pose_clamps_out_of_range(self) -> None:
        """Test that robust_01 clamps out-of-range values."""
        from src.models.aai_adapter import representative_aai_pose

        # Create frames with some out-of-range values
        # median([-0.5, 0.2]) = -0.15 -> clamped to 0.0
        # median([1.2, 0.3]) = 0.75 -> within range
        # median([0.9, 1.5]) = 1.2 -> clamped to 1.0
        frames = [
            [-0.5, 1.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9],
            [0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.5],
        ]

        pose = representative_aai_pose(frames, normalization="robust_01")

        # Values should be clamped to [0, 1] after median calculation
        assert pose.lp == 0.0  # median(-0.15) clamped to 0.0
        assert 0.0 <= pose.la <= 1.0  # median(0.75) within range
        assert pose.lat == 1.0  # median(1.2) clamped to 1.0

    def test_aai_to_canonical_state_robust_01(self) -> None:
        """Test conversion with robust_01 normalization."""
        from src.models.aai_adapter import (
            AAIConversionMetadata,
            AAITractVariables,
            aai_to_canonical_state,
        )

        # Create tract variables in [0, 1] range
        tvs = AAITractVariables(
            lp=0.5,
            la=0.6,
            ttcl=0.7,
            ttcd=0.8,
            tbcl=0.4,
            tbcd=0.3,
            vel=0.2,
            glo=0.9,
            lat=0.1,
        )

        metadata = AAIConversionMetadata(normalization="robust_01")
        state = aai_to_canonical_state(tvs, metadata=metadata)

        # All values should be in [0, 1] range
        assert 0.0 <= state["lip_protrusion"] <= 1.0
        assert 0.0 <= state["lip_aperture"] <= 1.0
        assert 0.0 <= state["tongue_tip_constriction_location"] <= 1.0
        assert 0.0 <= state["glottal_aperture"] <= 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
