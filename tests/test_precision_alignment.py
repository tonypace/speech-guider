"""Test precision forced alignment with phoneme classification."""

import numpy as np
import torch

from src.models.alignment import ForcedAligner, _classify_phoneme


def test_phoneme_classification():
    """Test that phonemes are correctly classified."""
    assert _classify_phoneme("i") == (True, True)
    assert _classify_phoneme("eɪ") == (True, True)
    assert _classify_phoneme("b") == (False, True)
    assert _classify_phoneme("p") == (False, False)
    assert _classify_phoneme("s") == (False, False)


def test_forced_alignment_basic():
    """Test basic forced alignment (placeholder behavior)."""
    sample_rate = 16_000
    duration_sec = 2.0
    t = np.linspace(0, duration_sec, int(sample_rate * duration_sec))
    audio_waveform = np.sin(2 * np.pi * 440 * t)
    audio_tensor = torch.from_numpy(audio_waveform).float()

    aligner = ForcedAligner()
    errors, alignment = aligner.analyze_pronunciation(audio_tensor, "hello world")

    assert alignment is not None
    assert alignment.total_duration == duration_sec


if __name__ == "__main__":
    test_phoneme_classification()
    test_forced_alignment_basic()
    print("\n✅ All precision alignment tests passed!")
