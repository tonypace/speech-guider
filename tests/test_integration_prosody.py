"""Integration test for prosody analysis in the application."""

import tempfile
from pathlib import Path

import numpy as np
import scipy.io.wavfile as wavfile
import torch

from src.audio import AudioContext, ProsodyAnalyzer
from src.models.alignment import ForcedAligner, _classify_phoneme


def test_phoneme_classification_logic():
    """Test phoneme classification works independently."""
    assert _classify_phoneme("i") == (True, True)
    assert _classify_phoneme("b") == (False, True)
    assert _classify_phoneme("p") == (False, False)
    assert _classify_phoneme("s") == (False, False)


def test_prosody_extraction_from_audio():
    """Test prosody metrics can be extracted from real audio."""
    sample_rate = 16_000
    duration = 2.0
    num_samples = int(sample_rate * duration)
    t = np.linspace(0, duration, num_samples)

    carrier_freq = 200.0 + 100.0 * np.sin(2 * np.pi * 3.0 * t)
    waveform = np.sin(2 * np.pi * carrier_freq * t)
    waveform = (waveform * 32767.0).astype(np.int16)

    temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    wavfile.write(temp_file.name, sample_rate, waveform)
    temp_file.close()

    try:
        audio_context = AudioContext(temp_file.name)
        prosody_analyzer = ProsodyAnalyzer(audio_context)

        prosody = prosody_analyzer.analyze_complete(vowel_timestamps=[], word_timestamps=[])

        assert prosody is not None
        assert hasattr(prosody, "pitch")
        assert hasattr(prosody, "rhythm")
        assert hasattr(prosody, "stress")
        assert prosody.pitch is not None
        assert prosody.pitch.f0_range >= 0.0
        assert len(prosody.pitch.f0_values) > 0
    finally:
        Path(temp_file.name).unlink()


def test_forced_aligner_placeholder():
    """Test forced aligner returns placeholder results without crashing."""
    audio_tensor = torch.linspace(0.0, 2.0, int(16_000 * 2.0))
    waveform = torch.sin(2 * torch.pi * 440 * audio_tensor).float()

    aligner = ForcedAligner()
    errors, alignment = aligner.analyze_pronunciation(waveform, "the weather is hot")

    assert alignment is not None
    assert alignment.total_duration == 2.0


if __name__ == "__main__":
    test_phoneme_classification_logic()
    test_prosody_extraction_from_audio()
    test_forced_aligner_placeholder()
    print("\n✅ All integration tests passed!")
