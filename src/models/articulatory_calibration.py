"""Canonical articulatory normalization and calibration helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

CANONICAL_ARTICULATORY_FIELDS: tuple[str, ...] = (
    "lip_aperture",
    "lip_protrusion",
    "tongue_tip_constriction_location",
    "tongue_tip_constriction_degree",
    "lateral_tongue_drop",
    "velic_aperture",
    "tongue_body_constriction_location",
    "tongue_body_constriction_degree",
    "glottal_aperture",
)


def clamp_unit(value: float) -> float:
    """Clamp a numeric value into the canonical normalized range."""

    return max(0.0, min(1.0, float(value)))


@dataclass(frozen=True)
class CalibrationRule:
    """A monotonic calibration rule for one canonical field."""

    mode: str = "identity"
    gamma: float = 1.0
    points: tuple[tuple[float, float], ...] = ()


def _apply_piecewise_linear(value: float, points: tuple[tuple[float, float], ...]) -> float:
    if not points:
        return value

    ordered = sorted((clamp_unit(x), clamp_unit(y)) for x, y in points)
    if value <= ordered[0][0]:
        return ordered[0][1]
    if value >= ordered[-1][0]:
        return ordered[-1][1]

    for index in range(1, len(ordered)):
        x0, y0 = ordered[index - 1]
        x1, y1 = ordered[index]
        if x0 <= value <= x1:
            if x1 == x0:
                return y1
            t = (value - x0) / (x1 - x0)
            return y0 + ((y1 - y0) * t)

    return value


def apply_calibration_rule(value: float, rule: CalibrationRule) -> float:
    """Apply one calibration rule to a normalized input value."""

    normalized = clamp_unit(value)
    if rule.mode == "identity":
        return normalized
    if rule.mode == "gamma":
        gamma = rule.gamma if rule.gamma > 0 else 1.0
        return clamp_unit(normalized**gamma)
    if rule.mode == "piecewise_linear":
        return clamp_unit(_apply_piecewise_linear(normalized, rule.points))
    raise ValueError(f"Unsupported calibration mode: {rule.mode}")


DEFAULT_CALIBRATION_RULES: dict[str, CalibrationRule] = {
    field_name: CalibrationRule() for field_name in CANONICAL_ARTICULATORY_FIELDS
}


def apply_global_articulatory_calibration(
    state: Mapping[str, float],
    rules: Mapping[str, CalibrationRule] | None = None,
) -> dict[str, float]:
    """Apply global per-field calibration to a canonical normalized state."""

    active_rules = rules or DEFAULT_CALIBRATION_RULES
    calibrated: dict[str, float] = {}
    for field_name in CANONICAL_ARTICULATORY_FIELDS:
        calibrated[field_name] = apply_calibration_rule(
            float(state.get(field_name, 0.0)),
            active_rules.get(field_name, CalibrationRule()),
        )
    return calibrated
