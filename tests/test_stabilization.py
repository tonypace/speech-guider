"""Numerical and partial-result regressions from the stabilization report."""

from unittest.mock import patch

import pytest
import torch

from app.api.analyze import SSLAnalysisError, _run_analysis_pipeline
from src.audio.processor import ProsodyAnalyzer


@pytest.mark.parametrize(
    ("intervals", "expected"),
    [
        ([], None),
        ([(0.0, 0.1)], None),
        ([(0.0, 0.1), (0.2, 0.3)], 0.0),
        ([(0.0, 0.1), (0.2, 0.4)], 200 / 3),
        ([(0.0, 0.0), (0.2, 0.3)], None),
        ([(0.0, float("nan")), (0.2, 0.3)], None),
        ([(0.0, 0.3), (0.2, 0.4)], None),
    ],
)
def test_npvi_reference_values(
    intervals: list[tuple[float, float]], expected: float | None
) -> None:
    analyzer = object.__new__(ProsodyAnalyzer)
    result = analyzer.analyze_rhythm(intervals)
    if expected is None:
        assert result.npvi is None
    else:
        assert result.npvi == pytest.approx(expected, abs=1e-10)


@pytest.mark.asyncio
async def test_partial_result_retains_diagnostic() -> None:
    with (
        patch("src.audio.processor.AudioContext"),
        patch("src.audio.processor.ProsodyAnalyzer") as analyzer,
        patch(
            "app.api.analyze._load_and_preprocess_audio", return_value=(torch.zeros(16000), 16000)
        ),
        patch(
            "app.api.analyze.try_primary_ssl_analysis",
            side_effect=SSLAnalysisError("missing R4 weights"),
        ),
    ):
        analyzer.return_value.analyze_complete.return_value = None
        result = await _run_analysis_pipeline("unused.wav", "hello", "diagnostic-123")
    assert result["success"] is False
    assert result["status"] == "partial"
    assert "missing R4 weights" in result["ssl_warning"]
    assert "diagnostic-123" in result["ssl_warning"]
