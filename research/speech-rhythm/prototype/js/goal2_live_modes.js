/**
 * ============================================================================
 * Speech Rhythm Interactive Suite — Goal 2: Live Guided Performance Modes
 * File: app/goal2_live_modes.js
 *
 * Defines `window.Goal2LiveTrainer` providing the 2 winning real-time guided
 * performance ("Rap Flow Game for Speech") visualizations during the 2-Bar
 * Call-and-Response entrainment loop:
 *   - Bar 1: Native Model "Call"     (Beats 0.0 – 4.0)
 *   - Bar 2: Live "Response"         (Beats 0.0 – 4.0)
 *
 * Display Modes (Focused 100% on the 2 Winning Visual Paradigms):
 *   1. 'flow_matrix' : Prosodic Flow Matrix (16-Slot Grid, Stress-Foot Pillars,
 *                      Thought-Group Pause Gates `||`, Anacrusis Ghost-Bead Launch
 *                      Ramps, Hatched Pre-Beat Consonant Lead-In `str-`/`pr-` + ♦
 *                      P-Center Bullseye, Variable-Gravity Parabolic Bouncing Ball,
 *                      and Bar 2 Live Performer Ghost Trail)
 *   2. 'osu_taiko'   : Taiko + Osu! Prosodic Conveyor (Single-Line F0 Pitch Track,
 *                      Big 1.7× Stressed Circles vs. Small Hollow Ghost Beads,
 *                      Radially Shrinking P-Center Approach Rings, Osu! Vowel Hold
 *                      Slider Tails with Rolling Follow-Ball, Pause Gates `||`,
 *                      and Bar 2 Live Fill & Ghost Trail Feedback)
 *
 * Zero-Microphone Evaluation Suite:
 *   Includes a built-in Bar 2 Live Virtual Speaker Simulator ("Bot Performer")
 *   + Hold-Spacebar Duration Tapper so users on machines without a microphone
 *   can experience, hear, and evaluate the full real-time Goal 2 model:
 *     - 'bot_native'    : 🤖 Simulate: Native Fluent Speaker
 *     - 'bot_dysfluent' : 🤖 Simulate: Dysfluent Speaker (Hesitation Block & Prolongation)
 *     - 'bot_choppy'    : 🤖 Simulate: L2 Choppy / Syllable-Timed Speaker
 *     - 'manual_space'  : ⌨️ Manual: Keyboard Hold-to-Speak (Hold Spacebar for Duration)
 * ============================================================================
 */
