"""Utility functions for handling audio file uploads."""

import io
import os
import tempfile
from pathlib import Path

from fastapi import UploadFile


async def save_upload_to_temp(upload_file: UploadFile) -> str:
    """
    Save an uploaded file to a temporary location.

    Args:
        upload_file: FastAPI UploadFile object

    Returns:
        Path to the temporary file
    """
    # Read the uploaded file contents
    contents = await upload_file.read()

    # Get file extension from filename or content type
    original_filename = upload_file.filename or "audio.wav"
    suffix = Path(original_filename).suffix or ".wav"

    # Create temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
        tmp_file.write(contents)
        return tmp_file.name


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
