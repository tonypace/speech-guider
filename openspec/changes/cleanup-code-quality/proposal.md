## Why

The repository has accumulated code-quality drift that makes routine cleanup harder and hides real failures:

- test and lint configuration now lives in duplicate files
- broad lint and typing suppressions hide type-shape problems instead of fixing them
- several backend paths catch broad exceptions and can downgrade real failures into misleading fallback or success responses
- stale scripts, outdated docs, and generated junk make it harder to know which entrypoints are real
- error-heavy modules still lack regression tests for the failure paths they rely on

This change creates a dedicated cleanup pass so future feature work can build on a smaller, more trustworthy base.

## What Changes

- consolidate duplicate pytest and ESLint configuration into a single source of truth for each tool
- add standard project scripts for linting, type checking, and Python or JavaScript test entrypoints
- keep the current relaxed line-length policy instead of tightening wrapping rules as part of this cleanup
- reduce broad `type: ignore`, `noqa`, and global mypy suppression usage where typed structures or targeted overrides can replace them
- tighten exception handling in backend analysis and utility code so fatal failures do not silently appear as successful results
- add regression tests for error handling, fallback behavior, and currently untested cleanup-sensitive modules
- remove or relocate stale demo scripts, outdated setup wrappers, and obsolete docs that point at no-longer-valid entrypoints
- remove backup files and generated junk from the tracked project surface and ensure ignore rules cover them

## Capabilities

### New Capabilities
- `code-quality-cleanup`: The repository defines a maintainable baseline for configuration, exception behavior, test coverage, and stale-asset pruning.

## Impact

- modifies repository-level developer workflow and quality gates
- touches backend API behavior where failures are currently hidden or misreported
- adds tests for failure and fallback scenarios that are not currently protected
- removes stale documentation and unused support files that no longer match the live app entrypoints
