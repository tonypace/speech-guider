"""Shared app-data paths and locking for persisted local state."""

import os
from pathlib import Path
from threading import RLock

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _resolve_data_dir() -> Path:
    if data_dir := os.environ.get("SPEECH_GUIDER_DATA_DIR"):
        raw_path = Path(data_dir).expanduser()
    elif presets_file := os.environ.get("SPEECH_GUIDER_PRESETS_FILE"):
        raw_path = Path(presets_file).expanduser().parent
    else:
        raw_path = PROJECT_ROOT
    if not raw_path.is_absolute():
        raw_path = PROJECT_ROOT / raw_path
    return raw_path.resolve()


DATA_DIR = _resolve_data_dir()
STATE_LOCK = RLock()


def data_file(filename: str) -> Path:
    """Return the path for a persisted app-data file inside the data directory."""
    return DATA_DIR / filename
