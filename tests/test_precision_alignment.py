"""Test precision forced alignment with phoneme classification."""

import numpy as np
import torch

from src.models.alignment import ForcedAligner, _classify_phoneme


def test_phoneme_classification():
    """Test that phonemes are correctly classified."""
    # Test vowels
    assert _classify_phoneme("i") == (True, True)
    assert _classify_phoneme("eɪ") == (True, True)
    assert _classify_phoneme("aɪ") == (True, True)

    # Test voiced consonants
    assert _classify_phoneme("b") == (False, True)
    assert _classify_phoneme("v") == (False, True)
    assert _classify_phoneme("z") == (False, True)

    # Test voiceless consonants
    assert _classify_phoneme("p") == (False, False)
    assert _classify_phoneme("s") == (False, False)
    assert _classify_phoneme("f") == (False, False)

    print("✓ Phoneme classification tests passed")


def test_forced_alignment_basic():
    """Test basic forced alignment with torchaudio."""
    # Create simple test audio (sine wave)
    sample_rate = 16_000
    duration_sec = 2.0
    num_samples = int(sample_rate * duration_sec)

    # Create a simple sine wave at 440Hz (A4) as test audio
    t = np.linspace(0, duration_sec, num_samples)
    audio_waveform = np.sin(2 * np.pi * 440 * t)

    # Convert to torch tensor
    audio_tensor = torch.from_numpy(audio_waveform).float()

    # Test alignment
    aligner = ForcedAligner()
    target_text = "hello world"

    try:
        errors, alignment = aligner.analyze_pronunciation(audio_tensor, target_text)

        # Check that alignment was created
        assert alignment is not None
        assert alignment.total_duration > 0
        assert alignment.total_duration == duration_sec

        # Check that phonemes were aligned
        total_phonemes = sum(len(word.phonemes) for word in alignment.words)
        assert total_phonemes > 0

        # Check that phonemes have metadata for voice quality analysis
        for word in alignment.words:
            for phoneme in word.phonemes:
                assert phoneme.start_time < phoneme.end_time
                assert 0.0 <= phoneme.start_time <= duration_sec
                assert 0.0 <= phoneme.end_time <= duration_sec
                assert isinstance(phoneme.is_vowel, bool)
                assert isinstance(phoneme.is_voiced, bool)

        print("✓ Forced alignment test passed")
        print(f"  - Total words: {len(alignment.words)}")
        print(f"  - Total phonemes: {total_phonemes}")
        print(f"  - Duration: {alignment.total_duration:.2f}s")
        print(f"  - Overall score: {alignment.overall_score:.2f}")
        print(f"  - Errors detected: {len(errors)}")

        if alignment.words:
            first_word = alignment.words[0]
            print(
                f"  - First word: '{first_word.word}' ({first_word.start_time:.2f}s - {first_word.end_time:.2f}s)"
            )
            if first_word.phonemes:
                first_phone = first_word.phonemes[0]
                print(
                    f"  - First phoneme: '{first_phone.phoneme}' ({first_phone.start_time:.2f}s - {first_phone.end_time:.2f}s)"
                )
                print(f"  - is_vowel: {first_phone.is_vowel}, is_voiced: {first_phone.is_voiced}")

    finally:
        aligner.cleanup()


if __name__ == "__main__":
    test_phoneme_classification()
    test_forced_alignment_basic()
    print("\n✅ All precision alignment tests passed!")
