"""Inference port of the frozen R4 bounded_v12 decoder.

Source: external/R4 26-11-06/{models.py,aai_streaming/bounded_model.py},
revision cb2f2f15c6445cfddb69d791debf1f5923fc40f2. Licensed CC BY-NC 4.0; see docs/r4-LICENSE.txt.
Training-only heads remain registered so checkpoint loading stays strict.
"""

from pathlib import Path
from typing import Any

import torch
from torch import nn
from torch.nn import functional

from src.models.aai_adapter import AAI_TV_ORDER


class AsymmetricConv1d(nn.Conv1d):
    """Keep saved Conv1d parameter names while bounding future context."""

    def __init__(self, inputs: int, outputs: int, kernel: int, right: int) -> None:
        super().__init__(inputs, outputs, kernel)
        if not 0 <= right < kernel:
            raise ValueError("R4 convolution context exceeds its kernel")
        self.right = right
        self.left = kernel - 1 - right

    def forward(self, values: torch.Tensor) -> torch.Tensor:
        return super().forward(functional.pad(values, (self.left, self.right)))


class TransposeConvLayer(nn.Module):
    def __init__(self, inputs: int, outputs: int, right: int) -> None:
        super().__init__()
        self.conv = AsymmetricConv1d(inputs, outputs, 5, right)

    def forward(self, values: torch.Tensor) -> torch.Tensor:
        result: torch.Tensor = self.conv(values.transpose(1, 2)).transpose(1, 2)
        return result


class V12LowRankExtensionHead(nn.Module):
    def __init__(self, hidden: int, width: int, config: dict[str, Any]) -> None:
        super().__init__()
        state_rank = int(config.get("decoder_rank", 32))
        feature_rank = int(config.get("feature_rank", 8))
        self.state_projection = nn.Linear(hidden, state_rank)
        self.feature_projection = nn.Linear(width, feature_rank)
        self.output = nn.Linear(state_rank + feature_rank, 3)

    def forward(self, states: torch.Tensor, features: torch.Tensor) -> torch.Tensor:
        result: torch.Tensor = self.output(
            torch.cat(
                (
                    functional.gelu(self.state_projection(states)),
                    functional.gelu(self.feature_projection(features)),
                ),
                dim=-1,
            )
        )
        return result


class V12LatTemporalExtensionHead(nn.Module):
    def __init__(
        self, hidden: int, width: int, config: dict[str, Any], right_context: list[int]
    ) -> None:
        super().__init__()
        self.base_head = V12LowRankExtensionHead(hidden, width, config)
        state_rank = int(config.get("temporal_state_rank", 16))
        feature_rank = int(config.get("temporal_feature_rank", 8))
        temporal_hidden = int(config.get("temporal_hidden", 32))
        self.state_context = nn.Linear(hidden, state_rank)
        self.feature_context = nn.Linear(width, feature_rank)
        self.temporal = nn.Sequential(
            AsymmetricConv1d(state_rank + feature_rank + 1, temporal_hidden, 5, right_context[0]),
            nn.GELU(),
            AsymmetricConv1d(temporal_hidden, temporal_hidden, 5, right_context[1]),
            nn.GELU(),
            nn.Conv1d(temporal_hidden, 1, 1),
        )

    def forward(self, states: torch.Tensor, features: torch.Tensor) -> torch.Tensor:
        base = self.base_head(states, features)
        context = torch.cat(
            (
                functional.gelu(self.state_context(states)),
                functional.gelu(self.feature_context(features)),
                torch.sigmoid(base[..., 2:3]),
            ),
            dim=-1,
        )
        residual = self.temporal(context.transpose(1, 2)).transpose(1, 2)
        return torch.cat((base[..., :2], base[..., 2:3] + residual), dim=-1)


