"""Tests for Wav2Vec2 model and forced alignment."""

import sys
from pathlib import Path

import pytest
import torch

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models.alignment import ForcedAligner, SentenceAlignment, WordAlignment
from src.models.wav2vec2 import Wav2Vec2Model


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


def test_wav2vec2_model_initialization() -> None:
    """Test that Wav2Vec2 model can be initialized."""
    model = Wav2Vec2Model()

    assert model.model_name == "facebook/wav2vec2-xlsr-53-espeak-cv-ft"
    assert hasattr(model, "processor")
    assert hasattr(model, "model")

    model.cleanup()


@pytest.mark.parametrize("frequency", [440.0, 880.0, 220.0])
def test_wav2vec2_transcription(frequency: float) -> None:
    """Test Wav2Vec2 transcription with different audio frequencies."""
    model = Wav2Vec2Model()
    audio_tensor = create_sine_wave(duration=1.0, frequency=frequency)

    result = model.transcribe(audio_tensor)

    assert "logits" in result
    assert "predicted_phonemes" in result
    assert "token_ids" in result
    assert isinstance(result["logits"], torch.Tensor)
    assert isinstance(result["predicted_phonemes"], str)
    assert isinstance(result["token_ids"], torch.Tensor)

    model.cleanup()


def test_forced_aligner_initialization() -> None:
    """Test forced aligner initialization."""
    aligner = ForcedAligner()

    assert aligner.model is not None
    assert hasattr(aligner.model, "model")
    assert hasattr(aligner.model, "processor")

    aligner.cleanup()


def test_forced_alignment_basic() -> None:
    """Test basic forced alignment functionality."""
    aligner = ForcedAligner()
    audio_tensor = create_sine_wave(duration=1.0)

    text = "test sentence alignment"
    alignment = aligner.align(audio_tensor, text)

    assert isinstance(alignment, SentenceAlignment)
    assert alignment.text == text
    assert len(alignment.words) == 3

    for word in alignment.words:
        assert isinstance(word, WordAlignment)
        assert isinstance(word.word, str)
        assert word.start_time < word.end_time

    aligner.cleanup()


def test_forced_alignment_empty_text() -> None:
    """Test forced alignment with empty text."""
    aligner = ForcedAligner()
    audio_tensor = create_sine_wave(duration=1.0)

    alignment = aligner.align(audio_tensor, "")

    assert alignment.text == ""
    assert len(alignment.words) == 0

    aligner.cleanup()


def test_word_alignment_timestamps() -> None:
    """Test that word alignment timestamps are valid."""
    aligner = ForcedAligner()
    audio_tensor = create_sine_wave(duration=1.0)

    text = "hello world"
    alignment = aligner.align(audio_tensor, text)

    # Check that timestamps are monotonically increasing
    prev_end = 0.0
    for word in alignment.words:
        assert word.start_time >= prev_end
        assert word.end_time > word.start_time
        prev_end = word.end_time

    # Check that last word doesn't exceed total duration
    assert alignment.words[-1].end_time <= alignment.total_duration

    aligner.cleanup()


def test_model_cleanup() -> None:
    """Test that model cleanup properly frees resources."""
    model = Wav2Vec2Model()

    # Verify model exists before cleanup
    assert model.model is not None

    model.cleanup()

    # After cleanup, these should no longer exist
    assert not hasattr(model, "model") or model.model is None


@pytest.mark.slow
def test_wav2vec2_device_selection() -> None:
    """Test that model loads on appropriate device."""
    cuda_available = torch.cuda.is_available()
    mps_available = torch.backends.mps.is_available()

    model_cpu = Wav2Vec2Model(device="cpu")
    assert model_cpu.device == "cpu"
    model_cpu.cleanup()

    if cuda_available:
        model_cuda = Wav2Vec2Model(device="cuda")
        assert model_cuda.device == "cuda"
        model_cuda.cleanup()

    if mps_available:
        model_mps = Wav2Vec2Model(device="mps")
        assert model_mps.device == "mps"
        model_mps.cleanup()


def test_auto_detect_device() -> None:
    """Test that auto-detection picks the best available device."""
    model = Wav2Vec2Model()

    if torch.cuda.is_available():
        assert model.device == "cuda"
    elif torch.backends.mps.is_available():
        assert model.device == "mps"
    else:
        assert model.device == "cpu"

    model.cleanup()
