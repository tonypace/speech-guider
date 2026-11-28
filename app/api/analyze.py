"""Main analysis endpoints for pronunciation evaluation."""

import asyncio
import logging
import math
from typing import Any

import numpy as np
import parselmouth
import torch
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from app.api.settings import load_settings
from app.api.sse import create_job_id, send_progress_update
from app.services.concurrency import run_blocking, run_with_semaphore
from app.services.jobs import claim_job, finish_job
from app.utils.audio import (
    AudioConversionError,
    cleanup_temp_file,
    load_audio_tensor,
    save_upload_to_temp,
)
from src.audio import processor
from src.audio.prosody_lab import detect_syllables_and_pcenters
from src.models.aai_adapter import (
    SPEAKER_Z_METADATA,
    aai_to_canonical_state,
    decode_aai_row,
    r4_trajectory_to_canonical_frames,
    representative_aai_pose,
)
from src.models.diagnostic_passages import list_diagnostic_passages
from src.models.pronunciation_diagnostics import evaluate_pronunciation_diagnostics
from src.models.r5_predictor import R5AAIPredictor
from src.models.ssl_common import (
    DEFAULT_SSL_FEATURE_CONFIG,
    clear_torch_device_cache,
    get_best_torch_device,
)
from src.services.model_cache import get_forced_aligner, get_ssl_predictor

router = APIRouter()
logger = logging.getLogger(__name__)


class SSLAnalysisError(Exception):
    """Raised when SSL AAI analysis fails unexpectedly."""

    pass


def _ssl_aai_to_animation_state(
    audio_tensor: torch.Tensor,
    sample_rate: int,
    return_trajectory: bool = False,
    contact_enabled: bool = False,
    hinter_options: dict[str, Any] | None = None,
    extras_out: dict[str, Any] | None = None,
) -> dict[str, float] | tuple[dict[str, float], list[dict[str, float]], dict[str, Any]]:
    """Convert audio to animation state via SSL AAI predictor.

    Uses the active R5 or R4 predictor and display normalization.

    Args:
        audio_tensor: Audio tensor
        sample_rate: Audio sample rate in Hz
        return_trajectory: If True, also return full trajectory frames

    Returns:
        Canonical animation state dict, or (state, frames, meta) tuple if
        return_trajectory=True.
    """
    try:
        predictor = get_ssl_predictor()
    except (FileNotFoundError, RuntimeError) as e:
        logger.exception("SSL predictor could not be loaded")
        raise SSLAnalysisError(f"SSL predictor could not be loaded: {e}") from e

    metadata = SPEAKER_Z_METADATA
    try:
        prediction = predictor.predict_with_metadata(
            audio_tensor,
            sample_rate,
            contact_enabled=contact_enabled,
            **(hinter_options or {}),
        )
        tvs_array = prediction["tvs"].numpy()
        ssl_meta: dict[str, Any] = prediction["metadata"]
        if extras_out is not None:
            tvs_raw = prediction.get("tvs_raw")
            tvs_11 = prediction.get("tvs_11ch")
            bypass_43 = prediction.get("bypass_43d")
            lab_ret = prediction.get("labiodental_retraction")
            if tvs_raw is not None:
                extras_out["tvs_raw"] = tvs_raw.numpy()
            if tvs_11 is not None:
                extras_out["tvs_11ch"] = tvs_11.numpy()
            if bypass_43 is not None:
                extras_out["bypass_43d"] = bypass_43.numpy()
            if lab_ret is not None:
                extras_out["labiodental_retraction"] = lab_ret.numpy()
            if isinstance(predictor, R5AAIPredictor) and predictor.badges is not None:
                extras_out["r5_badges"] = predictor.badges

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
            labiodental_tensor = prediction.get("labiodental_retraction")
            labiodental_array = (
                labiodental_tensor.numpy() if labiodental_tensor is not None else None
            )
            frames = r4_trajectory_to_canonical_frames(tvs_array, labiodental_array)
            logger.debug(f"[_ssl_aai_to_animation_state] Generated {len(frames)} trajectory frames")
            return animation_state, frames, ssl_meta

        return animation_state

    except Exception as e:
        logger.exception("Articulatory prediction failed")
        raise SSLAnalysisError(f"SSL AAI prediction failed: {e}") from e


