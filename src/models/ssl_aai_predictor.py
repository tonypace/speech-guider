"""Local ContentVec-L7 + frozen R4 inference for both student and reference audio."""

import logging
from pathlib import Path
from threading import RLock
from typing import Any, cast

import numpy as np
import torch
import yaml
from transformers import AutoFeatureExtractor, AutoModel  # type: ignore[import-untyped]

from src.models.aai_adapter import AAI_TV_ORDER as AAI_TV_ORDER
from src.models.legacy_aai_predictor import AAIHead, DANNPredictorHead  # noqa: F401
from src.models.r4_decoder import R4Decoder, load_r4_decoder
from src.models.ssl_common import (
    DEFAULT_SSL_FEATURE_CONFIG,
    SSLFeatureConfig,
    clear_torch_device_cache,
    get_best_torch_device,
)

logger = logging.getLogger(__name__)
DEFAULT_R4_BUNDLE = Path(__file__).resolve().parents[2] / "external" / "R4 26-11-06"


def _get_default_checkpoint_path() -> Path:
    """Resolve the self-contained R4 successor, never the provenance base path."""
    return DEFAULT_R4_BUNDLE / "weights" / "r4.pt"


class SSLAAIPredictor:
    """Replay uploaded audio through R4's batch-one fixed-window contract.

    Uses 1.2 s windows, 100 ms hops/lookahead, 50 Hz output. Each call owns its
    rolling buffer. Tail silence supplies lookahead and is trimmed from output.
    Raw oral values retain speaker-Z bounds [-0.1, 1.1]; display alone clamps.
    """

    MODEL_NAME = DEFAULT_SSL_FEATURE_CONFIG.model_name
    SAMPLE_RATE = 16000
    FEATURE_DIM = 768
    NUM_TVS = 9
    FRAME_RATE = 50
    HOP_SAMPLES = 1600
    WINDOW_SAMPLES = 19200
    LOOKAHEAD_SAMPLES = 1600
    STRIDE_SAMPLES = 320
    FEATURE_FRAMES = 59
    COMMITTED_SLICE = slice(49, 54)

    def __init__(
        self,
        checkpoint_path: str | Path | None = None,
        device: str | None = None,
        ssl_config: SSLFeatureConfig | None = None,
        bundle_path: str | Path | None = None,
    ) -> None:
        self.bundle_path = Path(bundle_path or DEFAULT_R4_BUNDLE).expanduser().resolve()
        self.checkpoint_path = (
            Path(checkpoint_path or self.bundle_path / "weights" / "r4.pt").expanduser().resolve()
        )
        self.ssl_config = ssl_config or DEFAULT_SSL_FEATURE_CONFIG
        if (
            self.ssl_config.sample_rate != 16000
            or self.ssl_config.target_layer != 7
            or self.ssl_config.feature_dim != 768
            or self.ssl_config.frame_rate != 50
        ):
            raise ValueError("R4 requires 16 kHz, ContentVec-L7 width 768, 50 Hz output")
        self.device = device or get_best_torch_device()
        self._ssl_model: Any = None
        self._feature_extractor: Any = None
        self._predictor_head: R4Decoder | None = None
        self._metadata: dict[str, Any] = {}
        self._loaded = False
        self._warmed_up = False
        self._lock = RLock()

    def load(self, checkpoint_path: str | Path | None = None) -> None:
        """Load only local assets; publish state only after all validation passes."""
        with self._lock:
            path = (
                Path(checkpoint_path).expanduser().resolve()
                if checkpoint_path
                else self.checkpoint_path
            )
            if not path.is_file():
                raise FileNotFoundError(f"R4 checkpoint not found: {path}")
            self._validate_contract()
            encoder_path = self.bundle_path / "weights" / "contentvec"
            if not (encoder_path / "model.safetensors").is_file():
                raise FileNotFoundError(f"R4 local ContentVec weights not found: {encoder_path}")
            decoder, metadata = load_r4_decoder(path, self.device)
            encoder = AutoModel.from_pretrained(encoder_path, local_files_only=True)
            if encoder.config.num_hidden_layers != 7 or encoder.config.hidden_size != 768:
                raise ValueError("R4 local encoder must be truncated to seven layers, width 768")
            processor = AutoFeatureExtractor.from_pretrained(encoder_path, local_files_only=True)
            self._ssl_model = encoder.to(self.device).eval()
            self._feature_extractor = processor
            self._predictor_head = decoder
            self._metadata = metadata
            self.checkpoint_path = path
            self._loaded = True
            self._warmed_up = False
            logger.info("R4 loaded on %s from %s", self.device, path)

    def _validate_contract(self) -> None:
        """Reject bundles whose sample-clock policy differs from this adapter."""
        config_path = self.bundle_path / "configs" / "nine_channel_v12_100ms.yaml"
        config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        expected_temporal = {
            "frame_rate_hz": 50,
            "hop_samples": 1600,
            "window_samples": 19200,
            "lookahead_samples": 1600,
            "contentvec_stride_samples": 320,
            "contentvec_receptive_field_samples": 400,
        }
        if (
            not isinstance(config, dict)
            or config.get("version") != "nine_channel_streaming_v1"
            or config.get("audio", {}).get("sample_rate_hz") != 16000
            or config.get("audio", {}).get("channels") != 1
            or config.get("audio", {}).get("normalization")
            != "huggingface_hubert_zero_mean_unit_variance_v1"
            or config.get("temporal") != expected_temporal
            or config.get("model", {}).get("contentvec_layer") != 7
            or config.get("model", {}).get("feature_width") != 768
            or tuple(config.get("model", {}).get("channels", ())) != AAI_TV_ORDER
            or config.get("policy", {}).get("emit_after_samples") != 3200
            or config.get("policy", {}).get("contact_augmentation") != "disabled"
        ):
            raise ValueError("Unsupported R4 streaming contract")

    def _validate_output(self, output: torch.Tensor) -> None:
        if output.ndim != 2:
            raise ValueError(f"Predictor output must be 2D (T, 9), got {output.shape}")
        if output.shape[1] != 9:
            raise ValueError(f"Predictor output must have 9 channels, got {output.shape[1]}")
        if output.shape[0] == 0:
            raise ValueError("Predictor output has no time frames")
        if not torch.isfinite(output).all():
            raise ValueError("Predictor output contains NaN or Inf values")

    def _predict_window(self, samples: np.ndarray) -> torch.Tensor:
        processed = self._feature_extractor(samples, sampling_rate=16000, return_tensors="pt")
        inputs = {key: value.to(self.device) for key, value in processed.items()}
        features = self._ssl_model(**inputs).last_hidden_state
        if features.shape != (1, self.FEATURE_FRAMES, 768):
            raise ValueError(f"Unexpected R4 encoder feature shape: {tuple(features.shape)}")
        assert self._predictor_head is not None
        prediction = self._predictor_head(features)[0]
        if prediction.shape != (self.FEATURE_FRAMES, 9):
            raise ValueError(f"Unexpected R4 trajectory shape: {tuple(prediction.shape)}")
        self._validate_output(prediction)
        return cast(
            torch.Tensor, prediction[self.COMMITTED_SLICE].detach().to("cpu", dtype=torch.float32)
        )

    def predict_with_metadata(
        self, audio_tensor: torch.Tensor, sample_rate: int = 16000
    ) -> dict[str, Any]:
        """Return raw/display trajectories and sample-clock centers for one clip."""
        with self._lock, torch.inference_mode():
            if not self._loaded:
                raise RuntimeError("Predictor not loaded. Call load() first.")
            if sample_rate != 16000:
                raise ValueError("Audio sample rate must be 16000Hz")
            audio = audio_tensor.detach().to("cpu", dtype=torch.float32)
            if audio.ndim == 2 and audio.shape[0] == 1:
                audio = audio[0]
            if audio.ndim != 1 or audio.numel() == 0:
                raise ValueError("Audio must be one nonempty mono waveform")
            if not torch.isfinite(audio).all():
                raise ValueError("Audio contains NaN or Inf values")
            samples = audio.numpy()
            frame_count = (len(samples) + self.STRIDE_SAMPLES - 1) // self.STRIDE_SAMPLES
            hops = (len(samples) + self.HOP_SAMPLES - 1) // self.HOP_SAMPLES
            # One extra hop supplies future context for the final real audio hop.
            padded = np.pad(samples, (0, (hops + 1) * self.HOP_SAMPLES - len(samples)))
            window = np.zeros(self.WINDOW_SAMPLES, dtype=np.float32)
            packets: list[torch.Tensor] = []
            for hop_index in range(hops + 1):
                offset = hop_index * self.HOP_SAMPLES
                window[: -self.HOP_SAMPLES] = window[self.HOP_SAMPLES :]
                window[-self.HOP_SAMPLES :] = padded[offset : offset + self.HOP_SAMPLES]
                if hop_index >= 1:
                    packets.append(self._predict_window(window))
            raw = torch.cat(packets, dim=0)[:frame_count]
            self._validate_output(raw)
            outside = (raw < 0.0) | (raw > 1.0)
            return {
                "tvs": raw.clamp(0.0, 1.0),
                "tvs_raw": raw,
                "center_samples": torch.arange(frame_count) * self.STRIDE_SAMPLES + 160,
                "metadata": {
                    "decoder": "r4_bounded_v12",
                    "device": self.device,
                    "supra_decoder": "r4_lat_temporal_v12",
                    "layers": [7],
                    "normalization": "speaker_z_normalized",
                    "frame_rate": 50,
                    "lookahead_ms": 100,
                    "contact_augmentation": "disabled",
                    "clip_fraction": float(outside.float().mean().item()),
                    "source_commit": self._metadata.get("git_commit"),
                },
            }

    def predict(self, audio_tensor: torch.Tensor, sample_rate: int = 16000) -> torch.Tensor:
        """Return display-safe (T, 9) output shared by both application paths."""
        return cast(torch.Tensor, self.predict_with_metadata(audio_tensor, sample_rate)["tvs"])

    def predict_combined(
        self, audio_tensor: torch.Tensor, sample_rate: int = 16000
    ) -> dict[str, Any]:
        """Compatibility entry point; all nine channels now come from R4."""
        result = self.predict_with_metadata(audio_tensor, sample_rate)
        result.update(
            {
                "oral": result["tvs"][:, :6],
                "oral_raw": result["tvs_raw"][:, :6],
                "suprasegmental": result["tvs"][:, 6:],
                "clip_fraction": result["metadata"]["clip_fraction"],
            }
        )
        return result

    def warmup(self) -> None:
        with self._lock:
            if self._loaded and not self._warmed_up:
                self.predict(torch.zeros(self.HOP_SAMPLES))
                self._warmed_up = True

    def cleanup(self) -> None:
        with self._lock:
            self._ssl_model = None
            self._predictor_head = None
            self._feature_extractor = None
            self._metadata = {}
            self._loaded = False
            self._warmed_up = False
            clear_torch_device_cache(self.device)
