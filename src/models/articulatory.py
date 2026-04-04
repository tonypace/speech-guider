"""Articulatory mapping using pyclts to convert IPA to SVG renderer state.

Maps phoneme features (place, manner, voicing) to visual parameters for
vocal tract animation. Provides technical descriptions and friendly tooltips.
"""

from dataclasses import dataclass
from typing import Mapping, Optional

import pyclts


@dataclass
class ArticulatoryParameters:
    """Legacy articulatory parameters kept for preset normalization.

    9 articulatory variables for comprehensive phoneme representation:
    - tongueIndex: tongue horizontal position (back/front)
    - tongueDiameter: tongue constriction degree
    - tongueCurl: tongue tip retroflexion
    - tongueRoot: tongue root retraction
    - lipRounding: lip protrusion/rounding
    - lipClosure: lip aperture
    - nasality: velum opening
    - voicing: vocal fold vibration
    - aspiration: voice onset timing
    """

    # Tongue body position (0.0 = back/velar, 1.0 = front/alveolar)
    tongueIndex: float
    # Tongue constriction (0.0 = open/low, 1.0 = closed/high)
    tongueDiameter: float
    # Tongue tip retroflexion (0.0 = flat, 1.0 = curled back)
    tongueCurl: float
    # Tongue root position (0.0 = advanced, 1.0 = retracted/pharyngeal)
    tongueRoot: float
    # Lip rounding (0.0 = spread, 1.0 = rounded/protruded)
    lipRounding: float
    # Lip aperture (0.0 = open, 1.0 = sealed/closed)
    lipClosure: float
    # Nasality (0.0 = oral/closed velum, 1.0 = nasal/open velum)
    nasality: float
    # Voicing (0.0 = voiceless, 1.0 = voiced)
    voicing: float
    # Aspiration (0.0 = unaspirated/immediate VOT, 1.0 = aspirated/delayed VOT)
    aspiration: float


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
        "lat": 0,
        "vel": 0.00,
        "tbcl": 0.55,
        "tbcd": 0.55,
        "glo": 18,
    },
    "b": {
        "lip_aperture": 0.00,
        "lip_protrusion": 0.43,
        "ttcl": 0.45,
        "ttcd": 0.90,
        "lat": 0,
        "vel": 0.00,
        "tbcl": 0.55,
        "tbcd": 0.55,
        "glo": 3,
    },
    "m": {
        "lip_aperture": 0.00,
        "lip_protrusion": 0.43,
        "ttcl": 0.45,
        "ttcd": 0.70,
        "lat": 0,
        "vel": 0.88,
        "tbcl": 0.55,
        "tbcd": 0.55,
        "glo": 3,
    },
    "t": {
        "lip_aperture": 0.10,
        "lip_protrusion": 0.07,
        "ttcl": 0.95,
        "ttcd": 1.00,
        "lat": 0,
        "vel": 0.00,
        "tbcl": 0.75,
        "tbcd": 0.55,
        "glo": 18,
    },
    "d": {
        "lip_aperture": 0.10,
        "lip_protrusion": 0.07,
        "ttcl": 0.95,
        "ttcd": 1.00,
        "lat": 0,
        "vel": 0.00,
        "tbcl": 0.75,
        "tbcd": 0.55,
        "glo": 3,
    },
    "n": {
        "lip_aperture": 0.10,
        "lip_protrusion": 0.07,
        "ttcl": 0.95,
        "ttcd": 0.70,
        "lat": 0,
        "vel": 0.88,
        "tbcl": 0.75,
        "tbcd": 0.55,
        "glo": 3,
    },
    "k": {
        "lip_aperture": 0.10,
        "lip_protrusion": 0.14,
        "ttcl": 0.10,
        "ttcd": 1.00,
        "lat": 0,
        "vel": 0.00,
        "tbcl": 0.15,
        "tbcd": 1.00,
        "glo": 18,
    },
    "g": {
        "lip_aperture": 0.10,
        "lip_protrusion": 0.14,
        "ttcl": 0.10,
        "ttcd": 1.00,
        "lat": 0,
        "vel": 0.00,
        "tbcl": 0.15,
        "tbcd": 1.00,
        "glo": 3,
    },
    "ŋ": {
        "lip_aperture": 0.10,
        "lip_protrusion": 0.14,
        "ttcl": 0.10,
        "ttcd": 0.70,
        "lat": 0,
        "vel": 0.88,
        "tbcl": 0.15,
        "tbcd": 1.00,
        "glo": 3,
    },
    "f": {
        "lip_aperture": 0.15,
        "lip_protrusion": 0.07,
        "ttcl": 0.60,
        "ttcd": 0.70,
        "lat": 0,
        "vel": 0.00,
        "tbcl": 0.55,
        "tbcd": 0.40,
        "glo": 18,
    },
    "v": {
        "lip_aperture": 0.15,
        "lip_protrusion": 0.07,
        "ttcl": 0.60,
        "ttcd": 0.70,
        "lat": 0,
        "vel": 0.00,
        "tbcl": 0.55,
        "tbcd": 0.40,
        "glo": 3,
    },
    "s": {
        "lip_aperture": 0.10,
        "lip_protrusion": 0.07,
        "ttcl": 0.95,
        "ttcd": 0.70,
        "lat": 0,
        "vel": 0.00,
        "tbcl": 0.80,
        "tbcd": 0.55,
        "glo": 18,
    },
    "z": {
        "lip_aperture": 0.10,
        "lip_protrusion": 0.07,
        "ttcl": 0.95,
        "ttcd": 0.70,
        "lat": 0,
        "vel": 0.00,
        "tbcl": 0.80,
        "tbcd": 0.55,
        "glo": 3,
    },
    "ʃ": {
        "lip_aperture": 0.10,
        "lip_protrusion": 0.07,
        "ttcl": 0.80,
        "ttcd": 0.70,
        "lat": 0,
        "vel": 0.00,
        "tbcl": 0.70,
        "tbcd": 0.55,
        "glo": 18,
    },
    "ʒ": {
        "lip_aperture": 0.10,
        "lip_protrusion": 0.07,
        "ttcl": 0.80,
        "ttcd": 0.70,
        "lat": 0,
        "vel": 0.00,
        "tbcl": 0.70,
        "tbcd": 0.55,
        "glo": 3,
    },
    "tʃ": {
        "lip_aperture": 0.10,
        "lip_protrusion": 0.07,
        "ttcl": 0.82,
        "ttcd": 1.00,
        "lat": 0,
        "vel": 0.00,
        "tbcl": 0.72,
        "tbcd": 0.70,
        "glo": 18,
    },
    "dʒ": {
        "lip_aperture": 0.10,
        "lip_protrusion": 0.07,
        "ttcl": 0.82,
        "ttcd": 1.00,
        "lat": 0,
        "vel": 0.00,
        "tbcl": 0.72,
        "tbcd": 0.70,
        "glo": 3,
    },
    "h": {
        "lip_aperture": 0.25,
        "lip_protrusion": 0.00,
        "ttcl": 0.35,
        "ttcd": 0.20,
        "lat": 0,
        "vel": 0.00,
        "tbcl": 0.35,
        "tbcd": 0.14,
        "glo": 20,
    },
    "l": {
        "lip_aperture": 0.15,
        "lip_protrusion": 0.07,
        "ttcl": 0.95,
        "ttcd": 0.40,
        "lat": 18,
        "vel": 0.00,
        "tbcl": 0.75,
        "tbcd": 0.40,
        "glo": 3,
    },
    "ɹ": {
        "lip_aperture": 0.20,
        "lip_protrusion": 0.07,
        "ttcl": 0.75,
        "ttcd": 0.30,
        "lat": 0,
        "vel": 0.00,
        "tbcl": 0.60,
        "tbcd": 0.40,
        "glo": 3,
    },
    "j": {
        "lip_aperture": 0.25,
        "lip_protrusion": 0.00,
        "ttcl": 0.85,
        "ttcd": 0.20,
        "lat": 0,
        "vel": 0.00,
        "tbcl": 0.65,
        "tbcd": 0.28,
        "glo": 3,
    },
    "w": {
        "lip_aperture": 0.20,
        "lip_protrusion": 0.71,
        "ttcl": 0.25,
        "ttcd": 0.20,
        "lat": 0,
        "vel": 0.00,
        "tbcl": 0.25,
        "tbcd": 0.28,
        "glo": 3,
    },
}

