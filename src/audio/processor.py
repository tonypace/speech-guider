"""Audio processing for prosody analysis using Parselmouth.

Implements rhythm (nPVI), stress patterns, pitch extraction,
and voice quality metrics (jitter, shimmer, CPPS, spectral tilt).
"""

import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, cast

import numpy as np
import parselmouth
from parselmouth import Pitch


@dataclass
class PitchContour:
    """Pitch (F0) analysis results."""

    f0_values: list[float]
    f0_range: float
    mean_f0: float
    std_f0: float

    @property
    def range_semitones(self) -> float:
        """Pitch movement is a frequency ratio; unvoiced frames carry no pitch."""
        voiced = [value for value in self.f0_values if math.isfinite(value) and value > 0]
        return 12.0 * math.log2(max(voiced) / min(voiced)) if voiced else 0.0


@dataclass
class RhythmMetrics:
    """Rhythm analysis results using nPVI."""

    npvi: float
    vowel_durations: list[float]
    classification: str  # "syllable-timed" or "stress-timed"


@dataclass
class StressPattern:
    """Stress pattern analysis for primary prominence."""

    primary_stress_word: str
    primary_stress_time: float
    prominence_score: float  # Combined F0 and intensity score


@dataclass
class VoiceQuality:
    """Voice quality metrics.

    Attributes:
        jitter_local: Cycle-to-cycle F0 variation (Perturbation quotient, %)
        shimmer_local: Cycle-to-cycle amplitude variation (dB)
        cpps: Cepstral Peak Prominence Smoothed (dB) - roughness measure
        spectral_tilt: Spectral slope (dB/octave) - breathiness indicator
    """

    jitter_local: float
    shimmer_local: float
    cpps: float
    spectral_tilt: float


@dataclass
class ProsodyMetrics:
    """Complete prosody analysis results."""

    pitch: PitchContour
    rhythm: RhythmMetrics
    stress: Optional[StressPattern]
    voice_quality: VoiceQuality = field(default_factory=lambda: VoiceQuality(0.0, 0.0, 0.0, 0.0))


@dataclass
class WordData:
    """Word-level data for stress analysis."""

    word: str
    start_time: float
    end_time: float
    prominence_score: float


class AudioContext:
    """Centralized audio context for unified analysis.

    Holds both high-fidelity and processed audio to support
    different analysis requirements (ML models vs acoustic analysis).
    """

    def __init__(self, audio_filepath: str, sample_rate: int = 16000) -> None:
        """Initialize audio context with file.

        Args:
            audio_filepath: Path to audio file
            sample_rate: Target sample rate for ML models (default 16kHz)
        """
        self.audio_filepath = Path(audio_filepath)
        self.target_sample_rate = sample_rate

        # Load original high-fidelity audio for acoustic analysis
        try:
            self.praat_sound = parselmouth.Sound(str(self.audio_filepath))
        except Exception as e:
            raise ValueError(f"Failed to load audio file: {e}") from e

        # Get audio metadata
        self.original_sample_rate = int(self.praat_sound.sampling_frequency)
        self.total_duration = self.praat_sound.total_duration

    def get_downsampled_tensor(self) -> np.ndarray:
        """Get downsampled audio as numpy array for ML models.

        Returns:
            Audio waveform as float32 numpy array at target sample rate
        """
        if self.original_sample_rate == self.target_sample_rate:
            samples = self.praat_sound.values[0]
        else:
            samples = self.praat_sound.resample(self.target_sample_rate).values[0]

        return cast(np.ndarray, samples.astype(np.float32))


