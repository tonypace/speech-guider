"""Presets API endpoints for Animation Lab."""

from fastapi import APIRouter

from app.models.schemas import PresetSaveRequest, PresetSaveResponse, PresetsResponse
from app.services.state import load_presets, save_preset

router = APIRouter()


@router.get("/api/presets", response_model=PresetsResponse)
async def get_presets():
    """
    Get all phoneme presets for Animation Lab.

    Returns:
        Dictionary of all phoneme presets
    """
    presets = load_presets()
    return PresetsResponse(phonemes=presets)


@router.post("/api/presets", response_model=PresetSaveResponse)
async def save_preset_endpoint(request: PresetSaveRequest):
    """
    Save a custom preset.

    Args:
        request: Preset save request with phoneme, params, and optional name

    Returns:
        Confirmation of save
    """
    preset_data = {"name": request.name or f"custom_{request.phoneme}", "params": request.params}

    save_preset(request.phoneme, preset_data)

    return PresetSaveResponse(
        status="saved",
        phoneme=request.phoneme,
        message=f"Preset '{request.phoneme}' saved successfully",
    )
