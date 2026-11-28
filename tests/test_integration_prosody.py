"""Integration test for prosody analysis in the application."""

from collections.abc import Callable
from pathlib import Path

import numpy as np
import pytest
import torch

from src.audio import AudioContext, ProsodyAnalyzer
from src.models.alignment import ForcedAligner
from src.models.g2p import CTC_V1_PHONES, OfflineEnglishG2P


def test_prosody_extraction_from_audio(dummy_wav_factory: Callable[..., Path]) -> None:
    """Test prosody metrics can be extracted from real audio."""
    wav_path = dummy_wav_factory(duration=2.0, frequency=200.0, modulated=True)

    audio_context = AudioContext(str(wav_path))
    prosody_analyzer = ProsodyAnalyzer(audio_context)

    prosody = prosody_analyzer.analyze_complete(vowel_timestamps=[], word_timestamps=[])

    assert prosody is not None
    assert hasattr(prosody, "pitch")
    assert hasattr(prosody, "rhythm")
    assert hasattr(prosody, "stress")
    assert prosody.pitch is not None
    assert prosody.pitch.f0_range >= 0.0
    assert len(prosody.pitch.f0_values) > 0


def test_forced_aligner_placeholder() -> None:
    """Test forced aligner returns alignment results using offline stubs without downloaded weights."""
    audio_tensor = torch.linspace(0.0, 2.0, int(16_000 * 2.0))
    waveform = torch.sin(2 * torch.pi * 440 * audio_tensor).float()

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
    _errors, alignment = aligner.analyze_pronunciation(waveform, "the weather is hot")

    assert alignment is not None
    assert alignment.total_duration == 2.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
