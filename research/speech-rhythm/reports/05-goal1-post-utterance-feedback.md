# Goal 1 Report: Post-Utterance Feedback Displays for Poorly Timed Speech

When a learner finishes recording an utterance (e.g., *"I'm going to the STRONGhold... to WAIT"*), a naive millisecond-by-millisecond timeline overlay (like a strict DAW grid) fails: if the learner speaks 15% slower overall or takes an extra 250ms breath between clauses, every subsequent syllable appears shifted right ("late"), even if their internal stress-foot ratios were native-like.

---

## 1. Decoupling Global Tempo from Local Rhythm

| Tool / Paradigm | Alignment Engine | How It Separates Global Tempo from Local Rhythm | Visual Representation |
| :--- | :--- | :--- | :--- |
| **Synchro Arts VocAlign / ReVoice Pro 5** | **APT (Audio Process Technology)** + Energy/Transient envelopes + Protected Regions | Segments utterance into phrase blocks separated by silence/pauses. Normalizes overall block length first, then computes a non-linear time-warp path between Guide (outline) and Dub (solid fill) transients. | Dual/overlaid waveform envelopes connected by **angled Warp Lines** (vertical = aligned after tempo normalization; steep angle = local rush/drag). |
| **DTW in CAPT (*BetterAccent Tutor*, *SpeechAce*)** | **Piecewise / Constrained DTW** on forced-aligned syllable nuclei | Computes the global regression slope $\bar{m} = T_{\text{student}} / T_{\text{native}}$ of the DTW warping path inside each intonational phrase (IP). **Global tempo drift** is the linear trendline $\bar{m}$; **local rhythmic error** is the residual deviation $e_i = w(t_i) - \bar{m} \cdot t_i$. | Stretches/rescales the X-axis of each phrase to match the reference width before overlaying pitch/intensity contours. |
| **Logic Pro *Smart Tempo* ("Adapt" Mode)** | Variable Beat Mapping on P-center / transient anchors | Warps the **grid lines** to hit the speaker's stressed downbeats (Stress Feet), then inspects where subdivisions (unstressed syllables) fall inside each elastic measure. | Elastic beat markers where every Stress Foot is normalized to 1 visual "bar" width regardless of millisecond duration. |
| **Melodics** | Relative Hit-Window Bins around local beat anchors | Evaluates hits within a tolerance window ($\pm \text{ms}$ or $\%$ of beat) relative to the active beat phase, color-coding deviations (**Green** = in-pocket, **Orange** = early, **Purple** = late). | Solid capsule bars offset left/right against translucent target grid slots. |

### Recommended Two-Stage Alignment Pipeline
1. **Pause-Clause Chunking & Tempo Normalization (Global):** Split the utterance at silent pauses ($>150\text{ ms}$) into Intonational Phrases (IPs). Scale each learner IP's time axis by $\alpha_{\text{IP}} = \text{Duration}_{\text{Native IP}} / \text{Duration}_{\text{Learner IP}}$ and display a separate badge (*"Speaking Rate: 0.85x — Evaluated relative to your speed"*).
2. **Stress-Foot Anchor Locking (Local):** Lock primary stressed vowel onsets (P-centers) via Forced Alignment + DTW so that local errors inside a stress foot do not cascade into the next foot.

---

## 2. The 4 Core L2 Speech Timing Errors & Visual Diagnostics

1. **Failure to Reduce ("Machine-Gun / Syllable-Timed" Error):**
   * *Cause:* Pronouncing unstressed function words (*"to the"*, *"of a"*, *"gonna"*) with full vowels and equal duration instead of compressing them into 40–70ms schwa "ghost notes."
   * *Visual Cue ("Bloated Ghost Notes"):* Target unstressed syllables are rendered as tiny, translucent hollow pills (`o`). When over-pronounced, the learner's capsule inflates into a **fat Amber/Red block** with outward-pushing expansion arrows (`|<-->|`), showing how bloated function words shoved the next stressed beat late.
2. **P-Center / Consonant-Cluster Lag:**
   * *Cause:* Starting initial consonant clusters (`/s-t-r/` in *"strong"*) *on* the beat instead of anticipating them 60–120ms *before* the beat so the **vowel onset (P-center)** lands on the downbeat.
   * *Visual Cue ("Lead-In Runway + Vowel Pin"):* Split every syllable capsule into a **hatched Consonant Lead-In Ramp (`///`)** and a **solid Vowel Core (`███`)** separated by a **P-Center Beat Pin (`♦`)**. Show the beat line passing through `♦`.
3. **Missing Phrase-Final Lengthening & Micro-Pauses:**
   * *Cause:* Rushing through thought-group boundaries or pausing mid-foot.
   * *Visual Cue ("Trailing Taper Tail & Breath Gate"):* Phrase-final syllables have a gradient deceleration tail (`███▓▓▒▒░░`) followed by a Breath Gate (`||`). Rushing clips the tail with a red edge (`███|⚡`); mid-foot hesitation tears the foot bar (`//⚡//`).
4. **Incorrect Stress-Foot / Syncopation Ratio:**
   * *Cause:* Reversing or flattening internal foot proportions (e.g., turning a $3:1:1$ dactyl into $1:1:1$).
   * *Visual Cue:* Canonical ratio badge (`3 : 1 : 1`) paired with a tilted ratio balance bar.

---

## 3. Three Complementary Visual Diff Metaphors

### Metaphor 1: Elastic Tether / Warp-Line Diff (VocAlign / DTW Style)
* **Layout:** Stacked **Native Reference** (top) and **Tempo-Normalized Learner** (bottom) tracks connected across an 80px **Alignment Tether Gutter**.
* **Visual Encoding:**
  * **Vertical Green Tether (`|`):** Locked in the rhythmic pocket ($\pm 15\text{ ms}$).
  * **Tilted Right Purple Tether (`\`):** Learner late (dragged or pushed by bloated preceding schwas).
  * **Tilted Left Orange Tether (`/`):** Learner early (rushed or clipped vowel).
  * **Trapezoid Ribbon Funnel:** Funneling wider downward (`/  \`) = bloated syllable duration; funneling narrower (`\  /`) = clipped vowel duration.

### Metaphor 2: Ghost-Target Overlay (Melodics / Prosogram Hybrid)
* **Layout:** Single unified timeline where Native targets are **translucent dashed Ghost Capsules** inside shaded **Beat Bins**, and Learner syllables render directly on top as solid pills.
* **Overhang Diffs:** Any portion of the learner's solid pill spilling outside the Ghost Capsule glows as an **Overhang Error** (Red/Amber spill on unreduced schwas; empty dashed gap on clipped stressed vowels).

### Metaphor 3: Proportional Foot Strip / Accordion Diff (Polak Subdivision Strips)
* **Layout:** Normalizes every **Stress Foot** (from one stressed P-center to the next) to **100% of an equal-width box**, completely removing global tempo and pause distractions.
* **Mechanics:** Compares the Native Foot Split (`STRONG 68% | to 14% | the 18%`) directly above the Learner Foot Split (`STRONG 40% | to 30% | the 30%`), immediately proving to the learner that *"to the"* consumed 60% of the beat's time budget instead of 32%.
