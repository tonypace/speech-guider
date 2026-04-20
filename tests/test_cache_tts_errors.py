"""Regression tests for comparison_cache and reference_tts error paths."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestComparisonCacheErrorPaths:
    """Tests for comparison cache error handling."""

    def test_cache_temp_file_read_failure(self, tmp_path):
        """Cache temp file read failure should be handled gracefully."""
        from src.services.comparison_cache import CacheEntry, ComparisonCache

        cache = ComparisonCache(cache_dir=tmp_path, max_size=2)

        # Create a mock entry with a temp file that will fail to read
        entry = CacheEntry(
            audio_path="/nonexistent/audio.wav",
            canonical_frames=[{"test": "data"}],
            frame_rate=50,
            duration_seconds=1.0,
            created_at=0,
            access_count=0,
        )

        # Manually inject into cache
        cache._cache["test-key"] = entry
        cache._key_order.append("test-key")

        # Attempt to get should return the entry even if temp file missing
        result = cache.get("test-key")
        # Should return None since entry exists but audio file doesn't
        assert result is None

    def test_cache_temp_file_write_failure(self, tmp_path):
        """Cache temp file write failure should fall back to memory."""
        from src.services.comparison_cache import ComparisonCache

        cache = ComparisonCache(cache_dir=tmp_path, max_size=2)

        # Mock Path.write_bytes to fail
        with patch.object(Path, "write_bytes", side_effect=IOError("Disk full")):
            # This should not raise - it should fall back to memory-only storage
            cache.set(
                "test-key",
                audio_path="/fake/path.wav",
                canonical_frames=[{"test": "data"}],
                frame_rate=50,
                duration_seconds=1.0,
            )

            # Entry should still be in memory cache
            result = cache.get("test-key")
            assert result is not None
            assert result["canonical_frames"] == [{"test": "data"}]

    def test_cache_eviction_with_missing_temp_files(self, tmp_path):
        """Cache eviction should handle missing temp files gracefully."""
        from src.services.comparison_cache import ComparisonCache

        cache = ComparisonCache(cache_dir=tmp_path, max_size=2)

        # Add entries
        cache.set("key1", "/fake1.wav", [{"f": 1}], 50, 1.0)
        cache.set("key2", "/fake2.wav", [{"f": 2}], 50, 1.0)

        # Simulate temp files being deleted externally
        for key in cache._cache:
            cache._cache[key].audio_path = "/nonexistent/file.wav"

        # Add third entry to trigger eviction
        cache.set("key3", "/fake3.wav", [{"f": 3}], 50, 1.0)

        # Should not raise - eviction should handle missing files
        assert len(cache._cache) <= 2  # LRU evicted oldest

    def test_cache_cleanup_all_entries(self, tmp_path):
        """Cache cleanup_all should handle errors during cleanup."""
        from src.services.comparison_cache import ComparisonCache

        cache = ComparisonCache(cache_dir=tmp_path, max_size=2)

        # Add some entries
        cache.set("key1", "/fake1.wav", [{"f": 1}], 50, 1.0)
        cache.set("key2", "/fake2.wav", [{"f": 2}], 50, 1.0)

        # Mock unlink to fail
        with patch.object(Path, "unlink", side_effect=PermissionError("Access denied")):
            # Should not raise - errors should be logged and ignored
            cache.cleanup_all()


class TestReferenceTTSErrorPaths:
    """Tests for reference TTS error handling."""

    def test_espeak_not_found_raises_error(self):
        """When espeak-ng is not found, should raise FileNotFoundError."""
        from src.audio.reference_tts import EspeakTTSProvider

        provider = EspeakTTSProvider()

        with patch("shutil.which", return_value=None):
            with pytest.raises(FileNotFoundError, match="espeak-ng"):
                provider.synthesize("hello")

    def test_espeak_command_failure_raises_runtime_error(self):
        """espeak-ng command failure should raise RuntimeError."""
        from src.audio.reference_tts import EspeakTTSProvider

        provider = EspeakTTSProvider()

        with patch("shutil.which", return_value="/usr/bin/espeak-ng"):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(
                    returncode=1,
                    stderr="Phoneme conversion failed",
                )

                with pytest.raises(RuntimeError, match="espeak-ng command failed"):
                    provider.synthesize("hello")

    def test_espeak_timeout_raises_runtime_error(self):
        """espeak-ng timeout should raise RuntimeError."""
        from src.audio.reference_tts import EspeakTTSProvider

        provider = EspeakTTSProvider()

        with patch("shutil.which", return_value="/usr/bin/espeak-ng"):
            with patch("subprocess.run") as mock_run:
                from subprocess import TimeoutExpired

                mock_run.side_effect = TimeoutExpired("espeak-ng", 10)

                with pytest.raises(RuntimeError, match="timed out"):
                    provider.synthesize("hello")

    def test_empty_text_raises_value_error(self):
        """Empty text should raise ValueError."""
        from src.audio.reference_tts import EspeakTTSProvider

        provider = EspeakTTSProvider()

        with pytest.raises(ValueError, match="cannot be empty"):
            provider.synthesize("")

        with pytest.raises(ValueError, match="cannot be empty"):
            provider.synthesize("   ")

    def test_phoneme_conversion_failure_raises_error(self):
        """Phoneme conversion failure should raise RuntimeError."""
        from src.audio.reference_tts import EspeakTTSProvider

        provider = EspeakTTSProvider()

        with patch("shutil.which", return_value="/usr/bin/espeak-ng"):
            with patch("subprocess.run") as mock_run:
                # First call (synthesize) succeeds
                # Second call (phoneme conversion) fails
                mock_run.side_effect = [
                    MagicMock(returncode=0, stderr=""),  # First call - success
                    MagicMock(returncode=1, stderr="Invalid phoneme"),  # Second call - failure
                ]

                with pytest.raises(RuntimeError, match="espeak-ng"):
                    provider.synthesize_phonemes("hello")


class TestReferenceTTSFactory:
    """Tests for TTS provider factory error handling."""

    def test_unknown_provider_raises_value_error(self):
        """Unknown provider name should raise ValueError."""
        from src.audio.reference_tts import create_tts_provider

        with pytest.raises(ValueError, match="Unknown TTS provider"):
            create_tts_provider("unknown_provider")

    def test_espeak_provider_creation(self):
        """espeak provider should be created successfully."""
        from src.audio.reference_tts import EspeakTTSProvider, create_tts_provider

        provider = create_tts_provider("espeak")
        assert isinstance(provider, EspeakTTSProvider)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
