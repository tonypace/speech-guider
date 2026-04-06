# Articulatory Animation API

This document defines the canonical 9-variable control contract for the Speech Guider SVG articulatory animation system.

Its purpose is to let other systems build translation layers from their own articulatory coordinate systems into this one without sign errors, inverted slider behavior, or mismatched tongue geometry assumptions.

This is the source-of-truth API document for the current implemented renderer contract.

## Scope

- This document describes the current runtime contract as implemented.
- It documents the canonical field names used in JSON payloads and renderer state.
- It documents the short slider aliases used in the Animation Lab UI.
- It documents actual numeric ranges, including the fact that not all 9 variables are normalized today.

## Canonical State Shape

```json
{
  "lip_aperture": 0.25,
  "lip_protrusion": 0.71,
  "tongue_tip_constriction_location": 0.20,
  "tongue_tip_constriction_degree": 1.0,
  "lateral_tongue_drop": 0.0,
  "velic_aperture": 0.0,
  "tongue_body_constriction_location": 0.70,
  "tongue_body_constriction_degree": 1.0,
  "glottal_aperture": 0.0
}
```

## Quick Reference

| Alias | Field name | Range | Default | Slider right means |
| --- | --- | --- | --- | --- |
| `LA` | `lip_aperture` | `0..1` | `0.25` | mouth opens more |
| `LP` | `lip_protrusion` | `0..1` | `0.71` | lips protrude more |
| `TTCL` | `tongue_tip_constriction_location` | `0..1` | `0.20` | tongue-tip anchor moves posteriorly on the tip track |
| `TTCD` | `tongue_tip_constriction_degree` | `0..1` | `1.0` | tongue tip moves farther away from the roof |
| `LAT` | `lateral_tongue_drop` | `0..40` | `0.0` | tongue sides drop more |
| `VEL` | `velic_aperture` | `0..1` | `0.0` | velum opens more / nasal coupling increases |
| `TBCL` | `tongue_body_constriction_location` | `0..1` | `0.70` | tongue-body anchor moves posteriorly on the body track |
| `TBCD` | `tongue_body_constriction_degree` | `0..1` | `1.0` | tongue body moves farther away from the roof |
| `GLO` | `glottal_aperture` | `0..30` | `0.0` | glottis opens more / voicing decreases |

## Global Rules

- All sliders increase numerically from left to right.
- Out-of-range values are clamped by the renderer.
- `LA`, `LP`, `TTCL`, `TTCD`, `VEL`, `TBCL`, and `TBCD` are canonical normalized controls.
- `LAT` and `GLO` are canonical but not normalized yet.
- Larger values do not always mean more constriction. In several cases they mean more opening.

## Tongue Geometry Model

The tongue controls are defined against a shared roof track.

- The roof track starts at the bottom of the upper incisor region.
- It follows the palate posteriorly.
- It extends to the posterior line opposite the incisor bottom.
- The visible palate and tongue sampling track are aligned by design.

Two different location controls use this one shared roof track, but they do not use the same subdomain.

- `TTCL` maps onto roof-track fraction `0.00..0.25`
- `TBCL` maps onto roof-track fraction `0.35..1.00`
- `0.25..0.35` is intentionally unused to reduce artifacts

This means:

- `TTCL=1.0` is the back of the tongue-tip domain, not the back of the whole mouth
- `TBCL=0.0` is the front of the tongue-body domain, not the incisors
- both `TTCL` and `TBCL` run anterior -> posterior as the value increases

For the tongue constriction degree variables:

- `TTCD=0` means tongue-tip contact with the roof track
- `TBCD=0` means tongue-body contact with the roof track
- larger values move the tongue farther inward from the roof, not closer to it

That sign convention is easy to invert accidentally. External systems that use "more constricted = larger value" will usually need to invert before mapping into `TTCD` or `TBCD`.

## Variable Reference

### 1. `LA` / `lip_aperture`

- Range: `0..1`
- Default: `0.25`
- Slider right means: more lip aperture, more mouth opening, more jaw opening
- `0` means: lips closed at the aperture control limit
- `1` means: maximum supported aperture in the normalized contract
- Internal renderer scale: `lip_aperture_px = LA * 40`

