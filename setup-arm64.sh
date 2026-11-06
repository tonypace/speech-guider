#!/bin/bash
# Native setup without shell edits, environment replacement, or dependency pins.
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

SETUP_PYTHON="${SPEECH_GUIDER_SETUP_PYTHON:-python3.12}"
if [ "$("$SETUP_PYTHON" -c 'import platform; print(platform.machine())')" != "arm64" ]; then
    echo "Use native ARM64 Python 3.12+; see docs/development.md." >&2
    exit 1
fi

ENV_DIR="$PROJECT_DIR/speech-guider"
if [ ! -e "$ENV_DIR" ]; then
    "$SETUP_PYTHON" -m venv "$ENV_DIR"
fi
if [ ! -x "$ENV_DIR/bin/python" ]; then
    echo "Existing speech-guider path is not a Python environment; see docs/development.md." >&2
    exit 1
fi
if [ "$("$ENV_DIR/bin/python" -c 'import platform; print(platform.machine())')" != "arm64" ]; then
    echo "Existing environment uses another architecture. Create a separate native environment manually." >&2
    exit 1
fi
"$ENV_DIR/bin/python" -m pip install -r "$PROJECT_DIR/requirements.txt"
npm ci
printf '%s\n' 'Setup complete. Activate with: source speech-guider/bin/activate'
