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

The initial codebase cleanup stack (`P0.1`–`P4.3`) was completed on **2026-11-17**, and the post-review cleanup, bug-fix, and UX refinement stack (`Section 1`–`Section 3`) was completed and logged in [completed tasks](completed_tasks.md) on **2026-11-19**. The **2026-11-20** project review fixed ten further correctness/lifecycle bugs, and the follow-up Praat-referenced CPPS computation repair was completed and logged in [completed tasks](completed_tasks.md) on **2026-11-20**; see the [review report](review-2026-11-20.md). Remaining work tracks release/hardware validation and planned domain features.

---

## Priority 1 — Correctness & release validation

### Desktop distribution and hardware validation
- **References:** [Desktop release](desktop-release.md), [Release contracts](release-contracts.md), [Stabilization repair evidence](stabilization-2026-11-07.md)
- **Scope:**
  - Measure cold first-launch readiness: one initial frozen-backend startup exceeded the 60-second smoke timeout during the 2026-11-24 rebuild; the startup probe and subsequent frozen/app smoke runs passed.
  - Complete macOS `.pkg` distribution signing, notarization, clean-machine install, WebView microphone/playback verification, and physical clicker verification (`npm run test:e2e:mocked` and `npm run test:e2e:real` already passed).

---

## Priority 2 — Planned features & domain research

### Prosody Lab Audio Mode evaluation after student testing
- **Files:** `app/templates/index.html`, `static/js/prosody_lab.js`, `static/js/prosody_rhythm_views.js`
- **Scope:** Prompt user after student testing to decide between `Synth + Beats` (`synth_beats`) and `Real Voice / TTS Only` (`real_tts`) on `#prosody-audio-mode-select`, then lock in the winning audio mode.

### Acoustic validation for voice quality and coaching thresholds
- **References:** [Release contracts](release-contracts.md)
- **Scope:** Validate heuristic CPPS, spectral tilt, jitter/shimmer, and pitch coaching thresholds against a versioned Praat reference script suite and licensed recorded speech before surfacing clinical/diagnostic claims.

### R4 articulatory hinter sensitivity on poorly enunciated consonants
- **Files:** `src/models/r4_hints.py`, `src/models/r4_contact.py`, `src/models/r4_lip.py`, `src/models/r4_dental.py`
- **Scope:** Observed during testing that some poorly enunciated consonants are still caught by the articulatory hinter and animated as full closures. Audit hinter classifier confidence thresholds, hysteresis, and blending so weak or reduced consonant articulations are not over-corrected in the animation.

### R4 dental hint validation
- **References:** [R4 integration](r4-model-integration.md), `external/R4 final with hinting models/IMPLEMENTATION_NOTES.md`
- **Scope:** Complete blind review and second-speaker validation of the experimental dental / “th” hint before enabling it by default. Compare false dental approaches against existing tongue contacts and lip seals.

### Forced alignment, phoneme error detection, and LLM feedback synthesis
- **References:** [R5 + mHuBERT alignment plan](r5-mhubert-alignment-plan.md)
- **Files:** `src/models/alignment.py`, `src/llm/__init__.py`, `app/api/analyze.py`
- **Scope:** Replace the `ForcedAligner` scaffold with shared `utter-project/mHuBERT-147` + `ctc_v1` IPA forced alignment and 6-category pronunciation weakness diagnostics (feeding real vowel/word timestamps into live nPVI and word stress), plus optional `src/llm/` feedback synthesis on the upcoming R5 branch.
