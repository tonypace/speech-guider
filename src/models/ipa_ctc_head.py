"""Safe PyTorch loader for istomin9192/mHuBERT-147-ipa-head (ctc_v1)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as functional

from src.models.mhubert_encoder import DEFAULT_MHUBERT_BUNDLE, verify_mhubert_checksums


class CTCHeadModel(nn.Module):
    """BiLSTM IPA CTC head matching `istomin9192/mHuBERT-147-ipa-head` `ctc_v1`."""

    def __init__(
        self,
        input_dim: int = 768,
        proj_dim: int = 256,
        lstm_hidden: int = 256,
        lstm_layers: int = 2,
        lstm_bidirectional: bool = True,
        dropout: float = 0.3,
        output_dim: int = 46,
        blank_id: int = 45,
    ) -> None:
        super().__init__()
        self.blank_id = int(blank_id)
        self.output_dim = int(output_dim)
        self.proj = nn.Linear(input_dim, proj_dim)
        self.lstm = nn.LSTM(
            proj_dim,
            lstm_hidden,
            num_layers=lstm_layers,
            bidirectional=lstm_bidirectional,
            batch_first=True,
            dropout=dropout if lstm_layers > 1 else 0.0,
        )
        self.drop = nn.Dropout(dropout)
        out_dim = lstm_hidden * (2 if lstm_bidirectional else 1)
        self.head = nn.Linear(out_dim, output_dim)

    def forward(self, embeddings: torch.Tensor) -> torch.Tensor:
        if embeddings.ndim == 2:
            embeddings = embeddings.unsqueeze(0)
        x = self.proj(embeddings)
        out, _ = self.lstm(x)
        return cast(torch.Tensor, self.head(self.drop(out)))


class IPACTCHead:
    """Loads `ctc_v1` weights safely (`weights_only=True`) and produces frame log-probs."""

    def __init__(
        self,
        bundle_path: str | Path | None = None,
        *,
        verify_checksums: bool = True,
    ) -> None:
        self.bundle_path = Path(bundle_path or DEFAULT_MHUBERT_BUNDLE).expanduser().resolve()
        self.verify_checksums = verify_checksums
        self.model: CTCHeadModel | None = None
        self.ipa_to_id: dict[str, int] = {}
        self.id_to_ipa: dict[int, str] = {}
        self.blank_id: int = 45

    def load(self) -> None:
        cfg_rel = "ctc_v1/config.json"
        weights_rel = "ctc_v1/pytorch_model.bin"
        ipa_rel = "ipa_map.json"
        for rel in (cfg_rel, weights_rel, ipa_rel):
            if not (self.bundle_path / rel).is_file():
                raise FileNotFoundError(
                    f"mHuBERT CTC head asset not found: {self.bundle_path / rel}"
                )
        if self.verify_checksums:
            verify_mhubert_checksums(self.bundle_path, (cfg_rel, weights_rel, ipa_rel))

        cfg: dict[str, Any] = json.loads((self.bundle_path / cfg_rel).read_text(encoding="utf-8"))
        arch = cfg.get("architecture", {})
        ipa_data = json.loads((self.bundle_path / ipa_rel).read_text(encoding="utf-8"))
        raw_p2i = ipa_data.get("phone2id", {})
        raw_i2p = ipa_data.get("id2phone", {})
        if not isinstance(raw_p2i, dict) or not isinstance(raw_i2p, dict):
            raise ValueError("Invalid ipa_map.json structure")

        ipa_to_id = {str(k): int(v) for k, v in raw_p2i.items()}
        id_to_ipa = {int(k): str(v) for k, v in raw_i2p.items()}
        blank_id = int(arch.get("blank_id", 45))
        output_dim = int(arch.get("output_dim", 46))
        if len(ipa_to_id) != 45 or blank_id != 45 or output_dim != 46:
            raise ValueError(
                f"Unexpected CTC vocab size: phones={len(ipa_to_id)}, output_dim={output_dim}, blank={blank_id}"
            )

        model = CTCHeadModel(
            input_dim=int(arch.get("input_dim", 768)),
            proj_dim=int(arch.get("proj_dim", 256)),
            lstm_hidden=int(arch.get("lstm_hidden", 256)),
            lstm_layers=int(arch.get("lstm_layers", 2)),
            lstm_bidirectional=bool(arch.get("lstm_bidirectional", True)),
            dropout=float(arch.get("dropout", 0.3)),
            output_dim=output_dim,
            blank_id=blank_id,
        )
        state_dict = torch.load(
            self.bundle_path / weights_rel, map_location="cpu", weights_only=True
        )
        model.load_state_dict(state_dict, strict=True)
        model.eval()

        self.model = model
        self.ipa_to_id = ipa_to_id
        self.id_to_ipa = id_to_ipa
        self.blank_id = blank_id

    def predict_log_probs(self, hidden_states: torch.Tensor) -> np.ndarray:
        """Return `(T, 46)` float32 log-softmax probabilities over IPA classes + blank."""
        if self.model is None:
            raise RuntimeError("IPACTCHead not loaded. Call load() first.")
        with torch.inference_mode():
            logits = self.model(hidden_states.detach().to("cpu", dtype=torch.float32))
            log_probs = functional.log_softmax(logits[0], dim=-1)
            return np.asarray(log_probs.numpy(), dtype=np.float32)

    def cleanup(self) -> None:
        self.model = None
