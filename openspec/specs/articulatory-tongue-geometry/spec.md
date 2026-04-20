### Requirement: Roof Track Defines Tongue Location Geometry
The SVG articulatory renderer SHALL define tongue-tip and tongue-body constriction locations against a shared anatomical roof track that starts at the bottom of the upper incisor, follows the palate, and extends to the posterior line opposite the incisor bottom.

#### Scenario: Tongue location track follows the visible roof
- **WHEN** the renderer computes tongue location anchors for animation lab or pronunciation views
- **THEN** it uses the shared roof track as the source of truth for both location sampling and the visible palate geometry

#### Scenario: Roof track reaches the required posterior endpoint
- **WHEN** a constriction location is sampled at the back of the location domain
- **THEN** the anchor lies on the posterior portion of the roof track at the line opposite the front incisor's bottom

### Requirement: Tongue Tip And Body Use Separate Location Domains
The system SHALL interpret tongue-tip and tongue-body constriction location controls as normalized values on separate subdomains of the shared roof track, with a buffer gap between them near the 30 percent region to reduce rendering artifacts.

#### Scenario: Tongue tip remains in the anterior region
- **WHEN** `tongue_tip_constriction_location` is set anywhere in its normalized `0..1` range
- **THEN** the resulting anchor is mapped only within the tongue-tip subdomain of the roof track

#### Scenario: Tongue body remains in the posterior region
- **WHEN** `tongue_body_constriction_location` is set anywhere in its normalized `0..1` range
- **THEN** the resulting anchor is mapped only within the tongue-body subdomain of the roof track

#### Scenario: Buffer gap prevents overlap near the split
- **WHEN** both tongue-tip and tongue-body location values are set near the boundary between their domains
- **THEN** the renderer preserves a gap around that split so the two anchors do not collapse into the same roof-track region

### Requirement: Tongue Constriction Degree Is Normalized
The system SHALL interpret tongue-tip and tongue-body constriction degree values as normalized distances from the roof track where `0` means contact with the roof track and `1` means a calibrated resting offset from it.

#### Scenario: Zero degree produces contact
- **WHEN** `tongue_tip_constriction_degree` or `tongue_body_constriction_degree` is `0`
- **THEN** the corresponding tongue target lies on the roof track at the sampled anchor point

#### Scenario: Full degree uses calibrated rest distances
- **WHEN** `tongue_tip_constriction_degree` is `1`
- **THEN** the renderer applies an inward offset of `32px` from the sampled roof-track anchor

#### Scenario: Full degree uses body calibration
- **WHEN** `tongue_body_constriction_degree` is `1`
- **THEN** the renderer applies an inward offset of `24px` from the sampled roof-track anchor

### Requirement: Tongue Geometry Stays Inside The Oral Cavity
The renderer SHALL constrain tongue anchor points, target points, and curve handles so the tongue does not cross above the roof track.

#### Scenario: High constriction values stay below the roof
- **WHEN** tongue target points are computed for any valid location and constriction degree inputs
- **THEN** the resulting tongue geometry remains on the oral-cavity side of the roof track

#### Scenario: Visible palate and movement constraints stay aligned
- **WHEN** the visible palate is redrawn or updated for velic shaping
- **THEN** tongue motion constraints continue to follow the same roof-track geometry rather than a separate outdated path

### Requirement: Legacy Preset Values Are Safely Normalized
The system SHALL normalize legacy renderer-state and preset values that still use the older raw-distance tongue-degree scale while allowing shipped presets and saved custom presets to be reviewed against the corrected geometry, and it SHALL require all external AAI-derived or SSL-derived animation states to be converted into the same canonical renderer schema before visualization.

#### Scenario: Legacy raw-distance values are converted
- **WHEN** backend state normalization receives tongue constriction degree values from the older raw-distance scale
- **THEN** it converts them into the normalized `0..1` schema before returning SVG articulatory state

#### Scenario: Presets remain reviewable after migration
- **WHEN** shipped defaults or user-saved presets are loaded after the geometry correction
- **THEN** the system preserves compatibility through normalization and supports redrawing presets whose animation remains visibly incorrect

#### Scenario: External animation sources are adapted before rendering
- **WHEN** AAI-derived or SSL-derived articulatory outputs are prepared for the SVG renderer
- **THEN** the backend converts them into the same canonical field names, sign conventions, and calibrated control domains used by the renderer contract before any visualization occurs
