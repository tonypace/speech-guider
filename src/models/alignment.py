"""Forced alignment infrastructure (phoneme-level alignment and GOP scoring).

NOTE: This module provides the alignment data structures and scoring logic,
but is currently non-functional pending integration of a phoneme CTC model.
The previous wav2vec2-based fallback has been removed.

TODO: Integrate a phoneme recognition model (e.g., MMS-300m-FA or similar CTC
model) to restore forced alignment and error detection functionality.
"""

from dataclasses import dataclass
from typing import Optional

import numpy as np
import torch
import torchaudio

from src.models.g2p import G2PConverter


@dataclass
class PhonemeAlignment:
    """Alignment data for a single phoneme."""

    phoneme: str
    start_time: float
    end_time: float
    score: float  # GOP score (log-probability)
    is_error: bool
    predicted_phoneme: Optional[str]  # What the model thought was spoken
    is_vowel: bool  # Is this a vowel (for voice quality analysis)
    is_voiced: bool  # Is this phoneme voiced (for voice quality analysis)


@dataclass
class WordAlignment:
    """Alignment data for a single word."""

    word: str
    start_time: float
    end_time: float
    phonemes: list[PhonemeAlignment]


@dataclass
class SentenceAlignment:
    """Complete alignment for a sentence."""

    text: str
    words: list[WordAlignment]
    total_duration: float
    overall_score: float


@dataclass
class PronunciationError:
    """Represents a specific pronunciation error."""

    error_type: str  # "substitution", "deletion", "insertion"
    target_phoneme: str
    predicted_phoneme: str
    word_context: str


def _classify_phoneme(phoneme: str) -> tuple[bool, bool]:
    """Classify phoneme as vowel/voiced for voice quality analysis.

    Comprehensive classification based on IPA phoneme vocabulary.

    Args:
        phoneme: IPA phoneme string

    Returns:
        Tuple of (is_vowel, is_voiced)
    """
    # Vowels (monophthongs, diphthongs, long vowels, nasalized, r-colored)
    vowels = {
        # Monophthongs - front
        "i",
        "ɪ",
        "e",
        "ɛ",
        "æ",
        "a",
        "ɶ",
        # Monophthongs - central
        "ə",
        "ɚ",
        "ɜ",
        "ɝ",
        "ɨ",
        "ᵻ",
        "ɘ",
        "ɐ",
        "ɵ",
        # Monophthongs - back
        "ɑ",
        "ɒ",
        "ɔ",
        "o",
        "ʊ",
        "u",
        "ʌ",
        "ɯ",
        # Rounded front vowels
        "y",
        "ʏ",
        "ø",
        "œ",
        # Long vowels
        "iː",
        "uː",
        "eː",
        "oː",
        "ɔː",
        "ɑː",
        "ɜː",
        "æː",
        "yː",
        "ɛː",
        "øː",
        "ʊː",
        "ɪː",
        "aː",
        "əː",
        # Nasalized vowels
        "ɑ̃",
        "ɔ̃",
        "ɛ̃",
        "œ̃",
        "ɐ̃",
        "ũ",
        "ĩ",
        "ã",
        "ẽ",
        "õ",
        "ũ",
        "ã",
        # R-colored vowels
        "ɛɹ",
        "ɪɹ",
        "ʊɹ",
        "ɑɹ",
        "ɔɹ",
        "oɹ",
        # Diphthongs
        "aɪ",
        "eɪ",
        "oʊ",
        "aʊ",
        "ɔɪ",
        "iə",
        "ʊə",
        "eʊ",
        "ɪu",
        "əɪ",
        "uɪ",
        "æi",
        "ɛɪ",
        "iʊ",
        "eə",
        "oɪ",
        "əʊ",
        # Triphthongs
        "aɪɚ",
        "aɪə",
    }

    # Voiced consonants (includes all voiced stops, fricatives, nasals, approximants, affricates)
    voiced_consonants = {
        # Plosives
        "b",
        "d",
        "ɡ",
        "ɟ",
        "ɖ",
        # Aspirated voiced (breathy)
        "bʰ",
        "dʰ",
        "ɡʰ",
        # Palatalized voiced plosives
        "bʲ",
        "dʲ",
        "ɡʲ",
        "dʲʲ",
        # Fricatives
        "v",
        "ð",
        "z",
        "ʒ",
        "ɣ",
        "ʐ",
        "ʑ",
        "ɦ",
        "ʝ",
        "β",
        "ɦ",
        # Palatalized fricatives
        "vʲ",
        "ɦʲ",
        # Nasals
        "m",
        "n",
        "ŋ",
        "ɲ",
        "ɳ",
        "ɴ",
        # Palatalized nasals
        "mʲ",
        "nʲ",
        "ŋʲ",
        # Approximants
        "l",
        "ɹ",
        "ɻ",
        "j",
        "w",
        "ʋ",
        "ʎ",
        "ɫ",
        # Palatalized approximants
        "lʲ",
        "rʲ",
        "nʲ",
        "ŋʲ",
        "ʎʲ",
        # Laterals
        "ɬ",
        "ɭ",
        # Taps/Flaps
        "ɾ",
        "ɽ",
        # Trills
        "r",
        "ʀ",
        "r̝",
        "r̩",
        # Affricates
        "dʒ",
        "dʑ",
        "dZ",
        # Palatalized affricates
        "dʒʲ",
        "dʑʲ",
        # Syllabic consonants
        "n̩",
        "l̩",
        "r̩",
        "m̩",
        # Implosives (rare but possible)
        "ɓ",
        "ɗ",
        "ɠ",
    }

    clean_phone = phoneme.strip().strip("/")

    is_vowel = clean_phone in vowels
    is_voiced = is_vowel or clean_phone in voiced_consonants

    return is_vowel, is_voiced