def try_primary_ssl_analysis(
    audio_tensor: torch.Tensor,
    sample_rate: int,
    return_trajectory: bool = False,
    contact_enabled: bool = False,
    hinter_options: dict[str, Any] | None = None,
    extras_out: dict[str, Any] | None = None,
) -> tuple[dict[str, float], list[dict[str, float]] | None, dict[str, Any]]:
    """Run the SSL AAI analysis path.

    Returns:
        tuple: (animation_state, ssl_trajectory, ssl_meta)
        - animation_state: canonical animation state dict
        - ssl_trajectory: list of canonical frame dicts or None (if return_trajectory=True)
        - ssl_meta: integration metadata (decoder, device, layers, display clipping)
    """
    logger.debug("[try_primary_ssl_analysis] Attempting SSL AAI path...")

    try:
        result = _ssl_aai_to_animation_state(
            audio_tensor,
            sample_rate,
            return_trajectory=return_trajectory,
            contact_enabled=contact_enabled,
            hinter_options=hinter_options,
            extras_out=extras_out,
        )
    except SSLAnalysisError as e:
        logger.warning(f"[try_primary_ssl_analysis] SSL AAI path failed: {e}")
        raise

    logger.debug("[try_primary_ssl_analysis] SSL AAI path succeeded")
    if isinstance(result, tuple):
        animation_state, ssl_trajectory, ssl_meta = result
        return animation_state, ssl_trajectory, ssl_meta
    return result, None, {}


def _load_and_preprocess_audio(
    audio_source: str | processor.AudioContext,
) -> tuple[torch.Tensor, int]:
    """Load and preprocess audio for SSL analysis, reusing an existing AudioContext."""
    if isinstance(audio_source, processor.AudioContext):
        return (
            torch.from_numpy(audio_source.get_downsampled_tensor()).float(),
            audio_source.target_sample_rate,
        )
    return load_audio_tensor(audio_source, DEFAULT_SSL_FEATURE_CONFIG.sample_rate)


def _extract_acoustic_vowel_intervals(
    audio_tensor: torch.Tensor,
    sample_rate: int,
    praat_sound: Any = None,
) -> list[tuple[float, float]]:
    """Estimate non-overlapping acoustic vowel (onset, offset) intervals via P-center detection."""
    samples = np.asarray(audio_tensor.detach().cpu().numpy(), dtype=np.float64).reshape(-1)
    if samples.size == 0 or sample_rate <= 0:
        return []
    sound = praat_sound if isinstance(praat_sound, parselmouth.Sound) else None
    detection = detect_syllables_and_pcenters(samples, sample_rate, sound=sound)
    intervals: list[tuple[float, float]] = []
    prev_end = 0.0
    for detail in detection.get("syllable_details", []):
        onset = float(detail.get("p_center_time", 0.0))
        duration = float(detail.get("vowel_duration", 0.0))
        offset = onset + duration
        if not (math.isfinite(onset) and math.isfinite(offset)) or onset < 0.0 or duration <= 0.0:
            continue
        if onset < prev_end:
            onset = prev_end
        if offset <= onset:
            continue
        intervals.append((onset, offset))
        prev_end = offset
    return intervals if len(intervals) >= 2 else []


