## ADDED Requirements

### Requirement: Reference Audio Must Be Generated From Text

The system SHALL provide a backend service to synthesize reference audio from target text using a pluggable text-to-speech provider.

#### Scenario: Reference audio is generated via espeak-ng
- **GIVEN** a `target_text` string
- **WHEN** the reference generation endpoint is called
- **THEN** the system uses espeak-ng to synthesize audio
- **AND** the audio is downsampled and compressed for efficient storage

#### Scenario: TTS provider is swappable
- **GIVEN** a configured TTS provider
- **WHEN** reference audio is requested
- **THEN** the system uses the configured provider (espeak-ng default)
- **AND** the provider interface allows future substitution without changing callers

### Requirement: Reference Assets Must Be Cached By Text Content

The system SHALL cache reference audio and articulatory frames keyed by normalized text content to avoid regeneration.

#### Scenario: Same text requested twice
- **GIVEN** a reference for text "hello world" has been generated
- **WHEN** the same text is requested again within cache TTL
- **THEN** the cached audio and frames are returned immediately
- **AND** no TTS or SSL inference is repeated

#### Scenario: Cache uses normalized text key
- **GIVEN** text "  Hello World  " with mixed case and whitespace
- **WHEN** normalized (lowercase, trimmed)
- **THEN** it matches "hello world" cache key
- **AND** cache lookup succeeds

#### Scenario: Cache expires after TTL
- **GIVEN** a cached reference older than configured TTL
- **WHEN** the text is requested again
- **THEN** cache miss occurs
- **AND** new generation is triggered

### Requirement: Backend Must Emit Canonical Frame Sequences

The system SHALL convert SSL AAI predictor outputs to canonical animation frame sequences before sending to frontend.

#### Scenario: Reference trajectory conversion
- **GIVEN** SSL predictor outputs z-scored AAI TVs at 50Hz
- **WHEN** reference generation completes
- **THEN** each frame is converted to canonical 9-variable animation state
- **AND** the sequence includes `lip_aperture`, `lip_protrusion`, `tongue_tip_constriction_location`, `tongue_tip_constriction_degree`, `lateral_tongue_drop`, `velic_aperture`, `tongue_body_constriction_location`, `tongue_body_constriction_degree`, `glottal_aperture`

#### Scenario: Student trajectory conversion
- **GIVEN** student audio uploaded for analysis
- **WHEN** SSL predictor processes the audio
- **THEN** full trajectory of canonical frames is included in response
- **AND** trajectory has same frame rate as reference (50Hz)

#### Scenario: Frame data is ready for renderer
- **GIVEN** a frame from the backend sequence
- **WHEN** received by frontend
- **THEN** no additional normalization or conversion is needed
- **AND** frame can be directly passed to SVG articulatory renderer

### Requirement: Audio Must Be Downsampled For Efficient Playback

The system SHALL downsample and compress audio to reduce memory usage while preserving timing for articulatory comparison.

#### Scenario: Reference audio downsampling
- **GIVEN** raw TTS output at 16kHz
- **WHEN** stored for comparison playback
- **THEN** audio is downsampled to 8kHz or lower
- **AND** compressed using WebM/Opus or compressed WAV format

#### Scenario: Student audio downsampling
- **GIVEN** recorded audio at 16kHz or higher
- **WHEN** processed for comparison
- **THEN** audio is downsampled for playback storage
- **AND** full quality retained for SSL predictor input (separate path)

#### Scenario: Playback quality is acceptable
- **GIVEN** downsampled 8kHz compressed audio
- **WHEN** played through browser AudioContext
- **THEN** timing is accurate for articulatory synchronization
- **AND** quality is sufficient for comparison purposes

### Requirement: Frontend Must Support Side-By-Side Animation Playback

The system SHALL provide a comparison view showing reference and student animations side-by-side with synchronized or independent playback.

#### Scenario: Two animations displayed
- **GIVEN** reference frames and student frames loaded
- **WHEN** comparison view is active
- **THEN** left side shows reference articulatory animation
- **AND** right side shows student articulatory animation
- **AND** both use the same SVG articulatory renderer

#### Scenario: Frame-by-frame rendering
- **GIVEN** playback at time position t
- **WHEN** current frame is determined
- **THEN** reference renderer updates to reference frame at t
- **AND** student renderer updates to student frame at t
- **AND** no renderer geometry recomputation per frame (pose update only)

### Requirement: Frontend Must Provide Audio Editing Controls

The system SHALL provide playback controls: play/pause, scrub timeline, variable speed, zoom window, and loop region.

