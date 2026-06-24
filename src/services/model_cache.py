"""Shared model caching for SSL AAI predictor.

Provides a globally cached singleton SSLAAIPredictor to avoid
redundant model loading across analysis and comparison endpoints.
"""

import logging
import os

logger = logging.getLogger(__name__)

_cached_ssl_predictor = None


def get_ssl_predictor():
    """Get or create cached SSL AAI predictor instance."""
    global _cached_ssl_predictor
    if _cached_ssl_predictor is None:
        from src.models.ssl_aai_predictor import SSLAAIPredictor

        checkpoint_path = os.getenv("SSL_AAI_CHECKPOINT_PATH")
        logger.info("[model_cache] Initializing SSL AAI predictor (first time)...")
        if checkpoint_path:
            logger.info(f"[model_cache] Using checkpoint: {checkpoint_path}")
        else:
            logger.info("[model_cache] Using default checkpoint path")

        _cached_ssl_predictor = SSLAAIPredictor(checkpoint_path=checkpoint_path)
        _cached_ssl_predictor.load()
        logger.info("[model_cache] SSL AAI predictor initialized and cached.")
    return _cached_ssl_predictor