async def _run_analysis_pipeline(
    audio_path: str,
    target_text: str,
    job_id: str,
    contact_enabled: bool = False,
    hinter_options: dict[str, Any] | None = None,
) -> dict[str, Any]:
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

    audio_context = await run_blocking(processor.AudioContext, audio_path)

    # Step 2: Analyze pronunciation
    await send_progress_update(job_id, 0.3, "Analyzing pronunciation...", "pronunciation")

    # Extract downsampled mono SSL tensor from the already-loaded AudioContext
    audio_tensor, sample_rate = await run_blocking(_load_and_preprocess_audio, audio_context)

    ssl_animation_state: dict[str, float] | None = None
    ssl_trajectory: list[dict[str, float]] | None = None
    ssl_meta: dict[str, Any] = {}
    ssl_extras: dict[str, Any] = {}
    ssl_error: str | None = None

    # Run SSL AAI analysis in thread to avoid blocking
    try:
        ssl_animation_state, ssl_trajectory, ssl_meta = await run_blocking(
            try_primary_ssl_analysis,
            audio_tensor,
            sample_rate,
            True,
            contact_enabled,
            hinter_options,
            ssl_extras,
        )
        logger.debug(
            "[analyze] SSL AAI analysis succeeded, animation state and trajectory generated"
        )
    except SSLAnalysisError as e:
        ssl_error = str(e)
        logger.warning(f"[analyze] SSL AAI analysis failed: {e}")
    except Exception as e:
        ssl_error = f"Unexpected SSL analysis error: {e}"
        logger.exception("Unexpected SSL analysis error for job %s", job_id)
    finally:
        meta_device = ssl_meta.get("device")
        device = (
            meta_device if isinstance(meta_device, str) and meta_device else get_best_torch_device()
        )
        await run_blocking(clear_torch_device_cache, device)

    # Step 2b: Forced alignment & 6-category pronunciation diagnostics (mHuBERT-147 + ctc_v1)
    alignment_result = None
    alignment_payload: dict[str, Any] | None = None
    alignment_meta: dict[str, Any] = {"status": "unavailable"}
    diagnostics_payload: dict[str, Any] = {
        "status": "unavailable",
        "reason": "Forced alignment assets are not staged.",
        "categories": [],
        "flagged_count": 0,
    }
    enriched_errors: list[dict[str, Any]] = []

    try:
        aligner = await run_blocking(get_forced_aligner)
        alignment_result = await run_blocking(
            aligner.align_with_posteriors,
            audio_tensor,
            target_text,
            sample_rate,
        )
        alignment_meta = {
            "status": "available",
            "model": "mhubert-147-ipa-ctc-v1",
            "word_count": len(alignment_result.alignment.words),
        }
        alignment_payload = _serialize_alignment(alignment_result.alignment)
        diagnostics_payload, enriched_errors = await run_blocking(
            lambda: evaluate_pronunciation_diagnostics(
                alignment_result,
                praat_sound=getattr(audio_context, "praat_sound", None),
                tvs_raw=ssl_extras.get("tvs_raw"),
                tvs_11ch=ssl_extras.get("tvs_11ch"),
                bypass_43d=ssl_extras.get("bypass_43d"),
                labiodental_retraction=ssl_extras.get("labiodental_retraction"),
                r5_badges=ssl_extras.get("r5_badges"),
            )
        )
    except FileNotFoundError as exc:
        logger.info("[analyze] Forced alignment unavailable (assets missing): %s", exc)
        diagnostics_payload["reason"] = "mHuBERT-147 forced alignment assets are not staged."
    except Exception as exc:
        logger.warning(
            "[analyze] Forced alignment failed; falling back to acoustic prosody: %s", exc
        )
        diagnostics_payload["reason"] = "Forced alignment did not complete for this clip."

    # Step 3: Extract prosody metrics
    await send_progress_update(job_id, 0.6, "Extracting prosody metrics...", "prosody")

    prosody_analyzer = processor.ProsodyAnalyzer(audio_context)

    vowel_intervals, word_timestamps = _extract_aligned_intervals(alignment_result)
    if len(vowel_intervals) < 2:
        try:
            vowel_intervals = await run_blocking(
                _extract_acoustic_vowel_intervals,
                audio_tensor,
                sample_rate,
                getattr(audio_context, "praat_sound", None),
            )
        except Exception:
            logger.debug(
                "[analyze] Acoustic vowel interval detection failed; proceeding without nPVI"
            )
            vowel_intervals = []

    logger.debug(
        "[analyze] Running prosody analysis with %d vowel intervals and %d words",
        len(vowel_intervals),
        len(word_timestamps),
    )
    prosody_metrics = await run_blocking(
        prosody_analyzer.analyze_complete,
        vowel_timestamps=vowel_intervals,
        word_timestamps=word_timestamps,
    )

    if prosody_metrics:
        logger.debug(f"[analyze] prosody_metrics type: {type(prosody_metrics)}")
        logger.debug(f"[analyze] prosody_metrics.pitch: {prosody_metrics.pitch}")
        logger.debug(f"[analyze] prosody_metrics.rhythm: {prosody_metrics.rhythm}")
        if prosody_metrics.rhythm:
            logger.debug(f"[analyze] nPVI value: {prosody_metrics.rhythm.npvi}")

    # Step 4: Generate feedback
    await send_progress_update(job_id, 0.9, "Generating feedback...", "feedback")

    feedback = _generate_comprehensive_feedback(prosody_metrics, diagnostics_payload)
    if ssl_animation_state is None:
        feedback = feedback.replace(
            "Articulatory trajectory captured",
            "Articulatory analysis unavailable; prosody feedback only",
        )
    elif ssl_meta.get("contact_augmentation") == "enabled":
        feedback = feedback.replace(
            "Articulatory trajectory captured",
            "Articulatory trajectory captured (tongue contact enhanced)",
        )
    elif ssl_meta.get("contact_augmentation") == "unavailable":
        feedback += (
            '<br><span class="text-xs text-amber-700">'
            "Tongue contact enhancement unavailable; using standard model."
            "</span>"
        )

    # Serialize trajectory if available
    serialized_trajectory: dict[str, Any] | None = None
    if ssl_trajectory:
        serialized_trajectory = {
            "frame_rate": DEFAULT_SSL_FEATURE_CONFIG.frame_rate,
            "frame_count": len(ssl_trajectory),
            "frames": ssl_trajectory,
        }

    result: dict[str, Any] = {
        "feedback": feedback,
        "prosody": serialize_prosody(prosody_metrics) if prosody_metrics else None,
        "ssl_animation_state": ssl_animation_state,
        "ssl_trajectory": serialized_trajectory,
        "integration_meta": ssl_meta,
        "alignment": alignment_payload,
        "alignment_meta": alignment_meta,
        "errors": enriched_errors,
        "pronunciation_diagnostics": diagnostics_payload,
        "success": ssl_animation_state is not None,
        "status": "complete" if ssl_animation_state is not None else "partial",
        "message": "Analysis complete"
        if ssl_animation_state is not None
        else "Partial analysis: articulatory inference failed",
    }

    if ssl_error:
        result["ssl_warning"] = (
            f"Articulatory analysis unavailable: {ssl_error}. Prosody feedback only. "
            f"Diagnostic job: {job_id}"
        )

    return result


