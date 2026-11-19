"""Six candidate syllable & P-center detection algorithms for speech-guider.

Implements:
1. baseline_energy: Raw frame energy peak picking (current prosody_lab.py heuristic)
2. praat_de_jong_wempe: De Jong & Wempe (2009) Praat intensity + mindip + voicing filter
3. mermelstein_convex_hull: Mermelstein (1975) recursive vocalic convex-hull segmentation
4. theta_sonority_oscillator: Räsänen et al. (2018) multi-band sonority + 3-9 Hz theta filter
5. r4_articulatory_sonority: ContentVec-L7 + R4 articulatory aperture & glottal voicing peaks
6. hybrid_acoustic_pcenter: Proposed production detector combining vocalic-to-sibilant
   spectral balance, Praat pitch + low-frequency voice bar, 4-band formant timbre flux,
   adaptive schwa/prolonged-vowel dip logic, and Šturm & Volín (2016) / Cummins & Port (1998)
   P-center & pre-beat consonant onset tracking.
"""

from __future__ import annotations

import logging
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, cast

import numpy as np
import parselmouth
import torch
from scipy.ndimage import gaussian_filter1d
from scipy.signal import butter, find_peaks, sosfiltfilt

from src.audio.prosody_lab import (
    _bandpass_filter,
    _compute_rms_db_envelope,
    _framed_energy,
    _heuristic_pause_spans,
    _load_audio_samples,
    _normalize_prominences,
    detect_syllables_and_pcenters,
)

logger = logging.getLogger(__name__)


def _heuristic_syllable_markers(y: np.ndarray, sr: int) -> list[float]:
    """Estimate syllable nuclei from raw energy peaks (legacy baseline)."""
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
        logger.warning("[_heuristic_syllable_markers] Peak detection failed: %s", e)
        return []


@dataclass
class SyllableDetectionResult:
    """Unified return structure for syllable identification benchmarks."""

    nuclei_times: list[float]
    p_center_times: list[float]
    consonant_onset_times: list[float]
    vowel_durations: list[float]
    prominences: list[float]
    pause_spans: list[dict[str, float]]
    runtime_ms: float

    def to_dict(self) -> dict[str, Any]:
        """Serialize detection result to JSON-friendly dictionary."""
        return asdict(self)


_R4_PREDICTOR_CACHE: Any = None


def _get_r4_predictor() -> Any:
    """Lazy-load and return the local ContentVec-L7 + R4 predictor singleton."""
    global _R4_PREDICTOR_CACHE
    if _R4_PREDICTOR_CACHE is None:
        from src.models.ssl_aai_predictor import SSLAAIPredictor

        predictor = SSLAAIPredictor()
        predictor.load()
        _R4_PREDICTOR_CACHE = predictor
    return _R4_PREDICTOR_CACHE


def _extract_pause_spans_from_db(
    times: np.ndarray,
    db_env: np.ndarray,
    silence_offset_db: float = 25.0,
    min_pause_sec: float = 0.12,
) -> list[dict[str, float]]:
    """Extract internal pause spans (excluding leading/trailing silence) from dB envelope."""
    if len(db_env) == 0:
        return []
    q98 = float(np.percentile(db_env, 98))
    thresh = q98 - silence_offset_db
    active_indices = np.where(db_env >= thresh)[0]
    if len(active_indices) < 2:
        return []
    first_active = int(active_indices[0])
    last_active = int(active_indices[-1])

    silent = db_env < thresh
    spans: list[dict[str, float]] = []
    start_idx: int | None = None
    for idx in range(first_active, last_active + 1):
        if silent[idx] and start_idx is None:
            start_idx = idx
        elif not silent[idx] and start_idx is not None:
            dur = float(times[idx] - times[start_idx])
            if dur >= min_pause_sec:
                spans.append(
                    {
                        "start_time": round(float(times[start_idx]), 4),
                        "end_time": round(float(times[idx]), 4),
                        "duration": round(dur, 4),
                    }
                )
            start_idx = None
    return spans


