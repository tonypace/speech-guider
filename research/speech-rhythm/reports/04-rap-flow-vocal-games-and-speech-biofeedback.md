# Report 4: Rap Flow Notation, Vocal Games, Kinetic Typography & Speech Biofeedback

## 1. Rap Flow & Hip-Hop Vocal Rhythm Notation

### A. Kyle Adams' Beat-Class Matrix / 16th-Note Grid Notation (2008, 2009)
* **16-Slot Cardinality Grid:** Represents each 4/4 bar as a 16-column tabular row (`1 x y z | 2 x y z | 3 x y z | 4 x y z`). Syllables are placed in the cell corresponding to their vowel onset (P-center).
* **Prosodic & Phonetic Highlighting:** Uses **BOLD/CAPS** for dynamically/metrically accented syllables and **color-coded cell backgrounds** (as popularized by Paul Edwards' *How to Rap* and Vox *Earworm* diagrams) for assonance and internal rhyme families. Vertical color alignment reveals regular end-rhymes; diagonal color cascades reveal polymetric cross-rhythms (e.g., 3-slot motifs drifting across a 16-slot bar).

### B. Mitchell Ohriner's Non-Isochronous Flow & Groove Deviation Plots (*Flow*, 2019)
* **Groove Deviation Plots:** Plots phase offset (in milliseconds or fractions of a 16th note, e.g., $-30\text{ ms}$ to $+50\text{ ms}$) across a verse, showing how an MC systematically lags behind the snare ("laid-back pocket") or drifts across a phrase before snapping back on the end-rhyme.
* **Spiral Metric Wheels:** Maps multi-bar flows onto a $360^\circ$ spiral where each 16th-note is a $22.5^\circ$ spoke; angular alignment reveals recurring rhythmic pockets, while angular drift exposes acceleration/deceleration.
* **Accent & Contour Stem Graphs:** Plots vocal $F_0$ (semitones) and Inter-Onset Intervals (IOIs) directly above the lyric matrix to separate *lexical dictionary stress* from *realized acoustic accent*.

### C. Martin Connor's Modified Percussion Staff & "Noctuplets" (2018)
* Uses a 1-line or 5-line staff with irrational tuplets (quintuplets, septuplets, "noctuplets"/9-tuplets), **X-noteheads** or ghost notes `(x)` for unpitched percussive consonants, and oval noteheads for sustained vowels.

---

## 2. Singing, Karaoke & Vocal Rhythm Games

### A. *Rock Band* Vocals & *YARG* (Pitch Tubes vs. "Talkie" Ribbons)
* **Pitched Vocal Tubes:** Scrolling horizontal tubes whose length = vowel duration and Y-height = target $F_0$.
* **"Talkies" (Unpitched / Rap Phrases):** Designated by `#` or `^` in the chart, transforming the thin pitch tube into a **wide, translucent horizontal band** where pitch tracking is disabled and replaced by **rhythmic amplitude envelope detection**.
* **Consonant Onset Splitting:** Charter rules place unvoiced consonant onsets (`s-`, `t-`, `k-`) slightly *before* the note tube start, aligning the tube's leading edge strictly with the **vowel onset (P-center)** so players never feel penalized for consonant lead-in time.

### B. *SingStar*, *Smule*, and *Twitch Sings*
* **SingStar Discrete Syllable Capsules:** Unlike *Rock Band*'s merged talkie ribbons, *SingStar* renders every syllable as a **discrete rounded horizontal capsule** with clear inter-syllable gaps, filling the capsule with color based on onset timing and duration.

---

## 3. Kinetic Typography & Embodied / Dance Notation

### A. Variable-Font / Elastic Prosodic Typography (MIT Media Lab *Prosodic Font*; CMU *Kinetic Typography*; *TypoProsody*)
* Encodes acoustic prosody **directly into the geometry of the text glyphs**, eliminating the split-attention effect between "graph" and "lyrics":
  * **Stress / Intensity (dB) $\rightarrow$ Font Weight (`wght`) & Scale:** Stressed syllables render bold (`wght: 800–900`); unstressed function words shrink into thin, light weights (`wght: 200–300`) with reduced opacity.
  * **Vowel Duration (ms) $\rightarrow$ Horizontal Stretch (`wdth`):** Drawn-out vowels stretch horizontally (`wdth: 150%+`) or elongate proportionally.
  * **Pitch ($F_0$) $\rightarrow$ Baseline Y-Shift:** Syllables shift above or below the baseline to trace intonation contours.
  * **Pauses $\rightarrow$ Proportional Whitespace:** Silence duration maps linearly to horizontal word spacing.

### B. Labanotation & Dalcroze / TaKeTiNa
* **Labanotation:** Continuous vertical staff where **1D block length strictly equals duration**, **polygon shape = spatial direction**, and **interior shading = vertical level/weight** (cross-hatched = high/light, center dot = mid, solid black fill = low/heavy).
* **Dalcroze Eurhythmics:** Uses **anacrusis $\rightarrow$ crusis $\rightarrow$ metacrusis** kinematic arc diagrams (preparation $\rightarrow$ attack $\rightarrow$ rebound) to group weak pickup syllables into stressed targets.

---

## 4. Speech Rhythm & Prosody Biofeedback Software (CAPT / SLP)

* **Syllable Bubble Tracks (*BetterAccent Tutor*, *KayPENTAX Visi-Pitch*, *IBM SpeechViewer*):**
  * Represents each syllable as a 2D circle/capsule where **diameter/area = stress intensity (`O` vs. `o`)**, **horizontal width/spacing = duration & rhythm**, and **Y-position = pitch**. Overlays user speech bubbles onto translucent native target ghost bubbles.
* **P-Center (Perceptual Center) Alignment Diagrams (Morton, Marcus, & Frankish 1976; Scott 1998):**
  * Models each syllable as a **two-part block**:
    1. **Pre-Beat Consonant Onset ("Anacrusis Lead-In"):** A narrow, lighter/hatched block extending *to the left* of the beat line ($50\text{–}120\text{ ms}$ before the beat for clusters like `str-`).
    2. **Beat Anchor + Vowel Nucleus ("Rime/Body"):** A vertical anchor tick at the **P-center** (vowel onset rise) snapped directly to the beat line, followed by a thick solid block for the vowel duration.
