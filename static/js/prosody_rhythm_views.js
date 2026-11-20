import { escapeHtml } from './ipa_tooltips.js';

export const PROSODY_PHRASES = [
    {
        id: 'prepared',
        title: 'We NEED to focus on the CORE... PROBLEMs first',
        vibeLabel: 'Prepared Presentation',
        bpm: 84,
        teacherNote: 'Balanced stress feet lead into "CORE...", which receives phrase-final lengthening plus a deliberate 350ms pause gate. Then the /pr/ cluster on "PROB-" launches early so its vowel P-center locks onto the post-pause beat.',
        pauseGate: { startBeat: 2.34, endBeat: 2.82, label: '|| 350ms Pause Gate' },
        feet: [
            { label: 'Pickup: We', startBeat: 0.0, endBeat: 0.34 },
            { label: 'Foot 1: NEED to', startBeat: 0.34, endBeat: 0.90 },
            { label: 'Foot 2: FO-cus on the', startBeat: 0.90, endBeat: 1.84 },
            { label: 'Foot 3: CORE... ||', startBeat: 1.84, endBeat: 2.84 },
            { label: 'Foot 4: PROB-lems FIRST', startBeat: 2.84, endBeat: 4.0 },
        ],
        syllables: [
            { index: 0, text: 'We', pre: 'w', preDur: 0.04, vowel: 'e', beat: 0.16, dur: 0.13, stress: 0.22, pitchST: -1.0, isGhost: true, isFinal: false },
            { index: 1, text: 'NEED', pre: 'n', preDur: 0.05, vowel: 'EED', beat: 0.38, dur: 0.34, stress: 0.88, pitchST: 3.2, isGhost: false, isFinal: false },
            { index: 2, text: 'to', pre: 't', preDur: 0.03, vowel: 'o', beat: 0.76, dur: 0.11, stress: 0.16, pitchST: -1.5, isGhost: true, isFinal: false },
            { index: 3, text: 'FO-', pre: 'f', preDur: 0.06, vowel: 'O', beat: 0.94, dur: 0.30, stress: 0.84, pitchST: 2.8, isGhost: false, isFinal: false },
            { index: 4, text: 'cus', pre: 'c', preDur: 0.03, vowel: 'us', beat: 1.28, dur: 0.13, stress: 0.22, pitchST: -0.5, isGhost: true, isFinal: false },
            { index: 5, text: 'on', pre: '', preDur: 0.0, vowel: 'on', beat: 1.48, dur: 0.12, stress: 0.18, pitchST: -1.8, isGhost: true, isFinal: false },
            { index: 6, text: 'the', pre: 'th', preDur: 0.04, vowel: 'e', beat: 1.65, dur: 0.11, stress: 0.15, pitchST: -2.2, isGhost: true, isFinal: false },
            { index: 7, text: 'CORE...', pre: 'c', preDur: 0.07, vowel: 'ORE', beat: 1.86, dur: 0.48, stress: 1.00, pitchST: 4.6, isGhost: false, isFinal: true },
            { index: 8, text: 'PROB-', pre: 'pr', preDur: 0.11, vowel: 'OB', beat: 2.86, dur: 0.32, stress: 0.90, pitchST: 3.4, isGhost: false, isFinal: false },
            { index: 9, text: 'lems', pre: 'l', preDur: 0.04, vowel: 'ems', beat: 3.24, dur: 0.14, stress: 0.24, pitchST: -0.8, isGhost: true, isFinal: false },
            { index: 10, text: 'FIRST', pre: 'f', preDur: 0.06, vowel: 'IRST', beat: 3.46, dur: 0.44, stress: 0.94, pitchST: 2.4, isGhost: false, isFinal: true },
        ],
    },
    {
        id: 'spontaneous',
        title: 'Well if you AC-tually THINK a-bout the PLAN',
        vibeLabel: 'Spontaneous Discussion',
        bpm: 92,
        teacherNote: 'Fast 3-syllable anacrusis pickup ("Well if you") and phonetic compression on "AC-tually" (/æk.tʃli/) launching into conversational stress anchors.',
        pauseGate: { startBeat: 2.15, endBeat: 2.48, label: '|| Turn-Hold Breath' },
        feet: [
            { label: 'Anacrusis: Well if you', startBeat: 0.0, endBeat: 0.72 },
            { label: 'Foot 1: AC-chlee', startBeat: 0.72, endBeat: 1.54 },
            { label: 'Foot 2: THINK ||', startBeat: 1.54, endBeat: 2.50 },
            { label: 'Foot 3: a-bout the PLAN', startBeat: 2.50, endBeat: 4.0 },
        ],
        syllables: [
            { index: 0, text: 'Well', pre: 'w', preDur: 0.04, vowel: 'ell', beat: 0.16, dur: 0.12, stress: 0.24, pitchST: -1.2, isGhost: true, isFinal: false },
            { index: 1, text: 'if', pre: '', preDur: 0.0, vowel: 'if', beat: 0.34, dur: 0.11, stress: 0.18, pitchST: -1.6, isGhost: true, isFinal: false },
            { index: 2, text: 'you', pre: 'y', preDur: 0.03, vowel: 'ou', beat: 0.52, dur: 0.11, stress: 0.16, pitchST: -2.0, isGhost: true, isFinal: false },
            { index: 3, text: 'AC-', pre: '', preDur: 0.0, vowel: 'AC', beat: 0.76, dur: 0.34, stress: 0.90, pitchST: 3.5, isGhost: false, isFinal: false },
            { index: 4, text: 'tually', pre: 'tʃl', preDur: 0.07, vowel: 'ee', beat: 1.18, dur: 0.14, stress: 0.20, pitchST: -0.6, isGhost: true, isFinal: false },
            { index: 5, text: 'THINK', pre: 'th', preDur: 0.07, vowel: 'INK', beat: 1.58, dur: 0.48, stress: 0.96, pitchST: 4.2, isGhost: false, isFinal: true },
            { index: 6, text: 'a-', pre: '', preDur: 0.0, vowel: 'a', beat: 2.54, dur: 0.10, stress: 0.14, pitchST: -2.2, isGhost: true, isFinal: false },
            { index: 7, text: 'bout', pre: 'b', preDur: 0.04, vowel: 'out', beat: 2.72, dur: 0.14, stress: 0.26, pitchST: -1.0, isGhost: true, isFinal: false },
            { index: 8, text: 'the', pre: 'th', preDur: 0.04, vowel: 'e', beat: 2.94, dur: 0.11, stress: 0.15, pitchST: -2.0, isGhost: true, isFinal: false },
            { index: 9, text: 'PLAN', pre: 'pl', preDur: 0.10, vowel: 'AN', beat: 3.22, dur: 0.52, stress: 0.98, pitchST: 3.0, isGhost: false, isFinal: true },
        ],
    },
    {
        id: 'contrastive',
        title: 'I said FIF-TEEN per-CENT... not FIF-ty',
        vibeLabel: 'Contrastive Argument',
        bpm: 88,
        teacherNote: 'Contrastive stress shifts onto "-TEEN" vs. "FIF-ty" with a sharp caesura pause gate after "per-CENT...".',
        pauseGate: { startBeat: 2.22, endBeat: 2.74, label: '|| Contrastive Caesura' },
        feet: [
            { label: 'Pickup: I said', startBeat: 0.0, endBeat: 0.58 },
            { label: 'Foot 1: FIF-TEEN', startBeat: 0.58, endBeat: 1.56 },
            { label: 'Foot 2: per-CENT ||', startBeat: 1.56, endBeat: 2.74 },
            { label: 'Foot 3: not FIF-ty', startBeat: 2.74, endBeat: 4.0 },
        ],
        syllables: [
            { index: 0, text: 'I', pre: '', preDur: 0.0, vowel: 'I', beat: 0.16, dur: 0.11, stress: 0.18, pitchST: -1.8, isGhost: true, isFinal: false },
            { index: 1, text: 'said', pre: 's', preDur: 0.05, vowel: 'aid', beat: 0.36, dur: 0.13, stress: 0.24, pitchST: -1.2, isGhost: true, isFinal: false },
            { index: 2, text: 'FIF-', pre: 'f', preDur: 0.06, vowel: 'IF', beat: 0.62, dur: 0.26, stress: 0.78, pitchST: 2.2, isGhost: false, isFinal: false },
            { index: 3, text: 'TEEN', pre: 't', preDur: 0.06, vowel: 'EEN', beat: 0.98, dur: 0.44, stress: 1.00, pitchST: 5.2, isGhost: false, isFinal: false },
            { index: 4, text: 'per-', pre: 'p', preDur: 0.04, vowel: 'er', beat: 1.52, dur: 0.11, stress: 0.16, pitchST: -1.8, isGhost: true, isFinal: false },
            { index: 5, text: 'CENT...', pre: 's', preDur: 0.07, vowel: 'ENT', beat: 1.74, dur: 0.46, stress: 0.90, pitchST: 3.4, isGhost: false, isFinal: true },
            { index: 6, text: 'not', pre: 'n', preDur: 0.04, vowel: 'ot', beat: 2.78, dur: 0.14, stress: 0.30, pitchST: -0.8, isGhost: true, isFinal: false },
            { index: 7, text: 'FIF-', pre: 'f', preDur: 0.07, vowel: 'IF', beat: 3.08, dur: 0.46, stress: 0.98, pitchST: 4.8, isGhost: false, isFinal: false },
            { index: 8, text: 'ty', pre: 't', preDur: 0.04, vowel: 'y', beat: 3.62, dur: 0.16, stress: 0.20, pitchST: -2.4, isGhost: true, isFinal: true },
        ],
    },
    {
        id: 'narrative',
        title: 'And then the WHOLE ROOM... went com-PLETE-ly SI-lent',
        vibeLabel: 'Expressive Storytelling',
        bpm: 78,
        teacherNote: 'Expressive narrative pacing: drawn-out emphasis on "WHOLE ROOM...", dramatic suspension pause, and rapid acceleration through "went com-PLETE-ly SI-lent".',
        pauseGate: { startBeat: 1.98, endBeat: 2.48, label: '|| Suspense Gate' },
        feet: [
            { label: 'Anacrusis: And then the', startBeat: 0.0, endBeat: 0.74 },
            { label: 'Foot 1: WHOLE ROOM ||', startBeat: 0.74, endBeat: 2.48 },
            { label: 'Foot 2: went com-PLETE-ly', startBeat: 2.48, endBeat: 3.38 },
            { label: 'Foot 3: SI-lent', startBeat: 3.38, endBeat: 4.0 },
        ],
        syllables: [
            { index: 0, text: 'And', pre: '', preDur: 0.0, vowel: 'And', beat: 0.14, dur: 0.11, stress: 0.18, pitchST: -1.8, isGhost: true, isFinal: false },
            { index: 1, text: 'then', pre: 'th', preDur: 0.04, vowel: 'en', beat: 0.32, dur: 0.11, stress: 0.20, pitchST: -1.4, isGhost: true, isFinal: false },
            { index: 2, text: 'the', pre: 'th', preDur: 0.04, vowel: 'e', beat: 0.50, dur: 0.10, stress: 0.14, pitchST: -2.2, isGhost: true, isFinal: false },
            { index: 3, text: 'WHOLE', pre: 'wh', preDur: 0.06, vowel: 'OLE', beat: 0.76, dur: 0.42, stress: 0.92, pitchST: 3.8, isGhost: false, isFinal: false },
            { index: 4, text: 'ROOM...', pre: 'r', preDur: 0.06, vowel: 'OOM', beat: 1.32, dur: 0.58, stress: 1.00, pitchST: 4.6, isGhost: false, isFinal: true },
            { index: 5, text: 'went', pre: 'w', preDur: 0.04, vowel: 'ent', beat: 2.52, dur: 0.12, stress: 0.22, pitchST: -1.4, isGhost: true, isFinal: false },
            { index: 6, text: 'com-', pre: 'k', preDur: 0.04, vowel: 'om', beat: 2.70, dur: 0.10, stress: 0.16, pitchST: -2.0, isGhost: true, isFinal: false },
            { index: 7, text: 'PLETE-', pre: 'pl', preDur: 0.09, vowel: 'ETE', beat: 2.92, dur: 0.30, stress: 0.88, pitchST: 3.2, isGhost: false, isFinal: false },
            { index: 8, text: 'ly', pre: 'l', preDur: 0.03, vowel: 'y', beat: 3.26, dur: 0.11, stress: 0.18, pitchST: -1.2, isGhost: true, isFinal: false },
            { index: 9, text: 'SI-', pre: 's', preDur: 0.07, vowel: 'I', beat: 3.46, dur: 0.30, stress: 0.94, pitchST: 2.6, isGhost: false, isFinal: false },
            { index: 10, text: 'lent', pre: 'l', preDur: 0.04, vowel: 'ent', beat: 3.80, dur: 0.16, stress: 0.20, pitchST: -2.6, isGhost: true, isFinal: true },
        ],
    },
];

