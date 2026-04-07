"""Comparison cache service for storing reference audio and articulatory frames.

Provides LRU caching with TTL for reference synthesis results keyed by
text content. Supports in-memory storage with optional temp file backing.
"""

import hashlib
import json
import tempfile
import time
from collections import OrderedDict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional


@dataclass
class ReferenceAsset:
    """Cached reference asset with audio and animation frames."""

    text_key: str  # Normalized text that generated this reference
    audio_bytes: bytes  # Compressed audio (OGG/Opus)
    audio_sample_rate: int
    audio_duration: float
    audio_format: str  # "ogg"
    frame_rate: int  # e.g., 50
    frames: list[dict]  # Canonical animation states
    frame_count: int
    created_at: float  # Unix timestamp
    ttl_seconds: float = 3600.0  # 1 hour default TTL

    def is_expired(self) -> bool:
        """Check if cache entry has exceeded TTL."""
        return (time.time() - self.created_at) > self.ttl_seconds

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "text_key": self.text_key,
            "audio_sample_rate": self.audio_sample_rate,
            "audio_duration": self.audio_duration,
            "audio_format": self.audio_format,
            "frame_rate": self.frame_rate,
            "frames": self.frames,
            "frame_count": self.frame_count,
            "created_at": self.created_at,
            "ttl_seconds": self.ttl_seconds,
            # audio_bytes stored separately
        }


