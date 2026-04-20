"""Audio processing for prosody analysis using Parselmouth.

Implements rhythm (nPVI), stress patterns, and pitch extraction.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

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
class ProsodyMetrics:
    """Complete prosody analysis results."""

    pitch: PitchContour
    rhythm: RhythmMetrics
    stress: Optional[StressPattern]


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
            samples = self.praat_sound.values[:, 0]
        else:
            samples = self.praat_sound.resample(self.target_sample_rate).values[:, 0]

        return samples.astype(np.float32)


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

        return ProsodyMetrics(
            pitch=pitch,
            rhythm=rhythm,
            stress=stress,
        )
