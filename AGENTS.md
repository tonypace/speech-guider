# Agent Guidelines for speech-guider

Welcome! You are an AI agent operating in the `speech-guider` repository. This file provides the essential context, commands, and code style guidelines you must follow to ensure consistency and reliability.

## 1. Project Overview & Architecture
This is a Pronunciation & Prosody Evaluator application.
- **Frontend**: Gradio (Python-based UI)
- **Backend**: Local Python pipeline optimized for 12GB VRAM (RTX 3060) or Apple Silicon MPS
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
- [x] Basic Gradio app.py prototype with UI
- [x] Parselmouth pitch (F0) extraction
- [x] Test fixtures for dummy audio generation
- [x] CI/CD tooling (ruff, mypy, pytest)
- [x] Forced alignment implementation (Wav2Vec2)
- [x] Apple Silicon MPS optimization (~60x faster than CPU)
- [x] Phonetic Error Detection with IPA and G2P integration
- [x] Goodness of Pronunciation (PyGOP) scoring system
- [x] Targeted error Classification (voicing, substitutions)
- [x] Gradio UI integration with detailed feedback
- [x] Prosody metrics (nPVI, stress patterns) - COMPLETED
- [x] Visual articulatory feedback (pyclts + Pink Trombone) - COMPLETED
- [ ] Model loading/management optimizations
- [ ] Voice quality analysis (Jitter, Shimmer, CPPS, Spectral Tilt)
- [ ] User documentation/help guides

### Expected Directory Structure
```text
speech-guider/
├── app.py                 # Main Gradio entrypoint
├── src/
│   ├── audio/             # Parselmouth/Praat prosody processing
│   ├── models/            # PyTorch Wav2Vec2 models & alignment
│   │   └── articulatory.py # pyclts mapping & Pink Trombone params
│   └── ui/
│       └── assets/        # Static JS/CSS for vocal tract visualization
│           ├── vocal_tract.js
│           └── vocal_tract.css
├── tests/                 # Pytest test suite
├── requirements.txt       # Dependencies
└── AGENTS.md              # You are here
```

## 2. Environment & Commands

### Setup
We use a Python virtual environment for development and testing.
```bash
# Activate the venv (macOS/Linux)
source speech-guider/bin/activate

# Activate the venv (Windows)
speech-guider\Scripts\activate

# Install dependencies (if not already installed)
pip install -r requirements.txt

# Note: macOS requires 'espeak' for phoneme conversion:
# brew install espeak-ng
```

### Running the App
To run the main Gradio application locally:
```bash
# Activate venv first, then:
python app.py
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
We strictly use `ruff` for fast linting/formatting, and `mypy` for static type checking.
```bash
# Format code
ruff format .

# Run linter and auto-fix simple issues
ruff check . --fix

# Run static type checking
mypy .
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
2. Third-party imports (e.g., `gradio as gr`, `torch`, `numpy as np`, `parselmouth`)
3. Local application imports (e.g., `from src.audio import processor`)

### Error Handling
- Use specific exception blocks. Never use bare `except:`.
- In Gradio UI components, use `raise gr.Error("Message")` to gracefully display errors to the user instead of crashing the backend.
- Always log critical audio processing failures (e.g., unreadable wav files).

### Audio & Tensor Management
- **VRAM Constraints**: Target hardware optimized for Apple Silicon. Use `with torch.no_grad():` during inference. Delete large tensors explicitly and call `torch.mps.empty_cache()` if memory fragmentation occurs during multi-step processing.
- **Device Detection**: Models auto-detect best available device (MPS > CPU). Priority: Apple Silicon GPU > CPU.
- **Audio Formats**: Standardize on 16kHz, mono `.wav` files for all processing unless explicitly required otherwise by a specific model.

### UI & Gradio Best Practices
- Prefer `gr.Blocks()` over `gr.Interface()` for anything more complex than a basic prototype. It allows custom layouts, state management, and better modularity.
- Handle long-running tasks gracefully. Use Gradio's progress bars (`gr.Progress`) for the multi-step pipeline (Alignment -> Phonemes -> Prosody -> LLM) so the user is aware of the processing status.

## 4. General AI Agent & Cursor/Copilot Instructions
If you are Cursor, GitHub Copilot, or an autonomous agent:
- Treat this `AGENTS.md` file as your primary `.cursorrules` equivalent.
- **Read First**: Always use your search tools to examine existing code, utilities, and architectural patterns before modifying or adding files.
- **Do Not Hallucinate Dependencies**: Only import libraries listed in `requirements.txt` or the standard library.
- **Comments**: Write concise comments focusing on the *why* rather than the *what*. This is highly important for complex audio processing math or tensor manipulations.
- **Paths**: Always use absolute paths via `pathlib.Path` relative to the project root to avoid `FileNotFoundError` during Gradio execution.
- **Test Generation**: When generating tests, use `pytest` fixtures for dummy audio waveforms (e.g., via `numpy` and `scipy.io.wavfile`) rather than assuming hardcoded real files exist.