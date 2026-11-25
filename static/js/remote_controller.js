import { getSettings } from './microphone.js';

export const REMOTE_ACTIONS = ['record', 'play_pause', 'speed_up', 'speed_down'];

export const DEFAULT_REMOTE_BINDINGS = {
    record: '',
    play_pause: '',
    speed_up: '',
    speed_down: '',
};

export const MEDIA_KEYS = new Set([
    'AudioVolumeUp',
    'AudioVolumeDown',
    'AudioVolumeMute',
    'MediaPlayPause',
    'MediaTrackNext',
    'MediaTrackPrevious',
]);

const IGNORED_KEYS = new Set([
    'Shift',
    'Control',
    'Alt',
    'Meta',
    'CapsLock',
    'NumLock',
    'ScrollLock',
    'Unidentified',
    'Dead',
    'Process',
]);

const KEY_LABELS = {
    AudioVolumeUp: 'Volume Up',
    AudioVolumeDown: 'Volume Down',
    AudioVolumeMute: 'Volume Mute',
    MediaPlayPause: 'Media Play / Pause',
    MediaTrackNext: 'Media Next',
    MediaTrackPrevious: 'Media Previous',
    PageDown: 'Page Down',
    PageUp: 'Page Up',
    ArrowLeft: 'Arrow Left',
    ArrowRight: 'Arrow Right',
    ArrowUp: 'Arrow Up',
    ArrowDown: 'Arrow Down',
    Space: 'Space',
    Escape: 'Esc',
    '.': '. (Period)',
};

export function normalizeRemoteKey(input) {
    const raw = typeof input === 'string' ? input : input?.key;
    if (!raw || typeof raw !== 'string') return '';
    if (IGNORED_KEYS.has(raw)) return '';
    if (raw === ' ') return 'Space';
    if (raw.length === 1 && /[A-Za-z]/.test(raw)) return raw.toLowerCase();
    return raw;
}

export function formatRemoteKeyLabel(token) {
    if (!token) return 'Not assigned';
    if (KEY_LABELS[token]) return KEY_LABELS[token];
    if (token.length === 1 && /[a-z]/.test(token)) return token.toUpperCase();
    return token;
}

function getTauriInvoke() {
    if (typeof window === 'undefined') return null;
    if (typeof window.__TAURI_INTERNALS__?.invoke === 'function') {
        return (cmd, args) => window.__TAURI_INTERNALS__.invoke(cmd, args);
    }
    if (typeof window.__TAURI__?.core?.invoke === 'function') {
        return (cmd, args) => window.__TAURI__.core.invoke(cmd, args);
    }
    return null;
}

const NON_TEXT_INPUT_TYPES = new Set([
    'button',
    'checkbox',
    'color',
    'file',
    'hidden',
    'image',
    'radio',
    'range',
    'reset',
    'submit',
]);

const TEXT_INPUT_ALLOWED_REMOTE_KEYS = new Set([
    'Tab',
    'PageUp',
    'PageDown',
    'Escape',
]);

function isTextInputTarget(target) {
    const el = target?.closest?.('input, textarea, [contenteditable="true"]');
    if (!el) return false;
    if (el.tagName === 'INPUT') {
        const type = (el.getAttribute('type') || 'text').toLowerCase();
        return !NON_TEXT_INPUT_TYPES.has(type);
    }
    return true;
}

function canTriggerInsideTextInput(key) {
    if (MEDIA_KEYS.has(key) || TEXT_INPUT_ALLOWED_REMOTE_KEYS.has(key)) return true;
    return /^F([1-9]|1[0-2])$/.test(key);
}

export class PresenterRemoteController {
    constructor() {
        this.learningCallback = null;
        this.holdRecordTab = null;
        this.holdRecordKey = null;
        this.destroyed = false;

        this._onKeyDown = (event) => this._handleDomKey(event, 'keydown');
        this._onKeyUp = (event) => this._handleDomKey(event, 'keyup');
        this._onMediaKey = (event) => this._handleMediaKey(event);
        this._onBlur = () => this._releaseHoldRecording();
        this._onTabChange = () => this._releaseHoldRecording();
        this._onSettingsChange = () => { void this.syncNativeCapture(); };

        this.bindEvents();
        void this.syncNativeCapture();
    }

