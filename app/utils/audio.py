"""Utility functions for handling audio file uploads."""

import importlib
import io
import os
import subprocess
import tempfile
from pathlib import Path

from fastapi import UploadFile


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
    original_filename = upload_file.filename or "audio.wav"
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
    """Convert audio file to WAV using pydub or ffmpeg.

    Args:
        input_path: Path to input audio file

    Returns:
        Path to converted WAV file

    Raises:
        AudioConversionError: If conversion fails
    """
    wav_path = input_path.rsplit(".", 1)[0] + ".wav"

    # Try pydub first (uses ffmpeg under the hood)
    try:
        pydub = importlib.import_module("pydub")
        AudioSegment = pydub.AudioSegment

        audio = AudioSegment.from_file(input_path)
        audio = audio.set_frame_rate(16000).set_channels(1)
        audio.export(wav_path, format="wav")

        if os.path.exists(wav_path):
            return wav_path
    except ImportError:
        print("[audio] pydub not available, trying ffmpeg directly...")
    except (OSError, ValueError) as e:
        print(f"[audio] pydub conversion failed: {e}, trying ffmpeg directly...")

    # Fallback to direct ffmpeg
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
