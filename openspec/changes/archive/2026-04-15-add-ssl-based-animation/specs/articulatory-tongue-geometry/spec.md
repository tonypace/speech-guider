## MODIFIED Requirements

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
