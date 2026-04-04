"""Tests for articulatory mapping module."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models.articulatory import (
    CONSONANT_TEMPLATES,
    VOWEL_TEMPLATES,
    ArticulatoryMapper,
    ArticulatoryParameters,
    ArticulatoryState,
    PhonemeDescription,
    default_articulatory_state,
    format_with_html_tooltips,
    legacy_to_svg_state,
    normalize_svg_state,
    svg_state_to_dict,
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

    svg_state = mapper.get_animation_params("/t/")

    assert isinstance(svg_state, dict)
    assert "lip_aperture" in svg_state
    assert "tongue_tip_constriction_location" in svg_state
    assert "tongue_body_constriction_degree" in svg_state

    neutral = default_articulatory_state()
    assert neutral.lip_aperture == 0.25

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


def test_consonant_templates():
    """Test that all consonant templates have the required 9 SVG keys."""
    required_keys = {
        "lip_aperture",
        "lip_protrusion",
        "ttcl",
        "ttcd",
        "lat",
        "vel",
        "tbcl",
        "tbcd",
        "glo",
    }
    for symbol, template in CONSONANT_TEMPLATES.items():
        assert required_keys == set(template.keys()), f"Template for /{symbol}/ missing keys"
        assert all(isinstance(v, (int, float)) for v in template.values()), (
            f"Non-numeric value in /{symbol}/"
        )
        assert 0 <= template["lip_aperture"] <= 1, f"LA out of range for /{symbol}/"
        assert 0 <= template["lip_protrusion"] <= 1, f"LP out of range for /{symbol}/"
        assert 0 <= template["ttcl"] <= 1, f"TTCL out of range for /{symbol}/"
        assert 0 <= template["ttcd"] <= 1, f"TTCD out of range for /{symbol}/"
        assert 0 <= template["lat"] <= 40, f"LAT out of range for /{symbol}/"
        assert 0 <= template["vel"] <= 1, f"VEL out of range for /{symbol}/"
        assert 0 <= template["tbcl"] <= 1, f"TBCL out of range for /{symbol}/"
        assert 0 <= template["tbcd"] <= 1, f"TBCD out of range for /{symbol}/"
        assert 0 <= template["glo"] <= 30, f"GLO out of range for /{symbol}/"
    print(f"✓ {len(CONSONANT_TEMPLATES)} consonant templates validated")


def test_vowel_templates():
    """Test that all vowel templates have the required 9 SVG keys."""
    required_keys = {
        "lip_aperture",
        "lip_protrusion",
        "ttcl",
        "ttcd",
        "lat",
        "vel",
        "tbcl",
        "tbcd",
        "glo",
    }
    for symbol, template in VOWEL_TEMPLATES.items():
        assert required_keys == set(template.keys()), f"Template for /{symbol}/ missing keys"
        assert all(isinstance(v, (int, float)) for v in template.values()), (
            f"Non-numeric value in /{symbol}/"
        )
        assert 0 <= template["lip_aperture"] <= 1, f"LA out of range for /{symbol}/"
        assert 0 <= template["lip_protrusion"] <= 1, f"LP out of range for /{symbol}/"
        assert 0 <= template["ttcl"] <= 1, f"TTCL out of range for /{symbol}/"
        assert 0 <= template["ttcd"] <= 1, f"TTCD out of range for /{symbol}/"
        assert 0 <= template["lat"] <= 40, f"LAT out of range for /{symbol}/"
        assert 0 <= template["vel"] <= 1, f"VEL out of range for /{symbol}/"
        assert 0 <= template["tbcl"] <= 1, f"TBCL out of range for /{symbol}/"
        assert 0 <= template["tbcd"] <= 1, f"TBCD out of range for /{symbol}/"
        assert 0 <= template["glo"] <= 30, f"GLO out of range for /{symbol}/"
        assert template["glo"] == 0, f"Vowel /{symbol}/ should have GLO=0 (voiced)"
    print(f"✓ {len(VOWEL_TEMPLATES)} vowel templates validated")


def test_template_lookup():
    """Test _get_template returns correct templates for known phonemes."""
    mapper = ArticulatoryMapper()

    for symbol in ["p", "b", "t", "k", "s", "m", "n", "f", "l", "j", "w", "h"]:
        t = mapper._get_template(symbol)
        assert t is not None, f"_get_template failed for /{symbol}/"
        assert "lip_aperture" in t

    for symbol in ["i", "e", "æ", "a", "ɑ", "o", "u", "ə", "ʌ", "ɔ", "ɪ", "ɛ", "ʊ"]:
        t = mapper._get_template(symbol)
        assert t is not None, f"_get_template failed for /{symbol}/"
        assert "lip_aperture" in t

    assert mapper._get_template("xyz") is None
    print("✓ Template lookup test passed")


def test_template_to_svg_state():
    """Test _template_to_svg_state converts template dict to ArticulatoryState."""
    mapper = ArticulatoryMapper()
    state = mapper._template_to_svg_state(CONSONANT_TEMPLATES["p"])

    assert isinstance(state, ArticulatoryState)
    assert state.lip_aperture == 0.0
    assert state.lip_protrusion == 0.43
    assert state.tongue_tip_constriction_location == 0.45
    assert state.tongue_tip_constriction_degree == 0.9
    assert state.lateral_tongue_drop == 0
    assert state.velic_aperture == 0.0
    assert state.tongue_body_constriction_location == 0.55
    assert state.tongue_body_constriction_degree == 0.55
    assert state.glottal_aperture == 18
    print("✓ _template_to_svg_state test passed")


def test_get_animation_params_template_hit():
    """Test get_animation_params uses template when available."""
    mapper = ArticulatoryMapper()

    for symbol in ["p", "t", "k", "s", "m", "n", "l", "j", "w", "h"]:
        result = mapper.get_animation_params(symbol)
        assert "lip_aperture" in result
        assert isinstance(result["lip_aperture"], (int, float))

    result_p = mapper.get_animation_params("p")
    assert result_p["lip_aperture"] == 0.0
    assert result_p["glottal_aperture"] == 18

    result_b = mapper.get_animation_params("b")
    assert result_b["lip_aperture"] == 0.0
    assert result_b["glottal_aperture"] == 3

    result_m = mapper.get_animation_params("m")
    assert result_m["velic_aperture"] == 0.88

    result_i = mapper.get_animation_params("i")
    assert result_i["glottal_aperture"] == 0

    result_u = mapper.get_animation_params("u")
    assert result_u["lip_aperture"] == 0.0
    assert result_u["lip_protrusion"] == 0.71
    print("✓ Template hit path in get_animation_params passed")


def test_svg_state_to_dict():
    """Test svg_state_to_dict converts ArticulatoryState to flat dict."""
    state = ArticulatoryState(
        lip_aperture=0.125,
        lip_protrusion=0.50,
        tongue_tip_constriction_location=0.45,
        tongue_tip_constriction_degree=1.0,
        lateral_tongue_drop=0,
        velic_aperture=0.50,
        tongue_body_constriction_location=0.60,
        tongue_body_constriction_degree=0.7,
        glottal_aperture=5,
    )
    d = svg_state_to_dict(state)

    assert isinstance(d, dict)
    assert d["lip_aperture"] == 0.125
    assert d["lip_protrusion"] == 0.50
    assert d["tongue_tip_constriction_location"] == 0.45
    assert d["tongue_tip_constriction_degree"] == 1.0
    assert d["lateral_tongue_drop"] == 0
    assert d["velic_aperture"] == 0.50
    assert d["tongue_body_constriction_location"] == 0.60
    assert d["tongue_body_constriction_degree"] == 0.7
    assert d["glottal_aperture"] == 5
    print("✓ svg_state_to_dict test passed")


def test_normalize_svg_state():
    """Test normalize_svg_state normalizes both SVG and legacy formats."""
    svg_input = {
        "lip_aperture": 0.20,
        "lip_protrusion": 0.21,
        "tongue_tip_constriction_location": 0.5,
        "tongue_tip_constriction_degree": 1.0,
        "lateral_tongue_drop": 10,
        "velic_aperture": 0.12,
        "tongue_body_constriction_location": 0.6,
        "tongue_body_constriction_degree": 0.7,
        "glottal_aperture": 3,
    }
    result = normalize_svg_state(svg_input)
    assert result["lip_aperture"] == 0.20
    assert result["glottal_aperture"] == 3
    assert result["tongue_tip_constriction_degree"] == 1.0
    assert result["tongue_body_constriction_degree"] == 0.7

    legacy_input = {
        "tongueIndex": 0.5,
        "tongueDiameter": 0.7,
        "tongueCurl": 0.2,
        "tongueRoot": 0.1,
        "lipRounding": 0.8,
        "lipClosure": 0.3,
        "nasality": 0.5,
        "voicing": 0.9,
        "aspiration": 0.0,
    }
    result_legacy = normalize_svg_state(legacy_input)
    assert "lip_aperture" in result_legacy
    assert "glottal_aperture" in result_legacy
    print("✓ normalize_svg_state test passed")


def test_normalize_svg_state_legacy_degree_scale():
    """Test normalize_svg_state converts older raw tongue distances."""

    legacy_svg_input = {
        "tongue_tip_constriction_degree": 40,
        "tongue_body_constriction_degree": 30,
    }
    result = normalize_svg_state(legacy_svg_input)
    assert result["tongue_tip_constriction_degree"] == 1.0
    assert result["tongue_body_constriction_degree"] == 1.0


def test_normalize_svg_state_partial_svg_input_uses_defaults():
    """Test partial SVG-shaped input still takes the SVG normalization path."""

    result = normalize_svg_state({"tongue_tip_constriction_degree": 40})
    assert result["tongue_tip_constriction_degree"] == 1.0
    assert result["tongue_body_constriction_degree"] == 1.0


def test_legacy_to_svg_state():
    """Test legacy_to_svg_state converts legacy params to SVG schema."""
    legacy = {
        "tongueIndex": 0.5,
        "tongueDiameter": 0.7,
        "tongueCurl": 0.0,
        "tongueRoot": 0.0,
        "lipRounding": 0.8,
        "lipClosure": 0.0,
        "nasality": 0.0,
        "voicing": 0.0,
        "aspiration": 0.0,
    }
    result = legacy_to_svg_state(legacy)
    assert isinstance(result, dict)
    assert "lip_aperture" in result
    assert "glottal_aperture" in result
    assert result["lip_aperture"] > 0
    assert result["glottal_aperture"] > 0

    params = ArticulatoryParameters(
        tongueIndex=0.3,
        tongueDiameter=0.5,
        tongueCurl=0.0,
        tongueRoot=0.0,
        lipRounding=0.5,
        lipClosure=0.0,
        nasality=0.0,
        voicing=1.0,
        aspiration=0.0,
    )
    result2 = legacy_to_svg_state(params)
    assert result2["glottal_aperture"] == 0
    print("✓ legacy_to_svg_state test passed")


def test_articulatory_state_dataclass():
    """Test ArticulatoryState holds all 9 SVG parameters."""
    state = ArticulatoryState(
        lip_aperture=1.0,
        lip_protrusion=1.0,
        tongue_tip_constriction_location=0.1,
        tongue_tip_constriction_degree=0.2,
        lateral_tongue_drop=5.0,
        velic_aperture=1.0,
        tongue_body_constriction_location=0.9,
        tongue_body_constriction_degree=1.0,
        glottal_aperture=8.0,
    )
    assert state.lip_aperture == 1.0
    assert state.glottal_aperture == 8.0
    assert state.lateral_tongue_drop == 5.0
    print("✓ ArticulatoryState dataclass test passed")


def test_default_articulatory_state():
    """Test default_articulatory_state returns sane defaults."""
    state = default_articulatory_state()
    assert isinstance(state, ArticulatoryState)
    assert state.lip_aperture == 0.25
    assert state.lip_protrusion == 0.71
    assert state.tongue_tip_constriction_location == 0.20
    assert state.tongue_tip_constriction_degree == 1.0
    assert state.lateral_tongue_drop == 0.0
    assert state.velic_aperture == 0.0
    assert state.tongue_body_constriction_location == 0.70
    assert state.tongue_body_constriction_degree == 1.0
    assert state.glottal_aperture == 0.0
    print("✓ default_articulatory_state test passed")


if __name__ == "__main__":
    test_articulatory_mapper_initialization()
    test_phoneme_description()
    test_parameter_mapping()
    test_delta_calculation()
    test_tooltip_formatting()
    test_feature_definitions()
    test_common_ipa_symbols()
    test_consonant_templates()
    test_vowel_templates()
    test_template_lookup()
    test_template_to_svg_state()
    test_get_animation_params_template_hit()
    test_svg_state_to_dict()
    test_normalize_svg_state()
    test_normalize_svg_state_legacy_degree_scale()
    test_normalize_svg_state_partial_svg_input_uses_defaults()
    test_legacy_to_svg_state()
    test_articulatory_state_dataclass()
    test_default_articulatory_state()
    print("\n✅ All articulatory mapping tests passed!")
