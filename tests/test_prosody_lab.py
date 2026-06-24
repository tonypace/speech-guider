"""Tests for Prosody Lab analysis helpers."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import soundfile as sf

from src.audio.prosody_lab import analyze_prosody_recording


def _write_test_wav(path: Path) -> None:
    sample_rate = 44100
    tone_a = 0.4 * np.sin(
        2 * np.pi * 220 * np.linspace(0, 0.4, int(sample_rate * 0.4), endpoint=False)
    )
    silence = np.zeros(int(sample_rate * 0.2), dtype=np.float32)
    tone_b = 0.4 * np.sin(
        2 * np.pi * 220 * np.linspace(0, 0.4, int(sample_rate * 0.4), endpoint=False)
    )
    waveform = np.concatenate([tone_a, silence, tone_b]).astype(np.float32)
    sf.write(path, waveform, sample_rate, subtype="PCM_16")


def test_analyze_prosody_recording_returns_summary(tmp_path) -> None:
    audio_path = tmp_path / "sample.wav"
    _write_test_wav(audio_path)

    result = analyze_prosody_recording(str(audio_path))

    assert result["recording_id"]
    assert result["analysis_source"] == "heuristic"
    assert result["summary"]["syllable_count"] > 0
    assert result["summary"]["pause_count"] > 0
    assert result["summary"]["rhythm_balance"] > 0
    assert result["summary"]["mean_f0_hz"] > 0
    assert len(result["pitch_track"]) > 0
    assert isinstance(result["syllable_onsets"], list)
