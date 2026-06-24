"""Forced alignment infrastructure (phoneme-level alignment and GOP scoring).

NOTE: This module provides the alignment data structures and scoring logic,
but is currently non-functional pending integration of a phoneme CTC model.
The previous wav2vec2-based fallback has been removed.

TODO: Integrate a phoneme recognition model (e.g., MMS-300m-FA or similar CTC
model) to restore forced alignment and error detection functionality.
"""

from dataclasses import dataclass
from typing import Optional

import torch


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
    """Placeholder aligner. Non-functional pending phoneme CTC model integration."""

    def __init__(self) -> None:
        print("WARNING: ForcedAligner is non-functional pending phoneme model integration.")

    def analyze_pronunciation(
        self,
        audio_tensor: torch.Tensor,
        target_text: str,
        sample_rate: int = 16000,
    ) -> tuple[list[PronunciationError], SentenceAlignment]:
        """Return placeholder alignment. No phoneme model integrated yet."""
        total_duration = audio_tensor.size(0) / sample_rate
        return [], SentenceAlignment(
            text=target_text, words=[], total_duration=total_duration, overall_score=0.0
        )

    def align(
        self, audio_tensor: torch.Tensor, target_text: str, sample_rate: int = 16000
    ) -> SentenceAlignment:
        _, alignment = self.analyze_pronunciation(audio_tensor, target_text, sample_rate)
        return alignment
