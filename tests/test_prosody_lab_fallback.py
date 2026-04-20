"""Regression tests for prosody_lab optional dependency fallbacks."""

import importlib
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
import scipy.io.wavfile as wavfile


class TestLibrosaFallback:
    """Tests for librosa optional dependency fallback paths."""

    def test_librosa_none_uses_scipy_fallback(self, tmp_path):
        """When librosa is None, pitch computation should use scipy fallback."""
        from src.audio.prosody_lab import _compute_pitch_track

        # Create test audio
        sample_rate = 22050
        duration = 0.5
        t = np.linspace(0, duration, int(sample_rate * duration))
        waveform = np.sin(2 * np.pi * 440 * t).astype(np.float32)

        # Mock librosa as None (not installed)
        with patch("src.audio.prosody_lab.librosa", None):
            result = _compute_pitch_track(waveform, sample_rate)

        # Should still produce results using scipy fallback
        assert "pitch_track" in result
        assert "mean_f0_hz" in result

    def test_librosa_onset_detect_failure_falls_back(self, tmp_path):
        """librosa onset detection failure should fall back to energy-based detection."""
        from src.audio.prosody_lab import _heuristic_syllable_markers

        sample_rate = 22050
        duration = 0.5
        t = np.linspace(0, duration, int(sample_rate * duration))
        waveform = np.sin(2 * np.pi * 440 * t).astype(np.float32)

        # Mock librosa to raise ValueError
        mock_librosa = MagicMock()
        mock_librosa.onset.onset_detect.side_effect = ValueError("Invalid audio")

        with patch("src.audio.prosody_lab.librosa", mock_librosa):
            markers = _heuristic_syllable_markers(waveform, sample_rate)

        # Should return list (possibly empty if fallback also fails)
        assert isinstance(markers, list)

    def test_librosa_pause_detection_failure_falls_back(self, tmp_path):
        """librosa pause detection failure should fall back to energy-based detection."""
        from src.audio.prosody_lab import _heuristic_pause_spans

        sample_rate = 22050
        duration = 0.5
        t = np.linspace(0, duration, int(sample_rate * duration))
        waveform = np.sin(2 * np.pi * 440 * t).astype(np.float32)

        # Mock librosa to raise ValueError
        mock_librosa = MagicMock()
        mock_librosa.effects.split.side_effect = ValueError("Invalid audio")

        with patch("src.audio.prosody_lab.librosa", mock_librosa):
            spans = _heuristic_pause_spans(waveform, sample_rate)

        # Should return list (from fallback)
        assert isinstance(spans, list)

    def test_librosa_pyin_failure_falls_back(self, tmp_path):
        """librosa pitch detection failure should fall back to spectral peak."""
        from src.audio.prosody_lab import _compute_pitch_track

        sample_rate = 22050
        duration = 0.5
        t = np.linspace(0, duration, int(sample_rate * duration))
        waveform = np.sin(2 * np.pi * 440 * t).astype(np.float32)

        # Mock librosa to raise ValueError on pyin
        mock_librosa = MagicMock()
        mock_librosa.note_to_hz.side_effect = [65.0, 1046.0]  # fmin, fmax
        mock_librosa.pyin.side_effect = ValueError("Invalid audio")

        with patch("src.audio.prosody_lab.librosa", mock_librosa):
            result = _compute_pitch_track(waveform, sample_rate)

        # Should still return results from fallback
        assert "pitch_track" in result


class TestSoundfileFallback:
    """Tests for soundfile optional dependency fallback paths."""

    def test_soundfile_none_uses_scipy_fallback(self, tmp_path):
        """When soundfile is None, audio loading should use scipy fallback."""
        from src.audio.prosody_lab import _load_audio_samples

        # Create a real WAV file
        wav_path = tmp_path / "test.wav"
        sample_rate = 16000
        duration = 0.1
        t = np.linspace(0, duration, int(sample_rate * duration))
        waveform = np.sin(2 * np.pi * 440 * t)
        wavfile.write(str(wav_path), sample_rate, (waveform * 32767).astype(np.int16))

        # Mock soundfile as None
        with patch("src.audio.prosody_lab.sf", None):
            y, sr = _load_audio_samples(str(wav_path), sample_rate)

        # Should load using scipy
        assert len(y) > 0
        assert sr == sample_rate

    def test_soundfile_load_failure_falls_back(self, tmp_path):
        """soundfile load failure should fall back to scipy."""
        from src.audio.prosody_lab import _load_audio_samples

        # Create a real WAV file
        wav_path = tmp_path / "test.wav"
        sample_rate = 16000
        duration = 0.1
        t = np.linspace(0, duration, int(sample_rate * duration))
        waveform = np.sin(2 * np.pi * 440 * t)
        wavfile.write(str(wav_path), sample_rate, (waveform * 32767).astype(np.int16))

        # Mock soundfile to raise ValueError
        mock_sf = MagicMock()
        mock_sf.read.side_effect = ValueError("Corrupted file")

        with patch("src.audio.prosody_lab.sf", mock_sf):
            y, sr = _load_audio_samples(str(wav_path), sample_rate)

        # Should load using scipy fallback
        assert len(y) > 0
        assert sr == sample_rate


