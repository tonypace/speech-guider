"""Audio processing for prosody analysis using Parselmouth.

Implements rhythm (nPVI), stress patterns, and pitch extraction.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np
import parselmouth

# Temporary debug flag for nPVI calculation verification
# TODO: Remove after confirming nPVI works correctly
DEBUG_NPVI = True


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
            raise ValueError(f"Failed to load audio file: {e}")

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

        return samples.astype(np.float32)  # type: ignore[no-any-return]


class ProsodyAnalyzer:
    """Analyzes prosody features: rhythm, stress, and pitch."""

    def __init__(self, audio_context: AudioContext) -> None:
        """Initialize prosody analyzer.

        Args:
            audio_context: AudioContext for the audio to analyze
        """
        self.audio = audio_context.praat_sound

    def analyze_pitch(self) -> PitchContour:
        """Extract pitch (F0) contour.

        Returns:
            PitchContour with F0 values and statistics
        """
        pitch = self.audio.to_pitch()
        f0_values = pitch.selected_array["frequency"]

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
        if DEBUG_NPVI:
            print("[DEBUG_nPVI] === RHYTHM ANALYSIS ===")
            print(
                f"[DEBUG_nPVI] Called with {len(vowel_timestamps) if vowel_timestamps else 0} vowel timestamps"
            )
            print(f"[DEBUG_nPVI] Timestamps: {vowel_timestamps}")

        print(
            f"[analyze_rhythm] Called with {len(vowel_timestamps) if vowel_timestamps else 0} timestamps"
        )
        if vowel_timestamps:
            print(f"[analyze_rhythm] vowel_timestamps: {vowel_timestamps}")

        if not vowel_timestamps or len(vowel_timestamps) < 2:
            if DEBUG_NPVI:
                print(
                    f"[DEBUG_nPVI] INSUFFICIENT DATA - need at least 2 vowels, got {len(vowel_timestamps) if vowel_timestamps else 0}"
                )
            print("[analyze_rhythm] Insufficient vowel timestamps, returning 0 nPVI")
            return RhythmMetrics(
                npvi=0.0,
                vowel_durations=[],
                classification="insufficient_data",
            )

        # Calculate vowel durations
        vowel_durations = [end - start for start, end in vowel_timestamps]
        print(f"[analyze_rhythm] vowel_durations: {vowel_durations}")
        if DEBUG_NPVI:
            print(f"[DEBUG_nPVI] Vowel durations: {[round(d, 3) for d in vowel_durations]}")
            print(f"[DEBUG_nPVI] Sum of durations: {sum(vowel_durations):.3f}s")
            print(f"[DEBUG_nPVI] Mean duration: {np.mean(vowel_durations):.3f}s")
            print(f"[DEBUG_nPVI] Std duration: {np.std(vowel_durations):.3f}s")

        # Calculate nPVI
        num_vowels = len(vowel_durations)
        durations = np.array(vowel_durations)

        # Pairwise differences
        differences = np.abs(durations[:-1] - durations[1:])
        means = (durations[:-1] + durations[1:]) / 2

        if DEBUG_NPVI:
            print(f"[DEBUG_nPVI] Pairwise differences: {[round(d, 3) for d in differences]}")
            print(f"[DEBUG_nPVI] Pairwise means: {[round(m, 3) for m in means]}")
            print(
                f"[DEBUG_nPVI] Differences/means: {[round(d / m, 3) for d, m in zip(differences, means)]}"
            )

        # nPVI formula
        npvi = 100 * np.sum(differences / means) / (num_vowels - 1)

        print(f"[analyze_rhythm] Calculated nPVI: {npvi}")
        if DEBUG_NPVI:
            print(f"[DEBUG_nPVI] Sum(differences/means): {np.sum(differences / means):.3f}")
            print(
                f"[DEBUG_nPVI] nPVI = 100 * {np.sum(differences / means):.3f} / {num_vowels - 1} = {npvi:.2f}"
            )

        # Classify based on nPVI threshold
        # English (stress-timed) typically has nPVI > 40
        # Romance languages (syllable-timed) typically have nPVI < 40
        classification = "stress-timed" if npvi > 40 else "syllable-timed"
        if DEBUG_NPVI:
            print(f"[DEBUG_nPVI] Classification: {classification} (threshold: 40)")

        return RhythmMetrics(
            npvi=float(npvi),
            vowel_durations=vowel_durations,
            classification=classification,
        )

    def analyze_stress(
        self,
        word_timestamps: list[tuple[str, float, float]],
    ) -> Optional[StressPattern]:
        """Identify primary stressed word using combined F0 and intensity.

        Args:
            word_timestamps: List of (word, start_time, end_time)

        Returns:
            StressPattern with primary stress information
        """
        if not word_timestamps:
            return None

        words_data = []

        for word, start_time, end_time in word_timestamps:
            # Extract sound part for this word
            sound_slice = self.audio.extract_part(from_time=start_time, to_time=end_time)

            # Extract pitch range over this word
            pitch_slice = sound_slice.to_pitch()
            pitch_values = pitch_slice.selected_array["frequency"]
            voiced_pitch = pitch_values[pitch_values > 0]

            # Extract intensity average over this word
            intensity_slice = sound_slice.to_intensity()
            mean_intensity = np.mean(intensity_slice.values)

            # Calculate prominence score (combined pitch excursion and intensity)
            if len(voiced_pitch) > 0:
                pitch_excursion = np.max(voiced_pitch) - np.min(voiced_pitch)
            else:
                pitch_excursion = 0.0

            # Normalize and combine scores
            prominence_score = float(pitch_excursion) + float(mean_intensity / 100.0)

            words_data.append(
                {
                    "word": word,
                    "start_time": start_time,
                    "end_time": end_time,
                    "prominence_score": prominence_score,
                }
            )

        # Find word with highest prominence
        if not words_data:
            return None

        stressed_word_data = max(words_data, key=lambda x: x["prominence_score"])  # type: ignore[arg-type, return-value]

        return StressPattern(
            primary_stress_word=stressed_word_data["word"],  # type: ignore[arg-type]
            primary_stress_time=stressed_word_data["start_time"],  # type: ignore[arg-type]
            prominence_score=stressed_word_data["prominence_score"],  # type: ignore[arg-type]
        )

    def analyze_complete(
        self,
        vowel_timestamps: list[tuple[float, float]],
        word_timestamps: list[tuple[str, float, float]],
    ) -> ProsodyMetrics:
        """Run complete prosody analysis.

        Args:
            vowel_timestamps: List of vowel (start_time, end_time)
            word_timestamps: List of word (word, start_time, end_time)

        Returns:
            ProsodyMetrics with complete analysis
        """
        pitch = self.analyze_pitch()
        rhythm = self.analyze_rhythm(vowel_timestamps)
        stress = self.analyze_stress(word_timestamps)

        return ProsodyMetrics(
            pitch=pitch,
            rhythm=rhythm,
            stress=stress,
        )
