## ADDED Requirements

### Requirement: Repository Quality Tooling Must Have Single Sources Of Truth
The repository SHALL define one authoritative pytest configuration and one authoritative ESLint configuration so quality settings do not drift across duplicate files.

#### Scenario: Duplicate test configuration is removed
- **WHEN** a developer inspects or updates pytest discovery and markers
- **THEN** those settings exist in one maintained configuration source rather than split across multiple files

#### Scenario: Duplicate lint configuration is removed
- **WHEN** a developer updates JavaScript lint behavior
- **THEN** the effective ESLint rules come from one maintained configuration format rather than overlapping legacy and flat configs

### Requirement: Relaxed Line Length Must Remain Intentional
The repository SHALL preserve its current relaxed line-length policy during this cleanup instead of treating line wrapping as a breaking quality migration.

#### Scenario: Cleanup does not force line-length churn
- **WHEN** the cleanup change updates lint or formatter settings
- **THEN** it keeps line-length handling compatible with the current repository policy rather than introducing broad reflow-only edits

### Requirement: Fatal Backend Failures Must Not Be Reported As Successful Analysis
Backend analysis endpoints SHALL distinguish fatal failures from intentional fallback behavior so callers do not receive a success response when the underlying analysis has failed.

#### Scenario: Fatal analysis exception does not masquerade as success
- **WHEN** an unexpected internal error interrupts the main analysis pipeline
- **THEN** the API returns a failure result or propagated error instead of a payload that reports success

#### Scenario: Intended fallback remains explicit
- **WHEN** a documented fallback path is used because an optional feature is unavailable
- **THEN** the response preserves that degraded-path behavior without hiding unrelated internal bugs as ordinary fallback

### Requirement: Wrapped Exceptions Must Preserve Debug Context
The codebase SHALL preserve causal context when higher-level API or service errors wrap lower-level exceptions.

#### Scenario: Wrapped error keeps original cause
- **WHEN** a lower-level exception is translated into a domain-specific error or HTTP error
- **THEN** the raised exception keeps the original cause attached for debugging and testing

### Requirement: Broad Suppressions Must Be Reduced To Justified Cases
Lint, typing, and file-level suppression markers SHALL be reduced to cases with clear technical justification, with typed contracts or targeted overrides preferred over broad ignores.

#### Scenario: Structured data uses explicit typing instead of ignore comments
- **WHEN** the code accesses known structured payloads or model outputs
- **THEN** it uses explicit typing or adapter contracts instead of relying on broad `type: ignore` comments for routine access

#### Scenario: Third-party typing gaps are scoped narrowly
- **WHEN** a dependency lacks usable type information
- **THEN** any ignore or override is scoped to the affected module or import rather than applied globally across the repository

### Requirement: Error-Prone Paths Must Have Regression Tests
The repository SHALL include regression coverage for the failure and fallback paths that are most likely to regress during cleanup.

#### Scenario: Analysis failure handling is tested
- **WHEN** backend analysis encounters expected and unexpected failures
- **THEN** tests verify status handling, fallback boundaries, and response semantics

#### Scenario: Utility fallback behavior is tested
- **WHEN** upload conversion, optional dependency loading, cache access, or reference synthesis fails
- **THEN** tests verify the documented failure or fallback behavior instead of leaving those branches unprotected

### Requirement: Supported Developer Entry Points Must Match Documentation
Repository scripts, docs, and helper files SHALL describe only the supported development and runtime entrypoints.

#### Scenario: Outdated startup instructions are removed or corrected
- **WHEN** a developer follows setup or quickstart documentation
- **THEN** the documented commands match the current application entrypoints and supported workflow

#### Scenario: Stale support files are pruned
- **WHEN** obsolete demo scripts, wrapper scripts, backups, or generated junk are no longer part of the supported workflow
- **THEN** they are removed, relocated, or ignored so the repository surface reflects the maintained system