# =============================================================================
# 1. Baseline Energy Detector (Current prosody_lab.py heuristic)
# =============================================================================
def baseline_energy(audio_path: str) -> SyllableDetectionResult:
    """Current heuristic from src/audio/prosody_lab.py:_heuristic_syllable_markers."""
    t0 = time.perf_counter()
    y, sr = _load_audio_samples(audio_path, 22050)
    nuclei = _heuristic_syllable_markers(y, sr)
    pause_spans = _heuristic_pause_spans(y, sr)

    energy = _framed_energy(y, frame_length=2048, hop_length=256)
    hop_sec = 256.0 / sr

    p_centers: list[float] = []
    c_onsets: list[float] = []
    durations: list[float] = []
    raw_proms: list[float] = []

    for nuc_t in nuclei:
        idx = min(len(energy) - 1, max(0, int(round(nuc_t / hop_sec))))
        pk_val = float(energy[idx]) if len(energy) else 0.0
        raw_proms.append(pk_val)

        left_bound = max(0, idx - int(round(0.10 / hop_sec)))
        seg = energy[left_bound : idx + 1]
        if len(seg) > 1:
            half_val = float(np.min(seg) + 0.5 * (pk_val - np.min(seg)))
            above = np.where(seg >= half_val)[0]
            p_idx = left_bound + int(above[0]) if len(above) else idx
        else:
            p_idx = idx
        p_t = float(p_idx * hop_sec)
        p_centers.append(round(p_t, 4))
        c_onsets.append(round(max(0.0, p_t - 0.02), 4))

        right_bound = min(len(energy), idx + int(round(0.20 / hop_sec)))
        r_seg = energy[idx:right_bound]
        if len(r_seg) > 1:
            below = np.where(r_seg <= pk_val * 0.5)[0]
            end_idx = idx + int(below[0]) if len(below) else right_bound - 1
        else:
            end_idx = idx
        durations.append(round(max(0.04, float((end_idx - p_idx) * hop_sec)), 4))

    runtime_ms = (time.perf_counter() - t0) * 1000.0
    return SyllableDetectionResult(
        nuclei_times=[round(float(t), 4) for t in nuclei],
        p_center_times=p_centers,
        consonant_onset_times=c_onsets,
        vowel_durations=durations,
        prominences=_normalize_prominences(raw_proms),
        pause_spans=pause_spans,
        runtime_ms=round(runtime_ms, 3),
    )