def _get_pitch_range_label() -> str:
    """Return a student-friendly pitch range label."""
    return "measured pitch range"


def _get_pitch_range_coaching() -> str:
    """Avoid quality judgments without a speaker or task reference."""
    return "Observed F0 spread; no target reference available"


def _get_mean_pitch_label(mean_f0_hz: float) -> str:
    """Return a student-friendly mean pitch label."""
    if mean_f0_hz < 150:
        return "low voice"
    elif mean_f0_hz <= 220:
        return "middle voice"
    else:
        return "high voice"


def _get_mean_pitch_coaching() -> str:
    """Return coaching text for mean pitch."""
    return "Mean voiced F0; does not establish mood or speaking quality"


def _get_npvi_label(npvi: float | None) -> str:
    """Return a neutral duration-variability label for nPVI."""
    if npvi is None:
        return "unavailable"
    return "duration variability"


def _get_npvi_coaching(npvi: float | None) -> str:
    """Return coaching text for nPVI."""
    if npvi is None:
        return "Not enough syllables detected for rhythm metric."
    return "Duration variability; not a speaking-quality score."


def _build_npvi_bar_html(npvi: float | None) -> str:
    """Build a learner-friendly nPVI indicator using Tailwind utility classes."""
    if npvi is None:
        return (
            '<div class="mt-1.5 inline-flex items-center rounded-full bg-gray-100 '
            'px-3 py-1 text-xs font-medium text-gray-600">'
            "Not enough syllables detected for rhythm metric"
            "</div>"
        )
    label = _get_npvi_label(npvi)
    coaching = _get_npvi_coaching(npvi)
    width_pct = max(4.0, min(100.0, float(npvi)))
    return (
        '<div class="mt-1.5 flex items-center gap-2">'
        '<div class="h-2 flex-1 overflow-hidden rounded bg-gray-200">'
        f'<div class="h-full rounded bg-slate-500" style="width:{width_pct:.0f}%"></div>'
        "</div>"
        f'<span class="text-xs font-semibold text-gray-600">{label} — {coaching}</span>'
        "</div>"
    )


