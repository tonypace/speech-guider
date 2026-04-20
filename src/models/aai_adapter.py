"""AAI tract-variable adapter for SVG articulatory animation.

NORMALIZATION EVOLUTION (Documented for Future Work):
-----------------------------------------------------
| Stage | Normalization | Status                    |
|-------|--------------|---------------------------|
| Old   | z_score      | Removed (DistilHuBERT)    |
| Now   | robust_01    | Current (ContentVec+DANN) |
| Future| hard_sigmoid_01 | Under refinement       |

- z_score: Values in (-inf, +inf), required denormalization via AAINormalizationProfile
- robust_01: Values already in [0, 1], no denormalization needed
- hard_sigmoid_01: Hard-sigmoid clamped to [0, 1], upcoming refinement

The adapter handles both z_score (backward compatibility) and robust_01 (current).
For robust_01, values are used directly as unit interval inputs.
"""

from dataclasses import dataclass, field
from typing import Mapping, Sequence, cast

import numpy as np

from src.models.articulatory import (
    default_articulatory_state,
    normalize_svg_state,
    svg_state_to_dict,
)
from src.models.articulatory_calibration import (
    apply_global_articulatory_calibration,
    clamp_unit,
)

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
    """Metadata required to convert AAI tract variables.

    Args:
        normalization: One of "raw", "z_score", or "robust_01"
        source_dataset: Dataset source (affects masked fields)
        masked_fields: Fields to mask/fallback
    """

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
    """Reduce a TV trajectory to a stable representative pose.

    Args:
        frames: Sequence of (9,) TV rows
        profile: Normalization profile (used for z_score denormalization)
        normalization: One of "raw", "z_score", or "robust_01"

    Returns:
        AAITractVariables representing the median pose
    """
    if len(frames) == 0:
        raise ValueError("AAI frames must not be empty")

    matrix = np.asarray(frames, dtype=np.float32)
    if matrix.ndim != 2 or matrix.shape[1] != len(AAI_TV_ORDER):
        raise ValueError("AAI frames must have shape (T, 9)")

    center = np.median(matrix, axis=0)

    if normalization == "z_score":
        # z_score requires denormalization to physical units
        return denormalize_aai_row(center.tolist(), profile)
    elif normalization == "robust_01":
        # robust_01 values are already in [0, 1], use directly
        # Clamp to [0, 1] for safety
        center = np.clip(center, 0.0, 1.0)
        return decode_aai_row(center.tolist())
    else:
        # raw: use values as-is
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
    """Resolve incoming AAI values into one consistent physical scale.

    For z_score: denormalize to physical units (mm)
    For robust_01: values already in [0, 1], pass through
    """
    if metadata.normalization == "z_score":
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
    elif metadata.normalization == "robust_01":
        # Values already in [0, 1], no transformation needed
        # Just ensure they're properly bounded
        return AAITractVariables(
            lp=max(0.0, min(1.0, tract_variables.lp)),
            la=max(0.0, min(1.0, tract_variables.la)),
            ttcl=max(0.0, min(1.0, tract_variables.ttcl)),
            ttcd=max(0.0, min(1.0, tract_variables.ttcd)),
            tbcl=max(0.0, min(1.0, tract_variables.tbcl)),
            tbcd=max(0.0, min(1.0, tract_variables.tbcd)),
            vel=max(0.0, min(1.0, tract_variables.vel)),
            glo=max(0.0, min(1.0, tract_variables.glo)),
            lat=max(0.0, min(1.0, tract_variables.lat)),
        )
    else:
        # raw: pass through as-is
        return tract_variables


