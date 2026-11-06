"""Main analysis endpoints for pronunciation evaluation."""

import asyncio
import logging

import torch
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from app.api.sse import create_job_id, send_progress_update
from app.services.concurrency import run_blocking, run_with_semaphore
from app.services.jobs import claim_job, finish_job
from app.utils.audio import cleanup_temp_file, load_audio_tensor, save_upload_to_temp
from src.models.ssl_common import (
    DEFAULT_SSL_FEATURE_CONFIG,
    clear_torch_device_cache,
)
from src.services.model_cache import get_ssl_predictor

router = APIRouter()
logger = logging.getLogger(__name__)

# Cached device string for VRAM cleanup after inference
_ssl_device: str | None = None


class SSLAnalysisError(Exception):
    """Raised when SSL AAI analysis fails unexpectedly."""

    pass


def _ssl_aai_to_animation_state(
    audio_tensor: torch.Tensor,
    sample_rate: int,
    return_trajectory: bool = False,
) -> dict | tuple[dict, list[dict] | None, dict] | None:
    """Convert audio to animation state via SSL AAI predictor.

    Uses the same frozen R4 decoder and display normalization as reference audio.

    Args:
        audio_tensor: Audio tensor
        sample_rate: Audio sample rate in Hz
        return_trajectory: If True, also return full trajectory frames

    Returns:
        Canonical animation state dict, or (state, frames, meta) tuple if
        return_trajectory=True, or None if predictor unavailable/failed.
    """

    from src.models.aai_adapter import (
        AAIConversionMetadata,
        aai_to_canonical_state,
        aai_to_canonical_states_batch,
        decode_aai_row,
        representative_aai_pose,
    )

    try:
        predictor = get_ssl_predictor()
    except (FileNotFoundError, RuntimeError) as e:
        logger.debug(f"[_ssl_aai_to_animation_state] SSL predictor unavailable: {e}")
        return None

    metadata = AAIConversionMetadata(normalization="speaker_z_normalized")
    try:
        prediction = predictor.predict_with_metadata(audio_tensor, sample_rate)
        tvs_array = prediction["tvs"].numpy()
        ssl_meta = prediction["metadata"]

        # Get representative pose from trajectory
        if len(tvs_array) == 1:
            pose = decode_aai_row(tvs_array[0])
        else:
            pose = representative_aai_pose(
                tvs_array,
                normalization=metadata.normalization,
            )

        # Values are already in the normalized rig space; no denormalization
        animation_state = aai_to_canonical_state(pose, metadata=metadata)

        logger.debug("[_ssl_aai_to_animation_state] Generated animation state via SSL AAI path")

        if return_trajectory:
            frames = aai_to_canonical_states_batch(tvs_array, metadata)
            logger.debug(f"[_ssl_aai_to_animation_state] Generated {len(frames)} trajectory frames")
            return animation_state, frames, ssl_meta

        return animation_state

    except Exception as e:
        logger.exception("R4 articulatory prediction failed")
        raise SSLAnalysisError(f"SSL AAI prediction failed: {e}") from e


def try_primary_ssl_analysis(
    audio_tensor: torch.Tensor, sample_rate: int, return_trajectory: bool = False
) -> tuple[dict | None, list[dict] | None, dict]:
    """Run the SSL AAI analysis path.

    Returns:
        tuple: (animation_state, ssl_trajectory, ssl_meta)
        - animation_state: canonical animation state dict or None
        - ssl_trajectory: list of canonical frame dicts or None (if return_trajectory=True)
        - ssl_meta: integration metadata (decoder, device, layers, display clipping)
    """

    logger.debug("[try_primary_ssl_analysis] Attempting SSL AAI path...")

    try:
        result = _ssl_aai_to_animation_state(
            audio_tensor, sample_rate, return_trajectory=return_trajectory
        )
    except SSLAnalysisError as e:
        logger.warning(f"[try_primary_ssl_analysis] SSL AAI path failed: {e}")
        return None, None, {}

    if result is not None:
        logger.debug("[try_primary_ssl_analysis] SSL AAI path succeeded")
        if return_trajectory and isinstance(result, tuple):
            animation_state, ssl_trajectory, ssl_meta = result
            return animation_state, ssl_trajectory, ssl_meta
        if isinstance(result, dict):
            return result, None, {}

    # If we reach here, SSL AAI path failed
    logger.debug("[try_primary_ssl_analysis] SSL AAI path failed")
    return None, None, {}