Meaning:

- This is an opening variable, not a closure variable.
- It primarily drives vertical jaw displacement and oral opening.

Translation warning:

- If your source system uses lip closure, not lip aperture, do not copy the value directly.
- A closure-style variable usually needs inversion.

Typical adapter:

```text
LA = 1 - lip_closure
```

### 2. `LP` / `lip_protrusion`

- Range: `0..1`
- Default: `0.71`
- Slider right means: lips protrude more
- `0` means: least protruded / spread end of the supported range
- `1` means: most protruded / rounded end of the supported range
- Internal renderer scale: `lip_protrusion_px = LP * 14`

Meaning:

- This controls horizontal lip protrusion and visual rounding.
- Larger values push the lip contour forward.

Translation warning:

- If your source system separates rounding from protrusion, you must decide how to collapse them.
- In this renderer, one scalar covers the visible protrusion/rounding effect.

### 3. `TTCL` / `tongue_tip_constriction_location`

- Range: `0..1`
- Default: `0.20`
- Slider right means: tongue-tip anchor moves posteriorly along the tongue-tip roof-track subdomain
- `0` means: most anterior tongue-tip position supported by the tip domain
- `1` means: most posterior tongue-tip position supported by the tip domain
- Internal mapping: `roof_fraction = lerp(0.00, 0.25, TTCL)`

Meaning:

- This is a location variable, not a constriction-width variable.
- It determines where along the anterior palate/incisor region the tongue-tip constriction is anchored.

Translation warning:

- `TTCL` increases front -> back.
- Do not invert it unless your source system explicitly uses back -> front.
- Do not assume `TTCL=1` means uvular or velar territory. It only reaches the back of the tip subdomain.

### 4. `TTCD` / `tongue_tip_constriction_degree`

- Range: `0..1`
- Default: `1.0`
- Slider right means: tongue tip moves farther away from the roof track
- `0` means: tongue-tip contact with the roof track
- `1` means: the calibrated resting offset from the roof track
- Internal mapping: `distance_from_roof_px = TTCD * 32`

Meaning:

- This is a distance-from-roof variable.
- It is not a "more constricted = larger" variable.

Translation warning:

- Many articulatory datasets define constriction degree in the opposite direction.
- If your source variable increases as the constriction gets tighter, invert it before mapping.

Typical adapter:

```text
TTCD = 1 - tip_constriction_tightness
```

### 5. `LAT` / `lateral_tongue_drop`

- Range: `0..40`
- Default: `0.0`
- Slider right means: more lateral tongue-side opening or side drop
- `0` means: no lateral drop
- `40` means: maximum supported lateral drop in the current contract

Meaning:

- This controls how much the tongue sides are lowered.
- Higher values visually reduce tongue bulk and can expose lateral airflow cues.

Translation warning:

- `LAT` is not normalized today.
- If your source system uses `0..1`, multiply by `40`.

Typical adapter:

```text
LAT = 40 * lateral_drop_normalized
```

### 6. `VEL` / `velic_aperture`

- Range: `0..1`
- Default: `0.0`
- Slider right means: velic opening increases and nasal coupling increases
- `0` means: oral configuration, velum closed
- `1` means: maximum supported velic opening in the normalized contract
- Internal renderer scale: `velic_aperture_px = VEL * 40`

Meaning:

- This is an opening variable for the velopharyngeal port.
- Larger values correspond to more nasal airflow potential.

Translation warning:

- If your source system uses nasality rather than velic closure, it may already have the same sign.
- If your source system uses velum closure instead, invert it.

Typical adapters:

```text
VEL = nasality
VEL = 1 - velum_closure
```

### 7. `TBCL` / `tongue_body_constriction_location`

- Range: `0..1`
- Default: `0.70`
- Slider right means: tongue-body anchor moves posteriorly along the tongue-body roof-track subdomain
- `0` means: most anterior tongue-body position supported by the body domain
- `1` means: most posterior tongue-body position supported by the body domain
- Internal mapping: `roof_fraction = lerp(0.35, 1.00, TBCL)`

Meaning:

