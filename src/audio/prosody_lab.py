"""Prosody Lab analysis helpers using librosa and my-voice-analysis."""

from __future__ import annotations

import contextlib
import importlib
import io
import re
import shutil
import tempfile
import uuid
from pathlib import Path
from typing import Any

import numpy as np
from scipy.io import wavfile as scipy_wavfile
from scipy.signal import find_peaks, resample_poly

try:
    import librosa
except ImportError:  # pragma: no cover - fallback for minimal environments
    librosa = None  # type: ignore[assignment]

try:
    import soundfile as sf
except ImportError:  # pragma: no cover - fallback for minimal environments
    sf = None  # type: ignore[assignment]


_NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def _hz_to_midi_value(frequency: float) -> float:
    return 69.0 + 12.0 * np.log2(frequency / 440.0)


def _midi_to_note_name(midi: float) -> str:
    rounded = int(round(midi))
    note = _NOTE_NAMES[((rounded % 12) + 12) % 12]
    octave = rounded // 12 - 1
    return f"{note}{octave}"


def _hz_to_note_name(frequency: float) -> str:
    return _midi_to_note_name(_hz_to_midi_value(frequency))


def _load_my_voice_analysis_module() -> Any | None:
    """Attempt to load the my-voice-analysis package."""

    for module_name in ("myspsolution", "mysp", "my_voice_analysis"):
        try:
            return importlib.import_module(module_name)
        except ImportError:
            continue

    try:
        return __import__("my-voice-analysis")
    except Exception:
        return None


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        number = float(value)
        if np.isnan(number):
            return default
        return number
    except (TypeError, ValueError):
        return default


def _extract_metric(raw_output: str, key_pattern: str, default: float = 0.0) -> float:
    match = re.search(key_pattern, raw_output, re.IGNORECASE | re.MULTILINE)
    if not match:
        return default
    return _safe_float(match.group(1), default)


def _extract_int_metric(raw_output: str, key_pattern: str, default: int = 0) -> int:
    match = re.search(key_pattern, raw_output, re.IGNORECASE | re.MULTILINE)
    if not match:
        return default
    try:
        return int(float(match.group(1)))
    except (TypeError, ValueError):
        return default


def _parse_my_voice_analysis_output(raw_output: str) -> dict[str, float | int]:
    """Parse the text output from my-voice-analysis.

    The package prints metrics rather than returning them, so we capture and
    parse the useful subset we need for the UI.
    """

    return {
        "syllable_count": _extract_int_metric(
            raw_output, r"number[ _]*of[ _]*syllables\s*=?\s*([0-9]+)"
        ),
        "pause_count": _extract_int_metric(raw_output, r"number[ _]*of[ _]*pauses\s*=?\s*([0-9]+)"),
        "speech_rate": _extract_metric(
            raw_output, r"rate[ _]*of[ _]*speech\s*=?\s*([0-9]+(?:\.[0-9]+)?)"
        ),
        "articulation_rate": _extract_metric(
            raw_output, r"articulation[ _]*rate\s*=?\s*([0-9]+(?:\.[0-9]+)?)"
        ),
        "rhythm_balance": _extract_metric(raw_output, r"balance\s*=?\s*([0-9]+(?:\.[0-9]+)?)"),
    }


def _heuristic_syllable_markers(y: np.ndarray, sr: int) -> list[float]:
    """Estimate syllable nuclei from onset peaks as a fallback."""

    if librosa is not None:
        onsets = librosa.onset.onset_detect(y=y, sr=sr, units="time", backtrack=True)
        if onsets.size == 0:
            return []
        return [float(value) for value in np.unique(np.round(onsets, 3))]

    if y.size == 0:
        return []

    frame_length = 2048
    hop_length = 256
    padded = np.pad(y, (0, max(0, frame_length - len(y))), mode="constant")
    frames = np.lib.stride_tricks.sliding_window_view(padded, frame_length)[::hop_length]
    energy = np.mean(np.abs(frames), axis=1)
    if energy.size == 0:
        return []

    distance = max(1, int(0.12 * sr / hop_length))
    peaks, _ = find_peaks(energy, distance=distance, prominence=max(energy.max() * 0.1, 1e-6))
    return [round(float(index * hop_length / sr), 3) for index in peaks]