def _resolved_aai_to_canonical_state(
    tract_variables: AAITractVariables,
    profile: AAINormalizationProfile,
    metadata: AAIConversionMetadata,
    fallback_state: Mapping[str, float] | None = None,
) -> dict[str, float]:
    """Map resolved AAI tract variables into canonical normalized state.

    Handles both z_score (physical mm values) and robust_01 ([0,1] values).
    """
    defaults = svg_state_to_dict(default_articulatory_state())
    fallback = dict(fallback_state or defaults)

    # For robust_01, values are already in [0,1], use directly
    # For z_score, we need to scale from physical mm to [0,1]
    if metadata.normalization == "robust_01":
        # Values already in [0, 1] range, use directly
        candidate = {
            "lip_aperture": clamp_unit(tract_variables.la),
            "lip_protrusion": clamp_unit(tract_variables.lp),
            "tongue_tip_constriction_location": clamp_unit(tract_variables.ttcl),
            "tongue_tip_constriction_degree": clamp_unit(tract_variables.ttcd),
            "lateral_tongue_drop": clamp_unit(tract_variables.lat),
            "velic_aperture": clamp_unit(tract_variables.vel),
            "tongue_body_constriction_location": clamp_unit(tract_variables.tbcl),
            "tongue_body_constriction_degree": clamp_unit(tract_variables.tbcd),
            "glottal_aperture": clamp_unit(tract_variables.glo),
        }
    else:
        # z_score or raw: scale from physical mm to [0,1]
        lp_extent = _reference_extent(profile.mean[0], profile.std[0])
        la_extent = _reference_extent(profile.mean[1], profile.std[1])
        ttcd_extent = _reference_extent(profile.mean[3], profile.std[3])
        tbcd_extent = _reference_extent(profile.mean[5], profile.std[5])
        vel_extent = _reference_extent(profile.mean[6], profile.std[6])

        candidate = {
            "lip_aperture": _mm_to_unit_interval(tract_variables.la, la_extent),
            "lip_protrusion": _lp_to_renderer(tract_variables.lp, lp_extent),
            "tongue_tip_constriction_location": clamp_unit(tract_variables.ttcl),
            "tongue_tip_constriction_degree": _mm_to_unit_interval(
                tract_variables.ttcd, ttcd_extent
            ),
            "lateral_tongue_drop": _lat_to_unit_interval(tract_variables.lat),
            "velic_aperture": _mm_to_unit_interval(tract_variables.vel, vel_extent),
            "tongue_body_constriction_location": clamp_unit(tract_variables.tbcl),
            "tongue_body_constriction_degree": _mm_to_unit_interval(
                tract_variables.tbcd, tbcd_extent
            ),
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


def aai_to_canonical_states_batch(
    tvs_array: np.ndarray,
    metadata: AAIConversionMetadata,
    fallback_state: Mapping[str, float] | None = None,
) -> list[dict[str, float]]:
    """Convert batch of tract variables to canonical states (vectorized).

    For robust_01 normalization, the conversion is element-wise clamp + calibration,
    which can be done efficiently with numpy. For z_score, falls back to per-frame
    processing.

    Args:
        tvs_array: Array of shape (T, 9) with tract variable rows
        metadata: Conversion metadata with normalization type
        fallback_state: Optional fallback for masked fields

    Returns:
        List of length T with canonical state dicts
    """
    if tvs_array.ndim != 2 or tvs_array.shape[1] != 9:
        raise ValueError(f"Expected shape (T, 9), got {tvs_array.shape}")

    defaults = svg_state_to_dict(default_articulatory_state())
    fallback = dict(fallback_state or defaults)

    if metadata.normalization == "robust_01":
        # Vectorized: clamp all values at once
        clamped = np.clip(tvs_array, 0.0, 1.0)

        # Apply calibration rule (identity by default, just clamp)
        # For robust_01, we just need to ensure [0,1] which np.clip handles
        calibrated = clamped  # DEFAULT_CALIBRATION_RULES uses identity mode

        # Build list of dicts
        frames = []
        for i in range(calibrated.shape[0]):
            row = calibrated[i]
            candidate = {
                "lip_aperture": clamp_unit(row[1]),  # la
                "lip_protrusion": clamp_unit(row[0]),  # lp
                "tongue_tip_constriction_location": clamp_unit(row[2]),  # ttcl
                "tongue_tip_constriction_degree": clamp_unit(row[3]),  # ttcd
                "lateral_tongue_drop": clamp_unit(row[8]),  # lat
                "velic_aperture": clamp_unit(row[6]),  # vel
                "tongue_body_constriction_location": clamp_unit(row[4]),  # tbcl
                "tongue_body_constriction_degree": clamp_unit(row[5]),  # tbcd
                "glottal_aperture": clamp_unit(row[7]),  # glo
            }

            # Handle masked fields
            masked_fields = set(metadata.masked_fields)
            if metadata.source_dataset in AAI_MASKED_FIELDS_BY_SOURCE:
                masked_fields |= AAI_MASKED_FIELDS_BY_SOURCE[metadata.source_dataset]

            if masked_fields:
                masked_field_mapping = {
                    "VEL": "velic_aperture",
                    "GLO": "glottal_aperture",
                    "LAT": "lateral_tongue_drop",
                }
                for aai_key, canonical_key in masked_field_mapping.items():
                    if aai_key in masked_fields:
                        candidate[canonical_key] = fallback.get(
                            canonical_key, defaults[canonical_key]
                        )

            # Apply global calibration (identity by default)
            calibrated_state = apply_global_articulatory_calibration(candidate)
            frames.append(calibrated_state)

        return frames
    else:
        # z_score or raw: fall back to per-frame processing
        frames = []
        for i in range(tvs_array.shape[0]):
            row = tvs_array[i]
            aaiv = AAITractVariables(
                lp=float(row[0]),
                la=float(row[1]),
                ttcl=float(row[2]),
                ttcd=float(row[3]),
                tbcl=float(row[4]),
                tbcd=float(row[5]),
                vel=float(row[6]),
                glo=float(row[7]),
                lat=float(row[8]),
            )
            frame = aai_to_canonical_state(aaiv, metadata=metadata, fallback_state=fallback_state)
            frames.append(frame)
        return frames


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
