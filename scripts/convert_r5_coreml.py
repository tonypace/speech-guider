#!/usr/bin/env python3
"""Convert R5's WavLM-Base+ L1..L8 TorchScript graph to Core ML FP32 (.mlpackage).

R5's bypass decoder contains a 1D-vector matmul not lowered by coremltools 9.0,
and FP16 WavLM introduces quantization drift on low-energy segments. Using
Core ML FP32 (`mlprogram`, macOS 15+, ComputeUnit.ALL) for `r5_wavlm_l8` paired
with CPU TorchScript `r5_bypass_decoder.ts.pt` achieves ~10x speedup over CPU
TorchScript with near-exact numerical parity across all fixtures.
"""

from __future__ import annotations

import argparse
import json
import shutil
import time
from pathlib import Path
from typing import Any

import coremltools as ct  # type: ignore[import-untyped]
import numpy as np
import torch


def convert_and_benchmark(
    bundle_dir: Path, *, warmup_hops: int = 10, bench_hops: int = 40
) -> dict[str, Any]:
    out_dir = bundle_dir / "coreml_fp32"
    pkg_path = out_dir / "r5_wavlm_l8.mlpackage"
    if pkg_path.exists():
        shutil.rmtree(pkg_path)
    out_dir.mkdir(parents=True, exist_ok=True)

    ts_dir = bundle_dir / "torchscript"
    traced_wavlm = torch.jit.load(str(ts_dir / "r5_wavlm_l8.ts.pt"), map_location="cpu").eval()
    mlmodel = ct.convert(
        traced_wavlm,
        convert_to="mlprogram",
        minimum_deployment_target=ct.target.macOS15,
        compute_precision=ct.precision.FLOAT32,
        compute_units=ct.ComputeUnit.ALL,
        inputs=[ct.TensorType(name="raw_window", shape=(1, 19200), dtype=np.float32)],
        outputs=[ct.TensorType(name="ssl_layers", dtype=np.float32)],
    )
    mlmodel.save(str(pkg_path))

    decoder = torch.jit.load(str(ts_dir / "r5_bypass_decoder.ts.pt"), map_location="cpu").eval()
    fman = json.loads(
        (bundle_dir / "fixtures" / "fixtures_manifest.json").read_text(encoding="utf-8")
    )
    fixture_metrics: dict[str, dict[str, float]] = {}
    oral_maes: list[float] = []
    max_diffs: list[float] = []

    with torch.inference_mode():
        for fix in fman["fixtures"]:
            fdir = bundle_dir / "fixtures" / fix["name"]
            wins = np.load(fdir / "raw_windows.npy")
            ref_11 = np.load(fdir / "ref_committed_11ch.npy")
            preds: list[np.ndarray] = []
            for i in range(len(wins)):
                x = wins[i : i + 1]
                ssl = mlmodel.predict({"raw_window": x})["ssl_layers"].astype(np.float32)
                o11, _ = decoder(torch.from_numpy(x), torch.from_numpy(ssl))
                preds.append(o11.numpy()[0])
            sp = np.stack(preds, axis=0)
            if not np.isfinite(sp).all():
                raise RuntimeError(f"Non-finite output on fixture {fix['name']}")
            oral_mae = float(np.mean(np.abs(sp[..., :7] - ref_11[..., :7])))
            max_diff = float(np.max(np.abs(sp - ref_11)))
            if oral_mae >= 1e-4:
                raise RuntimeError(f"Parity gate failed on {fix['name']}: oral_mae={oral_mae}")
            oral_maes.append(oral_mae)
            max_diffs.append(max_diff)
            fixture_metrics[fix["name"]] = {
                "oral_mae": round(oral_mae, 7),
                "max_diff": round(max_diff, 7),
            }

    dummy = np.zeros((1, 19200), dtype=np.float32)
    benchmarks: dict[str, dict[str, float | bool]] = {}
    for cu_name, cu in (("ALL", ct.ComputeUnit.ALL), ("CPU_AND_GPU", ct.ComputeUnit.CPU_AND_GPU)):
        cu_model = ct.models.MLModel(str(pkg_path), compute_units=cu)
        for _ in range(warmup_hops):
            ssl = cu_model.predict({"raw_window": dummy})["ssl_layers"].astype(np.float32)
            with torch.inference_mode():
                decoder(torch.from_numpy(dummy), torch.from_numpy(ssl))
        lats: list[float] = []
        for _ in range(bench_hops):
            t0 = time.perf_counter()
            ssl = cu_model.predict({"raw_window": dummy})["ssl_layers"].astype(np.float32)
            with torch.inference_mode():
                decoder(torch.from_numpy(dummy), torch.from_numpy(ssl))
            lats.append((time.perf_counter() - t0) * 1000.0)
        arr = np.asarray(lats)
        benchmarks[cu_name] = {
            "p50_ms": round(float(np.percentile(arr, 50)), 2),
            "p95_ms": round(float(np.percentile(arr, 95)), 2),
            "p99_ms": round(float(np.percentile(arr, 99)), 2),
            "meets_proxy_60ms_p95": bool(np.percentile(arr, 95) < 60.0),
        }

    report: dict[str, Any] = {
        "pipeline": "coreml_fp32_wavlm_l8_plus_cpu_bypass_decoder",
        "precision": "fp32",
        "mean_oral_mae": round(float(np.mean(oral_maes)), 7),
        "worst_max_diff": round(float(max(max_diffs)), 7),
        "fixtures": fixture_metrics,
        "benchmarks": benchmarks,
    }
    (out_dir / "coreml_parity_bench.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--bundle-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "external" / "R5_CoreML_Export_v1",
    )
    parser.add_argument("--warmup-hops", type=int, default=10)
    parser.add_argument("--bench-hops", type=int, default=40)
    args = parser.parse_args()
    report = convert_and_benchmark(
        args.bundle_dir.expanduser().resolve(),
        warmup_hops=args.warmup_hops,
        bench_hops=args.bench_hops,
    )
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    main()
