# Low-Latency Streaming Implementation Plan

Status: **IN PROGRESS — R4 REVIEW PACKET READY; M4/CORE ML/LIVE CAPTURE QUALIFICATION PENDING**

Planning update, 2026-09-19: Stage 7's R4 training and diagnostic packet are
implemented; review and field qualification remain open. Use
[future_plans.md](future_plans.md) for implementation order and
[streaming_successor_training_plan.md](streaming_successor_training_plan.md)
for the training results. The original rolling V1.2 quality failure below is
historical, not an instruction to restart Stage 1.

Date: 2026-08-14

## Objective

Reduce local speech-to-animation latency by replacing full-utterance inference
with rolling on-device inference. The primary deployment target is the A18 Pro
MacBook Neo through Core ML. An M4 Mac is the available development proxy; it
is not performance-equivalent target hardware.

This is not a remote-streaming project. The microphone, model, trajectory queue,
and renderer remain on the same device.

## Fixed first target

| Item | Contract |
| :--- | :--- |
| Model | Nine-channel V1.2 release candidate |
| Checkpoint | `checkpoints/experiment_phase2/nine_channel_v12/lat_temporal_seed13/best_LAT.full.pt` |
| Audio | Mono float, 16 kHz |
| Hop | 1,600 samples / 100 ms |
| Rolling window | 19,200 samples / 1.2 s |
| Lookahead | 100 ms |
| Feature layer | ContentVec hidden state 7 |
| Feature shape | `1 x 59 x 768` for a 1.2 s window |
| Committed output | Five 50-Hz frames per hop |
| Working slice | Feature/trajectory frames `[49:54]`; frames `[54:59]` are lookahead |
| Startup | Left-pad the rolling window with silence; first output after 200 ms of captured audio |
| Precision | FP32 reference; FP16 Core ML deployment |
| Deployment | Local Core ML `mlprogram`, `ComputeUnit.ALL` |

The first target excludes contact inference, V6, global low-pass filtering, and
whole-utterance `tongue_silence_v3`. These are later, conditional stages.

## Latency budget

Steady-state latency consists of lookahead, hop alignment, inference, and frame
scheduling. A 100 ms lookahead does not imply 100 ms total latency.

| Component | Target |
| :--- | ---: |
| Intentional lookahead | 100 ms |
| Hop alignment | 0–100 ms; approximately 50 ms average |
| Warm inference, P50 | `< 60 ms` |
| Warm inference, P95 | `< 80 ms` |
| Warm inference, P99 | `< 95 ms` |
| Renderer scheduling | `< 16 ms` |
| Expected steady-state perceived latency | approximately 170–250 ms |

Inference taking 100 ms per 100 ms hop is a failure: it leaves no margin for
OS scheduling, concurrent applications, or thermal throttling. The runtime must
never build a growing queue.

## Stage 0 — Freeze contracts and fixtures

1. Add a versioned streaming configuration containing the fixed values above.
2. Select 20–30 non-sealed validation recordings: ordinary speech first, fast
   speech as a separate stress subset, plus silence and clipped-audio fixtures.
3. Save the exact offline V1.2 outputs and ContentVec-7 features for those files.
4. Freeze waveform normalization to exactly match the current Hugging Face
   feature extractor. Do not allow the Swift and Python implementations to
   choose different variance conventions or epsilon values.
5. Define timestamps in audio-sample coordinates. Derive trajectory timestamps
   from sample positions; do not advance them from wall-clock callback counts.

Deliverables:

- `configs/streaming/nine_channel_v12_100ms.yaml`
- `data/evaluation/streaming_v1/fixture_manifest.json`
- reference feature and trajectory hashes

Gate: repeated offline inference is bit-stable in FP32 and every fixture has an
unambiguous audio-sample-to-trajectory-frame mapping.

## Stage 1 — Build the rolling PyTorch reference

Implement a deterministic file-replay runtime before microphone capture:

1. Initialize a 19,200-sample ring buffer with silence.
2. Append 1,600 samples per step and discard the oldest 1,600 samples.
3. Normalize the full current window.
4. Recompute truncated ContentVec through layer 7.
5. Run the strict V1.2 checkpoint without the unused domain-classifier result.
6. Commit only output frames `[49:54]`.
7. Attach absolute audio-sample timestamps to all five frames.
8. Concatenate committed frames without smoothing or seam repair.

Proposed modules:

- `aai_streaming/contracts.py`
- `aai_streaming/audio_window.py`
- `aai_streaming/pytorch_runtime.py`
- `scripts/evaluate_streaming_replay.py`

The replay report must include per-channel rolling-versus-offline MAE, PCC,
GLO/LAT threshold disagreement, chunk-boundary position/velocity jumps, and
startup versus steady-state results. This is a compact diagnostic, not a new
sealed-test audit.

Initial quality targets:

- oral-channel rolling-versus-offline MAE `<= 0.05`;
- no fixed one-frame alignment error;
- streaming boundary-jump P95 `<= 1.5x` the offline boundary-jump P95;
- no normalized boundary jump above `0.10` without a corresponding offline
  movement; and
