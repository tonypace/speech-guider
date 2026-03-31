"""Prosody Lab analysis endpoint."""

from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.models.schemas import ProsodyLabAnalysisResponse
from app.utils.audio import cleanup_temp_file, save_upload_to_temp
from src.audio.prosody_lab import analyze_prosody_recording

router = APIRouter()


@router.post("/api/prosody-lab/analyze", response_model=ProsodyLabAnalysisResponse)
async def analyze_prosody_lab(audio: UploadFile = File(..., description="Recording to analyze")):
    """Analyze a short recording for rhythm and intonation feedback."""

    temp_path = await save_upload_to_temp(audio)
    try:
        analysis = analyze_prosody_recording(temp_path)
        return ProsodyLabAnalysisResponse(**analysis)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Prosody analysis failed: {exc}") from exc
    finally:
        cleanup_temp_file(temp_path)
