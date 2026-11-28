"""R5 streaming articulatory predictor (WavLM-Base+ L1..L8 + 43-d acoustic bypass)."""

from __future__ import annotations

import hashlib
import json
import logging
import os
from pathlib import Path
from threading import RLock
from typing import Any, Literal, cast

import numpy as np
import torch

from src.models.r5_badges import R5_CHANNELS_11, R5Stage5Badges
from src.models.ssl_common import clear_torch_device_cache

logger = logging.getLogger(__name__)

DEFAULT_R5_BUNDLE = Path(__file__).resolve().parents[2] / "external" / "R5_CoreML_Export_v1"


def _sha256_file(path: Path) -> str:
    with path.open("rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


class R5AAIPredictor:
    """Predict 11-ch articulatory trajectories + 43-d bypass under R5's contract.

    Uses 1.2 s (19,200-sample) rolling windows with 100 ms (1,600-sample) hops
    and lookahead on raw unnormalized 16 kHz mono float32 waveforms.

    Runtime selection:
    - ``coreml_split``: Apple Silicon Core ML FP32 ``r5_wavlm_l8.mlpackage`` +
      CPU TorchScript ``r5_bypass_decoder.ts.pt`` (~10x faster than CPU).
    - ``torchscript``: CPU TorchScript ``r5_end_to_end.ts.pt`` (never MPS due to
      float64 ops in the traced graph).
    - ``auto``: prefers ``coreml_split`` when available, else ``torchscript``.
    """

    SAMPLE_RATE = 16000
    NUM_TVS = 9
    NUM_R5_CHANNELS = 11
    BYPASS_DIM = 43
    FRAME_RATE = 50
    HOP_SAMPLES = 1600
    WINDOW_SAMPLES = 19200
    LOOKAHEAD_SAMPLES = 1600
    STRIDE_SAMPLES = 320
    FEATURE_FRAMES = 59
    COMMITTED_SLICE = slice(49, 54)

    def __init__(
        self,
        bundle_path: str | Path | None = None,
        *,
        runtime_backend: Literal["auto", "coreml_split", "torchscript"] | None = None,
        compute_units: str | None = None,
        verify_checksums: bool = True,
    ) -> None:
        self.bundle_path = Path(bundle_path or DEFAULT_R5_BUNDLE).expanduser().resolve()
        env_backend = os.getenv("R5_RUNTIME_BACKEND", "auto").strip().lower()
        selected_backend = (runtime_backend or env_backend or "auto").lower()
        if selected_backend not in {"auto", "coreml_split", "torchscript"}:
            raise ValueError(
                f"R5 runtime_backend must be 'auto', 'coreml_split', or 'torchscript', got {selected_backend!r}"
            )
        self.requested_backend = selected_backend
        raw_cu = (
            compute_units
            if compute_units is not None
            else os.getenv("R5_COREML_COMPUTE_UNITS", "ALL")
        )
        self.compute_units_name = raw_cu.strip().upper()
        self.verify_checksums = verify_checksums
        self.device = "cpu"
        self.active_backend: str = "unloaded"
        self._contract: dict[str, Any] = {}
        self._manifest: dict[str, Any] = {}
        self._coreml_wavlm: Any = None
        self._ts_decoder: Any = None
        self._ts_e2e: Any = None
        self._badges: R5Stage5Badges | None = None
        self._loaded = False
        self._lock = RLock()

    def _validate_contract(self) -> dict[str, Any]:
        contract_path = self.bundle_path / "configs" / "r5_streaming_contract.json"
        if not contract_path.is_file():
            raise FileNotFoundError(f"R5 streaming contract not found: {contract_path}")
        contract = json.loads(contract_path.read_text(encoding="utf-8"))
        if (
            not isinstance(contract, dict)
            or contract.get("format_version") != "r5_streaming_contract_v1"
            or contract.get("sample_rate_hz") != self.SAMPLE_RATE
            or contract.get("frame_rate_hz") != self.FRAME_RATE
            or contract.get("hop_samples") != self.HOP_SAMPLES
            or contract.get("window_samples") != self.WINDOW_SAMPLES
            or contract.get("lookahead_samples") != self.LOOKAHEAD_SAMPLES
            or contract.get("feature_frames") != self.FEATURE_FRAMES
            or contract.get("committed_slice") != [49, 54]
            or contract.get("do_normalize_waveform") is not False
            or tuple(contract.get("channels_11", ())) != R5_CHANNELS_11
            or contract.get("bypass_dim") != self.BYPASS_DIM
        ):
            raise ValueError("Unsupported R5 streaming contract")
        return contract

    def _verify_bundle_checksums(self, rel_paths: tuple[str, ...]) -> None:
        if not self.verify_checksums:
            return
        sums_path = self.bundle_path / "SHA256SUMS"
        if not sums_path.is_file():
            raise FileNotFoundError(f"R5 SHA256SUMS not found: {sums_path}")
        hashes: dict[str, str] = {}
        for line in sums_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            digest, rel = line.split(maxsplit=1)
            hashes[rel.removeprefix("*").removeprefix("./")] = digest
        for rel in rel_paths:
            target = self.bundle_path / rel
            if rel not in hashes:
                raise ValueError(f"R5 artifact missing from SHA256SUMS: {rel}")
            if not target.is_file():
                raise FileNotFoundError(f"R5 artifact missing: {target}")
            if _sha256_file(target) != hashes[rel]:
                raise ValueError(f"R5 checksum mismatch for {rel}")

    def _coreml_available(self) -> bool:
        pkg = self.bundle_path / "coreml_fp32" / "r5_wavlm_l8.mlpackage"
        dec = self.bundle_path / "torchscript" / "r5_bypass_decoder.ts.pt"
        if not (pkg / "Manifest.json").is_file() or not dec.is_file():
            return False
        try:
            import coremltools  # type: ignore[import-untyped]  # noqa: F401
        except ImportError:
            return False
        return True

    def _resolve_coreml_compute_units(self, ct_module: Any) -> Any:
        mapping = {
            "ALL": ct_module.ComputeUnit.ALL,
            "CPU_AND_GPU": ct_module.ComputeUnit.CPU_AND_GPU,
            "CPU_AND_NE": ct_module.ComputeUnit.CPU_AND_NE,
            "CPU_ONLY": ct_module.ComputeUnit.CPU_ONLY,
        }
        if self.compute_units_name not in mapping:
            raise ValueError(f"Unsupported R5_COREML_COMPUTE_UNITS: {self.compute_units_name!r}")
        return mapping[self.compute_units_name]

    def load(self) -> None:
        """Load R5 artifacts locally after contract and SHA-256 verification."""
        with self._lock:
            contract = self._validate_contract()
            manifest_path = self.bundle_path / "export_manifest.json"
            manifest = (
                json.loads(manifest_path.read_text(encoding="utf-8"))
                if manifest_path.is_file()
                else {}
            )

            use_coreml = self.requested_backend == "coreml_split" or (
                self.requested_backend == "auto" and self._coreml_available()
            )

            to_verify = ["configs/r5_streaming_contract.json"]
            badge_rel = "weights/realization_badges_v1.json"
            if (self.bundle_path / badge_rel).is_file():
                to_verify.append(badge_rel)

            coreml_wavlm = None
            ts_decoder = None
            ts_e2e = None
            active_backend: str

            if use_coreml:
                import coremltools as ct  # type: ignore[import-untyped]

                pkg = self.bundle_path / "coreml_fp32" / "r5_wavlm_l8.mlpackage"
                dec_path = self.bundle_path / "torchscript" / "r5_bypass_decoder.ts.pt"
                if not (pkg / "Manifest.json").is_file():
                    raise FileNotFoundError(f"R5 Core ML package not found: {pkg}")
                to_verify.append("torchscript/r5_bypass_decoder.ts.pt")
                self._verify_bundle_checksums(tuple(to_verify))
                cu = self._resolve_coreml_compute_units(ct)
                coreml_wavlm = ct.models.MLModel(str(pkg), compute_units=cu)
                ts_decoder = torch.jit.load(str(dec_path), map_location="cpu").eval()
                active_backend = "coreml_split"
                device_label = f"coreml:{self.compute_units_name}"
            else:
                e2e_rel = "torchscript/r5_end_to_end.ts.pt"
                to_verify.append(e2e_rel)
                self._verify_bundle_checksums(tuple(to_verify))
                ts_e2e = torch.jit.load(str(self.bundle_path / e2e_rel), map_location="cpu").eval()
                active_backend = "torchscript"
                device_label = "cpu"

            badges = (
                R5Stage5Badges.from_file(self.bundle_path / badge_rel)
                if (self.bundle_path / badge_rel).is_file()
                else None
            )

            self._contract = contract
            self._manifest = manifest
            self._coreml_wavlm = coreml_wavlm
            self._ts_decoder = ts_decoder
            self._ts_e2e = ts_e2e
            self._badges = badges
            self.active_backend = active_backend
            self.device = device_label
            self._loaded = True
            logger.info("R5 loaded (%s) from %s", device_label, self.bundle_path)

    @property
    def badges(self) -> R5Stage5Badges | None:
        return self._badges

    def _build_windows(self, samples: np.ndarray) -> tuple[np.ndarray, int]:
        """Slice raw unnormalized audio into R5's 1.2s/100ms rolling windows."""
        frame_count = (len(samples) + self.STRIDE_SAMPLES // 2 - 1) // self.STRIDE_SAMPLES
        hops = (len(samples) + self.HOP_SAMPLES - 1) // self.HOP_SAMPLES
        padded = np.pad(samples, (0, (hops + 1) * self.HOP_SAMPLES - len(samples)))
        window = np.zeros(self.WINDOW_SAMPLES, dtype=np.float32)
        windows: list[np.ndarray] = []
        for hop_index in range(hops + 1):
            offset = hop_index * self.HOP_SAMPLES
            hop = padded[offset : offset + self.HOP_SAMPLES]
            window[: -self.HOP_SAMPLES] = window[self.HOP_SAMPLES :]
            window[-self.HOP_SAMPLES :] = hop
            if hop_index >= 1:
                windows.append(window.copy())
        if not windows:
            return np.zeros((0, self.WINDOW_SAMPLES), dtype=np.float32), 0
        return np.stack(windows, axis=0), frame_count

    def _run_windows(self, windows: np.ndarray) -> tuple[torch.Tensor, torch.Tensor]:
        if len(windows) == 0:
            return (
                torch.zeros((0, self.NUM_R5_CHANNELS), dtype=torch.float32),
                torch.zeros((0, self.BYPASS_DIM), dtype=torch.float32),
            )
        preds_11: list[torch.Tensor] = []
        preds_byp: list[torch.Tensor] = []
        if self.active_backend == "coreml_split":
            assert self._coreml_wavlm is not None and self._ts_decoder is not None
            for i in range(len(windows)):
                x_np = windows[i : i + 1]
                ssl = self._coreml_wavlm.predict({"raw_window": x_np})["ssl_layers"].astype(
                    np.float32
                )
                o11, obyp = self._ts_decoder(torch.from_numpy(x_np), torch.from_numpy(ssl))
                preds_11.append(o11[0].detach().to("cpu", dtype=torch.float32))
                preds_byp.append(obyp[0].detach().to("cpu", dtype=torch.float32))
        else:
            assert self._ts_e2e is not None
            for i in range(len(windows)):
                x_t = torch.from_numpy(windows[i : i + 1])
                o11, obyp = self._ts_e2e(x_t)
                preds_11.append(o11[0].detach().to("cpu", dtype=torch.float32))
                preds_byp.append(obyp[0].detach().to("cpu", dtype=torch.float32))
        return torch.cat(preds_11, dim=0), torch.cat(preds_byp, dim=0)

    def predict_with_metadata(
        self,
        audio_tensor: torch.Tensor,
        sample_rate: int = 16000,
        *,
        contact_enabled: bool = False,
        **_: Any,
    ) -> dict[str, Any]:
        """Return 9-ch display/raw trajectories, 11-ch R5 channels, and 43-d bypass."""
        del contact_enabled
        with self._lock, torch.inference_mode():
            if not self._loaded:
                raise RuntimeError("R5 predictor not loaded. Call load() first.")
            if sample_rate != self.SAMPLE_RATE:
                raise ValueError("Audio sample rate must be 16000Hz")
            audio = audio_tensor.detach().to("cpu", dtype=torch.float32)
            if audio.ndim == 2 and audio.shape[0] == 1:
                audio = audio[0]
            if audio.ndim != 1 or audio.numel() == 0:
                raise ValueError("Audio must be one nonempty mono waveform")
            if not torch.isfinite(audio).all():
                raise ValueError("Audio contains NaN or Inf values")

            samples = audio.numpy()
            windows, frame_count = self._build_windows(samples)
            raw_11, bypass_43 = self._run_windows(windows)
            raw_11 = raw_11[:frame_count]
            bypass_43 = bypass_43[:frame_count]

            if raw_11.shape != (frame_count, self.NUM_R5_CHANNELS):
                raise ValueError(f"Unexpected R5 11ch shape: {tuple(raw_11.shape)}")
            if not torch.isfinite(raw_11).all():
                raise ValueError("R5 predictor output contains NaN or Inf values")

            raw_9 = raw_11[:, : self.NUM_TVS]
            outside = (raw_9 < 0.0) | (raw_9 > 1.0)
            return {
                "tvs": raw_9.clamp(0.0, 1.0),
                "tvs_raw": raw_9,
                "tvs_11ch": raw_11,
                "bypass_43d": bypass_43,
                "labiodental_retraction": torch.zeros(frame_count, dtype=torch.float32),
                "center_samples": torch.arange(frame_count) * self.STRIDE_SAMPLES + 160,
                "metadata": {
                    "model_version": "r5",
                    "decoder": "r5_arm_b_direct",
                    "encoder": self._contract.get("encoder_id", "microsoft/wavlm-base-plus"),
                    "runtime_backend": self.active_backend,
                    "compute_units": self.compute_units_name
                    if self.active_backend == "coreml_split"
                    else "CPU",
                    "device": self.device,
                    "layers": list(range(1, int(self._contract.get("max_layer", 8)) + 1)),
                    "channels": self.NUM_R5_CHANNELS,
                    "normalization": "speaker_z_normalized",
                    "frame_rate": self.FRAME_RATE,
                    "lookahead_ms": 100,
                    "contact_augmentation": "native_r5",
                    "clip_fraction": float(outside.float().mean().item()) if frame_count else 0.0,
                    "source_trunk_sha256": self._manifest.get("source_trunk_sha256"),
                },
            }

    def predict(
        self, audio_tensor: torch.Tensor, sample_rate: int = 16000, *, contact_enabled: bool = False
    ) -> torch.Tensor:
        return cast(
            torch.Tensor,
            self.predict_with_metadata(audio_tensor, sample_rate, contact_enabled=contact_enabled)[
                "tvs"
            ],
        )

    def cleanup(self) -> None:
        with self._lock:
            self._coreml_wavlm = None
            self._ts_decoder = None
            self._ts_e2e = None
            self._badges = None
            self._contract = {}
            self._manifest = {}
            self.active_backend = "unloaded"
            self._loaded = False
            clear_torch_device_cache("cpu")
