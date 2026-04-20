"""SSL-based AAI tract-variable predictor using ContentVec + DANN.

Loads a trained DANN checkpoint and predicts tract variables from audio
waveforms. Uses ContentVec as the SSL backbone (replacing DistilHuBERT)
and a DANN-based predictor head with LayerNorm and Dropout.

Normalization: robust_01 (outputs already in [0, 1] range)

Normalization Evolution Note:
- z_score (old): required denormalization via AAINormalizationProfile
- robust_01 (current): values already in [0,1], no denormalization needed
- hard_sigmoid_01 (future): hard-sigmoid clamped to [0,1] (under refinement)
"""

from pathlib import Path
from typing import Optional

import torch
import torch.nn as nn
from transformers import AutoModel, Wav2Vec2FeatureExtractor

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

    The checkpoint is expected to contain:
    - predictor.*: DANN predictor head weights
      Keys: 0.weight, 0.bias (Linear 768->256), 1.weight, 1.bias (LayerNorm 256),
            4.weight, 4.bias (Linear 256->9)

    Usage:
        predictor = SSLAAIPredictor()
        predictor.load()  # or load(checkpoint_path)
        tvs = predictor.predict(audio_tensor, sample_rate=16000)
        # tvs shape: (T, 9), values in [0, 1]
    """

    MODEL_NAME = "lengyue233/content-vec-best"
    SAMPLE_RATE = 16000
    FEATURE_LAYER = -2  # Penultimate hidden state
    FEATURE_DIM = 768
    NUM_TVS = 9

    def __init__(
        self,
        checkpoint_path: Optional[str | Path] = None,
        device: Optional[str] = None,
    ) -> None:
        """Initialize SSL AAI predictor.

        Args:
            checkpoint_path: Path to DANN checkpoint (uses default if None)
            device: Target device (auto-detected if None)
        """
        self.checkpoint_path = (
            Path(checkpoint_path) if checkpoint_path else _get_default_checkpoint_path()
        )
        self.device = device or self._auto_detect_device()
        self._ssl_model: Optional[AutoModel] = None
        self._feature_extractor: Optional[Wav2Vec2FeatureExtractor] = None
        self._predictor_head: Optional[DANNPredictorHead] = None
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

        # Load feature extractor and SSL model (ContentVec)
        # ContentVec doesn't have a preprocessor_config.json, so we create
        # the feature extractor with default settings for 16kHz audio
        self._feature_extractor = Wav2Vec2FeatureExtractor(
            feature_size=1,
            sampling_rate=self.SAMPLE_RATE,
            padding_value=0.0,
            do_normalize=True,
            return_attention_mask=False,
        )
        self._ssl_model = AutoModel.from_pretrained(self.MODEL_NAME)
        self._ssl_model.to(self.device)
        self._ssl_model.eval()

        # Create predictor head
        self._predictor_head = DANNPredictorHead(
            input_dim=self.FEATURE_DIM,
            hidden_dim=256,
            output_dim=self.NUM_TVS,
        )
        self._predictor_head.to(self.device)
        self._predictor_head.eval()

        # Load checkpoint state dict
        state_dict = torch.load(path, map_location=self.device, weights_only=True)

        # Load predictor head weights into self.net (nn.Sequential)
        predictor_state = {}
        for key, value in state_dict.items():
            if key.startswith("predictor."):
                predictor_state[key[len("predictor.") :]] = value

        self._predictor_head.net.load_state_dict(predictor_state, strict=True)

        print("[SSLAAIPredictor] Loaded successfully")
        print(f"[SSLAAIPredictor] SSL model: {self.MODEL_NAME}")
        print(f"[SSLAAIPredictor] Predictor head: {self.FEATURE_DIM} -> 256 -> {self.NUM_TVS}")
        print(f"[SSLAAIPredictor] Output: robust_01 normalized TVs, order: {AAI_TV_ORDER}")
        print("[SSLAAIPredictor] Normalization note: robust_01 (values in [0,1])")

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
        # Validate robust_01 range
        if output.min() < 0.0 or output.max() > 1.0:
            print(
                f"[SSLAAIPredictor] Warning: Output outside [0,1] range: [{output.min():.3f}, {output.max():.3f}]"
            )

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
            torch.Tensor: Tract variables in robust_01 normalization,
                         shape (T, 9), values in [0, 1]
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

        # Extract ContentVec features
        inputs = self._feature_extractor(
            audio_tensor.cpu().numpy(),
            sampling_rate=self.SAMPLE_RATE,
            return_tensors="pt",
        )
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        # Forward through SSL model and predictor
        with torch.no_grad():
            outputs = self._ssl_model(
                **inputs,
                output_hidden_states=True,
                return_dict=True,
            )
            # Get penultimate layer features
            hidden_states = outputs.hidden_states[self.FEATURE_LAYER]
            # Remove batch dimension: (1, T, 768) -> (T, 768)
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
