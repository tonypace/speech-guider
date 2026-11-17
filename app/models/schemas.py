"""Pydantic schemas for FastAPI endpoints."""

from typing import Any

from pydantic import BaseModel, Field


class ProsodyLabPitchPoint(BaseModel):
    """Single point in a prosody pitch track."""

    time: float
    f0_hz: float | None = None
    midi: float | None = None
    note: str | None = None
    confidence: float = 0.0


class ProsodyLabPauseSpan(BaseModel):
    """Detected pause segment."""

    start_time: float
    end_time: float
    duration: float


class ProsodyLabSummary(BaseModel):
    """Prosody Lab summary metrics."""

    duration_seconds: float
    syllable_count: int
    pause_count: int
    rhythm_balance: float
    mean_f0_hz: float
    mean_midi: float | None = None
    mean_note: str | None = None
    speech_rate: float | None = None
    articulation_rate: float | None = None


class ProsodyLabAnalysisResponse(BaseModel):
    """Response from the Prosody Lab endpoint."""

    recording_id: str
    summary: ProsodyLabSummary
    pitch_track: list[ProsodyLabPitchPoint]
    syllable_onsets: list[float]
    pause_spans: list[ProsodyLabPauseSpan] = Field(default_factory=list)
    raw_feedback: str = ""
    analysis_source: str = "heuristic"
    success: bool = True
    message: str = "Analysis complete"


class SelectErrorRequest(BaseModel):
    """Request body for selecting an error."""

    error_index: int
    errors: list[dict[str, Any]]


class SelectErrorResponse(BaseModel):
    """Response for error selection."""

    incorrect_desc: str
    correct_desc: str
    animation_params: dict[str, Any]
    highlight_params: dict[str, Any]
