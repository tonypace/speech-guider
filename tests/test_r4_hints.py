"""Hint boundary behavior and asset integrity without encoder inference."""

import hashlib
from pathlib import Path
from typing import Any
from unittest.mock import Mock

import numpy as np
import pytest

from src.models.r4_calibration import (
    CurveCalibrationParams,
    OutputCalibrator,
    TipCalibrationParams,
    apply_conditional_calibration,
)
from src.models.r4_dental import apply_dental_correction
from src.models.r4_hints import load_silence, verified_asset
from src.models.r4_labiodental import apply_labiodental_correction
from src.models.r4_lip import LipClosureConfig, LipCorrection
from src.services import model_cache


def test_lip_motion_continues_across_packets_and_resets_for_new_clip() -> None:
    correction = LipCorrection(
        [[0.0], [0.0], [0.0], [0.0]],
        [0.0, 0.0, 1.0, 0.0],
        ["open", "approach", "hold", "release"],
        LipClosureConfig(),
    )
    features = np.zeros((5, 1), dtype=np.float32)
    frames = np.full((5, 9), 0.8, dtype=np.float32)
    stream = correction.new_stream()
    first, phases = stream.apply(features, frames)
    second, _ = stream.apply(features, frames)
    assert np.all(phases == "hold")
    assert second[-1, 1] == pytest.approx(0.02)
    assert first[0, 1] > second[0, 1]
    np.testing.assert_array_equal(
        first[:, [0, 2, 3, 4, 5, 6, 7, 8]], frames[:, [0, 2, 3, 4, 5, 6, 7, 8]]
    )
    reset, _ = correction.new_stream().apply(features, frames)
    np.testing.assert_array_equal(reset, first)


def test_dental_respects_contact_and_lip_seals() -> None:
    frames = np.full((4, 9), 0.5, dtype=np.float32)
    frames[1, 3] = 0.015
    frames[2, 5] = 0.015
    frames[3, 1] = 0.02
    output, strength = apply_dental_correction(frames, np.ones(4), 0.6)
    assert output[0, 2] == pytest.approx(0.06)
    assert output[0, 3] == pytest.approx(0.045)
    np.testing.assert_array_equal(output[1:], frames[1:])
    np.testing.assert_array_equal(strength, [1, 0, 0, 0])


