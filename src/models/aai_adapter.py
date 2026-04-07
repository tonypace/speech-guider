"""AAI tract-variable adapter for SVG articulatory animation."""

from dataclasses import dataclass, field
from typing import Mapping, Sequence, cast

import numpy as np

from src.models.articulatory import (
    default_articulatory_state,
    normalize_svg_state,
    svg_state_to_dict,
)
from src.models.articulatory_calibration import apply_global_articulatory_calibration, clamp_unit

AAI_TV_ORDER: tuple[str, ...] = ("LP", "LA", "TTCL", "TTCD", "TBCL", "TBCD", "VEL", "GLO", "LAT")
AAI_MASKED_FIELDS_BY_SOURCE: dict[str, set[str]] = {
    "xrmb": {"VEL", "GLO", "LAT"},
}


@dataclass(frozen=True)
class AAINormalizationProfile:
    """Normalization stats for AAI tract variables."""

    mean: tuple[float, ...]
    std: tuple[float, ...]
    speaker_id: str | None = None
    profile_name: str = "reference"

    def __post_init__(self) -> None:
        if len(self.mean) != len(AAI_TV_ORDER):
            raise ValueError("AAI mean profile must contain 9 values")
        if len(self.std) != len(AAI_TV_ORDER):
            raise ValueError("AAI std profile must contain 9 values")
        if any(value <= 0 for value in self.std):
            raise ValueError("AAI std values must be positive")


@dataclass(frozen=True)
class AAIConversionMetadata:
    """Metadata required to convert AAI tract variables."""

    normalization: str = "raw"
    source_dataset: str | None = None
    masked_fields: frozenset[str] = field(default_factory=frozenset)

    @classmethod
    def from_payload(
        cls,
        payload: Mapping[str, object],
    ) -> "AAIConversionMetadata":
        source_dataset = payload.get("source_dataset")
        source_name = str(source_dataset).lower() if source_dataset is not None else None
        payload_masked = payload.get("masked_fields", [])
        masked_fields: set[str] = set()
        if isinstance(payload_masked, Sequence) and not isinstance(payload_masked, (str, bytes)):
            for field_name in cast(Sequence[object], payload_masked):
                masked_fields.add(str(field_name).upper())
        if source_name in AAI_MASKED_FIELDS_BY_SOURCE:
            masked_fields |= AAI_MASKED_FIELDS_BY_SOURCE[source_name]
        return cls(
            normalization=str(payload.get("normalization", "raw")),
            source_dataset=source_name,
            masked_fields=frozenset(masked_fields),
        )


@dataclass(frozen=True)
class AAITractVariables:
    """Named AAI tract variables in dataset field order semantics."""

    lp: float
    la: float
    ttcl: float
    ttcd: float
    tbcl: float
    tbcd: float
    vel: float
    glo: float
    lat: float

    def as_dict(self) -> dict[str, float]:
        """Return named AAI fields."""

        return {
            "LP": self.lp,
            "LA": self.la,
            "TTCL": self.ttcl,
            "TTCD": self.ttcd,
            "TBCL": self.tbcl,
            "TBCD": self.tbcd,
            "VEL": self.vel,
            "GLO": self.glo,
            "LAT": self.lat,
        }


DEFAULT_AAI_REFERENCE_PROFILE = AAINormalizationProfile(
    mean=(-3.035, 33.41, 0.0, 14.96, 0.85, 7.78, 11.64, 1.0, 0.0),
    std=(0.632, 0.68, 1.0, 0.73, 0.07, 0.20, 0.64, 1.0, 1.0),
    profile_name="aai_global_reference",
)


def decode_aai_row(row: Sequence[float | int]) -> AAITractVariables:
    """Decode a single AAI TV row using the dataset field order."""

    if len(row) != len(AAI_TV_ORDER):
        raise ValueError("AAI row must contain 9 values")

    values = [float(value) for value in row]
    return AAITractVariables(
        lp=values[0],
        la=values[1],
        ttcl=values[2],
        ttcd=values[3],
        tbcl=values[4],
        tbcd=values[5],
        vel=values[6],
        glo=values[7],
        lat=values[8],
    )


