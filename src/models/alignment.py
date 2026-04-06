"""Forced alignment using a deprecated Wav2Vec2 fallback path.

Implements phoneme-level alignment and Goodness of Pronunciation (GOP) scoring.
"""

from dataclasses import dataclass
from typing import Optional

import numpy as np
import torch
import torchaudio

from src.models.g2p import G2PConverter
from src.models.wav2vec2 import Wav2Vec2Model


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

    Comprehensive classification based on Wav2Vec2 XLSR-53 vocabulary
    and espeak-ng IPA output.

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
    """Performs forced alignment using the deprecated Wav2Vec2 fallback path."""

    def __init__(
        self,
        wav2vec2_model: Optional[Wav2Vec2Model] = None,
        g2p_converter: Optional[G2PConverter] = None,
    ) -> None:
        """Initialize forced aligner with acoustic model and G2P converter.

        Args:
            wav2vec2_model: Pre-loaded Wav2Vec2 fallback model (loads default if None)
            g2p_converter: G2P converter (creates default if None)
        """
        if wav2vec2_model is None:
            print("WARNING: Falling back to deprecated Wav2Vec2 forced alignment.")
            self.model = Wav2Vec2Model()
        else:
            self.model = wav2vec2_model

        if g2p_converter is None:
            self.g2p = G2PConverter()
        else:
            self.g2p = g2p_converter

    def analyze_pronunciation(
        self,
        audio_tensor: torch.Tensor,
        target_text: str,
        sample_rate: int = 16000,
    ) -> tuple[list[PronunciationError], SentenceAlignment]:
        """Analyze pronunciation and detect phoneme-level errors.

        Args:
            audio_tensor: Audio waveform tensor
            target_text: Target text string to align
            sample_rate: Sample rate of audio

        Returns:
            Tuple of (list of pronunciation errors, sentence alignment)
        """
        # Convert target text to IPA phonemes
        expected_ipa = self.g2p.convert_to_ipa(target_text)
        expected_phonemes = [p for p in expected_ipa if p not in [" ", "ˈ", "ː"]]

        # Get model predictions and logits
        result = self.model.transcribe(audio_tensor, sample_rate)
        logits_tensor: torch.Tensor = result["logits"]  # type: ignore

        # Perform forced alignment
        alignment = self._perform_alignment(
            target_text,
            expected_phonemes,
            logits_tensor,
            audio_tensor.size(0),
            sample_rate,
        )

        # Detect pronunciation errors
        errors = self._detect_errors(alignment)

        return errors, alignment

    def align(
        self, audio_tensor: torch.Tensor, target_text: str, sample_rate: int = 16000
    ) -> SentenceAlignment:
        """Legacy method for basic forced alignment (backward compatibility).

        Args:
            audio_tensor: Audio waveform tensor
            target_text: Target text string to align
            sample_rate: Sample rate of audio

        Returns:
            SentenceAlignment object with word and phoneme timestamps
        """
        errors, alignment = self.analyze_pronunciation(audio_tensor, target_text, sample_rate)
        return alignment

    def _perform_alignment(
        self,
        text: str,
        expected_phonemes: list[str],
        logits: torch.Tensor,
        num_samples: int,
        sample_rate: int,
    ) -> SentenceAlignment:
        """Perform forced alignment with GOP scoring using torchaudio.

        Args:
            text: Original text string
            expected_phonemes: List of expected IPA phonemes
            logits: Model output logits (T, C) where T is time, C is vocab size
            num_samples: Total number of audio samples
            sample_rate: Audio sample rate

        Returns:
            SentenceAlignment with phoneme-level timing and scores
        """
        if len(expected_phonemes) == 0:
            empty_alignment = SentenceAlignment(
                text=text,
                words=[],
                total_duration=num_samples / sample_rate,
                overall_score=0.0,
            )
            return empty_alignment

        total_duration = num_samples / sample_rate
        num_frames = logits.size(0)

        # Convert logits to log probabilities
        log_probs = torch.log_softmax(logits, dim=-1)

        # Get token IDs for expected phonemes
        target_ids = []
        valid_phonemes = []
        for phoneme in expected_phonemes:
            token_id = self._get_token_id(phoneme)
            if token_id > 0:  # Only include valid phonemes (not blank)
                target_ids.append(token_id)
                valid_phonemes.append(phoneme)

        if len(target_ids) == 0:
            empty_alignment = SentenceAlignment(
                text=text,
                words=[],
                total_duration=total_duration,
                overall_score=0.0,
            )
            return empty_alignment

        target_tensor = torch.tensor([target_ids], dtype=torch.long)

        # Use torchaudio's forced_align to get exact timestamps
        try:
            aligned_labels, scores = torchaudio.functional.forced_align(
                log_probs.unsqueeze(0),
                target_tensor,
                blank=1,  # CTC blank token
            )
        except Exception:
            # Fall back to equal duration if forced_align fails
            return self._fallback_alignment(
                text, expected_phonemes, logits, num_samples, sample_rate
            )

        # Convert frame-level alignment to phoneme-level timestamps
        aligned_labels = aligned_labels[0]  # Remove batch dimension
        scores = scores[0]

        aligned_phonemes = []
        phoneme_idx = 0
        frame_idx = 0
        blank_id = 1

        while frame_idx < num_frames and phoneme_idx < len(valid_phonemes):
            current_label = int(aligned_labels[frame_idx])

            if current_label == blank_id:
                frame_idx += 1
                continue

            target_phoneme_id = target_ids[phoneme_idx]

            # Find the segment of frames assigned to this phoneme
            segment_start = frame_idx
            segment_scores = []

            while frame_idx < num_frames and int(aligned_labels[frame_idx]) == current_label:
                if current_label == target_phoneme_id:
                    segment_scores.append(scores[frame_idx])
                frame_idx += 1

            # If this segment matches our expected phoneme
            if current_label == target_phoneme_id:
                start_time = segment_start * sample_rate / num_frames / sample_rate
                end_time = frame_idx * sample_rate / num_frames / sample_rate

                # Calculate GOP score from segment scores
                gop_score = np.mean(segment_scores) if segment_scores else -10.0

                # Get what was actually predicted
                predicted_phoneme = valid_phonemes[phoneme_idx]
                if gop_score < 0.0:
                    segment_logits = logits[segment_start:frame_idx]

                    # Mask out structural tokens (<pad>=0, <s>=1, </s>=2, <unk>=3)
                    # to avoid picking blank tokens as predicted phonemes
                    masked_logits = segment_logits.clone()
                    masked_logits[:, 0] = -1e9
                    masked_logits[:, 1] = -1e9
                    masked_logits[:, 2] = -1e9
                    masked_logits[:, 3] = -1e9

                    # Find the max logit across the entire time segment
                    # This captures the actual phoneme spike rather than averaging it out with noise
                    max_val, max_idx = torch.max(masked_logits.view(-1), dim=0)
                    # Convert 1D index back to (frame, token) and get the token ID
                    predicted_id = (max_idx % masked_logits.size(1)).item()
                    predicted_phoneme = self.model.processor.decode([predicted_id])

                # Classify phoneme for voice quality analysis
                is_vowel, is_voiced = _classify_phoneme(valid_phonemes[phoneme_idx])

                aligned_phonemes.append(
                    PhonemeAlignment(
                        phoneme=valid_phonemes[phoneme_idx],
                        start_time=start_time,
                        end_time=end_time,
                        score=float(gop_score),
                        is_error=bool(gop_score < 0.0),
                        predicted_phoneme=predicted_phoneme,
                        is_vowel=is_vowel,
                        is_voiced=is_voiced,
                    )
                )
                phoneme_idx += 1
            else:
                frame_idx += 1

        # Create word-level alignment using G2P to map words to phonemes
        words = text.split()
        aligned_words = self._align_words_to_phonemes(
            words, expected_phonemes, aligned_phonemes, total_duration
        )

        # Calculate overall score
        overall_score = np.mean([p.score for p in aligned_phonemes]) if aligned_phonemes else 0.0

        return SentenceAlignment(
            text=text,
            words=aligned_words,
            total_duration=total_duration,
            overall_score=float(overall_score),
        )

    def _fallback_alignment(
        self,
        text: str,
        expected_phonemes: list[str],
        logits: torch.Tensor,
        num_samples: int,
        sample_rate: int,
    ) -> SentenceAlignment:
        """Fall back to equal-duration alignment if forced_align fails.

        Args:
            text: Original text string
            expected_phonemes: List of expected IPA phonemes
            logits: Model output logits
            num_samples: Total number of audio samples
            sample_rate: Audio sample rate

        Returns:
            SentenceAlignment with phoneme-level timing and scores
        """
        total_duration = num_samples / sample_rate
        num_frames = logits.size(0)

        per_phoneme_duration = total_duration / len(expected_phonemes)

        aligned_phonemes = []
        for i, phoneme in enumerate(expected_phonemes):
            start_time = i * per_phoneme_duration
            end_time = (i + 1) * per_phoneme_duration

            frame_start = int(start_time / total_duration * num_frames)
            frame_end = int(end_time / total_duration * num_frames)

            frame_logits = logits[frame_start:frame_end]
            phoneme_id = self._get_token_id(phoneme)
            gop_score = self._calculate_gop(frame_logits, phoneme_id)

            # Get predicted phoneme while masking out structural tokens
            masked_logits = frame_logits.clone()

            # Mask out structural tokens (<pad>=0, <s>=1, </s>=2, <unk>=3)
            masked_logits[:, 0] = -1e9
            masked_logits[:, 1] = -1e9
            masked_logits[:, 2] = -1e9
            masked_logits[:, 3] = -1e9

            # Find the max logit across the entire time segment
            # This captures the actual phoneme spike rather than averaging it out with noise
            max_val, max_idx = torch.max(masked_logits.view(-1), dim=0)
            # Convert 1D index back to (frame, token) and get the token ID
            predicted_id = (max_idx % masked_logits.size(1)).item()
            predicted_phoneme = self.model.processor.decode([predicted_id])
            is_vowel, is_voiced = _classify_phoneme(phoneme)

            aligned_phonemes.append(
                PhonemeAlignment(
                    phoneme=phoneme,
                    start_time=start_time,
                    end_time=end_time,
                    score=float(gop_score),
                    is_error=bool(gop_score < 0.0),
                    predicted_phoneme=predicted_phoneme,
                    is_vowel=is_vowel,
                    is_voiced=is_voiced,
                )
            )

        words = text.split()
        aligned_words = self._align_words_to_phonemes(
            words, expected_phonemes, aligned_phonemes, total_duration
        )

        overall_score = np.mean([p.score for p in aligned_phonemes])

        return SentenceAlignment(
            text=text,
            words=aligned_words,
            total_duration=total_duration,
            overall_score=float(overall_score),
        )

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

    def _get_token_id(self, phoneme: str) -> int:
        """Get tokenizer ID for a phoneme string.

        Args:
            phoneme: IPA phoneme string

        Returns:
            Tokenizer ID (0 if not found)
        """
        # Create a mapping from tokenizer vocabulary
        vocab = self.model.processor.tokenizer.get_vocab()

        # Clean the phoneme string
        clean_phoneme = phoneme.strip()

        if clean_phoneme in vocab:
            return vocab[clean_phoneme]  # type: ignore[no-any-return]

        # Try variations (with/without stress marks)
        for token, token_id in vocab.items():
            if token == clean_phoneme:
                return token_id  # type: ignore[no-any-return]

        # Return 0 (blank token) if not found
        return 0

    def _calculate_gop(self, logits: torch.Tensor, target_id: int) -> float:
        """Calculate Goodness of Pronunciation score.

        GOP is the log-posterior probability of the target phoneme
        normalized by the maximum probability.

        Args:
            logits: Frame-level logits
            target_id: Token ID of target phoneme

        Returns:
            GOP score (lower indicates worse pronunciation)
        """
        if logits.size(0) == 0:
            return 0.0

        # Convert to log probabilities
        log_probs = torch.log_softmax(logits, dim=-1)

        # Get probability of target phoneme across all frames
        target_probs = log_probs[:, target_id]

        # Average log probability
        avg_target_score = torch.mean(target_probs).item()

        return avg_target_score

    def _detect_errors(self, alignment: SentenceAlignment) -> list[PronunciationError]:
        """Detect specific pronunciation errors from alignment.

        Args:
            alignment: Sentence alignment with phoneme scores

        Returns:
            List of detected errors
        """
        errors = []

        for word in alignment.words:
            for phoneme in word.phonemes:
                if phoneme.is_error:
                    # Determine error type
                    error_type = self._classify_error(phoneme)

                    errors.append(
                        PronunciationError(
                            error_type=error_type,
                            target_phoneme=phoneme.phoneme,
                            predicted_phoneme=phoneme.predicted_phoneme or "",
                            word_context=word.word,
                        )
                    )

        return errors

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

    def cleanup(self) -> None:
        """Clean up model resources."""
        self.model.cleanup()
