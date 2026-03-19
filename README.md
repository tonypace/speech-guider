# Pronunciation & Prosody Evaluator

A Python-based application that provides real-time feedback on pronunciation and intonation for language learners, particularly targeting ESL students.

## Features

- **Audio Capture**: Record or upload audio via microphone or file
- **Pronunciation Analysis**: Detect phoneme errors using Wav2Vec2/PyGOP with IPA precision
- **Prosody Analysis**: Extract pitch (F0), rhythm (nPVI), and stress patterns
- **Visual Articulatory Feedback**: Side-by-side vocal tract animations with amber highlighting using Pink Trombone
- **Teacher-Friendly**: Technical linguistic terminology with hover tooltips for explanations
- **Hardware Optimization**: Automatic device detection (MPS > CPU) - optimized for Apple Silicon (~60x faster than CPU) with CPU fallback. Designed for local classroom use.

## Tech Stack

- **Frontend**: Gradio (Python-based UI) with custom HTML5 Canvas animations
- **Backend**: Local Python pipeline
- **Audio Processing**: PyTorch, Torchaudio, Parselmouth (Praat), Transformers (Wav2Vec2)
- **Linguistic Features**: pyclts (Cross-Linguistic Transcription Systems) for IPA feature extraction
- **Visualization**: Custom Pink Trombone JavaScript (visual-only, no audio synthesis)

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
python app.py
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

## Project Structure

```text
speech-guider/
├── app.py                 # Main Gradio entrypoint
├── src/
│   ├── audio/             # Parselmouth/Praat prosody processing
│   ├── models/            # PyTorch Wav2Vec2 models & alignment
│   │   ├── articulatory.py  # pyclts mapping & Pink Trombone params
│   │   ├── alignment.py     # Forced alignment & GOP scoring
│   │   ├── g2p.py          # Grapheme-to-phoneme conversion
│   │   └── wav2vec2.py     # Wav2Vec2 model wrapper
│   └── ui/
│       └── assets/        # Static JS/CSS for vocal tract visualization
│           ├── vocal_tract.js
│           └── vocal_tract.css
├── tests/                 # Pytest test suite
├── requirements.txt       # Dependencies
├── AGENTS.md              # Agent development guidelines
└── README.md              # This file
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

**Note:** Apple Silicon MPS provides ~60x faster inference compared to CPU for Wav2Vec2 models.

**For Other Systems (CPU Only):**
- CPU: Modern multi-core processor
- RAM: 16GB recommended
- Storage: 10GB+ for model caching

## License

This project is licensed under the MIT License.

## Contributing

Contributions are welcome! Please see [AGENTS.md](AGENTS.md) for development guidelines and coding standards.