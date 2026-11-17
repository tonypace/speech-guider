"""Tests for Prosody Lab analysis helpers."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from src.audio.prosody_lab import analyze_prosody_recording


def test_analyze_prosody_recording_returns_summary(
    dummy_wav_factory: Callable[..., Path],
    create_dummy_wav: Callable[..., tuple[int, NDArray[np.int16]]],
) -> None:
    sample_rate = 44100
    _, tone = create_dummy_wav(
        duration=0.4, sample_rate=sample_rate, frequency=220.0, amplitude=0.4
    )
    silence = np.zeros(int(sample_rate * 0.2), dtype=np.int16)
    audio_path = dummy_wav_factory(
        "sample.wav",
        sample_rate=sample_rate,
        waveform=np.concatenate([tone, silence, tone]),
    )

    result = analyze_prosody_recording(str(audio_path))

    assert result["recording_id"]
    assert result["analysis_source"] == "heuristic"
    assert result["summary"]["syllable_count"] > 0
    assert result["summary"]["pause_count"] > 0
    assert result["summary"]["rhythm_balance"] > 0
    assert result["summary"]["mean_f0_hz"] > 0
    assert len(result["pitch_track"]) > 0
    assert isinstance(result["syllable_onsets"], list)