def test_corrupt_hint_rejected_before_unpickling(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import src.models.r4_hints as hints

    (tmp_path / "silence_fit.json").write_text('{"sklearn_version":"1.9.0"}')
    (tmp_path / "SHA256SUMS").write_text("0" * 64 + "  silence_fit.json\n")
    loader = Mock()
    monkeypatch.setattr(hints.joblib, "load", loader)
    with pytest.raises(ValueError, match="checksum mismatch"):
        load_silence(tmp_path, "reviewed")
    loader.assert_not_called()


def test_verified_asset_checks_release_digest(tmp_path: Path) -> None:
    path = tmp_path / "lip.json"
    path.write_bytes(b"original")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    (tmp_path / "SHA256SUMS").write_text(f"{digest}  lip.json\n")
    assert verified_asset(tmp_path, "lip.json") == path
    path.write_bytes(b"changed")
    with pytest.raises(ValueError, match="checksum mismatch"):
        verified_asset(tmp_path, "lip.json")


def test_reference_identity_tracks_hint_settings_and_assets(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(model_cache, "_cached_ssl_predictor", None)
    monkeypatch.setenv("SSL_AAI_BUNDLE_PATH", str(tmp_path))
    monkeypatch.delenv("SSL_AAI_DENTAL_ENABLED", raising=False)
    monkeypatch.delenv("SSL_AAI_CHECKPOINT_PATH", raising=False)
    for name in (
        "weights/r4.pt",
        "weights/contentvec/model.safetensors",
        "weights/contentvec/config.json",
        "weights/contentvec/preprocessor_config.json",
        "configs/nine_channel_v12_100ms.yaml",
    ):
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()
    original = model_cache.get_ssl_cache_identity(contact_enabled=True)
    (tmp_path / "weights/lip.json").write_text("updated lip head")
    assert model_cache.get_ssl_cache_identity(True) != original
    before = model_cache.get_ssl_cache_identity(True)
    monkeypatch.setenv("SSL_AAI_DENTAL_ENABLED", "1")
    assert model_cache.get_ssl_cache_identity(True) != before
    disabled = model_cache.get_ssl_cache_identity(False)
    (tmp_path / "weights/lip.json").write_text("another lip update")
    assert model_cache.get_ssl_cache_identity(False) == disabled
    # A loaded predictor's settings take precedence over changed environment.
    predictor: Any = Mock(
        bundle_path=tmp_path,
        checkpoint_path=tmp_path / "weights/r4.pt",
        lip_enabled=True,
        dental_enabled=False,
        calibrate_enabled=True,
        labiodental_enabled=True,
        silence_mode="reviewed",
    )
    monkeypatch.setattr(model_cache, "_cached_ssl_predictor", predictor)
    assert model_cache.get_ssl_cache_identity(True)["hints"] == {
        "lip": True,
        "dental": False,
        "calibrate": True,
        "labiodental": True,
        "silence": "reviewed",
    }


def test_installer_stages_final_hint_assets_and_manifest(tmp_path: Path) -> None:
    from scripts.build_desktop_installer import R4_FILES, _stage_r4

    bundle = tmp_path / "bundle"
    bundle.mkdir()
    hashes = []
    for name in (*R4_FILES, "LICENSE", "CONTENTVEC_STATE_SHA256", "IMPLEMENTATION_NOTES.md"):
        path = bundle / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(name)
        hashes.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {name}")
    (bundle / "SHA256SUMS").write_text("\n".join(hashes) + "\n")
    target = tmp_path / "installed"
    _stage_r4(bundle, target)
    assert (target / "SHA256SUMS").read_bytes() == (bundle / "SHA256SUMS").read_bytes()
    for name in R4_FILES:
        assert (target / name).read_bytes() == (bundle / name).read_bytes()
        assert (target / name).stat().st_mode & 0o777 == 0o644
    (bundle / "weights/lip.json").write_text("corrupt")
    with pytest.raises(ValueError, match="checksum mismatch"):
        _stage_r4(bundle, target)


def test_conditional_calibration_expands_speech_and_preserves_silence_identity() -> None:
    calibrator = OutputCalibrator(
        ttcl=TipCalibrationParams(p0=0.5, g=4.0, span=0.34, cd_lo=0.35, cd_hi=0.57, w_open=0.25),
        tbcl=CurveCalibrationParams(p0=0.5, g=5.0, span=0.34),
        lp=CurveCalibrationParams(p0=0.5, g=2.5, span=0.34),
    )
    frames = np.full((2, 9), 0.6, dtype=np.float32)
    frames[:, 3] = 0.2  # TTCD active
    result = apply_conditional_calibration(frames, calibrator, speech_weight=np.array([0.0, 1.0]))
    # Confirmed silence (weight=0.0) is exact identity
    np.testing.assert_array_equal(result[0], frames[0])
    # Active speech (weight=1.0) expands TTCL/TBCL/LP away from p0=0.5, leaves other channels intact
    assert result[1, 0] > frames[1, 0]
    assert result[1, 2] > frames[1, 2]
    assert result[1, 4] > frames[1, 4]
    np.testing.assert_array_equal(result[1, [1, 3, 5, 6, 7, 8]], frames[1, [1, 3, 5, 6, 7, 8]])


def test_labiodental_correction_gates_bilabial_seals_and_tongue_stops() -> None:
    frames = np.full((3, 9), 0.5, dtype=np.float32)
    frames[1, 1] = 0.02  # bilabial seal (LA <= 0.05)
    frames[2, 3] = 0.01  # tongue tip stop (TTCD <= 0.03)
    probs = np.array([0.9, 0.9, 0.9], dtype=np.float32)
    retraction, strength = apply_labiodental_correction(frames, probs, threshold=0.315)
    assert retraction[0] > 0.9
    assert strength[0] > 0.9
    assert retraction[1] == 0.0
    assert retraction[2] == 0.0
