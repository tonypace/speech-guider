# Pronunciation & Prosody Evaluator

Speech Guider is a local-first pronunciation and prosody coaching app for ESL practice. It records speech, analyzes pronunciation and rhythm, and shows articulatory feedback through an SVG vocal-tract renderer.

## Current Status

- Implemented: ContentVec-based SSL articulatory analysis, SVG articulatory feedback, Animation Lab, Prosody Lab, student-friendly prosody summaries, and the musical-score Prosody Lab display
- In progress: Comparison Lab playback polish and validation, plus the Tauri classroom shell workflow
- Backlog: phoneme-level error detection (requires CTC phoneme model), voice-quality metrics, and end-user help docs

## Features

- **Analysis tab**: record or upload audio, analyze articulatory features and prosody
- **Articulatory feedback**: view mouth shapes via the SVG articulatory renderer using ContentVec-based AAI prediction
- **Animation Lab**: explore and tune canonical phoneme positions directly
- **Prosody Lab**: record short clips, inspect rhythm and pitch, and compare recent takes
- **Musical-score display**: view Prosody Lab pitch as note lanes with truth-mode and lock-to-beat views
- **Comparison Lab**: generate a reference animation from text and compare it side by side with a student trajectory
- **Classroom-ready direction**: Tauri shell and clicker controls are present in the repo but still under validation

## Tech Stack

- **Frontend**: HTML5, Tailwind CSS, vanilla JavaScript
- **Backend**: FastAPI, Jinja2, Server-Sent Events
- **Speech and audio**: PyTorch, Torchaudio, Parselmouth, librosa, `my-voice-analysis`
- **Models**: ContentVec-based SSL with DANN predictor for articulatory inversion (9 tract variables)
- **Visualization**: custom SVG articulatory renderer and Plotly-based prosody charts
- **Desktop shell**: Tauri workspace in `src-tauri/`

## Installation

### Prerequisites

- Python 3.10 or later
- Node.js for JS tests and Tauri tooling
- macOS: `espeak-ng` for phoneme and reference TTS support via `brew install espeak-ng`

### Setup

```bash
source speech-guider/bin/activate
pip install -r requirements.txt
npm install
```

## Running The App

```bash
source speech-guider/bin/activate
python -m app.main
```

Or:

```bash
uvicorn app.main:app --reload
```

The web app runs at `http://localhost:7860`.

For the desktop shell:

```bash
npm run tauri dev
```

## How To Use

1. Open the `Analysis` tab and enter or keep the target sentence.
2. Hold the record button or upload audio.
3. Run analysis to get articulatory and prosody feedback.
4. View the articulatory animation showing your vocal tract shape.
5. Use `Animation Lab` to explore individual phoneme shapes.
6. Use `Prosody Lab` to compare recent recordings with rhythm and pitch views.
7. Use `Comparison Lab` to prepare a reference animation from text and compare it with a student recording.

## Development

### Python

```bash
ruff format .
ruff check . --fix
mypy .
pytest
```

### JavaScript

```bash
npm run test:run
```

### End-to-end tests

```bash
npm run test:e2e:mocked
npm run test:e2e:real
```

For detailed development guidance, see `AGENTS.md`.

For the canonical 9-variable articulatory animation contract, see `docs/articulatory-animation-api.md`.

## Active Work

- `add-ssl-comparison-playback`: remaining work is mostly tests, validation, docs, and some playback plumbing
- `add-tauri-classroom-shell`: remaining work is microphone, clicker-flow, and browser-vs-Tauri validation

Recently archived completed changes include SSL-based animation, Prosody Lab voice analysis, student-friendly prosody feedback, and the musical-score display.

## Project Structure

```text
speech-guider/
├── app/
│   ├── api/
│   │   ├── analyze.py
│   │   ├── comparison.py
│   │   ├── prosody_lab.py
│   │   ├── presets.py
│   │   ├── errors.py
│   │   └── sse.py
│   ├── templates/
│   │   └── index.html
│   └── main.py
├── static/
│   ├── css/
│   │   └── vocal_tract.css
│   └── js/
│       ├── app.js
│       ├── recorder.js
│       ├── prosody_lab.js
│       ├── comparison_lab.js
│       ├── ssl_comparison_controller.js
│       ├── svg_articulatory_renderer.js
│       ├── tauri_controller.js
│       └── ipa_tooltips.js
├── src/
│   ├── audio/
│   │   ├── processor.py
│   │   ├── prosody_lab.py
│   │   └── reference_tts.py
│   ├── models/
│   │   ├── aai_adapter.py
│   │   ├── alignment.py
│   │   ├── articulatory.py
│   │   ├── articulatory_calibration.py
│   │   ├── contentvec.py
│   │   ├── g2p.py
│   │   ├── hubert.py
│   │   └── ssl_aai_predictor.py
│   └── services/
│       └── comparison_cache.py
├── src-tauri/
├── tests/
├── docs/
├── openspec/
├── README.md
└── PROJECT.md
```

## Hardware Notes

- Apple Silicon MPS is the preferred acceleration path
- CPU fallback is supported for local use, but slower
- Leave enough storage for local model caches and generated assets

## License

This project is licensed under the MIT License.
