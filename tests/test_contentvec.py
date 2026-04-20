"""Tests for ContentVec model and SSL AAI predictor."""

import sys
from pathlib import Path

import pytest
import torch

sys.path.insert(0, str(Path(__file__).parent.parent))


def create_sine_wave(
    duration: float = 1.0, sample_rate: int = 16000, frequency: float = 440.0
) -> torch.Tensor:
    """Create a simple sine wave for testing.

    Args:
        duration: Duration in seconds
        sample_rate: Sample rate in Hz
        frequency: Frequency in Hz

    Returns:
        Audio tensor
    """
    t = torch.linspace(0.0, duration, int(sample_rate * duration))
    waveform = torch.sin(2 * torch.pi * frequency * t).float()
    return waveform


class TestContentVecModel:
    """Tests for ContentVec model wrapper."""

    def test_contentvec_model_initialization(self) -> None:
        """Test that ContentVec model can be initialized."""
        from src.models.contentvec import ContentVecModel

        model = ContentVecModel()

        assert model.model_name == "lengyue233/content-vec-best"
        assert model.SAMPLE_RATE == 16000
        assert model.FEATURE_DIM == 768
        assert hasattr(model, "feature_extractor")
        assert hasattr(model, "model")

        model.cleanup()

    def test_contentvec_extract_features_shape(self) -> None:
        """Test that feature extraction returns correct shape."""
        from src.models.contentvec import ContentVecModel

        model = ContentVecModel()
        audio_tensor = create_sine_wave(duration=1.0)

        features = model.extract_features(audio_tensor)

        # Should be (T, 768) where T is roughly duration * frame_rate
        assert features.dim() == 2
        assert features.shape[1] == 768
        assert features.shape[0] > 0  # At least some frames
        assert isinstance(features, torch.Tensor)

        model.cleanup()

    def test_contentvec_extract_features_2d_input(self) -> None:
        """Test that 2D input (batch dimension) is handled."""
        from src.models.contentvec import ContentVecModel

        model = ContentVecModel()
        audio_tensor = create_sine_wave(duration=1.0).unsqueeze(0)  # (1, samples)

        features = model.extract_features(audio_tensor)

        assert features.dim() == 2
        assert features.shape[1] == 768

        model.cleanup()

    def test_contentvec_wrong_sample_rate_raises(self) -> None:
        """Test that wrong sample rate raises ValueError."""
        from src.models.contentvec import ContentVecModel

        model = ContentVecModel()
        audio_tensor = create_sine_wave(duration=1.0)

        with pytest.raises(ValueError, match="sample rate must be 16000Hz"):
            model.extract_features(audio_tensor, sample_rate=22050)

        model.cleanup()

    @pytest.mark.slow
    def test_contentvec_device_selection(self) -> None:
        """Test that model loads on appropriate device."""
        from src.models.contentvec import ContentVecModel

        cuda_available = torch.cuda.is_available()
        mps_available = torch.backends.mps.is_available()

        # Test CPU explicitly
        model_cpu = ContentVecModel(device="cpu")
        assert model_cpu.device == "cpu"
        model_cpu.cleanup()

        if cuda_available:
            model_cuda = ContentVecModel(device="cuda")
            assert model_cuda.device == "cuda"
            model_cuda.cleanup()

        if mps_available:
            model_mps = ContentVecModel(device="mps")
            assert model_mps.device == "mps"
            model_mps.cleanup()

    def test_contentvec_auto_detect_device(self) -> None:
        """Test that auto-detection picks the best available device."""
        from src.models.contentvec import ContentVecModel

        model = ContentVecModel()

        if torch.cuda.is_available():
            assert model.device == "cuda"
        elif torch.backends.mps.is_available():
            assert model.device == "mps"
        else:
            assert model.device == "cpu"

        model.cleanup()

    def test_contentvec_cleanup(self) -> None:
        """Test that model cleanup properly frees resources."""
        from src.models.contentvec import ContentVecModel

        model = ContentVecModel()

        # Verify model exists before cleanup
        assert model.model is not None

        model.cleanup()

        # After cleanup, these should no longer exist
        assert not hasattr(model, "model") or model.model is None


class TestSSLAAIPredictor:
    """Tests for SSL AAI predictor with ContentVec + DANN."""

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

    def test_dann_predictor_head_forward(self) -> None:
        """Test DANN predictor head forward pass."""
        from src.models.ssl_aai_predictor import DANNPredictorHead

        head = DANNPredictorHead(input_dim=768, hidden_dim=256, output_dim=9)

        # Test with 2D input (T, 768)
        x = torch.randn(50, 768)
        output = head(x)

        assert output.shape == (50, 9)
        assert output.min() >= 0.0  # Clamped
        assert output.max() <= 1.0  # Clamped

        # Test with 3D input (B, T, 768)
        x_batch = torch.randn(2, 50, 768)
        output_batch = head(x_batch)

        assert output_batch.shape == (2, 50, 9)
        assert output_batch.min() >= 0.0
        assert output_batch.max() <= 1.0


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
