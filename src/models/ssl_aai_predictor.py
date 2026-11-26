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
from src.models.r4_calibration import CausalSpeechWeightTracker, OutputCalibrator
from src.models.r4_contact import ContactTracker, R4ContactHead, load_contact_head
from src.models.r4_contract import StreamingContract, load_streaming_contract
from src.models.r4_decoder import R4Decoder, load_r4_decoder
from src.models.r4_dental import DentalCorrection
from src.models.r4_hints import (
    load_dental,
    load_labiodental,
    load_lip,
    load_output_calibration,
    load_silence,
)
from src.models.r4_labiodental import LabiodentalCorrection
from src.models.r4_lip import LipCorrection, LipCorrectionStream
from src.models.r4_silence import apply_silence_hint
from src.models.ssl_common import (
    DEFAULT_SSL_FEATURE_CONFIG,
    SSLFeatureConfig,
    clear_torch_device_cache,
    get_best_torch_device,
)

logger = logging.getLogger(__name__)
DEFAULT_R4_BUNDLE = (
    Path(__file__).resolve().parents[2] / "external" / "R4 final with hinting models"
)


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
        *,
        lip_enabled: bool = True,
        dental_enabled: bool = False,
        calibrate_enabled: bool = True,
        labiodental_enabled: bool = True,
        silence_mode: str = "reviewed",
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
        if silence_mode not in {"off", "reviewed", "expanded"}:
            raise ValueError("R4 silence mode must be off, reviewed, or expanded")
        self.lip_enabled = lip_enabled
        self.dental_enabled = dental_enabled
        self.calibrate_enabled = calibrate_enabled
        self.labiodental_enabled = labiodental_enabled
        self.silence_mode = silence_mode
        self._contract: StreamingContract | None = None
        self._lip_correction: LipCorrection | None = None
        self._dental_correction: DentalCorrection | None = None
        self._output_calibrator: OutputCalibrator | None = None
        self._labiodental_correction: LabiodentalCorrection | None = None
        self._silence: dict[str, tuple[Any, dict[str, Any], dict[str, int]]] = {}
        self._calibration_silence: tuple[Any, dict[str, Any], dict[str, int]] | None = None
        self.device = device or get_best_torch_device()
        self._ssl_model: Any = None
        self._feature_extractor: Any = None
        self._predictor_head: R4Decoder | None = None
        self._contact_head: R4ContactHead | None = None
        self._metadata: dict[str, Any] = {}
        self._loaded = False
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
            self._contact_head = None
            self._lip_correction = None
            self._dental_correction = None
            self._output_calibrator = None
            self._labiodental_correction = None
            self._silence = {}
            self._calibration_silence = None
            self._metadata = metadata
            self.checkpoint_path = path
            self._loaded = True
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
        self._contract = load_streaming_contract(config_path)

    def _validate_output(self, output: torch.Tensor, *, allow_empty: bool = False) -> None:
        if output.ndim != 2:
            raise ValueError(f"Predictor output must be 2D (T, 9), got {output.shape}")
        if output.shape[1] != 9:
            raise ValueError(f"Predictor output must have 9 channels, got {output.shape[1]}")
        if output.shape[0] == 0 and not allow_empty:
            raise ValueError("Predictor output has no time frames")
        if not torch.isfinite(output).all():
            raise ValueError("Predictor output contains NaN or Inf values")

    def _predict_window(
        self,
        samples: np.ndarray,
        tracker: ContactTracker | None = None,
        lip_stream: LipCorrectionStream | None = None,
        dental: DentalCorrection | None = None,
        output_calibrator: OutputCalibrator | None = None,
        speech_weight: np.ndarray | None = None,
        labiodental: LabiodentalCorrection | None = None,
        labiodental_out: list[np.ndarray] | None = None,
    ) -> torch.Tensor:
        processed = self._feature_extractor(samples, sampling_rate=16000, return_tensors="pt")
        inputs = {key: value.to(self.device) for key, value in processed.items()}
        features = self._ssl_model(**inputs).last_hidden_state
        if features.shape != (1, self.FEATURE_FRAMES, 768):
            raise ValueError(f"Unexpected R4 encoder feature shape: {tuple(features.shape)}")
        assert self._predictor_head is not None
        if tracker is None:
            trajectory = self._predictor_head(features)
            prediction = trajectory[0, self.COMMITTED_SLICE]
        else:
            assert self._contact_head is not None
            trajectory, states, scaled = self._predictor_head.predict_with_states(features)
            prediction = self._contact_head(
                trajectory, states, scaled, self.COMMITTED_SLICE, tracker
            )
        if trajectory.shape != (1, self.FEATURE_FRAMES, 9):
            raise ValueError(f"Unexpected R4 trajectory shape: {tuple(trajectory.shape)}")
        self._validate_output(prediction)
        prediction = prediction.detach().to("cpu", dtype=torch.float32)
        if (
            lip_stream is not None
            or output_calibrator is not None
            or dental is not None
            or labiodental is not None
        ):
            # Hint readouts use unscaled L7 rows, after committed-frame contact.
            committed_features = (
                features[0, self.COMMITTED_SLICE].to("cpu", dtype=torch.float32).numpy()
            )
            values = prediction.numpy()
            if lip_stream is not None:
                values, _ = lip_stream.apply(committed_features, values)
            if output_calibrator is not None:
                values = output_calibrator.apply(values, speech_weight=speech_weight)
            if dental is not None:
                values, _ = dental.apply(committed_features, values)
            if labiodental is not None:
                labiodental_ret, _ = labiodental.apply(committed_features, values)
                if labiodental_out is not None:
                    labiodental_out.append(labiodental_ret)
            prediction = torch.from_numpy(values)
        self._validate_output(prediction)
        return cast(torch.Tensor, prediction)

    def predict_with_metadata(
        self,
        audio_tensor: torch.Tensor,
        sample_rate: int = 16000,
        *,
        contact_enabled: bool = False,
        lip_enabled: bool | None = None,
        dental_enabled: bool | None = None,
        calibrate_enabled: bool | None = None,
        labiodental_enabled: bool | None = None,
        silence_mode: str | None = None,
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
            tracker = None
            contact_mode = "disabled"
            if contact_enabled:
                contact_path = self.bundle_path / "weights" / "contact.pt"
                if self._contact_head is None and contact_path.is_file():
                    self._contact_head = load_contact_head(
                        contact_path, self.checkpoint_path, self.device
                    )
                if self._contact_head is not None:
                    tracker = ContactTracker()
                    contact_mode = "enabled"
                else:
                    contact_mode = "unavailable"
            effective_lip = self.lip_enabled if lip_enabled is None else lip_enabled
            effective_dental = self.dental_enabled if dental_enabled is None else dental_enabled
            effective_calibrate = (
                self.calibrate_enabled if calibrate_enabled is None else calibrate_enabled
            )
            effective_labiodental = (
                self.labiodental_enabled if labiodental_enabled is None else labiodental_enabled
            )
            effective_silence = self.silence_mode if silence_mode is None else silence_mode
            if effective_silence not in {"off", "reviewed", "expanded"}:
                raise ValueError("R4 silence mode must be off, reviewed, or expanded")
            lip_stream = None
            dental = None
            output_calibrator = None
            speech_tracker = None
            labiodental = None
            if tracker is not None and self._contract is not None:
                if effective_lip and (self.bundle_path / "weights/lip.json").is_file():
                    if self._lip_correction is None:
                        self._lip_correction = load_lip(
                            self.bundle_path, self._metadata, self._contract
                        )
                    lip_stream = self._lip_correction.new_stream()
                if effective_dental:
                    if self._dental_correction is None:
                        self._dental_correction = load_dental(
                            self.bundle_path, self._metadata, self._contract
                        )
                    dental = self._dental_correction
                if (
                    effective_silence != "off"
                    and (self.bundle_path / "weights/silence.joblib").is_file()
                ):
                    if effective_silence not in self._silence:
                        self._silence[effective_silence] = load_silence(
                            self.bundle_path, effective_silence
                        )
                if (
                    effective_calibrate
                    and (self.bundle_path / "configs/output_calibration.json").is_file()
                    and (self.bundle_path / "weights/silence.joblib").is_file()
                ):
                    if self._output_calibrator is None:
                        self._output_calibrator = load_output_calibration(self.bundle_path)
                    output_calibrator = self._output_calibrator
                    if self._calibration_silence is None:
                        self._calibration_silence = load_silence(self.bundle_path, "expanded")
                    cal_classifier, cal_gates, cal_allowance = self._calibration_silence
                    speech_tracker = CausalSpeechWeightTracker(
                        cal_classifier,
                        cal_gates,
                        self._contract,
                        allowance=cal_allowance,
                    )
                if (
                    effective_labiodental
                    and (self.bundle_path / "weights/labiodental.json").is_file()
                ):
                    if self._labiodental_correction is None:
                        self._labiodental_correction = load_labiodental(
                            self.bundle_path, self._metadata, self._contract
                        )
                    labiodental = self._labiodental_correction
            samples = audio.numpy()
            # The final bundle emits only frames whose centers lie inside source audio.
            frame_count = (len(samples) + self.STRIDE_SAMPLES // 2 - 1) // self.STRIDE_SAMPLES
            hops = (len(samples) + self.HOP_SAMPLES - 1) // self.HOP_SAMPLES
            # One extra hop supplies future context for the final real audio hop.
            padded = np.pad(samples, (0, (hops + 1) * self.HOP_SAMPLES - len(samples)))
            window = np.zeros(self.WINDOW_SAMPLES, dtype=np.float32)
            packets: list[torch.Tensor] = []
            labiodental_packets: list[np.ndarray] = []
            for hop_index in range(hops + 1):
                offset = hop_index * self.HOP_SAMPLES
                hop = padded[offset : offset + self.HOP_SAMPLES]
                window[: -self.HOP_SAMPLES] = window[self.HOP_SAMPLES :]
                window[-self.HOP_SAMPLES :] = hop
                sw = speech_tracker.append_hop(hop) if speech_tracker is not None else None
                if hop_index >= 1:
                    packet = (
                        self._predict_window(window)
                        if tracker is None
                        else self._predict_window(
                            window,
                            tracker,
                            lip_stream,
                            dental,
                            output_calibrator,
                            sw,
                            labiodental,
                            labiodental_packets,
                        )
                    )
                    packets.append(packet)
            raw = torch.cat(packets, dim=0)[:frame_count]
            self._validate_output(raw, allow_empty=True)
            labiodental_ret = (
                np.concatenate(labiodental_packets)[:frame_count].astype(np.float32)
                if labiodental_packets
                else np.zeros(frame_count, dtype=np.float32)
            )
            settled = np.zeros(frame_count, dtype=bool)
            silence_mode_applied = "off"
            if (
                tracker is not None
                and effective_silence != "off"
                and effective_silence in self._silence
                and frame_count
            ):
                assert self._contract is not None
                classifier, gates, allowance = self._silence[effective_silence]
                values, settled = apply_silence_hint(
                    raw.numpy(), samples, classifier, gates, allowance, self._contract
                )
                raw = torch.from_numpy(values)
                self._validate_output(raw)
                labiodental_ret = labiodental_ret.copy()
                labiodental_ret[settled] = 0.0
                silence_mode_applied = effective_silence
            outside = (raw < 0.0) | (raw > 1.0)
            return {
                "tvs": raw.clamp(0.0, 1.0),
                "tvs_raw": raw,
                "labiodental_retraction": torch.from_numpy(labiodental_ret),
                "center_samples": torch.arange(frame_count) * self.STRIDE_SAMPLES + 160,
                "metadata": {
                    "decoder": "r4_bounded_v12",
                    "device": self.device,
                    "supra_decoder": "r4_lat_temporal_v12",
                    "layers": [7],
                    "normalization": "speaker_z_normalized",
                    "frame_rate": 50,
                    "lookahead_ms": 100,
                    "contact_augmentation": contact_mode,
                    "lip_correction": lip_stream is not None,
                    "output_calibration": output_calibrator is not None,
                    "dental_correction": dental is not None,
                    "labiodental_correction": labiodental is not None,
                    "silence_hint": silence_mode_applied,
                    "silence_settled_frames": int(settled.sum()),
                    "clip_fraction": float(outside.float().mean().item()) if frame_count else 0.0,
                    "source_commit": self._metadata.get("git_commit"),
                },
            }

    def predict(
        self, audio_tensor: torch.Tensor, sample_rate: int = 16000, *, contact_enabled: bool = False
    ) -> torch.Tensor:
        """Return display-safe (T, 9) output shared by both application paths."""
        return cast(
            torch.Tensor,
            self.predict_with_metadata(audio_tensor, sample_rate, contact_enabled=contact_enabled)[
                "tvs"
            ],
        )

    def cleanup(self) -> None:
        with self._lock:
            self._ssl_model = None
            self._predictor_head = None
            self._contact_head = None
            self._feature_extractor = None
            self._lip_correction = None
            self._dental_correction = None
            self._output_calibrator = None
            self._labiodental_correction = None
            self._silence = {}
            self._calibration_silence = None
            self._contract = None
            self._metadata = {}
            self._loaded = False
            clear_torch_device_cache(self.device)
