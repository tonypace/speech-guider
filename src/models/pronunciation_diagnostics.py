"""Six-category pronunciation diagnostics combining CTC posteriors, Praat formants, and R5/R4 cues."""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import Any

import numpy as np
import parselmouth

from src.models.alignment import AlignmentResult, PhonemeAlignment, WordAlignment
from src.models.r5_badges import R5Stage5Badges

logger = logging.getLogger(__name__)

FRAME_RATE_HZ = 50
DISCLAIMER_TEXT = (
    "Acoustic and articulatory cues are uncalibrated aids for guided practice, "
    "not clinical pass/fail scores. Click any word to listen and inspect."
)


@dataclass(frozen=True)
class CategorySpec:
    id: str
    title: str
    contrast: str
    description: str


CATEGORIES: tuple[CategorySpec, ...] = (
    CategorySpec(
        id="voiceless_dental",
        title="Voiceless Dental Fricative",
        contrast="/θ/ vs /s, f, t/",
        description="Checks whether /θ/ holds dental friction rather than shifting to /s/, /f/, or /t/.",
    ),
    CategorySpec(
        id="voiced_dental",
        title="Voiced Dental Fricative",
        contrast="/ð/ vs /d, z/",
        description="Checks whether /ð/ holds voiced dental friction rather than stopping to /d/ or /z/.",
    ),
    CategorySpec(
        id="labiodental_glide",
        title="Labiodental vs. Bilabial Glide",
        contrast="/v/ vs /w/",
        description="Separates lower-lip/teeth /v/ from rounded bilabial glide /w/.",
    ),
    CategorySpec(
        id="liquid_contrast",
        title="Liquid Contrast",
        contrast="/r, ɹ̩/ vs /l, l̩/",
        description="Separates /r/ and syllabic /ɹ̩/ from lateral /l/ and syllabic /l̩/.",
    ),
    CategorySpec(
        id="final_clusters",
        title="Final Consonants & Clusters",
        contrast="Coda stops & clusters",
        description="Checks word-final obstruents and clusters for deletion or weak oral closure.",
    ),
    CategorySpec(
        id="vowel_pairs",
        title="Tense/Lax & Front Vowel Pairs",
        contrast="/ɪ/ vs /iː/, /æ/ vs /ɛ/",
        description="Combines CTC vowel margins with Praat F1/F2 formants and vowel duration.",
    ),
)

_CODA_TARGET_PHONES = frozenset(
    {"p", "b", "t", "d", "k", "g", "s", "z", "θ", "ð", "tʃ", "dʒ", "ʃ", "v", "f"}
)


def _span_frames(start_time: float, end_time: float, total_frames: int) -> tuple[int, int]:
    if total_frames <= 0:
        return 0, 0
    s = max(0, min(int(math.floor(start_time * FRAME_RATE_HZ)), total_frames - 1))
    e = max(s + 1, min(int(math.ceil(end_time * FRAME_RATE_HZ)), total_frames))
    return s, e


def _mean_log_probs(log_probs: np.ndarray, start_time: float, end_time: float) -> np.ndarray:
    s, e = _span_frames(start_time, end_time, int(log_probs.shape[0]))
    if e <= s:
        return np.zeros(log_probs.shape[1], dtype=np.float32)
    return np.asarray(np.mean(log_probs[s:e], axis=0), dtype=np.float32)


def _max_group_lp(
    mean_lp: np.ndarray, ipa_to_id: dict[str, int], phones: tuple[str, ...]
) -> tuple[float, str]:
    best_lp = -1e9
    best_phone = phones[0]
    for p in phones:
        idx = ipa_to_id.get(p)
        if idx is not None and float(mean_lp[idx]) > best_lp:
            best_lp = float(mean_lp[idx])
            best_phone = p
    return best_lp, best_phone


