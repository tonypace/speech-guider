"""DistilHuBERT model management for local SSL feature extraction."""

from typing import Optional

import torch
from transformers import AutoFeatureExtractor, AutoModel


class DistilHuBERTModel:
    """Primary SSL backbone for future AAI inference on local devices.

    This wrapper is intended for Apple Silicon MPS, CUDA, or CPU execution via
    the standard torch device selection path. It extracts hidden features but
    does not itself perform articulatory prediction.
    """

    MODEL_NAME = "ntu-spml/distilhubert"
    SAMPLE_RATE = 16000

    def __init__(self, model_name: str = MODEL_NAME, device: Optional[str] = None) -> None:
        self.model_name = model_name
        self.device = device or self._auto_detect_device()
        self._load_model()

    def _auto_detect_device(self) -> str:
        if torch.cuda.is_available():
            return "cuda"
        if torch.backends.mps.is_available():
            return "mps"
        return "cpu"

    def _load_model(self) -> None:
        print(f"Loading DistilHuBERT model: {self.model_name}")
        print(f"Device: {self.device}")

        self.feature_extractor = AutoFeatureExtractor.from_pretrained(self.model_name)
        self.model = AutoModel.from_pretrained(self.model_name)
        self.model.to(self.device)
        self.model.eval()

        print("DistilHuBERT model loaded successfully.")

    def extract_features(
        self,
        audio_tensor: torch.Tensor,
        sample_rate: int = SAMPLE_RATE,
    ) -> torch.Tensor:
        """Extract hidden SSL features for an audio waveform."""

        if audio_tensor.dim() == 2:
            audio_tensor = audio_tensor.squeeze()

        if sample_rate != self.SAMPLE_RATE:
            raise ValueError(f"Audio sample rate must be {self.SAMPLE_RATE}Hz")

        inputs = self.feature_extractor(
            audio_tensor,
            sampling_rate=self.SAMPLE_RATE,
            return_tensors="pt",
        )
        inputs = {key: value.to(self.device) for key, value in inputs.items()}

        with torch.no_grad():
            outputs = self.model(**inputs)

        return outputs.last_hidden_state

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
