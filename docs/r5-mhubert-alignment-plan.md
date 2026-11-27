# R5 + mHuBERT-147 Forced Alignment & Pronunciation Diagnostics Plan

**Status:** Planned for upcoming R5 (`mHuBERT`) branch  
**Target Passage:** Default 5-sentence diagnostic reading in [index.html](file:///Users/tonypace/Documents/Code/speech-guider/app/templates/index.html#L85-L89) (`#target_text`)

> *Every Thursday morning, Ruth and Phil drive their silver van past the busy harbor. Phil loves fresh fruit, so he grabs six sweet peaches and three red apples at the market. A thick fog rolls over the water, making the paths wet and slick. Ruth checks her watch, smiles, and says, "They'll ship those crates before noon if we hurry." Then they bet a small bat can reach the big ship before the sheep cross.*

---

## 1. Purpose & Design Principle

Instead of bundling a redundant 300M+ parameter standalone forced aligner (`wav2vec2-lv-60-espeak-cv-ft` or `MMS-300m-FA`, which adds +600 MiB to +1.2 GiB RAM/disk and duplicates a 50 Hz SSL speech encoder), the R5 branch will **share a single frozen `utter-project/mHuBERT-147` encoder** across:

1. **R5 articulatory inference** (upcoming mHuBERT-based articulatory branch), and
2. **Offline IPA phoneme forced alignment, CTC-GOP scoring, and 6-category pronunciation weakness diagnostics** using **`istomin9192/mHuBERT-147-ipa-head` (`ctc_v1`)**.

### Clarifying How Neural Forced Alignment Works
Neural CTC forced aligners do **not** run TTS or synthesize matching audio:
- Text-to-phoneme conversion (G2P) is a deterministic dictionary/rule lookup (e.g., CMUdict → IPA), with no audio synthesis or `espeak-ng` runtime binary required.
- Student 16 kHz mono audio makes **one** full-utterance pass through the shared 50 Hz encoder + `ctc_v1` BiLSTM head to produce `[T, 46]` frame log-probabilities (20 ms frame step).
- A ~50-line **Viterbi CTC dynamic program** aligns the canonical target phoneme sequence monotonically to `[T, 46]`, yielding exact `[start_time, end_time]` boundaries per phoneme and word plus log-posterior scores (GOP).

---

## 2. Target Pronunciation Weakness Categories

The Analysis diagnostic evaluates six learner-weakness groups present in the default 5-sentence passage:

| Category | Target Contrast | Passage Test Words | Primary Signals |
| --- | --- | --- | --- |
| **1. Voiceless dental fricative** | `/θ/` vs `/s/, /f/, /t/` | *Thursday, Ruth, thick, paths, three* | CTC-GOP + `log P(θ) − max log P(s, f, t)`; optional R4/R5 dental probe |
| **2. Voiced dental fricative** | `/ð/` vs `/d/, /z/` | *the, their, they'll, those, then, they* | CTC-GOP + `log P(ð) − max log P(d, z)` |
| **3. Labiodental vs bilabial glide** | `/v/` vs `/w/` | `/v/`: *drive, van, loves, over*<br>`/w/`: *water, wet, watch, we* | CTC-GOP + `log P(v) − log P(w)` + R4/R5 `labiodental_retraction` & `LP` cross-check |
| **4. Liquid contrast** | `/r, ɹ̩/` vs `/l, l̩/` | `/r/`: *Ruth, drive, harbor, fresh, fruit, grabs, three, red, rolls, hurry, crates, reach, cross*<br>`/l/`: *Phil, silver, loves, apples, slick, smiles, they'll, small* | CTC-GOP + `log P(r) − log P(l)` + R4/R5 `LAT` cross-check |
| **5. Final consonants & clusters** | Deletion / devoicing / simplification | *past, grabs, six, paths, wet, watch, crates, cross* | Aligned coda window peak posterior vs `<blank>` dominance & expected cluster-stop presence |
| **6. Tense/lax & front vowel pairs** | `/ɪ/` vs `/iː/`; `/æ/` vs `/ɛ/` | *ship* `/ɪ/` vs *sheep* `/iː/`; *bat* `/æ/` vs *bet* `/ɛ/` | CTC posterior margin (`ɪ/i`, `æ/ɛ`) + **Praat F1/F2 formants & vowel duration** on aligned vowel slices |

---

## 3. Verified Model & Asset Specifications

### 3.1 Shared Encoder: `utter-project/mHuBERT-147`
- **Architecture:** HuBERT-base (7-layer conv frontend, stride 320 samples = 20 ms / 50 Hz, receptive field 400 samples; 12 Transformer layers, `hidden_size=768`, 12 attention heads, GELU).
- **Parameters & Footprint:** ~94.4M params; ~360 MiB FP32 (~180 MiB FP16) on disk and weight RAM.
- **Training & License:** 90,430 hours across 147 open-license languages; **CC-BY-NC-4.0** (compatible with `Speech Guider - Local Noncommercial.pkg`).
- **Why multilingual:** Cross-lingual phonetic training sharpens L2 non-native substitutions (`/θ/→/s,f,t/`, `/ð/→/d,z/`, `/v/→/w/`, `/r/↔/l/`, tense/lax vowel mergers).

### 3.2 Phoneme CTC Head: `istomin9192/mHuBERT-147-ipa-head` (`ctc_v1`)
- **Compatibility:** Trained strictly on **100% frozen** `utter-project/mHuBERT-147` (`last_hidden_state`), requiring zero backbone weight divergence from R5.
- **Architecture (`CTCHeadModel`):**
  - `proj`: `Linear(768, 256)`
  - `lstm`: `LSTM(256, 256, num_layers=2, bidirectional=True, batch_first=True, dropout=0.3)`
  - `drop`: `Dropout(0.3)` (inactive in `.eval()`)
  - `head`: `Linear(512, 46)` (`output_dim = 46`, `blank_id = 45`)
- **Footprint & License:** **10.88 MiB** (`11,404,379` bytes `ctc_v1/pytorch_model.bin`); **Apache-2.0**.
- **Benchmarks (upstream):** TIMIT Test PER = `0.0957`, Buckeye Val PER = `0.2150`.
- **Safe Loading Policy:** Re-implement the ~25-line `CTCHeadModel` directly in `src/models/ipa_ctc_head.py` and load weights with `torch.load(..., weights_only=True)` after SHA-256 verification (do **not** use `trust_remote_code=True`).

### 3.3 Output IPA Vocabulary (45 Phones + `<blank>` = 46)
Index `45` is `<blank>`. Indices `0..44`:

```text
0:sil  1:aɪ   2:aʊ   3:b    4:d    5:dʒ   6:eɪ   7:f    8:g
9:h    10:i   11:j   12:k   13:l   14:l̩   15:m   16:m̩   17:n
18:n̩   19:oʊ  20:p   21:r   22:s   23:t   24:tʃ  25:u   26:v
27:w   28:z   29:æ   30:ð   31:ŋ   32:ɑ   33:ɔ   34:ɔɪ  35:ə
36:ɛ   37:ɪ   38:ɹ̩   39:ɾ   40:ʃ   41:ʊ   42:ʒ   43:ʔ   44:θ
```

Key upstream TIMIT/Buckeye normalization rules to mirror in our English G2P mapper:
- Stop closure + release merged into single release phone (`bcl+b → b`, `dcl+d → d`, etc.)
- Syllabics & schwa: `ER/AXR → ɹ̩`, `EL → l̩`, `EM → m̩`, `EN → n̩`, `AH0/AX → ə`, `AH1/AH2 → ə` (verify `ʌ→ə` collapse against `ipa_map.json` — note `ʌ` is absent from the 45-phone set and maps to `ə`), flap `DX → ɾ`, glottal stop `Q → ʔ`.
- Long/short front vowel distinction: `/iː/` maps to `i` (index `10`); `/ɪ/` maps to `ɪ` (index `37`); `/æ/` maps to `æ` (index `29`); `/ɛ/` maps to `ɛ` (index `36`).

---

## 4. Integration Architecture & Planned Files

### 4.1 Clock & Forward-Pass Sharing
- Both `mHuBERT-147` and ContentVec-L7 operate on 16 kHz mono audio with 320-sample stride (**50 Hz**, center `160 + 320 * frame_index`).
- Unlike R4's 1.2 s sliding window (12× overlapping compute for streaming-compatible articulatory state), `ctc_v1` uses a **bidirectional** BiLSTM over `mHuBERT-147` `last_hidden_state`.
- **Execution in `POST /api/analyze`:** Run `mHuBERT-147` **once** over the full utterance (`torch.inference_mode()`), feeding its hidden states to both **R5** (if R5 uses full-utterance or cached encoder features) and **`ctc_v1`**. Align frame count to R4/R5 sample-center timestamps (`160 + 320 * i`).

### 4.2 Planned Backend Modules
1. **`src/models/mhubert_encoder.py`** *(new)*
   - Thread-safe lazy singleton loader for local `utter-project/mHuBERT-147` (`local_files_only=True`, SHA-256 verification, MPS/CUDA/CPU device selection + `clear_torch_device_cache`).
2. **`src/models/ipa_ctc_head.py`** *(new)*
   - Typed `CTCHeadModel` PyTorch `nn.Module` matching `ctc_v1` (`weights_only=True` load, `ipa_map.json` validation).
3. **`src/models/g2p.py`** *(new)*
   - Offline English CMUdict JSON (~3 MB bundled asset) + deterministic ARPAbet → 45-phone `ctc_v1` IPA mapper (with pronunciation variants for words like *the*, *their*, *they'll*, *paths* `/θs/` vs `/ðz/`) + rule-based OOV fallback. Zero `espeak-ng` dependency.
4. **`src/models/alignment.py`** *(replace `ForcedAligner` stub)*
   - Keep existing `PhonemeAlignment`, `WordAlignment`, `SentenceAlignment`, `PronunciationError`, and `_classify_phoneme`.
   - Implement pure-NumPy/PyTorch constrained CTC Viterbi forced aligner (`~50` LOC) over `[T, 46]` log-posteriors, returning word and phoneme `[start_time, end_time]`, `score` (segment GOP), and `predicted_phoneme` (top non-blank/competing phone inside each aligned span).
5. **`src/models/pronunciation_diagnostics.py`** *(new)*
   - Evaluates the 6 weakness categories against aligned `SentenceAlignment` + `[T, 46]` posteriors + Praat `AudioContext` + R4/R5 trajectory:
     - **Consonant substitutions** (`/θ/`, `/ð/`, `/v/↔/w/`, `/r/↔/l/`): log-likelihood ratio between target phone and category confusables inside the aligned span.
     - **Final clusters** (`past, grabs, six, paths, wet, watch, crates, cross`): coda phone posterior & `<blank>` ratio per coda consonant in word-final position.
     - **Vowel pairs** (`ship/sheep`, `bat/bet`): CTC posterior margin + Praat `Sound.to_formant_burg()` F1/F2 medians + segment duration over aligned vowel intervals.
     - **Articulatory cross-checks:** sample `labiodental_retraction`, `LP`, `LAT`, `TTCL`, and `dental` over `[start_frame:end_frame]` for corroborating visual evidence.
6. **`app/api/analyze.py` & `app/models/schemas.py`** *(update)*
   - Run `ForcedAligner` in `_run_analysis_pipeline` using `target_text`.
   - Feed real aligned `vowel_timestamps` (`is_vowel=True`) and `word_timestamps` into `ProsodyAnalyzer.analyze_complete(...)`, unlocking real vocalic **nPVI** and **word stress prominence** alongside `PronunciationError` output.
   - Emit `alignment`, `errors`, and `pronunciation_diagnostics` in `/api/analyze` JSON while preserving graceful partial fallback if `mhubert-147` assets are absent.
7. **`app/api/errors.py`, `static/js/recorder.js`, `static/js/analysis_trajectory.js`** *(update)*
   - Render a grouped **Pronunciation Weakness Summary** in `#feedback-container` (6 category cards + flagged words).
   - Clicking a flagged word seeks the Analysis audio/SVG trajectory scrubber to `[start_time, end_time]`, displays the articulatory comparison (`POST /api/select-error`), and offers a one-click jump to **Comparison Lab** prefilled with that word or contrast pair.

---

## 5. Desktop Packaging, Offline Policy & Validation

### 5.1 Staged Assets (`external/mhubert-147/`, gitignored)
```text
external/mhubert-147/
  encoder/                  # utter-project/mHuBERT-147 config, preprocessor_config, model.safetensors
  ctc_v1/                   # istomin9192/mHuBERT-147-ipa-head ctc_v1 weights + config.json
  ipa_map.json
  cmudict_ipa.json          # Offline CMUdict ARPAbet/IPA lexicon
  SHA256SUMS
```
- Add pinned download/checksum restore script (`scripts/restore_mhubert.py` or alongside R5 bundle).
- Update [desktop_assets.py](file:///Users/tonypace/Documents/Code/speech-guider/src/services/desktop_assets.py), [model_cache.py](file:///Users/tonypace/Documents/Code/speech-guider/src/services/model_cache.py), [build_desktop_installer.py](file:///Users/tonypace/Documents/Code/speech-guider/scripts/build_desktop_installer.py), [smoke_desktop_backend.py](file:///Users/tonypace/Documents/Code/speech-guider/scripts/smoke_desktop_backend.py), and [installer-assets.md](file:///Users/tonypace/Documents/Code/speech-guider/docs/installer-assets.md) (crediting `utter-project/mHuBERT-147` CC-BY-NC-4.0 and `istomin9192/mHuBERT-147-ipa-head` Apache-2.0).
- **Installer & Memory Budget:** +~375 MiB FP32 (~190 MiB if FP16 weights on Apple Silicon) → `.pkg` ~1.95 GB (or ~1.77 GB FP16); keep model loading lazy on first Analysis so desktop startup readiness stays fast.

### 5.2 Calibration & Release-Contract Gate
Per [release-contracts.md](file:///Users/tonypace/Documents/Code/speech-guider/docs/release-contracts.md), do **not** ship uncalibrated pass/fail clinical claims:
- Validate GOP / confusion-pair thresholds and Praat F1/F2 vowel boundaries on an annotated L2 corpus (e.g., **Speechocean762**) plus real teacher/student recordings of the 5-sentence passage.
- Expose confidence/evidence neutrally (e.g., *"Weak `/θ/` cue — sounded closer to `/s/`"* + clickable playback/SVG inspection) until corpus ROC calibration passes.

---

## 6. Phased Rollout Checklist (New Branch)

- **Phase 0 — Asset & Offline Checksum Prep:** Stage `utter-project/mHuBERT-147` + `ctc_v1` + `cmudict_ipa.json` with `SHA256SUMS`; verify `local_files_only=True` and offline E2E asset policy.
- **Phase 1 — Shared Encoder & CTC Forced Aligner:** Implement `mhubert_encoder.py`, `ipa_ctc_head.py`, `g2p.py`, and Viterbi `ForcedAligner` in `alignment.py`; unit-test alignment boundaries, GOP monotonicity, and synthetic substitutions/deletions.
- **Phase 2 — 6-Category Diagnostics & Prosody Unlock:** Implement `pronunciation_diagnostics.py` (CTC margins + cluster deletions + Praat F1/F2 + R4/R5 gesture cross-check) and wire real `vowel_timestamps` / `word_timestamps` into `app/api/analyze.py`.
- **Phase 3 — Analysis UI & Drill Integration:** Render grouped weakness cards and word-level seek/compare controls in `recorder.js` / `analysis_trajectory.js`; rebuild Tailwind (`npm run assets:build`).
- **Phase 4 — R5 Merge, Calibration & Desktop Build:** Share `mHuBERT-147` inference with R5 decoder, calibrate thresholds on L2 recordings, run `npm run check`, `cargo test`, `npm run test:e2e:mocked`, and rebuild `.app` / `.pkg` with frozen smoke verification.