def denormalize_aai_row(
    row: Sequence[float | int],
    profile: AAINormalizationProfile | None = None,
) -> AAITractVariables:
    """Denormalize one z-scored AAI row using a stats profile."""

    stats = profile or DEFAULT_AAI_REFERENCE_PROFILE
    if len(row) != len(AAI_TV_ORDER):
        raise ValueError("AAI row must contain 9 values")

    values = [float(value) for value in row]
    denormalized = [
        (value * stats.std[index]) + stats.mean[index] for index, value in enumerate(values)
    ]
    return decode_aai_row(denormalized)


def representative_aai_pose(
    frames: Sequence[Sequence[float | int]],
    profile: AAINormalizationProfile | None = None,
    normalization: str = "raw",
) -> AAITractVariables:
    """Reduce a TV trajectory to a stable representative pose."""

    if len(frames) == 0:
        raise ValueError("AAI frames must not be empty")

    matrix = np.asarray(frames, dtype=np.float32)
    if matrix.ndim != 2 or matrix.shape[1] != len(AAI_TV_ORDER):
        raise ValueError("AAI frames must have shape (T, 9)")

    center = np.median(matrix, axis=0)
    if normalization == "z_score":
        return denormalize_aai_row(center.tolist(), profile)
    return decode_aai_row(center.tolist())


def _mm_to_unit_interval(value: float, reference_extent: float) -> float:
    """Scale nonnegative millimeter values into the canonical 0..1 range."""

    if reference_extent <= 0:
        return 0.0
    return max(0.0, min(1.0, value / reference_extent))


def _lp_to_renderer(value: float, reference_extent: float) -> float:
    """Map signed AAI lip protrusion to unsigned renderer protrusion."""

    return _mm_to_unit_interval(max(0.0, value), reference_extent)


def _glo_to_unit_interval(value: float) -> float:
    """Normalize glottal aperture into canonical 0..1 range."""

    return clamp_unit(value)


def _lat_to_unit_interval(value: float) -> float:
    """Normalize lateral tongue drop into canonical 0..1 range."""

    return clamp_unit(value)


def _reference_extent(mean: float, std: float) -> float:
    """Return a conservative positive reference extent from stats."""

    return max(1.0, abs(mean) + (3.0 * std))


def _resolve_aai_input_variables(
    tract_variables: AAITractVariables,
    profile: AAINormalizationProfile,
    metadata: AAIConversionMetadata,
) -> AAITractVariables:
    """Resolve incoming AAI values into one consistent physical scale."""

    if metadata.normalization != "z_score":
        return tract_variables

    return denormalize_aai_row(
        [
            tract_variables.lp,
            tract_variables.la,
            tract_variables.ttcl,
            tract_variables.ttcd,
            tract_variables.tbcl,
            tract_variables.tbcd,
            tract_variables.vel,
            tract_variables.glo,
            tract_variables.lat,
        ],
        profile,
    )


