"""Developer feedback packet export endpoint (audio, interaction JSON, and notes)."""

from __future__ import annotations

import json
import logging
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from app.services import state
from app.services.concurrency import run_blocking

router = APIRouter()
logger = logging.getLogger(__name__)

DEFAULT_BUILDS_FEEDBACK_DIR = Path.home() / "Builds and Artifacts" / "speech-guider-feedback"
_SAFE_SEGMENT_RE = re.compile(r"[^a-z0-9_-]+")


def resolve_feedback_export_dir() -> Path:
    """Resolve destination folder for 'Send to Developer' packets."""
    configured = os.getenv("SPEECH_GUIDER_FEEDBACK_DIR", "").strip()
    if configured:
        return Path(configured).expanduser().resolve()
    builds_parent = Path.home() / "Builds and Artifacts"
    if builds_parent.is_dir():
        return DEFAULT_BUILDS_FEEDBACK_DIR
    return state.DATA_DIR / "feedback_exports"


def _write_feedback_packet(
    *,
    tab: str,
    categories: list[str],
    note: str,
    target_text: str,
    payload: dict[str, Any],
    audio_bytes: bytes | None,
    audio_filename: str | None,
) -> Path:
    root = resolve_feedback_export_dir()
    root.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    safe_tab = _SAFE_SEGMENT_RE.sub("-", tab.lower()).strip("-") or "app"
    packet_dir = root / f"{ts}_{safe_tab}_{uuid.uuid4().hex[:6]}"
    packet_dir.mkdir(parents=True, exist_ok=True)

    if audio_bytes:
        ext = Path(audio_filename or "audio.wav").suffix.lower()
        if ext not in {".wav", ".ogg", ".webm", ".mp3", ".m4a"}:
            ext = ".wav"
        (packet_dir / f"audio{ext}").write_bytes(audio_bytes)

    interaction_doc = {
        "exported_at_utc": datetime.now(timezone.utc).isoformat(),
        "tab": safe_tab,
        "categories": categories,
        "note": note,
        "target_text": target_text,
        "payload": payload,
    }
    (packet_dir / "interaction.json").write_text(
        json.dumps(interaction_doc, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    note_lines = [
        f"Exported: {interaction_doc['exported_at_utc']}",
        f"Tab: {safe_tab}",
        f"Categories: {', '.join(categories) if categories else '(none)'}",
        f"Target Text: {target_text}",
        "",
        "Note:",
        note.strip() or "(none)",
    ]
    (packet_dir / "note.txt").write_text("\n".join(note_lines) + "\n", encoding="utf-8")
    return packet_dir


@router.post("/api/export-feedback")
async def export_developer_feedback(
    tab: str = Form(default="analysis"),
    categories: str = Form(default="[]"),
    note: str = Form(default=""),
    target_text: str = Form(default=""),
    payload_json: str = Form(default="{}"),
    audio: UploadFile | None = File(default=None),
) -> JSONResponse:
    """Save an interaction packet (audio + JSON + note) to the developer Builds folder."""
    try:
        parsed_categories = json.loads(categories)
        if not isinstance(parsed_categories, list):
            parsed_categories = []
        cat_list = [str(item) for item in parsed_categories if str(item).strip()]
    except json.JSONDecodeError:
        cat_list = []

    try:
        parsed_payload = json.loads(payload_json)
        if not isinstance(parsed_payload, dict):
            parsed_payload = {"raw": parsed_payload}
    except json.JSONDecodeError:
        parsed_payload = {}

    audio_bytes: bytes | None = None
    audio_filename: str | None = None
    if audio is not None and audio.filename:
        audio_bytes = await audio.read()
        audio_filename = audio.filename

    try:
        packet_dir = await run_blocking(
            _write_feedback_packet,
            tab=tab,
            categories=cat_list,
            note=note,
            target_text=target_text,
            payload=parsed_payload,
            audio_bytes=audio_bytes,
            audio_filename=audio_filename,
        )
    except OSError as exc:
        logger.exception("Failed to export developer feedback packet")
        raise HTTPException(
            status_code=500, detail=f"Could not save feedback packet: {exc}"
        ) from exc

    return JSONResponse(
        content={
            "success": True,
            "packet_dir": str(packet_dir),
            "folder_name": packet_dir.name,
        }
    )