def _voice_quality_payload(vq: processor.VoiceQuality | None) -> dict[str, float] | None:
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


def serialize_prosody(prosody: processor.ProsodyMetrics | None) -> dict[str, Any]:
    """Convert ProsodyMetrics to dict."""
    pitch = prosody.pitch if prosody else None
    rhythm = prosody.rhythm if prosody else None
    stress = prosody.stress if prosody else None
    vq = prosody.voice_quality if prosody else None

    pitch_mean = pitch.mean_f0 if pitch else 0.0
    pitch_range = pitch.f0_range if pitch else 0.0
    pitch_var = pitch.std_f0 if pitch else 0.0
    npvi = rhythm.npvi if rhythm else None

    return {
        "pitch_mean": pitch_mean,
        "pitch_range": pitch_range,
        "pitch_variability": pitch_var,
        "npvi": npvi,
        "rhythm_status": rhythm.classification if rhythm else "insufficient_data",
        "rhythm_interval_type": "vowel_duration",
        "stress_pattern": stress.primary_stress_word if stress else None,
        "pitch_range_semitones": pitch.range_semitones if pitch else 0.0,
        "pitch_range_label": _get_pitch_range_label(),
        "pitch_range_coaching": _get_pitch_range_coaching(),
        "mean_pitch_label": _get_mean_pitch_label(pitch_mean),
        "mean_pitch_coaching": _get_mean_pitch_coaching(),
        "npvi_label": _get_npvi_label(npvi),
        "npvi_color": "gray",
        "npvi_coaching": _get_npvi_coaching(npvi),
        "npvi_bar_html": _build_npvi_bar_html(npvi),
        "voice_quality": _voice_quality_payload(vq),
    }


def _extract_aligned_intervals(
    alignment_result: Any,
) -> tuple[list[tuple[float, float]], list[tuple[str, float, float]]]:
    """Extract strictly non-overlapping vowel intervals and word spans from alignment."""
    if alignment_result is None or not getattr(alignment_result, "alignment", None):
        return [], []
    vowel_intervals: list[tuple[float, float]] = []
    word_timestamps: list[tuple[str, float, float]] = []
    prev_end = 0.0
    for word in alignment_result.alignment.words:
        if getattr(word, "not_reached", False):
            continue
        if word.end_time > word.start_time:
            word_timestamps.append((word.word, word.start_time, word.end_time))
        for ph in word.phonemes:
            if ph.is_vowel and ph.end_time > ph.start_time:
                start_t = max(prev_end, ph.start_time)
                if ph.end_time > start_t:
                    vowel_intervals.append((start_t, ph.end_time))
                    prev_end = ph.end_time
    return vowel_intervals, word_timestamps


def _serialize_alignment(sentence_alignment: Any) -> dict[str, Any]:
    return {
        "total_duration": sentence_alignment.total_duration,
        "overall_score": round(float(sentence_alignment.overall_score), 3),
        "words": [
            {
                "word": w.word,
                "start_time": w.start_time,
                "end_time": w.end_time,
                "not_reached": bool(getattr(w, "not_reached", False)),
                "syllables": [
                    {
                        "syllable_index": s.syllable_index,
                        "phonemes_target": s.phonemes_target,
                        "phonemes_predicted": s.phonemes_predicted,
                        "start_time": s.start_time,
                        "end_time": s.end_time,
                        "score": s.score,
                        "severity": s.severity,
                    }
                    for s in getattr(w, "syllables", [])
                ],
                "phonemes": [
                    {
                        "phoneme": p.phoneme,
                        "start_time": p.start_time,
                        "end_time": p.end_time,
                        "score": round(float(p.score), 3),
                        "is_error": p.is_error,
                        "predicted_phoneme": p.predicted_phoneme,
                        "is_vowel": p.is_vowel,
                    }
                    for p in w.phonemes
                ],
            }
            for w in sentence_alignment.words
        ],
    }


