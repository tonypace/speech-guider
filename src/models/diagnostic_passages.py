"""Curated diagnostic passages designed to expose typical pronunciation errors."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class DiagnosticPassage:
    """One curated practice passage with targeted pronunciation contrasts."""

    id: str
    title: str
    subtitle: str
    focus_categories: tuple[str, ...]
    target_contrasts: tuple[str, ...]
    text: str


DIAGNOSTIC_PASSAGES: tuple[DiagnosticPassage, ...] = (
    DiagnosticPassage(
        id="full_diagnostic",
        title="Full 6-Category Diagnostic",
        subtitle="Balanced 5-sentence screening across dentals, /v/-/w/, /r/-/l/, final clusters, and front vowel pairs",
        focus_categories=(
            "voiceless_dental",
            "voiced_dental",
            "labiodental_glide",
            "liquid_contrast",
            "final_clusters",
            "vowel_pairs",
        ),
        target_contrasts=(
            "/θ/",
            "/ð/",
            "/v/ vs /w/",
            "/r/ vs /l/",
            "Final clusters",
            "/ɪ/ vs /iː/, /æ/ vs /ɛ/",
        ),
        text=(
            "Every Thursday morning, Ruth and Phil drive their silver van past the busy harbor. "
            "Phil loves fresh fruit, so he grabs six sweet peaches and three red apples at the market. "
            "A thick fog rolls over the water, making the paths wet and slick. "
            'Ruth checks her watch, smiles, and says, "They\'ll ship those crates before noon if we hurry." '
            "Then they bet a small bat can reach the big ship before the sheep cross."
        ),
    ),
    DiagnosticPassage(
        id="dental_fricatives",
        title="Dental Fricatives (/θ/ & /ð/)",
        subtitle="Targets tongue-tip placement between or behind upper teeth without /s, f, t, d, z/ substitution",
        focus_categories=("voiceless_dental", "voiced_dental"),
        target_contrasts=("/θ/ vs /s, f, t/", "/ð/ vs /d, z/"),
        text=(
            "Ruth thinks those three thick paths lead to the harbor, "
            "though they breathe better in the northern weather on Thursday."
        ),
    ),
    DiagnosticPassage(
        id="labiodental_glide",
        title="Labiodental vs. Glide (/v/ & /w/)",
        subtitle="Contrasts upper-teeth lower-lip contact (/v/) against rounded bilabial glide (/w/)",
        focus_categories=("labiodental_glide",),
        target_contrasts=("/v/ vs /w/",),
        text=(
            "Phil drives a silver van over wet waves, "
            "while five visitors watch warm water swirl past the west harbor."
        ),
    ),
    DiagnosticPassage(
        id="liquid_contrast",
        title="Liquid Contrast (/r/ & /l/)",
        subtitle="Contrasts retroflex/bunched /r/ against lateral /l/ in onsets, clusters, and codas",
        focus_categories=("liquid_contrast",),
        target_contrasts=("/r, ɹ̩/ vs /l, l̩/",),
        text=(
            "Right by the light, Ruth rolls red apples across fresh grass "
            "while Phil smiles and lifts a small silver glass."
        ),
    ),
    DiagnosticPassage(
        id="final_clusters",
        title="Final Consonants & Clusters",
        subtitle="Checks word-final stops and obstruent clusters against deletion or vowel epenthesis",
        focus_categories=("final_clusters",),
        target_contrasts=("Coda stops", "Final -ks / -ts / -st / -θs"),
        text=(
            "Phil grabs six crates, checks five desks and wet masks, "
            "and walks past the slick paths before work."
        ),
    ),
    DiagnosticPassage(
        id="vowel_pairs",
        title="Tense/Lax & Front Vowel Pairs",
        subtitle="Minimal pairs testing /ɪ/ vs /iː/ (ship/sheep) and /æ/ vs /ɛ/ (bat/bet)",
        focus_categories=("vowel_pairs",),
        target_contrasts=("/ɪ/ vs /iː/", "/æ/ vs /ɛ/"),
        text=(
            "They bet a small bat can reach the big ship before the sheep cross; "
            "please sit in this seat and let the bad bed rest."
        ),
    ),
)


def list_diagnostic_passages() -> list[dict[str, Any]]:
    """Return JSON-serializable list of curated diagnostic passages."""
    items: list[dict[str, Any]] = []
    for passage in DIAGNOSTIC_PASSAGES:
        data = asdict(passage)
        data["focus_categories"] = list(passage.focus_categories)
        data["target_contrasts"] = list(passage.target_contrasts)
        items.append(data)
    return items


def get_diagnostic_passage(passage_id: str) -> DiagnosticPassage | None:
    for passage in DIAGNOSTIC_PASSAGES:
        if passage.id == passage_id:
            return passage
    return None
