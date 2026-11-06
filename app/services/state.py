"""State persistence for presets and other saved data."""

import json
import logging
import math
import os
import tempfile
from pathlib import Path
from threading import RLock
from typing import Any, Dict

from src.models.articulatory import normalize_svg_state

LOGGER = logging.getLogger(__name__)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
PRESETS_FILE = Path(
    os.environ.get("SPEECH_GUIDER_PRESETS_FILE", PROJECT_ROOT / "presets.json")
).expanduser()
if not PRESETS_FILE.is_absolute():
    PRESETS_FILE = PROJECT_ROOT / PRESETS_FILE
PRESETS_FILE = PRESETS_FILE.resolve()
_PRESETS_LOCK = RLock()


def load_presets() -> Dict[str, Dict[str, Any]]:
    """
    Load phoneme presets from JSON file.

    Returns:
        Dictionary of phoneme presets
    """
    with _PRESETS_LOCK:
        try:
            with PRESETS_FILE.open("r", encoding="utf-8") as preset_file:
                data = json.load(preset_file)
        except FileNotFoundError:
            return normalize_presets(get_default_presets())
        except (json.JSONDecodeError, OSError) as exc:
            LOGGER.warning("Could not read presets from %s: %s", PRESETS_FILE, exc)
            return normalize_presets(get_default_presets())

        if not isinstance(data, dict):
            LOGGER.warning("Ignoring malformed presets in %s: expected object", PRESETS_FILE)
            return normalize_presets(get_default_presets())

        defaults = get_default_presets()
        valid: dict[str, dict[str, Any]] = {}
        for phoneme, entry in data.items():
            if not isinstance(phoneme, str) or not isinstance(entry, dict):
                LOGGER.warning("Ignoring malformed preset entry in %s", PRESETS_FILE)
                continue
            if not isinstance(entry.get("name", "custom"), str):
                LOGGER.warning("Ignoring malformed name for preset %r", phoneme)
                continue
            params = entry.get("params", {})
            if not isinstance(params, dict) or not _has_finite_numeric_params(params):
                LOGGER.warning("Ignoring malformed parameters for preset %r", phoneme)
                continue
            valid[phoneme] = normalize_preset_entry(entry)
        return {**normalize_presets(defaults), **valid}


def save_presets(presets: Dict[str, Dict[str, Any]]) -> None:
    """
    Save phoneme presets to JSON file.

    Args:
        presets: Dictionary of phoneme presets
    """
    with _PRESETS_LOCK:
        temp_path: Path | None = None
        try:
            for phoneme, entry in presets.items():
                params = entry.get("params", {})
                if not isinstance(params, dict) or not _has_finite_numeric_params(params):
                    raise ValueError(f"Preset {phoneme!r} has invalid numeric parameters")
            normalized = normalize_presets(presets)
            PRESETS_FILE.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=PRESETS_FILE.parent,
                prefix=f".{PRESETS_FILE.name}.",
                suffix=".tmp",
                delete=False,
            ) as temp_file:
                temp_path = Path(temp_file.name)
                json.dump(normalized, temp_file, indent=2, allow_nan=False)
                temp_file.flush()
                os.fsync(temp_file.fileno())
            os.replace(temp_path, PRESETS_FILE)
        except (OSError, TypeError, ValueError):
            LOGGER.exception("Could not save presets to %s", PRESETS_FILE)
            raise
        finally:
            if temp_path is not None:
                try:
                    temp_path.unlink(missing_ok=True)
                except OSError:
                    LOGGER.warning("Could not remove temporary preset file %s", temp_path)


def save_preset(phoneme: str, preset: Dict[str, Any]) -> None:
    """
    Save a single preset.

    Args:
        phoneme: Phoneme symbol (e.g., 'i', 'u')
        preset: Preset data with 'name' and 'params' keys
    """
    with _PRESETS_LOCK:
        params = preset.get("params", {})
        if not isinstance(params, dict) or not _has_finite_numeric_params(params):
            raise ValueError("Preset parameters must be finite numbers")
        presets = load_presets()
        presets[phoneme] = normalize_preset_entry(preset)
        save_presets(presets)


