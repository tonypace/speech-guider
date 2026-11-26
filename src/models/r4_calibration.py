"""Conditional causal output calibration for streaming R4/Model-A trajectories.

Calibration math follows the final reference bundle (CC BY-NC 4.0).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import numpy as np

from src.models.r4_contract import NINE_CHANNELS, StreamingContract

FORMAT = "streaming_output_calibration_v1"

SAMPLE_RATE = 16_000
FRAME = 320
ONSETS_AHEAD = 4

LP_CHANNEL = NINE_CHANNELS.index("LP")
LA_CHANNEL = NINE_CHANNELS.index("LA")
TTCL_CHANNEL = NINE_CHANNELS.index("TTCL")
TTCD_CHANNEL = NINE_CHANNELS.index("TTCD")
TBCL_CHANNEL = NINE_CHANNELS.index("TBCL")
TBCD_CHANNEL = NINE_CHANNELS.index("TBCD")
VEL_CHANNEL = NINE_CHANNELS.index("VEL")
GLO_CHANNEL = NINE_CHANNELS.index("GLO")
LAT_CHANNEL = NINE_CHANNELS.index("LAT")

_FREQ_EDGES = (0.0, 150.0, 300.0, 600.0, 1200.0, 2400.0, 4000.0, 6000.0, 8000.1)
_HANNING_2FRAME = np.hanning(2 * FRAME)
_FREQUENCIES = np.fft.rfftfreq(2 * FRAME, 1.0 / SAMPLE_RATE)
_BAND_MASKS = tuple(
    (_FREQUENCIES >= lo) & (_FREQUENCIES < hi) for lo, hi in zip(_FREQ_EDGES[:-1], _FREQ_EDGES[1:])
)


@dataclass(frozen=True)
class CurveCalibrationParams:
    """Bounded monotonic tanh-expansion parameters around neutral pivot ``p0``."""

    p0: float
    g: float
    span: float

    def __post_init__(self) -> None:
        if not (np.isfinite(self.p0) and 0.0 <= float(self.p0) <= 1.0):
            raise ValueError(f"pivot p0 must be finite and in [0, 1], got {self.p0!r}")
        if not (np.isfinite(self.g) and float(self.g) > 0.0):
            raise ValueError(f"gain g must be finite and > 0, got {self.g!r}")
        if not (np.isfinite(self.span) and float(self.span) > 0.0):
            raise ValueError(f"span must be finite and > 0, got {self.span!r}")

    def to_dict(self) -> dict[str, float]:
        return {"p0": float(self.p0), "g": float(self.g), "span": float(self.span)}

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> CurveCalibrationParams:
        if not isinstance(payload, Mapping):
            raise ValueError("Channel calibration config must be a mapping")
        for key in ("p0", "g", "span"):
            if key not in payload:
                raise ValueError(f"Channel calibration missing required key {key!r}")
        return cls(p0=float(payload["p0"]), g=float(payload["g"]), span=float(payload["span"]))


@dataclass(frozen=True)
class TipCalibrationParams(CurveCalibrationParams):
    """TTCL calibration parameters including TTCD-based tip activity gating."""

    cd_lo: float = 0.20
    cd_hi: float = 0.65
    w_open: float = 0.20

    def __post_init__(self) -> None:
        super().__post_init__()
        if not (np.isfinite(self.cd_lo) and np.isfinite(self.cd_hi)):
            raise ValueError("cd_lo and cd_hi must be finite")
        if not (0.0 <= float(self.cd_lo) < float(self.cd_hi) <= 1.0):
            raise ValueError(
                f"must satisfy 0 <= cd_lo < cd_hi <= 1, got ({self.cd_lo}, {self.cd_hi})"
            )
        if not (np.isfinite(self.w_open) and 0.0 <= float(self.w_open) <= 1.0):
            raise ValueError(f"w_open must be finite and in [0, 1], got {self.w_open!r}")

    def to_dict(self) -> dict[str, float]:
        base = super().to_dict()
        base.update(
            {
                "cd_lo": float(self.cd_lo),
                "cd_hi": float(self.cd_hi),
                "w_open": float(self.w_open),
            }
        )
        return base

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> TipCalibrationParams:
        base = CurveCalibrationParams.from_mapping(payload)
        for key in ("cd_lo", "cd_hi", "w_open"):
            if key not in payload:
                raise ValueError(f"TTCL calibration missing required key {key!r}")
        return cls(
            p0=base.p0,
            g=base.g,
            span=base.span,
            cd_lo=float(payload["cd_lo"]),
            cd_hi=float(payload["cd_hi"]),
            w_open=float(payload["w_open"]),
        )


def _silence_gate(
    activity: np.ndarray,
    thresholds: list[float] | np.ndarray,
    durations: list[int] | np.ndarray,
    *,
    isolated_noise_frames: int = 0,
) -> np.ndarray:
    """Causal silence core mask requiring past inactivity and no onset within ONSETS_AHEAD."""
    scores = np.asarray(activity, dtype=np.float64)
    n = len(scores)
    if n == 0:
        return np.zeros((len(thresholds), 0), dtype=bool)
    thresh_arr = np.asarray(thresholds, dtype=np.float64)[:, None]
    dur_arr = np.asarray(durations, dtype=np.int64)[:, None]
    quiet = scores[None, :] < thresh_arr
    positions = np.arange(n, dtype=np.int64)
    age = positions - np.maximum.accumulate(np.where(quiet, -1, positions), axis=1)
    future = np.full(n, -np.inf, dtype=np.float64)
    for offset in range(1, ONSETS_AHEAD + 1):
        if offset < n:
            future[:-offset] = np.maximum(future[:-offset], scores[offset:])
    qualified = age >= dur_arr
    if isolated_noise_frames:
        window_end = positions + 1
        window_start = window_end - dur_arr
        noisy = ~quiet
        cumulative_noise = np.pad(np.cumsum(noisy, axis=1), ((0, 0), (1, 0)))
        noisy_neighbors = noisy & np.pad(noisy[:, :-1], ((0, 0), (1, 0)))
        cumulative_neighbors = np.pad(np.cumsum(noisy_neighbors, axis=1), ((0, 0), (1, 0)))
        prior_noise: np.ndarray = cumulative_noise[:, window_end] - np.take_along_axis(
            cumulative_noise, np.maximum(window_start, 0), axis=1
        )
        adjacent_noise: np.ndarray = cumulative_neighbors[:, window_end] - np.take_along_axis(
            cumulative_neighbors, np.maximum(window_start + 1, 0), axis=1
        )
        qualified = (
            (window_start >= 0)
            & (age >= 5)
            & (prior_noise <= isolated_noise_frames)
            & (adjacent_noise == 0)
        )
    return np.asarray(qualified & (future[None, :] < thresh_arr), dtype=bool)


def _validate_silence_contract(contract: StreamingContract, ramp_frames: int) -> None:
    if (contract.sample_rate_hz, contract.samples_per_frame) != (SAMPLE_RATE, FRAME):
        raise ValueError("Causal speech weights require a 16 kHz / 320-sample (50 Hz) contract")
    if ONSETS_AHEAD > contract.lookahead_frames:
        raise ValueError(
            f"ONSETS_AHEAD={ONSETS_AHEAD} exceeds contract lookahead_frames={contract.lookahead_frames}"
        )
    if int(ramp_frames) < 0:
        raise ValueError(f"ramp_frames must be >= 0, got {ramp_frames}")


def _eligible_silence_mask(
    probability: np.ndarray,
    rms: np.ndarray,
    gates: Mapping[str, Mapping[str, Any]],
    allowance: Mapping[str, int],
) -> np.ndarray:
    eligible = np.zeros(len(rms), dtype=bool)
    for scores, name in ((probability, "speech_probability"), (rms, "rms_dbfs")):
        if name not in gates:
            raise ValueError(f"Missing silence gate config for {name!r}")
        gate = gates[name]
        core = _silence_gate(
            scores,
            [float(gate["threshold"])],
            [int(gate["inactivity_frames"])],
            isolated_noise_frames=int(allowance.get(name, 0)),
        )
        eligible |= core[0]
    return eligible


class CausalSpeechWeightTracker:
    """Streaming hop-by-hop tracker producing causal speech_weight in [0.0, 1.0]."""

    def __init__(
        self,
        classifier: Any,
        gates: Mapping[str, Mapping[str, Any]],
        contract: StreamingContract,
        *,
        allowance: Mapping[str, int] | None = None,
        ramp_frames: int = 4,
    ) -> None:
        _validate_silence_contract(contract, ramp_frames)
        self.classifier = classifier
        self.gates = gates
        self.contract = contract
        self.allowance = dict(allowance) if allowance is not None else {}
        self.ramp_frames = int(ramp_frames)

        self._sample_buffer = np.empty((0,), dtype=np.float32)
        self._received_samples = 0
        self._emitted_frames = 0
        self._prev_block = np.zeros(FRAME, dtype=np.float32)
        self._prev_spectrum: np.ndarray | None = None
        self._log_bands_hist: np.ndarray | None = None
        self._rms_hist: list[np.ndarray] = []
        self._prob_hist: list[np.ndarray] = []
        self._phase: float | None = None

    def append_hop(self, samples: np.ndarray) -> np.ndarray | None:
        """Append one audio hop and return speech weights once lookahead exists."""
        hop = np.asarray(samples, dtype=np.float32)
        if hop.ndim != 1 or hop.shape[0] != self.contract.hop_samples:
            raise ValueError(
                f"expected one mono hop of {self.contract.hop_samples} samples, got {hop.shape}"
            )
        if not np.isfinite(hop).all():
            raise ValueError("audio hop contains non-finite values")
        self._received_samples += len(hop)
        self._sample_buffer = np.concatenate((self._sample_buffer, hop))

        n_blocks = len(self._sample_buffer) // FRAME
        if n_blocks > 0:
            consumed = n_blocks * FRAME
            blocks = self._sample_buffer[:consumed].reshape(n_blocks, FRAME)
            self._sample_buffer = self._sample_buffer[consumed:]
            self._ingest_blocks(blocks)

        if self._received_samples < self.contract.first_emit_after_samples:
            return None

        start = self._emitted_frames
        end = start + self.contract.emitted_frames
        rms_arr = np.concatenate(self._rms_hist)
        prob_arr = np.concatenate(self._prob_hist)
        eligible = _eligible_silence_mask(prob_arr, rms_arr, self.gates, self.allowance)
        packet_mask = eligible[start:end]
        self._emitted_frames = end
        return self._step_weights(packet_mask)

    def _ingest_blocks(self, blocks: np.ndarray) -> None:
        count = len(blocks)
        rms = 10.0 * np.log10(np.maximum(np.mean(blocks**2, axis=1), 1e-16))
        joined = np.concatenate((self._prev_block, blocks.ravel()))
        windows = np.lib.stride_tricks.sliding_window_view(joined, 2 * FRAME)[::FRAME][:count]
        self._prev_block = blocks[-1].copy()

        power = np.abs(np.fft.rfft(windows * _HANNING_2FRAME)) ** 2
        bands = np.stack([np.mean(power[:, mask], axis=1) for mask in _BAND_MASKS], axis=1)
        log_bands = 10.0 * np.log10(np.maximum(bands, 1e-12))
        spectrum = power / np.maximum(power.sum(axis=1, keepdims=True), 1e-12)
        prev_spec = spectrum[:1] if self._prev_spectrum is None else self._prev_spectrum[None, :]
        flux = np.abs(np.diff(spectrum, axis=0, prepend=prev_spec)).sum(axis=1)
        self._prev_spectrum = spectrum[-1].copy()

        if self._log_bands_hist is None:
            hist = np.repeat(log_bands[:1], 4, axis=0)
        else:
            hist = self._log_bands_hist
        padded_lb = np.concatenate((hist, log_bands), axis=0)
        baseline = sum(padded_lb[offset : offset + count] for offset in range(4)) / 4.0
        self._log_bands_hist = padded_lb[-4:].copy()

        features = np.column_stack((rms, log_bands, log_bands - baseline, flux)).astype(np.float32)
        prob = np.asarray(self.classifier.predict_proba(features)[:, 1], dtype=np.float64)
        self._rms_hist.append(rms.astype(np.float64))
        self._prob_hist.append(prob)

    def _step_weights(self, packet_mask: np.ndarray) -> np.ndarray:
        if self.ramp_frames == 0:
            return np.asarray(~packet_mask, dtype=np.float32)
        step = 1.0 / float(self.ramp_frames)
        out = np.empty(len(packet_mask), dtype=np.float64)
        for idx, is_silent in enumerate(packet_mask):
            if self._phase is None:
                self._phase = 0.0 if is_silent else 1.0
            if is_silent:
                self._phase = max(0.0, self._phase - step)
            else:
                self._phase = min(1.0, self._phase + step)
            out[idx] = 0.5 * (1.0 - np.cos(np.pi * self._phase))
        return np.asarray(out, dtype=np.float32)


def _extract_channel_configs(
    config: OutputCalibrator | Mapping[str, Any],
) -> tuple[TipCalibrationParams, CurveCalibrationParams, CurveCalibrationParams]:
    if isinstance(config, OutputCalibrator):
        return config.ttcl, config.tbcl, config.lp
    if not isinstance(config, Mapping):
        raise ValueError("Calibration config must be an OutputCalibrator or mapping")
    if "format" in config and config["format"] != FORMAT:
        raise ValueError(f"Unsupported output calibration format: {config['format']!r}")
    channels = config["channels"] if "channels" in config else config
    if not isinstance(channels, Mapping):
        raise ValueError("Calibration config 'channels' must be a mapping")
    for required in ("TTCL", "TBCL", "LP"):
        if required not in channels:
            raise ValueError(f"Calibration config missing channel {required!r}")
    return (
        TipCalibrationParams.from_mapping(channels["TTCL"]),
        CurveCalibrationParams.from_mapping(channels["TBCL"]),
        CurveCalibrationParams.from_mapping(channels["LP"]),
    )


def _expand_around_pivot(
    x: np.ndarray, params: CurveCalibrationParams, weight: np.ndarray
) -> np.ndarray:
    centered = x - params.p0
    delta = params.span * np.tanh((params.g * centered) / params.span)
    calibrated = np.clip(params.p0 + weight * delta + (1.0 - weight) * centered, 0.0, 1.0)
    # Preserve exact identity whenever weight == 0 (for valid [0, 1] inputs).
    return np.asarray(
        np.where(
            weight == 0.0, np.where((x >= 0.0) & (x <= 1.0), x, np.clip(x, 0.0, 1.0)), calibrated
        ),
        dtype=np.float64,
    )


def apply_conditional_calibration(
    trajectory: np.ndarray,
    config: OutputCalibrator | Mapping[str, Any],
    *,
    speech_weight: np.ndarray | float | None = None,
) -> np.ndarray:
    """Apply bounded conditional calibration to TTCL, TBCL, and LP.

    Pure function: never mutates ``trajectory``, preserves ``dtype`` and shape
    ``(T, 9)``, and leaves LA, TTCD, TBCD, VEL, GLO, and LAT bitwise identical.
    """
    values = np.asarray(trajectory)
    if (
        values.ndim != 2
        or values.shape[1] != len(NINE_CHANNELS)
        or not np.issubdtype(values.dtype, np.floating)
    ):
        raise ValueError(
            f"Expected float trajectory of shape (T, {len(NINE_CHANNELS)}), got {values.shape}"
        )
    if not np.isfinite(values).all():
        raise ValueError("Trajectory contains non-finite values")

    ttcl_cfg, tbcl_cfg, lp_cfg = _extract_channel_configs(config)
    n_frames = len(values)
    if speech_weight is None:
        sw = np.ones(n_frames, dtype=np.float64)
    else:
        sw_arr = np.asarray(speech_weight, dtype=np.float64)
        if sw_arr.ndim == 0:
            sw = np.full(n_frames, float(sw_arr), dtype=np.float64)
        elif sw_arr.shape == (n_frames,):
            sw = sw_arr
        else:
            raise ValueError(
                f"speech_weight must be scalar or shape ({n_frames},), got {sw_arr.shape}"
            )
        if not np.isfinite(sw).all() or np.any(sw < 0.0) or np.any(sw > 1.0):
            raise ValueError("speech_weight must be finite and within [0.0, 1.0]")

    out = values.copy()
    if n_frames == 0:
        return out

    ttcd = values[:, TTCD_CHANNEL].astype(np.float64)
    u = np.clip((ttcd - ttcl_cfg.cd_lo) / (ttcl_cfg.cd_hi - ttcl_cfg.cd_lo), 0.0, 1.0)
    tip_activity = 1.0 - (u * u * (3.0 - 2.0 * u))
    w_ttcl = sw * (ttcl_cfg.w_open + (1.0 - ttcl_cfg.w_open) * tip_activity)

    out[:, TTCL_CHANNEL] = _expand_around_pivot(
        values[:, TTCL_CHANNEL].astype(np.float64), ttcl_cfg, w_ttcl
    ).astype(values.dtype)
    out[:, TBCL_CHANNEL] = _expand_around_pivot(
        values[:, TBCL_CHANNEL].astype(np.float64), tbcl_cfg, sw
    ).astype(values.dtype)
    out[:, LP_CHANNEL] = _expand_around_pivot(
        values[:, LP_CHANNEL].astype(np.float64), lp_cfg, sw
    ).astype(values.dtype)
    return out


class OutputCalibrator:
    """Versioned conditional output calibrator for TTCL, TBCL, and LP."""

    def __init__(
        self,
        *,
        ttcl: TipCalibrationParams,
        tbcl: CurveCalibrationParams,
        lp: CurveCalibrationParams,
        metadata: Mapping[str, Any] | None = None,
    ) -> None:
        self.ttcl = ttcl
        self.tbcl = tbcl
        self.lp = lp
        self.metadata = dict(metadata) if metadata is not None else {}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> OutputCalibrator:
        if not isinstance(payload, Mapping):
            raise ValueError("Calibration payload must be a JSON object")
        if payload.get("format") != FORMAT:
            raise ValueError(f"Unsupported output calibration format: {payload.get('format')!r}")
        ttcl, tbcl, lp = _extract_channel_configs(payload)
        meta = payload.get("metadata")
        if meta is not None and not isinstance(meta, Mapping):
            raise ValueError("Calibration metadata must be a mapping when provided")
        return cls(ttcl=ttcl, tbcl=tbcl, lp=lp, metadata=meta)

    @classmethod
    def load(cls, path: str | Path) -> OutputCalibrator:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls.from_dict(payload)

    def apply(
        self,
        trajectory: np.ndarray,
        speech_weight: np.ndarray | float | None = None,
    ) -> np.ndarray:
        """Apply conditional calibration to one trajectory or committed packet."""
        return apply_conditional_calibration(trajectory, self, speech_weight=speech_weight)
