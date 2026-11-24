import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { getSettings, listMicrophones, microphoneError, openMicrophone } from '../../static/js/microphone.js';
import '../../static/js/settings.js';
import { MockAudioContext, MockMediaRecorder } from './mocks/webAudioMock.js';

function renderSettingsDom() {
    document.body.innerHTML = `
        <form id="settings-form">
            <input id="settings-mic-enabled" type="checkbox" checked>
            <select id="settings-mic-device">
                <option value="">System default</option>
            </select>
            <button id="settings-refresh-devices" type="button">Refresh microphones</button>
            <button id="settings-mic-test" type="button">Test microphone</button>
            <meter id="settings-mic-level" min="0" max="1" value="0"></meter>
            <p id="settings-mic-status" role="status"></p>
            <audio id="settings-test-playback" controls hidden></audio>
            <input id="settings-contact" type="checkbox" checked>
            <input id="settings-remote-enabled" type="checkbox" checked>
            <select id="settings-remote-record-mode">
                <option value="toggle">Toggle</option>
                <option value="hold">Hold</option>
            </select>
            <span data-remote-binding="record">Not assigned</span>
            <button type="button" data-remote-assign="record">Assign button</button>
            <button type="button" data-remote-clear="record">Clear</button>
            <span data-remote-binding="play_pause">Not assigned</span>
            <button type="button" data-remote-assign="play_pause">Assign button</button>
            <button type="button" data-remote-clear="play_pause">Clear</button>
            <span data-remote-binding="speed_up">Not assigned</span>
            <button type="button" data-remote-assign="speed_up">Assign button</button>
            <button type="button" data-remote-clear="speed_up">Clear</button>
            <span data-remote-binding="speed_down">Not assigned</span>
            <button type="button" data-remote-assign="speed_down">Assign button</button>
            <button type="button" data-remote-clear="speed_down">Clear</button>
            <p id="settings-remote-status" role="status"></p>
            <div id="settings-remote-macos-box" class="hidden">
                <p id="settings-remote-permission-status"></p>
                <button id="settings-remote-permission-btn" type="button">Enable</button>
                <button id="settings-remote-permission-refresh" type="button">Re-check</button>
            </div>
            <button id="settings-save" type="submit">Save settings</button>
            <p id="settings-save-status" role="status"></p>
        </form>
    `;
}

async function mountSettings({ settings = {}, devices = [], getUserMedia } = {}) {
    renderSettingsDom();
    window.__SPEECH_GUIDER_SETTINGS__ = settings;
    const stop = vi.fn();
    const defaultStream = {
        getTracks: () => [{ stop }],
        getAudioTracks: () => [{ label: 'Built-in Mic', stop }],
    };
    Object.defineProperty(navigator, 'mediaDevices', {
        configurable: true,
        writable: true,
        value: {
            enumerateDevices: vi.fn().mockResolvedValue(devices),
            getUserMedia: getUserMedia || vi.fn().mockResolvedValue(defaultStream),
        },
    });
    document.dispatchEvent(new Event('DOMContentLoaded'));
    // Allow renderDevices() microtask chain from DOMContentLoaded to settle.
    await vi.waitFor(() => expect(navigator.mediaDevices.enumerateDevices).toHaveBeenCalled());
    return { stop, defaultStream };
}