def _resolved_aai_to_canonical_state(
    tract_variables: AAITractVariables,
    profile: AAINormalizationProfile,
    metadata: AAIConversionMetadata,
    fallback_state: Mapping[str, float] | None = None,
) -> dict[str, float]:
    """Map resolved AAI tract variables into canonical normalized state."""

    defaults = svg_state_to_dict(default_articulatory_state())
    fallback = dict(fallback_state or defaults)

    lp_extent = _reference_extent(profile.mean[0], profile.std[0])
    la_extent = _reference_extent(profile.mean[1], profile.std[1])
    ttcd_extent = _reference_extent(profile.mean[3], profile.std[3])
    tbcd_extent = _reference_extent(profile.mean[5], profile.std[5])
    vel_extent = _reference_extent(profile.mean[6], profile.std[6])

    candidate = {
        "lip_aperture": _mm_to_unit_interval(tract_variables.la, la_extent),
        "lip_protrusion": _lp_to_renderer(tract_variables.lp, lp_extent),
        "tongue_tip_constriction_location": clamp_unit(tract_variables.ttcl),
        "tongue_tip_constriction_degree": _mm_to_unit_interval(tract_variables.ttcd, ttcd_extent),
        "lateral_tongue_drop": _lat_to_unit_interval(tract_variables.lat),
        "velic_aperture": _mm_to_unit_interval(tract_variables.vel, vel_extent),
        "tongue_body_constriction_location": clamp_unit(tract_variables.tbcl),
        "tongue_body_constriction_degree": _mm_to_unit_interval(tract_variables.tbcd, tbcd_extent),
        "glottal_aperture": _glo_to_unit_interval(tract_variables.glo),
    }

    masked_fields = set(metadata.masked_fields)
    if metadata.source_dataset in AAI_MASKED_FIELDS_BY_SOURCE:
        masked_fields |= AAI_MASKED_FIELDS_BY_SOURCE[metadata.source_dataset]

    masked_field_mapping = {
        "VEL": "velic_aperture",
        "GLO": "glottal_aperture",
        "LAT": "lateral_tongue_drop",
    }
    for aai_key, canonical_key in masked_field_mapping.items():
        if aai_key in masked_fields:
            candidate[canonical_key] = fallback.get(canonical_key, defaults[canonical_key])

    return apply_global_articulatory_calibration(normalize_svg_state(candidate))


def aai_to_canonical_state(
    tract_variables: AAITractVariables,
    profile: AAINormalizationProfile | None = None,
    metadata: AAIConversionMetadata | None = None,
    fallback_state: Mapping[str, float] | None = None,
) -> dict[str, float]:
    """Convert AAI tract variables into the canonical renderer contract."""

    stats = profile or DEFAULT_AAI_REFERENCE_PROFILE
    conversion_metadata = metadata or AAIConversionMetadata()
    resolved_variables = _resolve_aai_input_variables(tract_variables, stats, conversion_metadata)
    return _resolved_aai_to_canonical_state(
        resolved_variables,
        profile=stats,
        metadata=conversion_metadata,
        fallback_state=fallback_state,
    )


def parse_aai_animation_payload(
    payload: Mapping[str, object],
    fallback_state: Mapping[str, float] | None = None,
) -> dict[str, float]:
    """Parse an AAI animation payload into canonical renderer state."""

    metadata = AAIConversionMetadata.from_payload(payload)
    profile_payload = payload.get("stats_reference")
    profile = DEFAULT_AAI_REFERENCE_PROFILE
    if isinstance(profile_payload, Mapping):
        mean = profile_payload.get("mean", DEFAULT_AAI_REFERENCE_PROFILE.mean)
        std = profile_payload.get("std", DEFAULT_AAI_REFERENCE_PROFILE.std)
        speaker_id = profile_payload.get("speaker_id")
        profile_name = str(profile_payload.get("profile_name", "payload_reference"))
        profile = AAINormalizationProfile(
            mean=tuple(float(value) for value in mean),
            std=tuple(float(value) for value in std),
            speaker_id=str(speaker_id) if speaker_id is not None else None,
            profile_name=profile_name,
        )

    if "frames" in payload:
        frames = payload.get("frames")
        if not isinstance(frames, Sequence):
            raise ValueError("AAI frames payload must be a sequence")
        tract_variables = representative_aai_pose(
            frames,
            profile=profile,
            normalization=metadata.normalization,
        )
    else:
        values = payload.get("values")
        if not isinstance(values, Sequence):
            raise ValueError("AAI values payload must be a sequence")
        tract_variables = decode_aai_row(values)

    return aai_to_canonical_state(
        tract_variables,
        profile=profile,
        metadata=metadata,
        fallback_state=fallback_state,
    )