def _extract_praat_vowel_acoustics(
    praat_sound: parselmouth.Sound | None,
    start_time: float,
    end_time: float,
) -> dict[str, float] | None:
    """Measure median F1, F2 (Hz) and duration (ms) on an aligned vowel interval."""
    dur_ms = max(0.0, (end_time - start_time) * 1000.0)
    if praat_sound is None or dur_ms < 25.0:
        return {"duration_ms": round(dur_ms, 1)}
    try:
        clip_start = max(0.0, start_time)
        clip_end = min(float(praat_sound.total_duration), end_time)
        if clip_end - clip_start < 0.025:
            return {"duration_ms": round(dur_ms, 1)}
        part = praat_sound.extract_part(
            from_time=clip_start, to_time=clip_end, preserve_times=False
        )
        formant = part.to_formant_burg(
            time_step=0.01, max_number_of_formants=5, maximum_formant=5500.0
        )
        xs = formant.xs()
        f1_vals = [
            float(formant.get_value_at_time(1, t))
            for t in xs
            if math.isfinite(formant.get_value_at_time(1, t))
        ]
        f2_vals = [
            float(formant.get_value_at_time(2, t))
            for t in xs
            if math.isfinite(formant.get_value_at_time(2, t))
        ]
        out: dict[str, float] = {"duration_ms": round(dur_ms, 1)}
        if f1_vals:
            out["f1_hz"] = round(float(np.median(f1_vals)), 0)
        if f2_vals:
            out["f2_hz"] = round(float(np.median(f2_vals)), 0)
        return out
    except (parselmouth.PraatError, RuntimeError, ValueError):
        return {"duration_ms": round(dur_ms, 1)}


def _articulatory_cue_for_phone(
    target_phone: str,
    start_time: float,
    end_time: float,
    *,
    tvs_raw: np.ndarray | None = None,
    tvs_11ch: np.ndarray | None = None,
    bypass_43d: np.ndarray | None = None,
    labiodental_retraction: np.ndarray | None = None,
    r5_badges: R5Stage5Badges | None = None,
) -> tuple[str | None, dict[str, Any] | None]:
    """Sample R5/R4 articulatory channels over an aligned span and format a brief cue."""
    tvs = tvs_11ch[:, :9] if tvs_11ch is not None else tvs_raw
    if tvs is None or len(tvs) == 0:
        return None, None
    s, e = _span_frames(start_time, end_time, len(tvs))
    if e <= s:
        return None, None

    seg = tvs[s:e]
    med_9 = [round(float(v), 4) for v in np.median(seg, axis=0)]
    animation_left = {
        "normalization": "speaker_z_normalized",
        "values": med_9,
    }
    cue_parts: list[str] = []

    if target_phone in {"v", "w"}:
        lp_med = float(np.median(seg[:, 0]))
        la_min = float(np.min(seg[:, 1]))
        if labiodental_retraction is not None and len(labiodental_retraction) >= e:
            ret_max = float(np.max(labiodental_retraction[s:e]))
            cue_parts.append(f"LP={lp_med:.2f}, LA_min={la_min:.2f}, labiodental={ret_max:.2f}")
        else:
            cue_parts.append(f"LP={lp_med:.2f}, LA_min={la_min:.2f}")
    elif target_phone in {"r", "ɹ̩", "l", "l̩"}:
        lat_med = float(np.median(seg[:, 8]))
        ttcd_min = float(np.min(seg[:, 3]))
        cue_parts.append(f"LAT={lat_med:.2f}, TTCD_min={ttcd_min:.2f}")
    elif target_phone in {"θ", "ð"}:
        ttcl_med = float(np.median(seg[:, 2]))
        ttcd_min = float(np.min(seg[:, 3]))
        cue_parts.append(f"TTCL={ttcl_med:.2f}, TTCD_min={ttcd_min:.2f}")
    elif (
        target_phone in {"k", "p"}
        and r5_badges is not None
        and tvs_11ch is not None
        and bypass_43d is not None
        and "coda_kp_del" in r5_badges.badges
    ):
        badge = r5_badges.evaluate_badge(
            "coda_kp_del",
            tvs_11ch,
            bypass_43d,
            s,
            e,
            target_phone=target_phone,
        )
        if badge.status == "sealed_unreleased":
            cue_parts.append(f"R5 seal reached ({badge.oral_seal_min:.2f}, unreleased)")
        elif badge.oral_seal_reached:
            cue_parts.append(f"R5 seal={badge.oral_seal_min:.2f}")
        else:
            cue_parts.append(f"R5 open seal_min={badge.oral_seal_min:.2f}")

    return (", ".join(cue_parts) if cue_parts else None), animation_left


