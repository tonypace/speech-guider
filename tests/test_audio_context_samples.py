"""AudioContext must preserve the waveform sample axis during resampling."""

from collections.abc import Callable
from pathlib import Path

import numpy as np
import pytest

from src.audio.processor import AudioContext


@pytest.fixture(params=[16000, 24000])
def waveform_path(request: pytest.FixtureRequest, dummy_wav_factory: Callable[..., Path]) -> Path:
    rate = int(request.param)
    return dummy_wav_factory(
        "waveform.wav", duration=1.0, sample_rate=rate, frequency=220.0, amplitude=0.5
    )


def test_waveform_contains_every_mono_sample(waveform_path: Path) -> None:
    samples = AudioContext(str(waveform_path)).get_downsampled_tensor()
    assert samples.shape == (16000,)
    assert samples.dtype == np.float32
    assert np.std(samples) > 0.3
