import { describe, expect, it, vi } from 'vitest';
import { showAnalysisTrajectory } from '../../static/js/analysis_trajectory.js';

describe('analysis trajectory', () => {
    it('pauses hidden analysis playback and removes its tab listener on disposal', () => {
        const container = document.createElement('div');
        const dispose = showAnalysisTrajectory(container, { frame_rate: 50, frames: [{ lip_aperture: 0.1 }] });
        const pause = vi.spyOn(container.querySelector('audio'), 'pause').mockImplementation(() => {});

        window.dispatchEvent(new CustomEvent('speechguider:tabchange', { detail: 'analysis' }));
        expect(pause).not.toHaveBeenCalled();
        window.dispatchEvent(new CustomEvent('speechguider:tabchange', { detail: 'comparison' }));
        expect(pause).toHaveBeenCalledOnce();

        dispose();
        pause.mockClear();
        window.dispatchEvent(new CustomEvent('speechguider:tabchange', { detail: 'prosody' }));
        expect(pause).not.toHaveBeenCalled();
    });

    it('renders and seeks actual frames, then disposes view', () => {
        const container = document.createElement('div');
        const dispose = showAnalysisTrajectory(container, {
            frame_rate: 50,
            frames: [{ lip_aperture: 0.1 }, { lip_aperture: 0.8 }],
        });
        expect(container.querySelector('svg')).not.toBeNull();
        expect(container.querySelector('select').value).toBe('0.5');
        expect(container.querySelector('[data-speed-badge]').textContent).toBe('Slow Motion (0.5x)');
        expect(container.querySelector('output').textContent).toContain('0.000 s');
        const slider = container.querySelector('input');
        slider.value = '1';
        slider.dispatchEvent(new Event('input'));
        expect(container.querySelector('output').textContent).toContain('0.020 s');
        vi.spyOn(container.querySelector('audio'), 'pause').mockImplementation(() => {});
        dispose();
        expect(container.children).toHaveLength(0);
    });

    it('prepends articulatory estimate above feedback with tongue contact highlight', () => {
        const container = document.createElement('div');
        const feedback = document.createElement('div');
        feedback.id = 'feedback-card';
        container.appendChild(feedback);
        const dispose = showAnalysisTrajectory(container, {
            frame_rate: 50,
            frames: [{ lip_aperture: 0.1, tongue_tip_constriction_degree: 0.0 }],
        });
        expect(container.firstElementChild.tagName).toBe('SECTION');
        expect(container.firstElementChild.textContent).toContain('tongue contact enhanced');
        expect(container.firstElementChild.className).toContain('min-h-');
        dispose();
    });

    it('uses definite square container sizing without WebKit flex-auto collapse', () => {
        const container = document.createElement('div');
        const dispose = showAnalysisTrajectory(container, {
            frame_rate: 50,
            frames: [{ lip_aperture: 0.1 }],
        });
        const tract = container.querySelector('[data-tract]');
        expect(tract.classList.contains('w-full')).toBe(true);
        expect(tract.classList.contains('max-w-[62vh]')).toBe(true);
        expect(tract.classList.contains('aspect-square')).toBe(true);
        expect(tract.classList.contains('shrink-0')).toBe(true);
        expect(tract.classList.contains('mx-auto')).toBe(true);
        expect(tract.classList.contains('[&>svg]:w-auto')).toBe(false);
        expect(tract.classList.contains('flex')).toBe(false);
        dispose();
    });

    it('updates SVG frame and output even when setting audio.currentTime throws before metadata loads', () => {
        const originalCreate = URL.createObjectURL;
        const originalRevoke = URL.revokeObjectURL;
        URL.createObjectURL = vi.fn(() => 'blob:mock-audio');
        URL.revokeObjectURL = vi.fn();
        try {
            const container = document.createElement('div');
            const dispose = showAnalysisTrajectory(
                container,
                {
                    frame_rate: 50,
                    frames: [{ lip_aperture: 0.1 }, { lip_aperture: 0.85 }],
                },
                new Blob(['wav'], { type: 'audio/wav' }),
            );
            const audio = container.querySelector('audio');
            vi.spyOn(audio, 'pause').mockImplementation(() => {});
            Object.defineProperty(audio, 'currentTime', {
                configurable: true,
                get: () => 0,
                set: () => {
                    throw new DOMException('InvalidStateError');
                },
            });

            const jawBefore = container.querySelector('#analysis-estimate-jaw-group')?.getAttribute('transform');
            const slider = container.querySelector('input');
            slider.value = '1';
            slider.dispatchEvent(new Event('input'));

            const jawAfter = container.querySelector('#analysis-estimate-jaw-group')?.getAttribute('transform');
            expect(container.querySelector('output').textContent).toContain('0.020 s · frame 2/2');
            expect(jawAfter).not.toBe(jawBefore);

            dispose();
            expect(URL.revokeObjectURL).toHaveBeenCalledWith('blob:mock-audio');
        } finally {
            if (originalCreate === undefined) {
                delete URL.createObjectURL;
            } else {
                URL.createObjectURL = originalCreate;
            }
            if (originalRevoke === undefined) {
                delete URL.revokeObjectURL;
            } else {
                URL.revokeObjectURL = originalRevoke;
            }
        }
    });

    it('cancels animation frame and renders final frame on audio ended', () => {
        const rafSpy = vi.spyOn(window, 'requestAnimationFrame').mockReturnValue(42);
        const cancelSpy = vi.spyOn(window, 'cancelAnimationFrame').mockImplementation(() => {});
        try {
            const container = document.createElement('div');
            const dispose = showAnalysisTrajectory(container, {
                frame_rate: 50,
                frames: [
                    { lip_aperture: 0.1 },
                    { lip_aperture: 0.5 },
                    { lip_aperture: 0.9 },
                ],
            });
            const audio = container.querySelector('audio');
            vi.spyOn(audio, 'pause').mockImplementation(() => {});
            let currentTime = 0;
            Object.defineProperty(audio, 'currentTime', {
                configurable: true,
                get: () => currentTime,
                set: (v) => { currentTime = v; },
            });
            Object.defineProperty(audio, 'paused', { configurable: true, get: () => false });
            Object.defineProperty(audio, 'ended', { configurable: true, get: () => false });

            audio.onplay();
            expect(rafSpy).toHaveBeenCalled();

            cancelSpy.mockClear();
            currentTime = 0.045;
            audio.onended();

            expect(cancelSpy).toHaveBeenCalledWith(42);
            expect(container.querySelector('output').textContent).toContain('0.040 s · frame 3/3');

            dispose();
        } finally {
            rafSpy.mockRestore();
            cancelSpy.mockRestore();
        }
    });
});
