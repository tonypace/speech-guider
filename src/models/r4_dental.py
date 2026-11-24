"""Display correction for an acoustic dental-fricative readout."""

import json
from pathlib import Path
from typing import cast

import numpy as np

FORMAT = "streaming_dental_probe_v1"
# The current SVG maps tip location onto [0, 0.25] of its oral roof track.
# Position 0.015 on that track is on the upper-incisor curve.
INCISOR_LOCATION = 0.06
# A small visible gap keeps the stop-contact patch off (cutoff 0.03).
DENTAL_DEGREE = 0.045


class DentalCorrection:
    def __init__(self, weights: list[float], bias: float, threshold: float) -> None:
        self.weights = np.asarray(weights, dtype=np.float64)
        self.bias = float(bias)
        self.threshold = float(threshold)
        if (
            self.weights.ndim != 1
            or not len(self.weights)
            or not np.isfinite(self.weights).all()
            or not np.isfinite(self.bias)
            or not 0 <= self.threshold <= 1
        ):
            raise ValueError("Invalid dental readout parameters")

    @classmethod
    def load(cls, path: str | Path) -> "DentalCorrection":
        model = json.loads(Path(path).read_text())
        if (model["format"], model["target_tip_location"], model["target_tip_degree"]) != (
            FORMAT,
            INCISOR_LOCATION,
            DENTAL_DEGREE,
        ):
            raise ValueError("Dental readout uses a different display target")
        return cls(model["weight"], model["bias"], model["threshold"])

    def probabilities(self, features: np.ndarray) -> np.ndarray:
        features = np.asarray(features)
        if (
            features.ndim != 2
            or features.shape[1] != len(self.weights)
            or not np.isfinite(features).all()
        ):
            raise ValueError("Expected one frozen ContentVec feature vector per committed frame")
        logits = features @ self.weights + self.bias
        return cast(np.ndarray, np.exp(-np.logaddexp(0, -logits)))

    def apply(self, features: np.ndarray, trajectory: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Apply to one committed packet or a contiguous replay on the same clock."""
        return apply_dental_correction(trajectory, self.probabilities(features), self.threshold)


def apply_dental_correction(
    trajectory: np.ndarray,
    probabilities: np.ndarray,
    threshold: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Blend committed tip place and gap toward the incisors on confident frames."""
    values = np.asarray(trajectory)
    probabilities = np.asarray(probabilities)
    if (
        values.ndim != 2
        or values.shape[1] != 9
        or probabilities.shape != (len(values),)
        or not np.issubdtype(values.dtype, np.floating)
    ):
        raise ValueError("Expected a nine-channel trajectory and one probability per frame")
    if (
        not 0 <= threshold <= 1
        or not np.isfinite(values).all()
        or not np.isfinite(probabilities).all()
    ):
        raise ValueError("Dental correction requires finite values and a valid threshold")

    # Retain existing tongue holds and lip seals when the readout disagrees.
    eligible = (values[:, 3] > 0.03) & (values[:, 5] > 0.03) & (values[:, 1] > 0.05)
    ramp = np.clip((probabilities - threshold) / min(0.20, max(0.01, 1 - threshold)), 0, 1)
    strength = (ramp * ramp * (3 - 2 * ramp)).astype(values.dtype)
    strength[~eligible] = 0
    out = values.copy()
    active = strength > 0
    blend = strength[active]
    out[active, 2] += blend * (INCISOR_LOCATION - values[active, 2])
    out[active, 3] += blend * (np.minimum(values[active, 3], DENTAL_DEGREE) - values[active, 3])
    return out, strength
