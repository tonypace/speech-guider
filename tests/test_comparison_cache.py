"""Reference cache lifecycle regressions without external model assets."""

from pathlib import Path
from unittest.mock import patch

import pytest

from src.services.comparison_cache import ComparisonCache


def _put(cache: ComparisonCache, audio: bytes = b"audio", **kwargs: float) -> None:
    cache.put("hello", audio, 8000, 1.0, "ogg", 50, [], **kwargs)


def test_cache_instances_own_independent_audio_files(tmp_path: Path) -> None:
    first = ComparisonCache(temp_dir=tmp_path)
    second = ComparisonCache(temp_dir=tmp_path)
    _put(first, b"first")
    _put(second, b"second")

    assert first.get("hello").audio_bytes == b"first"
    first.clear()
    assert second.get("hello").audio_bytes == b"second"
    second.clear()
    assert not list(tmp_path.iterdir())


def test_failed_replacement_uses_new_memory_audio(tmp_path: Path) -> None:
    cache = ComparisonCache(temp_dir=tmp_path)
    _put(cache, b"old")
    with patch.object(Path, "write_bytes", side_effect=OSError("disk full")):
        _put(cache, b"new")

    assert cache.get("hello").audio_bytes == b"new"
    assert cache.get_stats()["temp_files"] == 0


def test_zero_ttl_expires_immediately() -> None:
    cache = ComparisonCache(use_temp_files=False)
    with patch("src.services.comparison_cache.time.time", return_value=100):
        _put(cache, ttl_seconds=0)
    with patch("src.services.comparison_cache.time.time", return_value=101):
        assert cache.get("hello") is None
    assert cache.get_stats()["misses"] == 1


@pytest.mark.parametrize("max_entries", [0, -1])
def test_invalid_capacity_rejected(max_entries: int) -> None:
    with pytest.raises(ValueError, match="max_entries"):
        ComparisonCache(max_entries=max_entries)
