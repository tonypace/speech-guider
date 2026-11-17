"""Utility functions for handling audio file uploads."""

import asyncio
import logging
import os
import subprocess
import tempfile
from pathlib import Path
from typing import BinaryIO

import soundfile as sf
import torch
from fastapi import UploadFile

from app.services.concurrency import await_owned
from src.audio.processor import resample_audio, to_mono_float32
from src.services.desktop_assets import asset_override

logger = logging.getLogger(__name__)
MAX_UPLOAD_BYTES = 50 * 1024 * 1024


class AudioConversionError(Exception):
    """Raised when audio conversion fails."""

    pass


async def save_upload_to_temp(upload_file: UploadFile) -> str:
    """
    Save an uploaded file to a temporary location, converting to WAV if needed.

    Args:
        upload_file: FastAPI UploadFile object

    Returns:
        Path to the temporary WAV file

    Raises:
        AudioConversionError: If upload exceeds MAX_UPLOAD_BYTES or conversion to WAV fails
    """
    if upload_file.size is not None and upload_file.size > MAX_UPLOAD_BYTES:
        raise AudioConversionError(
            f"Uploaded audio exceeds maximum size of {MAX_UPLOAD_BYTES} bytes."
        )
    contents = await upload_file.read(MAX_UPLOAD_BYTES + 1)
    if len(contents) > MAX_UPLOAD_BYTES:
        raise AudioConversionError(
            f"Uploaded audio exceeds maximum size of {MAX_UPLOAD_BYTES} bytes."
        )
    task = asyncio.create_task(
        asyncio.to_thread(_save_contents_to_temp, contents, upload_file.filename or "audio.wav")
    )
    return await await_owned(task, discard=cleanup_temp_file)


def _save_contents_to_temp(contents: bytes, original_filename: str) -> str:
    """Own file creation and ffmpeg conversion entirely within one worker."""
    suffix = Path(original_filename).suffix.lower() or ".wav"

    # Create temp file with original extension
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
        tmp_file.write(contents)
        tmp_path = tmp_file.name

    logger.debug("Saved upload: %s (%d bytes, format: %s)", tmp_path, len(contents), suffix)

    # Convert to WAV if not already WAV
    if suffix not in (".wav", ".wave"):
        try:
            wav_path = _convert_to_wav(tmp_path)
            logger.debug("Converted %s -> %s", tmp_path, wav_path)
            return wav_path
        except AudioConversionError as e:
            logger.warning("Audio conversion failed for %s: %s", tmp_path, e)
            raise AudioConversionError(f"Could not convert {suffix} file to WAV: {e}") from e
        finally:
            cleanup_temp_file(tmp_path)

    return tmp_path


def _ffmpeg_command() -> str:
    configured = asset_override("SPEECH_GUIDER_FFMPEG_PATH", "bin/ffmpeg")
    if configured and (os.getenv("SPEECH_GUIDER_FFMPEG_PATH") or Path(configured).is_file()):
        return configured
    return "ffmpeg"


def _convert_to_wav(input_path: str) -> str:
    """Convert audio file to WAV using ffmpeg.

    Args:
        input_path: Path to input audio file

    Returns:
        Path to converted WAV file

    Raises:
        AudioConversionError: If conversion fails
    """
    wav_path = str(Path(input_path).with_suffix(".wav"))
    conversion_succeeded = False

    try:
        result = subprocess.run(
            [
                _ffmpeg_command(),
                "-y",
                "-i",
                input_path,
                "-ac",
                "1",
                "-ar",
                "16000",
                "-f",
                "wav",
                wav_path,
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0 and os.path.exists(wav_path):
            conversion_succeeded = True
            return wav_path
        else:
            error_msg = result.stderr if result.stderr else "ffmpeg returned non-zero exit code"
            raise AudioConversionError(f"ffmpeg conversion failed: {error_msg}")
    except subprocess.TimeoutExpired as e:
        raise AudioConversionError("ffmpeg conversion timed out after 30s") from e
    except FileNotFoundError as e:
        raise AudioConversionError("ffmpeg not found in PATH") from e
    except subprocess.SubprocessError as e:
        raise AudioConversionError(f"ffmpeg subprocess failed: {e}") from e
    finally:
        if not conversion_succeeded:
            cleanup_temp_file(wav_path)


def cleanup_temp_file(filepath: str) -> None:
    """Remove a temporary file if it exists.

    Args:
        filepath: Path to file to remove
    """
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
    except OSError as e:
        # Log but don't fail - cleanup is best effort
        logger.warning("Failed to cleanup temp file %s: %s", filepath, e)


def load_audio_tensor(source: str | BinaryIO, target_rate: int) -> tuple[torch.Tensor, int]:
    """Decode audio into the mono float tensor shared by both SSL paths."""
    audio_data, sample_rate = sf.read(source, dtype="float32")
    mono_audio = to_mono_float32(audio_data)
    resampled = resample_audio(mono_audio, int(sample_rate), target_rate)
    return torch.from_numpy(resampled).float(), target_rate