- no repeated freeze, reversal, or discontinuity obvious in a short synchronized
  visual review.

Gate: the raw 100 ms-lookahead output is usable enough to justify deployment
work. If oral MAE exceeds `0.08` or seams are severe, skip to Stage 7 rather than
hiding the failure with smoothing.

## Stage 2 — Establish the M4 PyTorch MPS proxy

Run the Stage 1 replay unchanged on the available M4 Mac:

1. Load ContentVec on CPU, remove encoder layers 8–12, then transfer the
   truncated model to `mps`.
2. Keep waveform, ContentVec, decoder state, and output tensors on MPS.
3. Use `torch.inference_mode()` and a persistent model instance.
4. Record cold load, first prediction, warm P50/P95/P99, resident memory, and a
   ten-minute sustained run.
5. Report missed deadlines and maximum queue depth; averages alone are
   insufficient.
6. Record the exact Mac model, chip, memory, macOS, PyTorch, and Transformers
   versions with every result.
7. Add scheduler tests that inject 60, 80, 100, and 120 ms inference delays.
   These test backpressure and missed-hop recovery, not A18 performance.

This stage is a baseline, not the final deployment. MPS uses the GPU rather than
the Neural Engine. There is no reliable way to simulate A18 Pro GPU throughput,
Neural Engine placement, 60 GB/s memory bandwidth, or fanless sustained behavior
on an M4. Do not scale M4 timings into claimed Neo timings. Interpret M4 MPS
results only as a functional baseline and an indication of where time is spent.

Gate: CPU/MPS outputs agree within the rolling-reference tolerance, the M4 run
is reproducible, scheduler recovery passes all injected-delay cases, and the
benchmark is packaged so it can later run unchanged on an A18 Pro Neo.

## Stage 3 — Prepare deployment-only PyTorch graphs

Create two inference wrappers:

### ContentVec-L7 wrapper

- input: normalized `1 x 19,200` waveform;
- force eager attention rather than fused PyTorch SDPA;
- remove encoder layers above layer 7 before tracing;
- return a plain `1 x 59 x 768` tensor;
- eliminate Hugging Face output containers and unused hidden states; and
- fold/remove weight-normalization parametrizations if Core ML cannot lower
  the positional convolution directly.

### V1.2 wrapper

- input: `1 x 59 x 768` ContentVec features;
- execute only the temporal predictor, oral projection, and VEL/GLO/LAT head;
- omit the training-only domain classifier and unused auxiliary outputs; and
- initially return all 59 frames, then add a verified `[49:54]` deployment
  slice.

Trace each fixed-shape wrapper with `torch.jit.trace`, freeze it, and compare it
with eager PyTorch. Wrapper refactoring must have FP32 MAE below `1e-6` before
Core ML conversion begins.

Deliverables:

- `aai_streaming/coreml_wrappers.py`
- `scripts/export_streaming_coreml.py`
- frozen TorchScript intermediates with source-checkpoint hashes

Gate: eager and traced PyTorch outputs match, including the committed frame
indices.

## Stage 4 — Convert and validate Core ML FP16

Convert the wrappers separately first:

1. Use a pinned Core ML Tools environment and the `mlprogram` format.
2. Set a minimum deployment target of macOS 15 or newer.
3. Use fixed input shapes, FP16 compute, and `ComputeUnit.ALL`.
4. Keep waveform input FP32 for the first parity run; use FP16 feature I/O
   between the two models to avoid unnecessary casts.
5. Save versioned `.mlpackage` artifacts with checkpoint, wrapper, converter,
   precision, and normalization metadata.
6. On macOS, compare Core ML with traced PyTorch on every Stage 0 fixture.

Conversion-parity gates:

- oral-channel Core-ML-versus-PyTorch MAE `< 0.01`;
- aggregate PCC change `< 0.005`;
- no systematic frame shift;
- GLO/LAT threshold disagreement `< 2%` of frames; and
- no nonfinite output or unsupported-shape fallback.

On the M4, inspect the compiled Core ML compute plan and benchmark three
policies:

- all compute units;
- CPU plus Neural Engine; and
- CPU plus GPU.

Do not assume Neural Engine use from successful conversion. Record per-operation
placement and identify CPU fallbacks, especially attention, normalization, and
positional convolution. Device placement and relative cost may change on the
A18 Pro, so the M4 compute plan is diagnostic rather than target qualification.

Proxy gate: FP16 parity passes and M4 warm P95 is below 60 ms, with below 40 ms
preferred as headroom for the lower-bandwidth target. This is a risk screen, not
an A18 performance claim. If separate models miss the proxy gate mainly through
copies or dispatch, fuse the wrappers into one waveform-to-five-frame model and
repeat parity before considering quantization. Produce a one-command compiled
Core ML benchmark for eventual execution on the Neo.

## Stage 5 — Integrate local live capture and rendering

Implement the client loop in process; do not add sockets or a service boundary:

