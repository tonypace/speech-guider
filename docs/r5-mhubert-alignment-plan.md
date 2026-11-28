# R5 + mHuBERT-147 Forced Alignment & Pronunciation Diagnostics Plan

**Status:** Implemented (R5 WavLM-Base+ + separate mHuBERT-147 forced aligner; classroom pilot testing deferred)  
**Target Passages:** Curated diagnostic passages in `src/models/diagnostic_passages.py` (defaulting to the 5-sentence diagnostic reading in [index.html](../app/templates/index.html))

> *Every Thursday morning, Ruth and Phil drive their silver van past the busy harbor. Phil loves fresh fruit, so he grabs six sweet peaches and three red apples at the market. A thick fog rolls over the water, making the paths wet and slick. Ruth checks her watch, smiles, and says, "They'll ship those crates before noon if we hurry." Then they bet a small bat can reach the big ship before the sheep cross.*

---

## 1. Purpose & Design Principle

The shipped R5 articulatory export (`R5_CoreML_Export_v1`) uses **`microsoft/wavlm-base-plus` (layers 1–8)** rather than `mHuBERT-147`, and no pretrained phoneme/IPA CTC head exists for frozen `wavlm-base-plus` L1–L8. Therefore, `speech-guider` separates the two concerns cleanly:

1. **R5 Articulatory Inference (`src/models/r5_predictor.py`):** Hybrid Apple Silicon Core ML FP32 (`coreml_fp32/r5_wavlm_l8.mlpackage`, `ComputeUnit.ALL`) + CPU TorchScript bypass decoder (`torchscript/r5_bypass_decoder.ts.pt`), with full CPU TorchScript (`torchscript/r5_end_to_end.ts.pt`) fallback, producing 11 articulatory channels (`LP..LAT, BLCL, BLCD`) + 43-d acoustic bypass + Stage 5 realization badges (`weights/realization_badges_v1.json`).
2. **Offline IPA Phoneme Forced Alignment & 6-Category Diagnostics:** Lazy-loaded `utter-project/mHuBERT-147` + `istomin9192/mHuBERT-147-ipa-head` (`ctc_v1`) + offline CMUdict→IPA G2P (`src/models/g2p.py`, zero `espeak-ng` dependency) + constrained NumPy CTC Viterbi forced aligner (`src/models/alignment.py`).

### Clarifying How Neural Forced Alignment Works
Neural CTC forced aligners do **not** run TTS or synthesize matching audio:
- Text-to-phoneme conversion (G2P) is a deterministic dictionary/rule lookup (`cmudict_ipa.json` + OOV rules), with no audio synthesis or `espeak-ng` runtime binary required.
- Student 16 kHz mono audio makes **one** full-utterance pass through `mHuBERT-147` + `ctc_v1` BiLSTM head to produce `[T, 46]` frame log-probabilities (20 ms frame step).
- A vectorized **Viterbi CTC dynamic program** aligns the canonical target phoneme sequence monotonically to `[T, 46]`, yielding exact `[start_time, end_time]` boundaries per phoneme and word plus segment GOP scores.

---

## 2. Target Pronunciation Weakness Categories

The Analysis diagnostic evaluates six learner-weakness groups:

