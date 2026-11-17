"""Regression tests for prosody_lab optional dependency fallbacks."""

from collections.abc import Callable
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from src.audio.prosody_lab import _load_audio_samples, analyze_prosody_recording


class TestSoundfileFallback:
    """Tests for soundfile optional dependency fallback paths."""

    def test_soundfile_none_uses_scipy_fallback(
        self, dummy_wav_factory: Callable[..., Path]
    ) -> None:
        """When soundfile is None, audio loading should use scipy fallback."""
        sample_rate = 16000
        wav_path = dummy_wav_factory(duration=0.1, sample_rate=sample_rate, frequency=440.0)

        with patch("src.audio.prosody_lab.sf", None):
            y, sr = _load_audio_samples(str(wav_path), sample_rate)

        assert len(y) > 0
        assert sr == sample_rate

    def test_soundfile_load_failure_falls_back(
        self, dummy_wav_factory: Callable[..., Path]
    ) -> None:
        """soundfile load failure should fall back to scipy."""
        sample_rate = 16000
        wav_path = dummy_wav_factory(duration=0.1, sample_rate=sample_rate, frequency=440.0)

        mock_sf = MagicMock()
        mock_sf.read.side_effect = ValueError("Corrupted file")

        with patch("src.audio.prosody_lab.sf", mock_sf):
            y, sr = _load_audio_samples(str(wav_path), sample_rate)

        assert len(y) > 0
        assert sr == sample_rate


class TestEmptyAudioHandling:
    """Tests for empty audio error handling in prosody analysis."""

    def test_empty_audio_raises_valueerror(self, dummy_wav_factory: Callable[..., Path]) -> None:
        """Empty audio file should raise ValueError."""
        audio_path = dummy_wav_factory(
            "empty.wav", sample_rate=16000, waveform=np.array([], dtype=np.int16)
        )

        with pytest.raises(ValueError, match="Audio file is empty"):
            analyze_prosody_recording(str(audio_path))


class TestAnalyzeProsodyRecordingIntegration:
    """Integration tests for analyze_prosody_recording."""

    def test_complete_analysis(self, dummy_wav_factory: Callable[..., Path]) -> None:
        """Full analysis should work."""
        audio_path = dummy_wav_factory(duration=1.0, sample_rate=44100, frequency=440.0)

        result = analyze_prosody_recording(str(audio_path))

        assert "recording_id" in result
        assert "summary" in result
        assert "pitch_track" in result
        assert result["analysis_source"] == "heuristic"
