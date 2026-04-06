"""SSL-based AAI tract-variable predictor using DistilHuBERT.

Loads a trained checkpoint and predicts z-scored AAI tract variables
from audio waveforms. Uses the existing AAI adapter for conversion
to canonical animation states.
"""

import os
from pathlib import Path
from typing import Optional

import torch
import torch.nn as nn
from transformers import AutoFeatureExtractor, AutoModel

# AAI TV field order confirmed by training
AAI_TV_ORDER = ("LP", "LA", "TTCL", "TTCD", "TBCL", "TBCD", "VEL", "GLO", "LAT")


def _get_default_checkpoint_path() -> Path:
    """Return the default checkpoint path relative to project root."""
    return Path(__file__).parent.parent.parent / "models" / "distillhubert-aai" / "best_model.pt"


class AAIHead(nn.Module):
    """Predictor head: 768 -> 256 -> 9 with ReLU and Dropout."""

    def __init__(self) -> None:
        super().__init__()
        self.fc1 = nn.Linear(768, 256)
        self.relu = nn.ReLU()
        self.dropout = nn.Dropout(0.1)
        self.fc2 = nn.Linear(256, 9)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass returning (T, 9) z-scored AAI TVs."""

        x = self.fc1(x)
        x = self.relu(x)
        x = self.dropout(x)
        x = self.fc2(x)
        return x


class SSLAAIPredictor:
    """SSL-based predictor for AAI tract variables.

    Loads a trained DistilHuBERT + predictor head checkpoint and
    provides inference for audio waveforms. Outputs are z-scored
    AAI tract variables in the confirmed order:
    LP, LA, TTCL, TTCD, TBCL, TBCD, VEL, GLO, LAT

    The checkpoint is expected to contain:
    - ssl_model.*: DistilHuBERT weights
    - predictor.*: Predictor head weights (ignored: domain_classifier.*)

    Usage:
        predictor = SSLAAIPredictor()
        predictor.load()  # or load(checkpoint_path)
        tvs = predictor.predict(audio_tensor, sample_rate=16000)
        # tvs shape: (T, 9), z-scored
    """

    MODEL_NAME = "ntu-spml/distilhubert"
    SAMPLE_RATE = 16000

    def __init__(
        self,
        checkpoint_path: Optional[str | Path] = None,
        device: Optional[str] = None,
    ) -> None:
        self.checkpoint_path = (
            Path(checkpoint_path) if checkpoint_path else _get_default_checkpoint_path()
        )
        self.device = device or self._auto_detect_device()
        self._ssl_model: Optional[AutoModel] = None
        self._feature_extractor: Optional[AutoFeatureExtractor] = None
        self._predictor_head: Optional[AAIHead] = None
        self._loaded = False

    def _auto_detect_device(self) -> str:
        """Auto-detect best available device."""

        if torch.cuda.is_available():
            return "cuda"
        if torch.backends.mps.is_available():
            return "mps"
        return "cpu"

    def load(self, checkpoint_path: Optional[str | Path] = None) -> None:
        """Load SSL backbone and predictor head from checkpoint.

        Args:
            checkpoint_path: Optional override path. Uses init path if not provided.

        Raises:
            FileNotFoundError: If checkpoint does not exist.
            RuntimeError: If checkpoint loading fails or state dict incompatible.
        """

        path = Path(checkpoint_path) if checkpoint_path else self.checkpoint_path
        if not path.exists():
            raise FileNotFoundError(f"SSL AAI checkpoint not found: {path}")

        print(f"[SSLAAIPredictor] Loading checkpoint from {path}")
        print(f"[SSLAAIPredictor] Device: {self.device}")

        # Load feature extractor and SSL model
        self._feature_extractor = AutoFeatureExtractor.from_pretrained(self.MODEL_NAME)
        self._ssl_model = AutoModel.from_pretrained(self.MODEL_NAME)
        self._ssl_model.to(self.device)
        self._ssl_model.eval()

        # Create and load predictor head
        self._predictor_head = AAIHead()
        self._predictor_head.to(self.device)
        self._predictor_head.eval()

        # Load state dict
        state_dict = torch.load(path, map_location=self.device, weights_only=True)

        # Filter and load SSL model weights
        ssl_state = {
            k.replace("ssl_model.", ""): v
            for k, v in state_dict.items()
            if k.startswith("ssl_model.")
        }
        self._ssl_model.load_state_dict(ssl_state)

        # Filter and load predictor weights
        # Checkpoint uses sequential keys: 0.weight, 0.bias, 3.weight, 3.bias
        # Map to our named parameters: fc1.weight, fc1.bias, fc2.weight, fc2.bias
        predictor_state = {}
        for k, v in state_dict.items():
            if k.startswith("predictor."):
                key = k.replace("predictor.", "")
                if key == "0.weight":
                    predictor_state["fc1.weight"] = v
                elif key == "0.bias":
                    predictor_state["fc1.bias"] = v
                elif key == "3.weight":
                    predictor_state["fc2.weight"] = v
                elif key == "3.bias":
                    predictor_state["fc2.bias"] = v

        self._predictor_head.load_state_dict(predictor_state, strict=True)

        print(f"[SSLAAIPredictor] Loaded successfully")
        print(f"[SSLAAIPredictor] SSL model: {self.MODEL_NAME}")
        print(f"[SSLAAIPredictor] Predictor head: 768 -> 256 -> 9")
        print(f"[SSLAAIPredictor] Output: z-scored AAI TVs, order: {AAI_TV_ORDER}")

        self._loaded = True

    def _validate_output(self, output: torch.Tensor) -> None:
        """Validate predictor output shape and values."""

        if output.ndim != 2:
            raise ValueError(f"Predictor output must be 2D (T, 9), got shape {output.shape}")
        if output.shape[1] != 9:
            raise ValueError(f"Predictor output must have 9 channels, got {output.shape[1]}")
        if output.shape[0] == 0:
            raise ValueError("Predictor output has no time frames")
        if not torch.isfinite(output).all():
            raise ValueError("Predictor output contains NaN or Inf values")

    def predict(
        self,
        audio_tensor: torch.Tensor,
        sample_rate: int = SAMPLE_RATE,
    ) -> torch.Tensor:
        """Predict AAI tract variables from audio.

        Args:
            audio_tensor: Audio waveform as 1D tensor
            sample_rate: Audio sample rate (must be 16000)

        Returns:
            torch.Tensor: Z-scored AAI tract variables, shape (T, 9)
                         Order: LP, LA, TTCL, TTCD, TBCL, TBCD, VEL, GLO, LAT

        Raises:
            RuntimeError: If predictor not loaded.
            ValueError: If sample rate mismatch or invalid output.
        """

        if not self._loaded:
            raise RuntimeError("Predictor not loaded. Call load() first.")

        if sample_rate != self.SAMPLE_RATE:
            raise ValueError(f"Audio sample rate must be {self.SAMPLE_RATE}Hz")

        if audio_tensor.dim() == 2:
            audio_tensor = audio_tensor.squeeze()

        # Extract features
        inputs = self._feature_extractor(
            audio_tensor.cpu().numpy(),
            sampling_rate=self.SAMPLE_RATE,
            return_tensors="pt",
        )
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        # Forward through SSL model and predictor
        with torch.no_grad():
            ssl_outputs = self._ssl_model(**inputs)
            hidden_states = ssl_outputs.last_hidden_state  # (B, T, 768)
            # Remove batch dimension if present
            if hidden_states.dim() == 3 and hidden_states.shape[0] == 1:
                hidden_states = hidden_states.squeeze(0)
            # Predict tract variables
            tvs = self._predictor_head(hidden_states)

        self._validate_output(tvs)

        return tvs.cpu()

    def cleanup(self) -> None:
        """Free model resources."""

        if self._ssl_model is not None:
            del self._ssl_model
            self._ssl_model = None
        if self._predictor_head is not None:
            del self._predictor_head
            self._predictor_head = None
        if self._feature_extractor is not None:
            del self._feature_extractor
            self._feature_extractor = None

        if self.device == "cuda" and torch.cuda.is_available():
            torch.cuda.empty_cache()
        elif self.device == "mps" and torch.backends.mps.is_available():
            torch.mps.empty_cache()

        self._loaded = False
        print("[SSLAAIPredictor] Cleaned up resources")
