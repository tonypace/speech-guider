# Build and run the standalone macOS app

This release targets Apple Silicon with macOS 26 or later. The current build uses
Homebrew Python and native libraries whose binary deployment target is macOS 26.
The app contains its own Python runtime, web assets, and backend libraries.
Node.js, Python, Homebrew, and ffmpeg are not needed to launch the built app or
analyze WAV recordings from the UI.

## Build on Apple Silicon

From the repository root, use native Python 3.12, Node.js, Rust, and the macOS
command line developer tools. Set up the project environment as described in
[development](development.md), then install the freeze tools and build:

```sh
source speech-guider/bin/activate
python -m pip install --target build/desktop-packager -r requirements-desktop-build.txt
npm ci
npm run desktop:build
```

`desktop:build` checks the committed frontend assets, freezes and smoke-tests the
Python backend, then bundles it in `src-tauri/target/release/bundle/macos/Speech Guider.app`.
The frozen files are staged under `build/desktop-backend/`. Neither directory is
source to commit. Use `npm run desktop:bundle` to rebundle a verified frozen backend
without running the freezer again. Bare `tauri build` has bundling disabled so it
cannot produce an app without the backend.

This is a local app with an [ad hoc signature](https://v2.tauri.app/distribute/sign/macos/#ad-hoc-signing).
Distribution to other machines still requires Developer ID signing, notarization,
and verification on a clean Mac.

## Build the all-in-one installer

For a local noncommercial install that includes both models, build with:

```sh
npm run desktop:installer
```

The package is `build/installer/Speech Guider - Local Noncommercial.pkg`. It
installs one app under `/Applications`; the signed app contains its models
and uses them by default. Explicit model path overrides still take precedence.
Installation does not move or replace your presets or recording summaries.

The build verifies the supplied R4 checksums and the two known OmniVoice GGUF
checksums and relocates the OmniVoice libraries. It combines the
[component credits](installer-assets.md) and
[R4 dataset credits](attribution-for-r4.md) for the installer and the app
bundle. It only copies R4 files needed for inference. The evaluation kit and
its recordings stay local. The `.pkg` is a local build, without a Developer ID
Installer signature or notarization.

## Run and install models

Open **Speech Guider.app**. The launcher starts one backend on a free loopback port,
waits for its readiness file and health endpoint, then opens the rendered app.
Quit Speech Guider to stop its backend and any audio subprocesses. If startup fails
or the backend exits unexpectedly, the app shows a failure screen with the log path.

Presets and recent Prosody Lab summaries live in
`~/Library/Application Support/com.speechguider.app/`, independent of the assigned
port. Logs are in `~/Library/Logs/com.speechguider.app/backend.log`. For isolated
launches from a shell, set `SPEECH_GUIDER_DESKTOP_STATE_DIR` to an absolute directory;
its logs go under `logs/`. Existing development presets are not copied automatically;
copy a prior `presets.json` only if you want it and the destination has no saved file.
Browser-only `localStorage` presets and history stay in that browser.

Models are separate local assets. The app shows the install directory when an asset
is missing, and Prosody Lab and Animation Lab still open. Put assets under the app
state directory as follows:

```text
assets/
  r4/                              # Entire supplied bundle; retain its terms
    configs/nine_channel_v12_100ms.yaml
    weights/r4.pt
    weights/contentvec/            # Local encoder and processor files
  omnivoice/
    omnivoice-tts                   # Executable arm64 build, with its needed libraries
    models/omnivoice-base-Q8_0.gguf
    models/omnivoice-tokenizer-F32.gguf
  bin/ffmpeg                        # Optional executable for non-WAV API uploads
```

Use a relocatable OmniVoice build or point `OMNIVOICE_TTS_PATH` at the installed
executable in its original build directory so its libraries remain discoverable.
Keep supplied licenses with assets. Restart after installing or replacing a model.
The shell also accepts `SPEECH_GUIDER_ASSET_DIR`, `SSL_AAI_BUNDLE_PATH`,
`SSL_AAI_CHECKPOINT_PATH`, `OMNIVOICE_TTS_PATH`, `OMNIVOICE_MODEL_PATH`,
`OMNIVOICE_CODEC_PATH`, and `SPEECH_GUIDER_FFMPEG_PATH` when started from a shell.
See [R4 integration](r4-model-integration.md) for bundle details.

## Verify a build

```sh
python scripts/smoke_desktop_backend.py
python scripts/smoke_desktop_backend.py --r4-bundle 'external/R4 26-11-06'
python scripts/smoke_desktop_app.py  # Opens test windows in a macOS desktop session
npm run test:e2e:offline
```

The smoke script starts the frozen executable from a fresh temporary directory
with a system-only `PATH`, verifies startup and serves the UI, analyzes a generated
WAV, and checks shutdown cleanup. The optional R4 check uses a generated tone to
check packaged inference dependencies; it does not assess pronunciation quality.
The browser suite blocks and counts all external requests. See
[release contracts](release-contracts.md) for remaining hardware and distribution
validation.

## Local verification

The Apple Silicon build was verified on macOS 26.6.2. Strict code-signature
verification passed. The packaged WebView loaded local assets with port 7860
occupied, restored a saved preset after restarting on a different port, showed
backend crash feedback, and cleaned up on quit. A copy outside the repository
also launched with a system-only `PATH`. The bundled backend processed synthetic
WAV audio and produced R4 frames with the separately installed model bundle.
No physical recording or clean-machine install was used for these checks.
