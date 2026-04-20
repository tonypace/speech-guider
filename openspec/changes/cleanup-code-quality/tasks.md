## 1. Tooling And Config Consolidation

- [ ] 1.1 Choose a single pytest configuration source and remove the duplicate configuration file or duplicate keys
- [ ] 1.2 Choose a single ESLint configuration source and remove the obsolete config format
- [ ] 1.3 Add standard scripts for linting, type checking, Python tests, JavaScript tests, and a combined quality check command
- [ ] 1.4 Preserve the current relaxed line-length policy instead of tightening wrapping rules during this cleanup

## 2. Suppression Reduction

- [ ] 2.1 Replace structured-data `type: ignore` usage in `src/audio/processor.py` with typed models or equivalent explicit typing
- [ ] 2.2 Replace avoidable `type: ignore` usage in `src/models/alignment.py` and `src/models/contentvec.py` with typed contracts
- [ ] 2.3 Remove avoidable package-level ignores in `src/__init__.py` and other low-value suppressions
- [ ] 2.4 Replace global mypy `ignore_missing_imports` with targeted overrides only where third-party libraries require them
- [ ] 2.5 Revisit existing `noqa` and file-level suppression usage in tests and scripts, keeping only the ones with a clear justification

## 3. Exception Handling Cleanup

- [ ] 3.1 Fix `app/api/analyze.py` so fatal analysis failures are not returned as successful responses
- [ ] 3.2 Reorder exception handlers in API endpoints so `HTTPException` and other specific cases are not shadowed by generic handlers
- [ ] 3.3 Preserve exception causes when wrapping lower-level failures in API or service errors
- [ ] 3.4 Narrow broad exception handling in `app/api/errors.py`, `app/utils/audio.py`, and `src/audio/prosody_lab.py` to intentional fallback cases
- [ ] 3.5 Keep documented fallback behavior where needed, but surface fallback reasons through logs or response metadata where appropriate

## 4. Regression Test Coverage

- [ ] 4.1 Add tests for `app/api/analyze.py` failure modes, fallback boundaries, and HTTP status preservation
- [ ] 4.2 Add tests for malformed payload and fallback behavior in `app/api/errors.py`
- [ ] 4.3 Add tests for upload conversion and cleanup failure paths in `app/utils/audio.py`
- [ ] 4.4 Add tests for optional-dependency and fallback branches in `src/audio/prosody_lab.py`
- [ ] 4.5 Add tests for `src/services/comparison_cache.py` and `src/audio/reference_tts.py` error paths
- [ ] 4.6 Replace environment-specific or checkpoint-path-dependent skips with mocks where practical

## 5. Repo And Docs Hygiene

- [ ] 5.1 Remove or relocate stale root-level demo and benchmark scripts that are no longer part of the supported workflow
- [ ] 5.2 Remove obsolete wrapper scripts and setup helpers that no longer match the current runtime path
- [ ] 5.3 Update or remove outdated docs such as `QUICKSTART.md` and `USING_VENV.md` so documented entrypoints match the live app
- [ ] 5.4 Remove backup files, generated junk, and cache artifacts from the project surface and strengthen ignore coverage where needed

## 6. Validation

- [ ] 6.1 Run the consolidated lint and type-check commands
- [ ] 6.2 Run the relevant Python and JavaScript test suites
- [ ] 6.3 Verify the cleaned developer workflow from docs and scripts still reflects the actual project entrypoints
