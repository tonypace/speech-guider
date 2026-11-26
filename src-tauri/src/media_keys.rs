use serde::Serialize;
use std::sync::{
    atomic::{AtomicBool, AtomicU32, Ordering},
    Arc,
};
use tauri::{AppHandle, State};

pub const BIT_VOLUME_UP: u32 = 1 << 0;
pub const BIT_VOLUME_DOWN: u32 = 1 << 1;
pub const BIT_VOLUME_MUTE: u32 = 1 << 2;
pub const BIT_PLAY_PAUSE: u32 = 1 << 3;
pub const BIT_TRACK_NEXT: u32 = 1 << 4;
pub const BIT_TRACK_PREV: u32 = 1 << 5;

#[derive(Debug, Clone, Serialize, PartialEq, Eq)]
pub struct MediaKeyStatus {
    pub supported: bool,
    pub permission_granted: bool,
    pub tap_active: bool,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct MediaKeyEvent {
    pub key: &'static str,
    pub pressed: bool,
    pub is_repeat: bool,
}

pub fn media_key_bit(key: &str) -> u32 {
    match key {
        "AudioVolumeUp" => BIT_VOLUME_UP,
        "AudioVolumeDown" => BIT_VOLUME_DOWN,
        "AudioVolumeMute" => BIT_VOLUME_MUTE,
        "MediaPlayPause" => BIT_PLAY_PAUSE,
        "MediaTrackNext" => BIT_TRACK_NEXT,
        "MediaTrackPrevious" => BIT_TRACK_PREV,
        _ => 0,
    }
}

pub fn mask_from_keys(keys: &[String]) -> u32 {
    keys.iter().fold(0, |acc, key| acc | media_key_bit(key))
}

/// Decode a macOS `NX_SYSDEFINED` (subtype 8) media-key event payload (`NSEvent.data1`).
pub fn decode_nx_media_key(subtype: i16, data1: isize) -> Option<MediaKeyEvent> {
    const NX_SUBTYPE_AUX_CONTROL_BUTTONS: i16 = 8;
    const NX_KEYTYPE_SOUND_UP: usize = 0;
    const NX_KEYTYPE_SOUND_DOWN: usize = 1;
    const NX_KEYTYPE_MUTE: usize = 7;
    const NX_KEYTYPE_PLAY: usize = 16;
    const NX_KEYTYPE_NEXT: usize = 17;
    const NX_KEYTYPE_PREVIOUS: usize = 18;
    const KEY_STATE_DOWN: usize = 0x0A;
    const KEY_STATE_UP: usize = 0x0B;

    if subtype != NX_SUBTYPE_AUX_CONTROL_BUTTONS {
        return None;
    }

    let raw = data1 as usize;
    let key_code = (raw & 0xFFFF_0000) >> 16;
    let key_flags = raw & 0x0000_FFFF;
    let key_state = (key_flags & 0xFF00) >> 8;
    let is_repeat = (key_flags & 0x01) != 0;

    let pressed = match key_state {
        KEY_STATE_DOWN => true,
        KEY_STATE_UP => false,
        _ => return None,
    };

    let key = match key_code {
        NX_KEYTYPE_SOUND_UP => "AudioVolumeUp",
        NX_KEYTYPE_SOUND_DOWN => "AudioVolumeDown",
        NX_KEYTYPE_MUTE => "AudioVolumeMute",
        NX_KEYTYPE_PLAY => "MediaPlayPause",
        NX_KEYTYPE_NEXT => "MediaTrackNext",
        NX_KEYTYPE_PREVIOUS => "MediaTrackPrevious",
        _ => return None,
    };

    Some(MediaKeyEvent {
        key,
        pressed,
        is_repeat,
    })
}

pub struct MediaKeyState {
    focused: AtomicBool,
    learning: AtomicBool,
    bound_mask: AtomicU32,
    tap_active: AtomicBool,
    tap_started: AtomicBool,
}

impl Default for MediaKeyState {
    fn default() -> Self {
        Self {
            focused: AtomicBool::new(true),
            learning: AtomicBool::new(false),
            bound_mask: AtomicU32::new(0),
            tap_active: AtomicBool::new(false),
            tap_started: AtomicBool::new(false),
        }
    }
}

impl MediaKeyState {
    pub fn set_focused(&self, focused: bool) {
        self.focused.store(focused, Ordering::Release);
    }