def _load_and_preprocess_audio(audio_path: str) -> tuple[torch.Tensor, int]:
    """Load and preprocess audio file for analysis.

    Args:
        audio_path: Path to audio file

    Returns:
        Tuple of (audio_tensor, sample_rate)

    Raises:
        ValueError: If audio cannot be loaded or processed
    """
    return load_audio_tensor(audio_path, DEFAULT_SSL_FEATURE_CONFIG.sample_rate)


async def _run_analysis_pipeline(audio_path: str, target_text: str, job_id: str) -> dict:
    """Run the full analysis pipeline.

    Args:
        audio_path: Path to temporary audio file
        target_text: Target sentence to analyze
        job_id: Job ID for progress updates

    Returns:
        Analysis results dictionary with success status

    Raises:
        SSLAnalysisError: If SSL analysis fails
        Exception: For other unexpected errors (propagated)
    """
    # Step 1: Load audio
    await send_progress_update(job_id, 0.1, "Loading audio file...", "load_audio")

    from src.audio.processor import AudioContext, ProsodyAnalyzer

    audio_context = await run_blocking(AudioContext, audio_path)

    # Step 2: Analyze pronunciation
    await send_progress_update(job_id, 0.3, "Analyzing pronunciation...", "pronunciation")

    # Load audio in thread to avoid blocking
    audio_tensor, sample_rate = await run_blocking(_load_and_preprocess_audio, audio_path)

    ssl_animation_state = None
    ssl_trajectory = None
    ssl_meta: dict = {}
    ssl_error = None

    # Run SSL AAI analysis in thread to avoid blocking
    try:
        ssl_animation_state, ssl_trajectory, ssl_meta = await run_blocking(
            try_primary_ssl_analysis, audio_tensor, sample_rate, True
        )
        if ssl_animation_state is not None:
            global _ssl_device
            _ssl_device = get_ssl_predictor().device
            logger.debug(
                "[analyze] SSL AAI analysis succeeded, animation state and trajectory generated"
            )
        else:
            ssl_error = "SSL AAI predictor unavailable or failed"
            logger.warning(f"[analyze] {ssl_error}")
    except SSLAnalysisError as e:
        ssl_error = str(e)
        logger.warning(f"[analyze] SSL AAI analysis failed: {e}")
    except Exception as e:
        ssl_error = f"Unexpected SSL analysis error: {e}"
        logger.error(f"[analyze] Unexpected SSL analysis error: {e}")

    # Clear device cache after SSL inference to free VRAM
    if _ssl_device:
        await run_blocking(clear_torch_device_cache, _ssl_device)

    # Step 3: Extract prosody metrics
    await send_progress_update(job_id, 0.6, "Extracting prosody metrics...", "prosody")

    prosody_analyzer = ProsodyAnalyzer(audio_context)

    # Run prosody analysis without phoneme alignment (alignment requires phoneme model)
    logger.debug("[analyze] Running prosody analysis without alignment timestamps")
    prosody_metrics = await run_blocking(
        prosody_analyzer.analyze_complete, vowel_timestamps=[], word_timestamps=[]
    )

    if prosody_metrics:
        logger.debug(f"[analyze] prosody_metrics type: {type(prosody_metrics)}")
        logger.debug(f"[analyze] prosody_metrics.pitch: {prosody_metrics.pitch}")
        logger.debug(f"[analyze] prosody_metrics.rhythm: {prosody_metrics.rhythm}")
        if prosody_metrics.rhythm:
            logger.debug(f"[analyze] nPVI value: {prosody_metrics.rhythm.npvi}")

    # Step 4: Generate feedback
    await send_progress_update(job_id, 0.9, "Generating feedback...", "feedback")

    feedback = _generate_comprehensive_feedback(prosody_metrics)
    if ssl_animation_state is None:
        feedback = feedback.replace(
            "Articulatory analysis via ContentVec-L7 + R4",
            "Articulatory analysis unavailable; prosody feedback only",
        )

    # Serialize trajectory if available
    serialized_trajectory = None
    if ssl_trajectory:
        serialized_trajectory = {
            "frame_rate": DEFAULT_SSL_FEATURE_CONFIG.frame_rate,
            "frame_count": len(ssl_trajectory),
            "frames": ssl_trajectory,
        }

    result = {
        "feedback": feedback,
        "prosody": serialize_prosody(prosody_metrics) if prosody_metrics else None,
        "ssl_animation_state": ssl_animation_state,
        "ssl_trajectory": serialized_trajectory,
        "integration_meta": ssl_meta,
        "success": True,
        "message": "Analysis complete",
    }

    if ssl_error:
        result["ssl_warning"] = (
            "Articulatory analysis unavailable; prosody feedback is still available."
        )

    return result