describe('microphone utilities', () => {
    afterEach(() => {
        delete window.__SPEECH_GUIDER_SETTINGS__;
        vi.restoreAllMocks();
        vi.unstubAllGlobals();
    });

    it('reads shared global settings with empty object fallback', () => {
        delete window.__SPEECH_GUIDER_SETTINGS__;
        expect(getSettings()).toEqual({});

        const configured = { microphone_enabled: false, microphone_device_id: 'mic-1' };
        window.__SPEECH_GUIDER_SETTINGS__ = configured;
        expect(getSettings()).toBe(configured);
    });

    it('lists only audioinput devices and handles missing mediaDevices', async () => {
        Object.defineProperty(navigator, 'mediaDevices', {
            configurable: true,
            writable: true,
            value: {
                enumerateDevices: vi.fn().mockResolvedValue([
                    { kind: 'audioinput', deviceId: 'mic-1', label: 'USB Mic' },
                    { kind: 'audiooutput', deviceId: 'spk-1', label: 'Speakers' },
                    { kind: 'videoinput', deviceId: 'cam-1', label: 'Camera' },
                ]),
            },
        });
        expect(await listMicrophones()).toEqual([
            { kind: 'audioinput', deviceId: 'mic-1', label: 'USB Mic' },
        ]);

        Object.defineProperty(navigator, 'mediaDevices', {
            configurable: true,
            writable: true,
            value: undefined,
        });
        expect(await listMicrophones()).toEqual([]);
    });

    it('maps microphone error names to user-facing guidance', () => {
        expect(microphoneError({ name: 'NotAllowedError' }))
            .toBe('Microphone permission was denied. Check browser or macOS permissions.');
        expect(microphoneError({ name: 'NotFoundError' }))
            .toBe('Microphone unavailable. Reconnect it or choose System default in Settings.');
        expect(microphoneError({ name: 'OverconstrainedError' }))
            .toBe('Microphone unavailable. Reconnect it or choose System default in Settings.');
        expect(microphoneError(new Error('Hardware busy'))).toBe('Hardware busy');
        expect(microphoneError({})).toBe('Could not open the microphone.');
    });

    it('rejects openMicrophone when disabled or mediaDevices is unavailable', async () => {
        await expect(openMicrophone({ microphone_enabled: false }))
            .rejects.toThrow('Microphone is off in Settings.');

        Object.defineProperty(navigator, 'mediaDevices', {
            configurable: true,
            writable: true,
            value: {},
        });
        await expect(openMicrophone({ microphone_enabled: true }))
            .rejects.toThrow('Microphone access is unavailable.');
    });

    it('disables browser voice processing and resolves unique label fallback across origin changes', async () => {
        const getUserMedia = vi.fn().mockResolvedValue({ getTracks: () => [] });
        const enumerateDevices = vi.fn().mockResolvedValue([
            { kind: 'audioinput', deviceId: 'new-origin-id', label: 'Studio USB Mic' },
            { kind: 'audioinput', deviceId: 'other-id', label: 'Built-in Mic' },
        ]);
        Object.defineProperty(navigator, 'mediaDevices', {
            configurable: true,
            writable: true,
            value: { enumerateDevices, getUserMedia },
        });

        await openMicrophone({
            microphone_enabled: true,
            microphone_device_id: 'old-origin-id',
            microphone_label: 'Studio USB Mic',
        });

        expect(getUserMedia).toHaveBeenCalledWith({
            audio: {
                autoGainControl: false,
                noiseSuppression: false,
                echoCancellation: false,
                deviceId: { exact: 'new-origin-id' },
            },
        });
    });

    it('keeps saved deviceId when duplicate labels are ambiguous', async () => {
        const getUserMedia = vi.fn().mockResolvedValue({ getTracks: () => [] });
        const enumerateDevices = vi.fn().mockResolvedValue([
            { kind: 'audioinput', deviceId: 'id-a', label: 'USB Mic' },
            { kind: 'audioinput', deviceId: 'id-b', label: 'USB Mic' },
        ]);
        Object.defineProperty(navigator, 'mediaDevices', {
            configurable: true,
            writable: true,
            value: { enumerateDevices, getUserMedia },
        });

        await openMicrophone({
            microphone_enabled: true,
            microphone_device_id: 'saved-id',
            microphone_label: 'USB Mic',
        });

        expect(getUserMedia).toHaveBeenCalledWith({
            audio: {
                autoGainControl: false,
                noiseSuppression: false,
                echoCancellation: false,
                deviceId: { exact: 'saved-id' },
            },
        });
    });
});

