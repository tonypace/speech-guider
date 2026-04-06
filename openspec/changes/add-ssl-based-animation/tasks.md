## 1. AAI Adapter Foundation

- [x] 1.1 Add a tract-variable adapter module that decodes AAI arrays using the documented field order `LP, LA, TTCL, TTCD, TBCL, TBCD, VEL, GLO, LAT`.
- [x] 1.2 Add data structures for speaker or reference `mean`/`std` normalization profiles and support denormalization from z-scored AAI targets.
- [x] 1.3 Implement conversion from named AAI tract variables into the canonical 9-variable animation API with explicit clamping and field-level mapping.
- [x] 1.4 Define and document the handling of signed AAI `LP` values when converting into the renderer's unsigned `lip_protrusion` control.

## 2. Phase 1 Visualization Integration

- [x] 2.1 Add backend utilities that derive stable representative poses from time-varying AAI trajectories for current visualization endpoints.
- [x] 2.2 Integrate AAI-derived canonical animation states into a development or comparison path without breaking the existing renderer-facing response contract.
- [x] 2.3 Preserve the current rule/template-based articulatory mapper as fallback when AAI-derived states are unavailable or disabled.

## 3. Masking And Validation

- [x] 3.1 Implement source-aware handling for XRMB-masked `VEL`, `GLO`, and `LAT` channels.
- [x] 3.2 Add fixture tests based on the AAI dataset contract that verify field order, denormalization, and canonical field completeness.
- [x] 3.3 Add tests that verify sign and direction correctness against `docs/articulatory-animation-api.md`, especially for `TTCD`, `TBCD`, `GLO`, `TTCL`, and `TBCL`.
- [x] 3.4 Add regression tests confirming converted AAI-derived states can be consumed by existing animation payload paths without frontend contract changes.

## 4. Phase 2 SSL Prediction Path

- [x] 4.1 Define an SSL feature-extraction abstraction for local models such as Wav2Vec2 or HuBERT.
- [ ] 4.2 Implement an initial predictor that maps SSL features into AAI tract-variable outputs rather than directly into renderer fields.
- [ ] 4.3 Route SSL-predicted tract variables through the same AAI adapter used for dataset-backed conversion.
- [ ] 4.4 Preserve fallback to the current symbolic articulatory mapper when SSL predictions are unavailable, disabled, or low-confidence.

## 5. Documentation

- [x] 5.1 Document the AAI tract-variable contract and its mapping into the canonical animation API for local development.
- [x] 5.2 Document normalization, stats-profile selection, and masked-channel behavior for future dataset and model work.
- [x] 5.3 Document phase-1 representative-pose behavior versus future continuous trajectory-driven animation behavior.
