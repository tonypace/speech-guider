## Context

The current articulatory animation pipeline spans multiple layers:

1. Model output / SSL trajectory
2. Python adaptation into canonical animation fields
3. JSON payloads emitted by backend endpoints
4. JavaScript app helpers
5. SVG renderer input normalization
6. SVG renderer geometry expansion into pixels

Today, this pipeline mixes unit systems and compatibility behavior:
- `LA`, `LP`, `TTCL`, `TTCD`, `VEL`, `TBCL`, and `TBCD` are treated as normalized
- `LAT` and `GLO` still use renderer-oriented ranges
- renderer methods silently coerce larger values as legacy raw inputs
- Python adapters still use z-score and mm-scale conversion logic in canonical output paths

That ambiguity is acceptable for experimentation but not for a stable training and tuning workflow.

## Goals

- Normalize all 9 canonical animation fields to `0..1`
- Preserve current semantic directions unless intentionally changed
- Make the SVG renderer normalized-only
- Add global Python-side calibration for post-model shaping
- Keep calibration monotonic and phoneme-independent
- Update docs and tests so the normalized contract is the source of truth

## Non-Goals

- Phoneme-conditioned or context-conditioned calibration
- Learned calibration models
- Interactive calibration UI
- Major renderer geometry redesign

## Canonical Normalized Contract

All canonical fields SHALL use `0..1`.

### Field Semantics

- `lip_aperture`
  - `0` = closed
  - `1` = maximum supported opening

- `lip_protrusion`
  - `0` = least protruded
  - `1` = most protruded

- `tongue_tip_constriction_location`
  - `0` = front of tip domain
  - `1` = back of tip domain

- `tongue_tip_constriction_degree`
  - `0` = maximal constriction / roof contact
  - `1` = rest / most open supported offset

- `lateral_tongue_drop`
  - `0` = no side drop
  - `1` = maximum supported side drop

- `velic_aperture`
  - `0` = velum closed
  - `1` = maximum supported opening

- `tongue_body_constriction_location`
  - `0` = front of body domain
  - `1` = back of body domain

- `tongue_body_constriction_degree`
  - `0` = maximal constriction / roof contact
  - `1` = rest / most open supported offset

- `glottal_aperture`
  - `0` = closed / strongest voicing tendency
  - `1` = maximum supported glottal opening

## Decision: Preserve current constriction semantics

We will preserve the current renderer semantics for constriction degree:
- lower values mean tighter constriction
- higher values mean more open / farther from the roof

Rationale:
- this matches current renderer behavior
- changing direction during normalization would multiply migration risk
- it allows training targets to remain consistent with current lab controls

Consequence:
- external articulatory datasets that use "larger = tighter" must invert before mapping into canonical `TTCD` or `TBCD`

## Decision: Add Python-side global calibration

We will add a global calibration stage between normalized model output and emitted canonical frames.

This stage will:
- run in Python
- be global across all utterances
- operate per parameter
- use monotonic transforms only
- not depend on phoneme identity
- apply equally to reference and student frame generation

Rationale:
- model output may be approximately right but visually unsatisfying
- perceptual tuning should not require retraining
- phoneme-conditioned logic is intentionally avoided because phoneme computation is expensive and outside scope

### Calibration Modes

Initial supported modes:
- `identity`
- `gamma`
- `piecewise_linear`

### Example

A global `gamma` transform on `tongue_tip_constriction_degree` can compress lower values toward `0`, making low-to-mid constriction values render closer to the palate while preserving monotonic order.

## Decision: Renderer becomes normalized-only

The SVG renderer will accept only normalized canonical inputs.

It will still convert normalized values into pixel geometry internally, but it will no longer:
- treat values greater than `1` as legacy raw values
- silently divide by old maxima
- guess which unit system the caller intended

Rationale:
- strict contracts reduce ambiguity
- silent coercion hides errors
- renderer should render, not infer semantics

## Decision: Keep compatibility only at migration boundaries

During migration, compatibility code may temporarily remain in backend adaptation paths if needed.

Compatibility should not remain in:
- the SVG renderer
- app-level JS state normalization helpers

Rationale:
- migration ambiguity should live at explicit ingestion boundaries only
- the renderer should remain stable and deterministic

## Module Placement

The new global calibration logic should live in a dedicated Python module:
- `src/models/articulatory_calibration.py`

Recommended responsibilities:
- canonical field list
- calibration rule definitions
- transform functions
- helpers to apply calibration to canonical frame dicts
- optional validation helpers for normalized payloads

## Data Flow After Change

### Reference / Student path

```text
[model output]
    -> [normalize into canonical fields]
    -> [global Python calibration]
    -> [normalized canonical frames]
    -> [frontend]
    -> [renderer setState()]
    -> [pixel geometry]
```

### Renderer path

```text
[normalized canonical values]
    -> [strict clamp / validate]
    -> [normalized-to-pixel expansion]
    -> [SVG geometry]
```

## Migration Strategy

### Phase 1: Freeze contract
- define all 9 canonical fields as `0..1`
- update docs
- update examples
- update tests to target the new contract

### Phase 2: Add calibration
- implement `src/models/articulatory_calibration.py`
- add per-parameter transform config
- apply calibration to canonical backend output

### Phase 3: Normalize backend output
- normalize `LAT`
- normalize `GLO`
- update adapter and response payloads
- keep temporary backend-only compatibility if required

### Phase 4: Make frontend strict
- remove legacy coercion from renderer
- remove legacy coercion from app helpers
- ensure labs and comparison playback only use normalized values

### Phase 5: Remove legacy paths
- delete temporary compatibility branches after validation

## Risks

- existing labs may assume mixed ranges
- old tests may fail because they expect implicit normalization
- existing saved payload examples may be stale
- renderer output may shift perceptually after `LAT` and `GLO` normalization

## Mitigations

- update docs first
- add explicit range assertions in tests
- keep calibration configurable in Python
- migrate reference and student paths together

## Open Questions

- Should payload metadata use a new explicit value like `canonical_normalized` during migration?
- Should calibration be stored as Python constants or typed dataclasses?

Recommended answers:
- yes, use explicit metadata during migration if multiple payload modes coexist
- use typed Python dataclasses or module constants in `src/models/articulatory_calibration.py`
