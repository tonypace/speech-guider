"""Reproducible benchmark suite for syllable & P-center identification in speech-guider.

Builds a 21-item evaluation corpus across:
1. Parametric Synthetic Speech Corpus (10 items with exact analytical ground-truth
   vowel nucleus timestamps, P-center timestamps, consonant lead-in onsets,
   unvoiced sibilant/plosive distractors, fast/slow speech rates, prolonged
   vibrato vowels, and hesitation blocks).
2. Real Recorded Speech (5 items: omnivoice-tts/examples/freeman.wav full 17.26s
   recording + 4 single-sentence slices freeman_s1..s4).
3. OmniVoice TTS Synthesized Utterances (6 items cached in fixtures/).

Evaluates all 6 candidate detectors in `detectors.py` and writes:
- `research/speech-rhythm/experiments/results.json`
- `research/speech-rhythm/experiments/README.md`
"""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import parselmouth
from scipy.io import wavfile
from scipy.signal import butter, sosfiltfilt

PROJECT_ROOT = Path(__file__).resolve().parents[3]
EXPERIMENTS_DIR = Path(__file__).resolve().parent
FIXTURES_DIR = EXPERIMENTS_DIR / "fixtures"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(EXPERIMENTS_DIR) not in sys.path:
    sys.path.insert(0, str(EXPERIMENTS_DIR))

from detectors import ALGORITHMS, SyllableDetectionResult  # noqa: E402


@dataclass
class SyllableSpec:
    """Analytical specification of one synthetic syllable for waveform generation."""

    v_onset_sec: float
    v_dur_sec: float
    f0_start_hz: float
    f0_end_hz: float
    formants_hz: tuple[float, float, float]
    amp_db: float = 0.0
    pre_consonant_dur_sec: float = 0.0
    pre_consonant_type: str = "none"  # "sibilant", "plosive", "cluster", "none"
    vibrato_hz: float = 0.0
    vibrato_depth_db: float = 0.0
    is_prolonged: bool = False


@dataclass
class UnvoicedBurstSpec:
    """Standalone unvoiced consonant burst distractor (/s/, /t/, /k/, /p/)."""

    onset_sec: float
    dur_sec: float
    kind: str  # "sibilant" or "plosive"
    amp_scale: float = 0.85


@dataclass
class BenchmarkItem:
    """Single benchmark test case with ground-truth metadata."""

    item_id: str
    category: str  # "synthetic", "real", "tts"
    description: str
    audio_path: str
    duration_sec: float
    gt_count: int
    canonical_count: int
    gt_nuclei_times: list[float] = field(default_factory=list)
    gt_p_center_times: list[float] = field(default_factory=list)
    gt_consonant_onset_times: list[float] = field(default_factory=list)
    gt_vowel_durations: list[float] = field(default_factory=list)
    unvoiced_burst_times: list[float] = field(default_factory=list)
    prolonged_vowel_spans: list[tuple[float, float]] = field(default_factory=list)


# Distinct vowel formant presets (F1, F2, F3 in Hz) so adjacent syllables have realistic formant transitions
VOWEL_FORMANTS: dict[str, tuple[float, float, float]] = {
    "a": (730.0, 1090.0, 2440.0),
    "i": (280.0, 2250.0, 2950.0),
    "u": (320.0, 880.0, 2250.0),
    "e": (480.0, 1950.0, 2650.0),
    "o": (520.0, 920.0, 2400.0),
    "schwa": (500.0, 1500.0, 2500.0),
}


