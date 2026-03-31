## Context

The app already has a hold-to-record speech flow and an analysis backend, but it does not yet provide a dedicated prosody-focused learning tab. The new feature adds a local-only Prosody Lab that combines short recordings, acoustic analysis, and a comparison-friendly visualization for teacher/student use.

## Goals / Non-Goals

**Goals:**
- Add a dedicated Prosody Lab tab for short recordings.
- Use `my-voice-analysis` for syllable, pause, and rhythm-related feedback.
- Use `librosa.pyin` for pitch contour extraction and Plotly for interactive visualization.
- Preserve a simple hold-to-record flow and keep only the last three recordings.
- Support vertical comparison of teacher and student samples.

**Non-Goals:**
- No target sentence workflow in this tab.
- No cloud sync or long-term recording library.
- No transcription-based scoring.

## Decisions

- **Plotly over matplotlib**: Plotly is the better fit because the user explicitly wants zoomable/stretchable time exploration in-browser. matplotlib would be simpler for static output, but it makes the requested interaction less natural.
- **Recording history limited to 3 items**: This keeps the UI lightweight and matches the local-use expectation while still preserving enough context for teacher/student comparison.
- **Local storage of recent analyses**: Store recent recordings and derived visualization payloads temporarily on the server or browser session, then prune oldest entries. This supports quick comparison without creating a persistence burden.
- **Split responsibilities between analysis libraries**: `my-voice-analysis` provides syllable/pause/rhythm outputs; `librosa.pyin` provides the pitch track used by the visualization. This keeps each tool focused on the part it does best.
- **Vertical comparison layout**: Teacher above student makes the comparison read naturally as a reference-versus-learner presentation.

## Risks / Trade-offs

- [Library compatibility] `my-voice-analysis` and `librosa` may require careful audio format normalization → Standardize the analysis input format and add conversion if needed.
- [Performance] Plotly traces for longer recordings may become heavy → Limit recording length and downsample the display data if necessary.
- [History storage] Keeping recent recordings increases state management complexity → Prune aggressively and store only the last three.
- [Interpretation clarity] Prosody visualizations can be misunderstood without labels → Pair the chart with concise metric summaries.