class ForcedAligner:
    """Forced alignment infrastructure (non-functional pending phoneme model).

    This class provides the data structures and scoring logic for forced alignment,
    but requires a phoneme CTC model to be integrated. The previous wav2vec2-based
    implementation has been removed.

    TODO: Integrate a phoneme recognition model to restore functionality.
    """

    def __init__(
        self,
        g2p_converter: Optional[G2PConverter] = None,
    ) -> None:
        """Initialize forced aligner.

        Args:
            g2p_converter: G2P converter (creates default if None)
        """
        print("WARNING: ForcedAligner is non-functional pending phoneme model integration.")
        self.g2p = g2p_converter if g2p_converter is not None else G2PConverter()

    def analyze_pronunciation(
        self,
        audio_tensor: torch.Tensor,
        target_text: str,
        sample_rate: int = 16000,
    ) -> tuple[list[PronunciationError], SentenceAlignment]:
        """Analyze pronunciation and detect phoneme-level errors.

        NOTE: Currently non-functional. Returns empty errors and a placeholder
        alignment. Requires phoneme model integration to work.

        Args:
            audio_tensor: Audio waveform tensor
            target_text: Target text string to align
            sample_rate: Sample rate of audio

        Returns:
            Tuple of (empty list, placeholder alignment)
        """
        # Placeholder implementation - returns empty results
        # TODO: Integrate phoneme model to restore functionality
        total_duration = audio_tensor.size(0) / sample_rate

        empty_alignment = SentenceAlignment(
            text=target_text,
            words=[],
            total_duration=total_duration,
            overall_score=0.0,
        )

        return [], empty_alignment

    def align(
        self, audio_tensor: torch.Tensor, target_text: str, sample_rate: int = 16000
    ) -> SentenceAlignment:
        """Legacy method for basic forced alignment.

        NOTE: Currently non-functional. Returns placeholder alignment.

        Args:
            audio_tensor: Audio waveform tensor
            target_text: Target text string to align
            sample_rate: Sample rate of audio

        Returns:
            Placeholder SentenceAlignment
        """
        errors, alignment = self.analyze_pronunciation(audio_tensor, target_text, sample_rate)
        return alignment

    def _align_words_to_phonemes(
        self,
        words: list[str],
        expected_phonemes: list[str],
        aligned_phonemes: list[PhonemeAlignment],
        total_duration: float,
    ) -> list[WordAlignment]:
        """Map words to their aligned phonemes using G2P word boundaries.

        Args:
            words: List of words in the sentence
            expected_phonemes: Complete list of expected phonemes
            aligned_phonemes: Aligned phoneme objects with timestamps
            total_duration: Total audio duration

        Returns:
            List of word alignments with associated phonemes
        """
        aligned_words = []
        phoneme_idx = 0

        for word in words:
            # Get phonemes for this specific word using G2P
            word_ipa = self.g2p.convert_to_ipa(word)
            word_phonemes = [p for p in word_ipa if p not in [" ", "ˈ", "ː"]]

            if not word_phonemes:
                continue

            # Find the corresponding aligned phonemes
            word_aligned_phonemes = []
            end_idx = min(phoneme_idx + len(word_phonemes), len(aligned_phonemes))

            for i in range(phoneme_idx, end_idx):
                if aligned_phonemes[i].phoneme in word_phonemes:
                    word_aligned_phonemes.append(aligned_phonemes[i])

            if word_aligned_phonemes:
                start_time = word_aligned_phonemes[0].start_time
                end_time = word_aligned_phonemes[-1].end_time

                aligned_words.append(
                    WordAlignment(
                        word=word,
                        start_time=start_time,
                        end_time=end_time,
                        phonemes=word_aligned_phonemes,
                    )
                )

            phoneme_idx = end_idx

        return aligned_words

    def _classify_error(self, alignment: PhonemeAlignment) -> str:
        """Classify the type of pronunciation error.

        Args:
            alignment: Phoneme alignment data

        Returns:
            Error type string
        """
        if not alignment.predicted_phoneme:
            return "deletion"

        # Common substitutions for ESL learners
        voicing_errors = {
            "/s/": "/z/",
            "/z/": "/s/",
            "/f/": "/v/",
            "/v/": "/f/",
            "/p/": "/b/",
            "/b/": "/p/",
            "/t/": "/d/",
            "/d/": "/t/",
            "/k/": "/g/",
            "/g/": "/k/",
        }

        target = alignment.phoneme
        predicted = alignment.predicted_phoneme

        # Check for voicing errors
        for voiced, unvoiced in voicing_errors.items():
            if target in unvoiced and predicted in voiced:
                return "final-consonant-devoicing"
            if target in voiced and predicted in unvoiced:
                return "initial-consonant-devoicing"

        # Check for specific substitutions
        substitutions = {
            "/θ/": "/s/",  # think -> sink
            "/ð/": "/d/",  # this -> dis
            "/r/": "/l/",  # rice -> lice
            "/l/": "/r/",  # lice -> rice
        }

        for target_phoneme, substitute in substitutions.items():
            if target in target_phoneme and predicted in substitute:
                return f"substitution-{target_phoneme[1:-1]}-{substitute[1:-1]}"

        return "substitution"
