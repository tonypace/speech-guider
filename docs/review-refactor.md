# Review and refactor — 2026-11-06

## Scope

Three Sol subsystem reviewers covered backend, frontend, and audio/model/cache
code, with integration review of tooling, documentation, and desktop launchers.
A requested additional Luna audit could not start because the agent thread limit
was reached; a Sol reviewer performed the independent backend/launcher audit.
Existing uncommitted R4 integration, formatting, and archive changes were preserved.
This report distinguishes implemented cleanup from architectural work still open.

Detailed inventories: [backend](review-backend.md), [pipeline](review-pipeline.md),
and [frontend](review-frontend.md).

## Implemented

| Boundary | Result |
| --- | --- |
| Waveform extraction | Praat channel selection retains the full mono waveform instead of one sample. |
| Shared audio conversion | API inference paths share decoding/resampling; browser recording paths share temporary AudioContext cleanup. |
| Playback | Reference/student advancement and source ownership share helpers; seek, rate changes, loops, and replacement synchronize audio and frames. Stale decodes cannot restore obsolete buffers. |
| Cache ownership | Independent caches cannot overwrite/delete each other's audio; failed replacement cannot reload old audio; explicit zero TTL is respected. |
| Backend resources | Busy rejection closes unstarted coroutine; failed ffmpeg conversion removes partial output; templates use public Starlette API. |
| Desktop development | Paths resolve from script location; startup failure stops launch; exit cleans process groups; backend death stops the desktop session. |
| Browser test helpers | Replaced unsupported range-input `fill()` calls with a shared native input/change helper. |
| Quality gates | Fixed intrinsic typing/lint errors, removed unused JS code, scoped third-party stub exceptions and scan exclusions, made pytest root imports deterministic. |
| Source packaging | `.gitignore` no longer hides `app/models/*.py`; required schemas now appear as source to add to Git. |
| Documentation | Added indexed architecture/development/review guides, reduced PROJECT duplication, corrected default model and port guidance. |

No model weights, temporal-window policy, canonical renderer field names, prosody
extraction formulas, or frontend framework were replaced. Code remains intentionally split
between HTTP orchestration and scientific/model modules.

## Follow-up implementation

The next prioritized pass used Luna agents for bounded HTML, preset, cache, and
comparison work; the main agent completed integration and partial recorder edits
when agent usage limits were reached.

| Priority | Completed change | Acceptance evidence |
| --- | --- | --- |
| High | Shared inference ownership across primary, reference and Prosody Lab; heavy stages off the event loop; cancellation drains workers before gate/file release. | Competing endpoint and repeated-cancel tests, retained-file checks, off-loop stage assertions. |
| High | Reserved progress jobs, status lookup, independent subscribers, bounded replay/cursors, terminal events and expiry; recorder subscribes before upload. | HTTP reservation/submission/replay, multiple subscribers, disconnect, duplicate claim, capacity/expiry tests. |
| High | Escaped client-derived phonemes, tooltips, error contexts and stored prosody labels; public failures omit tracebacks/internal exceptions. | Hostile HTML/attribute tests plus existing feedback/browser flows. |
| Medium | Root-based configurable preset location, shape/finite validation, atomic replace and locked read-modify-write. | Corrupt shape/NaN recovery, interrupted writes, concurrent saves, finite-save validation. |
| Medium | Namespaced exact-text cache keys include provider settings and model file revisions; synchronized independent snapshots avoid disk-audio memory retention. | Provider/model changes, input/response mutation, concurrent methods, disk response-byte tests. |
| Medium | Generation checks span text changes/fetch/decode/UI commit; captured student audio feeds playback; disposal invalidates pending decodes. | Delayed/stale reference/student decode and microphone/disposal tests. |
| Medium | Capture listeners/tracks/contexts have explicit ownership and idempotent teardown; partial initialization and late permission results release resources. | Repeated init/destroy, late permission, partial visualizer failure, no-submit-on-destroy regressions. |
| Medium | Prosody history storage extracted into a bounded, shape-validating module. | Malformed storage, retention and role-eviction tests. |
| Domain | Pitch labels use explicit semitone range while the legacy Hz field remains available. | Exact octave references at different base pitches and a generated sweep tracked by Praat. |
| Maintenance | ARM setup no longer edits shell config or replaces environments; unused HTMX removed; legacy recorder tests assert real behavior instead of missing-method guards. | Shell syntax, direct PCM/timer/listener assertions and the combined quality suite. |

