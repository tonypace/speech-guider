"""Comparison API endpoints for reference generation and student analysis."""

import io
from typing import Optional

import torch
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.utils.audio import load_audio_tensor
from src.audio.reference_tts import ReferenceAudio, TTSProviderFactory
from src.models.aai_adapter import AAIConversionMetadata, aai_to_canonical_states_batch
from src.models.ssl_common import DEFAULT_SSL_FEATURE_CONFIG
from src.services.comparison_cache import ComparisonCache, ReferenceAsset, get_comparison_cache
from src.services.model_cache import get_ssl_predictor

router = APIRouter()


class ReferenceAnimationRequest(BaseModel):
    """Request for reference animation generation."""

    target_text: str = Field(..., min_length=1, max_length=500, description="Text to synthesize")
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


class TrajectoryPayload(BaseModel):
    """Trajectory data for student or reference."""

    audio_base64: str
    audio_sample_rate: int
    audio_duration_seconds: float
    frame_rate: int
    frames: list[AnimationFrame]
    frame_count: int


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
    cache: Optional[ComparisonCache] = None,
) -> tuple[ReferenceAsset, bool]:
    """Generate reference audio and animation frames.

    Pipeline: text -> cache check -> TTS -> SSL predictor -> canonical frames
    """
    cache = cache or get_comparison_cache()
    cached = cache.get(text)
    if cached:
        print(f"[ComparisonAPI] Cache hit for: '{text[:50]}...'")
        return cached, True

    print(f"[ComparisonAPI] Cache miss, generating reference for: '{text[:50]}...'")

    reference_audio = TTSProviderFactory.create(tts_provider).synthesize(
        text, output_sample_rate=8000
    )

    audio_tensor = _prepare_reference_audio_tensor(reference_audio)
    trajectory = get_ssl_predictor().predict(
        audio_tensor, sample_rate=DEFAULT_SSL_FEATURE_CONFIG.sample_rate
    )

    frames = aai_to_canonical_states_batch(
        trajectory.numpy(),
        AAIConversionMetadata(normalization="speaker_z_normalized"),
    )

    asset = cache.put(
        text=text,
        audio_bytes=reference_audio.audio_bytes,
        audio_sample_rate=reference_audio.sample_rate,
        audio_duration=reference_audio.duration_seconds,
        audio_format=reference_audio.format,
        frame_rate=DEFAULT_SSL_FEATURE_CONFIG.frame_rate,
        frames=frames,
    )

    return asset, False


@router.post("/api/reference-animation", response_model=ReferenceAnimationResponse)
async def generate_reference_animation(request: ReferenceAnimationRequest):
    """Generate reference audio and articulatory animation from text.

    Uses TTS to synthesize audio, then runs SSL AAI predictor to extract
    articulatory trajectory, converts to canonical frames, and returns
    both compressed audio and animation frames.

    Results are cached by text content.
    """
    try:
        asset, was_cached = _generate_reference_asset(
            text=request.target_text,
            tts_provider=request.tts_provider,
        )

        import base64

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

    except Exception as e:
        print(f"[ComparisonAPI] Error generating reference: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate reference animation: {str(e)}",
        )


@router.get("/api/comparison-cache/stats")
async def get_cache_stats():
    """Get comparison cache statistics."""
    cache = get_comparison_cache()
    return cache.get_stats()


@router.delete("/api/comparison-cache")
async def clear_cache():
    """Clear all cached reference assets."""
    cache = get_comparison_cache()
    cache.clear()
    return {"status": "cleared"}
