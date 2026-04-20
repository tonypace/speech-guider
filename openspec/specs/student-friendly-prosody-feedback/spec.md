### Requirement: Student-friendly pitch range feedback
The system SHALL present pitch range in student-friendly language in the main analysis panel.

#### Scenario: Pitch range is narrow
- **WHEN** pitch range is less than 6 semitones
- **THEN** the analysis panel SHALL display `A little flat`

#### Scenario: Pitch range is moderate
- **WHEN** pitch range is between 6 and 12 semitones (inclusive)
- **THEN** the analysis panel SHALL display `Nice variety`

#### Scenario: Pitch range is wide
- **WHEN** pitch range is greater than 12 semitones
- **THEN** the analysis panel SHALL display `Very expressive`

#### Scenario: Numeric pitch range is visible
- **WHEN** pitch range is displayed
- **THEN** the raw pitch range value SHALL remain visible alongside the label

### Requirement: Student-friendly mean pitch feedback
The system SHALL present mean pitch in student-friendly language in the main analysis panel.

#### Scenario: Mean pitch is low
- **WHEN** mean pitch is below 150 Hz
- **THEN** the analysis panel SHALL display `Low voice`

#### Scenario: Mean pitch is middle
- **WHEN** mean pitch is between 150 Hz and 220 Hz (inclusive)
- **THEN** the analysis panel SHALL display `Middle voice`

#### Scenario: Mean pitch is high
- **WHEN** mean pitch is above 220 Hz
- **THEN** the analysis panel SHALL display `High voice`

#### Scenario: Numeric mean pitch is visible
- **WHEN** mean pitch is displayed
- **THEN** the raw mean pitch value SHALL remain visible alongside the label

### Requirement: Teacher-friendly nPVI feedback with color bar
The system SHALL present nPVI as a teacher-friendly qualitative label with a red-to-green bar.

#### Scenario: nPVI is low (more flat)
- **WHEN** nPVI is between 0 and 25 (inclusive)
- **THEN** the analysis panel SHALL display `More flat` with a red bar

#### Scenario: nPVI is medium (mixed rhythm)
- **WHEN** nPVI is between 25 and 45 (inclusive)
- **THEN** the analysis panel SHALL display `Mixed rhythm` with an amber bar

#### Scenario: nPVI is high (strong rhythm)
- **WHEN** nPVI is above 45
- **THEN** the analysis panel SHALL display `Strong rhythm` with a green bar

#### Scenario: Numeric nPVI is visible
- **WHEN** nPVI is displayed
- **THEN** the raw nPVI value SHALL remain visible alongside the colored bar

### Requirement: Brief coaching copy for each metric
The system SHALL include short coaching text for each prosody metric in the main analysis panel.

#### Scenario: Coaching copy is displayed for pitch range
- **WHEN** the analysis panel renders pitch range feedback
- **THEN** it SHALL include a short supportive note beside the label

#### Scenario: Coaching copy is displayed for mean pitch
- **WHEN** the analysis panel renders mean pitch feedback
- **THEN** it SHALL include a short supportive note beside the label

#### Scenario: Coaching copy is displayed for nPVI
- **WHEN** the analysis panel renders nPVI feedback
- **THEN** it SHALL include a short supportive note beside the label

### Requirement: Analysis panel scope
The system SHALL apply these qualitative prosody summaries only to the main analysis panel.

#### Scenario: Prosody Lab remains unchanged
- **WHEN** the user opens the Prosody Lab tab
- **THEN** the existing detailed Prosody Lab interface SHALL remain available
- **AND** the new student-friendly labels SHALL NOT replace the Prosody Lab experience
