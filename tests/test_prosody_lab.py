"""Tests for Prosody Lab analysis helpers and hybrid acoustic P-center syllable detection."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import numpy as np
from fastapi.testclient import TestClient
from numpy.typing import NDArray
from scipy.signal import butter, sosfiltfilt

from app.main import app
from src.audio.prosody_lab import (
    analyze_prosody_recording,
    detect_syllables_and_pcenters,
    generate_prosody_reference,
    syllabify_english_text,
)


def _synthesize_test_utterance(
    sr: int,
    vowel_specs: list[tuple[float, float, float]],
    sibilant_bursts: list[tuple[float, float]] | None = None,
) -> NDArray[np.int16]:
    """Build multi-syllable voiced waveform with optional unvoiced sibilant bursts."""
    total_dur = max(t + d for t, d, _ in vowel_specs) + 0.35
    n_samples = int(round(total_dur * sr))
    y = np.zeros(n_samples, dtype=np.float64)
    rng = np.random.default_rng(42)

    for start_t, dur_t, f0 in vowel_specs:
        s_idx = int(round(start_t * sr))
        n_v = int(round(dur_t * sr))
        t_vec = np.arange(n_v, dtype=np.float64) / sr
        sig = np.zeros(n_v, dtype=np.float64)
        for h in range(1, 16):
            if h * f0 >= 3200.0:
                break
            sig += (1.0 / (h**0.65)) * np.sin(2.0 * np.pi * h * f0 * t_vec)
        sos = butter(3, [450.0 / (0.5 * sr), 2200.0 / (0.5 * sr)], btype="bandpass", output="sos")
        sig = sosfiltfilt(sos, sig)
        sig /= max(float(np.max(np.abs(sig))), 1e-6)
        env = np.ones(n_v, dtype=np.float64)
        atk = min(int(0.018 * sr), n_v // 3)
        rel = min(int(0.025 * sr), n_v // 3)
        if atk > 1:
            env[:atk] = 0.5 * (1.0 - np.cos(np.pi * np.arange(atk) / atk))
        if rel > 1:
            env[-rel:] = 0.5 * (1.0 + np.cos(np.pi * np.arange(rel) / rel))
        y[s_idx : s_idx + n_v] += 0.65 * sig * env

    for b_start, b_dur in sibilant_bursts or []:
        b_idx = int(round(b_start * sr))
        n_b = int(round(b_dur * sr))
        noise = rng.standard_normal(n_b)
        sos_s = butter(
            4, [4200.0 / (0.5 * sr), 7500.0 / (0.5 * sr)], btype="bandpass", output="sos"
        )
        sib = sosfiltfilt(sos_s, noise)
        sib /= max(float(np.max(np.abs(sib))), 1e-6)
        y[b_idx : b_idx + n_b] += 0.55 * sib

    y = np.clip(y, -0.98, 0.98)
    return (y * 32767.0).astype(np.int16)


def test_analyze_prosody_recording_returns_summary(
    dummy_wav_factory: Callable[..., Path],
    create_dummy_wav: Callable[..., tuple[int, NDArray[np.int16]]],
) -> None:
    sample_rate = 44100
    _, tone = create_dummy_wav(
        duration=0.4, sample_rate=sample_rate, frequency=220.0, amplitude=0.4
    )
    silence = np.zeros(int(sample_rate * 0.2), dtype=np.int16)
    audio_path = dummy_wav_factory(
        "sample.wav",
        sample_rate=sample_rate,
        waveform=np.concatenate([tone, silence, tone]),
    )

    result = analyze_prosody_recording(str(audio_path))

    assert result["recording_id"]
    assert result["analysis_source"] == "heuristic"
    assert result["summary"]["syllable_count"] == 2
    assert result["summary"]["pause_count"] > 0
    assert result["summary"]["rhythm_balance"] > 0
    assert result["summary"]["mean_f0_hz"] > 0
    assert result["summary"]["speech_rate"] is not None
    assert result["summary"]["articulation_rate"] is not None
    assert result["summary"]["npvi"] is not None
    assert len(result["pitch_track"]) > 0
    assert isinstance(result["syllable_onsets"], list)
    assert len(result["syllable_p_centers"]) == 2
    assert len(result["syllable_details"]) == 2


def test_hybrid_pcenter_detector_ignores_unvoiced_sibilant_bursts(
    dummy_wav_factory: Callable[..., Path],
) -> None:
    sample_rate = 22050
    waveform = _synthesize_test_utterance(
        sample_rate,
        vowel_specs=[
            (0.22, 0.18, 130.0),
            (0.55, 0.06, 118.0),
            (0.76, 0.21, 145.0),
            (1.15, 0.19, 135.0),
        ],
        sibilant_bursts=[
            (0.14, 0.08),
            (0.68, 0.08),
            (1.06, 0.09),
            (1.38, 0.09),
        ],
    )
    audio_path = dummy_wav_factory(
        "sibilant_phrase.wav", sample_rate=sample_rate, waveform=waveform
    )

    result = analyze_prosody_recording(str(audio_path))

    assert result["summary"]["syllable_count"] == 4
    assert len(result["syllable_details"]) == 4
    # First syllable has a pre-beat sibilant burst at 0.12s before vowel at 0.22s
    first_detail = result["syllable_details"][0]
    assert 0.20 <= first_detail["p_center_time"] <= 0.25
    assert first_detail["pre_duration"] > 0.02


def test_detect_syllables_and_pcenters_handles_empty_input() -> None:
    empty = detect_syllables_and_pcenters(np.array([], dtype=np.float32), 22050)
    assert empty["nuclei_times"] == []
    assert empty["p_center_times"] == []
    assert empty["syllable_details"] == []


def test_syllabify_english_text_splits_words_and_marks_function_words() -> None:
    items = syllabify_english_text("We need to focus on the core... problems first.")
    texts = [item["text"] for item in items]
    assert texts == [
        "We",
        "need",
        "to",
        "fo-",
        "cus",
        "on",
        "the",
        "core...",
        "prob-",
        "lems",
        "first",
    ]
    assert items[0]["is_function_word"] is True
    assert items[1]["is_function_word"] is False
    assert items[3]["pre"] == "f"
    assert items[3]["vowel"] == "o"
    assert items[7]["has_pause_after"] is True
    assert items[-1]["has_pause_after"] is True


def test_generate_prosody_reference_uses_synthetic_fallback_and_builds_phrase(
    monkeypatch: object,
) -> None:
    import os

    monkeypatch.delenv("OMNIVOICE_TTS_PATH", raising=False)  # type: ignore[attr-defined]
    os.environ.pop("OMNIVOICE_TTS_PATH", None)

    result = generate_prosody_reference("We need to focus on the core... problems first")
    assert result["synthesis_source"] == "synthetic_fallback"
    assert result["mime_type"] == "audio/wav"
    assert len(result["audio_base64"]) > 100
    phrase = result["phrase"]
    assert phrase["id"] == "custom"
    assert phrase["bpm"] == 88
    assert phrase["pauseGate"] is not None
    assert len(phrase["feet"]) >= 2
    assert len(phrase["syllables"]) == 11
    for idx, syl in enumerate(phrase["syllables"]):
        assert syl["index"] == idx
        assert "beat" in syl
        assert "dur" in syl
        assert "pre" in syl
        assert "vowel" in syl
        assert "isGhost" in syl
        assert "isFinal" in syl


def test_prosody_lab_reference_endpoint_returns_custom_phrase(
    monkeypatch: object,
) -> None:
    monkeypatch.delenv("OMNIVOICE_TTS_PATH", raising=False)  # type: ignore[attr-defined]
    client = TestClient(app)
    response = client.post(
        "/api/prosody-lab/reference",
        json={"target_text": "I said fifteen percent, not fifty."},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["target_text"] == "I said fifteen percent, not fifty."
    assert payload["synthesis_source"] in {"omnivoice", "synthetic_fallback"}
    assert payload["phrase"]["id"] == "custom"
    assert len(payload["phrase"]["syllables"]) == 9
    assert payload["analysis"]["summary"]["syllable_count"] >= 1
