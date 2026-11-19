"""Prosody Lab analysis helpers using hybrid acoustic P-center & Parselmouth prosody."""

from __future__ import annotations

import base64
import io
import logging
import re
import tempfile
import uuid
from pathlib import Path
from typing import Any, cast

import numpy as np
import parselmouth
from scipy.io import wavfile as scipy_wavfile
from scipy.ndimage import gaussian_filter1d
from scipy.signal import butter, find_peaks, resample_poly, sosfiltfilt

from src.audio.reference_tts import OmniVoiceTTSProvider

try:
    import soundfile as sf
except ImportError:  # pragma: no cover - fallback for minimal environments
    sf = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)


_NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
_FUNCTION_WORDS: frozenset[str] = frozenset(
    {
        "a",
        "an",
        "the",
        "to",
        "of",
        "in",
        "on",
        "at",
        "for",
        "with",
        "and",
        "or",
        "but",
        "if",
        "is",
        "was",
        "are",
        "were",
        "be",
        "been",
        "we",
        "you",
        "they",
        "it",
        "he",
        "she",
        "i",
        "that",
        "as",
        "by",
        "from",
    }
)
_ONSET_DIGRAPHS: frozenset[str] = frozenset(
    {
        "bl",
        "br",
        "ch",
        "cl",
        "cr",
        "dr",
        "fl",
        "fr",
        "gl",
        "gr",
        "ph",
        "pl",
        "pr",
        "qu",
        "sc",
        "sh",
        "sk",
        "sl",
        "sm",
        "sn",
        "sp",
        "st",
        "sw",
        "th",
        "tr",
        "tw",
        "wh",
        "wr",
    }
)


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


def _bandpass_filter(
    y: np.ndarray, sr: int, low_hz: float, high_hz: float, order: int = 4
) -> np.ndarray:
    """Apply zero-phase Butterworth bandpass filter."""
    nyq = 0.5 * sr
    lo = max(20.0 / nyq, min(0.96, low_hz / nyq))
    hi = max(lo + 0.01, min(0.99, high_hz / nyq))
    sos = butter(order, [lo, hi], btype="bandpass", output="sos")
    return cast(np.ndarray, sosfiltfilt(sos, y.astype(np.float64)))


