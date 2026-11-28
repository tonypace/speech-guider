"""Main FastAPI application entry point."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.api import (
    analyze,
    comparison,
    desktop_history,
    errors,
    feedback_export,
    prosody_lab,
    settings,
    sse,
)
from src.services.comparison_cache import reset_comparison_cache
from src.services.desktop_assets import desktop_asset_dir, desktop_assets_missing


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    """Remove owned reference audio before the process loses its cache namespace."""
    try:
        yield
    finally:
        reset_comparison_cache()


# Create FastAPI app
app = FastAPI(
    title="Pronunciation & Prosody Evaluator",
    description="Real-time pronunciation feedback with vocal tract visualization",
    version="1.0.0",
    lifespan=lifespan,
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
app.include_router(desktop_history.router)
app.include_router(feedback_export.router)
app.include_router(prosody_lab.router)
app.include_router(settings.router)
app.include_router(errors.router)
app.include_router(sse.router)


@app.get("/", response_class=HTMLResponse)
async def root(request: Request) -> HTMLResponse:
    """Serve the main UI page."""
    is_desktop = desktop_history.desktop_enabled()
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "request": request,
            "settings": settings.settings_payload(settings.load_settings()),
            "reference_text_limit": comparison.REFERENCE_TEXT_LIMIT,
            "is_desktop": is_desktop,
            "desktop_asset_dir": desktop_asset_dir() if is_desktop else None,
            "desktop_assets_missing": desktop_assets_missing() if is_desktop else [],
            "desktop_history": (
                desktop_history.load_desktop_history().model_dump(mode="json")
                if is_desktop
                else None
            ),
        },
    )


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok", "service": "pronunciation-evaluator"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=7860, reload=True)
