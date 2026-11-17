"""Test audio processor module for prosody analysis."""

from collections.abc import Callable
from pathlib import Path

import numpy as np

from src.audio.processor import AudioContext, ProsodyAnalyzer


def test_audio_context(dummy_wav_factory: Callable[..., Path]) -> None:
    """Test AudioContext initialization and downsampled tensor extraction."""
    wav_path = dummy_wav_factory(duration=2.0, frequency=200.0, modulated=True)

    context = AudioContext(str(wav_path))
    samples = context.get_downsampled_tensor()

    assert context.total_duration > 0
    assert len(samples) > 0
    assert samples.dtype == np.float32
    assert np.max(np.abs(samples)) <= 1.0


def test_pitch_analysis(dummy_wav_factory: Callable[..., Path]) -> None:
    """Test pitch (F0) extraction."""
    wav_path = dummy_wav_factory(duration=2.0, frequency=200.0, modulated=True)

    context = AudioContext(str(wav_path))
    analyzer = ProsodyAnalyzer(context)
    pitch = analyzer.analyze_pitch()

    assert pitch is not None
    assert len(pitch.f0_values) > 0
    assert pitch.f0_range >= 0


def test_rhythm_analysis(dummy_wav_factory: Callable[..., Path]) -> None:
    """Test rhythm analysis using nPVI."""
    wav_path = dummy_wav_factory(duration=2.0, frequency=200.0, modulated=True)

    context = AudioContext(str(wav_path))
    analyzer = ProsodyAnalyzer(context)

    vowel_timestamps = [
        (0.0, 0.1),
        (0.2, 0.25),
        (0.4, 0.55),
        (0.6, 0.75),
        (0.9, 1.0),
    ]

    rhythm = analyzer.analyze_rhythm(vowel_timestamps)

    assert rhythm is not None
    assert rhythm.npvi is not None
    assert rhythm.npvi >= 0.0
    assert rhythm.classification in [
        "stress-timed",
        "syllable-timed",
        "insufficient_data",
    ]
    assert len(rhythm.vowel_durations) == len(vowel_timestamps)


def test_stress_analysis(dummy_wav_factory: Callable[..., Path]) -> None:
    """Test stress pattern analysis."""
    wav_path = dummy_wav_factory(duration=2.0, frequency=200.0, modulated=True)

    context = AudioContext(str(wav_path))
    analyzer = ProsodyAnalyzer(context)

    word_timestamps = [
        ("hello", 0.0, 0.2),
        ("world", 0.3, 0.5),
        ("test", 0.6, 0.8),
    ]

    stress = analyzer.analyze_stress(word_timestamps)

    assert stress is not None
    assert stress.primary_stress_word in [w[0] for w in word_timestamps]
    assert stress.primary_stress_time >= 0.0
    assert stress.prominence_score > 0.0


def test_complete_prosody_analysis(dummy_wav_factory: Callable[..., Path]) -> None:
    """Test complete prosody analysis pipeline with voice quality."""
    wav_path = dummy_wav_factory(duration=2.0, frequency=200.0, modulated=True)

    context = AudioContext(str(wav_path))
    analyzer = ProsodyAnalyzer(context)

    vowel_timestamps = [(0.0, 0.1), (0.2, 0.3), (0.4, 0.5), (0.6, 0.7)]
    word_timestamps = [("hello", 0.0, 0.2), ("world", 0.3, 0.5), ("test", 0.6, 0.8)]

    prosody = analyzer.analyze_complete(vowel_timestamps, word_timestamps)

    assert prosody is not None
    assert prosody.pitch is not None
    assert prosody.rhythm is not None
    assert prosody.stress is not None
    assert prosody.voice_quality is not None


def test_voice_quality_analysis(dummy_wav_factory: Callable[..., Path]) -> None:
    """Test voice quality metrics extraction."""
    wav_path = dummy_wav_factory(duration=2.0, frequency=200.0, modulated=True)

    context = AudioContext(str(wav_path))
    analyzer = ProsodyAnalyzer(context)
    vq = analyzer.analyze_voice_quality()

    assert vq is not None
    assert isinstance(vq.jitter_local, float)
    assert isinstance(vq.shimmer_local, float)
    assert isinstance(vq.cpps, float)
    assert isinstance(vq.spectral_tilt, float)
    assert vq.jitter_local >= 0
    assert vq.shimmer_local >= 0