| Category | Target Contrast | Passage Test Words | Primary Signals |
| --- | --- | --- | --- |
| **1. Voiceless dental fricative** | `/θ/` vs `/s/, /f/, /t/` | *Thursday, Ruth, thick, paths, three* | CTC-GOP + `log P(θ) − max log P(s, f, t)` + R5/R4 `TTCL`/`TTCD` cue |
| **2. Voiced dental fricative** | `/ð/` vs `/d/, /z/` | *the, their, they'll, those, then, they* | CTC-GOP + `log P(ð) − max log P(d, z)` + R5/R4 `TTCL`/`TTCD` cue |
| **3. Labiodental vs bilabial glide** | `/v/` vs `/w/` | `/v/`: *drive, van, loves, over*<br>`/w/`: *water, wet, watch, we* | CTC-GOP + `log P(v) − log P(w)` + R5/R4 `LP`/`LA`/`labiodental_retraction` cross-check |
| **4. Liquid contrast** | `/r, ɹ̩/` vs `/l, l̩/` | `/r/`: *Ruth, drive, harbor, fresh, fruit, grabs, three, red, rolls, hurry, crates, reach, cross*<br>`/l/`: *Phil, silver, loves, apples, slick, smiles, they'll, small* | CTC-GOP + `log P(r) − log P(l)` + R5/R4 `LAT` cross-check |
| **5. Final consonants & clusters** | Deletion / devoicing / simplification | *past, grabs, six, paths, wet, watch, crates, cross* | Aligned coda window peak posterior vs `<blank>` dominance + R5 Stage 5 `coda_kp_del` supporting oral-seal cue |
| **6. Tense/lax & front vowel pairs** | `/ɪ/` vs `/iː/`; `/æ/` vs `/ɛ/` | *ship* `/ɪ/` vs *sheep* `/iː/`; *bat* `/æ/` vs *bet* `/ɛ/` | CTC posterior margin (`ɪ/i`, `æ/ɛ`) + **Praat F1/F2 formants & vowel duration** on aligned vowel slices |

---

## 3. Verified Model & Runtime Specifications

### 3.1 R5 Articulatory Pipeline (`R5_CoreML_Export_v1`)
- **Encoder:** `microsoft/wavlm-base-plus` (`L1..L8`, `do_normalize = false` — raw unnormalized mono float32 `[-1, 1]`).
- **Apple Silicon Runtime:** Core ML **FP32** (`coreml_fp32/r5_wavlm_l8.mlpackage`, `ComputeUnit.ALL`, macOS 15+) + CPU TorchScript `r5_bypass_decoder.ts.pt`.
  - Measured on Apple M3: **15.14 ms P50 / 16.99 ms P95** per 100 ms hop (~10× faster than PyTorch CPU), with `mean_oral_mae = 4e-7` (`worst_max_diff = 1.7e-5`) across all 6 bundle fixtures.
  - Note: FP16 Core ML conversion introduced quantization drift (`oral_mae = 0.056` on `silence_control`), and `r5_bypass_decoder.ts.pt` contains a 1D matmul unsupported by `coremltools` 9.0, so the hybrid Core ML FP32 + CPU decoder split is used, with `r5_end_to_end.ts.pt` on CPU as fallback (PyTorch MPS is disabled for R5 TorchScript due to float64 ops).

### 3.2 Shared Alignment Encoder: `utter-project/mHuBERT-147`
- **Architecture:** HuBERT-base (7-layer conv frontend, stride 320 samples = 20 ms / 50 Hz, 12 Transformer layers, `hidden_size=768`).
- **Parameters & Footprint:** ~94.4M params; ~360 MiB FP32; **CC-BY-NC-4.0**.

### 3.3 Phoneme CTC Head: `istomin9192/mHuBERT-147-ipa-head` (`ctc_v1`)
- **Compatibility:** Trained on frozen `utter-project/mHuBERT-147` (`last_hidden_state`), **10.88 MiB**, **Apache-2.0**.
- **Safe Loading Policy:** Re-implemented `CTCHeadModel` in `src/models/ipa_ctc_head.py` loaded via `torch.load(..., weights_only=True)` after SHA-256 verification (no `trust_remote_code=True`).

---

## 4. Calibration & Deferred Classroom Pilot

Per [release-contracts.md](release-contracts.md), diagnostics surface neutral, observational cues (*"Weak `/θ/` cue — leaned closer to `/s/`"*) with clickable audio/SVG inspection rather than uncalibrated clinical pass/fail claims. Classroom pilot logging/review tooling (`r5-client-suggestions.md`) is explicitly deferred until after this integration and L2 recording calibration.
