"""Tests for global articulatory calibration rules."""

from src.models.articulatory_calibration import (
    CalibrationRule,
    apply_calibration_rule,
    apply_global_articulatory_calibration,
)


def test_identity_rule_preserves_value() -> None:
    assert apply_calibration_rule(0.37, CalibrationRule(mode="identity")) == 0.37


def test_gamma_rule_is_monotonic() -> None:
    rule = CalibrationRule(mode="gamma", gamma=1.5)
    values = [0.0, 0.1, 0.3, 0.6, 1.0]
    outputs = [apply_calibration_rule(value, rule) for value in values]
    assert outputs == sorted(outputs)
    assert outputs[0] == 0.0
    assert outputs[-1] == 1.0


def test_piecewise_linear_rule_is_monotonic() -> None:
    rule = CalibrationRule(
        mode="piecewise_linear",
        points=((0.0, 0.0), (0.25, 0.10), (0.6, 0.5), (1.0, 1.0)),
    )
    values = [0.0, 0.1, 0.25, 0.5, 0.8, 1.0]
    outputs = [apply_calibration_rule(value, rule) for value in values]
    assert outputs == sorted(outputs)
    assert outputs[2] == 0.10


def test_global_calibration_can_tighten_ttcd() -> None:
    state = {
        "lip_aperture": 0.3,
        "lip_protrusion": 0.4,
        "tongue_tip_constriction_location": 0.6,
        "tongue_tip_constriction_degree": 0.3,
        "lateral_tongue_drop": 0.2,
        "velic_aperture": 0.1,
        "tongue_body_constriction_location": 0.7,
        "tongue_body_constriction_degree": 0.8,
        "glottal_aperture": 0.25,
    }
    calibrated = apply_global_articulatory_calibration(
        state,
        rules={
            "tongue_tip_constriction_degree": CalibrationRule(mode="gamma", gamma=1.5),
        },
    )

    assert calibrated["tongue_tip_constriction_degree"] < state["tongue_tip_constriction_degree"]
    assert calibrated["lip_aperture"] == state["lip_aperture"]
    assert 0.0 <= calibrated["tongue_tip_constriction_degree"] <= 1.0
