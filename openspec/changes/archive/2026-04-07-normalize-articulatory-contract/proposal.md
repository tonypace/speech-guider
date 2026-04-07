## Why

The articulatory animation system currently uses a mixed contract. Some canonical animation fields are normalized, while others still use renderer-specific numeric ranges. In addition, the JavaScript renderer and app helpers still accept and silently coerce legacy raw values. The backend adapter also mixes z-score denormalization, mm-based reference extents, and canonical renderer mapping.

This makes the system harder to reason about in four important ways:

1. CUDA model training does not have a single stable target contract.
2. Renderer inaccuracies are hard to diagnose because model output, backend conversion, and frontend coercion can all alter the same field.
3. Visual tuning currently risks pushing retraining pressure onto the model instead of allowing safe post-model calibration.
4. Existing documentation describes a contract that is partly normalized and partly legacy-shaped.

We want one strict articulatory animation contract across the system:
- all 9 canonical fields normalized to `0..1`
- backend emits normalized renderer-ready frames
- renderer accepts normalized values only
- global Python-side calibration allows monotonic visual tuning without phoneme-conditioned logic

## What Changes

This change introduces a new normalized articulatory contract and applies it across:
- Python backend adaptation
- comparison/reference frame generation
- analysis trajectory emission
- JavaScript renderer input contract
- app-level state normalization helpers
- docs and tests

It also introduces a global Python-side calibration layer so that visually important tweaks, such as making low-ish tongue constriction values sit closer to the palate, can be adjusted without retraining and without phoneme inference.

## Benefits

- Stable training target for the CUDA training workflow
- Explicit separation between model semantics and render calibration
- Simpler renderer contract
- Easier debugging and regression testing
- Safer iteration on visual tuning
- Cleaner documentation for future contributors

## Non-Goals

- Phoneme-conditioned calibration
- Replacing the SVG renderer geometry model
- Rebuilding the palate/tongue topology in this change
- Keeping permanent support for legacy mixed-range payloads
- Introducing a UI for calibration tuning in this change
