import { describe, expect, it } from 'vitest';
import { loadHistory, storeRecord, getRoleId, setRoleId } from '../../static/js/prosody_history.js';

const recording = id => ({ recording_id: id, summary: {}, pitch_track: [], syllable_onsets: [] });

describe('prosody history', () => {
    it('recovers malformed JSON, shapes, and entries', () => {
        for (const bad of ['broken', '{}', '[null,1,{"recording_id":3}]']) {
            localStorage.setItem('prosodyLabHistory', bad);
            expect(loadHistory()).toEqual([]);
        }
    });

    it('bounds history and reassigns roles after eviction', () => {
        storeRecord(recording('1'));
        storeRecord(recording('2'));
        setRoleId('teacher', '1');
        storeRecord(recording('3'));
        storeRecord(recording('4'));
        expect(loadHistory().map(item => item.recording_id)).toEqual(['4', '3', '2']);
        expect(getRoleId('teacher')).toBe('3');
        expect(getRoleId('student')).toBe('4');
    });
});
