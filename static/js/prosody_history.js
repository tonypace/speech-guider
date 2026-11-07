/** Persist only bounded, structurally valid recording history. */
const HISTORY_KEY = 'prosodyLabHistory';
const ROLE_KEYS = { teacher: 'prosodyLabTeacherId', student: 'prosodyLabStudentId' };

export function trimProsodyHistory(history, maxItems = 3) {
    return history.slice(0, maxItems);
}

export function loadHistory(storage = localStorage) {
    try {
        const history = JSON.parse(storage.getItem(HISTORY_KEY) || '[]');
        return Array.isArray(history) ? trimProsodyHistory(history.filter((record) => record &&
            typeof record.recording_id === 'string' && record.summary &&
            typeof record.summary === 'object' && Array.isArray(record.pitch_track) &&
            Array.isArray(record.syllable_onsets))) : [];
    } catch (error) {
        console.warn('Ignoring unreadable prosody history', error);
        return [];
    }
}

export function getRoleId(role, storage = localStorage) {
    if (!ROLE_KEYS[role]) return '';
    try {
        return storage.getItem(ROLE_KEYS[role]) || '';
    } catch {
        return '';
    }
}

export function setRoleId(role, id, storage = localStorage) {
    if (ROLE_KEYS[role]) storage.setItem(ROLE_KEYS[role], id);
}

export function storeRecord(record, storage = localStorage) {
    const stored = { ...record, created_at: new Date().toISOString() };
    const history = trimProsodyHistory([
        stored, ...loadHistory(storage).filter((item) => item.recording_id !== stored.recording_id)
    ]);
    storage.setItem(HISTORY_KEY, JSON.stringify(history));
    for (const [role, fallbackIndex] of [['teacher', 1], ['student', 0]]) {
        if (!history.some((item) => item.recording_id === getRoleId(role, storage)) && history[fallbackIndex]) {
            setRoleId(role, history[fallbackIndex].recording_id, storage);
        }
    }
}

/** Desktop loopback origins change on relaunch; persist summaries in app data. */
export function createDesktopHistoryStorage(initial) {
    const state = { recordings: [], teacher_id: '', student_id: '', ...initial };
    const fieldForKey = {
        [HISTORY_KEY]: 'recordings',
        [ROLE_KEYS.teacher]: 'teacher_id',
        [ROLE_KEYS.student]: 'student_id',
    };
    let pending = Promise.resolve();
    return {
        getItem(key) {
            if (key === HISTORY_KEY) return JSON.stringify(state.recordings);
            return state[fieldForKey[key]] ?? null;
        },
        setItem(key, value) {
            if (key === HISTORY_KEY) state.recordings = JSON.parse(value);
            else if (fieldForKey[key]) state[fieldForKey[key]] = value;
        },
        flush() {
            // Write snapshots in submission order, even if earlier saves fail.
            const body = JSON.stringify(state);
            pending = pending.catch(() => {}).then(async () => {
                const response = await fetch('/api/desktop-history', {
                    method: 'PUT', headers: { 'Content-Type': 'application/json' }, body,
                });
                if (!response.ok) throw new Error('Could not save prosody history.');
            });
            return pending;
        },
    };
}
