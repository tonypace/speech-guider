## 1. Musical score chart builder

- [x] 1.1 Replace `buildPitchChart` with `buildMusicalScoreChart` in `static/js/prosody_lab.js`
- [x] 1.2 Chunk pitch_track into bar-length windows (2s default, zoom-adjustable)
- [x] 1.3 Create one Plotly subplot row per bar with shared x-axis and independent y-axis per row
- [x] 1.4 Quantize pitch points to nearest integer MIDI and draw as dark `#0f0f0f` markers of size 8–10
- [x] 1.5 Render stressed syllable anchors at their real timestamps (truth mode) or grid-snapped positions (locked mode)
- [x] 1.6 Render unstressed syllables as grace-note clusters (size 5–6) between stressed anchors, max 3 per inter-anchor region

## 2. Two-mode display controls

- [x] 2.1 Add "Lock to the beat" toggle button in the Prosody Lab tab
- [x] 2.2 Add beat-density selector (4 or 8 beats per bar) with auto-detect default
- [x] 2.3 Implement beat-grid quantization: snap syllable onsets to nearest beat position
- [x] 2.4 Implement auto beat-density detection from speech rate and syllable count

## 3. Zoom and layout

- [x] 3.1 Wire Plotly's scroll zoom to adjust effective bar density
- [x] 3.2 Handle single short rows (no stretching) vs multi-row stacking
- [x] 3.3 Ensure teacher/student comparison uses consistent beat density in locked mode

## 4. UI integration and tests

- [x] 4.1 Update the Prosody Lab tab template to include beat-lock toggle and density selector
- [x] 4.2 Wire new controls to trigger re-render of `buildMusicalScoreChart`
- [x] 4.3 Update `buildMusicalScoreChart` to produce a valid Plotly figure from a record
- [x] 4.4 Add unit tests for beat quantization logic and bar-chunking logic
- [x] 4.5 Verify both truth and locked modes render correctly in browser
