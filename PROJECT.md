# Speech Guider - PROJECT.md

## Goal

Help ESL students hear, see, and compare how their speech differs from a fluent target by combining pronunciation analysis, prosody analysis, and articulatory visualization.

## Project Overview

Speech Guider is a local-first pronunciation and prosody evaluator built around four teaching surfaces:

- **Analysis** for sentence-based pronunciation review
- **Articulatory Feedback** for incorrect-vs-target mouth-shape comparison
- **Animation Lab** for direct phoneme exploration and preset tuning
- **Prosody Lab** and **Comparison Lab** for rhythm, pitch, and side-by-side trajectory comparison

## Current Product State

### Implemented

- SSL-based articulatory inference pipeline using AAI-style intermediate tract variables
- SVG articulatory renderer with corrected tongue geometry and canonical 9-variable contract
- Main pronunciation analysis flow with IPA-aware feedback and articulatory review
- Prosody Lab with short-recording history, prosody summaries, and musical-score visualization
- Student-friendly prosody wording in the main analysis panel
- Reference-generation pipeline and Comparison Lab UI foundations
- Tauri shell foundation and classroom-control bridge scaffolding

### Still Open

- Phoneme-level error detection (requires CTC phoneme model integration)
- Comparison Lab test coverage, end-to-end validation, and remaining playback plumbing
- Tauri microphone and clicker-flow validation in real use
- Model loading and lifecycle optimization
- Voice-quality metrics such as jitter, shimmer, CPPS, and spectral tilt
- User-facing documentation and help flows

## Architecture and development

The maintained [architecture guide](docs/architecture.md) describes implemented
ownership and workflows. See [development](docs/development.md) for setup and
checks, and [review/refactor](docs/review-refactor.md) for remaining cleanup.
The default articulatory model is ContentVec-L7 plus R4; legacy DANN descriptions
refer to historical implementations.

## OpenSpec Status

### Active Changes

- `add-ssl-comparison-playback`
- `add-tauri-classroom-shell`

### Recently Archived Completed Changes

- `add-ssl-based-animation`
- `add-student-friendly-prosody-feedback`
- `add-musical-score-prosody-display`
- `add-prosody-lab-voice-analysis`

## Constraints And Priorities

- Keep the app local-first and classroom-friendly
- Preserve the canonical renderer contract so backend and frontend stay aligned
- Prefer Apple Silicon acceleration when available, but keep CPU fallback working
- Avoid introducing unnecessary frontend framework complexity

## Near-Term Priorities

1. Finish Comparison Lab validation and documentation.
2. Validate Tauri classroom workflows with real microphone and clicker behavior.
3. Reduce model startup and cache-management overhead.
4. Add voice-quality analysis once the current comparison and desktop flows settle.

---

Last updated: 2026-11-06