    pub fn set_capture(&self, learning: bool, bound_keys: &[String]) {
        self.learning.store(learning, Ordering::Release);
        self.bound_mask
            .store(mask_from_keys(bound_keys), Ordering::Release);
    }

    pub fn wants_tap(&self) -> bool {
        self.learning.load(Ordering::Acquire) || self.bound_mask.load(Ordering::Acquire) != 0
    }

    pub fn should_intercept(&self, key: &str) -> bool {
        if !self.focused.load(Ordering::Acquire) {
            return false;
        }
        if self.learning.load(Ordering::Acquire) {
            return media_key_bit(key) != 0;
        }
        (self.bound_mask.load(Ordering::Acquire) & media_key_bit(key)) != 0
    }

    pub fn status(&self) -> MediaKeyStatus {
        MediaKeyStatus {
            supported: cfg!(target_os = "macos"),
            permission_granted: is_accessibility_trusted(),
            tap_active: self.tap_active.load(Ordering::Acquire),
        }
    }
}

pub struct ManagedMediaKeys(pub Arc<MediaKeyState>);

impl Default for ManagedMediaKeys {
    fn default() -> Self {
        Self(Arc::new(MediaKeyState::default()))
    }
}

#[tauri::command]
pub fn get_media_key_status(
    app: AppHandle,
    state: State<'_, ManagedMediaKeys>,
) -> MediaKeyStatus {
    ensure_tap_if_needed(&app, &state.0);
    state.0.status()
}

#[tauri::command]
pub fn request_media_key_permission(
    app: AppHandle,
    state: State<'_, ManagedMediaKeys>,
) -> MediaKeyStatus {
    request_accessibility_prompt();
    ensure_tap_if_needed(&app, &state.0);
    state.0.status()
}

#[tauri::command]
pub fn set_media_key_capture(
    app: AppHandle,
    state: State<'_, ManagedMediaKeys>,
    learning: bool,
    bound_keys: Vec<String>,
) -> MediaKeyStatus {
    state.0.set_capture(learning, &bound_keys);
    ensure_tap_if_needed(&app, &state.0);
    state.0.status()
}

#[cfg(not(target_os = "macos"))]
fn is_accessibility_trusted() -> bool {
    false
}

#[cfg(not(target_os = "macos"))]
fn request_accessibility_prompt() {}

#[cfg(not(target_os = "macos"))]
pub fn ensure_tap_if_needed(_app: &AppHandle, _state: &Arc<MediaKeyState>) {}

#[cfg(target_os = "macos")]
mod macos {
    use super::{decode_nx_media_key, MediaKeyState};
    use std::{
        ffi::{c_char, c_void},
        ptr,
        sync::{
            atomic::{AtomicPtr, Ordering},
            Arc,
        },
        thread,
    };
    use tauri::{AppHandle, Manager};

    const K_CG_SESSION_EVENT_TAP: u32 = 1;
    const K_CG_HEAD_INSERT_EVENT_TAP: u32 = 0;
    const K_CG_EVENT_TAP_OPTION_DEFAULT: u32 = 0;
    const NX_SYSDEFINED_EVENT_TYPE: u32 = 14;
    const K_CG_EVENT_TAP_DISABLED_BY_TIMEOUT: u32 = 0xFFFF_FFFE;
    const K_CG_EVENT_TAP_DISABLED_BY_USER_INPUT: u32 = 0xFFFF_FFFF;

