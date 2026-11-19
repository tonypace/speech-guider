"""Prosody Lab analysis endpoint."""

from __future__ import annotations

import logging

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from app.models.schemas import (
    ProsodyLabAnalysisResponse,
    ProsodyLabReferenceRequest,
    ProsodyLabReferenceResponse,
)
from app.services.concurrency import run_inference
from app.utils.audio import AudioConversionError, cleanup_temp_file, save_upload_to_temp
from src.audio.prosody_lab import analyze_prosody_recording, generate_prosody_reference

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/api/prosody-lab/analyze", response_model=ProsodyLabAnalysisResponse)
async def analyze_prosody_lab(
    audio: UploadFile = File(..., description="Recording to analyze"),
) -> JSONResponse:
    """Analyze a short recording for rhythm and intonation feedback."""

    temp_path: str | None = None
    try:
        temp_path = await save_upload_to_temp(audio)
        analysis = await run_inference(analyze_prosody_recording, temp_path)
        payload = ProsodyLabAnalysisResponse(**analysis).model_dump(mode="json")
        return JSONResponse(content=payload)
    except HTTPException:
        raise
    except AudioConversionError as exc:
        status_code = 413 if "maximum size" in str(exc).lower() else 400
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Prosody analysis failed")
        raise HTTPException(
            status_code=500, detail="Prosody analysis failed. Please try another recording."
        ) from exc
    finally:
        if temp_path is not None:
            cleanup_temp_file(temp_path)


@router.post("/api/prosody-lab/reference", response_model=ProsodyLabReferenceResponse)
async def create_prosody_lab_reference(
    request: ProsodyLabReferenceRequest,
) -> JSONResponse:
    """Synthesize a custom reference utterance and build a beat-mapped prosody phrase."""

    try:
        result = await run_inference(generate_prosody_reference, request.target_text)
        payload = ProsodyLabReferenceResponse(**result).model_dump(mode="json", by_alias=True)
        return JSONResponse(content=payload)
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Prosody reference generation failed")
        raise HTTPException(status_code=500, detail="Prosody reference generation failed.") from exc
