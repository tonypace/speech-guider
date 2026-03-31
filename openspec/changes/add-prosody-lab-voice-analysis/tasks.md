## 1. Prosody Lab foundation

- [x] 1.1 Add the new Prosody Lab tab and wire it into the existing navigation.
- [x] 1.2 Reuse the existing hold-to-record interface without adding a target text field.
- [x] 1.3 Add local history handling for the last three recordings and their derived visualizations.

## 2. Analysis pipeline

- [x] 2.1 Add backend audio normalization for the recording input expected by `my-voice-analysis` and `librosa`.
- [x] 2.2 Integrate `my-voice-analysis` to extract syllable, pause, and rhythm balance data.
- [x] 2.3 Integrate `librosa.pyin` pitch tracking and map pitch values into visualization-ready data.

## 3. Visualization and comparison

- [x] 3.1 Build the Plotly prosody visualization with a stretchable time axis and discrete pitch grid.
- [x] 3.2 Overlay syllable onset markers, pitch baseline, and confidence coloring on the chart.
- [x] 3.3 Add the vertical teacher/student comparison layout for two saved recordings.

## 4. Feedback and polish

- [x] 4.1 Display the key prosody feedback metrics for syllables, pauses, and rhythm balance.
- [x] 4.2 Handle empty, failed, or discarded recordings gracefully.
- [x] 4.3 Add tests for recording history, analysis payloads, and visualization data generation.
