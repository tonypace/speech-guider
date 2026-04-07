"""Text-to-speech service for generating reference audio from text.

Uses espeak-ng as the default provider, with a pluggable architecture
for future TTS upgrades. Includes audio downsampling and compression
for efficient storage and playback.
"""

import io
import subprocess
import tempfile
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np
import soundfile as sf


@dataclass
class ReferenceAudio:
    """Reference audio artifact with compressed audio data."""

    audio_bytes: bytes
    sample_rate: int
    duration_seconds: float
    format: str


class TTSProvider(ABC):
    """Abstract base class for text-to-speech providers."""

    @abstractmethod
    def synthesize(
        self,
        text: str,
        output_sample_rate: int = 8000,
    ) -> ReferenceAudio:
        """Synthesize audio from text.

        Args:
            text: Text to synthesize
            output_sample_rate: Target sample rate for output (default 8kHz)

        Returns:
            ReferenceAudio with compressed audio data
        """
        pass


class EspeakTTSProvider(TTSProvider):
    """espeak-ng based TTS provider.

    Uses espeak-ng command-line tool to synthesize audio.
    Outputs are downsampled and compressed for efficient storage.
    """

    ESPEAK_PATH = "/usr/local/bin/espeak-ng"
    DEFAULT_LANGUAGE = "en-us"

    def __init__(
        self,
        espeak_path: Optional[str] = None,
        language: str = DEFAULT_LANGUAGE,
    ) -> None:
        """Initialize espeak-ng TTS provider.

        Args:
            espeak_path: Path to espeak-ng binary
            language: Language code (default: en-us)
        """
        self.espeak_path = espeak_path or self.ESPEAK_PATH
        self.language = language
        self._verify_espeak()

    def _verify_espeak(self) -> None:
        """Verify espeak-ng is accessible."""
        try:
            result = subprocess.run(
                [self.espeak_path, "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode != 0:
                raise RuntimeError(f"espeak-ng command failed: {result.stderr}")
            print(f"[EspeakTTSProvider] Using: {result.stderr.strip()}")
        except FileNotFoundError:
            raise FileNotFoundError(
                f"espeak-ng not found at {self.espeak_path}. Install with: brew install espeak-ng"
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError("espeak-ng command timed out")

    def synthesize(
        self,
        text: str,
        output_sample_rate: int = 8000,
    ) -> ReferenceAudio:
        """Synthesize audio using espeak-ng.

        Generates WAV at 16kHz (espeak default), then downsamples
        to target rate and compresses.

        Args:
            text: Text to synthesize
            output_sample_rate: Target sample rate (default 8kHz)

        Returns:
            ReferenceAudio with compressed audio data
        """
        if not text.strip():
            raise ValueError("Text cannot be empty")

        # Create temporary WAV file for espeak output
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_wav:
            tmp_wav_path = tmp_wav.name

        try:
            # Generate audio using espeak-ng
            # espeak-ng outputs at 22050Hz by default, but we specify -s for speed
            args = [
                self.espeak_path,
                "-v",
                self.language,
                "-w",
                tmp_wav_path,  # Output to WAV file
                "-s",
                "150",  # Speed (words per minute)
                text,
            ]

            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                raise RuntimeError(f"espeak-ng synthesis failed: {result.stderr}")

            # Read the generated WAV file
            audio_data, orig_sample_rate = sf.read(tmp_wav_path, dtype="float32")

            # Ensure mono
            if len(audio_data.shape) > 1:
                audio_data = np.mean(audio_data, axis=1)

            # Downsample to target rate
            if output_sample_rate != orig_sample_rate:
                from scipy import signal

                # Calculate resampling ratio
                num_samples = int(len(audio_data) * output_sample_rate / orig_sample_rate)
                audio_data = signal.resample(audio_data, num_samples)

            # Convert to int16 for compressed storage
            audio_int16 = (audio_data * 32767).astype(np.int16)

            # Compress to OGG Vorbis for efficient storage
            # OGG is well-supported and provides good compression
            buffer = io.BytesIO()
            sf.write(
                buffer,
                audio_int16,
                output_sample_rate,
                format="OGG",
                subtype="VORBIS",
            )
            buffer.seek(0)
            compressed_bytes = buffer.read()

            duration = len(audio_int16) / output_sample_rate

            print(
                f"[EspeakTTSProvider] Synthesized: '{text[:50]}...' "
                f"({duration:.1f}s @ {output_sample_rate}Hz, "
                f"{len(compressed_bytes)} bytes compressed)"
            )

            return ReferenceAudio(
                audio_bytes=compressed_bytes,
                sample_rate=output_sample_rate,
                duration_seconds=duration,
                format="ogg",
            )

        finally:
            # Cleanup temporary file
            try:
                Path(tmp_wav_path).unlink(missing_ok=True)
            except Exception:
                pass


class TTSProviderFactory:
    """Factory for creating TTS providers."""

    _providers: dict[str, type[TTSProvider]] = {
        "espeak": EspeakTTSProvider,
    }

    @classmethod
    def create(
        cls,
        provider_name: str = "espeak",
        **kwargs,
    ) -> TTSProvider:
        """Create a TTS provider instance.

        Args:
            provider_name: Provider type (default: "espeak")
            **kwargs: Provider-specific arguments

        Returns:
            TTSProvider instance

        Raises:
            ValueError: If provider_name is unknown
        """
        if provider_name not in cls._providers:
            raise ValueError(f"Unknown TTS provider: {provider_name}")

        provider_class = cls._providers[provider_name]
        return provider_class(**kwargs)

    @classmethod
    def register_provider(
        cls,
        name: str,
        provider_class: type[TTSProvider],
    ) -> None:
        """Register a new TTS provider type.

        Args:
            name: Provider identifier
            provider_class: TTSProvider subclass
        """
        cls._providers[name] = provider_class
