"""Display correction for an acoustic labiodental-fricative readout.

Readout math follows the final reference bundle (CC BY-NC 4.0).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

FORMAT = "streaming_labiodental_probe_v1"
LABIODENTAL_TARGET = 1.0


class LabiodentalCorrection:
    """Frozen ContentVec-L7 linear readout driving the optional labiodental channel."""

    def __init__(self, weights: Any, bias: float, threshold: float) -> None:
        self.weights = np.asarray(weights, dtype=np.float64)
        self.bias = float(bias)
        self.threshold = float(threshold)
        if (
            self.weights.ndim != 1
            or not len(self.weights)
            or not np.isfinite(self.weights).all()
            or not np.isfinite(self.bias)
            or not 0.0 <= self.threshold <= 1.0
        ):
            raise ValueError("Invalid labiodental readout parameters")

    @classmethod
    def load(
        cls,
        path: str | Path,
        *,
        contentvec_sha256: str | None = None,
    ) -> LabiodentalCorrection:
        model = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(model, dict):
            raise ValueError("Labiodental readout payload must be a JSON object")
        if model.get("format") != FORMAT:
            raise ValueError(f"Unsupported labiodental readout format: {model.get('format')!r}")
        if (
            contentvec_sha256 is not None
            and model.get("contentvec_state_sha256") != contentvec_sha256
        ):
            raise ValueError("Labiodental readout requires the matching ContentVec encoder")
        target = float(model.get("target_retraction", LABIODENTAL_TARGET))
        if not np.isfinite(target) or target != LABIODENTAL_TARGET:
            raise ValueError("Labiodental readout uses a different display target")
        for required_key in ("weight", "bias", "threshold"):
            if required_key not in model:
                raise ValueError(f"Labiodental readout missing required key: {required_key!r}")
        return cls(model["weight"], model["bias"], model["threshold"])

    def probabilities(self, features: Any) -> np.ndarray:
        features_arr = np.asarray(features)
        if (
            features_arr.ndim != 2
            or features_arr.shape[1] != len(self.weights)
            or not np.issubdtype(features_arr.dtype, np.number)
            or not np.isfinite(features_arr).all()
        ):
            raise ValueError("Expected one frozen ContentVec feature vector per committed frame")
        logits = features_arr.astype(np.float64, copy=False) @ self.weights + self.bias
        return np.asarray(np.exp(-np.logaddexp(0.0, -logits)), dtype=np.float64)

    def apply(self, features: Any, trajectory: Any) -> tuple[np.ndarray, np.ndarray]:
        """Apply to one committed packet or a contiguous replay on the same clock."""
        return apply_labiodental_correction(
            trajectory, self.probabilities(features), self.threshold
        )


def apply_labiodental_correction(
    trajectory: Any, probabilities: Any, threshold: float
) -> tuple[np.ndarray, np.ndarray]:
    """Compute gated labiodental retraction signal in [0, 1] without mutating trajectory."""
    values = np.asarray(trajectory)
    probs = np.asarray(probabilities)
    if (
        values.ndim != 2
        or values.shape[1] != 9
        or probs.shape != (len(values),)
        or not np.issubdtype(values.dtype, np.floating)
        or not np.issubdtype(probs.dtype, np.number)
    ):
        raise ValueError("Expected a nine-channel trajectory and one probability per frame")
    if (
        not 0.0 <= float(threshold) <= 1.0
        or not np.isfinite(values).all()
        or not np.isfinite(probs).all()
    ):
        raise ValueError("Labiodental correction requires finite values and a valid threshold")

    # Retain existing bilabial seals (LA <= 0.05) and tongue stops (TTCD/TBCD <= 0.03).
    eligible = (values[:, 3] > 0.03) & (values[:, 5] > 0.03) & (values[:, 1] > 0.05)
    denom = min(0.20, max(0.01, 1.0 - float(threshold)))
    ramp = np.clip((probs.astype(np.float64, copy=False) - float(threshold)) / denom, 0.0, 1.0)
    strength = (ramp * ramp * (3.0 - 2.0 * ramp)).astype(np.float32)
    strength[~eligible] = 0.0
    retraction = np.clip(strength * np.float32(LABIODENTAL_TARGET), 0.0, 1.0).astype(np.float32)
    return retraction, strength
