"""Tests for articulatory mapping module."""

from src.models.aai_adapter import (
    AAIConversionMetadata,
    AAINormalizationProfile,
    AAITractVariables,
    aai_to_canonical_state,
    decode_aai_row,
    denormalize_aai_row,
    parse_aai_animation_payload,
    representative_aai_pose,
)
from src.models.articulatory import (
    CONSONANT_TEMPLATES,
    VOWEL_TEMPLATES,
    ArticulatoryMapper,
    ArticulatoryState,
    PhonemeDescription,
    default_articulatory_state,
    normalize_svg_state,
    svg_state_to_dict,
)
from src.models.articulatory_calibration import CANONICAL_ARTICULATORY_FIELDS


def test_articulatory_mapper_initialization() -> None:
    """Test that articulatory mapper can be initialized."""
    mapper = ArticulatoryMapper()

    assert mapper is not None
    assert hasattr(mapper, "_tooltip_definitions")


def test_phoneme_description() -> None:
    """Test phoneme description parsing with placeholder data."""
    mapper = ArticulatoryMapper()

    description = mapper.parse_phoneme("/θ/")

    assert isinstance(description, PhonemeDescription)
    assert "θ" in description.ipa_symbol
    assert hasattr(description, "features")
    assert hasattr(description, "tooltips")


def test_parameter_mapping() -> None:
    """Test that phoneme description can be mapped to canonical 9-field parameters."""
    mapper = ArticulatoryMapper()

    svg_state = mapper.get_animation_params("/t/")

    assert isinstance(svg_state, dict)
    assert set(svg_state.keys()) == set(CANONICAL_ARTICULATORY_FIELDS)
    assert "lip_aperture" in svg_state
    assert "tongue_tip_constriction_location" in svg_state
    assert "tongue_body_constriction_degree" in svg_state

    neutral = default_articulatory_state()
    assert neutral.lip_aperture == 0.25


def test_common_ipa_symbols() -> None:
    """Test parsing and mapping of common IPA phonemes."""
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

    for phoneme in common_phonemes:
        description = mapper.parse_phoneme(phoneme)
        assert isinstance(description, PhonemeDescription)
        assert description.ipa_symbol == phoneme.strip("/")
        assert description.technical_name
        svg_state = mapper.get_animation_params(phoneme)
        assert set(svg_state.keys()) == set(CANONICAL_ARTICULATORY_FIELDS)
        for val in svg_state.values():
            assert 0.0 <= val <= 1.0


def test_consonant_templates() -> None:
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
        assert 0 <= template["lat"] <= 1, f"LAT out of range for /{symbol}/"
        assert 0 <= template["vel"] <= 1, f"VEL out of range for /{symbol}/"
        assert 0 <= template["tbcl"] <= 1, f"TBCL out of range for /{symbol}/"
        assert 0 <= template["tbcd"] <= 1, f"TBCD out of range for /{symbol}/"
        assert 0 <= template["glo"] <= 1, f"GLO out of range for /{symbol}/"


def test_vowel_templates() -> None:
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
        assert 0 <= template["lat"] <= 1, f"LAT out of range for /{symbol}/"
        assert 0 <= template["vel"] <= 1, f"VEL out of range for /{symbol}/"
        assert 0 <= template["tbcl"] <= 1, f"TBCL out of range for /{symbol}/"
        assert 0 <= template["tbcd"] <= 1, f"TBCD out of range for /{symbol}/"
        assert 0 <= template["glo"] <= 1, f"GLO out of range for /{symbol}/"
        assert template["glo"] == 0, f"Vowel /{symbol}/ should have GLO=0 (voiced)"


def test_template_lookup() -> None:
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


def test_template_to_svg_state() -> None:
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
    assert state.glottal_aperture == 0.6


