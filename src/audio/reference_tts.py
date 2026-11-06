"""Text-to-speech service for generating reference audio from text.

Uses omnivoice.cpp as the default provider via CLI subprocess.
Includes audio downsampling and compression for efficient storage and playback.

Required env vars:
    OMNIVOICE_TTS_PATH    Path to omnivoice-tts binary
    OMNIVOICE_MODEL_PATH  Path to quantized GGUF model
    OMNIVOICE_CODEC_PATH  Path to tokenizer codec GGUF
    OMNIVOICE_LANGUAGE    Language for synthesis (e.g. "English")
"""

import io
import os
import subprocess
import tempfile
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, cast

import numpy as np
import soundfile as sf


@dataclass
class ReferenceAudio:
    """Reference audio artifact with compressed audio data."""

    audio_bytes: bytes
    sample_rate: int
    duration_seconds: float
    format: str


def _require_file(path: str | None, env_name: str, label: str) -> str:
    """Validate and return a path from env/config.

    Raises ValueError if missing, FileNotFoundError if missing on disk.
    """
    if not path:
        raise ValueError(
            f"OmniVoiceTTSProvider missing required config: {env_name}. "
            f"Set the {env_name} environment variable."
        )
    if not os.path.isfile(path):
        raise FileNotFoundError(
            f"{label} not found at: {path}. Set {env_name} to the correct path."
        )
    return path


def file_identity(path: str | Path) -> tuple[str, int, int]:
    """Cheap local asset revision; do not hash multi-gigabyte weights per request."""
    resolved = Path(path).expanduser().resolve()
    info = resolved.stat()
    return str(resolved), info.st_size, info.st_mtime_ns


def _to_mono(audio_data: np.ndarray) -> np.ndarray:
    """Convert stereo to mono by averaging channels."""
    if len(audio_data.shape) > 1:
        return cast(np.ndarray, np.mean(audio_data, axis=1))
    return audio_data


def _resample_audio(audio_data: np.ndarray, orig_rate: int, target_rate: int) -> np.ndarray:
    """Resample audio to target sample rate."""
    if orig_rate == target_rate:
        return audio_data
    from scipy import signal

    num_samples = int(len(audio_data) * target_rate / orig_rate)
    return cast(np.ndarray, signal.resample(audio_data, num_samples))


def _compress_ogg(audio_data: np.ndarray, sample_rate: int) -> bytes:
    """Convert float32 samples to int16 OGG Vorbis bytes."""
    audio_int16 = (np.clip(audio_data, -1.0, 1.0) * 32767).astype(np.int16)
    buffer = io.BytesIO()
    sf.write(buffer, audio_int16, sample_rate, format="OGG", subtype="VORBIS")
    return buffer.getvalue()


class TTSProvider(ABC):
    """Abstract base class for text-to-speech providers."""

    def cache_identity(self) -> dict[str, Any]:
        """Custom providers should include every setting that affects synthesis."""
        return {"implementation": f"{type(self).__module__}.{type(self).__qualname__}"}

    @abstractmethod
    def synthesize(self, text: str, output_sample_rate: int = 8000) -> ReferenceAudio:
        pass


class OmniVoiceTTSProvider(TTSProvider):
    """omnivoice.cpp based TTS provider via CLI subprocess.

    All config sourced from environment variables.
    """

    def __init__(
        self,
        tts_path: Optional[str] = None,
        model_path: Optional[str] = None,
        codec_path: Optional[str] = None,
        language: Optional[str] = None,
    ) -> None:
        self.tts_path = _require_file(
            tts_path or os.environ.get("OMNIVOICE_TTS_PATH"),
            "OMNIVOICE_TTS_PATH",
            "omnivoice-tts binary",
        )
        self.model_path = _require_file(
            model_path or os.environ.get("OMNIVOICE_MODEL_PATH"),
            "OMNIVOICE_MODEL_PATH",
            "omnivoice model",
        )
        self.codec_path = _require_file(
            codec_path or os.environ.get("OMNIVOICE_CODEC_PATH"),
            "OMNIVOICE_CODEC_PATH",
            "omnivoice codec",
        )
        self.language = language or os.environ.get("OMNIVOICE_LANGUAGE", "English")

    def cache_identity(self) -> dict[str, Any]:
        identity = super().cache_identity()
        identity.update(
            {
                "language": self.language,
                "binary": file_identity(self.tts_path),
                "model": file_identity(self.model_path),
                "codec": file_identity(self.codec_path),
            }
        )
        return identity

    def synthesize(self, text: str, output_sample_rate: int = 8000) -> ReferenceAudio:
        if not text.strip():
            raise ValueError("Text cannot be empty")

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as wav:
            wav_path = wav.name

        try:
            result = subprocess.run(
                [
                    self.tts_path,
                    "--model",
                    self.model_path,
                    "--codec",
                    self.codec_path,
                    "--lang",
                    self.language,
                    "-o",
                    wav_path,
                ],
                input=text,
                capture_output=True,
                text=True,
                timeout=120,
            )
            if result.returncode != 0:
                raise RuntimeError(
                    f"omnivoice-tts failed (exit {result.returncode}): {result.stderr}"
                )

            audio_data, orig_rate = sf.read(wav_path, dtype="float32")
            audio_data = _resample_audio(_to_mono(audio_data), orig_rate, output_sample_rate)
            compressed = _compress_ogg(audio_data, output_sample_rate)
            duration = len(audio_data) / output_sample_rate

            return ReferenceAudio(
                audio_bytes=compressed,
                sample_rate=output_sample_rate,
                duration_seconds=duration,
                format="ogg",
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError("omnivoice-tts timed out after 120s")
        finally:
            try:
                Path(wav_path).unlink(missing_ok=True)
            except Exception:
                pass


class TTSProviderFactory:
    """Factory for creating TTS providers."""

    _providers: dict[str, type[TTSProvider]] = {
        "omnivoice": OmniVoiceTTSProvider,
    }

    @classmethod
    def create(cls, provider_name: str = "omnivoice", **kwargs) -> TTSProvider:
        if provider_name not in cls._providers:
            raise ValueError(f"Unknown TTS provider: {provider_name}")
        return cls._providers[provider_name](**kwargs)

    @classmethod
    def register_provider(cls, name: str, provider_class: type[TTSProvider]) -> None:
        cls._providers[name] = provider_class
