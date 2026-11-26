"""Load local R4 hints with release integrity and encoder/clock checks.

Hint math follows the final reference bundle (CC BY-NC 4.0).
"""

import hashlib
import json
from pathlib import Path
from typing import Any

import joblib  # type: ignore[import-untyped]
import sklearn  # type: ignore[import-untyped]

from src.models.r4_calibration import OutputCalibrator
from src.models.r4_contract import StreamingContract
from src.models.r4_dental import DentalCorrection
from src.models.r4_labiodental import LabiodentalCorrection
from src.models.r4_lip import LipCorrection


def verified_asset(bundle: Path, relative: str) -> Path:
    """Check release bytes before reading hint parameters or unpickling assets."""
    manifest = {}
    for line in (bundle / "SHA256SUMS").read_text(encoding="utf-8").splitlines():
        digest, name = line.split(maxsplit=1)
        manifest[name.removeprefix("*").removeprefix("./")] = digest
    path = bundle / relative
    with path.open("rb") as source:
        digest = hashlib.file_digest(source, "sha256").hexdigest()
    if manifest.get(relative) != digest:
        raise ValueError(f"R4 hint asset checksum mismatch: {relative}")
    return path


def _validate_encoder(bundle: Path, metadata: dict[str, Any]) -> str:
    digest = verified_asset(bundle, "CONTENTVEC_STATE_SHA256").read_text(encoding="utf-8").strip()
    if metadata.get("contentvec", {}).get("parameter_sha256") != digest:
        raise ValueError("R4 hints require the matching ContentVec encoder")
    verified_asset(bundle, "weights/contentvec/model.safetensors")
    verified_asset(bundle, "weights/contentvec/config.json")
    verified_asset(bundle, "weights/contentvec/preprocessor_config.json")
    return digest


def load_lip(bundle: Path, metadata: dict[str, Any], contract: StreamingContract) -> LipCorrection:
    digest = _validate_encoder(bundle, metadata)
    return LipCorrection.load(
        verified_asset(bundle, "weights/lip.json"), contract, contentvec_sha256=digest
    )


def load_dental(
    bundle: Path, metadata: dict[str, Any], contract: StreamingContract
) -> DentalCorrection:
    _validate_encoder(bundle, metadata)
    correction = DentalCorrection.load(verified_asset(bundle, "weights/dental.json"))
    if len(correction.weights) != contract.feature_width:
        raise ValueError("Dental readout width does not match the streaming contract")
    return correction


def load_silence(bundle: Path, mode: str) -> tuple[Any, dict[str, Any], dict[str, int]]:
    provenance = json.loads(verified_asset(bundle, "silence_fit.json").read_text())
    if sklearn.__version__ != provenance["sklearn_version"]:
        raise ValueError(
            f"R4 silence hints require scikit-learn=={provenance['sklearn_version']}; "
            "install requirements.txt"
        )
    reviewed = verified_asset(bundle, "configs/silence_reviewed.json")
    config = json.loads(reviewed.read_text())
    with (bundle / "configs/nine_channel_v12_100ms.yaml").open("rb") as source:
        digest = hashlib.file_digest(source, "sha256").hexdigest()
    if (
        config["format_version"] != "streaming_silence_settling_v3"
        or config["streaming_contract_sha256"] != digest
        or (config["anchor_frames"], config["entrance_frames"], config["return_frames"])
        != (5, 6, 4)
    ):
        raise ValueError("Unsupported R4 silence contract")
    allowance = {}
    if mode == "expanded":
        expanded = json.loads(verified_asset(bundle, "configs/silence_expanded.json").read_text())
        if (
            expanded["format_version"] != "streaming_silence_coverage_v1"
            or expanded["baseline_sha256"] != hashlib.sha256(reviewed.read_bytes()).hexdigest()
        ):
            raise ValueError("Expanded silence gate requires the matching reviewed gate")
        allowance = expanded["isolated_noise_allowance"]
    classifier = joblib.load(verified_asset(bundle, "weights/silence.joblib"))
    return classifier, config["gates"], allowance


def load_output_calibration(bundle: Path) -> OutputCalibrator:
    return OutputCalibrator.load(verified_asset(bundle, "configs/output_calibration.json"))


def load_labiodental(
    bundle: Path, metadata: dict[str, Any], contract: StreamingContract
) -> LabiodentalCorrection:
    digest = _validate_encoder(bundle, metadata)
    correction = LabiodentalCorrection.load(
        verified_asset(bundle, "weights/labiodental.json"), contentvec_sha256=digest
    )
    if len(correction.weights) != contract.feature_width:
        raise ValueError("Labiodental readout width does not match the streaming contract")
    return correction
