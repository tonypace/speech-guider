## Context

Speech Guider already has a stable renderer-facing articulatory API and an SVG renderer whose tongue geometry semantics are now documented and tested. The current state generation path is symbolic: phoneme templates and rule-based mapping produce canonical poses for the renderer.

We now have an AAI dataset contract that defines continuous time-varying tract-variable supervision with nine channels: `LP, LA, TTCL, TTCD, TBCL, TBCD, VEL, GLO, LAT`. Those channels are semantically close to our renderer contract, but they differ in three critical ways:

- the field order is different from our canonical animation API
- some channels use raw physical units while our renderer expects calibrated normalized controls or renderer-native scales
- the dataset is emitted as per-speaker z-scored trajectories and includes masked channels for XRMB (`VEL`, `GLO`, `LAT`)

This change should therefore be structured in two phases:

1. AAI adapter phase: ingest tract-variable trajectories plus stats metadata and convert them into the canonical animation API safely.
2. SSL inference phase: predict tract-variable trajectories from self-supervised model features, then reuse the same adapter.

This preserves a clean seam between model prediction and renderer conversion.

## Goals / Non-Goals

**Goals:**
- Define a stable adapter from AAI tract-variable data into the canonical 9-variable renderer contract.
- Make field-order, sign, masking, and normalization behavior explicit and testable.
- Support per-speaker z-score denormalization with a global-reference fallback.
- Add an SSL inference pathway that predicts AAI-style tract-variable outputs from local speech model features.
- Keep the existing symbolic articulatory mapper available as a fallback and comparison baseline.
- Start with stable segment-level or representative poses while preserving a path to trajectory-driven animation later.

**Non-Goals:**
- Replacing the SVG renderer or changing its public input contract
- Shipping a public web deployment workflow
- Claiming physically exact articulatory reconstruction from acoustics alone
- Requiring full continuous animation playback in the first implementation phase

## Decisions

### Decision: Split the work into two internal phases

Phase 1 will implement the AAI tract-variable adapter and conversion pipeline before any new model prediction logic is required. Phase 2 will add SSL-model prediction into that tract-variable space.

Rationale:
- The dataset contract is already detailed enough to validate conversion logic independently of model inference.
- This creates a stable test seam: AAI fixtures can prove the renderer contract mapping before model outputs are introduced.
- It reduces debugging ambiguity because renderer errors and model errors are separated.

Alternatives considered:
- Build direct audio-to-renderer mapping first: rejected because it mixes model inference, normalization, and renderer conversion into one hard-to-debug path.
- Keep a single undifferentiated implementation phase: rejected because it makes validation and rollback harder.

### Decision: Use named-field mapping, never positional reuse

The adapter will decode AAI arrays according to the dataset's documented TV order and immediately convert them into named fields before any downstream processing.

AAI order:
- `LP, LA, TTCL, TTCD, TBCL, TBCD, VEL, GLO, LAT`

Canonical renderer order:
- `LA, LP, TTCL, TTCD, LAT, VEL, TBCL, TBCD, GLO`

Rationale:
- The orders differ and accidental positional reuse would silently produce wrong animation.
- Named-field conversion makes tests and debug logs readable.

Alternatives considered:
- Passing raw arrays through multiple layers: rejected because it invites sign and order mistakes.

### Decision: Treat AAI tract variables as the intermediate contract for SSL prediction

The SSL model pathway will predict AAI-style tract-variable outputs first, then reuse the adapter to reach the renderer contract.

Rationale:
- The dataset supervision already lives in tract-variable space.
- Reusing the same adapter for both dataset fixtures and model outputs guarantees consistent conversion behavior.
- This keeps future model-family swaps localized to the feature extractor / predictor layer.

Alternatives considered:
- Predict renderer variables directly from SSL features: rejected for phase 1 because it throws away the documented dataset contract and makes supervision alignment less transparent.

### Decision: Support denormalization with per-speaker stats and fallback stats

The adapter will support:
- per-speaker `mean`/`std` arrays when available
- a global reference stats profile when speaker-specific stats are unavailable

Rationale:
- The dataset API states the supervised values are z-scored, and correct world-space interpretation requires denormalization.
- Rendering directly from z-scores would be speaker-dependent and unstable.

Alternatives considered:
- Render directly from z-scored outputs: rejected because it makes animation dependent on hidden normalization context.
- Require speaker stats always: rejected because some inference cases may only have a global reference profile.

### Decision: Preserve canonical renderer semantics even when dataset semantics are richer

The adapter will convert AAI variables into the renderer contract using explicit calibration and clamping rules.

Important cases:
- `LP` in AAI is signed (`-` retracted, `+` protruded) while the renderer uses a nonnegative protrusion control
- `LA`, `TTCD`, `TBCD`, and `VEL` already align directionally with renderer opening semantics
- `GLO` uses `0..1` in the dataset but the renderer uses `0..30`
- `LAT` uses `0..1` in the dataset but the renderer uses `0..40`

Rationale:
- The renderer API is already documented and tested; upstream data must adapt to it, not the other way around.
- Keeping one canonical contract prevents frontend branching.

Alternatives considered:
- Expanding the renderer contract to accept signed or z-scored raw values: rejected because it would weaken the existing API and spread normalization responsibilities into the frontend.

### Decision: Start with representative poses, not full continuous playback

The internal pipeline will support trajectories, but the first user-facing integration will focus on stable segment-level or representative articulatory states.

Rationale:
- The current UI primarily consumes canonical states rather than full framewise animation sequences.
- Continuous framewise output adds smoothing, timing, and flicker-control problems that are easier to solve after the adapter is validated.

Alternatives considered:
- Deliver full framewise articulatory animation immediately: rejected for phase 1 because it adds temporal instability risk too early.

## Risks / Trade-offs

- [AAI field order mismatch] -> Convert arrays to named fields at the boundary and add fixture tests that fail on order mistakes.
- [LP sign mismatch] -> Document and test how signed retraction/protrusion maps into the renderer's unsigned lip protrusion control.
- [XRMB masked channels are weakly supervised] -> Carry mask awareness through training and inference, and preserve fallback logic for `VEL`, `GLO`, and `LAT`.
- [Per-speaker normalization context may be missing] -> Support a global reference profile and log which stats profile was used.
- [TBCL semantics may not perfectly match renderer body location] -> Treat this as a calibrated mapping with explicit tests rather than assuming identity.
- [Trajectory outputs may flicker when visualized directly] -> Start with representative poses and defer continuous playback policy.

## Migration Plan

1. Add an AAI adapter module and fixture-based tests using the documented dataset contract.
2. Integrate adapter outputs into backend animation payload generation behind a development/comparison path.
3. Keep the existing symbolic mapper as the default fallback until SSL-derived outputs are validated.
4. Add SSL feature extraction and tract-variable prediction using the same adapter target contract.
5. Expand to temporal playback only after segment-level outputs are stable.

Rollback is straightforward because the existing symbolic path remains available. If the SSL path or adapter produces unstable outputs, the backend can return the current template-driven states without changing the renderer API.

## Open Questions

- How should signed AAI `LP` values map into the renderer's unsigned `lip_protrusion` control when the source is strongly retracted?
- What global reference stats profile should be used when speaker-specific normalization metadata is unavailable at inference time?
- Should phase-1 API responses expose only representative poses, or optionally include raw trajectories for debugging?
- Which SSL feature representation should be the first supported source: current Wav2Vec2 internals, HuBERT, or a thin abstraction that can host either?
