### Requirement: Prosody Lab recording tab
The system SHALL provide a Prosody Lab tab that uses the same hold-to-record interaction model as the existing recorder.

#### Scenario: User starts and stops a short recording
- **WHEN** the user holds the record control in Prosody Lab and then releases it
- **THEN** the system SHALL capture a short local audio recording for analysis

### Requirement: Prosody analysis pipeline
The system SHALL analyze each recording with `my-voice-analysis` and pitch tracking with `librosa.pyin`.

#### Scenario: Recording is submitted for analysis
- **WHEN** a recording is completed
- **THEN** the system SHALL extract syllable, pause, rhythm, and pitch data for the recording

### Requirement: Prosody visualization
The system SHALL render an interactive Plotly visualization of the recording's pitch contour and rhythm timing.

#### Scenario: Visualization is generated
- **WHEN** analysis completes successfully
- **THEN** the system SHALL display a stretchable time-based pitch visualization with syllable markers and a baseline reference

### Requirement: Recent recording comparison
The system SHALL keep the last three recordings and their visualizations for comparison.

#### Scenario: A fourth recording is completed
- **WHEN** the user creates a new recording after three recordings already exist
- **THEN** the system SHALL discard the oldest recording and its visualization

### Requirement: Teacher and student comparison view
The system SHALL present recording comparisons vertically so that a teacher sample can be compared with a student sample.

#### Scenario: Two recordings are selected for comparison
- **WHEN** the user selects a teacher recording and a student recording
- **THEN** the system SHALL display the two visualization panels stacked vertically for comparison

### Requirement: Prosody feedback summary
The system SHALL display prosody feedback focused on syllables, pauses, and rhythm balance.

#### Scenario: Analysis finishes
- **WHEN** the recording analysis is complete
- **THEN** the system SHALL show the analyzed syllable, pause, and rhythm balance results to the user
