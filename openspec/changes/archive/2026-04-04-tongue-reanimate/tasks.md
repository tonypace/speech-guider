## 1. Roof Track Geometry

- [x] 1.1 Replace the current tongue location path in `static/js/svg_articulatory_renderer.js` with a shared roof track that starts at the bottom of the upper incisor, follows the palate, and reaches the posterior line opposite the incisor bottom.
- [x] 1.2 Update visible palate rendering so the displayed palate and the tongue-location sampling path use the same geometry.
- [x] 1.3 Rework tongue location sampling to use path-length positions on the roof track instead of the current piecewise Bezier parameter mapping.

## 2. Tongue Control Semantics

- [x] 2.1 Map `tongue_tip_constriction_location` and `tongue_body_constriction_location` to separate roof-track subdomains with a buffer gap around the 30 percent region.
- [x] 2.2 Convert `tongue_tip_constriction_degree` and `tongue_body_constriction_degree` to normalized `0..1` controls and apply calibrated rest distances of `32px` and `24px` in the renderer.
- [x] 2.3 Constrain tongue target points and curve handles so the tongue cannot cross above the roof track.

## 3. Preset And State Migration

- [x] 3.1 Update defaults, sliders, and frontend state handling in `app/templates/index.html` and `static/js/app.js` to use the new normalized tongue-degree contract.
- [x] 3.2 Update `src/models/articulatory.py` normalization logic to convert legacy raw-distance tongue-degree values into the new normalized schema.
- [x] 3.3 Review and redraw shipped phoneme presets so they animate correctly under the corrected tongue geometry, and preserve compatibility for previously saved custom presets.

## 4. Validation

- [x] 4.1 Update Python, JS unit, and end-to-end tests to reflect the new roof-track mapping, normalized degree scale, and preset behavior.
- [x] 4.2 Run the relevant automated tests and verify the key tongue visualizations manually in the animation lab and pronunciation views.
