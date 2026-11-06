# Audio, model, and cache review

## Scope and preservation

Reviewed `src/` boundaries, model inference contracts, audio extraction, adapters, cache ownership, and associated existing tests. Existing uncommitted R4 integration (`ssl_aai_predictor`, `aai_adapter`, `model_cache`, decoder additions, and existing model tests) remains intact. No checkpoint layout, trained weights, normalization policy, temporal window, phoneme templates, or acoustic formula was changed.

## Fixed findings

- **Waveform sample axis:** `AudioContext.get_downsampled_tensor()` selected `values[:, 0]` from Praat's `(channels, samples)` array, returning one value for mono recordings. Select the first channel's complete sample vector, including after resampling. New generated-waveform tests assert 16,000 samples and meaningful signal variance for both 16 kHz and 24 kHz input.
- **Cache instance isolation:** deterministic audio filenames let separate caches overwrite or delete each other's same-text audio. Per-instance UUID namespaces isolate ownership while retaining deterministic filenames within an instance.
- **Failed cache replacement:** failed disk writes retained the old backing-file mapping, allowing a subsequent hit to reload old audio. Remove the old entry/backing file before publishing the new in-memory fallback.
- **Explicit TTL:** `0` previously selected the default TTL through truthiness. Only `None` selects the default now. Nonpositive capacities now fail explicitly instead of silently exceeding capacity.
- **Observability:** cache disk failures use structured logger warnings with exception context, limited to filesystem errors. Cache payload annotations specify dictionary element types.
- **Compatibility cleanup:** legacy camelCase dataclass names carry local documented lint exceptions because they define serialized animation fields. Local delta variables use snake_case. Removed nonexistent test-function invocation from the manual test runner.
- **Static typing:** explicit casts at untyped library boundaries and integer conversions for NumPy search indices resolve intrinsic mypy errors without changing signal processing.

## Module inventory

| Modules | Review outcome |
| --- | --- |
| `audio/processor.py` | Fixed sample axis; inspected pitch, nPVI, stress and voice-quality paths. Acoustic formulas retained. |
| `audio/prosody_lab.py` | Inspected file normalization, short/empty-waveform handling, energy/pitch and pause fallbacks. Return annotations corrected; no algorithm change. |
| `audio/reference_tts.py` | Inspected required-file checks, subprocess argument handling, timeout/nonzero exits, WAV cleanup, mono conversion, resampling and OGG encoding. Only boundary typing changed. |
| `models/ssl_aai_predictor.py` | Inspected local-only bundle loading, validated fixed-window contract, inference lock/mode, raw/display outputs and cleanup. Existing R4 changes retained. |
| `models/r4_decoder.py` | Inspected strict checkpoint/config checks, asymmetric temporal convolution and extension heads. No added finding requiring safe refactor. |
| `models/bigru_decoder.py` | Inspected checkpoint path, architecture and display bounds; retained successor-independent compatibility implementation. |
| `models/legacy_aai_predictor.py` | Inspected archived loading/inference/cleanup boundary. Tensor return cast only. |
| `models/ssl_common.py` | Inspected device selection/cache release, feature config/extractor and hidden-state selection. Added missing argument type and boundary cast. |
| `models/aai_adapter.py` | Inspected channel order, metadata/profile handling, batch conversion and raw/canonical mapping. Existing integration changes retained. |
| `models/articulatory.py` | Inspected template/pyclts fallback, normalization, parameter deltas and serialization. Naming cleanup preserves wire contract. |
| `models/articulatory_calibration.py` | Inspected identity/gamma/piecewise calibration and defaults. No behavior change warranted. |
| `models/alignment.py` | Confirmed explicit nonfunctional forced-alignment placeholder; no phoneme-model behavior invented. |
| `services/model_cache.py` | Confirmed lock-protected singleton only publishes successfully loaded predictor; current integration retained. |
| `services/comparison_cache.py` | Fixed ownership, stale replacement and TTL findings above; LRU/statistics behavior retained. |
| `__init__.py`, `audio/__init__.py`, `models/__init__.py`, `llm/__init__.py` | Inspected package exports and LLM placeholder. No change warranted. |

## Validation and limits

- Model/audio/articulatory targeted suite: **87 passed, 3 skipped** (existing asset-dependent skips).
- Cache/TTS errors plus new cache regressions: **20 passed**.
- Waveform regression plus processor/prosody suites after typing cleanup: **13 passed**.
- Ruff: all `src/` and touched/new tests pass.
- Mypy: intrinsic source errors resolved; missing third-party stubs require the repository-level targeted configuration handled separately.

These are unit/regression checks, not perceptual or scientific validation of model quality. Tests do not establish pronunciation accuracy or equivalence against a real recorded evaluation corpus.

## Deferred issues

- Forced alignment and pronunciation error detection remain placeholders pending a real phoneme CTC model. Empty error lists are not evidence of correct pronunciation.
- Comparison cache has no synchronization across concurrent API worker threads, and cached assets are mutable. Full atomic synchronization and copy/immutability policy need an explicit concurrency design; a superficial lock around only one method would not establish safe ownership for returned objects.
- Cache reads refill `audio_bytes` on the stored object, retaining bytes in memory after the first hit despite temporary-file mode's memory-pressure goal. Fix needs a deliberate response/ownership policy.
- Voice-quality CPPS/spectral tilt are heuristic implementations; scientific changes require reference Praat fixtures and method-specific validation, outside behavior-preserving cleanup.
- Device priority currently prefers CUDA before MPS; ordinary Apple Silicon machines use MPS, but this differs from the guideline's literal MPS-first priority on hypothetical dual-backend hosts. Retained existing behavior.
- Several legacy/model diagnostic paths still print and catch broad exceptions; converting all fallbacks safely requires explicit expected exception contracts and additional failure fixtures.
- Full real-asset end-to-end inference, TTS binary integration and hardware-memory profiling remain distinct from these deterministic unit checks.