def _get_pitch_range_label(range_semitones: float) -> str:
    """Return a student-friendly pitch range label."""
    if range_semitones < 6:
        return "a little flat"
    elif range_semitones <= 12:
        return "nice variety"
    else:
        return "very expressive"


def _get_pitch_range_coaching(range_semitones: float) -> str:
    """Return coaching text for pitch range."""
    if range_semitones < 6:
        return "try adding more movement"
    elif range_semitones <= 12:
        return "good contrast"
    else:
        return "strong range"


def _get_mean_pitch_label(mean_f0_hz: float) -> str:
    """Return a student-friendly mean pitch label."""
    if mean_f0_hz < 150:
        return "low voice"
    elif mean_f0_hz <= 220:
        return "middle voice"
    else:
        return "high voice"


def _get_mean_pitch_coaching(mean_f0_hz: float) -> str:
    """Return coaching text for mean pitch."""
    if mean_f0_hz < 150:
        return "calm and grounded"
    elif mean_f0_hz <= 220:
        return "balanced"
    else:
        return "bright and energetic"


def _get_npvi_label(npvi: float) -> tuple[str, str]:
    """Return (label, color) for nPVI. Color is 'red', 'amber', or 'green'."""
    if npvi <= 25:
        return "more flat", "red"
    elif npvi <= 45:
        return "mixed rhythm", "amber"
    else:
        return "strong rhythm", "green"


def _get_npvi_coaching(npvi: float) -> str:
    """Return coaching text for nPVI."""
    if npvi <= 25:
        return "rhythm is still very even"
    elif npvi <= 45:
        return "getting closer to natural stress timing"
    else:
        return "nice stress contrast"


def _build_npvi_bar_html(npvi: float) -> str:
    """Build an inline colored nPVI bar HTML."""
    label, color = _get_npvi_label(npvi)
    coaching = _get_npvi_coaching(npvi)
    color_map = {
        "red": "#ef4444",
        "amber": "#f59e0b",
        "green": "#22c55e",
    }
    bar_color = color_map.get(color, "#9ca3af")
    bar_html = (
        f'<div style="display:flex;align-items:center;gap:8px;margin-top:4px;">'
        f'<div style="flex:1;height:8px;background:#e5e7eb;border-radius:4px;overflow:hidden;">'
        f'<div style="width:100%;height:100%;background:{bar_color};border-radius:4px;"></div>'
        f"</div>"
        f'<span style="font-size:12px;color:{bar_color};font-weight:600;">{label} — {coaching}</span>'
        f"</div>"
    )
    return bar_html


def _voice_quality_payload(vq) -> dict | None:
    """Serialize voice quality to dict if any metric is non-zero."""
    if vq is None:
        return None
    payload = {
        "jitter_local": vq.jitter_local,
        "shimmer_local": vq.shimmer_local,
        "cpps": vq.cpps,
        "spectral_tilt": vq.spectral_tilt,
    }
    return payload if any(payload.values()) else None


def serialize_prosody(prosody):
    """Convert ProsodyMetrics to dict."""
    pitch = prosody.pitch if prosody else None
    rhythm = prosody.rhythm if prosody else None
    stress = prosody.stress if prosody else None
    vq = prosody.voice_quality if prosody else None

    pitch_mean = pitch.mean_f0 if pitch else 0
    pitch_range = pitch.f0_range if pitch else 0
    pitch_var = pitch.std_f0 if pitch else 0
    npvi = rhythm.npvi if rhythm else 0

    return {
        "pitch_mean": pitch_mean,
        "pitch_range": pitch_range,
        "pitch_variability": pitch_var,
        "npvi": npvi,
        "stress_pattern": stress.primary_stress_word if stress else None,
        "pitch_range_semitones": pitch.range_semitones if pitch else 0.0,
        "pitch_range_label": _get_pitch_range_label(pitch.range_semitones if pitch else 0.0),
        "pitch_range_coaching": _get_pitch_range_coaching(pitch.range_semitones if pitch else 0.0),
        "mean_pitch_label": _get_mean_pitch_label(pitch_mean),
        "mean_pitch_coaching": _get_mean_pitch_coaching(pitch_mean),
        "npvi_label": _get_npvi_label(npvi)[0],
        "npvi_color": _get_npvi_label(npvi)[1],
        "npvi_coaching": _get_npvi_coaching(npvi),
        "npvi_bar_html": _build_npvi_bar_html(npvi),
        "voice_quality": _voice_quality_payload(vq),
    }


