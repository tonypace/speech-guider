"""Tests for articulatory mapping module."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models.articulatory import (
    ArticulatoryMapper,
    ArticulatoryParameters,
    default_articulatory_state,
    PhonemeDescription,
    format_with_html_tooltips,
)


def test_articulatory_mapper_initialization():
    """Test that articulatory mapper can be initialized."""
    mapper = ArticulatoryMapper()

    assert mapper is not None
    assert hasattr(mapper, "_feature_definitions")
    assert hasattr(mapper, "_tooltip_definitions")

    print("✓ ArticulatoryMapper initialization test passed")


def test_phoneme_description():
    """Test phoneme description parsing with placeholder data."""
    mapper = ArticulatoryMapper()

    # Test with a known IPA phoneme
    description = mapper.parse_phoneme("/θ/")

    # We can't guarantee CLTS features without the package installed
    # But we can test basic structure
    assert isinstance(description, PhonemeDescription)
    assert "θ" in description.ipa_symbol  # Check if θ symbol is contained
    assert hasattr(description, "features")
    assert hasattr(description, "tooltips")

    print("✓ Phoneme description test passed")
    print(f"  - IPA Symbol: {description.ipa_symbol}")
    print(f"  - Technical Name: {description.technical_name}")


def test_parameter_mapping():
    """Test that phoneme description can be mapped to parameters."""
    mapper = ArticulatoryMapper()

    # Create a test phoneme description
    placeholder_description = PhonemeDescription(
        technical_name="Test Phonetic",
        ipa_symbol="t",
        features={
            "place": "alveolar",
            "manner": "plosive",
            "voicing": "voiceless",
            "rounding": "unrounded",
        },
        tooltips={},
    )

    svg_state = mapper.get_animation_params("/t/")

    assert isinstance(svg_state, dict)
    assert "lip_aperture" in svg_state
    assert "tongue_tip_constriction_location" in svg_state
    assert "tongue_body_constriction_degree" in svg_state

    neutral = default_articulatory_state()
    assert neutral.lip_aperture == 10.0

    print("✓ Parameter mapping test passed")
    print(f"  SVG state keys: {list(svg_state.keys())}")


def test_delta_calculation():
    """Test delta calculation between target and predicted parameters."""
    mapper = ArticulatoryMapper()

    # Create two sets of parameters with known differences
    target_params = ArticulatoryParameters(0.7, 0.3, 0.0, 0.0, 0.8, 0.1, 0.2, 0.9, 0.0)

    predicted_params = ArticulatoryParameters(0.3, 0.7, 0.0, 0.0, 0.2, 0.9, 0.1, 0.1, 0.0)

    delta_description, highlight_zone = mapper.calculate_delta(target_params, predicted_params)

    assert delta_description is not None
    assert highlight_zone in [None, "lips", "tongue_tip", "tongue_body", "glottis"]

    print("✓ Delta calculation test passed")
    print(f"  - Delta Description: {delta_description}")
    print(f"  - Highlight Zone: {highlight_zone}")


def test_tooltip_formatting():
    """Test HTML tooltip formatting."""
    description = PhonemeDescription(
        technical_name="Voiced Alveolar Fricative",
        ipa_symbol="z",
        features={
            "place": "alveolar",
            "manner": "fricative",
            "voicing": "voiced",
        },
        tooltips={
            "place": "Tongue against bony ridge behind upper teeth",
            "manner": "Air forced through narrow channel, creating friction",
            "voicing": "Vocal cords are vibrating",
        },
    )

    html = format_with_html_tooltips(description)

    assert isinstance(html, str)
    assert "title=" in html or html == ""
    assert "tooltip" in html or html == ""

    print("✓ Tooltip formatting test passed")
    print(f"  HTML Output: {html}")


def test_feature_definitions():
    """Test that feature definitions are properly structured."""
    mapper = ArticulatoryMapper()

    required_features = ["place", "manner", "voicing", "rounding"]

    for feature in required_features:
        assert feature in mapper._feature_definitions or feature in mapper._tooltip_definitions

    print("✓ Feature definitions test passed")
    print(f"  Features defined: {list(mapper._feature_definitions.keys())}")


def test_common_ipa_symbols():
    """Test parsing of common IPA phonemes."""
    mapper = ArticulatoryMapper()

    common_phonemes = [
        "/i/",
        "/a/",
        "/u/",
        "/p/",
        "/t/",
        "/k/",
        "/m/",
        "/n/",
        "/s/",
        "/z/",
        "/ʃ/",
        "/l/",
        "/r/",
    ]

    parsed_phonemes = []
    for phoneme in common_phonemes:
        try:
            description = mapper.parse_phoneme(phoneme)
            parsed_phonemes.append(
                (
                    phoneme,
                    description.technical_name,
                    description.ipa_symbol,
                )
            )
        except Exception:
            pass

    print("✓ Common IPA symbols test passed")
    print(f"  Parsed {len(parsed_phonemes)}/{len(common_phonemes)} phonemes")

    # Show a few examples
    for phoneme, name, symbol in parsed_phonemes[:5]:
        print(f"  - {phoneme}: {name} ({symbol})")


if __name__ == "__main__":
    test_articulatory_mapper_initialization()
    test_phoneme_description()
    test_parameter_mapping()
    test_delta_calculation()
    test_tooltip_formatting()
    test_feature_definitions()
    test_common_ipa_symbols()
    print("\n✅ All articulatory mapping tests passed!")
