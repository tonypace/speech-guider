## Context

The SSL AAI predictor is now operational and produces z-scored AAI tract variables from audio. The system needs to shift from automatic error detection to visual articulatory comparison. This requires:

1. Reference audio generation from text (starting with espeak-ng)
2. Full trajectory extraction from SSL predictor (not just representative poses)
3. Synchronized playback of two articulatory animations with audio
4. Audio editing-style inspection controls

## Goals / Non-Goals

**Goals:**
- Generate reference audio and articulatory animation from target text using espeak-ng
- Record student audio and generate their articulatory animation
- Display both animations side-by-side with synchronized or independent playback
- Provide audio editing controls: play/pause, scrub timeline, variable speed, zoom, loop
- Use downsampling and compression for responsive audio playback
- Backend emits ready-to-use canonical frame sequences
- Cache reference assets by text to avoid regeneration

**Non-Goals:**
- Replacing espeak-ng with better TTS yet (keep swappable architecture)
- Automatic phoneme error detection (focus on visual comparison)
- Rewriting the SVG renderer (use frame-by-frame feeding)
- Full continuous trajectory playback in first version (can use representative frames)
- Real-time streaming comparison (batch processing first)

## Decisions

### Decision: Use espeak-ng as first TTS provider

Rationale:
- Already integrated and tested in the system
- Fast enough for reference generation
- Good enough to validate the comparison workflow
- Architecture keeps TTS provider swappable for later upgrade

Alternatives:
- Local neural TTS: rejected due to size and initialization time
- Cloud TTS: rejected to keep local/offline operation

### Decision: Backend emits canonical frame sequences, not z-scored TVs

Rationale:
- Normalization and adapter logic stays backend-only
- Frontend receives data ready for renderer consumption
- Prevents duplication of AAI adapter logic in JavaScript
- Safer against sign/order mistakes

Format:
```json
{
  "audio_url": "blob://...",
  "frame_rate": 50,
  "duration_seconds": 3.2,
  "frames": [
    {
      "lip_aperture": 0.25,
      "lip_protrusion": 0.71,
      "tongue_tip_constriction_location": 0.20,
      "tongue_tip_constriction_degree": 1.0,
      "lateral_tongue_drop": 0.0,
      "velic_aperture": 0.0,
      "tongue_body_constriction_location": 0.70,
      "tongue_body_constriction_degree": 1.0,
      "glottal_aperture": 0.0
    }
  ]
}
```

### Decision: Downsample audio for responsive playback

Rationale:
- SSL predictor works at 16kHz but outputs frames at 50Hz
- Full 16kHz audio for playback is memory-intensive for per-frame payloads
- Downsampling to 8kHz or lower preserves articulatory timing while reducing size
- Compressed formats (WebM/Opus) further reduce memory footprint

Implementation:
- Backend downsamples audio before storage
- Frontend receives compressed audio blob
- AudioContext handles compressed playback

### Decision: Independent timelines with optional link toggle

Rationale:
- Student and reference durations will differ
- Strict lockstep is misleading without time-warping
- Independent scrub allows inspecting same relative position
- Link toggle allows synchronized playback when desired

Default:
- Independent timelines
- Play/Pause each separately
- Optional "Link Playheads" checkbox

### Decision: Cache reference assets by normalized text

Rationale:
- Text entry typically happens before recording
- Reference generation takes ~1-2 seconds
- Caching avoids regeneration on re-recording
- Normalized text (lowercase, trimmed) as cache key

Storage:
- In-memory LRU cache with TTL
- Optional temp file backing for audio
- Cache invalidation on explicit refresh

### Decision: Debounce reference generation on text entry

Rationale:
- Typing generates many intermediate states
- Eager generation wastes compute
- 500-800ms delay after typing stops is reasonable
- Can show "preparing reference" indicator

Implementation:
- Frontend debounce on target_text input
- Cancel prior pending fetch on new input
- Backend cancels stale generation if newer request arrives

## Architecture

### Backend Components

1. **Reference TTS Service** (`src/audio/reference_tts.py`)
   - Provider interface: `TextToSpeechProvider`
   - espeak-ng implementation: `EspeakTTSProvider`
   - Generate audio file from text
   - Downsample and compress for storage

2. **Comparison Cache Service** (`src/services/comparison_cache.py`)
   - Cache reference audio + frames by normalized text
   - LRU with TTL (e.g., 50 entries, 1 hour TTL)
   - Optional temp file backing

3. **Reference Animation Endpoint** (`app/api/comparison.py`)
   - POST `/api/reference-animation`
   - Input: `target_text`
   - Output: canonical frame sequence + audio URL
   - Uses TTS → SSL predictor → AAI adapter pipeline
   - Returns cached result if available

4. **Modified Analysis Endpoint** (`app/api/analyze.py`)
   - Extend to emit full trajectory, not just representative pose
   - Include `ssl_trajectory` field in response

### Frontend Components

1. **Comparison Controller** (`static/js/ssl_comparison_controller.js`)
   - Manage two timelines: reference and student
   - Handle play/pause, scrub, speed, zoom, loop
   - Synchronize or decouple playheads
   - Update renderers frame-by-frame

2. **Comparison UI Module** (`static/js/comparison_lab.js`)
   - New "Comparison Lab" tab
   - Side-by-side animation containers
   - Timeline controls
   - Target text input with debounce
   - Recording trigger

3. **Playback Controls**
   - Scrub bar with zoom window
   - Speed selector (0.25x, 0.5x, 0.75x, 1x, 1.25x)
   - Play/Pause per track
   - Loop in/out markers
   - Link playheads toggle

### Data Flow

**Reference Generation:**
```
[target_text] → debounce(500ms) → POST /api/reference-animation
                                        ↓
                              [check cache]
                                        ↓
                              [generate TTS audio]
                                        ↓
                              [downsample/compress]
                                        ↓
                              [SSL predictor]
                                        ↓
                              [AAI adapter]
                                        ↓
                              [canonical frames]
                                        ↓
                              [cache and respond]
```

**Student Analysis:**
```
[student audio] → POST /api/analyze
                          ↓
                   [SSL predictor]
                          ↓
                   [AAI adapter]
                          ↓
                   [canonical frames + audio]
```

**Playback:**
```
[comparison controller] → [select frame at time t]
                                ↓
                    [update left renderer with ref frame]
                                ↓
                    [update right renderer with student frame]
                                ↓
                    [sync audio playback if armed]
```

## Risks / Trade-offs

- [espeak-ng audio quality] → Acceptable for workflow validation, plan upgrade path
- [Per-frame payload size] → Mitigated by downsampling and frame decimation
- [Timing drift between audio and animation] → Use frame-rate-based indexing
- [Browser audio compression support] → Use widely-supported WebM/Opus or compressed WAV
- [Cache invalidation] → Start simple with TTL, add explicit refresh later

## Performance Considerations

- Reference generation: ~1-2 seconds (TTS + SSL inference)
- Cache hit: <100ms response
- Audio storage: ~8kHz mono compressed ~10KB/second
- Frame storage: ~50 frames/second × 9 floats × 4 bytes = ~1.8KB/second
- Total for 3-second utterance: ~35KB payload (manageable)

## Open Questions

- Should we decimate frames further for initial testing (e.g., 25Hz)?
- Loop region: UI markers or just start/end time inputs first?
- Audio compression: WebM/Opus or MP3 or compressed WAV?
- Cache eviction: LRU only or also explicit user clear?
- Initial view: full trajectories or start with representative poses?