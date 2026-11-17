# Report 1: Rhythm Games, Commercial Drum Trainers & Non-Linear UIs

## 1. Highway / Scrolling Note Displays
*(Rock Band Pro Drums, Clone Hero, Phase Shift, DrumMania/GITADORA, Paradiddle VR, Beatstar)*

Highway displays project time onto a 1D spatial axis (vertical top-to-bottom or perspective Z-axis toward a strikeline) and map discrete sound sources/limbs onto parallel lanes.

### Specific Visual Mechanics
* **Elastic Beat Lines & Tempo-Mapped Grids:** Horizontal lines traverse the highway at quarter-note (thin/faint line) and measure/downbeat (thick/bright line) intervals. In *Rock Band*, *Clone Hero*, and *DrumMania*, these lines dynamically stretch or compress when a song's tempo map (BPM) fluctuates—allowing live, unquantized human recordings (e.g., funk, classic rock, or jazz tracks) to keep notes aligned with visual beat lines by warping the underlying tempo map frame-by-frame.
* **Ghost Notes & Dynamic Accents (Velocity Encoding):**
  * **Clone Hero (Pro Drums) & YARG:** Introduced native MIDI velocity scoring and visual encoding. **Ghost notes** (low-velocity snare/hi-hat strokes) render as **physically smaller, desaturated, or hollowed-out/translucent gems** (~50–60% scale of a normal note). **Accents** (high-velocity rimshots/crashes) render as **oversized gems with high-contrast white outer halos, spikes, or glowing cores**.
  * **Phase Shift & Rock Band 3:** Used subtle inner-gem shading or distinct cymbal/tom shapes (rings/wedges for cymbals vs. rectangular bricks for pads).
  * **Beatstar:** Encodes swipe direction and hold durations directly onto the note surface using arrows and tapered tails with tick marks.
* **Tuplets, Swing, and Shuffle Grids:**
  * Highway engines rarely draw triplet/quintuplet grid lines (which create visual clutter). Instead, they keep **quarter-note beat lines visible** and position notes at their exact fractional temporal offset ($y = v_{\text{scroll}} \cdot \Delta t$).
  * For **swing/shuffle** (e.g., 60%–66% swing ratio or Latin cascara/songo patterns), the visual signature is **spatial pairing**: two notes travel down the highway as an asymmetric "couple" (a wide gap followed by a tight gap just before the beat line). Experienced players read **gestalt spatial clusters** (e.g., a 3-note gallop or a drag/ruff grace-note pair) rather than counting grid subdivisions.
* **Paradiddle VR (3D Spatial Highways):**
  * Projects curved note ribbons directly onto the 3D spatial coordinates of each virtual drum/cymbal, or uses shrinking "note rings" directly on the drumhead surface, eliminating cognitive translation between 2D lane color and 3D physical target.

### Pros & Cons for Unquantized / Expressive Rhythms
* **Pros:** Strong lookahead (1–2 seconds) for motor planning; continuous spatial axis requires no quantization to render millisecond offsets.
* **Cons:** **Scroll Speed vs. Density Paradox** (slow scroll clumps ghost notes and flams into an unreadable blob; fast scroll destroys macro-phrase lookahead); constant scroll speed implies false isochrony during rubato or speech-like pauses.

---

## 2. Commercial Drum Learning Software
*(Melodics, Roland V-Drums Coach / DT-1, Drumeo / Soundslice, Yousician, Freedrum)*

