"""Shared SSL backbone config and utilities.

Single source for model constants, device helpers, and hidden-state
extraction. Extracts features from a single target layer (layer 7
for ContentVec).
"""

from dataclasses import dataclass
from typing import Any, cast

import torch
from transformers import Wav2Vec2FeatureExtractor


@dataclass(frozen=True)
class SSLFeatureConfig:
    """SSL backbone configuration.

    Attributes:
        model_name: HuggingFace model identifier
        sample_rate: Required audio sample rate in Hz
        frame_rate: Output frame rate in Hz
        feature_dim: Hidden state dimension
        target_layer: Layer index to extract features from
    """

    model_name: str = "lengyue233/content-vec-best"
    sample_rate: int = 16000
    frame_rate: int = 50
    feature_dim: int = 768
    target_layer: int = 7


DEFAULT_SSL_FEATURE_CONFIG = SSLFeatureConfig()


def get_best_torch_device() -> str:
    """Auto-detect best available torch device."""
    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def clear_torch_device_cache(device: str) -> None:
    """Free cached memory for a given device."""
    if device == "cuda" and torch.cuda.is_available():
        torch.cuda.empty_cache()
    elif device == "mps" and torch.backends.mps.is_available():
        torch.mps.empty_cache()


def build_contentvec_feature_extractor(
    sample_rate: int = 16000,
) -> Wav2Vec2FeatureExtractor:
    """Create a Wav2Vec2FeatureExtractor for ContentVec."""
    return Wav2Vec2FeatureExtractor(
        feature_size=1,
        sampling_rate=sample_rate,
        padding_value=0.0,
        do_normalize=True,
        return_attention_mask=False,
    )


def extract_hidden_states(
    outputs: Any,
    target_layer: int | None = None,
) -> torch.Tensor:
    """Extract hidden-state features from a single model output layer.

    Args:
        outputs: Model outputs with hidden_states attribute
        target_layer: Layer index to extract (uses config default if None)

    Returns:
        torch.Tensor: Hidden features of shape (T, D)
    """
    layer = target_layer if target_layer is not None else DEFAULT_SSL_FEATURE_CONFIG.target_layer
    hidden = outputs.hidden_states[layer]
    if hidden.dim() == 3 and hidden.shape[0] == 1:
        hidden = hidden.squeeze(0)
    return cast(torch.Tensor, hidden)
