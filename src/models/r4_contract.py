"""R4 release sample clock (CC BY-NC 4.0; see docs/r4-LICENSE.txt)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import numpy as np
import yaml

STREAMING_CONTRACT_VERSION = "nine_channel_streaming_v1"
NINE_CHANNELS = ("LP", "LA", "TTCL", "TTCD", "TBCL", "TBCD", "VEL", "GLO", "LAT")


@dataclass(frozen=True)
class StreamingContract:
    """Static timing and shape constraints shared by every streaming backend."""

    sample_rate_hz: int
    frame_rate_hz: int
    hop_samples: int
    window_samples: int
    lookahead_samples: int
    contentvec_stride_samples: int
    contentvec_receptive_field_samples: int
    feature_width: int
    channels: tuple[str, ...] = NINE_CHANNELS
    version: str = STREAMING_CONTRACT_VERSION

    def __post_init__(self) -> None:
        if self.version != STREAMING_CONTRACT_VERSION:
            raise ValueError(f"unsupported streaming contract version: {self.version!r}")
        positive = {
            "sample_rate_hz": self.sample_rate_hz,
            "frame_rate_hz": self.frame_rate_hz,
            "hop_samples": self.hop_samples,
            "window_samples": self.window_samples,
            "lookahead_samples": self.lookahead_samples,
            "contentvec_stride_samples": self.contentvec_stride_samples,
            "contentvec_receptive_field_samples": self.contentvec_receptive_field_samples,
            "feature_width": self.feature_width,
        }
        if any(int(value) <= 0 for value in positive.values()):
            raise ValueError(f"streaming contract values must be positive: {positive}")
        if self.sample_rate_hz % self.frame_rate_hz:
            raise ValueError("sample rate must divide exactly into trajectory frame rate")
        if self.hop_samples % self.samples_per_frame:
            raise ValueError("hop_samples must contain an integer number of trajectory frames")
        if self.lookahead_samples % self.samples_per_frame:
            raise ValueError(
                "lookahead_samples must contain an integer number of trajectory frames"
            )
        if self.window_samples % self.hop_samples:
            raise ValueError("window_samples must be an integer number of hops")
        if self.window_samples < self.hop_samples + self.lookahead_samples:
            raise ValueError("window is too short to contain one working hop and lookahead")
        if self.contentvec_stride_samples != self.samples_per_frame:
            raise ValueError("ContentVec stride must equal the canonical trajectory frame size")
        if self.feature_frames <= self.emitted_frames + self.lookahead_frames:
            raise ValueError("ContentVec window does not contain a committed interior slice")
        if tuple(self.channels) != NINE_CHANNELS:
            raise ValueError(f"unexpected nine-channel contract: {tuple(self.channels)!r}")

    @property
    def samples_per_frame(self) -> int:
        return self.sample_rate_hz // self.frame_rate_hz

    @property
    def emitted_frames(self) -> int:
        return self.hop_samples // self.samples_per_frame

    @property
    def lookahead_frames(self) -> int:
        return self.lookahead_samples // self.samples_per_frame

    @property
    def feature_frames(self) -> int:
        """Expected HuBERT/ContentVec frame count for a fixed waveform window."""

        usable = self.window_samples - self.contentvec_receptive_field_samples
        return 1 + usable // self.contentvec_stride_samples

    @property
    def committed_slice(self) -> slice:
        end = self.feature_frames - self.lookahead_frames
        return slice(end - self.emitted_frames, end)

    @property
    def first_emit_after_samples(self) -> int:
        return self.hop_samples + self.lookahead_samples

    def validate_prediction_shape(self, values: np.ndarray) -> None:
        array = np.asarray(values)
        expected = (self.feature_frames, len(self.channels))
        if array.shape != expected:
            raise ValueError(f"expected trajectory shape {expected}, got {array.shape}")
        if not np.isfinite(array).all():
            raise ValueError("trajectory contains non-finite values")

    def committed_frame_center_samples(self, received_samples: int) -> np.ndarray:
        """Return absolute sample centers for the next committed five-frame packet."""

        if received_samples < self.first_emit_after_samples:
            raise ValueError(
                f"need {self.first_emit_after_samples} received samples before emission, "
                f"got {received_samples}"
            )
        start = received_samples - self.lookahead_samples - self.hop_samples
        offsets = (np.arange(self.emitted_frames, dtype=np.int64) * self.samples_per_frame) + (
            self.samples_per_frame // 2
        )
        return start + offsets

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "StreamingContract":
        if payload.get("version") != STREAMING_CONTRACT_VERSION:
            raise ValueError(f"unsupported streaming config version: {payload.get('version')!r}")
        audio = payload.get("audio", {})
        temporal = payload.get("temporal", {})
        model = payload.get("model", {})
        return cls(
            version=str(payload["version"]),
            sample_rate_hz=int(audio["sample_rate_hz"]),
            frame_rate_hz=int(temporal["frame_rate_hz"]),
            hop_samples=int(temporal["hop_samples"]),
            window_samples=int(temporal["window_samples"]),
            lookahead_samples=int(temporal["lookahead_samples"]),
            contentvec_stride_samples=int(temporal["contentvec_stride_samples"]),
            contentvec_receptive_field_samples=int(temporal["contentvec_receptive_field_samples"]),
            feature_width=int(model["feature_width"]),
            channels=tuple(str(name) for name in model["channels"]),
        )


def load_streaming_contract(path: str | Path) -> StreamingContract:
    """Load and validate one versioned streaming YAML contract."""

    source = Path(path)
    payload = yaml.safe_load(source.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError(f"streaming config must be a mapping: {source}")
    return StreamingContract.from_mapping(payload)
