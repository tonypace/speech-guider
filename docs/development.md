# Development

## Setup

Use Python 3.12+, Node.js, and ffmpeg for uploaded-format conversion. Run commands
from the repository root. On Apple Silicon, use native ARM Python for MPS support.

```bash
python3.12 -m venv speech-guider
source speech-guider/bin/activate
python -m pip install -r requirements.txt
npm ci
```

Skip venv creation when an environment already exists. Model inference additionally
requires the assets described in [R4 integration](r4-model-integration.md).
Reference speech requires a built OmniVoice executable and its model/codec files.
`.env.sample` lists the settings; the server does not automatically load `.env`.
Export the configured variables in the launching shell.

`setup-arm64.sh` is a legacy environment migration script, not the default setup:
it can modify shell configuration, move an existing environment, and pin older
PyTorch. Prefer the explicit setup above for new environments.

## Run

```bash
python -m app.main
# Equivalent development server with an explicit port:
uvicorn app.main:app --reload --port 7860
```

Visit http://localhost:7860. `bash scripts/start-server.sh` resolves the repository
and its `speech-guider` environment even when invoked from another directory.
`npm run dev` starts and owns both the backend and Tauri development shell; it
fails if a server already answers on port 7860. `npm run tauri dev` launches only
the shell and requires a separately running backend. Packaged desktop operation
is still incomplete: the current bundle does not package/start Python.

## Checks

Activate the Python environment first; npm Python scripts use its PATH.

```bash
npm run lint          # ESLint, Ruff lint and format checks
npm run typecheck     # mypy over owned Python sources and tests
npm run test:run      # one-shot Vitest run
npm run test:py       # pytest
npm run check        # all of the above, stops on first failure
npm run test:e2e:mocked
npm run test:e2e:real
```

Playwright requires an installed Chromium browser (`npx playwright install chromium`)
and a reachable backend.
Mocked browser tests still start the Python app, but intercept analysis requests.
Real tests additionally depend on local models, audio tooling, and browser media
behavior. Tests that need retired model checkpoints can skip; a skipped test does
not validate current R4 inference. Generated fixtures should be used for new
unit tests. See the review report for observed check results and limitations.

Configuration lives in `pyproject.toml`, `eslint.config.mjs`, `vitest.config.js`,
and `playwright.config.js`. Third-party assets, archives, environments, and build
outputs are excluded from code-quality scans. Missing-stub exceptions are scoped
to specific third-party packages; application typing remains checked.

## Conventions and boundaries

- Python: Ruff formatting, snake_case internals, explicit argument/return types,
  standard/third-party/local import groups. Preserve camelCase serialized fields
  required by the renderer; document narrow naming exceptions.
- JavaScript: four-space indentation, single quotes, semicolons, vanilla JS.
  Keep HTML event-handler entrypoints on `window`; keep internal helpers scoped.
- Put HTTP parsing/status handling in `app/api`, shared request resources in
  `app/utils` or `app/services`, and model/audio computation in `src`.
- A resource creator owns cleanup: temporary files, AudioContexts, playback
  sources, animation callbacks, and subprocesses need success and failure paths.
- Keep audio units explicit. SSL input is mono 16 kHz; Prosody Lab browser
  conversion currently uses 44.1 kHz. Do not normalize scientific values merely
  to make implementations look alike.
- Resolve persistent paths against an explicit root. Existing preset persistence
  is still an exception documented in the backend review.
- Changes to sample rate, tract-variable order, timing, normalization, or cache
  keys require behavior-focused regression coverage.
