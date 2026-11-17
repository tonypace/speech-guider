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

The initial codebase cleanup stack (`P0.1`–`P4.3`) was completed and logged in [completed tasks](completed_tasks.md) on **2026-11-17**. Remaining open work below tracks release/hardware validation, planned features, and minor deferred cleanup.

---

## Priority 1 — Release & live-environment validation

### Desktop distribution, E2E, and hardware validation
- **References:** [Desktop release](desktop-release.md), [Release contracts](release-contracts.md), [Stabilization repair evidence](stabilization-2026-11-07.md)
- **Scope:**
  - Run `npm run test:e2e:mocked` in a non-sandboxed environment supporting loopback server binding (verifying updated `offlineAssets.spec.js` and `prosodyLab.spec.js`; `npm run test:e2e:real` passed per user run after `serial` fix).
  - Complete macOS `.pkg` distribution signing, notarization, clean-machine install, WebView microphone/playback verification, and physical clicker verification.

---

## Priority 2 — Planned features & domain research

### Prosody Lab feature implementation
- **Context:** `#tab-btn-prosody` remains `hidden` in `app/templates/index.html` pending a dedicated feature pass.
- **Scope:** Un-hide Prosody Lab when ready, build the measurement timeline and event diagnostics, replace unvalidated FFT/energy heuristics in `src/audio/prosody_lab.py` with validated syllable/timing and speech-rate metrics, and define sliding-window nPVI semantics.

### Acoustic validation for voice quality and coaching thresholds
- **References:** [Release contracts](release-contracts.md)
- **Scope:** Validate heuristic CPPS, spectral tilt, jitter/shimmer, and pitch coaching thresholds against a versioned Praat reference script suite and licensed recorded speech before surfacing clinical/diagnostic claims.

### Forced alignment, phoneme error detection, and LLM feedback synthesis
- **Files:** `src/models/alignment.py`, `src/llm/__init__.py`, `app/api/analyze.py`
- **Scope:** Replace the `ForcedAligner` scaffold with a real phoneme CTC / forced-alignment model so `/api/analyze` supplies real vowel/word timestamps (enabling live nPVI and word stress), phoneme errors, and optional `src/llm/` feedback synthesis.

---

## Priority 3 — Minor deferred technical cleanup

### Remaining single-load analysis and test fixture deduplication
- **Files:** `app/api/analyze.py`, `app/api/comparison.py`, `tests/test_analyze_failure_modes.py`, `tests/test_integration_prosody.py`, `tests/test_ssl_aai_predictor.py`
- **Scope:**
  - Unify `AudioContext` + `_load_and_preprocess_audio` in `app/api/analyze.py` into a single disk read once `tests/test_inference_ownership.py` and `tests/test_analyze_failure_modes.py` mock contracts are updated together.
  - Consolidate shared SSL trajectory framing across `analyze.py` and `comparison.py` (`AnimationFrame` vs `CANONICAL_ARTICULATORY_FIELDS`) and migrate the remaining inline WAV generators in `test_analyze_failure_modes.py`, `test_integration_prosody.py`, and `test_ssl_aai_predictor.py` to `tests/conftest.py`.
