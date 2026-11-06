"""Reference cache lifecycle regressions without external model assets."""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

import pytest

from src.services.comparison_cache import ComparisonCache


def _put(cache: ComparisonCache, audio: bytes = b"audio", ttl_seconds: float | None = None) -> None:
    cache.put("hello", audio, 8000, 1.0, "ogg", 50, [], ttl_seconds=ttl_seconds)


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


def test_cache_identity_preserves_exact_text_and_supports_namespace() -> None:
    cache = ComparisonCache(use_temp_files=False)
    cache.put("Hello", b"upper", 8000, 1.0, "ogg", 50, [])
    cache.put("hello", b"lower", 8000, 1.0, "ogg", 50, [])
    cache.put("hello", b"other", 8000, 1.0, "ogg", 50, [], namespace="provider/model-b")

    assert cache.get("Hello").audio_bytes == b"upper"
    assert cache.get("hello").audio_bytes == b"lower"
    assert cache.get("hello", namespace="provider/model-b").audio_bytes == b"other"
    assert cache.get("hello", namespace="provider/model-a") is None


@pytest.mark.parametrize("use_temp_files", [False, True])
def test_put_and_get_return_independent_snapshots(tmp_path: Path, use_temp_files: bool) -> None:
    cache = ComparisonCache(use_temp_files=use_temp_files, temp_dir=tmp_path)
    source_frames = [{"tract": {"tongue": 1}}]
    returned = cache.put("hello", b"audio", 8000, 1.0, "ogg", 50, source_frames)

    assert returned.audio_bytes == b"audio"
    source_frames[0]["tract"]["tongue"] = 2
    returned.frames[0]["tract"]["tongue"] = 3
    returned.audio_bytes = b"changed"

    cached = cache.get("hello")
    assert cached.audio_bytes == b"audio"
    assert cached.frames == [{"tract": {"tongue": 1}}]
    cached.frames[0]["tract"]["tongue"] = 4
    assert cache.get("hello").frames == [{"tract": {"tongue": 1}}]
    if use_temp_files:
        assert cache._cache[cache._normalize_text("hello")].audio_bytes == b""


def test_concurrent_cache_operations_and_clear_are_safe() -> None:
    cache = ComparisonCache(max_entries=8, use_temp_files=False)

    def worker(index: int) -> None:
        key = f"text-{index % 8}"
        for _ in range(40):
            cache.put(key, b"audio", 8000, 1.0, "ogg", 50, [{"index": index}])
            cache.get(key)
            if index % 3 == 0:
                cache.clear()

    with ThreadPoolExecutor(max_workers=8) as executor:
        list(executor.map(worker, range(8)))

    stats = cache.get_stats()
    assert 0 <= stats["entries"] <= cache.max_entries
