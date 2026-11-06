#!/bin/bash
# Resolve the environment and import root independently of the caller's cwd.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_DIR"
exec "$PROJECT_DIR/speech-guider/bin/python" -m app.main
