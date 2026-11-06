# Backend review

Reviewed every Python source module under `app/`: `main`, API routers (`analyze`,
`comparison`, `errors`, `presets`, `prosody_lab`, `sse`), request/response schemas,
state/concurrency services, audio utilities, and package initializers. Existing
working-tree R4 integration changes in analyze/comparison were preserved.

## Implemented

- Upload and reference SSL paths duplicated soundfile decoding, channel averaging,
  Fourier resampling, and float tensor construction. Both now delegate to
  `load_audio_tensor`, retaining the existing sample-count truncation and 16 kHz
  configuration. Thin endpoint helpers remain compatible with existing callers
  and mocks.
- Busy analysis rejection leaked the already-created coroutine, producing an
  unawaited-coroutine warning and retaining its frame. The rejected coroutine is
  now closed before the existing HTTP 503 response. Active-operation cleanup and
  busy status remain unchanged.
- Failed/timed-out ffmpeg conversions left partial WAV outputs behind. Conversion
  now cleans those outputs on every failure while retaining the original input
  for the existing supported-format fallback.
- Replaced custom wrapper around private Starlette `_TemplateResponse` with public
  `Jinja2Templates(env=...)`. Kept Jinja autoescaping, cache disablement, context,
  and response behavior. Project root is explicitly resolved.
- Fixed schema import ordering and explicitly constructed error-selection response
  so static typing does not infer an incompatible heterogeneous unpacked dict.

## Deferred findings

These affect contracts or require wider coordination, so this refactor does not
silently change them:

- `analyze` runs `AudioContext` construction and complete Praat prosody extraction
  synchronously; reference generation and Prosody Lab also perform blocking work
  directly in async endpoints. Moving operations to workers requires cancellation
  ownership: canceling `to_thread` does not stop its worker, so input deletion and
  the ML concurrency slot must remain owned until work actually finishes.
- Only primary analysis uses the ML concurrency gate; reference inference can
  overlap it. Gate is process-local and does not coordinate multiple workers.
- SSE queue creation depends on subscribers arriving first; producer drops updates
  without a queue. Main analysis creates a job ID internally without returning it
  before work, so clients cannot discover that job in time. Queue lifecycle and
  multiple subscribers need a defined job/subscription protocol.
- Preset file path depends on working directory. Writes are neither atomic nor
  protected against concurrent read-modify-write; malformed JSON shapes are not
  validated. Persisted-location migration and recovery policy need agreement.
- Error-selection descriptions interpolate client-supplied phonemes into HTML;
  consumers using `innerHTML` need escaping or text-node rendering.
- Analyze failures expose tracebacks to clients, while successful fallback feedback
  still claims articulatory analysis even when SSL failed. Response/error UX
  policy should distinguish diagnostic detail from public feedback.
- Reference cache keys use text alone despite accepting a TTS provider argument;
  provider changes can reuse another provider's audio. Cache-key versioning belongs
  with cache implementation and integration tests.
- `_get_pitch_range_label` names its input semitones, but callers pass `f0_range`
  in Hz. Coaching thresholds therefore need domain validation before changing.
- Uploads are read fully into memory, and ffmpeg conversion runs synchronously.
  Upload bounds and streaming should be coordinated with frontend expectations.

## Validation

Focused backend suite covers generated stereo waveform resampling, rejected
coroutine closure, partial output cleanup on ffmpeg error/timeout, public-template
rendering, existing analysis failure modes, comparison frames, error fallback,
Prosody Lab, and audio upload failure behavior. No model downloads required.