    type CGEventTapCallBack = extern "C" fn(
        proxy: *mut c_void,
        event_type: u32,
        event: *mut c_void,
        user_info: *mut c_void,
    ) -> *mut c_void;

    #[link(name = "ApplicationServices", kind = "framework")]
    extern "C" {
        static kAXTrustedCheckOptionPrompt: *const c_void;
        fn AXIsProcessTrusted() -> bool;
        fn AXIsProcessTrustedWithOptions(options: *const c_void) -> bool;
    }

    #[link(name = "CoreFoundation", kind = "framework")]
    extern "C" {
        static kCFBooleanTrue: *const c_void;
        static kCFTypeDictionaryKeyCallBacks: u8;
        static kCFTypeDictionaryValueCallBacks: u8;
        static kCFRunLoopCommonModes: *const c_void;

        fn CFDictionaryCreate(
            allocator: *const c_void,
            keys: *const *const c_void,
            values: *const *const c_void,
            num_values: isize,
            key_callbacks: *const c_void,
            value_callbacks: *const c_void,
        ) -> *const c_void;
        fn CFRelease(cf: *const c_void);
        fn CFMachPortCreateRunLoopSource(
            allocator: *const c_void,
            port: *mut c_void,
            order: isize,
        ) -> *mut c_void;
        fn CFRunLoopGetCurrent() -> *mut c_void;
        fn CFRunLoopAddSource(rl: *mut c_void, source: *mut c_void, mode: *const c_void);
        fn CFRunLoopRun();
    }

    #[link(name = "CoreGraphics", kind = "framework")]
    extern "C" {
        fn CGEventTapCreate(
            tap: u32,
            place: u32,
            options: u32,
            events_of_interest: u64,
            callback: CGEventTapCallBack,
            user_info: *mut c_void,
        ) -> *mut c_void;
        fn CGEventTapEnable(tap: *mut c_void, enable: bool);
    }

    #[link(name = "AppKit", kind = "framework")]
    #[link(name = "objc")]
    extern "C" {
        fn objc_getClass(name: *const c_char) -> *mut c_void;
        fn sel_registerName(name: *const c_char) -> *mut c_void;
        fn objc_autoreleasePoolPush() -> *mut c_void;
        fn objc_autoreleasePoolPop(pool: *mut c_void);
        fn objc_msgSend();
    }

    struct TapContext {
        app: AppHandle,
        state: Arc<MediaKeyState>,
        port: AtomicPtr<c_void>,
    }

    pub fn is_accessibility_trusted() -> bool {
        unsafe { AXIsProcessTrusted() }
    }

    pub fn request_accessibility_prompt() {
        unsafe {
            let keys = [kAXTrustedCheckOptionPrompt];
            let values = [kCFBooleanTrue];
            let dict = CFDictionaryCreate(
                ptr::null(),
                keys.as_ptr(),
                values.as_ptr(),
                1,
                (&kCFTypeDictionaryKeyCallBacks as *const u8).cast::<c_void>(),
                (&kCFTypeDictionaryValueCallBacks as *const u8).cast::<c_void>(),
            );
            if !dict.is_null() {
                let _ = AXIsProcessTrustedWithOptions(dict);
                CFRelease(dict);
            }
        }
    }

    unsafe fn decode_cg_system_event(event: *mut c_void) -> Option<(i16, isize)> {
        let pool = objc_autoreleasePoolPush();
        let result = (|| {
            let cls = objc_getClass(c"NSEvent".as_ptr());
            if cls.is_null() {
                return None;
            }
            let sel_from_cg = sel_registerName(c"eventWithCGEvent:".as_ptr());
            let msg_from_cg: unsafe extern "C" fn(*mut c_void, *mut c_void, *mut c_void) -> *mut c_void =
                std::mem::transmute(objc_msgSend as *const ());
            let ns_event = msg_from_cg(cls, sel_from_cg, event);
            if ns_event.is_null() {
                return None;
            }
            let sel_subtype = sel_registerName(c"subtype".as_ptr());
            let msg_subtype: unsafe extern "C" fn(*mut c_void, *mut c_void) -> i16 =
                std::mem::transmute(objc_msgSend as *const ());
            let subtype = msg_subtype(ns_event, sel_subtype);

            let sel_data1 = sel_registerName(c"data1".as_ptr());
            let msg_data1: unsafe extern "C" fn(*mut c_void, *mut c_void) -> isize =
                std::mem::transmute(objc_msgSend as *const ());
            let data1 = msg_data1(ns_event, sel_data1);
            Some((subtype, data1))
        })();
        objc_autoreleasePoolPop(pool);
        result
    }