let customPhraseStore = null;

function computeRampProgress(syllables) {
    const out = (syllables || []).map((s) => ({ ...s }));
    let ghostRun = [];
    for (let i = 0; i < out.length; i += 1) {
        if (out[i].isGhost) {
            ghostRun.push(i);
        } else {
            const len = ghostRun.length;
            ghostRun.forEach((gIdx, pos) => {
                out[gIdx].rampProgress = len > 1 ? (pos + 1) / (len + 1) : 0.45;
            });
            ghostRun = [];
            out[i].rampProgress = 1.0;
        }
    }
    ghostRun.forEach((gIdx, pos) => {
        out[gIdx].rampProgress = (pos + 1) / (ghostRun.length + 1);
    });
    return out;
}

export function setCustomPhrase(phraseObj) {
    if (!phraseObj || !Array.isArray(phraseObj.syllables) || phraseObj.syllables.length === 0) return null;
    customPhraseStore = {
        id: 'custom',
        title: phraseObj.title || 'Custom Target Sentence',
        vibeLabel: phraseObj.vibeLabel || 'Custom Target Sentence',
        bpm: Number(phraseObj.bpm) || 88,
        teacherNote: phraseObj.teacherNote || 'Custom sentence synthesized via Reference TTS and segmented into acoustic P-centers.',
        pauseGate: phraseObj.pauseGate || null,
        feet: Array.isArray(phraseObj.feet) && phraseObj.feet.length > 0
            ? phraseObj.feet
            : [{ label: phraseObj.title || 'Custom Phrase', startBeat: 0.0, endBeat: 4.0 }],
        syllables: computeRampProgress(phraseObj.syllables),
        audioBase64: phraseObj.audioBase64 || null,
        mimeType: phraseObj.mimeType || 'audio/wav',
    };
    return customPhraseStore;
}

export function getPhraseById(phraseId) {
    if (phraseId === 'custom' && customPhraseStore) {
        return customPhraseStore;
    }
    const found = PROSODY_PHRASES.find((p) => p.id === phraseId) || PROSODY_PHRASES[0];
    return {
        ...found,
        syllables: computeRampProgress(found.syllables),
    };
}