def _generate_comprehensive_feedback(
    prosody_metrics: processor.ProsodyMetrics | None,
    diagnostics_payload: dict[str, Any] | None = None,
) -> str:
    """Generate comprehensive feedback text."""
    logger.debug(f"[feedback] prosody_metrics: {prosody_metrics}")

    sections: list[str] = []

    if diagnostics_payload and diagnostics_payload.get("status") == "available":
        flagged = int(diagnostics_payload.get("flagged_count", 0))
        cue_note = (
            f"{flagged} pronunciation cue(s) highlighted below."
            if flagged > 0
            else "All checked phoneme cues clear."
        )
        sections.append(
            f"<strong>Pronunciation:</strong> Articulatory trajectory captured — {cue_note}"
        )
    else:
        sections.append("<strong>Pronunciation:</strong> Articulatory trajectory captured")

    # Prosody summary with student-friendly labels
    if prosody_metrics:
        sections.append("<br><strong>Prosody:</strong>")
        if prosody_metrics.pitch:
            f0_range = prosody_metrics.pitch.f0_range
            f0_mean = prosody_metrics.pitch.mean_f0
            range_label = _get_pitch_range_label()
            range_coaching = _get_pitch_range_coaching()
            pitch_label = _get_mean_pitch_label(f0_mean)
            pitch_coaching = _get_mean_pitch_coaching()
            sections.append(f"- Pitch range: {range_label} — {range_coaching} ({f0_range:.1f} Hz)")
            sections.append(f"- Mean pitch: {pitch_label} — {pitch_coaching} ({f0_mean:.1f} Hz)")
        if prosody_metrics.stress and prosody_metrics.stress.primary_stress_word:
            sections.append(
                f"- Primary stress word: <strong>{prosody_metrics.stress.primary_stress_word}</strong>"
            )
        if prosody_metrics.rhythm:
            npvi = prosody_metrics.rhythm.npvi
            npvi_label = _get_npvi_label(npvi)
            npvi_coaching = _get_npvi_coaching(npvi)
            sections.append(
                "- Rhythm: nPVI unavailable" if npvi is None else f"- Rhythm (nPVI {npvi:.2f})"
            )
            sections.append(f"  {npvi_label} — {npvi_coaching}")
            sections.append(_build_npvi_bar_html(npvi))
            logger.debug("[feedback] nPVI value: %s", npvi)

    result = "<br>".join(sections)
    logger.debug(f"[feedback] Final feedback string: {result}")
    return result


@router.get("/api/diagnostic-passages")
async def get_diagnostic_passages() -> JSONResponse:
    """Return curated diagnostic reading passages for the Analysis tab."""
    return JSONResponse(content={"passages": list_diagnostic_passages()})


@router.post("/api/analyze")
async def analyze_audio(
    audio: UploadFile = File(..., description="Audio file to analyze"),
    target_text: str = Form(..., description="Target sentence to practice"),
    job_id: str | None = Form(default=None, description="Optional reserved analysis job ID"),
) -> JSONResponse:
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
        settings = load_settings()
        hinter_options = {
            "lip_enabled": settings.lip_enabled,
            "calibrate_enabled": settings.calibrate_enabled,
            "labiodental_enabled": settings.labiodental_enabled,
            "dental_enabled": settings.dental_enabled,
            "silence_mode": settings.silence_mode,
        }
        result = await run_with_semaphore(
            _run_analysis_pipeline(
                temp_path,
                target_text,
                job.job_id,
                settings.contact_enabled,
                hinter_options,
            )
        )
        result["job_id"] = job.job_id
        response = JSONResponse(content=result)
        finish_job(
            job,
            "complete" if result["success"] else "failed",
            result.get("message", "Analysis complete"),
        )
        return response
    except asyncio.CancelledError:
        finish_job(job, "cancelled", "Analysis request cancelled")
        raise
    except AudioConversionError as exc:
        status_code = 413 if "maximum size" in str(exc).lower() else 400
        finish_job(job, "failed", str(exc))
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc
    except ValueError as exc:
        finish_job(job, "failed", str(exc))
        raise HTTPException(status_code=400, detail=str(exc)) from exc
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
