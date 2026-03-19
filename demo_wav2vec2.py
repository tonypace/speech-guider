#!/usr/bin/env python3
"""Demo script for Wav2Vec2 model and forced alignment."""

import sys
from pathlib import Path

src_path = Path(__file__).parent.parent
sys.path.insert(0, str(src_path))

import torch  # noqa: E402

from src.models.alignment import ForcedAligner  # noqa: E402
from src.models.wav2vec2 import Wav2Vec2Model  # noqa: E402


def create_sine_wave(
    duration: float = 1.0, sample_rate: int = 16000, frequency: float = 440.0
) -> torch.Tensor:
    """Create a simple sine wave for testing.

    Args:
        duration: Duration in seconds
        sample_rate: Sample rate in Hz
        frequency: Frequency in Hz

    Returns:
        Audio tensor
    """
    t = torch.linspace(0.0, duration, int(sample_rate * duration))
    waveform = torch.sin(2 * torch.pi * frequency * t).float()
    return waveform


def main() -> None:
    """Demonstrate Wav2Vec2 model and forced alignment functionality."""
    print("=" * 60)
    print("Wav2Vec2 Model and Forced Alignment Demo")
    print("=" * 60)

    # 1. Initialize Wav2Vec2 model
    print("\n1. Initializing Wav2Vec2 model...")
    model = Wav2Vec2Model()
    print(f"   Model: {model.model_name}")
    print(f"   Device: {model.device}")

    # 2. Generate test audio
    print("\n2. Generating test audio (sine wave)...")
    audio_tensor = create_sine_wave(duration=1.0, frequency=440.0)
    print(f"   Audio shape: {audio_tensor.shape}")
    print(f"   Duration: {audio_tensor.shape[0] / 16000:.2f} seconds")

    # 3. Transcribe audio
    print("\n3. Transcribing audio...")
    result = model.transcribe(audio_tensor)
    print(f"   Logits shape: {result['logits'].shape}")  # type: ignore
    print(f"   Predicted text: '{result['predicted_text']}'")

    # 4. Initialize forced aligner
    print("\n4. Initializing forced aligner...")
    aligner = ForcedAligner(wav2vec2_model=model)
    print("   Aligner initialized")

    # 5. Perform forced alignment
    print("\n5. Performing forced alignment...")
    target_text = "hello world test sentence"
    alignment = aligner.align(audio_tensor, target_text)

    print(f"   Target text: '{alignment.text}'")
    print(f"   Total duration: {alignment.total_duration:.2f}s")
    print(f"   Number of words: {len(alignment.words)}")

    print("\n   Word alignments:")
    for i, word in enumerate(alignment.words):
        print(
            f"     {i + 1}. '{word.word}' ({word.start_time:.3f}s - {word.end_time:.3f}s)"
        )
        print(f"        Duration: {word.end_time - word.start_time:.3f}s")

    # 6. Cleanup
    print("\n6. Cleaning up models...")
    aligner.cleanup()
    model.cleanup()
    print("   Models cleaned up successfully")

    print("\n" + "=" * 60)
    print("Demo completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()
