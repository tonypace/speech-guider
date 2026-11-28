"""Lazy local loader for frozen utter-project/mHuBERT-147 encoder."""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from threading import RLock
from typing import Any, cast

import numpy as np
import torch
from transformers import AutoFeatureExtractor, AutoModel  # type: ignore[import-untyped]

from src.models.ssl_common import clear_torch_device_cache, get_best_torch_device

logger = logging.getLogger(__name__)

DEFAULT_MHUBERT_BUNDLE = Path(__file__).resolve().parents[2] / "external" / "mhubert-147"


def _sha256_file(path: Path) -> str:
    with path.open("rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


def verify_mhubert_checksums(bundle_path: Path, rel_paths: tuple[str, ...]) -> None:
    """Verify staged mHuBERT-147 / ctc_v1 files against SHA256SUMS if present."""
    sums_path = bundle_path / "SHA256SUMS"
    if not sums_path.is_file():
        return
    hashes: dict[str, str] = {}
    for line in sums_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, rel = line.split(maxsplit=1)
        hashes[rel.removeprefix("*").removeprefix("./")] = digest
    for rel in rel_paths:
        target = bundle_path / rel
        if not target.is_file():
            raise FileNotFoundError(f"mHuBERT staged asset missing: {target}")
        if rel in hashes and _sha256_file(target) != hashes[rel]:
            raise ValueError(f"mHuBERT asset checksum mismatch for {rel}")


class MHuBERTEncoder:
    """Thread-safe full-utterance 50 Hz feature extractor for mHuBERT-147."""

    SAMPLE_RATE = 16000
    STRIDE_SAMPLES = 320
    HIDDEN_DIM = 768

    def __init__(
        self,
        bundle_path: str | Path | None = None,
        device: str | None = None,
        *,
        verify_checksums: bool = True,
    ) -> None:
        self.bundle_path = Path(bundle_path or DEFAULT_MHUBERT_BUNDLE).expanduser().resolve()
        if device is None:
            best = get_best_torch_device()
            # PyTorch MPS Conv1d rejects > 65536 length (> ~20.48 s at 16 kHz); CPU handles full utterances in ~1.3 s.
            self.device = "cpu" if best == "mps" else best
        else:
            self.device = device
        self.verify_checksums = verify_checksums
        self._model: Any = None
        self._feature_extractor: Any = None
        self._loaded = False
        self._lock = RLock()

    def load(self) -> None:
        with self._lock:
            encoder_dir = self.bundle_path / "encoder"
            if not encoder_dir.is_dir():
                raise FileNotFoundError(f"mHuBERT encoder directory not found: {encoder_dir}")
            required = ["encoder/config.json", "encoder/preprocessor_config.json"]
            if (encoder_dir / "model.safetensors").is_file():
                required.append("encoder/model.safetensors")
            elif (encoder_dir / "pytorch_model.bin").is_file():
                required.append("encoder/pytorch_model.bin")
            else:
                raise FileNotFoundError(f"mHuBERT encoder weights missing in {encoder_dir}")

            if self.verify_checksums:
                verify_mhubert_checksums(self.bundle_path, tuple(required))

            extractor = AutoFeatureExtractor.from_pretrained(encoder_dir, local_files_only=True)
            model = AutoModel.from_pretrained(encoder_dir, local_files_only=True)
            if getattr(model.config, "hidden_size", None) != self.HIDDEN_DIM:
                raise ValueError(
                    f"Expected mHuBERT hidden_size={self.HIDDEN_DIM}, got {model.config.hidden_size}"
                )
            self._feature_extractor = extractor
            self._model = model.to(self.device).eval()
            self._loaded = True
            logger.info("mHuBERT-147 encoder loaded on %s from %s", self.device, encoder_dir)

    def extract_features(
        self, audio_tensor: torch.Tensor, sample_rate: int = 16000
    ) -> torch.Tensor:
        """Extract 50 Hz last_hidden_state tensor of shape (T, 768) on CPU."""
        with self._lock, torch.inference_mode():
            if not self._loaded or self._model is None or self._feature_extractor is None:
                raise RuntimeError("MHuBERTEncoder is not loaded. Call load() first.")
            if sample_rate != self.SAMPLE_RATE:
                raise ValueError(f"Expected {self.SAMPLE_RATE} Hz audio, got {sample_rate}")
            audio = audio_tensor.detach().to("cpu", dtype=torch.float32)
            if audio.ndim == 2 and audio.shape[0] == 1:
                audio = audio[0]
            if audio.ndim != 1 or audio.numel() == 0:
                raise ValueError("Audio must be a nonempty mono waveform")
            if not torch.isfinite(audio).all():
                raise ValueError("Audio contains NaN or Inf values")

            samples = np.asarray(audio.numpy(), dtype=np.float32)
            # Minimum receptive field is 400 samples (25 ms) for 7-layer HuBERT conv frontend.
            if samples.shape[0] < 400:
                samples = np.pad(samples, (0, 400 - samples.shape[0]))
            processed = self._feature_extractor(
                samples, sampling_rate=self.SAMPLE_RATE, return_tensors="pt"
            )
            try:
                inputs = {k: v.to(self.device) for k, v in processed.items()}
                try:
                    outputs = self._model(**inputs)
                except (NotImplementedError, RuntimeError) as exc:
                    if self.device != "mps" or "65536" not in str(exc):
                        raise
                    logger.warning(
                        "mHuBERT MPS hit > 65536 length limit; falling back to CPU: %s", exc
                    )
                    clear_torch_device_cache("mps")
                    self._model = self._model.to("cpu")
                    self.device = "cpu"
                    cpu_inputs = {k: v.to("cpu") for k, v in processed.items()}
                    outputs = self._model(**cpu_inputs)
                hidden = outputs.last_hidden_state[0].detach().to("cpu", dtype=torch.float32)
                return cast(torch.Tensor, hidden)
            finally:
                clear_torch_device_cache(self.device)

    def cleanup(self) -> None:
        with self._lock:
            self._model = None
            self._feature_extractor = None
            self._loaded = False
            clear_torch_device_cache(self.device)