def test_get_animation_params_template_hit() -> None:
    """Test get_animation_params uses template when available."""
    mapper = ArticulatoryMapper()

    for symbol in ["p", "t", "k", "s", "m", "n", "l", "j", "w", "h"]:
        result = mapper.get_animation_params(symbol)
        assert "lip_aperture" in result
        assert isinstance(result["lip_aperture"], (int, float))

    result_p = mapper.get_animation_params("p")
    assert result_p["lip_aperture"] == 0.0
    assert result_p["glottal_aperture"] == 0.6

    result_b = mapper.get_animation_params("b")
    assert result_b["lip_aperture"] == 0.0
    assert result_b["glottal_aperture"] == 0.1

    result_m = mapper.get_animation_params("m")
    assert result_m["velic_aperture"] == 0.88

    result_i = mapper.get_animation_params("i")
    assert result_i["glottal_aperture"] == 0

    result_u = mapper.get_animation_params("u")
    assert result_u["lip_aperture"] == 0.0
    assert result_u["lip_protrusion"] == 0.71


def test_svg_state_to_dict() -> None:
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
        glottal_aperture=0.5,
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
    assert d["glottal_aperture"] == 0.5


def test_normalize_svg_state() -> None:
    """Test normalize_svg_state normalizes and clamps all 9 canonical fields."""
    svg_input = {
        "lip_aperture": 0.20,
        "lip_protrusion": 0.21,
        "tongue_tip_constriction_location": 0.5,
        "tongue_tip_constriction_degree": 1.0,
        "lateral_tongue_drop": 0.25,
        "velic_aperture": 0.12,
        "tongue_body_constriction_location": 0.6,
        "tongue_body_constriction_degree": 0.7,
        "glottal_aperture": 0.3,
    }
    result = normalize_svg_state(svg_input)
    assert result["lip_aperture"] == 0.20
    assert result["glottal_aperture"] == 0.3
    assert result["tongue_tip_constriction_degree"] == 1.0
    assert result["tongue_body_constriction_degree"] == 0.7


def test_normalize_svg_state_clamps_non_normalized_svg_input() -> None:
    """Test normalize_svg_state clamps all 9 SVG fields into [0.0, 1.0]."""

    out_of_range_input = {
        "lip_aperture": -0.5,
        "lip_protrusion": 1.5,
        "tongue_tip_constriction_location": -0.2,
        "tongue_tip_constriction_degree": 40,
        "lateral_tongue_drop": 5.0,
        "velic_aperture": -1.0,
        "tongue_body_constriction_location": 2.4,
        "tongue_body_constriction_degree": 30,
        "glottal_aperture": 12.0,
    }
    result = normalize_svg_state(out_of_range_input)
    assert result["lip_aperture"] == 0.0
    assert result["lip_protrusion"] == 1.0
    assert result["tongue_tip_constriction_location"] == 0.0
    assert result["tongue_tip_constriction_degree"] == 1.0
    assert result["lateral_tongue_drop"] == 1.0
    assert result["velic_aperture"] == 0.0
    assert result["tongue_body_constriction_location"] == 1.0
    assert result["tongue_body_constriction_degree"] == 1.0
    assert result["glottal_aperture"] == 1.0


def test_normalize_svg_state_partial_svg_input_uses_defaults() -> None:
    """Test partial SVG-shaped input fills defaults and clamps values."""

    result = normalize_svg_state({"tongue_tip_constriction_degree": 40})
    assert result["tongue_tip_constriction_degree"] == 1.0
    assert result["tongue_body_constriction_degree"] == 1.0


def test_map_to_svg_state_feature_fallback() -> None:
    """Test map_to_svg_state maps CLTS phoneme features directly into canonical 9-field state."""
    mapper = ArticulatoryMapper()
    desc = PhonemeDescription(
        technical_name="Voiceless Retroflex Fricative",
        ipa_symbol="ʂ",
        features={
            "place": "retroflex",
            "manner": "fricative",
            "voicing": "voiceless",
            "rounding": "unrounded",
        },
        tooltips={},
    )
    result = mapper.map_to_svg_state(desc)
    assert set(result.keys()) == set(CANONICAL_ARTICULATORY_FIELDS)
    assert result["lateral_tongue_drop"] == 0.25
    assert result["glottal_aperture"] == 1.0
    assert result["lip_protrusion"] == 0.0
    for val in result.values():
        assert 0.0 <= val <= 1.0