def _heuristic_pause_spans(y: np.ndarray, sr: int) -> list[dict[str, float]]:
    """Estimate silent spans for pause visualization."""

    if y.size == 0:
        return []

    if librosa is not None:
        segments = librosa.effects.split(y, top_db=35)
        if len(segments) == 0:
            return []

        spans: list[dict[str, float]] = []
        previous_end = 0
        for start, end in segments:
            if start > previous_end:
                pause_start = previous_end / sr
                pause_end = start / sr
                duration = pause_end - pause_start
                if duration > 0.08:
                    spans.append(
                        {
                            "start_time": float(pause_start),
                            "end_time": float(pause_end),
                            "duration": float(duration),
                        }
                    )
            previous_end = end

        total_duration = len(y) / sr
        if previous_end < len(y):
            pause_start = previous_end / sr
            pause_end = total_duration
            duration = pause_end - pause_start
            if duration > 0.08:
                spans.append(
                    {
                        "start_time": float(pause_start),
                        "end_time": float(pause_end),
                        "duration": float(duration),
                    }
                )

        return spans

    spans: list[dict[str, float]] = []
    frame_length = 2048
    hop_length = 256
    padded = np.pad(y, (0, max(0, frame_length - len(y))), mode="constant")
    frames = np.lib.stride_tricks.sliding_window_view(padded, frame_length)[::hop_length]
    energy = np.mean(np.abs(frames), axis=1)
    if energy.size == 0:
        return []

    silence_threshold = max(energy.max() * 0.18, 1e-6)
    silent = energy < silence_threshold
    start_index: int | None = None
    for index, is_silent in enumerate(silent):
        if is_silent and start_index is None:
            start_index = index
        elif not is_silent and start_index is not None:
            duration = (index - start_index) * hop_length / sr
            if duration > 0.08:
                spans.append(
                    {
                        "start_time": float(start_index * hop_length / sr),
                        "end_time": float(index * hop_length / sr),
                        "duration": float(duration),
                    }
                )
            start_index = None

    if start_index is not None:
        duration = (len(silent) - start_index) * hop_length / sr
        if duration > 0.08:
            spans.append(
                {
                    "start_time": float(start_index * hop_length / sr),
                    "end_time": float(len(silent) * hop_length / sr),
                    "duration": float(duration),
                }
            )

    return spans


