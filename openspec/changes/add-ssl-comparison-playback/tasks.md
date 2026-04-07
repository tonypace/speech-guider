## 1. Backend Reference TTS Service

- [x] 1.1 Create `src/audio/reference_tts.py` with TTS provider interface
- [x] 1.2 Implement `EspeakTTSProvider` using existing espeak-ng integration
- [x] 1.3 Add audio downsampling from 16kHz to 8kHz for playback
- [x] 1.4 Add audio compression (OGG/Vorbis)
- [x] 1.5 Add provider factory for future swappable TTS
- [ ] 1.6 Write tests for TTS service

## 2. Backend Comparison Cache Service

- [x] 2.1 Create `src/services/comparison_cache.py` for reference asset caching
- [x] 2.2 Implement LRU cache with TTL (50 entries, 1 hour default)
- [x] 2.3 Implement normalized text key generation (lowercase, trim, hash)
- [x] 2.4 Add cache entry: audio blob + canonical frames + metadata
- [x] 2.5 Add optional temp file backing for large audio
- [ ] 2.6 Write tests for cache service

## 3. Backend Reference Animation Endpoint

- [x] 3.1 Create `app/api/comparison.py` with new router
- [x] 3.2 Implement POST `/api/reference-animation` endpoint
- [x] 3.3 Add request schema: `target_text` string
- [x] 3.4 Add response schema with `audio_url`, `frame_rate`, `duration_seconds`, `frames`, `cached`
- [x] 3.5 Integrate TTS → SSL predictor → AAI adapter pipeline
- [x] 3.6 Add cache lookup and storage
- [x] 3.7 Add endpoint to FastAPI app
- [ ] 3.8 Write endpoint tests

## 4. Backend Student Trajectory Extension

- [x] 4.1 Modify `app/api/analyze.py` to extract full SSL trajectory
- [x] 4.2 Add trajectory conversion: z-scored TVs → canonical frames
- [x] 4.3 Add `ssl_trajectory` field to analyze response
- [ ] 4.4 Include downsampled audio URL for playback
- [x] 4.5 Maintain backward compatibility with existing response fields
- [ ] 4.6 Write tests for trajectory response

## 5. Frontend Comparison Controller

- [x] 5.1 Create `static/js/ssl_comparison_controller.js`
- [x] 5.2 Implement two-timeline state management (reference + student)
- [x] 5.3 Add play/pause per track with AudioContext integration
- [x] 5.4 Add scrub bar with current time indicator
- [x] 5.5 Add speed control (0.25x, 0.5x, 0.75x, 1x, 1.25x)
- [x] 5.6 Add zoom window control for timeline
- [x] 5.7 Add loop in/out markers
- [x] 5.8 Implement link playheads toggle
- [x] 5.9 Add frame-by-frame renderer updates
- [ ] 5.10 Write controller tests

## 6. Frontend Comparison UI Module

- [x] 6.1 Create `static/js/comparison_lab.js`
- [x] 6.2 Add new "Comparison Lab" tab to HTML template
- [x] 6.3 Implement side-by-side animation containers (left=reference, right=student)
- [x] 6.4 Add target text input with debounce (500-800ms)
- [x] 6.5 Add "Preparing reference..." indicator
- [x] 6.6 Add record button for student audio
- [x] 6.7 Add shared timeline scrub bar with zoom
- [x] 6.8 Add play/pause buttons per track
- [x] 6.9 Add speed selector control
- [x] 6.10 Add link playheads checkbox
- [x] 6.11 Add loop region controls (in/out markers)
- [x] 6.12 Integrate with existing SVG articulatory renderer

## 7. Frontend Debounced Reference Loading

- [x] 7.1 Add debounce utility (500-800ms) for text input
- [x] 7.2 Implement text change detection
- [x] 7.3 Add cancel prior pending fetch on new input
- [x] 7.4 Call `/api/reference-animation` endpoint after debounce
- [x] 7.5 Handle cache hit vs cache miss responses
- [x] 7.6 Load and store reference frames and audio
- [x] 7.7 Update UI to "Reference ready" state

## 8. Integration and Testing

- [ ] 8.1 End-to-end test: text entry → reference generation → student recording → side-by-side playback
- [ ] 8.2 Test cache hit response time (<100ms)
- [ ] 8.3 Test cache miss generation time (<2s)
- [ ] 8.4 Test scrubbing updates both animations
- [ ] 8.5 Test speed control affects playback rate
- [ ] 8.6 Test zoom control affects timeline precision
- [ ] 8.7 Test loop region repeats correctly
- [ ] 8.8 Test link/unlink playheads modes
- [ ] 8.9 Test audio compression format support across browsers
- [ ] 8.10 Test memory usage with 3-5 minute utterances

## 9. Documentation

- [ ] 9.1 Document TTS provider interface for future swaps
- [ ] 9.2 Document cache configuration options
- [ ] 9.3 Document frame sequence format
- [ ] 9.4 Document comparison playback API
- [ ] 9.5 Add usage guide for Comparison Lab tab
- [ ] 9.6 Document audio compression and downsampling pipeline

## 10. Performance Optimization (Future)

- [ ] 10.1 Consider frame decimation (25Hz vs 50Hz) if payload too large
- [ ] 10.2 Consider streaming audio if memory constrained
- [ ] 10.3 Consider Web Worker for trajectory processing
- [ ] 10.4 Consider GPU-accelerated audio decoding
- [ ] 10.5 Profile and optimize if needed after initial deployment
