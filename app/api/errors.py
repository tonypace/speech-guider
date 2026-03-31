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
    print(f"[select_error] Called with index: {request.error_index}")
    print(f"[select_error] Errors count: {len(request.errors)}")

    errors = request.errors
    idx = request.error_index

    if idx < 0 or idx >= len(errors):
        print(f"[select_error] Invalid index: {idx}")
        raise HTTPException(status_code=400, detail="Invalid error index")

    error = errors[idx]
    print(f"[select_error] Selected error: {error}")

    # Use articulatory mapper to generate descriptions
    mapper = ArticulatoryMapper()

    # Generate comparison descriptions
    target_phoneme = error.get("target_phoneme", "")
    predicted_phoneme = error.get("predicted_phoneme", "")
    print(
        f"[select_error] target_phoneme: {target_phoneme}, predicted_phoneme: {predicted_phoneme}"
    )

    # Get descriptions (using HTML instead of markdown)
    incorrect_desc = f"<strong>What you're doing:</strong> Saying /{predicted_phoneme}/ instead of /{target_phoneme}/"
    correct_desc = f"<strong>What you should do:</strong> Position tongue for /{target_phoneme}/"

    # Get animation parameters for both phonemes
    try:
        target_params = mapper.get_animation_params(target_phoneme)
        predicted_params = mapper.get_animation_params(predicted_phoneme)
        print(f"[select_error] target_params from mapper: {target_params}")
        print(f"[select_error] predicted_params from mapper: {predicted_params}")
    except Exception as e:
        print(f"[select_error] Exception getting animation params: {e}")
        # Fallback to default params
        target_params = {
            "lip_aperture": 10.0,
            "lip_protrusion": 10.0,
            "tongue_tip_constriction_location": 0.20,
            "tongue_tip_constriction_degree": 40.0,
            "lateral_tongue_drop": 0.0,
            "velic_aperture": 0.0,
            "tongue_body_constriction_location": 0.70,
            "tongue_body_constriction_degree": 30.0,
            "glottal_aperture": 0.0,
        }
        predicted_params = dict(target_params)

    # Determine highlight zone based on error type
    highlight_zone = "tongue_tip"  # Default
    if error.get("error_type") == "lip_rounding":
        highlight_zone = "lips"
    elif error.get("error_type") == "voicing":
        highlight_zone = "glottis"

    response_data = {
        "incorrect_desc": incorrect_desc,
        "correct_desc": correct_desc,
        "animation_params": {"left": predicted_params, "right": target_params},
        "highlight_params": {"zone": highlight_zone},
    }
    print(f"[select_error] Returning response: {response_data}")

    return SelectErrorResponse(**response_data)