export function recordToSyllableItems(record, targetBeats = 4.0) {
    if (!record) return [];
    const totalDur = Math.max(0.4, Number(record.summary?.duration_seconds) || 2.0);
    const details = Array.isArray(record.syllable_details) && record.syllable_details.length > 0
        ? record.syllable_details
        : null;

    if (details) {
        const firstT = Math.max(0, Number(details[0].p_center_time ?? details[0].nucleus_time) - 0.12);
        const lastDetail = details[details.length - 1];
        const lastEndT = Math.max(
            firstT + 0.35,
            Number(lastDetail.p_center_time ?? lastDetail.nucleus_time) + Number(lastDetail.vowel_duration || 0.15) + 0.08,
        );
        const spanT = Math.max(0.35, lastEndT - firstT);
        const scale = (targetBeats - 0.28) / spanT;

        return computeRampProgress(details.map((d, idx) => {
            const pTime = Number(d.p_center_time ?? d.nucleus_time ?? 0);
            const cTime = Number(d.consonant_onset_time ?? pTime);
            const preSec = Math.max(0, Number(d.pre_duration ?? (pTime - cTime)));
            const vSec = Math.max(0.04, Number(d.vowel_duration ?? 0.12));
            const prom = Number(d.prominence ?? 0.55);
            const isStressed = Boolean(d.is_stressed);
            const beat = Math.max(0.12, Math.min(targetBeats - 0.12, 0.16 + (pTime - firstT) * scale));
            const dur = Math.max(0.09, Math.min(0.95, vSec * scale));
            const preDur = Math.max(0, Math.min(0.22, preSec * scale));

            return {
                index: idx,
                text: `S${idx + 1}`,
                pre: preDur >= 0.025 ? 'c' : '',
                preDur: Number(preDur.toFixed(3)),
                vowel: `S${idx + 1}`,
                beat: Number(beat.toFixed(3)),
                dur: Number(dur.toFixed(3)),
                stress: Number(prom.toFixed(3)),
                pitchST: Number(d.pitch_st ?? 0),
                pitchSlope: Number(d.pitch_slope ?? 0),
                isGhost: !isStressed,
                isFinal: idx === details.length - 1,
                timeSec: pTime,
                vowelSec: vSec,
                preSec,
            };
        }));
    }

    const onsets = Array.isArray(record.syllable_p_centers) && record.syllable_p_centers.length > 0
        ? record.syllable_p_centers
        : (Array.isArray(record.syllable_onsets) ? record.syllable_onsets : []);
    if (!onsets.length) return [];

    const firstT = Math.max(0, Number(onsets[0]) - 0.10);
    const lastT = Math.max(firstT + 0.35, Number(onsets[onsets.length - 1]) + 0.22, totalDur);
    const spanT = Math.max(0.35, lastT - firstT);
    const scale = (targetBeats - 0.28) / spanT;

    return computeRampProgress(onsets.map((t, idx) => {
        const nextT = idx + 1 < onsets.length ? Number(onsets[idx + 1]) : lastT;
        const ioiSec = Math.max(0.06, nextT - Number(t));
        const isStressed = idx % 3 === 0 || ioiSec >= 0.24;
        const vSec = Math.min(0.38, Math.max(0.05, ioiSec * (isStressed ? 0.68 : 0.42)));
        const preSec = isStressed ? 0.045 : 0.015;
        const beat = Math.max(0.12, Math.min(targetBeats - 0.12, 0.16 + (Number(t) - firstT) * scale));
        const dur = Math.max(0.09, Math.min(0.85, vSec * scale));
        return {
            index: idx,
            text: `S${idx + 1}`,
            pre: isStressed ? 'c' : '',
            preDur: Number((preSec * scale).toFixed(3)),
            vowel: `S${idx + 1}`,
            beat: Number(beat.toFixed(3)),
            dur: Number(dur.toFixed(3)),
            stress: isStressed ? 0.85 : 0.24,
            pitchST: isStressed ? 2.5 : -1.2,
            pitchSlope: 0,
            isGhost: !isStressed,
            isFinal: idx === onsets.length - 1,
            timeSec: Number(t),
            vowelSec: vSec,
            preSec,
        };
    }));
}

export function buildProfileComparison(phraseId, profileKey = 'dysfluent_hesitation') {
    const phrase = getPhraseById(phraseId);
    const natSyls = phrase.syllables;
    const midIdx = Math.max(1, Math.floor(natSyls.length * 0.6));

    const lrnSyls = natSyls.map((nat, idx) => {
        let rawBeat;
        let normBeat = nat.beat;
        let dur = nat.dur;
        let stress = nat.stress;
        let hasBlockBefore = false;
        let blockMs = 0;
        let isProlonged = false;
        let isStuttered = false;
        let stutterPrefix = '';
        let isClipped = false;
        let crashedPause = false;

        if (profileKey === 'dysfluent_hesitation') {
            rawBeat = Number((nat.beat / 0.78).toFixed(3));
            if (nat.isGhost && idx >= Math.max(1, midIdx - 3) && idx < midIdx) {
                dur = Number((nat.dur * 2.35).toFixed(3));
                stress = Math.min(0.85, nat.stress + 0.45);
                isProlonged = true;
            }
            if (!nat.isGhost && idx >= midIdx) {
                hasBlockBefore = idx === midIdx;
                blockMs = hasBlockBefore ? 440 : 0;
                normBeat = Number((nat.beat + 0.34).toFixed(3));
            }
        } else if (profileKey === 'syllable_timed_choppy') {
            rawBeat = Number((nat.beat / 0.84).toFixed(3));
            if (nat.isGhost) {
                dur = Number((nat.dur * 2.15).toFixed(3));
                stress = 0.72;
                isProlonged = true;
                normBeat = Number((nat.beat + 0.08).toFixed(3));
            } else if (nat.pre && nat.pre.length >= 2) {
                normBeat = Number((nat.beat + 0.15).toFixed(3));
            }
        } else if (profileKey === 'cluttered_runon') {
            rawBeat = Number((nat.beat / 1.16).toFixed(3));
            if (nat.isFinal) {
                dur = Number((nat.dur * 0.48).toFixed(3));
                isClipped = true;
            }
            if (idx >= midIdx) {
                normBeat = Number(Math.max(0.2, nat.beat - 0.24).toFixed(3));
                crashedPause = idx === midIdx + 1;
            }
        } else if (profileKey === 'dysfluent_stutter') {
            rawBeat = Number((nat.beat / 0.82).toFixed(3));
            if (!nat.isGhost && idx >= Math.min(2, natSyls.length - 1)) {
                isStuttered = true;
                stutterPrefix = `[${(nat.pre || nat.text.slice(0, 1)).toLowerCase()}-]`;
                normBeat = Number((nat.beat + 0.19).toFixed(3));
            }
        } else {
            // native_expressive
            rawBeat = Number((nat.beat / 0.92).toFixed(3));
            normBeat = Number((nat.beat + (nat.isGhost ? -0.01 : 0.02)).toFixed(3));
            dur = Number((nat.dur * (nat.isGhost ? 0.92 : 1.05)).toFixed(3));
        }

        return {
            ...nat,
            rawBeat,
            normBeat,
            dur,
            stress,
            hasBlockBefore,
            blockMs,
            isProlonged,
            isStuttered,
            stutterPrefix,
            isClipped,
            crashedPause,
        };
    });

    return { phrase, natSyls, lrnSyls };
}

