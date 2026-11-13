import { describe, expect, it, vi } from 'vitest';
import { IntercomRecorder } from '../../static/js/recorder.js';

describe('analysis text rendering', () => {
    it('renders hostile error context as text while retaining IPA tooltips', () => {
        document.body.innerHTML = '<div id="error-list"></div>';
        const recorder = new IntercomRecorder();
        window.wrapIPATooltip = vi.fn(() => '<span class="ipa-tooltip-wrapper">p</span>');
        recorder.populateErrors([{
            word_context: '<img src=x onerror=alert(1)>', target_phoneme: 'p', predicted_phoneme: 'b'
        }]);
        expect(document.querySelector('#error-list img')).toBeNull();
        expect(document.querySelector('#error-list').textContent).toContain('<img src=x onerror=alert(1)>');
        expect(document.querySelectorAll('.ipa-tooltip-wrapper')).toHaveLength(2);
        recorder.destroy();
    });
});

it('keeps partial feedback and escapes model failure diagnostics', () => {
    document.body.innerHTML = '<div id="feedback-container"></div>';
    const recorder = new IntercomRecorder();
    recorder.displayResults({ success: false, status: 'partial', feedback: 'Prosody retained', ssl_warning: '<img src=x> missing weights' });
    expect(document.querySelector('[role="alert"]').textContent).toContain('<img src=x>');
    expect(document.querySelector('#feedback-container img')).toBeNull();
    expect(document.querySelector('#feedback-container').textContent).toContain('Prosody retained');
    recorder.destroy();
});
