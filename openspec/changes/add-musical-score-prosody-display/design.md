## Context

The existing Prosody Lab visualization renders pitch as a scatter trace with a color-mapped confidence overlay. This is hard to read and does not support the "sing along" use case. The redesign treats each recording as a musical score: pitch becomes a note lane, stressed syllables anchor the beat, and unstressed syllables compress into grace-note clusters.

## Goals / Non-Goals

**Goals:**
- Create a readable musical score visualization from pitch and syllable data.
- Support two display modes: truth (real timing) and locked (quantized to bar grid).
- Make pitch points visually distinct: dark, large, directly on note lines.
- Add zoom to change effective bar density.
- Support teacher/student comparison in the new layout.

**Non-Goals:**
- No backend changes — the analysis pipeline is unchanged.
- No MIDI playback or audio export.
- No automatic pitch correction.

## Decisions

### Two-mode display: Truth and Locked

**Truth mode** (default):
- All timing is real and unaltered.
- Pitch shown as continuous note envelope (dark line, large dots on note lines).
- Stressed syllables anchor real-time positions.
- Unstressed syllables shown as small grace-note markers between stressed anchors.

**Locked mode**:
- User toggles "Lock to the beat".
- Syllable timings are quantized to a bar grid.
- Beats per bar auto-detected from speech rate (default 4, override to 8).
- Makes the display usable as a practice score.

### Zoom changes bar density

Zooming in/out changes how much time each row represents. Short recordings show one short row. Longer recordings stack vertically. The user can zoom to make bars shorter or longer.

### Grace-note compression for unstressed syllables

Unstressed syllables are drawn as small markers packed between the stressed anchors. They do not have their own horizontal space — they cluster vertically between the anchor beats. This keeps the display clean while preserving the information.

### Dark, large pitch markers

Each pitch point is drawn as a dark marker (`#0f0f0f`, size 8–10) sitting directly on the note line it quantizes to. No color scale. No fuzzy overlay. The note name is shown as a y-axis tick. This makes the data immediately readable.

### Backend unchanged

The existing pitch_track (from librosa.pyin), syllable_onsets, and summary data are reused directly. No new analysis endpoints are needed.

## Risks / Trade-offs

- [Quantization clarity] Lock-to-beat quantization can distort perceived rhythm if speech rate is irregular → Show both modes so users can compare.
- [Grace-note crowding] Very rapid unstressed syllables could crowd the display → Limit grace-note markers to at most 3 per inter-anchor region.
- [Zoom UX] Per-row zoom might feel unfamiliar → Default zoom set to a comfortable bar density (≈2s per bar at 4 beats/basic speech rate).
- [Beat detection] Auto beat-per-bar detection depends on syllable count and duration → Fall back to 4 beats/basic if detection is ambiguous.
