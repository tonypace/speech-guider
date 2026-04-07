"""Main analysis endpoints for pronunciation evaluation."""

import asyncio
import os

import numpy as np
import torch
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from scipy.io import wavfile

from app.api.sse import create_job_id, send_progress_update
from app.services.concurrency import run_with_semaphore
from app.utils.audio import cleanup_temp_file, save_upload_to_temp

router = APIRouter()

# Cached model instances
_cached_aligner = None
_cached_ssl_predictor = None
_cached_g2p = None


def get_ssl_predictor():
    """Get or create cached SSL AAI predictor instance."""

    global _cached_ssl_predictor
    if _cached_ssl_predictor is None:
        from src.models.ssl_aai_predictor import SSLAAIPredictor

        checkpoint_path = os.getenv("SSL_AAI_CHECKPOINT_PATH")
        print(f"[get_ssl_predictor] Initializing SSL AAI predictor (first time)...")
        if checkpoint_path:
            print(f"[get_ssl_predictor] Using checkpoint: {checkpoint_path}")
        else:
            print(f"[get_ssl_predictor] Using default checkpoint path")

        _cached_ssl_predictor = SSLAAIPredictor(checkpoint_path=checkpoint_path)
        _cached_ssl_predictor.load()
        print("[get_ssl_predictor] SSL AAI predictor initialized and cached.")
    return _cached_ssl_predictor


def get_aligner():
    """Get or create cached deprecated fallback aligner instance (lazy)."""

    global _cached_aligner
    if _cached_aligner is None:
        from src.models.alignment import ForcedAligner

        print("[get_aligner] Initializing deprecated Wav2Vec2 aligner fallback (first time)...")
        _cached_aligner = ForcedAligner()
        print("[get_aligner] Deprecated Wav2Vec2 aligner fallback initialized and cached.")
    return _cached_aligner


def should_use_deprecated_wav2vec2_fallback() -> bool:
    """Return whether the deprecated alignment fallback should be used."""

    value = os.getenv("ENABLE_WAV2VEC2_FALLBACK", "1").strip().lower()
    return value not in {"0", "false", "no"}


