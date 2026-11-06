"""Pitch-unit references independent of model checkpoints or real recordings."""

import math
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from app.api.analyze import serialize_prosody
from src.audio.processor import AudioContext, PitchContour, ProsodyAnalyzer, ProsodyMetrics


@pytest.mark.parametrize("base", [100.0, 200.0])
def test_coaching_uses_frequency_ratio_and_keeps_hz_payload(base: float) -> None:
    pitch = PitchContour([0.0, base, base * 2, float("nan")], base, base * 1.5, 1.0)
    assert pitch.range_semitones == pytest.approx(12.0)
    payload = serialize_prosody(ProsodyMetrics(pitch=pitch, rhythm=None, stress=None))
    assert payload["pitch_range"] == base
    assert payload["pitch_range_semitones"] == pytest.approx(12.0)
    assert payload["pitch_range_label"] == "nice variety"


@pytest.fixture
def octave_sweep(tmp_path: Path) -> Path:
    rate = 16000
    time = np.arange(rate * 2) / rate
    # Integrate a linear 120 -> 240 Hz sweep; phase is cycles, not instantaneous F0*t.
    phase = 120 * time + 0.5 * 60 * time**2
    signal = 0.5 * np.sin(2 * math.pi * phase)
    path = tmp_path / "octave.wav"
    sf.write(path, signal, rate)
    return path


def test_praat_tracks_known_octave_sweep(octave_sweep: Path) -> None:
    pitch = ProsodyAnalyzer(AudioContext(str(octave_sweep))).analyze_pitch()
    assert 10.0 < pitch.range_semitones <= 12.5
    assert 165 < pitch.mean_f0 < 195


def test_unvoiced_pitch_has_zero_movement() -> None:
    assert PitchContour([0.0, float("nan")], 0, 0, 0).range_semitones == 0.0
