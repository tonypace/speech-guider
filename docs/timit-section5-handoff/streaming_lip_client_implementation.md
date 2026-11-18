# Live client implementation for Model A lip correction

Status, 2026-11-16. The optional PyTorch reference is implemented and
verified. The hosted comparison has positive playback feedback. The macOS
client, Core ML parity and device timing are pending. Use the accepted
correction for the first client port. [Reference and review](streaming_lip_reference_replay_2026-11-13.md#model-a-integration)

## Dependencies

- Use extended R4 with the coupled contact head and the committed-frame
  tongue tracker. Start from the same R4, contact and ContentVec checkpoints
  as the [Model A replay command](../scripts/replay_model_a.py). Restore the
  local weight bundle before generating fixtures.
- Use the 100 ms deployment stages for graph export, Core ML conversion,
  and the single-inference live loop. The existing wrappers in the plan
  describe the V1.2 base. Export Model A's actual outputs for this work.
  [Streaming implementation plan](streaming_implementation_plan.md#stage-3--prepare-deployment-only-pytorch-graphs)
- Bundle the versioned lip config with the matching exported model. Record
  the config hash, ContentVec parameter hash, base and contact checkpoint
  hashes, channel order and sample clock in the client build manifest.
  [Frozen lip config](../configs/streaming/model_a_lip_correction_v1.json) ·
  [100 ms contract](../configs/streaming/nine_channel_v12_100ms.yaml)

## Integrate in the packet producer

1. Export the 59 by 768 ContentVec L7 feature window with the reference
   window normalization. Export the R4 trajectory and coupled contact-head
   outputs. Run the committed-frame tongue tracker and trajectory realization
   on the host to obtain Model A's base packet for this correction. Keep
   the corresponding five feature rows for lip prediction. Both paths
   use indices `[49:54]` in the full window, with the upper bound exclusive.
   Derive the slice from the contract. Verify the Model A packet and feature
   slice before adding the correction. [Contact decoder](../aai_streaming/contact_decoder.py)
2. Run the fixed four-class linear head locally on those five FP32 feature
   rows. Use `features @ weights.T + bias`, with first-index tie breaking
   and the class order from the config. The head uses the raw ContentVec
   rows supplied to the decoder, before the decoder's internal scaling.
   Start with a host FP32 head and measure its cost. If the feature export
   uses FP16, check phase and seal agreement from that path explicitly.
3. Port `LipClosureController.step` to the client with the same state,
   motion limits and update order. Use double-precision controller math and
   cast the emitted aperture back to `Float`. For each row, clamp the
   baseline `LA` to `[0, 1]` as in the reference, advance the controller once,
   and write the result to channel index 1. Forward the other eight values
   unchanged. Apply this before handing the packet to the renderer queue so
   interpolation and redraws consume the same corrected values. The 0.05
   seal threshold is a parity measurement. The configured hold target is
   0.02. [Python controller and phase head](../aai_streaming/lip_closure.py)
4. Keep the controller on the ordered inference worker, one instance per
   stream. Tie state advancement to accepted packets. Discard duplicate or
   stale results before updating state. Reset the lip and tongue trackers
   with the waveform window on stream restart, capture interruption or
   sample-clock discontinuity. If an inference hop is dropped, restart the
   controller before the next packet and record the gap on the audio clock.
   Flush pending results from the previous stream when restarting.
5. Add an opt-in client setting for the experimental build. Apply changes
   to the setting at a stream boundary. If the correction config is missing,
   invalid or incompatible, use Model A and record the reason in diagnostics.
   Keep packet shape `5 x 9` and the renderer interface as specified in the
   live loop. At 16 kHz the first packet follows 3,200 captured samples, with
   frame centers `160, 480, 800, 1120, 1440`. Each hop advances 1,600 samples.
   The correction uses the existing 100 ms lookahead.
   [PyTorch packet producer](../aai_streaming/pytorch_backend.py) ·
   [Live capture and rendering](streaming_implementation_plan.md#stage-5--integrate-local-live-capture-and-rendering)

## Verify before enabling it in a release

1. Generate local fixtures with the Python reference containing committed
   features, baseline trajectories, phases, corrected aperture and sample
   centers. Include approach through a packet boundary, an isolated short
   /p/, a shared /mp/ gesture, /n/ and /v/ controls, and return to open. Use a
   synthetic fixture for stream reset, duplicate result, skipped hop and
   nonfinite input. Reuse licensed audio from the existing local review.
2. Feed the same fixture features and trajectory to the client. Require
   identical phases and seal masks, maximum aperture error of `1e-6`,
   exact sample centers and exact non-`LA` output compared with the client
   branch off. On stored or stopped audio, exercise zero-padding to a hop
   and adding the lookahead tail. Discard centers at or beyond the original
   audio length as in the reference replay.
   Run two independent streams to verify state isolation. On Core ML, apply
   the existing conversion gates and report phase disagreements, changes
   in sealed frames and onset or reopening errors against PyTorch. Inspect
   any divergences in matched playback before making the release decision.
3. On the M4, measure inference and end-to-end capture-to-render timing,
   missed hops, queue depth and memory with the correction on and off. Apply
   the existing live-loop checks, then repeat on the target device. Review
   synchronized playback on clear new clips. Record overall visual preference
   and use missed seals, extra seals and release timing to diagnose differences.
   [M4 criteria](streaming_implementation_plan.md#development-candidate-completion-criteria) ·
   [Target device qualification](streaming_implementation_plan.md#deferred-a18-pro-qualification) ·
   [Lip review scoring](streaming_lip_reference_replay_2026-11-13.md#lip-correction-scoring)

Deliver the versioned client build, fixture exporter and parity report,
device timings, and the playback decision. The research replay stays
available alongside the client build for comparison.
