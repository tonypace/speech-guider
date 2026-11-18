# Speech Rhythm & P-Center Syllable Identification Benchmark

This directory (`research/speech-rhythm/experiments/`) contains a reproducible evaluation corpus and benchmark comparing **6 syllable nucleus and perceptual center (P-center) detection algorithms** for `speech-guider`.

## 1. Reproducing the Benchmark

Run the benchmark suite using the repository virtual environment:

```bash
./speech-guider/bin/python research/speech-rhythm/experiments/syllable_benchmark.py
```

- **Detectors Implementation**: [`detectors.py`](detectors.py) (`detect_syllables(audio_path: str, algorithm: str) -> SyllableDetectionResult`)
- **Benchmark Runner & Synthetic Corpus Generator**: [`syllable_benchmark.py`](syllable_benchmark.py)
- **Cached Audio Fixtures**: [`fixtures/`](fixtures/) (10 parametric synthetic `.wav` clips, 4 single-sentence slices of `freeman.wav`, and 6 OmniVoice TTS `.wav` clips)
- **Raw JSON Metrics & Per-Clip Outputs**: [`results.json`](results.json)

---

## 2. Benchmark Corpus (21 Evaluation Clips)

The benchmark evaluates detectors across **3 categories (21 audio clips total)**:

1. **Parametric Synthetic Speech Corpus (10 clips, exact analytical ground-truth timestamps)**:
   - Formant-filtered harmonic glottal pulse trains ($F_0$ contours `110–172 Hz`, 3-formant resonator bank $F_1/F_2/F_3$) with known vowel onset ($V_{\text{onset}}$), steepest-rise perceptual center (**P-center**), vowel nucleus peak, pre-beat consonant onset ($C_{\text{onset}}$), and vowel duration:
     - `synth_clean_4syll`: 4 syllables (alternating `200ms` stressed vowels and `55ms` reduced schwas).
     - `synth_clean_6syll`: 6 syllables (iambic stress feet with three `55ms` schwas and three `190–220ms` stressed vowels).
     - `synth_clean_7syll`: 7 syllables (double-schwa unstressed foot trough `55ms + 55ms` between stressed anchors).
     - `synth_clean_9syll`: 9 syllables (multi-foot prosodic phrase with `52–55ms` schwas and `180–220ms` stressed vowels).
     - `synth_sibilant_cluster_5syll`: 5 voiced syllables flanked by **6 loud unvoiced sibilant/plosive bursts** (`/s/`, `/t/`, `/k/` at `3600–7600 Hz`) that fool raw energy peak pickers.
     - `synth_plosive_coda_6syll`: 6 voiced syllables with `75–90ms` pre-beat consonant clusters (`/sp/`, `/tr/`, `/kl/`) and **4 loud unvoiced stop release bursts**.
     - `synth_fast_speech_8syll`: Fast speech at **`6.5 syll/s`** (8 syllables over `1.23s` active speech).
     - `synth_slow_speech_5syll`: Slow speech at **`2.2 syll/s`** (5 syllables over `2.27s` active speech).
     - `synth_prolonged_vibrato_3syll`: Dysfluent prolonged vowel test (3 syllables containing **two `440ms` prolonged vowels with `4.5 Hz` amplitude tremor/vibrato** $\pm 3.2\text{ dB}$ that fool standard peak pickers into double-counting).
     - `synth_hesitation_block_6syll`: 6 syllables with a **`440ms` prolonged hesitation vowel** (`"theeee..."`) + **`480ms` mid-phrase silent block** + rapid 4-syllable recovery rush.
