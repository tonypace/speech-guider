# Frontend review and refactor

Reviewed module boundaries, template loading, renderer lifecycle, recording, comparison request handling, storage, and tooltip rendering against the existing dirty worktree. Existing frontend changes were almost entirely formatting (`git diff -w`); preserved those changes.

## Implemented

- Added `static/js/audio_conversion.js` as the shared temporary decoding boundary. Analysis retains its 16 kHz request, prosody retains 44.1 kHz, and both retain their existing PCM encoders. Temporary AudioContexts now close after failed decode or encode as well as successful conversion.
- Centralized comparison source creation/disposal. Playback speed now applies to audible audio; seeking during playback restarts audio at the displayed position; loops restart audio together with frames and preserve overshoot.
- Replaced duplicate reference/student timeline advancement with one method. Zero-valued initial clock readings no longer discard the first elapsed interval.
- Track replacement pauses playback, resets position, and clears previous audio. Per-track decode versions prevent obsolete asynchronous decodes from restoring cleared or replaced buffers.
- Added regression coverage for audio context release, preserved sample rates/encoder delegation, speed, seek, loop, zero clock origin, replacement, and out-of-order decode completion.

Public window APIs, template controls, SVG geometry, server routes, PCM encoding and storage schemas remain unchanged.

## Architecture and followups

- `app.js` coordinates globals, tab switching, presets, and analysis renderers. `recorder.js` handles analysis capture/submission. `prosody_lab.js` combines capture, history/storage, plots, and score rendering. `comparison_lab.js` owns requests/UI and delegates timelines/audio to `ssl_comparison_controller.js`. SVG rendering and IPA tooltips have separate modules; Tauri keyboard/menu behavior remains isolated in its bridge.
- **Comparison request race:** `handleTextInput` clears text without aborting an outstanding reference request; request checks also precede asynchronous audio decode. A request can still mark reference ready after input changes during decode. Followup should coordinate a request generation token across fetch, decode, and UI commit, with delayed-decode UI tests.
- **Capture lifetime:** analysis and prosody each acquire a microphone stream during initialization, retain document listeners, and lack an explicit destroy path. Repeated initialization can acquire extra streams/contexts. Comparison also permits repeated clicks while microphone permission is pending. Consolidating capture ownership needs permission, rapid-click, tab-change, and disposal tests.
- **Student playback:** comparison loads student frames with null audio, so student playback remains frame-only. Integrating captured/normalized audio requires an explicit backend/frontend audio contract.
- **Trust boundary:** feedback/descriptions intentionally accept server HTML; error labels, history entries, and tooltip data also reach HTML sinks. A separate hardening change should distinguish trusted server markup from plain text and test hostile input, rather than silently altering rendering during this refactor.
- **Storage recovery:** animation preset selection parses localStorage without recovery; malformed persisted JSON can interrupt selection. Prosody storage/plotting is a candidate for a separate pure-data module once persistence behavior is covered.
- **Style and dependencies:** template contains a few layout inline styles while most custom styles live in `vocal_tract.css`; external Tailwind, HTMX and Plotly scripts remain CDN dependencies. Moving style boundaries or bundling assets should be a separate visual/build change.
- **Test quality:** existing recorder tests frequently guard assertions with `if (recorder)` and mock rendering behavior; existing test environment emits jsdom canvas warnings. New tests assert concrete audio lifecycle behavior, but they do not replace browser/device validation.

## Validation

- `npm run test:run`: 6 files passed; 100 tests passed, 1 existing skipped test. Existing jsdom canvas warnings remain.
- `npx eslint static/js tests/js --no-warn-ignored`: 0 errors and 0 warnings after removing unused trailing parameters/locals and strengthening the file-input listener assertion.
- No browser or native Tauri audio-device run performed. Audible playback changes are verified with explicit source/clock mocks, not physical hardware.
