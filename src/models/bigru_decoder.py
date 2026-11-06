"""Haskins layer-12 BiGRU tract-variable decoder.

Implements the validated `paper_bigru` decoder contract from
external/aai_haskins_bigru/client_documentation.md:

    Linear(768->256) -> GELU -> Dropout(0.3) -> Linear(256->256) -> GELU -> Dropout(0.3)
    2-layer bidirectional GRU (256 units/direction, dropout 0.3, batch_first)
    Linear(512->256) -> GELU -> Dropout(0.3) -> Linear(256->256) -> GELU -> Dropout(0.3)
    Linear(256->6)

Features come from ContentVec hidden state 12 (NOT layer 7). Outputs are
speaker-Z normalized trajectories:

    normalized = (raw_mm - mean) * (0.2 / std) + 0.5

They must be consumed directly with a normalized rig; do NOT invert them
with training speaker statistics. Display-side bounding is clamp(-0.1, 1.1)
with the clipped fraction recorded for telemetry.

Output channel order (6): LP, LA, TTCL, TTCD, TBCL, TBCD
"""

from pathlib import Path
from typing import Optional

import torch
import torch.nn as nn
from torch import Tensor

BIGRU_FEATURE_LAYER = 12
BIGRU_OUTPUT_CHANNELS = 6

# Display bounds per client contract; raw output preserved for telemetry.
BIGRU_DISPLAY_CLAMP_MIN = -0.1
BIGRU_DISPLAY_CLAMP_MAX = 1.1

BIGRU_TV_ORDER: tuple[str, ...] = ("LP", "LA", "TTCL", "TTCD", "TBCL", "TBCD")


def _get_default_bigru_checkpoint_path() -> Path:
    """Return default BiGRU checkpoint path relative to project root."""
    return (
        Path(__file__).parent.parent.parent
        / "external"
        / "aai_haskins_bigru"
        / "best_bigru.weights.pt"
    )


class BiGRUTVDecoder(nn.Module):
    """Faithful paper-style BiGRU decoder mapping ContentVec features to 6 TVs.

    Submodule key layout mirrors the released checkpoint exactly
    (`input_net.0`, `gru`, `output_net.6`, ...), so `load_state_dict` is strict.
    """

    def __init__(self, input_dim: int = 768, hidden_size: int = 256, dropout: float = 0.3) -> None:
        super().__init__()
        self.input_net = nn.Sequential(
            nn.Linear(input_dim, hidden_size),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_size, hidden_size),
            nn.GELU(),
            nn.Dropout(dropout),
        )
        self.gru = nn.GRU(
            input_size=hidden_size,
            hidden_size=hidden_size,
            num_layers=2,
            batch_first=True,
            bidirectional=True,
            dropout=dropout,
        )
        self.output_net = nn.Sequential(
            nn.Linear(2 * hidden_size, hidden_size),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_size, hidden_size),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_size, BIGRU_OUTPUT_CHANNELS),
        )

    def forward(
        self, features: torch.Tensor, lengths: Optional[torch.Tensor] = None
    ) -> torch.Tensor:
        """Decode ContentVec features into 6 tract-variable channels.

        Args:
            features: (batch, frames, 768) or (frames, 768) ContentVec hidden
                state. Single unpadded utterance: batch=1, lengths=None.
            lengths: True feature-frame lengths for padded batches. The GRU is
                bidirectional, so the complete utterance is required for the
                final output.

        Returns:
            Normalized TVs preserving input batch dimensionality:
            (batch, frames, 6) for 3D input, (frames, 6) for 2D input.
            Linear output (not clamped).
        """
        hidden = self.input_net(features if features.dim() == 3 else features.unsqueeze(0))
        gru_out, _ = self.gru(hidden)
        decoded: Tensor = self.output_net(gru_out)
        return decoded if features.dim() == 3 else decoded[0]


def load_bigru_decoder(
    checkpoint_path: Path | str | None = None,
    device: str = "cpu",
) -> BiGRUTVDecoder:
    """Load a weights-only BiGRU checkpoint into a decoder.

    Raises:
        FileNotFoundError: If checkpoint does not exist.
        RuntimeError: If state dict is incompatible.
    """
    path = Path(checkpoint_path) if checkpoint_path else _get_default_bigru_checkpoint_path()
    if not path.exists():
        raise FileNotFoundError(f"BiGRU checkpoint not found: {path}")

    state_dict = torch.load(path, map_location=device, weights_only=True)
    decoder = BiGRUTVDecoder()
    decoder.load_state_dict(state_dict, strict=True)
    decoder.to(device)
    decoder.eval()
    return decoder


def clamp_display(tvs: torch.Tensor) -> tuple[torch.Tensor, float]:
    """Clamp a raw prediction to display bounds, returning (clipped, clip_fraction).

    Raw output must be preserved for telemetry; clamp only at the display
    boundary and record the fraction of values clipped.
    """
    outside = (tvs < BIGRU_DISPLAY_CLAMP_MIN) | (tvs > BIGRU_DISPLAY_CLAMP_MAX)
    clip_fraction = float(outside.float().mean().item()) if tvs.numel() else 0.0
    return tvs.clamp(BIGRU_DISPLAY_CLAMP_MIN, BIGRU_DISPLAY_CLAMP_MAX), clip_fraction


def tongue_confidence_tier(clip_fraction: float) -> str:
    """Map the clip-fraction telemetry into a client-facing confidence tier.

    Tier contract (client_documentation.md):
      usable | needs_caution | do_not_trust_tongue_contact
    """
    if clip_fraction > 0.25:
        return "do_not_trust_tongue_contact"
    if clip_fraction > 0.05:
        return "needs_caution"
    return "usable"
