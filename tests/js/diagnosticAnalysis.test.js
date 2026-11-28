import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

describe('Diagnostic Analysis Tab UI', () => {
    let recorder;

    beforeEach(async () => {
        document.body.innerHTML = `
            <select id="diagnostic-passage-select">
                <option value="full_diagnostic" selected>Full</option>
                <option value="vowel_pairs">Vowels</option>
                <option value="custom">Custom</option>
            </select>
            <div id="diagnostic-passage-badges"></div>
            <textarea id="target_text">Every Thursday morning...</textarea>
            <textarea id="comparison-target-text"></textarea>
            <div id="recorder">
                <button id="record-btn">Record</button>
                <span id="rec-timer">00:00</span>
                <canvas id="waveform"></canvas>
            </div>
            <div id="file-upload-section"><input type="file" id="audio" /></div>
            <div id="progress-container" class="hidden"></div>
            <div id="feedback-container"></div>
            <section id="articulatory-section" class="hidden">
                <div id="error-list"></div>
            </section>
        `;

        vi.spyOn(global, 'fetch').mockResolvedValue({
            ok: true,
            json: async () => ({
                passages: [
                    {
                        id: 'full_diagnostic',
                        target_contrasts: ['/θ/', '/ð/'],
                        text: 'Every Thursday morning...',
                    },
                    {
                        id: 'vowel_pairs',
                        target_contrasts: ['/ɪ/ vs /iː/'],
                        text: 'They bet a small bat can reach the big ship before the sheep cross; please sit in this seat and let the bad bed rest.',
                    },
                ],
            }),
        });

        const mod = await import('../../static/js/recorder.js');
        recorder = new mod.IntercomRecorder({
            location: { protocol: 'https:', hostname: 'localhost' },
        });
    });

    afterEach(() => {
        recorder?.destroy();
        vi.restoreAllMocks();
        delete window.selectError;
        delete window.switchTab;
    });

    it('updates target_text and contrast badges when a diagnostic passage is selected', () => {
        const select = document.getElementById('diagnostic-passage-select');
        const target = document.getElementById('target_text');
        select.value = 'vowel_pairs';
        select.dispatchEvent(new Event('change'));
        expect(target.value).toContain('ship');
        expect(document.getElementById('diagnostic-passage-badges').textContent).toContain('/ɪ/ vs /iː/');
    });

    it('renders 6-category summary cards, aligned transcript, seek, selectError, and Compare jump', () => {
        window.selectError = vi.fn();
        window.switchTab = vi.fn();

        const mockResult = {
            success: true,
            feedback: '<strong>Pronunciation:</strong> Articulatory trajectory captured',
            integration_meta: { model_version: 'r5' },
            ssl_trajectory: {
                frame_rate: 50,
                frames: Array.from({ length: 60 }, () => ({ lip_aperture: 0.3 })),
            },
            alignment: {
                words: [
                    { word: 'Thursday', start_time: 0.2, end_time: 0.6 },
                    { word: 'ship', start_time: 0.7, end_time: 1.0 },
                ],
            },
            errors: [
                {
                    error_index: 0,
                    target_phoneme: 'θ',
                    predicted_phoneme: 's',
                    word_context: 'Thursday',
                    start_time: 0.2,
                    end_time: 0.4,
                    evidence_summary: 'Weak /θ/ cue — leaned closer to /s/',
                },
            ],
            pronunciation_diagnostics: {
                status: 'available',
                disclaimer: 'Guided practice cues only.',
                flagged_count: 1,
                categories: [
                    {
                        id: 'voiceless_dental',
                        title: 'Voiceless Dental Fricative',
                        contrast: '/θ/ vs /s, f, t/',
                        status: 'watch',
                        summary: 'Weak /θ/ cue — leaned closer to /s/',
                        flagged_words: [
                            {
                                word: 'Thursday',
                                target_phoneme: 'θ',
                                start_time: 0.2,
                                end_time: 0.4,
                                error_index: 0,
                                comparison_prompt: 'Thursday',
                            },
                        ],
                    },
                ],
            },
        };

        recorder.displayResults(mockResult);

        expect(document.getElementById('pronunciation-diagnostics-grid')).not.toBeNull();
        expect(document.getElementById('syllable-diff-card')).not.toBeNull();
        expect(document.body.textContent).toContain('R5 audio-based estimate');

        const wordBtn = Array.from(document.querySelectorAll('#pronunciation-diagnostics-grid button'))
            .find((b) => b.textContent.includes('Thursday'));
        wordBtn.click();
        expect(window.selectError).toHaveBeenCalledWith(0);
        expect(document.querySelector('[data-focus-badge]').textContent).toContain('Thursday');

        const compareBtn = Array.from(document.querySelectorAll('#pronunciation-diagnostics-grid button'))
            .find((b) => b.textContent.includes('Compare'));
        compareBtn.click();
        expect(document.getElementById('comparison-target-text').value).toBe('Thursday');
        expect(window.switchTab).toHaveBeenCalledWith('comparison');
    });

    it('renders syllable diff with red/yellow/not_reached styling, weakness drill links, and slices student WAV to comparison lab', async () => {
        window.switchTab = vi.fn();
        const loadSliceSpy = vi.fn().mockResolvedValue();
        window.comparisonLab = { loadStudentSliceAndReference: loadSliceSpy };

        const { encodePcmWav } = await import('../../static/js/audio_conversion.js');
        const samples = new Float32Array(16000 * 2); // 2s mono 16kHz
        const wavBlob = encodePcmWav({
            sampleRate: 16000,
            length: samples.length,
            numberOfChannels: 1,
            getChannelData: () => samples,
        });

        const mockResult = {
            success: true,
            feedback: '<strong>Pronunciation:</strong> ok',
            integration_meta: { model_version: 'r5' },
            ssl_trajectory: {
                frame_rate: 50,
                frames: Array.from({ length: 100 }, (_, idx) => ({ lip_aperture: idx * 0.01 })),
            },
            alignment: {
                words: [
                    {
                        word: 'Thursday',
                        start_time: 0.2,
                        end_time: 0.6,
                        not_reached: false,
                        syllables: [
                            { syllable_index: 0, start_time: 0.2, end_time: 0.4, severity: 'red', phonemes_target: ['θ'], phonemes_predicted: ['s'] },
                            { syllable_index: 1, start_time: 0.4, end_time: 0.6, severity: 'clear', phonemes_target: ['d'], phonemes_predicted: ['d'] },
                        ],
                    },
                    {
                        word: 'ship',
                        start_time: 0.7,
                        end_time: 1.0,
                        not_reached: false,
                        syllables: [
                            { syllable_index: 0, start_time: 0.7, end_time: 1.0, severity: 'yellow', phonemes_target: ['ɪ'], phonemes_predicted: ['iː'] },
                        ],
                    },
                    {
                        word: 'unread',
                        start_time: 0.0,
                        end_time: 0.0,
                        not_reached: true,
                        syllables: [],
                    },
                ],
            },
            errors: [],
            pronunciation_diagnostics: {
                status: 'available',
                categories: [],
                weakness_summary: [
                    {
                        category_id: 'vowel_pairs',
                        summary_text: '1 issue on /ɪ/ vs /iː/ (ship).',
                        drill_passage_id: 'vowel_pairs',
                        sample_word: {
                            word: 'ship',
                            comparison_prompt: 'ship',
                            start_time: 0.7,
                            end_time: 1.0,
                        },
                    },
                ],
            },
        };

        recorder.displayResults(mockResult, wavBlob);

        const diffCard = document.getElementById('syllable-diff-card');
        expect(diffCard).not.toBeNull();
        expect(diffCard.textContent).toContain('unread');
        expect(diffCard.querySelector('.line-through')).not.toBeNull();

        const redBtn = Array.from(diffCard.querySelectorAll('button')).find((b) => b.textContent.includes('/θ/'));
        expect(redBtn.className).toContain('bg-rose-100');
        redBtn.click();

        await vi.waitFor(() => expect(loadSliceSpy).toHaveBeenCalledOnce());
        const [promptArg, framesArg, wavSliceArg] = loadSliceSpy.mock.calls[0];
        expect(promptArg).toBe('Thursday');
        expect(framesArg.length).toBeGreaterThan(0);
        expect(wavSliceArg).toBeInstanceOf(Blob);
        expect(wavSliceArg.size).toBeGreaterThan(44);
        expect(window.switchTab).toHaveBeenCalledWith('comparison');

        const summaryCard = document.getElementById('weakness-summary-card');
        expect(summaryCard).not.toBeNull();
        const drillBtn = Array.from(summaryCard.querySelectorAll('button')).find((b) => b.textContent.includes('Practice focused drill'));
        drillBtn.click();
        expect(document.getElementById('target_text').value).toContain('sheep');
    });

    it('opens dev feedback modal and posts categories + note to /api/export-feedback', async () => {
        document.body.insertAdjacentHTML('beforeend', `
            <button type="button" data-dev-export-tab="analysis">Send to Developer</button>
            <div id="dev-feedback-modal" class="hidden">
                <form id="dev-feedback-form">
                    <span id="dev-feedback-tab-label"></span>
                    <span id="dev-feedback-audio-badge"></span>
                    <div id="dev-feedback-categories"></div>
                    <textarea id="dev-feedback-note"></textarea>
                    <p id="dev-feedback-status" class="hidden"></p>
                    <button type="button" id="dev-feedback-cancel">Cancel</button>
                    <button type="submit" id="dev-feedback-submit">Save</button>
                </form>
            </div>
        `);

        const { initFeedbackExport } = await import('../../static/js/feedback_export.js');
        initFeedbackExport();

        const fetchMock = vi.spyOn(global, 'fetch').mockResolvedValue({
            ok: true,
            json: async () => ({ success: true, folder: '/tmp/feedback_1', saved_files: ['note.txt'] }),
        });

        document.querySelector('[data-dev-export-tab="analysis"]').click();
        const modal = document.getElementById('dev-feedback-modal');
        expect(modal.classList.contains('hidden')).toBe(false);

        const firstCheckbox = modal.querySelector('input[type="checkbox"]');
        firstCheckbox.checked = true;
        document.getElementById('dev-feedback-note').value = 'Spurious /t/ release';

        document.getElementById('dev-feedback-form').dispatchEvent(new Event('submit', { cancelable: true, bubbles: true }));
        await vi.waitFor(() => expect(fetchMock).toHaveBeenCalledWith('/api/export-feedback', expect.objectContaining({ method: 'POST' })));
    });
});
