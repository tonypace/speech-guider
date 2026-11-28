"""Tests for offline G2P, CTCHeadModel, Viterbi forced aligner, and mHuBERT integration."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import soundfile as sf
import torch

from src.models.alignment import ForcedAligner, viterbi_ctc_align
from src.models.diagnostic_passages import DIAGNOSTIC_PASSAGES
from src.models.g2p import CTC_V1_PHONES, OfflineEnglishG2P
from src.models.ipa_ctc_head import CTCHeadModel
from src.models.mhubert_encoder import DEFAULT_MHUBERT_BUNDLE

HAS_MHUBERT = (DEFAULT_MHUBERT_BUNDLE / "ctc_v1" / "pytorch_model.bin").is_file() and (
    (DEFAULT_MHUBERT_BUNDLE / "encoder" / "model.safetensors").is_file()
    or (DEFAULT_MHUBERT_BUNDLE / "encoder" / "pytorch_model.bin").is_file()
)


def test_offline_g2p_covers_all_diagnostic_passages_and_oov() -> None:
    g2p = OfflineEnglishG2P(
        cmudict_path=DEFAULT_MHUBERT_BUNDLE / "cmudict_ipa.json"
        if (DEFAULT_MHUBERT_BUNDLE / "cmudict_ipa.json").is_file()
        else None
    )
    for passage in DIAGNOSTIC_PASSAGES:
        words = g2p.text_to_words(passage.text)
        assert len(words) > 5
        for wp in words:
            assert wp.phonemes, f"Empty phonemes for {wp.word}"
            for phone in wp.phonemes:
                assert phone in CTC_V1_PHONES, f"Invalid ctc_v1 phone {phone!r} in {wp.word}"

    # Verify OOV fallback produces valid ctc_v1 phones
    oov = g2p.text_to_words("blorgthwacking zyxophone")
    assert len(oov) == 2
    assert all(p in CTC_V1_PHONES for wp in oov for p in wp.phonemes)


def test_ctc_head_model_forward_shape() -> None:
    model = CTCHeadModel()
    model.eval()
    emb = torch.randn(25, 768)
    out = model(emb)
    assert out.shape == (1, 25, 46)


def test_viterbi_ctc_align_monotonic_boundaries_and_gop_monotonicity() -> None:
    ipa_to_id = {"b": 3, "æ": 29, "t": 23, "θ": 44, "s": 22, "sil": 0}
    id_to_ipa = {v: k for k, v in ipa_to_id.items()}
    blank_id = 45

    class _FakeEncoder:
        def extract_features(
            self, audio_tensor: torch.Tensor, sample_rate: int = 16000
        ) -> torch.Tensor:
            del sample_rate
            n_frames = max(1, int(audio_tensor.numel() // 320))
            return torch.zeros((n_frames, 768), dtype=torch.float32)

    class _FakeHead:
        def __init__(self, log_probs: np.ndarray) -> None:
            self._lp = log_probs
            self.ipa_to_id = ipa_to_id
            self.id_to_ipa = id_to_ipa
            self.blank_id = blank_id

        def predict_log_probs(self, hidden_states: torch.Tensor) -> np.ndarray:
            del hidden_states
            return self._lp

    # 30 frames (0.60 s): "bat" -> b [2..8], æ [10..18], t [20..26]
    lp_clean = np.full((30, 46), -6.0, dtype=np.float32)
    lp_clean[:, blank_id] = -0.5
    lp_clean[2:8, 3] = -0.1  # b
    lp_clean[10:18, 29] = -0.1  # æ
    lp_clean[20:26, 23] = -0.1  # t

    spans = viterbi_ctc_align(lp_clean, [3, 29, 23], blank_id=blank_id)
    assert len(spans) == 3
    assert spans[0][0] < spans[0][1] <= spans[1][0] < spans[1][1] <= spans[2][0] < spans[2][1]
    assert spans[0][0] >= 2 and spans[1][0] >= 10 and spans[2][0] >= 20

    aligner_clean = ForcedAligner(
        encoder=_FakeEncoder(),
        ctc_head=_FakeHead(lp_clean),
        g2p=OfflineEnglishG2P(cmudict_path="/nonexistent/cmudict.json"),
    )
    audio = torch.zeros(30 * 320, dtype=torch.float32)
    errs_clean, sent_clean = aligner_clean.analyze_pronunciation(audio, "bat", 16000)
    assert errs_clean == []
    assert len(sent_clean.words) == 1
    assert sent_clean.overall_score == pytest.approx(0.0, abs=1e-4)

    # Substitution case: target "b æ t", spoken with "ɛ" instead of "æ" in middle
    lp_sub = lp_clean.copy()
    lp_sub[10:18, 29] = -4.5  # weak æ
    lp_sub[10:18, 0] = -5.0
    # Add ɛ at id 36
    ipa_to_id_sub = {**ipa_to_id, "ɛ": 36}
    id_to_ipa_sub = {**id_to_ipa, 36: "ɛ"}
    lp_sub[10:18, 36] = -0.1

    head_sub = _FakeHead(lp_sub)
    head_sub.ipa_to_id = ipa_to_id_sub
    head_sub.id_to_ipa = id_to_ipa_sub
    aligner_sub = ForcedAligner(
        encoder=_FakeEncoder(),
        ctc_head=head_sub,
        g2p=OfflineEnglishG2P(cmudict_path="/nonexistent/cmudict.json"),
    )
    errs_sub, sent_sub = aligner_sub.analyze_pronunciation(audio, "bat", 16000)
    assert sent_sub.overall_score < sent_clean.overall_score
    assert len(errs_sub) == 1
    assert errs_sub[0].target_phoneme == "æ"
    assert errs_sub[0].predicted_phoneme == "ɛ"


@pytest.mark.skipif(not HAS_MHUBERT, reason="mHuBERT-147 + ctc_v1 assets not staged")
def test_real_mhubert_forced_alignment_on_speech_fixture() -> None:
    wav_path = Path("external/R5_CoreML_Export_v1/fixtures/ffes0_001_val/audio.wav")
    if not wav_path.is_file():
        pytest.skip("Fixture audio not found")
    audio, sr = sf.read(wav_path, dtype="float32")
    aligner = ForcedAligner(bundle_path=DEFAULT_MHUBERT_BUNDLE)
    aligner.load()
    try:
        res = aligner.align_with_posteriors(torch.from_numpy(audio), "she had your dark suit", sr)
        assert res.log_probs.ndim == 2 and res.log_probs.shape[1] == 46
        assert len(res.alignment.words) == 5
        prev_end = 0.0
        for w in res.alignment.words:
            assert w.start_time >= prev_end - 1e-6
            assert w.end_time > w.start_time
            prev_end = w.end_time
    finally:
        aligner.cleanup()


def test_partial_unfinished_alignment_marks_trailing_words_not_reached_and_syllables() -> None:
    # Target has 2 words ("bat kip" -> b æ t | k ɪ p), but audio only speaks "bat"
    # followed by silence. Prefix CTC alignment should mark "kip" as not_reached.
    blank_id = 45
    ipa_to_id = {"sil": 0, "b": 3, "k": 12, "p": 18, "t": 23, "æ": 29, "ɪ": 37}
    id_to_ipa = {v: k for k, v in ipa_to_id.items()}

    num_frames = 40
    lp = np.full((num_frames, 46), -6.0, dtype=np.float32)
    lp[:, blank_id] = -0.3
    lp[2:8, 3] = -0.1  # b
    lp[9:16, 29] = -0.1  # æ
    lp[17:22, 23] = -0.1  # t
    lp[23:, 0] = -0.2  # trailing silence

    spans, reached = viterbi_ctc_align(
        lp,
        [3, 29, 23, 12, 37, 18],
        blank_id=blank_id,
        word_end_token_counts=[3, 6],
        allow_partial=True,
    )
    assert len(spans) == 6
    assert reached == 1

    class _FakeEncoder:
        def extract_features(
            self, audio_tensor: torch.Tensor, sample_rate: int = 16000
        ) -> torch.Tensor:
            del sample_rate
            return torch.zeros((max(1, int(audio_tensor.numel() // 320)), 768), dtype=torch.float32)

    class _FakeHead:
        def __init__(self, log_probs: np.ndarray) -> None:
            self._lp = log_probs
            self.ipa_to_id = ipa_to_id
            self.id_to_ipa = id_to_ipa
            self.blank_id = blank_id

        def predict_log_probs(self, hidden_states: torch.Tensor) -> np.ndarray:
            del hidden_states
            return self._lp

    aligner = ForcedAligner(
        encoder=_FakeEncoder(),
        ctc_head=_FakeHead(lp),
        g2p=OfflineEnglishG2P(cmudict_path="/nonexistent/cmudict.json"),
    )
    audio = torch.zeros(num_frames * 320, dtype=torch.float32)
    res = aligner.align_with_posteriors(audio, "bat kip", 16000, allow_partial=True)
    assert len(res.alignment.words) == 2
    assert res.alignment.words[0].word == "bat"
    assert res.alignment.words[0].not_reached is False
    assert len(res.alignment.words[0].syllables) >= 1
    assert res.alignment.words[1].word == "kip"
    assert res.alignment.words[1].not_reached is True
    assert res.alignment.words[1].syllables == []


def test_mhubert_encoder_avoids_mps_and_falls_back_on_65536_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from types import SimpleNamespace

    from src.models.mhubert_encoder import MHuBERTEncoder

    monkeypatch.setattr("src.models.mhubert_encoder.get_best_torch_device", lambda: "mps")
    auto_enc = MHuBERTEncoder()
    assert auto_enc.device == "cpu"

    class _FakeTensor:
        def __init__(self, device: str = "cpu") -> None:
            self.device = device

        def to(self, device: str) -> _FakeTensor:
            return _FakeTensor(device)

    class _FakeExtractor:
        def __call__(
            self, samples: np.ndarray, sampling_rate: int = 16000, return_tensors: str = "pt"
        ) -> dict[str, _FakeTensor]:
            del samples, sampling_rate, return_tensors
            return {"input_values": _FakeTensor()}

    class _FakeModel:
        def __init__(self) -> None:
            self.moved_to: list[str] = []

        def to(self, device: str) -> _FakeModel:
            self.moved_to.append(device)
            return self

        def __call__(self, input_values: _FakeTensor) -> SimpleNamespace:
            if input_values.device == "mps":
                raise NotImplementedError("Output channels > 65536 not supported at the MPS device")
            return SimpleNamespace(last_hidden_state=torch.ones((1, 4, 768), dtype=torch.float32))

    explicit_enc = MHuBERTEncoder(device="mps")
    explicit_enc._loaded = True
    explicit_enc._feature_extractor = _FakeExtractor()
    explicit_enc._model = _FakeModel()

    hidden = explicit_enc.extract_features(torch.zeros(1600, dtype=torch.float32), 16000)
    assert hidden.shape == (4, 768)
    assert explicit_enc.device == "cpu"
    assert explicit_enc._model.moved_to == ["cpu"]
