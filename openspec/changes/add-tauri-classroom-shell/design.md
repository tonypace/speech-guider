## Context

Speech Guider currently runs as a FastAPI-served web app with Jinja templates and static JavaScript. The existing interface already supports mode switching between pronunciation analysis, animation exploration, and prosody analysis, but it depends on normal browser interaction. The classroom use case needs a native shell that can be summoned quickly and controlled with minimal visible computer use.

This change is intentionally Phase 1 only: wrap the current app with Tauri, add menu-bar presence, and define a Tauri-only semantic controller for the three-button clicker. The future AAI/utterance-level animation direction should remain compatible with this controller model.

## Goals / Non-Goals

**Goals:**
- Provide a native macOS shell around the existing FastAPI app.
- Support menu-bar launching into pronunciation, prosody, and animation modes.
- Make the clicker drive semantic classroom actions in Tauri mode only.
- Preserve the existing browser app unchanged outside Tauri.
- Keep the interaction model compatible with future utterance-level animation navigation.

**Non-Goals:**
- Rewriting the frontend into a separate SPA.
- Packaging the Python backend into the production app bundle.
- Making every current UI control clicker-operable.
- Implementing fullscreen presentation mode in this phase.
- Moving the browser app to Tauri-only behavior.

## Decisions

1. **Wrap the existing FastAPI app instead of introducing a separate frontend build.**
   - Rationale: The app already serves its UI from FastAPI, so Tauri can add native behavior without duplicating architecture.
   - Alternatives considered: A Vite-based frontend rewrite or a SPA migration. Rejected for Phase 1 because they add scope and break the current same-origin model.

2. **Use task-oriented menu items rather than generic app navigation.**
   - Rationale: Teachers think in terms of practice tasks, not internal tabs.
   - Alternatives considered: Literal tab names only. Rejected because the app is meant to feel like a teaching tool, not a browser page.

3. **Model the clicker as semantic actions, not DOM focus traversal.**
   - Rationale: The clicker emits only `Left`, `Right`, and `Tab`, so the app should interpret those as previous/next/record instead of relying on browser tab order.
   - Alternatives considered: Standard keyboard focus navigation. Rejected because it is fragile and does not match the classroom workflow.

4. **Keep `Tab` as the primary hold-to-record control in Tauri mode.**
   - Rationale: The clicker’s blank-screen button maps naturally to a hold/release recording gesture.
   - Alternatives considered: Retaining `F5` as the primary shortcut. Rejected for the native classroom shell because it is less intuitive and less portable.

5. **Allow pronunciation review to auto-animate when stepping through teaching moments.**
   - Rationale: The clicker should move attention, not require extra confirmation steps.
   - Alternatives considered: Separate select and animate actions. Rejected for Phase 1 because they slow the live teaching loop.

6. **Keep prosody navigation minimal in Phase 1.**
   - Rationale: Prosody charts and comparison controls are useful, but only the core record/review loop should be clicker-driven initially.
   - Alternatives considered: Making all chart controls clicker-operable. Rejected because it adds complexity without improving the live classroom loop.

## Risks / Trade-offs

- [Risk] Tauri webview microphone support may differ from the browser.
  → [Mitigation] Verify microphone permission and recording flow early in the shell.
- [Risk] CDN-loaded assets may be less reliable in a native shell.
  → [Mitigation] Accept this for Phase 1, then revisit asset bundling later if needed.
- [Risk] Semantic clicker handling can drift into mode ambiguity.
  → [Mitigation] Keep the controller vocabulary small and mode-specific.
- [Risk] Fullscreen/presentation mode may become desirable quickly.
  → [Mitigation] Keep the controller abstraction separate so a future fullscreen shell can reuse it.

## Migration Plan

1. Add the Tauri shell and menu bar without changing the web app structure.
2. Verify the Tauri shell can load the existing FastAPI app and access the microphone.
3. Add the Tauri-only semantic controller bridge.
4. Map pronunciation, prosody, and animation modes onto the existing UI.
5. Remove `F5` as the primary native interaction model while keeping browser behavior unchanged.

Rollback is straightforward: the browser app remains available without Tauri, and the web app continues to function independently.

## Open Questions

- Should the Tauri shell eventually become fullscreen/presentation-first?
- Should prosody navigation eventually step through recordings, teacher/student assignments, or future utterance-level regions?
- Should the menu bar include additional debug or developer actions, or stay strictly classroom-focused?
