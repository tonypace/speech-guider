"""Main analysis endpoints for pronunciation evaluation."""

import asyncio
import logging
import os

import numpy as np
import torch
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from app.api.sse import create_job_id, send_progress_update
from app.services.concurrency import run_with_semaphore
from app.utils.audio import cleanup_temp_file, save_upload_to_temp

router = APIRouter()
logger = logging.getLogger(__name__)

# Cached model instances
_cached_ssl_predictor = None


class SSLAnalysisError(Exception):
    """Raised when SSL AAI analysis fails unexpectedly."""

    pass


def get_ssl_predictor():
    """Get or create cached SSL AAI predictor instance."""

    global _cached_ssl_predictor
    if _cached_ssl_predictor is None:
        from src.models.ssl_aai_predictor import SSLAAIPredictor

        checkpoint_path = os.getenv("SSL_AAI_CHECKPOINT_PATH")
        logger.info("[get_ssl_predictor] Initializing SSL AAI predictor (first time)...")
        if checkpoint_path:
            logger.info(f"[get_ssl_predictor] Using checkpoint: {checkpoint_path}")
        else:
            logger.info("[get_ssl_predictor] Using default checkpoint path")

        _cached_ssl_predictor = SSLAAIPredictor(checkpoint_path=checkpoint_path)
        _cached_ssl_predictor.load()
        logger.info("[get_ssl_predictor] SSL AAI predictor initialized and cached.")
    return _cached_ssl_predictor


