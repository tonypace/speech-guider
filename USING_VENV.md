# Using the Speech-Guider Virtual Environment

## Setup Complete ✅

The `speech-guider/` virtual environment is configured and ready for development and testing.

## Quick Start

```bash
# Activate the venv
source speech-guider/bin/activate

# Run the application
python app.py

# Run tests
pytest

# Deactivate when done
deactivate
```

## Virtual Environment Details

- **Name**: `speech-guider`
- **Location**: `/Users/tonypace/Documents/Code/speech-guider/speech-guider/`
- **Python Version**: 3.10.10
- **Platform**: macOS (Apple Silicon MPS available)

## Installed Dependencies

Key packages already installed:
- **gradio**: 5.50.0 (web UI)
- **pyclts**: 3.2.0 (linguistic features)
- **torch**: 2.10.0 (PyTorch with MPS)
- **torchaudio**: 2.10.0 (audio processing)
- **transformers**: 4.57.6 (Wav2Vec2)
- **praat-parselmouth**: 0.4.7 (prosody analysis)
- **ruff**: (code quality)
- **pytest**: 9.0.2 (testing)

## Test Results

All tests passing with this venv:
- ✅ 9 articulatory tests passed
- ✅ Imports successful
- ✅ MPS acceleration available

## Development Workflow

1. Activate venv: `source speech-guider/bin/activate`
2. Make code changes
3. Run tests: `pytest -v`
4. Check code quality: `ruff check . --fix`
5. Run app: `python app.py`
6. Deactivate: `deactivate`

## Troubleshooting

### "command not found: pyth3"
Make sure venv is activated:
```bash
source speech-guider/bin/activate
```

### Module not found errors
Reinstall dependencies:
```bash
source speech-guider/bin/activate
pip install -r requirements.txt
```

### Tests fail
Check all dependencies are installed:
```bash
source speech-guider/bin/activate
pip list | grep -E "gradio|pyclts|torch"
```

## Next Steps

1. Activate venv
2. Run the app: `python app.py`
3. Open browser to `http://localhost:7860`
4. Try recording and analyzing pronunciation!
