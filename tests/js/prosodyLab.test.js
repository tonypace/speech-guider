import { describe, it, expect, beforeEach } from 'vitest';
import { ProsodyLabRecorder } from '../../static/js/prosody_lab.js';
import { trimProsodyHistory } from '../../static/js/prosody_history.js';
import {
    renderVocAlignTetherDiagnosticSVG,
    renderFlowMatrixTrainerSVG,
    alignRecordPairToTetherItems,
} from '../../static/js/prosody_rhythm_views.js';

describe('Prosody Lab helpers', () => {
    beforeEach(() => {
        document.body.innerHTML = '';
        localStorage.clear();
    });

    it('trims recording history to the latest three entries', () => {
        const history = [
            { recording_id: '1' },
            { recording_id: '2' },
            { recording_id: '3' },
            { recording_id: '4' },
        ];

        const trimmed = trimProsodyHistory(history, 3);
        expect(trimmed).toHaveLength(3);
        expect(trimmed.map((item) => item.recording_id)).toEqual(['1', '2', '3']);
    });

    it('renders Goal 1 VocAlign Elastic Tether & Beat Bin SVG for presets and recorded pairs', () => {
        const presetSvg = renderVocAlignTetherDiagnosticSVG({
            phraseId: 'prepared',
            profileKey: 'dysfluent_hesitation',
            normFactor: 0.0,
        });
        expect(presetSvg).toContain('data-prosody-tether-svg="true"');
        expect(presetSvg).toContain('REFERENCE');
        expect(presetSvg).toContain('LEARNER TAKE');
        expect(presetSvg).not.toContain('DEDICATED MILLISECOND DEVIATION');

        const teacherRecord = {
            recording_id: 'teach-1',
            summary: { duration_seconds: 1.6, syllable_count: 3 },
            syllable_details: [
                { index: 0, nucleus_time: 0.2, p_center_time: 0.18, consonant_onset_time: 0.14, pre_duration: 0.04, vowel_duration: 0.22, prominence: 0.9, is_stressed: true },
                { index: 1, nucleus_time: 0.6, p_center_time: 0.58, consonant_onset_time: 0.56, pre_duration: 0.02, vowel_duration: 0.07, prominence: 0.25, is_stressed: false },
                { index: 2, nucleus_time: 1.0, p_center_time: 0.96, consonant_onset_time: 0.90, pre_duration: 0.06, vowel_duration: 0.28, prominence: 0.95, is_stressed: true },
            ],
        };
        const studentRecord = {
            recording_id: 'stu-1',
            summary: { duration_seconds: 2.0, syllable_count: 3 },
            syllable_details: [
                { index: 0, nucleus_time: 0.25, p_center_time: 0.22, consonant_onset_time: 0.18, pre_duration: 0.04, vowel_duration: 0.20, prominence: 0.85, is_stressed: true },
                { index: 1, nucleus_time: 0.75, p_center_time: 0.72, consonant_onset_time: 0.70, pre_duration: 0.02, vowel_duration: 0.22, prominence: 0.75, is_stressed: false },
                { index: 2, nucleus_time: 1.55, p_center_time: 1.50, consonant_onset_time: 1.44, pre_duration: 0.06, vowel_duration: 0.14, prominence: 0.80, is_stressed: true },
            ],
        };

        const aligned = alignRecordPairToTetherItems(teacherRecord, studentRecord, 'prepared');
        expect(aligned.sourceMode).toBe('recorded_pair');
        expect(aligned.lrnSyls).toHaveLength(3);

        const pairSvg = renderVocAlignTetherDiagnosticSVG({
            phraseId: 'prepared',
            normFactor: 0.0,
            teacherRecord,
            studentRecord,
        });
        expect(pairSvg).toContain('data-source-mode="recorded_pair"');
    });

    it('renders Goal 2 Stationary 16-Slot Prosodic Flow Matrix SVG', () => {
        const flowSvg = renderFlowMatrixTrainerSVG({
            phraseId: 'contrastive',
            beat: 1.75,
            isResponseBar: true,
            performer: 'bot_dysfluent',
        });
        expect(flowSvg).toContain('data-prosody-flow-svg="true"');
        expect(flowSvg).toContain('BAR 2: LIVE RESPONSE');
        expect(flowSvg).toContain('♦ P-Center');
        expect(flowSvg).toContain('|| PAUSE GATE');
    });

    it('renders persisted history labels and metrics as text', () => {
        const historyEl = document.createElement('div');
        const recorder = Object.create(ProsodyLabRecorder.prototype);
        recorder.historyEl = historyEl;
        recorder.getTeacherId = () => '';
        recorder.getStudentId = () => '';
        recorder.setRole = () => {};
        const hostile = '<img src=x onerror=alert(1)>';

        recorder.renderHistory([{
            recording_id: hostile,
            created_at: 'invalid date',
            summary: { syllable_count: hostile, pause_count: 1, rhythm_balance: hostile },
        }]);

        expect(historyEl.querySelector('img')).toBeNull();
        expect(historyEl.textContent).toContain(hostile.slice(0, 6));
        expect(historyEl.textContent).toContain(hostile);
        expect(historyEl.querySelector('button').getAttribute('data-recording-id')).toBe(hostile);
    });

    it('renders feedback summary values as text', () => {
        const feedbackEl = document.createElement('div');
        const recorder = Object.create(ProsodyLabRecorder.prototype);
        recorder.feedbackEl = feedbackEl;
        const hostile = '<svg onload=alert(1)>';

        recorder.renderFeedback({ summary: { mean_note: hostile, syllable_count: 2 } });

        expect(feedbackEl.querySelector('svg')).toBeNull();
        expect(feedbackEl.textContent).toContain(hostile);
    });
});