class ProsodyAnalyzer:
    """Analyzes prosody features: rhythm, stress, and pitch."""

    def __init__(self, audio_context: AudioContext) -> None:
        """Initialize prosody analyzer.

        Args:
            audio_context: AudioContext for the audio to analyze
        """
        self.audio = audio_context.praat_sound

    def analyze_pitch(self, pitch_obj: Optional[Pitch] = None) -> PitchContour:
        """Extract pitch (F0) contour.

        Args:
            pitch_obj: Optional pre-computed Pitch object. If None, computed here.
                Allows reuse when called from analyze_complete().

        Returns:
            PitchContour with F0 values and statistics
        """
        if pitch_obj is None:
            pitch_obj = self.audio.to_pitch()
        f0_values = pitch_obj.selected_array["frequency"]

        # Filter out unvoiced segments (F0 == 0)
        voiced_f0 = f0_values[f0_values > 0]

        if len(voiced_f0) == 0:
            return PitchContour(
                f0_values=f0_values.tolist(),
                f0_range=0.0,
                mean_f0=0.0,
                std_f0=0.0,
            )

        f0_range = np.max(voiced_f0) - np.min(voiced_f0)
        mean_f0 = np.mean(voiced_f0)
        std_f0 = np.std(voiced_f0)

        return PitchContour(
            f0_values=f0_values.tolist(),
            f0_range=float(f0_range),
            mean_f0=float(mean_f0),
            std_f0=float(std_f0),
        )

    def analyze_rhythm(self, vowel_timestamps: list[tuple[float, float]]) -> RhythmMetrics:
        """Calculate rhythm using nPVI (normalized Pairwise Variability Index).

        Args:
            vowel_timestamps: List of (start_time, end_time) for each vowel

        Returns:
            RhythmMetrics with nPVI score and classification
        """
        if not vowel_timestamps or len(vowel_timestamps) < 2:
            return RhythmMetrics(
                npvi=0.0,
                vowel_durations=[],
                classification="insufficient_data",
            )

        vowel_durations = [end - start for start, end in vowel_timestamps]

        num_vowels = len(vowel_durations)
        durations = np.array(vowel_durations)

        differences = np.abs(durations[:-1] - durations[1:])
        means = (durations[:-1] + durations[1:]) / 2

        npvi = 100 * np.sum(differences / means) / (num_vowels - 1)

        classification = "stress-timed" if npvi > 40 else "syllable-timed"

        return RhythmMetrics(
            npvi=float(npvi),
            vowel_durations=vowel_durations,
            classification=classification,
        )

    def _compute_jitter_and_shimmer(self, sound: parselmouth.Sound) -> tuple[float, float]:
        """Compute jitter (F0 period variation) and shimmer (amplitude variation)."""
        pitch_obj = sound.to_pitch()
        f0 = pitch_obj.selected_array["frequency"]
        voiced_mask = f0 > 0
        n_voiced = int(np.sum(voiced_mask))
        if n_voiced < 3:
            return (0.0, 0.0)

        periods = np.where(voiced_mask, 1.0 / np.maximum(f0, 1e-6), 0.0)
        voiced_periods = periods[voiced_mask]
        jitter = (
            float(np.mean(np.abs(np.diff(voiced_periods))) / np.mean(voiced_periods) * 100)
            if len(voiced_periods) > 2
            else 0.0
        )

        intensity_obj = sound.to_intensity()
        intensity = intensity_obj.values.flatten()
        n_pitch = len(f0)
        shimmer = 0.0
        if len(intensity) > 1 and n_pitch > 1:
            idx = np.clip(
                np.linspace(0, len(intensity) - 1, n_pitch).astype(int), 0, len(intensity) - 1
            )
            voiced_int = intensity[idx][voiced_mask]
            if len(voiced_int) > 2:
                shimmer = float(np.mean(np.abs(np.diff(voiced_int))) / np.mean(voiced_int) * 100)
        return (jitter, shimmer)

    def _compute_cpps(self, sound: parselmouth.Sound) -> float:
        """Compute Cepstral Peak Prominence Smoothed (roughness measure)."""
        try:
            samples = sound.values.flatten()
            sr = int(sound.sampling_frequency)
            fl = int(0.03 * sr)
            hl = int(0.01 * sr)
            peaks = []
            for start in range(0, len(samples) - fl, hl):
                frame = samples[start : start + fl] * np.hanning(fl)
                cepstrum_mag = np.abs(np.fft.rfft(np.log(np.abs(np.fft.rfft(frame)) + 1e-10)))
                quef = np.fft.rfftfreq(fl, d=1.0 / sr)
                lo, hi = (
                    max(1, int(np.searchsorted(quef, 1.0 / 500.0))),
                    min(len(cepstrum_mag), int(np.searchsorted(quef, 1.0 / 60.0))),
                )
                if lo >= hi:
                    continue
                pk = int(np.argmax(cepstrum_mag[lo:hi])) + lo
                c = np.arange(len(cepstrum_mag), dtype=float)
                baseline = np.polyval(np.polyfit(c, cepstrum_mag, 1), c[pk])
                peaks.append(float(cepstrum_mag[pk] - baseline))
            return float(np.mean(peaks)) if peaks else 0.0
        except Exception:
            return 0.0

    def _compute_spectral_tilt(self, sound: parselmouth.Sound) -> float:
        """Compute spectral slope (breathiness indicator)."""
        try:
            samples = sound.values.flatten()
            sr = int(sound.sampling_frequency)
            spectrum = np.abs(np.fft.rfft(samples))
            freqs = np.fft.rfftfreq(len(samples), d=1.0 / sr)
            lo, hi = np.searchsorted(freqs, 100), np.searchsorted(freqs, 4000)
            if lo >= hi:
                return 0.0
            log_f = np.log2(freqs[lo:hi] + 1)
            log_m = np.log(spectrum[lo:hi] + 1e-10)
            return float(np.polyfit(log_f, log_m, 1)[0])
        except Exception:
            return 0.0

    def analyze_voice_quality(self) -> VoiceQuality:
        """Compute voice quality metrics using Parselmouth."""
        jitter, shimmer = self._compute_jitter_and_shimmer(self.audio)
        cpps = self._compute_cpps(self.audio)
        tilt = self._compute_spectral_tilt(self.audio)
        return VoiceQuality(
            jitter_local=jitter,
            shimmer_local=shimmer,
            cpps=cpps,
            spectral_tilt=tilt,
        )

    def analyze_stress(
        self,
        word_timestamps: list[tuple[str, float, float]],
        pitch_obj: Optional[Pitch] = None,
    ) -> Optional[StressPattern]:
        """Identify primary stressed word using combined F0 and intensity.

        Computes pitch and intensity once for the full audio, then slices
        by word timestamps to avoid redundant Parselmouth calls.

        Args:
            word_timestamps: List of (word, start_time, end_time)
            pitch_obj: Optional pre-computed Pitch object. If None, computed here.
                Passing in avoids redundant pitch computation when called from
                analyze_complete() which already computes pitch.

        Returns:
            StressPattern with primary stress information
        """
        if not word_timestamps:
            return None

        if pitch_obj is None:
            pitch_obj = self.audio.to_pitch()
        pitch_values = pitch_obj.selected_array["frequency"]
        pitch_dt = pitch_obj.time_step

        intensity_obj = self.audio.to_intensity()
        intensity_values = intensity_obj.values
        intensity_dt = intensity_obj.time_step
        intensity_t0 = intensity_obj.start_time

        words_data: list[WordData] = []

        for word, start_time, end_time in word_timestamps:
            pitch_start = int(start_time / pitch_dt)
            pitch_end = int(end_time / pitch_dt)
            word_pitch = pitch_values[pitch_start:pitch_end]
            voiced_pitch = word_pitch[word_pitch > 0]

            intensity_start = int((start_time - intensity_t0) / intensity_dt)
            intensity_end = int((end_time - intensity_t0) / intensity_dt)
            word_intensity = intensity_values[intensity_start:intensity_end]
            mean_intensity = np.mean(word_intensity) if len(word_intensity) > 0 else 0.0

            if len(voiced_pitch) > 0:
                pitch_excursion = np.max(voiced_pitch) - np.min(voiced_pitch)
            else:
                pitch_excursion = 0.0

            prominence_score = float(pitch_excursion) + float(mean_intensity / 100.0)

            words_data.append(
                WordData(
                    word=word,
                    start_time=start_time,
                    end_time=end_time,
                    prominence_score=prominence_score,
                )
            )

        if not words_data:
            return None

        stressed_word_data = max(words_data, key=lambda x: x.prominence_score)

        return StressPattern(
            primary_stress_word=stressed_word_data.word,
            primary_stress_time=stressed_word_data.start_time,
            prominence_score=stressed_word_data.prominence_score,
        )

    def analyze_complete(
        self,
        vowel_timestamps: list[tuple[float, float]],
        word_timestamps: list[tuple[str, float, float]],
    ) -> ProsodyMetrics:
        """Run complete prosody analysis.

        Computes pitch once and reuses for both pitch extraction and stress analysis.

        Args:
            vowel_timestamps: List of vowel (start_time, end_time)
            word_timestamps: List of word (word, start_time, end_time)

        Returns:
            ProsodyMetrics with complete analysis
        """
        # Compute pitch once and reuse for both analyze_pitch and analyze_stress
        pitch_obj = self.audio.to_pitch()
        pitch = self.analyze_pitch(pitch_obj=pitch_obj)
        rhythm = self.analyze_rhythm(vowel_timestamps)
        stress = self.analyze_stress(word_timestamps, pitch_obj=pitch_obj)
        voice_quality = self.analyze_voice_quality()

        return ProsodyMetrics(
            pitch=pitch,
            rhythm=rhythm,
            stress=stress,
            voice_quality=voice_quality,
        )
