# Report 3: Academic Literature, Ethnomusicology, Paper Notation & Geometric Topologies

## 1. Paper & Pedagogical Rhythm Notation Systems

### A. Time Unit Box System (TUBS)
* **Origins:** Philip Harland (1962) and James Koetting (1970, *"Analysis and Notation of West African Drum Ensemble Music"*).
* **Mechanics:** Time is sliced into equal horizontal atomic boxes representing the fastest functional pulse (*tatum*, Bilmes 1993). Each row represents a distinct instrument or stroke timbre; symbols inside boxes (`•`, `x`, `o`) denote onset and articulation, while empty boxes denote continuation/silence.
* **Strengths:** Eliminates Western bar-line metric bias, allowing interlocking polyrhythms, cross-rhythms, and asymmetric timelines (West African bell patterns, Afro-Cuban *clave*) to be read vertically as phase alignments.

### B. Visual-Verbal Pedagogical Mappings (Konnakol, Takadimi, Kodály)
* **Konnakol / Solkattu (Carnatic Tradition):** Maps complex subdivisions (3, 4, 5, 7, 9) onto percussive vocal syllables (*ta, ka, di, mi, thom*) where consonant/vowel phonetics naturally encode attack weight and sustain. Written with horizontal under-brackets (`____`) for subdivision compression and `,` / `;` for unit rests (*aksharakala*).
* **Takadimi (Hoffman, Pelto, & White, 1996):** **Phase-locked to the beat** rather than duration-locked. Simple meter: `ta-ka-di-mi`; compound meter: `ta-ki-da`. Teaches learners to feel syncopation and polyrhythm (e.g., 3:4 shares `ta` on the downbeat) by naming the exact **phase angle** within the beat cycle.

### C. Joseph Schillinger's Ribbon / Interference Graphs (1941)
* **Mechanics:** Replaced noteheads with **proportional square-wave ribbons** on Cartesian graph paper (X-axis = exact duration, Y-axis = pitch/layer).
* **Interference of Periodicities:** Plots two pulse streams ($a$ and $b$, e.g., $4:3$) as parallel square-wave ribbons and projects their union onto a composite **Resultant Rhythm ribbon ($r_{a \div b}$)**, turning polyrhythmic interference into a single visual duration block sequence (`3, 1, 2, 2, 1, 3`).

### D. Proportional & Graphic Notation (Earle Brown, Stockhausen)
* **Earle Brown (*December 1952*, *Four Systems*):** Replaced noteheads/stems with **solid horizontal rectangles** whose horizontal length = exact duration and vertical thickness = dynamic intensity/weight—directly prefiguring modern computational speech Prosograms.
* **Stockhausen & Boulez (Feathered Beams):** Fan-shaped converging or diverging secondary beams that visually depict continuous micro-accelerations and decelerations (*tempo-slopes*) within a single rhythmic gesture.

---

## 2. Ethnomusicological & Groove Micro-Timing Visualizations

