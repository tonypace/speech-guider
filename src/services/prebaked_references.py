"""Pre-baked offline reference audio & R5 articulatory frames for canned passages."""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_PREBAKED_PATH = (
    Path(__file__).resolve().parents[2] / "static" / "data" / "prebaked_references.json"
)


def _normalize_key(text: str) -> str:
    return " ".join(text.strip().split())


@lru_cache(maxsize=1)
def _load_prebaked_map() -> dict[str, dict[str, Any]]:
    if not DEFAULT_PREBAKED_PATH.is_file():
        return {}
    try:
        raw = json.loads(DEFAULT_PREBAKED_PATH.read_text(encoding="utf-8"))
        entries = raw.get("entries", {}) if isinstance(raw, dict) else {}
        return {
            _normalize_key(k): v
            for k, v in entries.items()
            if isinstance(k, str) and isinstance(v, dict)
        }
    except (OSError, json.JSONDecodeError):
        logger.warning(
            "Failed to load prebaked references at %s", DEFAULT_PREBAKED_PATH, exc_info=True
        )
        return {}


def clear_prebaked_cache() -> None:
    _load_prebaked_map.cache_clear()


def get_prebaked_reference(text: str) -> dict[str, Any] | None:
    """Return pre-baked reference payload for a canned text if available."""
    key = _normalize_key(text)
    if not key:
        return None
    return _load_prebaked_map().get(key)