def _ssl_aai_to_animation_state(
    audio_tensor: torch.Tensor,
    sample_rate: int,
    return_trajectory: bool = False,
) -> dict | tuple[dict, list[dict]] | None:
    """Convert audio to animation state via SSL AAI predictor.

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
        decode_aai_row,
        representative_aai_pose,
    )

    try:
        predictor = get_ssl_predictor()
    except (FileNotFoundError, RuntimeError) as e:
        print(f"[_ssl_aai_to_animation_state] SSL predictor unavailable: {e}")
        return None

    try:
        # Predict z-scored AAI tract variables
        print(
            f"[_ssl_aai_to_animation_state] Calling predictor.predict with audio shape={audio_tensor.shape}, sr={sample_rate}"
        )
        tvs_tensor = predictor.predict(audio_tensor, sample_rate)
        print(f"[_ssl_aai_to_animation_state] Prediction succeeded: shape={tvs_tensor.shape}")
        tvs_array = tvs_tensor.numpy()

        # Get representative pose from trajectory
        # For now, use the first frame if short, or median across trajectory
        if len(tvs_array) == 1:
            pose = decode_aai_row(tvs_array[0])
        else:
            pose = representative_aai_pose(tvs_array.tolist())

        # Convert to canonical animation state
        metadata = AAIConversionMetadata(normalization="z_score")
        animation_state = aai_to_canonical_state(pose, metadata=metadata)

        print(f"[_ssl_aai_to_animation_state] Generated animation state via SSL AAI path")

        if return_trajectory:
            # Convert full trajectory to canonical frames
            frames = []
            for i in range(tvs_array.shape[0]):
                tv_row = decode_aai_row(tvs_array[i])
                frame = aai_to_canonical_state(tv_row, metadata=metadata)
                frames.append(frame)
            print(f"[_ssl_aai_to_animation_state] Generated {len(frames)} trajectory frames")
            return animation_state, frames

        return animation_state

    except Exception as e:
        import traceback

        tb = traceback.format_exc()
        msg = f"[_ssl_aai_to_animation_state] SSL AAI prediction failed: {e}\n{tb}"
        print(msg)
        # Write to file so we can see it even without terminal access
        with open("/tmp/ssl_debug.log", "a") as f:
            f.write(msg + "\n" + "=" * 80 + "\n")
        return None


def try_primary_ssl_analysis(
    audio_tensor: torch.Tensor, sample_rate: int, return_trajectory: bool = False
) -> tuple[list, object | None, dict | None, list[dict] | None]:
    """Try the primary SSL AAI path before falling back to Wav2Vec2 alignment.

    Returns:
        tuple: (errors, alignment, animation_state, ssl_trajectory)
        - errors: list of pronunciation errors
        - alignment: alignment object or None
        - animation_state: canonical animation state dict or None
        - ssl_trajectory: list of canonical frame dicts or None (if return_trajectory=True)

    Note:
        The SSL AAI path currently only produces animation state, not full
        pronunciation analysis. It returns empty errors and None alignment.
    """

    print("[try_primary_ssl_analysis] Attempting SSL AAI path...")

    result = _ssl_aai_to_animation_state(
        audio_tensor, sample_rate, return_trajectory=return_trajectory
    )

    if result is not None:
        print("[try_primary_ssl_analysis] SSL AAI path succeeded")
        if return_trajectory and isinstance(result, tuple):
            animation_state, ssl_trajectory = result
            return [], None, animation_state, ssl_trajectory
        if isinstance(result, dict):
            return [], None, result, None

    # If we reach here, SSL AAI path failed
    raise NotImplementedError("SSL AAI prediction failed or unavailable")


async def run_analysis_blocking(audio_path: str, target_text: str, job_id: str):
    """
    Run the full analysis pipeline in a blocking context (thread).

    Args:
        audio_path: Path to temporary audio file
        target_text: Target sentence to analyze
        job_id: Job ID for progress updates

    Returns:
        Analysis results dictionary
    """
    # Step 1: Load audio
    await send_progress_update(job_id, 0.1, "Loading audio file...", "load_audio")

    from src.audio.processor import AudioContext, ProsodyAnalyzer

    audio_context = AudioContext(audio_path)

    # Step 2: Analyze pronunciation
    await send_progress_update(job_id, 0.3, "Analyzing pronunciation...", "pronunciation")

    try:
        # Use soundfile for flexible format support (WAV, WebM, OGG, MP3, etc.)
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

        errors = []
        alignment = None
        ssl_animation_state = None
        ssl_trajectory = None
        path_used = "unknown"

        try:
            errors, alignment, ssl_animation_state, ssl_trajectory = try_primary_ssl_analysis(
                audio_tensor, sample_rate, return_trajectory=True
            )
            path_used = "ssl_aai"
            print(
                f"[analyze] Primary SSL AAI analysis succeeded, animation state and trajectory generated"
            )
        except NotImplementedError as ssl_exc:
            print(f"[analyze] Primary SSL AAI analysis unavailable: {ssl_exc}")
            if not should_use_deprecated_wav2vec2_fallback():
                raise RuntimeError(
                    "Primary SSL analysis is unavailable and deprecated Wav2Vec2 fallback is disabled"
                ) from ssl_exc

            print("[analyze] Falling back to deprecated Wav2Vec2 forced alignment")
            aligner = get_aligner()
            errors, alignment = aligner.analyze_pronunciation(
                audio_tensor, target_text, sample_rate
            )
            path_used = "wav2vec2_fallback"

    except Exception:
        await send_progress_update(job_id, 0.8, "Analysis encountered issues...", "error")
        errors = []
        alignment = None

    if torch.backends.mps.is_available():
        torch.mps.empty_cache()
    elif torch.cuda.is_available():
        torch.cuda.empty_cache()

    # Step 3: Extract prosody metrics
    await send_progress_update(job_id, 0.6, "Extracting prosody metrics...", "prosody")

    prosody_analyzer = ProsodyAnalyzer(audio_context)

    if alignment:
        vowel_timestamps = [
            (phoneme.start_time, phoneme.end_time)
            for word in alignment.words
            for phoneme in word.phonemes
            if phoneme.is_vowel
        ]

        word_timestamps = [(word.word, word.start_time, word.end_time) for word in alignment.words]

        print(f"[analyze] vowel_timestamps ({len(vowel_timestamps)}): {vowel_timestamps}")
        print(f"[analyze] word_timestamps ({len(word_timestamps)}): {word_timestamps}")

        prosody_metrics = prosody_analyzer.analyze_complete(
            vowel_timestamps=vowel_timestamps, word_timestamps=word_timestamps
        )
    else:
        print("[analyze] No alignment, running prosody analysis without timestamps")
        prosody_metrics = prosody_analyzer.analyze_complete(vowel_timestamps=[], word_timestamps=[])

    print(f"[analyze] prosody_metrics type: {type(prosody_metrics)}")
    print(f"[analyze] prosody_metrics: {prosody_metrics}")
    if prosody_metrics:
        print(f"[analyze] prosody_metrics.pitch: {prosody_metrics.pitch}")
        print(f"[analyze] prosody_metrics.rhythm: {prosody_metrics.rhythm}")
        if prosody_metrics.rhythm:
            print(f"[analyze] nPVI value: {prosody_metrics.rhythm.npvi}")

    # Step 4: Generate feedback
    await send_progress_update(job_id, 0.9, "Generating feedback...", "feedback")

    from src.models.articulatory import ArticulatoryMapper

    mapper = ArticulatoryMapper()
    feedback = _generate_comprehensive_feedback(errors, alignment, prosody_metrics, mapper)

    await send_progress_update(job_id, 1.0, "Analysis complete!", "complete")

    # Filter out identical phoneme pairs (e.g., /d/ -> /d/)
    filtered_errors = (
        [serialize_error(e) for e in errors if e.target_phoneme != e.predicted_phoneme]
        if errors
        else []
    )

    if len(filtered_errors) < len(errors):
        print(
            f"[analyze] Filtered out {len(errors) - len(filtered_errors)} identical phoneme pairs"
        )

    print(f"[analyze] Analysis path used: {path_used}")

    # Serialize trajectory if available
    serialized_trajectory = None
    if ssl_trajectory:
        serialized_trajectory = {
            "frame_rate": 50,  # SSL predictor outputs at 50Hz
            "frame_count": len(ssl_trajectory),
            "frames": ssl_trajectory,
        }

    return {
        "errors": filtered_errors,
        "feedback": feedback,
        "alignment": serialize_alignment(alignment) if alignment else None,
        "prosody": serialize_prosody(prosody_metrics) if prosody_metrics else None,
        "path_used": path_used,
        "ssl_animation_state": ssl_animation_state,
        "ssl_trajectory": serialized_trajectory,
        "success": True,
        "message": "Analysis complete",
    }


def serialize_error(error):
    """Convert PronunciationError dataclass to dict."""
    return {
        "error_type": error.error_type,
        "target_phoneme": error.target_phoneme,
        "predicted_phoneme": error.predicted_phoneme,
        "word_context": error.word_context,
    }


def serialize_alignment(alignment):
    """Convert SentenceAlignment dataclass to dict."""
    return {
        "text": alignment.text,
        "total_duration": alignment.total_duration,
        "overall_score": alignment.overall_score,
        "words": [
            {
                "word": w.word,
                "start_time": w.start_time,
                "end_time": w.end_time,
                "phonemes": [
                    {
                        "phoneme": p.phoneme,
                        "start_time": p.start_time,
                        "end_time": p.end_time,
                        "score": p.score,
                        "is_error": p.is_error,
                        "predicted_phoneme": p.predicted_phoneme,
                        "is_vowel": p.is_vowel,
                        "is_voiced": p.is_voiced,
                    }
                    for p in w.phonemes
                ],
            }
            for w in alignment.words
        ],
    }


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


def _f0_to_semitones(f0_hz: float, reference_hz: float = 1.0) -> float:
    """Convert a frequency in Hz to semitones above a reference frequency."""
    if f0_hz <= 0 or reference_hz <= 0:
        return 0.0
    return 12.0 * (f0_hz / reference_hz) ** (1 / 12) - 12.0


def serialize_prosody(prosody):
    """Convert ProsodyMetrics to dict."""
    print(f"[serialize_prosody] Called with: {prosody}")
    print(
        f"[serialize_prosody] prosody.pitch: {prosody.pitch if prosody else 'prosody is None/False'}"
    )
    print(
        f"[serialize_prosody] prosody.rhythm: {prosody.rhythm if prosody else 'prosody is None/False'}"
    )
    if prosody and prosody.rhythm:
        print(f"[serialize_prosody] nPVI: {prosody.rhythm.npvi}")
    elif prosody:
        print("[serialize_prosody] rhythm is None, nPVI will be 0")

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


def _generate_comprehensive_feedback(errors, alignment, prosody_metrics, mapper):
    """Generate comprehensive feedback text."""
    print(f"[feedback] Generating feedback for {len(errors) if errors else 0} errors")
    print(f"[feedback] alignment: {alignment}")
    print(f"[feedback] prosody_metrics: {prosody_metrics}")

    sections = []

    # Pronunciation summary
    if errors:
        sections.append(f"<strong>Pronunciation:</strong> Found {len(errors)} error(s)")
        for i, error in enumerate(errors[:5], 1):
            sections.append(
                f"{i}. '{error.word_context}': /{error.target_phoneme}/ → /{error.predicted_phoneme}/"
            )
    else:
        sections.append("<strong>Pronunciation:</strong> No errors detected")

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
            print(f"[feedback] nPVI value being used: {npvi:.2f}")

    result = "<br>".join(sections)
    print("[feedback] Final feedback string:")
    print(result)
    print(f"[feedback] Feedback repr: {repr(result)}")
    return result


@router.post("/api/analyze")
async def analyze_audio(
    audio: UploadFile = File(..., description="Audio file to analyze"),
    target_text: str = Form(..., description="Target sentence to practice"),
):
    """
    Main analysis endpoint - performs pronunciation and prosody analysis.

    Args:
        audio: Audio file (WAV format recommended)
        target_text: The target sentence the user was practicing

    Returns:
        Analysis results with errors, feedback, alignment, and prosody metrics
    """
    if not target_text.strip():
        raise HTTPException(status_code=400, detail="Please enter the target sentence.")

    if not audio.filename:
        raise HTTPException(status_code=400, detail="Please upload an audio file.")

    # Create job ID for progress tracking
    job_id = create_job_id()

    # Save uploaded file to temp location
    temp_path = await save_upload_to_temp(audio)

    async def do_analysis():
        try:
            # Run blocking analysis in thread pool
            result = await asyncio.to_thread(
                lambda: asyncio.run(run_analysis_blocking(temp_path, target_text, job_id))
            )
            return result
        finally:
            # Cleanup temp file
            cleanup_temp_file(temp_path)

    try:
        # Run with concurrency protection
        result = await run_with_semaphore(do_analysis())
        return JSONResponse(content=result)
    except Exception as e:
        # Catch-all for unexpected errors
        import traceback

        print(f"[analyze] UNEXPECTED ERROR: {e}")
        print(traceback.format_exc())
        cleanup_temp_file(temp_path)
        return JSONResponse(
            content={
                "success": False,
                "error": f"Unexpected error: {str(e)}",
                "traceback": traceback.format_exc(),
            },
            status_code=500,
        )
    except HTTPException as e:
        # Cleanup on error
        cleanup_temp_file(temp_path)
        return JSONResponse(
            content={"success": False, "error": e.detail}, status_code=e.status_code
        )
    except Exception as e:
        # Cleanup on unexpected error
        cleanup_temp_file(temp_path)
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)
