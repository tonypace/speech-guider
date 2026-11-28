"""Error selection endpoint for articulatory feedback."""

import logging
from html import escape
from typing import Any

from fastapi import APIRouter, HTTPException

from app.models.schemas import SelectErrorRequest, SelectErrorResponse
from src.models.aai_adapter import parse_aai_animation_payload
from src.models.articulatory import (
    ArticulatoryMapper,
    default_articulatory_state,
    svg_state_to_dict,
)

router = APIRouter()
logger = logging.getLogger(__name__)


class AAIPayloadError(Exception):
    """Raised when AAI payload parsing fails."""

    pass


def _resolve_animation_params(
    phoneme: str,
    fallback_state: dict[str, float] | None,
    aai_payload: Any,
    mapper: ArticulatoryMapper,
) -> dict[str, float]:
    """Resolve canonical animation params from AAI payload or symbolic fallback."""

    if isinstance(aai_payload, dict):
        try:
            return parse_aai_animation_payload(aai_payload, fallback_state=fallback_state)
        except (KeyError, ValueError, TypeError) as exc:
            # Specific parsing errors - log and fall back to symbolic mapping
            logger.debug("Failed to parse AAI payload: %s", exc)
            # Re-raise as specific error type for better handling
            raise AAIPayloadError(f"Invalid AAI payload: {exc}") from exc

    return mapper.get_animation_params(phoneme)


@router.post("/api/select-error", response_model=SelectErrorResponse)
async def select_error(request: SelectErrorRequest) -> SelectErrorResponse:
    """
    Get articulatory feedback for a selected error.

    Args:
        request: Contains error_index and errors list

    Returns:
        Articulatory feedback with animation parameters
    """
    logger.debug(
        "select_error called with index=%d, errors_count=%d",
        request.error_index,
        len(request.errors),
    )

    errors = request.errors
    idx = request.error_index

    if idx < 0 or idx >= len(errors):
        logger.debug("Invalid error index: %d", idx)
        raise HTTPException(status_code=400, detail="Invalid error index")

    error = errors[idx]
    logger.debug("Selected error: %s", error)

    # Use articulatory mapper to generate descriptions
    mapper = ArticulatoryMapper()

    # Generate comparison descriptions
    target_phoneme = error.get("target_phoneme", "")
    predicted_phoneme = error.get("predicted_phoneme", "")
    logger.debug(
        "target_phoneme=%s, predicted_phoneme=%s",
        target_phoneme,
        predicted_phoneme,
    )

    # Get descriptions (using HTML instead of markdown)
    # Descriptions intentionally contain formatting markup; phonemes remain plain text.
    safe_target = escape(str(target_phoneme))
    safe_predicted = escape(str(predicted_phoneme))
    incorrect_desc = (
        f"<strong>What you're doing:</strong> Saying /{safe_predicted}/ instead of /{safe_target}/"
    )
    correct_desc = f"<strong>What you should do:</strong> Position tongue for /{safe_target}/"

    # Get animation parameters for both phonemes
    try:
        target_params = mapper.get_animation_params(target_phoneme)
        predicted_params = mapper.get_animation_params(predicted_phoneme)
        target_params = _resolve_animation_params(
            target_phoneme,
            target_params,
            error.get("animation_right"),
            mapper,
        )
        predicted_params = _resolve_animation_params(
            predicted_phoneme,
            predicted_params,
            error.get("animation_left"),
            mapper,
        )
        logger.debug("target_params from mapper: %s", target_params)
        logger.debug("predicted_params from mapper: %s", predicted_params)
    except AAIPayloadError as e:
        # AAI payload error - log specific message and fall back to default
        logger.debug("AAI payload error, using fallback: %s", e)
        target_params = svg_state_to_dict(default_articulatory_state())
        predicted_params = dict(target_params)
    except (KeyError, ValueError, TypeError) as e:
        # Data structure errors - log and fall back
        logger.debug("Data error getting animation params: %s", e)
        target_params = svg_state_to_dict(default_articulatory_state())
        predicted_params = dict(target_params)

    # Determine highlight zone based on error type or target phoneme
    highlight_zone = "tongue_tip"  # Default
    err_type = str(error.get("error_type") or error.get("category_id") or "")
    clean_target = str(target_phoneme).strip().strip("/")
    if err_type in {"lip_rounding", "labiodental_glide"} or clean_target in {
        "p",
        "b",
        "m",
        "f",
        "v",
        "w",
        "u",
        "o",
    }:
        highlight_zone = "lips"
    elif err_type == "voicing":
        highlight_zone = "glottis"
    elif err_type == "vowel_pairs" or clean_target in {
        "k",
        "g",
        "ɡ",
        "ŋ",
        "æ",
        "ɛ",
        "ɪ",
        "i",
        "ɑ",
        "ɔ",
        "ə",
    }:
        highlight_zone = "tongue_body"

    logger.debug("Returning select_error response for highlight zone: %s", highlight_zone)

    return SelectErrorResponse(
        incorrect_desc=incorrect_desc,
        correct_desc=correct_desc,
        animation_params={"left": predicted_params, "right": target_params},
        highlight_params={"zone": highlight_zone},
    )