def _generate_comprehensive_feedback(prosody_metrics):
    """Generate comprehensive feedback text."""
    logger.debug(f"[feedback] prosody_metrics: {prosody_metrics}")

    sections = []

    # Pronunciation summary
    # NOTE: Phoneme-level error detection requires a phoneme CTC model.
    # This feature is currently non-functional pending model integration.
    sections.append("<strong>Pronunciation:</strong> Articulatory analysis via ContentVec-L7 + R4")

    # Prosody summary with student-friendly labels
    if prosody_metrics:
        sections.append("<br><strong>Prosody:</strong>")
        if prosody_metrics.pitch:
            f0_range = prosody_metrics.pitch.f0_range
            f0_mean = prosody_metrics.pitch.mean_f0
            range_label = _get_pitch_range_label(prosody_metrics.pitch.range_semitones)
            range_coaching = _get_pitch_range_coaching(prosody_metrics.pitch.range_semitones)
            pitch_label = _get_mean_pitch_label(f0_mean)
            pitch_coaching = _get_mean_pitch_coaching(f0_mean)
            sections.append(f"- Pitch range: {range_label} — {range_coaching} ({f0_range:.1f} Hz)")
            sections.append(f"- Mean pitch: {pitch_label} — {pitch_coaching} ({f0_mean:.1f} Hz)")
        if prosody_metrics.rhythm:
            npvi = prosody_metrics.rhythm.npvi
            npvi_label, npvi_color = _get_npvi_label(npvi)
            npvi_coaching = _get_npvi_coaching(npvi)
            sections.append(f"- Rhythm (nPVI {npvi:.2f})")
            sections.append(f"  {npvi_label} — {npvi_coaching}")
            sections.append(_build_npvi_bar_html(npvi))
            logger.debug(f"[feedback] nPVI value being used: {npvi:.2f}")

    result = "<br>".join(sections)
    logger.debug(f"[feedback] Final feedback string: {result}")
    return result


@router.post("/api/analyze")
async def analyze_audio(
    audio: UploadFile = File(..., description="Audio file to analyze"),
    target_text: str = Form(..., description="Target sentence to practice"),
    job_id: str | None = Form(default=None, description="Optional reserved analysis job ID"),
):
    """
    Main analysis endpoint - performs articulatory and prosody analysis.

    Args:
        audio: Audio file (WAV format recommended)
        target_text: The target sentence the user was practicing

    Returns:
        Analysis results with articulatory feedback, prosody metrics, and feedback.
        Uses local ContentVec-L7 + frozen R4 for articulatory inference.
    """
    if not target_text.strip():
        raise HTTPException(status_code=400, detail="Please enter the target sentence.")

    if not audio.filename:
        raise HTTPException(status_code=400, detail="Please upload an audio file.")

    job = claim_job(job_id or create_job_id())
    temp_path: str | None = None
    try:
        temp_path = await save_upload_to_temp(audio)
        result = await run_with_semaphore(
            _run_analysis_pipeline(temp_path, target_text, job.job_id)
        )
        result["job_id"] = job.job_id
        response = JSONResponse(content=result)
        finish_job(job, "complete", "Analysis complete!")
        return response
    except asyncio.CancelledError:
        finish_job(job, "cancelled", "Analysis request cancelled")
        raise
    except HTTPException:
        finish_job(job, "failed", "Analysis could not be started")
        raise
    except Exception:
        logger.exception("Analysis failed for job %s", job.job_id)
        finish_job(job, "failed", "Analysis failed. Please try another recording.")
        return JSONResponse(
            content={
                "success": False,
                "error": "Analysis failed. Please try another recording.",
                "job_id": job.job_id,
            },
            status_code=500,
        )
    finally:
        if temp_path is not None:
            cleanup_temp_file(temp_path)
