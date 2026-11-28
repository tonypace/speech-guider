"""Pure-Python offline English G2P mapping words to the 45-phone ctc_v1 IPA set."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from src.models.mhubert_encoder import DEFAULT_MHUBERT_BUNDLE

CTC_V1_PHONES: frozenset[str] = frozenset(
    {
        "sil",
        "aɪ",
        "aʊ",
        "b",
        "d",
        "dʒ",
        "eɪ",
        "f",
        "g",
        "h",
        "i",
        "j",
        "k",
        "l",
        "l̩",
        "m",
        "m̩",
        "n",
        "n̩",
        "oʊ",
        "p",
        "r",
        "s",
        "t",
        "tʃ",
        "u",
        "v",
        "w",
        "z",
        "æ",
        "ð",
        "ŋ",
        "ɑ",
        "ɔ",
        "ɔɪ",
        "ə",
        "ɛ",
        "ɪ",
        "ɹ̩",
        "ɾ",
        "ʃ",
        "ʊ",
        "ʒ",
        "ʔ",
        "θ",
    }
)

# Built-in offline lexicon covering curated diagnostic passages and frequent function words.
_BUILTIN_LEXICON: dict[str, list[list[str]]] = {
    "a": [["ə"], ["eɪ"]],
    "and": [["æ", "n", "d"], ["ə", "n", "d"]],
    "apples": [["æ", "p", "ə", "l", "z"], ["æ", "p", "l̩", "z"]],
    "at": [["æ", "t"]],
    "bad": [["b", "æ", "d"]],
    "bat": [["b", "æ", "t"]],
    "beat": [["b", "i", "t"]],
    "bed": [["b", "ɛ", "d"]],
    "before": [["b", "ɪ", "f", "ɔ", "r"]],
    "bet": [["b", "ɛ", "t"]],
    "big": [["b", "ɪ", "g"]],
    "bit": [["b", "ɪ", "t"]],
    "both": [["b", "oʊ", "θ"]],
    "breathe": [["b", "r", "i", "ð"]],
    "busy": [["b", "ɪ", "z", "i"]],
    "can": [["k", "æ", "n"], ["k", "ə", "n"]],
    "checks": [["tʃ", "ɛ", "k", "s"]],
    "clown": [["k", "l", "aʊ", "n"]],
    "crates": [["k", "r", "eɪ", "t", "s"]],
    "cross": [["k", "r", "ɔ", "s"]],
    "crown": [["k", "r", "aʊ", "n"]],
    "desks": [["d", "ɛ", "s", "k", "s"]],
    "drive": [["d", "r", "aɪ", "v"]],
    "every": [["ɛ", "v", "ɹ̩", "i"], ["ɛ", "v", "r", "i"]],
    "facts": [["f", "æ", "k", "t", "s"]],
    "five": [["f", "aɪ", "v"]],
    "fog": [["f", "ɔ", "g"], ["f", "ɑ", "g"]],
    "fresh": [["f", "r", "ɛ", "ʃ"]],
    "fruit": [["f", "r", "u", "t"]],
    "glass": [["g", "l", "æ", "s"]],
    "grabs": [["g", "r", "æ", "b", "z"]],
    "grass": [["g", "r", "æ", "s"]],
    "harbor": [["h", "ɑ", "r", "b", "ɹ̩"]],
    "he": [["h", "i"]],
    "her": [["h", "ɹ̩"]],
    "hurry": [["h", "ɹ̩", "i"]],
    "if": [["ɪ", "f"]],
    "in": [["ɪ", "n"]],
    "is": [["ɪ", "z"]],
    "it": [["ɪ", "t"]],
    "leave": [["l", "i", "v"]],
    "led": [["l", "ɛ", "d"]],
    "light": [["l", "aɪ", "t"]],
    "live": [["l", "ɪ", "v"], ["l", "aɪ", "v"]],
    "loves": [["l", "ə", "v", "z"]],
    "making": [["m", "eɪ", "k", "ɪ", "ŋ"]],
    "man": [["m", "æ", "n"]],
    "market": [["m", "ɑ", "r", "k", "ə", "t"]],
    "masks": [["m", "æ", "s", "k", "s"]],
    "men": [["m", "ɛ", "n"]],
    "morning": [["m", "ɔ", "r", "n", "ɪ", "ŋ"]],
    "noon": [["n", "u", "n"]],
    "of": [["ə", "v"]],
    "on": [["ɑ", "n"], ["ɔ", "n"]],
    "over": [["oʊ", "v", "ɹ̩"]],
    "pan": [["p", "æ", "n"]],
    "past": [["p", "æ", "s", "t"]],
    "paths": [["p", "æ", "θ", "s"], ["p", "æ", "ð", "z"]],
    "peaches": [["p", "i", "tʃ", "ə", "z"]],
    "pen": [["p", "ɛ", "n"]],
    "phil": [["f", "ɪ", "l"]],
    "reach": [["r", "i", "tʃ"]],
    "red": [["r", "ɛ", "d"]],
    "right": [["r", "aɪ", "t"]],
    "rolls": [["r", "oʊ", "l", "z"]],
    "ruth": [["r", "u", "θ"]],
    "says": [["s", "ɛ", "z"]],
    "seat": [["s", "i", "t"]],
    "sheep": [["ʃ", "i", "p"]],
    "ship": [["ʃ", "ɪ", "p"]],
    "silver": [["s", "ɪ", "l", "v", "ɹ̩"]],
    "sit": [["s", "ɪ", "t"]],
    "six": [["s", "ɪ", "k", "s"]],
    "slick": [["s", "l", "ɪ", "k"]],
    "small": [["s", "m", "ɔ", "l"]],
    "smiles": [["s", "m", "aɪ", "l", "z"]],
    "so": [["s", "oʊ"]],
    "sweet": [["s", "w", "i", "t"]],
    "the": [["ð", "ə"], ["ð", "i"]],
    "their": [["ð", "ɛ", "r"]],
    "then": [["ð", "ɛ", "n"]],
    "they": [["ð", "eɪ"]],
    "they'll": [["ð", "eɪ", "l"]],
    "thick": [["θ", "ɪ", "k"]],
    "think": [["θ", "ɪ", "ŋ", "k"]],
    "those": [["ð", "oʊ", "z"]],
    "three": [["θ", "r", "i"]],
    "thursday": [["θ", "ɹ̩", "z", "d", "eɪ"]],
    "to": [["t", "u"], ["t", "ə"]],
    "trip": [["t", "r", "ɪ", "p"]],
    "van": [["v", "æ", "n"]],
    "very": [["v", "ɛ", "r", "i"]],
    "vest": [["v", "ɛ", "s", "t"]],
    "vine": [["v", "aɪ", "n"]],
    "walk": [["w", "ɔ", "k"], ["w", "ɑ", "k"]],
    "watch": [["w", "ɑ", "tʃ"], ["w", "ɔ", "tʃ"]],
    "water": [["w", "ɔ", "t", "ɹ̩"], ["w", "ɑ", "t", "ɹ̩"]],
    "wave": [["w", "eɪ", "v"]],
    "we": [["w", "i"]],
    "weather": [["w", "ɛ", "ð", "ɹ̩"]],
    "west": [["w", "ɛ", "s", "t"]],
    "wet": [["w", "ɛ", "t"]],
    "wine": [["w", "aɪ", "n"]],
    "with": [["w", "ɪ", "ð"], ["w", "ɪ", "θ"]],
    "work": [["w", "ɹ̩", "k"]],
}

_WORD_RE = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)?")

_OOV_MULTI_RULES: tuple[tuple[str, list[str]], ...] = (
    ("tion", ["ʃ", "ə", "n"]),
    ("sion", ["ʒ", "ə", "n"]),
    ("tch", ["tʃ"]),
    ("igh", ["aɪ"]),
    ("th", ["θ"]),
    ("sh", ["ʃ"]),
    ("ch", ["tʃ"]),
    ("ng", ["ŋ"]),
    ("ph", ["f"]),
    ("qu", ["k", "w"]),
    ("wh", ["w"]),
    ("ck", ["k"]),
    ("ee", ["i"]),
    ("ea", ["i"]),
    ("oo", ["u"]),
    ("ai", ["eɪ"]),
    ("ay", ["eɪ"]),
    ("oa", ["oʊ"]),
    ("ow", ["aʊ"]),
    ("ou", ["aʊ"]),
    ("oi", ["ɔɪ"]),
    ("oy", ["ɔɪ"]),
    ("er", ["ɹ̩"]),
    ("ir", ["ɹ̩"]),
    ("ur", ["ɹ̩"]),
    ("ar", ["ɑ", "r"]),
    ("or", ["ɔ", "r"]),
)

_OOV_SINGLE_RULES: dict[str, list[str]] = {
    "a": ["æ"],
    "b": ["b"],
    "c": ["k"],
    "d": ["d"],
    "e": ["ɛ"],
    "f": ["f"],
    "g": ["g"],
    "h": ["h"],
    "i": ["ɪ"],
    "j": ["dʒ"],
    "k": ["k"],
    "l": ["l"],
    "m": ["m"],
    "n": ["n"],
    "o": ["ɑ"],
    "p": ["p"],
    "q": ["k"],
    "r": ["r"],
    "s": ["s"],
    "t": ["t"],
    "u": ["ə"],
    "v": ["v"],
    "w": ["w"],
    "x": ["k", "s"],
    "y": ["j"],
    "z": ["z"],
}


@dataclass(frozen=True)
class WordPronunciation:
    """Word text paired with its canonical ctc_v1 IPA phoneme sequence."""

    word: str
    normalized: str
    phonemes: list[str]
    variants: list[list[str]]


def _oov_fallback(word: str) -> list[str]:
    """Deterministic rule-based English G2P fallback emitting only ctc_v1 phones."""
    clean = re.sub(r"[^a-z]", "", word.lower())
    if not clean:
        return []
    # Drop silent trailing 'e' on multi-syllable/CVC words (e.g., "cake")
    if len(clean) > 2 and clean.endswith("e") and clean[-2] not in "aeiouy":
        clean = clean[:-1]

    phones: list[str] = []
    idx = 0
    n = len(clean)
    while idx < n:
        matched = False
        for seq, out in _OOV_MULTI_RULES:
            if clean.startswith(seq, idx):
                phones.extend(out)
                idx += len(seq)
                matched = True
                break
        if matched:
            continue
        ch = clean[idx]
        # Skip immediate duplicate consonant letters (e.g., "tt", "ss", "ll")
        if idx + 1 < n and clean[idx + 1] == ch and ch not in "aeiou":
            idx += 1
            continue
        if ch == "c" and idx + 1 < n and clean[idx + 1] in "eiy":
            phones.append("s")
        elif ch == "y" and idx == n - 1 and n > 2:
            phones.append("i")
        elif ch in _OOV_SINGLE_RULES:
            phones.extend(_OOV_SINGLE_RULES[ch])
        idx += 1

    return [p for p in phones if p in CTC_V1_PHONES]


class OfflineEnglishG2P:
    """Offline English grapheme-to-phoneme converter targeting ctc_v1 IPA."""

    def __init__(self, cmudict_path: str | Path | None = None) -> None:
        default_path = DEFAULT_MHUBERT_BUNDLE / "cmudict_ipa.json"
        resolved = Path(cmudict_path).expanduser().resolve() if cmudict_path else default_path
        self._lexicon: dict[str, list[list[str]]] = {
            k: [list(v) for v in vs] for k, vs in _BUILTIN_LEXICON.items()
        }
        if resolved.is_file():
            loaded = json.loads(resolved.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                for word, variants in loaded.items():
                    if not isinstance(word, str) or not isinstance(variants, list):
                        continue
                    valid_variants = [
                        [str(p) for p in var if str(p) in CTC_V1_PHONES]
                        for var in variants
                        if isinstance(var, list)
                    ]
                    valid_variants = [v for v in valid_variants if v]
                    if valid_variants and word not in _BUILTIN_LEXICON:
                        self._lexicon[word.lower()] = valid_variants

    def lookup_word(self, word: str) -> list[list[str]]:
        norm = word.lower().strip("'")
        if not norm:
            return []
        if norm in self._lexicon:
            return [list(v) for v in self._lexicon[norm]]
        if norm.endswith("'s") and norm[:-2] in self._lexicon:
            base = self._lexicon[norm[:-2]][0]
            suffix = "z" if base[-1] in {"b", "d", "g", "v", "ð", "m", "n", "ŋ", "l", "r"} else "s"
            return [base + [suffix]]
        fallback = _oov_fallback(norm)
        return [fallback] if fallback else []

    def text_to_words(self, text: str) -> list[WordPronunciation]:
        words: list[WordPronunciation] = []
        for match in _WORD_RE.finditer(text):
            raw = match.group(0)
            norm = raw.lower()
            variants = self.lookup_word(norm)
            if not variants:
                continue
            words.append(
                WordPronunciation(
                    word=raw,
                    normalized=norm,
                    phonemes=list(variants[0]),
                    variants=variants,
                )
            )
        return words
