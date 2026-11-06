"""Pydantic schemas for FastAPI endpoints."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    """Request body for analyze endpoint."""

    target_text: str = Field(..., description="The target sentence to practice")


class ErrorDetail(BaseModel):
    """Pronunciation error detail."""

    error_type: str = Field(..., description="Type of error: substitution, deletion, insertion")
    target_phoneme: str
    predicted_phoneme: str
    word_context: str
    animation_left: Optional[Dict[str, Any]] = None
    animation_right: Optional[Dict[str, Any]] = None
    highlight_zone: Optional[str] = None


class WordAlignment(BaseModel):
    """Word-level alignment data."""

    word: str
    start_time: float
    end_time: float
    phonemes: List[Dict[str, Any]]


class SentenceAlignment(BaseModel):
    """Complete sentence alignment."""

    text: str
    words: List[WordAlignment]
    total_duration: float
    overall_score: float


class ProsodyMetrics(BaseModel):
    """Prosody analysis results."""

    pitch_mean: float
    pitch_range: float
    pitch_variability: float
    npvi: float  # Normalized Pairwise Variability Index
    stress_pattern: Optional[str] = None


class ProsodyLabPitchPoint(BaseModel):
    """Single point in a prosody pitch track."""

    time: float
    f0_hz: Optional[float] = None
    midi: Optional[float] = None
    note: Optional[str] = None
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
    mean_midi: Optional[float] = None
    mean_note: Optional[str] = None
    speech_rate: Optional[float] = None
    articulation_rate: Optional[float] = None


class ProsodyLabAnalysisResponse(BaseModel):
    """Response from the Prosody Lab endpoint."""

    recording_id: str
    summary: ProsodyLabSummary
    pitch_track: List[ProsodyLabPitchPoint]
    syllable_onsets: List[float]
    pause_spans: List[ProsodyLabPauseSpan] = Field(default_factory=list)
    raw_feedback: str = ""
    analysis_source: str = "fallback"
    success: bool = True
    message: str = "Analysis complete"


class AnalyzeResponse(BaseModel):
    """Response from analyze endpoint."""

    errors: List[ErrorDetail] = []
    feedback: str
    alignment: Optional[SentenceAlignment] = None
    prosody: Optional[ProsodyMetrics] = None
    success: bool = True
    message: str = "Analysis complete"


class SelectErrorRequest(BaseModel):
    """Request body for selecting an error."""

    error_index: int
    errors: List[Dict[str, Any]]


class SelectErrorResponse(BaseModel):
    """Response for error selection."""

    incorrect_desc: str
    correct_desc: str
    animation_params: Dict[str, Any]
    highlight_params: Dict[str, Any]


class PhonemePreset(BaseModel):
    """Single phoneme preset."""

    name: str
    params: Dict[str, float]


class PresetsResponse(BaseModel):
    """Response containing all phoneme presets."""

    phonemes: Dict[str, PhonemePreset]


class PresetSaveRequest(BaseModel):
    """Request to save a custom preset."""

    phoneme: str
    params: Dict[str, float]
    name: Optional[str] = None


class PresetSaveResponse(BaseModel):
    """Response after saving a preset."""

    status: str
    phoneme: str
    message: str = "Preset saved successfully"


class ProgressUpdate(BaseModel):
    """SSE progress update message."""

    job_id: str
    progress: float = Field(..., ge=0.0, le=1.0)
    message: str
    step: Optional[str] = None


class ErrorResponse(BaseModel):
    """Standard error response."""

    error: str
    detail: Optional[str] = None
