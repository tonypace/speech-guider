### Requirement: AAI Tract Variables Must Be Converted By Named Field Mapping
The system SHALL convert AAI supervision arrays into named tract-variable fields using the documented dataset field order before producing canonical animation states.

#### Scenario: Dataset arrays are decoded using the AAI field contract
- **WHEN** the backend receives or loads a tract-variable array from the AAI dataset
- **THEN** it interprets the columns in the order `LP, LA, TTCL, TTCD, TBCL, TBCD, VEL, GLO, LAT` before any further mapping

#### Scenario: Canonical animation states are not built positionally from dataset order
- **WHEN** the system converts AAI tract variables into renderer-facing state
- **THEN** it maps named fields into the canonical animation API rather than reusing the dataset column order directly

### Requirement: AAI Normalization Context Must Be Supported
The system SHALL support z-scored AAI targets together with speaker or reference statistics so tract variables can be converted into renderer-safe values.

#### Scenario: Per-speaker stats are used when available
- **WHEN** AAI data includes speaker-specific `mean` and `std` arrays
- **THEN** the system uses those statistics to denormalize tract variables before applying renderer calibration rules

#### Scenario: Global reference stats can be used as fallback
- **WHEN** speaker-specific normalization statistics are unavailable at inference time
- **THEN** the system uses a documented global reference profile to denormalize tract variables before rendering or evaluation

### Requirement: AAI Variables Must Be Converted Into The Canonical Animation API
The system SHALL convert AAI tract variables into the canonical renderer-facing animation schema documented by the app.

#### Scenario: Output state contains canonical animation fields
- **WHEN** an AAI tract-variable frame or representative pose is converted for visualization
- **THEN** the result contains `lip_aperture`, `lip_protrusion`, `tongue_tip_constriction_location`, `tongue_tip_constriction_degree`, `lateral_tongue_drop`, `velic_aperture`, `tongue_body_constriction_location`, `tongue_body_constriction_degree`, and `glottal_aperture`

#### Scenario: Converted values honor documented sign conventions
- **WHEN** AAI tract variables are converted into canonical animation fields
- **THEN** the resulting state preserves the documented directionality of opening, constriction, voicing, and tongue-location axes used by the renderer

### Requirement: Dataset-Specific Channel Gaps Must Be Mask-Aware
The system SHALL preserve awareness of masked or weakly supervised AAI channels so unsupported values do not silently appear fully supervised.

#### Scenario: XRMB mask semantics are preserved
- **WHEN** the source dataset does not supervise `VEL`, `GLO`, or `LAT`
- **THEN** the system carries mask information or equivalent source-awareness through training or conversion logic rather than treating those channels as fully observed ground truth

#### Scenario: Unsupported channels can fall back safely
- **WHEN** a required renderer-facing field comes from a masked or weakly supervised AAI channel
- **THEN** the system uses documented fallback behavior rather than silently assuming the placeholder value is physically correct

### Requirement: Phase 1 Must Support Stable Pose Extraction From Trajectories
The system SHALL support generating representative articulatory poses from time-varying AAI trajectories before full continuous articulatory playback is required.

#### Scenario: Segment-level representative poses can be produced from trajectories
- **WHEN** the backend receives a time-varying tract-variable sequence for an utterance or segment
- **THEN** it can derive a stable canonical animation state suitable for the current visualization pipeline

#### Scenario: Trajectory support is preserved for later phases
- **WHEN** the system stores or processes AAI-derived articulatory outputs internally
- **THEN** it retains sufficient temporal structure to support future continuous animation work without redefining the canonical renderer contract

### Requirement: SSL Predictions Must Reuse The AAI Adapter Contract
The system SHALL treat AAI tract variables as the intermediate contract for SSL-based articulatory prediction.

#### Scenario: SSL outputs are converted through the same adapter
- **WHEN** an SSL model predicts articulatory outputs from audio
- **THEN** those outputs are translated through the same tract-variable adapter used for dataset-backed conversion before reaching the renderer-facing API

#### Scenario: Symbolic mapping remains available as fallback
- **WHEN** SSL-derived articulatory output is unavailable, low-confidence, or disabled
- **THEN** the backend can continue returning the current rule/template-based articulatory state without changing the renderer contract
