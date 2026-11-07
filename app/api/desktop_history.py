"""Preserve desktop prosody summaries across WebView origin changes."""

import logging
import os
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, ValidationError

from app.models.schemas import ProsodyLabAnalysisResponse
from app.services import state
from app.services.atomic_json import write_json_atomic
from app.services.concurrency import run_blocking

router = APIRouter()
logger = logging.getLogger(__name__)


class SavedProsodyRecord(ProsodyLabAnalysisResponse):
    created_at: str = Field(max_length=64)


class DesktopHistory(BaseModel):
    recordings: list[SavedProsodyRecord] = Field(default_factory=list, max_length=3)
    teacher_id: str = Field(default="", max_length=128)
    student_id: str = Field(default="", max_length=128)


def desktop_enabled() -> bool:
    return os.getenv("SPEECH_GUIDER_DESKTOP") == "1"


def _history_path() -> Path:
    return state.PRESETS_FILE.with_name("prosody-history.json")


def load_desktop_history() -> DesktopHistory:
    path = _history_path()
    try:
        return DesktopHistory.model_validate_json(path.read_bytes())
    except FileNotFoundError:
        return DesktopHistory()
    except (OSError, ValidationError):
        logger.warning("Ignoring unreadable desktop history at %s", path, exc_info=True)
        return DesktopHistory()


@router.put("/api/desktop-history", status_code=204)
async def save_desktop_history(history: DesktopHistory) -> None:
    if not desktop_enabled():
        raise HTTPException(status_code=404, detail="Desktop history is unavailable")
    try:
        await run_blocking(write_json_atomic, _history_path(), history.model_dump(mode="json"))
    except (OSError, ValueError) as exc:
        logger.exception("Desktop history save failed")
        raise HTTPException(status_code=500, detail="Could not save desktop history.") from exc
