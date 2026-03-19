#!/usr/bin/env python3
"""Benchmark MPS vs CPU performance for Wav2Vec2."""

import sys
import time
from pathlib import Path

src_path = Path(__file__).parent.parent
sys.path.insert(0, str(src_path))

import torch  # noqa: E402

from src.models.wav2vec2 import Wav2Vec2Model  # noqa: E402


def create_test_audio(
    duration_sec: float = 2.0, sample_rate: int = 16000
) -> torch.Tensor:
    """Create test audio for benchmarking."""
    frequency = 440.0
    t = torch.linspace(0.0, duration_sec, int(sample_rate * duration_sec))
    waveform = torch.sin(2 * torch.pi * frequency * t).float()
    return waveform


def benchmark_device(device: str, num_runs: int = 5) -> float:
    """Benchmark transcription performance on a device.

    Args:
        device: Device to benchmark ('cpu', 'mps', or 'cuda')
        num_runs: Number of runs to average

    Returns:
        Average time in seconds
    """
    model = Wav2Vec2Model(device=device)
    audio = create_test_audio(duration_sec=2.0)

    print(f"\nTesting {device.upper()} device...")
    print(f"  Device: {model.device}")

    # Warmup run
    with torch.no_grad():
        model.transcribe(audio)

    # Benchmark runs
    times = []
    for i in range(num_runs):
        start = time.time()
        with torch.no_grad():
            model.transcribe(audio)
        end = time.time()
        times.append(end - start)
        print(f"  Run {i + 1}: {times[-1]:.3f}s")

    avg_time = sum(times) / len(times)
    model.cleanup()

    return avg_time


def main() -> None:
    """Run the benchmark comparison."""
    print("=" * 60)
    print("Wav2Vec2 Performance Benchmark: MPS vs CPU")
    print("=" * 60)

    devices_to_test = []

    # Add available devices
    if torch.cuda.is_available():
        devices_to_test.append("cuda")
    if torch.backends.mps.is_available():
        devices_to_test.append("mps")
    devices_to_test.append("cpu")

    results = {}
    for device in devices_to_test:
        results[device] = benchmark_device(device)

    print("\n" + "=" * 60)
    print("Results Summary")
    print("=" * 60)

    # Find fastest for comparison
    fastest_device = min(results.items(), key=lambda x: x[1])[0]
    fastest_time = results[fastest_device]

    for device, time_val in results.items():
        speedup = time_val / fastest_time
        print(f"{device.upper():8s}: {time_val:6.3f}s (speedup: {speedup:.2f}x)")

    if len(devices_to_test) > 1:
        print(f"\nFastest: {fastest_device.upper()} ({fastest_time:.3f}s)")

    print("=" * 60)


if __name__ == "__main__":
    main()
