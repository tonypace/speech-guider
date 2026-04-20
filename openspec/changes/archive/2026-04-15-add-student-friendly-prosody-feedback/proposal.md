## Why

The analysis panel already shows prosody metrics, but the raw numbers are hard for students to interpret quickly. This change adds short, student-friendly coaching language so the panel works as a fast checkup, while the deeper Prosody Lab remains available for advanced rhythm and intonation work.

## What Changes

- Add plain-language interpretations for pitch range, mean pitch, and nPVI in the main analysis panel.
- Keep the numeric values visible, but lead with coaching-oriented labels.
- Add a red-to-green nPVI bar with teacher-friendly wording.
- Make pitch feedback more student-friendly without changing the underlying analysis pipeline.
- Keep this scope limited to the existing analysis panel, not the Prosody Lab tab.

## Capabilities

### New Capabilities
- `student-friendly-prosody-feedback`: Interpreted prosody feedback for the main analysis panel.

### Modified Capabilities
- `pronunciation-analysis`: The analysis panel presentation changes to include qualitative prosody summaries.

## Impact

- Frontend: analysis feedback rendering in `static/js/recorder.js` and related UI display code.
- Backend: feedback generation in `app/api/analyze.py`.
- Tests: update analysis and feedback tests for the new labels and thresholds.