class R4Decoder(nn.Module):
    """Nine-channel temporal decoder; oral speaker-Z, extension sigmoid outputs."""

    def __init__(self, config: dict[str, Any], metadata: dict[str, Any]) -> None:
        super().__init__()
        cfg = config["model"]
        extension = cfg.get("extension_head", {})
        if (
            cfg.get("superb", True)
            or cfg.get("predictor_architecture") != "conv"
            or cfg.get("output_activation") != "hardtanh"
            or cfg.get("smoothing_head", "none") != "none"
            or cfg.get("alignment_type") is not None
            or config.get("train", {}).get("auxiliary_targets", {}).get("enabled", False)
            or cfg.get("auxiliary_targets", {}).get("enabled", False)
            or not extension.get("enabled")
            or extension.get("architecture") != "lat_temporal_v12_compat"
            or int(extension.get("temporal_kernel", 5)) != 5
            or int(cfg.get("num_tvs", -1)) != 9
            or int(cfg.get("input_size", -1)) != 768
            or int(cfg.get("contentvec_layer", cfg.get("freeze_layer", -1))) != 7
        ):
            raise ValueError("Unsupported R4 model configuration")
        if (
            metadata.get("format_version") != "nine_channel_streaming_successor_v1"
            or metadata.get("architecture") != "bounded_v12"
            or metadata.get("streaming_contract_version") != "nine_channel_streaming_v1"
            or tuple(metadata.get("channels", ())) != AAI_TV_ORDER
        ):
            raise ValueError("Unsupported R4 checkpoint format or channel order")
        context = metadata["context_allocation"]
        base_rc = context["base_right_context"]
        lat_rc = context["lat_right_context"]
        if (
            len(base_rc) != 4
            or len(lat_rc) != 2
            or any(type(v) is not int or not 0 <= v <= 4 for v in base_rc + lat_rc)
            or sum(base_rc) not in (4, 5)
            or sum(base_rc + lat_rc) != 5
            or context.get("oral_future_context_frames") != sum(base_rc)
            or context.get("lat_future_context_frames") != 5
        ):
            raise ValueError("Unsupported R4 lookahead allocation")
        encoder = metadata.get("contentvec", {})
        if encoder.get("layer") != 7 or encoder.get("feature_width") != 768:
            raise ValueError("R4 requires ContentVec layer 7, width 768")
        hidden = int(cfg["predictor_hidden_size"])
        self.scale_factor = nn.Parameter(torch.ones(1))
        self.predictor_layers = nn.ModuleList(
            [
                TransposeConvLayer(768 if i == 0 else hidden, hidden, rc)
                for i, rc in enumerate(base_rc)
            ]
        )
        self.lns = nn.ModuleList([nn.LayerNorm(hidden) for _ in range(4)])
        self.final_proj = nn.Linear(hidden, 9)
        self.extension_head = V12LatTemporalExtensionHead(hidden, 768, extension, lat_rc)
        # Saved training heads are never applied without dataset IDs at inference.
        self.alignment = nn.Module()
        self.alignment.nets = nn.ModuleList(
            [nn.Sequential(nn.Linear(9, 32), nn.GELU(), nn.Linear(32, 9)) for _ in range(10)]
        )
        domain_hidden = int(cfg["domain_hidden_size"])
        self.domain_classifier = nn.Sequential(
            nn.Linear(768, domain_hidden),
            nn.LayerNorm(domain_hidden),
            nn.GELU(),
            nn.Dropout(0.2),
            nn.Linear(domain_hidden, domain_hidden),
            nn.LayerNorm(domain_hidden),
            nn.GELU(),
            nn.Dropout(0.2),
            nn.Linear(domain_hidden, int(cfg["num_domains"])),
        )

    def forward(self, features: torch.Tensor) -> torch.Tensor:
        scaled = self.scale_factor * features
        states = scaled
        for conv, norm in zip(self.predictor_layers, self.lns):
            residual = states
            states = functional.gelu(norm(conv(states)))
            if states.shape == residual.shape:
                states = states + residual
        oral = self.final_proj(states).clamp(-0.1, 1.1)[..., :6]
        extension = torch.sigmoid(self.extension_head(states, scaled))
        return torch.cat((oral, extension), dim=-1)


def load_r4_decoder(path: Path, device: str) -> tuple[R4Decoder, dict[str, Any]]:
    """Reject legacy checkpoints and require every released state tensor."""
    payload = torch.load(path, map_location="cpu", weights_only=True)
    if not isinstance(payload, dict) or not isinstance(payload.get("metadata"), dict):
        raise ValueError("R4 checkpoint requires successor metadata")
    model = R4Decoder(payload["config"], payload["metadata"])
    model.load_state_dict(payload["state_dict"], strict=True)
    return model.to(device).eval(), payload["metadata"]