export function alignRecordPairToTetherItems(teacherRecord, studentRecord, phraseId = 'prepared', profileKey = 'dysfluent_hesitation') {
    const base = getPhraseById(phraseId);
    const useStudentRecord = Boolean(
        studentRecord &&
        (profileKey === 'recorded_take' || !profileKey || profileKey === 'dysfluent_hesitation') &&
        ((Array.isArray(studentRecord.syllable_details) && studentRecord.syllable_details.length > 0) ||
            (Array.isArray(studentRecord.syllable_onsets) && studentRecord.syllable_onsets.length > 0)),
    );

    if (!useStudentRecord) {
        return {
            ...buildProfileComparison(phraseId, profileKey),
            sourceMode: 'preset',
        };
    }

    const rawStudentSyls = recordToSyllableItems(studentRecord, 4.0);
    const teacherSylsFromRecord = teacherRecord ? recordToSyllableItems(teacherRecord, 4.0) : [];
    const rawTeacherSyls = (teacherSylsFromRecord.length >= 2 || base.syllables.length < 2)
        ? (teacherSylsFromRecord.length > 0 ? teacherSylsFromRecord : base.syllables)
        : base.syllables;

    const count = Math.max(1, rawTeacherSyls.length);
    const natSyls = rawTeacherSyls.slice(0, count).map((s, idx) => ({
        ...s,
        index: idx,
        text: base.syllables[idx]?.text || s.text || `S${idx + 1}`,
        pre: base.syllables[idx]?.pre ?? s.pre ?? '',
        vowel: base.syllables[idx]?.vowel || s.vowel || `S${idx + 1}`,
    }));

    if (rawStudentSyls.length === 0) {
        return {
            phrase: base,
            natSyls,
            lrnSyls: natSyls.map((nat) => ({
                ...nat,
                rawBeat: nat.beat,
                normBeat: nat.beat,
                isMissing: true,
                hasBlockBefore: false,
                blockMs: 0,
                isProlonged: false,
                isClipped: false,
                crashedPause: false,
                isStuttered: false,
            })),
            sourceMode: teacherSylsFromRecord.length >= 2 ? 'recorded_pair' : 'student_record',
        };
    }

    const studentDur = Math.max(0.4, Number(studentRecord.summary?.duration_seconds) || 2.0);
    const teacherDur = Math.max(0.4, Number(teacherRecord?.summary?.duration_seconds) || (60 / base.bpm) * 4.0);
    const rateRatio = teacherDur / studentDur;

    const alignedCount = Math.min(count, rawStudentSyls.length);
    const firstNat = natSyls[0].beat;
    const lastNat = natSyls[alignedCount - 1].beat;
    const firstStu = rawStudentSyls[0].beat;
    const lastStu = rawStudentSyls[alignedCount - 1].beat;
    const natSpan = Math.max(0.25, lastNat - firstNat);
    const stuSpan = Math.max(0.25, lastStu - firstStu);

    const lrnSyls = natSyls.map((nat, idx) => {
        const stu = rawStudentSyls[idx];
        if (!stu) {
            return {
                ...nat,
                rawBeat: nat.beat,
                normBeat: nat.beat,
                dur: Math.max(0.08, nat.dur * 0.55),
                stress: 0.15,
                isMissing: true,
                hasBlockBefore: false,
                blockMs: 0,
                isProlonged: false,
                isClipped: false,
                crashedPause: false,
                isStuttered: false,
            };
        }
        const normBeat = alignedCount === 1
            ? nat.beat
            : Number((firstNat + ((stu.beat - firstStu) / stuSpan) * natSpan).toFixed(3));
        const rawBeat = Number(Math.max(0.08, Math.min(4.6, normBeat / Math.max(0.5, Math.min(2.0, rateRatio)))).toFixed(3));
        const durRatio = stu.dur / Math.max(0.05, nat.dur);
        const prevStuEnd = idx > 0 ? rawStudentSyls[idx - 1].beat + rawStudentSyls[idx - 1].dur : 0;
        const prevNatEnd = idx > 0 ? natSyls[idx - 1].beat + natSyls[idx - 1].dur : 0;
        const gapExcessBeats = (stu.beat - prevStuEnd) - (nat.beat - prevNatEnd);
        const hasBlockBefore = idx > 0 && gapExcessBeats > 0.24;
        const blockMs = hasBlockBefore ? Math.round(gapExcessBeats * (60 / base.bpm) * 1000) : 0;
        const isProlonged = nat.isGhost && durRatio >= 1.42;
        const isClipped = !nat.isGhost && durRatio <= 0.64;
        const crashedPause = idx > 0 && (nat.beat - prevNatEnd) >= 0.30 && (stu.beat - prevStuEnd) <= 0.14;

        return {
            ...nat,
            rawBeat,
            normBeat,
            dur: stu.dur,
            stress: stu.stress,
            pitchST: stu.pitchST,
            isMissing: false,
            hasBlockBefore,
            blockMs,
            isProlonged,
            isStuttered: false,
            stutterPrefix: '',
            isClipped,
            crashedPause,
        };
    });

    return {
        phrase: base,
        natSyls,
        lrnSyls,
        sourceMode: teacherRecord ? 'recorded_pair' : 'recorded_vs_phrase',
    };
}

/**
 * Timing Review Winner: Render VocAlign Elastic Tethers & Beat Bins SVG (clean, no middle deviation strip).
 */
