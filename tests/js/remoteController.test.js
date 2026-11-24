import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import {
    PresenterRemoteController,
    formatRemoteKeyLabel,
    normalizeRemoteKey,
} from '../../static/js/remote_controller.js';

describe('PresenterRemoteController', () => {
    let controller;

    beforeEach(() => {
        document.body.innerHTML = `
            <div id="feedback-container">
                <div data-playback>
                    <audio src="blob:test"></audio>
                    <select>
                        <option value="0.3">0.3x</option>
                        <option value="0.5" selected>0.5x</option>
                        <option value="0.75">0.75x</option>
                        <option value="1">1x</option>
                    </select>
                </div>
            </div>
            <select id="comparison-speed">
                <option value="0.25">0.25x</option>
                <option value="0.5" selected>0.5x</option>
                <option value="1">1x</option>
            </select>
            <input id="target_text" type="text" value="Hello">
        `;
        window.currentTab = 'analysis';
        window.__SPEECH_GUIDER_SETTINGS__ = {
            remote_enabled: true,
            remote_record_mode: 'toggle',
            remote_bindings: {
                record: 'PageDown',
                play_pause: 'PageUp',
                speed_up: 'AudioVolumeUp',
                speed_down: 'AudioVolumeDown',
            },
        };
        controller = new PresenterRemoteController();
    });

    afterEach(() => {
        controller?.destroy();
        delete window.recorder;
        delete window.prosodyLabRecorder;
        delete window.comparisonLab;
        delete window.currentTab;
        delete window.__SPEECH_GUIDER_SETTINGS__;
        delete window.__TAURI_INTERNALS__;
        vi.restoreAllMocks();
    });

    it('normalizes and formats keyboard and hardware media keys', () => {
        expect(normalizeRemoteKey({ key: ' ' })).toBe('Space');
        expect(normalizeRemoteKey({ key: 'B' })).toBe('b');
        expect(normalizeRemoteKey({ key: 'Shift' })).toBe('');
        expect(normalizeRemoteKey('AudioVolumeUp')).toBe('AudioVolumeUp');

        expect(formatRemoteKeyLabel('')).toBe('Not assigned');
        expect(formatRemoteKeyLabel('AudioVolumeUp')).toBe('Volume Up');
        expect(formatRemoteKeyLabel('AudioVolumeDown')).toBe('Volume Down');
        expect(formatRemoteKeyLabel('PageDown')).toBe('Page Down');
        expect(formatRemoteKeyLabel('b')).toBe('B');
    });

    it('toggles recording across Analysis, Prosody Lab, and Comparison Lab in toggle mode', () => {
        const analysisRec = {
            isRecording: false,
            startRecording: vi.fn(() => { analysisRec.isRecording = true; }),
            stopRecording: vi.fn(() => { analysisRec.isRecording = false; }),
        };
        const prosodyRec = {
            isRecording: false,
            startRecording: vi.fn(() => { prosodyRec.isRecording = true; }),
            stopRecording: vi.fn(() => { prosodyRec.isRecording = false; }),
        };
        const compRec = {
            isRecording: false,
            startRecording: vi.fn(() => { compRec.isRecording = true; }),
            stopRecording: vi.fn(() => { compRec.isRecording = false; }),
        };
        window.recorder = analysisRec;
        window.prosodyLabRecorder = prosodyRec;
        window.comparisonLab = compRec;

        // Analysis toggle on / off
        document.dispatchEvent(new KeyboardEvent('keydown', { key: 'PageDown', cancelable: true }));
        expect(analysisRec.startRecording).toHaveBeenCalledOnce();
        document.dispatchEvent(new KeyboardEvent('keydown', { key: 'PageDown', cancelable: true }));
        expect(analysisRec.stopRecording).toHaveBeenCalledOnce();

        // Prosody toggle
        window.currentTab = 'prosody';
        document.dispatchEvent(new KeyboardEvent('keydown', { key: 'PageDown', cancelable: true }));
        expect(prosodyRec.startRecording).toHaveBeenCalledOnce();

        // Comparison toggle
        window.currentTab = 'comparison';
        document.dispatchEvent(new KeyboardEvent('keydown', { key: 'PageDown', cancelable: true }));
        expect(compRec.startRecording).toHaveBeenCalledOnce();
    });

    it('starts on keydown and stops on keyup or blur in hold mode', () => {
        window.__SPEECH_GUIDER_SETTINGS__.remote_record_mode = 'hold';
        const analysisRec = {
            isRecording: false,
            startRecording: vi.fn(() => { analysisRec.isRecording = true; }),
            stopRecording: vi.fn(() => { analysisRec.isRecording = false; }),
        };
        window.recorder = analysisRec;

        document.dispatchEvent(new KeyboardEvent('keydown', { key: 'PageDown', cancelable: true }));
        expect(analysisRec.startRecording).toHaveBeenCalledOnce();
        document.dispatchEvent(new KeyboardEvent('keyup', { key: 'PageDown', cancelable: true }));
        expect(analysisRec.stopRecording).toHaveBeenCalledOnce();

        // Release on blur if keyup is missed
        document.dispatchEvent(new KeyboardEvent('keydown', { key: 'PageDown', cancelable: true }));
        expect(analysisRec.isRecording).toBe(true);
        window.dispatchEvent(new Event('blur'));
        expect(analysisRec.stopRecording).toHaveBeenCalledTimes(2);
    });

    it('steps playback speed with Volume Up / Volume Down via native media-key events', () => {
        const analysisSelect = document.querySelector('#feedback-container [data-playback] select');
        const changeSpy = vi.fn();
        analysisSelect.addEventListener('change', changeSpy);

        window.dispatchEvent(new CustomEvent('speechguider:mediakey', {
            detail: { key: 'AudioVolumeUp', type: 'keydown', repeat: false },
        }));
        expect(analysisSelect.value).toBe('0.75');
        expect(changeSpy).toHaveBeenCalledOnce();

        window.dispatchEvent(new CustomEvent('speechguider:mediakey', {
            detail: { key: 'AudioVolumeDown', type: 'keydown', repeat: false },
        }));
        expect(analysisSelect.value).toBe('0.5');

        // Also works in Comparison Lab
        window.currentTab = 'comparison';
        const compSelect = document.getElementById('comparison-speed');
        window.dispatchEvent(new CustomEvent('speechguider:mediakey', {
            detail: { key: 'AudioVolumeUp', type: 'keydown', repeat: false },
        }));
        expect(compSelect.value).toBe('1');
    });

    it('toggles Analysis audio playback on play_pause key', () => {
        const audio = document.querySelector('#feedback-container audio');
        let paused = true;
        Object.defineProperty(audio, 'paused', { configurable: true, get: () => paused });
        Object.defineProperty(audio, 'ended', { configurable: true, get: () => false });
        const playSpy = vi.spyOn(audio, 'play').mockImplementation(() => {
            paused = false;
            return Promise.resolve();
        });
        const pauseSpy = vi.spyOn(audio, 'pause').mockImplementation(() => {
            paused = true;
        });

        document.dispatchEvent(new KeyboardEvent('keydown', { key: 'PageUp', cancelable: true }));
        expect(playSpy).toHaveBeenCalledOnce();

        document.dispatchEvent(new KeyboardEvent('keydown', { key: 'PageUp', cancelable: true }));
        expect(pauseSpy).toHaveBeenCalledOnce();
    });

    it('captures native media keys and Escape cancellation in learning mode and syncs Tauri IPC', async () => {
        const invoke = vi.fn().mockResolvedValue({ supported: true, permission_granted: true, tap_active: true });
        window.__TAURI_INTERNALS__ = { invoke };

        const learned = vi.fn();
        controller.setLearningCallback(learned);
        expect(invoke).toHaveBeenCalledWith('set_media_key_capture', {
            learning: true,
            boundKeys: ['AudioVolumeUp', 'AudioVolumeDown'],
        });

        window.dispatchEvent(new CustomEvent('speechguider:mediakey', {
            detail: { key: 'AudioVolumeUp', type: 'keydown', repeat: false },
        }));
        expect(learned).toHaveBeenCalledWith({ key: 'AudioVolumeUp', label: 'Volume Up' });

        const cancelled = vi.fn();
        controller.setLearningCallback(cancelled);
        document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', cancelable: true }));
        expect(cancelled).toHaveBeenCalledWith({ cancelled: true });
    });

    it('ignores keyboard remote keys while typing inside text inputs', () => {
        const analysisRec = { isRecording: false, startRecording: vi.fn(), stopRecording: vi.fn() };
        window.recorder = analysisRec;
        const input = document.getElementById('target_text');

        input.dispatchEvent(new KeyboardEvent('keydown', { key: 'PageDown', bubbles: true, cancelable: true }));
        expect(analysisRec.startRecording).not.toHaveBeenCalled();
    });
});
