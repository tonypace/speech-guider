"""Error selection endpoint for articulatory feedback."""

from fastapi import APIRouter, HTTPException
from app.models.schemas import SelectErrorRequest, SelectErrorResponse
from src.models.articulatory import ArticulatoryMapper

router = APIRouter()


@router.post("/api/select-error", response_model=SelectErrorResponse)
async def select_error(request: SelectErrorRequest):
    """
    Get articulatory feedback for a selected error.

    Args:
        request: Contains error_index and errors list

    Returns:
        Articulatory feedback with animation parameters
    """
    errors = request.errors
    idx = request.error_index

    if idx < 0 or idx >= len(errors):
        raise HTTPException(status_code=400, detail="Invalid error index")

    error = errors[idx]

    # Use articulatory mapper to generate descriptions
    mapper = ArticulatoryMapper()

    # Generate comparison descriptions
    target_phoneme = error.get("target_phoneme", "")
    predicted_phoneme = error.get("predicted_phoneme", "")

    # Get descriptions
    incorrect_desc = (
        f"**What you're doing:** Saying /{predicted_phoneme}/ instead of /{target_phoneme}/"
    )
    correct_desc = f"**What you should do:** Position tongue for /{target_phoneme}/"

    # Get animation parameters for both phonemes
    try:
        target_params = mapper.get_animation_params(target_phoneme)
        predicted_params = mapper.get_animation_params(predicted_phoneme)
    except Exception:
        # Fallback to default params
        target_params = {
            "tongueIndex": 0.5,
            "tongueDiameter": 0.5,
            "lipRounding": 0.5,
            "voicing": 1.0,
        }
        predicted_params = {
            "tongueIndex": 0.5,
            "tongueDiameter": 0.5,
            "lipRounding": 0.5,
            "voicing": 1.0,
        }

    # Determine highlight zone based on error type
    highlight_zone = "tongue_tip"  # Default
    if error.get("error_type") == "lip_rounding":
        highlight_zone = "lips"
    elif error.get("error_type") == "voicing":
        highlight_zone = "glottis"

    return SelectErrorResponse(
        incorrect_desc=incorrect_desc,
        correct_desc=correct_desc,
        animation_params={"left": predicted_params, "right": target_params},
        highlight_params={"zone": highlight_zone},
    )
