"""Comparison API endpoints for reference generation and student analysis."""

import io
from typing import Optional

import numpy as np
import soundfile as sf
import torch
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.audio.reference_tts import TTSProviderFactory
from src.models.aai_adapter import (
    AAIConversionMetadata,
    aai_to_canonical_state,
    decode_aai_row,
)
from src.models.ssl_aai_predictor import SSLAAIPredictor
from src.services.comparison_cache import ComparisonCache, ReferenceAsset, get_comparison_cache

router = APIRouter()


class ReferenceAnimationRequest(BaseModel):
    """Request for reference animation generation."""

    target_text: str = Field(..., min_length=1, max_length=500, description="Text to synthesize")
    tts_provider: str = Field(default="espeak", description="TTS provider to use")


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


def _ssl_trajectory_to_canonical_frames(
    trajectory: torch.Tensor,
    sample_rate: int = 16000,
) -> list[dict]:
    """Convert SSL predictor trajectory to canonical animation frames.

    Args:
        trajectory: Tensor of shape (T, 9) with robust_01 AAI TVs (values in [0, 1])
        sample_rate: Original audio sample rate

    Returns:
        List of canonical animation state dictionaries
    """
    frames = []
    metadata = AAIConversionMetadata(normalization="robust_01")

    for i in range(trajectory.shape[0]):
        # Get robust_01 TV row
        tv_row = trajectory[i].tolist()

        # Decode to named tract variables
        tract_vars = decode_aai_row(tv_row)

        # Convert to canonical animation state
        canonical = aai_to_canonical_state(tract_vars, metadata=metadata)

        frames.append(canonical)

    return frames


def _generate_reference_asset(
    text: str,
    tts_provider: str = "espeak",
    cache: Optional[ComparisonCache] = None,
) -> ReferenceAsset:
    """Generate reference audio and animation frames.

    Pipeline:
        text -> TTS -> audio -> SSL predictor -> AAI TVs -> canonical frames

    Args:
        text: Target text to synthesize
        tts_provider: TTS provider name
        cache: Optional cache instance

    Returns:
        ReferenceAsset with audio and frames
    """
    # Check cache first
    cache = cache or get_comparison_cache()
    cached = cache.get(text)
    if cached:
        print(f"[ComparisonAPI] Cache hit for: '{text[:50]}...'")
        return cached

    print(f"[ComparisonAPI] Cache miss, generating reference for: '{text[:50]}...'")

    # Step 1: Generate reference audio via TTS
    tts = TTSProviderFactory.create(tts_provider)
    reference_audio = tts.synthesize(text, output_sample_rate=8000)

    # Step 2: Prepare audio for SSL predictor (needs 16kHz)
    # Decode compressed audio and resample to 16kHz
    audio_buffer = io.BytesIO(reference_audio.audio_bytes)
    audio_data, orig_rate = sf.read(audio_buffer, dtype="float32")

    # Resample to 16kHz for SSL predictor
    if orig_rate != 16000:
        from scipy import signal

        num_samples = int(len(audio_data) * 16000 / orig_rate)
        audio_data = signal.resample(audio_data, num_samples)

    # Ensure mono
    if len(audio_data.shape) > 1:
        audio_data = np.mean(audio_data, axis=1)

    # Convert to tensor
    audio_tensor = torch.from_numpy(audio_data).float()

    # Step 3: Run SSL predictor to get AAI trajectory
    predictor = SSLAAIPredictor()
    predictor.load()

    try:
        trajectory = predictor.predict(audio_tensor, sample_rate=16000)
        # trajectory shape: (T, 9) robust_01 normalized AAI TVs (values in [0, 1])

        # Step 4: Convert trajectory to canonical frames
        frames = _ssl_trajectory_to_canonical_frames(trajectory)

        # Step 5: Store in cache
        asset = cache.put(
            text=text,
            audio_bytes=reference_audio.audio_bytes,
            audio_sample_rate=reference_audio.sample_rate,
            audio_duration=reference_audio.duration_seconds,
            audio_format=reference_audio.format,
            frame_rate=50,  # SSL predictor frame rate
            frames=frames,
        )

        print(
            f"[ComparisonAPI] Generated reference: "
            f"{len(frames)} frames, {reference_audio.duration_seconds:.1f}s audio"
        )

        return asset

    finally:
        predictor.cleanup()


@router.post("/api/reference-animation", response_model=ReferenceAnimationResponse)
async def generate_reference_animation(request: ReferenceAnimationRequest):
    """Generate reference audio and articulatory animation from text.

    Uses TTS to synthesize audio, then runs SSL AAI predictor to extract
    articulatory trajectory, converts to canonical frames, and returns
    both compressed audio and animation frames.

    Results are cached by text content.
    """
    try:
        asset = _generate_reference_asset(
            text=request.target_text,
            tts_provider=request.tts_provider,
        )

        # Encode audio to base64 for JSON response
        import base64

        audio_b64 = base64.b64encode(asset.audio_bytes).decode("utf-8")

        # Convert frames to Pydantic models
        animation_frames = [AnimationFrame(**frame) for frame in asset.frames]

        return ReferenceAnimationResponse(
            audio_base64=audio_b64,
            audio_sample_rate=asset.audio_sample_rate,
            audio_duration_seconds=asset.audio_duration,
            audio_format=asset.audio_format,
            frame_rate=asset.frame_rate,
            frames=animation_frames,
            frame_count=asset.frame_count,
            cached=False,  # TODO: track if was actually cached
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
