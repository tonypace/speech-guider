# Speech Rhythm — Exploratory Research & UI Prototypes

Exploratory domain survey and interactive browser prototypes for visualizing, diagnosing, and coaching complex unquantized speech timing in support of `speech-guider`'s Prosody Lab.

---

## Overview

Speech timing pedagogy requires separating global speaking-rate drift from local prosodic errors (failure to reduce unstressed function words, consonant-cluster P-center lag, clipped phrase-final lengthening, and mid-foot hesitations or stutter repetitions) while avoiding visual traps during live performance. This research explores two complementary coaching goals across four authentic English discourse registers (*Prepared Speech / Presentation*, *Spontaneous Discussion / Turn-Taking*, *Heated Argument / Contrastive Stress*, and *Expressive Storytelling / Narrative*):

- **Goal 1 — Post-Utterance Timing Diagnostics**
  - **VocAlign Elastic Tethers & Danielsen Beat Bins (`vocalign_tether`):** Dual-track Native Reference vs. Dysfluent/Learner alignment connected across a tether gutter with millisecond deviation readouts, jagged mid-foot hesitation tear zones, prolongation funnels, stutter echoes, guillotine clipping markers, and a continuous raw-clock (0%) to DTW foot-normalized (100%) blend control.
  - **Melodics Overhang + Mertens' Prosogram Pitch/Duration Diff (`prosogram_overlay`):** Plots perceived syllable-nucleus pitch (semitones) and glissando slopes against dashed native ghost targets to expose flattened intonation and duration overhangs.
  - **Polak 100% Foot Budget Strips + Desain-Honing Simplex (`foot_budget_strips`):** Normalizes each stress foot from one stressed P-center to the next to 100% width so proportional time-budget theft by unreduced schwas or hesitations is immediately visible alongside nPVI contrast and chronotopological ratio diagnostics.
- **Goal 2 — Real-Time Guided Speech Performance**
  - **Stationary 16-Slot Prosodic Flow Matrix (`flow_matrix`):** A 2-bar Call-and-Response entrainment loop (`1 e & a | 2 e & a | 3 e & a | 4 e & a`) with stationary phrase placement (avoiding smooth-pursuit reading strain), stress-foot pillars, thought-group pause gates (`||`), ascending anacrusis ghost-bead ramps, hatched pre-beat consonant lead-in runways before the `♦` P-center bullseye, and a variable-gravity parabolic bouncing ball.
  - **Taiko + Osu! Single-Line Conveyor (`osu_taiko`):** Single-line F0 pitch conveyor pairing scaled stressed circles (`1.7×`) and hollow ghost beads with radially shrinking P-center approach rings and Osu!-style vowel-hold slider tails.
  - **No-Mic Audition & Simulation Suite:** Includes a Web Audio API prosodic voice & dysfluency synthesizer (`GrooveAudioEngine` in `prototype/js/data_and_audio.js`), five comparison profiles (`dysfluent_hesitation`, `dysfluent_stutter`, `syllable_timed_choppy`, `cluttered_runon`, `native_expressive`), Bar 2 Virtual Speaker Bots (`bot_native`, `bot_dysfluent`, `bot_choppy`), and a Spacebar vowel-duration hold mode (`manual_space`).

---

## Running the Prototype

- **Self-contained standalone bundle** (works directly in any browser or when downloaded from GitHub):
  - Open [prototype/dist/speech-rhythm-standalone.html](./prototype/dist/speech-rhythm-standalone.html)
- **Modular dev server** (for local testing of `prototype/index.html` and `prototype/js/`):
  ```bash
  cd research/speech-rhythm/prototype && python3 -m http.server 8000
  ```
- **Rebuilding the standalone bundle**:
  ```bash
  node research/speech-rhythm/prototype/build_bundle.mjs
  ```

---

## Reports Index

- [00-master-rhythm-display-survey.md](./reports/00-master-rhythm-display-survey.md) — Master survey & comparative synthesis across all domains
- [01-rhythm-games-and-trainers.md](./reports/01-rhythm-games-and-trainers.md) — Rhythm games, commercial drum trainers & non-linear UIs
- [02-daws-groove-and-circular-sequencers.md](./reports/02-daws-groove-and-circular-sequencers.md) — DAWs, groove/micro-timing visualizers & circular/hybrid sequencers
- [03-academic-ethnomusicology-and-paper-notation.md](./reports/03-academic-ethnomusicology-and-paper-notation.md) — Academic literature, ethnomusicology, paper notation & geometric topologies
- [04-rap-flow-vocal-games-and-speech-biofeedback.md](./reports/04-rap-flow-vocal-games-and-speech-biofeedback.md) — Rap flow notation, vocal games, kinetic typography & speech biofeedback
- [05-goal1-post-utterance-feedback.md](./reports/05-goal1-post-utterance-feedback.md) — Goal 1 deep dive: post-utterance feedback displays for poorly timed speech
- [06-goal2-live-guided-rap-flow-interface.md](./reports/06-goal2-live-guided-rap-flow-interface.md) — Goal 2 deep dive: real-time guided performance interfaces ("Rap Flow Game for Speech")

---

## Integration Roadmap for `speech-guider` Prosody Lab

The prototype suite under `research/speech-rhythm/` intentionally runs on curated synthetic timing profiles and Web Audio synthesis outside the production bundle (see [Future plans](../../docs/future_plans.md)). Validated display mechanics can graduate incrementally into [`static/js/prosody_lab.js`](../../static/js/prosody_lab.js) and [`src/audio/prosody_lab.py`](../../src/audio/prosody_lab.py) once the following prerequisites are met:

1. **Real Forced-Alignment & Acoustic Timing Data:** Replace the heuristic energy-peak syllable markers in [`src/audio/prosody_lab.py`](../../src/audio/prosody_lab.py) with forced-aligned phoneme/vowel-nucleus timestamps (from `src/models/alignment.py`) and validated Parselmouth/Praat F0, intensity, and pause measurements so P-centers ($V_{\text{onset}}$), pre-beat consonant lead-ins ($C_{\text{onset}}$), and vocalic/consonantal intervals reflect real learner speech.
2. **DTW Tempo Decoupling Pipeline:** Implement pause-clause chunking and piecewise DTW tempo normalization on real reference/learner pairs so [`static/js/prosody_lab.js`](../../static/js/prosody_lab.js) can separate global rate drift from local foot-timing deviations.
3. **Graduated Visual Mechanics:** Bring proven Goal 1 diagnostics (VocAlign elastic tethers, Danielsen beat-bin tolerance bands, P-center beat anchors, and 100% normalized stress-foot budget strips) into the Prosody Lab measurement timeline, followed by low-latency Goal 2 call-and-response guidance if live rhythmic entrainment is added.
4. **Production Testing & Code Standards:** Refactor graduated UI components into ES modules compliant with ESLint (`npm run lint:js`), offline asset bundling (`npm run assets:check`), unit tests in [`tests/js/`](../../tests/js/) (extending `tests/js/prosodyLab.test.js`), and the full `npm run check` gate.
