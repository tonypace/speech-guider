import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { SSLComparisonController } from '../../static/js/ssl_comparison_controller.js';

function audioBuffer(duration, ...speechRegions) {
    const sampleRate = 16000;
    const samples = new Float32Array(Math.round(duration * sampleRate));
    for (const [start, end] of speechRegions) {
        samples.fill(0.2, Math.round(start * sampleRate), Math.round(end * sampleRate));
    }
    return {
        duration, sampleRate, length: samples.length, numberOfChannels: 1,
        getChannelData: () => samples,
    };
}

// Drive playback through the media clock so sync tests include seeks and rate changes.
describe('SSL comparison playback lifecycle', () => {
    let controller;
    let context;
    let audioElements;
    const frames = Array.from({ length: 150 }, (_, index) => ({ index }));

    beforeEach(() => {
        audioElements = [];
        vi.stubGlobal('Audio', class {
            constructor() {
                this.currentTime = 0;
                this.playbackRate = 1;
                this.preservesPitch = false;
                this.ended = false;
                this.play = vi.fn().mockResolvedValue(undefined);
                this.pause = vi.fn();
                this.load = vi.fn();
                this.removeAttribute = vi.fn();
                audioElements.push(this);
            }
        });
        vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:comparison');
        vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => {});
        context = { decodeAudioData: vi.fn(), close: vi.fn() };
        controller = new SSLComparisonController();
        controller.audioContext = context;
        vi.spyOn(globalThis, 'requestAnimationFrame').mockReturnValue(1);
    });

    afterEach(() => {
        controller.destroy();
        vi.restoreAllMocks();
        vi.unstubAllGlobals();
    });

    async function load(type, buffer) {
        context.decodeAudioData.mockResolvedValueOnce(buffer);
        await (type === 'reference'
            ? controller.loadReference(frames, 'AA==')
            : controller.loadStudent(frames, new Blob(['audio'])));
        return audioElements.at(-1);
    }

    it('uses pitch-preserving audio at the selected playback speed', async () => {
        const audio = await load('reference', audioBuffer(2, [0, 2]));
        controller.setSpeed(0.5);
        controller.play('reference');
        expect(audio.preservesPitch).toBe(true);
        expect(audio.play).toHaveBeenCalledOnce();
        expect(audio.playbackRate).toBe(0.5);
        controller.setSpeed(1.25);
        expect(audio.playbackRate).toBe(1.25);
    });

    it('trims both quiet edges and retains pauses, padding, and source frame offsets', async () => {
        const audio = await load('reference', audioBuffer(3, [0.5, 1], [1.5, 2]));
        expect(controller.getDuration('reference')).toBeCloseTo(1.7);
        expect(controller.getCurrentFrame('reference')).toEqual({ index: 20 });
        const bytes = await URL.createObjectURL.mock.calls[0][0].arrayBuffer();
        const wav = new DataView(bytes);
        expect(wav.getUint32(40, true)).toBe(27200 * 2);
        expect(wav.getInt16(44, true)).toBe(0);
        expect(wav.getInt16(44 + 1600 * 2, true)).toBeGreaterThan(0);
        expect(wav.getInt16(44 + 12000 * 2, true)).toBe(0);

        controller.play('reference');
        controller.setTime('reference', 1.2);
        expect(audio.currentTime).toBe(1.2);
        expect(controller.getCurrentFrame('reference')).toEqual({ index: 80 });
    });

    it('matches duration and keeps frame, media clock, and loop offsets in sync', async () => {
        await load('reference', audioBuffer(3, [0.5, 2.5]));
        const audio = await load('student', audioBuffer(3, [0.4, 2.2]));
        const originalDuration = controller.getDuration('student');
        controller.setTime('student', 1);
        controller.setDurationMatching(true);
        const rate = originalDuration / controller.getDuration('reference');
        expect(controller.getDuration('student')).toBeCloseTo(controller.getDuration('reference'));
        expect(audio.currentTime).toBeCloseTo(1);
        expect(controller.getCurrentFrame('student')).toEqual({ index: 65 });

        controller.setSpeed(0.75);
        controller.play('student');
        expect(audio.playbackRate).toBeCloseTo(0.75 * rate);
        audio.currentTime = 0.6 * rate;
        controller.animationLoop();
        expect(controller.studentTime).toBeCloseTo(0.6);
        expect(controller.getCurrentFrame('student').index).toBe(controller.getFrameIndex('student', 0.6));

        controller.setLoopRegion(0.5, 1.5);
        audio.currentTime = 1.6 * rate;
        controller.advanceTrack('student', 0);
        expect(controller.studentTime).toBeCloseTo(0.6);
        expect(audio.currentTime).toBeCloseTo(0.6 * rate);

        controller.setDurationMatching(false);
        expect(controller.getDuration('student')).toBeCloseTo(originalDuration);
        expect(controller.studentTime).toBeCloseTo(audio.currentTime);
    });

    it.each([
        ['a truncated take', audioBuffer(3, [0.5, 1.5])],
        ['an unusually long take', audioBuffer(6, [0.2, 4.5])],
        ['sparse speech with a similar span', audioBuffer(3, [0.5, 0.6], [2.4, 2.5])],
        ['a silent take', audioBuffer(3)],
        ['a click in silence', audioBuffer(3, [0.5, 0.51])],
    ])('declines matching for %s', async (_description, buffer) => {
        await load('reference', audioBuffer(3, [0.5, 2.5]));
        await load('student', buffer);
        const originalDuration = controller.getDuration('student');
        expect(controller.getMatchRate()).toBeNull();
        controller.setDurationMatching(true);
        expect(controller.durationMatching).toBe(false);
        expect(controller.getDuration('student')).toBe(originalDuration);
    });

    it('matches takes within 0.5x-2.0x even with a central pause', async () => {
        await load('reference', audioBuffer(3, [0.5, 2.5]));
        await load('student', audioBuffer(5, [0.4, 1.4], [2.8, 3.8]));
        const rate = controller.getMatchRate();
        expect(rate).not.toBeNull();
        expect(rate).toBeGreaterThanOrEqual(0.5);
        expect(rate).toBeLessThanOrEqual(2.0);
    });

    it('advances frame-only playback and preserves the linked position at end of playback', () => {
        controller.referenceFrames = frames;
        controller.studentFrames = frames.slice(0, 50);
        controller.setLinkedPlayheads(true);
        const clock = vi.spyOn(performance, 'now').mockReturnValue(0);
        controller.play('reference');
        clock.mockReturnValue(1000);
        controller.animationLoop();
        expect(controller.referenceTime).toBe(1);
        clock.mockReturnValue(3000);
        controller.animationLoop();
        expect(controller.referenceTime).toBe(3);
        expect(controller.studentTime).toBe(1);
        expect(controller.animationFrameId).toBeNull();
    });

    it('releases old media and resets matching and position on replacement', async () => {
        await load('reference', audioBuffer(3, [0.5, 2.5]));
        const audio = await load('student', audioBuffer(3, [0.4, 2.2]));
        controller.setDurationMatching(true);
        controller.play('student');
        controller.setTime('student', 1);
        await controller.loadStudent([{ jaw: 0.7 }], null);
        expect(controller.isPlaying.student).toBe(false);
        expect(controller.studentTime).toBe(0);
        expect(controller.durationMatching).toBe(false);
        expect(controller.tracks.student).toBeNull();
        expect(audio.pause).toHaveBeenCalledOnce();
        expect(audio.removeAttribute).toHaveBeenCalledWith('src');
        expect(URL.revokeObjectURL).toHaveBeenCalledOnce();
    });

    it('ignores audio decode completion after clear', async () => {
        let completeDecode;
        context.decodeAudioData.mockReturnValue(new Promise(resolve => { completeDecode = resolve; }));
        const loading = controller.loadReference([], 'AA==');
        controller.clear();
        completeDecode(audioBuffer(2));
        expect(await loading).toBe(false);
        expect(controller.tracks.reference).toBeNull();
        expect(URL.createObjectURL).not.toHaveBeenCalled();
    });

    it('keeps newest audio when decode requests resolve out of order', async () => {
        const complete = [];
        context.decodeAudioData.mockImplementation(() => new Promise(resolve => complete.push(resolve)));
        const first = controller.loadReference([], 'AA==');
        const second = controller.loadReference([], 'AQ==');
        complete[1](audioBuffer(2));
        expect(await second).toBe(true);
        complete[0](audioBuffer(1));
        expect(await first).toBe(false);
        expect(controller.getDuration('reference')).toBe(2);
        expect(URL.createObjectURL).toHaveBeenCalledOnce();
    });
});
