# Future plans — working stack

This document is the active, priority-ordered **working stack** for cleanup, bug fixes, refactoring, and technical improvements in `speech-guider`. Higher priorities appear first; within each tier, items are ordered so top items can be popped next.

## Stack workflow

1. Read this stack and [completed tasks](completed_tasks.md) before starting cleanup or improvement work.
2. Pop the top unblocked item (or the specific item requested by the user).
3. Implement the change with tests and verify the full quality gate (`npm run check`).
4. Remove the completed item from this file and record it in [completed_tasks.md](completed_tasks.md) with the completion date, touched files, and verification notes.
5. Push newly discovered bugs, technical debt, or follow-up work into the appropriate priority tier here.

---

## Stack status

The initial codebase cleanup stack (`P0.1`–`P4.3`) was completed and logged in [completed tasks](completed_tasks.md) on **2026-11-17**. A full 3-agent review on **2026-11-19** queued the cleanup, bug-fix, and UX improvement sections below (`Section 1`–`Section 3`), followed by release validation and planned domain research.

---

## Priority 0 — Post-review cleanup, bug fixes & UX refinement (2026-11-19)

### Section 2 — Fix bugs, lifecycle leaks, architecture & test hygiene
- **2.1 Tauri controller & desktop config fixes:** Sync `TauriController.currentMode` with active tab (`speechguider:tabchange`) and default `'analysis'` tab on startup; add `"Prosody Lab"` item to system tray (`src-tauri/src/main.rs`); fix `<200ms` short `Tab` press leaving microphone stuck recording; ignore shortcuts when focus is inside `input`/`textarea`/`select` or modifier keys are pressed; read `window.currentErrors` dynamically instead of 2000ms `setTimeout`; align `minimumSystemVersion` in `src-tauri/tauri.release.conf.json` with `src-tauri/tauri.conf.json`.
- **2.2 Comparison Lab Loop In/Out buttons:** Add `'comparison-loop-in'` and `'comparison-loop-out'` to `updateUIState()` controls in `static/js/comparison_lab.js` and display active loop bounds.
- **2.3 Upload/audio error handling (`400`/`413` vs `500`):** Catch `AudioConversionError` and `ValueError` in `app/api/analyze.py` and `app/api/prosody_lab.py` (moving `save_upload_to_temp` inside `try:`) to return HTTP `400`/`413` instead of `500`.
- **2.4 AudioContext, RAF loop & stale error cleanup:** Close `ProsodyAudioPlayer` `AudioContext` on destroy and prune finished nodes in `activeNodes`; stop Prosody playback and 2-bar `requestAnimationFrame` loop when switching away from `prosody` tab; stop `svgLeftRenderer`/`svgRightRenderer` animation loops and re-hide `#articulatory-section` when a new analysis has 0 errors or user switches tabs.
- **2.5 Recorder parity & error message surfacing:** Ensure `ProsodyLabRecorder` respects `getSettings().microphone_enabled === false` and HTTPS/localhost check; encapsulate `resetInput()` on recorder classes; add `catch` block around `convertToWav` in `IntercomRecorder.sendForAnalysis`; parse backend `{ detail, error }` JSON on HTTP error responses in `recorder.js` and `prosody_lab.js`.
- **2.6 Prosody Lab in-memory analysis & unified Praat pitch track:** Avoid redundant temp-WAV disk write/re-read in `generate_prosody_reference` and drive `_compute_pitch_track` from the shared Praat `Sound` / autocorrelation pitch object in `src/audio/prosody_lab.py`.
- **2.7 Typing & test suite coverage/hygiene:** Enable `strict_optional = true` in `pyproject.toml`, add `ProsodyLabPhrase` schema in `app/models/schemas.py`, add `TestClient` tests for `POST /api/reference-animation` and `POST /api/prosody-lab/analyze`, add unit tests for `app/desktop_backend.py`, and fix `tests/test_articulatory.py`, `tests/test_audio_utils_failure.py`, and `tests/test_analyze_failure_modes.py`.

### Section 3 — Design & usability (UX/UI) improvements
- **3.1 Recording interaction & cutoff fix:** Prevent accidental `mouseleave` recording cutoff during hold-to-record, add keyboard `Space`/`Enter` support on focused record buttons, and unify record button styling/semantics.
- **3.2 Cross-tab target sentence sync & contextual instructions:** Sync target sentence across `Analysis`, `Comparison Lab`, and `Prosody Lab (Custom)`; move `#tab-panel-analysis` instructions inside `#tab-panel-analysis`; add a direct `"Compare with Reference in Comparison Lab"` action from `Analysis` results.
- **3.3 Learner-friendly Analysis & Prosody Lab defaults:** Compute acoustic vocalic nPVI in `/api/analyze` when forced alignment is absent and replace raw pipeline diagnostic strings with learner-friendly metrics; in Prosody Lab, hide `#prosody-custom-sentence-bar` unless `5. Custom Sentence (TTS)...` is selected, auto-select `Latest Recorded Take (Student)` once recorded, and open coaching/history `<details>` by default.
- **3.4 Vocal tract anatomical legend, dynamic pose preview & playback speed clarity:** Add anatomical orientation labels to `SvgArticulatoryRenderer`, animate tongue/jaw pose transition on `Animate` button click, and clarify slow-motion playback speed (`0.3x` / `0.5x` / `1.0x`).
- **3.5 Accessibility & color semantics:** Add `role="tablist"` / `role="tab"` / `role="tabpanel"` / `aria-selected` to main and Prosody tabs; make `.ipa-phoneme` tooltips keyboard-focusable (`tabindex="0"`, `focusin`/`focusout`); replace blocking `window.alert()` in `recorder.js` with inline status banners; fix inverted target/error phoneme colors in `recorder.js`.

---

## Priority 1 — Release & live-environment validation

### Desktop distribution and hardware validation
- **References:** [Desktop release](desktop-release.md), [Release contracts](release-contracts.md), [Stabilization repair evidence](stabilization-2026-11-07.md)
- **Scope:**
  - Complete macOS `.pkg` distribution signing, notarization, clean-machine install, WebView microphone/playback verification, and physical clicker verification (`npm run test:e2e:mocked` and `npm run test:e2e:real` already passed).

---

## Priority 2 — Planned features & domain research

### Prosody Lab Audio Mode evaluation after student testing
- **Files:** `app/templates/index.html`, `static/js/prosody_lab.js`, `static/js/prosody_rhythm_views.js`
- **Scope:** Prompt user after student testing to decide between `Synth + Beats` (`synth_beats`) and `Real Voice / TTS Only` (`real_tts`) on `#prosody-audio-mode-select`, then lock in the winning audio mode.

### Acoustic validation for voice quality and coaching thresholds
- **References:** [Release contracts](release-contracts.md)
- **Scope:** Validate heuristic CPPS, spectral tilt, jitter/shimmer, and pitch coaching thresholds against a versioned Praat reference script suite and licensed recorded speech before surfacing clinical/diagnostic claims.

### Forced alignment, phoneme error detection, and LLM feedback synthesis
- **Files:** `src/models/alignment.py`, `src/llm/__init__.py`, `app/api/analyze.py`
- **Scope:** Replace the `ForcedAligner` scaffold with a real phoneme CTC / forced-alignment model so `/api/analyze` supplies real vowel/word timestamps (enabling live nPVI and word stress), phoneme errors, and optional `src/llm/` feedback synthesis.
