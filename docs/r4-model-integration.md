# Frozen R4 integration

Both `/api/analyze` and `/api/reference-animation` now use the frozen R4
`bounded_v12` successor. The application does not merge the old MLP and
Haskins BiGRU outputs or fall back to those models when R4 fails.

## Local assets

Keep the evaluation bundle at `external/R4 26-11-06/`, containing:

```text
configs/nine_channel_v12_100ms.yaml
weights/r4.pt
weights/contentvec/config.json
weights/contentvec/preprocessor_config.json
weights/contentvec/model.safetensors
```

`external/` is ignored by Git. New checkouts need these assets copied separately.
No Hugging Face download occurs during R4 loading. Do not substitute the original
base checkpoint named in the YAML: that field records training provenance.

To move the bundle, set `SSL_AAI_BUNDLE_PATH` to its absolute directory. Optionally
set `SSL_AAI_CHECKPOINT_PATH` to another compatible R4 successor checkpoint;
this does not change the bundle used for the encoder or streaming contract.
Legacy checkpoints are rejected. Loading validates the declared architecture,
channel order, lookahead allocation, local encoder shape, streaming policy,
and every decoder state-dict key and tensor shape.

## Inference contract

- Audio: mono float32, 16 kHz. Existing upload/TTS preprocessing performs resampling.
- Encoder: bundled seven-layer ContentVec, last hidden state, width 768.
- Decoder: learned feature scale, four asymmetric residual convolutions,
  nine-channel projection, and the V1.2 temporal VEL/GLO/LAT extension head.
- Replay: 19,200-sample windows, 1,600-sample hops, 1,600-sample lookahead.
- Each window yields 59 feature frames; indices `49:54` are committed.
- Output: 50 Hz, ordered `LP, LA, TTCL, TTCD, TBCL, TBCD, VEL, GLO, LAT`.
- The uploaded-clip adapter pads the final partial hop and flushes one extra
  silence hop. It returns `ceil(audio_samples / 320)` frames, trimming padding.
- Frame centers follow the bundle's sample clock: `160 + frame_index * 320`.
  Existing browser playback uses the corresponding uniform 50 Hz frame grid.
- Each clip starts with a fresh rolling buffer. Model loading and inference are
  locked so concurrent requests cannot share partial initialization or device work.

Raw oral outputs retain speaker-Z normalized values in `[-0.1, 1.1]`;
VEL/GLO/LAT use sigmoid outputs. The adapter clamps a separate display tensor
to `[0, 1]` and passes it directly into the existing canonical renderer mapping.
It never inverts speaker-specific training statistics. `clip_fraction` reports
values changed at this display boundary; old BiGRU confidence thresholds are
not used to claim R4 confidence.

The baseline bundle policy remains active: **contact augmentation disabled**.
The optional `contact.pt` decoder, review renderer contact exaggeration, tongue
location compression, and deferred silence stabilization are not applied. They
change model/display behavior and require separate qualification. R4 animation
remains an audio-based estimate, not a measured contact trace.

The application still analyzes uploaded recordings; using the bounded model
does not add live microphone streaming or Core ML deployment.

## Device selection and verification

The existing device helper selects CUDA when present, otherwise Apple MPS,
otherwise CPU. Native arm64 Python and the existing PyTorch MPS build are
sufficient on this Mac. The Codex execution sandbox hides GPU access; the same
virtual environment reports MPS available and can run GPU inference outside
that sandbox. Start the app normally from Terminal to access MPS:

```bash
source speech-guider/bin/activate
python -m app.main
```

Check device visibility in the same environment used to launch the backend:

```bash
python -c 'import torch; print(torch.backends.mps.is_built(), torch.backends.mps.is_available())'
```

Existing pinned app dependencies load this bundle; the evaluation kit's newer
benchmark environment is not required by this inference port. Focused checks:

```bash
python -m pytest tests/test_r4_predictor.py tests/test_ssl_aai_predictor.py
```

The integration test compares raw outputs and timestamps with the unmodified
bundled decoder and replay scheduler, including partial tails and silence.
Without local model assets, the model-dependent tests skip; deterministic
boundary and API-consistency tests still run.

## Source and terms

The inference port in `src/models/r4_decoder.py` follows the bundle's
`models.py` and `aai_streaming/bounded_model.py`, source revision
`cb2f2f15c6445cfddb69d791debf1f5923fc40f2`. Changes remove training execution,
preserve saved training-head parameters for strict loading, and expose only the
trajectory tensor. The bundle's CC BY-NC 4.0 license is retained in
[r4-LICENSE.txt](r4-LICENSE.txt). Model assets retain their supplied terms.

The previous integration remains in `src/models/legacy_aai_predictor.py` for
explicit legacy use and historical regression checks. It is not the app's
runtime fallback. Legacy checkpoint bundles and research data were moved into
`archive/2026-11-06/backup/`; restore their original paths to run historical
checkpoint-dependent tests. See [workspace archive](workspace-archive.md).
