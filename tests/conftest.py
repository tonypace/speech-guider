"""Shared pytest fixtures and helpers for generating PCM WAV test audio."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any, Protocol

import numpy as np
import pytest
import scipy.io.wavfile as wavfile
from numpy.typing import NDArray


def create_dummy_wav(
    duration: float = 1.0,
    sample_rate: int = 16000,
    frequency: float = 440.0,
    channels: int = 1,
    amplitude: float = 1.0,
    modulated: bool = False,
) -> tuple[int, NDArray[np.int16]]:
    """Generate a mono or multi-channel 16-bit PCM sine waveform."""
    if channels < 1:
        raise ValueError("channels must be >= 1")

    num_samples = int(sample_rate * duration)
    t = np.linspace(0.0, duration, num_samples, endpoint=False)
    if modulated:
        # Simulate speech-like F0 and intensity variations for prosody/voice-quality checks.
        modulation = np.sin(2 * np.pi * 5.0 * t)
        envelope = 0.5 + 0.3 * np.sin(2 * np.pi * 2.0 * t)
        waveform = np.sin(2 * np.pi * frequency * t * (1.0 + 0.2 * modulation)) * envelope
    else:
        waveform = amplitude * np.sin(2 * np.pi * frequency * t)

    waveform_int16: NDArray[np.int16] = (np.clip(waveform, -1.0, 1.0) * 32767.0).astype(np.int16)
    if channels > 1:
        waveform_int16 = np.tile(waveform_int16[:, np.newaxis], (1, channels))
    return sample_rate, waveform_int16


def write_dummy_wav(
    path: Path,
    *,
    duration: float = 1.0,
    sample_rate: int = 16000,
    frequency: float = 440.0,
    channels: int = 1,
    amplitude: float = 1.0,
    modulated: bool = False,
    waveform: NDArray[Any] | None = None,
) -> Path:
    """Write a valid 16-bit PCM WAV file to ``path`` and return it."""
    if waveform is None:
        sr, pcm = create_dummy_wav(
            duration=duration,
            sample_rate=sample_rate,
            frequency=frequency,
            channels=channels,
            amplitude=amplitude,
            modulated=modulated,
        )
    else:
        sr = sample_rate
        arr = np.asarray(waveform)
        if arr.dtype == np.int16:
            pcm = arr
        else:
            pcm = (np.clip(arr, -1.0, 1.0) * 32767.0).astype(np.int16)

    path.parent.mkdir(parents=True, exist_ok=True)
    wavfile.write(str(path), sr, pcm)
    return path


class DummyWavFactory(Protocol):
    """Callable fixture protocol for creating temporary PCM WAV files."""

    def __call__(
        self,
        filename: str | None = None,
        *,
        duration: float = 1.0,
        sample_rate: int = 16000,
        frequency: float = 440.0,
        channels: int = 1,
        amplitude: float = 1.0,
        modulated: bool = False,
        waveform: NDArray[Any] | None = None,
    ) -> Path: ...


@pytest.fixture(name="create_dummy_wav")
def create_dummy_wav_fixture() -> Callable[..., tuple[int, NDArray[np.int16]]]:
    """Provide ``create_dummy_wav`` as a pytest fixture."""
    return create_dummy_wav


@pytest.fixture
def dummy_wav_factory(tmp_path: Path) -> DummyWavFactory:
    """Create uniquely named temporary PCM WAV files under pytest's ``tmp_path``."""
    counter = 0

    def _create(
        filename: str | None = None,
        *,
        duration: float = 1.0,
        sample_rate: int = 16000,
        frequency: float = 440.0,
        channels: int = 1,
        amplitude: float = 1.0,
        modulated: bool = False,
        waveform: NDArray[Any] | None = None,
    ) -> Path:
        nonlocal counter
        counter += 1
        target = tmp_path / (filename or f"dummy_{counter}.wav")
        return write_dummy_wav(
            target,
            duration=duration,
            sample_rate=sample_rate,
            frequency=frequency,
            channels=channels,
            amplitude=amplitude,
            modulated=modulated,
            waveform=waveform,
        )

    return _create
