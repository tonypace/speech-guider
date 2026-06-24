"""Tests for normalized comparison frame generation."""

import torch

from src.models.aai_adapter import AAIConversionMetadata, aai_to_canonical_states_batch


def test_aai_to_canonical_states_batch_emits_normalized_values() -> None:
    trajectory = torch.tensor(
        [
            [0.5, 0.8, 0.1, 0.0, 0.8, 0.6, 0.1, 0.2, 0.3],
            [0.2, 0.9, 0.3, 0.2, 0.7, 0.4, 0.0, 0.0, 0.1],
        ],
        dtype=torch.float32,
    )

    metadata = AAIConversionMetadata(normalization="robust_01")
    frames = aai_to_canonical_states_batch(trajectory.numpy(), metadata)

    assert len(frames) == 2
    for frame in frames:
        assert set(frame.keys()) == {
            "lip_aperture",
            "lip_protrusion",
            "tongue_tip_constriction_location",
            "tongue_tip_constriction_degree",
            "lateral_tongue_drop",
            "velic_aperture",
            "tongue_body_constriction_location",
            "tongue_body_constriction_degree",
            "glottal_aperture",
        }
        for value in frame.values():
            assert 0.0 <= value <= 1.0