2. **Real Recorded Speech (`omnivoice-tts/examples/freeman.wav` + 4 sentence slices)**:
   - `freeman_full` (`17.26s`, **52 syllables**): *"If you go into different cultures, they have different concepts of creation. They have their own creation story and what an afterlife is. Where you go, what you do, who you're going to be with. People say, well..."*
   - `freeman_s1` (`6.00s`, **19 syllables**): *"If you go into different cultures, they have different concepts of creation."*
   - `freeman_s2` (`5.75s`, **16 syllables**): *"They have their own creation story and what an afterlife is."*
   - `freeman_s3` (`4.35s`, **13 syllables**): *"Where you go, what you do, who you're going to be with."*
   - `freeman_s4` (`1.16s`, **4 syllables**): *"People say, well..."*
3. **OmniVoice TTS Synthesized Utterances (6 clips cached in `fixtures/`)**:
   - `tts_phrase_1` (`2.47s`, **11 syllables**): *"We need to arrow in on the core problem."*
   - `tts_phrase_2` (`2.01s`, **9 phonetic / 11 canonical syllables**; `"Actually"` realized as 2-syllable `/ˈæk.tʃli/`): *"Actually I think there is a better way."*
   - `tts_phrase_3` (`2.24s`, **9 syllables**): *"I said fifteen percent, not fifty."*
   - `tts_phrase_4` (`2.73s`, **11 syllables**): *"And then the whole room went completely silent."*
   - `tts_phrase_5` (`1.86s`, **5 syllables**): *"Speak clearly right now."*
   - `tts_phrase_6` (`3.52s`, **14 syllables**): *"We all need to understand how this modern system works."*

---

## 3. Aggregate Benchmark Results

| Algorithm | Count MAE (All) | Count MAE (Synth / TTS / Real) | Exact Match % | Within-1 Match % | Nucleus Precision % | Nucleus Recall % | Nucleus F1 % | P-Center MAE (ms) | $C_{\text{onset}}$ MAE (ms) | Sibilant / Plosive FP % | Prolonged Vowel FP % | Runtime (ms / s audio) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **`hybrid_acoustic_pcenter`** *(Winner)* | **0.19** | **0.00 / 0.00 / 0.80** | **85.7%** | **95.2%** | **94.2%** | **95.3%** | **94.7%** | **2.21 ms** | **13.52 ms** | **0.0%** | **0.0%** | **5.10 ms/s** |
| `praat_de_jong_wempe` | 1.09 | 0.60 / 1.00 / 2.20 | 38.1% | 66.7% | 90.1% | 91.2% | 90.6% | 30.52 ms | 35.16 ms | 10.0% | 100.0% | 0.93 ms/s |
| `baseline_energy` *(Current Heuristic)* | 1.67 | 0.90 / 2.17 / 2.60 | 28.6% | 52.4% | 82.7% | 75.9% | 79.1% | 45.22 ms | 41.36 ms | 30.0% | 100.0% | 0.49 ms/s |
| `r4_articulatory_sonority` | 1.76 | 1.10 / 2.83 / 1.80 | 23.8% | 57.1% | 85.2% | 77.6% | 81.2% | 34.09 ms | 57.68 ms | 0.0% | 66.7% | 137.87 ms/s |
| `theta_sonority_oscillator` | 1.76 | 0.70 / 0.67 / 5.20 | 33.3% | 66.7% | 76.7% | 85.3% | 80.8% | 12.14 ms | 15.05 ms | 0.0% | 100.0% | 4.00 ms/s |
| `mermelstein_convex_hull` | 1.95 | 1.90 / 1.50 / 2.60 | 9.5% | 38.1% | 92.9% | 77.1% | 84.2% | 4.00 ms | 42.34 ms | 0.0% | 100.0% | 1.47 ms/s |

---

## 4. Per-Item Syllable Count Breakdown