def test_decode_aai_row_uses_documented_field_order():
    """AAI rows should decode by named field order, not renderer order."""

    row = [-2.45, 35.21, 0.00, 15.34, 0.83, 7.66, 12.02, 1.00, 0.00]
    tv = decode_aai_row(row)

    assert tv.lp == -2.45
    assert tv.la == 35.21
    assert tv.ttcl == 0.00
    assert tv.ttcd == 15.34
    assert tv.tbcl == 0.83
    assert tv.tbcd == 7.66
    assert tv.vel == 12.02
    assert tv.glo == 1.00
    assert tv.lat == 0.00


def test_denormalize_aai_row_with_profile():
    """Z-scored AAI rows should denormalize using provided stats."""

    profile = AAINormalizationProfile(
        mean=(-3.035, 33.41, 0.0, 14.96, 0.85, 7.78, 11.64, 1.0, 0.0),
        std=(0.632, 0.68, 1.0, 0.73, 0.07, 0.20, 0.64, 1.0, 1.0),
        speaker_id="F1",
        profile_name="speaker_F1",
    )
    row = [0.92, 2.63, 0.0, 0.51, -0.28, -0.59, 0.58, 0.0, 0.0]

    tv = denormalize_aai_row(row, profile)

    assert round(tv.lp, 2) == -2.45
    assert round(tv.la, 2) == 35.20
    assert round(tv.ttcd, 2) == 15.33
    assert round(tv.tbcl, 2) == 0.83
    assert round(tv.tbcd, 2) == 7.66


def test_aai_to_canonical_state_preserves_sign_directions():
    """AAI conversion should preserve canonical opening and location directions."""

    tv = AAITractVariables(
        lp=-2.0,
        la=35.0,
        ttcl=0.1,
        ttcd=0.0,
        tbcl=0.9,
        tbcd=8.0,
        vel=0.0,
        glo=1.0,
        lat=1.0,
    )

    state = aai_to_canonical_state(tv)

    assert state["lip_aperture"] > 0
    assert state["lip_protrusion"] == 0.0
    assert state["tongue_tip_constriction_location"] == 0.1
    assert state["tongue_tip_constriction_degree"] == 0.0
    assert state["tongue_body_constriction_location"] == 0.9
    assert state["tongue_body_constriction_degree"] > 0
    assert state["velic_aperture"] == 0.0
    assert state["glottal_aperture"] == 1.0
    assert state["lateral_tongue_drop"] == 1.0

    for value in state.values():
        assert 0.0 <= value <= 1.0


def test_parse_aai_animation_payload_zscore_matches_single_step_conversion():
    """AAI payload parsing should denormalize z-scored values exactly once."""

    payload = {
        "source_dataset": "timit",
        "normalization": "z_score",
        "stats_reference": {
            "mean": [-3.035, 33.41, 0.0, 14.96, 0.85, 7.78, 11.64, 1.0, 0.0],
            "std": [0.632, 0.68, 1.0, 0.73, 0.07, 0.20, 0.64, 1.0, 1.0],
        },
        "values": [0.92, 2.63, 0.0, 0.51, -0.28, -0.59, 0.58, 0.0, 0.0],
    }

    profile = AAINormalizationProfile(
        mean=tuple(payload["stats_reference"]["mean"]),
        std=tuple(payload["stats_reference"]["std"]),
        profile_name="payload_reference",
    )
    expected = aai_to_canonical_state(
        decode_aai_row(payload["values"]),
        profile=profile,
        metadata=AAIConversionMetadata(normalization="z_score", source_dataset="timit"),
    )

    assert parse_aai_animation_payload(payload) == expected


