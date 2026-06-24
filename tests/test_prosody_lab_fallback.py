"""Regression tests for prosody_lab optional dependency fallbacks."""

from unittest.mock import MagicMock, patch

import numpy as np
import pytest
import scipy.io.wavfile as wavfile


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
    """Integration tests for analyze_prosody_recording."""

    def test_complete_analysis(self, tmp_path):
        """Full analysis should work."""
        from src.audio.prosody_lab import analyze_prosody_recording

        # Create a real WAV file
        audio_path = tmp_path / "test.wav"
        sample_rate = 44100
        duration = 1.0
        t = np.linspace(0, duration, int(sample_rate * duration))
        waveform = np.sin(2 * np.pi * 440 * t).astype(np.float32)
        wavfile.write(str(audio_path), sample_rate, (waveform * 32767).astype(np.int16))

        result = analyze_prosody_recording(str(audio_path))

        assert "recording_id" in result
        assert "summary" in result
        assert "pitch_track" in result
        assert result["analysis_source"] == "heuristic"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
