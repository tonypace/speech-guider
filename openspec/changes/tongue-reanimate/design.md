## Context

The current SVG articulatory renderer approximates the palate-following tongue track with a coarse hardcoded curve and treats tongue constriction degree values as raw renderer distances. This causes several visible problems: tongue-tip and tongue-body locations do not align with the visible palate, high constriction degree values can push the tongue above the roof of the mouth, and shipped or user-saved presets were authored against geometry that is now known to be anatomically wrong. The change touches frontend rendering, UI controls, preset normalization, and test expectations, so a design document helps lock the geometry and migration behavior before implementation.

## Goals / Non-Goals

**Goals:**
- Replace the current tongue location path with an anatomically grounded roof track that starts at the bottom of the upper incisor, follows the palate, and extends to the posterior line opposite that incisor bottom.
- Interpret `ttcl` and `tbcl` as separate normalized subdomains on that shared roof track, with a fixed buffer gap near the 30 percent region to reduce self-intersection and rendering artifacts.
- Interpret `ttcd` and `tbcd` as normalized constriction degree values where `0` means palate contact and `1` means a calibrated resting offset, using `32px` for tongue tip and `24px` for tongue body.
- Prevent tongue anchor points, target points, and tongue curve handles from crossing above the roof track.
- Migrate defaults, backend normalization, and preset handling so older saved values still load safely while incorrect presets can be redrawn.

**Non-Goals:**
- Reworking unrelated articulatory parameters such as lip aperture, velic aperture, or glottal aperture.
- Introducing a new rendering engine or replacing the SVG renderer architecture.
- Automatically determining anatomically perfect values for every phoneme without manual tuning.

## Decisions

- **Use one anatomical roof track as the source of truth.** The renderer will define a dedicated path for tongue-location sampling and visible palate drawing so the control geometry and displayed roof stay aligned. This is more reliable than keeping separate visual and invisible curves that can drift apart.
- **Sample locations by path length, not Bezier parameter.** `ttcl` and `tbcl` will map to arc-length positions on the roof track because equal normalized steps should correspond to equal travel along the anatomical surface. This avoids the non-uniform motion produced by the current piecewise quadratic parameterization.
- **Segment tongue-tip and tongue-body domains with a buffer gap.** The shared path will be partitioned internally so `ttcl` maps to the anterior region, `tbcl` maps to the posterior region, and a dead zone around the 30 percent area prevents the two articulators from collapsing into each other. This matches the user's requested research-style interpretation better than letting both controls address the full path.
- **Normalize constriction degree with calibrated rest distances.** `ttcd` and `tbcd` will remain `0..1` in data and UI, then be converted in the renderer to bounded inward distances using `32px` for tongue tip and `24px` for tongue body. This preserves a meaningful articulatory interpretation while keeping the visual envelope compact.
- **Constrain movement inward relative to the roof track.** The renderer will compute an inward-facing normal for sampled roof points and clamp tongue targets and upper tongue handles to remain on the oral-cavity side of that boundary. This is preferred over post-hoc visual clipping because it keeps the underlying geometry valid.
- **Treat existing presets as migratable but not automatically trustworthy.** Backend normalization will convert legacy raw-distance values into the new normalized schema, but shipped defaults and user-facing presets should be reviewed and redrawn because many were tuned against the incorrect tongue geometry. This is safer than silently preserving visibly wrong shapes.

## Risks / Trade-offs

- **Preset migration may preserve mathematically valid but visually wrong poses** -> Normalize old values for compatibility, then redraw shipped presets and leave room to flag or overwrite user presets after review.
- **Path-length sampling and collision clamping add renderer complexity** -> Keep the implementation isolated in the SVG renderer and cover it with focused unit tests around mapping and boundary behavior.
- **Changing control semantics will invalidate current slider and test expectations** -> Update UI ranges, defaults, test fixtures, and preset assertions in the same change so the new contract is applied consistently.
- **A single hardcoded roof path may still need anatomical tuning after visual review** -> Centralize track control points and mapping constants so they can be adjusted without rewriting the renderer logic.

## Migration Plan

1. Introduce the corrected roof track and segmented tongue location mapping in the SVG renderer.
2. Convert tongue constriction degree semantics and UI sliders to normalized `0..1` values with calibrated rest distances.
3. Add backend normalization for legacy renderer-state and preset values so existing saved data still loads.
4. Redraw default phoneme presets and update tests to reflect the corrected geometry.
5. Verify the animation lab and pronunciation visualizations, then manually review any persisted custom presets that still look wrong.

## Open Questions

- Should user-saved custom presets be explicitly flagged in the UI as needing review after migration, or is backend normalization plus documentation enough for the first pass?
- Should the posterior end of the shared roof track terminate exactly at the back wall reference line or slightly before it for easier tongue-curve shaping, while still preserving the requested academic endpoint for location mapping?