def test_aai_masked_channels_fall_back_to_existing_state():
    """Masked XRMB channels should fall back rather than pretending to be observed."""

    tv = AAITractVariables(
        lp=0.0,
        la=10.0,
        ttcl=0.2,
        ttcd=5.0,
        tbcl=0.7,
        tbcd=5.0,
        vel=12.0,
        glo=1.0,
        lat=1.0,
    )
    fallback = {
        "lip_aperture": 0.1,
        "lip_protrusion": 0.2,
        "tongue_tip_constriction_location": 0.3,
        "tongue_tip_constriction_degree": 0.4,
        "lateral_tongue_drop": 0.0,
        "velic_aperture": 0.0,
        "tongue_body_constriction_location": 0.5,
        "tongue_body_constriction_degree": 0.6,
        "glottal_aperture": 0.3,
    }
    metadata = AAIConversionMetadata(normalization="raw", source_dataset="xrmb")

    state = aai_to_canonical_state(tv, metadata=metadata, fallback_state=fallback)

    assert state["velic_aperture"] == 0.0
    assert state["glottal_aperture"] == 0.3
    assert state["lateral_tongue_drop"] == 0.0


def test_representative_aai_pose_uses_median_of_trajectory():
    """Representative AAI pose should reduce trajectories to a stable median pose."""

    frames = [
        [0.0, 10.0, 0.1, 5.0, 0.4, 4.0, 0.0, 0.0, 0.0],
        [1.0, 20.0, 0.2, 6.0, 0.5, 5.0, 0.1, 0.5, 0.2],
        [2.0, 30.0, 0.3, 7.0, 0.6, 6.0, 0.2, 1.0, 0.4],
    ]

    pose = representative_aai_pose(frames)

    assert pose.lp == 1.0
    assert pose.la == 20.0
    assert round(pose.ttcl, 6) == 0.2
    assert round(pose.glo, 6) == 0.5


def test_parse_aai_animation_payload_returns_canonical_state():
    """AAI payload parsing should produce canonical renderer-facing state."""

    payload = {
        "source_dataset": "timit",
        "normalization": "z_score",
        "stats_reference": {
            "mean": [-3.035, 33.41, 0.0, 14.96, 0.85, 7.78, 11.64, 1.0, 0.0],
            "std": [0.632, 0.68, 1.0, 0.73, 0.07, 0.20, 0.64, 1.0, 1.0],
        },
        "values": [0.92, 2.63, 0.0, 0.51, -0.28, -0.59, 0.58, 0.0, 0.0],
    }

    state = parse_aai_animation_payload(payload)

    assert set(state.keys()) == {
        "lip_aperture",
        "lip_protrusion",
        "tongue_tip_constriction_location",
        "tongue_tip_constriction_degree",
        "lateral_tongue_drop",
        "velic_aperture",
        "tongue_body_constriction_location",
        "tongue_body_constriction_degree",
        "glottal_aperture",
    }
    assert state["tongue_tip_constriction_location"] == 0.0
    assert round(state["tongue_body_constriction_location"], 2) == 0.83
    for value in state.values():
        assert 0.0 <= value <= 1.0


def test_articulatory_state_dataclass() -> None:
    """Test ArticulatoryState holds all 9 SVG parameters."""
    state = ArticulatoryState(
        lip_aperture=1.0,
        lip_protrusion=1.0,
        tongue_tip_constriction_location=0.1,
        tongue_tip_constriction_degree=0.2,
        lateral_tongue_drop=0.5,
        velic_aperture=1.0,
        tongue_body_constriction_location=0.9,
        tongue_body_constriction_degree=1.0,
        glottal_aperture=0.8,
    )
    assert state.lip_aperture == 1.0
    assert state.glottal_aperture == 0.8
    assert state.lateral_tongue_drop == 0.5


def test_default_articulatory_state() -> None:
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
