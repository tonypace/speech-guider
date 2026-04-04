#!/bin/bash
set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Speech Guider Tauri Dev${NC}"
echo "========================="
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ] && [ ! -d "speech-guider" ]; then
    echo "Warning: No virtual environment found. Please ensure Python dependencies are installed."
fi

# Function to cleanup processes on exit
cleanup() {
    echo ""
    echo "Shutting down..."
    if [ -n "$FASTAPI_PID" ]; then
        kill $FASTAPI_PID 2>/dev/null || true
    fi
    exit 0
}

trap cleanup INT TERM

# Start FastAPI backend
echo -e "${GREEN}Starting FastAPI backend...${NC}"
if [ -d "venv" ]; then
    source venv/bin/activate
    uvicorn app.main:app --host 127.0.0.1 --port 7860 --reload &
    FASTAPI_PID=$!
elif [ -d "speech-guider" ]; then
    source speech-guider/bin/activate
    uvicorn app.main:app --host 127.0.0.1 --port 7860 --reload &
    FASTAPI_PID=$!
else
    uvicorn app.main:app --host 127.0.0.1 --port 7860 --reload &
    FASTAPI_PID=$!
fi

echo "FastAPI running on http://127.0.0.1:7860"
echo ""

# Wait for FastAPI to be ready
echo "Waiting for FastAPI to be ready..."
for i in {1..30}; do
    if curl -s http://127.0.0.1:7860/health > /dev/null 2>&1; then
        echo -e "${GREEN}FastAPI is ready!${NC}"
        break
    fi
    sleep 1
done

echo ""
echo -e "${GREEN}Starting Tauri app...${NC}"
echo ""

# Start Tauri
npm run tauri -- dev &
TAURI_PID=$!

# Wait for Tauri
wait $TAURI_PID
