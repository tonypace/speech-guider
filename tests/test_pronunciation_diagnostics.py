"""Tests for 6-category pronunciation diagnostics, diagnostic passages API, and analyze wiring."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import parselmouth
import torch
from fastapi.testclient import TestClient

from app.main import app
from src.models.alignment import (
    AlignmentResult,
    PhonemeAlignment,
    SentenceAlignment,
    WordAlignment,
)
from src.models.pronunciation_diagnostics import evaluate_pronunciation_diagnostics


def _make_vowel_sound(
    f1_hz: float = 550.0, f2_hz: float = 1750.0, duration_s: float = 0.4
) -> parselmouth.Sound:
    sr = 16000
    t = np.linspace(0.0, duration_s, int(sr * duration_s), endpoint=False)
    wave = 0.3 * np.sin(2 * np.pi * f1_hz * t) + 0.2 * np.sin(2 * np.pi * f2_hz * t)
    return parselmouth.Sound(wave, sampling_frequency=sr)


def test_six_category_diagnostics_flags_each_weakness_neutrally() -> None:
    ipa_map = (
        json.loads(Path("external/mhubert-147/ipa_map.json").read_text(encoding="utf-8"))[
            "phone2id"
        ]
        if Path("external/mhubert-147/ipa_map.json").is_file()
        else {
            "sil": 0,
            "b": 3,
            "d": 4,
            "f": 7,
            "i": 10,
            "k": 12,
            "l": 13,
            "p": 20,
            "r": 21,
            "s": 22,
            "t": 23,
            "v": 26,
            "w": 27,
            "z": 28,
            "æ": 29,
            "ð": 30,
            "ɛ": 36,
            "ɪ": 37,
            "ɹ̩": 38,
            "l̩": 14,
            "θ": 44,
        }
    )
    blank_id = 45
    n_frames = 60
    log_probs = np.full((n_frames, 46), -6.0, dtype=np.float32)
    log_probs[:, blank_id] = -2.0

    # Construct 6 aligned words spanning frames [0..60]
    words = [
        WordAlignment(
            "thick",
            0.00,
            0.16,
            [
                PhonemeAlignment("θ", 0.00, 0.08, -2.5, True, "s", False, False),
                PhonemeAlignment("ɪ", 0.08, 0.16, -1.8, True, "i", True, True),
            ],
        ),
        WordAlignment(
            "they",
            0.16,
            0.30,
            [
                PhonemeAlignment("ð", 0.16, 0.24, -2.2, True, "d", False, True),
                PhonemeAlignment("eɪ", 0.24, 0.30, 0.0, False, "eɪ", True, True),
            ],
        ),
        WordAlignment(
            "van",
            0.30,
            0.46,
            [
                PhonemeAlignment("v", 0.30, 0.40, -2.0, True, "w", False, True),
                PhonemeAlignment("æ", 0.40, 0.46, 0.0, False, "æ", True, True),
            ],
        ),
        WordAlignment(
            "red",
            0.46,
            0.62,
            [
                PhonemeAlignment("r", 0.46, 0.56, -2.1, True, "l", False, True),
                PhonemeAlignment("ɛ", 0.56, 0.62, 0.0, False, "ɛ", True, True),
            ],
        ),
        WordAlignment(
            "work",
            0.62,
            0.80,
            [
                PhonemeAlignment("w", 0.62, 0.70, 0.0, False, "w", False, True),
                PhonemeAlignment("k", 0.70, 0.80, -3.0, True, "<blank>", False, False),
            ],
        ),
        WordAlignment(
            "ship",
            0.80,
            1.00,
            [
                PhonemeAlignment("ɪ", 0.80, 0.96, -2.0, True, "i", True, True),
                PhonemeAlignment("p", 0.96, 1.00, 0.0, False, "p", False, False),
            ],
        ),
    ]

    # Set competing posteriors in each window
    log_probs[0:4, ipa_map["s"]] = -0.1
    log_probs[4:8, ipa_map["i"]] = -0.1
    log_probs[8:12, ipa_map["d"]] = -0.1
    log_probs[15:20, ipa_map["w"]] = -0.1
    log_probs[23:28, ipa_map["l"]] = -0.1
    # Final /k/ blank-dominated
    log_probs[35:40, blank_id] = -0.05
    log_probs[35:40, ipa_map["k"]] = -5.0
    # "ship" /ɪ/ shifted to /i/
    log_probs[40:48, ipa_map["i"]] = -0.1
    # "ship" /p/ clear
    log_probs[48:50, ipa_map["p"]] = -0.1

    ar = AlignmentResult(
        errors=[],
        alignment=SentenceAlignment(
            text="thick they van red work ship", words=words, total_duration=1.0, overall_score=-1.5
        ),
        log_probs=log_probs,
        ipa_to_id=ipa_map,
        id_to_ipa={v: k for k, v in ipa_map.items()},
    )
    sound = _make_vowel_sound(duration_s=1.05)
    tvs_11 = np.full((52, 11), 0.4, dtype=np.float32)

    diag, errs = evaluate_pronunciation_diagnostics(
        ar,
        praat_sound=sound,
        tvs_11ch=tvs_11,
    )
    assert diag["status"] == "available"
    assert len(diag["categories"]) == 6
    by_id = {c["id"]: c for c in diag["categories"]}
    for cid in (
        "voiceless_dental",
        "voiced_dental",
        "labiodental_glide",
        "liquid_contrast",
        "final_clusters",
        "vowel_pairs",
    ):
        assert by_id[cid]["flagged_count"] >= 1
        assert by_id[cid]["status"] in {"watch", "needs_focus"}
    # Ensure vowel acoustics (duration + F1/F2) and neutral wording are present
    vowel_item = by_id["vowel_pairs"]["flagged_words"][0]
    assert vowel_item["acoustics"]["duration_ms"] > 0
    assert "clinical" in diag["disclaimer"].lower()
    assert all("animation_left" in err for err in errs)


def test_diagnostic_passages_endpoint() -> None:
    client = TestClient(app)
    resp = client.get("/api/diagnostic-passages")
    assert resp.status_code == 200
    passages = resp.json()["passages"]
    assert len(passages) == 6
    assert passages[0]["id"] == "full_diagnostic"
    assert "Thursday" in passages[0]["text"]


def test_analyze_endpoint_wires_aligned_prosody_and_graceful_fallback(
    dummy_wav_factory: Callable[..., Path],
) -> None:
    client = TestClient(app)
    wav_path = dummy_wav_factory(duration=1.0, frequency=220.0)

    fake_ssl_predictor = MagicMock()
    fake_ssl_predictor.device = "cpu"
    fake_ssl_predictor.predict_with_metadata.return_value = {
        "tvs": torch.full((50, 9), 0.5),
        "tvs_raw": torch.full((50, 9), 0.5),
        "labiodental_retraction": torch.zeros(50),
        "metadata": {"model_version": "r5", "device": "cpu"},
    }

    fake_ipa_to_id = {"b": 3, "æ": 29, "t": 23, "ɛ": 36, "sil": 0}
    fake_lp = np.full((50, 46), -5.0, dtype=np.float32)
    fake_lp[:, 45] = -1.0
    fake_lp[5:15, 29] = -0.1
    fake_lp[25:35, 36] = -0.1
    fake_alignment = AlignmentResult(
        errors=[],
        alignment=SentenceAlignment(
            text="bat bet",
            words=[
                WordAlignment(
                    "bat",
                    0.04,
                    0.36,
                    [
                        PhonemeAlignment("b", 0.04, 0.12, 0.0, False, "b", False, True),
                        PhonemeAlignment("æ", 0.12, 0.30, 0.0, False, "æ", True, True),
                        PhonemeAlignment("t", 0.30, 0.36, 0.0, False, "t", False, False),
                    ],
                ),
                WordAlignment(
                    "bet",
                    0.40,
                    0.74,
                    [
                        PhonemeAlignment("b", 0.40, 0.50, 0.0, False, "b", False, True),
                        PhonemeAlignment("ɛ", 0.50, 0.68, 0.0, False, "ɛ", True, True),
                        PhonemeAlignment("t", 0.68, 0.74, 0.0, False, "t", False, False),
                    ],
                ),
            ],
            total_duration=1.0,
            overall_score=0.0,
        ),
        log_probs=fake_lp,
        ipa_to_id=fake_ipa_to_id,
        id_to_ipa={v: k for k, v in fake_ipa_to_id.items()},
    )
    fake_aligner = MagicMock()
    fake_aligner.align_with_posteriors.return_value = fake_alignment

    with (
        patch("app.api.analyze.get_ssl_predictor", return_value=fake_ssl_predictor),
        patch("app.api.analyze.get_forced_aligner", return_value=fake_aligner),
    ):
        with wav_path.open("rb") as f:
            resp = client.post(
                "/api/analyze",
                files={"audio": ("test.wav", f, "audio/wav")},
                data={"target_text": "bat bet"},
            )
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["alignment_meta"]["status"] == "available"
        assert payload["pronunciation_diagnostics"]["status"] == "available"
        assert payload["prosody"]["stress_pattern"] in {"bat", "bet"}
        assert payload["prosody"]["npvi"] is not None

    # Now verify graceful fallback when mHuBERT assets are missing
    with (
        patch("app.api.analyze.get_ssl_predictor", return_value=fake_ssl_predictor),
        patch("app.api.analyze.get_forced_aligner", side_effect=FileNotFoundError("not staged")),
    ):
        with wav_path.open("rb") as f:
            resp_fallback = client.post(
                "/api/analyze",
                files={"audio": ("test.wav", f, "audio/wav")},
                data={"target_text": "bat bet"},
            )
        assert resp_fallback.status_code == 200
        fb = resp_fallback.json()
        assert fb["success"] is True
        assert fb["pronunciation_diagnostics"]["status"] == "unavailable"
        assert fb["alignment"] is None


def test_weakness_summary_syllable_severity_and_skips_not_reached() -> None:
    from src.models.alignment import (
        AlignmentResult,
        PhonemeAlignment,
        SentenceAlignment,
        SyllableAlignment,
        WordAlignment,
    )
    from src.models.pronunciation_diagnostics import evaluate_pronunciation_diagnostics

    ipa_to_id = {
        "θ": 42,
        "s": 21,
        "ɜ": 34,
        "d": 6,
        "eɪ": 30,
        "ɪ": 37,
        "iː": 38,
        "ʃ": 41,
        "p": 18,
        "sil": 0,
    }
    lp = np.full((50, 46), -5.0, dtype=np.float32)
    lp[:, 45] = -1.0
    # Make θ weak and s strong in frames 2..8
    lp[2:8, 42] = -4.0
    lp[2:8, 21] = -0.1

    sent = SentenceAlignment(
        text="Thursday unread",
        words=[
            WordAlignment(
                word="Thursday",
                start_time=0.04,
                end_time=0.40,
                phonemes=[
                    PhonemeAlignment("θ", 0.04, 0.16, -4.0, True, "s", False, False),
                    PhonemeAlignment("ɜ", 0.16, 0.24, -0.2, False, "ɜ", True, True),
                    PhonemeAlignment("d", 0.24, 0.30, -0.2, False, "d", False, False),
                    PhonemeAlignment("eɪ", 0.30, 0.40, -0.2, False, "eɪ", True, True),
                ],
                not_reached=False,
                syllables=[
                    SyllableAlignment(0, ["θ", "ɜ"], ["s", "ɜ"], 0.04, 0.24, -2.1, "clear"),
                    SyllableAlignment(1, ["d", "eɪ"], ["d", "eɪ"], 0.24, 0.40, -0.2, "clear"),
                ],
            ),
            WordAlignment(
                word="unread",
                start_time=0.0,
                end_time=0.0,
                phonemes=[PhonemeAlignment("θ", 0.0, 0.0, 0.0, False, None, False, False)],
                not_reached=True,
                syllables=[],
            ),
        ],
        total_duration=1.0,
        overall_score=-1.0,
    )
    alignment_res = AlignmentResult(
        errors=[],
        alignment=sent,
        log_probs=lp,
        ipa_to_id=ipa_to_id,
        id_to_ipa={v: k for k, v in ipa_to_id.items()},
    )

    out, _enriched = evaluate_pronunciation_diagnostics(alignment_res)
    assert out["status"] == "available"
    assert len(out["weakness_summary"]) >= 1
    first = out["weakness_summary"][0]
    assert first["drill_passage_id"] == "dental_fricatives"
    assert first["sample_word"]["word"] == "Thursday"
    # Syllable severity should be updated from clear -> red/yellow
    assert sent.words[0].syllables[0].severity in {"red", "yellow"}
    assert sent.words[0].syllables[1].severity == "clear"
    # Unread word should not appear in flagged words
    flagged_words = [fw["word"] for cat in out["categories"] for fw in cat["flagged_words"]]
    assert "unread" not in flagged_words
