"""Forced alignment infrastructure (phoneme-level CTC alignment and GOP scoring)."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional, Protocol

import numpy as np
import torch

from src.models.g2p import OfflineEnglishG2P, WordPronunciation
from src.models.ipa_ctc_head import IPACTCHead
from src.models.mhubert_encoder import DEFAULT_MHUBERT_BUNDLE, MHuBERTEncoder

logger = logging.getLogger(__name__)

FRAME_STEP_SECONDS = 0.02  # 50 Hz (320-sample stride @ 16 kHz)
DEFAULT_GOP_ERROR_THRESHOLD = -1.25


@dataclass
class PhonemeAlignment:
    """Alignment data for a single phoneme."""

    phoneme: str
    start_time: float
    end_time: float
    score: float  # GOP score (log-probability margin)
    is_error: bool
    predicted_phoneme: Optional[str]  # Top competing non-blank phone in span
    is_vowel: bool
    is_voiced: bool


@dataclass
class SyllableAlignment:
    """Syllable-level grouping of aligned phonemes for diff display."""

    syllable_index: int
    phonemes_target: list[str]
    phonemes_predicted: list[str]
    start_time: float
    end_time: float
    score: float
    severity: str  # "clear" | "yellow" | "red"


@dataclass
class WordAlignment:
    """Alignment data for a single word."""

    word: str
    start_time: float
    end_time: float
    phonemes: list[PhonemeAlignment]
    not_reached: bool = False
    syllables: list[SyllableAlignment] = field(default_factory=list)


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


@dataclass
class AlignmentResult:
    """Full alignment bundle including frame log-posteriors for downstream diagnostics."""

    errors: list[PronunciationError]
    alignment: SentenceAlignment
    log_probs: np.ndarray  # (T, 46)
    ipa_to_id: dict[str, int]
    id_to_ipa: dict[int, str]
    frame_step_s: float = FRAME_STEP_SECONDS


class FeatureEncoderProto(Protocol):
    def extract_features(
        self, audio_tensor: torch.Tensor, sample_rate: int = 16000
    ) -> torch.Tensor: ...


class CTCHeadProto(Protocol):
    ipa_to_id: dict[str, int]
    id_to_ipa: dict[int, str]
    blank_id: int

    def predict_log_probs(self, hidden_states: torch.Tensor) -> np.ndarray: ...


def _classify_phoneme(phoneme: str) -> tuple[bool, bool]:
    """Classify phoneme as (is_vowel, is_voiced) for voice quality and rhythm analysis."""
    vowels = {
        "i",
        "ɪ",
        "e",
        "ɛ",
        "æ",
        "a",
        "ɶ",
        "ə",
        "ɚ",
        "ɜ",
        "ɝ",
        "ɨ",
        "ᵻ",
        "ɘ",
        "ɐ",
        "ɵ",
        "ɑ",
        "ɒ",
        "ɔ",
        "o",
        "ʊ",
        "u",
        "ʌ",
        "ɯ",
        "y",
        "ʏ",
        "ø",
        "œ",
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
        "ɛɹ",
        "ɪɹ",
        "ʊɹ",
        "ɑɹ",
        "ɔɹ",
        "oɹ",
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
        "aɪɚ",
        "aɪə",
        "ɹ̩",
    }

    voiced_consonants = {
        "b",
        "d",
        "g",
        "ɡ",
        "ɟ",
        "ɖ",
        "bʰ",
        "dʰ",
        "ɡʰ",
        "bʲ",
        "dʲ",
        "ɡʲ",
        "dʲʲ",
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
        "vʲ",
        "ɦʲ",
        "m",
        "n",
        "ŋ",
        "ɲ",
        "ɳ",
        "ɴ",
        "mʲ",
        "nʲ",
        "ŋʲ",
        "l",
        "ɹ",
        "ɻ",
        "j",
        "w",
        "ʋ",
        "ʎ",
        "ɫ",
        "lʲ",
        "rʲ",
        "ʎʲ",
        "ɭ",
        "ɾ",
        "ɽ",
        "r",
        "ʀ",
        "r̝",
        "dʒ",
        "dʑ",
        "dZ",
        "dʒʲ",
        "dʑʲ",
        "n̩",
        "l̩",
        "r̩",
        "m̩",
        "ɓ",
        "ɗ",
        "ɠ",
    }

    clean_phone = phoneme.strip().strip("/")
    is_vowel = clean_phone in vowels
    is_voiced = is_vowel or (clean_phone in voiced_consonants)
    return is_vowel, is_voiced


def syllabify_word_phonemes(phonemes: list[PhonemeAlignment]) -> list[SyllableAlignment]:
    """Group a word's aligned phonemes into syllables around vowel nuclei."""
    if not phonemes:
        return []
    vowel_indices = [i for i, p in enumerate(phonemes) if p.is_vowel]
    if len(vowel_indices) <= 1:
        groups = [phonemes]
    else:
        groups = []
        start_idx = 0
        for idx in range(len(vowel_indices) - 1):
            v_curr = vowel_indices[idx]
            v_next = vowel_indices[idx + 1]
            inter_consonants = v_next - v_curr - 1
            # Maximal-onset split: keep at most 1-2 onset consonants with the following vowel
            if inter_consonants <= 0:
                split_at = v_next
            elif inter_consonants == 1:
                split_at = v_next - 1
            else:
                split_at = v_curr + 2
            groups.append(phonemes[start_idx:split_at])
            start_idx = split_at
        groups.append(phonemes[start_idx:])

    syllables: list[SyllableAlignment] = []
    for s_idx, grp in enumerate(groups):
        if not grp:
            continue
        min_score = min(p.score for p in grp)
        has_err = any(p.is_error for p in grp)
        if has_err or min_score < -1.25:
            severity = "red"
        elif min_score < -0.5:
            severity = "yellow"
        else:
            severity = "clear"
        syllables.append(
            SyllableAlignment(
                syllable_index=s_idx,
                phonemes_target=[p.phoneme for p in grp],
                phonemes_predicted=[p.predicted_phoneme or p.phoneme for p in grp],
                start_time=grp[0].start_time,
                end_time=grp[-1].end_time,
                score=round(float(min_score), 3),
                severity=severity,
            )
        )
    return syllables


