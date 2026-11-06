#!/bin/bash
# Own both development processes so every exit releases the backend.
set -euo pipefail
# Give each background command its own group, including npm/uvicorn descendants.
set -m

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_DIR"

FASTAPI_PID=""
TAURI_PID=""
cleanup() {
    trap - EXIT
    for process_id in "$TAURI_PID" "$FASTAPI_PID"; do
        if [ -n "$process_id" ]; then
            kill -- "-$process_id" 2>/dev/null || true
            wait "$process_id" 2>/dev/null || true
        fi
    done
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

if [ -x "$PROJECT_DIR/speech-guider/bin/python" ]; then
    VENV_PYTHON="$PROJECT_DIR/speech-guider/bin/python"
elif [ -x "$PROJECT_DIR/venv/bin/python" ]; then
    VENV_PYTHON="$PROJECT_DIR/venv/bin/python"
else
    VENV_PYTHON="python3"
fi

# A pre-existing server would mask a bind failure and run stale code.
if curl --fail --silent --max-time 1 http://127.0.0.1:7860/health >/dev/null 2>&1; then
    echo "Port 7860 already serves an app. Stop it before running npm run dev." >&2
    exit 1
fi

"$VENV_PYTHON" -m uvicorn app.main:app --host 127.0.0.1 --port 7860 --reload &
FASTAPI_PID=$!

ready=false
for ((attempt = 0; attempt < 30; attempt++)); do
    if ! kill -0 "$FASTAPI_PID" 2>/dev/null; then
        echo "FastAPI exited during startup." >&2
        exit 1
    fi
    if curl --fail --silent --max-time 1 http://127.0.0.1:7860/health >/dev/null 2>&1; then
        ready=true
        break
    fi
    sleep 1
done
if [ "$ready" != true ]; then
    echo "FastAPI did not become ready within 30 startup attempts." >&2
    exit 1
fi

npm run tauri -- dev &
TAURI_PID=$!
while kill -0 "$TAURI_PID" 2>/dev/null; do
    if ! kill -0 "$FASTAPI_PID" 2>/dev/null; then
        echo "FastAPI exited while desktop app was running." >&2
        exit 1
    fi
    sleep 0.2
done
wait "$TAURI_PID"
