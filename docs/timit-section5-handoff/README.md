# TIMIT -> Speech Guider Section 5 Handoff (2026-11-18)

This folder packages the verified TIMIT streaming/contact/lip/renderer context
for `speech-guider` Section 5 integration.

## Model & Experiment Status

- **Selected streaming base:** Extended R4 (`r4_bounded_distilled_seam_seed13/best.successor.full.pt`, SHA-256 `9c10c26293345c94048dead4c924fba0e93694215fe265d4af88100e2ce178cc`), already staged in `external/R4 26-11-06/weights/r4.pt`.
- **Selected contact head:** Model A (`r4_contact_coupled_seed13/best.contact_decoder.pt`, SHA-256 `d4a028f79f0ec9c131b57077d7594212f4ce0a65691bf1d8fe635a45df01b710`), already staged in `external/R4 26-11-06/weights/contact.pt` with the committed-frame tracker fix (`src/models/r4_contact.py`).
- **TIMIT Section 3 screens (all closed without replacing Model A):**
  - MOCHA EPG within-speaker sampling balance (500 updates, A100): numeric gate failed (`body_short` 11/12 vs. 11/12, `tip_long` 100/106 vs. 101/106) and blinded playback rated 8/8 `Same`.
  - Direct contact/place/duration auxiliary supervision on R4 (1,000 updates, A100): failed numeric gates (`0/190` contacts `<= 0.03` without external contact realization; `oral_mae` and `mean_boundary_ratio` regressed).
  - Phonetic FiLM routing (`RoutedContactStateHead(H=64)` vs. equal-capacity `ExplicitContactStateHead(H=68)`, 2,000 updates, A100): improved tip contacts (`159/169` vs. `155/169`) and halved silence false contacts (`11/264` vs. `21/264`), but regressed body stops (`/k, g, ng/`: `16/21` vs. `19/21`).

## New Assets Needed in Speech Guider

1. **Optional calibrated lip correction** (`model_a_lip_correction_v1.json`, `04a86e29...`, + `lip_closure.py`, `a451f09e...`):
   - Note: `speech-guider` does not yet integrate `LipCorrection` (`configs/streaming/model_a_lip_correction_v1.json`).
   - Follow `streaming_lip_client_implementation.md` to wire `LipCorrection.load(..., contentvec_sha256=...)` after Model A contact realization, preserving packet parity and vowel openness.
2. **Frozen SVG renderer** (`svg_articulatory_renderer.js`, `b0f6943c...`):
   - `speech-guider/static/js/svg_articulatory_renderer.js` currently has SHA-256 `06555d08...` rather than the TIMIT frozen renderer `b0f6943c176538befb7952d9e765a487e78c8ecaf926563597a1efa387e93666` (upper-teeth/contact geometry fixes). Diff and reconcile before live student playback.
3. **Client & deployment contracts:**
   - `streaming_perceptual_client.md`: synchronized playback, sample-clock trajectory logging, and expanded silence gate.
   - `streaming_implementation_plan.md`: M4 MPS timing baseline, Core ML conversion/parity, and live microphone capture/render integration.

## Verified SHA-256 Checksums

- `lip_closure.py`: `a451f09e1bdc2039ff287b06144df24becba2e09910630e419d58530bd1cf307`
- `model_a_lip_correction_v1.json`: `04a86e29a5e3e56e8c8e61259b706c75b332e9e61b10427a7a3c8b6b0ec64b9c`
- `svg_articulatory_renderer.js`: `b0f6943c176538befb7952d9e765a487e78c8ecaf926563597a1efa387e93666`
- `streaming_implementation_plan.md`: `2dd3071d467157ec545fc7c990f475f02014b1b3922a04e171e973f942b2ca2b`
- `streaming_lip_client_implementation.md`: `03d2f3fed833682865d9871268a2370d7bff8c152cdb9eaa7619f38a584a9b4b`
- `streaming_perceptual_client.md`: `9cc02c349a8b13c588482ea6b69a60650c18cf5c8b396a36343d834a30048b`
