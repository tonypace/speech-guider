"""Shared SSL backbone config and device utilities."""

from dataclasses import dataclass

import torch


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
    """Auto-detect best available torch device (MPS > CUDA > CPU)."""
    if torch.backends.mps.is_available():
        return "mps"
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"


def clear_torch_device_cache(device: str | None) -> None:
    """Free cached memory for a given device."""
    if device is None:
        return
    if device == "cuda" and torch.cuda.is_available():
        torch.cuda.empty_cache()
    elif device == "mps" and torch.backends.mps.is_available():
        torch.mps.empty_cache()
