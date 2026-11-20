"""Tests for Praat-referenced CPPS computation in ``src/audio/processor.py``."""

from __future__ import annotations

import math
from collections.abc import Callable
from pathlib import Path

import numpy as np
import parselmouth
import pytest
from numpy.typing import NDArray

from src.audio.processor import AudioContext, ProsodyAnalyzer

PRAAT_CPPS_SCRIPT = (
    Path(__file__).resolve().parent / "fixtures" / "praat" / "cpps_maryn_weenink_2015.praat"
)


def _praat_reference_cpps(sound: parselmouth.Sound) -> float:
    """Compute reference CPPS (dB) via versioned Praat script."""
    _, output = parselmouth.praat.run_file(sound, str(PRAAT_CPPS_SCRIPT), capture_output=True)
    return float(output.strip())


def _harmonic_complex(
    sample_rate: int = 16000,
    duration: float = 1.0,
    f0_hz: float = 200.0,
    num_harmonics: int = 14,
    peak: float = 0.5,
) -> NDArray[np.float64]:
    """Generate deterministic harmonic complex peaking at ``peak``."""
    times = np.arange(int(sample_rate * duration)) / sample_rate
    signal_sum = np.zeros_like(times, dtype=np.float64)
    for k in range(1, num_harmonics + 1):
        signal_sum += np.sin(2.0 * np.pi * f0_hz * k * times) / k
    max_abs = float(np.max(np.abs(signal_sum)))
    if max_abs > 0.0:
        signal_sum = signal_sum / max_abs * peak
    return signal_sum


def _white_noise(
    sample_rate: int = 16000,
    duration: float = 1.0,
    peak: float = 0.5,
    seed: int = 12345,
) -> NDArray[np.float64]:
    """Generate deterministic white noise peaking at ``peak``."""
    rng = np.random.default_rng(seed)
    noise = rng.normal(0.0, 1.0, int(sample_rate * duration))
    max_abs = float(np.max(np.abs(noise)))
    if max_abs > 0.0:
        noise = noise / max_abs * peak
    return np.asarray(noise, dtype=np.float64)


def _jittered_harmonic(
    sample_rate: int = 16000,
    duration: float = 1.0,
    f0_hz: float = 200.0,
    jitter_std: float = 0.08,
    num_harmonics: int = 14,
    peak: float = 0.5,
    seed: int = 12345,
) -> NDArray[np.float64]:
    """Generate deterministic cycle-by-cycle F0-jittered harmonic waveform."""
    rng = np.random.default_rng(seed)
    n_samples = int(sample_rate * duration)
    phases = np.empty(n_samples, dtype=np.float64)
    phase = 0.0
    cycle_f0 = f0_hz
    for i in range(n_samples):
        phases[i] = phase
        phase += 2.0 * np.pi * cycle_f0 / sample_rate
        if phase >= 2.0 * np.pi:
            phase -= 2.0 * np.pi
            cycle_f0 = max(60.0, f0_hz * (1.0 + float(rng.normal(0.0, jitter_std))))
    waveform = np.zeros(n_samples, dtype=np.float64)
    for k in range(1, num_harmonics + 1):
        waveform += np.sin(k * phases) / k
    max_abs = float(np.max(np.abs(waveform)))
    if max_abs > 0.0:
        waveform = waveform / max_abs * peak
    return waveform


def _cpps_from_wav(
    dummy_wav_factory: Callable[..., Path],
    waveform: NDArray[np.float64],
    sample_rate: int = 16000,
) -> tuple[float, float]:
    """Analyze WAV via ProsodyAnalyzer and compare with Praat reference script."""
    wav_path = dummy_wav_factory(sample_rate=sample_rate, waveform=waveform)
    context = AudioContext(str(wav_path))
    vq = ProsodyAnalyzer(context).analyze_voice_quality()
    ref_cpps = _praat_reference_cpps(context.praat_sound)
    return vq.cpps, ref_cpps


