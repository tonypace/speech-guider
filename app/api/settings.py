"""Local preferences shared across desktop launches and browser sessions."""

import logging
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, ValidationError

from app.services import state
from app.services.atomic_json import write_json_atomic
from app.services.concurrency import run_blocking
from src.models.ssl_aai_predictor import DEFAULT_R4_BUNDLE
from src.services.desktop_assets import asset_override

router = APIRouter()
logger = logging.getLogger(__name__)


class RemoteBindings(BaseModel):
    record: str = Field(default="", max_length=64)
    play_pause: str = Field(default="", max_length=64)
    speed_up: str = Field(default="", max_length=64)
    speed_down: str = Field(default="", max_length=64)


class AppSettings(BaseModel):
    contact_enabled: bool = True
    microphone_enabled: bool = True
    microphone_device_id: str = Field(default="", max_length=512)
    microphone_label: str = Field(default="", max_length=512)
    remote_enabled: bool = True
    remote_record_mode: Literal["toggle", "hold"] = "toggle"
    remote_bindings: RemoteBindings = Field(default_factory=RemoteBindings)


def _settings_path() -> Path:
    return state.data_file("settings.json")


def load_settings() -> AppSettings:
    path = _settings_path()
    with state.STATE_LOCK:
        try:
            return AppSettings.model_validate_json(path.read_bytes())
        except FileNotFoundError:
            return AppSettings()
        except (OSError, ValidationError):
            logger.warning("Ignoring unreadable settings at %s", path, exc_info=True)
            return AppSettings()


def _write_settings(settings: AppSettings) -> None:
    with state.STATE_LOCK:
        write_json_atomic(_settings_path(), settings.model_dump(mode="json"))


def settings_payload(settings: AppSettings) -> dict[str, object]:
    bundle = Path(asset_override("SSL_AAI_BUNDLE_PATH", "r4") or DEFAULT_R4_BUNDLE)
    return {
        **settings.model_dump(),
        "contact_available": (bundle / "weights" / "contact.pt").is_file(),
    }


@router.put("/api/settings")
async def save_settings(settings: AppSettings) -> dict[str, object]:
    try:
        await run_blocking(_write_settings, settings)
    except (OSError, ValueError) as exc:
        logger.exception("Could not save settings")
        raise HTTPException(status_code=500, detail="Could not save settings.") from exc
    return settings_payload(settings)