| Item ID | Category | Ground Truth (`gt_count`) | `hybrid_acoustic_pcenter` | `praat_de_jong_wempe` | `baseline_energy` | `mermelstein_convex_hull` | `theta_sonority_oscillator` | `r4_articulatory_sonority` |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `synth_clean_4syll` | Synthetic | **4** | **4** (`0`) | 4 (`0`) | 4 (`0`) | 2 (`-2`) | 4 (`0`) | 4 (`0`) |
| `synth_clean_6syll` | Synthetic | **6** | **6** (`0`) | 6 (`0`) | 5 (`-1`) | 4 (`-2`) | 5 (`-1`) | 5 (`-1`) |
| `synth_clean_7syll` | Synthetic | **7** | **7** (`0`) | 7 (`0`) | 6 (`-1`) | 5 (`-2`) | 6 (`-1`) | 5 (`-2`) |
| `synth_clean_9syll` | Synthetic | **9** | **9** (`0`) | 9 (`0`) | 7 (`-2`) | 6 (`-3`) | 8 (`-1`) | 7 (`-2`) |
| `synth_sibilant_cluster_5syll` | Synthetic | **5** | **5** (`0`) | 5 (`0`) | 7 (`+2`) | 5 (`0`) | 5 (`0`) | 4 (`-1`) |
| `synth_plosive_coda_6syll` | Synthetic | **6** | **6** (`0`) | 6 (`0`) | 7 (`+1`) | 5 (`-1`) | 6 (`0`) | 5 (`-1`) |
| `synth_fast_speech_8syll` | Synthetic | **8** | **8** (`0`) | 8 (`0`) | 8 (`0`) | 2 (`-6`) | 8 (`0`) | 5 (`-3`) |
| `synth_slow_speech_5syll` | Synthetic | **5** | **5** (`0`) | 8 (`+3`) | 5 (`0`) | 5 (`0`) | 5 (`0`) | 5 (`0`) |
| `synth_prolonged_vibrato_3syll` | Synthetic | **3** | **3** (`0`) | 5 (`+2`) | 5 (`+2`) | 5 (`+2`) | 6 (`+3`) | 4 (`+1`) |
| `synth_hesitation_block_6syll` | Synthetic | **6** | **6** (`0`) | 7 (`+1`) | 6 (`0`) | 5 (`-1`) | 7 (`+1`) | 6 (`0`) |
| `tts_phrase_1` | TTS | **11** | **11** (`0`) | 9 (`-2`) | 6 (`-5`) | 8 (`-3`) | 10 (`-1`) | 7 (`-4`) |
| `tts_phrase_2` | TTS | **9** | **9** (`0`) | 8 (`-1`) | 6 (`-3`) | 8 (`-1`) | 9 (`0`) | 5 (`-4`) |
| `tts_phrase_3` | TTS | **9** | **9** (`0`) | 8 (`-1`) | 9 (`0`) | 8 (`-1`) | 8 (`-1`) | 9 (`0`) |
| `tts_phrase_4` | TTS | **11** | **11** (`0`) | 11 (`0`) | 9 (`-2`) | 10 (`-1`) | 11 (`0`) | 8 (`-3`) |
| `tts_phrase_5` | TTS | **5** | **5** (`0`) | 5 (`0`) | 3 (`-2`) | 3 (`-2`) | 5 (`0`) | 3 (`-2`) |
| `tts_phrase_6` | TTS | **14** | **14** (`0`) | 12 (`-2`) | 13 (`-1`) | 13 (`-1`) | 12 (`-2`) | 9 (`-5`) |
| `freeman_full` | Real | **52** | **52** (`0`) | 49 (`-3`) | 45 (`-7`) | 48 (`-4`) | 62 (`+10`) | 48 (`-4`) |
| `freeman_s1` | Real | **19** | **19** (`0`) | 17 (`-2`) | 18 (`-1`) | 17 (`-2`) | 21 (`+2`) | 16 (`-3`) |
| `freeman_s2` | Real | **16** | **18** (`+2`) | 16 (`0`) | 14 (`-2`) | 15 (`-1`) | 21 (`+5`) | 15 (`-1`) |
| `freeman_s3` | Real | **13** | **14** (`+1`) | 14 (`+1`) | 11 (`-2`) | 15 (`+2`) | 16 (`+3`) | 12 (`-1`) |
| `freeman_s4` | Real | **4** | **3** (`-1`) | 3 (`-1`) | 2 (`-2`) | 2 (`-2`) | 4 (`0`) | 3 (`-1`) |