class TestMyVoiceAnalysisFallback:
    """Tests for my-voice-analysis optional dependency fallback."""

    def test_module_not_available_uses_fallback(self, tmp_path):
        """When my-voice-analysis is not available, use heuristic metrics."""
        from src.audio.prosody_lab import _run_my_voice_analysis

        temp_dir = tmp_path
        wav_stem = "test"

        # Mock _load_my_voice_analysis_module to return None
        with patch("src.audio.prosody_lab._load_my_voice_analysis_module", return_value=None):
            metrics, raw_output = _run_my_voice_analysis(temp_dir, wav_stem)

        # Should return fallback metrics
        assert metrics["syllable_count"] == 0
        assert metrics["pause_count"] == 0
        assert raw_output == ""

    def test_module_missing_mysptotal_uses_fallback(self, tmp_path):
        """When mysp.total is not available, use heuristic metrics."""
        from src.audio.prosody_lab import _run_my_voice_analysis

        temp_dir = tmp_path
        wav_stem = "test"

        # Mock module without mysptotal attribute
        mock_module = SimpleNamespace()

        with patch(
            "src.audio.prosody_lab._load_my_voice_analysis_module",
            return_value=mock_module,
        ):
            metrics, raw_output = _run_my_voice_analysis(temp_dir, wav_stem)

        # Should return fallback metrics
        assert metrics["syllable_count"] == 0
        assert metrics["pause_count"] == 0
        assert raw_output == ""

    def test_mysptotal_failure_uses_fallback(self, tmp_path):
        """When mysptotal raises an error, use heuristic metrics."""
        from src.audio.prosody_lab import _run_my_voice_analysis

        temp_dir = tmp_path
        wav_stem = "test"

        # Mock module with failing mysptotal
        def failing_mysptotal(basename, folder):
            raise RuntimeError("Analysis failed")

        mock_module = SimpleNamespace(mysptotal=failing_mysptotal)

        with patch(
            "src.audio.prosody_lab._load_my_voice_analysis_module",
            return_value=mock_module,
        ):
            metrics, raw_output = _run_my_voice_analysis(temp_dir, wav_stem)

        # Should return fallback metrics after catching the error
        assert metrics["syllable_count"] == 0
        assert metrics["pause_count"] == 0


class TestNormalizeAudioFile:
    """Tests for _normalize_audio_file error handling."""

    def test_empty_audio_raises_valueerror(self, tmp_path):
        """Empty audio file should raise ValueError."""
        from src.audio.prosody_lab import _normalize_audio_file

        # Create an empty file
        audio_path = tmp_path / "empty.wav"
        wavfile.write(str(audio_path), 16000, np.array([], dtype=np.int16))

        output_path = tmp_path / "output.wav"

        with pytest.raises(ValueError, match="Audio file is empty"):
            _normalize_audio_file(str(audio_path), output_path, 16000)


class TestAnalyzeProsodyRecordingIntegration:
    """Integration tests for analyze_prosody_recording fallback behavior."""

    def test_complete_analysis_with_fallbacks(self, tmp_path):
        """Full analysis should work even with all optional deps missing."""
        from src.audio.prosody_lab import analyze_prosody_recording

        # Create a real WAV file
        audio_path = tmp_path / "test.wav"
        sample_rate = 44100
        duration = 1.0
        t = np.linspace(0, duration, int(sample_rate * duration))
        waveform = np.sin(2 * np.pi * 440 * t).astype(np.float32)
        wavfile.write(str(audio_path), sample_rate, (waveform * 32767).astype(np.int16))

        # Mock all optional dependencies as None
        with patch("src.audio.prosody_lab.librosa", None):
            with patch("src.audio.prosody_lab.sf", None):
                with patch(
                    "src.audio.prosody_lab._load_my_voice_analysis_module",
                    return_value=None,
                ):
                    result = analyze_prosody_recording(str(audio_path))

        # Should complete with fallback metrics
        assert "recording_id" in result
        assert "summary" in result
        assert "pitch_track" in result
        assert "analysis_source" in result
        assert result["analysis_source"] == "fallback"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
