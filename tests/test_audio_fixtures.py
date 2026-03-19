import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))


def create_dummy_wav(
    duration: float = 1.0, sample_rate: int = 16000, frequency: float = 440.0
) -> tuple[int, np.ndarray]:
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    waveform = np.sin(2 * np.pi * frequency * t)

    waveform_int16 = (waveform * 32767).astype(np.int16)

    return sample_rate, waveform_int16


def test_dummy_wav_creation() -> None:
    sample_rate, waveform = create_dummy_wav(duration=0.5, frequency=220.0)
    assert sample_rate == 16000
    assert len(waveform) == 8000
    assert waveform.dtype == np.int16
    assert np.max(np.abs(waveform)) <= 32767
