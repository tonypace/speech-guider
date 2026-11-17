"""Simple mock test for articulatory module without pyclts dependency."""

import sys
import types
from pathlib import Path

import pytest

import src.models.articulatory as articulatory_module
from src.models.aai_adapter import parse_aai_animation_payload
from src.models.articulatory import (
    ArticulatoryMapper,
    ArticulatoryState,
    PhonemeDescription,
    default_articulatory_state,
)


@pytest.fixture
def mock_pyclts(monkeypatch: pytest.MonkeyPatch) -> None:
    """Inject a mock pyclts module without mutating sys.modules at import time."""

    class MockTranscriptionSystem:
        def __init__(self, name: str) -> None:
            self.name = name

        def __getitem__(self, symbol: str) -> object:
            raise KeyError(symbol)

    pyclts_mock = types.ModuleType("pyclts")
    pyclts_mock.TranscriptionSystem = MockTranscriptionSystem  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "pyclts", pyclts_mock)
    monkeypatch.setattr(articulatory_module, "pyclts", pyclts_mock)


def test_basic_structure(mock_pyclts: None) -> None:
    """Test that basic data structures work with mocked pyclts."""
    del mock_pyclts

    # Test dataclass instantiation
    state = default_articulatory_state()
    assert isinstance(state, ArticulatoryState)

    description = PhonemeDescription(
        technical_name="Voiced Alveolar Fricative",
        ipa_symbol="z",
        features={"place": "alveolar", "manner": "fricative", "voicing": "voiced"},
        tooltips={
            "place": "Tongue against bony ridge",
            "manner": "Air through narrow channel",
            "voicing": "Vibrating vocal cords",
        },
    )

    # Test mapper initialization and mocked pyclts lookup
    mapper = ArticulatoryMapper()
    assert len(mapper._tooltip_definitions) > 0
    unknown_desc = mapper.parse_phoneme("/unknown_symbol/")
    assert unknown_desc.technical_name == "Unknown: unknown_symbol"

    # Test parameter mapping
    mapped_params = mapper.map_to_parameters(description)
    assert mapped_params is not None
    svg_state = mapper.get_animation_params("/z/")
    assert "lip_aperture" in svg_state
    assert "tongue_tip_constriction_location" in svg_state

    fallback_state = mapper.get_animation_params("/unknown_symbol/")
    assert fallback_state["lip_aperture"] == state.lip_aperture


def test_static_assets() -> None:
    """Test that the current static assets exist."""
    js_path = Path("static/js/app.js")
    css_path = Path("static/css/vocal_tract.css")

    assert js_path.exists(), "JavaScript file not found"
    assert css_path.exists(), "CSS file not found"

    js_content = js_path.read_text()
    css_content = css_path.read_text()

    assert "window.switchTab" in js_content, "JavaScript missing app bootstrap"
    assert ".tooltip" in css_content, "CSS missing tooltip styling"


def test_aai_payload_parse_without_pyclts() -> None:
    """AAI adapter should work without pyclts dependency."""
    payload = {
        "source_dataset": "xrmb",
        "normalization": "raw",
        "values": [0.0, 25.0, 0.2, 3.0, 0.7, 4.0, 12.0, 1.0, 1.0],
    }

    state = parse_aai_animation_payload(payload)

    assert "lip_aperture" in state
    assert "glottal_aperture" in state
    assert state["tongue_tip_constriction_location"] == 0.2
    assert state["tongue_body_constriction_location"] == 0.7