export function renderVocAlignTetherDiagnosticSVG({
    phraseId = 'prepared',
    profileKey = 'dysfluent_hesitation',
    normFactor = 1.0,
    teacherRecord = null,
    studentRecord = null,
} = {}) {
    const parsedNorm = Number(normFactor);
    const nf = Math.max(0, Math.min(1, Number.isFinite(parsedNorm) ? parsedNorm : 1.0));
    const aligned = alignRecordPairToTetherItems(teacherRecord, studentRecord, phraseId, profileKey);
    const { natSyls, lrnSyls, sourceMode } = aligned;

    const maxBeat = 4.65;
    const leftPad = 48;
    const rightPad = 928;
    const spanW = rightPad - leftPad;
    const beatToX = (b) => leftPad + (Math.max(0, Math.min(maxBeat, b)) / maxBeat) * spanW;

    const items = natSyls.map((nat, idx) => {
        const lrn = lrnSyls[idx] || nat;
        const displayBeat = lrn.rawBeat * (1 - nf) + lrn.normBeat * nf;
        const offsetBeats = displayBeat - nat.beat;
        const inBeatBin = Math.abs(offsetBeats) <= 0.095 && !lrn.hasBlockBefore && !lrn.isStuttered;

        let strokeColor = '#10b981';
        let ribbonFill = 'rgba(16, 185, 129, 0.22)';

        if (lrn.isMissing) {
            strokeColor = '#64748b';
            ribbonFill = 'rgba(100, 116, 139, 0.14)';
        } else if (lrn.hasBlockBefore) {
            strokeColor = '#f43f5e';
            ribbonFill = 'rgba(244, 63, 94, 0.30)';
        } else if (lrn.isStuttered) {
            strokeColor = '#c084fc';
            ribbonFill = 'rgba(192, 132, 252, 0.28)';
        } else if (lrn.isProlonged) {
            strokeColor = '#f59e0b';
            ribbonFill = 'rgba(245, 158, 11, 0.32)';
        } else if (lrn.crashedPause || lrn.isClipped) {
            strokeColor = '#fb923c';
            ribbonFill = 'rgba(249, 115, 22, 0.28)';
        } else if (!inBeatBin) {
            strokeColor = offsetBeats > 0 ? '#a855f7' : '#fb923c';
            ribbonFill = offsetBeats > 0 ? 'rgba(168, 85, 247, 0.24)' : 'rgba(249, 115, 22, 0.24)';
        }

        return {
            ...nat,
            lrn,
            displayBeat,
            inBeatBin,
            strokeColor,
            ribbonFill,
        };
    });

    const natTrackY = 16;
    const natTrackH = 84;
    const gutterY = 100;
    const lrnTrackY = 200;
    const lrnTrackH = 92;

    let svg = `
    <svg data-prosody-tether-svg="true" data-source-mode="${escapeHtml(sourceMode)}" viewBox="0 0 960 320" class="w-full h-auto rounded-lg bg-slate-950 shadow-inner">
      <defs>
        <pattern id="pl-hatch-pre" width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
          <rect width="8" height="8" fill="rgba(245, 158, 11, 0.18)" />
          <line x1="0" y1="0" x2="0" y2="8" stroke="#f59e0b" stroke-width="2.2" />
        </pattern>
        <pattern id="pl-hatch-tear" width="10" height="10" patternUnits="userSpaceOnUse" patternTransform="rotate(-45)">
          <rect width="10" height="10" fill="rgba(244, 63, 94, 0.30)" />
          <line x1="0" y1="0" x2="0" y2="10" stroke="#fb7185" stroke-width="3" />
        </pattern>
        <linearGradient id="pl-beatbin-grad" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stop-color="#10b981" stop-opacity="0.02" />
          <stop offset="50%" stop-color="#10b981" stop-opacity="0.24" />
          <stop offset="100%" stop-color="#10b981" stop-opacity="0.02" />
        </linearGradient>
      </defs>

      <!-- Track Containers -->
      <rect x="14" y="${natTrackY}" width="932" height="${natTrackH}" rx="7" fill="rgba(15, 23, 42, 0.90)" stroke="rgba(56, 189, 248, 0.35)" />
      <text x="24" y="${natTrackY + 16}" fill="#38bdf8" font-size="10.5" font-weight="800">
        REFERENCE
      </text>

      <rect x="14" y="${gutterY}" width="932" height="${lrnTrackY - gutterY}" fill="rgba(2, 6, 23, 0.82)" />

      <rect x="14" y="${lrnTrackY}" width="932" height="${lrnTrackH}" rx="7" fill="rgba(15, 23, 42, 0.90)" stroke="rgba(244, 63, 94, 0.35)" />
      <text x="24" y="${lrnTrackY + 16}" fill="#f8fafc" font-size="10.5" font-weight="800">
        LEARNER TAKE
      </text>
    `;

    // Beat Grid Lines
    for (let b = 0; b <= 4.5; b += 0.5) {
        const gx = beatToX(b);
        const isWhole = Math.abs(b - Math.round(b)) < 0.01 && b >= 1 && b <= 4;
        svg += `<line x1="${gx}" y1="${natTrackY}" x2="${gx}" y2="${lrnTrackY + lrnTrackH}" stroke="${isWhole ? 'rgba(99, 102, 241, 0.35)' : 'rgba(148, 163, 184, 0.08)'}" stroke-width="${isWhole ? 1.5 : 1}" stroke-dasharray="${isWhole ? '4 3' : ''}" />`;
        if (isWhole) {
            svg += `<text x="${gx}" y="${lrnTrackY + lrnTrackH + 16}" text-anchor="middle" fill="#818cf8" font-size="10" font-family="monospace" font-weight="700">Beat ${Math.round(b)}</text>`;
        }
    }

    // Danielsen Beat Bins around Stressed Native P-Centers
    items.forEach((it) => {
        if (!it.isGhost) {
            const nx = beatToX(it.beat);
            const binHalfW = Math.max(16, (0.095 / maxBeat) * spanW);
            svg += `
              <rect x="${nx - binHalfW}" y="${natTrackY + 20}" width="${binHalfW * 2}" height="${lrnTrackY + lrnTrackH - natTrackY - 24}" fill="url(#pl-beatbin-grad)" />
              <line x1="${nx}" y1="${natTrackY + 20}" x2="${nx}" y2="${lrnTrackY + lrnTrackH - 4}" stroke="#10b981" stroke-width="1.2" stroke-opacity="0.55" stroke-dasharray="3 2" />
            `;
        }
    });

    // Syllables, Clean Direct Elastic Tethers & Tear Zones
    let minLearnerX = 28;
    let prevLearnerRightX = 28;
    items.forEach((it, idx) => {
        const nx = beatToX(it.beat);
        const nw = Math.max(22, (it.dur / maxBeat) * spanW);
        const showPre = !it.isGhost && (it.pre || '').length >= 2 && it.preDur > 0;
        const nPreW = showPre ? Math.max(14, (it.preDur / maxBeat) * spanW) : 0;

        const rawLx = beatToX(it.displayBeat);
        const lx = Math.max(rawLx, minLearnerX + (it.lrn.hasBlockBefore ? 40 : 0));
        const lw = Math.max(22, (it.lrn.dur / maxBeat) * spanW);
        minLearnerX = lx + lw + 4;

        const natTop = it.isGhost ? natTrackY + 42 : natTrackY + 32;
        const natH = it.isGhost ? 26 : 38;
        const natBot = natTop + natH;

        const lrnTop = it.isGhost && !it.lrn.isProlonged ? lrnTrackY + 38 : lrnTrackY + 28;
        const lrnH = it.isGhost && !it.lrn.isProlonged ? 28 : 40;

        if (it.lrn.hasBlockBefore) {
            const tearStart = idx > 0 ? Math.min(lx - 24, prevLearnerRightX + 2) : Math.max(48, lx - 52);
            const tearEnd = Math.max(tearStart + 30, lx - 3);
            const tearMid = 0.5 * (tearStart + tearEnd);
            svg += `
              <rect x="${tearStart}" y="${gutterY + 8}" width="${tearEnd - tearStart}" height="${lrnTrackY + lrnTrackH - gutterY - 14}" fill="url(#pl-hatch-tear)" stroke="#f43f5e" stroke-width="1.8" stroke-dasharray="4 2" />
              <rect x="${tearMid - 46}" y="${gutterY + 36}" width="92" height="18" rx="4" fill="#881337" stroke="#fb7185" />
              <text x="${tearMid}" y="${gutterY + 48}" text-anchor="middle" fill="#ffe4e6" font-size="9" font-family="monospace" font-weight="800">⚡ ${it.lrn.blockMs}ms Pause</text>
            `;
        }

        if (!it.lrn.isMissing) {
            // Elastic Tether Ribbon
            svg += `
              <polygon points="${nx},${natBot} ${nx + nw},${natBot} ${lx + lw},${lrnTop} ${lx},${lrnTop}" fill="${it.ribbonFill}" />
              <line x1="${nx}" y1="${natBot}" x2="${lx}" y2="${lrnTop}" stroke="${it.strokeColor}" stroke-width="2.2" />
              <line x1="${nx + nw}" y1="${natBot}" x2="${lx + lw}" y2="${lrnTop}" stroke="${it.strokeColor}" stroke-width="1.4" stroke-dasharray="3 2" />
            `;
        }

        // Native Pre-Beat Consonant + Capsule + ♦ P-Center
        if (nPreW > 0 && !it.isGhost) {
            svg += `
              <rect x="${nx - nPreW}" y="${natTop + 5}" width="${nPreW}" height="${natH - 10}" rx="4" fill="url(#pl-hatch-pre)" stroke="#f59e0b" stroke-width="1.2" />
              <text x="${nx - nPreW / 2}" y="${natTop + natH / 2 + 3}" text-anchor="middle" fill="#fde68a" font-size="9" font-family="monospace" font-weight="800">${escapeHtml(it.pre)}-</text>
            `;
        }
        svg += `
          <rect x="${nx}" y="${natTop}" width="${nw}" height="${natH}" rx="${it.isGhost ? 12 : 7}" fill="${it.isGhost ? 'rgba(30, 41, 59, 0.85)' : 'rgba(14, 116, 144, 0.45)'}" stroke="${it.isGhost ? '#64748b' : '#38bdf8'}" stroke-width="1.6" />
          <polygon points="${nx},${natTop + natH / 2 - 5} ${nx + 5},${natTop + natH / 2} ${nx},${natTop + natH / 2 + 5} ${nx - 5},${natTop + natH / 2}" fill="#fbbf24" />
          <text x="${nx + nw / 2}" y="${natTop + natH / 2 + 4}" text-anchor="middle" fill="#f8fafc" font-size="${it.isGhost ? 10 : 11.5}" font-weight="800">${escapeHtml(it.text)}</text>
        `;

        // Learner Capsule + Callouts
        if (it.lrn.isClipped) {
            const fullW = Math.max(lw + 14, nw);
            svg += `
              <rect x="${lx + lw}" y="${lrnTop}" width="${fullW - lw}" height="${lrnH}" rx="4" fill="rgba(249, 115, 22, 0.15)" stroke="#fb923c" stroke-dasharray="3 2" />
              <line x1="${lx + lw}" y1="${lrnTop - 6}" x2="${lx + lw}" y2="${lrnTop + lrnH + 6}" stroke="#f43f5e" stroke-width="2.2" />
            `;
        }
        svg += `
          <rect x="${lx}" y="${lrnTop}" width="${lw}" height="${lrnH}" rx="${it.isGhost && !it.lrn.isProlonged ? 12 : 7}" fill="rgba(15, 23, 42, 0.92)" stroke="${it.strokeColor}" stroke-width="2" />
          <polygon points="${lx},${lrnTop + lrnH / 2 - 5} ${lx + 5},${lrnTop + lrnH / 2} ${lx},${lrnTop + lrnH / 2 + 5} ${lx - 5},${lrnTop + lrnH / 2}" fill="${it.strokeColor}" />
          <text x="${lx + lw / 2}" y="${lrnTop + lrnH / 2 + 4}" text-anchor="middle" fill="#f8fafc" font-size="${it.isGhost && !it.lrn.isProlonged ? 10 : 11.5}" font-weight="800">${escapeHtml(it.lrn.isStuttered ? `${it.lrn.stutterPrefix}${it.text}` : it.text)}</text>
        `;
        prevLearnerRightX = lx + lw;
    });

    svg += `
      <g id="prosody-tether-playhead" transform="translate(-40, 0)" style="opacity: 0; pointer-events: none;">
        <line x1="0" y1="16" x2="0" y2="296" stroke="#38bdf8" stroke-width="2.8" />
        <polygon points="-7,16 7,16 0,26" fill="#38bdf8" />
      </g>
    </svg>`;
    return svg;
}

