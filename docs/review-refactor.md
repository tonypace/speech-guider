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
formulas, or frontend framework were replaced. Code remains intentionally split
between HTTP orchestration and scientific/model modules.

## Prioritized remaining work

| Priority | Finding | Next change and acceptance evidence |
| --- | --- | --- |
| High | Blocking model/Praat/TTS work inside async routes; concurrency gate covers only primary analysis. | Introduce one inference orchestration service with explicit cancellation/file ownership; test simultaneous analysis/reference calls and canceled requests. |
| High | SSE has no complete job discovery/subscription lifecycle. | Define job creation, IDs, subscriptions, terminal events and expiry together; test reconnect and multiple subscribers. |
| High | User-derived strings can reach HTML sinks; error responses expose diagnostic tracebacks. | Define plain-text versus trusted-markup contracts; escape or render text nodes; test hostile inputs and public error payloads. |
| Medium | Preset path depends on cwd; writes are non-atomic and shapes unchecked. | Define persistent storage root and migration, validate shape, atomically replace, coordinate concurrent saves; test interrupted writes and recovery. |
| Medium | Cache keys omit provider/model identity; mutable entries and memory retention weaken ownership. | Version keys with generation inputs, define immutable responses and shared-worker synchronization; test provider changes and concurrent eviction. |
| Medium | Comparison UI request generation can become stale across fetch/decode. | Carry one generation token through request, decode and UI commit; test text changes during delayed decode. |
| Medium | Recorder initialization retains streams/listeners; large controllers mix capture/storage/rendering. | Introduce explicit initialize/destroy ownership, then extract history and plotting modules; test rapid clicks, repeated initialization and tab transitions. |
| Medium | Student comparison animation has no audio; Tauri release lacks packaged Python backend. | Define audio response and desktop runtime contracts before declaring either workflow complete. |
| Domain validation | Pitch-range label units disagree with caller; voice-quality metrics include heuristics. | Establish reference audio/Praat expectations before changing coaching thresholds or acoustic math. |
| Maintenance | Legacy setup script mutates shell/environment; UI depends on CDN scripts; existing unit tests contain guarded assertions. | Replace legacy setup with documented commands, define offline asset strategy, strengthen behavior assertions incrementally. |

These items are not marked complete by this cleanup. Large module decomposition
should follow explicit lifecycle/data contracts and regression coverage, avoiding
file moves that merely relocate coupled state.

## Validation

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
