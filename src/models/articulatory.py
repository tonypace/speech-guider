"""Articulatory mapping using pyclts to convert IPA to SVG renderer state.

Maps phoneme features (place, manner, voicing) to visual parameters for
vocal tract animation. Provides technical descriptions and friendly tooltips.
"""

import logging
from dataclasses import dataclass
from typing import Mapping, Optional

import pyclts

from src.models.articulatory_calibration import clamp_unit

logger = logging.getLogger(__name__)


@dataclass
class ArticulatoryState:
    """SVG articulatory model state used by the new renderer."""

    lip_aperture: float
    lip_protrusion: float
    tongue_tip_constriction_location: float
    tongue_tip_constriction_degree: float
    lateral_tongue_drop: float
    velic_aperture: float
    tongue_body_constriction_location: float
    tongue_body_constriction_degree: float
    glottal_aperture: float


def default_articulatory_state() -> ArticulatoryState:
    """Return the neutral SVG articulatory pose."""

    return ArticulatoryState(
        lip_aperture=0.25,
        lip_protrusion=0.71,
        tongue_tip_constriction_location=0.20,
        tongue_tip_constriction_degree=1.0,
        lateral_tongue_drop=0.0,
        velic_aperture=0.0,
        tongue_body_constriction_location=0.70,
        tongue_body_constriction_degree=1.0,
        glottal_aperture=0.0,
    )


@dataclass
class PhonemeDescription:
    """Complete description of a phoneme for display."""

    technical_name: str
    ipa_symbol: str
    features: dict[str, str]
    tooltips: dict[str, str]