1. Capture mono audio with `AVAudioEngine`.
2. Resample once to 16 kHz and append samples to the ring buffer.
3. Schedule one asynchronous Core ML prediction per 1,600 new samples.
4. Permit only one prediction in flight. Record and recover from a missed hop
   rather than queueing unbounded work.
5. Pass five timestamped nine-channel frames to a bounded renderer queue.
6. Interpolate at display refresh rate using the audio sample clock.
7. Expose diagnostic counters: inference duration, missed hops, queue depth,
   underruns, and current end-to-end lag.
8. Reset model/window state explicitly on device changes, interruption, and
   end-of-stream.

The renderer consumes the existing channel order:

`LP, LA, TTCL, TTCD, TBCL, TBCD, VEL, GLO, LAT`.

Proxy gate: ten minutes of live use on the M4 without growing backlog, dropped
trajectory batches, timestamp drift, or memory growth, plus correct recovery in
the injected-delay tests from Stage 2. Target resident memory is below 1.5 GB;
2 GB is a hard investigation threshold because the eventual Neo has 8 GB.

## Stage 6 — Add causal silence behavior

Do not call whole-utterance `tongue_silence_v3` on each rolling window. Implement
a stateful display postprocessor with:

- rolling energy calibration;
- persistent threshold hysteresis;
- 120 ms minimum-silence confirmation;
- a short causal raised-cosine transition;
- anchors derived only from committed past frames; and
- explicit end-of-stream handling for final silence.

Lip, VEL, GLO, and LAT channels remain unchanged. The postprocessor may settle
the tongue but must not hold an arbitrary last speech frame indefinitely.

Gate: silence transitions show settle/move/settle behavior without suppressing
low-energy consonants or adding more than one hop of new delay.

## Stage 7 — Conditional quality or performance work

Enter this stage only when a prior gate identifies a specific failure.

### If rolling quality is inadequate

Train a streaming-compatible V1.2 successor:

1. Generate training examples with random rolling-window boundaries.
2. Preserve the 100 ms lookahead contract during training.
3. Replace centered decoder padding with explicit bounded-lookahead/asymmetric
   padding, or train with the exact truncated boundary seen at inference.
4. Distill toward the offline V1.2 outputs while retaining supervised trajectory
   loss.
5. Evaluate 100 ms against a 200 ms-lookahead quality fallback.

The concrete implementation, ablation, measurement, and promotion gates are in
`DOCS/streaming_successor_training_plan.md`. That plan permits a clearly labeled
research artifact to proceed through M4 measurement and experimental Core ML
conversion under relaxed, R0-relative admission limits so streaming can be
compared perceptually with offline V1.2 in the field. This does not satisfy the
development-candidate completion criteria below.

### If Core ML misses the latency gate

Apply optimizations in this order:

1. fuse ContentVec and V1.2;
2. remove CPU fallbacks and redundant casts;
3. retain only the committed output slice;
4. try Core ML weight-only 8-bit compression; and
5. only then test calibrated weight-and-activation INT8.

Every optimization must repeat the Stage 4 parity gates. INT8 is not admitted
solely because the model is smaller.

### Contact and V6

Do not add the 18-head contact ensemble or V6 to the default streaming path.
Consider them only if the base pipeline has at least 20 ms of P95 inference
headroom. V6 additionally requires retraining without utterance-normalized
`-1..+1` position and with a bounded-lookahead temporal contract; the unchanged
artifact is not valid for indefinite streaming.

## Development-candidate completion criteria

The implementation is ready for target-hardware qualification when:

1. The exact model, normalization, window, lookahead, and frame-slice contracts
   are versioned and reproducible.
2. Core ML FP16 passes conversion parity against PyTorch.
3. M4 proxy P95 inference is below 60 ms and P99 below 80 ms; below 40 ms P95
   is preferred.
4. Ten minutes of M4 live inference produces no backlog or timestamp drift, and
   injected 60–120 ms delays recover without unbounded queueing.
5. Expected steady-state perceived latency is 170–250 ms and is shown in client
   diagnostics as a target estimate rather than described as “100 ms latency.”
6. The compact replay and visual checks show no severe closure, seam, startup,
   or silence failure.
7. The client can fall back cleanly to offline V1.2 inference.

## Deferred A18 Pro qualification

The development candidate is not target-qualified until the same packaged
benchmark and live loop run on an A18 Pro MacBook Neo. Final gates are:

- warm inference P95 `< 80 ms` and P99 `< 95 ms`;
- ten minutes without backlog, timestamp drift, or material thermal slowdown;
- resident memory below 1.5 GB; and
- parity and short visual checks unchanged from the M4 candidate.

Until these pass, report M4 measurements directly and label Neo latency as
unmeasured. Do not publish a scaled or simulated A18 estimate as a measurement.

## Related records

- `DOCS/STREAMING_SPEECH_TO_AVATAR_REVIEW.md`
- `DOCS/release_candidates/NINE_CHANNEL_V12_IMPLEMENTATION.md`
- `DOCS/release_candidates/client_documentation.md`
- `DOCS/CONTACT_AUGMENTATION_CLIENT_EXPERIMENT.md`