def _compute_rms_db_envelope(
    y: np.ndarray,
    sr: int,
    hop_sec: float = 0.005,
    win_sec: float = 0.025,
    smooth_sigma: float = 1.5,
) -> tuple[np.ndarray, np.ndarray]:
    """Compute smoothed RMS envelope in dB at fixed time step."""
    hop = max(1, int(round(hop_sec * sr)))
    win = max(hop, int(round(win_sec * sr)))
    if win % 2 == 1:
        win += 1
    padded = np.pad(y.astype(np.float64), (win // 2, win // 2), mode="constant")
    if len(padded) < win:
        return np.array([0.0]), np.array([-100.0])
    window = np.hanning(win)
    window_norm = np.sum(window**2) / win
    frames = np.lib.stride_tricks.sliding_window_view(padded, win)[::hop]
    power = np.mean((frames * window) ** 2, axis=1) / max(window_norm, 1e-12)
    db = 10.0 * np.log10(np.maximum(power, 1e-12))
    if smooth_sigma > 0 and len(db) > 3:
        db = gaussian_filter1d(db, sigma=smooth_sigma)
    times = np.arange(len(db), dtype=np.float64) * (hop / sr)
    return times, db


def _normalize_prominences(raw_scores: list[float]) -> list[float]:
    """Normalize prominence scores into [0.15, 1.0]."""
    if not raw_scores:
        return []
    arr = np.asarray(raw_scores, dtype=np.float64)
    lo = float(np.min(arr))
    hi = float(np.max(arr))
    if hi - lo < 1e-6:
        return [0.65 for _ in raw_scores]
    normed = 0.15 + 0.85 * ((arr - lo) / (hi - lo))
    return [round(float(x), 4) for x in normed]


def _compute_vocalic_npvi(durations: list[float]) -> float | None:
    """Compute normalized Pairwise Variability Index (nPVI) over vocalic durations."""
    valid = [float(d) for d in durations if d > 0.0]
    if len(valid) < 2:
        return None
    diffs: list[float] = []
    for idx in range(len(valid) - 1):
        d1, d2 = valid[idx], valid[idx + 1]
        mean_d = 0.5 * (d1 + d2)
        if mean_d > 0.0:
            diffs.append(abs(d1 - d2) / mean_d)
    if not diffs:
        return None
    return round(float(100.0 * sum(diffs) / len(diffs)), 2)


def detect_syllables_and_pcenters(
    y: np.ndarray,
    sr: int,
    sound: parselmouth.Sound | None = None,
) -> dict[str, Any]:
    """Detect syllable nuclei, perceptual centers (V_onset), consonant onsets, and durations.

    Implements the benchmarked `hybrid_acoustic_pcenter` detector combining:
    - Vocalic bandpass energy (200-3200 Hz) vs. high-frequency sibilant/burst energy (3500-7800 Hz)
    - Dual voicing gate (Praat autocorrelation F0 OR low-frequency voice bar 80-850 Hz)
    - 4-subband vocalic timbre flux + adaptive dip pruning (sensitive to 40-55ms schwas,
      immune to 4.5 Hz prolonged-vowel vibrato/tremor)
    - Šturm & Volín (2016) / Cummins & Port (1998) steepest-rise P-center and pre-beat
      consonant onset tracking.
    """
    if y.size == 0 or len(y) < max(64, int(0.06 * sr)):
        return {
            "nuclei_times": [],
            "p_center_times": [],
            "consonant_onset_times": [],
            "vowel_durations": [],
            "prominences": [],
            "syllable_details": [],
        }

    if sound is None:
        sound = parselmouth.Sound(y.astype(np.float64), sampling_frequency=float(sr))

    hop_sec = 0.005
    win_sec = 0.026

    y_voc = _bandpass_filter(y, sr, 200.0, min(3200.0, 0.47 * sr), order=4)
    y_lf = _bandpass_filter(y, sr, 80.0, min(850.0, 0.45 * sr), order=3)

    times, voc_db = _compute_rms_db_envelope(
        y_voc, sr, hop_sec=hop_sec, win_sec=win_sec, smooth_sigma=1.5
    )
    _, lf_db = _compute_rms_db_envelope(
        y_lf, sr, hop_sec=hop_sec, win_sec=win_sec, smooth_sigma=1.5
    )
    _, full_db = _compute_rms_db_envelope(y, sr, hop_sec=hop_sec, win_sec=0.016, smooth_sigma=1.0)

    if 0.5 * sr > 3700.0:
        y_sib = _bandpass_filter(y, sr, 3500.0, min(7800.0, 0.48 * sr), order=4)
        _, sib_db = _compute_rms_db_envelope(
            y_sib, sr, hop_sec=hop_sec, win_sec=0.018, smooth_sigma=1.2
        )
    else:
        sib_db = voc_db - 20.0

    subbands = [(200.0, 600.0), (600.0, 1200.0), (1200.0, 2200.0), (2200.0, 3400.0)]
    b_list: list[np.ndarray] = []
    for lo_b, hi_b in subbands:
        yb = _bandpass_filter(y, sr, lo_b, min(hi_b, 0.47 * sr), order=3)
        _, b_db = _compute_rms_db_envelope(
            yb, sr, hop_sec=hop_sec, win_sec=win_sec, smooth_sigma=1.5
        )
        b_list.append(b_db)
    b_matrix = np.stack(b_list, axis=1)
    b_norm = b_matrix - np.mean(b_matrix, axis=1, keepdims=True)

    n_frames = len(times)
    if n_frames < 5:
        return {
            "nuclei_times": [],
            "p_center_times": [],
            "consonant_onset_times": [],
            "vowel_durations": [],
            "prominences": [],
            "syllable_details": [],
        }

    pitch = sound.to_pitch_ac(
        time_step=0.008,
        pitch_floor=65.0,
        max_number_of_candidates=15,
        very_accurate=False,
        silence_threshold=0.02,
        voicing_threshold=0.33,
        octave_cost=0.01,
        octave_jump_cost=0.35,
        voiced_unvoiced_cost=0.14,
        pitch_ceiling=500.0,
    )
    f0_track = np.array([pitch.get_value_at_time(float(t)) for t in times], dtype=np.float64)
    q98_voc = float(np.percentile(voc_db, 98))
    silence_thresh_db = q98_voc - 19.5
    noise_floor_db = float(np.percentile(full_db, 10))

    has_f0 = np.isfinite(f0_track) & (f0_track > 0.0)
    has_voice_bar = (lf_db >= q98_voc - 14.0) & (sib_db <= voc_db - 5.0) & (lf_db >= sib_db + 6.0)
    voiced_mask = has_f0 | has_voice_bar

    raw_peaks, _ = find_peaks(
        voc_db,
        height=silence_thresh_db,
        distance=12,
        prominence=0.45,
    )

    cands: list[int] = []
    for pk in raw_peaks:
        pk_i = int(pk)
        if not np.any(voiced_mask[max(0, pk_i - 3) : min(n_frames, pk_i + 4)]):
            continue
        if sib_db[pk_i] > voc_db[pk_i] + 1.0:
            continue
        cands.append(pk_i)

    filtered_cands: list[int] = []
    for i, pk_i in enumerate(cands):
        if voc_db[pk_i] < q98_voc - 14.5:
            prev_dom = (
                i > 0
                and (times[pk_i] - times[cands[i - 1]]) < 0.145
                and (voc_db[cands[i - 1]] - voc_db[pk_i]) > 11.5
            )
            next_dom = (
                i + 1 < len(cands)
                and (times[cands[i + 1]] - times[pk_i]) < 0.145
                and (voc_db[cands[i + 1]] - voc_db[pk_i]) > 11.5
            )
            if prev_dom or next_dom:
                continue
        filtered_cands.append(pk_i)

    validated_peaks: list[int] = []
    if filtered_cands:
        curr_pk = filtered_cands[0]
        for next_pk in filtered_cands[1:]:
            val_idx = curr_pk + int(np.argmin(voc_db[curr_pk : next_pk + 1]))
            dip = min(
                float(voc_db[curr_pk] - voc_db[val_idx]),
                float(voc_db[next_pk] - voc_db[val_idx]),
            )
            dt = float(times[next_pk] - times[curr_pk])
            v_rat = float(np.mean(voiced_mask[curr_pk : next_pk + 1]))
            timbre_shift = float(
                np.linalg.norm(b_norm[next_pk] - b_norm[curr_pk])
                + np.linalg.norm(b_norm[val_idx] - 0.5 * (b_norm[curr_pk] + b_norm[next_pk]))
            )

            if v_rat >= 0.90 and timbre_shift < 10.5:
                req_dip = 6.20
            elif dt < 0.095:
                req_dip = 3.20
            elif min(float(voc_db[curr_pk]), float(voc_db[next_pk])) < q98_voc - 12.5:
                req_dip = 3.00
            elif v_rat < 0.85 or timbre_shift >= 12.0:
                req_dip = 1.38
            else:
                req_dip = 2.15

            if dip >= req_dip:
                validated_peaks.append(curr_pk)
                curr_pk = next_pk
            else:
                if voc_db[next_pk] > voc_db[curr_pk]:
                    curr_pk = next_pk
        validated_peaks.append(curr_pk)

    # Fallback for steady pure-tone synthetic fixtures that have no internal dip
    if not validated_peaks and np.any(voiced_mask):
        voiced_idx = np.where(voiced_mask)[0]
        best_idx = int(voiced_idx[np.argmax(voc_db[voiced_idx])])
        if voc_db[best_idx] >= silence_thresh_db - 6.0:
            validated_peaks.append(best_idx)

    nuclei: list[float] = []
    p_centers: list[float] = []
    c_onsets: list[float] = []
    durations: list[float] = []
    raw_proms: list[float] = []
    syllable_f0s: list[float | None] = []
    syllable_pitch_sts: list[float] = []
    syllable_slopes: list[float] = []

    voiced_f0_all = f0_track[has_f0]
    mean_f0 = float(np.median(voiced_f0_all)) if len(voiced_f0_all) else 130.0

    for idx_pos, pk in enumerate(validated_peaks):
        t_pk = float(times[pk])
        nuclei.append(round(t_pk, 4))

        prev_limit = validated_peaks[idx_pos - 1] if idx_pos > 0 else 0
        back_start = max(prev_limit, pk - int(round(0.160 / hop_sec)))
        if pk > back_start:
            valley_rel = int(np.argmin(voc_db[back_start : pk + 1]))
            valley_idx = back_start + valley_rel
        else:
            valley_idx = pk

        if pk > valley_idx:
            rise_seg = voc_db[valley_idx : pk + 1]
            deriv = np.diff(rise_seg)
            valid_rise = np.where(
                rise_seg[:-1] >= max(silence_thresh_db - 2.0, float(voc_db[pk] - 16.0))
            )[0]
            if len(valid_rise) > 0:
                steep_rel = int(valid_rise[np.argmax(deriv[valid_rise])])
                p_idx = valley_idx + steep_rel
            else:
                p_idx = valley_idx + int(np.argmax(deriv))
        else:
            p_idx = pk

        p_t = float(times[p_idx])
        p_centers.append(round(p_t, 4))

        c_search_start = max(
            prev_limit + 1 if idx_pos > 0 else 0, p_idx - int(round(0.130 / hop_sec))
        )
        c_idx = p_idx
        if p_idx > c_search_start:
            cons_threshold = max(noise_floor_db + 8.0, voc_db[pk] - 24.0)
            for scan_i in range(p_idx - 1, c_search_start - 1, -1):
                if full_db[scan_i] >= cons_threshold or sib_db[scan_i] >= cons_threshold - 2.0:
                    c_idx = scan_i
                else:
                    break
        c_t = float(times[min(p_idx, c_idx)])
        c_onsets.append(round(c_t, 4))

        next_limit = (
            validated_peaks[idx_pos + 1] if idx_pos + 1 < len(validated_peaks) else n_frames - 1
        )
        fwd_end = min(next_limit, pk + int(round(0.280 / hop_sec)))
        if fwd_end > pk:
            fall_seg = voc_db[pk : fwd_end + 1]
            drop_thresh = max(silence_thresh_db, float(voc_db[pk] - 6.5))
            below = np.where(fall_seg <= drop_thresh)[0]
            if len(below) > 0:
                end_idx = pk + int(below[0])
            else:
                end_idx = pk + int(np.argmin(fall_seg))
        else:
            end_idx = pk

        v_dur = max(0.035, float(times[end_idx] - p_t))
        durations.append(round(v_dur, 4))

        win_f0 = f0_track[max(0, p_idx) : min(n_frames, end_idx + 1)]
        win_f0_v = win_f0[np.isfinite(win_f0) & (win_f0 > 0)]
        if len(win_f0_v) == 0:
            near_f0 = f0_track[max(0, pk - 3) : min(n_frames, pk + 4)]
            win_f0_v = near_f0[np.isfinite(near_f0) & (near_f0 > 0)]

        if len(win_f0_v) > 0 and mean_f0 > 0:
            med_f0 = float(np.median(win_f0_v))
            pitch_st = float(12.0 * np.log2(med_f0 / mean_f0))
            st_above_mean = max(0.0, float(12.0 * np.log2(np.max(win_f0_v) / mean_f0)))
            if len(win_f0_v) >= 2:
                pitch_slope = float(12.0 * np.log2(win_f0_v[-1] / win_f0_v[0]))
            else:
                pitch_slope = 0.0
            syllable_f0s.append(round(med_f0, 2))
        else:
            pitch_st = 0.0
            st_above_mean = 0.0
            pitch_slope = 0.0
            syllable_f0s.append(None)

        syllable_pitch_sts.append(round(pitch_st, 2))
        syllable_slopes.append(round(pitch_slope, 2))

        int_score = max(0.0, float(voc_db[pk] - silence_thresh_db)) / 22.0
        dur_score = min(1.0, v_dur / 0.22)
        f0_score = min(1.0, st_above_mean / 6.0)
        raw_proms.append(0.45 * int_score + 0.35 * dur_score + 0.20 * f0_score)

    prominences = _normalize_prominences(raw_proms)
    med_prom = float(np.median(prominences)) if prominences else 0.55

    details: list[dict[str, Any]] = []
    for idx in range(len(nuclei)):
        prom = prominences[idx]
        is_stressed = bool(
            prom >= max(0.56, med_prom)
            or (
                idx > 0
                and idx + 1 < len(prominences)
                and prom >= prominences[idx - 1]
                and prom >= prominences[idx + 1]
            )
            or len(nuclei) == 1
        )
        p_t = p_centers[idx]
        c_t = c_onsets[idx]
        details.append(
            {
                "index": idx,
                "nucleus_time": nuclei[idx],
                "p_center_time": p_t,
                "consonant_onset_time": c_t,
                "pre_duration": round(max(0.0, p_t - c_t), 4),
                "vowel_duration": durations[idx],
                "prominence": prom,
                "is_stressed": is_stressed,
                "f0_hz": syllable_f0s[idx],
                "pitch_st": syllable_pitch_sts[idx],
                "pitch_slope": syllable_slopes[idx],
            }
        )

    return {
        "nuclei_times": nuclei,
        "p_center_times": p_centers,
        "consonant_onset_times": c_onsets,
        "vowel_durations": durations,
        "prominences": prominences,
        "syllable_details": details,
    }


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
            logger.warning("[_load_audio_samples] soundfile load failed: %s, trying scipy", e)

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
    pitch_y, pitch_sr = _load_audio_samples(audio_path, 22050)
    if pitch_y.size == 0:
        raise ValueError("Audio file is empty")

    pitch = _compute_pitch_track(pitch_y, pitch_sr)
    syllable_data = detect_syllables_and_pcenters(pitch_y, pitch_sr)
    markers = syllable_data["nuclei_times"]
    p_centers = syllable_data["p_center_times"] or markers
    syllable_details = syllable_data["syllable_details"]
    pause_spans = _heuristic_pause_spans(pitch_y, pitch_sr)

    syllable_count = max(1, len(markers))
    pause_count = len(pause_spans)

    total_duration = len(pitch_y) / pitch_sr if pitch_sr else 0.0
    pause_duration = sum(segment["duration"] for segment in pause_spans)
    speaking_duration = max(0.05, total_duration - pause_duration)
    rhythm_balance = max(
        0.0, min(1.0, 1.0 - (pause_duration / total_duration if total_duration else 0.0))
    )

    speech_rate = (
        round(float(syllable_count / total_duration), 2) if total_duration > 0.05 else None
    )
    articulation_rate = (
        round(float(syllable_count / speaking_duration), 2) if total_duration > 0.05 else None
    )
    npvi = _compute_vocalic_npvi(syllable_data["vowel_durations"])

    duration_seconds = len(pitch_y) / pitch_sr if pitch_sr else 0.0
    summary = {
        "duration_seconds": float(duration_seconds),
        "syllable_count": int(syllable_count),
        "pause_count": int(pause_count),
        "rhythm_balance": float(rhythm_balance),
        "mean_f0_hz": float(pitch["mean_f0_hz"]),
        "mean_midi": pitch["mean_midi"],
        "mean_note": pitch["mean_note"],
        "speech_rate": speech_rate,
        "articulation_rate": articulation_rate,
        "npvi": npvi,
    }

    return {
        "recording_id": recording_id,
        "summary": summary,
        "pitch_track": pitch["pitch_track"],
        "syllable_onsets": markers,
        "syllable_p_centers": p_centers,
        "syllable_details": syllable_details,
        "pause_spans": pause_spans,
        "raw_feedback": "",
        "analysis_source": "heuristic",
    }


def _find_vowel_runs(word: str) -> list[tuple[int, int]]:
    """Locate contiguous vowel nuclei runs in an English word."""
    vowels = set("aeiouyAEIOUY")
    runs: list[tuple[int, int]] = []
    n = len(word)
    i = 0
    while i < n:
        ch = word[i]
        is_vowel = ch in vowels
        if ch in {"y", "Y"} and i == 0 and i + 1 < n and word[i + 1] in vowels:
            is_vowel = False
        if is_vowel:
            start = i
            while i < n and word[i] in vowels:
                i += 1
            runs.append((start, i))
        else:
            i += 1

    if len(runs) >= 2:
        last_start, last_end = runs[-1]
        tail = word[last_start:last_end].lower()
        is_syllabic_le = (
            last_end == n
            and tail == "e"
            and last_start >= 2
            and word[last_start - 1].lower() == "l"
            and word[last_start - 2].lower() not in set("aeiouylrw")
        )
        if last_end == n and tail == "e" and not is_syllabic_le:
            runs.pop()

    return runs


def _split_word_into_syllables(word: str) -> list[str]:
    """Split a single alphabetic word into orthographic syllables."""
    clean = re.sub(r"[^A-Za-z']", "", word)
    if not clean:
        return []

    runs = _find_vowel_runs(clean)
    if len(runs) <= 1:
        return [clean]

    boundaries: list[int] = [0]
    for idx in range(len(runs) - 1):
        _, e_curr = runs[idx]
        s_next, _ = runs[idx + 1]
        cons = clean[e_curr:s_next]
        c_len = len(cons)
        if c_len == 0:
            split_at = e_curr
        elif c_len == 1:
            split_at = e_curr
        elif c_len == 2:
            if cons.lower() in {"ch", "sh", "th", "ph", "wh", "qu"}:
                split_at = e_curr
            else:
                split_at = e_curr + 1
        else:
            if cons[-2:].lower() in _ONSET_DIGRAPHS:
                split_at = s_next - 2
            else:
                split_at = s_next - 1
        boundaries.append(split_at)
    boundaries.append(len(clean))

    parts = [clean[boundaries[k] : boundaries[k + 1]] for k in range(len(boundaries) - 1)]
    return [p for p in parts if p]


def _split_onset_and_rhyme(syllable: str) -> tuple[str, str]:
    """Split a syllable into lowercase consonant onset (`pre`) and vowel+coda (`vowel`)."""
    clean = re.sub(r"[^A-Za-z']", "", syllable)
    if not clean:
        return "", syllable
    vowels = set("aeiouyAEIOUY")
    for idx, ch in enumerate(clean):
        if ch in {"y", "Y"} and idx == 0 and idx + 1 < len(clean) and clean[idx + 1] in vowels:
            continue
        if ch in vowels:
            return clean[:idx].lower(), clean[idx:]
    return "", clean


def syllabify_english_text(text: str) -> list[dict[str, Any]]:
    """Split English text into syllable dicts with onset, vowel nucleus, function flag, and pauses."""
    raw_tokens = re.findall(r"[A-Za-z'-]+[^\sA-Za-z'-]*", text)
    syllables: list[dict[str, Any]] = []

    for token in raw_tokens:
        m = re.match(r"^([A-Za-z'-]+)(.*)$", token)
        if not m:
            continue
        word_part, punct = m.group(1), m.group(2)
        explicit_chunks = [c for c in word_part.split("-") if re.sub(r"[^A-Za-z']", "", c)]
        if not explicit_chunks:
            continue

        word_alpha = re.sub(r"[^A-Za-z']", "", word_part).lower()
        is_func = word_alpha in _FUNCTION_WORDS
        has_pause = any(p in punct for p in ("...", ",", ";", ".", "?", "!", ":", "—", "--"))
        has_ellipsis = "..." in punct

        word_syllables: list[str] = []
        if len(explicit_chunks) > 1:
            word_syllables = [re.sub(r"[^A-Za-z']", "", c) for c in explicit_chunks]
        else:
            word_syllables = _split_word_into_syllables(explicit_chunks[0])

        for idx, syl_raw in enumerate(word_syllables):
            is_last_in_word = idx == len(word_syllables) - 1
            pre, vowel = _split_onset_and_rhyme(syl_raw)
            display_text = syl_raw
            if not is_last_in_word:
                display_text = f"{syl_raw}-"
            elif has_ellipsis:
                display_text = f"{syl_raw}..."

            syllables.append(
                {
                    "text": display_text,
                    "pre": pre,
                    "vowel": vowel,
                    "is_function_word": bool(is_func and len(word_syllables) == 1),
                    "has_pause_after": bool(is_last_in_word and has_pause),
                }
            )

    if not syllables:
        fallback = text.strip() or "AH"
        syllables.append(
            {
                "text": fallback,
                "pre": "",
                "vowel": fallback,
                "is_function_word": False,
                "has_pause_after": False,
            }
        )

    return syllables


def build_prosody_phrase_from_text_and_analysis(
    target_text: str,
    analysis: dict[str, Any],
) -> dict[str, Any]:
    """Align orthographic syllables with analyzed acoustic syllable details onto a 4.0-beat bar."""
    orth = syllabify_english_text(target_text)
    details: list[dict[str, Any]] = list(analysis.get("syllable_details") or [])
    n_syl = len(orth)
    target_beats = 4.0
    bpm = 88

    mapped_times: list[float] = []
    mapped_pre_sec: list[float] = []
    mapped_v_sec: list[float] = []
    mapped_prom: list[float] = []
    mapped_stressed: list[bool] = []
    mapped_pitch_st: list[float] = []

    if details:
        m_det = len(details)
        for i, item in enumerate(orth):
            pos = (i * (m_det - 1) / max(1, n_syl - 1)) if n_syl > 1 and m_det > 1 else 0.0
            lo_idx = min(m_det - 1, int(np.floor(pos)))
            hi_idx = min(m_det - 1, int(np.ceil(pos)))
            frac = pos - lo_idx
            d_lo = details[lo_idx]
            d_hi = details[hi_idx]

            p_t = (1.0 - frac) * float(d_lo.get("p_center_time", 0.2)) + frac * float(
                d_hi.get("p_center_time", 0.2)
            )
            pre_s = (1.0 - frac) * float(d_lo.get("pre_duration", 0.03)) + frac * float(
                d_hi.get("pre_duration", 0.03)
            )
            v_s = (1.0 - frac) * float(d_lo.get("vowel_duration", 0.14)) + frac * float(
                d_hi.get("vowel_duration", 0.14)
            )
            prom = (1.0 - frac) * float(d_lo.get("prominence", 0.5)) + frac * float(
                d_hi.get("prominence", 0.5)
            )
            p_st = (1.0 - frac) * float(d_lo.get("pitch_st", 0.0)) + frac * float(
                d_hi.get("pitch_st", 0.0)
            )
            ac_stress = bool(d_lo.get("is_stressed") if frac < 0.5 else d_hi.get("is_stressed"))

            if item["is_function_word"]:
                is_stressed = False
                prom = min(prom, 0.28)
                p_st = min(p_st, -0.8)
            else:
                is_stressed = ac_stress or (not item["text"].endswith("-") and prom >= 0.48)

            mapped_times.append(p_t)
            mapped_pre_sec.append(pre_s if item["pre"] else 0.0)
            mapped_v_sec.append(v_s)
            mapped_prom.append(prom)
            mapped_stressed.append(is_stressed)
            mapped_pitch_st.append(p_st)
    else:
        cursor_t = 0.18
        for i, item in enumerate(orth):
            is_stressed = not item["is_function_word"] and (i % 2 == 0 or i == n_syl - 1)
            v_s = 0.22 if is_stressed else 0.11
            pre_s = (0.05 if is_stressed else 0.03) if item["pre"] else 0.0
            mapped_times.append(cursor_t)
            mapped_pre_sec.append(pre_s)
            mapped_v_sec.append(v_s)
            mapped_prom.append(0.88 if is_stressed else 0.20)
            mapped_stressed.append(is_stressed)
            mapped_pitch_st.append(3.0 if is_stressed else -1.4)
            cursor_t += v_s + (0.24 if item["has_pause_after"] else 0.08)

    if not any(mapped_stressed) and n_syl > 0:
        best_idx = max(
            range(n_syl),
            key=lambda idx: (not orth[idx]["is_function_word"], mapped_prom[idx]),
        )
        mapped_stressed[best_idx] = True
        mapped_prom[best_idx] = max(0.82, mapped_prom[best_idx])

    first_t = max(0.0, mapped_times[0] - 0.10)
    last_end_t = max(first_t + 0.40, mapped_times[-1] + mapped_v_sec[-1] + 0.10)
    span_t = max(0.40, last_end_t - first_t)
    scale = (target_beats - 0.34) / span_t

    phrase_syllables: list[dict[str, Any]] = []
    min_next_beat = 0.16
    for idx, item in enumerate(orth):
        is_stressed = mapped_stressed[idx]
        is_ghost = not is_stressed
        raw_beat = 0.16 + (mapped_times[idx] - first_t) * scale
        max_allowed = 3.82 - (n_syl - 1 - idx) * 0.12
        beat = round(float(max(min_next_beat, min(max_allowed, raw_beat))), 2)
        dur = round(
            float(
                max(
                    0.10 if is_ghost else 0.24,
                    min(0.54, mapped_v_sec[idx] * scale),
                )
            ),
            2,
        )
        min_next_beat = round(
            min(3.86, beat + max(0.12, dur * 0.85) + (0.22 if item["has_pause_after"] else 0.03)),
            2,
        )
        pre_dur = (
            round(float(max(0.03, min(0.12, mapped_pre_sec[idx] * scale))), 2)
            if item["pre"]
            else 0.0
        )

        raw_text = str(item["text"])
        raw_vowel = str(item["vowel"])
        if is_stressed:
            has_hyph = raw_text.endswith("-")
            has_ell = raw_text.endswith("...")
            core = re.sub(r"[-.]+$", "", raw_text).upper()
            syl_text = f"{core}-" if has_hyph else (f"{core}..." if has_ell else core)
            vowel_str = raw_vowel.upper()
        else:
            syl_text = raw_text
            vowel_str = raw_vowel.lower()

        phrase_syllables.append(
            {
                "index": idx,
                "text": syl_text,
                "pre": str(item["pre"]),
                "preDur": pre_dur,
                "vowel": vowel_str,
                "beat": beat,
                "dur": dur,
                "stress": round(float(mapped_prom[idx]), 2),
                "pitchST": round(float(mapped_pitch_st[idx]), 1),
                "isGhost": is_ghost,
                "isFinal": bool(idx == n_syl - 1 or item["has_pause_after"]),
            }
        )

    pause_gate: dict[str, Any] | None = None
    for idx in range(n_syl - 1):
        if orth[idx]["has_pause_after"]:
            cur_s = phrase_syllables[idx]
            nxt_s = phrase_syllables[idx + 1]
            g_start = round(min(3.60, float(cur_s["beat"]) + float(cur_s["dur"])), 2)
            g_end = round(max(g_start + 0.18, float(nxt_s["beat"]) - 0.02), 2)
            if g_end > g_start:
                pause_gate = {
                    "startBeat": g_start,
                    "endBeat": min(3.88, g_end),
                    "label": "|| Phrase Pause Gate",
                }
                break

    feet: list[dict[str, Any]] = []
    stressed_indices = [i for i, s in enumerate(phrase_syllables) if not s["isGhost"]]
    if stressed_indices:
        first_st = stressed_indices[0]
        if first_st > 0:
            pickup_text = " ".join(str(phrase_syllables[k]["text"]) for k in range(first_st))
            feet.append(
                {
                    "label": f"Pickup: {pickup_text}",
                    "startBeat": 0.0,
                    "endBeat": round(float(phrase_syllables[first_st]["beat"]), 2),
                }
            )
        for f_num, st_idx in enumerate(stressed_indices, start=1):
            next_st_idx = (
                stressed_indices[f_num] if f_num < len(stressed_indices) else len(phrase_syllables)
            )
            start_b = (
                0.0 if (f_num == 1 and first_st == 0) else float(phrase_syllables[st_idx]["beat"])
            )
            end_b = (
                4.0
                if next_st_idx >= len(phrase_syllables)
                else float(phrase_syllables[next_st_idx]["beat"])
            )
            foot_words = " ".join(
                str(phrase_syllables[k]["text"]) for k in range(st_idx, next_st_idx)
            )
            feet.append(
                {
                    "label": f"Foot {f_num}: {foot_words}",
                    "startBeat": round(start_b, 2),
                    "endBeat": round(max(start_b + 0.2, end_b), 2),
                }
            )

    return {
        "id": "custom",
        "title": target_text.strip(),
        "vibeLabel": "Custom Target Sentence",
        "bpm": bpm,
        "pauseGate": pause_gate,
        "feet": feet,
        "syllables": phrase_syllables,
    }


def _synthesize_fallback_prosody_wav(
    target_text: str,
    sample_rate: int = 16000,
) -> bytes:
    """Synthesize a clean 16kHz mono WAV reference with stress-timed vowel formants and F0 contour."""
    orth = syllabify_english_text(target_text)
    n_syl = len(orth)

    events: list[tuple[float, float, float, float, float]] = []
    cursor = 0.16
    seen_stressed_in_word = False

    for idx, item in enumerate(orth):
        is_continuation = idx > 0 and str(orth[idx - 1]["text"]).endswith("-")
        if not is_continuation:
            seen_stressed_in_word = False

        if item["is_function_word"]:
            is_stressed = False
        elif not seen_stressed_in_word:
            is_stressed = True
            seen_stressed_in_word = True
        else:
            is_stressed = False

        pre_dur = (0.045 if is_stressed else 0.025) if item["pre"] else 0.0
        v_dur = 0.21 if is_stressed else 0.09
        if idx == n_syl - 1 or item["has_pause_after"]:
            v_dur += 0.05

        declination = 12.0 * (idx / max(1, n_syl - 1))
        f0 = (152.0 - declination) if is_stressed else (122.0 - 0.6 * declination)
        amp = 0.72 if is_stressed else 0.36

        v_start = cursor + pre_dur
        events.append((v_start, v_dur, f0, amp, pre_dur))
        gap = 0.28 if item["has_pause_after"] else 0.085
        cursor = v_start + v_dur + gap

    total_dur = max(0.8, cursor + 0.22)
    n_samples = int(round(total_dur * sample_rate))
    y = np.zeros(n_samples, dtype=np.float64)
    rng = np.random.default_rng(42)

    for v_start, v_dur, f0, amp, pre_dur in events:
        if pre_dur > 0.0:
            p_idx = max(0, int(round((v_start - pre_dur) * sample_rate)))
            n_p = max(1, int(round(pre_dur * sample_rate)))
            if p_idx + n_p <= n_samples:
                noise = rng.standard_normal(n_p)
                sos_c = butter(
                    3,
                    [3600.0 / (0.5 * sample_rate), min(0.95, 7200.0 / (0.5 * sample_rate))],
                    btype="bandpass",
                    output="sos",
                )
                cons_sig = cast(np.ndarray, sosfiltfilt(sos_c, noise))
                cons_sig /= max(float(np.max(np.abs(cons_sig))), 1e-6)
                y[p_idx : p_idx + n_p] += 0.20 * amp * cons_sig

        s_idx = int(round(v_start * sample_rate))
        n_v = max(1, int(round(v_dur * sample_rate)))
        if s_idx + n_v > n_samples:
            break
        f0_curve = f0 * (1.0 + 0.04 * np.sin(np.pi * np.linspace(0.0, 1.0, n_v)))
        phase = 2.0 * np.pi * np.cumsum(f0_curve) / sample_rate
        sig = np.zeros(n_v, dtype=np.float64)
        for h in range(1, 16):
            if h * f0 >= 3200.0:
                break
            sig += (1.0 / (h**0.68)) * np.sin(h * phase)

        sos_v = butter(
            3,
            [320.0 / (0.5 * sample_rate), 2400.0 / (0.5 * sample_rate)],
            btype="bandpass",
            output="sos",
        )
        sig = cast(np.ndarray, sosfiltfilt(sos_v, sig))
        sig /= max(float(np.max(np.abs(sig))), 1e-6)

        env = np.ones(n_v, dtype=np.float64)
        atk = min(int(0.018 * sample_rate), max(2, n_v // 4))
        rel = min(int(0.028 * sample_rate), max(2, n_v // 3))
        env[:atk] = 0.5 * (1.0 - np.cos(np.pi * np.arange(atk) / atk))
        env[-rel:] = 0.5 * (1.0 + np.cos(np.pi * np.arange(rel) / rel))
        y[s_idx : s_idx + n_v] += amp * sig * env

    y = np.clip(y, -0.96, 0.96)
    pcm16 = (y * 32767.0).astype(np.int16)
    buf = io.BytesIO()
    scipy_wavfile.write(buf, sample_rate, pcm16)
    return buf.getvalue()


def generate_prosody_reference(target_text: str) -> dict[str, Any]:
    """Synthesize reference audio for target_text, analyze prosody, and build a beat-aligned phrase."""
    clean_text = target_text.strip()
    if not clean_text:
        raise ValueError("Target sentence cannot be empty")

    audio_bytes: bytes
    mime_type: str
    synthesis_source: str

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_wav:
        temp_wav_path = tmp_wav.name

    try:
        try:
            provider = OmniVoiceTTSProvider()
            ref_audio = provider.synthesize(clean_text, output_sample_rate=16000)
            audio_bytes = ref_audio.audio_bytes
            mime_type = "audio/ogg" if ref_audio.format == "ogg" else "audio/wav"
            synthesis_source = "omnivoice"
            if sf is not None:
                decoded, sr = sf.read(io.BytesIO(audio_bytes), dtype="float32")
                sf.write(temp_wav_path, decoded, sr, format="WAV", subtype="PCM_16")
            else:
                Path(temp_wav_path).write_bytes(audio_bytes)
        except (ValueError, FileNotFoundError, RuntimeError) as exc:
            logger.info("[generate_prosody_reference] Using synthetic prosody fallback: %s", exc)
            audio_bytes = _synthesize_fallback_prosody_wav(clean_text, sample_rate=16000)
            mime_type = "audio/wav"
            synthesis_source = "synthetic_fallback"
            Path(temp_wav_path).write_bytes(audio_bytes)

        analysis = analyze_prosody_recording(temp_wav_path)
        phrase = build_prosody_phrase_from_text_and_analysis(clean_text, analysis)

        return {
            "target_text": clean_text,
            "audio_base64": base64.b64encode(audio_bytes).decode("ascii"),
            "mime_type": mime_type,
            "phrase": phrase,
            "analysis": analysis,
            "synthesis_source": synthesis_source,
        }
    finally:
        Path(temp_wav_path).unlink(missing_ok=True)