CONSONANT_TEMPLATES: dict[str, dict[str, float]] = {
    "p": {
        "lip_aperture": 0.00,
        "lip_protrusion": 0.43,
        "ttcl": 0.45,
        "ttcd": 0.90,
        "lat": 0.00,
        "vel": 0.00,
        "tbcl": 0.55,
        "tbcd": 0.55,
        "glo": 0.60,
    },
    "b": {
        "lip_aperture": 0.00,
        "lip_protrusion": 0.43,
        "ttcl": 0.45,
        "ttcd": 0.90,
        "lat": 0.00,
        "vel": 0.00,
        "tbcl": 0.55,
        "tbcd": 0.55,
        "glo": 0.10,
    },
    "m": {
        "lip_aperture": 0.00,
        "lip_protrusion": 0.43,
        "ttcl": 0.45,
        "ttcd": 0.70,
        "lat": 0.00,
        "vel": 0.88,
        "tbcl": 0.55,
        "tbcd": 0.55,
        "glo": 0.10,
    },
    "t": {
        "lip_aperture": 0.10,
        "lip_protrusion": 0.07,
        "ttcl": 0.95,
        "ttcd": 1.00,
        "lat": 0.00,
        "vel": 0.00,
        "tbcl": 0.75,
        "tbcd": 0.55,
        "glo": 0.60,
    },
    "d": {
        "lip_aperture": 0.10,
        "lip_protrusion": 0.07,
        "ttcl": 0.95,
        "ttcd": 1.00,
        "lat": 0.00,
        "vel": 0.00,
        "tbcl": 0.75,
        "tbcd": 0.55,
        "glo": 0.10,
    },
    "n": {
        "lip_aperture": 0.10,
        "lip_protrusion": 0.07,
        "ttcl": 0.95,
        "ttcd": 0.70,
        "lat": 0.00,
        "vel": 0.88,
        "tbcl": 0.75,
        "tbcd": 0.55,
        "glo": 0.10,
    },
    "k": {
        "lip_aperture": 0.10,
        "lip_protrusion": 0.14,
        "ttcl": 0.10,
        "ttcd": 1.00,
        "lat": 0.00,
        "vel": 0.00,
        "tbcl": 0.15,
        "tbcd": 1.00,
        "glo": 0.60,
    },
    "g": {
        "lip_aperture": 0.10,
        "lip_protrusion": 0.14,
        "ttcl": 0.10,
        "ttcd": 1.00,
        "lat": 0.00,
        "vel": 0.00,
        "tbcl": 0.15,
        "tbcd": 1.00,
        "glo": 0.10,
    },
    "ŋ": {
        "lip_aperture": 0.10,
        "lip_protrusion": 0.14,
        "ttcl": 0.10,
        "ttcd": 0.70,
        "lat": 0.00,
        "vel": 0.88,
        "tbcl": 0.15,
        "tbcd": 1.00,
        "glo": 0.10,
    },
    "f": {
        "lip_aperture": 0.15,
        "lip_protrusion": 0.07,
        "ttcl": 0.60,
        "ttcd": 0.70,
        "lat": 0.00,
        "vel": 0.00,
        "tbcl": 0.55,
        "tbcd": 0.40,
        "glo": 0.60,
    },
    "v": {
        "lip_aperture": 0.15,
        "lip_protrusion": 0.07,
        "ttcl": 0.60,
        "ttcd": 0.70,
        "lat": 0.00,
        "vel": 0.00,
        "tbcl": 0.55,
        "tbcd": 0.40,
        "glo": 0.10,
    },
    "s": {
        "lip_aperture": 0.10,
        "lip_protrusion": 0.07,
        "ttcl": 0.95,
        "ttcd": 0.70,
        "lat": 0.00,
        "vel": 0.00,
        "tbcl": 0.80,
        "tbcd": 0.55,
        "glo": 0.60,
    },
    "z": {
        "lip_aperture": 0.10,
        "lip_protrusion": 0.07,
        "ttcl": 0.95,
        "ttcd": 0.70,
        "lat": 0.00,
        "vel": 0.00,
        "tbcl": 0.80,
        "tbcd": 0.55,
        "glo": 0.10,
    },
    "ʃ": {
        "lip_aperture": 0.10,
        "lip_protrusion": 0.07,
        "ttcl": 0.80,
        "ttcd": 0.70,
        "lat": 0.00,
        "vel": 0.00,
        "tbcl": 0.70,
        "tbcd": 0.55,
        "glo": 0.60,
    },
    "ʒ": {
        "lip_aperture": 0.10,
        "lip_protrusion": 0.07,
        "ttcl": 0.80,
        "ttcd": 0.70,
        "lat": 0.00,
        "vel": 0.00,
        "tbcl": 0.70,
        "tbcd": 0.55,
        "glo": 0.10,
    },
    "tʃ": {
        "lip_aperture": 0.10,
        "lip_protrusion": 0.07,
        "ttcl": 0.82,
        "ttcd": 1.00,
        "lat": 0.00,
        "vel": 0.00,
        "tbcl": 0.72,
        "tbcd": 0.70,
        "glo": 0.60,
    },
    "dʒ": {
        "lip_aperture": 0.10,
        "lip_protrusion": 0.07,
        "ttcl": 0.82,
        "ttcd": 1.00,
        "lat": 0.00,
        "vel": 0.00,
        "tbcl": 0.72,
        "tbcd": 0.70,
        "glo": 0.10,
    },
    "h": {
        "lip_aperture": 0.25,
        "lip_protrusion": 0.00,
        "ttcl": 0.35,
        "ttcd": 0.20,
        "lat": 0.00,
        "vel": 0.00,
        "tbcl": 0.35,
        "tbcd": 0.14,
        "glo": 0.67,
    },
    "l": {
        "lip_aperture": 0.15,
        "lip_protrusion": 0.07,
        "ttcl": 0.95,
        "ttcd": 0.40,
        "lat": 0.45,
        "vel": 0.00,
        "tbcl": 0.75,
        "tbcd": 0.40,
        "glo": 0.10,
    },
    "ɹ": {
        "lip_aperture": 0.20,
        "lip_protrusion": 0.07,
        "ttcl": 0.75,
        "ttcd": 0.30,
        "lat": 0.00,
        "vel": 0.00,
        "tbcl": 0.60,
        "tbcd": 0.40,
        "glo": 0.10,
    },
    "j": {
        "lip_aperture": 0.25,
        "lip_protrusion": 0.00,
        "ttcl": 0.85,
        "ttcd": 0.20,
        "lat": 0.00,
        "vel": 0.00,
        "tbcl": 0.65,
        "tbcd": 0.28,
        "glo": 0.10,
    },
    "w": {
        "lip_aperture": 0.20,
        "lip_protrusion": 0.71,
        "ttcl": 0.25,
        "ttcd": 0.20,
        "lat": 0.00,
        "vel": 0.00,
        "tbcl": 0.25,
        "tbcd": 0.28,
        "glo": 0.10,
    },
}

