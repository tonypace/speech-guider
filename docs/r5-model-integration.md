# R5 Articulatory Model Integration (`R5_CoreML_Export_v1`)

Analysis and Comparison Lab support the R5 streaming articulatory bundle (`external/R5_CoreML_Export_v1/`) alongside backwards-compatible R4 fallback.

## Model & Streaming Contract
- **Encoder:** `microsoft/wavlm-base-plus` layers 1–8 (`do_normalize = false` — raw unnormalized mono float32 audio in `[-1, 1]`).
- **Replay windowing:** 16,000 Hz mono, `19,200`-sample window (1.2 s), `1,600`-sample hop (100 ms), `1,600`-sample lookahead (100 ms), committed slice `[49:54]` (5 frames per hop at 50 Hz, frame centers `160 + 320 * frame_index`).
- **Outputs:**
  - `11` articulatory channels: `LP, LA, TTCL, TTCD, TBCL, TBCD, VEL, GLO, LAT, BLCL, BLCD` (channels `0..8` map directly to the canonical 9-field SVG renderer; `BLCL, BLCD` track tongue blade pitch/clearance).
  - `43`-dim unnormalized acoustic bypass (`committed_bypass_43d`), consumed alongside `committed_11ch` by Stage 5 realization badges (`weights/realization_badges_v1.json`).

## Apple Silicon Runtime Policy
- **Default (`R5_RUNTIME_BACKEND=auto`):** Uses hybrid **Core ML FP32** `coreml_fp32/r5_wavlm_l8.mlpackage` (`ComputeUnit.ALL`, macOS 15+) paired with CPU TorchScript `torchscript/r5_bypass_decoder.ts.pt`.
  - Measured on Apple M3: **15.14 ms P50 / 16.99 ms P95** per hop, `mean_oral_mae = 4e-7` across all 6 reference fixtures.
  - Regenerate the Core ML package via `python scripts/convert_r5_coreml.py`.
- **Fallback (`R5_RUNTIME_BACKEND=torchscript`):** Runs `torchscript/r5_end_to_end.ts.pt` on **CPU** (PyTorch MPS is never used for R5 TorchScript due to float64 tensor ops in the traced graph).

## Environment Variables
| Variable | Default | Behavior |
| --- | --- | --- |
| `SSL_AAI_MODEL_VERSION` | `auto` | `auto` selects R5 when `R5_BUNDLE_PATH` / `external/R5_CoreML_Export_v1` is present, else R4; set `r5` or `r4` to force. |
| `R5_BUNDLE_PATH` | `external/R5_CoreML_Export_v1` | Overrides the R5 bundle directory. |
| `R5_RUNTIME_BACKEND` | `auto` | `auto`, `coreml_split`, or `torchscript`. |
| `R5_COREML_COMPUTE_UNITS` | `ALL` | `ALL`, `CPU_AND_GPU`, `CPU_AND_NE`, or `CPU_ONLY`. |
| `MHUBERT_BUNDLE_PATH` | `external/mhubert-147` | Overrides the staged `mHuBERT-147` + `ctc_v1` aligner bundle directory. |
