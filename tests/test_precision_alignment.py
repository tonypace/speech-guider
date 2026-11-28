"""Test precision forced alignment with phoneme classification."""

import numpy as np
import torch

from src.models.alignment import ForcedAligner, _classify_phoneme
from src.models.g2p import CTC_V1_PHONES, OfflineEnglishG2P


def test_phoneme_classification():
    """Test that phonemes are correctly classified."""
    assert _classify_phoneme("i") == (True, True)
    assert _classify_phoneme("eɪ") == (True, True)
    assert _classify_phoneme("b") == (False, True)
    assert _classify_phoneme("p") == (False, False)
    assert _classify_phoneme("s") == (False, False)
    assert _classify_phoneme("ɬ") == (False, False)  # voiceless lateral fricative


def test_forced_alignment_basic() -> None:
    """Test basic forced alignment using offline stubs without downloaded weights."""
    sample_rate = 16_000
    duration_sec = 2.0
    t = np.linspace(0, duration_sec, int(sample_rate * duration_sec))
    audio_waveform = np.sin(2 * np.pi * 440 * t)
    audio_tensor = torch.from_numpy(audio_waveform).float()

    phones = sorted(CTC_V1_PHONES)
    blank_id = len(phones)
    ipa_to_id = {p: i for i, p in enumerate(phones)}
    id_to_ipa = {i: p for p, i in ipa_to_id.items()}

    class _StubEncoder:
        def extract_features(
            self, audio_tensor: torch.Tensor, sample_rate: int = 16000
        ) -> torch.Tensor:
            del sample_rate
            n_frames = max(1, int(audio_tensor.numel() // 320))
            return torch.zeros((n_frames, 768), dtype=torch.float32)

    class _StubHead:
        def __init__(self) -> None:
            self.ipa_to_id = ipa_to_id
            self.id_to_ipa = id_to_ipa
            self.blank_id = blank_id

        def predict_log_probs(self, hidden_states: torch.Tensor) -> np.ndarray:
            n_frames = int(hidden_states.shape[0])
            lp = np.full((n_frames, blank_id + 1), -4.0, dtype=np.float32)
            lp[:, blank_id] = -0.2
            return lp

    aligner = ForcedAligner(
        encoder=_StubEncoder(),
        ctc_head=_StubHead(),
        g2p=OfflineEnglishG2P(cmudict_path="/nonexistent/cmudict.json"),
    )
    _errors, alignment = aligner.analyze_pronunciation(audio_tensor, "hello world")

    assert alignment is not None
    assert alignment.total_duration == duration_sec


if __name__ == "__main__":
    test_phoneme_classification()
    test_forced_alignment_basic()
    print("\n✅ All precision alignment tests passed!")
