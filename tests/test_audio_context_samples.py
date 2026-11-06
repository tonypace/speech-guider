"""AudioContext must preserve the waveform sample axis during resampling."""

from pathlib import Path

import numpy as np
import pytest
from scipy.io import wavfile

from src.audio.processor import AudioContext


@pytest.fixture(params=[16000, 24000])
def waveform_path(request: pytest.FixtureRequest, tmp_path: Path) -> Path:
    rate = int(request.param)
    waveform = 0.5 * np.sin(2 * np.pi * 220 * np.arange(rate) / rate)
    path = tmp_path / "waveform.wav"
    wavfile.write(path, rate, waveform.astype(np.float32))
    return path


def test_waveform_contains_every_mono_sample(waveform_path: Path) -> None:
    samples = AudioContext(str(waveform_path)).get_downsampled_tensor()
    assert samples.shape == (16000,)
    assert samples.dtype == np.float32
    assert np.std(samples) > 0.3
