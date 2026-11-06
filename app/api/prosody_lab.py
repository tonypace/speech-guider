"""Prosody Lab analysis endpoint."""

from __future__ import annotations

import logging

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.models.schemas import ProsodyLabAnalysisResponse
from app.services.concurrency import run_inference
from app.utils.audio import cleanup_temp_file, save_upload_to_temp
from src.audio.prosody_lab import analyze_prosody_recording

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/api/prosody-lab/analyze", response_model=ProsodyLabAnalysisResponse)
async def analyze_prosody_lab(audio: UploadFile = File(..., description="Recording to analyze")):
    """Analyze a short recording for rhythm and intonation feedback."""

    temp_path = await save_upload_to_temp(audio)
    try:
        analysis = await run_inference(analyze_prosody_recording, temp_path)
        return ProsodyLabAnalysisResponse(**analysis)
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Prosody analysis failed")
        raise HTTPException(
            status_code=500, detail="Prosody analysis failed. Please try another recording."
        ) from exc
    finally:
        cleanup_temp_file(temp_path)