    bindEvents() {
        document.addEventListener('keydown', this._onKeyDown, true);
        document.addEventListener('keyup', this._onKeyUp, true);
        window.addEventListener('speechguider:mediakey', this._onMediaKey);
        window.addEventListener('blur', this._onBlur);
        window.addEventListener('speechguider:tabchange', this._onTabChange);
        window.addEventListener('speechguider:settingschange', this._onSettingsChange);
    }

    destroy() {
        if (this.destroyed) return;
        this.destroyed = true;
        this._releaseHoldRecording();
        this.learningCallback = null;
        document.removeEventListener('keydown', this._onKeyDown, true);
        document.removeEventListener('keyup', this._onKeyUp, true);
        window.removeEventListener('speechguider:mediakey', this._onMediaKey);
        window.removeEventListener('blur', this._onBlur);
        window.removeEventListener('speechguider:tabchange', this._onTabChange);
        window.removeEventListener('speechguider:settingschange', this._onSettingsChange);
    }

    getRemoteConfig() {
        const settings = getSettings();
        return {
            enabled: settings.remote_enabled !== false,
            recordMode: settings.remote_record_mode === 'hold' ? 'hold' : 'toggle',
            bindings: {
                ...DEFAULT_REMOTE_BINDINGS,
                ...(settings.remote_bindings || {}),
            },
        };
    }

    findActionForKey(key) {
        if (!key) return null;
        const { enabled, bindings } = this.getRemoteConfig();
        if (!enabled) return null;
        for (const action of REMOTE_ACTIONS) {
            if (normalizeRemoteKey(bindings[action]) === key) {
                return action;
            }
        }
        return null;
    }

    setLearningCallback(callback) {
        this.learningCallback = typeof callback === 'function' ? callback : null;
        void this.syncNativeCapture();
    }

    async syncNativeCapture() {
        const invoke = getTauriInvoke();
        if (!invoke) return null;
        const { enabled, bindings } = this.getRemoteConfig();
        const boundKeys = enabled
            ? Array.from(new Set(
                REMOTE_ACTIONS
                    .map((action) => normalizeRemoteKey(bindings[action]))
                    .filter((key) => MEDIA_KEYS.has(key)),
            ))
            : [];
        try {
            return await invoke('set_media_key_capture', {
                learning: Boolean(this.learningCallback),
                boundKeys,
            });
        } catch (error) {
            console.warn('[PresenterRemote] Could not sync native media-key capture:', error);
            return null;
        }
    }

    async getMediaKeyStatus() {
        const invoke = getTauriInvoke();
        if (!invoke) {
            return { supported: false, permission_granted: false, tap_active: false };
        }
        try {
            return await invoke('get_media_key_status');
        } catch (error) {
            console.warn('[PresenterRemote] Could not read native media-key status:', error);
            return { supported: false, permission_granted: false, tap_active: false };
        }
    }

    async requestMediaKeyPermission() {
        const invoke = getTauriInvoke();
        if (!invoke) {
            return { supported: false, permission_granted: false, tap_active: false };
        }
        try {
            return await invoke('request_media_key_permission');
        } catch (error) {
            console.warn('[PresenterRemote] Could not request macOS permission:', error);
            return { supported: false, permission_granted: false, tap_active: false };
        }
    }

    _handleDomKey(event, type) {
        if (this.destroyed) return;
        const key = normalizeRemoteKey(event);
        if (!key) return;

        if (this.learningCallback) {
            if (type !== 'keydown' || event.repeat) return;
            event.preventDefault();
            event.stopImmediatePropagation();
            const callback = this.learningCallback;
            this.setLearningCallback(null);
            if (key === 'Escape') {
                callback({ cancelled: true });
            } else {
                callback({ key, label: formatRemoteKeyLabel(key) });
            }
            return;
        }

        if (event.metaKey || event.ctrlKey || event.altKey) return;
        if (isTextInputTarget(event.target) && !canTriggerInsideTextInput(key)) return;

        const handled = this._dispatchKey(key, type, Boolean(event.repeat));
        if (handled) {
            event.preventDefault();
            event.stopImmediatePropagation();
        }
    }

    _handleMediaKey(event) {
        if (this.destroyed) return;
        const detail = event?.detail || {};
        const key = normalizeRemoteKey(detail.key);
        const type = detail.type === 'keyup' ? 'keyup' : 'keydown';
        if (!key) return;

        if (this.learningCallback) {
            if (type !== 'keydown' || detail.repeat) return;
            const callback = this.learningCallback;
            this.setLearningCallback(null);
            callback({ key, label: formatRemoteKeyLabel(key) });
            return;
        }

        this._dispatchKey(key, type, Boolean(detail.repeat));
    }

