"""Integration test for prosody analysis in the application."""

from collections.abc import Callable
from pathlib import Path

import pytest
import torch

from src.audio import AudioContext, ProsodyAnalyzer
from src.models.alignment import ForcedAligner


def test_prosody_extraction_from_audio(dummy_wav_factory: Callable[..., Path]) -> None:
    """Test prosody metrics can be extracted from real audio."""
    wav_path = dummy_wav_factory(duration=2.0, frequency=200.0, modulated=True)

    audio_context = AudioContext(str(wav_path))
    prosody_analyzer = ProsodyAnalyzer(audio_context)

    prosody = prosody_analyzer.analyze_complete(vowel_timestamps=[], word_timestamps=[])

    assert prosody is not None
    assert hasattr(prosody, "pitch")
    assert hasattr(prosody, "rhythm")
    assert hasattr(prosody, "stress")
    assert prosody.pitch is not None
    assert prosody.pitch.f0_range >= 0.0
    assert len(prosody.pitch.f0_values) > 0


def test_forced_aligner_placeholder() -> None:
    """Test forced aligner returns placeholder results without crashing."""
    audio_tensor = torch.linspace(0.0, 2.0, int(16_000 * 2.0))
    waveform = torch.sin(2 * torch.pi * 440 * audio_tensor).float()

    aligner = ForcedAligner()
    errors, alignment = aligner.analyze_pronunciation(waveform, "the weather is hot")

    assert alignment is not None
    assert alignment.total_duration == 2.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
