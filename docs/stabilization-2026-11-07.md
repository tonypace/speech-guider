# Stabilization repair evidence — November 7, 2026

## Confirmed desktop failure

The installed application's backend log reports `PermissionError` opening
`/Applications/Speech Guider.app/Contents/Resources/assets/r4/configs/nine_channel_v12_100ms.yaml`.
The config, R4 checkpoint, and all three ContentVec files are owned by root with
mode 0700. The installer copied the source bundle's owner-only modes using
`shutil.copy2`; installing as root made those files unreadable to the app user.
The same failure also explains the observed Comparison Lab reference error.

Installer staging now explicitly sets data files to 0644 and native executable
assets to 0755. Regression tests cover both and preserve source permissions.
The user restored read access to the five installed files. Verified all five are
readable; loading these installed assets through the repository runtime on CPU
produced 50 finite nine-channel frames for a one-second synthetic input.
The packaged runtime and WebView recording workflow still need verification.
A rebuilt/reinstalled app is required for the source/UI changes below.

## Implemented source repairs

- Preserve model exceptions through the analysis boundary; return partial status,
  `success: false`, a diagnostic cause and job ID when articulation fails.
  Terminal progress reports failure instead of successful full analysis.
- Display partial prosody with a visible, text-escaped failure message.
- Display successful articulatory trajectories with audio playback and frame
  seeking. The renderer shows estimates, not phoneme-error judgments.
- Missing vowel segmentation produces null nPVI, not zero. Invalid/nonfinite,
  nonpositive and overlapping intervals are rejected. Reference tests distinguish
  unavailable values from legitimate zero and independently calculated 66.67.
- Remove unsupported mean-pitch, pitch-range and nPVI quality judgments.
- Hide Animation and Comparison navigation and help links; retain implementations.

## Verification

- 57 focused Python tests passed, plus two installer permission tests.
- 37 JavaScript tests passed; one pre-existing skipped test. Includes trajectory
  inspection, partial-result escaping and recorder ownership.
- Ruff, focused ESLint and focused mypy passed.
- Actual local model inference and a generated WAV posted through `/api/analyze`
  passed on CPU: HTTP 200, complete status, 50 nine-channel frames for one second,
  nPVI null. Synthetic audio verifies plumbing, not pronunciation accuracy.

## Still required before broad testing resumes

- Installed-app recording workflow verification (asset permissions repaired and
  installed assets verified through the repository runtime).
- Rebuild/install source changes and verify WebView audio/frame synchronization.
- Microphone settings, device selection and input diagnostics.
- Annotated natural/careful/fast recordings for syllable count and timing tests.
  The current heuristic remains unvalidated; do not tune to an expected count.
- Prosody Lab measurement timeline and explicit event diagnostics.
- Sliding-window nPVI with defined interval, pause and window semantics.

Main analysis still has no vowel alignment; null nPVI is intentional until real
intervals are available. The full stabilization exit criteria are not yet met.

## Follow-up: installed UI and reference 503

After permission repair, the installed UI still lacks the newly implemented
Analysis trajectory viewer; source edits do not update the frozen app.
A subsequent Comparison Lab request returned 503. The shared inference gate
returns this status while another workflow owns the worker. The log shows an
earlier generation for incomplete text, consistent with overlapping debounced
requests. Browser cancellation cannot immediately stop the backend worker.
Reference errors now display the server's detail, with an actionable busy
fallback for non-JSON responses. Regression coverage verifies that message.

Updated installer built successfully at `build/installer/Speech Guider - Local Noncommercial.pkg`. Frozen-backend smoke verification passed with actual R4 inference; the first cold-start attempt exceeded its 60-second timeout. Native bundle signature checks passed during packaging. Staged R4 data permissions verified as 0644. Installation and user WebView playback verification remain outstanding.