#### Scenario: Scrub timeline
- **GIVEN** a timeline showing utterance duration
- **WHEN** user drags scrub head
- **THEN** both animations update to frame at scrub position
- **AND** audio playback jumps to position (if armed)

#### Scenario: Variable speed playback
- **GIVEN** speed selector with options 0.25x, 0.5x, 0.75x, 1x, 1.25x
- **WHEN** user selects non-1x speed
- **THEN** playback rate changes for both tracks
- **AND** animation frame advance rate scales accordingly

#### Scenario: Zoom window
- **GIVEN** zoom control on timeline
- **WHEN** user zooms in
- **THEN** visible timeline window narrows around current position
- **AND** precision of scrubbing increases

#### Scenario: Loop region
- **GIVEN** loop in/out markers set
- **WHEN** playback reaches loop end
- **THEN** playback jumps to loop start
- **AND** both reference and student loop together

### Requirement: Frontend Must Support Linked And Independent Timelines

The system SHALL allow reference and student timelines to be scrubbed independently or linked together.

#### Scenario: Independent timelines (default)
- **GIVEN** comparison mode active
- **WHEN** user scrubs reference timeline
- **THEN** only reference animation and audio update
- **AND** student timeline remains at its position

#### Scenario: Link playheads mode
- **GIVEN** "Link Playheads" checkbox enabled
- **WHEN** user scrubs either timeline
- **THEN** both timelines move together at same relative position
- **AND** both animations update synchronously

#### Scenario: Independent play buttons
- **GIVEN** comparison mode with unlinked timelines
- **WHEN** user clicks play on reference only
- **THEN** reference plays while student pauses
- **AND** each track has its own play/pause button

### Requirement: Reference Generation Must Be Debounced On Text Entry

The system SHALL debounce reference generation requests to avoid waste during typing.

#### Scenario: Typing triggers debounced generation
- **GIVEN** user typing in target text input
- **WHEN** typing pauses for 500-800ms
- **THEN** reference generation request fires
- **AND** prior pending request is cancelled if new text entered

#### Scenario: Preparation indicator shown
- **GIVEN** reference generation in progress
- **WHEN** user waits for completion
- **THEN** UI shows "Preparing reference..." indicator
- **AND** animations are disabled until ready

#### Scenario: Cache hit is immediate
- **GIVEN** cached reference available
- **WHEN** text entry completes
- **THEN** no debounce delay for cache lookup
- **AND** reference displays immediately

### Requirement: Trajectory Data Must Support Frame-Rate Synchronization

The system SHALL align audio and animation using frame-rate-based indexing.

#### Scenario: 50Hz frame alignment
- **GIVEN** SSL predictor outputs at 50 frames/second
- **WHEN** playback time is t seconds
- **THEN** frame index = floor(t × 50)
- **AND** audio playback position matches frame timing

#### Scenario: Duration mismatch handling
- **GIVEN** reference duration 3.2s and student duration 3.5s
- **WHEN** at relative position 50%
- **THEN** reference shows frame at 1.6s
- **AND** student shows frame at 1.75s
- **AND** linked mode uses relative percentage, not absolute time

### Requirement: Backend Must Provide New Comparison Endpoint

The system SHALL expose a dedicated endpoint for reference generation separate from student analysis.

#### Scenario: POST /api/reference-animation
- **GIVEN** valid target_text in request body
- **WHEN** endpoint called
- **THEN** response includes:
  - `audio_url`: URL or blob handle for downsampled audio
  - `frame_rate`: 50
  - `duration_seconds`: utterance length
  - `frames`: array of canonical animation states
  - `cached`: boolean indicating cache hit

#### Scenario: Cache hit response
- **GIVEN** cached reference exists
- **WHEN** endpoint called with matching text
- **THEN** response returned within 100ms
- **AND** `cached: true` in response

#### Scenario: Cache miss response
- **GIVEN** no cached reference
- **WHEN** endpoint called
- **THEN** TTS and SSL inference execute
- **AND** response returned within 2 seconds
- **AND** `cached: false` in response

### Requirement: Student Analysis Must Include Full Trajectory

The system SHALL extend student analysis endpoint to return full articulatory trajectory, not just representative pose.

#### Scenario: Analyze response includes trajectory
- **GIVEN** student audio uploaded
- **WHEN** analysis completes
- **THEN** response includes `ssl_trajectory` field
- **AND** trajectory has same format as reference endpoint
- **AND** includes audio_url for downsampled playback audio

#### Scenario: Backward compatibility
- **GIVEN** existing client expecting old response format
- **WHEN** analysis endpoint called
- **THEN** old fields remain present for compatibility
- **AND** new `ssl_trajectory` field is additive only
