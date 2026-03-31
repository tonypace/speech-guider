## Why

ESL learners need a way to hear and see how their speech rhythm and intonation develop over time, not just whether a pronunciation was “right” or “wrong.” Adding a dedicated Prosody Lab gives them a short-recording workflow plus visual feedback from `my-voice-analysis` and `librosa` in a form that is easier to compare across teacher and student samples.

## What Changes

- Add a new `Prosody Lab` tab with the same hold-to-record interface as the existing recorder.
- Analyze short local recordings with `my-voice-analysis` and pitch tracking from `librosa.pyin`.
- Display prosody feedback focused on syllables, pauses, rhythm balance, and pitch contour visualization.
- Keep the last three recordings and their visualizations for side-by-side comparison, then discard older entries.
- Support teacher-vs-student comparison in a vertical layout.
- Omit the target sentence field from this tab.

## Capabilities

### New Capabilities
- `prosody-lab-voice-analysis`: Record speech, analyze prosody, and visualize intonation/rhythm in the Prosody Lab tab.

### Modified Capabilities
- 

## Impact

- Frontend: new tab UI, recording/history controls, Plotly visualization, comparison layout.
- Backend: audio analysis endpoint(s), storage for recent recordings, `my-voice-analysis` and `librosa` integration.
- Dependencies: add `librosa` and supporting audio/plotting packages if not already present.
- Data handling: store recent recordings and derived visualization data temporarily for local comparison.
