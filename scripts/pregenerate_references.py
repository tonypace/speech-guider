#!/usr/bin/env python3
"""Pre-bake OmniVoice reference audio + R5 frames for canned Analysis & Prosody Lab texts."""

from __future__ import annotations

import base64
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.api.comparison import _prepare_reference_audio_tensor  # noqa: E402
from src.audio.prosody_lab import generate_prosody_reference  # noqa: E402
from src.audio.reference_tts import TTSProviderFactory  # noqa: E402
from src.models.aai_adapter import r4_trajectory_to_canonical_frames  # noqa: E402
from src.models.diagnostic_passages import DIAGNOSTIC_PASSAGES  # noqa: E402
from src.models.ssl_common import DEFAULT_SSL_FEATURE_CONFIG  # noqa: E402
from src.services.model_cache import get_ssl_predictor  # noqa: E402
from src.services.prebaked_references import DEFAULT_PREBAKED_PATH, _normalize_key  # noqa: E402

PROSODY_LAB_CANNED_TEXTS: tuple[str, ...] = (
    "We NEED to focus on the CORE, PROBLEMs first",
    "Well if you ACtually THINK about the PLAN",
    "I said FIFTEEN perCENT, not FIFty",
    "And then the WHOLE ROOM, went comPLETEly SIlent",
)


def main() -> None:
    provider = TTSProviderFactory.create("omnivoice")
    predictor = get_ssl_predictor()

    entries: dict[str, dict[str, Any]] = {}

    for passage in DIAGNOSTIC_PASSAGES:
        key = _normalize_key(passage.text)
        print(f"[prebake] Analysis passage: {passage.id} ({len(key)} chars)", flush=True)
        ref_audio = provider.synthesize(passage.text, output_sample_rate=8000)
        tensor = _prepare_reference_audio_tensor(ref_audio)
        pred = predictor.predict_with_metadata(
            tensor, sample_rate=DEFAULT_SSL_FEATURE_CONFIG.sample_rate
        )
        labio = pred.get("labiodental_retraction")
        frames = r4_trajectory_to_canonical_frames(
            pred["tvs"].numpy(),
            labio.numpy() if labio is not None else None,
        )
        # Round floats to 4 decimals to keep bundled JSON compact
        compact_frames = [{k: round(float(v), 4) for k, v in fr.items()} for fr in frames]
        entries[key] = {
            "kind": "analysis",
            "id": passage.id,
            "audio_base64": base64.b64encode(ref_audio.audio_bytes).decode("ascii"),
            "audio_sample_rate": ref_audio.sample_rate,
            "audio_duration_seconds": round(float(ref_audio.duration_seconds), 4),
            "audio_format": ref_audio.format,
            "frame_rate": DEFAULT_SSL_FEATURE_CONFIG.frame_rate,
            "frames": compact_frames,
            "frame_count": len(compact_frames),
        }

    for text in PROSODY_LAB_CANNED_TEXTS:
        key = _normalize_key(text)
        print(f"[prebake] Prosody Lab phrase: {key}", flush=True)
        prosody_ref = generate_prosody_reference(text)
        ref_audio = provider.synthesize(text, output_sample_rate=8000)
        tensor = _prepare_reference_audio_tensor(ref_audio)
        pred = predictor.predict_with_metadata(
            tensor, sample_rate=DEFAULT_SSL_FEATURE_CONFIG.sample_rate
        )
        frames = r4_trajectory_to_canonical_frames(pred["tvs"].numpy())
        compact_frames = [{k: round(float(v), 4) for k, v in fr.items()} for fr in frames]
        entries[key] = {
            "kind": "prosody_lab",
            "audio_base64": base64.b64encode(ref_audio.audio_bytes).decode("ascii"),
            "audio_sample_rate": ref_audio.sample_rate,
            "audio_duration_seconds": round(float(ref_audio.duration_seconds), 4),
            "audio_format": ref_audio.format,
            "frame_rate": DEFAULT_SSL_FEATURE_CONFIG.frame_rate,
            "frames": compact_frames,
            "frame_count": len(compact_frames),
            "prosody_reference": prosody_ref,
        }

    DEFAULT_PREBAKED_PATH.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_PREBAKED_PATH.write_text(
        json.dumps({"format_version": "prebaked_references_v1", "entries": entries}),
        encoding="utf-8",
    )
    size_kb = DEFAULT_PREBAKED_PATH.stat().st_size / 1024.0
    print(
        f"Wrote {len(entries)} pre-baked references to {DEFAULT_PREBAKED_PATH} ({size_kb:.1f} KiB)"
    )


if __name__ == "__main__":
    main()
