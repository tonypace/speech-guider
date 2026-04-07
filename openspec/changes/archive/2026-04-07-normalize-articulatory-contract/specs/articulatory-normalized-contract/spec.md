## ADDED Requirements

### Requirement: Canonical Articulatory Animation Frames Must Be Fully Normalized

The system SHALL define a single canonical articulatory animation contract in which all nine fields are normalized to `0..1`.

#### Scenario: Backend emits normalized canonical frames
- **GIVEN** a canonical animation frame emitted by the backend
- **WHEN** the frame is serialized in a comparison or analysis response
- **THEN** `lip_aperture`, `lip_protrusion`, `tongue_tip_constriction_location`, `tongue_tip_constriction_degree`, `lateral_tongue_drop`, `velic_aperture`, `tongue_body_constriction_location`, `tongue_body_constriction_degree`, and `glottal_aperture` are each within `0..1`

#### Scenario: Lateral tongue drop is normalized
- **GIVEN** a canonical frame
- **WHEN** `lateral_tongue_drop` is present
- **THEN** `0` means no lateral tongue-side drop
- **AND** `1` means maximum supported side drop

#### Scenario: Glottal aperture is normalized
- **GIVEN** a canonical frame
- **WHEN** `glottal_aperture` is present
- **THEN** `0` means glottal closure or strongest voicing tendency
- **AND** `1` means maximum supported glottal opening

### Requirement: Constriction Degree Semantics Must Remain Stable

The system SHALL preserve the current semantic direction for tongue constriction degree variables during normalization.

#### Scenario: Tongue tip constriction degree remains inverted-tightness
- **GIVEN** canonical `tongue_tip_constriction_degree`
- **WHEN** its value decreases toward `0`
- **THEN** the tongue tip moves closer to the roof track
- **AND** `0` represents maximal constriction or roof contact
- **AND** `1` represents rest or most open supported offset

#### Scenario: Tongue body constriction degree remains inverted-tightness
- **GIVEN** canonical `tongue_body_constriction_degree`
- **WHEN** its value decreases toward `0`
- **THEN** the tongue body moves closer to the roof track
- **AND** `0` represents maximal constriction or roof contact
- **AND** `1` represents rest or most open supported offset

### Requirement: Renderer Must Accept Only Normalized Canonical Inputs

The SVG articulatory renderer SHALL accept only canonical normalized inputs and SHALL NOT silently reinterpret non-normalized values as legacy units.

#### Scenario: Renderer receives normalized canonical input
- **GIVEN** a normalized canonical articulatory state
- **WHEN** it is passed to the renderer
- **THEN** the renderer updates geometry using that normalized state directly
- **AND** any pixel-space expansion remains an internal implementation detail

#### Scenario: Renderer no longer rescales legacy values
- **GIVEN** a value greater than `1` for a canonical normalized field
- **WHEN** it is passed into the renderer
- **THEN** the renderer does not divide it by a legacy maximum to reinterpret it
- **AND** the renderer treats normalized-only input as the supported runtime contract

### Requirement: Backend Must Emit Renderer-Ready Normalized Frames

The backend SHALL emit canonical normalized animation frames that are ready for direct renderer consumption without additional frontend semantic conversion.

#### Scenario: Reference frames are renderer-ready
- **GIVEN** a reference animation response
- **WHEN** frames are returned from the backend
- **THEN** each frame already conforms to the canonical normalized renderer contract
- **AND** the frontend can pass the frame directly to `setState()`

#### Scenario: Student trajectory frames are renderer-ready
- **GIVEN** a student analysis response including `ssl_trajectory`
- **WHEN** trajectory frames are returned from the backend
- **THEN** each frame already conforms to the canonical normalized renderer contract
- **AND** the frontend does not need mm-to-normalized, z-score-to-normalized, or mixed-range conversion logic

### Requirement: The System Must Support Global Python-Side Calibration

The system SHALL support a global Python-side calibration stage that adjusts normalized canonical animation values before they are emitted to the renderer.

