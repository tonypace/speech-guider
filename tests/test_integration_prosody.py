"""Integration test for prosody analysis in the application."""

import tempfile
from pathlib import Path

import numpy as np
import scipy.io.wavfile as wavfile
import torch

from src.audio import AudioContext, ProsodyAnalyzer
from src.models.alignment import ForcedAligner


def create_test_audio_tensor(
    duration: float = 2.0, frequency: float = 440.0
) -> torch.Tensor:
    """Create a simple sine wave tensor for testing (like demo_pronunciation.py).

    Args:
        duration: Duration in seconds
        frequency: Frequency in Hz

    Returns:
        Audio tensor
    """
    t = torch.linspace(0.0, duration, int(16_000 * duration))
    waveform = torch.sin(2 * torch.pi * frequency * t).float()
    return waveform


def create_test_wav_data(
    sample_rate: int = 16_000, duration: float = 2.0
) -> tuple[str, np.ndarray]:
    """Create test WAV data for integration testing.

    Args:
        sample_rate: Sample rate in Hz
        duration: Duration in seconds

    Returns:
        Tuple of (file_path, audio_array)
    """
    num_samples = int(sample_rate * duration)
    t = np.linspace(0, duration, num_samples)

    # Create modulated sine wave to simulate speech-like F0 contour
    carrier_freq = 200.0 + 100.0 * np.sin(2 * np.pi * 3.0 * t)
    modulation = np.sin(2 * np.pi * 5.0 * t)
    waveform = np.sin(2 * np.pi * carrier_freq * t * (1 + 0.2 * modulation))

    # Add amplitude variation (intensity changes)
    amplitude_envelope = 0.5 + 0.3 * np.sin(2 * np.pi * 2.0 * t)
    waveform = waveform * amplitude_envelope

    # Normalize to 16-bit range
    waveform = (waveform * 32767.0).astype(np.int16)

    # Create temporary file
    temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    wavfile.write(temp_file.name, sample_rate, waveform)
    temp_file.close()

    return temp_file.name, waveform


def test_forced_alignment_with_simple_audio():
    """Test forced alignment using simple sine wave audio."""
    # Create simple test audio like demo_pronunciation.py
    audio_tensor = create_test_audio_tensor(duration=2.0, frequency=440.0)

    # Initialize forced aligner
    aligner = ForcedAligner()
    target_text = "the weather is hot"

    # Perform alignment
    errors, alignment = aligner.analyze_pronunciation(audio_tensor, target_text)

    # Check alignment results
    assert alignment is not None
    assert alignment.total_duration == 2.0
    assert len(alignment.words) > 0

    # Check that phonemes have voice quality metadata
    has_vowel_data = False
    has_voiced_data = False

    for word in alignment.words:
        for phoneme in word.phonemes:
            assert hasattr(phoneme, "is_vowel")
            assert hasattr(phoneme, "is_voiced")
            assert isinstance(phoneme.is_vowel, bool)
            assert isinstance(phoneme.is_voiced, bool)
            if phoneme.is_vowel:
                has_vowel_data = True
            if phoneme.is_voiced:
                has_voiced_data = True

    assert has_vowel_data, "Alignment should include vowel data"
    assert has_voiced_data, "Alignment should include voiced data"

    print("✓ Forced alignment with simple audio test passed")
    print(f"  - Words aligned: {len(alignment.words)}")
    print(f"  - Total phonemes: {sum(len(w.phonemes) for w in alignment.words)}")
    print(f"  - Errors detected: {len(errors)}")

    aligner.cleanup()