(function (global) {
  'use strict';

  // --------------------------------------------------------------------------
  // 1. Winning Display Modes Catalog (Focused 100% on Flow Matrix & Osu! Taiko)
  // --------------------------------------------------------------------------
  const LIVE_MODES = {
    flow_matrix: {
      id: 'flow_matrix',
      shortLabel: '1. Prosodic Flow Matrix (Rap Grid + Arcs)',
      title: 'Stationary 16-Slot Prosodic Flow Matrix + Kinematic Bouncing Ball + P-Center Runways',
      badge: 'Rap Flow Matrix',
      description:
        'Stationary 4-Beat / 16-subdivision (1 e & a) matrix prevents eye-tracking saccade strain. Shows Stress-Foot Pillars, Thought-Group Pause Gates (||), Anacrusis Ghost-Bead Launch Ramps, Hatched Pre-Beat Consonant Runways (str-, pr-, pl-) left of the ♦ P-Center Bullseye, a Variable-Gravity Bouncing Ball, and a Bar 2 Live Performer Ghost Trail.'
    },
    osu_taiko: {
      id: 'osu_taiko',
      shortLabel: '2. Taiko + Osu! Prosodic Conveyor',
      title: 'Taiko + Osu! Single-Line Prosodic Conveyor (Shrinking Approach Rings + Vowel Hold Sliders)',
      badge: 'Taiko + Osu! Conveyor',
      description:
        'Single-line conveyor with Big Stressed Circles (1.7× Dai-Don with halo) vs. Small Hollow Ghost Beads positioned along the F0 pitch contour. Radially shrinking Osu! approach rings converge at the exact ♦ P-center moment while vowel hold slider tails guide sustained vowel duration with a rolling follow-ball and live Bar 2 fill feedback.'
    }
  };

  // Alias legacy mode keys safely to 'flow_matrix' so external callers never break
  const MODE_FALLBACK_MAP = {
    flow_matrix: 'flow_matrix',
    matrix: 'flow_matrix',
    osu_taiko: 'osu_taiko',
    taiko: 'osu_taiko',
    osu: 'osu_taiko',
    adofai_wheel: 'flow_matrix',
    kinetic_typo: 'flow_matrix'
  };

  // --------------------------------------------------------------------------
  // 2. The 4 Speech Vibes (Prosodic Context & Visual/Kinematic Adaptation)
  // --------------------------------------------------------------------------
  const SPEECH_VIBES = {
    prepared_speech: {
      id: 'prepared_speech',
      shortLabel: '🎙️ Prepared Speech',
      name: 'Prepared Speech / Keynote Delivery',
      accentColor: '#38bdf8',
      badgeBg: 'rgba(56, 189, 248, 0.16)',
      gravityScale: 1.05,
      pauseGateLabel: '|| THOUGHT-GROUP PAUSE GATE',
      rhythmRule:
        'Clear Stress-Foot Pillars + deliberate Thought-Group Pause Gates (||) + full phrase-final vowel lengthening before pauses.'
    },
    spontaneous_discussion: {
      id: 'spontaneous_discussion',
      shortLabel: '💬 Spontaneous Discussion',
      name: 'Spontaneous Conversational Discussion',
      accentColor: '#34d399',
      badgeBg: 'rgba(52, 211, 153, 0.16)',
      gravityScale: 0.92,
      pauseGateLabel: '|| TURN-HOLD BREATH',
      rhythmRule:
        'Rapid function-word schwa compression ("I was", "do you" → /dʒə/) on steep Anacrusis Ramps launching into conversational stress anchors.'
    },
    heated_argument: {
      id: 'heated_argument',
      shortLabel: '🔥 Heated Argument',
      name: 'Heated Argument / Emphatic Debate',
      accentColor: '#fb7185',
      badgeBg: 'rgba(251, 113, 133, 0.16)',
      gravityScale: 1.22,
      pauseGateLabel: '|| EMPHATIC CAESURA',
      rhythmRule:
        'High-velocity punchy stress anchors, aggressive pre-beat consonant lead-ins (str-, pl-, ch-), and sharp syncopated counter-beats.'
    },
    expressive_storytelling: {
      id: 'expressive_storytelling',
      shortLabel: '🎭 Expressive Storytelling',
      name: 'Expressive Narrative & Poetic Storytelling',
      accentColor: '#c084fc',
      badgeBg: 'rgba(192, 132, 252, 0.16)',
      gravityScale: 1.12,
      pauseGateLabel: '|| NARRATIVE SUSPENSE GATE',
      rhythmRule:
        'Wide F0 pitch contours, rolling trochaic/dactylic foot waves, and elastic vowel hold sliders on imagery-rich content words.'
    }
  };

  const VIBE_KEYS = Object.keys(SPEECH_VIBES);

  // --------------------------------------------------------------------------
  // 3. Bar 2 Live Performer Modes (Zero-Mic Virtual Speakers + Spacebar Hold)
  // --------------------------------------------------------------------------
  const LIVE_PERFORMERS = {
    bot_native: {
      id: 'bot_native',
      shortLabel: '🤖 Native Fluent Speaker',
      fullLabel: '🤖 Simulate: Native Fluent Speaker',
      badgeColor: '#10b981',
      goal1ProfileHint: 'native_like',
      description:
        'Automatically voices Bar 2 with native micro-timing: initiates pre-beat consonants (str-, pl-) early so the ♦ vowel P-center locks onto the beat, compresses schwa ghost beads tightly, and holds vowel sliders to full length.'
    },
    bot_dysfluent: {
      id: 'bot_dysfluent',
      shortLabel: '🤖 Dysfluent (Block & Prolong)',
      fullLabel: '🤖 Simulate: Dysfluent Speaker (Hesitation Block & Prolongation)',
      badgeColor: '#f59e0b',
      goal1ProfileHint: 'live_recorded',
      description:
        'Simulates a speaker who prolongs a function word ("theeee..."), freezes in a silent articulatory hesitation block before a heavy stressed word, and rushes to catch up—demonstrating calm, stutter-free visual biofeedback with zero red error flashes while logging the exact trajectory for Goal 1.'
    },
    bot_choppy: {
      id: 'bot_choppy',
      shortLabel: '🤖 L2 Choppy / Syllable-Timed',
      fullLabel: '🤖 Simulate: L2 Choppy / Syllable-Timed Speaker',
      badgeColor: '#f43f5e',
      goal1ProfileHint: 'syllable_timed',
      description:
        'Simulates a machine-gun syllable-timed speaker who hammers every small schwa ghost bead like a heavy stressed block (1.85× bloat), starts consonant clusters late ON the beat (+0.18b P-center lag), and clips phrase-final vowels.'
    },
    manual_space: {
      id: 'manual_space',
      shortLabel: '⌨️ Hold Spacebar to Speak',
      fullLabel: '⌨️ Manual: Keyboard Hold-to-Speak (Spacebar)',
      badgeColor: '#38bdf8',
      goal1ProfileHint: 'live_recorded',
      description:
        'Hold down Spacebar (or hold the button below) to voice the active syllable for as long as you hold the key—testing both P-center onset timing and vowel hold duration with zero microphone required!'
    }
  };

  // Rhyme group color palette for prosodic accent badges
  const RHYME_PALETTE = {
    A: { fill: 'rgba(244, 63, 94, 0.22)', stroke: '#fb7185', text: '#fda4af', glow: '#f43f5e' },
    B: { fill: 'rgba(168, 85, 247, 0.22)', stroke: '#c084fc', text: '#d8b4fe', glow: '#a855f7' },
    C: { fill: 'rgba(245, 158, 11, 0.22)', stroke: '#fbbf24', text: '#fde68a', glow: '#f59e0b' },
    D: { fill: 'rgba(14, 165, 233, 0.22)', stroke: '#38bdf8', text: '#bae6fd', glow: '#0ea5e9' },
    NONE: { fill: 'rgba(99, 102, 241, 0.20)', stroke: '#818cf8', text: '#c7d2fe', glow: '#6366f1' }
  };

  // Fallback phrase if SpeechRhythmCore hasn't loaded a phrase yet
  const FALLBACK_PHRASE = {
    id: 0,
    title: 'I was WALK-ing to the STR-EET... to WAIT',
    vibe: 'prepared_speech',
    bpm: 88,
    beatsPerBar: 4,
    feet: [
      { footId: 0, label: 'Anacrusis Pickup', startBeat: 0.0, endBeat: 0.65 },
      { footId: 1, label: 'Foot 1: WALK-ing to the', startBeat: 0.65, endBeat: 2.0 },
      { footId: 2, label: 'Foot 2: STR-EET... ||', startBeat: 2.0, endBeat: 3.35 },
      { footId: 3, label: 'Foot 3: to WAIT', startBeat: 3.35, endBeat: 4.0 }
    ],
    syllables: [
      { id: 0, text: 'I', pre: '', preDur: 0.0, vowel: 'I', beat: 0.22, dur: 0.14, stress: 0.22, pitchST: -1.5, isGhost: true, footId: 0, rhyme: null },
      { id: 1, text: 'was', pre: 'w', preDur: 0.04, vowel: 'as', beat: 0.42, dur: 0.13, stress: 0.16, pitchST: -2.0, isGhost: true, footId: 0, rhyme: null },
      { id: 2, text: 'WALK-', pre: 'w', preDur: 0.06, vowel: 'ALK', beat: 0.68, dur: 0.36, stress: 0.88, pitchST: 3.0, isGhost: false, footId: 1, rhyme: 'A', leadInMs: 45 },
      { id: 3, text: 'ing', pre: '', preDur: 0.0, vowel: 'ing', beat: 1.12, dur: 0.16, stress: 0.28, pitchST: 1.0, isGhost: true, footId: 1, rhyme: null },
      { id: 4, text: 'to', pre: 't', preDur: 0.04, vowel: 'o', beat: 1.44, dur: 0.12, stress: 0.15, pitchST: -1.5, isGhost: true, footId: 1, rhyme: null },
      { id: 5, text: 'the', pre: 'th', preDur: 0.04, vowel: 'e', beat: 1.64, dur: 0.12, stress: 0.15, pitchST: -2.0, isGhost: true, footId: 1, rhyme: null },
      { id: 6, text: 'STR-EET...', pre: 'str', preDur: 0.14, vowel: 'EET', beat: 2.00, dur: 0.62, stress: 1.00, pitchST: 4.5, isGhost: false, isFinal: true, footId: 2, rhyme: 'B', leadInMs: 95 },
      { id: 7, text: 'to', pre: 't', preDur: 0.04, vowel: 'o', beat: 3.16, dur: 0.13, stress: 0.18, pitchST: -2.0, isGhost: true, footId: 2, rhyme: null },
      { id: 8, text: 'WAIT', pre: 'w', preDur: 0.06, vowel: 'AIT', beat: 3.45, dur: 0.48, stress: 0.94, pitchST: 2.5, isGhost: false, isFinal: true, footId: 3, rhyme: 'C', leadInMs: 45 }
    ]
  };

  // --------------------------------------------------------------------------
  // 4. Phrase & Speech Vibe Normalization + Bot Trajectory Generator
  // --------------------------------------------------------------------------
  function inferSpeechVibeKey(src, explicitVibe) {
    if (explicitVibe && SPEECH_VIBES[explicitVibe]) return explicitVibe;
    const rawVibe = src && (src.vibe || src.vibeId || src.vibeKey || src.speechVibe || '');
    if (rawVibe && SPEECH_VIBES[rawVibe]) return rawVibe;

    const cat = String((src && (src.category || src.subtitle || src.title)) || '').toLowerCase();
    if (/prepared|ted|keynote|lecture|formal|wait/i.test(cat) && src && src.id === 0) return 'prepared_speech';
    if (/spontaneous|discussion|question|conversational|plan/i.test(cat)) return 'spontaneous_discussion';
    if (/argument|heated|debate|rap|bounce|emphatic/i.test(cat)) return 'heated_argument';
    if (/story|narrative|poetic|stream|expressive/i.test(cat)) return 'expressive_storytelling';

    const idx = typeof (src && src.id) === 'number' ? src.id : 0;
    return VIBE_KEYS[Math.abs(idx) % VIBE_KEYS.length] || 'prepared_speech';
  }

  function normalizePhrase(rawPhrase, explicitVibe) {
    const core = global.SpeechRhythmCore;
    const src =
      rawPhrase ||
      (core && typeof core.getCurrentPhrase === 'function' && core.getCurrentPhrase()) ||
      (core && core.currentPhrase) ||
      (core && Array.isArray(core.PHRASES) && core.PHRASES[core.currentPhraseIndex || 0]) ||
      FALLBACK_PHRASE;

    const vibeKey = inferSpeechVibeKey(src, explicitVibe);
    const vibeMeta = SPEECH_VIBES[vibeKey] || SPEECH_VIBES.prepared_speech;

    const rawSyls = src.syllables || src.tokens || src.items || FALLBACK_PHRASE.syllables;
    let maxBeatEnd = 4.0;
    rawSyls.forEach((s) => {
      const b = typeof s.beat === 'number' ? s.beat : typeof s.targetBeat === 'number' ? s.targetBeat : 0;
      const d = typeof s.dur === 'number' ? s.dur : typeof s.duration === 'number' ? s.duration : 0.25;
      if (b + d > maxBeatEnd) maxBeatEnd = b + d;
    });
    const scaleTo4 = maxBeatEnd > 4.25 ? 3.85 / maxBeatEnd : 1.0;
    const bpm = src.defaultBpm || src.bpm || 88;

    const normalized = rawSyls.map((s, idx) => {
      const rawBeat =
        typeof s.beat === 'number'
          ? s.beat
          : typeof s.targetBeat === 'number'
          ? s.targetBeat
          : typeof s.onsetBeat === 'number'
          ? s.onsetBeat
          : idx * 0.4;
      const rawDur =
        typeof s.dur === 'number'
          ? s.dur
          : typeof s.duration === 'number'
          ? s.duration
          : typeof s.durBeats === 'number'
          ? s.durBeats
          : 0.25;

      const beat = +(rawBeat * scaleTo4).toFixed(3);
      const dur = +Math.max(0.10, rawDur * scaleTo4).toFixed(3);
      const stress =
        typeof s.stress === 'number'
          ? s.stress
          : typeof s.weight === 'number'
          ? s.weight
          : s.isGhost
          ? 0.22
          : 0.9;
      const isGhost = typeof s.isGhost === 'boolean' ? s.isGhost : stress < 0.48;

      const text = String(s.text || s.label || s.word || '');
      let pre = s.pre !== undefined ? s.pre : s.consonantPre || s.onsetConsonant || '';
      let vowel = s.vowel !== undefined ? s.vowel : s.nucleus || s.rime || '';
      if (!vowel && text) {
        const clean = text.replace(/[-.?!]/g, '');
        const match = clean.match(/^([^aeiouyAEIOUY]+)(.*)$/);
        if (match && match[2]) {
          if (!pre) pre = match[1].toLowerCase();
          vowel = match[2];
        } else {
          vowel = clean;
        }
      }

      const pitchST =
        typeof s.pitchST === 'number'
          ? s.pitchST
          : typeof s.pitch === 'number'
          ? s.pitch
          : isGhost
          ? -1.8 + (idx % 2) * 0.5
          : 3.0 + (stress - 0.5) * 4.0;

      const preDur =
        typeof s.preDur === 'number' && s.preDur > 0
          ? +(s.preDur * scaleTo4).toFixed(3)
          : pre
          ? +Math.min(0.16, 0.035 + pre.length * 0.032).toFixed(3)
          : 0;

      const leadInMs =
        typeof s.leadInMs === 'number'
          ? s.leadInMs
          : preDur > 0
          ? Math.round(preDur * (60 / bpm) * 1000)
          : 0;

      const rhymeMap = ['NONE', 'A', 'B', 'C', 'D'];
      let rhyme = null;
      if (typeof s.rhyme === 'string') {
        rhyme = s.rhyme;
      } else if (typeof s.rhymeGroup === 'number' && s.rhymeGroup > 0) {
        rhyme = rhymeMap[s.rhymeGroup] || 'A';
      } else if (!isGhost) {
        rhyme = idx % 3 === 0 ? 'A' : 'B';
      }

      return {
        id: s.id !== undefined ? s.id : idx,
        index: idx,
        text,
        pre,
        preDur,
        vowel: vowel || text,
        ipa: s.ipa || '',
        beat,
        rawBeat,
        dur,
        stress,
        isGhost,
        isFinal: Boolean(s.isFinal || idx === rawSyls.length - 1),
        footId: typeof s.footId === 'number' ? s.footId : Math.floor(beat),
        pitchST,
        pitchSlope: typeof s.pitchSlope === 'number' ? s.pitchSlope : 0,
        leadInMs,
        rhyme,
        tip: s.tip || ''
      };
    });

    // Compute Anacrusis Ghost-Bead Launch Ramp progress for consecutive ghost syllables
    let runIndices = [];
    for (let i = 0; i < normalized.length; i++) {
      if (normalized[i].isGhost) {
        runIndices.push(i);
      } else {
        const total = runIndices.length;
        runIndices.forEach((gIdx, k) => {
          normalized[gIdx].rampStep = k;
          normalized[gIdx].rampTotal = total;
          normalized[gIdx].rampProgress = total > 1 ? (k + 1) / (total + 1) : 0.55;
          normalized[gIdx].targetAnchorBeat = normalized[i].beat;
        });
        runIndices = [];
        normalized[i].rampStep = 0;
        normalized[i].rampTotal = 0;
        normalized[i].rampProgress = 1.0;
      }
    }
    if (runIndices.length) {
      const total = runIndices.length;
      runIndices.forEach((gIdx, k) => {
        normalized[gIdx].rampStep = k;
        normalized[gIdx].rampTotal = total;
        normalized[gIdx].rampProgress = (k + 1) / (total + 1);
      });
    }

    // Derive Stress-Foot Pillars (`feet`) & Thought-Group Pause Gates (`pauseGates`)
    const feet = Array.isArray(src.feet) && src.feet.length
      ? src.feet.map((f, fIdx) => ({
          footId: f.footId !== undefined ? f.footId : fIdx,
          label: f.label || `Foot ${fIdx + 1}`,
          startBeat: +(f.startBeat * scaleTo4).toFixed(3),
          endBeat: +(f.endBeat * scaleTo4).toFixed(3)
        }))
      : [
          { footId: 0, label: 'Foot 1', startBeat: 0.0, endBeat: 1.0 },
          { footId: 1, label: 'Foot 2', startBeat: 1.0, endBeat: 2.0 },
          { footId: 2, label: 'Foot 3', startBeat: 2.0, endBeat: 3.0 },
          { footId: 3, label: 'Foot 4', startBeat: 3.0, endBeat: 4.0 }
        ];

    const pauseGates = [];
    for (let i = 0; i < normalized.length - 1; i++) {
      const cur = normalized[i];
      const nxt = normalized[i + 1];
      const curEnd = cur.beat + cur.dur;
      const nextStart = nxt.beat - (nxt.preDur || 0);
      const gap = nextStart - curEnd;
      if ((cur.isFinal && i < normalized.length - 1) || gap >= 0.24) {
        pauseGates.push({
          afterIndex: i,
          startBeat: +curEnd.toFixed(3),
          endBeat: +Math.max(curEnd + 0.14, nextStart).toFixed(3),
          midBeat: +((curEnd + Math.max(curEnd + 0.14, nextStart)) / 2).toFixed(3),
          label: vibeMeta.pauseGateLabel
        });
      }
    }
    // Always include a subtle phrase-end boundary gate near Beat 3.92 if none mid-phrase
    if (pauseGates.length === 0 && normalized.length > 0) {
      const last = normalized[normalized.length - 1];
      const endB = Math.min(3.82, last.beat + last.dur);
      pauseGates.push({
        afterIndex: normalized.length - 1,
        startBeat: +endB.toFixed(3),
        endBeat: 3.98,
        midBeat: +((endB + 3.98) / 2).toFixed(3),
        label: '|| PHRASE BOUNDARY GATE'
      });
    }

    return {
      id: typeof src.id === 'number' ? src.id : 0,
      title: src.title || src.text || FALLBACK_PHRASE.title,
      subtitle: src.subtitle || vibeMeta.name,
      category: src.category || vibeMeta.name,
      vibeKey,
      vibeMeta,
      bpm,
      beatsPerBar: 4,
      scaleTo4,
      feet,
      pauseGates,
      syllables: normalized
    };
  }

  /**
   * Build the Bar 2 Virtual Speaker ("Bot Performer") syllable trajectory for a phrase.
   * Used both to drive real-time Bar 2 audio + visuals AND to log into Goal 1 (`SpeechRhythmCore.recordLiveSyllables`).
   */
  function generateBotTrajectory(phrase, performerId) {
    const syls = phrase.syllables;

    if (performerId === 'bot_native') {
      return syls.map((s, idx) => {
        const microJitter = ((idx % 3) - 1) * 0.008;
        const perfBeat = +Math.max(0.02, s.beat + microJitter).toFixed(3);
        const perfDur = +Math.max(0.09, s.dur * (1 + microJitter * 0.5)).toFixed(3);
        return {
          index: idx,
          id: s.id,
          text: s.text,
          pre: s.pre,
          preDur: s.preDur,
          vowel: s.vowel,
          targetBeat: s.beat,
          targetDur: s.dur,
          perfBeat,
          perfPreStart: +Math.max(0, perfBeat - s.preDur).toFixed(3),
          perfDur,
          perfStress: s.stress,
          perfPitchST: s.pitchST,
          perfPitchSlope: s.pitchSlope,
          isGhost: s.isGhost,
          isFinal: s.isFinal,
          kind: 'fluent',
          tag: s.preDur >= 0.08
            ? `✓ Pre-beat /${s.pre}/ lead-in (-${s.leadInMs}ms)`
            : s.isGhost
            ? '✓ Compressed schwa ramp'
            : '✓ P-Center locked in pocket'
        };
      });
    }

    if (performerId === 'bot_dysfluent') {
      // Identify the main cluster/stressed anchor (e.g. "STR-EET...", "PLA-N?", "BOUNCE", "FLOW-"/"STREAM")
      // and the ghost function word immediately preceding it (e.g. "the", "to")
      let blockIdx = syls.findIndex((s, i) => i >= 2 && !s.isGhost && (s.preDur >= 0.08 || s.stress >= 0.9));
      if (blockIdx < 1) blockIdx = Math.min(syls.length - 1, 2);
      const prolongIdx = Math.max(0, blockIdx - 1);

      return syls.map((s, idx) => {
        if (idx === prolongIdx) {
          // Prolongation on function word ("theeee..." / "toooo...")
          const prolongedDur = +Math.min(0.42, Math.max(0.28, s.dur * 2.45)).toFixed(3);
          const cleanText = s.text.replace(/-/g, '');
          const prolongedLabel = cleanText + cleanText.slice(-1).repeat(3) + '…';
          return {
            index: idx,
            id: s.id,
            text: s.text,
            displayLabel: prolongedLabel,
            pre: s.pre,
            preDur: s.preDur,
            vowel: s.vowel,
            targetBeat: s.beat,
            targetDur: s.dur,
            perfBeat: +s.beat.toFixed(3),
            perfPreStart: +Math.max(0, s.beat - s.preDur).toFixed(3),
            perfDur: prolongedDur,
            perfStress: Math.min(0.65, s.stress + 0.30),
            perfPitchST: s.pitchST - 0.5,
            perfPitchSlope: 0,
            isGhost: s.isGhost,
            isFinal: s.isFinal,
            kind: 'prolongation',
            tag: `⏳ Prolonged "${prolongedLabel}" (${(prolongedDur / s.dur).toFixed(1)}× hold)`
          };
        }

        if (idx === blockIdx) {
          // Silent Hesitation Block before heavy consonant cluster / stressed word (+0.26b freeze)
          const blockDelay = 0.26;
          const perfBeat = +Math.min(3.85, s.beat + blockDelay).toFixed(3);
          const blockZoneStart = s.beat - (s.preDur || 0.06);
          const blockZoneEnd = perfBeat - (s.preDur || 0.06);
          return {
            index: idx,
            id: s.id,
            text: s.text,
            pre: s.pre,
            preDur: s.preDur,
            vowel: s.vowel,
            targetBeat: s.beat,
            targetDur: s.dur,
            perfBeat,
            perfPreStart: +Math.max(0, perfBeat - s.preDur).toFixed(3),
            perfDur: +Math.max(0.18, s.dur * 0.78).toFixed(3),
            perfStress: Math.min(1.0, s.stress + 0.08),
            perfPitchST: s.pitchST + 0.8,
            perfPitchSlope: s.pitchSlope,
            isGhost: s.isGhost,
            isFinal: s.isFinal,
            kind: 'hesitation_block',
            blockZoneStart: +Math.max(0, blockZoneStart).toFixed(3),
            blockZoneEnd: +Math.max(blockZoneStart + 0.14, blockZoneEnd).toFixed(3),
            tag: `⏸ Hesitation Block (+${blockDelay.toFixed(2)}b freeze before "${s.text.replace(/[-.]/g, '')}")`
          };
        }

        if (idx > blockIdx) {
          // Post-block rush to catch up
          const rushShift = idx === blockIdx + 1 ? 0.12 : -0.08;
          const perfBeat = +Math.min(3.88, Math.max(0.1, s.beat + rushShift)).toFixed(3);
          return {
            index: idx,
            id: s.id,
            text: s.text,
            pre: s.pre,
            preDur: s.preDur,
            vowel: s.vowel,
            targetBeat: s.beat,
            targetDur: s.dur,
            perfBeat,
            perfPreStart: +Math.max(0, perfBeat - s.preDur).toFixed(3),
            perfDur: +Math.max(0.10, s.dur * 0.74).toFixed(3),
            perfStress: s.stress,
            perfPitchST: s.pitchST,
            perfPitchSlope: s.pitchSlope * 0.6,
            isGhost: s.isGhost,
            isFinal: s.isFinal,
            kind: 'post_block_rush',
            tag: '⏩ Post-block catch-up rush'
          };
        }

        // Earlier syllables before prolongation
        return {
          index: idx,
          id: s.id,
          text: s.text,
          pre: s.pre,
          preDur: s.preDur,
          vowel: s.vowel,
          targetBeat: s.beat,
          targetDur: s.dur,
          perfBeat: +s.beat.toFixed(3),
          perfPreStart: +Math.max(0, s.beat - s.preDur).toFixed(3),
          perfDur: +s.dur.toFixed(3),
          perfStress: s.stress,
          perfPitchST: s.pitchST,
          perfPitchSlope: s.pitchSlope,
          isGhost: s.isGhost,
          isFinal: s.isFinal,
          kind: 'fluent',
          tag: '✓ Smooth pickup'
        };
      });
    }

    // Default / 'bot_choppy': L2 Choppy / Syllable-Timed Speaker
    return syls.map((s, idx) => {
      const isCluster = (s.pre && s.pre.length >= 2) || s.preDur >= 0.08;
      // Starts consonant cluster ON the beat instead of pre-beat -> P-center lags by +0.18b
      const clusterLag = isCluster ? 0.18 : s.preDur > 0.03 ? 0.06 : 0.02;
      const earlyGhosts = syls.slice(0, idx).filter((g) => g.isGhost).length;
      const ghostDrift = earlyGhosts * 0.028;
      const perfBeat = +Math.min(3.88, s.beat + clusterLag + ghostDrift).toFixed(3);
      const perfDur = s.isGhost
        ? +Math.min(0.32, s.dur * 1.85).toFixed(3) // Hammers every small ghost bead
        : s.isFinal
        ? +Math.max(0.16, s.dur * 0.68).toFixed(3) // Clips final vowel
        : +Math.max(0.16, s.dur * 0.86).toFixed(3);

      return {
        index: idx,
        id: s.id,
        text: s.text,
        pre: s.pre,
        preDur: s.preDur,
        vowel: s.vowel,
        targetBeat: s.beat,
        targetDur: s.dur,
        perfBeat,
        // Notice: Choppy speaker starts the consonant ON `s.beat` instead of `s.beat - preDur`!
        perfPreStart: +Math.max(0, perfBeat - s.preDur).toFixed(3),
        perfDur,
        perfStress: s.isGhost ? 0.68 : 0.76,
        perfPitchST: s.isGhost ? 0.0 : +(s.pitchST * 0.45).toFixed(2),
        perfPitchSlope: 0,
        isGhost: s.isGhost,
        isFinal: s.isFinal,
        kind: isCluster ? 'cluster_lag' : s.isGhost ? 'bloated_ghost' : 'clipped_stress',
        tag: isCluster
          ? `⚠️ Late /${s.pre}/ cluster (+${clusterLag.toFixed(2)}b P-center lag)`
          : s.isGhost
          ? '⚠️ Over-stressed schwa bead (1.85× bloat)'
          : '⚠️ Clipped vowel hold'
      };
    });
  }

  // --------------------------------------------------------------------------
  // 5. Goal2LiveTrainer Controller & Renderer
  // --------------------------------------------------------------------------
  const Goal2LiveTrainer = {
    MODES: LIVE_MODES,
    modes: Object.values(LIVE_MODES),
    SPEECH_VIBES,
    PERFORMERS: LIVE_PERFORMERS,
    currentMode: 'flow_matrix',
    currentPerformer: 'bot_native', // Default to Native Bot so user can immediately experience Bar 2 without a mic!
    explicitVibe: null,
    containerEl: null,
    svgEl: null,

    // Playback & Loop State
    isPlaying: false,
    bpm: 88,
    animFrame: null,
    startTime: 0,
    lastHalfStep: -1,
    lastSpokenSylKey: '',
    lastBotSpokenSylKey: '',
    currentBeat: 0.0,
    isResponseBar: false,
    barIndex: 0, // 0 = Bar 1 (Native Call), 1 = Bar 2 (Live Response)
    voiceEnergy: 0,

    // Live Biofeedback & Hold-Spacebar State
    userRipples: [],
    capsuleGlows: {}, // { [sylIndex]: { time, beat, dur, offsetMs, energy, tag, kind } }
    recordedHits: [],
    phraseHitSlots: {},
    manualTrails: {}, // { [sylIndex]: { perfBeat, perfDur, perfPreStart, perfStress, tag, active } }
    activeHold: null, // { sylIndex, startBeat, startTimeMs, oscNodes }

    /**
     * Initialize or mount the Goal 2 Live Trainer inside a container element or SVG.
     */
    init(containerOrId, options = {}) {
      const target =
        typeof containerOrId === 'string'
          ? document.getElementById(containerOrId) || document.querySelector(containerOrId)
          : containerOrId;

      if (options.mode) {
        this.currentMode = MODE_FALLBACK_MAP[options.mode] || 'flow_matrix';
      }
      if (options.performer && LIVE_PERFORMERS[options.performer]) {
        this.currentPerformer = options.performer;
      }
      if (options.vibe && SPEECH_VIBES[options.vibe]) {
        this.explicitVibe = options.vibe;
      }
      if (options.phrase) {
        this.phrase = options.phrase;
      }
      if (options.bpm) {
        this.bpm = Number(options.bpm) || 88;
      }

      if (target) {
        if (target.tagName && target.tagName.toLowerCase() === 'svg') {
          this.svgEl = target;
          this.containerEl = target.parentElement;
        } else {
          this.containerEl = target;
          this._buildStageDOM(target, options);
        }
      }

      this._bindKeyboardOnce();
      this.renderFrame(this.currentBeat, this.isResponseBar);
      return this;
    },

    mount(containerOrId, options = {}) {
      return this.init(containerOrId, options);
    },

    /**
     * Set active prosodic phrase and refresh
     */
    setPhrase(phraseObj) {
      this.phrase = phraseObj;
      this.explicitVibe = null; // Follow phrase's native Speech Vibe unless overridden
      this.userRipples = [];
      this.capsuleGlows = {};
      this.manualTrails = {};
      if (this.phrase && this.phrase.defaultBpm) {
        this.bpm = this.phrase.defaultBpm;
      }
      this._syncVibeUI();
      // Pre-populate Goal 1 live telemetry for the active bot performer so switching to Goal 1 works immediately
      if (this.currentPerformer !== 'manual_space') {
        this._syncBotTelemetryToCore(normalizePhrase(this.phrase, this.explicitVibe), this.currentPerformer);
      }
      this.renderFrame(this.currentBeat, this.isResponseBar);
      return this;
    },

    /**
     * Set Speech Vibe explicitly ('prepared_speech' | 'spontaneous_discussion' | 'heated_argument' | 'expressive_storytelling')
     */
    setVibe(vibeId) {
      if (!SPEECH_VIBES[vibeId]) return this;
      this.explicitVibe = vibeId;
      this._syncVibeUI();
      this.renderFrame(this.currentBeat, this.isResponseBar);
      return this;
    },

    /**
     * Set Bar 2 Live Performer ('bot_native' | 'bot_dysfluent' | 'bot_choppy' | 'manual_space')
     */
    setPerformer(performerId) {
      if (!LIVE_PERFORMERS[performerId]) return this;
      this.currentPerformer = performerId;
      this.capsuleGlows = {};
      this.userRipples = [];

      const phrase = normalizePhrase(this.phrase, this.explicitVibe);
      if (performerId !== 'manual_space') {
        this._syncBotTelemetryToCore(phrase, performerId);
      }

      if (this.containerEl) {
        this.containerEl.querySelectorAll('[data-goal2-perf-btn]').forEach((btn) => {
          const p = btn.getAttribute('data-goal2-perf-btn');
          const active = p === performerId;
          btn.className = active
            ? 'px-2.5 py-1.5 rounded-lg text-xs font-bold transition-all border bg-emerald-600 text-white border-emerald-400 shadow-sm'
            : 'px-2.5 py-1.5 rounded-lg text-xs font-semibold transition-all border bg-slate-900/80 text-slate-300 border-slate-700/80 hover:border-slate-500 hover:text-white';
        });
        const perfDesc = this.containerEl.querySelector('[data-goal2-perf-desc]');
        if (perfDesc) {
          perfDesc.textContent = LIVE_PERFORMERS[performerId].description;
        }
        const badge = this.containerEl.querySelector('[data-goal2-telemetry-badge]');
        if (badge) {
          badge.textContent =
            performerId === 'manual_space'
              ? '⌨️ Hold Spacebar during Bar 2 to voice & sustain syllables'
              : `🤖 Bar 2 Auto-Sim Ready: ${LIVE_PERFORMERS[performerId].shortLabel} (logged to Goal 1)`;
        }
      }

      // Render Bar 2 preview immediately if not currently playing so the user can see the Ghost Trail right away
      if (!this.isPlaying) {
        this.isResponseBar = true;
        this.renderFrame(this.currentBeat || 2.15, true, phrase);
      } else {
        this.renderFrame(this.currentBeat, this.isResponseBar, phrase);
      }
      return this;
    },

    getPerformer() {
      return this.currentPerformer;
    },

    /**
     * One-click helper to jump straight into Bar 2 (Live Response) and audition the selected Virtual Speaker or Spacebar Hold
     */
    auditionResponseBarNow() {
      const phrase = normalizePhrase(this.phrase, this.explicitVibe);
      const bpm = this._getEffectiveBpm(phrase);
      const beatDurMs = (60 / bpm) * 1000;

      if (!this.isPlaying) {
        this.startLoop();
      }
      // Shift startTime back by 4 beats so the 8-beat loop is immediately at Beat 0.0 of Bar 2!
      this.startTime = performance.now() - 4.0 * beatDurMs;
      this.lastBotSpokenSylKey = '';
      this.isResponseBar = true;
      this.currentBeat = 0.0;

      const core = global.SpeechRhythmCore;
      if (core && core.audioEngine && core.audioEngine.ctx && core.audioEngine.isPlaying) {
        const secPerBar = (60 / core.audioEngine.bpm) * 4.0;
        core.audioEngine._loopStartTime = core.audioEngine.ctx.currentTime - secPerBar;
      }
      return this;
    },

    /**
     * Build self-contained 2-Mode Switcher + Speech Vibe Bar + Bar 2 Virtual Speaker Toolbar + SVG Stage
     */
    _buildStageDOM(container, options = {}) {
      const existingSvg = container.querySelector('svg[data-goal2-stage]');
      if (existingSvg && container.querySelector('[data-goal2-mode-bar]')) {
        this.svgEl = existingSvg;
        return;
      }

      const showChrome = options.showChrome !== false && !container.hasAttribute('data-bare-stage');
      if (!showChrome) {
        container.innerHTML = `
          <svg data-goal2-stage="true" class="w-full h-full" viewBox="0 0 980 360" preserveAspectRatio="xMidYMid meet"></svg>
        `;
        this.svgEl = container.querySelector('svg[data-goal2-stage]');
        return;
      }

      const phrase = normalizePhrase(this.phrase, this.explicitVibe);

      const modeButtonsHtml = Object.values(LIVE_MODES)
        .map((m) => {
          const active = m.id === this.currentMode;
          return `
            <button
              type="button"
              data-goal2-mode-btn="${m.id}"
              class="px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all border ${
                active
                  ? 'bg-indigo-600 text-white border-indigo-400 shadow-sm'
                  : 'bg-slate-900/70 text-slate-300 border-slate-700/80 hover:border-slate-500 hover:text-white'
              }"
            >
              ${m.shortLabel}
            </button>
          `;
        })
        .join('');

      const vibeButtonsHtml = Object.values(SPEECH_VIBES)
        .map((v) => {
          const active = v.id === phrase.vibeKey;
          return `
            <button
              type="button"
              data-goal2-vibe-btn="${v.id}"
              class="px-2.5 py-1 rounded-md text-[11px] font-semibold transition-all border ${
                active
                  ? 'bg-sky-500/20 text-sky-200 border-sky-400/60 shadow-sm'
                  : 'bg-slate-900/60 text-slate-400 border-slate-800 hover:text-slate-200'
              }"
            >
              ${v.shortLabel}
            </button>
          `;
        })
        .join('');

      const performerButtonsHtml = Object.values(LIVE_PERFORMERS)
        .map((p) => {
          const active = p.id === this.currentPerformer;
          return `
            <button
              type="button"
              data-goal2-perf-btn="${p.id}"
              class="px-2.5 py-1.5 rounded-lg text-xs ${
                active
                  ? 'font-bold bg-emerald-600 text-white border-emerald-400 shadow-sm'
                  : 'font-semibold bg-slate-900/80 text-slate-300 border-slate-700/80 hover:border-slate-500 hover:text-white'
              } transition-all border"
            >
              ${p.shortLabel}
            </button>
          `;
        })
        .join('');

      container.innerHTML = `
        <div class="space-y-3 select-none">
          <!-- Compact Control Bar -->
          <div class="flex flex-wrap items-center justify-between gap-2 bg-slate-950/90 border border-slate-800 rounded-xl p-2.5">
            <div class="flex flex-wrap items-center gap-1.5">
              <span class="text-xs font-bold text-slate-300 mr-1">Bar 2 Performer:</span>
              <div class="flex flex-wrap items-center gap-1.5" data-goal2-performer-bar>
                ${performerButtonsHtml}
              </div>
            </div>

            <div class="flex flex-wrap items-center gap-2">
              <button
                type="button"
                data-goal2-audition-bar2-btn
                class="px-3 py-1.5 rounded-lg text-xs font-bold bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 border border-amber-500/40 transition"
              >
                ▶ Preview Bar 2
              </button>
              <button
                type="button"
                data-goal2-tap-btn
                class="px-3 py-1.5 rounded-lg text-xs font-bold bg-sky-500/20 hover:bg-sky-500/30 active:bg-emerald-500/40 text-sky-200 border border-sky-400/50 transition"
              >
                🎤 Hold Spacebar
              </button>
              <span data-goal2-phase-pill class="px-2.5 py-1 rounded-full text-xs font-semibold bg-cyan-500/15 text-cyan-300 border border-cyan-500/30">
                🔊 Bar 1: Reference Call
              </span>
            </div>
          </div>

          <!-- Primary SVG Stage (Prosodic Flow Matrix Winner) -->
          <div class="relative rounded-xl border border-slate-800 bg-slate-950/95 overflow-hidden shadow-inner" style="min-height: 360px;">
            <svg data-goal2-stage="true" class="w-full h-full block" viewBox="0 0 980 360" preserveAspectRatio="xMidYMid meet"></svg>
          </div>

          <!-- Collapsible Teacher Notes Dropdown -->
          <details class="bg-slate-900/75 border border-slate-800 rounded-xl px-3.5 py-2 text-xs text-slate-300">
            <summary class="cursor-pointer font-bold text-slate-200 select-none">
              Teacher Notes &amp; Performer Details
            </summary>
            <div class="mt-2 space-y-1.5 pt-2 border-t border-slate-800 text-slate-400">
              <p data-goal2-perf-desc>${LIVE_PERFORMERS[this.currentPerformer].description}</p>
              <p data-goal2-vibe-rule class="font-mono text-[11px] text-sky-300">
                ${phrase.vibeMeta.shortLabel}: ${phrase.vibeMeta.rhythmRule}
              </p>
              <p data-goal2-telemetry-badge class="font-mono text-[11px] text-emerald-400">
                ${LIVE_PERFORMERS[this.currentPerformer].shortLabel}
              </p>
            </div>
          </details>
        </div>
      `;

      this.svgEl = container.querySelector('svg[data-goal2-stage]');

      // Bind Mode buttons
      container.querySelectorAll('[data-goal2-mode-btn]').forEach((btn) => {
        btn.addEventListener('click', () => {
          const m = btn.getAttribute('data-goal2-mode-btn');
          this.setMode(m);
        });
      });

      // Bind Speech Vibe buttons
      container.querySelectorAll('[data-goal2-vibe-btn]').forEach((btn) => {
        btn.addEventListener('click', () => {
          const v = btn.getAttribute('data-goal2-vibe-btn');
          this.setVibe(v);
        });
      });

      // Bind Bar 2 Performer buttons
      container.querySelectorAll('[data-goal2-perf-btn]').forEach((btn) => {
        btn.addEventListener('click', () => {
          const p = btn.getAttribute('data-goal2-perf-btn');
          this.setPerformer(p);
        });
      });

      // Bind "Hear/Watch Bar 2 Bot Now" button
      const auditionBtn = container.querySelector('[data-goal2-audition-bar2-btn]');
      if (auditionBtn) {
        auditionBtn.addEventListener('click', () => {
          this.auditionResponseBarNow();
          // Sync main play button label in index.html if present
          const btnText = document.getElementById('loop-btn-text');
          const btnIcon = document.getElementById('loop-btn-icon');
          const mainBtn = document.getElementById('btn-play-loop');
          if (btnText && btnIcon && mainBtn) {
            btnText.textContent = 'Stop 2-Bar Groove Loop';
            btnIcon.textContent = '■';
            mainBtn.className =
              'px-3.5 py-1.5 rounded-lg text-xs font-bold bg-rose-600 hover:bg-rose-500 text-white shadow transition flex items-center gap-1.5';
          }
        });
      }

      // Bind Hold-to-Speak button (supports press-and-hold duration as well as click)
      const tapBtn = container.querySelector('[data-goal2-tap-btn]');
      if (tapBtn) {
        tapBtn.addEventListener('pointerdown', (e) => {
          e.preventDefault();
          this.startHoldTap();
        });
        tapBtn.addEventListener('pointerup', (e) => {
          e.preventDefault();
          this.endHoldTap();
        });
        tapBtn.addEventListener('pointerleave', () => {
          if (this.activeHold) this.endHoldTap();
        });
      }

      // Sync initial bot telemetry to SpeechRhythmCore
      this._syncBotTelemetryToCore(phrase, this.currentPerformer);
    },

    _syncVibeUI() {
      if (!this.containerEl) return;
      const phrase = normalizePhrase(this.phrase, this.explicitVibe);
      this.containerEl.querySelectorAll('[data-goal2-vibe-btn]').forEach((btn) => {
        const v = btn.getAttribute('data-goal2-vibe-btn');
        const active = v === phrase.vibeKey;
        btn.className = active
          ? 'px-2.5 py-1 rounded-md text-[11px] font-semibold transition-all border bg-sky-500/20 text-sky-200 border-sky-400/60 shadow-sm'
          : 'px-2.5 py-1 rounded-md text-[11px] font-semibold transition-all border bg-slate-900/60 text-slate-400 border-slate-800 hover:text-slate-200';
      });
      const ruleEl = this.containerEl.querySelector('[data-goal2-vibe-rule]');
      if (ruleEl) {
        ruleEl.textContent = `${phrase.vibeMeta.shortLabel}: ${phrase.vibeMeta.rhythmRule}`;
      }
    },

    /**
     * Bind Keyboard Spacebar Hold-to-Speak (`keydown` starts vowel hold, `keyup` ends vowel hold)
     */
    _bindKeyboardOnce() {
      if (this._kbBound || typeof global.addEventListener !== 'function') return;
      this._kbBound = true;

      global.addEventListener('keydown', (e) => {
        if (e.code === 'Space' && !e.repeat) {
          const activeTag = document.activeElement && document.activeElement.tagName;
          if (activeTag === 'INPUT' || activeTag === 'TEXTAREA' || activeTag === 'SELECT') return;
          const svg = this._resolveSvg();
          if (svg && svg.offsetParent !== null) {
            e.preventDefault();
            this.startHoldTap();
          }
        }
      });

      global.addEventListener('keyup', (e) => {
        if (e.code === 'Space') {
          if (this.activeHold) {
            e.preventDefault();
            this.endHoldTap();
          }
        }
      });
    },

    _resolveSvg(explicitTarget) {
      if (explicitTarget) {
        if (explicitTarget.tagName && explicitTarget.tagName.toLowerCase() === 'svg') return explicitTarget;
        const inner = explicitTarget.querySelector && explicitTarget.querySelector('svg');
        if (inner) return inner;
      }
      if (this.svgEl && (!global.document || !global.document.body || global.document.body.contains(this.svgEl))) {
        return this.svgEl;
      }
      if (typeof document !== 'undefined') {
        const fallback =
          document.getElementById('goal2-stage-svg') ||
          document.getElementById('flow-svg') ||
          document.querySelector('svg[data-goal2-stage]');
        if (fallback) {
          this.svgEl = fallback;
        }
      }
      return this.svgEl;
    },

    /**
     * Switch between the 2 Winning Live Guided Performance Modes:
     * 'flow_matrix' | 'osu_taiko'
     */
    setMode(modeId) {
      const resolved = MODE_FALLBACK_MAP[modeId] || 'flow_matrix';
      this.currentMode = resolved;

      if (this.containerEl) {
        this.containerEl.querySelectorAll('[data-goal2-mode-btn]').forEach((btn) => {
          const m = btn.getAttribute('data-goal2-mode-btn');
          if (m === resolved) {
            btn.className =
              'px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all border bg-indigo-600 text-white border-indigo-400 shadow-sm';
          } else {
            btn.className =
              'px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all border bg-slate-900/70 text-slate-300 border-slate-700/80 hover:border-slate-500 hover:text-white';
          }
        });
        const descEl = this.containerEl.querySelector('[data-goal2-mode-desc]');
        if (descEl) descEl.textContent = LIVE_MODES[resolved].description;
      }

      if (typeof this.onModeChange === 'function') {
        this.onModeChange(resolved, LIVE_MODES[resolved]);
      }

      this.renderFrame(this.currentBeat, this.isResponseBar);
      return this;
    },

    switchMode(modeId) {
      return this.setMode(modeId);
    },

    getMode() {
      return this.currentMode;
    },

    getModeMetadata(modeId) {
      const resolved = MODE_FALLBACK_MAP[modeId || this.currentMode] || 'flow_matrix';
      return LIVE_MODES[resolved];
    },

    /**
     * Start a live Hold-to-Speak vowel gesture (`Spacebar` down or button pointerdown).
     * Voices the syllable with Web Audio formant synthesis while held and tracks duration.
     */
    startHoldTap(beatOverride) {
      const now = performance.now();
      const phrase = normalizePhrase(this.phrase, this.explicitVibe);
      const beat =
        typeof beatOverride === 'number'
          ? beatOverride
          : this.isPlaying
          ? this.currentBeat
          : this._findNextSequentialBeat(phrase);

      // Find nearest syllable to voice
      let nearestSyl = phrase.syllables[0];
      let minDiff = Infinity;
      phrase.syllables.forEach((s) => {
        const diff = Math.abs(beat - s.beat);
        if (diff < minDiff) {
          minDiff = diff;
          nearestSyl = s;
        }
      });

      // Start sustained formant voice in Web Audio while key is held
      const oscNodes = this._startSustainedFormantVoice(nearestSyl);

      this.activeHold = {
        sylIndex: nearestSyl.index,
        syl: nearestSyl,
        startBeat: beat,
        startTimeMs: now,
        oscNodes
      };

      this.manualTrails[nearestSyl.index] = {
        index: nearestSyl.index,
        perfBeat: beat,
        perfPreStart: Math.max(0, beat - (nearestSyl.preDur || 0.04)),
        perfDur: 0.12,
        perfStress: 0.92,
        perfPitchST: nearestSyl.pitchST,
        tag: `⌨️ Holding "${nearestSyl.text.replace(/-/g, '')}"...`,
        kind: 'manual_hold',
        active: true
      };

      // Trigger immediate P-center shockwave ripple at onset
      this.triggerTap(beat, 0.92, { fromHoldStart: true, sylIndex: nearestSyl.index, dur: 0.14 });
      return this.activeHold;
    },

    /**
     * End the live Hold-to-Speak vowel gesture (`Spacebar` up or pointerup),
     * computing exact held duration in beats and logging to Goal 1.
     */
    endHoldTap() {
      if (!this.activeHold) return null;
      const now = performance.now();
      const phrase = normalizePhrase(this.phrase, this.explicitVibe);
      const bpm = this._getEffectiveBpm(phrase);
      const beatDurMs = (60 / bpm) * 1000;

      const heldMs = Math.max(90, now - this.activeHold.startTimeMs);
      const heldBeats = +Math.max(0.10, Math.min(1.4, heldMs / beatDurMs)).toFixed(3);
      const syl = this.activeHold.syl;
      const startBeat = this.activeHold.startBeat;

      // Stop sustained Web Audio formant oscillators cleanly
      this._stopSustainedFormantVoice(this.activeHold.oscNodes);
      this.activeHold = null;

      const ratio = heldBeats / Math.max(0.08, syl.dur);
      const holdDesc =
        ratio > 1.35
          ? `Prolonged hold (${ratio.toFixed(1)}×)`
          : ratio < 0.65
          ? `Clipped hold (${ratio.toFixed(1)}×)`
          : `Good hold (${heldBeats.toFixed(2)}b)`;

      this.manualTrails[syl.index] = {
        index: syl.index,
        perfBeat: startBeat,
        perfPreStart: Math.max(0, startBeat - (syl.preDur || 0.04)),
        perfDur: heldBeats,
        perfStress: 0.92,
        perfPitchST: syl.pitchST,
        tag: `⌨️ "${syl.text.replace(/-/g, '')}": ${holdDesc}`,
        kind: 'manual_hold',
        active: false
      };

      // Finalize hit record with measured vowel duration `heldBeats`
      return this.triggerTap(startBeat, 0.94, {
        sylIndex: syl.index,
        dur: heldBeats,
        tag: this.manualTrails[syl.index].tag
      });
    },

    _startSustainedFormantVoice(syl) {
      const core = global.SpeechRhythmCore;
      if (!core || !core.audioEngine || typeof core.audioEngine.initContext !== 'function') return null;
      const ctx = core.audioEngine.initContext();
      if (!ctx) return null;

      try {
        const now = ctx.currentTime;
        const baseHz = 148 * Math.pow(2, ((syl && syl.pitchST) || 0) / 12);
        const osc = ctx.createOscillator();
        const sub = ctx.createOscillator();
        osc.type = 'sawtooth';
        sub.type = 'triangle';
        osc.frequency.setValueAtTime(baseHz, now);
        sub.frequency.setValueAtTime(baseHz, now);

        const filter = ctx.createBiquadFilter();
        filter.type = 'bandpass';
        filter.frequency.setValueAtTime(syl && syl.isGhost ? 520 : 660, now);
        filter.Q.setValueAtTime(4.0, now);

        const gain = ctx.createGain();
        gain.gain.setValueAtTime(0.001, now);
        gain.gain.linearRampToValueAtTime(0.28, now + 0.02);

        osc.connect(filter);
        sub.connect(gain);
        filter.connect(gain);
        gain.connect(core.audioEngine.masterGain || ctx.destination);

        osc.start(now);
        sub.start(now);
        return { ctx, osc, sub, gain };
      } catch (e) {
        return null;
      }
    },

    _stopSustainedFormantVoice(nodes) {
      if (!nodes || !nodes.ctx) return;
      try {
        const now = nodes.ctx.currentTime;
        nodes.gain.gain.setValueAtTime(nodes.gain.gain.value || 0.2, now);
        nodes.gain.gain.exponentialRampToValueAtTime(0.001, now + 0.045);
        nodes.osc.stop(now + 0.05);
        nodes.sub.stop(now + 0.05);
      } catch (e) {
        // Ignore already stopped
      }
    },

    /**
     * Sync an entire Virtual Speaker ("Bot Performer") trajectory into `SpeechRhythmCore.recordLiveSyllables`
     * so inspecting in Goal 1 immediately reflects the selected bot's timing & durations.
     */
    _syncBotTelemetryToCore(phrase, performerId) {
      const core = global.SpeechRhythmCore;
      if (!core || typeof core.recordLiveSyllables !== 'function') return;
      const botTraj = generateBotTrajectory(phrase, performerId);
      const scaleBack = phrase.scaleTo4 || 1.0;
      const hitEvents = botTraj.map((t) => ({
        beat: +(t.perfBeat / scaleBack).toFixed(3),
        rawBeat: +(t.perfBeat / scaleBack).toFixed(3),
        dur: +(t.perfDur / scaleBack).toFixed(3),
        preDur: t.preDur,
        stress: t.perfStress,
        pitchST: t.perfPitchST,
        pitchSlope: t.perfPitchSlope
      }));
      const numericPhraseId = typeof phrase.id === 'number' ? phrase.id : 0;
      this.phraseHitSlots[numericPhraseId] = hitEvents;
      const rate = performerId === 'bot_choppy' ? 0.85 : performerId === 'bot_dysfluent' ? 0.88 : 0.98;
      core.recordLiveSyllables(numericPhraseId, hitEvents, rate);
    },

    /**
     * Stutter-Free Live Biofeedback during Bar 2 (Response):
     * No jarring red "MISS/LATE" text popups while speaking! Instead:
     *  - Triggers glowing concentric P-Center shockwave ripples
     *  - Fills the active/nearest syllable capsule with warm luminescence
     *  - Records the hit timestamp, P-center offset, and vowel hold duration into `SpeechRhythmCore`
     *    so the user can switch to Goal 1 to inspect exact timing telemetry.
     */
    triggerTap(beatOverride, energy = 0.92, extra = {}) {
      const now = performance.now();
      const phrase = normalizePhrase(this.phrase, this.explicitVibe);
      const beat =
        typeof beatOverride === 'number'
          ? beatOverride
          : this.isPlaying
          ? this.currentBeat
          : this._findNextSequentialBeat(phrase);

      // Resolve target syllable
      let nearestSyl =
        typeof extra.sylIndex === 'number' && phrase.syllables[extra.sylIndex]
          ? phrase.syllables[extra.sylIndex]
          : phrase.syllables[0];

      if (typeof extra.sylIndex !== 'number') {
        let minDiff = Infinity;
        phrase.syllables.forEach((s) => {
          const diff = Math.abs(beat - s.beat);
          if (diff < minDiff) {
            minDiff = diff;
            nearestSyl = s;
          }
        });
      }

      const bpm = this._getEffectiveBpm(phrase);
      const beatDurMs = (60 / bpm) * 1000;
      const scaleBack = phrase.scaleTo4 || 1.0;
      const offsetBeats = (beat - nearestSyl.beat) / scaleBack;
      const offsetMs = Math.round(offsetBeats * beatDurMs);
      const performedDur = typeof extra.dur === 'number' ? extra.dur : nearestSyl.dur;

      // Store ripple for immediate concentric shockwave animation
      this.userRipples.push({
        beat,
        sylIndex: nearestSyl.index,
        pitchST: nearestSyl.pitchST,
        stress: nearestSyl.stress,
        time: now,
        kind: extra.kind || 'fluent',
        energy: Math.max(0.4, Math.min(1.0, energy))
      });

      // Store warm capsule luminescence on the syllable
      this.capsuleGlows[nearestSyl.index] = {
        time: now,
        beat,
        dur: performedDur,
        offsetMs,
        tag: extra.tag || '',
        kind: extra.kind || 'fluent',
        energy: Math.max(0.5, Math.min(1.0, energy))
      };

      // Record hit telemetry silently into SpeechRhythmCore for Goal 1 inspection
      const hitRecord = {
        phraseId: phrase.id,
        syllableId: nearestSyl.id,
        syllableIndex: nearestSyl.index,
        text: nearestSyl.text,
        targetBeat: nearestSyl.rawBeat !== undefined ? nearestSyl.rawBeat : nearestSyl.beat,
        performedBeat: +(beat / scaleBack).toFixed(3),
        normalizedTargetBeat: nearestSyl.beat,
        normalizedPerformedBeat: +beat.toFixed(3),
        beat: +(beat / scaleBack).toFixed(3),
        rawBeat: +(beat / scaleBack).toFixed(3),
        dur: +(performedDur / scaleBack).toFixed(3),
        stress: Math.min(1.0, Math.max(nearestSyl.stress, energy)),
        pitchST: typeof extra.pitchST === 'number' ? extra.pitchST : nearestSyl.pitchST,
        offsetMs,
        energy,
        performer: this.currentPerformer,
        bar: this.isResponseBar ? 2 : 1,
        mode: this.currentMode,
        timestamp: now
      };
      this.recordedHits.push(hitRecord);

      // Update per-phrase syllable slot telemetry for SpeechRhythmCore.recordLiveSyllables(phraseId, hitEvents)
      const numericPhraseId = typeof phrase.id === 'number' ? phrase.id : 0;
      if (!Array.isArray(this.phraseHitSlots[numericPhraseId])) {
        this.phraseHitSlots[numericPhraseId] = phrase.syllables.map((s) => ({
          beat: s.rawBeat !== undefined ? s.rawBeat : s.beat,
          rawBeat: s.rawBeat !== undefined ? s.rawBeat : s.beat,
          dur: s.dur,
          stress: s.stress,
          pitchST: s.pitchST
        }));
      }
      this.phraseHitSlots[numericPhraseId][nearestSyl.index] = {
        beat: hitRecord.performedBeat,
        rawBeat: hitRecord.performedBeat,
        dur: hitRecord.dur,
        stress: hitRecord.stress,
        pitchST: hitRecord.pitchST
      };

      const core = global.SpeechRhythmCore;
      if (core) {
        if (typeof core.recordLiveSyllables === 'function') {
          core.recordLiveSyllables(numericPhraseId, this.phraseHitSlots[numericPhraseId]);
        }
        if (Array.isArray(core.userHits)) {
          core.userHits.push(hitRecord);
        } else {
          core.userHits = [hitRecord];
        }
      }

      // Update telemetry badge gently (never showing jarring red error popups)
      if (this.containerEl) {
        const badge = this.containerEl.querySelector('[data-goal2-telemetry-badge]');
        if (badge) {
          const label = extra.tag || `✨ Captured "${nearestSyl.text.replace(/-/g, '')}" (${performedDur.toFixed(2)}b hold → Goal 1)`;
          badge.textContent = label;
        }
      }

      if (!this.isPlaying) {
        this.isResponseBar = true;
        this.renderFrame(beat, true, phrase);
      }
      return hitRecord;
    },

    triggerUserTap(beatOverride, energy) {
      return this.triggerTap(beatOverride, energy);
    },

    recordHit(beatOverride, energy) {
      return this.triggerTap(beatOverride, energy);
    },

    _findNextSequentialBeat(phrase) {
      if (!phrase.syllables.length) return 1.0;
      this._demoTapIdx = ((this._demoTapIdx || 0) + 1) % phrase.syllables.length;
      return phrase.syllables[this._demoTapIdx].beat;
    },

    _getEffectiveBpm(phrase) {
      const core = global.SpeechRhythmCore;
      if (core && core.audioEngine && typeof core.audioEngine.bpm === 'number') return core.audioEngine.bpm;
      if (core && typeof core.bpm === 'number') return core.bpm;
      return this.bpm || (phrase && phrase.bpm) || 88;
    },

    /**
     * Start standalone 2-Bar Call-and-Response animation loop
     * Bar 1 = Native Model Call (Beats 0.0 – 4.0)
     * Bar 2 = Live Response (Virtual Speaker Bot or Manual Spacebar/Mic, Beats 0.0 – 4.0)
     */
    startLoop(options = {}) {
      if (this.isPlaying) return this;
      this.isPlaying = true;
      this.startTime = performance.now();
      this.lastHalfStep = -1;
      this.lastSpokenSylKey = '';
      this.lastBotSpokenSylKey = '';
      this.userRipples = [];
      this.capsuleGlows = {};

      const phrase = normalizePhrase(this.phrase, this.explicitVibe);
      const core = global.SpeechRhythmCore;
      if (core && core.audioEngine && !options.externalAudio) {
        if (!core.audioEngine.isPlaying) {
          const startFn = core.audioEngine.startLoop || core.audioEngine.start;
          if (typeof startFn === 'function') {
            startFn.call(core.audioEngine, {
              bpm: this._getEffectiveBpm(phrase),
              phrase: this.phrase || 0,
              callAndResponseMode: true
            });
            this._startedCoreAudio = true;
          }
        }
        if (!this._boundCoreOnset && typeof core.audioEngine.onOnset === 'function') {
          this._boundCoreOnset = true;
          core.audioEngine.onOnset((onset) => {
            if (this.isPlaying && this.isResponseBar) {
              this.triggerTap(onset.beat, onset.vowelEnergy || 0.85);
            }
          });
        }
      }

      const step = (now) => {
        if (!this.isPlaying) return;
        const curPhrase = normalizePhrase(this.phrase, this.explicitVibe);
        const bpm = this._getEffectiveBpm(curPhrase);
        const beatDurMs = (60 / bpm) * 1000;
        const secPerBeat = 60 / bpm;
        const elapsedBeats = (now - this.startTime) / beatDurMs;

        // 8-beat cycle: Bar 1 [0..4) = Native Call, Bar 2 [4..8) = Student / Virtual Speaker Response
        let cycleBeat = elapsedBeats % 8.0;
        let isResponseBar = cycleBeat >= 4.0;
        let localBeat = cycleBeat % 4.0;
        let cycleIndex = Math.floor(elapsedBeats / 8.0);

        if (core && core.audioEngine && core.audioEngine.isPlaying) {
          const ph = core.audioEngine.getPlayheadState();
          localBeat = ph.beat;
          isResponseBar = Boolean(ph.isResponseBar);
          cycleBeat = (isResponseBar ? 4.0 : 0.0) + localBeat;
          cycleIndex = Math.floor((ph.barIndex || 0) / 2);

          if (isResponseBar && typeof core.audioEngine.getMicFrame === 'function') {
            const micFrame = core.audioEngine.getMicFrame();
            this.voiceEnergy = micFrame.vowelEnergy || 0;
            if (
              micFrame.source === 'live_mic' &&
              micFrame.isVowelOnset &&
              (!this._lastAutoRipple || now - this._lastAutoRipple > 190)
            ) {
              this._lastAutoRipple = now;
              this.triggerTap(localBeat, micFrame.vowelEnergy || 0.85);
            }
          }
        }

        // If user is currently holding Spacebar in Bar 2, update live held duration dynamically
        if (this.activeHold) {
          const heldMs = Math.max(60, now - this.activeHold.startTimeMs);
          const heldBeats = +Math.min(1.5, heldMs / beatDurMs).toFixed(3);
          const trail = this.manualTrails[this.activeHold.sylIndex];
          if (trail) {
            trail.perfDur = heldBeats;
          }
          this._updateSimulatedMeters(0.85, 0.78, 0.22);
        }

        // Drive Virtual Speaker Bot ("bot_native" | "bot_dysfluent" | "bot_choppy") automatically during Bar 2!
        if (isResponseBar && this.currentPerformer !== 'manual_space') {
          const botTraj = generateBotTrajectory(curPhrase, this.currentPerformer);
          let simLow = 0.04,
            simMid = 0.04,
            simHigh = 0.02;

          botTraj.forEach((item) => {
            // Pre-beat consonant sibilance energy
            if (localBeat >= item.perfPreStart && localBeat < item.perfBeat) {
              simHigh = Math.max(simHigh, item.pre && item.pre.length >= 2 ? 0.88 : 0.52);
              simMid = Math.max(simMid, 0.24);
            }
            // Active vowel nucleus hold
            if (localBeat >= item.perfBeat && localBeat <= item.perfBeat + item.perfDur) {
              simLow = Math.max(simLow, 0.35 + item.perfStress * 0.6);
              simMid = Math.max(simMid, 0.3 + item.perfStress * 0.55);
            }
            // Trigger bot syllable onset when playhead crosses `perfBeat`
            if (Math.abs(localBeat - item.perfBeat) < 0.065) {
              const botKey = `bot_${cycleIndex}_${item.index}_${this.currentPerformer}`;
              if (this.lastBotSpokenSylKey !== botKey) {
                this.lastBotSpokenSylKey = botKey;
                // Synthesize audible formant vowel for the virtual speaker in real time!
                if (core && core.audioEngine && core.audioEngine.ctx && typeof core.audioEngine.playSyllableCue === 'function') {
                  core.audioEngine.playSyllableCue(
                    {
                      text: item.text,
                      pre: item.pre,
                      preDur: item.preDur,
                      vowel: item.vowel,
                      beat: 0,
                      dur: item.perfDur,
                      stress: item.perfStress,
                      pitchST: item.perfPitchST,
                      pitchSlope: item.perfPitchSlope,
                      isGhost: item.isGhost && item.kind !== 'bloated_ghost'
                    },
                    core.audioEngine.ctx.currentTime,
                    secPerBeat,
                    false
                  );
                }
                // Fire stutter-free ripple & log to Goal 1
                this.triggerTap(item.perfBeat, item.perfStress, {
                  sylIndex: item.index,
                  dur: item.perfDur,
                  pitchST: item.perfPitchST,
                  tag: item.tag,
                  kind: item.kind
                });
              }
            }
          });
          this._updateSimulatedMeters(simLow, simMid, simHigh);
        }

        this.currentBeat = localBeat;
        this.isResponseBar = isResponseBar;
        this.barIndex = isResponseBar ? 1 : 0;

        this._updatePhaseBanner(localBeat, isResponseBar);
        this.renderFrame(localBeat, isResponseBar, curPhrase);

        if (typeof options.onFrame === 'function') {
          options.onFrame({ localBeat, isResponseBar, cycleBeat, phrase: curPhrase });
        }

        this.animFrame = requestAnimationFrame(step);
      };

      this.animFrame = requestAnimationFrame(step);
      return this;
    },

    _updateSimulatedMeters(lowRed, midGreen, highCyan) {
      if (typeof document === 'undefined') return;
      const rEl = document.getElementById('meter-red');
      const gEl = document.getElementById('meter-green');
      const cEl = document.getElementById('meter-cyan');
      if (rEl) rEl.style.height = `${Math.max(15, Math.round(lowRed * 100))}%`;
      if (gEl) gEl.style.height = `${Math.max(15, Math.round(midGreen * 100))}%`;
      if (cEl) cEl.style.height = `${Math.max(15, Math.round(highCyan * 100))}%`;
    },

    stopLoop() {
      this.isPlaying = false;
      if (this.animFrame) {
        cancelAnimationFrame(this.animFrame);
        this.animFrame = null;
      }
      if (this.activeHold) {
        this._stopSustainedFormantVoice(this.activeHold.oscNodes);
        this.activeHold = null;
      }
      const core = global.SpeechRhythmCore;
      if (this._startedCoreAudio && core && core.audioEngine && core.audioEngine.isPlaying) {
        core.audioEngine.stop();
        this._startedCoreAudio = false;
      }
      this.renderFrame(this.currentBeat, this.isResponseBar);
      return this;
    },

    togglePlay(options = {}) {
      return this.isPlaying ? this.stopLoop() : this.startLoop(options);
    },

    _updatePhaseBanner(localBeat, isResponseBar) {
      if (!this.containerEl) return;
      const pill = this.containerEl.querySelector('[data-goal2-phase-pill]');
      if (!pill) return;
      if (!isResponseBar) {
        if (localBeat >= 3.35) {
          pill.textContent = '🌬️ Beat 4 Pickup: INHALE & Pre-Position Articulators...';
          pill.className =
            'px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-500/20 text-amber-300 border border-amber-500/40';
        } else {
          pill.textContent = `🔊 Bar 1: Native Model Call (Beat ${Math.floor(localBeat) + 1} / 4)`;
          pill.className =
            'px-2.5 py-1 rounded-full text-xs font-semibold bg-cyan-500/15 text-cyan-300 border border-cyan-500/30';
        }
      } else {
        const perf = LIVE_PERFORMERS[this.currentPerformer] || LIVE_PERFORMERS.bot_native;
        pill.textContent = `🎤 Bar 2 Live (${perf.shortLabel}) • Beat ${Math.floor(localBeat) + 1} / 4`;
        pill.className =
          'px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/40';
      }
    },

    /**
     * Resolve active Bar 2 Live Performer Ghost Trail data for each syllable
     */
    _getActivePerformerTrails(phrase) {
      if (this.currentPerformer === 'manual_space') {
        return phrase.syllables.map((s, idx) => {
          if (this.manualTrails[idx]) {
            return this.manualTrails[idx];
          }
          return {
            index: idx,
            perfBeat: s.beat,
            perfPreStart: Math.max(0, s.beat - s.preDur),
            perfDur: 0,
            perfStress: s.stress,
            perfPitchST: s.pitchST,
            tag: 'Press & hold Spacebar when ball lands',
            kind: 'awaiting_manual'
          };
        });
      }
      return generateBotTrajectory(phrase, this.currentPerformer);
    },

    /**
     * Primary Frame Renderer (supports flexible argument signatures)
     */
    renderFrame(arg1 = 0, arg2 = false, arg3 = null, arg4 = {}) {
      let localBeat = 0;
      let isResponseBar = false;
      let rawPhrase = null;
      let opts = arg4 || {};

      if (arg1 && typeof arg1 === 'object' && !Array.isArray(arg1)) {
        localBeat =
          typeof arg1.localBeat === 'number'
            ? arg1.localBeat
            : typeof arg1.beat === 'number'
            ? arg1.beat
            : this.currentBeat;
        isResponseBar =
          typeof arg1.isResponseBar === 'boolean'
            ? arg1.isResponseBar
            : arg1.bar === 2 || arg1.phase === 'response';
        rawPhrase = arg1.phrase || this.phrase;
        if (arg1.mode) this.currentMode = MODE_FALLBACK_MAP[arg1.mode] || 'flow_matrix';
        opts = arg1;
      } else {
        localBeat = typeof arg1 === 'number' ? arg1 : this.currentBeat;
        isResponseBar = typeof arg2 === 'boolean' ? arg2 : Boolean(this.isResponseBar);
        rawPhrase = arg3 || this.phrase;
      }

      const beat = ((localBeat % 4.0) + 4.0) % 4.0;
      this.currentBeat = beat;
      this.isResponseBar = isResponseBar;

      const phrase = normalizePhrase(rawPhrase, this.explicitVibe);
      const svg = this._resolveSvg(opts.svg || opts.container);
      if (!svg) return '';

      const now = performance.now();
      this.userRipples = this.userRipples.filter((r) => now - r.time < 780);

      let svgContent = this._renderSharedDefs(isResponseBar, phrase);
      svgContent += this._renderTopCallResponseHud(beat, isResponseBar, phrase);

      if (this.currentMode === 'osu_taiko') {
        svgContent += this._renderOsuTaikoMode(beat, isResponseBar, phrase, now);
      } else {
        svgContent += this._renderFlowMatrixMode(beat, isResponseBar, phrase, now);
      }

      svg.setAttribute('viewBox', '0 0 980 360');
      svg.innerHTML = svgContent;
      return svgContent;
    },

    draw(localBeat, isResponseBar, phrase, opts) {
      return this.renderFrame(localBeat, isResponseBar, phrase, opts);
    },
    render(localBeat, isResponseBar, phrase, opts) {
      return this.renderFrame(localBeat, isResponseBar, phrase, opts);
    },

    // ------------------------------------------------------------------------
    // Shared SVG Gradients, Patterns & Glow Filters
    // ------------------------------------------------------------------------
    _renderSharedDefs(isResponseBar, phrase) {
      const themeGlow = isResponseBar ? '#10b981' : phrase.vibeMeta.accentColor || '#38bdf8';
      return `
        <defs>
          <!-- Hatched Diagonal Pattern for Pre-Beat Consonant Runways -->
          <pattern id="g2-amber-hatch" width="8" height="8" patternTransform="rotate(-45 0 0)" patternUnits="userSpaceOnUse">
            <rect width="8" height="8" fill="rgba(245, 158, 11, 0.16)" />
            <line x1="0" y1="0" x2="0" y2="8" stroke="rgba(251, 191, 36, 0.56)" stroke-width="3" />
          </pattern>

          <!-- Hesitation Block Freeze Pattern (Calm Amber/Teal Stripes, Never Jarring Red) -->
          <pattern id="g2-hesitation-hatch" width="10" height="10" patternTransform="rotate(45 0 0)" patternUnits="userSpaceOnUse">
            <rect width="10" height="10" fill="rgba(245, 158, 11, 0.14)" />
            <line x1="0" y1="0" x2="0" y2="10" stroke="rgba(251, 191, 36, 0.45)" stroke-width="2.5" />
          </pattern>

          <!-- Thought-Group Pause Gate Pattern (||) -->
          <pattern id="g2-pause-gate" width="6" height="6" patternUnits="userSpaceOnUse">
            <rect width="6" height="6" fill="rgba(139, 92, 246, 0.09)" />
            <circle cx="3" cy="3" r="1" fill="rgba(192, 132, 252, 0.35)" />
          </pattern>

          <!-- Soft Neon Glow Filter -->
          <filter id="g2-glow" x="-30%" y="-30%" width="160%" height="160%">
            <feGaussianBlur stdDeviation="4" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>

          <!-- Warm Affirmative Luminescence Gradient (Bar 2 Stutter-Free Biofeedback) -->
          <linearGradient id="g2-warm-luminescence" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stop-color="#10b981" stop-opacity="0.72" />
            <stop offset="60%" stop-color="#34d399" stop-opacity="0.52" />
            <stop offset="100%" stop-color="#fbbf24" stop-opacity="0.55" />
          </linearGradient>

          <!-- Bar 1 Model Call Wipe Gradient -->
          <linearGradient id="g2-call-wipe" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stop-color="#0284c7" stop-opacity="0.68" />
            <stop offset="100%" stop-color="#38bdf8" stop-opacity="0.48" />
          </linearGradient>

          <!-- Osu! Slider Ribbon Gradient -->
          <linearGradient id="g2-osu-slider" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stop-color="${themeGlow}" stop-opacity="0.54" />
            <stop offset="100%" stop-color="#818cf8" stop-opacity="0.16" />
          </linearGradient>
        </defs>
      `;
    },

    // ------------------------------------------------------------------------
    // Shared Top Call-and-Response 2-Bar Timeline Strip + Speech Vibe Badge
    // ------------------------------------------------------------------------
    _renderTopCallResponseHud(beat, isResponseBar, phrase) {
      const callFillPct = !isResponseBar ? (beat / 4.0) * 100 : 100;
      const respFillPct = isResponseBar ? (beat / 4.0) * 100 : 0;
      const isPickupCue = !isResponseBar && beat >= 3.35;
      const perf = LIVE_PERFORMERS[this.currentPerformer] || LIVE_PERFORMERS.bot_native;

      return `
        <g transform="translate(24, 6)">
          <!-- Bar 1: Native Model Call [Beats 0–4] -->
          <rect x="0" y="0" width="356" height="22" rx="6" fill="rgba(15, 23, 42, 0.92)" stroke="${
            !isResponseBar ? '#38bdf8' : 'rgba(148, 163, 184, 0.25)'
          }" stroke-width="${!isResponseBar ? 1.6 : 1}" />
          <rect x="0" y="0" width="${(356 * callFillPct) / 100}" height="22" rx="6" fill="rgba(56, 189, 248, 0.22)" />
          <text x="10" y="15" fill="${!isResponseBar ? '#7dd3fc' : '#64748b'}" font-size="10.5" font-weight="800" font-family="sans-serif">
            BAR 1: NATIVE MODEL CALL
          </text>
          <text x="346" y="15" text-anchor="end" fill="${
            isPickupCue ? '#fbbf24' : !isResponseBar ? '#38bdf8' : '#64748b'
          }" font-size="10" font-weight="700" font-family="monospace">
            ${isPickupCue ? '🌬️ INHALE PICKUP!' : !isResponseBar ? `Beat ${(beat + 1).toFixed(1)}` : '✓ Model Done'}
          </text>

          <!-- Center Speech Vibe Pill -->
          <rect x="364" y="0" width="204" height="22" rx="6" fill="${phrase.vibeMeta.badgeBg}" stroke="${phrase.vibeMeta.accentColor}" stroke-width="1.2" />
          <text x="466" y="15" text-anchor="middle" fill="#f8fafc" font-size="10.5" font-weight="800" font-family="sans-serif">
            ${phrase.vibeMeta.shortLabel.toUpperCase()}
          </text>

          <!-- Bar 2: Live Response [Beats 0–4] -->
          <rect x="576" y="0" width="356" height="22" rx="6" fill="rgba(15, 23, 42, 0.92)" stroke="${
            isResponseBar ? '#10b981' : 'rgba(148, 163, 184, 0.25)'
          }" stroke-width="${isResponseBar ? 1.8 : 1}" />
          <rect x="576" y="0" width="${(356 * respFillPct) / 100}" height="22" rx="6" fill="rgba(16, 185, 129, 0.25)" />
          <text x="586" y="15" fill="${isResponseBar ? '#6ee7b7' : '#94a3b8'}" font-size="10.5" font-weight="800" font-family="sans-serif">
            BAR 2: ${perf.shortLabel.toUpperCase()}
          </text>
          <text x="922" y="15" text-anchor="end" fill="${
            isResponseBar ? '#34d399' : '#64748b'
          }" font-size="10" font-weight="700" font-family="monospace">
            ${isResponseBar ? `Beat ${(beat + 1).toFixed(1)}` : 'Ghost Trail Ready'}
          </text>
        </g>
      `;
    },

    // ========================================================================
    // MODE 1: 'flow_matrix'
    // Stationary 16-Slot Rap Flow Matrix + Stress-Foot Pillars + Pause Gates (||)
    // + Anacrusis Ghost-Bead Ramps + Hatched Pre-Beat Runways + ♦ P-Center
    // + Variable-Gravity Parabolic Bouncing Ball + Bar 2 Live Performer Ghost Trail
    // ========================================================================
    _renderFlowMatrixMode(beat, isResponseBar, phrase, now) {
      const syls = phrase.syllables;
      const leftX = 56;
      const rightX = 936;
      const width = rightX - leftX;
      const beatToX = (b) => leftX + (Math.max(0, Math.min(4.0, b)) / 4.0) * width;

      const subLabels = ['1', 'e', '&', 'a', '2', 'e', '&', 'a', '3', 'e', '&', 'a', '4', 'e', '&', 'a'];
      const perfTrails = this._getActivePerformerTrails(phrase);
      const perfMeta = LIVE_PERFORMERS[this.currentPerformer] || LIVE_PERFORMERS.bot_native;
      let out = '';

      // 0. Top Stress-Foot Pillar Brackets (Speech Vibe Foot Structure)
      phrase.feet.forEach((f, idx) => {
        const fx1 = beatToX(f.startBeat);
        const fx2 = beatToX(f.endBeat);
        const fw = Math.max(24, fx2 - fx1 - 3);
        const isFootActive = beat >= f.startBeat && beat < f.endBeat;
        out += `
          <g>
            <rect
              x="${fx1 + 1.5}" y="34" width="${fw}" height="18" rx="4"
              fill="${isFootActive ? 'rgba(99, 102, 241, 0.25)' : 'rgba(30, 41, 59, 0.75)'}"
              stroke="${isFootActive ? phrase.vibeMeta.accentColor : 'rgba(148, 163, 184, 0.28)'}"
              stroke-width="1"
            />
            <text
              x="${fx1 + fw / 2}" y="46.5"
              text-anchor="middle" fill="${isFootActive ? '#f8fafc' : '#94a3b8'}"
              font-size="9.5" font-weight="700" font-family="monospace"
            >${f.label}</text>
          </g>
        `;
      });

      // 1. 16-Slot Subdivision Columns & 4 Primary Beat Pillars
      for (let slot = 0; slot < 16; slot++) {
        const slotBeat = slot * 0.25;
        const x = beatToX(slotBeat);
        const slotW = width / 16;
        const isMainBeat = slot % 4 === 0;
        const beatNum = Math.floor(slot / 4) + 1;
        const isCurrentSlot = beat >= slotBeat && beat < slotBeat + 0.25;

        out += `
          <rect
            x="${x}" y="55" width="${slotW - 2}" height="260" rx="4"
            fill="${
              isCurrentSlot
                ? isResponseBar
                  ? 'rgba(16, 185, 129, 0.08)'
                  : 'rgba(56, 189, 248, 0.08)'
                : slot % 2 === 0
                ? 'rgba(30, 41, 59, 0.30)'
                : 'rgba(15, 23, 42, 0.30)'
            }"
          />
        `;

        if (isMainBeat) {
          const isBeatHit = Math.abs(beat - slotBeat) < 0.14;
          const pillarColor = isBeatHit
            ? isResponseBar
              ? '#34d399'
              : '#38bdf8'
            : '#818cf8';
          const drumRole = beatNum % 2 === 1 ? 'KICK' : 'SNARE';
          out += `
            <rect
              x="${x - 16}" y="55" width="32" height="260" rx="6"
              fill="${isBeatHit ? 'rgba(99, 102, 241, 0.20)' : 'rgba(99, 102, 241, 0.06)'}"
            />
            <line
              x1="${x}" y1="55" x2="${x}" y2="315"
              stroke="${pillarColor}" stroke-width="${isBeatHit ? 2.6 : 1.7}" stroke-dasharray="5 3"
            />
            <rect x="${x - 38}" y="57" width="76" height="18" rx="5" fill="rgba(30, 27, 75, 0.92)" stroke="${pillarColor}" stroke-width="1" />
            <text x="${x}" y="69.5" text-anchor="middle" fill="#e0e7ff" font-size="10" font-weight="800" font-family="monospace">
              BEAT ${beatNum}·${drumRole}
            </text>
          `;
        } else {
          out += `
            <line x1="${x}" y1="76" x2="${x}" y2="313" stroke="rgba(148, 163, 184, 0.12)" stroke-width="1" />
          `;
        }

        // 16th-note subdivision label ("1 e & a") along bottom ruler
        out += `
          <text
            x="${x + (isMainBeat ? 0 : slotW * 0.15)}"
            y="330"
            text-anchor="middle"
            fill="${isMainBeat ? '#a5b4fc' : '#64748b'}"
            font-size="${isMainBeat ? '11.5' : '10'}"
            font-weight="${isMainBeat ? '800' : '600'}"
            font-family="monospace"
          >${subLabels[slot]}</text>
        `;
      }

      // 1b. Thought-Group Pause Gates (`||`) for the active Speech Vibe
      phrase.pauseGates.forEach((gate) => {
        const gx1 = beatToX(gate.startBeat);
        const gx2 = beatToX(gate.endBeat);
        const gw = Math.max(18, gx2 - gx1);
        const gMid = (gx1 + gx2) / 2;
        out += `
          <g>
            <rect
              x="${gx1}" y="78" width="${gw}" height="196" rx="6"
              fill="url(#g2-pause-gate)" stroke="rgba(192, 132, 252, 0.45)" stroke-width="1.2" stroke-dasharray="4 3"
            />
            <line x1="${gMid - 4}" y1="92" x2="${gMid - 4}" y2="256" stroke="#c084fc" stroke-width="2.2" stroke-opacity="0.7" />
            <line x1="${gMid + 4}" y1="92" x2="${gMid + 4}" y2="256" stroke="#c084fc" stroke-width="2.2" stroke-opacity="0.7" />
            <rect x="${gMid - 42}" y="80" width="84" height="16" rx="4" fill="rgba(46, 16, 101, 0.92)" stroke="#c084fc" stroke-width="1" />
            <text x="${gMid}" y="91" text-anchor="middle" fill="#e9d5ff" font-size="9" font-weight="800" font-family="monospace">
              || PAUSE GATE
            </text>
          </g>
        `;
      });

      // 2. Anacrusis Ghost-Bead Ramp Connector Lines (stepping upward into Stressed Beat Capsule)
      for (let i = 0; i < syls.length - 1; i++) {
        const cur = syls[i];
        const nxt = syls[i + 1];
        if (cur.isGhost) {
          const x1 = beatToX(cur.beat) + Math.max(16, (cur.dur / 4.0) * width * 0.5);
          const y1 = 224 - cur.rampProgress * 44;
          const x2 = beatToX(nxt.beat);
          const y2 = nxt.isGhost ? 224 - nxt.rampProgress * 44 : 146;
          out += `
            <line
              x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}"
              stroke="rgba(56, 189, 248, 0.45)" stroke-width="2" stroke-dasharray="3 3"
            />
          `;
        }
      }

      // 3. Variable-Gravity Parabolic Bouncing Ball Trajectory Curve (scaled by Speech Vibe gravity)
      const gScale = phrase.vibeMeta.gravityScale || 1.0;
      let arcD = '';
      for (let i = 0; i < syls.length - 1; i++) {
        const s1 = syls[i];
        const s2 = syls[i + 1];
        const x1 = beatToX(s1.beat);
        const x2 = beatToX(s2.beat);
        const y1 = s1.isGhost ? 210 - s1.rampProgress * 42 : 124;
        const y2 = s2.isGhost ? 210 - s2.rampProgress * 42 : 124;
        const ioi = Math.max(0.12, s2.beat - s1.beat);
        const apexLift = (s2.isGhost ? Math.min(34, 16 + ioi * 32) : Math.min(88, 50 + ioi * 64)) * gScale;
        const apexY = Math.max(66, Math.min(y1, y2) - apexLift);
        const cx = (x1 + x2) / 2;
        arcD += `M ${x1.toFixed(1)} ${y1.toFixed(1)} Q ${cx.toFixed(1)} ${apexY.toFixed(1)} ${x2.toFixed(1)} ${y2.toFixed(1)} `;
      }
      out += `
        <path
          d="${arcD}"
          fill="none"
          stroke="${isResponseBar ? 'rgba(16, 185, 129, 0.42)' : 'rgba(56, 189, 248, 0.42)'}"
          stroke-width="2.2"
          stroke-dasharray="6 4"
        />
      `;

      // 4. Target Syllables: Anacrusis Ghost Beads + Stressed Capsules with Pre-Beat Consonant Runway & ♦ P-Center
      syls.forEach((s) => {
        const pCenterX = beatToX(s.beat);
        const vowelW = Math.max(34, (s.dur / 4.0) * width);
        const preW = s.pre ? Math.max(24, (s.preDur / 4.0) * width, s.pre.length * 10 + 8) : 0;
        const isActive = beat >= s.beat - 0.03 && beat <= s.beat + s.dur;
        const wipePct = Math.max(0, Math.min(1, (beat - s.beat) / s.dur));

        const glowInfo = this.capsuleGlows[s.index];
        const glowAge = glowInfo ? (now - glowInfo.time) / 1600 : 999;
        const hasWarmGlow = glowAge < 1.0;
        const warmAlpha = hasWarmGlow ? (1 - glowAge) * 0.85 : 0;

        if (s.isGhost) {
          const beadW = Math.max(34, vowelW * 0.88);
          const beadH = 26;
          const beadY = 210 - s.rampProgress * 42;
          const fill = hasWarmGlow
            ? `rgba(16, 185, 129, ${0.25 + warmAlpha * 0.45})`
            : isActive
            ? isResponseBar
              ? 'rgba(16, 185, 129, 0.34)'
              : 'rgba(56, 189, 248, 0.34)'
            : 'rgba(30, 41, 59, 0.78)';
          const stroke = hasWarmGlow
            ? '#34d399'
            : isActive
            ? isResponseBar
              ? '#10b981'
              : '#38bdf8'
            : 'rgba(148, 163, 184, 0.42)';

          out += `
            <g opacity="${isActive || hasWarmGlow ? '1.0' : '0.76'}">
              <rect
                x="${pCenterX - 3}" y="${beadY}" width="${beadW}" height="${beadH}" rx="13"
                fill="${fill}" stroke="${stroke}" stroke-width="1.5"
              />
              <rect
                x="${pCenterX - 3}" y="${beadY}" width="${beadW * wipePct}" height="${beadH}" rx="13"
                fill="${isResponseBar ? 'url(#g2-warm-luminescence)' : 'url(#g2-call-wipe)'}"
              />
              <text
                x="${pCenterX - 3 + beadW / 2}" y="${beadY + 17}"
                text-anchor="middle" fill="#e2e8f0" font-size="11.5" font-weight="700" font-family="sans-serif"
              >${s.text}</text>
              <text
                x="${pCenterX - 3 + beadW / 2}" y="${beadY + beadH + 11}"
                text-anchor="middle" fill="#38bdf8" font-size="9" font-weight="700" font-family="monospace"
              >↗ ramp</text>
            </g>
          `;
        } else {
          const capY = 122;
          const capH = 50;
          const rhymeStyle = RHYME_PALETTE[s.rhyme] || RHYME_PALETTE.NONE;
          const activeColor = isResponseBar ? '#10b981' : '#38bdf8';

          // 4a. Hatched Pre-Beat Consonant Lead-In Runway (LEFT of the P-Center Beat Line)
          if (preW > 0) {
            out += `
              <g>
                <rect
                  x="${pCenterX - preW}" y="${capY + 7}" width="${preW}" height="${capH - 14}" rx="6"
                  fill="url(#g2-amber-hatch)" stroke="#f59e0b" stroke-width="1.5" stroke-dasharray="3 2"
                />
                <text
                  x="${pCenterX - preW / 2}" y="${capY + 30}"
                  text-anchor="middle" fill="#fde68a" font-size="12" font-weight="800" font-family="monospace"
                >${s.pre}-</text>
                <text
                  x="${pCenterX - preW / 2}" y="${capY + 2}"
                  text-anchor="middle" fill="#fbbf24" font-size="9" font-weight="700" font-family="monospace"
                >-${s.leadInMs}ms</text>
              </g>
            `;
          }

          // 4b. Solid Vowel Nucleus Capsule snapped directly onto P-Center X
          out += `
            <g>
              ${
                hasWarmGlow || isActive
                  ? `<rect x="${pCenterX - 2}" y="${capY - 2}" width="${vowelW + 4}" height="${capH + 4}" rx="12" fill="none" stroke="${
                      hasWarmGlow ? '#34d399' : activeColor
                    }" stroke-width="2.5" opacity="${hasWarmGlow ? warmAlpha : 0.75}" filter="url(#g2-glow)" />`
                  : ''
              }
              <rect
                x="${pCenterX}" y="${capY}" width="${vowelW}" height="${capH}" rx="10"
                fill="${hasWarmGlow ? 'rgba(6, 78, 59, 0.80)' : 'rgba(15, 23, 42, 0.92)'}"
                stroke="${hasWarmGlow ? '#34d399' : isActive ? activeColor : rhymeStyle.stroke}"
                stroke-width="${isActive || hasWarmGlow ? 2.5 : 1.8}"
              />
              <rect
                x="${pCenterX}" y="${capY}" width="${vowelW * wipePct}" height="${capH}" rx="10"
                fill="${isResponseBar || hasWarmGlow ? 'url(#g2-warm-luminescence)' : 'url(#g2-call-wipe)'}"
              />

              <!-- Vowel Nucleus Label -->
              <text
                x="${pCenterX + vowelW / 2}" y="${capY + 31}"
                text-anchor="middle" fill="#f8fafc" font-size="15.5" font-weight="900" letter-spacing="0.5" font-family="sans-serif"
              >${s.vowel}</text>

              <!-- ♦ P-Center Bullseye Diamond locked on the Beat Line -->
              <polygon
                points="${pCenterX},${capY + capH / 2 - 7} ${pCenterX + 7},${capY + capH / 2} ${pCenterX},${capY + capH / 2 + 7} ${pCenterX - 7},${capY + capH / 2}"
                fill="${isActive || hasWarmGlow ? '#fbbf24' : activeColor}"
                stroke="#0f172a" stroke-width="1.4"
              />
              <text
                x="${pCenterX}" y="${capY + capH + 14}"
                text-anchor="middle" fill="#a5b4fc" font-size="10" font-weight="700" font-family="monospace"
              >♦ P-Center</text>
            </g>
          `;

          if (s.isFinal) {
            out += `
              <text x="${pCenterX + vowelW}" y="${capY + capH + 14}" text-anchor="end" fill="#c084fc" font-size="9.5" font-weight="700" font-family="sans-serif">
                hold tail ➔
              </text>
            `;
          }
        }
      });

      // 5. BAR 2 LIVE PERFORMER GHOST TRAIL LANE (y: 266..308)
      // Visually compares the Virtual Speaker's (or Spacebar Holder's) actual onset, hesitation blocks, and vowel hold duration vs. the target!
      const laneY = 266;
      const laneH = 42;
      out += `
        <rect
          x="${leftX - 8}" y="${laneY}" width="${width + 16}" height="${laneH}" rx="8"
          fill="rgba(15, 23, 42, 0.92)"
          stroke="${isResponseBar ? perfMeta.badgeColor : 'rgba(148, 163, 184, 0.25)'}"
          stroke-width="${isResponseBar ? 1.6 : 1}"
        />
        <text x="${leftX}" y="${laneY + 13}" fill="${isResponseBar ? '#f8fafc' : '#94a3b8'}" font-size="9.5" font-weight="800" font-family="monospace">
          BAR 2 LIVE PERFORMER GHOST TRAIL (${perfMeta.shortLabel.toUpperCase()}) — Performed Onset ♦ &amp; Vowel Duration vs. Target Dashed Outline:
        </text>
      `;

      perfTrails.forEach((t, idx) => {
        const s = syls[idx];
        const targetX = beatToX(s.beat);
        const targetW = Math.max(24, (s.dur / 4.0) * width);
        const perfX = beatToX(t.perfBeat);
        const perfW = Math.max(10, (t.perfDur / 4.0) * width);
        const barY = laneY + 18;
        const barH = 18;

        // Progressive reveal during Bar 2 playback (or full reveal when paused/previewing)
        const fillProgress = !this.isPlaying
          ? 1.0
          : !isResponseBar
          ? 0.25
          : beat < t.perfBeat
          ? 0.0
          : Math.min(1.0, (beat - t.perfBeat) / Math.max(0.06, t.perfDur));

        // 5a. Hesitation Block Freeze Zone (for Dysfluent Speaker Simulator)
        if (t.kind === 'hesitation_block' && typeof t.blockZoneStart === 'number') {
          const bx1 = beatToX(t.blockZoneStart);
          const bx2 = beatToX(t.blockZoneEnd);
          const bw = Math.max(18, bx2 - bx1);
          out += `
            <g>
              <rect
                x="${bx1}" y="${barY - 2}" width="${bw}" height="${barH + 4}" rx="4"
                fill="url(#g2-hesitation-hatch)" stroke="#fbbf24" stroke-width="1.2" stroke-dasharray="2 2"
              />
              <text x="${bx1 + bw / 2}" y="${barY + 11}" text-anchor="middle" fill="#fde68a" font-size="8.5" font-weight="800" font-family="monospace">
                ⏸ BLOCK
              </text>
            </g>
          `;
        }

        // 5b. Target Reference Dashed Ghost Box
        out += `
          <rect
            x="${targetX}" y="${barY}" width="${targetW}" height="${barH}" rx="5"
            fill="none" stroke="rgba(148, 163, 184, 0.35)" stroke-width="1" stroke-dasharray="3 2"
          />
        `;

        // 5c. Performed Syllable Capsule Fill & Label
        if (t.perfDur > 0.01) {
          const trailStroke =
            t.kind === 'fluent'
              ? '#10b981'
              : t.kind === 'prolongation' || t.kind === 'hesitation_block'
              ? '#f59e0b'
              : t.kind === 'manual_hold'
              ? '#38bdf8'
              : '#fb7185';
          const trailFill =
            t.kind === 'fluent'
              ? 'rgba(16, 185, 129, 0.38)'
              : t.kind === 'prolongation' || t.kind === 'hesitation_block'
              ? 'rgba(245, 158, 11, 0.36)'
              : t.kind === 'manual_hold'
              ? 'rgba(56, 189, 248, 0.42)'
              : 'rgba(244, 63, 94, 0.34)';

          out += `
            <g>
              <!-- Tether line from Target P-center to Performed P-center -->
              <line x1="${targetX}" y1="${barY}" x2="${perfX}" y2="${barY}" stroke="${trailStroke}" stroke-width="1.5" />
              <rect
                x="${perfX}" y="${barY}" width="${perfW}" height="${barH}" rx="5"
                fill="rgba(15, 23, 42, 0.75)" stroke="${trailStroke}" stroke-width="1.4"
              />
              <rect
                x="${perfX}" y="${barY}" width="${perfW * fillProgress}" height="${barH}" rx="5"
                fill="${trailFill}"
              />
              <polygon
                points="${perfX},${barY + 5} ${perfX + 4},${barY + 9} ${perfX},${barY + 13} ${perfX - 4},${barY + 9}"
                fill="${trailStroke}"
              />
              <text
                x="${perfX + perfW / 2}" y="${barY + 12.5}"
                text-anchor="middle" fill="#f8fafc" font-size="9.5" font-weight="700" font-family="sans-serif"
              >${t.displayLabel || s.text.replace(/[-.]/g, '')}</text>
            </g>
          `;
        }
      });

      // 6. Stutter-Free Concentric P-Center Shockwave Ripples
      this.userRipples.forEach((r) => {
        const rx = beatToX(r.beat);
        const age = (now - r.time) / 780;
        const r1 = 12 + age * 54;
        const r2 = 6 + age * 34;
        const alpha = Math.max(0, (1 - age) * 0.9);
        out += `
          <g pointer-events="none">
            <circle cx="${rx}" cy="148" r="${r1}" fill="none" stroke="rgba(52, 211, 153, ${alpha})" stroke-width="3" />
            <circle cx="${rx}" cy="148" r="${r2}" fill="rgba(16, 185, 129, ${alpha * 0.25})" stroke="rgba(251, 191, 36, ${alpha * 0.85})" stroke-width="1.8" />
          </g>
        `;
      });

      // 7. Kinematic Variable-Gravity Bouncing Ball Playhead
      const playX = beatToX(beat);
      let ballY = 122;
      if (syls.length > 0) {
        if (beat <= syls[0].beat) {
          const t = syls[0].beat > 0 ? beat / syls[0].beat : 1;
          const targetY = syls[0].isGhost ? 210 - syls[0].rampProgress * 42 : 122;
          ballY = (1 - t) * 92 + t * targetY;
        } else if (beat >= syls[syls.length - 1].beat) {
          const last = syls[syls.length - 1];
          const t = Math.min(1, (beat - last.beat) / Math.max(0.3, 4.0 - last.beat));
          const startY = last.isGhost ? 210 - last.rampProgress * 42 : 122;
          ballY = startY - Math.sin(t * Math.PI) * 30;
        } else {
          for (let i = 0; i < syls.length - 1; i++) {
            const s1 = syls[i];
            const s2 = syls[i + 1];
            if (beat >= s1.beat && beat <= s2.beat) {
              const span = Math.max(0.05, s2.beat - s1.beat);
              const t = (beat - s1.beat) / span;
              const y1 = s1.isGhost ? 210 - s1.rampProgress * 42 : 122;
              const y2 = s2.isGhost ? 210 - s2.rampProgress * 42 : 122;
              const apexLift = (s2.isGhost ? Math.min(34, 16 + span * 32) : Math.min(88, 50 + span * 64)) * gScale;
              const apexY = Math.max(66, Math.min(y1, y2) - apexLift);
              ballY = (1 - t) * (1 - t) * y1 + 2 * (1 - t) * t * apexY + t * t * y2;
              break;
            }
          }
        }
      }

      const playColor = isResponseBar ? '#10b981' : '#38bdf8';
      out += `
        <line x1="${playX}" y1="55" x2="${playX}" y2="315" stroke="${playColor}" stroke-width="2" stroke-opacity="0.65" />
        <circle cx="${playX}" cy="${ballY}" r="15" fill="none" stroke="${playColor}" stroke-width="2" stroke-opacity="0.45" />
        <circle cx="${playX}" cy="${ballY}" r="9" fill="${playColor}" filter="url(#g2-glow)" />
        <circle cx="${playX - 2.5}" cy="${ballY - 2.5}" r="2.8" fill="#ffffff" />
      `;

      // Bottom Legend
      out += `
        <text x="${leftX}" y="350" fill="#94a3b8" font-size="10" font-family="sans-serif">
          Amber Hatched Runway = Pre-beat consonant lead-in (str-, pl-) • ♦ = Vowel P-Center on Beat • || = Pause Gate • Bottom Track = Bar 2 Live Performer Trail
        </text>
      `;

      return out;
    },

    // ========================================================================
    // MODE 2: 'osu_taiko'
    // Taiko + Osu! Single-Line Prosodic Conveyor (Big Stressed Circles vs. Small
    // Ghost Beads, Radially Shrinking Approach Rings, Osu! Vowel Hold Slider
    // Tails with Rolling Follow-Ball, Pause Gates `||`, and Bar 2 Live Fill)
    // ========================================================================
    _renderOsuTaikoMode(beat, isResponseBar, phrase, now) {
      const syls = phrase.syllables;
      const leftX = 68;
      const rightX = 924;
      const width = rightX - leftX;
      const centerY = 166;
      const beatToX = (b) => leftX + (Math.max(0, Math.min(4.0, b)) / 4.0) * width;
      const pitchToY = (st) => centerY - Math.max(-6, Math.min(7, st || 0)) * 6.8;

      const perfTrails = this._getActivePerformerTrails(phrase);
      const perfMeta = LIVE_PERFORMERS[this.currentPerformer] || LIVE_PERFORMERS.bot_native;
      let out = '';

      // 1. Taiko / Osu! Conveyor Track Frame & Stress-Foot Header Bands
      out += `
        <rect x="28" y="36" width="924" height="232" rx="14" fill="rgba(15, 23, 42, 0.82)" stroke="rgba(148, 163, 184, 0.22)" stroke-width="1.2" />
        <line x1="42" y1="${centerY}" x2="938" y2="${centerY}" stroke="rgba(148, 163, 184, 0.26)" stroke-width="2" stroke-dasharray="6 4" />
        <text x="38" y="${centerY - 8}" fill="#64748b" font-size="9.5" font-family="monospace">F0 Pitch Midline (0 ST)</text>
      `;

      // Stress-Foot Zones along the top of the Taiko Conveyor
      phrase.feet.forEach((f) => {
        const fx1 = beatToX(f.startBeat);
        const fx2 = beatToX(f.endBeat);
        const fw = Math.max(20, fx2 - fx1 - 3);
        const isFootActive = beat >= f.startBeat && beat < f.endBeat;
        out += `
          <rect
            x="${fx1 + 1.5}" y="42" width="${fw}" height="16" rx="4"
            fill="${isFootActive ? 'rgba(99, 102, 241, 0.25)' : 'rgba(30, 41, 59, 0.65)'}"
            stroke="${isFootActive ? phrase.vibeMeta.accentColor : 'rgba(148, 163, 184, 0.22)'}"
          />
          <text x="${fx1 + fw / 2}" y="53" text-anchor="middle" fill="#cbd5e1" font-size="9" font-weight="700" font-family="monospace">
            ${f.label}
          </text>
        `;
      });

      // 4 Beat Pillar Markers along the Taiko Track
      for (let b = 0; b < 4; b++) {
        const bx = beatToX(b);
        const isNear = Math.abs(beat - b) < 0.14;
        out += `
          <line x1="${bx}" y1="62" x2="${bx}" y2="262" stroke="${
            isNear ? '#818cf8' : 'rgba(99, 102, 241, 0.30)'
          }" stroke-width="${isNear ? 2.4 : 1.3}" stroke-dasharray="4 4" />
          <text x="${bx}" y="74" text-anchor="middle" fill="#a5b4fc" font-size="10.5" font-weight="800" font-family="monospace">
            BEAT ${b + 1}
          </text>
        `;
      }

      // Thought-Group Pause Gates (`||`) on the Conveyor
      phrase.pauseGates.forEach((gate) => {
        const gx1 = beatToX(gate.startBeat);
        const gx2 = beatToX(gate.endBeat);
        const gMid = (gx1 + gx2) / 2;
        out += `
          <line x1="${gMid - 3.5}" y1="78" x2="${gMid - 3.5}" y2="252" stroke="#c084fc" stroke-width="2" stroke-dasharray="4 3" />
          <line x1="${gMid + 3.5}" y1="78" x2="${gMid + 3.5}" y2="252" stroke="#c084fc" stroke-width="2" stroke-dasharray="4 3" />
          <text x="${gMid}" y="258" text-anchor="middle" fill="#d8b4fe" font-size="9" font-weight="800" font-family="monospace">|| PAUSE</text>
        `;
      });

      // 2. Smooth F0 Pitch Contour & Osu! Follow-Point Dashed Connector Lines
      if (syls.length > 1) {
        let f0Path = `M ${beatToX(syls[0].beat).toFixed(1)} ${pitchToY(syls[0].pitchST).toFixed(1)} `;
        for (let i = 0; i < syls.length - 1; i++) {
          const x1 = beatToX(syls[i].beat);
          const y1 = pitchToY(syls[i].pitchST);
          const x2 = beatToX(syls[i + 1].beat);
          const y2 = pitchToY(syls[i + 1].pitchST);
          const cx = (x1 + x2) / 2;
          f0Path += `C ${cx.toFixed(1)} ${y1.toFixed(1)}, ${cx.toFixed(1)} ${y2.toFixed(1)}, ${x2.toFixed(1)} ${y2.toFixed(1)} `;

          out += `
            <line
              x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}"
              stroke="rgba(148, 163, 184, 0.35)" stroke-width="2" stroke-dasharray="3 6"
            />
          `;
        }
        out += `
          <path d="${f0Path}" fill="none" stroke="rgba(99, 102, 241, 0.28)" stroke-width="5" stroke-linecap="round" />
        `;
      }

      // 3. Render Each Syllable: Tapered Osu! Slider Ribbon Tail + Big Stressed Circle (1.7×) vs Small Ghost Bead + Shrinking Approach Ring
      const baseGhostR = 15;
      const stressedR = Math.round(baseGhostR * 1.7); // ~26px radius

      syls.forEach((s, idx) => {
        const cx = beatToX(s.beat);
        const cy = pitchToY(s.pitchST);
        const r = s.isGhost ? baseGhostR : stressedR;
        const tailW = Math.max(24, (s.dur / 4.0) * width);
        const isHolding = beat >= s.beat && beat <= s.beat + s.dur;
        const holdPct = Math.max(0, Math.min(1, (beat - s.beat) / s.dur));

        const glowInfo = this.capsuleGlows[s.index];
        const glowAge = glowInfo ? (now - glowInfo.time) / 1600 : 999;
        const hasWarmGlow = glowAge < 1.0;

        // 3a. Pre-beat consonant lead-in whisker (left of the Taiko/Osu hit circle)
        if (s.pre) {
          const leadW = Math.max(24, (s.preDur / 4.0) * width, s.pre.length * 10 + 8);
          out += `
            <path
              d="M ${cx - r - leadW} ${cy} L ${cx - r} ${cy}"
              stroke="#f59e0b" stroke-width="6" stroke-linecap="round" stroke-dasharray="3 3" opacity="0.88"
            />
            <text x="${cx - r - leadW / 2}" y="${cy - 9}" text-anchor="middle" fill="#fde68a" font-size="10.5" font-weight="800" font-family="monospace">
              ${s.pre}-
            </text>
          `;
        }

        // 3b. Tapered Osu! Vowel Hold Slider Ribbon Tail + Progressive Fill
        const startH = s.isGhost ? 15 : 32;
        const endH = s.isGhost ? 6 : 12;
        const xEnd = cx + tailW;
        const ribbonPath = `
          M ${cx} ${cy - startH / 2}
          L ${xEnd} ${cy - endH / 2}
          A ${endH / 2} ${endH / 2} 0 0 1 ${xEnd} ${cy + endH / 2}
          L ${cx} ${cy + startH / 2}
          Z
        `;
        out += `
          <path
            d="${ribbonPath}"
            fill="url(#g2-osu-slider)"
            stroke="${isHolding || hasWarmGlow ? (isResponseBar ? '#34d399' : '#38bdf8') : 'rgba(129, 140, 248, 0.45)'}"
            stroke-width="${isHolding ? 2.2 : 1.3}"
          />
        `;

        // Active slider follow-ball rolling along the tapered ribbon during vowel hold
        if (isHolding) {
          const followX = cx + tailW * holdPct;
          const followR = (startH * (1 - holdPct) + endH * holdPct) * 0.48;
          out += `
            <circle
              cx="${followX}" cy="${cy}" r="${Math.max(5, followR)}"
              fill="${isResponseBar ? '#34d399' : '#38bdf8'}" stroke="#ffffff" stroke-width="2"
              filter="url(#g2-glow)"
            />
          `;
        }

        // 3c. Radially Shrinking Osu! Approach Ring (converges onto syllable head at exact P-center moment)
        let deltaBeats = s.beat - beat;
        if (deltaBeats < -0.25) deltaBeats += 4.0;
        const approachWindow = 1.35;
        if (deltaBeats >= -0.08 && deltaBeats <= approachWindow) {
          const norm = Math.max(0, deltaBeats / approachWindow);
          const approachR = r + norm * (s.isGhost ? 24 : 44);
          const ringAlpha = 0.25 + (1 - norm) * 0.72;
          const ringColor = deltaBeats <= 0.12 ? '#fbbf24' : isResponseBar ? '#34d399' : '#38bdf8';
          out += `
            <circle
              cx="${cx}" cy="${cy}" r="${approachR.toFixed(1)}"
              fill="none" stroke="${ringColor}" stroke-width="${s.isGhost ? 2 : 3}"
              stroke-opacity="${ringAlpha.toFixed(2)}"
            />
          `;
        }

        // 3d. Syllable Head Circle: Big Stressed 1.7× Dai-Don with Halo vs. Small Hollow Ghost Bead
        if (s.isGhost) {
          out += `
            <circle
              cx="${cx}" cy="${cy}" r="${r}"
              fill="${hasWarmGlow ? 'rgba(16, 185, 129, 0.38)' : isHolding ? 'rgba(56, 189, 248, 0.28)' : 'rgba(15, 23, 42, 0.88)'}"
              stroke="${hasWarmGlow ? '#34d399' : isHolding ? '#38bdf8' : 'rgba(148, 163, 184, 0.65)'}"
              stroke-width="2" stroke-dasharray="4 2"
            />
            <text x="${cx}" y="${cy + 4}" text-anchor="middle" fill="#cbd5e1" font-size="10.5" font-weight="700" font-family="sans-serif">
              ${s.text}
            </text>
          `;
        } else {
          const haloColor = hasWarmGlow ? '#10b981' : isResponseBar ? '#10b981' : '#f43f5e';
          const innerFill = hasWarmGlow
            ? 'rgba(6, 95, 70, 0.92)'
            : isHolding
            ? isResponseBar
              ? 'rgba(5, 150, 105, 0.92)'
              : 'rgba(225, 29, 72, 0.90)'
            : 'rgba(30, 27, 75, 0.95)';
          out += `
            <circle
              cx="${cx}" cy="${cy}" r="${r + 6}"
              fill="none" stroke="${haloColor}" stroke-width="2.5"
              stroke-opacity="${isHolding || hasWarmGlow ? '0.9' : '0.42'}"
              filter="url(#g2-glow)"
            />
            <circle
              cx="${cx}" cy="${cy}" r="${r}"
              fill="${innerFill}"
              stroke="#f8fafc" stroke-width="2.8"
            />
            <text x="${cx}" y="${cy + 5}" text-anchor="middle" fill="#ffffff" font-size="13" font-weight="900" font-family="sans-serif">
              ${s.vowel}
            </text>
            <text x="${cx}" y="${cy + r + 16}" text-anchor="middle" fill="#a5b4fc" font-size="9.5" font-weight="700" font-family="monospace">
              ♦ ${s.pitchST >= 0 ? '+' : ''}${s.pitchST.toFixed(1)}ST
            </text>
          `;
        }
      });

      // 4. BAR 2 LIVE PERFORMER CONVEYOR FEEDBACK STRIP (y: 274..322)
      const laneY = 274;
      const laneH = 46;
      out += `
        <rect
          x="28" y="${laneY}" width="924" height="${laneH}" rx="10"
          fill="rgba(15, 23, 42, 0.92)"
          stroke="${isResponseBar ? perfMeta.badgeColor : 'rgba(148, 163, 184, 0.25)'}"
          stroke-width="${isResponseBar ? 1.6 : 1}"
        />
        <text x="42" y="${laneY + 14}" fill="${isResponseBar ? '#f8fafc' : '#94a3b8'}" font-size="9.5" font-weight="800" font-family="monospace">
          BAR 2 LIVE TAiKO/OSU! FILL (${perfMeta.shortLabel.toUpperCase()}) — Performed Circle Hit &amp; Slider Hold Duration:
        </text>
      `;

      perfTrails.forEach((t, idx) => {
        const s = syls[idx];
        const perfX = beatToX(t.perfBeat);
        const perfW = Math.max(12, (t.perfDur / 4.0) * width);
        const cy = laneY + 30;
        const r = s.isGhost ? 7 : 10;

        if (t.kind === 'hesitation_block' && typeof t.blockZoneStart === 'number') {
          const bx1 = beatToX(t.blockZoneStart);
          const bx2 = beatToX(t.blockZoneEnd);
          out += `
            <rect x="${bx1}" y="${cy - 9}" width="${Math.max(16, bx2 - bx1)}" height="18" rx="4" fill="url(#g2-hesitation-hatch)" stroke="#fbbf24" stroke-width="1" />
          `;
        }

        if (t.perfDur > 0.01) {
          const color =
            t.kind === 'fluent'
              ? '#10b981'
              : t.kind === 'prolongation' || t.kind === 'hesitation_block'
              ? '#f59e0b'
              : t.kind === 'manual_hold'
              ? '#38bdf8'
              : '#fb7185';
          out += `
            <line x1="${perfX}" y1="${cy}" x2="${perfX + perfW}" y2="${cy}" stroke="${color}" stroke-width="${s.isGhost ? 6 : 10}" stroke-linecap="round" stroke-opacity="0.65" />
            <circle cx="${perfX}" cy="${cy}" r="${r}" fill="${color}" stroke="#ffffff" stroke-width="1.5" />
            <text x="${perfX + perfW / 2}" y="${cy + 3}" text-anchor="middle" fill="#ffffff" font-size="8.5" font-weight="800" font-family="sans-serif">
              ${t.displayLabel || s.text.replace(/[-.]/g, '')}
            </text>
          `;
        }
      });

      // 5. Stutter-Free Concentric Shockwave Ripples on the Conveyor Line
      this.userRipples.forEach((r) => {
        const rx = beatToX(r.beat);
        const ry = pitchToY(r.pitchST || 0);
        const age = (now - r.time) / 780;
        const rad = 18 + age * 56;
        const alpha = Math.max(0, (1 - age) * 0.9);
        out += `
          <circle cx="${rx}" cy="${ry}" r="${rad}" fill="none" stroke="rgba(52, 211, 153, ${alpha})" stroke-width="3.2" />
        `;
      });

      // 6. Playhead Cursor Line
      const playX = beatToX(beat);
      const playColor = isResponseBar ? '#10b981' : '#38bdf8';
      out += `
        <line x1="${playX}" y1="40" x2="${playX}" y2="318" stroke="${playColor}" stroke-width="2.2" stroke-opacity="0.7" />
        <polygon points="${playX - 7},40 ${playX + 7},40 ${playX},50" fill="${playColor}" />
      `;

      // Legend Footer
      out += `
        <text x="42" y="346" fill="#94a3b8" font-size="10" font-family="sans-serif">
          ◎ Shrinking Ring converges at exact P-Center • Big Circle (1.7×) = Stressed Beat • Small Hollow Bead = Schwa • Slider Tail = Vowel Hold Duration
        </text>
      `;

      return out;
    }
  };

  // Expose globally as `window.Goal2LiveTrainer`
  global.Goal2LiveTrainer = Goal2LiveTrainer;
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = Goal2LiveTrainer;
  }
})(typeof window !== 'undefined' ? window : globalThis);
