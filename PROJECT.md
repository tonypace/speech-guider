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

## Architecture

### Backend

- **Framework**: FastAPI with Jinja2 templates and SSE support
- **Primary endpoints**:
  - `app/api/analyze.py` for pronunciation analysis
  - `app/api/comparison.py` for reference animation generation
  - `app/api/prosody_lab.py` for Prosody Lab workflows
  - `app/api/presets.py`, `app/api/errors.py`, and `app/api/sse.py` for supporting UI behavior

### Audio And Model Pipeline

1. **Audio capture and normalization**: microphone or upload input is standardized for downstream processing
2. **Articulatory extraction**: ContentVec + DANN-based AAI predictor for 9 tract variables (robust_01 normalized)
3. **Articulatory inference**: SSL outputs are translated through `src/models/ssl_aai_predictor.py` and `src/models/aai_adapter.py`
4. **Prosody extraction**: Parselmouth, `librosa.pyin`, and `my-voice-analysis` provide pitch, rhythm, and recording summaries
5. **Reference generation**: `src/audio/reference_tts.py` plus `src/services/comparison_cache.py` prepare cached comparison assets
6. **Visualization**: frontend consumes canonical articulatory states and Plotly-ready prosody payloads

### Frontend

- **Delivery model**: server-rendered HTML with static JS and CSS
- **State model**: vanilla JavaScript on `window` plus module-based helpers
- **Key UI modules**:
  - `static/js/recorder.js`
  - `static/js/prosody_lab.js`
  - `static/js/comparison_lab.js`
  - `static/js/ssl_comparison_controller.js`
  - `static/js/svg_articulatory_renderer.js`
  - `static/js/tauri_controller.js`

### Desktop Shell

- `src-tauri/` contains the native shell workspace
- Phase 1 desktop support is focused on launch shortcuts, menu-bar presence, and classroom clicker semantics rather than a separate frontend rewrite

## OpenSpec Status

### Active Changes

- `add-ssl-comparison-playback`
- `add-tauri-classroom-shell`

### Recently Archived Completed Changes

- `add-ssl-based-animation`
- `add-student-friendly-prosody-feedback`
- `add-musical-score-prosody-display`
- `add-prosody-lab-voice-analysis`

## Project Structure

```text
speech-guider/
├── app/
│   ├── api/
│   ├── models/
│   ├── services/
│   ├── templates/
│   ├── utils/
│   └── main.py
├── static/
│   ├── css/
│   └── js/
├── src/
│   ├── audio/
│   ├── models/
│   ├── services/
│   └── llm/
├── src-tauri/
├── tests/
│   ├── js/
│   └── e2e/
├── docs/
├── openspec/
├── requirements.txt
├── package.json
├── README.md
└── PROJECT.md
```

## Key Files

- `app/main.py`: FastAPI entrypoint, router setup, static mounting, and root page rendering
- `app/templates/index.html`: main multi-tab UI shell
- `app/api/analyze.py`: pronunciation analysis and feedback response assembly
- `app/api/comparison.py`: reference animation generation endpoint
- `app/api/prosody_lab.py`: Prosody Lab analysis routes
- `src/models/aai_adapter.py`: AAI tract-variable to renderer-state conversion
- `src/models/ssl_aai_predictor.py`: SSL articulatory prediction layer
- `src/models/articulatory.py`: canonical articulatory mapping and preset behavior
- `src/audio/reference_tts.py`: reference TTS provider abstraction
- `src/services/comparison_cache.py`: cached reference asset storage for comparison playback

## Running The Project

### Setup

```bash
source speech-guider/bin/activate
pip install -r requirements.txt
npm install
```

### Web App

```bash
source speech-guider/bin/activate
python -m app.main
```

Or:

```bash
uvicorn app.main:app --reload
```

### Tauri Shell

```bash
npm run tauri dev
```

## Development Commands

### Python quality checks

```bash
ruff format .
ruff check . --fix
mypy .
pytest
```

### JavaScript and browser tests

```bash
npm run test:run
npm run test:e2e:mocked
npm run test:e2e:real
```

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

Last updated: 2026-04-17