VOWEL_TEMPLATES: dict[str, dict[str, float]] = {
    "i": {
        "lip_aperture": 0.30,
        "lip_protrusion": 0.00,
        "ttcl": 0.80,
        "ttcd": 0.60,
        "lat": 0,
        "vel": 0.00,
        "tbcl": 0.85,
        "tbcd": 0.85,
        "glo": 0,
    },
    "e": {
        "lip_aperture": 0.25,
        "lip_protrusion": 0.07,
        "ttcl": 0.70,
        "ttcd": 0.50,
        "lat": 0,
        "vel": 0.00,
        "tbcl": 0.75,
        "tbcd": 0.70,
        "glo": 0,
    },
    "æ": {
        "lip_aperture": 0.35,
        "lip_protrusion": 0.07,
        "ttcl": 0.60,
        "ttcd": 0.60,
        "lat": 0,
        "vel": 0.00,
        "tbcl": 0.55,
        "tbcd": 0.70,
        "glo": 0,
    },
    "a": {
        "lip_aperture": 0.35,
        "lip_protrusion": 0.14,
        "ttcl": 0.55,
        "ttcd": 0.50,
        "lat": 0,
        "vel": 0.00,
        "tbcl": 0.50,
        "tbcd": 0.55,
        "glo": 0,
    },
    "ɑ": {
        "lip_aperture": 0.30,
        "lip_protrusion": 0.14,
        "ttcl": 0.30,
        "ttcd": 0.60,
        "lat": 0,
        "vel": 0.00,
        "tbcl": 0.35,
        "tbcd": 0.70,
        "glo": 0,
    },
    "o": {
        "lip_aperture": 0.10,
        "lip_protrusion": 0.57,
        "ttcl": 0.25,
        "ttcd": 0.50,
        "lat": 0,
        "vel": 0.00,
        "tbcl": 0.35,
        "tbcd": 0.70,
        "glo": 0,
    },
    "u": {
        "lip_aperture": 0.00,
        "lip_protrusion": 0.71,
        "ttcl": 0.15,
        "ttcd": 0.60,
        "lat": 0,
        "vel": 0.00,
        "tbcl": 0.20,
        "tbcd": 0.85,
        "glo": 0,
    },
    "ə": {
        "lip_aperture": 0.25,
        "lip_protrusion": 0.36,
        "ttcl": 0.35,
        "ttcd": 0.50,
        "lat": 0,
        "vel": 0.00,
        "tbcl": 0.55,
        "tbcd": 0.70,
        "glo": 0,
    },
    "ʌ": {
        "lip_aperture": 0.25,
        "lip_protrusion": 0.29,
        "ttcl": 0.30,
        "ttcd": 0.50,
        "lat": 0,
        "vel": 0.00,
        "tbcl": 0.40,
        "tbcd": 0.70,
        "glo": 0,
    },
    "ɔ": {
        "lip_aperture": 0.07,
        "lip_protrusion": 0.64,
        "ttcl": 0.20,
        "ttcd": 0.40,
        "lat": 0,
        "vel": 0.00,
        "tbcl": 0.30,
        "tbcd": 0.55,
        "glo": 0,
    },
    "ɪ": {
        "lip_aperture": 0.25,
        "lip_protrusion": 0.07,
        "ttcl": 0.75,
        "ttcd": 0.60,
        "lat": 0,
        "vel": 0.00,
        "tbcl": 0.80,
        "tbcd": 0.85,
        "glo": 0,
    },
    "ɛ": {
        "lip_aperture": 0.30,
        "lip_protrusion": 0.07,
        "ttcl": 0.65,
        "ttcd": 0.50,
        "lat": 0,
        "vel": 0.00,
        "tbcl": 0.70,
        "tbcd": 0.70,
        "glo": 0,
    },
    "ʊ": {
        "lip_aperture": 0.05,
        "lip_protrusion": 0.57,
        "ttcl": 0.20,
        "ttcd": 0.60,
        "lat": 0,
        "vel": 0.00,
        "tbcl": 0.30,
        "tbcd": 0.85,
        "glo": 0,
    },
}


