import { beforeEach, describe, expect, it, vi } from 'vitest';
import { SSLComparisonController } from '../../static/js/ssl_comparison_controller.js';

// Keep clock and audio source behavior explicit: timeline-only tests miss audible drift.
describe('SSL comparison playback lifecycle', () => {
    let controller;
    let context;
    let sources;

    beforeEach(() => {
        sources = [];
        context = {
            currentTime: 0,
            state: 'running',
            destination: {},
            createBufferSource: () => {
                const source = {
                    playbackRate: { value: 1 },
                    connect: vi.fn(),
                    disconnect: vi.fn(),
                    start: vi.fn(),
                    stop: vi.fn(),
                };
                sources.push(source);
                return source;
            },
            decodeAudioData: vi.fn(),
        };
        controller = new SSLComparisonController();
        controller.audioContext = context;
        controller.referenceFrames = Array(500).fill({ jaw: 0.5 });
        controller.studentFrames = Array(250).fill({ jaw: 0.3 });
        controller.audioBuffers.reference = { duration: 10 };
        vi.spyOn(globalThis, 'requestAnimationFrame').mockReturnValue(1);
    });

    it('applies selected speed to audio before play and during playback', () => {
        controller.setSpeed(0.5);
        controller.play('reference');
        expect(sources[0].playbackRate.value).toBe(0.5);
        controller.setSpeed(1.25);
        expect(sources[0].playbackRate.value).toBe(1.25);
    });

    it('restarts audible playback when seeking', () => {
        controller.play('reference');
        controller.setTime('reference', 4);
        expect(sources[0].stop).toHaveBeenCalledOnce();
        expect(sources[0].disconnect).toHaveBeenCalledOnce();
        expect(sources[1].start).toHaveBeenCalledWith(0, 4);
    });

    it('wraps audio and frames together, preserving loop overshoot', () => {
        controller.play('reference');
        controller.setLoopRegion(1, 3);
        controller.referenceTime = 2.9;
        controller.advanceTrack('reference', 0.2);
        expect(controller.referenceTime).toBeCloseTo(1.1);
        expect(sources[1].start.mock.calls[0][1]).toBeCloseTo(1.1);
    });

    it('advances from an audio clock starting at zero', () => {
        controller.play('reference');
        context.currentTime = 1;
        controller.animationLoop();
        expect(controller.referenceTime).toBe(1);
    });

    it('clears old audio and resets position when replacing a track without audio', async () => {
        controller.play('reference');
        controller.setTime('reference', 4);
        await controller.loadReference([{ jaw: 0.7 }], null);
        expect(controller.isPlaying.reference).toBe(false);
        expect(controller.referenceTime).toBe(0);
        expect(controller.audioBuffers.reference).toBeNull();
    });

    it('ignores audio decode completion after clear', async () => {
        let completeDecode;
        context.decodeAudioData.mockReturnValue(new Promise(resolve => { completeDecode = resolve; }));
        const loading = controller.loadReference([], 'AA==');
        controller.clear();
        completeDecode({ duration: 10 });
        await loading;
        expect(controller.audioBuffers.reference).toBeNull();
    });

    it('keeps newest audio when decode requests resolve out of order', async () => {
        const complete = [];
        context.decodeAudioData.mockImplementation(() => new Promise(resolve => complete.push(resolve)));
        const first = controller.loadReference([], 'AA==');
        const second = controller.loadReference([], 'AQ==');
        const latest = { duration: 2 };
        complete[1](latest);
        await second;
        complete[0]({ duration: 1 });
        await first;
        expect(controller.audioBuffers.reference).toBe(latest);
    });
});