def _synthesize_glottal_formant_vowel(
    sr: int,
    dur_sec: float,
    f0_start: float,
    f0_end: float,
    formants: tuple[float, float, float],
    amp_db: float,
    vibrato_hz: float = 0.0,
    vibrato_depth_db: float = 0.0,
    rng: np.random.Generator | None = None,
) -> tuple[np.ndarray, float, float]:
    """Synthesize a realistic formant-filtered voiced vowel with analytical P-center & nucleus peak.

    Returns:
        (waveform, rel_p_center_sec, rel_nucleus_peak_sec)
    """
    n_samples = max(16, int(round(dur_sec * sr)))
    t = np.arange(n_samples, dtype=np.float64) / sr

    # Instantaneous phase for harmonic glottal pulse train
    f0_t = np.linspace(f0_start, f0_end, n_samples)
    phase = 2.0 * np.pi * np.cumsum(f0_t) / sr

    source = np.zeros(n_samples, dtype=np.float64)
    max_harm = min(38, int((0.46 * sr) // max(f0_start, f0_end)))
    for k in range(1, max_harm + 1):
        # -6 dB/octave glottal spectral tilt
        source += (1.0 / (k**1.15)) * np.sin(k * phase)

    # Parallel 3-formant resonator bank (F1, F2, F3) with natural vocal-tract bandwidths
    f1, f2, f3 = formants
    bws = (130.0, 180.0, 240.0)
    gains = (1.0, 0.65, 0.30)
    vocalic = np.zeros(n_samples, dtype=np.float64)
    nyq = 0.5 * sr
    for fc, bw, g in zip((f1, f2, f3), bws, gains):
        lo = max(60.0, fc - 0.5 * bw) / nyq
        hi = min(0.95, (fc + 0.5 * bw) / nyq)
        if hi > lo + 0.005:
            sos = butter(2, [lo, hi], btype="bandpass", output="sos")
            vocalic += g * sosfiltfilt(sos, source)

    # Stabilize short-time pitch-harmonic envelope before applying target prosodic contour
    win_norm = max(32, int(round(0.025 * sr)))
    local_pow = np.convolve(vocalic**2, np.ones(win_norm) / win_norm, mode="same")
    vocalic = vocalic / np.sqrt(local_pow + 1e-8)
    rms = float(np.sqrt(np.mean(vocalic**2) + 1e-12))
    vocalic = vocalic / rms

    # Smooth raised-cosine attack and release envelope:
    # Attack duration is min(28ms, 0.30 * dur_sec). Half-rise point is at 0.5 * attack_sec.
    attack_sec = min(0.028, 0.28 * dur_sec)
    release_sec = min(0.040, 0.35 * dur_sec)
    n_att = max(4, int(round(attack_sec * sr)))
    n_rel = max(4, int(round(release_sec * sr)))

    env = np.ones(n_samples, dtype=np.float64)
    env[:n_att] = 0.5 * (1.0 - np.cos(np.pi * np.arange(n_att) / n_att))
    env[-n_rel:] = 0.5 * (1.0 + np.cos(np.pi * np.arange(n_rel) / n_rel))

    # Arch contour peaking near 42% of vowel duration (unless vibrato modulation is active)
    arch = np.sin(np.pi * np.clip(t / max(dur_sec, 1e-4), 0.0, 1.0)) ** 0.35
    env = env * arch

    if vibrato_hz > 0.0 and vibrato_depth_db > 0.0:
        # Amplitude tremor/vibrato on prolonged vowel (e.g. +-2.3 dB at 5.8 Hz)
        mod_db = vibrato_depth_db * np.sin(2.0 * np.pi * vibrato_hz * t)
        env = env * (10.0 ** (mod_db / 20.0))

    scale = 0.38 * (10.0 ** (amp_db / 20.0))
    waveform = scale * env * vocalic

    rel_p_center = 0.5 * attack_sec
    rel_peak = float(np.argmax(env) / sr) if vibrato_hz == 0.0 else 0.42 * dur_sec
    return waveform, rel_p_center, rel_peak


def _synthesize_unvoiced_consonant(
    sr: int,
    dur_sec: float,
    kind: str,
    amp_scale: float,
    rng: np.random.Generator,
) -> np.ndarray:
    """Synthesize unvoiced high-frequency sibilant (/s/) or plosive burst (/t/, /k/, /p/)."""
    n_samples = max(8, int(round(dur_sec * sr)))
    noise = rng.standard_normal(n_samples)
    nyq = 0.5 * sr
    if kind == "sibilant":
        sos = butter(4, [4200.0 / nyq, min(0.96, 7600.0 / nyq)], btype="bandpass", output="sos")
        filtered = sosfiltfilt(sos, noise)
        env = np.hanning(n_samples)
    elif kind == "cluster":
        sos = butter(4, [3800.0 / nyq, min(0.96, 7500.0 / nyq)], btype="bandpass", output="sos")
        filtered = sosfiltfilt(sos, noise)
        env = np.sin(np.pi * np.linspace(0.0, 1.0, n_samples)) ** 0.6
    else:
        # Plosive release burst + aspiration (> 3600 Hz)
        sos = butter(4, [3600.0 / nyq, min(0.96, 7600.0 / nyq)], btype="bandpass", output="sos")
        filtered = sosfiltfilt(sos, noise)
        t_rel = np.linspace(0.0, 1.0, n_samples)
        env = np.exp(-3.5 * t_rel)
        env[: min(n_samples, max(2, n_samples // 6))] *= 1.6

    rms = float(np.sqrt(np.mean(filtered**2) + 1e-12))
    return np.asarray((amp_scale * 0.28 * (filtered / rms) * env), dtype=np.float64)


def _render_synthetic_item(
    item_id: str,
    description: str,
    total_dur_sec: float,
    syllables: list[SyllableSpec],
    distractor_bursts: list[UnvoicedBurstSpec] | None = None,
    seed: int = 1234,
) -> BenchmarkItem:
    """Render a parametric synthetic utterance to WAV and return its exact BenchmarkItem."""
    sr = 16000
    rng = np.random.default_rng(seed)
    n_total = int(round(total_dur_sec * sr))
    # Subtle -58 dB room floor so Praat autocorrelation & log-intensity behave smoothly
    canvas = rng.standard_normal(n_total) * 0.0008

    gt_nuclei: list[float] = []
    gt_p_centers: list[float] = []
    gt_c_onsets: list[float] = []
    gt_v_durs: list[float] = []
    burst_centers: list[float] = []
    prolonged_spans: list[tuple[float, float]] = []

    for syll in syllables:
        v_wav, rel_p, rel_pk = _synthesize_glottal_formant_vowel(
            sr=sr,
            dur_sec=syll.v_dur_sec,
            f0_start=syll.f0_start_hz,
            f0_end=syll.f0_end_hz,
            formants=syll.formants_hz,
            amp_db=syll.amp_db,
            vibrato_hz=syll.vibrato_hz,
            vibrato_depth_db=syll.vibrato_depth_db,
            rng=rng,
        )
        i0 = max(0, int(round(syll.v_onset_sec * sr)))
        i1 = min(n_total, i0 + len(v_wav))
        canvas[i0:i1] += v_wav[: i1 - i0]

        p_time = syll.v_onset_sec + rel_p
        pk_time = syll.v_onset_sec + rel_pk
        c_time = max(0.0, syll.v_onset_sec - syll.pre_consonant_dur_sec)

        if syll.pre_consonant_dur_sec > 0.005 and syll.pre_consonant_type != "none":
            c_wav = _synthesize_unvoiced_consonant(
                sr=sr,
                dur_sec=syll.pre_consonant_dur_sec,
                kind=syll.pre_consonant_type,
                amp_scale=0.75,
                rng=rng,
            )
            c0 = max(0, int(round(c_time * sr)))
            c1 = min(n_total, c0 + len(c_wav))
            canvas[c0:c1] += c_wav[: c1 - c0]

        gt_nuclei.append(round(pk_time, 4))
        gt_p_centers.append(round(p_time, 4))
        gt_c_onsets.append(round(c_time if syll.pre_consonant_dur_sec > 0.005 else p_time, 4))
        gt_v_durs.append(round(syll.v_dur_sec, 4))
        if syll.is_prolonged:
            prolonged_spans.append(
                (round(syll.v_onset_sec, 4), round(syll.v_onset_sec + syll.v_dur_sec, 4))
            )

    for burst in distractor_bursts or []:
        b_wav = _synthesize_unvoiced_consonant(
            sr=sr,
            dur_sec=burst.dur_sec,
            kind=burst.kind,
            amp_scale=burst.amp_scale,
            rng=rng,
        )
        b0 = max(0, int(round(burst.onset_sec * sr)))
        b1 = min(n_total, b0 + len(b_wav))
        canvas[b0:b1] += b_wav[: b1 - b0]
        burst_centers.append(round(burst.onset_sec + 0.5 * burst.dur_sec, 4))

    peak_abs = float(np.max(np.abs(canvas)))
    if peak_abs > 0.95:
        canvas = canvas * (0.92 / peak_abs)

    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    out_path = FIXTURES_DIR / f"{item_id}.wav"
    pcm16 = (np.clip(canvas, -1.0, 1.0) * 32767.0).astype(np.int16)
    wavfile.write(str(out_path), sr, pcm16)

    return BenchmarkItem(
        item_id=item_id,
        category="synthetic",
        description=description,
        audio_path=str(out_path),
        duration_sec=round(total_dur_sec, 4),
        gt_count=len(syllables),
        canonical_count=len(syllables),
        gt_nuclei_times=gt_nuclei,
        gt_p_center_times=gt_p_centers,
        gt_consonant_onset_times=gt_c_onsets,
        gt_vowel_durations=gt_v_durs,
        unvoiced_burst_times=burst_centers,
        prolonged_vowel_spans=prolonged_spans,
    )


def build_synthetic_corpus() -> list[BenchmarkItem]:
    """Construct the 10-item Parametric Synthetic Speech Corpus."""
    items: list[BenchmarkItem] = []

    # 1. Clean 4-syllable stressed + reduced schwa trochaic feet (200ms vs 55ms)
    items.append(
        _render_synthetic_item(
            item_id="synth_clean_4syll",
            description="4 syllables: alternating 200ms stressed vowels and 55ms reduced schwas",
            total_dur_sec=1.35,
            syllables=[
                SyllableSpec(
                    0.18,
                    0.20,
                    155.0,
                    145.0,
                    VOWEL_FORMANTS["a"],
                    amp_db=0.0,
                    pre_consonant_dur_sec=0.03,
                    pre_consonant_type="plosive",
                ),
                SyllableSpec(0.45, 0.055, 125.0, 120.0, VOWEL_FORMANTS["schwa"], amp_db=-6.5),
                SyllableSpec(
                    0.62,
                    0.20,
                    165.0,
                    140.0,
                    VOWEL_FORMANTS["i"],
                    amp_db=0.5,
                    pre_consonant_dur_sec=0.04,
                    pre_consonant_type="plosive",
                ),
                SyllableSpec(0.90, 0.055, 118.0, 110.0, VOWEL_FORMANTS["schwa"], amp_db=-7.0),
            ],
            seed=101,
        )
    )

    # 2. Clean 6-syllable iambic feet with 55ms schwas and 200ms stressed anchors
    items.append(
        _render_synthetic_item(
            item_id="synth_clean_6syll",
            description="6 syllables: iambic rhythm with three 55ms unstressed schwas and three 200ms stressed nuclei",
            total_dur_sec=1.80,
            syllables=[
                SyllableSpec(0.15, 0.055, 125.0, 128.0, VOWEL_FORMANTS["schwa"], amp_db=-6.0),
                SyllableSpec(
                    0.29,
                    0.20,
                    160.0,
                    150.0,
                    VOWEL_FORMANTS["e"],
                    amp_db=0.0,
                    pre_consonant_dur_sec=0.04,
                    pre_consonant_type="plosive",
                ),
                SyllableSpec(0.58, 0.055, 122.0, 120.0, VOWEL_FORMANTS["schwa"], amp_db=-6.5),
                SyllableSpec(
                    0.72,
                    0.19,
                    158.0,
                    142.0,
                    VOWEL_FORMANTS["a"],
                    amp_db=0.0,
                    pre_consonant_dur_sec=0.04,
                    pre_consonant_type="plosive",
                ),
                SyllableSpec(1.01, 0.055, 120.0, 118.0, VOWEL_FORMANTS["schwa"], amp_db=-7.0),
                SyllableSpec(
                    1.16,
                    0.22,
                    170.0,
                    115.0,
                    VOWEL_FORMANTS["o"],
                    amp_db=1.0,
                    pre_consonant_dur_sec=0.05,
                    pre_consonant_type="plosive",
                ),
            ],
            seed=102,
        )
    )

    # 3. Clean 7-syllable dactylic/anapestic sequence with double-schwa trough
    items.append(
        _render_synthetic_item(
            item_id="synth_clean_7syll",
            description="7 syllables: double-schwa unstressed foot trough (55ms + 55ms) between stressed anchors",
            total_dur_sec=1.95,
            syllables=[
                SyllableSpec(0.16, 0.19, 160.0, 148.0, VOWEL_FORMANTS["i"], amp_db=0.0),
                SyllableSpec(0.42, 0.055, 125.0, 122.0, VOWEL_FORMANTS["schwa"], amp_db=-6.5),
                SyllableSpec(0.55, 0.055, 122.0, 120.0, VOWEL_FORMANTS["u"], amp_db=-6.0),
                SyllableSpec(
                    0.69,
                    0.20,
                    168.0,
                    145.0,
                    VOWEL_FORMANTS["a"],
                    amp_db=0.5,
                    pre_consonant_dur_sec=0.04,
                    pre_consonant_type="plosive",
                ),
                SyllableSpec(0.97, 0.055, 120.0, 118.0, VOWEL_FORMANTS["schwa"], amp_db=-6.5),
                SyllableSpec(1.11, 0.18, 152.0, 138.0, VOWEL_FORMANTS["e"], amp_db=-0.5),
                SyllableSpec(
                    1.38,
                    0.22,
                    162.0,
                    112.0,
                    VOWEL_FORMANTS["o"],
                    amp_db=0.8,
                    pre_consonant_dur_sec=0.04,
                    pre_consonant_type="plosive",
                ),
            ],
            seed=103,
        )
    )

    # 4. Clean 9-syllable multi-foot utterance
    items.append(
        _render_synthetic_item(
            item_id="synth_clean_9syll",
            description="9 syllables: multi-foot prosodic phrase with 50-60ms schwas and 190-220ms stressed vowels",
            total_dur_sec=2.35,
            syllables=[
                SyllableSpec(0.14, 0.055, 124.0, 126.0, VOWEL_FORMANTS["schwa"], amp_db=-6.0),
                SyllableSpec(
                    0.27,
                    0.19,
                    162.0,
                    148.0,
                    VOWEL_FORMANTS["a"],
                    amp_db=0.0,
                    pre_consonant_dur_sec=0.035,
                    pre_consonant_type="plosive",
                ),
                SyllableSpec(0.53, 0.052, 122.0, 120.0, VOWEL_FORMANTS["i"], amp_db=-6.5),
                SyllableSpec(0.65, 0.055, 120.0, 118.0, VOWEL_FORMANTS["schwa"], amp_db=-6.8),
                SyllableSpec(
                    0.79,
                    0.20,
                    168.0,
                    145.0,
                    VOWEL_FORMANTS["e"],
                    amp_db=0.5,
                    pre_consonant_dur_sec=0.04,
                    pre_consonant_type="plosive",
                ),
                SyllableSpec(1.07, 0.055, 124.0, 120.0, VOWEL_FORMANTS["schwa"], amp_db=-6.2),
                SyllableSpec(1.20, 0.18, 155.0, 140.0, VOWEL_FORMANTS["u"], amp_db=-0.5),
                SyllableSpec(1.46, 0.055, 120.0, 116.0, VOWEL_FORMANTS["schwa"], amp_db=-6.5),
                SyllableSpec(
                    1.60,
                    0.22,
                    172.0,
                    112.0,
                    VOWEL_FORMANTS["o"],
                    amp_db=1.0,
                    pre_consonant_dur_sec=0.045,
                    pre_consonant_type="plosive",
                ),
            ],
            seed=104,
        )
    )

    # 5. Heavy sibilant/plosive consonant clusters (5 voiced syllables + 6 loud unvoiced bursts)
    items.append(
        _render_synthetic_item(
            item_id="synth_sibilant_cluster_5syll",
            description="5 voiced syllables flanked by 6 loud unvoiced /s/, /t/, /k/ bursts that fool naive energy pickers",
            total_dur_sec=2.15,
            syllables=[
                SyllableSpec(0.28, 0.17, 155.0, 145.0, VOWEL_FORMANTS["a"], amp_db=0.0),
                SyllableSpec(0.64, 0.16, 150.0, 140.0, VOWEL_FORMANTS["i"], amp_db=-0.5),
                SyllableSpec(1.00, 0.06, 125.0, 120.0, VOWEL_FORMANTS["schwa"], amp_db=-5.5),
                SyllableSpec(1.26, 0.19, 168.0, 142.0, VOWEL_FORMANTS["e"], amp_db=0.8),
                SyllableSpec(1.66, 0.20, 160.0, 115.0, VOWEL_FORMANTS["o"], amp_db=0.5),
            ],
            distractor_bursts=[
                UnvoicedBurstSpec(0.11, 0.08, "sibilant", amp_scale=1.15),
                UnvoicedBurstSpec(0.49, 0.07, "sibilant", amp_scale=1.10),
                UnvoicedBurstSpec(0.84, 0.06, "plosive", amp_scale=1.10),
                UnvoicedBurstSpec(1.11, 0.07, "sibilant", amp_scale=1.20),
                UnvoicedBurstSpec(1.50, 0.07, "plosive", amp_scale=1.15),
                UnvoicedBurstSpec(1.92, 0.09, "sibilant", amp_scale=1.25),
            ],
            seed=105,
        )
    )

    # 6. Pre-beat consonant clusters & plosive codas (6 voiced syllables + 4 unvoiced bursts)
    items.append(
        _render_synthetic_item(
            item_id="synth_plosive_coda_6syll",
            description="6 syllables with 75-90ms pre-beat consonant clusters (/sp/, /tr/, /kl/) and 4 unvoiced stop releases",
            total_dur_sec=2.25,
            syllables=[
                SyllableSpec(
                    0.24,
                    0.17,
                    152.0,
                    142.0,
                    VOWEL_FORMANTS["e"],
                    amp_db=0.0,
                    pre_consonant_dur_sec=0.080,
                    pre_consonant_type="cluster",
                ),
                SyllableSpec(
                    0.50,
                    0.06,
                    125.0,
                    120.0,
                    VOWEL_FORMANTS["schwa"],
                    amp_db=-6.0,
                    pre_consonant_dur_sec=0.030,
                    pre_consonant_type="plosive",
                ),
                SyllableSpec(
                    0.76,
                    0.19,
                    164.0,
                    146.0,
                    VOWEL_FORMANTS["a"],
                    amp_db=0.5,
                    pre_consonant_dur_sec=0.085,
                    pre_consonant_type="cluster",
                ),
                SyllableSpec(
                    1.06,
                    0.06,
                    122.0,
                    118.0,
                    VOWEL_FORMANTS["i"],
                    amp_db=-5.8,
                    pre_consonant_dur_sec=0.035,
                    pre_consonant_type="plosive",
                ),
                SyllableSpec(
                    1.34,
                    0.18,
                    158.0,
                    140.0,
                    VOWEL_FORMANTS["u"],
                    amp_db=0.0,
                    pre_consonant_dur_sec=0.075,
                    pre_consonant_type="cluster",
                ),
                SyllableSpec(
                    1.72,
                    0.21,
                    166.0,
                    114.0,
                    VOWEL_FORMANTS["o"],
                    amp_db=0.8,
                    pre_consonant_dur_sec=0.090,
                    pre_consonant_type="cluster",
                ),
            ],
            distractor_bursts=[
                UnvoicedBurstSpec(0.05, 0.06, "plosive", amp_scale=1.10),
                UnvoicedBurstSpec(0.97, 0.05, "plosive", amp_scale=1.05),
                UnvoicedBurstSpec(1.55, 0.06, "sibilant", amp_scale=1.15),
                UnvoicedBurstSpec(1.98, 0.08, "sibilant", amp_scale=1.20),
            ],
            seed=106,
        )
    )

    # 7. Fast speech at 6.5 syllables/sec (8 syllables over 1.23s active speech)
    items.append(
        _render_synthetic_item(
            item_id="synth_fast_speech_8syll",
            description="Fast speech (6.5 syll/s): 8 rapid syllables over 1.23s with 65-90ms vowels",
            total_dur_sec=1.45,
            syllables=[
                SyllableSpec(0.12, 0.080, 150.0, 145.0, VOWEL_FORMANTS["a"], amp_db=0.0),
                SyllableSpec(0.26, 0.065, 130.0, 128.0, VOWEL_FORMANTS["i"], amp_db=-4.5),
                SyllableSpec(0.39, 0.085, 158.0, 150.0, VOWEL_FORMANTS["e"], amp_db=0.2),
                SyllableSpec(0.54, 0.065, 128.0, 125.0, VOWEL_FORMANTS["u"], amp_db=-5.0),
                SyllableSpec(0.67, 0.090, 164.0, 152.0, VOWEL_FORMANTS["a"], amp_db=0.5),
                SyllableSpec(0.83, 0.065, 126.0, 122.0, VOWEL_FORMANTS["i"], amp_db=-4.8),
                SyllableSpec(0.96, 0.085, 155.0, 142.0, VOWEL_FORMANTS["o"], amp_db=0.0),
                SyllableSpec(1.12, 0.110, 160.0, 118.0, VOWEL_FORMANTS["e"], amp_db=0.4),
            ],
            seed=107,
        )
    )

    # 8. Slow speech at 2.2 syllables/sec (5 syllables over 2.27s active speech)
    items.append(
        _render_synthetic_item(
            item_id="synth_slow_speech_5syll",
            description="Slow speech (2.2 syll/s): 5 deliberate syllables over 2.27s with 220-260ms vowels",
            total_dur_sec=2.55,
            syllables=[
                SyllableSpec(
                    0.18,
                    0.23,
                    150.0,
                    140.0,
                    VOWEL_FORMANTS["a"],
                    amp_db=0.0,
                    pre_consonant_dur_sec=0.04,
                    pre_consonant_type="plosive",
                ),
                SyllableSpec(
                    0.64,
                    0.22,
                    145.0,
                    135.0,
                    VOWEL_FORMANTS["i"],
                    amp_db=-1.5,
                    pre_consonant_dur_sec=0.04,
                    pre_consonant_type="plosive",
                ),
                SyllableSpec(
                    1.10,
                    0.25,
                    162.0,
                    146.0,
                    VOWEL_FORMANTS["o"],
                    amp_db=0.5,
                    pre_consonant_dur_sec=0.05,
                    pre_consonant_type="plosive",
                ),
                SyllableSpec(
                    1.58,
                    0.22,
                    142.0,
                    132.0,
                    VOWEL_FORMANTS["e"],
                    amp_db=-1.0,
                    pre_consonant_dur_sec=0.04,
                    pre_consonant_type="plosive",
                ),
                SyllableSpec(
                    2.04,
                    0.26,
                    165.0,
                    112.0,
                    VOWEL_FORMANTS["u"],
                    amp_db=0.8,
                    pre_consonant_dur_sec=0.05,
                    pre_consonant_type="plosive",
                ),
            ],
            seed=108,
        )
    )

    # 9. Dysfluent prolonged vowel (440ms single vowel with 4.5 Hz amplitude vibrato/tremor)
    items.append(
        _render_synthetic_item(
            item_id="synth_prolonged_vibrato_3syll",
            description="Dysfluent prolonged vowel: 3 syllables with two 440ms prolonged vowels having 4.5Hz amplitude tremor",
            total_dur_sec=1.75,
            syllables=[
                SyllableSpec(
                    0.14,
                    0.44,
                    148.0,
                    144.0,
                    VOWEL_FORMANTS["e"],
                    amp_db=0.0,
                    vibrato_hz=4.5,
                    vibrato_depth_db=3.2,
                    is_prolonged=True,
                ),
                SyllableSpec(
                    0.70,
                    0.44,
                    155.0,
                    148.0,
                    VOWEL_FORMANTS["a"],
                    amp_db=0.5,
                    pre_consonant_dur_sec=0.04,
                    pre_consonant_type="plosive",
                    vibrato_hz=4.5,
                    vibrato_depth_db=3.2,
                    is_prolonged=True,
                ),
                SyllableSpec(
                    1.28,
                    0.21,
                    160.0,
                    115.0,
                    VOWEL_FORMANTS["o"],
                    amp_db=0.2,
                    pre_consonant_dur_sec=0.04,
                    pre_consonant_type="plosive",
                ),
            ],
            seed=109,
        )
    )

    # 10. Hesitation pause block (480ms silent block) + prolonged vowel ("theeee...") + rapid rush
    items.append(
        _render_synthetic_item(
            item_id="synth_hesitation_block_6syll",
            description="6 syllables with 440ms prolonged hesitation vowel + 480ms mid-phrase block + rapid 4-syllable recovery",
            total_dur_sec=2.35,
            syllables=[
                SyllableSpec(0.14, 0.16, 152.0, 145.0, VOWEL_FORMANTS["i"], amp_db=0.0),
                SyllableSpec(
                    0.38,
                    0.44,
                    138.0,
                    134.0,
                    VOWEL_FORMANTS["schwa"],
                    amp_db=-1.0,
                    vibrato_hz=4.5,
                    vibrato_depth_db=3.1,
                    is_prolonged=True,
                ),
                # 480ms silent hesitation block between 0.82s and 1.30s
                SyllableSpec(
                    1.30,
                    0.15,
                    165.0,
                    152.0,
                    VOWEL_FORMANTS["a"],
                    amp_db=0.6,
                    pre_consonant_dur_sec=0.05,
                    pre_consonant_type="plosive",
                ),
                SyllableSpec(1.52, 0.06, 128.0, 124.0, VOWEL_FORMANTS["schwa"], amp_db=-5.5),
                SyllableSpec(
                    1.65,
                    0.16,
                    158.0,
                    142.0,
                    VOWEL_FORMANTS["e"],
                    amp_db=0.2,
                    pre_consonant_dur_sec=0.035,
                    pre_consonant_type="plosive",
                ),
                SyllableSpec(
                    1.89,
                    0.22,
                    164.0,
                    114.0,
                    VOWEL_FORMANTS["o"],
                    amp_db=0.8,
                    pre_consonant_dur_sec=0.04,
                    pre_consonant_type="plosive",
                ),
            ],
            seed=110,
        )
    )

    return items


def build_real_corpus() -> list[BenchmarkItem]:
    """Construct the 5-item Real Recorded Speech Corpus from freeman.wav and 4 sentence slices."""
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    freeman_path = PROJECT_ROOT / "omnivoice-tts" / "examples" / "freeman.wav"
    snd = parselmouth.Sound(str(freeman_path))

    slices_meta = [
        (
            "freeman_s1",
            "freeman_s1.wav",
            0.0,
            6.00,
            19,
            19,
            "Freeman S1: 'If you go into different cultures, they have different concepts of creation.'",
            [
                0.16,
                0.35,
                0.61,
                0.83,
                1.25,
                1.43,
                1.72,
                2.04,
                2.45,
                2.85,
                3.41,
                3.58,
                4.36,
                4.64,
                5.08,
                5.49,
                5.63,
                5.84,
                5.95,
            ],
        ),
        (
            "freeman_s2",
            "freeman_s2.wav",
            6.00,
            11.75,
            16,
            16,
            "Freeman S2: 'They have their own creation story and what an afterlife is.'",
            [
                0.12,
                0.25,
                0.45,
                0.98,
                1.21,
                1.63,
                1.76,
                2.24,
                2.50,
                2.97,
                3.29,
                3.65,
                3.93,
                4.09,
                4.42,
                4.90,
            ],
        ),
        (
            "freeman_s3",
            "freeman_s3.wav",
            11.75,
            16.10,
            13,
            13,
            "Freeman S3: 'Where you go, what you do, who you're going to be with.'",
            [0.24, 0.73, 0.93, 1.10, 1.46, 1.63, 1.82, 2.59, 2.84, 2.94, 3.09, 3.38, 3.86],
        ),
        (
            "freeman_s4",
            "freeman_s4.wav",
            16.10,
            float(snd.total_duration),
            4,
            4,
            "Freeman S4: 'People say, well...'",
            [0.27, 0.47, 0.65, 0.85],
        ),
    ]

    items: list[BenchmarkItem] = [
        BenchmarkItem(
            item_id="freeman_full",
            category="real",
            description="Full freeman.wav recording (17.26s, 52 syllables)",
            audio_path=str(freeman_path),
            duration_sec=round(float(snd.total_duration), 4),
            gt_count=52,
            canonical_count=52,
        )
    ]

    for item_id, fname, t0, t1, gt_cnt, can_cnt, desc, gt_nuc in slices_meta:
        out_wav = FIXTURES_DIR / fname
        if not out_wav.is_file():
            part = snd.extract_part(t0, t1, preserve_times=False)
            part.save(str(out_wav), "WAV")
        items.append(
            BenchmarkItem(
                item_id=item_id,
                category="real",
                description=desc,
                audio_path=str(out_wav),
                duration_sec=round(t1 - t0, 4),
                gt_count=gt_cnt,
                canonical_count=can_cnt,
                gt_nuclei_times=gt_nuc,
            )
        )
    return items


def build_tts_corpus() -> list[BenchmarkItem]:
    """Construct the 6-item OmniVoice TTS Synthesized Corpus (cached in fixtures/)."""
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    tts_bin = PROJECT_ROOT / "omnivoice-tts" / "build" / "omnivoice-tts"
    model_gguf = PROJECT_ROOT / "omnivoice-tts" / "models" / "omnivoice-base-Q8_0.gguf"
    codec_gguf = PROJECT_ROOT / "omnivoice-tts" / "models" / "omnivoice-tokenizer-F32.gguf"

    tts_specs = [
        (
            "tts_phrase_1",
            "tts_phrase_1.wav",
            "We need to arrow in on the core problem.",
            11,
            11,
            [0.32, 0.40, 0.54, 0.71, 0.83, 1.04, 1.35, 1.45, 1.70, 1.93, 2.10],
        ),
        (
            "tts_phrase_2",
            "tts_phrase_2.wav",
            "Actually I think there is a better way.",
            9,
            11,
            [0.24, 0.51, 0.63, 0.79, 1.06, 1.20, 1.32, 1.42, 1.62],
        ),
        (
            "tts_phrase_3",
            "tts_phrase_3.wav",
            "I said fifteen percent, not fifty.",
            9,
            9,
            [0.32, 0.46, 0.67, 0.86, 1.03, 1.23, 1.41, 1.65, 1.83],
        ),
        (
            "tts_phrase_4",
            "tts_phrase_4.wav",
            "And then the whole room went completely silent.",
            11,
            11,
            [0.26, 0.43, 0.64, 0.81, 0.93, 1.07, 1.29, 1.48, 1.72, 1.88, 2.09],
        ),
        (
            "tts_phrase_5",
            "tts_phrase_5.wav",
            "Speak clearly right now.",
            5,
            5,
            [0.46, 0.95, 1.05, 1.21, 1.47],
        ),
        (
            "tts_phrase_6",
            "tts_phrase_6.wav",
            "We all need to understand how this modern system works.",
            14,
            14,
            [0.40, 0.60, 0.77, 0.84, 0.94, 1.12, 1.35, 1.51, 1.67, 2.01, 2.21, 2.53, 2.71, 2.91],
        ),
    ]

    items: list[BenchmarkItem] = []
    for item_id, fname, text, gt_cnt, can_cnt, gt_nuc in tts_specs:
        wav_path = FIXTURES_DIR / fname
        if not wav_path.is_file() and tts_bin.is_file():
            subprocess.run(
                [
                    str(tts_bin),
                    "--model",
                    str(model_gguf),
                    "--codec",
                    str(codec_gguf),
                    "--instruct",
                    "male, young adult, moderate pitch",
                    "--lang",
                    "English",
                    "--seed",
                    "42",
                    "-o",
                    str(wav_path),
                ],
                input=text,
                text=True,
                capture_output=True,
                check=True,
            )
        snd = parselmouth.Sound(str(wav_path))
        items.append(
            BenchmarkItem(
                item_id=item_id,
                category="tts",
                description=f"OmniVoice TTS: '{text}' ({gt_cnt} phonetic / {can_cnt} canonical syll)",
                audio_path=str(wav_path),
                duration_sec=round(float(snd.total_duration), 4),
                gt_count=gt_cnt,
                canonical_count=can_cnt,
                gt_nuclei_times=gt_nuc,
            )
        )
    return items


def _match_timestamps(
    gt_times: list[float],
    pred_times: list[float],
    tolerance_sec: float = 0.050,
) -> tuple[list[tuple[int, int]], int, int]:
    """Greedy closest-first 1-to-1 matching within tolerance_sec.

    Returns:
        (matched_index_pairs, false_positives, false_negatives)
    """
    if not gt_times or not pred_times:
        return [], len(pred_times), len(gt_times)

    candidates: list[tuple[float, int, int]] = []
    for g_idx, g_t in enumerate(gt_times):
        for p_idx, p_t in enumerate(pred_times):
            diff = abs(g_t - p_t)
            if diff <= tolerance_sec:
                candidates.append((diff, g_idx, p_idx))
    candidates.sort(key=lambda x: x[0])

    used_g: set[int] = set()
    used_p: set[int] = set()
    matches: list[tuple[int, int]] = []
    for _, g_idx, p_idx in candidates:
        if g_idx not in used_g and p_idx not in used_p:
            used_g.add(g_idx)
            used_p.add(p_idx)
            matches.append((g_idx, p_idx))

    matches.sort(key=lambda x: x[0])
    fp = len(pred_times) - len(matches)
    fn = len(gt_times) - len(matches)
    return matches, fp, fn


def evaluate_all() -> dict[str, Any]:
    """Run all 6 detectors across the 21-item benchmark suite and compute summary metrics."""
    corpus = build_synthetic_corpus() + build_real_corpus() + build_tts_corpus()

    # Warm up R4 singleton once before timing so cold weight load is excluded from per-clip runtime
    if "r4_articulatory_sonority" in ALGORITHMS:
        _ = ALGORITHMS["r4_articulatory_sonority"](corpus[0].audio_path)

    per_algorithm_summary: dict[str, dict[str, Any]] = {}
    per_item_results: dict[str, dict[str, Any]] = {
        item.item_id: {
            "meta": asdict(item),
            "detectors": {},
        }
        for item in corpus
    }

    for alg_name, detector_fn in ALGORITHMS.items():
        abs_errors_all: list[int] = []
        abs_errors_synth: list[int] = []
        abs_errors_real: list[int] = []
        abs_errors_tts: list[int] = []
        exact_matches = 0
        within1_matches = 0

        total_tp = 0
        total_fp = 0
        total_fn = 0

        p_center_errors_ms: list[float] = []
        c_onset_errors_ms: list[float] = []

        sibilant_total = 0
        sibilant_false_positives = 0

        prolonged_total = 0
        prolonged_double_counts = 0

        total_runtime_ms = 0.0
        total_audio_sec = 0.0

        for item in corpus:
            res: SyllableDetectionResult = detector_fn(item.audio_path)
            pred_count = len(res.nuclei_times)
            err = abs(pred_count - item.gt_count)

            abs_errors_all.append(err)
            if item.category == "synthetic":
                abs_errors_synth.append(err)
            elif item.category == "real":
                abs_errors_real.append(err)
            elif item.category == "tts":
                abs_errors_tts.append(err)

            if err == 0:
                exact_matches += 1
            if err <= 1:
                within1_matches += 1

            total_runtime_ms += res.runtime_ms
            total_audio_sec += item.duration_sec

            # Nucleus detection P/R/F1 within +-50ms on items with ground-truth timestamps
            if item.gt_nuclei_times:
                # Use +-50ms tolerance on synthetic items, +-65ms on real/TTS items
                tol = 0.050 if item.category == "synthetic" else 0.065
                matches, fp, fn = _match_timestamps(
                    item.gt_nuclei_times, res.nuclei_times, tolerance_sec=tol
                )
                total_tp += len(matches)
                total_fp += fp
                total_fn += fn

                if item.gt_p_center_times and len(res.p_center_times) == len(res.nuclei_times):
                    for g_idx, p_idx in matches:
                        p_err_ms = (
                            abs(item.gt_p_center_times[g_idx] - res.p_center_times[p_idx]) * 1000.0
                        )
                        p_center_errors_ms.append(p_err_ms)

                if item.gt_consonant_onset_times and len(res.consonant_onset_times) == len(
                    res.nuclei_times
                ):
                    for g_idx, p_idx in matches:
                        c_err_ms = (
                            abs(
                                item.gt_consonant_onset_times[g_idx]
                                - res.consonant_onset_times[p_idx]
                            )
                            * 1000.0
                        )
                        c_onset_errors_ms.append(c_err_ms)

            # Check false positives on unvoiced sibilant/plosive bursts
            for b_time in item.unvoiced_burst_times:
                sibilant_total += 1
                if any(abs(nuc_t - b_time) <= 0.045 for nuc_t in res.nuclei_times):
                    sibilant_false_positives += 1

            # Check double-counting on prolonged vowels with vibrato/tremor
            for span_start, span_end in item.prolonged_vowel_spans:
                prolonged_total += 1
                inside = [
                    nuc_t
                    for nuc_t in res.nuclei_times
                    if (span_start - 0.02) <= nuc_t <= (span_end + 0.02)
                ]
                if len(inside) >= 2:
                    prolonged_double_counts += 1

            per_item_results[item.item_id]["detectors"][alg_name] = {
                "pred_count": pred_count,
                "gt_count": item.gt_count,
                "count_error": pred_count - item.gt_count,
                "nuclei_times": res.nuclei_times,
                "p_center_times": res.p_center_times,
                "consonant_onset_times": res.consonant_onset_times,
                "vowel_durations": res.vowel_durations,
                "prominences": res.prominences,
                "pause_spans": res.pause_spans,
                "runtime_ms": res.runtime_ms,
            }

        precision = total_tp / max(1, total_tp + total_fp)
        recall = total_tp / max(1, total_tp + total_fn)
        f1 = 2.0 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

        per_algorithm_summary[alg_name] = {
            "count_mae_all": round(float(np.mean(abs_errors_all)), 3),
            "count_mae_synthetic": round(float(np.mean(abs_errors_synth)), 3),
            "count_mae_real": round(float(np.mean(abs_errors_real)), 3),
            "count_mae_tts": round(float(np.mean(abs_errors_tts)), 3),
            "exact_match_pct": round(100.0 * exact_matches / len(corpus), 1),
            "within1_match_pct": round(100.0 * within1_matches / len(corpus), 1),
            "nucleus_precision": round(100.0 * precision, 1),
            "nucleus_recall": round(100.0 * recall, 1),
            "nucleus_f1": round(100.0 * f1, 1),
            "p_center_mae_ms": round(float(np.mean(p_center_errors_ms)), 2)
            if p_center_errors_ms
            else None,
            "c_onset_mae_ms": round(float(np.mean(c_onset_errors_ms)), 2)
            if c_onset_errors_ms
            else None,
            "sibilant_fp_rate_pct": round(
                100.0 * sibilant_false_positives / max(1, sibilant_total), 1
            ),
            "prolonged_vowel_fp_rate_pct": round(
                100.0 * prolonged_double_counts / max(1, prolonged_total), 1
            ),
            "combined_distractor_fp_rate_pct": round(
                100.0
                * (sibilant_false_positives + prolonged_double_counts)
                / max(1, sibilant_total + prolonged_total),
                1,
            ),
            "mean_runtime_ms_per_sec_audio": round(
                total_runtime_ms / max(1e-6, total_audio_sec), 2
            ),
            "mean_runtime_ms_per_clip": round(total_runtime_ms / len(corpus), 2),
        }

    results_payload = {
        "corpus_size": len(corpus),
        "summary": per_algorithm_summary,
        "items": per_item_results,
    }

    results_path = EXPERIMENTS_DIR / "results.json"
    results_path.write_text(json.dumps(results_payload, indent=2), encoding="utf-8")
    return results_payload


def main() -> None:
    """Run benchmark and print comparative summary table."""
    payload = evaluate_all()
    summary = payload["summary"]
    print(f"Benchmark completed across {payload['corpus_size']} audio items.\n")
    header = (
        f"{'Algorithm':28s} | {'MAE(All)':8s} | {'Exact%':6s} | {'<=1%':6s} | "
        f"{'P%':5s} | {'R%':5s} | {'F1%':5s} | {'P-Ctr MAE':9s} | "
        f"{'SibFP%':6s} | {'ProlFP%':7s} | {'ms/s':6s}"
    )
    print(header)
    print("-" * len(header))
    for alg, m in summary.items():
        print(
            f"{alg:28s} | {m['count_mae_all']:8.2f} | {m['exact_match_pct']:5.1f}% | "
            f"{m['within1_match_pct']:5.1f}% | {m['nucleus_precision']:5.1f} | "
            f"{m['nucleus_recall']:5.1f} | {m['nucleus_f1']:5.1f} | "
            f"{m['p_center_mae_ms']:7.1f}ms | {m['sibilant_fp_rate_pct']:5.1f}% | "
            f"{m['prolonged_vowel_fp_rate_pct']:6.1f}% | {m['mean_runtime_ms_per_sec_audio']:6.2f}"
        )


if __name__ == "__main__":
    main()
