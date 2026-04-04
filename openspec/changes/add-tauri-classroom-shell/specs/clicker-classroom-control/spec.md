## ADDED Requirements

### Requirement: Three-button classroom control
The Tauri shell SHALL interpret the classroom clicker as a semantic controller where `Left` means previous, `Right` means next, and `Tab` is the primary action.

#### Scenario: Clicker input drives semantic navigation
- **WHEN** the user presses the clicker’s left button in Tauri mode
- **THEN** the system SHALL move to the previous teaching moment for the current mode

### Requirement: Hold-to-record in practice modes
The Tauri shell SHALL treat `Tab` hold and release as record start and record stop in pronunciation and prosody practice modes.

#### Scenario: Pronunciation recording starts and stops with hold gesture
- **WHEN** the user holds the clicker’s tab button in pronunciation practice mode
- **THEN** the system SHALL start recording
- **AND WHEN** the user releases the button
- **THEN** the system SHALL stop recording and process the attempt

### Requirement: Pronunciation review auto-updates
When pronunciation review has usable teaching moments, navigating with `Left` or `Right` SHALL automatically select the current item and update the articulatory comparison view.

#### Scenario: Pronunciation review advances automatically
- **WHEN** the user presses the clicker’s right button while pronunciation review moments are available
- **THEN** the system SHALL advance to the next teaching moment and update the comparison visuals without requiring an extra confirm action

### Requirement: Prosody navigation is inert until usable
Prosody review navigation SHALL remain inert until at least two usable review targets exist.

#### Scenario: Prosody review has insufficient samples
- **WHEN** the user presses the clicker’s left or right button and fewer than two usable prosody review targets exist
- **THEN** the system SHALL not change the selected review target

### Requirement: Animation selection auto-animates
In Explore Mouth Shapes mode, selecting a phoneme with `Left` or `Right` SHALL automatically update and animate the current phoneme selection.

#### Scenario: Phoneme selection previews immediately
- **WHEN** the user presses the clicker’s right button in Explore Mouth Shapes mode
- **THEN** the system SHALL move to the next phoneme and animate the new selection automatically

### Requirement: Tauri-only controller behavior
Clicker semantics SHALL apply only inside the Tauri shell.

#### Scenario: Browser mode is unaffected
- **WHEN** the user opens Speech Guider in a normal browser
- **THEN** the clicker SHALL not override normal browser input behavior
