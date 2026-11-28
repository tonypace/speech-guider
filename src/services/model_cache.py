"""Shared model caching for SSL AAI predictors (R5 / R4) and forced alignment."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from threading import Lock
from typing import TYPE_CHECKING, Any, Literal, cast

from src.models.r5_predictor import DEFAULT_R5_BUNDLE, R5AAIPredictor
from src.models.ssl_aai_predictor import DEFAULT_R4_BUNDLE, SSLAAIPredictor
from src.services.desktop_assets import asset_override

if TYPE_CHECKING:
    from src.models.alignment import ForcedAligner

logger = logging.getLogger(__name__)

_ORIG_SSL_PREDICTOR_CLS = SSLAAIPredictor
_cached_ssl_predictor: SSLAAIPredictor | R5AAIPredictor | None = None
_cached_ssl_version: Literal["r5", "r4"] | None = None
_cached_forced_aligner: Any = None
_model_lock = Lock()
_aligner_lock = Lock()


def _resolve_r5_bundle_path() -> Path:
    configured = asset_override("R5_BUNDLE_PATH", "r5")
    return Path(configured or DEFAULT_R5_BUNDLE).expanduser().resolve()


def _has_r5_bundle(bundle: Path) -> bool:
    return (bundle / "configs" / "r5_streaming_contract.json").is_file() and (
        (bundle / "coreml_fp32" / "r5_wavlm_l8.mlpackage" / "Manifest.json").is_file()
        or (bundle / "torchscript" / "r5_end_to_end.ts.pt").is_file()
    )


def resolve_ssl_model_version() -> Literal["r5", "r4"]:
    """Choose R5 when configured/present, else fall back to R4."""
    requested = os.getenv("SSL_AAI_MODEL_VERSION", "auto").strip().lower()
    if requested == "r5":
        return "r5"
    if requested == "r4":
        return "r4"
    if requested != "auto":
        raise ValueError(f"SSL_AAI_MODEL_VERSION must be 'auto', 'r5', or 'r4', got {requested!r}")
    if SSLAAIPredictor is not _ORIG_SSL_PREDICTOR_CLS:
        return "r4"
    if (os.getenv("SSL_AAI_BUNDLE_PATH") or os.getenv("SSL_AAI_CHECKPOINT_PATH")) and not os.getenv(
        "R5_BUNDLE_PATH"
    ):
        return "r4"
    return "r5" if _has_r5_bundle(_resolve_r5_bundle_path()) else "r4"


def reset_model_cache() -> None:
    """Release cached predictor and forced-aligner instances (used by tests)."""
    global _cached_ssl_predictor, _cached_ssl_version, _cached_forced_aligner
    with _model_lock:
        if _cached_ssl_predictor is not None:
            _cached_ssl_predictor.cleanup()
        _cached_ssl_predictor = None
        _cached_ssl_version = None
    with _aligner_lock:
        if _cached_forced_aligner is not None and hasattr(_cached_forced_aligner, "cleanup"):
            _cached_forced_aligner.cleanup()
        _cached_forced_aligner = None


def get_ssl_predictor() -> SSLAAIPredictor | R5AAIPredictor:
    """Get or create cached SSL AAI predictor instance (R5 preferred, R4 fallback)."""
    global _cached_ssl_predictor, _cached_ssl_version
    version = resolve_ssl_model_version()
    with _model_lock:
        if _cached_ssl_predictor is not None and _cached_ssl_version == version:
            return _cached_ssl_predictor
        if _cached_ssl_predictor is not None:
            _cached_ssl_predictor.cleanup()
            _cached_ssl_predictor = None
        if version == "r5":
            r5_predictor = R5AAIPredictor(bundle_path=_resolve_r5_bundle_path())
            r5_predictor.load()
            _cached_ssl_predictor = r5_predictor
            _cached_ssl_version = "r5"
            logger.info("[model_cache] R5 predictor initialized and cached.")
            return _cached_ssl_predictor
        r4_predictor = SSLAAIPredictor(
            checkpoint_path=os.getenv("SSL_AAI_CHECKPOINT_PATH"),
            bundle_path=asset_override("SSL_AAI_BUNDLE_PATH", "r4"),
            lip_enabled=os.getenv("SSL_AAI_LIP_ENABLED", "1") == "1",
            dental_enabled=os.getenv("SSL_AAI_DENTAL_ENABLED", "0") == "1",
            calibrate_enabled=os.getenv("SSL_AAI_CALIBRATE_ENABLED", "1") == "1",
            labiodental_enabled=os.getenv("SSL_AAI_LABIODENTAL_ENABLED", "1") == "1",
            silence_mode=os.getenv("SSL_AAI_SILENCE_MODE", "reviewed"),
        )
        r4_predictor.load()
        _cached_ssl_predictor = r4_predictor
        _cached_ssl_version = "r4"
        logger.info("[model_cache] R4 predictor initialized and cached.")
        return _cached_ssl_predictor


def get_forced_aligner() -> ForcedAligner:
    """Get or create cached mHuBERT-147 + ctc_v1 ForcedAligner instance."""
    global _cached_forced_aligner
    from src.models.alignment import ForcedAligner

    with _aligner_lock:
        if _cached_forced_aligner is None:
            bundle = asset_override("MHUBERT_BUNDLE_PATH", "mhubert-147")
            aligner = ForcedAligner(bundle_path=bundle)
            aligner.load()
            _cached_forced_aligner = aligner
            logger.info("[model_cache] mHuBERT-147 ForcedAligner initialized and cached.")
        return cast(ForcedAligner, _cached_forced_aligner)


def get_ssl_cache_identity(
    contact_enabled: bool = False,
    *,
    lip_enabled: bool | None = None,
    dental_enabled: bool | None = None,
    calibrate_enabled: bool | None = None,
    labiodental_enabled: bool | None = None,
    silence_mode: str | None = None,
) -> dict[str, object]:
    """Identify actual loaded assets, or configured assets before lazy loading."""
    from src.audio.reference_tts import file_identity

    version = resolve_ssl_model_version()
    if version == "r5":
        with _model_lock:
            predictor = (
                _cached_ssl_predictor if isinstance(_cached_ssl_predictor, R5AAIPredictor) else None
            )
            r5_bundle = (
                (predictor.bundle_path if predictor else _resolve_r5_bundle_path())
                .expanduser()
                .resolve()
            )
            backend = (
                predictor.active_backend
                if predictor
                else os.getenv("R5_RUNTIME_BACKEND", "auto").strip().lower()
            )

            def _opt_identity(path: Path) -> object:
                return file_identity(path) if path.is_file() else "unavailable"

            return {
                "pipeline": "wavlm-l8-r5-direct-v1",
                "model_version": "r5",
                "runtime_backend": backend,
                "contract": _opt_identity(r5_bundle / "configs" / "r5_streaming_contract.json"),
                "sha256sums": _opt_identity(r5_bundle / "SHA256SUMS"),
                "decoder_ts": _opt_identity(r5_bundle / "torchscript" / "r5_bypass_decoder.ts.pt"),
                "e2e_ts": _opt_identity(r5_bundle / "torchscript" / "r5_end_to_end.ts.pt"),
                "coreml_wavlm": _opt_identity(
                    r5_bundle / "coreml_fp32" / "r5_wavlm_l8.mlpackage" / "Manifest.json"
                ),
            }

    with _model_lock:
        r4_predictor = (
            _cached_ssl_predictor
            if _cached_ssl_predictor is not None
            and not isinstance(_cached_ssl_predictor, R5AAIPredictor)
            else None
        )
        bundle = (
            (
                r4_predictor.bundle_path
                if r4_predictor
                else Path(asset_override("SSL_AAI_BUNDLE_PATH", "r4") or DEFAULT_R4_BUNDLE)
            )
            .expanduser()
            .resolve()
        )
        checkpoint = (
            r4_predictor.checkpoint_path
            if r4_predictor
            else Path(os.getenv("SSL_AAI_CHECKPOINT_PATH", str(bundle / "weights" / "r4.pt")))
        )
        contact_path = bundle / "weights" / "contact.pt"
        hints = {
            "lip": (
                lip_enabled
                if lip_enabled is not None
                else (
                    r4_predictor.lip_enabled
                    if r4_predictor
                    else os.getenv("SSL_AAI_LIP_ENABLED", "1") == "1"
                )
            ),
            "dental": (
                dental_enabled
                if dental_enabled is not None
                else (
                    r4_predictor.dental_enabled
                    if r4_predictor
                    else os.getenv("SSL_AAI_DENTAL_ENABLED", "0") == "1"
                )
            ),
            "calibrate": (
                calibrate_enabled
                if calibrate_enabled is not None
                else (
                    r4_predictor.calibrate_enabled
                    if r4_predictor
                    else os.getenv("SSL_AAI_CALIBRATE_ENABLED", "1") == "1"
                )
            ),
            "labiodental": (
                labiodental_enabled
                if labiodental_enabled is not None
                else (
                    r4_predictor.labiodental_enabled
                    if r4_predictor
                    else os.getenv("SSL_AAI_LABIODENTAL_ENABLED", "1") == "1"
                )
            ),
            "silence": (
                silence_mode
                if silence_mode is not None
                else (
                    r4_predictor.silence_mode
                    if r4_predictor
                    else os.getenv("SSL_AAI_SILENCE_MODE", "reviewed")
                )
            ),
        }
        return {
            "pipeline": "contentvec-l7-r4-final-hints-v3",
            "hints": hints if contact_enabled else "disabled",
            "hint_assets": {
                name: file_identity(bundle / name) if (bundle / name).is_file() else "unavailable"
                for name in (
                    "weights/lip.json",
                    "weights/dental.json",
                    "weights/labiodental.json",
                    "configs/output_calibration.json",
                    "weights/silence.joblib",
                    "configs/silence_reviewed.json",
                    "configs/silence_expanded.json",
                    "silence_fit.json",
                    "CONTENTVEC_STATE_SHA256",
                    "SHA256SUMS",
                )
            }
            if contact_enabled
            else "disabled",
            "decoder": file_identity(checkpoint),
            "contact_decoder": (
                file_identity(contact_path) if contact_path.is_file() else "unavailable"
            )
            if contact_enabled
            else "disabled",
            "encoder": file_identity(bundle / "weights" / "contentvec" / "model.safetensors"),
            "contract": file_identity(bundle / "configs" / "nine_channel_v12_100ms.yaml"),
            "encoder_config": file_identity(bundle / "weights" / "contentvec" / "config.json"),
            "feature_config": file_identity(
                bundle / "weights" / "contentvec" / "preprocessor_config.json"
            ),
        }