### Specific Visual Mechanics
* **Melodics (Horizontal Step-Grid + Micro-Timing Telemetry):**
  * **Layout:** Horizontal left-to-right scrolling timeline divided into color-coded horizontal lanes (Kick = bottom, Snare = middle, Hi-hat/Ride = top).
  * **Grid vs. Groove Representation:** Background vertical lines mark main beats (1, 2, 3, 4) with fainter dashed subdivision lines. In **hip-hop (J Dilla / boom-bap) or swung lessons**, target notes are visibly offset slightly to the right ("laid-back" / behind the beat) or left ("pushed") of the faint grid line.
  * **Ghost Note & Velocity Sizing:** Ghost notes render as **half-height or smaller rounded squares/diamonds** within the same lane as full-height accented blocks.
  * **Post-Hit Micro-Timing Imprint:** When the user strikes a pad, Melodics leaves a **persistent colored marker/imprint** at the exact millisecond the user hit, paired with an Early/Late deviation bar. Learners see their systematic bias (e.g., rushing ghost notes while dragging the backbeat) across the whole phrase.
* **Roland V-Drums Coach Mode & DT-1 (Time Check & Quiet Count):**
  * **Time Check Gauge:** A zero-centered horizontal deviation meter (like a strobe tuner) showing whether hits land early (left) or late (right) of the beat center.
  * **Quiet Count:** Drops the audio click for $N$ bars while keeping a minimal visual phase indicator, training the internal oscillator rather than visual reflex.
* **Drumeo / Soundslice / Yousician (Synchronized Hybrid Notation):**
  * Pairs standard percussion notation with a continuous playhead cursor and optional **time-proportional spacing** ($w \propto \Delta t$) alongside synchronized video/audio wave loops.

---

## 3. Unconventional & Non-Linear Rhythm Games
*(A Dance of Fire and Ice [ADOFAI], Rhythm Doctor, Osu!, Taiko no Tatsujin, Patapon, Hi-Fi Rush, Thumper)*

### Specific Visual Mechanics
* **A Dance of Fire and Ice (ADOFAI) — Geometric Angle = Temporal Interval:**
  * Two planets orbit each other at constant angular velocity ($\omega$) along a winding path of tiles. Because angular speed is constant, **the geometric angle ($\theta$) between consecutive tiles directly encodes the inter-onset interval (IOI)**:
    * $180^\circ$ straight line = 1 beat (isochronous pulse).
    * $90^\circ$ right-angle turn = $1/2$ beat.
    * $60^\circ$ triangle turn = $1/3$ beat (triplet).
    * **Swing / Micro-timed grooves:** Alternating obtuse and acute angles (e.g., $240^\circ / 120^\circ$ for 2:1 swing, or $195^\circ / 165^\circ$ for laid-back hip-hop swing).
  * Converts 1D time intervals into recognizable **2D geometric silhouettes** (staircases, hairpins, spirals).
* **Rhythm Doctor — Call-and-Response Pulse & Kinematic Wind-Ups:**
  * One-button rhythm game centered on an ECG/heartbeat monitor line. Uses **audiovisual call-and-response telegraphs** and character animations that provide a **continuous kinematic wind-up arc** before syncopated or skipped beats, allowing players to judge a continuous motion trajectory rather than sight-reading dense grids.
* **Osu! — Radial Approach Circles, 2D Distance Mapping, and Sliders:**
  * **Approach Circles:** Outer ring shrinks linearly toward the note border, decoupling *when* to hit (radial contraction) from *where* to hit (2D coordinates).
  * **2D Spatial Jump Distance $\propto \Delta t$:** Short intervals are clustered tightly; longer pauses require wide spatial jumps.
  * **Sliders:** Curved ribbons with a rolling ball that visually encode **sustained syllable/note duration and velocity contour**.
* **Taiko no Tatsujin — 1D Conveyor with Dual-Size/Color Weight:**
  * Single horizontal track where timbre is binary (Red *Don* = core/low, Blue *Ka* = rim/high) and **stress/weight is encoded by diameter** ($1.6\times$ larger circles for accented beats).
* **Patapon & Hi-Fi Rush — Lexical Chunking & Environmental Shockwaves:**
  * *Patapon* pulses the screen border on the macro-beat and groups inputs into 4-beat **lexical words** (*PATA-PATA-PATA-PON*), reinforcing rhythm as chunked prosodic phrases.
