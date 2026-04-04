#!/bin/bash
# Wrapper script to run the FastAPI server with venv activated

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR/.."

# Activate virtual environment
source "$PROJECT_DIR/speech-guider/bin/activate"

# Run the server
python -m app.main
