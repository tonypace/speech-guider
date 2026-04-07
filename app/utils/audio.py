"""Utility functions for handling audio file uploads."""

import io
import os
import tempfile
from pathlib import Path

from fastapi import UploadFile


async def save_upload_to_temp(upload_file: UploadFile, target_format: str = "wav") -> str:
    """
    Save an uploaded file to a temporary location, converting to WAV if needed.

    Args:
        upload_file: FastAPI UploadFile object
        target_format: Target format (default: wav for scipy compatibility)

    Returns:
        Path to the temporary file
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
    if suffix not in (".wav",):
        wav_path = _convert_to_wav(tmp_path)
        if wav_path:
            print(f"[audio] Converted {tmp_path} -> {wav_path}")
            # Clean up original temp file
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            return wav_path
        else:
            print(f"[audio] Conversion failed, trying to read original file anyway")

    return tmp_path


def _convert_to_wav(input_path: str) -> str | None:
    """Convert audio file to WAV using ffmpeg or pydub.

    Returns path to WAV file, or None if conversion failed.
    """
    try:
        # Try pydub first (uses ffmpeg under the hood)
        from pydub import AudioSegment

        audio = AudioSegment.from_file(input_path)
        audio = audio.set_frame_rate(16000).set_channels(1)

        wav_path = input_path.rsplit(".", 1)[0] + ".wav"
        audio.export(wav_path, format="wav")
        return wav_path
    except Exception as e:
        print(f"[audio] pydub conversion failed: {e}, trying ffmpeg directly...")

    # Fallback to direct ffmpeg
    wav_path = input_path.rsplit(".", 1)[0] + ".wav"
    try:
        import subprocess

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
            print(f"[audio] ffmpeg conversion failed: {result.stderr}")
    except Exception as e:
        print(f"[audio] ffmpeg conversion failed: {e}")

    return None


def cleanup_temp_file(filepath: str) -> None:
    """Remove a temporary file if it exists."""
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
    except Exception:
        pass  # Best effort cleanup


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
