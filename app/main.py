"""Main FastAPI application entry point."""

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from pathlib import Path

from app.api import analyze, presets, errors, sse

# Create FastAPI app
app = FastAPI(
    title="Pronunciation & Prosody Evaluator",
    description="Real-time pronunciation feedback with vocal tract visualization",
    version="1.0.0",
)

# Get project root
PROJECT_ROOT = Path(__file__).parent.parent

# Mount static files (CSS and JS)
static_path = PROJECT_ROOT / "static"
app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

# Setup Jinja2 templates
templates = Jinja2Templates(directory=str(PROJECT_ROOT / "app" / "templates"))

# Include API routers
app.include_router(analyze.router)
app.include_router(presets.router)
app.include_router(errors.router)
app.include_router(sse.router)


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Serve the main UI page."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "service": "pronunciation-evaluator"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=7860, reload=True)
