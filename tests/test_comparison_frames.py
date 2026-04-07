"""Tests for normalized comparison frame generation."""

import torch

from app.api.comparison import _ssl_trajectory_to_canonical_frames


def test_ssl_trajectory_to_canonical_frames_emits_normalized_values() -> None:
    trajectory = torch.tensor(
        [
            [0.5, 1.2, 0.1, 0.0, 0.8, 0.6, 0.1, 0.2, 0.3],
            [0.2, 0.9, 0.3, 0.2, 0.7, 0.4, 0.0, 0.0, 0.1],
        ],
        dtype=torch.float32,
    )

    frames = _ssl_trajectory_to_canonical_frames(trajectory)

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
