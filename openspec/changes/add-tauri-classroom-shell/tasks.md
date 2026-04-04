## 1. Tauri shell foundation
- [x] Initialize the Tauri workspace for the existing repo
- [x] Configure Tauri dev mode to load the FastAPI app at `http://127.0.0.1:7860`
- [x] Add macOS microphone permission text
- [ ] Verify the Tauri webview can access the existing microphone recording flow

## 2. Menu bar presence
- [x] Add a macOS menu bar icon and menu
- [x] Add `Open Window`, `Practice Pronunciation`, `Practice Prosody`, `Explore Mouth Shapes`, and `Quit`
- [x] Make menu actions show and focus the existing app window

## 3. Native controller bridge
- [x] Define Tauri-only semantic actions for mode launch, previous, next, record press, and record release
- [x] Deliver those actions into the existing web app
- [x] Ensure the browser version remains unchanged outside Tauri

## 4. Pronunciation mode behavior
- [x] Map `Practice Pronunciation` launch to the analysis tab
- [x] Arm pronunciation mode without starting recording automatically
- [x] Map clicker hold/release to recording start/stop in Tauri mode
- [x] Map `Left` and `Right` to previous/next pronunciation teaching moments
- [x] Auto-update articulatory visuals when stepping through reviewable moments

## 5. Prosody mode behavior
- [x] Map `Practice Prosody` launch to the prosody tab
- [x] Arm prosody mode without starting recording automatically
- [x] Map clicker hold/release to recording start/stop in Tauri mode
- [x] Keep `Left` and `Right` inert until at least two usable review targets exist
- [x] Keep advanced chart controls out of clicker scope for Phase 1

## 6. Animation mode behavior
- [x] Map `Explore Mouth Shapes` launch to the animation tab
- [x] Map `Left` and `Right` to previous/next phoneme selection
- [x] Make phoneme selection animate automatically
- [x] Keep slider editing and preset authoring out of clicker scope

## 7. Shortcut transition
- [x] Remove `F5` as the primary Tauri interaction model
- [x] Decide whether `F5` remains as a temporary fallback during migration
- [x] Preserve normal browser behavior outside Tauri

## 8. Validation
- [ ] Verify menu launch into all three modes
- [ ] Verify clicker-driven recording in pronunciation mode
- [ ] Verify clicker-driven recording in prosody mode
- [ ] Verify pronunciation review auto-advances and auto-updates visuals
- [ ] Verify prosody navigation remains inert until usable
- [ ] Verify animation mode auto-animates on phoneme selection
- [ ] Verify browser mode remains conventional
