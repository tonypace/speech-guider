## Context

The app already computes and displays prosody metrics such as pitch range, mean pitch, and nPVI. Those values are useful, but they are too technical for a quick student checkup. The main analysis panel should present the metrics in a way that is understandable in a single glance.

## Goals / Non-Goals

**Goals:**
- Add student-friendly language to the main analysis panel.
- Keep the raw prosody numbers visible for reference.
- Show a qualitative nPVI label with a red-to-green indicator.
- Make the feedback brief, encouraging, and suitable for quick review.

**Non-Goals:**
- No new recording workflow.
- No changes to the Prosody Lab tab.
- No deep coaching or sentence-level prosody instruction.
- No speaker-relative pitch modeling.

## Decisions

### Quick-checkup tone
The analysis panel reads like a short coaching summary, not a detailed lesson. Each line leads with the interpretation and follows with the raw number and a brief coaching note.

### Absolute pitch ranges
Speaker-relative pitch is not used. Display uses approximate absolute Hz thresholds for low/middle/high voice labels.

### Qualitative pitch range labels
Pitch range is explained as:
- `a little flat` — for narrow range
- `nice variety` — for moderate range
- `very expressive` — for wide range

### nPVI color bar
nPVI is shown as a colored bar from red to green with teacher-friendly labels:
- `more flat` (red)
- `mixed rhythm` (amber)
- `strong rhythm` (green)

### Coaching copy
Each metric gets a short supportive note:
- `Pitch range: Nice variety — good contrast`
- `Mean pitch: High voice — bright and energetic`
- `Rhythm: Strong rhythm — nice stress contrast`

## Risks / Trade-offs

- [Threshold mismatch] Absolute pitch thresholds may not fit every voice equally well → Keep labels approximate and treat them as guidance, not judgment.
- [nPVI reliability] If the current nPVI calculation is unstable, the qualitative label will be misleading → Fix the calculation before exposing the bar.
- [Too much text] The panel could become cluttered → Keep each line short; reserve deeper explanation for the Prosody Lab.

## Thresholds

### Mean pitch
- `< 150 Hz` → `Low voice`
- `150–220 Hz` → `Middle voice`
- `> 220 Hz` → `High voice`

### Pitch range
- `< 6 semitones` → `A little flat`
- `6–12 semitones` → `Nice variety`
- `> 12 semitones` → `Very expressive`

### nPVI
- `0–25` → red → `More flat`
- `25–45` → amber → `Mixed rhythm`
- `45+` → green → `Strong rhythm`

## Example display lines

```
Pitch range: Nice variety — good contrast
Mean pitch: High voice — bright and energetic
Rhythm: Mixed rhythm — getting closer to natural stress timing
```
