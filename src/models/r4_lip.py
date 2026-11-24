"""Stateful lip aperture realization on the committed 50 Hz frame clock."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import cast

import numpy as np

from src.models.r4_contract import NINE_CHANNELS, StreamingContract

LIP_PHASES = frozenset({"open", "approach", "hold", "release"})


@dataclass(frozen=True)
class LipClosureConfig:
    """Motion limits in normalized aperture per frame and frame².

    An unset approach aperture uses the same target as hold. Optional ramp
    lengths shape the reference before the existing velocity and acceleration
    limits are applied.
    """

    target_aperture: float = 0.02
    approach_max_velocity: float = 0.16
    approach_max_acceleration: float = 0.05
    release_max_velocity: float = 0.20
    release_max_acceleration: float = 0.08
    approach_aperture: float | None = None
    closure_ramp_frames: int | None = None
    release_ramp_frames: int | None = None

    def __post_init__(self) -> None:
        if not 0.0 <= self.target_aperture <= 1.0:
            raise ValueError("target_aperture must be in [0, 1]")
        if self.approach_aperture is not None and not (
            self.target_aperture <= self.approach_aperture <= 1.0
        ):
            raise ValueError("approach_aperture must be between target_aperture and 1")
        if self.closure_ramp_frames is not None:
            if self.closure_ramp_frames <= 0:
                raise ValueError("closure_ramp_frames must be positive")
        if self.release_ramp_frames is not None and self.release_ramp_frames <= 0:
            raise ValueError("release_ramp_frames must be positive")
        for name in (
            "approach_max_velocity",
            "approach_max_acceleration",
            "release_max_velocity",
            "release_max_acceleration",
        ):
            value = getattr(self, name)
            if not math.isfinite(value) or value <= 0.0:
                raise ValueError(f"{name} must be positive and finite")


def _clamp(value: float, lower: float, upper: float) -> float:
    return min(upper, max(lower, value))


def _stopping_speed(distance: float, acceleration: float) -> float:
    """Fastest step that can brake to zero within the remaining distance."""

    # Invert the sum v + max(v - a, 0) + max(v - 2a, 0) + ... .
    # n is the largest triangular number of acceleration steps that fits.
    n = math.floor(math.hypot(0.5, math.sqrt(2 * distance) / math.sqrt(acceleration)) - 0.5)
    return distance / (n + 1) + (n / 2) * acceleration


class LipClosureController:
    """Realize one lip aperture per committed frame, with one instance per stream.

    Approach drives toward the configured waypoint, and hold drives toward
    seal. Release and subsequent open frames track the live baseline until
    aperture and velocity rejoin it.
    Idle frames pass through exactly. If inherited baseline momentum or a
    phase switch makes both limits infeasible, acceleration takes precedence
    over velocity. The physical [0, 1] bounds take precedence over both.
    """

    def __init__(self, config: LipClosureConfig = LipClosureConfig()) -> None:
        self.config = config
        self.reset()

    def reset(self) -> None:
        self._active = False
        self._aperture: float | None = None
        self._previous_base: float | None = None
        self._velocity = 0.0
        self._closing_frames = 0
        self._releasing_frames = 0
        self._release_start = 0.0

    def step(self, base_aperture: float, phase: str) -> float:
        """Advance once on a normalized baseline sample and an explicit lip phase."""

        base_aperture = float(base_aperture)
        if not 0.0 <= base_aperture <= 1.0:
            raise ValueError("base_aperture must be in [0, 1]")
        if phase not in LIP_PHASES:
            raise ValueError(f"unknown lip phase: {phase!r}")

        aperture = base_aperture if self._aperture is None else self._aperture
        previous_base = base_aperture if self._previous_base is None else self._previous_base
        closing = phase in ("approach", "hold")
        self._closing_frames = self._closing_frames + 1 if closing else 0
        self._active = self._active or closing

        if self._active:
            self._releasing_frames = 0 if closing else self._releasing_frames + 1
            output = self._realize(aperture, base_aperture, phase)
            if closing:
                self._release_start = output
            if phase == "open" and output == base_aperture and aperture == previous_base:
                self._active = False
        else:
            output = base_aperture

        self._velocity = output - aperture
        self._aperture = output
        self._previous_base = base_aperture
        return output

    def _realize(self, aperture: float, base: float, phase: str) -> float:
        config = self.config
        if phase in ("approach", "hold"):
            acceleration = config.approach_max_acceleration
            max_velocity = config.approach_max_velocity
            target = config.target_aperture
            if phase == "approach" and config.approach_aperture is not None:
                target = config.approach_aperture
            goal = min(target, base, aperture)
        else:
            acceleration = config.release_max_acceleration
            max_velocity = config.release_max_velocity
            goal = base

        distance = goal - aperture
        desired_velocity = math.copysign(_stopping_speed(abs(distance), acceleration), distance)
        if self._closing_frames and config.closure_ramp_frames is not None:
            # Carry one quintic reference through approach and hold. Braking
            # still uses the final contact goal, so the moving reference
            # does not make the lips stop at an intermediate aperture.
            progress = min(self._closing_frames / config.closure_ramp_frames, 1.0)
            gain = progress**3 * (10.0 + progress * (-15.0 + 6.0 * progress))
            reference = base + gain * (goal - base)
            desired_velocity = max(desired_velocity, min(0.0, reference - aperture))
        elif self._releasing_frames and config.release_ramp_frames is not None:
            # Ease toward the live baseline from the last closing pose.
            # Only request motion in the direction of the baseline.
            progress = min(self._releasing_frames / config.release_ramp_frames, 1.0)
            gain = progress**2 * (3.0 - 2.0 * progress)
            reference = self._release_start + gain * (base - self._release_start)
            desired_velocity = _clamp(
                reference - aperture, min(0.0, desired_velocity), max(0.0, desired_velocity)
            )
        # Reserve enough braking distance at the physical bounds even if the
        # next phase has a smaller acceleration limit.
        braking = min(config.approach_max_acceleration, config.release_max_acceleration)
        min_velocity = -min(max_velocity, _stopping_speed(aperture, braking))
        max_velocity = min(max_velocity, _stopping_speed(1.0 - aperture, braking))
        velocity = _clamp(desired_velocity, min_velocity, max_velocity)
        velocity = _clamp(velocity, self._velocity - acceleration, self._velocity + acceleration)
        if velocity == distance:
            return goal
        return _clamp(aperture + velocity, 0.0, 1.0)


class LipCorrection:
    """Frozen phase head and motion settings shared by independent streams."""

    def __init__(
        self,
        weights: list[list[float]],
        bias: list[float],
        classes: list[str],
        motion: LipClosureConfig,
    ) -> None:
        self.weights = np.array(weights, dtype=np.float32)
        self.bias = np.array(bias, dtype=np.float32)
        self.classes = np.array(classes, dtype=str)
        self.motion = motion
        if (
            self.weights.ndim != 2
            or self.weights.shape[0] != 4
            or not self.weights.shape[1]
            or self.bias.shape != (4,)
            or self.classes.shape != (4,)
            or set(self.classes) != LIP_PHASES
            or not np.isfinite(self.weights).all()
            or not np.isfinite(self.bias).all()
        ):
            raise ValueError("Invalid four-phase lip correction head")
        for values in (self.weights, self.bias, self.classes):
            values.setflags(write=False)

    @classmethod
    def load(
        cls,
        path: str | Path,
        contract: StreamingContract,
        *,
        contentvec_sha256: str,
    ) -> LipCorrection:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        if payload["format_version"] != "streaming_lip_correction_v1":
            raise ValueError("Unsupported lip correction format")
        actual_clock = {
            key: getattr(contract, key)
            for key in (
                "sample_rate_hz",
                "frame_rate_hz",
                "window_samples",
                "hop_samples",
                "lookahead_samples",
                "contentvec_stride_samples",
                "contentvec_receptive_field_samples",
                "feature_width",
            )
        }
        if payload["contract"] != actual_clock or payload["contentvec_sha256"] != contentvec_sha256:
            raise ValueError(
                "Lip correction requires the original streaming contract and ContentVec encoder"
            )
        correction = cls(**payload["head"], motion=LipClosureConfig(**payload["motion"]))
        correction.validate_width(contract.feature_width)
        return correction

    def validate_width(self, feature_width: int) -> None:
        if self.weights.shape[1] != feature_width:
            raise ValueError("Lip correction feature width does not match the streaming contract")

    def predict_phases(self, features: np.ndarray) -> np.ndarray:
        features = np.asarray(features, dtype=np.float32)
        if (
            features.ndim != 2
            or features.shape[1] != self.weights.shape[1]
            or not np.isfinite(features).all()
        ):
            raise ValueError("Invalid features for lip correction")
        return cast(
            np.ndarray, self.classes[np.argmax(features @ self.weights.T + self.bias, axis=1)]
        )

    def new_stream(self) -> LipCorrectionStream:
        return LipCorrectionStream(self)


class LipCorrectionStream:
    """Apply the phase head and controller once per emitted frame."""

    def __init__(self, correction: LipCorrection) -> None:
        self.correction = correction
        self.controller = LipClosureController(correction.motion)

    def apply(self, features: np.ndarray, trajectory: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        values = np.asarray(trajectory)
        if (
            values.shape != (len(features), len(NINE_CHANNELS))
            or not np.issubdtype(values.dtype, np.floating)
            or not np.isfinite(values).all()
        ):
            raise ValueError("Lip correction needs aligned, finite nine-channel frames")
        phases = self.correction.predict_phases(features)
        output = values.copy()
        aperture = NINE_CHANNELS.index("LA")
        output[:, aperture] = [
            self.controller.step(aperture_value, phase)
            for aperture_value, phase in zip(
                np.clip(values[:, aperture], 0, 1), phases, strict=True
            )
        ]
        return output, phases
