"""Frozen silence feature, gate and pose math from the R4 replay scripts."""

from typing import Any

import numpy as np

from src.models.r4_contract import StreamingContract

SAMPLE_RATE = 16_000
FRAME = 320
ONSETS_AHEAD = 4
ENTRANCE_FRAMES = 6
ANCHOR_FRAMES = 5
RETURN_FRAMES = 4


def acoustic_features(audio: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    # The last block contains a frame only when its center is inside the source.
    count = (len(audio) + FRAME // 2 - 1) // FRAME
    blocks = np.pad(audio, (0, max(0, count * FRAME - len(audio))))[: count * FRAME].reshape(
        count, FRAME
    )
    rms = 10 * np.log10(np.maximum(np.mean(blocks**2, axis=1), 1e-16))
    history = np.pad(blocks.ravel(), (FRAME, 0))
    windows = np.lib.stride_tricks.sliding_window_view(history, 2 * FRAME)[::FRAME][:count]
    power = np.abs(np.fft.rfft(windows * np.hanning(2 * FRAME))) ** 2
    edges = (0, 150, 300, 600, 1200, 2400, 4000, 6000, 8000.1)
    frequencies = np.fft.rfftfreq(2 * FRAME, 1 / SAMPLE_RATE)
    bands = np.stack(
        [
            np.mean(power[:, (frequencies >= lo) & (frequencies < hi)], axis=1)
            for lo, hi in zip(edges[:-1], edges[1:], strict=True)
        ],
        axis=1,
    )
    log_bands = 10 * np.log10(np.maximum(bands, 1e-12))
    spectrum = power / np.maximum(power.sum(axis=1, keepdims=True), 1e-12)
    flux = np.abs(np.diff(spectrum, axis=0, prepend=spectrum[:1])).sum(axis=1)
    past = np.pad(log_bands, ((4, 0), (0, 0)), mode="edge")
    baseline = sum(past[offset : offset + count] for offset in range(4)) / 4
    features = np.column_stack((rms, log_bands, log_bands - baseline, flux))
    return features.astype(np.float32), rms


def silence_gate(
    activity: np.ndarray,
    thresholds: list[float],
    durations: list[int],
    release_frames: int = 0,
    *,
    isolated_noise_frames: int = 0,
) -> tuple[np.ndarray, np.ndarray]:
    """Require past inactivity and stop settling near a detected acoustic onset."""
    quiet = activity[None, :] < np.asarray(thresholds)[:, None]
    positions = np.arange(len(activity))
    age = positions - np.maximum.accumulate(np.where(quiet, -1, positions), axis=1)
    future = np.full_like(activity, -np.inf)
    for offset in range(1, ONSETS_AHEAD + 1):
        if offset < len(activity):
            future[:-offset] = np.maximum(future[:-offset], activity[offset:])
    duration_array = np.asarray(durations)[:, None]
    qualified = age >= duration_array
    if isolated_noise_frames:
        window_end = positions + 1
        window_start = window_end - duration_array
        noisy = ~quiet
        cumulative_noise = np.pad(np.cumsum(noisy, axis=1), ((0, 0), (1, 0)))
        noisy_neighbors = noisy & np.pad(noisy[:, :-1], ((0, 0), (1, 0)))
        cumulative_neighbors = np.pad(np.cumsum(noisy_neighbors, axis=1), ((0, 0), (1, 0)))
        prior_noise: np.ndarray = cumulative_noise[:, window_end] - np.take_along_axis(
            cumulative_noise,
            np.maximum(window_start, 0),
            axis=1,
        )
        adjacent_noise: np.ndarray = cumulative_neighbors[:, window_end] - np.take_along_axis(
            cumulative_neighbors,
            np.maximum(window_start + 1, 0),
            axis=1,
        )
        qualified = (
            (window_start >= 0)
            & (age >= 5)
            & (prior_noise <= isolated_noise_frames)
            & (adjacent_noise == 0)
        )
    core = qualified & (future[None, :] < np.asarray(thresholds)[:, None])
    if release_frames == 0:
        return core, core
    # The core stops four frames before signal onset. Its brief return blend
    # may use the intervening quiet frames, but leaves one raw frame before it.
    upcoming_quiet = np.pad(quiet[:, 1:], ((0, 0), (0, 1)), constant_values=True)
    last_nonquiet = np.maximum.accumulate(np.where(quiet & upcoming_quiet, -1, positions), axis=1)
    last_core = np.maximum.accumulate(np.where(core, positions, -1), axis=1)
    recovering = (positions - last_core <= release_frames) & (last_core > last_nonquiet)
    return core, core | recovering


def runs(mask: np.ndarray) -> np.ndarray:
    return np.flatnonzero(np.diff(np.r_[False, mask, False])).reshape(-1, 2)


def settle_pose(
    trajectory: np.ndarray,
    eligible: np.ndarray,
    contract: StreamingContract,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Settle after quiet confirmation and taper inside the eligible span."""
    values = trajectory.copy()
    tapering = np.zeros(len(eligible), dtype=bool)
    fully_settled = tapering.copy()
    for start, end in runs(eligible):
        previous = max(0, start - 1)
        history = trajectory[max(start - ANCHOR_FRAMES, 0) : previous + 1]
        anchor = np.median(history, axis=0)
        progress = np.minimum(np.arange(1, end - start + 1) / ENTRANCE_FRAMES, 1)
        weight = ((1 - np.cos(np.pi * progress)) / 2)[:, None]
        settled = (1 - weight) * trajectory[previous] + weight * anchor

        positions = np.arange(start, end)
        packet_end = (positions // contract.emitted_frames + 1) * contract.emitted_frames
        latest_score = packet_end + contract.lookahead_frames - 1
        # Peeking ahead to the first ineligible frame is valid only if
        # that frame's own onset check fits in this packet's available audio.
        exit_known = (end < len(eligible)) & (end + ONSETS_AHEAD <= latest_score)
        exit_progress = np.where(exit_known, np.minimum((end - positions) / RETURN_FRAMES, 1), 1)
        exit_weight = ((1 - np.cos(np.pi * exit_progress)) / 2)[:, None]
        values[start:end] = exit_weight * settled + (1 - exit_weight) * trajectory[start:end]
        tapering[start:end] = exit_progress < 1
        fully_settled[start:end] = (progress == 1) & ~tapering[start:end]
    return values, fully_settled, tapering


def apply_silence_hint(
    trajectory: np.ndarray,
    audio: np.ndarray,
    classifier: Any,
    gates: dict[str, Any],
    allowance: dict[str, int],
    contract: StreamingContract,
) -> tuple[np.ndarray, np.ndarray]:
    """Apply the reviewed or expanded quiet-pose gate in recording replay."""
    if (contract.sample_rate_hz, contract.samples_per_frame) != (SAMPLE_RATE, FRAME):
        raise ValueError("Silence hint requires the release audio and frame clock")
    features, rms = acoustic_features(audio)
    if len(rms) != len(trajectory):
        raise ValueError("Silence scores and trajectory have different frame clocks")
    probability = classifier.predict_proba(features)[:, 1]
    eligible = np.zeros(len(rms), dtype=bool)
    for scores, name in ((probability, "speech_probability"), (rms, "rms_dbfs")):
        gate = gates[name]
        _, allowed = silence_gate(
            scores,
            [gate["threshold"]],
            [gate["inactivity_frames"]],
            isolated_noise_frames=allowance.get(name, 0),
        )
        eligible |= allowed[0]
    values, settled, _ = settle_pose(trajectory, eligible, contract)
    return values, settled