- This is the tongue-body analog of `TTCL`.
- It controls where the tongue-body constriction is anchored along the posterior palate/velar track.

Translation warning:

- `TBCL` also increases front -> back.
- Do not assume the same raw geometry as `TTCL`; the domains are intentionally different.

### 8. `TBCD` / `tongue_body_constriction_degree`

- Range: `0..1`
- Default: `1.0`
- Slider right means: tongue body moves farther away from the roof track
- `0` means: tongue-body contact with the roof track
- `1` means: the calibrated resting offset from the roof track
- Internal mapping: `distance_from_roof_px = TBCD * 24`

Meaning:

- This is a distance-from-roof variable for the tongue body.
- Larger values mean more open space between the tongue body and roof.

Translation warning:

- This sign is easy to invert for the same reason as `TTCD`.
- If your source variable increases with tighter constriction, invert it first.

Typical adapter:

```text
TBCD = 1 - body_constriction_tightness
```

### 9. `GLO` / `glottal_aperture`

- Range: `0..30`
- Default: `0.0`
- Slider right means: glottis opens more, voicing potential decreases
- `0` means: maximally adducted end of the current visual range
- `30` means: maximally open end of the current visual range

Meaning:

- This is a glottal opening variable, not a voicing variable.
- Larger values correspond to more open vocal folds and weaker voicing in the visualization.

Translation warning:

- Do not map a voicing strength value directly without inversion.
- If your source system uses `1 = voiced` and `0 = voiceless`, the sign is opposite.
- `GLO` is also not normalized today.

Typical adapter:

```text
GLO = 30 * (1 - voiced_normalized)
```

## Legacy Compatibility

The runtime accepts some historical non-canonical values and normalizes them.

- `LA` values greater than `1` are treated as legacy `0..40` values and divided by `40`
- `LP` values greater than `1` are treated as legacy `0..14` values and divided by `14`
- `VEL` values greater than `1` are treated as legacy `0..40` values and divided by `40`
- `TTCD` values greater than `1` are treated as legacy pixel-distance style values and divided by `40`
- `TBCD` values greater than `1` are treated as legacy pixel-distance style values and divided by `30`

This behavior exists for compatibility. New integrations should emit the canonical ranges documented here, not the legacy ones.

## Translation Layer Guidance

### AAI tract-variable datasets

If your source is an AAI tract-variable dataset or model output, do not map by position into the canonical renderer API. The documented AAI TV order is:

```text
LP, LA, TTCL, TTCD, TBCL, TBCD, VEL, GLO, LAT
```

The canonical renderer-facing API order is:

```text
LA, LP, TTCL, TTCD, LAT, VEL, TBCL, TBCD, GLO
```

Always convert by named field.

Additional AAI notes:

- AAI `LP` may be signed, where negative means retracted; this renderer only accepts nonnegative protrusion, so negative values must be mapped intentionally rather than copied directly.
- AAI `GLO` and `LAT` commonly use `0..1` and must be scaled into renderer ranges `0..30` and `0..40` respectively.
- Some AAI datasets emit z-scored targets and require speaker or reference `mean`/`std` profiles for denormalization before rendering.
- XRMB-based data may not supervise `VEL`, `GLO`, or `LAT`; those channels should use explicit fallback behavior rather than being treated as fully observed.

### If your source system uses closure-style variables

Invert them before mapping into opening-style variables.

```text
lip_aperture = 1 - lip_closure
velic_aperture = 1 - velum_closure
```

### If your source system uses constriction-tightness variables

Invert them before mapping into distance-from-roof variables.

```text
tongue_tip_constriction_degree = 1 - tip_tightness
tongue_body_constriction_degree = 1 - body_tightness
```

### If your source system uses voicing rather than glottal opening

Convert from voicing to glottal opening instead of copying the value directly.

```text
glottal_aperture = 30 * (1 - voiced_normalized)
```

### If your source system has one tongue frontness axis

Do not send that same value unchanged to both `TTCL` and `TBCL` unless you have verified the result visually.

- `TTCL` and `TBCL` use different anatomical subdomains
- a single source frontness value often needs two calibrated mappings