def _comparison_prompt_for(category_id: str, word: str, target_phone: str) -> str:
    if category_id == "vowel_pairs":
        lower = word.lower()
        if lower in {"ship", "sheep"}:
            return "ship, sheep"
        if lower in {"bat", "bet"}:
            return "bat, bet"
        if lower in {"bit", "beat"}:
            return "bit, beat"
        if lower in {"sit", "seat"}:
            return "sit, seat"
        if lower in {"bad", "bed"}:
            return "bad, bed"
        if lower in {"live", "leave"}:
            return "live, leave"
    return word


def _category_status(flagged_count: int, tested_count: int) -> str:
    if tested_count == 0:
        return "not_tested"
    if flagged_count >= 2:
        return "needs_focus"
    if flagged_count == 1:
        return "watch"
    return "clear"


def evaluate_pronunciation_diagnostics(
    alignment_result: AlignmentResult,
    *,
    praat_sound: parselmouth.Sound | None = None,
    tvs_raw: np.ndarray | None = None,
    tvs_11ch: np.ndarray | None = None,
    bypass_43d: np.ndarray | None = None,
    labiodental_retraction: np.ndarray | None = None,
    r5_badges: R5Stage5Badges | None = None,
    margin_threshold: float = -0.5,
    coda_blank_margin: float = 0.6,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Evaluate 6 learner-weakness categories and produce enriched UI error entries."""
    log_probs = alignment_result.log_probs
    ipa_to_id = alignment_result.ipa_to_id
    blank_id = int(log_probs.shape[1] - 1)
    words: list[WordAlignment] = alignment_result.alignment.words

    cat_tested: dict[str, int] = {spec.id: 0 for spec in CATEGORIES}
    cat_flagged: dict[str, list[dict[str, Any]]] = {spec.id: [] for spec in CATEGORIES}
    cat_notes: dict[str, list[str]] = {spec.id: [] for spec in CATEGORIES}
    enriched_errors: list[dict[str, Any]] = []

    def _record_item(
        spec: CategorySpec,
        word_obj: WordAlignment,
        pa: PhonemeAlignment,
        *,
        flagged: bool,
        predicted: str,
        margin: float,
        evidence_summary: str,
        acoustics: dict[str, float] | None = None,
    ) -> None:
        cat_tested[spec.id] += 1
        cue, anim_left = _articulatory_cue_for_phone(
            pa.phoneme,
            pa.start_time,
            pa.end_time,
            tvs_raw=tvs_raw,
            tvs_11ch=tvs_11ch,
            bypass_43d=bypass_43d,
            labiodental_retraction=labiodental_retraction,
            r5_badges=r5_badges,
        )
        full_evidence = f"{evidence_summary} ({cue})" if cue else evidence_summary
        if not flagged:
            return
        err_index = len(enriched_errors)
        item: dict[str, Any] = {
            "error_index": err_index,
            "error_type": spec.id,
            "category_id": spec.id,
            "category_label": spec.title,
            "target_phoneme": pa.phoneme,
            "predicted_phoneme": predicted,
            "word_context": word_obj.word,
            "start_time": pa.start_time,
            "end_time": pa.end_time,
            "score": round(margin, 3),
            "evidence_summary": full_evidence,
            "comparison_prompt": _comparison_prompt_for(spec.id, word_obj.word, pa.phoneme),
        }
        if acoustics:
            item["acoustics"] = acoustics
        if anim_left is not None:
            item["animation_left"] = anim_left
        enriched_errors.append(item)
        cat_flagged[spec.id].append(
            {
                "word": word_obj.word,
                "target_phoneme": pa.phoneme,
                "predicted_phoneme": predicted,
                "start_time": pa.start_time,
                "end_time": pa.end_time,
                "error_index": err_index,
                "evidence_summary": full_evidence,
                "comparison_prompt": item["comparison_prompt"],
                "acoustics": acoustics,
            }
        )
        cat_notes[spec.id].append(full_evidence)

    spec_by_id = {spec.id: spec for spec in CATEGORIES}

    for word_obj in words:
        if getattr(word_obj, "not_reached", False):
            continue
        n_ph = len(word_obj.phonemes)
        for p_idx, pa in enumerate(word_obj.phonemes):
            mean_lp = _mean_log_probs(log_probs, pa.start_time, pa.end_time)
            target_id = ipa_to_id.get(pa.phoneme)
            if target_id is None:
                continue
            target_lp = float(mean_lp[target_id])

            # 1. Voiceless dental /θ/ vs /s, f, t/
            if pa.phoneme == "θ":
                comp_lp, comp_phone = _max_group_lp(mean_lp, ipa_to_id, ("s", "f", "t"))
                margin = target_lp - comp_lp
                flagged = margin < margin_threshold
                evidence = (
                    f"Weak /θ/ cue — leaned closer to /{comp_phone}/"
                    if flagged
                    else "/θ/ distinct from /s, f, t/"
                )
                _record_item(
                    spec_by_id["voiceless_dental"],
                    word_obj,
                    pa,
                    flagged=flagged,
                    predicted=comp_phone if flagged else "θ",
                    margin=margin,
                    evidence_summary=evidence,
                )

            # 2. Voiced dental /ð/ vs /d, z/
            elif pa.phoneme == "ð":
                comp_lp, comp_phone = _max_group_lp(mean_lp, ipa_to_id, ("d", "z"))
                margin = target_lp - comp_lp
                flagged = margin < margin_threshold
                evidence = (
                    f"Weak /ð/ cue — leaned closer to /{comp_phone}/"
                    if flagged
                    else "/ð/ distinct from /d, z/"
                )
                _record_item(
                    spec_by_id["voiced_dental"],
                    word_obj,
                    pa,
                    flagged=flagged,
                    predicted=comp_phone if flagged else "ð",
                    margin=margin,
                    evidence_summary=evidence,
                )

            # 3. Labiodental vs bilabial glide /v/ <-> /w/
            elif pa.phoneme in {"v", "w"}:
                other = "w" if pa.phoneme == "v" else "v"
                comp_lp, _ = _max_group_lp(mean_lp, ipa_to_id, (other,))
                margin = target_lp - comp_lp
                flagged = margin < margin_threshold
                evidence = (
                    f"Weak /{pa.phoneme}/ cue — leaned closer to /{other}/"
                    if flagged
                    else f"/{pa.phoneme}/ distinct from /{other}/"
                )
                _record_item(
                    spec_by_id["labiodental_glide"],
                    word_obj,
                    pa,
                    flagged=flagged,
                    predicted=other if flagged else pa.phoneme,
                    margin=margin,
                    evidence_summary=evidence,
                )

            # 4. Liquid contrast /r, ɹ̩/ <-> /l, l̩/
            elif pa.phoneme in {"r", "ɹ̩", "l", "l̩"}:
                comp_group = ("l", "l̩") if pa.phoneme in {"r", "ɹ̩"} else ("r", "ɹ̩")
                comp_lp, comp_phone = _max_group_lp(mean_lp, ipa_to_id, comp_group)
                margin = target_lp - comp_lp
                flagged = margin < margin_threshold
                evidence = (
                    f"Weak /{pa.phoneme}/ cue — leaned closer to /{comp_phone}/"
                    if flagged
                    else f"/{pa.phoneme}/ separated from /{comp_group[0]}/"
                )
                _record_item(
                    spec_by_id["liquid_contrast"],
                    word_obj,
                    pa,
                    flagged=flagged,
                    predicted=comp_phone if flagged else pa.phoneme,
                    margin=margin,
                    evidence_summary=evidence,
                )

            # 6. Front vowel pairs /ɪ/ vs /i/, /æ/ vs /ɛ/
            elif pa.phoneme in {"ɪ", "i", "æ", "ɛ"}:
                pair_map = {"ɪ": "i", "i": "ɪ", "æ": "ɛ", "ɛ": "æ"}
                other = pair_map[pa.phoneme]
                comp_lp, _ = _max_group_lp(mean_lp, ipa_to_id, (other,))
                margin = target_lp - comp_lp
                flagged = margin < margin_threshold
                acoustics = _extract_praat_vowel_acoustics(praat_sound, pa.start_time, pa.end_time)
                ac_note = ""
                if acoustics:
                    parts = []
                    if "f1_hz" in acoustics and "f2_hz" in acoustics:
                        parts.append(
                            f"F1={acoustics['f1_hz']:.0f}Hz, F2={acoustics['f2_hz']:.0f}Hz"
                        )
                    parts.append(f"{acoustics['duration_ms']:.0f}ms")
                    ac_note = " [" + ", ".join(parts) + "]"
                evidence = (
                    f"Vowel /{pa.phoneme}/ overlapped toward /{other}/{ac_note}"
                    if flagged
                    else f"/{pa.phoneme}/ clear{ac_note}"
                )
                _record_item(
                    spec_by_id["vowel_pairs"],
                    word_obj,
                    pa,
                    flagged=flagged,
                    predicted=other if flagged else pa.phoneme,
                    margin=margin,
                    evidence_summary=evidence,
                    acoustics=acoustics,
                )

            # 5. Final consonants & coda clusters (trailing obstruents in a word)
            is_coda_obstruent = pa.phoneme in _CODA_TARGET_PHONES and p_idx >= max(1, n_ph - 2)
            # Only treat penultimate phone as coda cluster member when trailing phone is also a consonant
            if p_idx == n_ph - 2 and n_ph >= 2:
                next_is_vowel = word_obj.phonemes[p_idx + 1].is_vowel
                if next_is_vowel:
                    is_coda_obstruent = False
            if is_coda_obstruent:
                s_f, e_f = _span_frames(pa.start_time, pa.end_time, int(log_probs.shape[0]))
                peak_target = (
                    float(np.max(log_probs[s_f:e_f, target_id])) if e_f > s_f else target_lp
                )
                blank_mean = float(mean_lp[blank_id])
                coda_margin = peak_target - blank_mean
                flagged = coda_margin < -coda_blank_margin
                evidence = (
                    f"Weak final /{pa.phoneme}/ release (blank-dominated coda)"
                    if flagged
                    else f"Final /{pa.phoneme}/ detected"
                )
                _record_item(
                    spec_by_id["final_clusters"],
                    word_obj,
                    pa,
                    flagged=flagged,
                    predicted="<deleted>" if flagged else pa.phoneme,
                    margin=coda_margin,
                    evidence_summary=evidence,
                )

    category_to_passage = {
        "voiceless_dental": "dental_fricatives",
        "voiced_dental": "dental_fricatives",
        "labiodental_glide": "labiodental_glide",
        "liquid_contrast": "liquid_contrast",
        "final_clusters": "final_clusters",
        "vowel_pairs": "vowel_pairs",
    }

    for word_obj in words:
        if getattr(word_obj, "not_reached", False) or not getattr(word_obj, "syllables", None):
            continue
        for syl in word_obj.syllables:
            for err in enriched_errors:
                if (
                    err["word_context"] == word_obj.word
                    and err["start_time"] >= syl.start_time - 0.01
                    and err["end_time"] <= syl.end_time + 0.01
                ):
                    syl.severity = "red"
                    break

    categories_payload: list[dict[str, Any]] = []
    weakness_summary: list[dict[str, Any]] = []
    for spec in CATEGORIES:
        flagged_items = cat_flagged[spec.id]
        tested = cat_tested[spec.id]
        status = _category_status(len(flagged_items), tested)
        summary_note = (
            cat_notes[spec.id][0]
            if cat_notes[spec.id]
            else (
                "Not targeted in this text."
                if tested == 0
                else f"Checked {tested} target cue(s); no clear shifts."
            )
        )
        categories_payload.append(
            {
                "id": spec.id,
                "title": spec.title,
                "contrast": spec.contrast,
                "description": spec.description,
                "status": status,
                "tested_count": tested,
                "flagged_count": len(flagged_items),
                "summary": summary_note,
                "flagged_words": flagged_items,
            }
        )
        if flagged_items:
            word_names = ", ".join(dict.fromkeys(str(item["word"]) for item in flagged_items[:4]))
            weakness_summary.append(
                {
                    "category_id": spec.id,
                    "title": spec.title,
                    "contrast": spec.contrast,
                    "flagged_count": len(flagged_items),
                    "drill_passage_id": category_to_passage.get(spec.id, "full_diagnostic"),
                    "summary_text": f"{spec.title} ({spec.contrast}): {cat_notes[spec.id][0]} — in {word_names}",
                    "sample_word": flagged_items[0],
                }
            )

    weakness_summary.sort(key=lambda x: int(x["flagged_count"]), reverse=True)

    diagnostics_payload = {
        "status": "available",
        "disclaimer": DISCLAIMER_TEXT,
        "categories": categories_payload,
        "weakness_summary": weakness_summary,
        "flagged_count": len(enriched_errors),
    }
    return diagnostics_payload, enriched_errors