    extern "C" fn event_tap_callback(
        _proxy: *mut c_void,
        event_type: u32,
        event: *mut c_void,
        user_info: *mut c_void,
    ) -> *mut c_void {
        if user_info.is_null() {
            return event;
        }
        let ctx = unsafe { &*(user_info as *const TapContext) };

        if event_type == K_CG_EVENT_TAP_DISABLED_BY_TIMEOUT
            || event_type == K_CG_EVENT_TAP_DISABLED_BY_USER_INPUT
        {
            let port = ctx.port.load(Ordering::Acquire);
            if !port.is_null() {
                unsafe { CGEventTapEnable(port, true) };
            }
            return event;
        }

        if event_type != NX_SYSDEFINED_EVENT_TYPE || event.is_null() {
            return event;
        }

        let Some((subtype, data1)) = (unsafe { decode_cg_system_event(event) }) else {
            return event;
        };
        let Some(media_event) = decode_nx_media_key(subtype, data1) else {
            return event;
        };

        if !ctx.state.should_intercept(media_event.key) {
            return event;
        }

        let event_name = if media_event.pressed { "keydown" } else { "keyup" };
        let key_json = serde_json::to_string(media_event.key).unwrap_or_default();
        let script = format!(
            "window.dispatchEvent(new CustomEvent('speechguider:mediakey', {{ detail: {{ key: {key_json}, type: '{event_name}', repeat: {} }} }}));",
            media_event.is_repeat
        );
        let app = ctx.app.clone();
        let _ = ctx.app.run_on_main_thread(move || {
            if let Some(window) = app.get_webview_window("main") {
                let _ = window.eval(script);
            }
        });

        // Swallow event so macOS does not adjust system volume while Speech Guider handles it.
        ptr::null_mut()
    }