A reasonable starting point is:

```text
TTCL = tongue_frontness_for_tip
TBCL = tongue_frontness_for_body
```

where both source values are already oriented as `0 = anterior`, `1 = posterior`.

## Conformance Examples

These are example states in the canonical API format.

### Neutral

```json
{
  "lip_aperture": 0.25,
  "lip_protrusion": 0.71,
  "tongue_tip_constriction_location": 0.20,
  "tongue_tip_constriction_degree": 1.0,
  "lateral_tongue_drop": 0.0,
  "velic_aperture": 0.0,
  "tongue_body_constriction_location": 0.70,
  "tongue_body_constriction_degree": 1.0,
  "glottal_aperture": 0.0
}
```

### Bilabial Stop /p/

```json
{
  "lip_aperture": 0.00,
  "lip_protrusion": 0.43,
  "tongue_tip_constriction_location": 0.45,
  "tongue_tip_constriction_degree": 0.90,
  "lateral_tongue_drop": 0.0,
  "velic_aperture": 0.0,
  "tongue_body_constriction_location": 0.55,
  "tongue_body_constriction_degree": 0.55,
  "glottal_aperture": 18.0
}
```

### Alveolar Stop /t/

```json
{
  "lip_aperture": 0.10,
  "lip_protrusion": 0.07,
  "tongue_tip_constriction_location": 0.95,
  "tongue_tip_constriction_degree": 1.00,
  "lateral_tongue_drop": 0.0,
  "velic_aperture": 0.0,
  "tongue_body_constriction_location": 0.75,
  "tongue_body_constriction_degree": 0.55,
  "glottal_aperture": 18.0
}
```

### Velar Stop /k/

```json
{
  "lip_aperture": 0.10,
  "lip_protrusion": 0.14,
  "tongue_tip_constriction_location": 0.10,
  "tongue_tip_constriction_degree": 1.00,
  "lateral_tongue_drop": 0.0,
  "velic_aperture": 0.0,
  "tongue_body_constriction_location": 0.15,
  "tongue_body_constriction_degree": 1.00,
  "glottal_aperture": 18.0
}
```

### Nasal /n/

```json
{
  "lip_aperture": 0.10,
  "lip_protrusion": 0.07,
  "tongue_tip_constriction_location": 0.95,
  "tongue_tip_constriction_degree": 0.70,
  "lateral_tongue_drop": 0.0,
  "velic_aperture": 0.88,
  "tongue_body_constriction_location": 0.75,
  "tongue_body_constriction_degree": 0.55,
  "glottal_aperture": 3.0
}
```

### High Front Vowel /i/

```json
{
  "lip_aperture": 0.00,
  "lip_protrusion": 0.00,
  "tongue_tip_constriction_location": 0.90,
  "tongue_tip_constriction_degree": 0.60,
  "lateral_tongue_drop": 0.0,
  "velic_aperture": 0.0,
  "tongue_body_constriction_location": 0.95,
  "tongue_body_constriction_degree": 0.25,
  "glottal_aperture": 0.0
}
```

### High Back Rounded Vowel /u/

```json
{
  "lip_aperture": 0.00,
  "lip_protrusion": 0.71,
  "tongue_tip_constriction_location": 0.10,
  "tongue_tip_constriction_degree": 0.90,
  "lateral_tongue_drop": 0.0,
  "velic_aperture": 0.0,
  "tongue_body_constriction_location": 0.15,
  "tongue_body_constriction_degree": 0.30,
  "glottal_aperture": 0.0
}
```

## Checklist For External Integrations

Before shipping a translation layer, verify all of the following:

- `LA` is treated as opening, not closure
- `TTCL` increases anterior -> posterior
- `TBCL` increases anterior -> posterior
- `TTCD=0` means roof contact
- `TBCD=0` means roof contact
- `TTCD` and `TBCD` are not accidentally inverted
- `VEL` increases with nasal opening, not oral closure
- `GLO` increases with glottal opening, not voicing
- `LAT` is scaled into `0..40`
- `GLO` is scaled into `0..30`

If any one of these is wrong, the animation may still move, but it will encode the wrong articulatory meaning.