VOWEL_TEMPLATES: dict[str, dict[str, float]] = {
    "i": {
        "lip_aperture": 0.30,
        "lip_protrusion": 0.00,
        "ttcl": 0.80,
        "ttcd": 0.60,
        "lat": 0.00,
        "vel": 0.00,
        "tbcl": 0.85,
        "tbcd": 0.85,
        "glo": 0.00,
    },
    "e": {
        "lip_aperture": 0.25,
        "lip_protrusion": 0.07,
        "ttcl": 0.70,
        "ttcd": 0.50,
        "lat": 0.00,
        "vel": 0.00,
        "tbcl": 0.75,
        "tbcd": 0.70,
        "glo": 0.00,
    },
    "æ": {
        "lip_aperture": 0.35,
        "lip_protrusion": 0.07,
        "ttcl": 0.60,
        "ttcd": 0.60,
        "lat": 0.00,
        "vel": 0.00,
        "tbcl": 0.55,
        "tbcd": 0.70,
        "glo": 0.00,
    },
    "a": {
        "lip_aperture": 0.35,
        "lip_protrusion": 0.14,
        "ttcl": 0.55,
        "ttcd": 0.50,
        "lat": 0.00,
        "vel": 0.00,
        "tbcl": 0.50,
        "tbcd": 0.55,
        "glo": 0.00,
    },
    "ɑ": {
        "lip_aperture": 0.30,
        "lip_protrusion": 0.14,
        "ttcl": 0.30,
        "ttcd": 0.60,
        "lat": 0.00,
        "vel": 0.00,
        "tbcl": 0.35,
        "tbcd": 0.70,
        "glo": 0.00,
    },
    "o": {
        "lip_aperture": 0.10,
        "lip_protrusion": 0.57,
        "ttcl": 0.25,
        "ttcd": 0.50,
        "lat": 0.00,
        "vel": 0.00,
        "tbcl": 0.35,
        "tbcd": 0.70,
        "glo": 0.00,
    },
    "u": {
        "lip_aperture": 0.00,
        "lip_protrusion": 0.71,
        "ttcl": 0.15,
        "ttcd": 0.60,
        "lat": 0.00,
        "vel": 0.00,
        "tbcl": 0.20,
        "tbcd": 0.85,
        "glo": 0.00,
    },
    "ə": {
        "lip_aperture": 0.25,
        "lip_protrusion": 0.36,
        "ttcl": 0.35,
        "ttcd": 0.50,
        "lat": 0.00,
        "vel": 0.00,
        "tbcl": 0.55,
        "tbcd": 0.70,
        "glo": 0.00,
    },
    "ʌ": {
        "lip_aperture": 0.25,
        "lip_protrusion": 0.29,
        "ttcl": 0.30,
        "ttcd": 0.50,
        "lat": 0.00,
        "vel": 0.00,
        "tbcl": 0.40,
        "tbcd": 0.70,
        "glo": 0.00,
    },
    "ɔ": {
        "lip_aperture": 0.07,
        "lip_protrusion": 0.64,
        "ttcl": 0.20,
        "ttcd": 0.40,
        "lat": 0.00,
        "vel": 0.00,
        "tbcl": 0.30,
        "tbcd": 0.55,
        "glo": 0.00,
    },
    "ɪ": {
        "lip_aperture": 0.25,
        "lip_protrusion": 0.07,
        "ttcl": 0.75,
        "ttcd": 0.60,
        "lat": 0.00,
        "vel": 0.00,
        "tbcl": 0.80,
        "tbcd": 0.85,
        "glo": 0.00,
    },
    "ɛ": {
        "lip_aperture": 0.30,
        "lip_protrusion": 0.07,
        "ttcl": 0.65,
        "ttcd": 0.50,
        "lat": 0.00,
        "vel": 0.00,
        "tbcl": 0.70,
        "tbcd": 0.70,
        "glo": 0.00,
    },
    "ʊ": {
        "lip_aperture": 0.05,
        "lip_protrusion": 0.57,
        "ttcl": 0.20,
        "ttcd": 0.60,
        "lat": 0.00,
        "vel": 0.00,
        "tbcl": 0.30,
        "tbcd": 0.85,
        "glo": 0.00,
    },
}


