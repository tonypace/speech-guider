"""Utility functions for handling audio file uploads."""

import asyncio
import io
import os
import subprocess
import tempfile
from pathlib import Path
from typing import BinaryIO

import numpy as np
import soundfile as sf
import torch
from fastapi import UploadFile

from app.services.concurrency import await_owned


class AudioConversionError(Exception):
    """Raised when audio conversion fails."""

    pass


async def save_upload_to_temp(upload_file: UploadFile, target_format: str = "wav") -> str:
    """
    Save an uploaded file to a temporary location, converting to WAV if needed.

    Args:
        upload_file: FastAPI UploadFile object
        target_format: Target format (default: wav for scipy compatibility)

    Returns:
        Path to the temporary file

    Raises:
        AudioConversionError: If conversion to WAV fails and original format is unusable
    """
    contents = await upload_file.read()
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

    print(f"[audio] Saved upload: {tmp_path} ({len(contents)} bytes, format: {suffix})")

    # Convert to WAV if not already WAV
    if suffix not in (".wav", ".wave"):
        try:
            wav_path = _convert_to_wav(tmp_path)
            print(f"[audio] Converted {tmp_path} -> {wav_path}")
            # Clean up original temp file
            cleanup_temp_file(tmp_path)
            return wav_path
        except AudioConversionError as e:
            print(f"[audio] Conversion failed: {e}")
            # If conversion fails, try to use original file (may fail later if incompatible)
            # But for non-WAV formats, we should raise the error
            if suffix not in (".mp3", ".ogg", ".webm", ".m4a", ".flac"):
                # For non-audio formats, cleanup and raise
                cleanup_temp_file(tmp_path)
                raise AudioConversionError(f"Could not convert {suffix} file to WAV: {e}") from e
            print(f"[audio] Trying to read original {suffix} file anyway")

    return tmp_path


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
                "ffmpeg",
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
        print(f"[audio] Failed to cleanup temp file {filepath}: {e}")


async def upload_to_bytesio(upload_file: UploadFile) -> io.BytesIO:
    """
    Convert UploadFile to BytesIO for in-memory processing.

    Args:
        upload_file: FastAPI UploadFile object

    Returns:
        BytesIO buffer containing file contents
    """
    contents = await upload_file.read()
    return io.BytesIO(contents)


def load_audio_tensor(source: str | BinaryIO, target_rate: int) -> tuple[torch.Tensor, int]:
    """Decode audio into the mono float tensor shared by both SSL paths."""
    audio_data, sample_rate = sf.read(source, dtype="float32")
    if audio_data.ndim > 1:
        audio_data = np.mean(audio_data, axis=1)
    if sample_rate != target_rate:
        from scipy import signal

        num_samples = int(len(audio_data) * target_rate / sample_rate)
        audio_data = signal.resample(audio_data, num_samples)
    return torch.from_numpy(audio_data).float(), target_rate
