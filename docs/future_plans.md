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

The initial codebase cleanup stack (`P0.1`–`P4.3`) was completed on **2026-11-17**, and the post-review cleanup, bug-fix, and UX refinement stack (`Section 1`–`Section 3`) was completed and logged in [completed tasks](completed_tasks.md) on **2026-11-19**. The **2026-11-20** project review fixed ten further correctness/lifecycle bugs and identified the CPPS repair below; see the [review report](review-2026-11-20.md). Remaining work tracks that repair, release/hardware validation, and planned domain features.

---

## Priority 1 — Correctness & release validation

### Repair CPPS computation before acoustic threshold validation
- **Finding:** P2, `src/audio/processor.py:281`; `_compute_cpps` constructs frequency bins in Hz and searches them with quefrency bounds in seconds. At 16 kHz with 30 ms frames, both search bounds resolve to index 1, so every frame is skipped and CPPS returns `0.0` even for a periodic harmonic signal.
- **Scope:** Correct the cepstral transform, quefrency axis, and dB baseline together, using a documented Praat reference. An axis-only patch would leave the forward FFT magnitude and output units inconsistent with the CPPS label. Add deterministic periodic/noisy waveform regressions and reference-script comparisons; keep coaching-threshold calibration as the separate domain task below.
- **Evidence:** [2026-11-20 review](review-2026-11-20.md).

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
