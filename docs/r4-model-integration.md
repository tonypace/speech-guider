# R4 final with hinting integration

Analysis and Comparison Lab share local ContentVec-L7, extended R4 (update
15,500), the coupled Model A tongue-contact head, lip closure correction, and
reviewed recording-replay silence settling. The default bundle is
`external/R4 final with hinting models/`. No model downloads occur at runtime.

## Assets and configuration

Keep these supplied files together; `external/` remains ignored by Git:

```text
configs/nine_channel_v12_100ms.yaml
configs/output_calibration.json
configs/silence_reviewed.json
configs/silence_expanded.json
weights/r4.pt
weights/contact.pt
weights/lip.json
weights/dental.json
weights/labiodental.json
weights/silence.joblib
weights/contentvec/{config.json,preprocessor_config.json,model.safetensors}
CONTENTVEC_STATE_SHA256
SHA256SUMS
silence_fit.json
```

`SSL_AAI_BUNDLE_PATH` overrides the bundle directory. `SSL_AAI_CHECKPOINT_PATH`
overrides only the decoder checkpoint; the coupled contact head still requires
its exact matching base weights. New checkouts need the local assets copied
separately. The installer stages the final hint assets and their checksum
manifest. Its default source is the same final bundle.

The Settings **Enhance articulatory animation** checkbox gates all hint branches.
It defaults on; turning it off selects baseline R4. Existing saved settings are
preserved. Startup environment options (also in `.env.sample`):

| Variable | Default | Behavior |
| --- | --- | --- |
| `SSL_AAI_LIP_ENABLED` | `1` | Set `0` for tongue contact without lip correction. |
| `SSL_AAI_CALIBRATE_ENABLED` | `1` | Set `0` to disable conditional `TTCL`/`TBCL`/`LP` output calibration. |
| `SSL_AAI_LABIODENTAL_ENABLED` | `1` | Set `0` to disable `/f, v/` lower-lip retraction (`labiodental_retraction`). |
| `SSL_AAI_DENTAL_ENABLED` | `0` | Set `1` for experimental dental / “th” correction. |
| `SSL_AAI_SILENCE_MODE` | `reviewed` | `reviewed`, `expanded`, or `off`. |

Restart the backend after changing assets or environment options. Model loading
is lazy and cached. Reference cache identities include hint options and all hint
asset/config revisions. Explicitly selected older bundles without hint assets
retain contact-only compatibility.

Install `requirements.txt` into the project environment. The silence classifier
requires its supplied **scikit-learn 1.9.0** serialization version; the loader
rejects a version mismatch. Release checksums are checked before unpickling the
local classifier and before loading hint configuration. Lip loading also checks
encoder identity and the streaming contract.

## Inference and timing

- Input: mono float32, 16 kHz; upload and TTS preprocessing resample as needed.
- Encoder: local seven-layer ContentVec, width 768, 59 feature rows per window.
- Replay: 19,200-sample window, 1,600-sample hop, 1,600-sample lookahead.
- Commit slice: `[49:54]`, five frames per packet, 50 Hz.
- Output order: `LP LA TTCL TTCD TBCL TBCD VEL GLO LAT`.
- Centers: `160 + 320 * frame_index`. The final partial hop and lookahead are
  padded, then **centers at or beyond source length are discarded**, matching the
  final bundle. Clips of 160 samples or fewer have no valid frame center.
- Each clip creates fresh rolling audio, tongue tracking, and lip motion state.
  Loading and inference remain locked.

Contact adjusts the four tongue channels first. Lip and optional dental
readouts use the committed **unscaled** ContentVec rows. Lip correction changes
aperture; dental correction changes tip place and degree while preserving tongue
holds and lip seals. Silence settling follows packet replay, on the same frame
clock; its onset guard and blend respect the reference's lookahead policy.
This integration analyzes completed recordings, with no live streaming or Core ML
qualification implied.

Raw oral values retain speaker-Z bounds `[-0.1, 1.1]`; VEL/GLO/LAT are sigmoid
outputs. Only the separate display tensor is clamped to `[0, 1]`, then mapped to
the canonical renderer fields. Metadata reports actual contact, lip, dental and
silence modes, settled frame count, and display clipping fraction.
The supplied renderer's palate and throat geometry already matches the app;
the app retains its anatomy labels and frame-render optimizations.

Dental correction remains experimental, awaiting blind review and validation
on a second speaker. Expanded silence coverage is optional. See the supplied
`IMPLEMENTATION_NOTES.md` for provenance and review limits.

## Verification and device selection

```bash
source speech-guider/bin/activate
pytest tests/test_r4_predictor.py tests/test_r4_hints.py tests/test_ssl_aai_predictor.py
npm run check
```

Integration tests compare raw output and timestamps against the unmodified final
bundle, including tongue/lip corrections, dental correction, both silence gates,
long pauses, speech recovery, partial tails and fresh-clip resets. Deterministic
tests cover lip motion, dental precedence, checksum rejection, cache identity and
installer staging. Model-dependent tests skip when local assets are absent.

Device preference is Apple MPS, then CUDA, then CPU. The execution sandbox can
hide GPU access; launch normally from Terminal for MPS:

```bash
python -m app.main
```

The inference ports retain the supplied CC BY-NC 4.0 terms in
[r4-LICENSE.txt](r4-LICENSE.txt). Decoder/contact architecture is unchanged from
the previous frozen R4 integration; hint math follows the final bundle's
`aai_streaming/{lip_closure,dental_correction,silence_hint}.py`.