describe('settings panel behavior', () => {
    beforeEach(() => {
        vi.stubGlobal('MediaRecorder', MockMediaRecorder);
        vi.stubGlobal('AudioContext', MockAudioContext);
    });

    afterEach(() => {
        window.dispatchEvent(new CustomEvent('speechguider:tabchange', { detail: 'analysis' }));
        delete window.__SPEECH_GUIDER_SETTINGS__;
        vi.useRealTimers();
        vi.restoreAllMocks();
        vi.unstubAllGlobals();
    });

    it('populates devices, resolves unique label match, and marks unavailable saved devices', async () => {
        await mountSettings({
            settings: {
                contact_enabled: false,
                microphone_enabled: true,
                microphone_device_id: 'stale-id',
                microphone_label: 'Headset Mic',
            },
            devices: [
                { kind: 'audioinput', deviceId: 'fresh-id', label: 'Headset Mic' },
                { kind: 'audioinput', deviceId: 'anon-id', label: '' },
            ],
        });

        const select = document.getElementById('settings-mic-device');
        expect(document.getElementById('settings-contact').checked).toBe(false);
        expect(document.getElementById('settings-mic-enabled').checked).toBe(true);
        expect(select.value).toBe('fresh-id');
        expect(Array.from(select.options).map((o) => o.textContent)).toEqual([
            'System default',
            'Headset Mic',
            'Microphone 2',
        ]);

        // Now mount with missing saved device so an "(unavailable)" fallback option is added.
        await mountSettings({
            settings: {
                microphone_enabled: true,
                microphone_device_id: 'disconnected-id',
                microphone_label: 'Removed Mic',
            },
            devices: [{ kind: 'audioinput', deviceId: 'builtin-id', label: 'Built-in Mic' }],
        });
        const fallbackSelect = document.getElementById('settings-mic-device');
        expect(fallbackSelect.value).toBe('disconnected-id');
        expect(Array.from(fallbackSelect.options).map((o) => o.textContent)).toContain('Removed Mic (unavailable)');
    });

    it('disables microphone sub-controls when microphone toggle is unchecked', async () => {
        await mountSettings({
            settings: { microphone_enabled: true },
            devices: [],
        });

        const enabled = document.getElementById('settings-mic-enabled');
        const devices = document.getElementById('settings-mic-device');
        const refresh = document.getElementById('settings-refresh-devices');
        const test = document.getElementById('settings-mic-test');

        enabled.checked = false;
        enabled.dispatchEvent(new Event('change'));

        expect(devices.disabled).toBe(true);
        expect(refresh.disabled).toBe(true);
        expect(test.disabled).toBe(true);
    });

    it('refreshes device list, stops temporary stream tracks, and surfaces microphoneError on denial', async () => {
        const stop = vi.fn();
        const stream = { getTracks: () => [{ stop }], getAudioTracks: () => [] };
        const getUserMedia = vi.fn().mockResolvedValueOnce(stream);

        await mountSettings({
            settings: { microphone_enabled: true },
            devices: [{ kind: 'audioinput', deviceId: 'mic-1', label: 'Desk Mic' }],
            getUserMedia,
        });

        navigator.mediaDevices.enumerateDevices.mockResolvedValueOnce([
            { kind: 'audioinput', deviceId: 'mic-1', label: 'Desk Mic' },
            { kind: 'audioinput', deviceId: 'mic-2', label: 'Boom Mic' },
        ]);

        document.getElementById('settings-refresh-devices').click();
        await vi.waitFor(() => {
            expect(document.getElementById('settings-mic-status').textContent).toBe('Microphone list refreshed.');
        });
        expect(stop).toHaveBeenCalledOnce();
        expect(Array.from(document.getElementById('settings-mic-device').options).map((o) => o.value))
            .toEqual(['', 'mic-1', 'mic-2']);

        getUserMedia.mockRejectedValueOnce(Object.assign(new Error('Denied'), { name: 'NotAllowedError' }));
        document.getElementById('settings-refresh-devices').click();
        await vi.waitFor(() => {
            expect(document.getElementById('settings-mic-status').textContent)
                .toBe('Microphone permission was denied. Check browser or macOS permissions.');
        });
    });

    it('persists settings via PUT /api/settings and dispatches speechguider:settingschange', async () => {
        const previous = {
            contact_enabled: true,
            microphone_enabled: true,
            microphone_device_id: '',
            microphone_label: '',
        };
        await mountSettings({
            settings: previous,
            devices: [{ kind: 'audioinput', deviceId: 'mic-usb', label: 'USB Mic' }],
        });

        document.getElementById('settings-contact').checked = false;
        document.getElementById('settings-mic-device').value = 'mic-usb';

        const savedPayload = {
            contact_enabled: false,
            microphone_enabled: true,
            microphone_device_id: 'mic-usb',
            microphone_label: 'USB Mic',
            contact_available: true,
        };
        const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue({
            ok: true,
            json: async () => savedPayload,
        });

        const settingsEvents = [];
        const onChange = (event) => settingsEvents.push(event.detail);
        window.addEventListener('speechguider:settingschange', onChange);

        try {
            document.getElementById('settings-form').dispatchEvent(new Event('submit', { cancelable: true }));
            await vi.waitFor(() => {
                expect(document.getElementById('settings-save-status').textContent).toBe('Settings saved.');
            });

            expect(fetchMock).toHaveBeenCalledWith('/api/settings', {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    contact_enabled: false,
                    microphone_enabled: true,
                    microphone_device_id: 'mic-usb',
                    microphone_label: 'USB Mic',
                    remote_enabled: true,
                    remote_record_mode: 'toggle',
                    remote_bindings: {
                        record: '',
                        play_pause: '',
                        speed_up: '',
                        speed_down: '',
                    },
                }),
            });
            expect(window.__SPEECH_GUIDER_SETTINGS__).toEqual(savedPayload);
            expect(settingsEvents).toEqual([{ previous, next: savedPayload }]);
        } finally {
            window.removeEventListener('speechguider:settingschange', onChange);
        }
    });

    it('reports save errors without updating settings or dispatching settingschange', async () => {
        const previous = {
            contact_enabled: true,
            microphone_enabled: true,
            microphone_device_id: '',
            microphone_label: '',
        };
        await mountSettings({ settings: previous, devices: [] });

        vi.spyOn(globalThis, 'fetch').mockResolvedValue({ ok: false, status: 500 });
        const changeSpy = vi.fn();
        window.addEventListener('speechguider:settingschange', changeSpy);

        try {
            document.getElementById('settings-form').dispatchEvent(new Event('submit', { cancelable: true }));
            await vi.waitFor(() => {
                expect(document.getElementById('settings-save-status').textContent).toBe('Could not save settings.');
            });
            expect(window.__SPEECH_GUIDER_SETTINGS__).toEqual(previous);
            expect(changeSpy).not.toHaveBeenCalled();
        } finally {
            window.removeEventListener('speechguider:settingschange', changeSpy);
        }
    });

    it('records a 3-second microphone test and shows playback audio on completion', async () => {
        await mountSettings({
            settings: { microphone_enabled: true },
            devices: [{ kind: 'audioinput', deviceId: 'mic-1', label: 'Studio Mic' }],
        });
        vi.useFakeTimers();
        const playback = document.getElementById('settings-test-playback');
        const pauseSpy = vi.spyOn(playback, 'pause').mockImplementation(() => {});
        const createObjectURL = vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:test-audio');
        const revokeObjectURL = vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => {});

        document.getElementById('settings-mic-test').click();
        await vi.waitFor(() => {
            expect(document.getElementById('settings-mic-status').textContent)
                .toBe('Recording from Built-in Mic. Speak for three seconds.');
        });

        vi.advanceTimersByTime(3000);
        expect(createObjectURL).toHaveBeenCalledOnce();
        expect(playback.src).toBe('blob:test-audio');
        expect(playback.hidden).toBe(false);
        expect(document.getElementById('settings-mic-status').textContent)
            .toBe('Test ready from Built-in Mic. Play it back below.');

        window.dispatchEvent(new CustomEvent('speechguider:tabchange', { detail: 'analysis' }));
        expect(pauseSpy).toHaveBeenCalledOnce();
        expect(revokeObjectURL).toHaveBeenCalledWith('blob:test-audio');
        expect(playback.hidden).toBe(true);
    });

    it('learns remote button presses, resolves conflicts, clears bindings, and saves remote config', async () => {
        await mountSettings({
            settings: {
                contact_enabled: true,
                microphone_enabled: true,
                remote_enabled: true,
                remote_record_mode: 'toggle',
                remote_bindings: { record: 'PageDown', play_pause: '', speed_up: '', speed_down: '' },
            },
            devices: [],
        });

        expect(document.querySelector('[data-remote-binding="record"]').textContent).toBe('Page Down');

        // Assign PageDown to play_pause: should move binding off record.
        document.querySelector('[data-remote-assign="play_pause"]').click();
        expect(document.querySelector('[data-remote-assign="play_pause"]').textContent).toBe('Press remote button…');
        document.dispatchEvent(new KeyboardEvent('keydown', { key: 'PageDown', bubbles: true, cancelable: true }));

        expect(document.querySelector('[data-remote-binding="play_pause"]').textContent).toBe('Page Down');
        expect(document.querySelector('[data-remote-binding="record"]').textContent).toBe('Not assigned');

        // Assign record to F5 and switch to hold mode.
        document.querySelector('[data-remote-assign="record"]').click();
        document.dispatchEvent(new KeyboardEvent('keydown', { key: 'F5', bubbles: true, cancelable: true }));
        expect(document.querySelector('[data-remote-binding="record"]').textContent).toBe('F5');

        // Clear play_pause.
        document.querySelector('[data-remote-clear="play_pause"]').click();
        expect(document.querySelector('[data-remote-binding="play_pause"]').textContent).toBe('Not assigned');

        document.getElementById('settings-remote-record-mode').value = 'hold';

        const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue({
            ok: true,
            json: async () => ({
                contact_enabled: true,
                microphone_enabled: true,
                microphone_device_id: '',
                microphone_label: '',
                remote_enabled: true,
                remote_record_mode: 'hold',
                remote_bindings: { record: 'F5', play_pause: '', speed_up: '', speed_down: '' },
            }),
        });

        document.getElementById('settings-form').dispatchEvent(new Event('submit', { cancelable: true }));
        await vi.waitFor(() => {
            expect(document.getElementById('settings-save-status').textContent).toBe('Settings saved.');
        });

        const sentBody = JSON.parse(fetchMock.mock.calls[0][1].body);
        expect(sentBody.remote_record_mode).toBe('hold');
        expect(sentBody.remote_bindings).toEqual({
            record: 'F5',
            play_pause: '',
            speed_up: '',
            speed_down: '',
        });
    });
});
