# Goal 2 Report: Real-Time Guided Performance Interfaces ("Rap Flow Game for Speech")

Guiding a student toward native speech timing *while they are speaking* requires solving three psychophysical traps that do not exist in finger-drumming games:

---

## 1. Three Psychophysical Traps in Live Speech Guidance

1. **The Split-Attention & Oculomotor Trap (Reading vs. Tracking):**
   * Natural reading relies on forward saccades with an *eye-voice span* of 250–500ms (~12–15 characters ahead of the voice). Scrolling text horizontally toward a strike line (as in *Rock Band Talkies*) forces the eyes into smooth pursuit to read moving letters while jumping back to the strike line to judge timing, inducing robotic prosody.
2. **Motor Planning & P-Center Lead Time ($C_{\text{onset}}$ vs. $P_{\text{center}}$):**
   * Because the perceived rhythmic beat (**P-center**) sits at the **vowel onset ($V_{\text{onset}}$)**, a speaker must initiate consonant clusters (`/str/`, `/pl/`, `/θr/`) **50 to 120ms *before* the beat**. If the UI aligns the first consonant letter with the beat line, the student starts `/s/` on the beat and their vowel arrives 100ms late.
3. **The Delayed Visual Feedback (DVF) "Stutter Trap":**
   * Displaying high-salience judgmental alerts (*"LATE!"*, *"MISS!"*, flashing red text) mid-sentence triggers a cognitive interrupt loop (analogous to Delayed Auditory Feedback stuttering), causing the speaker to freeze on the next syllable.

---

## 2. Core Real-Time Guidance Mechanics ("Rap Flow Engine")

### A. The 2-Bar "Call-and-Response" Entrainment Loop (*Rhythm Doctor* / *Patapon* / Shadowing)
* **Continuous Backing Pocket:** A lo-fi hip-hop, boom-bap, or shuffle drum loop (Kick on 1 & 3, Snare on 2 & 4, subtle 16th-note shaker) plays continuously with a subtle beat-pillar pulse.
* **Beats 1–4 (Bar 1 — Model "Call"):** The native reference voices the phrase in the pocket while the playhead sweeps across the stationary Flow Matrix, followed by a **Beat 4 Breath/Pickup Cue** that primes inhalation and articulatory readiness.
* **Beats 5–8 (Bar 2 — Student "Response"):** Without stopping the drum groove, the playhead sweeps across the exact same phrase layout as the student speaks directly into the pre-entrained pocket.

### B. Stationary 16-Slot Flow Matrix + Dual-Layer Kinematic Playhead
* **Stationary Multi-Word Layout:** Lock the phrase statically across the 4-Beat / 16-Slot matrix (`1 e & a | 2 e & a | 3 e & a | 4 e & a`) so the learner's eyes can use natural look-ahead saccades while peripheral vision tracks the sweeping playhead.
* **Variable-Gravity Bouncing Ball + Horizontal Capsule Wipe:**
  * **High, slow parabolic arc** over long intervals signals a major upcoming **stressed beat anchor** and gives visual countdown to initiate consonant clusters early.
  * **Low, rapid micro-skips** over unstressed function words (`to the`, `of a`) visually cue rapid schwa compression before landing heavily on the next stressed Beat Pillar.

### C. Anacrusis Ramps, Ghost Beads & P-Center Split-Capsules
* **Stressed Beat Capsules:** Tall, high-contrast capsules (`font-weight: 800`, 1.5x scale) snapped onto main Beat Pillars, with width spanning multiple 16th-note slots proportional to vowel duration.
* **Unstressed Ghost Beads on an Anacrusis Ramp:** Compact, 55%-opacity beads tucked into `e`, `&`, or `a` slots that **step upward in Y-elevation** toward the upcoming Beat Pillar, training the speaker to treat function words as a fast launchpad into the stressed vowel.
* **Pre-Beat Consonant Tail + P-Center Bullseye:** Inside every stressed capsule, initial consonant clusters (`str-` in `STR-ONG`) extend **to the left of the Beat Pillar line** in a translucent lead-in tail, while the **Vowel Nucleus (`-ONG`)** starts squarely on the vertical Beat Pillar line with a **P-Center Bullseye (`♦`)**.

### D. Bifurcated Biofeedback: Affirmative Live Glow vs. Post-Phrase Diagnostics
* **While Speaking (Beats 5–8):** Zero error text or red flashes. Voice energy fills capsules with warm luminescence; landing a vowel onset within $\pm 45\text{ ms}$ of a Beat Pillar triggers a satisfying **concentric P-center ripple ring** ($<20\text{ ms}$ client-side DSP).
* **After Beat 8 (Review Pause):** Automatically transitions into the **Goal 1 Post-Utterance Diagnostic Overlay**, revealing exact P-center offsets, bloated ghost beads, or clipped vowel tails.
