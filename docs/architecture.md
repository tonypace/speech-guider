# Runtime architecture

Speech Guider is a local FastAPI application serving a Jinja page and vanilla
JavaScript controllers. It has several workflows rather than one enforced
four-stage pipeline. Forced alignment and phoneme-error detection are not fully
implemented; `src/llm` is presently a placeholder.

## Ownership

| Area | Responsibility |
| --- | --- |
| `app/main.py` | App assembly, public Jinja integration, static routes, health |
| `app/api/` | HTTP validation, workflow orchestration, response assembly |
| `app/models/schemas.py` | Pydantic request and response schemas |
| `app/utils/audio.py` | Upload conversion, shared SSL waveform decoding |
| `app/services/` | Process-local inference ownership, progress jobs, atomic preset persistence |
| `src/audio/` | Praat/numpy prosody computation and OmniVoice reference speech |
| `src/models/` | Lazy SSL inference, R4/legacy decoders, articulatory contracts |
| `src/services/` | Model and reference-result caches |
| `static/js/` | Recording, lab controllers, synchronized playback, rendering |
| `app/templates/index.html` | UI composition and existing inline UI behavior |
| `src-tauri/` | Native tray/menu shell around the local web app |

## Analysis

The browser records or uploads audio. Upload conversion creates a temporary WAV;
`load_audio_tensor` decodes, averages channels, resamples, and builds mono 16 kHz
SSL tensors. Analysis combines articulatory inference with Praat prosody and
assembles UI feedback. Temporary upload resources are cleaned by their owner.
Analysis, reference generation, and Prosody Lab share one process-local gate.
Blocking stages run in worker threads; cancellation drains owned work before
releasing the gate or deleting files. See [the progress API](progress-api.md).

`AudioContext` provides Praat audio and downsampled tensors for audio processing.
Praat sample arrays use `[channel, sample]` axes. A mono channel must retain the
whole sample axis, including when resampling.

## Articulatory models and renderer

The default predictor uses local ContentVec-L7 and the R4 bounded temporal decoder.
Legacy decoder support remains isolated in its compatibility module. Model
loading is lazy and cached. The adapter maps model tract variables into the
canonical nine-field renderer state. Preserve field names, ordering, time units,
and normalization from [the contract](articulatory-animation-api.md).

## Reference comparison

Text enters the comparison route, OmniVoice produces reference audio, SSL creates
animation frames, and the reference cache stores both. Cache files are isolated to
each cache instance; failed writes retain new audio in memory. Keys preserve exact
text and include TTS/provider configuration and model asset revisions. Cache methods
are synchronized, and response snapshots do not mutate internal entries.
Model assets/configuration are startup inputs; restart the backend after replacing
model files because the loaded predictor remains cached. The browser comparison
controller owns two tracks and their audio sources, advancing each through a
shared playback path. Speed, seeking, looping, replacement, and destruction must
keep source timing and animation state aligned.

## Prosody and UI

Prosody Lab has a separate lightweight analysis workflow and browser recording
history. Analysis and Prosody Lab share browser conversion mechanics while
retaining their distinct sample-rate choices. Shared capture resource helpers own
listeners, tracks and AudioContexts; each recorder has idempotent init/destroy.
Prosody history persistence is isolated in `prosody_history.js` with bounded,
validated recovery. Student comparison playback uses its retained captured audio.
The SVG renderer owns tract drawing;
lab controllers own interaction. The template and large controllers still contain
mixed presentation/state logic; decomposition is prioritized in the review.

## Current operational limits

Inference gates, progress history, and caches are process-local: run one backend
worker. Presets default to project-root `presets.json`, with an explicit override,
atomic replacement and read-modify-write locking. The desktop release bundle still
has no Python sidecar, and Tailwind/Plotly remain CDN dependencies. See
[release contracts](release-contracts.md) for packaging/offline acceptance and
scientific validation work still needed.
