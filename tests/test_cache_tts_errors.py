"""Regression tests for comparison_cache and reference_tts error paths."""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestComparisonCacheErrorPaths:
    """Tests for comparison cache error handling."""

    def test_cache_temp_file_read_failure(self, tmp_path):
        """Cache temp file read failure should be handled gracefully."""
        from src.services.comparison_cache import ComparisonCache

        cache = ComparisonCache(max_entries=2, use_temp_files=False)
        normalized = cache._normalize_text("test")
        entry = cache.put(
            text="test",
            audio_bytes=b"test audio",
            audio_sample_rate=8000,
            audio_duration=1.0,
            audio_format="ogg",
            frame_rate=50,
            frames=[{"test": "data"}],
        )

        # Manually corrupt the audio path to simulate read failure
        cache._temp_files[normalized] = tmp_path / "nonexistent.ogg"
        cache.use_temp_files = True

        result = cache.get("test")
        assert result is None

    def test_cache_temp_file_write_failure(self, tmp_path):
        """Cache temp file write failure should fall back to memory."""
        from pathlib import Path

        from src.services.comparison_cache import ComparisonCache

        cache = ComparisonCache(max_entries=2, use_temp_files=True)

        with patch.object(Path, "write_bytes", side_effect=IOError("Disk full")):
            entry = cache.put(
                text="test",
                audio_bytes=b"test audio",
                audio_sample_rate=8000,
                audio_duration=1.0,
                audio_format="ogg",
                frame_rate=50,
                frames=[{"test": "data"}],
            )

            assert entry is not None
            assert len(entry.frames) > 0

    def test_cache_eviction_handles_errors(self, tmp_path):
        """Cache eviction should handle errors gracefully."""
        from src.services.comparison_cache import ComparisonCache

        cache = ComparisonCache(max_entries=2, use_temp_files=False)

        cache.put("key1", b"data1", 8000, 1.0, "ogg", 50, [{"f": 1}])
        cache.put("key2", b"data2", 8000, 1.0, "ogg", 50, [{"f": 2}])
        cache.put("key3", b"data3", 8000, 1.0, "ogg", 50, [{"f": 3}])

        assert len(cache._cache) <= 2

    def test_cache_cleanup_all_entries(self, tmp_path):
        """Cache cleanup_all should handle errors during cleanup."""
        from src.services.comparison_cache import ComparisonCache

        cache = ComparisonCache(max_entries=2, use_temp_files=False)

        cache.put("key1", b"data1", 8000, 1.0, "ogg", 50, [{"f": 1}])
        cache.put("key2", b"data2", 8000, 1.0, "ogg", 50, [{"f": 2}])

        cache.clear()
        assert len(cache._cache) == 0


