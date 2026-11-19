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
        const decoding = deferred();
        lab.controller = {
            referenceFrames: [], clear: vi.fn(),
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
        await vi.waitFor(() => expect(lab.controller.loadReference).toHaveBeenCalledOnce());
        lab.handleTextInput({ target: { value: 'new' } });
        decoding.resolve();
        await loading;
        expect(lab.referenceLoaded).toBe(false);
        expect(lab.controller.referenceFrames).toEqual([]);
    });

    it('sends the complete sentence on submit and blocks duplicate submissions', async () => {
        document.body.innerHTML = `<form id="comparison-reference-form">
            <input id="comparison-target-text"><button id="comparison-generate">Generate reference</button>
        </form>`;
        const request = deferred();
        vi.stubGlobal('fetch', vi.fn(() => request.promise));
        const lab = new ComparisonLab();
        lab.init();
        const text = document.getElementById('comparison-target-text');
        text.value = 'A complete sentence.';
        text.dispatchEvent(new Event('input'));
        expect(fetch).not.toHaveBeenCalled();
        const form = document.getElementById('comparison-reference-form');
        form.requestSubmit();
        form.requestSubmit();
        expect(fetch).toHaveBeenCalledOnce();
        expect(JSON.parse(fetch.mock.calls[0][1].body).target_text).toBe(text.value);
        request.resolve({ ok: true, json: async () => ({ frames: [{}] }) });
        await vi.waitFor(() => expect(lab.referenceLoaded).toBe(true));
        lab.destroy();
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

    it('decodes the captured student blob for playback', async () => {
        const controller = new SSLComparisonController();
        const decode = vi.fn().mockResolvedValue(null);
        controller.audioContext = { decodeAudioData: decode };
        const blob = new Blob(['audio'], { type: 'audio/webm' });
        await controller.loadStudent([{ jaw: 0.5 }], blob);
        expect(new TextDecoder().decode(decode.mock.calls[0][0])).toBe('audio');
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
        expect(controller.tracks.student).toBeNull();
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

describe('desktop-compatible comparison upload', () => {
    afterEach(() => vi.unstubAllGlobals());

    it('uses the same mono 16 kHz WAV for the analysis upload and playback', async () => {
        const lab = new ComparisonLab();
        lab.currentTargetText = 'Practice sentence';
        lab.recordedChunks = [new Blob(['encoded audio'], { type: 'audio/mp4' })];
        const close = vi.fn().mockResolvedValue();
        vi.stubGlobal('AudioContext', vi.fn(function() {
            this.close = close;
            this.decodeAudioData = async () => ({
                length: 2, numberOfChannels: 2, sampleRate: 16000,
                getChannelData: (channel) => channel ? [1, -1] : [0, 0],
            });
        }));
        const frames = [{ jaw: 0.5 }];
        lab.controller = { loadStudent: vi.fn().mockResolvedValue(true) };
        const post = vi.fn().mockResolvedValue(new Response(JSON.stringify({ ssl_trajectory: { frames } })));
        vi.stubGlobal('fetch', post);
        await lab.processRecording();

        const [, request] = post.mock.calls[0];
        const uploaded = request.body.get('audio');
        const [, playback] = lab.controller.loadStudent.mock.calls[0];
        expect(uploaded.name).toBe('recording.wav');
        expect(uploaded.type).toBe('audio/wav');
        expect(request.body.get('target_text')).toBe('Practice sentence');
        const bytes = await uploaded.arrayBuffer();
        expect(bytes).toEqual(await playback.arrayBuffer());
        const wav = new DataView(bytes);
        expect(wav.getUint16(22, true)).toBe(1);
        expect(wav.getUint32(24, true)).toBe(16000);
        expect(wav.getInt16(44, true)).toBe(16383);
        expect(wav.getInt16(46, true)).toBe(-16384);
        expect(close).toHaveBeenCalledOnce();
        expect(lab.studentLoaded).toBe(true);
    });
});

describe('reference failure explanation', () => {
    afterEach(() => vi.restoreAllMocks());

    it('blocks oversized passages and allows them after shortening', () => {
        document.body.innerHTML = `<form id="comparison-reference-form">
            <input id="comparison-target-text" data-text-limit="1000">
            <button id="comparison-generate">Generate reference</button>
            <div id="comparison-ref-status"></div>
        </form>`;
        const request = vi.spyOn(globalThis, 'fetch');
        const lab = new ComparisonLab();
        lab.init();
        const input = document.getElementById('comparison-target-text');
        const generate = document.getElementById('comparison-generate');
        input.value = `"${'a'.repeat(998)}😀"`;
        input.dispatchEvent(new Event('input'));
        expect(generate.disabled).toBe(true);
        expect(document.getElementById('comparison-ref-status').textContent).toContain('1000 characters');
        document.getElementById('comparison-reference-form').requestSubmit();
        expect(request).not.toHaveBeenCalled();

        input.value = `"${'a'.repeat(997)}😀"`;
        input.dispatchEvent(new Event('input'));
        expect(generate.disabled).toBe(false);
        expect(input.getAttribute('aria-invalid')).toBe('false');
        lab.destroy();
    });

    it('shows a structured validation error instead of a bare 422', async () => {
        document.body.innerHTML = '<div id="comparison-ref-status"></div>';
        const lab = new ComparisonLab();
        vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify({
            detail: [{ loc: ['body', 'target_text'], msg: 'String should have at most 1000 characters' }],
        }), { status: 422 }));
        await lab.generateReference('a'.repeat(1001));
        expect(document.getElementById('comparison-ref-status').textContent)
            .toContain('String should have at most 1000 characters');
        lab.destroy();
    });

    it('shows server busy detail instead of a bare HTTP status', async () => {
        document.body.innerHTML = '<div id="comparison-ref-status"></div>';
        const lab = new ComparisonLab();
        const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue({
            ok: false, status: 503,
            json: async () => ({ detail: 'Server is currently processing another request.' }),
        });
        await lab.generateReference('hello');
        expect(document.querySelector('#comparison-ref-status').textContent)
            .toContain('Server is currently processing another request.');
        fetchMock.mockRestore();
        lab.destroy();
    });

    it('enables loop In/Out buttons once a track is loaded and displays active loop bounds', () => {
        document.body.innerHTML = `
            <input type="checkbox" id="comparison-loop" disabled>
            <button id="comparison-loop-in" disabled>In</button>
            <button id="comparison-loop-out" disabled>Out</button>
            <span id="comparison-loop-range"></span>
        `;
        const lab = new ComparisonLab();
        lab.init();

        const loopToggle = document.getElementById('comparison-loop');
        const loopInBtn = document.getElementById('comparison-loop-in');
        const loopOutBtn = document.getElementById('comparison-loop-out');
        const loopRange = document.getElementById('comparison-loop-range');

        expect(loopInBtn.disabled).toBe(true);
        expect(loopOutBtn.disabled).toBe(true);

        lab.referenceLoaded = true;
        lab.controller.getDuration = vi.fn(() => 4.0);
        lab.updateUIState();

        expect(loopInBtn.disabled).toBe(false);
        expect(loopOutBtn.disabled).toBe(false);

        lab.controller.referenceTime = 0.5;
        loopInBtn.click();
        lab.controller.referenceTime = 2.25;
        loopOutBtn.click();

        expect(lab.controller.loopRegion.start).toBe(0.5);
        expect(lab.controller.loopRegion.end).toBe(2.25);
        expect(loopRange.textContent).toContain('0:00.50 – 0:02.25');

        loopToggle.checked = true;
        loopToggle.dispatchEvent(new Event('change'));
        expect(lab.controller.loopRegion.enabled).toBe(true);
        expect(loopRange.textContent).toContain('(Active)');

        lab.destroy();
    });
});