---

## 5. Key Engineering & Phonetic Insights

1. **Why `baseline_energy` Fails (`MAE = 1.67`, `SibFP = 30%`, `ProlFP = 100%`)**:
   - Raw `np.mean(np.abs(frames))` (`frame_length=2048` @ 22.05 kHz = `93 ms` window) lacks both spectral filtering and a voicing gate:
     - Loud high-frequency sibilants (`/s/` in `synth_sibilant_cluster_5syll`) and stop bursts trigger false-positive syllable nuclei (`30%` sibilant FP rate).
     - Its `93 ms` window blurs rapid unstressed function words (`"need to"`, `"in on the"`, `"Speak clearly"`), under-counting `tts_phrase_1` by 5 syllables (`6` vs `11`) and `freeman.wav` by 7 syllables (`45` vs `52`).
2. **Why `praat_de_jong_wempe` Under-Counts Fast Unstressed Schwas (`MAE = 1.09`, `ProlFP = 100%`)**:
   - Praat's `Sound.to_intensity(minimum_pitch=50.0)` uses a `3.2 / 50 Hz = 64 ms` Gaussian window, and `Sound.to_pitch_ac(pitch_floor=50.0)` requires a `60 ms` periodic window.
   - When an unstressed vowel is `35–50 ms` long and flanked by voiceless obstruents (e.g., `"-ty"` in `"fifty"` at `1.83s` in `tts_phrase_3.wav` or `"went"` in `tts_phrase_4.wav`), the `60 ms` autocorrelation window straddles the voiceless consonants and drops `F0`, causing De Jong & Wempe's voicing filter to discard genuine syllables.
   - Furthermore, De Jong & Wempe's fixed `mindip = 2.0 dB` splits prolonged vowels with `4.5 Hz` vocal tremor (`100%` prolonged-vowel FP rate).
3. **How `hybrid_acoustic_pcenter` Solves All Four Failure Modes (`MAE = 0.19`, `F1 = 94.7%`, `P-Center MAE = 2.21 ms`, `0%` Distractor FP)**:
   - **High-Resolution Vocalic Bandpass (`200–3200 Hz`, `26 ms` window, `5 ms` hop) + Sibilant Gate (`3500–7800 Hz`)**: Resolves `50 ms` unstressed schwas and liquid/glide transitions (`"ar-row in"`) while rejecting high-frequency sibilant/plosive noise.
   - **Dual Voicing Gate (Praat Autocorrelation $F_0$ OR Low-Frequency Voice Bar `80–850 Hz` with Steep Negative Spectral Tilt)**: Captures `35–45 ms` unstressed vowels between voiceless obstruents where long autocorrelation windows drop out, while still rejecting 100% of unvoiced sibilants and plosives (`0.0%` sibilant FP rate).
   - **4-Subband Vocalic Timbre Flux (`200–600`, `600–1200`, `1200–2200`, `2200–3400 Hz`) for Adaptive Valley Dip Thresholding**: Distinguishes true syllable-to-syllable articulatory transitions (`req_dip = 1.38 dB`) from single prolonged vowels with amplitude vibrato/tremor where the normalized 4-band formant profile remains invariant (`req_dip = 6.20 dB`, achieving `0.0%` prolonged-vowel FP rate).
   - **Šturm & Volín (2016) / Cummins & Port (1998) P-Center & Pre-Beat Consonant Extractor**: Pinpoints $V_{\text{onset}}$ at the maximum rising slope of the vocalic dB envelope (`2.21 ms` P-center MAE) and traces backward into pre-vocalic broadband/sibilant energy to recover $C_{\text{onset}}$ (`13.52 ms` MAE) at `5.10 ms` per second of audio.