def _compute_pitch_track(y: np.ndarray, sr: int) -> dict[str, Any]:
    """Compute pitch contour and quantize it into musical note data."""

    if librosa is not None:
        fmin = librosa.note_to_hz("C2")
        fmax = librosa.note_to_hz("C6")
        try:
            f0, voiced_flag, voiced_prob = librosa.pyin(y, fmin=fmin, fmax=fmax, sr=sr)
        except Exception:
            f0 = np.full(1, np.nan)
            voiced_flag = np.zeros(1, dtype=bool)
            voiced_prob = np.zeros(1, dtype=float)

        times = librosa.times_like(f0, sr=sr)
        midi = np.where(np.isnan(f0), np.nan, librosa.hz_to_midi(f0))
    else:
        frame_length = 2048
        hop_length = 256
        padded = np.pad(y, (0, max(0, frame_length - len(y))), mode="constant")
        frames = np.lib.stride_tricks.sliding_window_view(padded, frame_length)[::hop_length]
        window = np.hanning(frame_length)
        fmin = 65.0
        fmax = 1046.0
        freq_axis = np.fft.rfftfreq(frame_length, d=1.0 / sr)
        search_mask = (freq_axis >= fmin) & (freq_axis <= fmax)
        f0_values: list[float] = []
        voiced_flags: list[bool] = []
        confidences: list[float] = []

        for frame in frames:
            spectrum = np.abs(np.fft.rfft(frame * window))
            if not np.any(search_mask):
                peak_frequency = np.nan
                confidence = 0.0
            else:
                band = spectrum[search_mask]
                band_frequencies = freq_axis[search_mask]
                peak_index = int(np.argmax(band)) if band.size else 0
                peak_frequency = float(band_frequencies[peak_index]) if band.size else np.nan
                confidence = (
                    float(band[peak_index] / np.sum(band))
                    if band.size and np.sum(band) > 0
                    else 0.0
                )

            voiced = bool(np.isfinite(peak_frequency) and confidence > 0.08)
            f0_values.append(float(peak_frequency) if voiced else np.nan)
            voiced_flags.append(voiced)
            confidences.append(confidence if voiced else 0.0)

        f0 = np.array(f0_values, dtype=float)
        voiced_flag = np.array(voiced_flags, dtype=bool)
        voiced_prob = np.array(confidences, dtype=float)
        times = np.arange(len(f0), dtype=float) * hop_length / sr
        midi = np.where(np.isnan(f0), np.nan, 69.0 + 12.0 * np.log2(f0 / 440.0))

    pitch_track: list[dict[str, Any]] = []
    for index, time_value in enumerate(times):
        f0_value = None if np.isnan(f0[index]) else float(f0[index])
        midi_value = None if np.isnan(midi[index]) else float(midi[index])
        note_value = None
        if f0_value is not None:
            try:
                note_value = _hz_to_note_name(f0_value)
            except Exception:
                note_value = None
        pitch_track.append(
            {
                "time": float(time_value),
                "f0_hz": f0_value,
                "midi": midi_value,
                "note": note_value,
                "confidence": float(voiced_prob[index]) if index < len(voiced_prob) else 0.0,
                "voiced": bool(voiced_flag[index]) if index < len(voiced_flag) else False,
            }
        )

    voiced_f0 = f0[~np.isnan(f0)]
    voiced_midi = midi[~np.isnan(midi)]
    mean_f0 = float(np.mean(voiced_f0)) if voiced_f0.size else 0.0
    mean_midi = float(np.mean(voiced_midi)) if voiced_midi.size else None
    mean_note = None
    if mean_f0 > 0:
        try:
            mean_note = _hz_to_note_name(mean_f0)
        except Exception:
            mean_note = None

    return {
        "pitch_track": pitch_track,
        "mean_f0_hz": mean_f0,
        "mean_midi": mean_midi,
        "mean_note": mean_note,
        "pitch_range_hz": float(np.max(voiced_f0) - np.min(voiced_f0)) if voiced_f0.size else 0.0,
    }


def _normalize_audio_file(
    audio_path: str, output_path: Path, sample_rate: int = 44100
) -> tuple[np.ndarray, int]:
    """Load an audio file and write a normalized mono WAV copy."""

    y, sr = _load_audio_samples(audio_path, sample_rate)

    if y.size == 0:
        raise ValueError("Audio file is empty")

    y = y.astype(np.float32)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(output_path, y, sr, subtype="PCM_16")
    return y, sr


def _load_audio_samples(audio_path: str, sample_rate: int) -> tuple[np.ndarray, int]:
    """Load audio with librosa when available, otherwise fall back to scipy/soundfile."""

    if librosa is not None:
        y, sr = librosa.load(audio_path, sr=sample_rate, mono=True)
        return np.asarray(y, dtype=np.float32), int(sr)

    if sf is not None:
        y, sr = sf.read(audio_path, always_2d=False)
        if y.ndim > 1:
            y = np.mean(y, axis=1)
        if sr != sample_rate:
            y = resample_poly(np.asarray(y, dtype=np.float32), sample_rate, sr)
            sr = sample_rate
        return np.asarray(y, dtype=np.float32), int(sr)

    sr, y = scipy_wavfile.read(audio_path)
    if y.ndim > 1:
        y = np.mean(y, axis=1)
    if y.dtype.kind in {"i", "u"}:
        max_value = float(np.iinfo(y.dtype).max)
        y = y / max_value
    y = np.asarray(y, dtype=np.float32)
    if sr != sample_rate:
        y = resample_poly(y, sample_rate, sr)
        sr = sample_rate
    return y, int(sr)


