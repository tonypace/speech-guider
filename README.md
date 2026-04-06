# Pronunciation & Prosody Evaluator

A Python-based application that provides real-time feedback on pronunciation and intonation for language learners, particularly targeting ESL students.

## Features

- **Audio Capture**: Record or upload audio via microphone or file
- **Pronunciation Analysis**: Detect phoneme errors using local SSL models, with deprecated Wav2Vec2 fallback retained for legacy alignment
- **Prosody Analysis**: Extract pitch (F0), rhythm (nPVI), and stress patterns
- **Visual Articulatory Feedback**: Side-by-side vocal tract animations with amber highlighting using the SVG articulatory renderer
- **Teacher-Friendly**: Technical linguistic terminology with hover tooltips for explanations
- **Hardware Optimization**: Automatic device detection (MPS > CPU) - optimized for Apple Silicon (~60x faster than CPU) with CPU fallback. Designed for local classroom use.

## Tech Stack

- **Frontend**: HTML5/Tailwind CSS with vanilla JavaScript
- **Backend**: FastAPI with Server-Sent Events (SSE) for real-time updates
- **Audio Processing**: PyTorch, Torchaudio, Parselmouth (Praat), Transformers (DistilHuBERT primary, deprecated Wav2Vec2 fallback)
- **Linguistic Features**: pyclts (Cross-Linguistic Transcription Systems) for IPA feature extraction
- **Visualization**: Custom SVG articulatory renderer with vanilla JavaScript controls

## Installation

### Prerequisites

- Python 3.10 or later
- Virtual environment (recommended)

### Setup

```bash
# Activate the existing venv
source speech-guider/bin/activate  # On macOS/Linux
# speech-guider\Scripts\activate  # On Windows

# Install dependencies (if not already installed)
pip install -r requirements.txt
```

**System Requirements:**
- **macOS:** Ensure `espeak-ng` is installed for phoneme conversion: `brew install espeak-ng`
- **Apple Silicon:** Automatically uses MPS for acceleration (~60x faster than CPU) on macOS 12.3+.
- **CPU Fallback:** Works on any CPU (slower but functional).

## Usage

### Running the Application

```bash
# Activate venv first, then:
source speech-guider/bin/activate
python -m app.main
# or
uvicorn app.main:app --reload
```

The application will launch a web interface at `http://localhost:7860`.

### How to Use

1. Read the target sentence displayed in the UI
2. Click the microphone to record your pronunciation (or upload a .wav file)
3. Click "Analyze Pronunciation" to receive feedback
4. Select detected pronunciation errors from the list
5. Click "Animate" to see side-by-side vocal tract comparisons
6. Hover over technical terms for plain-English explanations
7. Amber highlighting shows which part of the mouth/tongue needs correction
8. Practice and try again!

## Development

### Code Quality

We maintain strict code quality standards using automated tools:

```bash
# Format code
ruff format .

# Run linter and auto-fix simple issues
ruff check . --fix

# Run static type checking
mypy .
```

### Testing

We use `pytest` for all unit and integration tests:

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_articulatory.py

# Run tests with verbose output
pytest -v
```

For detailed development guidelines, see [AGENTS.md](AGENTS.md).

For the canonical 9-variable articulatory animation contract and dataset translation guidance, see [docs/articulatory-animation-api.md](docs/articulatory-animation-api.md).

## Project Structure

```text
speech-guider/
├── app/                   # FastAPI application
│   ├── main.py           # FastAPI entrypoint
│   ├── api/              # API endpoints (analysis, presets, errors, sse)
│   ├── services/         # Business logic (state, concurrency)
│   ├── utils/            # Utilities (audio)
│   └── templates/        # Jinja2 HTML templates
│       └── index.html    # Main UI
├── static/               # Static assets
│   ├── js/               # JavaScript modules (app bootstrap + components)
│   │   ├── app.js
│   │   ├── svg_articulatory_renderer.js
│   │   ├── recorder.js
│   │   ├── prosody_lab.js
│   │   └── ipa_tooltips.js
│   └── css/              # CSS files (vocal_tract, etc.)
│       └── vocal_tract.css
├── src/                  # Python source modules
│   ├── audio/            # Parselmouth/Praat prosody processing
│   │   └── processor.py
│   └── models/           # PyTorch SSL models, adapters, and alignment
│       ├── articulatory.py  # pyclts mapping & SVG articulatory state
│       ├── alignment.py     # Forced alignment & GOP scoring
│       ├── g2p.py          # Grapheme-to-phoneme conversion
│       ├── hubert.py       # DistilHuBERT SSL model wrapper
│       ├── wav2vec2.py     # Deprecated Wav2Vec2 fallback wrapper
├── tests/                # Pytest test suite
├── docs/                 # Project and integration documentation
│   └── articulatory-animation-api.md
├── requirements.txt      # Dependencies
├── AGENTS.md             # Agent development guidelines
└── README.md             # This file
```

## Hardware Recommendations

### Minimum Configuration
- CPU: Modern multi-core processor (Apple M1/M2 or Intel/AMD equivalent)
- RAM: 8GB minimum
- Storage: 5GB free space for models

### Recommended Configuration

**For Apple Silicon (Optimized):**
- Chip: M1/M2/M3 Pro/Max/Ultra (with unified memory)
- RAM: 16GB minimum
- Storage: 10GB+ for model caching
- OS: macOS 12.3+

**Note:** Apple Silicon MPS remains the preferred local acceleration path for SSL models, including DistilHuBERT.

**For Other Systems (CPU Only):**
- CPU: Modern multi-core processor
- RAM: 16GB recommended
- Storage: 10GB+ for model caching

## License

This project is licensed under the MIT License.

## Contributing

Contributions are welcome! Please see [AGENTS.md](AGENTS.md) for development guidelines and coding standards.
