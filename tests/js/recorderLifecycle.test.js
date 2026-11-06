import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { IntercomRecorder } from '../../static/js/recorder.js';
import { ProsodyLabRecorder } from '../../static/js/prosody_lab.js';
import { MockMediaRecorder, MockAudioContext } from './mocks/webAudioMock.js';

function deferred() {
    let resolve;
    const promise = new Promise((done) => { resolve = done; });
    return { promise, resolve };
}

describe.each([IntercomRecorder, ProsodyLabRecorder])('%s capture ownership', (Recorder) => {
    let recorder;
    let stop;
    let stream;
    beforeEach(() => {
        document.body.innerHTML = '<button id="record-btn"></button><button id="prosody-record-btn"></button>';
        stop = vi.fn();
        stream = { getTracks: () => [{ stop }] };
        vi.stubGlobal('MediaRecorder', MockMediaRecorder);
        vi.stubGlobal('AudioContext', MockAudioContext);
        navigator.mediaDevices = { getUserMedia: vi.fn().mockResolvedValue(stream) };
        window.currentTab = 'prosody';
        recorder = new Recorder({ location: { protocol: 'https:', hostname: 'localhost' } });
    });
    afterEach(() => {
        recorder.destroy();
        vi.unstubAllGlobals();
    });

    it('initializes once, then destroys capture and listeners without submission', async () => {
        const analysis = vi.spyOn(recorder, 'sendForAnalysis').mockResolvedValue();
        await Promise.all([recorder.init(), recorder.init()]);
        await recorder.init();
        expect(navigator.mediaDevices.getUserMedia).toHaveBeenCalledOnce();
        const context = recorder.audioContext;
        const close = vi.spyOn(context, 'close');
        recorder.startRecording();
        expect(recorder.isRecording).toBe(true);
        recorder.destroy();
        recorder.destroy();
        expect(stop).toHaveBeenCalledOnce();
        expect(close).toHaveBeenCalledOnce();
        expect(analysis).not.toHaveBeenCalled();
        expect(recorder.eventListeners).toHaveLength(0);
        expect(recorder.isRecording).toBe(false);
        expect(recorder.animationId).toBeNull();
        recorder.recordBtn.click();
        expect(recorder.isRecording).toBe(false);
    });

    it('disposes late permission results after destroy', async () => {
        const permission = deferred();
        navigator.mediaDevices.getUserMedia.mockReturnValue(permission.promise);
        const init = recorder.init();
        recorder.destroy();
        permission.resolve(stream);
        await init;
        expect(stop).toHaveBeenCalledOnce();
        expect(recorder.mediaRecorder).toBeNull();
        expect(recorder.audioContext).toBeNull();
    });

    it('cleans partial capture when visualizer construction fails', async () => {
        vi.spyOn(recorder, 'setupVisualizer').mockImplementation(() => { throw new Error('audio failed'); });
        await recorder.init();
        expect(stop).toHaveBeenCalledOnce();
        expect(recorder.stream).toBeNull();
        expect(recorder.mediaRecorder).toBeNull();
    });
});
