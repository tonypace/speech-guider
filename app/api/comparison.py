"""Comparison API endpoints for reference generation and student analysis."""

import base64
import io
import json
import logging
from typing import Any

import torch
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.api.settings import load_settings
from app.services.concurrency import run_inference
from app.utils.audio import load_audio_tensor
from src.audio.reference_tts import ReferenceAudio, TTSProviderFactory
from src.models.aai_adapter import r4_trajectory_to_canonical_frames
from src.models.ssl_common import DEFAULT_SSL_FEATURE_CONFIG, clear_torch_device_cache
from src.services.comparison_cache import ComparisonCache, ReferenceAsset, get_comparison_cache
from src.services.model_cache import get_ssl_cache_identity, get_ssl_predictor

router = APIRouter()
logger = logging.getLogger(__name__)
REFERENCE_TEXT_LIMIT = 1000


class ReferenceAnimationRequest(BaseModel):
    """Request for reference animation generation."""

    target_text: str = Field(
        ..., min_length=1, max_length=REFERENCE_TEXT_LIMIT, description="Text to synthesize"
    )
    tts_provider: str = Field(default="omnivoice", description="TTS provider to use")


class AnimationFrame(BaseModel):
    """Single frame of articulatory animation."""

    lip_aperture: float
    lip_protrusion: float
    tongue_tip_constriction_location: float
    tongue_tip_constriction_degree: float
    lateral_tongue_drop: float
    velic_aperture: float
    tongue_body_constriction_location: float
    tongue_body_constriction_degree: float
    glottal_aperture: float


class ReferenceAnimationResponse(BaseModel):
    """Response with reference audio and animation frames."""

    audio_base64: str = Field(..., description="Base64-encoded compressed audio (OGG)")
    audio_sample_rate: int = Field(default=8000, description="Audio sample rate in Hz")
    audio_duration_seconds: float = Field(..., description="Audio duration")
    audio_format: str = Field(default="ogg", description="Audio format")
    frame_rate: int = Field(default=50, description="Animation frame rate")
    frames: list[AnimationFrame] = Field(..., description="Animation frames")
    frame_count: int = Field(..., description="Number of frames")
    cached: bool = Field(default=False, description="Whether result was cached")


def _prepare_reference_audio_tensor(
    reference_audio: ReferenceAudio,
) -> torch.Tensor:
    """Decode compressed reference audio and prepare tensor for SSL predictor."""
    audio_tensor, _ = load_audio_tensor(
        io.BytesIO(reference_audio.audio_bytes), DEFAULT_SSL_FEATURE_CONFIG.sample_rate
    )
    return audio_tensor


def _generate_reference_asset(
    text: str,
    tts_provider: str = "omnivoice",
    cache: ComparisonCache | None = None,
    contact_enabled: bool = False,
    hinter_options: dict[str, Any] | None = None,
) -> tuple[ReferenceAsset, bool]:
    """Generate reference audio and animation frames.

    Pipeline: text -> cache check -> TTS -> SSL predictor -> canonical frames
    """
    cache = cache or get_comparison_cache()
    provider = TTSProviderFactory.create(tts_provider)
    resolved_hints = hinter_options or {}
    namespace = json.dumps(
        {
            "version": 2,
            "provider_name": tts_provider,
            "tts": provider.cache_identity(),
            "ssl": get_ssl_cache_identity(contact_enabled, **resolved_hints),
            "audio_sample_rate": 8000,
        },
        sort_keys=True,
    )
    cached = cache.get(text, namespace=namespace)
    if cached:
        logger.info("Comparison cache hit for: '%s...'", text[:50])
        return cached, True

    logger.info("Comparison cache miss, generating reference for: '%s...'", text[:50])

    reference_audio = provider.synthesize(text, output_sample_rate=8000)

    audio_tensor = _prepare_reference_audio_tensor(reference_audio)
    predictor = get_ssl_predictor()
    try:
        prediction = predictor.predict_with_metadata(
            audio_tensor,
            sample_rate=DEFAULT_SSL_FEATURE_CONFIG.sample_rate,
            contact_enabled=contact_enabled,
            **resolved_hints,
        )
    finally:
        dev = getattr(predictor, "device", None)
        if isinstance(dev, str):
            clear_torch_device_cache(dev)

    trajectory = prediction["tvs"]
    labiodental_tensor = prediction.get("labiodental_retraction")
    labiodental_array = labiodental_tensor.numpy() if labiodental_tensor is not None else None
    frames = r4_trajectory_to_canonical_frames(trajectory.numpy(), labiodental_array)

    asset = cache.put(
        text=text,
        audio_bytes=reference_audio.audio_bytes,
        audio_sample_rate=reference_audio.sample_rate,
        audio_duration=reference_audio.duration_seconds,
        audio_format=reference_audio.format,
        frame_rate=DEFAULT_SSL_FEATURE_CONFIG.frame_rate,
        frames=frames,
        namespace=namespace,
    )

    return asset, False


@router.post("/api/reference-animation", response_model=ReferenceAnimationResponse)
async def generate_reference_animation(
    request: ReferenceAnimationRequest,
) -> ReferenceAnimationResponse:
    """Generate reference audio and articulatory animation from text.

    Uses TTS to synthesize audio, then runs SSL AAI predictor to extract
    articulatory trajectory, converts to canonical frames, and returns
    both compressed audio and animation frames.

    Results are cached by text content.
    """
    if not request.target_text.strip():
        raise HTTPException(status_code=400, detail="Please enter reference text.")
    try:
        settings = load_settings()
        hinter_options = {
            "lip_enabled": settings.lip_enabled,
            "calibrate_enabled": settings.calibrate_enabled,
            "labiodental_enabled": settings.labiodental_enabled,
            "dental_enabled": settings.dental_enabled,
            "silence_mode": settings.silence_mode,
        }
        asset, was_cached = await run_inference(
            _generate_reference_asset,
            text=request.target_text,
            tts_provider=request.tts_provider,
            contact_enabled=settings.contact_enabled,
            hinter_options=hinter_options,
        )

        audio_b64 = base64.b64encode(asset.audio_bytes).decode("utf-8")

        animation_frames = [AnimationFrame(**frame) for frame in asset.frames]

        return ReferenceAnimationResponse(
            audio_base64=audio_b64,
            audio_sample_rate=asset.audio_sample_rate,
            audio_duration_seconds=asset.audio_duration,
            audio_format=asset.audio_format,
            frame_rate=asset.frame_rate,
            frames=animation_frames,
            frame_count=asset.frame_count,
            cached=was_cached,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Reference generation failed")
        raise HTTPException(
            status_code=500,
            detail="Failed to generate reference animation. Please check local model configuration.",
        ) from e
