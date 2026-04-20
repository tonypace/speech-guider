## ADDED Requirements

### Requirement: Musical score visualization display
The system SHALL render each Prosody Lab recording as a musical score with stacked rows, a note-lane y-axis, and syllable markers.

#### Scenario: Short recording renders a single short row
- **WHEN** a recording shorter than one bar length is analyzed
- **THEN** the visualization shows one row that is as wide as the recording duration, with no stretching

#### Scenario: Long recording renders multiple stacked rows
- **WHEN** a recording is longer than one bar length
- **THEN** the visualization renders it as multiple vertically stacked rows, each row representing one bar's worth of time

### Requirement: Truth mode display
The system SHALL display recordings in truth mode by default, preserving real syllable timing.

#### Scenario: Truth mode renders real timing
- **WHEN** the user has not enabled "Lock to the beat"
- **THEN** stressed syllables are placed at their actual recorded timestamps and unstressed syllables are compressed between them

### Requirement: Lock-to-beat mode
The system SHALL provide a "Lock to the beat" toggle that quantizes syllable timings to a bar grid.

#### Scenario: User enables beat locking
- **WHEN** the user toggles "Lock to the beat" on
- **THEN** syllable timings are snapped to the nearest beat position within the bar grid

#### Scenario: Beat density auto-detection
- **WHEN** the recording is analyzed in locked mode
- **THEN** the system SHALL auto-detect whether 4 or 8 beats per bar best fits the speech rate, defaulting to 4

#### Scenario: User overrides beat density
- **WHEN** the user selects a manual beat density (4 or 8)
- **THEN** the system SHALL use the selected beat density for the bar grid instead of auto-detection

### Requirement: Pitch shown as note envelope
The system SHALL display pitch as a continuous dark line with large markers snapped to the nearest semitone.

#### Scenario: Pitch points quantize to nearest semitone
- **WHEN** pitch points are rendered
- **THEN** each point snaps to the nearest integer MIDI value (nearest note line)
- **AND** the marker is rendered at size 8–10 in a dark color (`#0f0f0f`)

#### Scenario: Note lane y-axis with discrete labels
- **WHEN** the chart is rendered
- **THEN** the y-axis shows discrete note names (e.g., C4, D#5) as tick labels
- **AND** each pitch marker sits directly on its corresponding note line

### Requirement: Grace-note compression for unstressed syllables
The system SHALL render unstressed syllables as small grace-note markers compressed between stressed syllable anchors.

#### Scenario: Unstressed syllables render as grace notes
- **WHEN** unstressed syllables are present between stressed anchors
- **THEN** they are rendered as small markers (size 5–6) clustered vertically between the surrounding stressed syllables
- **AND** they do not have independent horizontal space — they share the same row region as the surrounding stressed beats

#### Scenario: Grace-note crowding limit
- **WHEN** more than 3 unstressed syllables fall between two stressed anchors
- **THEN** only the 3 most prominent are shown as grace notes

### Requirement: Zoom changes bar density
The system SHALL allow the user to zoom in or out, changing how much time each row represents.

#### Scenario: Zoom in makes bars shorter
- **WHEN** the user zooms in on the chart
- **THEN** each row represents less time (bars appear compressed horizontally)

#### Scenario: Zoom out makes bars longer
- **WHEN** the user zooms out on the chart
- **THEN** each row represents more time (bars appear stretched horizontally)

### Requirement: Teacher vs Student comparison in musical score layout
The system SHALL display teacher and student recordings in vertically stacked panels using the musical score layout.

#### Scenario: Comparison view renders two recordings
- **WHEN** both a teacher and a student recording are selected
- **THEN** both are rendered in the musical score layout, teacher above student
- **AND** both use the same beat density when in locked mode

### Requirement: Summary metrics panel
The system SHALL display key prosody metrics alongside the musical score visualization.

#### Scenario: Metrics shown for current recording
- **WHEN** a recording is analyzed
- **THEN** the summary panel shows syllable count, pause count, rhythm balance, mean speaking note, and F0