    _dispatchKey(key, type, repeat) {
        if (type === 'keyup' && this.holdRecordKey && key === this.holdRecordKey) {
            this._releaseHoldRecording();
            return true;
        }

        if (this._activeTab() === 'settings') return false;

        const action = this.findActionForKey(key);
        if (!action) return false;

        if (action === 'record') {
            const { recordMode } = this.getRemoteConfig();
            if (recordMode === 'hold') {
                if (type === 'keydown' && !repeat) {
                    this._startHoldRecording(key);
                } else if (type === 'keyup') {
                    this._releaseHoldRecording();
                }
            } else if (type === 'keydown' && !repeat) {
                this.triggerRecordToggle();
            }
            return true;
        }

        if (type !== 'keydown') return true;

        if (action === 'play_pause') {
            if (!repeat) this.triggerPlayPause();
            return true;
        }
        if (action === 'speed_up') {
            this.stepPlaybackSpeed(1);
            return true;
        }
        if (action === 'speed_down') {
            this.stepPlaybackSpeed(-1);
            return true;
        }
        return false;
    }

    _activeTab() {
        return window.currentTab || 'analysis';
    }

    _recorderForTab(tab) {
        if (tab === 'analysis') return window.recorder || null;
        if (tab === 'prosody') return window.prosodyLabRecorder || null;
        if (tab === 'comparison') return window.comparisonLab || null;
        return null;
    }

    triggerRecordToggle() {
        const recorder = this._recorderForTab(this._activeTab());
        if (!recorder) return;
        if (recorder.isRecording || recorder.isStartingRecording) {
            recorder.stopRecording?.();
        } else {
            recorder.startRecording?.();
        }
    }

    _startHoldRecording(key) {
        const tab = this._activeTab();
        const recorder = this._recorderForTab(tab);
        if (!recorder || recorder.isRecording) return;
        this.holdRecordTab = tab;
        this.holdRecordKey = key;
        recorder.startRecording?.();
    }

    _releaseHoldRecording() {
        if (!this.holdRecordTab) return;
        const recorder = this._recorderForTab(this.holdRecordTab);
        this.holdRecordTab = null;
        this.holdRecordKey = null;
        if (recorder?.isRecording) {
            recorder.stopRecording?.();
        }
    }

    triggerPlayPause() {
        const tab = this._activeTab();
        if (tab === 'analysis') {
            const audio = document.querySelector('#feedback-container audio');
            if (!audio || !(audio.src || audio.getAttribute('src'))) return;
            if (audio.paused || audio.ended) {
                const promise = audio.play?.();
                promise?.catch?.(() => {});
            } else {
                audio.pause?.();
            }
            return;
        }

        if (tab === 'comparison') {
            const lab = window.comparisonLab;
            if (!lab?.handlePlayPause) return;
            if (lab.referenceLoaded) {
                lab.handlePlayPause('reference');
            } else if (lab.studentLoaded) {
                lab.handlePlayPause('student');
            }
            return;
        }

        if (tab === 'prosody') {
            const livePanel = document.getElementById('prosody-panel-live');
            if (livePanel && !livePanel.classList.contains('hidden')) {
                document.getElementById('prosody-flow-play-btn')?.click();
                return;
            }
            if (window.prosodyLabRecorder?.audioPlayer?.isPlaying) {
                window.prosodyLabRecorder.stopAllAudio?.();
                return;
            }
            const learnerBtn = document.getElementById('prosody-play-learner-btn');
            const refBtn = document.getElementById('prosody-play-ref-btn');
            (learnerBtn || refBtn)?.click();
        }
    }

    stepPlaybackSpeed(delta) {
        const tab = this._activeTab();
        let select = null;
        if (tab === 'analysis') {
            select = document.querySelector('#feedback-container [data-playback] select');
        } else if (tab === 'comparison') {
            select = document.getElementById('comparison-speed');
        }
        if (!select || select.disabled || !select.options?.length) return;
        const nextIndex = Math.max(0, Math.min(select.options.length - 1, select.selectedIndex + delta));
        if (nextIndex === select.selectedIndex) return;
        select.selectedIndex = nextIndex;
        select.dispatchEvent(new Event('change', { bubbles: true }));
    }
}

if (typeof document !== 'undefined') {
    document.addEventListener('DOMContentLoaded', () => {
        window.remoteController?.destroy?.();
        window.remoteController = new PresenterRemoteController();
    });
}