def test_cpps_harmonic_complex_nonzero_and_matches_praat_script(
    dummy_wav_factory: Callable[..., Path],
) -> None:
    """1s 200 Hz harmonic complex at 16 kHz must match Praat CPPS instead of returning 0.0."""
    harm = _harmonic_complex(sample_rate=16000, duration=1.0, f0_hz=200.0)
    cpps, ref_cpps = _cpps_from_wav(dummy_wav_factory, harm, sample_rate=16000)

    assert cpps > 20.0
    assert cpps == pytest.approx(ref_cpps, abs=1e-6)


def test_cpps_orders_periodic_jittered_mixed_and_noisy_signals(
    dummy_wav_factory: Callable[..., Path],
) -> None:
    """Periodic harmonics must exceed jittered, mixed, and noisy signals monotonically."""
    sr = 16000
    harm = _harmonic_complex(sample_rate=sr, duration=1.0, f0_hz=200.0)
    noise = _white_noise(sample_rate=sr, duration=1.0, seed=12345)
    jittered = _jittered_harmonic(sample_rate=sr, duration=1.0, f0_hz=200.0, seed=12345)
    voiced_unvoiced = np.concatenate([harm[: sr // 2], noise[: sr // 2]])

    signals = {
        "clean": harm,
        "snr20": harm + 0.1 * noise,
        "snr10": harm + 0.316 * noise,
        "snr0": harm + 1.0 * noise,
        "jittered": jittered,
        "voiced_unvoiced": voiced_unvoiced,
        "white_noise": noise,
    }
    results: dict[str, float] = {}
    for name, sig in signals.items():
        cpps, ref_cpps = _cpps_from_wav(dummy_wav_factory, sig, sample_rate=sr)
        assert cpps == pytest.approx(ref_cpps, abs=1e-6), f"Mismatch for {name}"
        results[name] = cpps

    assert (
        results["clean"]
        > results["snr20"]
        > results["snr10"]
        > results["snr0"]
        > results["white_noise"]
    )
    assert results["clean"] > results["jittered"] > results["white_noise"]
    assert results["clean"] > results["voiced_unvoiced"] > results["white_noise"]


def test_cpps_amplitude_invariance_am_and_clipping(
    dummy_wav_factory: Callable[..., Path],
) -> None:
    """CPPS should remain gain-invariant and match Praat for AM and clipped waveforms."""
    sr = 16000
    times = np.arange(sr) / sr
    harm = _harmonic_complex(sample_rate=sr, duration=1.0, f0_hz=200.0, peak=0.5)

    wav_01, _ = _cpps_from_wav(dummy_wav_factory, 0.2 * harm, sample_rate=sr)
    wav_05, _ = _cpps_from_wav(dummy_wav_factory, harm, sample_rate=sr)
    wav_10, _ = _cpps_from_wav(dummy_wav_factory, 2.0 * harm, sample_rate=sr)
    assert wav_01 == pytest.approx(wav_05, abs=1.0)
    assert wav_10 == pytest.approx(wav_05, abs=1.0)

    dummy_context = AudioContext(str(dummy_wav_factory(sample_rate=sr, waveform=harm)))
    analyzer = ProsodyAnalyzer(dummy_context)
    low_sound = parselmouth.Sound(0.01 * harm, sampling_frequency=sr)
    high_sound = parselmouth.Sound(harm, sampling_frequency=sr)
    assert analyzer._compute_cpps(low_sound) == pytest.approx(
        analyzer._compute_cpps(high_sound), abs=1e-4
    )

    am_harm = harm * (0.7 + 0.3 * np.sin(2.0 * np.pi * 8.0 * times))
    am_cpps, am_ref = _cpps_from_wav(dummy_wav_factory, am_harm, sample_rate=sr)
    assert math.isfinite(am_cpps) and am_cpps > 20.0
    assert am_cpps == pytest.approx(am_ref, abs=1e-6)

    clipped = np.clip(harm * 4.0, -1.0, 1.0)
    clip_cpps, clip_ref = _cpps_from_wav(dummy_wav_factory, clipped, sample_rate=sr)
    assert math.isfinite(clip_cpps) and clip_cpps > 20.0
    assert clip_cpps == pytest.approx(clip_ref, abs=1e-6)


@pytest.mark.parametrize("sample_rate", [8000, 16000, 22050, 44100, 48000])
def test_cpps_consistent_across_speech_sample_rates(
    dummy_wav_factory: Callable[..., Path],
    sample_rate: int,
) -> None:
    """CPPS should stay consistent across speech sample rates and match Praat."""
    harm = _harmonic_complex(sample_rate=sample_rate, duration=1.0, f0_hz=200.0)
    cpps, ref_cpps = _cpps_from_wav(dummy_wav_factory, harm, sample_rate=sample_rate)

    assert cpps > 20.0
    assert cpps == pytest.approx(ref_cpps, abs=1e-6)

    ref_16k_harm = _harmonic_complex(sample_rate=16000, duration=1.0, f0_hz=200.0)
    cpps_16k, _ = _cpps_from_wav(dummy_wav_factory, ref_16k_harm, sample_rate=16000)
    assert abs(cpps - cpps_16k) < 5.5


def test_cpps_stereo_matches_mono_reference_script(
    dummy_wav_factory: Callable[..., Path],
) -> None:
    """Multi-channel audio must match the mono-converting Praat reference script."""
    harm = _harmonic_complex(sample_rate=16000, duration=1.0, f0_hz=200.0)
    stereo = np.column_stack([harm, harm * 0.5])
    cpps, ref_cpps = _cpps_from_wav(dummy_wav_factory, stereo, sample_rate=16000)

    assert cpps > 20.0
    assert cpps == pytest.approx(ref_cpps, abs=1e-6)


def test_cpps_edge_cases_return_zero(dummy_wav_factory: Callable[..., Path]) -> None:
    """Silence, DC offset, ultra-short clips, and NaN waveforms should safely return 0.0."""
    sr = 16000

    silence_wav = dummy_wav_factory(sample_rate=sr, waveform=np.zeros(sr, dtype=np.float64))
    assert ProsodyAnalyzer(AudioContext(str(silence_wav))).analyze_voice_quality().cpps == 0.0

    dc_wav = dummy_wav_factory(sample_rate=sr, waveform=np.full(sr, 0.5, dtype=np.float64))
    assert ProsodyAnalyzer(AudioContext(str(dc_wav))).analyze_voice_quality().cpps == 0.0

    short_wav = dummy_wav_factory(
        sample_rate=sr,
        waveform=np.sin(2.0 * np.pi * 200.0 * np.arange(10) / sr),
    )
    analyzer = ProsodyAnalyzer(AudioContext(str(short_wav)))
    assert analyzer._compute_cpps(analyzer.audio) == 0.0

    nan_waveform = _harmonic_complex(sample_rate=sr, duration=1.0, f0_hz=200.0)
    nan_waveform[100] = np.nan
    nan_sound = parselmouth.Sound(nan_waveform, sampling_frequency=sr)
    assert analyzer._compute_cpps(nan_sound) == 0.0


def test_cpps_real_speech_fixture_matches_praat_script() -> None:
    """Real speech E2E WAV fixture should produce finite CPPS matching Praat script."""
    fixture_path = Path(__file__).resolve().parent / "e2e" / "fixtures" / "test-audio.wav"
    assert fixture_path.is_file()
    context = AudioContext(str(fixture_path))
    vq = ProsodyAnalyzer(context).analyze_voice_quality()
    ref_cpps = _praat_reference_cpps(context.praat_sound)

    assert vq.cpps > 5.0
    assert vq.cpps == pytest.approx(ref_cpps, abs=1e-6)
