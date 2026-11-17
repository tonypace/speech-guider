from collections.abc import Callable
from pathlib import Path

import numpy as np
import scipy.io.wavfile as wavfile
from numpy.typing import NDArray


def test_dummy_wav_creation(
    create_dummy_wav: Callable[..., tuple[int, NDArray[np.int16]]],
) -> None:
    sample_rate, waveform = create_dummy_wav(duration=0.5, frequency=220.0)
    assert sample_rate == 16000
    assert len(waveform) == 8000
    assert waveform.dtype == np.int16
    assert np.max(np.abs(waveform)) <= 32767


def test_dummy_wav_multichannel_and_file_factory(
    dummy_wav_factory: Callable[..., Path],
) -> None:
    wav_path = dummy_wav_factory(
        "stereo.wav", duration=0.25, sample_rate=24000, frequency=330.0, channels=2
    )
    sr, data = wavfile.read(str(wav_path))
    assert sr == 24000
    assert data.shape == (6000, 2)
    assert data.dtype == np.int16
