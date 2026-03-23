"""Main analysis endpoints for pronunciation evaluation."""

import asyncio
import torch
import numpy as np
from scipy.io import wavfile
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse

from app.models.schemas import AnalyzeResponse, AnalyzeRequest
from app.services.concurrency import run_with_semaphore
from app.api.sse import create_job_id, send_progress_update
from app.utils.audio import save_upload_to_temp, cleanup_temp_file

router = APIRouter()

# Cached model instances
_cached_aligner = None
_cached_g2p = None


def get_aligner():
    """Get or create cached ForcedAligner instance."""
    global _cached_aligner
    if _cached_aligner is None:
        from src.models.alignment import ForcedAligner

        print("Initializing Wav2Vec2 aligner (first time)...")
        _cached_aligner = ForcedAligner()
        print("Wav2Vec2 aligner initialized and cached.")
    return _cached_aligner


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
        sample_rate, audio_data = wavfile.read(audio_path)

        # Normalize audio
        if audio_data.dtype == np.int16:
            audio_data = audio_data.astype(np.float32) / 32768.0
        elif audio_data.dtype == np.int32:
            audio_data = audio_data.astype(np.float32) / 2147483648.0

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

        # Run alignment
        aligner = get_aligner()
        errors, alignment = aligner.analyze_pronunciation(audio_tensor, target_text, sample_rate)

    except Exception as e:
        await send_progress_update(job_id, 0.8, "Analysis encountered issues...", "error")
        errors = []
        alignment = None

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

        prosody_metrics = prosody_analyzer.analyze_complete(
            vowel_timestamps=vowel_timestamps, word_timestamps=word_timestamps
        )
    else:
        prosody_metrics = prosody_analyzer.analyze_complete()

    # Step 4: Generate feedback
    await send_progress_update(job_id, 0.9, "Generating feedback...", "feedback")

    from src.models.articulatory import ArticulatoryMapper, format_with_html_tooltips

    mapper = ArticulatoryMapper()
    feedback = _generate_comprehensive_feedback(errors, alignment, prosody_metrics, mapper)

    await send_progress_update(job_id, 1.0, "Analysis complete!", "complete")

    return {
        "errors": [serialize_error(e) for e in errors] if errors else [],
        "feedback": feedback,
        "alignment": serialize_alignment(alignment) if alignment else None,
        "prosody": serialize_prosody(prosody_metrics) if prosody_metrics else None,
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


def serialize_prosody(prosody):
    """Convert ProsodyMetrics to dict."""
    return {
        "pitch_mean": prosody.pitch.mean_f0 if prosody.pitch else 0,
        "pitch_range": prosody.pitch.f0_range if prosody.pitch else 0,
        "pitch_variability": prosody.pitch.std_f0 if prosody.pitch else 0,
        "npvi": prosody.rhythm.npvi if prosody.rhythm else 0,
        "stress_pattern": prosody.stress.primary_stress_word if prosody.stress else None,
    }


def _generate_comprehensive_feedback(errors, alignment, prosody_metrics, mapper):
    """Generate comprehensive feedback text."""
    # Simplified feedback generation
    sections = []

    # Pronunciation summary
    if errors:
        sections.append(f"**Pronunciation:** Found {len(errors)} error(s)")
        for i, error in enumerate(errors[:5], 1):
            sections.append(
                f"{i}. '{error.word_context}': /{error.target_phoneme}/ → /{error.predicted_phoneme}/"
            )
    else:
        sections.append("**Pronunciation:** No errors detected")

    # Prosody summary
    if prosody_metrics:
        sections.append(f"\\n**Prosody:**")
        if prosody_metrics.pitch:
            sections.append(f"- Pitch range: {prosody_metrics.pitch.f0_range:.1f} Hz")
            sections.append(f"- Mean pitch: {prosody_metrics.pitch.mean_f0:.1f} Hz")
        if prosody_metrics.rhythm:
            sections.append(f"- Rhythm (nPVI): {prosody_metrics.rhythm.npvi:.2f}")

    return "\\n".join(sections)


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
