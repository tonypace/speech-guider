## Why

The current Prosody Lab pitch visualization is difficult to read — the pitch contour lacks visual clarity, syllable markers are indistinct, and the display does not support the use case of singing along or practicing rhythm. A redesigned musical-score display gives ESL learners a clean, zoomable, note-lane view where stressed syllables anchor the beat and unstressed syllables cluster as grace notes.

## What Changes

- Replace the current pitch-trace visualization with a two-mode musical score display.
- **Truth mode** (default): real timing preserved, continuous pitch envelope shown as a dark line, stressed syllables as anchors, unstressed syllables compressed between them.
- **Lock to the beat mode**: syllable timings quantized to a configurable bar grid (4 or 8 beats per bar), making the display usable as a practice score.
- Zoom control to change effective bar density.
- Auto-detect default bar density from speech rate, with manual override.
- No confidence color mapping — markers are dark, large, and readable.

## Capabilities

### New Capabilities
- `musical-score-display`: Redesigned Prosody Lab visualization with a musical score metaphor, stress-anchor timing, grace-note compression for unstressed syllables, and a beat-lock quantization toggle.

### Modified Capabilities
- `prosody-lab-voice-analysis`: The musical score display replaces the current Plotly pitch-trace chart. Backend analysis pipeline is unchanged.

## Impact

- Frontend: `static/js/prosody_lab.js` — new `buildMusicalScoreChart` function, two-mode display logic, zoom control.
- `app/templates/index.html` — add "Lock to the beat" toggle and beat-density selector.
- Backend unchanged — the same `pitch_track`, `syllable_onsets`, and `summary` data feeds the new display.