def test_prosody_extraction_from_alignment():
    """Test that prosody metrics can be extracted from alignment results."""
    wav_path, _ = create_test_wav_data()

    try:
        audio_context = AudioContext(wav_path)
        prosody_analyzer = ProsodyAnalyzer(audio_context)

        # Create simple audio tensor for alignment
        audio_tensor = create_test_audio_tensor(duration=2.0, frequency=440.0)

        aligner = ForcedAligner()
        target_text = "the weather is hot"

        errors, alignment = aligner.analyze_pronunciation(audio_tensor, target_text)

        # Extract vowel and word timestamps from alignment
        vowel_timestamps = [
            (phoneme.start_time, phoneme.end_time)
            for word in alignment.words
            for phoneme in word.phonemes
            if phoneme.is_vowel
        ]

        word_timestamps = [
            (word.word, word.start_time, word.end_time) for word in alignment.words
        ]

        # Run complete prosody analysis
        prosody = prosody_analyzer.analyze_complete(vowel_timestamps, word_timestamps)

        # Verify prosody results
        assert prosody is not None
        assert hasattr(prosody, "pitch")
        assert hasattr(prosody, "rhythm")
        assert hasattr(prosody, "stress")

        # Check pitch analysis
        assert prosody.pitch is not None
        assert prosody.pitch.f0_range >= 0.0
        assert len(prosody.pitch.f0_values) > 0

        # Check rhythm analysis if vowels were found
        if len(vowel_timestamps) > 0:
            assert prosody.rhythm is not None
            assert prosody.rhythm.npvi >= 0.0
            assert len(prosody.rhythm.vowel_durations) == len(vowel_timestamps)
            assert prosody.rhythm.classification in [
                "stress-timed",
                "syllable-timed",
                "insufficient_data",
            ]

        # Check stress analysis if words were found
        if len(word_timestamps) > 0 and prosody.stress:
            assert prosody.stress.primary_stress_word in [w[0] for w in word_timestamps]
            assert prosody.stress.primary_stress_time >= 0.0
            assert prosody.stress.prominence_score > 0.0

        print("✓ Prosody extraction from alignment test passed")
        print(f"  - Pitch range: {prosody.pitch.f0_range:.2f}Hz")
        if prosody.rhythm and len(vowel_timestamps) > 0:
            print(f"  - nPVI: {prosody.rhythm.npvi:.2f}")
            print(f"  - Vowels extracted: {len(vowel_timestamps)}")
            print(f"  - Rhythm classification: {prosody.rhythm.classification}")
        if prosody.stress and len(word_timestamps) > 0:
            print(f"  - Primary stress: '{prosody.stress.primary_stress_word}'")

        aligner.cleanup()

    finally:
        Path(wav_path).unlink()


def test_error_handling_with_corrupted_audio():
    """Test graceful error handling when alignment fails."""
    # Create minimal test file
    wav_path, _ = create_test_wav_data(duration=0.5)

    try:
        audio_context = AudioContext(wav_path)

        # Test with very short audio that might cause alignment issues
        audio_tensor = create_test_audio_tensor(duration=0.5, frequency=440.0)

        aligner = ForcedAligner()

        # Try to align with a long sentence that doesn't fit in the audio
        target_text = (
            "this is a very long sentence that won't fit in the short audio clip"
        )

        try:
            errors, alignment = aligner.analyze_pronunciation(audio_tensor, target_text)
            # If it succeeds, verify it doesn't crash
            assert alignment is not None
        except Exception as e:
            print(f"  - Expected alignment issue: {type(e).__name__}")

        # Test prosody analysis fallback
        pitch = audio_context.praat_sound.to_pitch()
        f0_values = pitch.selected_array["frequency"]
        voiced_f0 = f0_values[f0_values > 0]

        if len(voiced_f0) > 0:
            print("✓ Error handling test passed")
            print(f"  - F0 analysis succeeded with {len(voiced_f0)} voiced frames")
        else:
            print("✓ Error handling test passed (no voiced frames found)")

        aligner.cleanup()

    finally:
        Path(wav_path).unlink()


if __name__ == "__main__":
    test_forced_alignment_with_simple_audio()
    test_prosody_extraction_from_alignment()
    test_error_handling_with_corrupted_audio()
    print("\n✅ All integration tests passed!")
