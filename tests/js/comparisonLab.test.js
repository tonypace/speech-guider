import { afterEach, describe, expect, it, vi } from 'vitest';
import { MockMediaRecorder } from './mocks/webAudioMock.js';
import { ComparisonLab } from '../../static/js/comparison_lab.js';
import { SSLComparisonController } from '../../static/js/ssl_comparison_controller.js';

function deferred() {
    let resolve;
    const promise = new Promise(done => { resolve = done; });
    return { promise, resolve };
}

describe('comparison request lifecycle', () => {
    afterEach(() => { vi.useRealTimers(); vi.unstubAllGlobals(); });

    it('ignores reference decode completion after text changes', async () => {
        document.body.innerHTML = '<input id="comparison-target-text"><div id="comparison-ref-status"></div>';
        const lab = new ComparisonLab();
        lab.debounceDelay = 1;
        const decoding = deferred();
        lab.controller = {
            referenceFrames: [], clearTrack: vi.fn(),
            loadReference: vi.fn(async (frames, _audio, isCurrent) => {
                await decoding.promise;
                if (isCurrent()) lab.controller.referenceFrames = frames;
            }),
        };
        globalThis.fetch = vi.fn().mockResolvedValue({
            ok: true, json: async () => ({ frames: [{ id: 'old' }], audio_base64: 'AA==' }),
        });
        lab.currentTargetText = 'old';
        const loading = lab.generateReference('old');
        await Promise.resolve();
        lab.handleTextInput({ target: { value: 'new' } });
        decoding.resolve();
        await loading;
        expect(lab.referenceLoaded).toBe(false);
        expect(lab.controller.referenceFrames).toEqual([]);
    });

    it('aborts old fetch and keeps newer response as the committed reference', async () => {
        const lab = new ComparisonLab();
        const first = deferred();
        const second = deferred();
        lab.controller = { loadReference: vi.fn(async frames => { lab.frames = frames; }) };
        globalThis.fetch = vi.fn()
            .mockImplementationOnce(() => first.promise)
            .mockImplementationOnce(() => second.promise);
        lab.currentTargetText = 'first';
        const oldRequest = lab.generateReference('first');
        lab.currentRequestId++;
        lab.currentTargetText = 'second';
        const newRequest = lab.generateReference('second', lab.currentRequestId);
        second.resolve({ ok: true, json: async () => ({ frames: ['second'], audio_base64: null }) });
        await newRequest;
        first.resolve({ ok: true, json: async () => ({ frames: ['first'], audio_base64: null }) });
        await oldRequest;
        expect(lab.frames).toEqual(['second']);
        expect(lab.referenceLoaded).toBe(true);
    });

    it('decodes captured student blob into audio buffer', async () => {
        const controller = new SSLComparisonController();
        controller.audioContext = { decodeAudioData: vi.fn().mockResolvedValue({ duration: 2 }) };
        const blob = new Blob(['audio'], { type: 'audio/webm' });
        await controller.loadStudent([{ jaw: 0.5 }], blob);
        expect(controller.audioBuffers.student.duration).toBe(2);
    });

    it('requests microphone only once while permission is pending', async () => {
        vi.stubGlobal('MediaRecorder', MockMediaRecorder);
        const lab = new ComparisonLab();
        const permission = deferred();
        navigator.mediaDevices = { getUserMedia: vi.fn(() => permission.promise) };
        const first = lab.startRecording();
        const second = lab.startRecording();
        expect(navigator.mediaDevices.getUserMedia).toHaveBeenCalledOnce();
        permission.resolve({ getTracks: () => [{ stop: vi.fn() }] });
        await Promise.all([first, second]);
        expect(lab.isRecording).toBe(true);
        lab.destroy();
    });
});

describe('comparison disposal', () => {
    it('releases late microphone permission without starting capture', async () => {
        const lab = new ComparisonLab();
        const permission = deferred();
        const stop = vi.fn();
        navigator.mediaDevices = { getUserMedia: vi.fn(() => permission.promise) };
        const pending = lab.startRecording();
        lab.destroy();
        permission.resolve({ getTracks: () => [{ stop }] });
        await pending;
        expect(stop).toHaveBeenCalledOnce();
        expect(lab.mediaRecorder).toBeNull();
        expect(lab.isRecording).toBe(false);
    });

    it('ignores obsolete student decode completion', async () => {
        const controller = new SSLComparisonController();
        const decoding = deferred();
        let current = true;
        controller.audioContext = { decodeAudioData: () => decoding.promise };
        const load = controller.loadStudent(['old'], 'AA==', () => current);
        current = false;
        decoding.resolve({ duration: 1 });
        expect(await load).toBe(false);
        expect(controller.studentFrames).toEqual([]);
        expect(controller.audioBuffers.student).toBeNull();
    });

    it('closes playback context and invalidates pending decode on disposal', async () => {
        const controller = new SSLComparisonController();
        const decoding = deferred();
        const close = vi.fn().mockResolvedValue();
        controller.audioContext = { decodeAudioData: () => decoding.promise, close };
        const load = controller.loadReference(['old'], 'AA==');
        controller.destroy();
        decoding.resolve({ duration: 1 });
        expect(await load).toBe(false);
        expect(controller.referenceFrames).toEqual([]);
        expect(close).toHaveBeenCalledOnce();
    });
});