# =============================================================================
# 2. Praat De Jong & Wempe (2009) Algorithm
# =============================================================================
def praat_de_jong_wempe(
    audio_path: str,
    silence_db: float = -25.0,
    mindip_db: float = 2.0,
) -> SyllableDetectionResult:
    """De Jong & Wempe (2009) Praat syllable nuclei detector via Parselmouth."""
    t0 = time.perf_counter()
    sound = parselmouth.Sound(str(audio_path))
    intensity = sound.to_intensity(minimum_pitch=50.0, time_step=0.016, subtract_mean=True)
    pitch = sound.to_pitch_ac(
        time_step=0.016,
        pitch_floor=50.0,
        max_number_of_candidates=15,
        very_accurate=False,
        silence_threshold=0.03,
        voicing_threshold=0.45,
        octave_cost=0.01,
        octave_jump_cost=0.35,
        voiced_unvoiced_cost=0.14,
        pitch_ceiling=500.0,
    )

    vals = intensity.values.flatten()
    n_frames = len(vals)
    times = np.array(
        [intensity.get_time_from_frame_number(i + 1) for i in range(n_frames)],
        dtype=np.float64,
    )

    q99 = float(np.percentile(vals, 99)) if n_frames else 0.0
    threshold = q99 + silence_db

    candidate_peaks: list[int] = []
    for i in range(1, n_frames - 1):
        if vals[i] > threshold and vals[i] >= vals[i - 1] and vals[i] > vals[i + 1]:
            candidate_peaks.append(i)

    valid_peaks: list[int] = []
    if candidate_peaks:
        current_peak = candidate_peaks[0]
        for next_peak in candidate_peaks[1:]:
            min_between = float(np.min(vals[current_peak : next_peak + 1]))
            dip_left = float(vals[current_peak] - min_between)
            dip_right = float(vals[next_peak] - min_between)
            if dip_left >= mindip_db and dip_right >= mindip_db:
                valid_peaks.append(current_peak)
                current_peak = next_peak
            else:
                if vals[next_peak] > vals[current_peak]:
                    current_peak = next_peak
        valid_peaks.append(current_peak)

    voiced_peaks: list[int] = []
    for pk in valid_peaks:
        t_pk = float(times[pk])
        has_voice = False
        for dt in (-0.030, -0.015, 0.0, 0.015, 0.030):
            f0_val = pitch.get_value_at_time(max(0.0, min(sound.total_duration, t_pk + dt)))
            if np.isfinite(f0_val) and f0_val > 0:
                has_voice = True
                break
        if has_voice:
            voiced_peaks.append(pk)

    nuclei: list[float] = []
    p_centers: list[float] = []
    c_onsets: list[float] = []
    durations: list[float] = []
    raw_proms: list[float] = []

    for idx_pos, pk in enumerate(voiced_peaks):
        t_pk = float(times[pk])
        nuclei.append(round(t_pk, 4))
        raw_proms.append(float(vals[pk] - threshold))

        prev_pk = voiced_peaks[idx_pos - 1] if idx_pos > 0 else 0
        search_start = max(prev_pk, pk - 8)
        if pk > search_start:
            valley_rel = int(np.argmin(vals[search_start : pk + 1]))
            valley_idx = search_start + valley_rel
            seg = vals[valley_idx : pk + 1]
            diffs = np.diff(seg)
            steep_idx = valley_idx + int(np.argmax(diffs)) if len(diffs) else pk
            p_t = float(times[steep_idx])
            c_t = float(times[max(search_start, steep_idx - 1)])
        else:
            p_t = t_pk
            c_t = t_pk

        next_pk = voiced_peaks[idx_pos + 1] if idx_pos + 1 < len(voiced_peaks) else n_frames - 1
        search_end = min(next_pk, pk + 12)
        r_seg = vals[pk : search_end + 1]
        below = np.where(r_seg <= vals[pk] - 6.0)[0]
        end_idx = pk + int(below[0]) if len(below) else min(n_frames - 1, pk + 5)
        dur = max(0.04, float(times[end_idx] - p_t))

        p_centers.append(round(p_t, 4))
        c_onsets.append(round(min(p_t, c_t), 4))
        durations.append(round(dur, 4))

    pause_spans = _extract_pause_spans_from_db(times, vals, silence_offset_db=abs(silence_db))
    runtime_ms = (time.perf_counter() - t0) * 1000.0
    return SyllableDetectionResult(
        nuclei_times=nuclei,
        p_center_times=p_centers,
        consonant_onset_times=c_onsets,
        vowel_durations=durations,
        prominences=_normalize_prominences(raw_proms),
        pause_spans=pause_spans,
        runtime_ms=round(runtime_ms, 3),
    )