    pub fn ensure_tap_if_needed(app: &AppHandle, state: &Arc<MediaKeyState>) {
        if !state.wants_tap() || !is_accessibility_trusted() {
            return;
        }
        if state
            .tap_started
            .compare_exchange(false, true, Ordering::AcqRel, Ordering::Acquire)
            .is_err()
        {
            return;
        }

        let (tx, rx) = std::sync::mpsc::sync_channel::<()>(1);
        let app_handle = app.clone();
        let state_arc = Arc::clone(state);
        let spawn_result = thread::Builder::new()
            .name("speech-guider-media-keys".into())
            .spawn(move || {
                let ctx = Box::new(TapContext {
                    app: app_handle,
                    state: Arc::clone(&state_arc),
                    port: AtomicPtr::new(ptr::null_mut()),
                });
                let ctx_ptr = Box::into_raw(ctx);
                let mask: u64 = 1u64 << (NX_SYSDEFINED_EVENT_TYPE as u64);
                let port = unsafe {
                    CGEventTapCreate(
                        K_CG_SESSION_EVENT_TAP,
                        K_CG_HEAD_INSERT_EVENT_TAP,
                        K_CG_EVENT_TAP_OPTION_DEFAULT,
                        mask,
                        event_tap_callback,
                        ctx_ptr.cast::<c_void>(),
                    )
                };
                if port.is_null() {
                    // Tap creation failed; allow future retry once permission is granted.
                    unsafe { drop(Box::from_raw(ctx_ptr)) };
                    state_arc.tap_active.store(false, Ordering::Release);
                    state_arc.tap_started.store(false, Ordering::Release);
                    let _ = tx.send(());
                    return;
                }
                unsafe {
                    (*ctx_ptr).port.store(port, Ordering::Release);
                    let source = CFMachPortCreateRunLoopSource(ptr::null(), port, 0);
                    if source.is_null() {
                        CFRelease(port.cast::<c_void>());
                        drop(Box::from_raw(ctx_ptr));
                        state_arc.tap_active.store(false, Ordering::Release);
                        state_arc.tap_started.store(false, Ordering::Release);
                        let _ = tx.send(());
                        return;
                    }
                    let run_loop = CFRunLoopGetCurrent();
                    CFRunLoopAddSource(run_loop, source, kCFRunLoopCommonModes);
                    CGEventTapEnable(port, true);
                    state_arc.tap_active.store(true, Ordering::Release);
                    let _ = tx.send(());
                    CFRunLoopRun();
                    CFRelease(source.cast::<c_void>());
                    CFRelease(port.cast::<c_void>());
                    drop(Box::from_raw(ctx_ptr));
                }
                state_arc.tap_active.store(false, Ordering::Release);
                state_arc.tap_started.store(false, Ordering::Release);
            });

        if spawn_result.is_ok() {
            let _ = rx.recv_timeout(std::time::Duration::from_millis(250));
        } else {
            state.tap_started.store(false, Ordering::Release);
        }
    }
}

#[cfg(target_os = "macos")]
use macos::{ensure_tap_if_needed, is_accessibility_trusted, request_accessibility_prompt};

#[cfg(test)]
mod tests {
    use super::*;

    fn pack_data1(key_code: usize, key_state: usize, repeat: bool) -> isize {
        let flags = (key_state << 8) | usize::from(repeat);
        ((key_code << 16) | flags) as isize
    }

    #[test]
    fn decodes_volume_and_media_key_events() {
        assert_eq!(
            decode_nx_media_key(8, pack_data1(0, 0x0A, false)),
            Some(MediaKeyEvent {
                key: "AudioVolumeUp",
                pressed: true,
                is_repeat: false,
            })
        );
        assert_eq!(
            decode_nx_media_key(8, pack_data1(1, 0x0B, false)),
            Some(MediaKeyEvent {
                key: "AudioVolumeDown",
                pressed: false,
                is_repeat: false,
            })
        );
        assert_eq!(
            decode_nx_media_key(8, pack_data1(7, 0x0A, true)),
            Some(MediaKeyEvent {
                key: "AudioVolumeMute",
                pressed: true,
                is_repeat: true,
            })
        );
        assert_eq!(
            decode_nx_media_key(8, pack_data1(16, 0x0A, false)),
            Some(MediaKeyEvent {
                key: "MediaPlayPause",
                pressed: true,
                is_repeat: false,
            })
        );
        assert_eq!(decode_nx_media_key(7, pack_data1(0, 0x0A, false)), None);
        assert_eq!(decode_nx_media_key(8, pack_data1(99, 0x0A, false)), None);
        assert_eq!(decode_nx_media_key(8, pack_data1(0, 0x0C, false)), None);
    }

    #[test]
    fn intercepts_media_keys_only_when_focused_and_bound_or_learning() {
        let state = MediaKeyState::default();
        assert!(!state.should_intercept("AudioVolumeUp"));

        state.set_capture(false, &["AudioVolumeUp".to_string()]);
        assert!(state.should_intercept("AudioVolumeUp"));
        assert!(!state.should_intercept("AudioVolumeDown"));

        state.set_focused(false);
        assert!(!state.should_intercept("AudioVolumeUp"));

        state.set_focused(true);
        state.set_capture(true, &[]);
        assert!(state.should_intercept("AudioVolumeDown"));
        assert!(!state.should_intercept("PageDown"));
    }
}
