## Why

The current pronunciation evaluation workflow focuses on automatically detecting phoneme errors. However, for teaching purposes, it's more valuable to show students directly what articulatory movements they should be making versus what they actually produced.

We need a new comparison mode where:
1. A reference pronunciation is generated from target text and analyzed via the SSL AAI predictor
2. The student's actual pronunciation is recorded and analyzed via the same predictor
3. Both articulatory trajectories can be played back side-by-side with audio editing-style controls (scrub, speed, zoom, loop)
4. Teachers and students can visually compare the moments where articulation diverges

This moves the system from "detect and report errors" to "demonstrate correct vs actual movement".

## What Changes

- Add reference audio generation from text using espeak-ng (first provider, swappable later)
- Add backend pipeline to synthesize reference audio → SSL AAI predictor → canonical animation frames
- Add student audio → SSL AAI predictor → canonical animation frames (reusing existing path)
- Add new API endpoint for reference generation with caching by text content
- Add backend service for audio downsampling and compressed audio storage for responsive playback
- Add trajectory comparison data format: per-frame canonical animation states with synchronized audio handles
- Add new frontend comparison controller module to manage two timelines (reference + student)
- Add side-by-side articulatory animation view with synchronized or independent playback
- Add audio editing controls: play/pause, scrub timeline, variable speed (0.25x-1.25x), zoom window, loop region
- Add debounced reference generation when target text is entered (500-800ms delay)
- Add audio compression and downsampling pipeline to manage memory for per-frame payloads

## Capabilities

### New Capabilities
- `ssl-comparison-playback`: Generate and compare student vs reference articulatory trajectories with synchronized playback controls

### Modified Capabilities
- `ssl-based-animation`: Expanded from single-pose generation to full trajectory playback
- `articulatory-tongue-geometry`: Used for both reference and student trajectories in comparison mode

## Impact

- New backend endpoint `/api/reference-animation` for on-demand reference generation
- New backend service `src/audio/reference_tts.py` for text-to-speech (espeak-ng provider, swappable)
- New backend module `src/services/comparison_cache.py` for caching reference assets by text
- Modified `app/api/analyze.py` to emit trajectory data not just representative poses
- New frontend module `static/js/ssl_comparison_controller.js` for comparison playback management
- New UI section "Comparison Lab" tab with side-by-side animations and timeline controls
- Audio compression and downsampling pipeline for efficient in-memory storage
- Full per-frame payloads with downsampling to match SSL frame rate (50Hz)

## Notes on Audio Compression and Downsampling

The SSL predictor outputs frames at 50Hz from 16kHz audio. To enable responsive playback:
- Downsample audio to a lower rate (e.g., 8kHz or 4kHz) suitable for articulatory comparison
- Use compressed audio formats (compressed WAV or WebM) for in-memory storage
- Backend prepares ready-to-use canonical frame sequences, not raw z-scored TVs
- Frontend receives compressed audio blobs + frame arrays, handles playback synchronization
- Downsampling to SSL frame rate helps align audio and animation frames efficiently