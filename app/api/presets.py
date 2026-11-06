"""Presets API endpoints for Animation Lab."""

import logging

from fastapi import APIRouter, HTTPException

from app.models.schemas import PhonemePreset, PresetSaveRequest, PresetSaveResponse, PresetsResponse
from app.services.concurrency import run_blocking
from app.services.state import load_presets, save_preset

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/api/presets", response_model=PresetsResponse)
async def get_presets() -> PresetsResponse:
    """
    Get all phoneme presets for Animation Lab.

    Returns:
        Dictionary of all phoneme presets
    """
    presets = await run_blocking(load_presets)
    return PresetsResponse(
        phonemes={key: PhonemePreset.model_validate(value) for key, value in presets.items()}
    )


@router.post("/api/presets", response_model=PresetSaveResponse)
async def save_preset_endpoint(request: PresetSaveRequest) -> PresetSaveResponse:
    """
    Save a custom preset.

    Args:
        request: Preset save request with phoneme, params, and optional name

    Returns:
        Confirmation of save
    """
    preset_data = {"name": request.name or f"custom_{request.phoneme}", "params": request.params}

    try:
        await run_blocking(save_preset, request.phoneme, preset_data)
    except ValueError as exc:
        raise HTTPException(
            status_code=400, detail="Preset parameters must be finite numbers."
        ) from exc
    except OSError as exc:
        logger.exception("Preset persistence failed")
        raise HTTPException(status_code=500, detail="Could not save preset.") from exc

    return PresetSaveResponse(
        status="saved",
        phoneme=request.phoneme,
        message=f"Preset '{request.phoneme}' saved successfully",
    )