/**
 * Live Flow Guide Winner: Render Stationary 16-Slot Prosodic Flow Matrix + Bouncing Ball + Bar 2 Ghost Trail SVG.
 */
export function renderFlowMatrixTrainerSVG({
    phraseId = 'prepared',
    beat = 0.0,
    isResponseBar = false,
    performer = 'bot_native',
    liveRecord = null,
} = {}) {
    const phrase = getPhraseById(phraseId);
    const syls = phrase.syllables;
    const clampedBeat = ((Number(beat) % 4.0) + 4.0) % 4.0;
    const leftX = 48;
    const rightX = 932;
    const width = rightX - leftX;
    const beatToX = (b) => leftX + (Math.max(0, Math.min(4.0, b)) / 4.0) * width;
    const subLabels = ['1', 'e', '&', 'a', '2', 'e', '&', 'a', '3', 'e', '&', 'a', '4', 'e', '&', 'a'];

    const recordedItems = liveRecord ? recordToSyllableItems(liveRecord, 4.0) : [];
    const perfTrails = syls.map((s, idx) => {
        if (performer === 'recorded_take' && recordedItems[idx]) {
            return {
                perfBeat: recordedItems[idx].beat,
                perfDur: recordedItems[idx].dur,
                kind: 'recorded',
                label: s.text,
            };
        }
        if (performer === 'bot_dysfluent') {
            const bloat = s.isGhost && idx >= 4 && idx <= 6;
            const block = !s.isGhost && idx >= Math.floor(syls.length * 0.6);
            return {
                perfBeat: Number(Math.min(3.85, s.beat + (block ? 0.20 : 0)).toFixed(3)),
                perfDur: Number((s.dur * (bloat ? 2.2 : 1.0)).toFixed(3)),
                kind: block ? 'hesitation_block' : (bloat ? 'prolongation' : 'fluent'),
                label: s.text,
            };
        }
        if (performer === 'bot_choppy') {
            return {
                perfBeat: Number(Math.min(3.88, s.beat + (s.pre && s.pre.length >= 2 ? 0.14 : 0.04)).toFixed(3)),
                perfDur: Number((s.dur * (s.isGhost ? 1.95 : 0.78)).toFixed(3)),
                kind: s.isGhost ? 'prolongation' : 'choppy',
                label: s.text,
            };
        }
        return {
            perfBeat: s.beat,
            perfDur: s.dur,
            kind: 'fluent',
            label: s.text,
        };
    });

    let svg = `
    <svg data-prosody-flow-svg="true" viewBox="0 0 960 356" class="w-full h-auto rounded-lg bg-slate-950 shadow-inner">
      <defs>
        <pattern id="fm-amber-hatch" width="8" height="8" patternTransform="rotate(-45 0 0)" patternUnits="userSpaceOnUse">
          <rect width="8" height="8" fill="rgba(245, 158, 11, 0.18)" />
          <line x1="0" y1="0" x2="0" y2="8" stroke="rgba(251, 191, 36, 0.65)" stroke-width="2.5" />
        </pattern>
        <pattern id="fm-pause-gate" width="6" height="6" patternUnits="userSpaceOnUse">
          <rect width="6" height="6" fill="rgba(139, 92, 246, 0.10)" />
          <circle cx="3" cy="3" r="1" fill="rgba(192, 132, 252, 0.40)" />
        </pattern>
        <linearGradient id="fm-warm-wipe" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stop-color="#10b981" stop-opacity="0.72" />
          <stop offset="100%" stop-color="#fbbf24" stop-opacity="0.55" />
        </linearGradient>
        <linearGradient id="fm-call-wipe" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stop-color="#0284c7" stop-opacity="0.68" />
          <stop offset="100%" stop-color="#38bdf8" stop-opacity="0.48" />
        </linearGradient>
      </defs>

      <!-- Top 2-Bar Call-and-Response HUD -->
      <rect x="16" y="6" width="440" height="22" rx="5" fill="rgba(15, 23, 42, 0.92)" stroke="${!isResponseBar ? '#38bdf8' : '#475569'}" stroke-width="${!isResponseBar ? 1.6 : 1}" />
      <rect x="16" y="6" width="${!isResponseBar ? (440 * clampedBeat) / 4.0 : 440}" height="22" rx="5" fill="rgba(56, 189, 248, 0.22)" />
      <text x="26" y="21" fill="${!isResponseBar ? '#7dd3fc' : '#94a3b8'}" font-size="10" font-weight="800" font-family="monospace">
        BAR 1: NATIVE MODEL CALL ${!isResponseBar && clampedBeat >= 3.35 ? '· 🌬️ INHALE PICKUP!' : `(Beat ${(clampedBeat + 1).toFixed(1)})`}
      </text>

      <rect x="468" y="6" width="476" height="22" rx="5" fill="rgba(15, 23, 42, 0.92)" stroke="${isResponseBar ? '#10b981' : '#475569'}" stroke-width="${isResponseBar ? 1.6 : 1}" />
      <rect x="468" y="6" width="${isResponseBar ? (476 * clampedBeat) / 4.0 : 0}" height="22" rx="5" fill="rgba(16, 185, 129, 0.25)" />
      <text x="478" y="21" fill="${isResponseBar ? '#6ee7b7' : '#94a3b8'}" font-size="10" font-weight="800" font-family="monospace">
        BAR 2: LIVE RESPONSE (${escapeHtml(performer.toUpperCase())})
      </text>
    `;

    // Stress-Foot Brackets
    phrase.feet.forEach((f) => {
        const fx1 = beatToX(f.startBeat);
        const fx2 = beatToX(f.endBeat);
        const fw = Math.max(24, fx2 - fx1 - 3);
        const active = clampedBeat >= f.startBeat && clampedBeat < f.endBeat;
        svg += `
          <rect x="${fx1 + 1.5}" y="32" width="${fw}" height="17" rx="4" fill="${active ? 'rgba(99, 102, 241, 0.26)' : 'rgba(30, 41, 59, 0.75)'}" stroke="${active ? '#38bdf8' : 'rgba(148, 163, 184, 0.25)'}" />
          <text x="${fx1 + fw / 2}" y="44" text-anchor="middle" fill="${active ? '#f8fafc' : '#94a3b8'}" font-size="9" font-family="monospace" font-weight="700">${escapeHtml(f.label)}</text>
        `;
    });

    // 16-Slot Grid & 4 Primary Beat Pillars
    for (let slot = 0; slot < 16; slot += 1) {
        const slotBeat = slot * 0.25;
        const x = beatToX(slotBeat);
        const slotW = width / 16;
        const isMain = slot % 4 === 0;
        const beatNum = Math.floor(slot / 4) + 1;
        const isCur = clampedBeat >= slotBeat && clampedBeat < slotBeat + 0.25;
        svg += `<rect x="${x}" y="53" width="${slotW - 2}" height="256" rx="3" fill="${isCur ? 'rgba(56, 189, 248, 0.08)' : slot % 2 === 0 ? 'rgba(30, 41, 59, 0.28)' : 'rgba(15, 23, 42, 0.28)'}" />`;
        if (isMain) {
            svg += `
              <line x1="${x}" y1="53" x2="${x}" y2="309" stroke="#818cf8" stroke-width="1.8" stroke-dasharray="5 3" />
              <rect x="${x - 34}" y="55" width="68" height="16" rx="4" fill="rgba(30, 27, 75, 0.92)" stroke="#818cf8" />
              <text x="${x}" y="66" text-anchor="middle" fill="#e0e7ff" font-size="9.5" font-weight="800" font-family="monospace">BEAT ${beatNum}</text>
            `;
        }
        svg += `<text x="${x + (isMain ? 0 : slotW * 0.15)}" y="324" text-anchor="middle" fill="${isMain ? '#a5b4fc' : '#64748b'}" font-size="${isMain ? 11 : 9.5}" font-family="monospace" font-weight="700">${subLabels[slot]}</text>`;
    }

    // Thought-Group Pause Gate (||)
    if (phrase.pauseGate) {
        const gx1 = beatToX(phrase.pauseGate.startBeat);
        const gx2 = beatToX(phrase.pauseGate.endBeat);
        const gw = Math.max(18, gx2 - gx1);
        const gMid = 0.5 * (gx1 + gx2);
        svg += `
          <rect x="${gx1}" y="74" width="${gw}" height="184" rx="5" fill="url(#fm-pause-gate)" stroke="#c084fc" stroke-dasharray="4 3" />
          <text x="${gMid}" y="88" text-anchor="middle" fill="#e9d5ff" font-size="8.5" font-family="monospace" font-weight="800">|| PAUSE GATE</text>
        `;
    }

    // Parabolic Bouncing Ball Arcs + Anacrusis Ramps
    let arcD = '';
    for (let i = 0; i < syls.length - 1; i += 1) {
        const s1 = syls[i];
        const s2 = syls[i + 1];
        const x1 = beatToX(s1.beat);
        const x2 = beatToX(s2.beat);
        const y1 = s1.isGhost ? 206 - s1.rampProgress * 40 : 120;
        const y2 = s2.isGhost ? 206 - s2.rampProgress * 40 : 120;
        const ioi = Math.max(0.12, s2.beat - s1.beat);
        const apexLift = s2.isGhost ? Math.min(32, 14 + ioi * 30) : Math.min(82, 46 + ioi * 60);
        const apexY = Math.max(62, Math.min(y1, y2) - apexLift);
        arcD += `M ${x1.toFixed(1)} ${y1.toFixed(1)} Q ${(0.5 * (x1 + x2)).toFixed(1)} ${apexY.toFixed(1)} ${x2.toFixed(1)} ${y2.toFixed(1)} `;
    }
    svg += `<path d="${arcD}" fill="none" stroke="${isResponseBar ? 'rgba(16, 185, 129, 0.45)' : 'rgba(56, 189, 248, 0.45)'}" stroke-width="2" stroke-dasharray="6 4" />`;

    // Target Syllables (Anacrusis Ghost Beads + Stressed Capsules with Hatched Pre-Beat Consonant Runway & ♦ P-Center)
    syls.forEach((s) => {
        const pCenterX = beatToX(s.beat);
        const vowelW = Math.max(32, (s.dur / 4.0) * width);
        const preW = !s.isGhost && s.pre && s.pre.length >= 2
            ? Math.max(20, (s.preDur / 4.0) * width, s.pre.length * 9 + 6)
            : 0;
        const isActive = clampedBeat >= s.beat - 0.03 && clampedBeat <= s.beat + s.dur;
        const wipePct = Math.max(0, Math.min(1, (clampedBeat - s.beat) / Math.max(0.05, s.dur)));

        if (s.isGhost) {
            const beadW = Math.max(32, vowelW * 0.88);
            const beadH = 25;
            const beadY = 206 - s.rampProgress * 40;
            svg += `
              <rect x="${pCenterX - 2}" y="${beadY}" width="${beadW}" height="${beadH}" rx="12" fill="rgba(30, 41, 59, 0.85)" stroke="${isActive ? '#34d399' : '#64748b'}" stroke-width="1.5" />
              <rect x="${pCenterX - 2}" y="${beadY}" width="${beadW * wipePct}" height="${beadH}" rx="12" fill="${isResponseBar ? 'url(#fm-warm-wipe)' : 'url(#fm-call-wipe)'}" />
              <text x="${pCenterX - 2 + beadW / 2}" y="${beadY + 16}" text-anchor="middle" fill="#e2e8f0" font-size="11" font-weight="700">${escapeHtml(s.text)}</text>
            `;
        } else {
            const capY = 118;
            const capH = 48;
            if (preW > 0) {
                svg += `
                  <rect x="${pCenterX - preW}" y="${capY + 6}" width="${preW}" height="${capH - 12}" rx="5" fill="url(#fm-amber-hatch)" stroke="#f59e0b" stroke-width="1.4" stroke-dasharray="3 2" />
                  <text x="${pCenterX - preW / 2}" y="${capY + 28}" text-anchor="middle" fill="#fde68a" font-size="11" font-family="monospace" font-weight="800">${escapeHtml(s.pre)}-</text>
                `;
            }
            svg += `
              <rect x="${pCenterX}" y="${capY}" width="${vowelW}" height="${capH}" rx="9" fill="rgba(15, 23, 42, 0.92)" stroke="${isActive ? '#34d399' : '#38bdf8'}" stroke-width="${isActive ? 2.4 : 1.7}" />
              <rect x="${pCenterX}" y="${capY}" width="${vowelW * wipePct}" height="${capH}" rx="9" fill="${isResponseBar ? 'url(#fm-warm-wipe)' : 'url(#fm-call-wipe)'}" />
              <polygon points="${pCenterX},${capY + capH / 2 - 6} ${pCenterX + 6},${capY + capH / 2} ${pCenterX},${capY + capH / 2 + 6} ${pCenterX - 6},${capY + capH / 2}" fill="#fbbf24" />
              <text x="${pCenterX + vowelW / 2}" y="${capY + 29}" text-anchor="middle" fill="#f8fafc" font-size="14" font-weight="900">${escapeHtml(s.vowel)}</text>
              <text x="${pCenterX}" y="${capY + capH + 13}" text-anchor="middle" fill="#a5b4fc" font-size="9.5" font-family="monospace" font-weight="700">♦ P-Center</text>
            `;
        }
    });

    // Bar 2 Live Performer Ghost Trail Lane
    const laneY = 262;
    const laneH = 42;
    svg += `
      <rect x="${leftX - 8}" y="${laneY}" width="${width + 16}" height="${laneH}" rx="7" fill="rgba(15, 23, 42, 0.94)" stroke="${isResponseBar ? '#10b981' : 'rgba(148, 163, 184, 0.25)'}" />
      <text x="${leftX}" y="${laneY + 13}" fill="#cbd5e1" font-size="9" font-family="monospace" font-weight="800">
        BAR 2 GHOST TRAIL
      </text>
    `;
    let minTrailX = leftX;
    perfTrails.forEach((t, idx) => {
        const s = syls[idx];
        const tx = beatToX(s.beat);
        const tw = Math.max(22, (s.dur / 4.0) * width);
        const px = Math.max(beatToX(t.perfBeat), minTrailX);
        const pw = Math.max(12, (t.perfDur / 4.0) * width);
        minTrailX = px + pw + 3;
        const by = laneY + 18;
        const stroke = t.kind === 'fluent' ? '#10b981' : (t.kind === 'prolongation' || t.kind === 'hesitation_block' ? '#f59e0b' : '#38bdf8');
        svg += `
          <rect x="${tx}" y="${by}" width="${tw}" height="18" rx="4" fill="none" stroke="rgba(148, 163, 184, 0.35)" stroke-dasharray="3 2" />
          <rect x="${px}" y="${by}" width="${pw}" height="18" rx="4" fill="rgba(16, 185, 129, 0.26)" stroke="${stroke}" stroke-width="1.3" />
          <text x="${px + pw / 2}" y="${by + 12.5}" text-anchor="middle" fill="#f8fafc" font-size="9" font-weight="700">${escapeHtml(t.label)}</text>
        `;
    });

    // Playhead + Bouncing Ball
    const playX = beatToX(clampedBeat);
    let ballY = 118;
    for (let i = 0; i < syls.length - 1; i += 1) {
        const s1 = syls[i];
        const s2 = syls[i + 1];
        if (clampedBeat >= s1.beat && clampedBeat <= s2.beat) {
            const u = (clampedBeat - s1.beat) / Math.max(0.05, s2.beat - s1.beat);
            const y1 = s1.isGhost ? 206 - s1.rampProgress * 40 : 120;
            const y2 = s2.isGhost ? 206 - s2.rampProgress * 40 : 120;
            const apexY = Math.max(62, Math.min(y1, y2) - 54);
            ballY = (1 - u) * (1 - u) * y1 + 2 * (1 - u) * u * apexY + u * u * y2;
            break;
        }
    }
    svg += `
      <line x1="${playX}" y1="53" x2="${playX}" y2="309" stroke="${isResponseBar ? '#34d399' : '#38bdf8'}" stroke-width="2" stroke-opacity="0.75" />
      <circle cx="${playX}" cy="${ballY}" r="9" fill="${isResponseBar ? '#10b981' : '#38bdf8'}" stroke="#ffffff" stroke-width="2" />
    </svg>`;

    return svg;
}