def _ssl_aai_to_animation_state(
    audio_tensor: torch.Tensor,
    sample_rate: int,
    return_trajectory: bool = False,
) -> dict | tuple[dict, list[dict]] | None:
    """Convert audio to animation state via SSL AAI predictor.

    Uses ContentVec + DANN predictor with robust_01 normalization.

    Args:
        audio_tensor: Audio tensor
        sample_rate: Audio sample rate in Hz
        return_trajectory: If True, also return full trajectory frames

    Returns:
        Canonical animation state dict, or (state, frames) tuple if return_trajectory=True,
        or None if predictor unavailable/failed.
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

    try:
        logger.debug(
            f"[_ssl_aai_to_animation_state] Calling predictor.predict with audio shape={audio_tensor.shape}, sr={sample_rate}"
        )
        tvs_tensor = predictor.predict(audio_tensor, sample_rate)
        logger.debug(
            f"[_ssl_aai_to_animation_state] Prediction succeeded: shape={tvs_tensor.shape}"
        )
        tvs_array = tvs_tensor.numpy()

        # Get representative pose from trajectory
        # For now, use the first frame if short, or median across trajectory
        if len(tvs_array) == 1:
            pose = decode_aai_row(tvs_array[0])
        else:
            pose = representative_aai_pose(
                tvs_array,  # Pass numpy array directly
                normalization="robust_01",
            )

        # Convert to canonical animation state
        # robust_01 means values are already in [0,1], no denormalization needed
        metadata = AAIConversionMetadata(normalization="robust_01")
        animation_state = aai_to_canonical_state(pose, metadata=metadata)

        logger.debug("[_ssl_aai_to_animation_state] Generated animation state via SSL AAI path")

        if return_trajectory:
            # Convert full trajectory using vectorized batch conversion
            frames = aai_to_canonical_states_batch(tvs_array, metadata)
            logger.debug(f"[_ssl_aai_to_animation_state] Generated {len(frames)} trajectory frames")
            return animation_state, frames

        return animation_state

    except Exception as e:
        import traceback

        tb = traceback.format_exc()
        msg = f"[_ssl_aai_to_animation_state] SSL AAI prediction failed: {e}\n{tb}"
        logger.error(msg)
        with open("/tmp/ssl_debug.log", "a") as f:
            f.write(msg + "\n" + "=" * 80 + "\n")
        raise SSLAnalysisError(f"SSL AAI prediction failed: {e}") from e


def try_primary_ssl_analysis(
    audio_tensor: torch.Tensor, sample_rate: int, return_trajectory: bool = False
) -> tuple[dict | None, list[dict] | None]:
    """Run the SSL AAI analysis path.

    Returns:
        tuple: (animation_state, ssl_trajectory)
        - animation_state: canonical animation state dict or None
        - ssl_trajectory: list of canonical frame dicts or None (if return_trajectory=True)
    """

    logger.debug("[try_primary_ssl_analysis] Attempting SSL AAI path...")

    result = _ssl_aai_to_animation_state(
        audio_tensor, sample_rate, return_trajectory=return_trajectory
    )

    if result is not None:
        logger.debug("[try_primary_ssl_analysis] SSL AAI path succeeded")
        if return_trajectory and isinstance(result, tuple):
            animation_state, ssl_trajectory = result
            return animation_state, ssl_trajectory
        if isinstance(result, dict):
            return result, None

    # If we reach here, SSL AAI path failed
    logger.debug("[try_primary_ssl_analysis] SSL AAI path failed")
    return None, None


def _load_and_preprocess_audio(audio_path: str) -> tuple[torch.Tensor, int]:
    """Load and preprocess audio file for analysis.

    Args:
        audio_path: Path to audio file

    Returns:
        Tuple of (audio_tensor, sample_rate)

    Raises:
        ValueError: If audio cannot be loaded or processed
    """
    import soundfile as sf

    audio_data, sample_rate = sf.read(audio_path, dtype="float32")

    # Convert to mono if stereo
    if len(audio_data.shape) > 1:
        audio_data = np.mean(audio_data, axis=1)

    # Resample to 16kHz if needed
    if sample_rate != 16000:
        import scipy.signal as signal

        num_samples = int(len(audio_data) * 16000 / sample_rate)
        audio_data = signal.resample(audio_data, num_samples)
        sample_rate = 16000

    audio_tensor = torch.from_numpy(audio_data).float()
    return audio_tensor, sample_rate


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

    audio_context = AudioContext(audio_path)

    # Step 2: Analyze pronunciation
    await send_progress_update(job_id, 0.3, "Analyzing pronunciation...", "pronunciation")

    # Load audio in thread to avoid blocking
    audio_tensor, sample_rate = await asyncio.to_thread(_load_and_preprocess_audio, audio_path)

    ssl_animation_state = None
    ssl_trajectory = None
    ssl_error = None

    # Run SSL AAI analysis in thread to avoid blocking
    try:
        ssl_animation_state, ssl_trajectory = await asyncio.to_thread(
            try_primary_ssl_analysis, audio_tensor, sample_rate, True
        )
        if ssl_animation_state is not None:
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

    try:
        predictor = get_ssl_predictor()
        if predictor.device == "mps" and torch.backends.mps.is_available():
            torch.mps.empty_cache()
        elif predictor.device == "cuda" and torch.cuda.is_available():
            torch.cuda.empty_cache()
    except (FileNotFoundError, RuntimeError) as e:
        logger.debug(f"[analyze] SSL predictor unavailable for cache cleanup: {e}")

    # Step 3: Extract prosody metrics
    await send_progress_update(job_id, 0.6, "Extracting prosody metrics...", "prosody")

    prosody_analyzer = ProsodyAnalyzer(audio_context)

    # Run prosody analysis without phoneme alignment (alignment requires phoneme model)
    logger.debug("[analyze] Running prosody analysis without alignment timestamps")
    prosody_metrics = prosody_analyzer.analyze_complete(vowel_timestamps=[], word_timestamps=[])

    if prosody_metrics:
        logger.debug(f"[analyze] prosody_metrics type: {type(prosody_metrics)}")
        logger.debug(f"[analyze] prosody_metrics.pitch: {prosody_metrics.pitch}")
        logger.debug(f"[analyze] prosody_metrics.rhythm: {prosody_metrics.rhythm}")
        if prosody_metrics.rhythm:
            logger.debug(f"[analyze] nPVI value: {prosody_metrics.rhythm.npvi}")

    # Step 4: Generate feedback
    await send_progress_update(job_id, 0.9, "Generating feedback...", "feedback")

    feedback = _generate_comprehensive_feedback(prosody_metrics)

    await send_progress_update(job_id, 1.0, "Analysis complete!", "complete")

    # Serialize trajectory if available
    serialized_trajectory = None
    if ssl_trajectory:
        serialized_trajectory = {
            "frame_rate": 50,  # SSL predictor outputs at 50Hz
            "frame_count": len(ssl_trajectory),
            "frames": ssl_trajectory,
        }

    result = {
        "feedback": feedback,
        "prosody": serialize_prosody(prosody_metrics) if prosody_metrics else None,
        "ssl_animation_state": ssl_animation_state,
        "ssl_trajectory": serialized_trajectory,
        "success": True,
        "message": "Analysis complete",
    }

    if ssl_error:
        result["ssl_warning"] = ssl_error

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


def serialize_prosody(prosody):
    """Convert ProsodyMetrics to dict."""
    logger.debug(f"[serialize_prosody] Called with: {prosody}")
    logger.debug(
        f"[serialize_prosody] prosody.pitch: {prosody.pitch if prosody else 'prosody is None/False'}"
    )
    logger.debug(
        f"[serialize_prosody] prosody.rhythm: {prosody.rhythm if prosody else 'prosody is None/False'}"
    )
    if prosody and prosody.rhythm:
        logger.debug(f"[serialize_prosody] nPVI: {prosody.rhythm.npvi}")
    elif prosody:
        logger.debug("[serialize_prosody] rhythm is None, nPVI will be 0")

    pitch_mean = prosody.pitch.mean_f0 if prosody and prosody.pitch else 0
    pitch_range = prosody.pitch.f0_range if prosody and prosody.pitch else 0
    npvi = prosody.rhythm.npvi if prosody and prosody.rhythm else 0

    return {
        "pitch_mean": pitch_mean,
        "pitch_range": pitch_range,
        "pitch_variability": prosody.pitch.std_f0 if prosody and prosody.pitch else 0,
        "npvi": npvi,
        "stress_pattern": prosody.stress.primary_stress_word
        if prosody and prosody.stress
        else None,
        "pitch_range_label": _get_pitch_range_label(pitch_range),
        "pitch_range_coaching": _get_pitch_range_coaching(pitch_range),
        "mean_pitch_label": _get_mean_pitch_label(pitch_mean),
        "mean_pitch_coaching": _get_mean_pitch_coaching(pitch_mean),
        "npvi_label": _get_npvi_label(npvi)[0],
        "npvi_color": _get_npvi_label(npvi)[1],
        "npvi_coaching": _get_npvi_coaching(npvi),
        "npvi_bar_html": _build_npvi_bar_html(npvi),
    }


def _generate_comprehensive_feedback(prosody_metrics):
    """Generate comprehensive feedback text."""
    logger.debug(f"[feedback] prosody_metrics: {prosody_metrics}")

    sections = []

    # Pronunciation summary
    # NOTE: Phoneme-level error detection requires a phoneme CTC model.
    # This feature is currently non-functional pending model integration.
    sections.append("<strong>Pronunciation:</strong> Articulatory analysis via ContentVec+AAI")

    # Prosody summary with student-friendly labels
    if prosody_metrics:
        sections.append("<br><strong>Prosody:</strong>")
        if prosody_metrics.pitch:
            f0_range = prosody_metrics.pitch.f0_range
            f0_mean = prosody_metrics.pitch.mean_f0
            range_label = _get_pitch_range_label(f0_range)
            range_coaching = _get_pitch_range_coaching(f0_range)
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
):
    """
    Main analysis endpoint - performs articulatory and prosody analysis.

    Args:
        audio: Audio file (WAV format recommended)
        target_text: The target sentence the user was practicing

    Returns:
        Analysis results with articulatory feedback, prosody metrics, and feedback.
        Uses ContentVec + DANN AAI predictor for articulatory inference.
    """
    if not target_text.strip():
        raise HTTPException(status_code=400, detail="Please enter the target sentence.")

    if not audio.filename:
        raise HTTPException(status_code=400, detail="Please upload an audio file.")

    # Create job ID for progress tracking
    job_id = create_job_id()

    # Save uploaded file to temp location
    temp_path = await save_upload_to_temp(audio)

    try:
        # Run analysis with concurrency protection
        result = await run_with_semaphore(_run_analysis_pipeline(temp_path, target_text, job_id))
        return JSONResponse(content=result)
    except HTTPException:
        # Re-raise HTTPExceptions directly (from validation errors)
        raise
    except Exception as e:
        # Catch-all for unexpected errors
        import traceback

        logger.error(f"[analyze] UNEXPECTED ERROR: {e}")
        logger.error(traceback.format_exc())
        return JSONResponse(
            content={
                "success": False,
                "error": f"Unexpected error: {str(e)}",
                "traceback": traceback.format_exc(),
            },
            status_code=500,
        )
    finally:
        # Cleanup temp file in all cases
        cleanup_temp_file(temp_path)
