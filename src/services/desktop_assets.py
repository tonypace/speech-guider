"""Resolve separately installed desktop assets without loading models at startup."""

import os
from pathlib import Path


def desktop_asset_dir() -> Path | None:
    configured = os.getenv("SPEECH_GUIDER_ASSET_DIR")
    return Path(configured).expanduser().resolve() if configured else None


def asset_override(env_name: str, relative_path: str) -> str | None:
    if configured := os.getenv(env_name):
        return str(Path(configured).expanduser().resolve())
    root = desktop_asset_dir()
    return str(root / relative_path) if root is not None else None


def desktop_assets_missing() -> list[str]:
    """List actionable feature prerequisites without running local executables."""
    root = desktop_asset_dir()
    if root is None:
        return []
    bundle = Path(asset_override("SSL_AAI_BUNDLE_PATH", "r4") or root / "r4")
    checkpoint = Path(os.getenv("SSL_AAI_CHECKPOINT_PATH") or bundle / "weights" / "r4.pt")
    missing = []
    if not all(
        path.is_file()
        for path in (
            checkpoint.expanduser(),
            bundle / "configs" / "nine_channel_v12_100ms.yaml",
            bundle / "weights" / "contentvec" / "model.safetensors",
            bundle / "weights" / "contentvec" / "config.json",
            bundle / "weights" / "contentvec" / "preprocessor_config.json",
        )
    ):
        missing.append("R4 / ContentVec (articulatory analysis): install the R4 bundle under r4/.")
    binary = Path(asset_override("OMNIVOICE_TTS_PATH", "omnivoice/omnivoice-tts") or "")
    if not (binary.is_file() and os.access(binary, os.X_OK)) or not all(
        Path(asset_override(env_name, relative_path) or "").is_file()
        for env_name, relative_path in (
            ("OMNIVOICE_MODEL_PATH", "omnivoice/models/omnivoice-base-Q8_0.gguf"),
            ("OMNIVOICE_CODEC_PATH", "omnivoice/models/omnivoice-tokenizer-F32.gguf"),
        )
    ):
        missing.append(
            "OmniVoice (reference speech): install its executable and models under omnivoice/."
        )
    return missing
