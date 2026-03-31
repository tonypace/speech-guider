"""State persistence for presets and other saved data."""

import json
import os
from pathlib import Path
from typing import Dict, Any

from src.models.articulatory import normalize_svg_state


PRESETS_FILE = Path("presets.json")


def load_presets() -> Dict[str, Dict[str, Any]]:
    """
    Load phoneme presets from JSON file.

    Returns:
        Dictionary of phoneme presets
    """
    if not PRESETS_FILE.exists():
        return normalize_presets(get_default_presets())

    try:
        with open(PRESETS_FILE, "r") as f:
            data = json.load(f)
            # Ensure all required fields exist
            defaults = get_default_presets()
            for key, value in defaults.items():
                if key not in data:
                    data[key] = value
            return normalize_presets(data)
    except (json.JSONDecodeError, IOError):
        return normalize_presets(get_default_presets())


def save_presets(presets: Dict[str, Dict[str, Any]]) -> None:
    """
    Save phoneme presets to JSON file.

    Args:
        presets: Dictionary of phoneme presets
    """
    with open(PRESETS_FILE, "w") as f:
        json.dump(presets, f, indent=2)


def save_preset(phoneme: str, preset: Dict[str, Any]) -> None:
    """
    Save a single preset.

    Args:
        phoneme: Phoneme symbol (e.g., 'i', 'u')
        preset: Preset data with 'name' and 'params' keys
    """
    presets = load_presets()
    presets[phoneme] = normalize_preset_entry(preset)
    save_presets(presets)


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
