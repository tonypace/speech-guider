## ADDED Requirements

### Requirement: Native classroom shell
The system SHALL provide a Tauri-based macOS shell that loads the existing FastAPI-served Speech Guider app without requiring a separate frontend rewrite.

#### Scenario: Tauri loads the existing app
- **WHEN** the user launches the Tauri app
- **THEN** the shell SHALL display the existing Speech Guider interface served by FastAPI

### Requirement: Menu bar launch actions
The system SHALL provide menu bar actions for `Open Window`, `Practice Pronunciation`, `Practice Prosody`, `Explore Mouth Shapes`, and `Quit`.

#### Scenario: Menu opens a practice mode
- **WHEN** the user selects `Practice Pronunciation` from the menu bar
- **THEN** the system SHALL show the window and switch the app into pronunciation practice mode

### Requirement: Mode launch does not auto-record
The system SHALL arm the selected practice mode without starting recording automatically when launched from the menu bar.

#### Scenario: Practice mode is armed only
- **WHEN** the user selects `Practice Prosody` from the menu bar
- **THEN** the system SHALL show the prosody mode and wait for the clicker hold gesture before recording begins

### Requirement: Browser behavior remains unchanged
The system SHALL preserve conventional browser behavior outside the Tauri shell.

#### Scenario: Browser app remains conventional
- **WHEN** the user opens Speech Guider in a normal browser
- **THEN** the browser app SHALL continue to behave without Tauri-only clicker interception
