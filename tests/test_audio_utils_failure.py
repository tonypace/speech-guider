"""Regression tests for audio utility failure paths and exception handling."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import scipy.io.wavfile as wavfile


class TestAudioConversionFailureModes:
    """Tests for _convert_to_wav error handling."""

    def test_pydub_not_available_uses_ffmpeg(self, tmp_path):
        """When pydub is not available, should try ffmpeg."""
        from app.utils.audio import _convert_to_wav

        # Create a test audio file
        input_path = str(tmp_path / "test.mp3")
        # Write a dummy MP3 file (invalid but exists)
        Path(input_path).write_bytes(b"FAKE_MP3_DATA")

        with patch.dict("sys.modules", {"pydub": None}):
            with patch("subprocess.run") as mock_run:
                # Simulate successful ffmpeg conversion
                mock_run.return_value = MagicMock(returncode=0, stderr="")
                wav_path = str(tmp_path / "test.wav")

                with patch("os.path.exists", side_effect=lambda p: p == wav_path):
                    result = _convert_to_wav(input_path)
                    assert result == wav_path
                    mock_run.assert_called_once()

    def test_ffmpeg_timeout_raises_error(self, tmp_path):
        """ffmpeg timeout should raise AudioConversionError."""
        from app.utils.audio import AudioConversionError, _convert_to_wav

        input_path = str(tmp_path / "test.mp3")
        Path(input_path).write_bytes(b"FAKE_MP3_DATA")

        with patch.dict("sys.modules", {"pydub": None}):
            with patch("subprocess.run") as mock_run:
                from subprocess import TimeoutExpired

                mock_run.side_effect = TimeoutExpired("ffmpeg", 30)

                with pytest.raises(AudioConversionError) as exc_info:
                    _convert_to_wav(input_path)

                assert "timed out" in str(exc_info.value).lower()

    def test_ffmpeg_not_found_raises_error(self, tmp_path):
        """ffmpeg not in PATH should raise AudioConversionError."""
        from app.utils.audio import AudioConversionError, _convert_to_wav

        input_path = str(tmp_path / "test.mp3")
        Path(input_path).write_bytes(b"FAKE_MP3_DATA")

        with patch.dict("sys.modules", {"pydub": None}):
            with patch("subprocess.run") as mock_run:
                mock_run.side_effect = FileNotFoundError("ffmpeg not found")

                with pytest.raises(AudioConversionError) as exc_info:
                    _convert_to_wav(input_path)

                assert "ffmpeg not found" in str(exc_info.value).lower()

    def test_ffmpeg_failure_raises_error(self, tmp_path):
        """ffmpeg non-zero exit code should raise AudioConversionError."""
        from app.utils.audio import AudioConversionError, _convert_to_wav

        input_path = str(tmp_path / "test.mp3")
        Path(input_path).write_bytes(b"FAKE_MP3_DATA")

        with patch.dict("sys.modules", {"pydub": None}):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=1, stderr="Invalid data")

                with pytest.raises(AudioConversionError) as exc_info:
                    _convert_to_wav(input_path)

                assert "ffmpeg conversion failed" in str(exc_info.value)

    def test_pydub_import_error_falls_back(self, tmp_path):
        """ImportError for pydub should trigger fallback to ffmpeg."""
        from app.utils.audio import AudioConversionError, _convert_to_wav

        input_path = str(tmp_path / "test.mp3")
        Path(input_path).write_bytes(b"FAKE_MP3_DATA")

        # Mock pydub to raise ImportError on import
        mock_pydub = MagicMock()
        mock_pydub.AudioSegment.from_file.side_effect = ImportError("No ffmpeg backend")

        with patch.dict("sys.modules", {"pydub": mock_pydub}):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=1, stderr="Failed")

                with pytest.raises(AudioConversionError):
                    _convert_to_wav(input_path)


class TestSaveUploadToTemp:
    """Tests for save_upload_to_temp error handling."""

    @pytest.mark.asyncio
    async def test_conversion_failure_for_non_audio_format(self, tmp_path):
        """Non-audio format conversion failure should raise error."""
        import io

        from fastapi import UploadFile

        from app.utils.audio import AudioConversionError, save_upload_to_temp

        # Create an UploadFile with a non-audio extension
        content = b"not audio data"
        file = io.BytesIO(content)
        upload = UploadFile(filename="test.xyz", file=file)

        with patch("app.utils.audio._convert_to_wav") as mock_convert:
            mock_convert.side_effect = AudioConversionError("Cannot convert XYZ")

            with pytest.raises(AudioConversionError):
                await save_upload_to_temp(upload)

    @pytest.mark.asyncio
    async def test_wav_file_skips_conversion(self, tmp_path):
        """WAV files should not trigger conversion."""
        import io

        from fastapi import UploadFile

        from app.utils.audio import save_upload_to_temp

        # Create a real WAV file
        wav_path = tmp_path / "test.wav"
        sample_rate = 16000
        duration = 0.1
        t = __import__("numpy").linspace(0, duration, int(sample_rate * duration))
        waveform = __import__("numpy").sin(2 * __import__("numpy").pi * 440 * t)
        wavfile.write(
            str(wav_path), sample_rate, (waveform * 32767).astype(__import__("numpy").int16)
        )

        with open(wav_path, "rb") as f:
            upload = UploadFile(filename="test.wav", file=io.BytesIO(f.read()))

        with patch("app.utils.audio._convert_to_wav") as mock_convert:
            result = await save_upload_to_temp(upload)
            # Should not call conversion for WAV
            mock_convert.assert_not_called()
            assert result.endswith(".wav")


class TestCleanupTempFile:
    """Tests for cleanup_temp_file behavior."""

    def test_cleanup_missing_file_logs_but_does_not_raise(self, capsys):
        """Cleanup of missing file should log but not raise."""
        from app.utils.audio import cleanup_temp_file

        # Should not raise
        cleanup_temp_file("/nonexistent/path/file.wav")

        # Check log output
        captured = capsys.readouterr()
        assert "Failed to cleanup" in captured.out or captured.err

    def test_cleanup_existing_file_succeeds(self, tmp_path):
        """Cleanup of existing file should succeed."""
        from app.utils.audio import cleanup_temp_file

        test_file = tmp_path / "test.wav"
        test_file.write_text("test")

        cleanup_temp_file(str(test_file))
        assert not test_file.exists()

    def test_cleanup_permission_error_logs(self, capsys, tmp_path):
        """Cleanup permission error should log but not raise."""
        from app.utils.audio import cleanup_temp_file

        test_file = tmp_path / "test.wav"
        test_file.write_text("test")

        with patch("os.remove") as mock_remove:
            mock_remove.side_effect = PermissionError("Access denied")

            # Should not raise
            cleanup_temp_file(str(test_file))

            # Check log output
            captured = capsys.readouterr()
            assert "Failed to cleanup" in captured.out or captured.err


class TestAudioConversionError:
    """Tests for AudioConversionError exception."""

    def test_error_is_exception(self):
        """AudioConversionError should inherit from Exception."""
        from app.utils.audio import AudioConversionError

        assert issubclass(AudioConversionError, Exception)

    def test_error_preserves_message(self):
        """AudioConversionError should preserve error message."""
        from app.utils.audio import AudioConversionError

        error = AudioConversionError("Custom error message")
        assert str(error) == "Custom error message"

    def test_error_preserves_cause(self):
        """AudioConversionError should preserve exception cause."""
        from app.utils.audio import AudioConversionError

        original = FileNotFoundError("ffmpeg not found")
        try:
            raise AudioConversionError("Conversion failed") from original
        except AudioConversionError as e:
            assert e.__cause__ is original


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
