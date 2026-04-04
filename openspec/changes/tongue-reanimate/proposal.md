## Why

The current tongue animation geometry does not follow an anatomically correct palate track, so tongue-tip and tongue-body controls can move above the visible palate and produce unstable or misleading shapes. We need to realign the renderer with standard articulatory modeling so location and constriction behave predictably and match the academic interpretation of tongue tip and tongue body controls.

## What Changes

- Redraw the renderer's palate-following control path so it starts at the bottom of the upper incisor, follows the palate closely, and extends to the posterior line opposite the incisor bottom.
- Change tongue-tip and tongue-body location handling to use distinct normalized segments on a shared anatomical roof track, with a buffer gap between the two domains to reduce rendering artifacts.
- Normalize tongue-tip and tongue-body constriction degree values so `0` means contact with the palate and `1` means a resting offset from the palate, using bounded renderer calibration instead of raw pixel distances.
- Constrain tongue target points and control handles so the tongue cannot cross above the palate line.
- Add backward-compatible normalization for saved presets and backend-provided values that still use the older raw-distance scale.
- Review and redraw shipped phoneme presets, and define how previously saved custom presets are migrated or flagged when they remain visually incorrect under the corrected tongue geometry.

## Capabilities

### New Capabilities
- `articulatory-tongue-geometry`: Defines the anatomical roof track, segmented tongue location mapping, normalized constriction degree behavior, and collision-safe tongue rendering rules for the SVG articulatory model.

### Modified Capabilities

## Impact

- Affected frontend renderer code in `static/js/svg_articulatory_renderer.js`, slider/UI configuration in `static/js/app.js` and `app/templates/index.html`, and preset/state normalization in `src/models/articulatory.py`.
- Affected tests in `tests/test_articulatory.py`, `tests/js/animationLab.test.js`, and related end-to-end animation tests.
- No new external dependencies are required, but existing saved presets and defaults must remain compatible through normalization while allowing visually incorrect presets to be redrawn.