/**
 * Dual-mode audio engine supporting both:
 * - 'synth_beats': Formant voice + rhythmic beat pulse synthesis
 * - 'real_tts': Real recorded / OmniVoice TTS playback without synthetic beats
 */
export class ProsodyAudioPlayer {
    constructor() {
        this.ctx = null;
        this.activeNodes = [];
        this.activeAudioEl = null;
    }

    _ensureCtx() {
        const AudioCtx = window.AudioContext || window.webkitAudioContext;
        if (!AudioCtx) return null;
        if (!this.ctx || this.ctx.state === 'closed') {
            this.ctx = new AudioCtx();
        }
        if (this.ctx.state === 'suspended') {
            void this.ctx.resume();
        }
        return this.ctx;
    }

    stop() {
        this.activeNodes.forEach((node) => {
            try {
                node.stop?.();
                node.disconnect?.();
            } catch {
                // Ignore already-stopped nodes
            }
        });
        this.activeNodes = [];
        if (this.activeAudioEl) {
            try {
                this.activeAudioEl.pause();
                this.activeAudioEl.currentTime = 0;
            } catch {
                // Ignore audio element cleanup error
            }
            this.activeAudioEl = null;
        }
    }

    destroy() {
        this.stop();
        if (this.ctx) {
            try {
                void this.ctx.close?.();
            } catch {
                // Ignore AudioContext close error
            }
            this.ctx = null;
        }
    }