class ArticulatoryMapper:
    """Maps IPA phonemes to articulatory visualization parameters."""

    def __init__(self) -> None:
        """Initialize articulatory mapper with pyclts."""
        self._bipa = None
        self._feature_definitions = self._build_feature_definitions()
        self._tooltip_definitions = self._build_tooltip_definitions()

    def _get_bipa(self) -> pyclts.TranscriptionSystem:
        """Lazy load CLTS BIPA system.

        Returns:
            CLTS BIPA transcription system
        """
        if self._bipa is None:
            self._bipa = pyclts.TranscriptionSystem("bipa")  # type: ignore[call-arg, assignment]
        return self._bipa

    def _build_feature_definitions(self) -> dict[str, str]:
        """Build dictionary of technical feature definitions.

        Returns:
            Dictionary mapping feature keys to technical names
        """
        return {
            "place": "Place",
            "manner": "Manner",
            "voicing": "Voicing",
            "rounding": "Lip Shape",
        }

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
        try:
            bipa = self._get_bipa()
        except Exception:
            return PhonemeDescription(
                technical_name="Unknown",
                ipa_symbol=ipa_symbol,
                features={},
                tooltips={},
            )

        # Clean IPA symbol (remove slashes)
        clean_ipa = ipa_symbol.strip().strip("/")

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

    def map_to_parameters(self, phoneme_description: PhonemeDescription) -> ArticulatoryParameters:
        """Map phoneme features to visualization parameters.

        Args:
            phoneme_description: Phoneme description with features

        Returns:
            ArticulatoryParameters for animation
        """
        # Default parameters (neutral position)
        params = ArticulatoryParameters(
            tongueIndex=0.5,
            tongueDiameter=0.5,
            tongueCurl=0.0,
            tongueRoot=0.0,
            lipRounding=0.5,
            lipClosure=0.0,
            nasality=0.0,
            voicing=0.5,
            aspiration=0.0,
        )

        features = phoneme_description.features

        # Map place of articulation to tongueIndex (0.0 = back, 1.0 = front)
        if "place" in features:
            place = features["place"]
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
            params.tongueIndex = place_mapping.get(place, 0.5)

            # Set retroflex curling for retroflex sounds
            if place == "retroflex":
                params.tongueCurl = 1.0

            # Set tongue root retraction for pharyngeal/uvular
            if place in ["pharyngeal", "uvular"]:
                params.tongueRoot = 1.0

        # Map manner of articulation to tongueDiameter (0.0 = open/vowel, 1.0 = closed/plosive)
        if "manner" in features:
            manner = features["manner"]
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
            params.tongueDiameter = manner_mapping.get(manner, 0.5)

            # Set nasality for nasal sounds
            if manner == "nasal":
                params.nasality = 1.0

        # Map lip rounding to lipRounding (0.0 = spread, 1.0 = rounded)
        if "rounding" in features:
            rounding = features["rounding"]
            if rounding == "rounded":
                params.lipRounding = 1.0
            elif rounding == "unrounded":
                params.lipRounding = 0.0
            else:
                params.lipRounding = 0.5

        # Set lip closure for labial stops
        if "place" in features and features["place"] == "bilabial":
            if "manner" in features and features["manner"] == "plosive":
                params.lipClosure = 1.0

        # Map voicing to voicing parameter (0.0 = voiceless, 1.0 = voiced)
        if "voicing" in features:
            voicing = features["voicing"]
            if voicing == "voiced":
                params.voicing = 1.0
            elif voicing == "voiceless":
                params.voicing = 0.0
            else:
                params.voicing = 0.5

        return params

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
            lateral_tongue_drop=template["lat"],
            velic_aperture=template["vel"],
            tongue_body_constriction_location=template["tbcl"],
            tongue_body_constriction_degree=template["tbcd"],
            glottal_aperture=template["glo"],
        )

    def map_to_svg_state(self, phoneme_description: PhonemeDescription) -> dict[str, float]:
        """Map phoneme features to the SVG articulatory schema."""

        legacy = self.map_to_parameters(phoneme_description)
        return legacy_to_svg_state(legacy)

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
        mapping, then preset fallback, then defaults.

        Args:
            ipa_symbol: IPA phoneme string (e.g., 'i', 'æ', 'k')

        Returns:
            Dictionary with SVG articulatory parameters.
        """
        print(f"[ArticulatoryMapper.get_animation_params] Called with: {ipa_symbol}")

        clean_ipa = ipa_symbol.strip().strip("/")

        template = self._get_template(clean_ipa)
        if template:
            state = self._template_to_svg_state(template)
            result = svg_state_to_dict(state)
            print(
                f"[ArticulatoryMapper.get_animation_params] Template hit for '{clean_ipa}': {result}"
            )
            return result

        description = self.parse_phoneme(ipa_symbol)
        print(f"[ArticulatoryMapper.get_animation_params] Parsed description: {description}")

        if description.features:
            svg_state = self.map_to_svg_state(description)
            print(f"[ArticulatoryMapper.get_animation_params] Articulatory state: {svg_state}")

            result = normalize_svg_state(svg_state)
            print(f"[ArticulatoryMapper.get_animation_params] Returning pyclts result: {result}")
            return result

        print(f"[ArticulatoryMapper.get_animation_params] pyclts failed, trying preset fallback")
        try:
            from app.services.state import load_presets

            presets = load_presets()
            if clean_ipa in presets:
                preset = presets[clean_ipa]
                if "params" in preset:
                    print(
                        f"[ArticulatoryMapper.get_animation_params] Found preset fallback: {preset}"
                    )
                    params = preset["params"]
                    return normalize_svg_state(params)
                else:
                    print(
                        f"[ArticulatoryMapper.get_animation_params] Preset has no params: {preset}"
                    )
            else:
                print(
                    f"[ArticulatoryMapper.get_animation_params] Phoneme {clean_ipa} not in presets"
                )
        except Exception as e:
            print(f"[ArticulatoryMapper.get_animation_params] Preset fallback failed: {e}")

        print(f"[ArticulatoryMapper.get_animation_params] All fallbacks failed, returning defaults")
        return svg_state_to_dict(default_articulatory_state())

    def calculate_delta(
        self,
        target_params: ArticulatoryParameters,
        predicted_params: ArticulatoryParameters,
    ) -> tuple[str, Optional[str]]:
        """Calculate the delta between target and predicted parameters.

        Determines which anatomical zone has the largest difference for highlighting.

        Args:
            target_params: Correct articulatory parameters
            predicted_params: Incorrect articulatory parameters

        Returns:
            Tuple of (zone_name, highlight_zone) where highlight_zone is
            the zone to highlight with amber aura
        """
        # Calculate differences for each parameter
        tongueIndex_delta = abs(target_params.tongueIndex - predicted_params.tongueIndex)
        tongueDiameter_delta = abs(target_params.tongueDiameter - predicted_params.tongueDiameter)
        tongueCurl_delta = abs(target_params.tongueCurl - predicted_params.tongueCurl)
        tongueRoot_delta = abs(target_params.tongueRoot - predicted_params.tongueRoot)
        lipRounding_delta = abs(target_params.lipRounding - predicted_params.lipRounding)
        lipClosure_delta = abs(target_params.lipClosure - predicted_params.lipClosure)
        nasality_delta = abs(target_params.nasality - predicted_params.nasality)
        voicing_delta = abs(target_params.voicing - predicted_params.voicing)
        aspiration_delta = abs(target_params.aspiration - predicted_params.aspiration)

        # Determine which zone has the largest delta
        deltas = {
            "tongueIndex": tongueIndex_delta,
            "tongueDiameter": tongueDiameter_delta,
            "tongueCurl": tongueCurl_delta,
            "tongueRoot": tongueRoot_delta,
            "lipRounding": lipRounding_delta,
            "lipClosure": lipClosure_delta,
            "nasality": nasality_delta,
            "voicing": voicing_delta,
            "aspiration": aspiration_delta,
        }

        max_delta = max(deltas.values())
        max_zone_key = max(deltas, key=lambda k: deltas[k])

        # Map to anatomical zones for highlighting
        if max_delta < 0.1:
            # No significant difference
            return ("No major difference", None)

        zone_mapping = {
            "lipRounding": "lips",
            "lipClosure": "lips",
            "nasality": "velum",
            "voicing": "glottis",
            "aspiration": "glottis",
            "tongueCurl": "tongue_tip",
            "tongueRoot": "tongue_root",
            "tongueIndex": "tongue_body",
            "tongueDiameter": "tongue_body",
        }

        highlight_zone = zone_mapping.get(max_zone_key, None)

        return (f"Largest difference: {max_zone_key}", highlight_zone)


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


def _normalize_tongue_degree(value: float, legacy_rest_distance: float) -> float:
    """Normalize tongue constriction degree to the 0..1 SVG contract."""

    if value <= 1.0:
        return max(0.0, min(1.0, value))
    return max(0.0, min(1.0, value / legacy_rest_distance))


def _normalize_scalar(value: float, legacy_max: float) -> float:
    """Normalize scalar articulatory controls to the 0..1 SVG contract."""

    if value <= 1.0:
        return max(0.0, min(1.0, value))
    return max(0.0, min(1.0, value / legacy_max))


def normalize_svg_state(params: Mapping[str, float | int]) -> dict[str, float]:
    """Normalize dictionaries into the SVG articulatory schema."""

    svg_keys = {
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

    if any(key in params for key in svg_keys):
        defaults = svg_state_to_dict(default_articulatory_state())
        return {
            "lip_aperture": float(
                _normalize_scalar(
                    float(params.get("lip_aperture", defaults["lip_aperture"])),
                    40.0,
                )
            ),
            "lip_protrusion": float(
                _normalize_scalar(
                    float(params.get("lip_protrusion", defaults["lip_protrusion"])),
                    14.0,
                )
            ),
            "tongue_tip_constriction_location": float(
                params.get(
                    "tongue_tip_constriction_location",
                    defaults["tongue_tip_constriction_location"],
                )
            ),
            "tongue_tip_constriction_degree": float(
                _normalize_tongue_degree(
                    float(
                        params.get(
                            "tongue_tip_constriction_degree",
                            defaults["tongue_tip_constriction_degree"],
                        )
                    ),
                    40.0,
                )
            ),
            "lateral_tongue_drop": float(
                params.get("lateral_tongue_drop", defaults["lateral_tongue_drop"])
            ),
            "velic_aperture": float(
                _normalize_scalar(
                    float(params.get("velic_aperture", defaults["velic_aperture"])),
                    40.0,
                )
            ),
            "tongue_body_constriction_location": float(
                params.get(
                    "tongue_body_constriction_location",
                    defaults["tongue_body_constriction_location"],
                )
            ),
            "tongue_body_constriction_degree": float(
                _normalize_tongue_degree(
                    float(
                        params.get(
                            "tongue_body_constriction_degree",
                            defaults["tongue_body_constriction_degree"],
                        )
                    ),
                    30.0,
                )
            ),
            "glottal_aperture": float(params.get("glottal_aperture", defaults["glottal_aperture"])),
        }

    legacy = {
        "tongueIndex": params.get("tongueIndex", 0.5),
        "tongueDiameter": params.get("tongueDiameter", 0.5),
        "tongueCurl": params.get("tongueCurl", 0.0),
        "tongueRoot": params.get("tongueRoot", 0.0),
        "lipRounding": params.get("lipRounding", 0.5),
        "lipClosure": params.get("lipClosure", 0.0),
        "nasality": params.get("nasality", 0.0),
        "voicing": params.get("voicing", 0.5),
        "aspiration": params.get("aspiration", 0.0),
    }
    return legacy_to_svg_state(legacy)


def legacy_to_svg_state(params: dict[str, float] | ArticulatoryParameters) -> dict[str, float]:
    """Convert legacy articulatory parameters to the SVG schema."""

    if isinstance(params, ArticulatoryParameters):
        legacy = {
            "tongueIndex": params.tongueIndex,
            "tongueDiameter": params.tongueDiameter,
            "tongueCurl": params.tongueCurl,
            "tongueRoot": params.tongueRoot,
            "lipRounding": params.lipRounding,
            "lipClosure": params.lipClosure,
            "nasality": params.nasality,
            "voicing": params.voicing,
            "aspiration": params.aspiration,
        }
    else:
        legacy = params

    tongue_index = float(legacy.get("tongueIndex", 0.5))
    tongue_diameter = float(legacy.get("tongueDiameter", 0.5))
    tongue_curl = float(legacy.get("tongueCurl", 0.0))
    tongue_root = float(legacy.get("tongueRoot", 0.0))
    lip_rounding = float(legacy.get("lipRounding", 0.5))
    lip_closure = float(legacy.get("lipClosure", 0.0))
    nasality = float(legacy.get("nasality", 0.0))
    voicing = float(legacy.get("voicing", 0.5))
    aspiration = float(legacy.get("aspiration", 0.0))

    tongue_front_back = max(0.0, min(1.0, (1.0 - tongue_index) * 0.85))
    tongue_body_location = max(0.0, min(1.0, 0.25 + tongue_front_back))
    lip_aperture = max(0.0, min(1.0, (1.0 - lip_closure) * (1.0 - 0.45 * lip_rounding)))
    lip_protrusion = max(0.0, min(1.0, lip_rounding))
    tongue_degree = max(0.0, min(1.0, tongue_diameter))
    lateral_drop = 40.0 * max(0.0, min(1.0, tongue_curl * 0.25))
    velic_aperture = max(0.0, min(1.0, nasality))
    glottal_aperture = max(
        0.0, min(30.0, 30.0 * max(0.0, min(1.0, (1.0 - voicing) + aspiration * 0.5)))
    )

    if tongue_root > 0.5:
        tongue_body_location = max(tongue_body_location, 0.65)

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


def format_with_html_tooltips(description: PhonemeDescription) -> str:
    """Format phoneme description with HTML tooltips for display.

    Args:
        description: Phoneme description with features and tooltips

    Returns:
        HTML string with tooltip spans
    """
    html_parts = []

    for feature, value in description.features.items():
        if value in ["", "unknown"]:
            continue

        # Get tooltip for this value
        tooltip = description.tooltips.get(feature, "")

        # Create HTML span with tooltip
        if tooltip:
            html_parts.append(
                f'<span class="tooltip" title="{tooltip}" data-feature="{feature}" data-value="{value}">{value.capitalize()}</span>'
            )
        else:
            html_parts.append(f"<span>{value.capitalize()}</span>")

        html_parts.append(" ")

    return "".join(html_parts).strip()
