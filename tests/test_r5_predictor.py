"""Tests for R5 streaming predictor, Core ML parity, Stage 5 badges, and model cache."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf
import torch

from src.models.r5_badges import R5Stage5Badges
from src.models.r5_predictor import DEFAULT_R5_BUNDLE, R5AAIPredictor
from src.services import model_cache

HAS_R5_BUNDLE = (DEFAULT_R5_BUNDLE / "configs" / "r5_streaming_contract.json").is_file()
HAS_MHUBERT = False  # Checked in test_mhubert_aligner.py


def test_r5_contract_validation_and_checksum_rejection(tmp_path: Path) -> None:
    bad_dir = tmp_path / "bad_r5"
    (bad_dir / "configs").mkdir(parents=True)
    (bad_dir / "configs" / "r5_streaming_contract.json").write_text(
        json.dumps({"format_version": "wrong"}), encoding="utf-8"
    )
    predictor = R5AAIPredictor(bundle_path=bad_dir, runtime_backend="torchscript")
    with pytest.raises(ValueError, match="Unsupported R5 streaming contract"):
        predictor.load()

    if not HAS_R5_BUNDLE:
        return
    tampered = tmp_path / "tampered_r5"
    (tampered / "configs").mkdir(parents=True)
    (tampered / "torchscript").mkdir(parents=True)
    shutil.copy2(
        DEFAULT_R5_BUNDLE / "configs" / "r5_streaming_contract.json",
        tampered / "configs" / "r5_streaming_contract.json",
    )
    shutil.copy2(DEFAULT_R5_BUNDLE / "SHA256SUMS", tampered / "SHA256SUMS")
    (tampered / "torchscript" / "r5_end_to_end.ts.pt").write_bytes(b"corrupted")
    bad_cksum = R5AAIPredictor(bundle_path=tampered, runtime_backend="torchscript")
    with pytest.raises(ValueError, match="checksum mismatch"):
        bad_cksum.load()


@pytest.mark.skipif(not HAS_R5_BUNDLE, reason="R5_CoreML_Export_v1 bundle not staged")
def test_r5_coreml_split_and_torchscript_parity_against_fixtures() -> None:
    manifest = json.loads(
        (DEFAULT_R5_BUNDLE / "fixtures" / "fixtures_manifest.json").read_text(encoding="utf-8")
    )
    coreml_pred = R5AAIPredictor(bundle_path=DEFAULT_R5_BUNDLE, runtime_backend="coreml_split")
    ts_pred = R5AAIPredictor(bundle_path=DEFAULT_R5_BUNDLE, runtime_backend="torchscript")
    coreml_pred.load()
    ts_pred.load()
    try:
        assert coreml_pred.active_backend == "coreml_split"
        assert ts_pred.active_backend == "torchscript"

        # Check full parity on real speech + silence + impulse stress fixtures
        for fix_name in ("ffes0_001_val", "maps0_001_sealed_test", "silence_control"):
            fdir = DEFAULT_R5_BUNDLE / "fixtures" / fix_name
            audio, sr = sf.read(fdir / "audio.wav", dtype="float32")
            ref_11 = np.load(fdir / "ref_committed_11ch.npy").reshape(-1, 11)
            ref_byp = np.load(fdir / "ref_committed_bypass_43d.npy").reshape(-1, 43)

            res_cm = coreml_pred.predict_with_metadata(torch.from_numpy(audio), sr)
            res_ts = ts_pred.predict_with_metadata(torch.from_numpy(audio), sr)

            n_valid = res_cm["tvs"].shape[0]
            expected_frames = (len(audio) + 160 - 1) // 320
            assert n_valid == expected_frames
            assert res_cm["tvs"].shape == (n_valid, 9)
            assert res_cm["tvs_11ch"].shape == (n_valid, 11)
            assert res_cm["bypass_43d"].shape == (n_valid, 43)
            assert torch.isfinite(res_cm["tvs_11ch"]).all()
            assert res_cm["metadata"]["model_version"] == "r5"

            cm_11 = res_cm["tvs_11ch"].numpy()
            ts_11 = res_ts["tvs_11ch"].numpy()
            assert float(np.mean(np.abs(cm_11[:, :7] - ref_11[:n_valid, :7]))) < 1e-4
            assert float(np.mean(np.abs(ts_11[:, :7] - ref_11[:n_valid, :7]))) < 1e-4
            assert float(np.mean(np.abs(res_cm["bypass_43d"].numpy() - ref_byp[:n_valid]))) < 1e-4

        assert len(manifest["fixtures"]) == 6
    finally:
        coreml_pred.cleanup()
        ts_pred.cleanup()


@pytest.mark.skipif(not HAS_R5_BUNDLE, reason="R5_CoreML_Export_v1 bundle not staged")
def test_r5_stage5_coda_kp_del_badge_on_sealed_and_open_spans() -> None:
    badges = R5Stage5Badges.from_file(DEFAULT_R5_BUNDLE / "weights" / "realization_badges_v1.json")
    tvs_sealed = np.load(
        DEFAULT_R5_BUNDLE / "fixtures" / "maps0_001_sealed_test" / "ref_committed_11ch.npy"
    ).reshape(-1, 11)
    byp_sealed = np.load(
        DEFAULT_R5_BUNDLE / "fixtures" / "maps0_001_sealed_test" / "ref_committed_bypass_43d.npy"
    ).reshape(-1, 43)

    sealed_eval = badges.evaluate_badge(
        "coda_kp_del", tvs_sealed, byp_sealed, 80, 85, target_phone="k"
    )
    assert sealed_eval.oral_seal_reached is True
    assert sealed_eval.oral_seal_min <= 0.1
    assert sealed_eval.status in {"pass", "sealed_unreleased"}
    assert sealed_eval.realization_label == "oral_seal_unreleased"

    tvs_open = np.full((25, 11), 0.45, dtype=np.float32)
    byp_open = np.zeros((25, 43), dtype=np.float32)
    byp_open[10:15, 40] = -8.0
    open_eval = badges.evaluate_badge("coda_kp_del", tvs_open, byp_open, 10, 15, target_phone="k")
    assert open_eval.oral_seal_reached is False
    assert open_eval.status == "flag"


def test_model_cache_version_selection_and_identity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    model_cache.reset_model_cache()
    try:
        empty_r5 = tmp_path / "missing_r5"
        monkeypatch.setenv("R5_BUNDLE_PATH", str(empty_r5))
        monkeypatch.setenv("SSL_AAI_MODEL_VERSION", "auto")
        assert model_cache.resolve_ssl_model_version() == "r4"
        r4_id = model_cache.get_ssl_cache_identity()
        assert r4_id["pipeline"] == "contentvec-l7-r4-final-hints-v3"

        monkeypatch.setenv("SSL_AAI_MODEL_VERSION", "r5")
        assert model_cache.resolve_ssl_model_version() == "r5"
        r5_id = model_cache.get_ssl_cache_identity()
        assert r5_id["pipeline"] == "wavlm-l8-r5-direct-v1"
        assert r5_id != r4_id
    finally:
        model_cache.reset_model_cache()