    _pruneNodes(...nodes) {
        this.activeNodes = this.activeNodes.filter((n) => !nodes.includes(n));
        nodes.forEach((node) => {
            try {
                node.disconnect?.();
            } catch {
                // Ignore disconnect error
            }
        });
    }

    playBase64Audio(base64, mimeType = 'audio/wav') {
        this.stop();
        if (!base64 || typeof Audio === 'undefined') return false;
        try {
            const audio = new Audio(`data:${mimeType};base64,${base64}`);
            this.activeAudioEl = audio;
            void audio.play().catch(() => {});
            return true;
        } catch {
            return false;
        }
    }

    playBlobUrl(blobUrl, { playbackRate = 1.0, trimStart = 0, trimEnd = null } = {}) {
        this.stop();
        if (!blobUrl || typeof Audio === 'undefined') return false;
        try {
            const audio = new Audio(blobUrl);
            if ('preservesPitch' in audio) audio.preservesPitch = true;
            if ('mozPreservesPitch' in audio) audio.mozPreservesPitch = true;
            if ('webkitPreservesPitch' in audio) audio.webkitPreservesPitch = true;
            audio.playbackRate = Math.max(0.5, Math.min(2.0, Number(playbackRate) || 1.0));
            if (trimStart > 0) {
                const seekToStart = () => {
                    try {
                        audio.currentTime = trimStart;
                    } catch {
                        // Ignore seek error before metadata
                    }
                };
                if (audio.readyState >= 1) seekToStart();
                else audio.addEventListener('loadedmetadata', seekToStart, { once: true });
            }
            if (trimEnd !== null && Number.isFinite(trimEnd) && trimEnd > trimStart) {
                audio.addEventListener('timeupdate', () => {
                    if (audio.currentTime >= trimEnd) {
                        audio.pause();
                    }
                });
            }
            this.activeAudioEl = audio;
            void audio.play().catch(() => {});
            return true;
        } catch {
            return false;
        }
    }

    scheduleBeatClick(beatIndex, whenSec) {
        const ctx = this._ensureCtx();
        if (!ctx) return;
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.type = 'triangle';
        osc.frequency.setValueAtTime(beatIndex % 4 === 0 ? 190 : 420, whenSec);
        gain.gain.setValueAtTime(0.001, whenSec);
        gain.gain.linearRampToValueAtTime(beatIndex % 4 === 0 ? 0.14 : 0.08, whenSec + 0.005);
        gain.gain.exponentialRampToValueAtTime(0.0001, whenSec + 0.055);
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.onended = () => this._pruneNodes(osc, gain);
        osc.start(whenSec);
        osc.stop(whenSec + 0.06);
        this.activeNodes.push(osc, gain);
    }

    playSyllableSequence(syllables, bpm = 88, includeBeats = true, { normFactor = 1.0 } = {}) {
        this.stop();
        const ctx = this._ensureCtx();
        if (!ctx || !Array.isArray(syllables) || syllables.length === 0) return 0;

        const nf = Math.max(0, Math.min(1, Number.isFinite(Number(normFactor)) ? Number(normFactor) : 1.0));
        const secPerBeat = 60 / Math.max(60, bpm);
        const now = ctx.currentTime + 0.03;

        if (includeBeats) {
            for (let b = 0; b < 4; b += 1) {
                this.scheduleBeatClick(b, now + b * secPerBeat);
            }
        }

        syllables.forEach((s) => {
            if (s.isMissing) return;
            const raw = s.rawBeat ?? s.beat ?? 0;
            const norm = s.normBeat ?? s.beat ?? 0;
            const beatPos = Number(raw) * (1 - nf) + Number(norm) * nf;
            const durSec = Math.max(0.05, Number(s.dur ?? 0.2) * secPerBeat);
            const startSec = now + beatPos * secPerBeat;
            const pitchST = Number(s.pitchST ?? (s.isGhost ? -1.5 : 3.0));
            const f0 = 145 * (2 ** (pitchST / 12));

            const osc = ctx.createOscillator();
            const filter = ctx.createBiquadFilter();
            const gain = ctx.createGain();

            osc.type = 'sawtooth';
            osc.frequency.setValueAtTime(f0, startSec);
            osc.frequency.linearRampToValueAtTime(f0 * (s.isGhost ? 0.96 : 0.90), startSec + durSec);

            filter.type = 'bandpass';
            filter.frequency.setValueAtTime(s.isGhost ? 560 : 720, startSec);
            filter.Q.setValueAtTime(3.2, startSec);

            const peakGain = s.isGhost ? 0.07 : 0.15;
            gain.gain.setValueAtTime(0.0001, startSec);
            gain.gain.linearRampToValueAtTime(peakGain, startSec + Math.min(0.02, durSec * 0.25));
            gain.gain.exponentialRampToValueAtTime(0.0001, startSec + durSec);

            osc.connect(filter);
            filter.connect(gain);
            gain.connect(ctx.destination);
            osc.onended = () => this._pruneNodes(osc, filter, gain);
            osc.start(startSec);
            osc.stop(startSec + durSec + 0.01);
            this.activeNodes.push(osc, filter, gain);
        });

        return Math.round(4.4 * secPerBeat * 1000);
    }
}