class TestOmniVoiceTTSErrorPaths:
    """Tests for OmniVoiceTTSProvider error paths."""

    def _make_env(self, tmp_path) -> dict:
        return {
            "OMNIVOICE_TTS_PATH": str(tmp_path / "omnivoice-tts"),
            "OMNIVOICE_MODEL_PATH": str(tmp_path / "model.gguf"),
            "OMNIVOICE_CODEC_PATH": str(tmp_path / "codec.gguf"),
            "OMNIVOICE_LANGUAGE": "English",
        }

    def _touch(self, path):
        Path(path).write_text("")

    def test_missing_env_raises_value_error(self):
        """Missing required env vars should raise ValueError."""
        from src.audio.reference_tts import OmniVoiceTTSProvider

        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="OMNIVOICE_TTS_PATH"):
                OmniVoiceTTSProvider()

    def test_binary_not_found_raises_file_not_found(self, tmp_path):
        """Binary missing should raise FileNotFoundError."""
        from src.audio.reference_tts import OmniVoiceTTSProvider

        self._touch(tmp_path / "model.gguf")
        self._touch(tmp_path / "codec.gguf")

        with pytest.raises(FileNotFoundError, match="omnivoice-tts binary not found"):
            OmniVoiceTTSProvider(
                tts_path=str(tmp_path / "nonexistent-tts"),
                model_path=str(tmp_path / "model.gguf"),
                codec_path=str(tmp_path / "codec.gguf"),
            )

    def test_model_not_found_raises_file_not_found(self, tmp_path):
        """Model missing should raise FileNotFoundError."""
        from src.audio.reference_tts import OmniVoiceTTSProvider

        self._touch(tmp_path / "omnivoice-tts")
        self._touch(tmp_path / "codec.gguf")
        os.chmod(tmp_path / "omnivoice-tts", 0o755)

        with pytest.raises(FileNotFoundError, match="omnivoice model not found"):
            OmniVoiceTTSProvider(
                tts_path=str(tmp_path / "omnivoice-tts"),
                model_path=str(tmp_path / "nonexistent-model.gguf"),
                codec_path=str(tmp_path / "codec.gguf"),
            )

    def test_codec_not_found_raises_file_not_found(self, tmp_path):
        """Codec missing should raise FileNotFoundError."""
        from src.audio.reference_tts import OmniVoiceTTSProvider

        self._touch(tmp_path / "omnivoice-tts")
        self._touch(tmp_path / "model.gguf")
        os.chmod(tmp_path / "omnivoice-tts", 0o755)

        with pytest.raises(FileNotFoundError, match="omnivoice codec not found"):
            OmniVoiceTTSProvider(
                tts_path=str(tmp_path / "omnivoice-tts"),
                model_path=str(tmp_path / "model.gguf"),
                codec_path=str(tmp_path / "nonexistent-codec.gguf"),
            )

    def test_synthesis_timeout_raises_runtime_error(self, tmp_path):
        """Subprocess timeout should raise RuntimeError."""
        from src.audio.reference_tts import OmniVoiceTTSProvider

        self._touch(tmp_path / "omnivoice-tts")
        self._touch(tmp_path / "model.gguf")
        self._touch(tmp_path / "codec.gguf")
        os.chmod(tmp_path / "omnivoice-tts", 0o755)

        provider = OmniVoiceTTSProvider(
            tts_path=str(tmp_path / "omnivoice-tts"),
            model_path=str(tmp_path / "model.gguf"),
            codec_path=str(tmp_path / "codec.gguf"),
        )

        from subprocess import TimeoutExpired

        with patch("subprocess.run", side_effect=TimeoutExpired("omnivoice-tts", 120)):
            with pytest.raises(RuntimeError, match="timed out"):
                provider.synthesize("hello")

    def test_synthesis_failure_raises_runtime_error(self, tmp_path):
        """Non-zero exit code should raise RuntimeError."""
        from src.audio.reference_tts import OmniVoiceTTSProvider

        self._touch(tmp_path / "omnivoice-tts")
        self._touch(tmp_path / "model.gguf")
        self._touch(tmp_path / "codec.gguf")
        os.chmod(tmp_path / "omnivoice-tts", 0o755)

        provider = OmniVoiceTTSProvider(
            tts_path=str(tmp_path / "omnivoice-tts"),
            model_path=str(tmp_path / "model.gguf"),
            codec_path=str(tmp_path / "codec.gguf"),
        )

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stderr="Synthesis failed")

            with pytest.raises(RuntimeError, match="omnivoice-tts failed"):
                provider.synthesize("hello")

    def test_empty_text_raises_value_error(self, tmp_path):
        """Empty text should raise ValueError."""
        from src.audio.reference_tts import OmniVoiceTTSProvider

        self._touch(tmp_path / "omnivoice-tts")
        self._touch(tmp_path / "model.gguf")
        self._touch(tmp_path / "codec.gguf")
        os.chmod(tmp_path / "omnivoice-tts", 0o755)

        provider = OmniVoiceTTSProvider(
            tts_path=str(tmp_path / "omnivoice-tts"),
            model_path=str(tmp_path / "model.gguf"),
            codec_path=str(tmp_path / "codec.gguf"),
        )

        with pytest.raises(ValueError, match="cannot be empty"):
            provider.synthesize("")

        with pytest.raises(ValueError, match="cannot be empty"):
            provider.synthesize("   ")

    def test_successful_synthesis_returns_reference_audio(self, tmp_path):
        """Successful synthesis should return ReferenceAudio with OGG bytes."""
        import numpy as np
        import soundfile as sf

        from src.audio.reference_tts import OmniVoiceTTSProvider

        self._touch(tmp_path / "omnivoice-tts")
        self._touch(tmp_path / "model.gguf")
        self._touch(tmp_path / "codec.gguf")
        os.chmod(tmp_path / "omnivoice-tts", 0o755)

        provider = OmniVoiceTTSProvider(
            tts_path=str(tmp_path / "omnivoice-tts"),
            model_path=str(tmp_path / "model.gguf"),
            codec_path=str(tmp_path / "codec.gguf"),
        )

        # Write a real WAV to the path that subprocess would produce
        wav_path = tmp_path / "omnivoice-tts-output.wav"

        def mock_subprocess_run(*args, **kwargs):
            sample_rate = 24000
            duration = 0.5
            t = np.linspace(0, duration, int(sample_rate * duration))
            waveform = np.sin(2 * np.pi * 440 * t).astype(np.float32)
            sf.write(str(wav_path), waveform, sample_rate)
            return MagicMock(returncode=0, stderr="")

        with patch("subprocess.run", side_effect=mock_subprocess_run):
            with patch("tempfile.NamedTemporaryFile") as mock_tmp:
                mock_tmp.return_value.__enter__.return_value.name = str(wav_path)
                result = provider.synthesize("hello")

        assert result.audio_bytes is not None
        assert len(result.audio_bytes) > 0
        assert result.sample_rate == 8000
        assert result.duration_seconds > 0
        assert result.format == "ogg"


class TestReferenceTTSFactory:
    """Tests for TTS provider factory."""

    def test_unknown_provider_raises_value_error(self):
        """Unknown provider name should raise ValueError."""
        from src.audio.reference_tts import TTSProviderFactory

        with pytest.raises(ValueError, match="Unknown TTS provider"):
            TTSProviderFactory.create("unknown_provider")

    def test_omnivoice_provider_creation(self):
        """omnivoice provider should be created successfully."""
        from src.audio.reference_tts import OmniVoiceTTSProvider, TTSProviderFactory

        with patch.dict(
            os.environ,
            {
                "OMNIVOICE_TTS_PATH": "/fake/bin",
                "OMNIVOICE_MODEL_PATH": "/fake/model.gguf",
                "OMNIVOICE_CODEC_PATH": "/fake/codec.gguf",
                "OMNIVOICE_LANGUAGE": "English",
            },
        ):
            with patch("os.path.isfile", return_value=True):
                provider = TTSProviderFactory.create("omnivoice")
                assert isinstance(provider, OmniVoiceTTSProvider)

    def test_default_provider_is_omnivoice(self):
        """Default provider should be OmniVoiceTTSProvider."""
        from src.audio.reference_tts import OmniVoiceTTSProvider, TTSProviderFactory

        with patch.dict(
            os.environ,
            {
                "OMNIVOICE_TTS_PATH": "/fake/bin",
                "OMNIVOICE_MODEL_PATH": "/fake/model.gguf",
                "OMNIVOICE_CODEC_PATH": "/fake/codec.gguf",
                "OMNIVOICE_LANGUAGE": "English",
            },
        ):
            with patch("os.path.isfile", return_value=True):
                provider = TTSProviderFactory.create()
                assert isinstance(provider, OmniVoiceTTSProvider)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
