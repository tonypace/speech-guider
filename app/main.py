"""Main FastAPI application entry point."""

import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.api import analyze, comparison, errors, presets, prosody_lab, sse
from app.services.state import load_presets

# Create FastAPI app
app = FastAPI(
    title="Pronunciation & Prosody Evaluator",
    description="Real-time pronunciation feedback with vocal tract visualization",
    version="1.0.0",
)

# Get project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Mount static files (CSS and JS)
static_path = PROJECT_ROOT / "static"
app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

# Setup Jinja2 templates with cache disabled
jinja_env = Environment(
    loader=FileSystemLoader(str(PROJECT_ROOT / "app" / "templates")),
    autoescape=select_autoescape(["html", "xml"]),
    cache_size=0,  # Disable template caching
)


templates = Jinja2Templates(env=jinja_env)

# Include API routers
app.include_router(analyze.router)
app.include_router(comparison.router)
app.include_router(prosody_lab.router)
app.include_router(presets.router)
app.include_router(errors.router)
app.include_router(sse.router)


@app.get("/", response_class=HTMLResponse)
async def root(request: Request) -> HTMLResponse:
    """Serve the main UI page."""
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "request": request,
            "phoneme_presets": load_presets(),
            "feature_flags": {
                "svgArticulatoryRenderer": os.environ.get("SVG_ARTICULATORY_RENDERER", "1") != "0",
            },
        },
    )


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok", "service": "pronunciation-evaluator"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=7860, reload=True)