# =============================================================================
# 3. Mermelstein (1975) Convex-Hull Sonority Segmentation
# =============================================================================
def _convex_hull_segment(
    env: np.ndarray,
    voiced: np.ndarray,
    start_idx: int,
    end_idx: int,
    dip_thresh_db: float,
    min_frames: int,
) -> list[tuple[int, int, int]]:
    """Recursively split sonority envelope using Mermelstein (1975) convex hull."""
    if end_idx - start_idx < min_frames:
        return []
    seg = env[start_idx : end_idx + 1]
    v_seg = voiced[start_idx : end_idx + 1]
    if not np.any(v_seg):
        return []

    peak_rel = int(np.argmax(seg))
    hull = np.empty_like(seg)
    hull[: peak_rel + 1] = np.maximum.accumulate(seg[: peak_rel + 1])
    hull[peak_rel:] = np.maximum.accumulate(seg[peak_rel:][::-1])[::-1]

    dips = hull - seg
    margin = max(2, min_frames // 3)
    if len(dips) > 2 * margin:
        inner_dips = dips[margin:-margin]
        max_dip_rel = margin + int(np.argmax(inner_dips))
        max_dip_val = float(dips[max_dip_rel])
        split_idx = start_idx + max_dip_rel
        if (
            max_dip_val >= dip_thresh_db
            and (split_idx - start_idx) >= min_frames
            and (end_idx - split_idx) >= min_frames
            and np.any(voiced[start_idx:split_idx])
            and np.any(voiced[split_idx + 1 : end_idx + 1])
        ):
            left_parts = _convex_hull_segment(
                env, voiced, start_idx, split_idx, dip_thresh_db, min_frames
            )
            right_parts = _convex_hull_segment(
                env, voiced, split_idx, end_idx, dip_thresh_db, min_frames
            )
            if left_parts and right_parts:
                return left_parts + right_parts

    voiced_indices = np.where(v_seg)[0]
    best_rel = int(voiced_indices[np.argmax(seg[voiced_indices])])
    return [(start_idx, start_idx + best_rel, end_idx)]


def mermelstein_convex_hull(
    audio_path: str,
    dip_thresh_db: float = 2.4,
) -> SyllableDetectionResult:
    """Mermelstein (1975) convex-hull segmentation on 300-3000 Hz vocalic band."""
    t0 = time.perf_counter()
    sound = parselmouth.Sound(str(audio_path))
    sr = int(sound.sampling_frequency)
    y = sound.values[0]

    y_voc = _bandpass_filter(y, sr, 300.0, 3000.0, order=4)
    hop_sec = 0.010
    times, db_env = _compute_rms_db_envelope(
        y_voc, sr, hop_sec=hop_sec, win_sec=0.025, smooth_sigma=1.5
    )

    pitch = sound.to_pitch_ac(time_step=hop_sec, pitch_floor=55.0, pitch_ceiling=500.0)
    voiced = np.array(
        [
            bool(
                np.isfinite(pitch.get_value_at_time(float(t)))
                and pitch.get_value_at_time(float(t)) > 0
            )
            for t in times
        ],
        dtype=bool,
    )

    q99 = float(np.percentile(db_env, 99)) if len(db_env) else 0.0
    floor_db = q99 - 25.0
    active = db_env > floor_db

    segments: list[tuple[int, int, int]] = []
    in_chunk = False
    chunk_start = 0
    min_frames = max(5, int(round(0.060 / hop_sec)))

    for idx, is_act in enumerate(active):
        if is_act and not in_chunk:
            in_chunk = True
            chunk_start = idx
        elif not is_act and in_chunk:
            in_chunk = False
            segments.extend(
                _convex_hull_segment(
                    db_env, voiced, chunk_start, idx - 1, dip_thresh_db, min_frames
                )
            )
    if in_chunk:
        segments.extend(
            _convex_hull_segment(
                db_env, voiced, chunk_start, len(active) - 1, dip_thresh_db, min_frames
            )
        )

    nuclei: list[float] = []
    p_centers: list[float] = []
    c_onsets: list[float] = []
    durations: list[float] = []
    raw_proms: list[float] = []

    for s_idx, pk_idx, e_idx in segments:
        t_pk = float(times[pk_idx])
        nuclei.append(round(t_pk, 4))
        raw_proms.append(float(db_env[pk_idx] - floor_db))

        rising = db_env[s_idx : pk_idx + 1]
        if len(rising) > 1:
            steep_rel = int(np.argmax(np.diff(rising)))
            p_idx = s_idx + steep_rel
        else:
            p_idx = pk_idx
        p_t = float(times[p_idx])
        c_t = float(times[s_idx])
        p_centers.append(round(p_t, 4))
        c_onsets.append(round(min(p_t, c_t), 4))
        durations.append(round(max(0.04, float(times[e_idx] - p_t)), 4))

    pause_spans = _extract_pause_spans_from_db(times, db_env, silence_offset_db=25.0)
    runtime_ms = (time.perf_counter() - t0) * 1000.0
    return SyllableDetectionResult(
        nuclei_times=nuclei,
        p_center_times=p_centers,
        consonant_onset_times=c_onsets,
        vowel_durations=durations,
        prominences=_normalize_prominences(raw_proms),
        pause_spans=pause_spans,
        runtime_ms=round(runtime_ms, 3),
    )


# =============================================================================
# 4. Theta Sonority Oscillator (Räsänen et al. 2018)
# =============================================================================
def theta_sonority_oscillator(audio_path: str) -> SyllableDetectionResult:
    """Subband vocalic sonority envelope penalized by HF frication + 3-9 Hz theta filter."""
    t0 = time.perf_counter()
    sound = parselmouth.Sound(str(audio_path))
    sr = int(sound.sampling_frequency)
    y = sound.values[0]

    edges = np.geomspace(250.0, 3500.0, 7)
    hop_sec = 0.005
    subband_envs: list[np.ndarray] = []
    times: np.ndarray = np.array([0.0])
    for b_idx in range(6):
        sub_y = _bandpass_filter(y, sr, float(edges[b_idx]), float(edges[b_idx + 1]), order=3)
        times, env_db = _compute_rms_db_envelope(
            sub_y, sr, hop_sec=hop_sec, win_sec=0.020, smooth_sigma=1.0
        )
        lin_amp = 10.0 ** (env_db / 20.0)
        subband_envs.append(lin_amp**0.3)

    vocalic_sonority = np.sum(subband_envs, axis=0)

    if 0.5 * sr > 4200.0:
        hf_y = _bandpass_filter(y, sr, 4000.0, min(7800.0, 0.48 * sr), order=3)
        _, hf_db = _compute_rms_db_envelope(
            hf_y, sr, hop_sec=hop_sec, win_sec=0.020, smooth_sigma=1.0
        )
        hf_amp = (10.0 ** (hf_db / 20.0)) ** 0.3
        sonority_raw = np.maximum(0.0, vocalic_sonority - 1.2 * hf_amp)
    else:
        sonority_raw = vocalic_sonority

    env_fs = 1.0 / hop_sec
    sos_theta = butter(
        3, [3.0 / (0.5 * env_fs), 9.0 / (0.5 * env_fs)], btype="bandpass", output="sos"
    )
    theta_wave = cast(np.ndarray, sosfiltfilt(sos_theta, sonority_raw))

    pitch = sound.to_pitch_ac(time_step=0.010, pitch_floor=55.0, pitch_ceiling=500.0)
    max_son = float(np.percentile(sonority_raw, 98)) if len(sonority_raw) else 1.0
    min_dist_frames = max(1, int(round(0.095 / hop_sec)))
    peaks, _ = find_peaks(
        theta_wave,
        distance=min_dist_frames,
        prominence=max(1e-6, float(np.std(theta_wave)) * 0.28),
    )

    nuclei: list[float] = []
    p_centers: list[float] = []
    c_onsets: list[float] = []
    durations: list[float] = []
    raw_proms: list[float] = []

    for pk in peaks:
        t_pk = float(times[pk])
        if sonority_raw[pk] < 0.14 * max_son:
            continue
        voiced_near = False
        for dt in (-0.02, 0.0, 0.02):
            f0_v = pitch.get_value_at_time(max(0.0, min(sound.total_duration, t_pk + dt)))
            if np.isfinite(f0_v) and f0_v > 0:
                voiced_near = True
                break
        if not voiced_near:
            continue

        nuclei.append(round(t_pk, 4))
        raw_proms.append(float(sonority_raw[pk]))

        left = max(0, pk - int(round(0.11 / hop_sec)))
        seg = theta_wave[left : pk + 1]
        if len(seg) > 1:
            p_idx = left + int(np.argmax(np.diff(seg)))
        else:
            p_idx = pk
        p_t = float(times[p_idx])
        p_centers.append(round(p_t, 4))
        c_onsets.append(round(max(0.0, p_t - 0.025), 4))
        durations.append(round(max(0.05, 2.0 * (t_pk - p_t)), 4))

    _, full_db = _compute_rms_db_envelope(y, sr, hop_sec=0.010, win_sec=0.025, smooth_sigma=1.5)
    pause_spans = _extract_pause_spans_from_db(
        np.arange(len(full_db)) * 0.010, full_db, silence_offset_db=25.0
    )
    runtime_ms = (time.perf_counter() - t0) * 1000.0
    return SyllableDetectionResult(
        nuclei_times=nuclei,
        p_center_times=p_centers,
        consonant_onset_times=c_onsets,
        vowel_durations=durations,
        prominences=_normalize_prominences(raw_proms),
        pause_spans=pause_spans,
        runtime_ms=round(runtime_ms, 3),
    )


# =============================================================================
# 5. R4 Articulatory Sonority Detector (ContentVec-L7 + R4)
# =============================================================================
def r4_articulatory_sonority(audio_path: str) -> SyllableDetectionResult:
    """Syllable detection from R4 articulatory opening (LA, TBCD, TTCD) & glottal voicing."""
    t0 = time.perf_counter()
    sound = parselmouth.Sound(str(audio_path))
    sound_16k = sound if int(sound.sampling_frequency) == 16000 else sound.resample(16000)
    wav_16k = np.asarray(sound_16k.values[0], dtype=np.float32)

    predictor = _get_r4_predictor()
    with torch.no_grad():
        out = predictor.predict_with_metadata(torch.from_numpy(wav_16k), 16000)
    tvs = out["tvs"].numpy()
    times = out["center_samples"].numpy().astype(np.float64) / 16000.0

    la = tvs[:, 1]
    ttcd = tvs[:, 3]
    tbcd = tvs[:, 5]
    glo = tvs[:, 7]

    oral_openness = 0.45 * la + 0.30 * tbcd + 0.25 * ttcd
    voicing_prob = np.clip(1.0 - glo, 0.0, 1.0)
    artic_sonority = gaussian_filter1d(oral_openness * voicing_prob, sigma=1.0)

    max_son = float(np.percentile(artic_sonority, 98)) if len(artic_sonority) else 1.0
    peaks, _ = find_peaks(
        artic_sonority,
        height=max(0.08, 0.22 * max_son),
        distance=5,
        prominence=max(0.02, 0.06 * max_son),
    )

    nuclei: list[float] = []
    p_centers: list[float] = []
    c_onsets: list[float] = []
    durations: list[float] = []
    raw_proms: list[float] = []

    for pk in peaks:
        if voicing_prob[pk] < 0.25:
            continue
        t_pk = float(times[pk])
        nuclei.append(round(t_pk, 4))
        raw_proms.append(float(artic_sonority[pk]))

        left = max(0, pk - 5)
        seg = artic_sonority[left : pk + 1]
        if len(seg) > 1:
            p_idx = left + int(np.argmax(np.diff(seg)))
        else:
            p_idx = pk
        p_t = float(times[p_idx])
        c_idx = left + int(np.argmin(oral_openness[left : pk + 1]))
        c_t = float(times[min(p_idx, c_idx)])
        p_centers.append(round(p_t, 4))
        c_onsets.append(round(c_t, 4))

        right = min(len(artic_sonority) - 1, pk + 6)
        r_seg = artic_sonority[pk : right + 1]
        below = np.where(r_seg <= 0.55 * artic_sonority[pk])[0]
        end_idx = pk + int(below[0]) if len(below) else min(len(artic_sonority) - 1, pk + 3)
        durations.append(round(max(0.04, float(times[end_idx] - p_t)), 4))

    pause_spans: list[dict[str, float]] = []
    silent = voicing_prob < 0.15
    act_idx = np.where(~silent)[0]
    if len(act_idx) >= 2:
        start_i: int | None = None
        for i in range(int(act_idx[0]), int(act_idx[-1]) + 1):
            if silent[i] and start_i is None:
                start_i = i
            elif not silent[i] and start_i is not None:
                dur = float(times[i] - times[start_i])
                if dur >= 0.12:
                    pause_spans.append(
                        {
                            "start_time": round(float(times[start_i]), 4),
                            "end_time": round(float(times[i]), 4),
                            "duration": round(dur, 4),
                        }
                    )
                start_i = None

    runtime_ms = (time.perf_counter() - t0) * 1000.0
    return SyllableDetectionResult(
        nuclei_times=nuclei,
        p_center_times=p_centers,
        consonant_onset_times=c_onsets,
        vowel_durations=durations,
        prominences=_normalize_prominences(raw_proms),
        pause_spans=pause_spans,
        runtime_ms=round(runtime_ms, 3),
    )


# =============================================================================
# 6. Hybrid Acoustic P-Center Detector (Proposed Production Winner)
# =============================================================================
def hybrid_acoustic_pcenter(audio_path: str) -> SyllableDetectionResult:
    """Production-grade acoustic syllable & P-center detector for speech-guider.

    Delegates syllable and P-center detection to `src.audio.prosody_lab.detect_syllables_and_pcenters`.
    """
    t0 = time.perf_counter()
    sound = parselmouth.Sound(str(audio_path))
    sr = int(sound.sampling_frequency)
    y = sound.values[0]
    if sound.values.shape[0] > 1:
        y = np.mean(sound.values, axis=0)

    detected = detect_syllables_and_pcenters(y, sr, sound=sound)
    times, full_db = _compute_rms_db_envelope(y, sr, hop_sec=0.005, win_sec=0.016, smooth_sigma=1.0)
    pause_spans = _extract_pause_spans_from_db(times, full_db, silence_offset_db=25.0)
    runtime_ms = (time.perf_counter() - t0) * 1000.0
    return SyllableDetectionResult(
        nuclei_times=detected["nuclei_times"],
        p_center_times=detected["p_center_times"],
        consonant_onset_times=detected["consonant_onset_times"],
        vowel_durations=detected["vowel_durations"],
        prominences=detected["prominences"],
        pause_spans=pause_spans,
        runtime_ms=round(runtime_ms, 3),
    )


ALGORITHMS: dict[str, Callable[[str], SyllableDetectionResult]] = {
    "baseline_energy": baseline_energy,
    "praat_de_jong_wempe": praat_de_jong_wempe,
    "mermelstein_convex_hull": mermelstein_convex_hull,
    "theta_sonority_oscillator": theta_sonority_oscillator,
    "r4_articulatory_sonority": r4_articulatory_sonority,
    "hybrid_acoustic_pcenter": hybrid_acoustic_pcenter,
}


def detect_syllables(
    audio_path: str | Path,
    algorithm: str = "hybrid_acoustic_pcenter",
) -> SyllableDetectionResult:
    """Unified entrypoint for syllable and P-center detection across all 6 algorithms."""
    if algorithm not in ALGORITHMS:
        raise ValueError(f"Unknown algorithm '{algorithm}'. Valid options: {list(ALGORITHMS)}")
    return ALGORITHMS[algorithm](str(audio_path))
