## 1. Helper functions and thresholds

- [x] 1.1 Add `getPitchRangeLabel(range_semitones)` returning `a little flat`, `nice variety`, or `very expressive`
- [x] 1.2 Add `getMeanPitchLabel(mean_f0_hz)` returning `low voice`, `middle voice`, or `high voice`
- [x] 1.3 Add `getNpviLabel(npvi)` returning `{ label, color }` where color is `red`, `amber`, or `green`
- [x] 1.4 Add coaching copy strings for each metric (short, supportive, student-friendly)

## 2. Backend feedback generation

- [x] 2.1 Update `_generate_comprehensive_feedback` in `app/api/analyze.py` to build qualitative lines for pitch range, mean pitch, and nPVI
- [x] 2.2 Prepend the interpreted label to the existing metric value in the feedback string
- [x] 2.3 Add the nPVI color bar HTML to the feedback string for the analysis panel
- [x] 2.4 Keep raw values for all three metrics

## 3. Frontend integration

- [x] 3.1 Update the analysis panel renderer to call the new helper functions server-side
- [x] 3.2 Ensure the nPVI bar renders as an inline colored indicator in the feedback HTML
- [x] 3.3 Confirm Prosody Lab tab is unaffected

## 4. Tests

- [x] 4.1 Add unit tests for `getPitchRangeLabel` covering all three threshold bands
- [x] 4.2 Add unit tests for `getMeanPitchLabel` covering all three threshold bands
- [x] 4.3 Add unit tests for `getNpviLabel` covering all three threshold bands and correct color return
- [x] 4.4 Add integration test for feedback string containing the new labels
