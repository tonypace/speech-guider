import { describe, expect, it, vi } from 'vitest';
import { showAnalysisTrajectory } from '../../static/js/analysis_trajectory.js';

describe('analysis trajectory', () => {
    it('renders and seeks actual frames, then disposes view', () => {
        const container = document.createElement('div');
        const dispose = showAnalysisTrajectory(container, {
            frame_rate: 50,
            frames: [{ lip_aperture: 0.1 }, { lip_aperture: 0.8 }],
        });
        expect(container.querySelector('svg')).not.toBeNull();
        expect(container.querySelector('output').textContent).toContain('0.000 s');
        const slider = container.querySelector('input');
        slider.value = '1';
        slider.dispatchEvent(new Event('input'));
        expect(container.querySelector('output').textContent).toContain('0.020 s');
        vi.spyOn(container.querySelector('audio'), 'pause').mockImplementation(() => {});
        dispose();
        expect(container.children).toHaveLength(0);
    });
});
