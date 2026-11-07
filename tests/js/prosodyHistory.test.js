import { describe, expect, it, vi } from 'vitest';
import { loadHistory, storeRecord, getRoleId, setRoleId, createDesktopHistoryStorage } from '../../static/js/prosody_history.js';

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


describe('desktop history storage', () => {
    it('persists initial history and sends complete snapshots in order', async () => {
        let complete;
        const first = new Promise((resolve) => { complete = resolve; });
        const send = vi.fn().mockReturnValueOnce(first).mockResolvedValue({ ok: true });
        vi.stubGlobal('fetch', send);
        try {
            const storage = createDesktopHistoryStorage({ recordings: [recording('old')], student_id: 'old' });
            expect(loadHistory(storage).map(item => item.recording_id)).toEqual(['old']);
            expect(getRoleId('student', storage)).toBe('old');
            storeRecord(recording('new'), storage);
            const one = storage.flush();
            setRoleId('student', 'new', storage);
            const two = storage.flush();
            await Promise.resolve();
            await Promise.resolve();
            expect(send).toHaveBeenCalledOnce();
            complete({ ok: true });
            await Promise.all([one, two]);
            const snapshots = send.mock.calls.map(([, request]) => JSON.parse(request.body));
            expect(snapshots.map(snapshot => snapshot.student_id)).toEqual(['old', 'new']);
            expect(snapshots[1].recordings.map(item => item.recording_id)).toEqual(['new', 'old']);
        } finally {
            vi.unstubAllGlobals();
        }
    });
});
