## Why

Speech Guider is most valuable in live teaching when it can be summoned instantly and driven with minimal visible computer interaction. A Tauri shell lets the existing FastAPI app run as a native macOS classroom tool with a menu bar presence and clicker-friendly launch behavior, without rewriting the current web app.

## What Changes

- Add a Tauri shell around the existing FastAPI-served app.
- Add a macOS menu bar with task-oriented actions for pronunciation practice, prosody practice, and mouth-shape exploration.
- Add Tauri-only launch behavior that opens the app directly into a selected mode.
- Add Tauri-only clicker semantics so `Left`, `Right`, and `Tab` drive teaching actions instead of browser focus order.
- Replace `F5` as the primary native interaction model.
- Keep the browser version conventional and unchanged outside the Tauri shell.
- Use a normal resizable window in Phase 1; defer fullscreen/presentation mode to a later change.

## Capabilities

### New Capabilities
- `tauri-classroom-shell`: Native macOS shell, menu bar presence, and mode-launch behavior for the existing app.
- `clicker-classroom-control`: Tauri-only three-button classroom control model for launching, recording, and stepping through teaching moments.

### Modified Capabilities

## Impact

- Native shell and macOS app configuration are added.
- The current FastAPI, Jinja, and `/static` delivery model stays intact.
- No new frontend build pipeline is introduced.
- The browser app retains its existing behavior outside Tauri.
