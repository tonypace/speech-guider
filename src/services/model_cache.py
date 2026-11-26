"""Shared model caching for SSL AAI predictor.

Provides a globally cached singleton SSLAAIPredictor to avoid
redundant model loading across analysis and comparison endpoints.
"""

import logging
import os
from pathlib import Path
from threading import Lock

from src.models.ssl_aai_predictor import SSLAAIPredictor
from src.services.desktop_assets import asset_override

logger = logging.getLogger(__name__)

_cached_ssl_predictor: SSLAAIPredictor | None = None
_model_lock = Lock()


def get_ssl_predictor() -> SSLAAIPredictor:
    """Get or create cached SSL AAI predictor instance."""
    global _cached_ssl_predictor
    with _model_lock:
        if _cached_ssl_predictor is None:
            predictor = SSLAAIPredictor(
                checkpoint_path=os.getenv("SSL_AAI_CHECKPOINT_PATH"),
                bundle_path=asset_override("SSL_AAI_BUNDLE_PATH", "r4"),
                lip_enabled=os.getenv("SSL_AAI_LIP_ENABLED", "1") == "1",
                dental_enabled=os.getenv("SSL_AAI_DENTAL_ENABLED", "0") == "1",
                calibrate_enabled=os.getenv("SSL_AAI_CALIBRATE_ENABLED", "1") == "1",
                labiodental_enabled=os.getenv("SSL_AAI_LABIODENTAL_ENABLED", "1") == "1",
                silence_mode=os.getenv("SSL_AAI_SILENCE_MODE", "reviewed"),
            )
            predictor.load()
            _cached_ssl_predictor = predictor
            logger.info("[model_cache] R4 predictor initialized and cached.")
    return _cached_ssl_predictor


def get_ssl_cache_identity(contact_enabled: bool = False) -> dict[str, object]:
    """Identify actual loaded assets, or configured assets before lazy loading."""
    from src.audio.reference_tts import file_identity
    from src.models.ssl_aai_predictor import DEFAULT_R4_BUNDLE

    with _model_lock:
        predictor = _cached_ssl_predictor
        bundle = (
            (
                predictor.bundle_path
                if predictor
                else Path(asset_override("SSL_AAI_BUNDLE_PATH", "r4") or DEFAULT_R4_BUNDLE)
            )
            .expanduser()
            .resolve()
        )
        checkpoint = (
            predictor.checkpoint_path
            if predictor
            else Path(os.getenv("SSL_AAI_CHECKPOINT_PATH", str(bundle / "weights" / "r4.pt")))
        )
        contact_path = bundle / "weights" / "contact.pt"
        hints = {
            "lip": predictor.lip_enabled
            if predictor
            else os.getenv("SSL_AAI_LIP_ENABLED", "1") == "1",
            "dental": predictor.dental_enabled
            if predictor
            else os.getenv("SSL_AAI_DENTAL_ENABLED", "0") == "1",
            "calibrate": predictor.calibrate_enabled
            if predictor
            else os.getenv("SSL_AAI_CALIBRATE_ENABLED", "1") == "1",
            "labiodental": predictor.labiodental_enabled
            if predictor
            else os.getenv("SSL_AAI_LABIODENTAL_ENABLED", "1") == "1",
            "silence": predictor.silence_mode
            if predictor
            else os.getenv("SSL_AAI_SILENCE_MODE", "reviewed"),
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
