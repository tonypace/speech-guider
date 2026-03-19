#!/usr/bin/env python3
"""Demo script for phoneme error detection using IPA and PyGOP."""

import sys
import time
from pathlib import Path

import torch

from src.models.alignment import ForcedAligner

src_path = Path(__file__).parent.parent
sys.path.insert(0, str(src_path))


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
    """Demonstrate phoneme error detection and GOP scoring."""
    print("=" * 60)
    print("Phoneme Error Detection & PyGOP Demo")
    print("=" * 60)

    # 1. Initialize Forced Aligner with IPA model
    print("\n1. Initializing IPA model and aligner...")
    aligner = ForcedAligner()
    print(f"   Model: {aligner.model.model_name}")
    print(f"   Device: {aligner.model.device}")

    # 2. Generate test audio
    print("\n2. Generating test audio (2.0 seconds)...")
    audio_tensor = create_sine_wave(duration=2.0, frequency=440.0)
    print(f"   Audio shape: {audio_tensor.shape}")
    print(f"   Duration: {audio_tensor.shape[0] / 16000:.2f} seconds")

    # 3. Analyze pronunciation
    print("\n3. Analyzing pronunciation for target sentence...")
    target_text = "the weather is very hot today"
    print(f"   Target: '{target_text}'")

    start_time = time.time()
    errors, alignment = aligner.analyze_pronunciation(audio_tensor, target_text)
    analysis_time = time.time() - start_time

    print(f"   Analysis completed in {analysis_time:.2f} seconds")
    print(f"   Overall score: {alignment.overall_score:.2f}")

    # 4. Display pronunciation errors
    print("\n4. Pronunciation Errors Detected:")
    if errors:
        for i, error in enumerate(errors, 1):
            print(f"   {i}. [{error.error_type}]")
            print(f"      Target: /{error.target_phoneme}/")
            print(f"      Detected: /{error.predicted_phoneme}/")
            print(f"      Context: '{error.word_context}'")
    else:
        print("   No significant errors detected")

    # 5. Display alignment details
    print("\n5. Word Alignment Details:")
    for word in alignment.words:
        print(f"   '{word.word}' ({word.start_time:.3f}s - {word.end_time:.3f}s)")

        if word.phonemes:
            print("      Phonemes:")
            for phoneme in word.phonemes:
                status = "❌ ERROR" if phoneme.is_error else "✅"
                print(f"         {status}/{phoneme.phoneme}/ Score: {phoneme.score:.2f}")
                if phoneme.is_error:
                    print(f"              Predicted: /{phoneme.predicted_phoneme}/")

    # 6. Cleanup
    print("\n6. Cleaning up...")
    aligner.cleanup()
    print("   Models cleaned up successfully")

    print("\n" + "=" * 60)
    print("Demo completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()
