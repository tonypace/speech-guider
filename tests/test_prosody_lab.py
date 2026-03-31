"""Tests for Prosody Lab analysis helpers."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

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


def test_analyze_prosody_recording_returns_summary(tmp_path, monkeypatch) -> None:
    audio_path = tmp_path / "sample.wav"
    _write_test_wav(audio_path)

    stub_module = SimpleNamespace(
        mysptotal=lambda basename, folder: print(
            "number_of_syllables 6\n"
            "number_of_pauses 2\n"
            "rate_of_speech 3.1\n"
            "articulation_rate 4.2\n"
            "balance 0.67\n"
        )
    )
    monkeypatch.setattr("src.audio.prosody_lab._load_my_voice_analysis_module", lambda: stub_module)

    result = analyze_prosody_recording(str(audio_path))

    assert result["recording_id"]
    assert result["analysis_source"] == "my-voice-analysis"
    assert result["summary"]["syllable_count"] == 6
    assert result["summary"]["pause_count"] == 2
    assert result["summary"]["rhythm_balance"] == 0.67
    assert result["summary"]["mean_f0_hz"] > 0
    assert len(result["pitch_track"]) > 0
    assert isinstance(result["syllable_onsets"], list)
