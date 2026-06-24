"""SSL-based AAI tract-variable predictor using ContentVec + DANN.

Loads a trained DANN checkpoint and predicts tract variables from audio
waveforms. Uses ContentVec as the SSL backbone and a DANN-based predictor
head with LayerNorm and Dropout.

Normalization: robust_01 (outputs already in [0, 1] range)
"""

from pathlib import Path
from typing import Optional

import torch
import torch.nn as nn
from transformers import AutoModel

from src.models.ssl_common import (
    DEFAULT_SSL_FEATURE_CONFIG,
    SSLFeatureConfig,
    build_contentvec_feature_extractor,
    clear_torch_device_cache,
    extract_hidden_states,
    get_best_torch_device,
)

# AAI TV field order confirmed by training
AAI_TV_ORDER = ("LP", "LA", "TTCL", "TTCD", "TBCL", "TBCD", "VEL", "GLO", "LAT")


def _get_default_checkpoint_path() -> Path:
    """Return the default checkpoint path relative to project root."""
    return Path(__file__).parent.parent.parent / "external" / "aai_portable0.1" / "best_model.pt"


class DANNPredictorHead(nn.Module):
    """DANN predictor head: 768 -> 256 -> 9 as nn.Sequential.

    Architecture matches checkpoint from external/aai_portable0.1/models.py:
    Sequential(Linear(768->256), LayerNorm(256), ReLU, Dropout(0.1), Linear(256->9))

    Output is in robust_01 normalization ([0, 1] range).
    """

    def __init__(self, input_dim: int = 768, hidden_dim: int = 256, output_dim: int = 9) -> None:
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(hidden_dim, output_dim),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass returning (T, 9) tract variables in [0, 1] range."""
        return torch.clamp(self.net(x), 0.0, 1.0)


AAIHead = DANNPredictorHead


class SSLAAIPredictor:
    """SSL-based predictor for AAI tract variables using ContentVec + DANN.

    Loads a trained DANN checkpoint with ContentVec backbone and provides
    inference for audio waveforms. Outputs are tract variables in [0, 1]
    range (robust_01 normalization) in the order:
    LP, LA, TTCL, TTCD, TBCL, TBCD, VEL, GLO, LAT

    Configuration sourced from SSLFeatureConfig (see ssl_common.py).
    Extracts features from ContentVec layer 7 by default.

    Usage:
        predictor = SSLAAIPredictor()
        predictor.load()
        tvs = predictor.predict(audio_tensor, sample_rate=16000)
    """

    MODEL_NAME = DEFAULT_SSL_FEATURE_CONFIG.model_name
    SAMPLE_RATE = DEFAULT_SSL_FEATURE_CONFIG.sample_rate
    FEATURE_DIM = DEFAULT_SSL_FEATURE_CONFIG.feature_dim
    NUM_TVS = 9

    def __init__(
        self,
        checkpoint_path: Optional[str | Path] = None,
        device: Optional[str] = None,
        ssl_config: SSLFeatureConfig | None = None,
    ) -> None:
        """Initialize SSL AAI predictor.

        Args:
            checkpoint_path: Path to DANN checkpoint (uses default if None)
            device: Target device (auto-detected if None)
            ssl_config: SSL backbone configuration (uses default if None)
        """
        self.checkpoint_path = (
            Path(checkpoint_path) if checkpoint_path else _get_default_checkpoint_path()
        )
        self.ssl_config = ssl_config or DEFAULT_SSL_FEATURE_CONFIG
        self.device = device or get_best_torch_device()
        self._ssl_model: Optional[AutoModel] = None
        self._feature_extractor = build_contentvec_feature_extractor(self.ssl_config.sample_rate)
        self._predictor_head: Optional[DANNPredictorHead] = None
        self._loaded = False
        self._warmed_up = False

    def warmup(self) -> None:
        """Run a dummy inference to trigger kernel compilation on the device.

        Call once after load() to reduce latency on first real prediction.
        """
        if self._warmed_up or not self._loaded:
            return
        import time

        start = time.time()
        dummy_audio = torch.randn(self.ssl_config.sample_rate, device="cpu")
        try:
            self.predict(dummy_audio, sample_rate=self.ssl_config.sample_rate)
            elapsed = time.time() - start
            print(f"[SSLAAIPredictor] Warmup complete ({elapsed:.2f}s)")
        except Exception as e:
            print(f"[SSLAAIPredictor] Warmup failed (non-critical): {e}")
        self._warmed_up = True

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

        # Load SSL backbone (ContentVec)
        self._ssl_model = AutoModel.from_pretrained(self.ssl_config.model_name)
        self._ssl_model.to(self.device)
        self._ssl_model.eval()

        # Create predictor head
        self._predictor_head = DANNPredictorHead(
            input_dim=self.ssl_config.feature_dim,
            hidden_dim=256,
            output_dim=self.NUM_TVS,
        )
        self._predictor_head.to(self.device)
        self._predictor_head.eval()

        # Load checkpoint state dict
        state_dict = torch.load(path, map_location=self.device, weights_only=True)

        # Load predictor head weights into self.net (nn.Sequential)
        predictor_state = {
            key[len("predictor.") :]: value
            for key, value in state_dict.items()
            if key.startswith("predictor.")
        }

        self._predictor_head.net.load_state_dict(predictor_state, strict=True)

        print("[SSLAAIPredictor] Loaded successfully")
        print(f"[SSLAAIPredictor] SSL model: {self.ssl_config.model_name}")
        print(
            f"[SSLAAIPredictor] Predictor head: {self.ssl_config.feature_dim} -> 256 -> {self.NUM_TVS}"
        )
        print(f"[SSLAAIPredictor] Output: robust_01 normalized TVs, order: {AAI_TV_ORDER}")

        self._loaded = True

    def _validate_output(self, output: torch.Tensor) -> None:
        """Validate predictor output shape and values."""
        if output.ndim != 2:
            raise ValueError(f"Predictor output must be 2D (T, 9), got shape {output.shape}")
        if output.shape[1] != self.NUM_TVS:
            raise ValueError(
                f"Predictor output must have {self.NUM_TVS} channels, got {output.shape[1]}"
            )
        if output.shape[0] == 0:
            raise ValueError("Predictor output has no time frames")
        if not torch.isfinite(output).all():
            raise ValueError("Predictor output contains NaN or Inf values")
        if output.min() < 0.0 or output.max() > 1.0:
            print(
                f"[SSLAAIPredictor] Warning: Output outside [0,1] range: [{output.min():.3f}, {output.max():.3f}]"
            )

    def predict(
        self,
        audio_tensor: torch.Tensor,
        sample_rate: int = DEFAULT_SSL_FEATURE_CONFIG.sample_rate,
    ) -> torch.Tensor:
        """Predict AAI tract variables from audio.

        Args:
            audio_tensor: Audio waveform as 1D tensor
            sample_rate: Audio sample rate (must match config)

        Returns:
            torch.Tensor: Tract variables in robust_01 normalization,
                         shape (T, 9), values in [0, 1]

        Raises:
            RuntimeError: If predictor not loaded.
            ValueError: If sample rate mismatch or invalid output.
        """
        import time

        start = time.time()

        if not self._loaded:
            raise RuntimeError("Predictor not loaded. Call load() first.")

        if sample_rate != self.ssl_config.sample_rate:
            raise ValueError(f"Audio sample rate must be {self.ssl_config.sample_rate}Hz")

        if audio_tensor.dim() == 2:
            audio_tensor = audio_tensor.squeeze()

        inputs = self._feature_extractor(
            audio_tensor.cpu().numpy(),
            sampling_rate=self.ssl_config.sample_rate,
            return_tensors="pt",
        )
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        with torch.inference_mode():
            outputs = self._ssl_model(
                **inputs,
                output_hidden_states=True,
                return_dict=True,
            )
            hidden_states = extract_hidden_states(outputs, self.ssl_config.target_layer)
            tvs = self._predictor_head(hidden_states)

        self._validate_output(tvs)

        elapsed = time.time() - start
        if elapsed > 1.0:
            print(
                f"[SSLAAIPredictor] Prediction took {elapsed:.2f}s for {audio_tensor.shape[-1]} samples"
            )

        return tvs.cpu()

    def cleanup(self) -> None:
        """Free model resources."""
        for attr in ("_ssl_model", "_predictor_head"):
            setattr(self, attr, None)
        self._feature_extractor = None
        clear_torch_device_cache(self.device)
        self._loaded = False
        print("[SSLAAIPredictor] Cleaned up resources")