#### Scenario: Calibration is global and phoneme-independent
- **GIVEN** normalized articulatory outputs are being prepared for response
- **WHEN** calibration is applied
- **THEN** the same configured transforms apply across all utterances
- **AND** no phoneme-conditioned logic is required

#### Scenario: Calibration preserves monotonic ordering
- **GIVEN** two normalized values `a` and `b` where `a < b`
- **WHEN** a configured calibration transform is applied
- **THEN** the calibrated output for `a` remains less than or equal to the calibrated output for `b`

#### Scenario: Identity calibration preserves normalized outputs
- **GIVEN** a parameter configured with `identity` calibration
- **WHEN** a normalized value is processed
- **THEN** the emitted calibrated value equals the incoming normalized value

### Requirement: Calibration Must Be Configurable Per Parameter

The system SHALL allow global calibration settings to be configured independently for articulatory parameters.

#### Scenario: TTCD can be tightened visually without retraining
- **GIVEN** `tongue_tip_constriction_degree` is configured with a non-identity monotonic transform
- **WHEN** normalized frames are emitted
- **THEN** low-to-mid `tongue_tip_constriction_degree` values may render closer to the palate than the raw model output would otherwise produce
- **AND** no phoneme inference is required
- **AND** no model retraining is required for that visual adjustment

#### Scenario: Multiple fields can use separate transforms
- **GIVEN** calibration config exists for multiple canonical fields
- **WHEN** frames are emitted
- **THEN** each supported field may use its own configured transform
- **AND** fields without configured shaping default to identity behavior

#### Scenario: Calibration applies consistently to reference and student paths
- **GIVEN** reference frames and student frames are both produced by backend articulatory paths
- **WHEN** calibration is enabled
- **THEN** the same global calibration rules apply to both paths

### Requirement: Calibration Configuration Must Live In Python

The system SHALL define calibration configuration in Python so that training-aligned visual tuning can be versioned and adjusted without frontend changes.

#### Scenario: Calibration module stores transform rules
- **GIVEN** the articulatory calibration system
- **WHEN** calibration rules are defined
- **THEN** they are stored in a Python module under `src/models/`
- **AND** backend adaptation code can apply them without JavaScript-side configuration

#### Scenario: Calibration module is the source of truth for global shaping
- **GIVEN** a future need to tune renderer-facing behavior
- **WHEN** developers adjust calibration
- **THEN** they update Python-side calibration rules rather than editing renderer geometry for semantic remapping

### Requirement: Documentation Must Describe The Normalized Contract Unambiguously

The system SHALL document the normalized articulatory contract and its semantic directions clearly enough for training and backend adaptation.

#### Scenario: Training workflow reads documentation
- **GIVEN** a CUDA training workflow uses the articulatory API documentation
- **WHEN** developers consult the canonical field definitions
- **THEN** the docs clearly state that all nine canonical fields are normalized to `0..1`
- **AND** the docs clearly state that `tongue_tip_constriction_degree` and `tongue_body_constriction_degree` use `0=tight` and `1=open/rest`

#### Scenario: Documentation separates semantics from pixel geometry
- **GIVEN** internal renderer constants still exist for drawing
- **WHEN** the documentation describes canonical fields
- **THEN** it distinguishes normalized semantic contract from renderer pixel-space implementation details

### Requirement: Tests Must Enforce The Normalized Contract

The system SHALL include tests that enforce normalized canonical output behavior and prevent regression to mixed-range semantics.

#### Scenario: Backend canonical frame tests enforce normalized ranges
- **GIVEN** backend-generated canonical frames
- **WHEN** tests inspect all fields
- **THEN** each canonical field is asserted to lie within `0..1`

#### Scenario: Renderer tests no longer assume legacy coercion
- **GIVEN** renderer unit tests
- **WHEN** they validate state behavior
- **THEN** they assert normalized-only input behavior
- **AND** they do not rely on implicit division by legacy maxima

#### Scenario: Calibration tests enforce monotonic transforms
- **GIVEN** configured calibration rules
- **WHEN** tests apply transforms across ordered input samples
- **THEN** calibrated outputs remain monotonic
- **AND** identity transforms remain exact
