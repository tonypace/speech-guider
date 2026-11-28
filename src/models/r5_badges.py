"""Pure-JSON Stage 5 realization badge scorer for R5 articulatory + bypass spans."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import numpy as np

R5_CHANNELS_11: tuple[str, ...] = (
    "LP",
    "LA",
    "TTCL",
    "TTCD",
    "TBCL",
    "TBCD",
    "VEL",
    "GLO",
    "LAT",
    "BLCL",
    "BLCD",
)


@dataclass(frozen=True)
class BadgeEvaluation:
    """Result of evaluating one R5 Stage 5 realization badge on an aligned span."""

    badge_id: str
    probability: float
    status: str  # "pass" | "watch" | "flag" | "sealed_unreleased"
    oral_seal_min: float
    oral_seal_reached: bool
    realization_label: str | None = None


def _sigmoid(x: float) -> float:
    if x >= 0:
        return 1.0 / (1.0 + math.exp(-x))
    exp_x = math.exp(x)
    return exp_x / (1.0 + exp_x)


def _softmax(logits: np.ndarray) -> np.ndarray:
    shifted = logits - np.max(logits)
    exps = np.exp(shifted)
    return np.asarray(exps / np.sum(exps), dtype=np.float64)


def _spec_tilt_from_mel(mel_frames: np.ndarray) -> float:
    """Estimate spectral tilt slope across the 40 log-mel bands."""
    if mel_frames.size == 0:
        return 0.0
    mean_mel = np.mean(mel_frames, axis=0)
    idx = np.arange(mean_mel.shape[0], dtype=np.float64)
    idx_centered = idx - np.mean(idx)
    denom = float(np.dot(idx_centered, idx_centered))
    if denom <= 0.0:
        return 0.0
    return float(np.dot(idx_centered, mean_mel - np.mean(mean_mel)) / denom)


def extract_stage5_features(
    tvs_11ch: np.ndarray,
    bypass_43d: np.ndarray,
    start_frame: int,
    end_frame: int,
    *,
    frame_rate_hz: int = 50,
    post_frames: int = 3,
) -> dict[str, float]:
    """Extract the 75 Stage 5 summary features over an aligned frame span."""
    total_frames = min(len(tvs_11ch), len(bypass_43d))
    if total_frames == 0:
        raise ValueError("Trajectory must not be empty")
    s = max(0, min(start_frame, total_frames - 1))
    e = max(s + 1, min(end_frame, total_frames))
    core_tv = np.asarray(tvs_11ch[s:e], dtype=np.float64)
    core_byp = np.asarray(bypass_43d[s:e], dtype=np.float64)

    post_start = min(e, total_frames - 1)
    post_end = min(total_frames, e + max(1, post_frames))
    if post_end <= post_start:
        post_tv = core_tv[-1:]
        post_byp = core_byp[-1:]
    else:
        post_tv = np.asarray(tvs_11ch[post_start:post_end], dtype=np.float64)
        post_byp = np.asarray(bypass_43d[post_start:post_end], dtype=np.float64)

    n_frames = float(e - s)
    dur_ms = (n_frames / float(frame_rate_hz)) * 1000.0
    feats: dict[str, float] = {
        "dur_ms": dur_ms,
        "n_frames": n_frames,
    }

    channel_means: dict[str, float] = {}
    for idx, ch in enumerate(R5_CHANNELS_11):
        col = core_tv[:, idx]
        col_mean = float(np.mean(col))
        post_mean = float(np.mean(post_tv[:, idx]))
        channel_means[ch] = col_mean
        feats[f"{ch}_min"] = float(np.min(col))
        feats[f"{ch}_mean"] = col_mean
        feats[f"{ch}_p10"] = float(np.percentile(col, 10))
        feats[f"{ch}_p90"] = float(np.percentile(col, 90))
        feats[f"{ch}_post_delta"] = post_mean - col_mean

    feats["blade_minus_tbcd"] = channel_means["BLCD"] - channel_means["TBCD"]
    feats["tip_minus_blcd"] = channel_means["TTCD"] - channel_means["BLCD"]
    feats["blcl_minus_tbcl"] = channel_means["BLCL"] - channel_means["TBCL"]
    feats["ttcl_minus_blcl"] = channel_means["TTCL"] - channel_means["BLCL"]

    # 43-d bypass layout: 0..39 log-mel (40), 40 log_rms, 41 hf_fric ratio, 42 zcr
    log_rms = core_byp[:, 40]
    post_log_rms = post_byp[:, 40]
    hf_fric = core_byp[:, 41]
    post_hf_fric = post_byp[:, 41]
    zcr = core_byp[:, 42]
    post_zcr = post_byp[:, 42]
    hf_mel = core_byp[:, 30:40]
    post_hf_mel = post_byp[:, 30:40]

    log_rms_mean = float(np.mean(log_rms))
    post_log_rms_max = float(np.max(post_log_rms))
    feats["log_rms_mean"] = log_rms_mean
    feats["log_rms_min"] = float(np.min(log_rms))
    feats["log_rms_max"] = float(np.max(log_rms))
    feats["post_log_rms_max"] = post_log_rms_max
    feats["post_burst_rms_jump"] = post_log_rms_max - log_rms_mean
    feats["hf_fric_mean"] = float(np.mean(hf_fric))
    feats["hf_fric_max"] = float(np.max(hf_fric))
    feats["post_hf_fric_max"] = float(np.max(post_hf_fric))
    feats["zcr_mean"] = float(np.mean(zcr))
    feats["post_zcr_max"] = float(np.max(post_zcr))
    feats["spec_tilt_core"] = _spec_tilt_from_mel(core_byp[:, :40])
    feats["spec_tilt_post"] = _spec_tilt_from_mel(post_byp[:, :40])
    feats["hf_mel_mean"] = float(np.mean(hf_mel))
    feats["post_hf_mel_max"] = float(np.max(post_hf_mel))
    return feats


class R5Stage5Badges:
    """Pure-JSON scorer for `weights/realization_badges_v1.json`."""

    def __init__(self, payload: dict[str, Any]) -> None:
        if payload.get("format_version") != "r5_stage5_realization_badges_v1":
            raise ValueError(f"Unsupported R5 badge format: {payload.get('format_version')}")
        self.payload = payload
        self.badges: dict[str, dict[str, Any]] = payload.get("badges", {})
        self.realization_head: dict[str, Any] = payload.get("realization_head", {})

    @classmethod
    def from_file(cls, path: Path) -> "R5Stage5Badges":
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls(data)

    def _vectorize(self, feature_dict: dict[str, float], spec: dict[str, Any]) -> np.ndarray:
        names: list[str] = spec["feature_names"]
        raw = np.array([feature_dict[name] for name in names], dtype=np.float64)
        mean = np.asarray(spec["scaler_mean"], dtype=np.float64)
        scale = np.where(
            np.asarray(spec["scaler_scale"], dtype=np.float64) == 0.0,
            1.0,
            np.asarray(spec["scaler_scale"], dtype=np.float64),
        )
        return cast(np.ndarray, (raw - mean) / scale)

    def predict_realization_label(self, feature_dict: dict[str, float]) -> str | None:
        head = self.realization_head
        if not head or not head.get("classes"):
            return None
        x = self._vectorize(feature_dict, head)
        weights = np.asarray(head["weights"], dtype=np.float64)
        bias = np.asarray(head["bias"], dtype=np.float64)
        logits = weights @ x + bias
        probs = _softmax(logits)
        best_idx = int(np.argmax(probs))
        tau_abstain = float(head.get("tau_abstain", 0.0))
        if float(probs[best_idx]) < tau_abstain:
            return None
        return str(head["classes"][best_idx])

    def evaluate_badge(
        self,
        badge_id: str,
        tvs_11ch: np.ndarray,
        bypass_43d: np.ndarray,
        start_frame: int,
        end_frame: int,
        *,
        target_phone: str | None = None,
    ) -> BadgeEvaluation:
        if badge_id not in self.badges:
            raise KeyError(f"Unknown Stage 5 badge: {badge_id}")
        spec = self.badges[badge_id]
        feats = extract_stage5_features(tvs_11ch, bypass_43d, start_frame, end_frame)
        x = self._vectorize(feats, spec)
        weights = np.asarray(spec["weights"], dtype=np.float64)
        bias = float(spec["bias"])
        prob = _sigmoid(float(np.dot(weights, x) + bias))

        if target_phone == "p":
            seal_min = feats["LA_min"]
        elif target_phone in {"k", "g", "ŋ"}:
            seal_min = feats["TBCD_min"]
        else:
            seal_min = min(feats["LA_min"], feats["TTCD_min"], feats["TBCD_min"])

        oral_seal_thresh = float(spec.get("oral_seal_thresh", 0.1))
        tau_seal_pass = float(spec.get("tau_seal_pass", 0.72))
        tau_pass = float(spec.get("tau_pass", 0.23))
        tau_flag = float(spec.get("tau_flag", 0.85))
        seal_reached = seal_min <= oral_seal_thresh
        realization_label = self.predict_realization_label(feats)

        # Stage 5 policy: unreleased oral closures (/k̚, p̚/) credit cleanly when seal is reached.
        if seal_reached and prob <= tau_seal_pass:
            status = "sealed_unreleased" if prob > tau_pass else "pass"
        elif prob >= tau_flag:
            status = "flag"
        elif prob <= tau_pass:
            status = "pass"
        else:
            status = "watch"

        return BadgeEvaluation(
            badge_id=badge_id,
            probability=prob,
            status=status,
            oral_seal_min=seal_min,
            oral_seal_reached=seal_reached,
            realization_label=realization_label,
        )
