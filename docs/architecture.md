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
| `app/services/` | Process-local concurrency, SSE queues, preset persistence |
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
The main analysis concurrency guard is process-local; it does not currently
serialize every inference endpoint.

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
each cache instance; failed writes retain new audio in memory. The browser comparison
controller owns two tracks and their audio sources, advancing each through a
shared playback path. Speed, seeking, looping, replacement, and destruction must
keep source timing and animation state aligned.

## Prosody and UI

Prosody Lab has a separate lightweight analysis workflow and browser recording
history. Analysis and Prosody Lab share browser conversion mechanics while
retaining their distinct sample-rate choices. The SVG renderer owns tract drawing;
lab controllers own interaction. The template and large controllers still contain
mixed presentation/state logic; decomposition is prioritized in the review.

## Current operational limits

SSE exists but lacks a complete discoverable job/subscription lifecycle. Several
async routes perform blocking computation. Presets are stored in a working-directory
JSON file. Caches and gates are single-process, and the desktop release bundle
has no Python sidecar. These are explicit remaining design tasks, not guarantees
provided by the current architecture.
