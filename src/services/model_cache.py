"""Shared model caching for SSL AAI predictor.

Provides a globally cached singleton SSLAAIPredictor to avoid
redundant model loading across analysis and comparison endpoints.
"""

import logging
import os
from threading import Lock

from src.models.ssl_aai_predictor import SSLAAIPredictor

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
                bundle_path=os.getenv("SSL_AAI_BUNDLE_PATH"),
            )
            predictor.load()
            _cached_ssl_predictor = predictor
            logger.info("[model_cache] R4 predictor initialized and cached.")
    return _cached_ssl_predictor
