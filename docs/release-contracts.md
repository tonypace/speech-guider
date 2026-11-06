# Desktop, offline assets, and acoustic validation

## Student comparison audio

Comparison Lab retains the captured WebM blob associated with a submitted student
analysis. It decodes that same blob into its controller's student AudioBuffer;
server animation frames remain at 50 Hz. The server continues to normalize its
inference input to mono 16 kHz without returning a duplicate base64 student clip.
The controller starts frame/audio clocks at zero, applies playback speed to both,
and invalidates pending decodes on replacement/disposal. Re-recording while an
analysis is pending uses a generation token through response, decode, and commit.
No voiced-frame alignment or TTS time-stretch correction is implied. Audible
synchronization across browser codecs still needs physical device validation.

## Desktop runtime boundary

Development currently owns Python and Tauri together through `npm run dev`, using
loopback port 7860 and `/health` readiness. The Tauri release configuration embeds
Jinja templates; it does not package or start Python. This is not a standalone
release installation, and production Python packaging was excluded from the
original desktop-shell change.

A standalone release must satisfy these requirements before being advertised:

- Package a native, versioned backend executable plus templates/static assets;
  never serve unrendered Jinja as the application's entrypoint.
- Let the native host own one backend process group, readiness timeout, and exit
  cleanup. Bind loopback only, select an available port, and pass it to the WebView.
- Place writable presets in an application-data directory using
  `SPEECH_GUIDER_PRESETS_FILE`; migrate a prior file only after checking both paths.
- Treat ContentVec/R4/TTS weights as separately installed local assets with supplied
  terms, explicit paths, readable errors, and a defined update/revision policy.
- Validate clean-machine launch, occupied ports, backend crash, repeated launches,
  native microphone permissions, clicker flow, and final process cleanup.

The repository has deterministic development-process lifecycle tests; these do
not validate a packaged sidecar, code signing, entitlements, or installer behavior.

## Offline frontend plan

Unused HTMX has been removed. Tailwind's browser CDN compiler and Plotly 2.32.0
remain network dependencies in the template. Before claiming offline classroom
support, replace them through a separate asset/build change:

1. Generate static Tailwind CSS from template and JS class usage, explicitly
   safelisting dynamically constructed classes and keeping its license.
2. Vendor the tested Plotly bundle and license under versioned `static/vendor/`
   paths. Pin hashes and document provenance; keep runtime network fetches absent.
3. Serve only local assets in the template; record the build command and lockfile.
4. Test with external network requests blocked: app load, all tabs, selected/saved
   phonemes, dynamic feedback colors, plots, and native shell rendering.

This plan avoids silently claiming offline support from an online browser test.

## Acoustic validation

Pitch coaching thresholds operate in semitones. Range is
`12 * log2(max(voiced_f0) / min(voiced_f0))`, ignoring zero/nonfinite frames.
`pitch_range` remains Hz for compatibility; `pitch_range_semitones` is explicit.
Tests use exact octave pairs at different base frequencies plus a generated,
integrated 120–240 Hz sweep tracked by Praat. They establish unit consistency and
basic tracking, not universal coaching-threshold suitability.

Voice-quality CPPS and spectral tilt remain heuristic approximations. Changing
those algorithms requires a reference suite beyond generated sine waves:

- Version Praat scripts/settings and results for voiced/unvoiced speech, jittered
  periodic signals, amplitude modulation, noise, and mixtures.
- Compare each metric with a named reference method and declared units/tolerance;
  include short/silent/clipped recordings and sampling-rate changes.
- Keep perceptual coaching thresholds separate from numerical agreement tests.
- Validate with licensed recorded speech covering speakers and recording setups.

Until those checks exist, voice-quality outputs must not be treated as calibrated
clinical or diagnostic measurements. This refactor leaves their formulas intact.
