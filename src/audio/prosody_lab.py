"""Prosody Lab analysis helpers using scipy/numpy heuristics."""

from __future__ import annotations

import shutil
import tempfile
import uuid
from pathlib import Path
from typing import Any, cast

import numpy as np
from scipy.io import wavfile as scipy_wavfile
from scipy.signal import find_peaks, resample_poly

try:
    import soundfile as sf
except ImportError:  # pragma: no cover - fallback for minimal environments
    sf = None  # type: ignore[assignment]


_NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def _hz_to_midi_value(frequency: float) -> float:
    return float(69.0 + 12.0 * np.log2(frequency / 440.0))


def _midi_to_note_name(midi: float) -> str:
    rounded = int(round(midi))
    note = _NOTE_NAMES[((rounded % 12) + 12) % 12]
    octave = rounded // 12 - 1
    return f"{note}{octave}"


def _hz_to_note_name(frequency: float) -> str:
    return _midi_to_note_name(_hz_to_midi_value(frequency))


def _framed_energy(y: np.ndarray, frame_length: int = 2048, hop_length: int = 256) -> np.ndarray:
    """Compute energy per frame using sliding window."""
    if y.size == 0:
        return np.array([], dtype=np.float64)
    padded = np.pad(y, (0, max(0, frame_length - len(y))), mode="constant")
    frames = np.lib.stride_tricks.sliding_window_view(padded, frame_length)[::hop_length]
    return cast(np.ndarray, np.mean(np.abs(frames), axis=1))


def _heuristic_syllable_markers(y: np.ndarray, sr: int) -> list[float]:
    """Estimate syllable nuclei from energy peaks."""
    if y.size == 0:
        return []

    energy = _framed_energy(y)
    if energy.size == 0:
        return []

    hop_length = 256
    distance = max(1, int(0.12 * sr / hop_length))
    try:
        peaks, _ = find_peaks(energy, distance=distance, prominence=max(energy.max() * 0.1, 1e-6))
        return [round(float(index * hop_length / sr), 3) for index in peaks]
    except ValueError as e:
        print(f"[_heuristic_syllable_markers] Peak detection failed: {e}")
        return []


def _heuristic_pause_spans(y: np.ndarray, sr: int) -> list[dict[str, float]]:
    """Estimate silent spans for pause visualization."""
    if y.size == 0:
        return []

    energy = _framed_energy(y)
    if energy.size == 0:
        return []

    hop_length = 256
    silence_threshold = max(energy.max() * 0.18, 1e-6)
    silent = energy < silence_threshold
    spans: list[dict[str, float]] = []
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

    frame_length = 2048
    hop_length = 256
    padded = np.pad(y, (0, max(0, frame_length - len(y))), mode="constant")
    frames = np.lib.stride_tricks.sliding_window_view(padded, frame_length)[::hop_length]
    window = np.hanning(frame_length)
    fmin, fmax = 65.0, 1046.0
    freq_axis = np.fft.rfftfreq(frame_length, d=1.0 / sr)
    search_mask = (freq_axis >= fmin) & (freq_axis <= fmax)

    f0_values: list[float] = []
    voiced_flags: list[bool] = []
    confidences: list[float] = []

    for frame in frames:
        spectrum = np.abs(np.fft.rfft(frame * window))
        if not np.any(search_mask):
            peak_frequency, confidence = np.nan, 0.0
        else:
            band = spectrum[search_mask]
            band_frequencies = freq_axis[search_mask]
            peak_index = int(np.argmax(band)) if band.size else 0
            peak_frequency = float(band_frequencies[peak_index]) if band.size else np.nan
            confidence = (
                float(band[peak_index] / np.sum(band)) if band.size and np.sum(band) > 0 else 0.0
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
    for idx, t in enumerate(times):
        f0_v = None if np.isnan(f0[idx]) else float(f0[idx])
        midi_v = None if np.isnan(midi[idx]) else float(midi[idx])
        note = None
        if f0_v is not None:
            try:
                note = _hz_to_note_name(f0_v)
            except ValueError:
                note = None
        pitch_track.append(
            {
                "time": float(t),
                "f0_hz": f0_v,
                "midi": midi_v,
                "note": note,
                "confidence": float(voiced_prob[idx]) if idx < len(voiced_prob) else 0.0,
                "voiced": bool(voiced_flag[idx]) if idx < len(voiced_flag) else False,
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
        except ValueError:
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
    if sf is None:
        raise RuntimeError("soundfile is required for audio normalization")
    sf.write(output_path, y, sr, subtype="PCM_16")
    return y, sr


def _load_audio_samples(audio_path: str, sample_rate: int) -> tuple[np.ndarray, int]:
    """Load audio using soundfile or scipy fallback."""

    if sf is not None:
        try:
            y, sr = sf.read(audio_path, always_2d=False)
            if y.ndim > 1:
                y = np.mean(y, axis=1)
            if sr != sample_rate:
                y = resample_poly(np.asarray(y, dtype=np.float32), sample_rate, sr)
                sr = sample_rate
            return np.asarray(y, dtype=np.float32), int(sr)
        except (ValueError, RuntimeError) as e:
            print(f"[_load_audio_samples] soundfile load failed: {e}, trying scipy")

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

        syllable_count = max(1, len(markers))
        pause_count = len(pause_spans)

        total_duration = len(pitch_y) / pitch_sr if pitch_sr else 0.0
        pause_duration = sum(segment["duration"] for segment in pause_spans)
        rhythm_balance = max(
            0.0, min(1.0, 1.0 - (pause_duration / total_duration if total_duration else 0.0))
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
            "speech_rate": None,
            "articulation_rate": None,
        }

        return {
            "recording_id": recording_id,
            "summary": summary,
            "pitch_track": pitch["pitch_track"],
            "syllable_onsets": markers,
            "pause_spans": pause_spans,
            "raw_feedback": "",
            "analysis_source": "heuristic",
        }
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
