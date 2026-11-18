# Streaming Perceptual Review Client

Status: **DIAGNOSTIC CLIENT — NOT MODEL ADMISSION OR RELEASE**

This document defines the Stage 7.6 local review client for comparing the R4
streaming successor with the current rolling V1.2 control and offline V1.2. It
is separate from the eventual field client: it operates on frozen validation
audio, but its scheduling and telemetry contracts are intended to transfer.
The current perceptual review uses the
[matched-closure packet](streaming_successor_training_plan.md#76-measure-perceptual-behavior).
The base R4 diagnostic below retains the latency-experience protocol.

## 1. Review artifacts

Build the packet with:

```bash
./.venv/bin/python scripts/build_streaming_perceptual_review.py \
  --device cuda \
  --output data/evaluation/streaming_successor_v1/perceptual_review_v1
```

The packet contains:

- `review_successor_vs_rolling.html`: R4-extended versus 100 ms rolling V1.2;
- `review_successor_vs_offline.html`: R4-extended versus full-utterance V1.2
  from the canonical waveform-derived Stage 7.1 teacher cache;
- balanced anonymous A/B assignments for 20 validation clips;
- browser-decodable 16 kHz PCM audio and exact timestamped trajectories;
- TSV rating sheets plus browser-exportable ratings and timing logs;
- `public_manifest.json` and a sealed `hidden_metadata.json`; and
- the canonical `svg_articulatory_renderer.js` with history trails disabled.

Selection is independent of model deltas: eight ordinary clips, four
fast-speech clips, four silence-transition clips, two clipped-audio clips, and
two field-audio stress clips. The ordinary group contains two clips from each
of MOCHA, USC-TIMIT, USC75, and XRMB.

## 2. Two questions, two playback modes

### 2.1 Synchronized quality

One audio clock drives both anonymous trajectories. Seeking or replaying does
not shift either trajectory. Use this mode for motion shape, closures, GLO/LAT
behavior, packet seams, freezes, reversals, and vibration. Presentation latency
must not influence this judgment.

### 2.2 Latency experience

Each anonymous side is played separately from a fresh click:

- A streaming side starts audio immediately, holds the initial avatar pose for
  the provisional 220 ms startup delay, then displays the trajectory at the
  current audio timestamp. It does not restart or shift audio.
- An offline side first plays the entire source as a capture pass while the
  avatar remains idle. It then waits the measured full-utterance processing
  duration and starts a second synchronized audio/avatar replay.

The pending phase is visible immediately. Offline click-to-result is therefore
the complete utterance duration plus processing and browser scheduling; it is
never capped at the streaming delay.

## 3. Scheduler state machine

```text
streaming: click -> audio + pending -> 220 ms -> timestamp-aligned avatar
offline:   click -> capture/idle -> process/idle -> audio + avatar replay
```

Stopping cancels the current timer and audio. A new play stops any other trial.
The browser always restores the initial pose before a new experience. Audio and
trajectory tensors are immutable; delays exist only in the presentation
scheduler.

## 4. Timing telemetry

Every latency-experience play records:

- trial and anonymous side;
- requested click-to-avatar delay;
- measured click-to-first-avatar-render time;
- audio-to-trajectory timestamp offset at first render;
- first-packet inference diagnostic;
- capture duration;
- full-utterance processing duration;
- timing source; and
- whether the timing is simulated.

Ratings and timing records persist only in browser local storage until the user
exports JSON. The repository packet contains no completed rating or behavioral
telemetry.

The 220 ms startup is provisional. Full-utterance processing is measured by the
builder on the available CUDA system, then replayed as a simulated delay. The
fresh full-utterance pass is timing-only; the displayed offline trajectory is
the frozen waveform-derived Stage 7.1 teacher. Training-validation teachers
decoded from legacy precomputed features are deliberately not used here. The
builder records bounded numeric parity between the displayed teacher and the
fresh pass (maximum absolute error <= 0.002 and mean absolute error <= 0.0002),
accounting
for harmless CUDA recomputation variation without accepting a clock, shape, or
material value mismatch. This is useful for evaluating the dominant capture
wait but is not an MPS claim.
Replace both with capture-to-render measurements on M4 before client
qualification, and later on the A18 MacBook target if it becomes available.

## 5. Rating contract

For each trial record `A`, `B`, `Same`, or `2xFail`, plus independent severe
failure flags. Notes should distinguish:

- closure and active motion;
- GLO/LAT timing;
- packet seam, freeze, reversal, or vibration; and
- latency frustration.

Complete synchronized-quality judgments before latency-experience judgments
when practical. Freeze both response files before opening hidden metadata.

R4-extended is admitted to this review under its predeclared diagnostic
tradeoff only: no more than 1% oral-MAE regression versus R4-10k, no more than
0.05 boundary-ratio regression, and at least one percentage point of GLO or LAT
disagreement improvement. Passing the review does not silently waive the
failed full-utterance regression gates.

## 6. Field-client handoff

The eventual field client must add microphone capture and save, on-device:

1. the mono 16 kHz waveform and absolute sample clock;
2. the live streaming trajectory and packet timestamps;
3. inference timings, underruns, and renderer timings; and
4. a post-capture offline V1.2 trajectory over the identical waveform.

It must then offer the same synchronized-quality and latency-experience views.
No transcript, speaker identity, filename, or audio may be transmitted as
telemetry. Audio remains local unless the user explicitly exports it.