class ComparisonCache:
    """LRU cache for reference audio and articulatory frames.

    Keys are normalized text strings. Entries expire after TTL.
    Optionally stores audio bytes in temp files to reduce memory pressure.
    """

    def __init__(
        self,
        max_entries: int = 50,
        default_ttl_seconds: float = 3600.0,
        use_temp_files: bool = True,
        temp_dir: Optional[Path] = None,
    ) -> None:
        """Initialize comparison cache.

        Args:
            max_entries: Maximum cached entries before LRU eviction
            default_ttl_seconds: Default TTL for new entries
            use_temp_files: Store audio bytes in temp files vs memory
            temp_dir: Directory for temp audio files (uses system temp if None)
        """
        self.max_entries = max_entries
        self.default_ttl_seconds = default_ttl_seconds
        self.use_temp_files = use_temp_files
        self.temp_dir = temp_dir or Path(tempfile.gettempdir())

        # LRU cache: OrderedDict maintains access order
        # Key: normalized text, Value: ReferenceAsset
        self._cache: OrderedDict[str, ReferenceAsset] = OrderedDict()

        # Track temp file paths for cleanup
        self._temp_files: dict[str, Path] = {}

        # Statistics
        self._hits = 0
        self._misses = 0
        self._evictions = 0

    def _normalize_text(self, text: str) -> str:
        """Normalize text for cache key.

        Lowercases, strips whitespace, and generates consistent key.
        """
        normalized = text.lower().strip()
        # Hash long text to keep keys manageable
        if len(normalized) > 200:
            hash_suffix = hashlib.md5(normalized.encode()).hexdigest()[:12]
            normalized = normalized[:188] + f"...{hash_suffix}"
        return normalized

    def _get_audio_path(self, text_key: str) -> Path:
        """Get temp file path for audio storage."""
        hash_key = hashlib.md5(text_key.encode()).hexdigest()[:16]
        return self.temp_dir / f"ref_audio_{hash_key}.ogg"

    def get(self, text: str) -> Optional[ReferenceAsset]:
        """Retrieve cached reference asset if available and not expired.

        Args:
            text: Original target text

        Returns:
            ReferenceAsset if cache hit and not expired, else None
        """
        text_key = self._normalize_text(text)

        if text_key not in self._cache:
            self._misses += 1
            return None

        asset = self._cache[text_key]

        # Check expiration
        if asset.is_expired():
            self._remove(text_key)
            self._misses += 1
            return None

        # Move to end (most recently used)
        self._cache.move_to_end(text_key)

        # Load audio from temp file if needed
        if self.use_temp_files and text_key in self._temp_files:
            audio_path = self._temp_files[text_key]
            try:
                asset.audio_bytes = audio_path.read_bytes()
            except Exception as e:
                print(f"[ComparisonCache] Failed to load audio from {audio_path}: {e}")
                self._remove(text_key)
                self._misses += 1
                return None

        self._hits += 1
        return asset

    def put(
        self,
        text: str,
        audio_bytes: bytes,
        audio_sample_rate: int,
        audio_duration: float,
        audio_format: str,
        frame_rate: int,
        frames: list[dict],
        ttl_seconds: Optional[float] = None,
    ) -> ReferenceAsset:
        """Store reference asset in cache.

        Args:
            text: Original target text
            audio_bytes: Compressed audio data
            audio_sample_rate: Audio sample rate
            audio_duration: Audio duration in seconds
            audio_format: Audio format (e.g., "ogg")
            frame_rate: Animation frame rate
            frames: List of canonical animation state dictionaries
            ttl_seconds: Override default TTL

        Returns:
            Created ReferenceAsset
        """
        text_key = self._normalize_text(text)
        ttl = ttl_seconds or self.default_ttl_seconds

        # Evict LRU if at capacity
        if len(self._cache) >= self.max_entries and text_key not in self._cache:
            self._evict_lru()

        # Write audio to temp file if configured
        stored_audio_bytes = audio_bytes
        if self.use_temp_files:
            audio_path = self._get_audio_path(text_key)
            try:
                audio_path.write_bytes(audio_bytes)
                self._temp_files[text_key] = audio_path
                stored_audio_bytes = b""  # Empty, loaded from file
            except Exception as e:
                print(f"[ComparisonCache] Failed to write audio to {audio_path}: {e}")
                # Fall back to in-memory storage
                stored_audio_bytes = audio_bytes

        asset = ReferenceAsset(
            text_key=text_key,
            audio_bytes=stored_audio_bytes,
            audio_sample_rate=audio_sample_rate,
            audio_duration=audio_duration,
            audio_format=audio_format,
            frame_rate=frame_rate,
            frames=frames,
            frame_count=len(frames),
            created_at=time.time(),
            ttl_seconds=ttl,
        )

        # Store in cache (move to end = most recent)
        self._cache[text_key] = asset
        self._cache.move_to_end(text_key)

        return asset

    def _evict_lru(self) -> None:
        """Remove least recently used entry."""
        if not self._cache:
            return

        # First item is LRU
        lru_key = next(iter(self._cache))
        self._remove(lru_key)
        self._evictions += 1

    def _remove(self, text_key: str) -> None:
        """Remove entry from cache and cleanup temp files."""
        if text_key in self._cache:
            del self._cache[text_key]

        if text_key in self._temp_files:
            temp_path = self._temp_files.pop(text_key)
            try:
                temp_path.unlink(missing_ok=True)
            except Exception:
                pass

    def invalidate(self, text: str) -> bool:
        """Explicitly invalidate cache entry for text.

        Returns:
            True if entry existed and was removed
        """
        text_key = self._normalize_text(text)
        if text_key in self._cache:
            self._remove(text_key)
            return True
        return False

    def clear(self) -> None:
        """Clear all cached entries and cleanup temp files."""
        # Cleanup temp files
        for temp_path in self._temp_files.values():
            try:
                temp_path.unlink(missing_ok=True)
            except Exception:
                pass

        self._cache.clear()
        self._temp_files.clear()

    def get_stats(self) -> dict:
        """Get cache statistics."""
        return {
            "entries": len(self._cache),
            "hits": self._hits,
            "misses": self._misses,
            "evictions": self._evictions,
            "hit_rate": self._hits / (self._hits + self._misses)
            if (self._hits + self._misses) > 0
            else 0.0,
            "temp_files": len(self._temp_files),
        }

    def cleanup_expired(self) -> int:
        """Remove all expired entries. Returns count removed."""
        expired_keys = [key for key, asset in self._cache.items() if asset.is_expired()]
        for key in expired_keys:
            self._remove(key)
        return len(expired_keys)


# Global cache instance
_comparison_cache: Optional[ComparisonCache] = None


def get_comparison_cache() -> ComparisonCache:
    """Get or create global comparison cache instance."""
    global _comparison_cache
    if _comparison_cache is None:
        _comparison_cache = ComparisonCache()
    return _comparison_cache


def reset_comparison_cache() -> None:
    """Reset global comparison cache (for testing)."""
    global _comparison_cache
    if _comparison_cache is not None:
        _comparison_cache.clear()
    _comparison_cache = None
