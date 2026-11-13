"""Inference port of R4's bundled explicit contact decoder (CC BY-NC 4.0).

Source: external/R4 26-11-06/aai_streaming/contact_decoder.py. See docs/r4-LICENSE.txt.
Only the committed frames advance the tracker in the 59-frame application replay.
"""

import hashlib
from pathlib import Path

import torch
from torch import nn
from torch.nn import functional

from src.models.r4_decoder import AsymmetricConv1d


class ContactTracker:
    """Maintain separate tip and body holds with the bundle's hysteresis."""

    def __init__(self) -> None:
        self.hold_frames = [0, 0]

    def step(self, probabilities: torch.Tensor) -> torch.Tensor:
        gates: list[list[bool]] = []
        for tip, body in probabilities.tolist():
            for index, probability, dominates in ((0, tip, tip >= body), (1, body, body > tip)):
                held = self.hold_frames[index]
                if held:
                    self.hold_frames[index] = held + 1 if probability >= 0.34 and held < 5 else 0
                elif probability >= 0.46 and dominates:
                    self.hold_frames[index] = 1
            if all(self.hold_frames):
                self.hold_frames[1 if tip > body else 0] = 0
            gates.append([count > 0 for count in self.hold_frames])
        return probabilities.new_tensor(gates)


class R4ContactHead(nn.Module):
    """Predict contact phases and places, then realize them in four tongue channels."""

    def __init__(self) -> None:
        super().__init__()
        self.state_norm = nn.LayerNorm(256)
        self.feature_norm = nn.LayerNorm(768)
        self.state_proj = nn.Linear(256, 64)
        self.feature_proj = nn.Linear(768, 64)
        self.conv1 = AsymmetricConv1d(64, 64, 5, 1)
        self.norm1 = nn.LayerNorm(64)
        self.conv2 = AsymmetricConv1d(64, 64, 5, 0)
        self.norm2 = nn.LayerNorm(64)
        self.tip_phase_head = nn.Linear(64, 4)
        self.body_phase_head = nn.Linear(64, 4)
        self.tip_place_head = nn.Linear(64, 1)
        self.body_place_head = nn.Linear(64, 1)

    def forward(
        self,
        base: torch.Tensor,
        states: torch.Tensor,
        features: torch.Tensor,
        committed: slice,
        tracker: ContactTracker,
    ) -> torch.Tensor:
        hidden = functional.gelu(
            self.state_proj(self.state_norm(states))
            + 0.25 * self.feature_proj(self.feature_norm(features))
        )
        hidden = functional.gelu(
            self.norm1(self.conv1(hidden.transpose(1, 2)).transpose(1, 2)) + hidden
        )
        hidden = functional.gelu(
            self.norm2(self.conv2(hidden.transpose(1, 2)).transpose(1, 2)) + hidden
        )
        hidden = hidden[0, committed]
        phases = torch.stack(
            (self.tip_phase_head(hidden).softmax(-1), self.body_phase_head(hidden).softmax(-1)),
            dim=1,
        )
        gates = tracker.step(phases[..., 2])
        approach_release = ((phases[..., [1, 3]] - 0.20) / 0.30).clamp(0, 1).sum(dim=-1)
        degree_weight = (gates + 0.25 * approach_release).clamp(0, 1)
        places = torch.cat(
            (self.tip_place_head(hidden), self.body_place_head(hidden)), dim=-1
        ).sigmoid()
        result = base[0, committed].clone()
        result[:, [2, 4]] = torch.lerp(result[:, [2, 4]], places, gates).clamp(0, 1)
        degrees = result[:, [3, 5]].clamp(0, 1)
        result[:, [3, 5]] = degrees + degree_weight * (0.015 - degrees)
        return result


def load_contact_head(path: Path, base_path: Path, device: str) -> R4ContactHead:
    """Require the coupled checkpoint and its matching frozen base weights."""
    payload = torch.load(path, map_location="cpu", weights_only=True)
    expected_config = {
        "state_dim": 256,
        "feature_dim": 768,
        "hidden_dim": 64,
        "kernel_size": 5,
        "right_context": 1,
        "contact_degree_target": 0.015,
    }
    if (
        not isinstance(payload, dict)
        or payload.get("format_version") != "streaming_contact_decoder_v1"
        or payload.get("coupling_mode") != "coupled"
        or payload.get("model_config") != expected_config
    ):
        raise ValueError("Unsupported R4 contact checkpoint")
    with base_path.open("rb") as base_file:
        digest = hashlib.file_digest(base_file, "sha256").hexdigest()
    if digest != payload.get("base_checkpoint_sha256"):
        raise ValueError(
            "R4 contact checkpoint requires its matching base weights. Turn off contact enhancement to use other weights."
        )
    head = R4ContactHead()
    head.load_state_dict(payload["contact_head_state_dict"], strict=True)
    return head.to(device).eval()
