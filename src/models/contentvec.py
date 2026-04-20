"""ContentVec model management for local SSL feature extraction."""

from typing import Optional

import torch
from transformers import AutoModel, Wav2Vec2FeatureExtractor


class ContentVecModel:
    """ContentVec SSL backbone for AAI tract-variable prediction.

    This wrapper loads the ContentVec model (lengyue233/content-vec-best) and
    extracts penultimate hidden-state features (layer -2) for articulatory
    inversion. The 768-dimensional features are extracted at 50Hz frame rate
    from 16kHz input audio.

    Device priority: CUDA > MPS > CPU
    """

    MODEL_NAME = "lengyue233/content-vec-best"
    SAMPLE_RATE = 16000
    FEATURE_LAYER = -2  # Penultimate hidden state
    FEATURE_DIM = 768
    FRAME_RATE = 50  # Hz

    def __init__(self, model_name: str = MODEL_NAME, device: Optional[str] = None) -> None:
        """Initialize ContentVec model.

        Args:
            model_name: HuggingFace model identifier
            device: Target device (auto-detected if None)
        """
        self.model_name = model_name
        self.device = device or self._auto_detect_device()
        self._load_model()

    def _auto_detect_device(self) -> str:
        """Auto-detect best available device."""
        if torch.cuda.is_available():
            return "cuda"
        if torch.backends.mps.is_available():
            return "mps"
        return "cpu"

    def _load_model(self) -> None:
        """Load ContentVec model and feature extractor."""
        print(f"Loading ContentVec model: {self.model_name}")
        print(f"Device: {self.device}")

        # ContentVec doesn't have a preprocessor_config.json, so we create
        # the feature extractor with default settings for 16kHz audio
        self.feature_extractor = Wav2Vec2FeatureExtractor(
            feature_size=1,
            sampling_rate=self.SAMPLE_RATE,
            padding_value=0.0,
            do_normalize=True,
            return_attention_mask=False,
        )
        self.model = AutoModel.from_pretrained(self.model_name)
        self.model.to(self.device)
        self.model.eval()

        print("ContentVec model loaded successfully.")

    def extract_features(
        self,
        audio_tensor: torch.Tensor,
        sample_rate: int = SAMPLE_RATE,
    ) -> torch.Tensor:
        """Extract ContentVec features from audio waveform.

        Extracts 768-dimensional features from the penultimate layer (layer -2)
        at 50Hz frame rate. Output shape is (T, 768) where T is the number of
        frames.

        Args:
            audio_tensor: Audio waveform as 1D or 2D tensor (samples,)
            sample_rate: Audio sample rate in Hz (must be 16000)

        Returns:
            torch.Tensor: Hidden features of shape (T, 768)

        Raises:
            ValueError: If sample rate is not 16000Hz
        """
        if sample_rate != self.SAMPLE_RATE:
            raise ValueError(f"Audio sample rate must be {self.SAMPLE_RATE}Hz")

        # Ensure 1D tensor
        if audio_tensor.dim() == 2:
            audio_tensor = audio_tensor.squeeze()

        # Extract features using feature extractor
        inputs = self.feature_extractor(
            audio_tensor.cpu().numpy(),
            sampling_rate=self.SAMPLE_RATE,
            return_tensors="pt",
        )
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        # Forward pass with hidden states
        with torch.no_grad():
            outputs = self.model(
                **inputs,
                output_hidden_states=True,
                return_dict=True,
            )
            # Get penultimate layer (layer -2)
            hidden_states = outputs.hidden_states[self.FEATURE_LAYER]

        # Remove batch dimension: (1, T, 768) -> (T, 768)
        if hidden_states.dim() == 3 and hidden_states.shape[0] == 1:
            hidden_states = hidden_states.squeeze(0)

        return hidden_states

    def cleanup(self) -> None:
        """Free model resources."""
        if hasattr(self, "model"):
            del self.model
        if hasattr(self, "feature_extractor"):
            del self.feature_extractor

        if self.device == "cuda" and torch.cuda.is_available():
            torch.cuda.empty_cache()
        elif self.device == "mps" and torch.backends.mps.is_available():
            torch.mps.empty_cache()

        print("ContentVec model resources freed.")
