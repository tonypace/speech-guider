## Why

The current animation system is driven primarily by phoneme templates and rule-based articulatory mapping. That produces canonical target poses, but it does not let the app infer articulatory motion directly from acoustic evidence or from the internal representations of local self-supervised speech models.

We now have a concrete AAI dataset contract whose 9 tract variables are close to our renderer semantics. This makes it practical to add an SSL-based pathway in two phases: first, an adapter from AAI tract-variable trajectories into the canonical animation API; second, model inference that predicts those tract variables from SSL features such as Wav2Vec2 or HuBERT.

## What Changes

- Add an AAI tract-variable adapter that converts dataset TV trajectories into the canonical 9-variable animation API used by the SVG renderer.
- Add explicit support for the AAI dataset's field order, z-score normalization, per-speaker stats, and masked channels.
- Add an SSL-based articulatory inference pathway that predicts tract-variable trajectories from local speech model features.
- Preserve the existing rule/template-based articulatory mapper as a fallback and regression baseline.
- Support phase-1 stable pose generation from time-varying trajectories, while designing the pipeline so full trajectory-driven animation can be added later.
- Add tests and documentation that prevent sign errors, field-order mismatches, and incorrect normalization when converting AAI outputs into renderer states.

## Capabilities

### New Capabilities
- `ssl-based-animation`: Derive canonical articulatory animation states from AAI tract variables and from SSL model predictions over audio.

### Modified Capabilities
- `articulatory-tongue-geometry`: Reuse the existing canonical renderer contract as the required target representation for AAI-derived and SSL-derived animation states.

## Impact

- Affected backend/model areas include `src/models/wav2vec2.py`, `src/models/articulatory.py`, and the analysis/error response pipeline that emits animation payloads.
- The frontend renderer contract stays stable and continues to consume the existing 9-variable API documented in `docs/articulatory-animation-api.md`.
- New adapter, normalization, and validation logic will be needed to convert AAI dataset outputs into renderer-safe states.
- The change remains local-first and offline; there is no requirement for public web deployment.
