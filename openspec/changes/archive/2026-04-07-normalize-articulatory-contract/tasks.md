## 1. Freeze the normalized canonical contract

- [x] 1.1 Define normalized semantics for all 9 canonical fields
- [x] 1.2 Normalize `lateral_tongue_drop` to `0..1`
- [x] 1.3 Normalize `glottal_aperture` to `0..1`
- [x] 1.4 Preserve `TTCD` and `TBCD` semantics as `0=tight`, `1=open/rest`
- [x] 1.5 Update canonical examples and defaults to use the normalized-only contract

## 2. Add global Python-side calibration

- [x] 2.1 Create `src/models/articulatory_calibration.py`
- [x] 2.2 Define per-parameter calibration rule types
- [x] 2.3 Implement `identity`, `gamma`, and `piecewise_linear` transforms
- [x] 2.4 Apply calibration to canonical normalized values before response emission
- [x] 2.5 Ensure calibration is global and phoneme-independent
- [x] 2.6 Add tests for identity and monotonicity

## 3. Normalize backend adapter outputs

- [x] 3.1 Update `src/models/aai_adapter.py` to emit fully normalized canonical values
- [x] 3.2 Remove mixed-range output behavior for `LAT`
- [x] 3.3 Remove mixed-range output behavior for `GLO`
- [x] 3.4 Isolate or remove mm/z-score conversion from the new normalized canonical path
- [x] 3.5 Ensure reference generation emits normalized canonical frames
- [x] 3.6 Ensure student trajectory emission emits normalized canonical frames
- [x] 3.7 Add tests asserting all 9 output fields remain within `0..1`

## 4. Make the renderer normalized-only

- [x] 4.1 Remove legacy raw-value coercion from `static/js/svg_articulatory_renderer.js`
- [x] 4.2 Keep only normalized-to-pixel geometry mapping inside the renderer
- [x] 4.3 Convert normalized `lateral_tongue_drop` into internal pixel-space drop
- [x] 4.4 Convert normalized `glottal_aperture` into internal pixel-space aperture
- [x] 4.5 Update voicing animation intensity to use normalized glottal semantics
- [x] 4.6 Add tests for strict normalized-only renderer input behavior

## 5. Simplify app-level JS state helpers

- [x] 5.1 Remove legacy raw-value normalization from `static/js/app.js`
- [x] 5.2 Ensure lab state helpers operate on normalized values only
- [x] 5.3 Ensure slider ingestion and state application preserve normalized semantics
- [x] 5.4 Remove mixed-range assumptions from helper code and defaults

## 6. Update docs and examples

- [x] 6.1 Update `docs/articulatory-animation-api.md` to declare all fields normalized
- [x] 6.2 Document `LAT` and `GLO` as normalized `0..1`
- [x] 6.3 Document the global Python-side calibration layer
- [x] 6.4 Document that calibration is monotonic and phoneme-independent
- [x] 6.5 Update example payloads and field descriptions

## 7. Update tests and integration coverage

- [x] 7.1 Update JS renderer tests to remove legacy coercion assumptions
- [x] 7.2 Update Python adapter tests to validate normalized canonical outputs
- [x] 7.3 Add integration tests for reference frame normalization
- [x] 7.4 Add integration tests for student trajectory normalization
- [x] 7.5 Add calibration behavior tests for representative tuned fields such as `TTCD`

## 8. Remove migration ambiguity

- [x] 8.1 Audit all code paths that emit articulatory frames
- [x] 8.2 Audit all code paths that consume articulatory frames
- [x] 8.3 Ensure comparison playback uses normalized frames only
- [x] 8.4 Ensure analysis animation paths use normalized frames only
- [x] 8.5 Remove temporary compatibility branches after validation