def _run_my_voice_analysis(temp_dir: Path, wav_stem: str) -> tuple[dict[str, float | int], str]:
    """Capture my-voice-analysis output or fall back to heuristics."""

    module = _load_my_voice_analysis_module()
    if module is None or not hasattr(module, "mysptotal"):
        return {
            "syllable_count": 0,
            "pause_count": 0,
            "speech_rate": 0.0,
            "articulation_rate": 0.0,
            "rhythm_balance": 0.0,
        }, ""

    buffer = io.StringIO()
    try:
        with contextlib.redirect_stdout(buffer):
            module.mysptotal(wav_stem, str(temp_dir))
        raw_output = buffer.getvalue()
        return _parse_my_voice_analysis_output(raw_output), raw_output
    except Exception:
        return {
            "syllable_count": 0,
            "pause_count": 0,
            "speech_rate": 0.0,
            "articulation_rate": 0.0,
            "rhythm_balance": 0.0,
        }, buffer.getvalue()


def analyze_prosody_recording(audio_path: str) -> dict[str, Any]:
    """Analyze a recording for Prosody Lab visualization."""

    recording_id = uuid.uuid4().hex
    temp_dir = Path(tempfile.mkdtemp(prefix="prosody-lab-"))
    normalized_path = temp_dir / f"{recording_id}.wav"

    try:
        y, sr = _normalize_audio_file(audio_path, normalized_path)
        pitch_y, pitch_sr = _load_audio_samples(str(normalized_path), 22050)
        pitch = _compute_pitch_track(pitch_y, pitch_sr)
        markers = _heuristic_syllable_markers(pitch_y, pitch_sr)
        pause_spans = _heuristic_pause_spans(pitch_y, pitch_sr)

        mva_metrics, raw_output = _run_my_voice_analysis(temp_dir, normalized_path.stem)
        syllable_count = int(mva_metrics.get("syllable_count", 0)) or max(1, len(markers))
        pause_count = int(mva_metrics.get("pause_count", 0)) or len(pause_spans)
        rhythm_balance = float(mva_metrics.get("rhythm_balance", 0.0))
        if rhythm_balance <= 0.0:
            total_duration = len(pitch_y) / pitch_sr if pitch_sr else 0.0
            speech_duration = sum(segment["duration"] for segment in pause_spans)
            rhythm_balance = max(
                0.0, min(1.0, 1.0 - (speech_duration / total_duration if total_duration else 0.0))
            )

        duration_seconds = len(pitch_y) / pitch_sr if pitch_sr else 0.0
        summary = {
            "duration_seconds": float(duration_seconds),
            "syllable_count": int(syllable_count),
            "pause_count": int(pause_count),
            "rhythm_balance": float(rhythm_balance),
            "mean_f0_hz": float(pitch["mean_f0_hz"]),
            "mean_midi": pitch["mean_midi"],
            "mean_note": pitch["mean_note"],
            "speech_rate": _safe_float(mva_metrics.get("speech_rate"), 0.0) or None,
            "articulation_rate": _safe_float(mva_metrics.get("articulation_rate"), 0.0) or None,
        }

        return {
            "recording_id": recording_id,
            "summary": summary,
            "pitch_track": pitch["pitch_track"],
            "syllable_onsets": markers,
            "pause_spans": pause_spans,
            "raw_feedback": raw_output,
            "analysis_source": "my-voice-analysis" if raw_output else "fallback",
        }
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
