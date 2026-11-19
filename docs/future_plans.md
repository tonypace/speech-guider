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
