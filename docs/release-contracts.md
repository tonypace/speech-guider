# Desktop, offline assets, and acoustic validation

## Student comparison audio

Comparison Lab converts the captured recording to mono 16 kHz PCM WAV in the
browser. It uploads that clip for analysis and uses it to prepare student
playback. Comparison playback trims quiet edges on both tracks and keeps up to
100 ms of padding at each detected edge. It maps the playback position back to
the original 50 Hz animation frames.

**Match duration** is opt-in for each take. It uses pitch-preserving media
playback to match the trimmed reference duration when the required rate is
within 15% of the original and the recording passes minimum activity checks.
Duration and activity are heuristics. The learner confirms that the recording
contains all the target words.

## Desktop runtime

The [standalone macOS build](desktop-release.md) packages a native backend, rendered
web app inputs, and local frontend assets. The shell owns the backend process group;
the backend binds an OS-selected loopback port and writes a PID-bound readiness file.
The shell checks health before navigation and shows local startup or crash feedback.
Presets and prosody summaries persist in app data across port changes; model assets
remain separately installed with their supplied terms.

The local release target is Apple Silicon on macOS 26+. Distribution signing,
notarization, a clean-machine install, physical microphone permissions, clicker
hardware, and real-recording playback are separate validation steps.

## Offline frontend

Tailwind 3.4.19 is compiled to static CSS. The lockfile,
licenses and checksum manifest record provenance. Use `npm run assets:build` after
changing UI classes and `npm run assets:check` to verify artifacts. The offline
browser check blocks external requests and covers all tabs, saved presets, dynamic
feedback styles and rendered SVG visualizations. See [asset provenance](../static/vendor/README.md).

## Acoustic validation

Pitch coaching thresholds operate in semitones. Range is
`12 * log2(max(voiced_f0) / min(voiced_f0))`, ignoring zero/nonfinite frames.
`pitch_range` remains Hz for compatibility; `pitch_range_semitones` is explicit.
Tests use exact octave pairs at different base frequencies plus a generated,
integrated 120–240 Hz sweep tracked by Praat. They establish unit consistency and
basic tracking, not universal coaching-threshold suitability.

CPPS is computed via Praat `PowerCepstrogram: Get CPPS` (Maryn & Weenink 2015 parameters, dB units) and verified against the versioned reference script `tests/fixtures/praat/cpps_maryn_weenink_2015.praat` across synthetic waveforms (periodic harmonics, jittered/noisy/mixed signals, AM/clipping, multi-rate, stereo, and edge cases) and the `tests/e2e/fixtures/test-audio.wav` fixture. Spectral tilt, jitter, and shimmer remain heuristic metrics, and perceptual/clinical coaching thresholds still require licensed multi-speaker corpus validation before surfacing diagnostic claims:

- Version Praat scripts/settings and results for voiced/unvoiced speech, jittered
  periodic signals, amplitude modulation, noise, and mixtures.
- Compare each metric with a named reference method and declared units/tolerance;
  include short/silent/clipped recordings and sampling-rate changes.
- Keep perceptual coaching thresholds separate from numerical agreement tests.
- Validate with licensed recorded speech covering speakers and recording setups.

Until those checks exist, voice-quality outputs must not be treated as calibrated
clinical or diagnostic measurements.