def viterbi_ctc_align(
    log_probs: np.ndarray,
    token_ids: list[int],
    blank_id: int = 45,
    *,
    word_end_token_counts: list[int] | None = None,
    allow_partial: bool = False,
) -> list[tuple[int, int]] | tuple[list[tuple[int, int]], int]:
    """Monotonic Viterbi CTC forced alignment returning `(start_frame, end_frame)` per token.

    When ``allow_partial=True`` and ``word_end_token_counts`` is provided, backtracks
    from the best-scoring word prefix when trailing words would otherwise be forced
    into blank/silence frames, returning ``(spans, reached_word_count)``.
    """
    n_frames = int(log_probs.shape[0])
    n_tokens = len(token_ids)
    if n_tokens == 0:
        return ([], 0) if allow_partial else []
    if n_frames == 0:
        empty = [(0, 0) for _ in range(n_tokens)]
        return (empty, 0) if allow_partial else empty

    # If the utterance has fewer frames than target tokens, strict CTC cannot visit all states;
    # fall back to proportional monotonic slices so downstream consumers still receive spans.
    if n_frames < n_tokens:
        spans: list[tuple[int, int]] = []
        for idx in range(n_tokens):
            s = (idx * n_frames) // n_tokens
            e = max(s + 1, ((idx + 1) * n_frames) // n_tokens)
            spans.append((min(s, n_frames - 1), min(e, n_frames)))
        if allow_partial:
            reached = len(word_end_token_counts) if word_end_token_counts else 0
            return spans, reached
        return spans

    state_len = 2 * n_tokens + 1
    expanded = np.full(state_len, blank_id, dtype=np.int64)
    expanded[1::2] = np.asarray(token_ids, dtype=np.int64)

    neg_inf = -1e9
    dp = np.full((n_frames, state_len), neg_inf, dtype=np.float64)
    back = np.zeros((n_frames, state_len), dtype=np.int64)

    dp[0, 0] = float(log_probs[0, blank_id])
    dp[0, 1] = float(log_probs[0, expanded[1]])

    can_skip = np.zeros(state_len, dtype=bool)
    for s in range(3, state_len, 2):
        if expanded[s] != expanded[s - 2]:
            can_skip[s] = True

    s_idx = np.arange(state_len)
    for t in range(1, n_frames):
        prev = dp[t - 1]
        best_prev = prev.copy()
        best_src = s_idx.copy()

        # Transition from s - 1
        cand1 = np.full(state_len, neg_inf, dtype=np.float64)
        cand1[1:] = prev[:-1]
        take1 = cand1 > best_prev
        best_prev = np.where(take1, cand1, best_prev)
        best_src = np.where(take1, s_idx - 1, best_src)

        # Skip blank from s - 2 when adjacent tokens differ
        cand2 = np.full(state_len, neg_inf, dtype=np.float64)
        cand2[2:] = prev[:-2]
        take2 = can_skip & (cand2 > best_prev)
        best_prev = np.where(take2, cand2, best_prev)
        best_src = np.where(take2, s_idx - 2, best_src)

        dp[t] = best_prev + log_probs[t, expanded]
        back[t] = best_src

    cur = state_len - 1 if dp[-1, state_len - 1] >= dp[-1, state_len - 2] else state_len - 2
    full_path = np.empty(n_frames, dtype=np.int64)
    probe = cur
    for t in range(n_frames - 1, -1, -1):
        full_path[t] = probe
        probe = int(back[t, probe]) if t > 0 else probe

    reached_words = len(word_end_token_counts) if word_end_token_counts else 0
    if allow_partial and word_end_token_counts and len(word_end_token_counts) >= 2:
        # Only allow early prefix truncation when the audio actually goes silent after the prefix.
        speech_slice = log_probs[:, 1:blank_id] if blank_id > 1 else log_probs[:, :blank_id]
        speech_frames = (
            np.flatnonzero(np.max(speech_slice, axis=1) > -2.5)
            if speech_slice.shape[1] > 0
            else np.asarray([], dtype=np.int64)
        )
        last_speech_frame = int(speech_frames[-1]) if speech_frames.size > 0 else n_frames - 1

        full_score = float(dp[-1, cur])
        best_prefix_score = full_score
        best_prefix_state = cur
        best_prefix_words = len(word_end_token_counts)
        for w_idx, tok_count in enumerate(word_end_token_counts[:-1], start=1):
            if tok_count <= 0:
                continue
            s_tok = 2 * tok_count - 1
            s_blk = 2 * tok_count
            cand_state = s_blk if dp[-1, s_blk] >= dp[-1, s_tok] else s_tok
            cand_score = float(dp[-1, cand_state])
            remaining_tokens = n_tokens - tok_count
            if cand_score - full_score > 3.5 * remaining_tokens and cand_score > best_prefix_score:
                # Verify against the full alignment's word end frame so active trailing words aren't truncated.
                tok_frames = np.flatnonzero(full_path == s_tok)
                full_word_end = int(tok_frames[-1]) if tok_frames.size > 0 else n_frames - 1
                tail_frames = log_probs[full_word_end + 1 :, token_ids[tok_count:]]
                tail_has_strong_phone = tail_frames.size > 0 and float(np.max(tail_frames)) > -2.0
                if last_speech_frame - full_word_end <= 5 and not tail_has_strong_phone:
                    best_prefix_score = cand_score
                    best_prefix_state = cand_state
                    best_prefix_words = w_idx
        cur = best_prefix_state
        reached_words = best_prefix_words

    path = np.empty(n_frames, dtype=np.int64)
    for t in range(n_frames - 1, -1, -1):
        path[t] = cur
        cur = int(back[t, cur]) if t > 0 else cur

    active_tokens = (
        word_end_token_counts[reached_words - 1]
        if (allow_partial and word_end_token_counts and reached_words > 0)
        else (0 if allow_partial and word_end_token_counts else n_tokens)
    )
    raw_spans: list[tuple[int, int]] = []
    for k in range(active_tokens):
        state = 2 * k + 1
        frames = np.flatnonzero(path == state)
        if frames.size > 0:
            raw_spans.append((int(frames[0]), int(frames[-1]) + 1))
        else:
            prev_end = raw_spans[-1][1] if raw_spans else 0
            s_frame = min(prev_end, n_frames - 1)
            raw_spans.append((s_frame, min(s_frame + 1, n_frames)))
    while len(raw_spans) < n_tokens:
        raw_spans.append((n_frames, n_frames))
    return (raw_spans, reached_words) if allow_partial else raw_spans


class ForcedAligner:
    """Offline mHuBERT-147 + ctc_v1 forced aligner and GOP scorer."""

    def __init__(
        self,
        bundle_path: str | Path | None = None,
        *,
        encoder: FeatureEncoderProto | None = None,
        ctc_head: CTCHeadProto | None = None,
        g2p: OfflineEnglishG2P | None = None,
        error_threshold: float = DEFAULT_GOP_ERROR_THRESHOLD,
    ) -> None:
        self.bundle_path = Path(bundle_path or DEFAULT_MHUBERT_BUNDLE).expanduser().resolve()
        self.encoder: Any = encoder
        self.ctc_head: Any = ctc_head
        self.g2p: OfflineEnglishG2P | None = g2p
        self.error_threshold = error_threshold
        self._loaded = encoder is not None and ctc_head is not None

    def load(self) -> None:
        if self.encoder is None:
            enc = MHuBERTEncoder(bundle_path=self.bundle_path)
            enc.load()
            self.encoder = enc
        if self.ctc_head is None:
            head = IPACTCHead(bundle_path=self.bundle_path)
            head.load()
            self.ctc_head = head
        if self.g2p is None:
            self.g2p = OfflineEnglishG2P(cmudict_path=self.bundle_path / "cmudict_ipa.json")
        self._loaded = True

    def _ensure_loaded(self) -> None:
        if not self._loaded:
            self.load()
        if self.g2p is None:
            self.g2p = OfflineEnglishG2P(cmudict_path=self.bundle_path / "cmudict_ipa.json")

    def align_with_posteriors(
        self,
        audio_tensor: torch.Tensor,
        target_text: str,
        sample_rate: int = 16000,
        *,
        allow_partial: bool = True,
    ) -> AlignmentResult:
        """Align `target_text` to `audio_tensor` and return posteriors + GOP scores."""
        self._ensure_loaded()
        assert self.encoder is not None and self.ctc_head is not None and self.g2p is not None

        total_duration = float(audio_tensor.reshape(-1).numel()) / float(sample_rate)
        hidden = self.encoder.extract_features(audio_tensor, sample_rate=sample_rate)
        log_probs = self.ctc_head.predict_log_probs(hidden)
        ipa_to_id: dict[str, int] = dict(self.ctc_head.ipa_to_id)
        id_to_ipa: dict[int, str] = dict(self.ctc_head.id_to_ipa)
        blank_id = int(self.ctc_head.blank_id)

        word_prons: list[WordPronunciation] = self.g2p.text_to_words(target_text)
        flat_tokens: list[tuple[int, str, int]] = []
        word_end_token_counts: list[int] = []
        for w_idx, wp in enumerate(word_prons):
            for phone in wp.phonemes:
                if phone in ipa_to_id:
                    flat_tokens.append((w_idx, phone, ipa_to_id[phone]))
            word_end_token_counts.append(len(flat_tokens))

        token_ids = [tok_id for _, _, tok_id in flat_tokens]
        if allow_partial:
            align_out = viterbi_ctc_align(
                log_probs,
                token_ids,
                blank_id=blank_id,
                word_end_token_counts=word_end_token_counts,
                allow_partial=True,
            )
            assert isinstance(align_out, tuple)
            spans, reached_words = align_out
        else:
            raw_only = viterbi_ctc_align(log_probs, token_ids, blank_id=blank_id)
            assert isinstance(raw_only, list)
            spans = raw_only
            reached_words = len(word_prons)

        # Build non-overlapping strictly monotonic phoneme & word alignments
        phonemes_by_word: dict[int, list[PhonemeAlignment]] = {
            i: [] for i in range(len(word_prons))
        }
        errors: list[PronunciationError] = []
        all_scores: list[float] = []
        prev_end_time = 0.0
        n_frames = int(log_probs.shape[0])

        for (w_idx, target_phone, target_id), (s_frame, e_frame) in zip(flat_tokens, spans):
            if w_idx >= reached_words:
                continue
            s_clamped = max(0, min(s_frame, max(0, n_frames - 1)))
            e_clamped = max(s_clamped + 1, min(e_frame, max(1, n_frames)))
            start_t = max(prev_end_time, round(s_clamped * FRAME_STEP_SECONDS, 4))
            end_t = max(start_t + FRAME_STEP_SECONDS, round(e_clamped * FRAME_STEP_SECONDS, 4))
            if total_duration > 0:
                end_t = min(end_t, max(start_t + 1e-3, total_duration))
            prev_end_time = end_t

            seg_lp = log_probs[s_clamped:e_clamped]
            mean_lp = np.mean(seg_lp, axis=0)
            speech_lp = mean_lp.copy()
            speech_lp[blank_id] = -1e9
            if 0 in id_to_ipa and id_to_ipa[0] == "sil" and target_id != 0:
                speech_lp[0] = -1e9

            top_id = int(np.argmax(speech_lp))
            gop = float(mean_lp[target_id] - speech_lp[top_id])
            predicted_phone = id_to_ipa.get(top_id, target_phone)
            is_err = gop < self.error_threshold and predicted_phone != target_phone

            is_vowel, is_voiced = _classify_phoneme(target_phone)
            pa = PhonemeAlignment(
                phoneme=target_phone,
                start_time=start_t,
                end_time=end_t,
                score=gop,
                is_error=is_err,
                predicted_phoneme=predicted_phone,
                is_vowel=is_vowel,
                is_voiced=is_voiced,
            )
            phonemes_by_word[w_idx].append(pa)
            all_scores.append(gop)
            if is_err:
                errors.append(
                    PronunciationError(
                        error_type="substitution",
                        target_phoneme=target_phone,
                        predicted_phoneme=predicted_phone,
                        word_context=word_prons[w_idx].word,
                    )
                )

        word_alignments: list[WordAlignment] = []
        for w_idx, wp in enumerate(word_prons):
            if w_idx >= reached_words:
                word_alignments.append(
                    WordAlignment(
                        word=wp.word,
                        start_time=prev_end_time,
                        end_time=prev_end_time,
                        phonemes=[],
                        not_reached=True,
                        syllables=[],
                    )
                )
                continue
            phs = phonemes_by_word[w_idx]
            if not phs:
                continue
            word_alignments.append(
                WordAlignment(
                    word=wp.word,
                    start_time=phs[0].start_time,
                    end_time=phs[-1].end_time,
                    phonemes=phs,
                    not_reached=False,
                    syllables=syllabify_word_phonemes(phs),
                )
            )

        overall_score = float(np.mean(all_scores)) if all_scores else 0.0
        sentence_alignment = SentenceAlignment(
            text=target_text,
            words=word_alignments,
            total_duration=total_duration,
            overall_score=overall_score,
        )
        return AlignmentResult(
            errors=errors,
            alignment=sentence_alignment,
            log_probs=log_probs,
            ipa_to_id=ipa_to_id,
            id_to_ipa=id_to_ipa,
        )

    def analyze_pronunciation(
        self,
        audio_tensor: torch.Tensor,
        target_text: str,
        sample_rate: int = 16000,
    ) -> tuple[list[PronunciationError], SentenceAlignment]:
        """Run forced alignment and return `(errors, SentenceAlignment)`."""
        result = self.align_with_posteriors(audio_tensor, target_text, sample_rate=sample_rate)
        return result.errors, result.alignment

    def align(
        self, audio_tensor: torch.Tensor, target_text: str, sample_rate: int = 16000
    ) -> SentenceAlignment:
        _, alignment = self.analyze_pronunciation(audio_tensor, target_text, sample_rate)
        return alignment

    def cleanup(self) -> None:
        if self.encoder is not None and hasattr(self.encoder, "cleanup"):
            self.encoder.cleanup()
        if self.ctc_head is not None and hasattr(self.ctc_head, "cleanup"):
            self.ctc_head.cleanup()
        self._loaded = False
