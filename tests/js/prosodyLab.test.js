import { describe, it, expect, beforeEach } from 'vitest';
import { ProsodyLabRecorder, midiToNoteName, trimProsodyHistory, buildMusicalScoreChart } from '../../static/js/prosody_lab.js';

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

    it('converts midi values to note names', () => {
        expect(midiToNoteName(60)).toBe('C4');
        expect(midiToNoteName(69)).toBe('A4');
    });

    it('builds a musical score chart with pitch and syllable markers', () => {
        const result = buildMusicalScoreChart(
            {
                summary: { mean_midi: 60, mean_note: 'C4', syllable_count: 2, duration_seconds: 0.5 },
                pitch_track: [
                    { time: 0, midi: 60, f0_hz: 261.6, note: 'C4', confidence: 0.9 },
                    { time: 0.5, midi: 62, f0_hz: 293.7, note: 'D4', confidence: 0.8 },
                ],
                syllable_onsets: [0.1, 0.4],
            },
            { locked: false, beatsPerBar: 4, zoomLevel: 1.0 },
        );

        expect(result.traces.length).toBeGreaterThan(0);
        expect(result.layout.title.text).toBe('Musical Score');
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