Contracts: [progress and ownership](progress-api.md), [desktop/offline/acoustic
release requirements](release-contracts.md). Browser checks also caught and fixed
DOM named-property startup (`window.recorder` initially resolves the element);
teardown now checks method presence. Browser server startup no longer uses the
source reloader, and readiness waits for application APIs instead of network idle.

## Prioritized remaining work

| Priority | Finding | Next change and acceptance evidence |
| --- | --- | --- |
| Medium / release | Standalone Tauri release still lacks a packaged backend. | Implement the documented native sidecar/port/readiness/asset/storage contract and validate on a clean machine. Student comparison audio is implemented. |
| Maintenance / release | Tailwind browser compilation and Plotly still load from CDNs. | Build static CSS and vendor licensed/pinned plot assets; run with external network blocked. Unused HTMX is removed. |
| Domain validation | Voice-quality CPPS/spectral tilt remain heuristics; coaching thresholds need recorded-speech validation. | Follow the versioned Praat/reference-corpus plan in release contracts. Pitch units/basic tracking are now covered. |
| Maintenance | Template/controllers still contain mixed rendering logic beyond extracted history/capture helpers. | Continue decomposition around covered pure-data boundaries; avoid cosmetic file moves. |
| Operational limit | Jobs/gates/presets locks/caches are process-local, and history is bounded. | Run one backend worker; multi-process/multi-user support needs separate shared-state/authentication design. |

These release and domain items remain open. Large module decomposition
should follow explicit lifecycle/data contracts and regression coverage, avoiding
file moves that merely relocate coupled state.

## Initial-pass validation

Integration results are recorded below after the final quality run. Unit checks
exercise deterministic resource and waveform behavior; they do not establish
pronunciation accuracy, perceptual audio quality, or physical microphone/Tauri
correctness. Retired-checkpoint skips remain expected. Existing jsdom canvas
warnings do not fail Vitest and are not evidence of browser canvas validation.

- `npm run check` with the project virtual environment activated: **passed**.
- ESLint: zero errors/warnings; Ruff lint and formatting: passed.
- Mypy: no issues in 57 Python files (one unused third-party override note).
- Pytest: **159 passed, 3 skipped**.
- Vitest: **100 passed, 1 skipped** across six test files.
- Shell syntax and mocked desktop lifecycle tests: passed.
- `git diff --check` and local documentation link resolution: passed.
- Mocked Playwright browser suite: **16 passed** after installing the required
  Chromium and correcting the existing range-input test helper. Initial attempts
  were blocked by sandbox server permissions and missing browser binaries.
- Real-model end-to-end runs and physical microphone/Tauri validation were not run.

## Follow-up validation

- `npm run check`: passed. Ruff lint/format, ESLint, and mypy (63 files) clean.
- Pytest: **185 passed, 3 skipped**. Vitest: **121 passed, 1 skipped**.
- Mocked Playwright suite: **16 passed** after explicit app-readiness checks and
  fixing recorder startup. An earlier run exposed those issues and was corrected.
- Shell syntax, documentation link resolution, and `git diff --check`: passed.
- Unit tests retain jsdom canvas warnings. Physical microphone/speaker behavior,
  packaged Tauri, network-blocked release assets, and recorded-corpus acoustic
  calibration remain release/domain validation work described above.