def _has_finite_numeric_params(params: dict[str, Any]) -> bool:
    """Reject persisted nonnumeric values before the schema normalizer sees them."""

    return all(
        isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
        for value in params.values()
    )


def normalize_preset_entry(preset: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize a preset entry to the SVG articulatory schema."""

    params = preset.get("params", {})
    normalized_params = normalize_svg_state(params) if isinstance(params, dict) else params
    return {
        "name": preset.get("name", "custom"),
        "params": normalized_params,
    }


def normalize_presets(presets: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Normalize all presets to the SVG articulatory schema."""

    return {phoneme: normalize_preset_entry(preset) for phoneme, preset in presets.items()}


def get_default_presets() -> Dict[str, Dict[str, Any]]:
    """
    Get default phoneme presets based on IPA research.

    Returns:
        Dictionary of default phoneme presets
    """
    return {
        # High Front
        "i": {
            "name": "beat",
            "params": {
                "tongueIndex": 1.00,
                "tongueDiameter": 0.85,
                "lipRounding": 0.00,
                "voicing": 1.0,
            },
        },
        "ɪ": {
            "name": "kit",
            "params": {
                "tongueIndex": 0.85,
                "tongueDiameter": 0.70,
                "lipRounding": 0.00,
                "voicing": 1.0,
            },
        },
        # Mid Front
        "e": {
            "name": "dress",
            "params": {
                "tongueIndex": 0.80,
                "tongueDiameter": 0.40,
                "lipRounding": 0.00,
                "voicing": 1.0,
            },
        },
        "ɛ": {
            "name": "dress",
            "params": {
                "tongueIndex": 0.78,
                "tongueDiameter": 0.40,
                "lipRounding": 0.00,
                "voicing": 1.0,
            },
        },
        # Low Front
        "æ": {
            "name": "trap",
            "params": {
                "tongueIndex": 1.00,
                "tongueDiameter": 0.10,
                "lipRounding": 0.00,
                "voicing": 1.0,
            },
        },
        "a": {
            "name": "father",
            "params": {
                "tongueIndex": 0.00,
                "tongueDiameter": 0.10,
                "lipRounding": 0.00,
                "voicing": 1.0,
            },
        },
        # Central
        "ə": {
            "name": "about",
            "params": {
                "tongueIndex": 0.50,
                "tongueDiameter": 0.50,
                "lipRounding": 0.10,
                "voicing": 1.0,
            },
        },
        # Back
        "ʌ": {
            "name": "strut",
            "params": {
                "tongueIndex": 0.30,
                "tongueDiameter": 0.35,
                "lipRounding": 0.00,
                "voicing": 1.0,
            },
        },
        "ɑ": {
            "name": "hot",
            "params": {
                "tongueIndex": 0.00,
                "tongueDiameter": 0.10,
                "lipRounding": 0.00,
                "voicing": 1.0,
            },
        },
        "ɔ": {
            "name": "thought",
            "params": {
                "tongueIndex": 0.10,
                "tongueDiameter": 0.35,
                "lipRounding": 0.60,
                "voicing": 1.0,
            },
        },
        # High Back Rounded
        "ʊ": {
            "name": "foot",
            "params": {
                "tongueIndex": 0.15,
                "tongueDiameter": 0.70,
                "lipRounding": 0.70,
                "voicing": 1.0,
            },
        },
        "u": {
            "name": "goose",
            "params": {
                "tongueIndex": 0.00,
                "tongueDiameter": 0.85,
                "lipRounding": 1.00,
                "voicing": 1.0,
            },
        },
        "o": {
            "name": "boat",
            "params": {
                "tongueIndex": 0.15,
                "tongueDiameter": 0.70,
                "lipRounding": 0.90,
                "voicing": 1.0,
            },
        },
        # Rhotic
        "ɝ": {
            "name": "bird",
            "params": {
                "tongueIndex": 0.52,
                "tongueDiameter": 0.50,
                "lipRounding": 0.40,
                "voicing": 1.0,
            },
        },
        # Plosives
        "p": {
            "name": "pat",
            "params": {
                "tongueIndex": 0.50,
                "tongueDiameter": 1.00,
                "lipRounding": 1.00,
                "voicing": 0.0,
            },
        },
        "b": {
            "name": "bat",
            "params": {
                "tongueIndex": 0.50,
                "tongueDiameter": 1.00,
                "lipRounding": 1.00,
                "voicing": 1.0,
            },
        },
        "t": {
            "name": "tap",
            "params": {
                "tongueIndex": 1.00,
                "tongueDiameter": 1.00,
                "lipRounding": 0.00,
                "voicing": 0.0,
            },
        },
        "d": {
            "name": "dad",
            "params": {
                "tongueIndex": 1.00,
                "tongueDiameter": 1.00,
                "lipRounding": 0.00,
                "voicing": 1.0,
            },
        },
        "k": {
            "name": "cat",
            "params": {
                "tongueIndex": 0.00,
                "tongueDiameter": 1.00,
                "lipRounding": 0.00,
                "voicing": 0.0,
            },
        },
        "g": {
            "name": "go",
            "params": {
                "tongueIndex": 0.00,
                "tongueDiameter": 1.00,
                "lipRounding": 0.00,
                "voicing": 1.0,
            },
        },
        # Fricatives
        "f": {
            "name": "fin",
            "params": {
                "tongueIndex": 0.70,
                "tongueDiameter": 0.95,
                "lipRounding": 0.80,
                "voicing": 0.0,
            },
        },
        "v": {
            "name": "van",
            "params": {
                "tongueIndex": 0.70,
                "tongueDiameter": 0.95,
                "lipRounding": 0.80,
                "voicing": 1.0,
            },
        },
        "s": {
            "name": "sip",
            "params": {
                "tongueIndex": 1.00,
                "tongueDiameter": 0.95,
                "lipRounding": 0.00,
                "voicing": 0.0,
            },
        },
        "z": {
            "name": "zip",
            "params": {
                "tongueIndex": 1.00,
                "tongueDiameter": 0.95,
                "lipRounding": 0.00,
                "voicing": 1.0,
            },
        },
        "ʃ": {
            "name": "ship",
            "params": {
                "tongueIndex": 0.80,
                "tongueDiameter": 0.93,
                "lipRounding": 0.40,
                "voicing": 0.0,
            },
        },
        "ʒ": {
            "name": "measure",
            "params": {
                "tongueIndex": 0.80,
                "tongueDiameter": 0.93,
                "lipRounding": 0.40,
                "voicing": 1.0,
            },
        },
        "h": {
            "name": "hat",
            "params": {
                "tongueIndex": 0.00,
                "tongueDiameter": 0.50,
                "lipRounding": 0.00,
                "voicing": 0.0,
            },
        },
        # Approximants
        "w": {
            "name": "wet",
            "params": {
                "tongueIndex": 0.00,
                "tongueDiameter": 0.80,
                "lipRounding": 1.00,
                "voicing": 1.0,
            },
        },
        "j": {
            "name": "yes",
            "params": {
                "tongueIndex": 0.85,
                "tongueDiameter": 0.80,
                "lipRounding": 0.00,
                "voicing": 1.0,
            },
        },
        "l": {
            "name": "let",
            "params": {
                "tongueIndex": 1.00,
                "tongueDiameter": 0.85,
                "lipRounding": 0.00,
                "voicing": 1.0,
            },
        },
        "r": {
            "name": "red",
            "params": {
                "tongueIndex": 0.70,
                "tongueDiameter": 0.80,
                "lipRounding": 0.50,
                "voicing": 1.0,
            },
        },
    }