### A. Anne Danielsen's "Beat Bin" Theory (2006, 2010, 2019, 2023)
* **Core Concept:** In funk, neo-soul, and hip-hop (e.g., James Brown, D'Angelo, J Dilla), the internal metric reference is not a zero-duration mathematical point ($t_0$), but a **Beat Bin**—a temporal window or "tolerance zone" of finite width (30–80+ ms) with a probability density profile. Multiple staggered onsets (early hi-hat, laid-back kick, delayed snare) cohabit the same perceptual beat bin to create rhythmic friction without breaking the groove.
* **Acoustic Coupling (P-Centers):** Danielsen (2019) proved that **Perceptual Centers (P-centers)** govern beat bin width: sounds with slow attack rise times or low frequencies have delayed P-centers and wider beat bins.
* **Visualizations:** Shaded **trapezoids or Gaussian bell-curve bands** over horizontal timelines replacing rigid vertical grid lines, paired with multi-track violin/scatter plots of millisecond deviations ($\Delta t$).

### B. Vijay Iyer: Embodied Speech-Like Groove Microtiming (1998, 2002)
* Categorizes rhythm into three embodied biological timescales: **Tactile-Motor Pulse ($1\text{–}3\text{ Hz}$)**, **Speech-Prosody / Oral-Gestural Subdivision ($3\text{–}10\text{ Hz}$, syllable rate)**, and **Fine Microtiming ($10\text{–}100\text{ Hz}$, $10\text{–}100\text{ ms}$, consonant-vowel VOT scale)**. Demonstrates that $10\text{–}50\text{ ms}$ groove deviations in African-American and West African musics are direct musical isomorphisms of **speech prosody**.

### C. Rainer Polak, Richard Jankowsky & Fernando Benadon: Non-Isochronous Subdivisions & Tempo-Slopes
* **Polak (2010, 2014):** Shows that Malian *jembe* ternary subdivisions are neither equal ($33:33:33$) nor 2:1 swing, but stable **non-isochronous ratios** such as **Short-Medium-Long ($22\% : 35\% : 43\%$)**. Visualized via **Normalized Subdivision Ratio Boxplots/Strip Charts** (0%–100% of beat period).
* **Jankowsky (2013, 2021):** **Aligned Tempo-Slope vs. Subdivision Ratio Plots** tracking how non-isochronous subdivision ratios morph as ritual music accelerates by 50%–150%.
* **Benadon (2006, 2007, 2009):**
  * **BUR (Beat-Upbeat Ratio) Contour Graphs:** Plots local swing ratio note-by-note across a phrase, showing swing as a dynamic expressive contour ($1.0\text{ to }2.5+$) rather than a fixed constant.
  * **Concentric Circular/Spiral Plots:** Concentric rings represent successive bars; systematic microtiming appears as **tilted or spiraling spokes** across the rings.

---

## 3. Geometric & Mathematical Rhythm Topologies

* **Godfried Toussaint (*The Geometry of Musical Rhythm*, 2013):**
  * **Necklace & Inscribed Polygon Notation:** Connects $k$ active onsets among $N$ circle nodes into convex polygons; clave variations are geometric rotations, and Euclidean rhythms $E(k, n)$ maximize pairwise chordal distances.
* **Lerdahl & Jackendoff (GTTM, 1983):**
  * **Hierarchical Metrical Dot Grids** (dot column height = metrical prominence) paired with **Grouping Slurs** (allowing out-of-phase anacrusis grouping vs. downbeat meter) and **Time-Span Reduction (TSR) Trees**.
* **Desain & Honing (2003) — The Chronotopological Simplex:**
  * Maps any 3-interval rhythm ($I_1 + I_2 + I_3 = 1$) into a **2D equilateral barycentric triangle**, plotting human perceptual categorization as **topographical attractor basins ("islands")** around 1:1:1 (center), 2:1:1, 1:2:1, and 1:1:2.

---

## 4. Speech Prosody & Rhythm Visuals in Linguistics & CAPT

* **Piet Mertens' *Prosogram* (2004):**
  * Segments only the **sonorant syllabic nucleus (vowel core)** and applies the human auditory **glissando threshold** ($G = 0.16 / T^2\text{ ST/s}$). Pitch changes below threshold render as **flat, thick horizontal black bars** (length = vowel duration, Y-height = perceived ST pitch, thickness = loudness); changes above threshold render as **slanted ramps**.
* **Rhythmic "Morse Code" Capsules (Lloyd James 1940; Gilbert *Clear Speech*):**
  * Visualizes stress-timed speech as alternating **large dashes/capsules (`●` / `▬▬▬`)** for stressed syllables and **tiny dots (`•`)** for reduced schwa syllables, diagnosing L2 syllable-timed flattening at a glance.
* **Pairwise Variability Index (PVI — Grabe & Low 2002; Patel & Daniele 2003):**
  * Quantifies sequential durational contrast between adjacent syllables ($nPVI\text{-}V$ and $rPVI\text{-}C$), plotted either as **2D Rhythm Topology Scatter Plots** or **Local Sawtooth Step Profiles** across an utterance.
