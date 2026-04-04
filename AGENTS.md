# Agent Guidelines for speech-guider

Welcome! You are an AI agent operating in the `speech-guider` repository. This file provides the essential context, commands, and code style guidelines you must follow to ensure consistency and reliability.

## 1. Project Overview & Architecture
This is a Pronunciation & Prosody Evaluator application.
- **Frontend**: HTML5/Tailwind CSS with vanilla JavaScript
- **Backend**: FastAPI with Server-Sent Events (SSE) for real-time updates
- **Audio Processing**: PyTorch, Torchaudio, Parselmouth (Praat), Transformers (Wav2Vec2)
- **Synthesis Engine**: Local/Remote LLM (Ollama, Gemini, OpenAI)

The audio pipeline follows a strict 4-step architecture:
1. Audio Capture & Forced Alignment
2. Pronunciation Extraction (Wav2Vec2/PyGOP)
3. Prosody Extraction (Parselmouth/Praat)
4. Diagnostic Synthesis (LLM)

### Project Status
- [x] Project initialization (AGENTS.md, directory structure)
- [x] Requirements files (CPU-only and CUDA variants)
- [x] FastAPI backend with SSE
- [x] Parselmouth pitch (F0) extraction
- [x] Test fixtures for dummy audio generation
- [x] CI/CD tooling (ruff, mypy, pytest)
- [x] Forced alignment implementation (Wav2Vec2)
- [x] Apple Silicon MPS optimization (~60x faster than CPU)
- [x] Phonetic Error Detection with IPA and G2P integration
- [x] Goodness of Pronunciation (PyGOP) scoring system
- [x] Targeted error Classification (voicing, substitutions)
- [x] HTML5/Tailwind frontend with vocal tract visualization
- [x] Prosody metrics (nPVI, stress patterns) - COMPLETED
- [x] Visual articulatory feedback (pyclts + Pink Trombone) - COMPLETED
- [x] IPA phoneme tooltips with hover examples - COMPLETED
- [ ] Model loading/management optimizations
- [ ] Voice quality analysis (Jitter, Shimmer, CPPS, Spectral Tilt)
- [ ] User documentation/help guides

### Expected Directory Structure
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
│   ├── js/               # JavaScript files (pink_trombone, recorder, tooltips)
│   └── css/              # CSS files (vocal_tract, etc.)
├── src/                  # Python source modules
│   ├── audio/            # Parselmouth/Praat prosody processing
│   └── models/           # PyTorch Wav2Vec2 models & alignment
├── tests/                # Pytest test suite
├── requirements.txt      # Dependencies
└── AGENTS.md             # You are here
```

## 2. Environment & Commands

### Setup
We use a Python virtual environment for development and testing. JavaScript linting requires Node.js.
```bash
# Activate the venv (macOS/Linux)
source speech-guider/bin/activate

# Activate the venv (Windows)
speech-guider\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt

# Install JavaScript linter (requires Node.js)
npm install

# Note: macOS requires 'espeak' for phoneme conversion:
# brew install espeak-ng
```

### Running the App
To run the main FastAPI application locally:
```bash
# Activate venv first, then:
python -m app.main
# or
uvicorn app.main:app --reload
```

### Testing
Run tests with pytest:
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_articulatory.py

# Run tests with verbose output
pytest -v
```

### Linting & Formatting
We strictly use `ruff` for fast linting/formatting, and `mypy` for static type checking on Python files. JavaScript files use `eslint` (requires Node.js).
```bash
# Format Python code
ruff format .

# Run linter and auto-fix simple issues (Python)
ruff check . --fix

# Run static type checking (Python)
mypy .

# Lint JavaScript files (requires Node.js)
npm install  # First time setup
eslint src/ui/assets/*.js
```

### Testing
We use `pytest` for all unit and integration tests.
```bash
# Run all tests
pytest

# Run tests in a specific file
pytest tests/test_audio_processor.py

# Run a single specific test function
pytest tests/test_audio_processor.py::test_f0_extraction

# Run tests with stdout output visible (useful for debugging tensors)
pytest -s -v
```

## 3. Code Style & Conventions

### Typing & Signatures
- **Type Hints**: You MUST use strict type hints for all function arguments and return types. Use modern Python standard collections (`list`, `dict`) or the `typing` module (`Optional`, `Union`, `Any`).
- Example: `def analyze_audio(audio_filepath: str, target_text: str) -> dict[str, Any]:`

### Naming Conventions
- Variables, functions, and file names: `snake_case`
- Classes and exceptions: `PascalCase`
- Constants: `UPPER_SNAKE_CASE`
- Private variables/methods: Prefix with an underscore (e.g., `_calculate_pitch`)

### Imports
Organize imports into three distinct blocks separated by a blank line:
1. Standard library imports (e.g., `os`, `pathlib`, `typing`)
2. Third-party imports (e.g., `fastapi`, `torch`, `numpy as np`, `parselmouth`)
3. Local application imports (e.g., `from src.audio import processor`)

### Error Handling
- Use specific exception blocks. Never use bare `except:`.
- In FastAPI, raise appropriate HTTP exceptions with `raise HTTPException(status_code=..., detail="...")`
- Always log critical audio processing failures (e.g., unreadable wav files).

### Audio & Tensor Management
- **VRAM Constraints**: Target hardware optimized for Apple Silicon. Use `with torch.no_grad():` during inference. Delete large tensors explicitly and call `torch.mps.empty_cache()` if memory fragmentation occurs during multi-step processing.
- **Device Detection**: Models auto-detect best available device (MPS > CPU). Priority: Apple Silicon GPU > CPU.
- **Audio Formats**: Standardize on 16kHz, mono `.wav` files for all processing unless explicitly required otherwise by a specific model.

### Frontend Best Practices
- Use vanilla JavaScript with global `window` object for state management
- Attach functions to `window` for accessibility from HTML event handlers: `window.myFunction = function(...) {}`
- Use CSS classes from Tailwind CSS for styling
- Inject custom CSS via `<style>` tags in the HTML template
- All JavaScript variables should be accessible globally or via event listeners

## 4. General AI Agent & Cursor/Copilot Instructions
If you are Cursor, GitHub Copilot, or an autonomous agent:
- Treat this `AGENTS.md` file as your primary `.cursorrules` equivalent.
- **Read First**: Always use your search tools to examine existing code, utilities, and architectural patterns before modifying or adding files.
- **Do Not Hallucinate Dependencies**: Only import libraries listed in `requirements.txt` or the standard library.
- **Comments**: Write concise comments focusing on the *why* rather than the *what*. This is highly important for complex audio processing math or tensor manipulations.
- **Paths**: Always use absolute paths via `pathlib.Path` relative to the project root to avoid `FileNotFoundError`.
- **Test Generation**: When generating tests, use `pytest` fixtures for dummy audio waveforms (e.g., via `numpy` and `scipy.io.wavfile`) rather than assuming hardcoded real files exist.