class ArticulatoryMapper:
    """Maps IPA phonemes to articulatory visualization parameters."""

    def __init__(self) -> None:
        """Initialize articulatory mapper with pyclts."""
        self._bipa = None
        self._tooltip_definitions = self._build_tooltip_definitions()

    def _get_bipa(self) -> pyclts.TranscriptionSystem:
        """Lazy load CLTS BIPA system.

        Returns:
            CLTS BIPA transcription system
        """
        if self._bipa is None:
            self._bipa = pyclts.TranscriptionSystem("bipa")  # type: ignore[call-arg, assignment]
        return self._bipa

    def _build_tooltip_definitions(self) -> dict[str, str]:
        """Build dictionary of friendly tooltip explanations.

        Returns:
            Dictionary mapping feature values to plain-English explanations
        """
        return {
            # Place of articulation tooltips
            "bilabial": "Lips come together (e.g., /b/, /p/)",
            "labiodental": "Lower lip touches upper front teeth (e.g., /f/, /v/)",
            "dental": "Tongue touches upper front teeth (e.g., /θ/, /ð/)",
            "alveolar": "Tongue against bony ridge behind upper teeth (e.g., /t/, /s/)",
            "postalveolar": "Tongue just behind alveolar ridge (e.g., /ʃ/, /tʃ/)",
            "retroflex": "Tongue tip curled back (common in some languages)",
            "palatal": "Tongue body raises toward hard palate (e.g., /j/)",
            "velar": "Back of tongue touches soft palate (e.g., /k/, /g/)",
            "uvular": "Back of tongue touches uvula (r-sound in French)",
            "pharyngeal": "Tongue root pulls back into pharynx",
            "glottal": "Airflow controlled by glottis (vocal cords) (e.g., /h/)",
            # Manner of articulation tooltips
            "plosive": "Airflow is completely stopped then released (e.g., /p/, /t/, /k/)",
            "nasal": "Air flows through nose (e.g., /m/, /n/)",
            "trill": "Articulator vibrates against another (e.g., rolled r)",
            "flap": "Quick tap of tip of tongue against ridge",
            "tap": "Tap (faster than a trill)",
            "fricative": "Air forced through narrow channel, creating friction (e.g., /s/, /f/)",
            "approximant": "Narrow but not blocked, little friction (e.g., /l/, /r/)",
            "glide": "Glide from one vowel to another (e.g., /j/ as in 'yes', /w/ as in 'wet')",
            "vowel": "Open vocal tract, voice resonates (e.g., /a/, /e/, /i/)",
            # Voicing tooltips
            "voiced": "Vocal cords are vibrating (e.g., /b/, /z/, /g/)",
            "voiceless": "Vocal cords do not vibrate (e.g., /p/, /s/, /k/)",
            # Lip rounding tooltips
            "rounded": "Lips are rounded (e.g., /u/, /o/)",
            "unrounded": "Lips are spread (e.g., /i/, /e/)",
            "neutral": "Lips in neutral position",
        }

    def parse_phoneme(self, ipa_symbol: str) -> PhonemeDescription:
        """Parse an IPA phoneme using pyclts to get features and description.

        Args:
            ipa_symbol: IPA phoneme string (may include slashes)

        Returns:
            PhonemeDescription with technical name, features, and tooltips
        """
        clean_ipa = ipa_symbol.strip().strip("/")
        try:
            bipa = self._get_bipa()
        except Exception:
            return PhonemeDescription(
                technical_name="Unknown",
                ipa_symbol=clean_ipa,
                features={},
                tooltips={},
            )

        try:
            # Get phoneme from CLTS
            phoneme = bipa[clean_ipa]
        except KeyError:
            return PhonemeDescription(
                technical_name=f"Unknown: {clean_ipa}",
                ipa_symbol=clean_ipa,
                features={},
                tooltips={},
            )

        # Extract features from CLTS
        features = {}
        tooltips = {}

        # Get feature strings from CLTS
        if hasattr(phoneme, "featureset"):
            featureset = phoneme.featureset

            # Map CLTS features to our standard terms
            feature_mapping = {
                "voicing": "voicing",
                "place": "place",
                "manner": "manner",
                "rounded": "rounding",
            }

            for clts_key, our_key in feature_mapping.items():
                if clts_key in featureset:
                    value = featureset[clts_key]
                    features[our_key] = value

                    # Add tooltip if available
                    if value in self._tooltip_definitions:
                        tooltips[our_key] = self._tooltip_definitions[value]

        # Build technical name from features
        technical_name = self._build_technical_name(features)

        return PhonemeDescription(
            technical_name=technical_name,
            ipa_symbol=clean_ipa,
            features=features,
            tooltips=tooltips,
        )

    def _build_technical_name(self, features: dict[str, str]) -> str:
        """Build technical phoneme name from features.

        Args:
            features: Dictionary of phoneme features

        Returns:
            Technical name string (e.g., "Voiced Alveolar Plosive")
        """
        parts = []

        if "voicing" in features and features["voicing"] in ["voiced", "voiceless"]:
            parts.append(features["voicing"].capitalize())

        if "place" in features:
            parts.append(features["place"].capitalize())

        if "manner" in features:
            parts.append(features["manner"].capitalize())

        return " ".join(parts) if parts else "Unknown"

    def map_to_svg_state(self, phoneme_description: PhonemeDescription) -> dict[str, float]:
        """Map phoneme features directly to the canonical 9-field SVG articulatory schema."""
        features = phoneme_description.features

        place_mapping = {
            "bilabial": 0.5,
            "labiodental": 0.7,
            "dental": 0.85,
            "alveolar": 1.0,
            "postalveolar": 0.9,
            "retroflex": 0.85,
            "palatal": 0.65,
            "velar": 0.0,
            "uvular": 0.05,
            "pharyngeal": 0.0,
            "glottal": 0.0,
        }
        manner_mapping = {
            "plosive": 1.0,
            "affricate": 0.9,
            "fricative": 0.75,
            "nasal": 0.7,
            "flap": 0.6,
            "tap": 0.6,
            "trill": 0.55,
            "approximant": 0.5,
            "glide": 0.4,
            "vowel": 0.0,
        }

        place = features.get("place", "")
        manner = features.get("manner", "")
        rounding = features.get("rounding", "")
        voicing_feat = features.get("voicing", "")

        tongue_index = place_mapping.get(place, 0.5)
        tongue_degree = manner_mapping.get(manner, 0.5)
        tongue_front_back = clamp_unit((1.0 - tongue_index) * 0.85)
        tongue_body_location = clamp_unit(0.25 + tongue_front_back)
        if place in ("pharyngeal", "uvular"):
            tongue_body_location = max(tongue_body_location, 0.65)

        if rounding == "rounded":
            lip_protrusion = 1.0
        elif rounding == "unrounded":
            lip_protrusion = 0.0
        else:
            lip_protrusion = 0.5

        lip_closure = 1.0 if (place == "bilabial" and manner == "plosive") else 0.0
        lip_aperture = clamp_unit((1.0 - lip_closure) * (1.0 - 0.45 * lip_protrusion))
        lateral_drop = 0.25 if place == "retroflex" else 0.0
        velic_aperture = 1.0 if manner == "nasal" else 0.0

        if voicing_feat == "voiced":
            glottal_aperture = 0.0
        elif voicing_feat == "voiceless":
            glottal_aperture = 1.0
        else:
            glottal_aperture = 0.5

        return {
            "lip_aperture": lip_aperture,
            "lip_protrusion": lip_protrusion,
            "tongue_tip_constriction_location": tongue_front_back,
            "tongue_tip_constriction_degree": tongue_degree,
            "lateral_tongue_drop": lateral_drop,
            "velic_aperture": velic_aperture,
            "tongue_body_constriction_location": tongue_body_location,
            "tongue_body_constriction_degree": tongue_degree,
            "glottal_aperture": glottal_aperture,
        }

    def _template_to_svg_state(self, template: dict[str, float]) -> ArticulatoryState:
        """Convert a template dict to ArticulatoryState.

        Args:
            template: Dictionary with keys: lip_aperture, lip_protrusion, ttcl, ttcd,
                      lat, vel, tbcl, tbcd, glo

        Returns:
            ArticulatoryState with all 9 SVG variables set
        """
        return ArticulatoryState(
            lip_aperture=template["lip_aperture"],
            lip_protrusion=template["lip_protrusion"],
            tongue_tip_constriction_location=template["ttcl"],
            tongue_tip_constriction_degree=template["ttcd"],
            lateral_tongue_drop=clamp_unit(float(template["lat"])),
            velic_aperture=template["vel"],
            tongue_body_constriction_location=template["tbcl"],
            tongue_body_constriction_degree=template["tbcd"],
            glottal_aperture=clamp_unit(float(template["glo"])),
        )

    def _get_template(self, ipa_symbol: str) -> Optional[dict[str, float]]:
        """Look up a phoneme in the consonant or vowel template tables.

        Args:
            ipa_symbol: Cleaned IPA symbol (no slashes)

        Returns:
            Template dict if found, None otherwise
        """
        if ipa_symbol in CONSONANT_TEMPLATES:
            return CONSONANT_TEMPLATES[ipa_symbol]
        if ipa_symbol in VOWEL_TEMPLATES:
            return VOWEL_TEMPLATES[ipa_symbol]
        return None

    def get_animation_params(self, ipa_symbol: str) -> dict[str, float]:
        """Get SVG animation parameters for a phoneme.

        Tries templates first (consonant/vowel tables), then CLTS feature
        mapping, then defaults.

        Args:
            ipa_symbol: IPA phoneme string (e.g., 'i', 'æ', 'k')

        Returns:
            Dictionary with SVG articulatory parameters.
        """
        logger.debug("[ArticulatoryMapper.get_animation_params] Called with: %s", ipa_symbol)

        clean_ipa = ipa_symbol.strip().strip("/")

        template = self._get_template(clean_ipa)
        if template:
            state = self._template_to_svg_state(template)
            result = svg_state_to_dict(state)
            logger.debug(
                "[ArticulatoryMapper.get_animation_params] Template hit for '%s': %s",
                clean_ipa,
                result,
            )
            return result

        description = self.parse_phoneme(ipa_symbol)
        logger.debug(
            "[ArticulatoryMapper.get_animation_params] Parsed description: %s", description
        )

        if description.features:
            svg_state = self.map_to_svg_state(description)
            logger.debug(
                "[ArticulatoryMapper.get_animation_params] Articulatory state: %s", svg_state
            )

            result = normalize_svg_state(svg_state)
            logger.debug(
                "[ArticulatoryMapper.get_animation_params] Returning pyclts result: %s", result
            )
            return result

        logger.debug(
            "[ArticulatoryMapper.get_animation_params] All fallbacks failed, returning defaults"
        )
        return svg_state_to_dict(default_articulatory_state())


