import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { TauriController } from '../../static/js/tauri_controller.js';

describe('TauriController', () => {
    let addedDocumentListeners;
    let origAddEventListener;

    beforeEach(() => {
        addedDocumentListeners = [];
        origAddEventListener = document.addEventListener.bind(document);
        vi.spyOn(document, 'addEventListener').mockImplementation((type, handler, options) => {
            addedDocumentListeners.push([type, handler, options]);
            return origAddEventListener(type, handler, options);
        });
    });

    afterEach(() => {
        addedDocumentListeners.forEach(([type, handler, options]) => {
            document.removeEventListener(type, handler, options);
        });
        delete window.__SPEECH_GUIDER_TAURI__;
        delete window.__TAURI__;
        delete window.currentTab;
        delete window.currentErrors;
        delete window.switchTab;
        delete window.selectError;
        delete window.recorder;
        delete window.prosodyLabRecorder;
        delete window.tauriController;
        vi.useRealTimers();
        vi.restoreAllMocks();
    });

    describe('detectTauri', () => {
        it('returns false outside Tauri and skips clicker setup', () => {
            const controller = new TauriController();
            expect(controller.isTauri).toBe(false);
            expect(controller.detectTauri()).toBe(false);
            expect(addedDocumentListeners).toHaveLength(0);
        });

        it('detects __SPEECH_GUIDER_TAURI__ === true', () => {
            window.__SPEECH_GUIDER_TAURI__ = true;
            const controller = new TauriController();
            expect(controller.isTauri).toBe(true);
            expect(controller.detectTauri()).toBe(true);
            expect(addedDocumentListeners.map(([type]) => type)).toEqual(['keydown', 'keyup']);
        });

        it('detects legacy __TAURI__ object', () => {
            window.__TAURI__ = {};
            const controller = new TauriController();
            expect(controller.isTauri).toBe(true);
            expect(controller.detectTauri()).toBe(true);
        });
    });

    describe('handleLaunch', () => {
        it('launches pronunciation mode, switches to analysis tab, and loads errors', () => {
            window.switchTab = vi.fn();
            window.currentErrors = [{ word_context: 'hot' }, { word_context: 'today' }];
            const controller = new TauriController();
            controller.currentErrorIndex = 1;

            controller.handleLaunch('pronunciation');

            expect(controller.currentMode).toBe('pronunciation');
            expect(window.switchTab).toHaveBeenCalledWith('analysis');
            expect(controller.pronunciationErrors).toEqual(window.currentErrors);
            expect(controller.currentErrorIndex).toBe(-1);
        });

        it('launches comparison mode with null clicker mode and switches to comparison tab', () => {
            window.switchTab = vi.fn();
            const controller = new TauriController();
            controller.currentMode = 'pronunciation';

            controller.handleLaunch('comparison');

            expect(controller.currentMode).toBeNull();
            expect(window.switchTab).toHaveBeenCalledWith('comparison');
        });

        it('launches prosody mode and switches to prosody tab', () => {
            window.switchTab = vi.fn();
            const controller = new TauriController();
            controller.prosodySamples = [{ recording_id: 'old' }];
            controller.currentSampleIndex = 0;

            controller.handleLaunch('prosody');

            expect(controller.currentMode).toBe('prosody');
            expect(window.switchTab).toHaveBeenCalledWith('prosody');
            expect(controller.prosodySamples).toEqual([]);
            expect(controller.currentSampleIndex).toBe(-1);
        });

        it('ignores retired animation mode and unknown modes', () => {
            window.switchTab = vi.fn();
            const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
            const controller = new TauriController();

            controller.handleLaunch('animation');
            controller.handleLaunch('unknown');

            expect(controller.currentMode).toBeNull();
            expect(window.switchTab).not.toHaveBeenCalled();
            expect(warnSpy).toHaveBeenCalledTimes(2);
        });
    });

    describe('ArrowLeft and ArrowRight navigation', () => {
        it('cycles through pronunciation errors in both directions with wrap-around', () => {
            window.__SPEECH_GUIDER_TAURI__ = true;
            window.currentTab = 'analysis';
            window.selectError = vi.fn();
            window.currentErrors = [{ id: 0 }, { id: 1 }, { id: 2 }];

            const controller = new TauriController();
            controller.handleLaunch('pronunciation');

            const right1 = new KeyboardEvent('keydown', { key: 'ArrowRight', cancelable: true });
            document.dispatchEvent(right1);
            expect(right1.defaultPrevented).toBe(true);
            expect(window.selectError).toHaveBeenLastCalledWith(0);

            document.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowRight', cancelable: true }));
            expect(window.selectError).toHaveBeenLastCalledWith(1);

            document.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowRight', cancelable: true }));
            expect(window.selectError).toHaveBeenLastCalledWith(2);

            document.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowRight', cancelable: true }));
            expect(window.selectError).toHaveBeenLastCalledWith(0);

            const left1 = new KeyboardEvent('keydown', { key: 'ArrowLeft', cancelable: true });
            document.dispatchEvent(left1);
            expect(left1.defaultPrevented).toBe(true);
            expect(window.selectError).toHaveBeenLastCalledWith(2);
        });

        it('navigates prosody samples only when at least two exist', () => {
            window.__SPEECH_GUIDER_TAURI__ = true;
            window.currentTab = 'prosody';
            let history = [{ recording_id: 'only-one' }];
            window.prosodyLabRecorder = { loadHistory: () => history };

            const controller = new TauriController();
            const selectSample = vi.spyOn(controller, 'selectProsodySample');
            controller.handleLaunch('prosody');

            document.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowRight', cancelable: true }));
            expect(selectSample).not.toHaveBeenCalled();

            history = [{ recording_id: 's1' }, { recording_id: 's2' }];
            document.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowLeft', cancelable: true }));
            expect(selectSample).toHaveBeenLastCalledWith(1);

            document.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowRight', cancelable: true }));
            expect(selectSample).toHaveBeenLastCalledWith(0);
        });

        it('does not intercept clicker keys in comparison mode or when no mode is active', () => {
            window.__SPEECH_GUIDER_TAURI__ = true;
            window.selectError = vi.fn();
            window.currentErrors = [{ id: 0 }];
            const controller = new TauriController();

            const idleEvent = new KeyboardEvent('keydown', { key: 'ArrowRight', cancelable: true });
            document.dispatchEvent(idleEvent);
            expect(idleEvent.defaultPrevented).toBe(false);
            expect(window.selectError).not.toHaveBeenCalled();

            controller.handleLaunch('pronunciation');
            window.currentTab = 'comparison';
            const comparisonEvent = new KeyboardEvent('keydown', { key: 'ArrowRight', cancelable: true });
            document.dispatchEvent(comparisonEvent);
            expect(comparisonEvent.defaultPrevented).toBe(false);
            expect(window.selectError).not.toHaveBeenCalled();
        });
    });

    describe('Tab hold/release recording', () => {
        it('starts pronunciation recording on Tab keydown and stops on release >= 200ms', () => {
            vi.useFakeTimers();
            window.__SPEECH_GUIDER_TAURI__ = true;
            window.currentTab = 'analysis';
            window.recorder = {
                startRecording: vi.fn(),
                stopRecording: vi.fn(),
            };
            window.currentErrors = [];

            const controller = new TauriController();
            controller.handleLaunch('pronunciation');

            const down = new KeyboardEvent('keydown', { key: 'Tab', cancelable: true });
            document.dispatchEvent(down);
            expect(down.defaultPrevented).toBe(true);
            expect(controller.isRecording).toBe(true);
            expect(window.recorder.startRecording).toHaveBeenCalledOnce();

            // Repeated Tab keydown while already recording should be ignored.
            document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Tab', cancelable: true }));
            expect(window.recorder.startRecording).toHaveBeenCalledOnce();

            vi.advanceTimersByTime(250);
            document.dispatchEvent(new KeyboardEvent('keyup', { key: 'Tab', cancelable: true }));
            expect(controller.isRecording).toBe(false);
            expect(window.recorder.stopRecording).toHaveBeenCalledOnce();

            window.currentErrors = [{ word_context: 'hot' }];
            vi.advanceTimersByTime(2000);
            expect(controller.pronunciationErrors).toEqual([{ word_context: 'hot' }]);
            expect(controller.currentErrorIndex).toBe(-1);
        });

        it('starts and stops prosody recording on Tab hold/release', () => {
            vi.useFakeTimers();
            window.__SPEECH_GUIDER_TAURI__ = true;
            window.currentTab = 'prosody';
            window.prosodyLabRecorder = {
                startRecording: vi.fn(),
                stopRecording: vi.fn(),
            };

            const controller = new TauriController();
            controller.handleLaunch('prosody');

            document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Tab', cancelable: true }));
            expect(controller.isRecording).toBe(true);
            expect(window.prosodyLabRecorder.startRecording).toHaveBeenCalledOnce();

            vi.advanceTimersByTime(200);
            document.dispatchEvent(new KeyboardEvent('keyup', { key: 'Tab', cancelable: true }));
            expect(controller.isRecording).toBe(false);
            expect(window.prosodyLabRecorder.stopRecording).toHaveBeenCalledOnce();
        });

        it('routes short Tab tap (< 200ms) to handlePrimaryAction instead of handleRecordRelease', () => {
            vi.useFakeTimers();
            window.__SPEECH_GUIDER_TAURI__ = true;
            window.currentTab = 'analysis';
            window.recorder = { startRecording: vi.fn(), stopRecording: vi.fn() };

            const controller = new TauriController();
            const primarySpy = vi.spyOn(controller, 'handlePrimaryAction');
            const releaseSpy = vi.spyOn(controller, 'handleRecordRelease');
            controller.handleLaunch('pronunciation');

            document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Tab', cancelable: true }));
            vi.advanceTimersByTime(50);
            document.dispatchEvent(new KeyboardEvent('keyup', { key: 'Tab', cancelable: true }));

            expect(primarySpy).toHaveBeenCalledOnce();
            expect(releaseSpy).not.toHaveBeenCalled();
            expect(window.recorder.stopRecording).not.toHaveBeenCalled();
        });
    });
});
