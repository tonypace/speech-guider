"""Test audio processor module for prosody analysis."""

import tempfile
from pathlib import Path

import numpy as np
import scipy.io.wavfile as wavfile

from src.audio.processor import AudioContext, ProsodyAnalyzer


def create_dummy_wav_file(sample_rate: int = 16000, duration: float = 2.0) -> str:
    """Create a dummy WAV file for testing.

    Args:
        sample_rate: Sample rate in Hz
        duration: Duration in seconds

    Returns:
        Path to the created WAV file
    """
    num_samples = int(sample_rate * duration)
    t = np.linspace(0, duration, num_samples)

    # Create a simple sine wave with frequency modulation to simulate speech
    carrier_freq = 200.0
    mod_freq = 5.0
    modulation = np.sin(2 * np.pi * mod_freq * t)
    waveform = np.sin(2 * np.pi * carrier_freq * t * (1 + 0.2 * modulation))

    # Add some variation in amplitude (simulating intensity changes)
    amplitude_envelope = 0.5 + 0.3 * np.sin(2 * np.pi * 2.0 * t)
    waveform = waveform * amplitude_envelope

    # Normalize to 16-bit range
    waveform = (waveform * 32767.0).astype(np.int16)

    # Create temporary file
    temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    wavfile.write(temp_file.name, sample_rate, waveform)
    temp_file.close()

    return temp_file.name


def test_audio_context():
    """Test AudioContext initialization and downsampled tensor extraction."""
    wav_path = create_dummy_wav_file()

    try:
        context = AudioContext(wav_path)
        samples = context.get_downsampled_tensor()

        assert context.total_duration > 0
        assert len(samples) > 0
        assert samples.dtype == np.float32
        assert np.max(np.abs(samples)) <= 1.0

    finally:
        Path(wav_path).unlink()


def test_pitch_analysis():
    """Test pitch (F0) extraction."""
    wav_path = create_dummy_wav_file()

    try:
        context = AudioContext(wav_path)
        analyzer = ProsodyAnalyzer(context)
        pitch = analyzer.analyze_pitch()

        assert pitch is not None
        assert len(pitch.f0_values) > 0
        assert pitch.f0_range >= 0

    finally:
        Path(wav_path).unlink()


def test_rhythm_analysis():
    """Test rhythm analysis using nPVI."""
    wav_path = create_dummy_wav_file()

    try:
        context = AudioContext(wav_path)
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
        assert rhythm.npvi >= 0.0
        assert rhythm.classification in [
            "stress-timed",
            "syllable-timed",
            "insufficient_data",
        ]
        assert len(rhythm.vowel_durations) == len(vowel_timestamps)

    finally:
        Path(wav_path).unlink()


def test_stress_analysis():
    """Test stress pattern analysis."""
    wav_path = create_dummy_wav_file()

    try:
        context = AudioContext(wav_path)
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

    finally:
        Path(wav_path).unlink()


def test_complete_prosody_analysis():
    """Test complete prosody analysis pipeline with voice quality."""
    wav_path = create_dummy_wav_file()

    try:
        context = AudioContext(wav_path)
        analyzer = ProsodyAnalyzer(context)

        vowel_timestamps = [(0.0, 0.1), (0.2, 0.3), (0.4, 0.5), (0.6, 0.7)]
        word_timestamps = [("hello", 0.0, 0.2), ("world", 0.3, 0.5), ("test", 0.6, 0.8)]

        prosody = analyzer.analyze_complete(vowel_timestamps, word_timestamps)

        assert prosody is not None
        assert prosody.pitch is not None
        assert prosody.rhythm is not None
        assert prosody.stress is not None
        assert prosody.voice_quality is not None

    finally:
        Path(wav_path).unlink()


def test_voice_quality_analysis():
    """Test voice quality metrics extraction."""
    wav_path = create_dummy_wav_file()

    try:
        context = AudioContext(wav_path)
        analyzer = ProsodyAnalyzer(context)
        vq = analyzer.analyze_voice_quality()

        assert vq is not None
        assert isinstance(vq.jitter_local, float)
        assert isinstance(vq.shimmer_local, float)
        assert isinstance(vq.cpps, float)
        assert isinstance(vq.spectral_tilt, float)
        assert vq.jitter_local >= 0
        assert vq.shimmer_local >= 0

    finally:
        Path(wav_path).unlink()


if __name__ == "__main__":
    test_audio_context()
    test_pitch_analysis()
    test_rhythm_analysis()
    test_stress_analysis()
    test_complete_prosody_analysis()
    print("\n✅ All audio processor tests passed!")