def svg_state_to_dict(state: ArticulatoryState) -> dict[str, float]:
    """Convert an articulatory SVG state into a plain dictionary."""

    return {
        "lip_aperture": state.lip_aperture,
        "lip_protrusion": state.lip_protrusion,
        "tongue_tip_constriction_location": state.tongue_tip_constriction_location,
        "tongue_tip_constriction_degree": state.tongue_tip_constriction_degree,
        "lateral_tongue_drop": state.lateral_tongue_drop,
        "velic_aperture": state.velic_aperture,
        "tongue_body_constriction_location": state.tongue_body_constriction_location,
        "tongue_body_constriction_degree": state.tongue_body_constriction_degree,
        "glottal_aperture": state.glottal_aperture,
    }


def normalize_svg_state(params: Mapping[str, float | int]) -> dict[str, float]:
    """Normalize dictionaries into the canonical 9-field SVG articulatory schema."""
    defaults = svg_state_to_dict(default_articulatory_state())
    return {
        "lip_aperture": float(clamp_unit(params.get("lip_aperture", defaults["lip_aperture"]))),
        "lip_protrusion": float(
            clamp_unit(params.get("lip_protrusion", defaults["lip_protrusion"]))
        ),
        "tongue_tip_constriction_location": float(
            clamp_unit(
                params.get(
                    "tongue_tip_constriction_location",
                    defaults["tongue_tip_constriction_location"],
                )
            )
        ),
        "tongue_tip_constriction_degree": float(
            clamp_unit(
                params.get(
                    "tongue_tip_constriction_degree",
                    defaults["tongue_tip_constriction_degree"],
                )
            )
        ),
        "lateral_tongue_drop": float(
            clamp_unit(params.get("lateral_tongue_drop", defaults["lateral_tongue_drop"]))
        ),
        "velic_aperture": float(
            clamp_unit(params.get("velic_aperture", defaults["velic_aperture"]))
        ),
        "tongue_body_constriction_location": float(
            clamp_unit(
                params.get(
                    "tongue_body_constriction_location",
                    defaults["tongue_body_constriction_location"],
                )
            )
        ),
        "tongue_body_constriction_degree": float(
            clamp_unit(
                params.get(
                    "tongue_body_constriction_degree",
                    defaults["tongue_body_constriction_degree"],
                )
            )
        ),
        "glottal_aperture": float(
            clamp_unit(params.get("glottal_aperture", defaults["glottal_aperture"]))
        ),
    }
