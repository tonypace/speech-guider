# Quick Start Guide - Speech-Guider Development

## Virtual Environment Setup

The project uses a Python virtual environment named `speech-guider` located in the project root directory.

### Activation

```bash
# macOS/Linux
source speech-guider/bin/activate

# Windows
speech-guider\Scripts\activate
```

### Deactivation

```bash
deactivate
```

## Quick Reference Commands

### Run the App
```bash
source speech-guider/bin/activate
python -m app.main
# or
uvicorn app.main:app --reload
```

### Run Tests
```bash
source speech-guider/bin/activate

# All tests
pytest

# Specific test file
pytest tests/test_articulatory.py

# Verbose output
pytest -v
```

### Code Quality
```bash
source speech-guider/bin/activate

# Format code
ruff format .

# Lint code
ruff check . --fix

# Type checking
mypy .
```

### Python Executable
```bash
# Direct path to Python in venv
./speech-guider/bin/python
```

## Environment Details

- **Virtual Environment**: `speech-guider/`
- **Python**: 3.10.10
- **PyTorch**: 2.10.0 (with MPS support)
- **FastAPI**: 0.115.11
- **pyclts**: 3.2.0
- **Location**: `/Users/tonypace/Documents/Code/speech-guider/speech-guider/`

## Troubleshooting

### If venv doesn't activate
```bash
# Check if venv exists
ls -la speech-guider/

# If missing, create it:
python3 -m venv speech-guider
source speech-guider/bin/activate
pip install -r requirements.txt
```

### If dependencies are missing
```bash
source speech-guider/bin/activate
pip install -r requirements.txt
```

### If Gradio fails to launch
```bash
# Update Gradio
source speech-guider/bin/activate
pip install --upgrade gradio
```
