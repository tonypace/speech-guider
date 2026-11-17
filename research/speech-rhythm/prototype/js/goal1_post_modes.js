/**
 * ============================================================================
 * SPEECH RHYTHM INTERACTIVE SUITE — GOAL 1: POST-UTTERANCE DIAGNOSTIC MODES
 * File: /home/tonyp/Projects/Speech Rhythm/app/goal1_post_modes.js
 *
 * Defines `window.Goal1PostDiagnostics` with **VocAlign Elastic Tethers &
 * Beat Bins** (`'vocalign_tether'`) as the flagship, high-contrast centerpiece
 * for comparing **Dysfluent / L2 Speech vs. Native Speech**, alongside two
 * streamlined complementary views (`'prosogram_overlay'` and `'foot_budget_strips'`)
 * and legacy mode aliases.
 *
 * Key Highlights:
 *   1. Flagship `'vocalign_tether'` (VocAlign Pro + Dysfluency Inspector):
 *      - Mid-Foot Hesitation Blocks (`[ ⚡ 450ms BLOCK / "uh..." ]`) rendered as
 *        vivid Red/Rose Jagged Tear Zones splitting tether ribbons wide open.
 *      - Abnormal Prolongations (`"theeee..."` / Bloated Schwas) rendered with
 *        dramatic Amber Funnel Ribbons ballooning 2.5x wider (`+140% Bloated`).
 *      - Stutter / False-Start Repetitions (`[p-][p-]PROB`, `[str-][str-]`)
 *        colliding into the beat runway before the vowel triggers (`♦ +210ms Late`).
 *      - Clipped Vowels & Obliterated Pauses (Cluttering) with Guillotine Cut
 *        Markers (`|✂ Clipped -52%`) and steep leftward-diving orange tethers
 *        (`⏪ -180ms Rushed`).
 *      - Dedicated "Deviation & Energy Diff Strip" inside the Tether Gutter with
 *        explicit millisecond timing offsets & duration ratios on EVERY syllable.
 *      - Integrated One-Click Audio Audition Bar (Play Native Reference, Play
 *        Dysfluent/Learner Take, Toggle Raw Clock 0% vs. DTW 100%) with a real-time
 *        animated dual-track playhead cursor.
 *   2. Complementary Views:
 *      - `'prosogram_overlay'` (Melodics Overhang + Mertens' Prosogram Pitch Diff)
 *      - `'foot_budget_strips'` (Polak 100% Stress-Foot Budget Bars + nPVI Meter)
 *   3. Rich Diagnostic Coaching Cards (`renderCoachingSummary`) tailored to the
 *      active Vibe (`Presentation`, `Discussion`, `Argument`, `Storytelling`) and
 *      active Dysfluency Profile (`dysfluent_hesitation`, `dysfluent_stutter`,
 *      `syllable_timed_choppy`, `cluttered_runon`, `native_expressive`).
 * ============================================================================
 */
(function (global) {
  'use strict';

  // --------------------------------------------------------------------------
  // 1. MODE METADATA, PROFILE ALIASES & VIBE DEFINITIONS
  // --------------------------------------------------------------------------
  const PRIMARY_MODES = {
    vocalign_tether: {
      id: 'vocalign_tether',
      shortLabel: '1. VocAlign Elastic Tethers & Beat Bins (Flagship)',
      title: 'VocAlign Pro Elastic Tethers, Danielsen Beat Bins & Dysfluency Tear/Funnel Inspector',
      badge: 'FLAGSHIP · VocAlign Pro + Dysfluency Inspector',
      subtitle:
        'High-contrast Native Reference (top) vs. Dysfluent/Learner Track (bottom) linked by Elastic Warp Ribbons, Jagged Hesitation Tear Zones (⚡ 450ms BLOCK), 2.5× Prolongation Funnels (+140% Bloated), Stutter Echoes ([p-][p-]), Guillotine Cuts (|✂ -52%), and a Dedicated Millisecond Deviation Strip.'
    },
    prosogram_overlay: {
      id: 'prosogram_overlay',
      shortLabel: '2. Melodics Overhang + Prosogram Pitch Diff',
      title: "Melodics Overhang Overlay + Piet Mertens' Prosogram Pitch & Duration Stylization",
      badge: 'Melodics Overhang + Mertens Prosogram',
      subtitle:
        'Perceived pitch (semitones) & glissando slopes on Y-axis vs. Time on X-axis. Reveals how dysfluent speech flattens intonation into a monotone band and spills outside dashed Native Ghost Boxes with bold hatched overhang zones, hesitation dropouts, and guillotine gaps.'
    },
    foot_budget_strips: {
      id: 'foot_budget_strips',
      shortLabel: '3. Polak 100% Foot Budget Bars + nPVI Meter',
      title: 'Polak 100% Stress-Foot Budget Bars + Desain-Honing Rhythm Contrast & nPVI Gauge',
      badge: 'Polak 100% Foot Budget + nPVI Contrast',
      subtitle:
        'Normalizes each stress foot to 100% width so you immediately see how a prolonged schwa + mid-foot block ("theeee + [⚡ 450ms block]") devours 65% of the foot budget vs. 14% in native speech, paired with the nPVI Rhythm Contrast gauge.'
    }
  };

  const LEGACY_SPECTRAL_MODE = {
    id: 'spectral_tracker',
    shortLabel: '4. Serato 3-Band RGB + SD3 Stalks',
    title: 'Serato 3-Band RGB Spectral Waveform + Superior Drummer 3 Velocity Stalks',
    badge: 'Serato DJ RGB + SD3 Tracker',
    subtitle:
      'Cyan/Blue high-frequency consonant bursts vs. Red/Orange/Green vowel formant swells, with Primary Stress Threshold, Ghost Reduction Floor, and P-Center Lollipop Stalks.'
  };

  // Expose the 3 streamlined views as enumerable keys while keeping legacy keys accessible
  const MODES = Object.assign({}, PRIMARY_MODES);
  Object.defineProperty(MODES, 'tether_diff', {
    value: PRIMARY_MODES.vocalign_tether,
    enumerable: false,
    configurable: true
  });
  Object.defineProperty(MODES, 'ghost_prosogram', {
    value: PRIMARY_MODES.prosogram_overlay,
    enumerable: false,
    configurable: true
  });
  Object.defineProperty(MODES, 'foot_strips_simplex', {
    value: PRIMARY_MODES.foot_budget_strips,
    enumerable: false,
    configurable: true
  });
  Object.defineProperty(MODES, 'spectral_tracker', {
    value: LEGACY_SPECTRAL_MODE,
    enumerable: false,
    configurable: true
  });

  const MODE_ALIASES = {
    vocalign_tether: 'vocalign_tether',
    tether: 'vocalign_tether',
    tether_diff: 'vocalign_tether',
    prosogram_overlay: 'prosogram_overlay',
    prosogram: 'prosogram_overlay',
    ghost: 'prosogram_overlay',
    ghost_prosogram: 'prosogram_overlay',
    foot_budget_strips: 'foot_budget_strips',
    foot_budget: 'foot_budget_strips',
    strip: 'foot_budget_strips',
    simplex: 'foot_budget_strips',
    foot_strips_simplex: 'foot_budget_strips',
    spectral: 'spectral_tracker',
    spectral_tracker: 'spectral_tracker'
  };

  const PROFILE_METADATA = {
    dysfluent_hesitation: {
      id: 'dysfluent_hesitation',
      canonical: 'dysfluent_hesitation',
      shortLabel: 'Hesitation Block + Prolongation ("theeee... [⚡ 450ms uh...]")',
      badge: '⚡ MID-FOOT BLOCK + 2.5× PROLONGATION',
      color: '#f43f5e',
      speakingRate: 0.78
    },
    dysfluent_stutter: {
      id: 'dysfluent_stutter',
      canonical: 'dysfluent_stutter',
      shortLabel: 'Stutter / False-Start Repetitions ("[p-][p-]PROB" +210ms Late)',
      badge: '🔁 ONSET STUTTER [c-][c-] + CLUSTER LAG',
      color: '#c084fc',
      speakingRate: 0.82
    },
    syllable_timed_choppy: {
      id: 'syllable_timed_choppy',
      canonical: 'syllable_timed_choppy',
      shortLabel: 'L2 Syllable-Timed Choppy ("Robotic" +140% Bloated Schwas)',
      badge: '🤖 SYLLABLE-TIMED +140% SCHWA BLOAT',
      color: '#f59e0b',
      speakingRate: 0.84
    },
    cluttered_runon: {
      id: 'cluttered_runon',
      canonical: 'cluttered_runon',
      shortLabel: 'Cluttered Run-On (|✂ Clipped -52% Vowels + Obliterated Pause)',
      badge: '✂️ CLUTTERED GUILLOTINE CLIP + RUSHED PAUSE',
      color: '#fb923c',
      speakingRate: 1.14
    },
    native_expressive: {
      id: 'native_expressive',
      canonical: 'native_expressive',
      shortLabel: 'Native Expressive Reference (Beat-Bin Lock + Rubato Pocket)',
      badge: '✨ NATIVE EXPRESSIVE RUBATO (IN BEAT BIN)',
      color: '#10b981',
      speakingRate: 0.92
    },
    dilla_drag: {
      id: 'dilla_drag',
      canonical: 'native_expressive',
      shortLabel: 'Laid-Back Expressive Pocket (+55ms Neo-Soul Rubato)',
      badge: '✨ LAID-BACK POCKET RUBATO (+55ms)',
      color: '#a855f7',
      speakingRate: 0.94
    },
    live_recorded: {
      id: 'live_recorded',
      canonical: 'live_recorded',
      shortLabel: '🎤 Live Recorded / Tapped Take (Goal 2 Performance)',
      badge: '🎤 LIVE RECORDED TAKE',
      color: '#06b6d4',
      speakingRate: 0.95
    }
  };

  const PROFILE_ALIASES = {
    dysfluent_hesitation: 'dysfluent_hesitation',
    hesitation: 'dysfluent_hesitation',
    block: 'dysfluent_hesitation',
    dysfluent_stutter: 'dysfluent_stutter',
    stutter: 'dysfluent_stutter',
    syllable_timed_choppy: 'syllable_timed_choppy',
    syllable_timed: 'syllable_timed_choppy',
    choppy: 'syllable_timed_choppy',
    cluttered_runon: 'cluttered_runon',
    rushed_pause: 'cluttered_runon',
    cluttered: 'cluttered_runon',
    native_expressive: 'native_expressive',
    native_like: 'native_expressive',
    dilla_drag: 'dilla_drag',
    live_recorded: 'live_recorded'
  };

  const VIBE_PROFILES = {
    Presentation: {
      id: 'Presentation',
      label: 'Presentation (Keynote Authority & Executive Framing)',
      icon: '📊',
      accent: '#38bdf8',
      nativeTrait: 'Crisp 50ms schwa pickups, pre-beat consonant launch, and deliberate 1.6× nuclear vowel hold before syntactic pauses to project calm executive authority.',
      dysfluencyImpact: 'Mid-foot blocks or bloated schwas shatter keynote authority and make prepared takeaways sound uncertain or unscripted.'
    },
    Discussion: {
      id: 'Discussion',
      label: 'Discussion (Collaborative Turn-Taking & Pragmatic Flow)',
      icon: '💬',
      accent: '#10b981',
      nativeTrait: 'Coalesced function-word reductions ("whatcha", "tə ðə") paired with a clear rising/falling nuclear pitch glide that signals turn boundaries cleanly.',
      dysfluencyImpact: 'Abnormal pauses or clipped final vowels confuse interlocutors about whether you are holding the floor or yielding your turn.'
    },
    Argument: {
      id: 'Argument',
      label: 'Argument (Contrastive Focus & Persuasive Punch)',
      icon: '⚖️',
      accent: '#f59e0b',
      nativeTrait: 'Extreme durational and pitch contrast (nPVI > 60): ultra-compressed background syllables launch into heavy, locked P-center strikes on contrastive focus words.',
      dysfluencyImpact: 'Stuttering on initial plosives or giving equal syllable weight ("machine-gun timing") destroys contrastive focus and weakens persuasive punch.'
    },
    Storytelling: {
      id: 'Storytelling',
      label: 'Storytelling (Narrative Suspense & Expressive Rubato)',
      icon: '📖',
      accent: '#c084fc',
      nativeTrait: 'Elastic stress-foot wave with intentional expressive rubato (+40ms pocket drag on imagery words) while keeping unstressed connectors weightless.',
      dysfluencyImpact: 'Cluttered run-ons obliterate dramatic suspense pauses, while involuntary blocks break the listener’s narrative immersion.'
    }
  };

  // Track last render state & active playback animation for the One-Click Audition Bar
  let _lastRenderState = {
    targetEl: null,
    mode: 'vocalign_tether',
    phrase: null,
    learnerSyllables: null,
    normFactor: 1.0,
    profileKey: 'dysfluent_hesitation',
    vibe: null,
    coachingContainer: null,
    data: null
  };

  let _auditionState = {
    isPlaying: false,
    trackType: null, // 'native' | 'learner'
    rafId: null,
    timeoutId: null,
    startTimeMs: 0,
    durationMs: 3200,
    maxBeat: 4.8
  };

  // --------------------------------------------------------------------------
  // 2. DATA NORMALIZATION & HIGH-CONTRAST DYSFLUENCY SIMULATION
  // --------------------------------------------------------------------------
  function normalizeModeKey(mode) {
    return MODE_ALIASES[mode] || 'vocalign_tether';
  }

  function normalizeProfileKey(profileKey) {
    return PROFILE_ALIASES[profileKey] || 'dysfluent_hesitation';
  }

  function clamp(val, min, max) {
    return Math.max(min, Math.min(max, val));
  }

  function resolveVibe(phrase, explicitVibe) {
    if (explicitVibe && VIBE_PROFILES[explicitVibe]) {
      return VIBE_PROFILES[explicitVibe];
    }
    if (phrase && typeof phrase.vibe === 'string') {
      const match = Object.keys(VIBE_PROFILES).find(
        k => k.toLowerCase() === phrase.vibe.toLowerCase()
      );
      if (match) return VIBE_PROFILES[match];
    }
    const cat = (phrase && (phrase.category || phrase.title) || '').toLowerCase();
    if (cat.includes('present') || cat.includes('keynote') || cat.includes('conversational')) {
      return VIBE_PROFILES.Presentation;
    }
    if (cat.includes('discuss') || cat.includes('question') || cat.includes('pragmatic')) {
      return VIBE_PROFILES.Discussion;
    }
    if (cat.includes('argu') || cat.includes('rap') || cat.includes('contrast') || cat.includes('persua')) {
      return VIBE_PROFILES.Argument;
    }
    if (cat.includes('story') || cat.includes('poetic') || cat.includes('narrat')) {
      return VIBE_PROFILES.Storytelling;
    }
    const idx = phrase && typeof phrase.id === 'number' ? phrase.id : 0;
    const keys = ['Presentation', 'Discussion', 'Argument', 'Storytelling'];
    return VIBE_PROFILES[keys[Math.abs(idx) % keys.length]];
  }

  function resolvePhrase(phraseOrIdx) {
    const core = global.SpeechRhythmCore;
    if (phraseOrIdx && typeof phraseOrIdx === 'object' && Array.isArray(phraseOrIdx.syllables)) {
      return phraseOrIdx;
    }
    if (core && Array.isArray(core.PHRASES)) {
      const idx = typeof phraseOrIdx === 'number' ? phraseOrIdx : 0;
      return core.PHRASES[idx] || core.PHRASES[0];
    }
    return {
      id: 0,
      title: 'I was WALK-ing to the STR-EET... to WAIT',
      vibe: 'Presentation',
      category: 'Presentation & Conversational Stress-Timing',
      totalBeats: 4.0,
      defaultBpm: 88,
      syllables: [
        { id: 0, text: 'I', pre: '', preDur: 0.0, vowel: 'I', beat: 0.22, dur: 0.14, stress: 0.22, pitchST: -1.5, pitchSlope: 0, isGhost: true, isFinal: false, footId: 0 },
        { id: 1, text: 'was', pre: 'w', preDur: 0.04, vowel: 'as', beat: 0.42, dur: 0.13, stress: 0.16, pitchST: -2.0, pitchSlope: 0, isGhost: true, isFinal: false, footId: 0 },
        { id: 2, text: 'WALK-', pre: 'w', preDur: 0.06, vowel: 'ALK', beat: 0.68, dur: 0.36, stress: 0.88, pitchST: 3.0, pitchSlope: 1.5, isGhost: false, isFinal: false, footId: 1 },
        { id: 3, text: 'ing', pre: '', preDur: 0.0, vowel: 'ing', beat: 1.12, dur: 0.16, stress: 0.28, pitchST: 1.0, pitchSlope: 0, isGhost: true, isFinal: false, footId: 1 },
        { id: 4, text: 'to', pre: 't', preDur: 0.04, vowel: 'o', beat: 1.44, dur: 0.12, stress: 0.15, pitchST: -1.5, pitchSlope: 0, isGhost: true, isFinal: false, footId: 1 },
        { id: 5, text: 'the', pre: 'th', preDur: 0.04, vowel: 'e', beat: 1.64, dur: 0.12, stress: 0.15, pitchST: -2.0, pitchSlope: 0, isGhost: true, isFinal: false, footId: 1 },
        { id: 6, text: 'STR-EET...', pre: 'str', preDur: 0.14, vowel: 'EET', beat: 2.00, dur: 0.62, stress: 1.00, pitchST: 4.5, pitchSlope: -4.0, isGhost: false, isFinal: true, footId: 2 },
        { id: 7, text: 'to', pre: 't', preDur: 0.04, vowel: 'o', beat: 3.16, dur: 0.13, stress: 0.18, pitchST: -2.0, pitchSlope: 0, isGhost: true, isFinal: false, footId: 2 },
        { id: 8, text: 'WAIT', pre: 'w', preDur: 0.06, vowel: 'AIT', beat: 3.45, dur: 0.48, stress: 0.94, pitchST: 2.5, pitchSlope: -3.5, isGhost: false, isFinal: true, footId: 3 }
      ]
    };
  }

  /**
   * Builds prolonged display text for bloated function words (e.g. "the" -> "theeee...", "to" -> "toooo...")
   */
  function makeProlongedText(rawText) {
    const clean = (rawText || 'the').replace(/\.\.\./g, '').replace(/-/g, '');
    const lower = clean.toLowerCase();
    if (lower === 'the') return 'theeee...';
    if (lower === 'to') return 'toooo...';
    if (lower === 'was') return 'waaas...';
    if (lower === 'do') return 'doooo...';
    if (lower === 'you') return 'yooou...';
    if (lower === 'a') return 'aaaa...';
    if (lower === 'of') return 'oooof...';
    const lastChar = clean.charAt(clean.length - 1) || 'e';
    return `${clean}${lastChar.repeat(3)}...`;
  }

  /**
   * Builds stuttering prefix string (e.g. "[str-][str-]", "[p-][p-]", "[w-][w-]")
   */
  function makeStutterPrefix(nat) {
    const rawPre = (nat.pre || '').trim();
    if (rawPre.length > 0) {
      return `[${rawPre}-][${rawPre}-]`;
    }
    const clean = (nat.text || 'p').replace(/[^a-zA-Z]/g, '');
    const first = (clean.slice(0, 2) || 'p').toLowerCase();
    return `[${first}-][${first}-]`;
  }

  /**
   * Prepares comparative Native vs. Dysfluent/Learner syllable items with
   * unmistakable, high-contrast dysfluency callouts and DTW tempo normalization.
   */
  function prepareComparativeData(phraseInput, learnerSyllablesInput, profileKey = 'dysfluent_hesitation', normFactor = 1.0, explicitVibe = null) {
    const phrase = resolvePhrase(phraseInput);
    const core = global.SpeechRhythmCore;
    const nf = clamp(typeof normFactor === 'number' && !isNaN(normFactor) ? normFactor : 1.0, 0.0, 1.0);
    const resolvedProfileKey = normalizeProfileKey(profileKey);
    const profileMeta = PROFILE_METADATA[resolvedProfileKey] || PROFILE_METADATA.dysfluent_hesitation;
    const vibe = resolveVibe(phrase, explicitVibe);

    let rawLearnerList = learnerSyllablesInput;
    if (!Array.isArray(rawLearnerList) || rawLearnerList.length === 0) {
      if (core && typeof core.generateLearnerSyllables === 'function') {
        try {
          rawLearnerList = core.generateLearnerSyllables(phrase, profileKey, true);
        } catch (e) {
          rawLearnerList = null;
        }
      }
    }

    const nativeSyls = phrase.syllables || [];
    const bpm = phrase.defaultBpm || 88;
    const msPerBeat = Math.round(60000 / bpm); // ~682ms per beat at 88 BPM
    const globalRate =
      (Array.isArray(rawLearnerList) && rawLearnerList[0] && rawLearnerList[0].speakingRate) ||
      profileMeta.speakingRate ||
      0.84;

    // Identify key structural indices in the phrase so every dysfluency profile has vivid focal points
    let primaryNuclearIdx = nativeSyls.findIndex((s, i) => !s.isGhost && i >= 4 && (s.isFinal || (s.pre && s.pre.length >= 2) || s.stress >= 0.9));
    if (primaryNuclearIdx < 0) {
      primaryNuclearIdx = nativeSyls.findIndex((s, i) => !s.isGhost && i >= 2);
    }
    if (primaryNuclearIdx < 0) primaryNuclearIdx = Math.min(nativeSyls.length - 1, 2);

    // Find the function word immediately preceding `primaryNuclearIdx` for prolongation ("theeee...")
    let prolongedGhostIdx = primaryNuclearIdx > 0 && nativeSyls[primaryNuclearIdx - 1].isGhost
      ? primaryNuclearIdx - 1
      : nativeSyls.findIndex((s, i) => s.isGhost && i >= 1);

    // Find stressed syllables with consonant onsets for stuttering
    const stutterTargetIndices = new Set();
    nativeSyls.forEach((s, idx) => {
      if (!s.isGhost && ((s.pre && s.pre.length >= 1) || idx === primaryNuclearIdx)) {
        if (stutterTargetIndices.size < 2 && (idx === primaryNuclearIdx || idx >= 2)) {
          stutterTargetIndices.add(idx);
        }
      }
    });
    if (stutterTargetIndices.size === 0) stutterTargetIndices.add(primaryNuclearIdx);

    // Find mid-phrase final syllable or pause boundary for cluttering rush
    let midPauseIdx = nativeSyls.findIndex((s, i) => s.isFinal && i < nativeSyls.length - 1);
    if (midPauseIdx < 0) {
      // Find largest inter-syllable gap
      let maxGap = 0;
      nativeSyls.forEach((s, i) => {
        if (i < nativeSyls.length - 1) {
          const gap = nativeSyls[i + 1].beat - (s.beat + s.dur);
          if (gap > maxGap) {
            maxGap = gap;
            midPauseIdx = i;
          }
        }
      });
    }

    const items = nativeSyls.map((nat, idx) => {
      const lrn = Array.isArray(rawLearnerList) && rawLearnerList[idx] ? rawLearnerList[idx] : null;
      const preStr = nat.pre || '';
      const natPreBeats = typeof nat.preDur === 'number'
        ? nat.preDur
        : (preStr.length >= 3 ? 0.14 : preStr.length === 2 ? 0.09 : preStr.length === 1 ? 0.04 : 0.0);

      const natPitchST = typeof nat.pitchST === 'number' ? nat.pitchST : (nat.isGhost ? -1.5 : 3.5);
      const natPitchSlope = typeof nat.pitchSlope === 'number' ? nat.pitchSlope : (nat.isGhost ? 0 : -3.0);

      // Default values before profile-specific high-contrast dysfluency shaping
      let normBeat = nat.beat;
      let normDur = nat.dur;
      let lrnStress = nat.stress;
      let lrnPitchST = natPitchST;
      let lrnPitchSlope = natPitchSlope;
      let learnerText = nat.text;

      // High-contrast dysfluency flags
      let hasBlockBefore = Boolean(lrn && lrn.hasBlockBefore);
      let blockMs = (lrn && lrn.blockMs) || 0;
      let blockBeats = (lrn && lrn.blockBeats) || 0;
      let blockLabel = (lrn && lrn.blockLabel) || '';

      let isProlonged = Boolean(lrn && lrn.isProlonged);
      let bloatPct = (lrn && lrn.bloatPct) || 0;

      let isStuttered = Boolean(lrn && (lrn.isStuttered || lrn.stutterCount > 0));
      let stutterPrefix = (lrn && lrn.stutterPrefix) || '';
      let stutterCount = (lrn && lrn.stutterCount) || 0;

      let isClipped = Boolean(lrn && lrn.isClipped);
      let clippedPct = (lrn && lrn.clippedPct) || 0;
      let crashedPause = Boolean(lrn && lrn.crashedPause);

      let dysfluencyTag = (lrn && lrn.errorTag) || '';

      // Apply unmistakable profile-specific dysfluency patterns
      if (resolvedProfileKey === 'dysfluent_hesitation') {
        if (idx === prolongedGhostIdx) {
          // Dramatic 2.5x Abnormal Prolongation ("theeee...") before the block
          isProlonged = true;
          normDur = Number((nat.dur * 2.45).toFixed(3)); // +145% bloated!
          bloatPct = 145;
          normBeat = Math.max(0.04, nat.beat - 0.04);
          learnerText = makeProlongedText(nat.text);
          lrnStress = Math.min(0.78, nat.stress + 0.45);
          lrnPitchST = -0.3;
          lrnPitchSlope = 0;
          dysfluencyTag = '+145% Bloated Prolongation';
        } else if (idx === primaryNuclearIdx) {
          // Vivid 450ms Mid-Foot Hesitation Block ("[ ⚡ 450ms BLOCK / 'uh...' ]")
          hasBlockBefore = true;
          blockMs = 450;
          blockBeats = Number((blockMs / msPerBeat).toFixed(3)); // ~0.66 beats
          blockLabel = '[ ⚡ 450ms BLOCK / "uh..." ]';
          normBeat = Number((nat.beat + 0.47).toFixed(3)); // +320ms Late after the block!
          normDur = Number((nat.dur * 0.76).toFixed(3));
          lrnStress = Math.max(0.58, nat.stress - 0.18);
          lrnPitchST = Number((natPitchST * 0.38).toFixed(2));
          lrnPitchSlope = -0.4;
          dysfluencyTag = '⚡ +450ms Block → +320ms Late';
        } else if (idx > primaryNuclearIdx) {
          // Downstream syllables remain pushed right by the mid-foot block tear
          normBeat = Number((nat.beat + 0.42).toFixed(3));
          normDur = nat.isGhost ? Number((nat.dur * 1.65).toFixed(3)) : Number((nat.dur * 0.85).toFixed(3));
          if (nat.isGhost) {
            isProlonged = true;
            bloatPct = 65;
          }
          lrnPitchST = Number((natPitchST * 0.45).toFixed(2));
          lrnPitchSlope = 0;
          dysfluencyTag = 'Post-Block Cascade (+285ms Late)';
        } else if (nat.isGhost && idx > 0) {
          // Earlier ghost word mildly bloated (+110%)
          isProlonged = true;
          normDur = Number((nat.dur * 2.1).toFixed(3));
          bloatPct = 110;
          normBeat = Number((nat.beat + 0.04).toFixed(3));
          lrnStress = Math.min(0.62, nat.stress + 0.34);
          lrnPitchST = -0.5;
          lrnPitchSlope = 0;
          dysfluencyTag = '+110% Unreduced Schwa';
        } else {
          normBeat = Number((nat.beat + (idx >= 2 ? 0.06 : 0.01)).toFixed(3));
          normDur = Number((nat.dur * 0.92).toFixed(3));
          lrnPitchST = Number((natPitchST * 0.55).toFixed(2));
          lrnPitchSlope = Number((natPitchSlope * 0.3).toFixed(2));
        }
      } else if (resolvedProfileKey === 'dysfluent_stutter') {
        const priorStutters = Array.from(stutterTargetIndices).filter(i => i < idx).length;
        if (stutterTargetIndices.has(idx)) {
          isStuttered = true;
          stutterCount = idx === primaryNuclearIdx ? 3 : 2;
          stutterPrefix = makeStutterPrefix(nat);
          const lagBeats = idx === primaryNuclearIdx ? 0.34 : 0.28; // +210ms to +240ms Late
          normBeat = Number((nat.beat + lagBeats + priorStutters * 0.08).toFixed(3));
          normDur = Number((nat.dur * 0.82).toFixed(3));
          lrnStress = Math.min(1.0, nat.stress + 0.08); // Tense glottal attack
          lrnPitchST = Number((natPitchST * 0.48 + 0.8).toFixed(2));
          lrnPitchSlope = 0;
          if (idx === primaryNuclearIdx) {
            hasBlockBefore = true;
            blockMs = 230;
            blockBeats = 0.32;
            blockLabel = `⚡ Glottal Block + ${stutterPrefix}`;
          }
          dysfluencyTag = `${stutterPrefix} Stutter (+${Math.round(lagBeats * msPerBeat)}ms Late)`;
        } else {
          const shift = priorStutters * 0.16 + (nat.isGhost ? 0.05 : 0.02);
          normBeat = Number((nat.beat + shift).toFixed(3));
          normDur = nat.isGhost ? Number((nat.dur * 1.65).toFixed(3)) : Number((nat.dur * 0.9).toFixed(3));
          lrnPitchST = Number((natPitchST * 0.5).toFixed(2));
          lrnPitchSlope = 0;
          dysfluencyTag = shift > 0.12 ? `+${Math.round(shift * msPerBeat)}ms Stutter Drift` : 'Tense Delivery';
        }
      } else if (resolvedProfileKey === 'syllable_timed_choppy') {
        const isCluster = preStr.length >= 2 || natPreBeats >= 0.08;
        const earlyGhosts = nativeSyls.slice(0, idx).filter(s => s.isGhost).length;
        const clusterLag = isCluster ? 0.24 : (natPreBeats >= 0.05 ? 0.09 : 0.0);
        normBeat = Number((nat.beat + clusterLag + earlyGhosts * 0.045).toFixed(3));

        if (nat.isGhost) {
          isProlonged = true;
          normDur = Number((nat.dur * 2.4).toFixed(3)); // +140% Bloated!
          bloatPct = 140;
          if (idx === prolongedGhostIdx) {
            learnerText = makeProlongedText(nat.text);
          }
          lrnStress = Math.min(0.74, nat.stress + 0.42);
          lrnPitchST = 0.0;
          lrnPitchSlope = 0;
          dysfluencyTag = '+140% Bloated Schwa (2.4×)';
        } else {
          normDur = Number((nat.dur * (nat.isFinal ? 0.68 : 0.80)).toFixed(3));
          if (nat.isFinal) {
            isClipped = true;
            clippedPct = -32;
          }
          lrnStress = Math.max(0.62, nat.stress - 0.16);
          lrnPitchST = Number((natPitchST * 0.35).toFixed(2));
          lrnPitchSlope = 0;
          dysfluencyTag = isCluster
            ? `/${preStr}/ On-Beat Lag (+${Math.round(clusterLag * msPerBeat)}ms)`
            : 'Flat Monotone Stress';
        }
      } else if (resolvedProfileKey === 'cluttered_runon') {
        // Cluttered Run-On: Guillotine-clipped stressed/final vowels (-52%) & obliterated pause gates (-180ms to -240ms rushed)
        const afterPause = midPauseIdx >= 0 && idx > midPauseIdx;
        const rushBeats = afterPause ? -0.29 : (idx >= 3 ? -0.14 : -0.04); // -180ms to -200ms Rushed!
        normBeat = Number(Math.max(0.04, nat.beat + rushBeats).toFixed(3));

        if (nat.isFinal || (!nat.isGhost && nat.dur >= 0.34)) {
          isClipped = true;
          clippedPct = -52;
          normDur = Number((nat.dur * 0.48).toFixed(3)); // Chopped by 52%!
          lrnStress = Math.max(0.52, nat.stress - 0.24);
          lrnPitchST = Number((natPitchST * 0.55).toFixed(2));
          lrnPitchSlope = Number((natPitchSlope * 0.25).toFixed(2));
          dysfluencyTag = '|✂ Clipped -52% Vowel';
        } else {
          normDur = Number((nat.dur * 0.76).toFixed(3));
          lrnPitchST = Number((natPitchST * 0.65).toFixed(2));
          lrnPitchSlope = 0;
          dysfluencyTag = 'Telescoped Rush';
        }

        if (afterPause && idx === midPauseIdx + 1) {
          crashedPause = true;
          dysfluencyTag = '⏪ -195ms Rushed (Pause Obliterated!)';
        }
      } else if (resolvedProfileKey === 'native_expressive') {
        // Expressive Native / Dilla Rubato: stays inside the Beat Bin while showing clear, purposeful micro-timing
        const isDilla = profileKey === 'dilla_drag';
        const rubatoBeats = !nat.isGhost
          ? (isDilla ? 0.068 : (nat.isFinal ? 0.042 : 0.025))
          : -0.012;
        normBeat = Number(Math.max(0.03, nat.beat + rubatoBeats).toFixed(3));
        normDur = !nat.isGhost
          ? Number((nat.dur * (nat.isFinal ? 1.14 : 1.06)).toFixed(3))
          : Number((nat.dur * 0.88).toFixed(3));
        lrnStress = !nat.isGhost ? Math.min(1.0, nat.stress + 0.04) : Math.max(0.10, nat.stress - 0.03);
        lrnPitchST = natPitchST;
        lrnPitchSlope = natPitchSlope;
        dysfluencyTag = !nat.isGhost
          ? `♦ +${Math.round(rubatoBeats * msPerBeat)}ms Expressive Pocket`
          : '✓ Crisp Schwa Reduction';
      } else if (lrn) {
        // Live Recorded or custom passed syllables
        normBeat = typeof lrn.beat === 'number' ? lrn.beat : nat.beat;
        normDur = typeof lrn.dur === 'number' ? lrn.dur : nat.dur;
        lrnStress = typeof lrn.stress === 'number' ? lrn.stress : nat.stress;
        lrnPitchST = typeof lrn.pitchST === 'number' ? lrn.pitchST : natPitchST;
        lrnPitchSlope = typeof lrn.pitchSlope === 'number' ? lrn.pitchSlope : natPitchSlope;
      }

      const rawBeat = Number((normBeat / globalRate).toFixed(3));
      const rawDur = Number((normDur / globalRate).toFixed(3));

      // Interpolate between Raw Unnormalized Clock Time (0.0) and Full DTW Tempo-Normalized Time (1.0)
      const displayBeat = rawBeat * (1 - nf) + normBeat * nf;
      const displayDur = rawDur * (1 - nf) + normDur * nf;

      const dtwOffsetBeats = normBeat - nat.beat;
      const apparentOffsetBeats = displayBeat - nat.beat;
      const dtwMs = Math.round(dtwOffsetBeats * msPerBeat);
      const apparentMs = Math.round(apparentOffsetBeats * msPerBeat);
      const durRatio = displayDur / Math.max(0.04, nat.dur);
      const normDurRatio = normDur / Math.max(0.04, nat.dur);
      const durDiffPct = Math.round((durRatio - 1.0) * 100);
      const energyDiffPct = Math.round((lrnStress - nat.stress) * 100);

      // Classify status & visual callout category
      let trueStatus = 'ok';
      let errorType = 'in_pocket';

      if (hasBlockBefore) {
        trueStatus = 'block';
        errorType = 'hesitation_block';
      } else if (isStuttered) {
        trueStatus = 'late';
        errorType = 'stutter_collision';
      } else if (isProlonged || (nat.isGhost && normDurRatio >= 1.45)) {
        trueStatus = 'warn';
        errorType = 'bloated_schwa';
        isProlonged = true;
        if (!bloatPct) bloatPct = Math.max(60, Math.round((normDurRatio - 1) * 100));
      } else if (crashedPause || dtwOffsetBeats <= -0.14) {
        trueStatus = 'rushed';
        errorType = 'rushed_pause';
        crashedPause = true;
      } else if (isClipped || normDurRatio <= 0.65) {
        trueStatus = 'clipped';
        errorType = 'clipped_vowel';
        isClipped = true;
        if (!clippedPct) clippedPct = Math.round((normDurRatio - 1) * 100);
      } else if (dtwOffsetBeats >= 0.11) {
        trueStatus = 'late';
        errorType = (preStr.length >= 2 || natPreBeats >= 0.08) ? 'cluster_lag' : 'late_drag';
      } else if (Math.abs(dtwMs) >= 20) {
        trueStatus = 'rubato';
        errorType = 'expressive_rubato';
      }

      let effectiveStatus = trueStatus;
      let isFalseTempoCascade = false;
      if (nf < 0.65 && Math.abs(apparentOffsetBeats) > 0.12 && Math.abs(dtwOffsetBeats) <= 0.09) {
        effectiveStatus = apparentOffsetBeats > 0 ? 'late' : 'rushed';
        isFalseTempoCascade = true;
      }

      // Build explicit Deviation & Energy Diff Strip readout so NO difference is ever subtle
      let stripPrimary = '';
      let stripSecondary = '';
      let stripColor = '#10b981';
      let stripBg = 'rgba(16, 185, 129, 0.16)';

      if (hasBlockBefore) {
        stripPrimary = `⚡ +${blockMs}ms BLOCK`;
        stripSecondary = `${apparentMs >= 0 ? '+' : ''}${apparentMs}ms Late`;
        stripColor = '#fb7185';
        stripBg = 'rgba(244, 63, 94, 0.28)';
      } else if (isStuttered) {
        stripPrimary = `${stutterPrefix} STUTTER`;
        stripSecondary = `♦ +${Math.max(180, Math.abs(apparentMs))}ms Late`;
        stripColor = '#e879f9';
        stripBg = 'rgba(192, 132, 252, 0.28)';
      } else if (isProlonged) {
        stripPrimary = `+${bloatPct || Math.max(95, durDiffPct)}% Bloated`;
        stripSecondary = `${durRatio.toFixed(1)}× Schwa | +${Math.max(25, energyDiffPct)}% Loud`;
        stripColor = '#fbbf24';
        stripBg = 'rgba(245, 158, 11, 0.26)';
      } else if (crashedPause) {
        stripPrimary = `⏪ ${apparentMs}ms Rushed`;
        stripSecondary = `Pause Obliterated!`;
        stripColor = '#fb923c';
        stripBg = 'rgba(249, 115, 22, 0.28)';
      } else if (isClipped) {
        stripPrimary = `|✂ Clipped ${clippedPct}%`;
        stripSecondary = `${durRatio.toFixed(2)}× Dur (${apparentMs >= 0 ? '+' : ''}${apparentMs}ms)`;
        stripColor = '#f97316';
        stripBg = 'rgba(249, 115, 22, 0.25)';
      } else if (errorType === 'cluster_lag' || effectiveStatus === 'late') {
        stripPrimary = `${apparentMs >= 0 ? '+' : ''}${apparentMs}ms Late`;
        stripSecondary = preStr.length >= 2 ? `/${preStr}/ On-Beat Lag` : `${durRatio.toFixed(1)}× Dur`;
        stripColor = isFalseTempoCascade ? '#fb7185' : '#c084fc';
        stripBg = isFalseTempoCascade ? 'rgba(244, 63, 94, 0.24)' : 'rgba(192, 132, 252, 0.24)';
      } else if (errorType === 'expressive_rubato') {
        stripPrimary = `${apparentMs >= 0 ? '+' : ''}${apparentMs}ms Pocket`;
        stripSecondary = `${durRatio.toFixed(2)}× Rubato Hold`;
        stripColor = '#34d399';
        stripBg = 'rgba(16, 185, 129, 0.20)';
      } else {
        stripPrimary = `${apparentMs >= 0 ? '+' : ''}${apparentMs}ms Lock`;
        stripSecondary = `${durRatio.toFixed(2)}× (${energyDiffPct >= 0 ? '+' : ''}${energyDiffPct}% Eng)`;
        stripColor = '#38bdf8';
        stripBg = 'rgba(56, 189, 248, 0.16)';
      }

      return {
        ...nat,
        index: idx,
        learnerText,
        pre: preStr,
        natPreBeats,
        pitchST: natPitchST,
        pitchSlope: natPitchSlope,
        normBeat,
        rawBeat,
        normDur,
        rawDur,
        learnerBeat: displayBeat,
        learnerDur: displayDur,
        learnerStress: lrnStress,
        learnerPitchST: lrnPitchST,
        learnerPitchSlope: lrnPitchSlope,
        status: effectiveStatus,
        trueStatus,
        errorType,
        errorTag: dysfluencyTag,
        hasBlockBefore,
        blockMs,
        blockBeats,
        blockLabel,
        isProlonged,
        bloatPct: bloatPct || Math.max(0, durDiffPct),
        isStuttered,
        stutterPrefix,
        stutterCount,
        isClipped,
        clippedPct: clippedPct || Math.min(0, durDiffPct),
        crashedPause,
        isFalseTempoCascade,
        apparentMs,
        dtwMs,
        durRatio,
        durDiffPct,
        energyDiffPct,
        stripPrimary,
        stripSecondary,
        stripColor,
        stripBg
      };
    });

    const metrics = computeMetrics(phrase, items, nf, globalRate, resolvedProfileKey);

    return {
      phrase,
      items,
      profile: resolvedProfileKey,
      rawProfileKey: profileKey,
      profileMeta,
      vibe,
      normFactor: nf,
      globalRate,
      msPerBeat,
      metrics
    };
  }

  /**
   * Computes nPVI, Inter-Onset Intervals (IOIs), Beat-Bin hit accuracy,
   * and 3-interval Barycentric Simplex ratios (I1 : I2 : I3).
   */
  function computeMetrics(phrase, items, normFactor = 1.0, globalRate = 0.84, resolvedProfileKey = 'dysfluent_hesitation') {
    function calcNPVI(durs) {
      if (!durs || durs.length < 2) return 0;
      let sum = 0;
      for (let k = 0; k < durs.length - 1; k++) {
        const d1 = Math.max(0.01, durs[k]);
        const d2 = Math.max(0.01, durs[k + 1]);
        sum += Math.abs((d1 - d2) / ((d1 + d2) / 2));
      }
      return Math.round((100 * sum) / (durs.length - 1));
    }

    const nativeNPVI = Math.max(58, calcNPVI(items.map(s => s.dur)));
    let learnerNPVI = calcNPVI(items.map(s => s.learnerDur));
    if (resolvedProfileKey === 'syllable_timed_choppy') {
      learnerNPVI = Math.min(26, learnerNPVI);
    } else if (resolvedProfileKey === 'cluttered_runon') {
      learnerNPVI = Math.min(34, learnerNPVI);
    }

    const nativeIOIs = [];
    const learnerIOIs = [];
    for (let i = 0; i < items.length - 1; i++) {
      nativeIOIs.push(Math.max(0.06, items[i + 1].beat - items[i].beat));
      learnerIOIs.push(Math.max(0.06, items[i + 1].learnerBeat - items[i].learnerBeat));
    }

    let startIdx = items.findIndex((s, idx) => !s.isGhost && idx + 2 < items.length && items[idx + 1].isGhost);
    if (startIdx < 0) startIdx = items.findIndex((s, idx) => !s.isGhost && idx + 2 < items.length);
    if (startIdx < 0) startIdx = 0;

    const triItems = items.slice(startIdx, startIdx + 3);
    const triLabel = triItems.map(s => s.text.replace(/\.\.\./g, '').replace(/-/g, '')).join(' · ');

    const natTriRaw = triItems.map(s => s.dur);
    const natTriSum = natTriRaw.reduce((a, b) => a + b, 0) || 1;
    const natSimplex = natTriRaw.map(v => v / natTriSum);

    const lrnTriRaw = triItems.map(s => s.learnerDur + (s.hasBlockBefore ? s.blockBeats * 0.5 : 0));
    const lrnTriSum = lrnTriRaw.reduce((a, b) => a + b, 0) || 1;
    const lrnSimplex = lrnTriRaw.map(v => v / lrnTriSum);

    const tol = 0.095; // ±0.095 beats (~65ms) Danielsen Beat Bin
    const inBinCurrent = items.filter(s => Math.abs(s.learnerBeat - s.beat) <= tol && !s.hasBlockBefore && !s.isStuttered).length;
    const inBinNormalized = items.filter(s => Math.abs(s.normBeat - s.beat) <= tol && !s.hasBlockBefore && !s.isStuttered).length;

    const problemCount = items.filter(s => s.hasBlockBefore || s.isProlonged || s.isStuttered || s.isClipped || s.crashedPause || Math.abs(s.apparentMs) > 65).length;

    return {
      nativeNPVI,
      learnerNPVI,
      nativeIOIs,
      learnerIOIs,
      triLabel,
      natSimplex,
      lrnSimplex,
      inBinCurrent,
      inBinNormalized,
      problemCount,
      totalSyllables: items.length,
      globalRate,
      normFactor
    };
  }

  // --------------------------------------------------------------------------
  // 3. SHARED SVG COORDINATE & HIGH-CONTRAST PATTERN HELPERS
  // --------------------------------------------------------------------------
  function getMaxBeat(phrase, items) {
    const baseTotal = phrase && phrase.totalBeats ? phrase.totalBeats : 4.0;
    let maxB = baseTotal <= 4.2 ? 4.88 : 5.95;
    items.forEach(s => {
      const endB = Math.max(s.beat + s.dur, s.rawBeat + s.rawDur, s.learnerBeat + s.learnerDur);
      if (endB + 0.16 > maxB) maxB = Math.min(baseTotal * 1.38, endB + 0.16);
    });
    return maxB;
  }

  function makeBeatToX(maxBeat = 4.88, leftPad = 56, rightPad = 934) {
    const span = rightPad - leftPad;
    return function (beat) {
      return leftPad + (beat / maxBeat) * span;
    };
  }

  function buildSharedSvgDefs() {
    return `
      <defs>
        <!-- Pre-Beat Consonant Lead-In Hatch (///str) -->
        <pattern id="g1-hatch-consonant" width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
          <rect width="8" height="8" fill="rgba(245, 158, 11, 0.18)" />
          <line x1="0" y1="0" x2="0" y2="8" stroke="#f59e0b" stroke-width="2.4" stroke-opacity="0.78" />
        </pattern>
        <pattern id="g1-hatch-consonant-late" width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
          <rect width="8" height="8" fill="rgba(192, 132, 252, 0.28)" />
          <line x1="0" y1="0" x2="0" y2="8" stroke="#e879f9" stroke-width="2.6" stroke-opacity="0.9" />
        </pattern>
        <!-- Vivid Red/Rose Jagged Hesitation Block Hazard Pattern -->
        <pattern id="g1-hatch-block-tear" width="10" height="10" patternUnits="userSpaceOnUse" patternTransform="rotate(-45)">
          <rect width="10" height="10" fill="rgba(244, 63, 94, 0.30)" />
          <line x1="0" y1="0" x2="0" y2="10" stroke="#fb7185" stroke-width="3.2" stroke-opacity="0.92" />
        </pattern>
        <!-- Amber Funnel Prolongation Pattern (+140% Bloated) -->
        <pattern id="g1-hatch-overhang-amber" width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(-45)">
          <rect width="8" height="8" fill="rgba(245, 158, 11, 0.32)" />
          <line x1="0" y1="0" x2="0" y2="8" stroke="#fbbf24" stroke-width="2.8" stroke-opacity="0.95" />
        </pattern>
        <pattern id="g1-hatch-overhang-purple" width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(-45)">
          <rect width="8" height="8" fill="rgba(192, 132, 252, 0.30)" />
          <line x1="0" y1="0" x2="0" y2="8" stroke="#e879f9" stroke-width="2.8" stroke-opacity="0.92" />
        </pattern>
        <!-- Guillotine Clipped Vowel Missing Tail Pattern -->
        <pattern id="g1-hatch-clipped-gap" width="7" height="7" patternUnits="userSpaceOnUse" patternTransform="rotate(30)">
          <rect width="7" height="7" fill="rgba(249, 115, 22, 0.14)" />
          <line x1="0" y1="0" x2="0" y2="7" stroke="#fb923c" stroke-width="1.8" stroke-opacity="0.7" />
        </pattern>
        <!-- Danielsen Beat-Bin Gaussian Vertical Gradient -->
        <linearGradient id="g1-beatbin-grad" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stop-color="#10b981" stop-opacity="0.02" />
          <stop offset="25%" stop-color="#10b981" stop-opacity="0.16" />
          <stop offset="50%" stop-color="#10b981" stop-opacity="0.28" />
          <stop offset="75%" stop-color="#10b981" stop-opacity="0.16" />
          <stop offset="100%" stop-color="#10b981" stop-opacity="0.02" />
        </linearGradient>
        <!-- Amber Funnel Vertical Gradient -->
        <linearGradient id="g1-funnel-amber-grad" x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" stop-color="#f59e0b" stop-opacity="0.20" />
          <stop offset="100%" stop-color="#f59e0b" stop-opacity="0.48" />
        </linearGradient>
        <!-- Arrowhead markers -->
        <marker id="g1-arrow-cyan" viewBox="0 0 10 10" refX="7" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
          <path d="M 0 1 L 9 5 L 0 9 z" fill="#38bdf8" />
        </marker>
        <marker id="g1-arrow-amber" viewBox="0 0 10 10" refX="7" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
          <path d="M 0 1 L 9 5 L 0 9 z" fill="#fbbf24" />
        </marker>
        <marker id="g1-arrow-rose" viewBox="0 0 10 10" refX="7" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
          <path d="M 0 1 L 9 5 L 0 9 z" fill="#fb7185" />
        </marker>
        <marker id="g1-arrow-orange" viewBox="0 0 10 10" refX="7" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
          <path d="M 0 1 L 9 5 L 0 9 z" fill="#fb923c" />
        </marker>
        <marker id="g1-arrow-purple" viewBox="0 0 10 10" refX="7" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
          <path d="M 0 1 L 9 5 L 0 9 z" fill="#e879f9" />
        </marker>
      </defs>
    `;
  }

  /**
   * Renders the top status & active dysfluency banner inside the SVG, plus
   * interactive SVG audition triggers and the animated dual-track playhead overlay.
   */
  function renderTopDiagnosticHeaderSVG(data) {
    const { normFactor, globalRate, metrics, profileMeta, vibe } = data;
    const pct = Math.round(normFactor * 100);
    const isRaw = normFactor < 0.35;
    const normColor = isRaw ? '#f43f5e' : (normFactor < 0.85 ? '#f59e0b' : '#10b981');
    const normText = isRaw
      ? `RAW CLOCK (0% · ${globalRate.toFixed(2)}× Rate Drift Included)`
      : `DTW FOOT-NORMALIZED (${pct}% · Global ${globalRate.toFixed(2)}× Rate Factored Out)`;

    return `
      <g>
        <!-- Left: Active Vibe & Dysfluency Profile Pill -->
        <rect x="16" y="8" width="552" height="28" rx="7" fill="rgba(15, 23, 42, 0.95)" stroke="${profileMeta.color}" stroke-width="1.4" />
        <circle cx="30" cy="22" r="5" fill="${profileMeta.color}" />
        <text x="42" y="26" fill="#f8fafc" font-size="11" font-weight="800" font-family="ui-monospace, SFMono-Regular, monospace">
          ${vibe.icon} ${vibe.id.toUpperCase()} VIBE  |  ${profileMeta.badge}
        </text>

        <!-- Right: DTW Normalization & Beat-Bin Accuracy Status -->
        <rect x="576" y="8" width="368" height="28" rx="7" fill="rgba(15, 23, 42, 0.95)" stroke="${normColor}" stroke-width="1.3" />
        <circle cx="590" cy="22" r="4.5" fill="${normColor}" />
        <text x="601" y="26" fill="#e2e8f0" font-size="10.5" font-weight="700" font-family="ui-monospace, SFMono-Regular, monospace">
          ${normText} · Bin: ${metrics.inBinCurrent}/${metrics.totalSyllables}
        </text>
      </g>
    `;
  }

  /**
   * Builds the animated SVG playhead cursor group (`#g1-svg-playhead`) that sweeps
   * across both Native and Learner tracks when audio audition is triggered.
   */
  function renderAnimatedPlayheadSVG(viewBoxHeight = 430) {
    return `
      <g id="g1-svg-playhead" transform="translate(-40, 0)" style="opacity: 0; pointer-events: none; transition: opacity 0.12s;">
        <line x1="0" y1="42" x2="0" y2="${viewBoxHeight - 16}" stroke="#38bdf8" stroke-width="3" />
        <line x1="0" y1="42" x2="0" y2="${viewBoxHeight - 16}" stroke="#ffffff" stroke-width="1.2" stroke-dasharray="4 3" />
        <polygon points="-8,42 8,42 0,54" fill="#38bdf8" />
        <rect x="-48" y="22" width="96" height="18" rx="4" fill="#0284c7" stroke="#bae6fd" stroke-width="1" />
        <text id="g1-svg-playhead-label" x="0" y="34" text-anchor="middle" fill="#ffffff" font-size="9.5" font-family="monospace" font-weight="800">🔊 AUDITION</text>
      </g>
    `;
  }

  // --------------------------------------------------------------------------
  // 4. PRIMARY FLAGSHIP VIEW: 'vocalign_tether'
  //    VocAlign Pro Elastic Tethers, Dysfluency Callouts & Deviation Diff Strip
  // --------------------------------------------------------------------------
  function renderVocAlignTetherSVG(data) {
    const { phrase, items, normFactor, globalRate } = data;
    const maxBeat = getMaxBeat(phrase, items);
    const beatToX = makeBeatToX(maxBeat, 56, 934);
    const spanW = 934 - 56;

    const svgH = 440;
    let svg = buildSharedSvgDefs();
    svg += `<rect x="0" y="0" width="960" height="${svgH}" rx="10" fill="#070d19" />`;
    svg += renderTopDiagnosticHeaderSVG(data);

    // Track Vertical Layout:
    // 1) Native Reference Track: y = 44..134 (h = 90)
    // 2) Upper Elastic Tether Zone: y = 134..206 (h = 72)
    // 3) Dedicated Deviation & Energy Diff Strip: y = 206..256 (h = 50)
    // 4) Lower Elastic Tether Zone: y = 256..304 (h = 48)
    // 5) Dysfluent / Learner Utterance Track: y = 304..408 (h = 104)
    const natTrackY = 44;
    const natTrackH = 90;
    const gutterY = 134;
    const diffStripY = 204;
    const diffStripH = 48;
    const lrnTrackY = 298;
    const lrnTrackH = 108;
    const gutterH = lrnTrackY - gutterY;

    svg += `
      <!-- 1. Native Reference Track Box -->
      <rect x="16" y="${natTrackY}" width="928" height="${natTrackH}" rx="8" fill="rgba(15, 23, 42, 0.90)" stroke="rgba(56, 189, 248, 0.35)" stroke-width="1.3" />
      <text x="28" y="${natTrackY + 16}" fill="#38bdf8" font-size="11" font-weight="800" letter-spacing="0.4">
        NATIVE REFERENCE TRACK — Target P-Centers (♦), Pre-Beat Consonant Runways (///str), Crisp Schwa Ghosts &amp; Danielsen Beat Bins
      </text>

      <!-- 2. Alignment Tether Gutter & Dedicated Deviation Strip -->
      <rect x="16" y="${gutterY}" width="928" height="${gutterH}" fill="rgba(2, 6, 23, 0.78)" />
      <rect x="16" y="${diffStripY}" width="928" height="${diffStripH}" fill="rgba(15, 23, 42, 0.94)" stroke="rgba(148, 163, 184, 0.28)" stroke-width="1" />
      <text x="26" y="${gutterY + 14}" fill="#94a3b8" font-size="10" font-weight="800">
        VOCALIGN ELASTIC TETHER GUTTER — ⚡ Red Tear = Mid-Foot Block | / \\ Amber Funnel = +140% Bloated Schwa | [c-][c-] Purple = Stutter Lag | |✂ Orange = Clipped/Rushed
      </text>
      <text x="26" y="${diffStripY + 13}" fill="#38bdf8" font-size="9.5" font-weight="800" letter-spacing="0.5">
        DEDICATED MILLISECOND DEVIATION &amp; ENERGY DIFF STRIP (Explicit Timing Offset + Duration Ratio on Every Syllable):
      </text>

      <!-- 3. Learner / Dysfluent Track Box -->
      <rect x="16" y="${lrnTrackY}" width="928" height="${lrnTrackH}" rx="8" fill="rgba(15, 23, 42, 0.90)" stroke="rgba(244, 63, 94, 0.32)" stroke-width="1.3" />
      <text x="28" y="${lrnTrackY + 16}" fill="#f8fafc" font-size="11" font-weight="800" letter-spacing="0.4">
        DYSFLUENT / LEARNER UTTERANCE TRACK (${normFactor >= 0.85 ? 'DTW Foot-Normalized to 1.0× Frame' : normFactor <= 0.15 ? `Raw Unnormalized Clock @ ${globalRate.toFixed(2)}× Rate` : `DTW Normalization ${(normFactor * 100).toFixed(0)}%`})
      </text>
    `;

    // Beat Grid Lines (every 0.5 beats)
    for (let b = 0; b <= maxBeat; b += 0.5) {
      const gx = beatToX(b);
      const isIntBeat = Math.abs(b - Math.round(b)) < 0.01 && b >= 1 && b <= 5;
      svg += `
        <line x1="${gx}" y1="${natTrackY}" x2="${gx}" y2="${lrnTrackY + lrnTrackH}"
          stroke="${isIntBeat ? 'rgba(99, 102, 241, 0.34)' : 'rgba(148, 163, 184, 0.07)'}"
          stroke-width="${isIntBeat ? 1.5 : 1}"
          stroke-dasharray="${isIntBeat ? '4 3' : ''}" />
      `;
      if (isIntBeat) {
        svg += `<text x="${gx}" y="${lrnTrackY + lrnTrackH + 15}" text-anchor="middle" fill="#818cf8" font-size="10.5" font-family="monospace" font-weight="800">Beat ${Math.round(b)}.0</text>`;
      }
    }

    // Danielsen Shaded Beat Bins (Gaussian Tolerance Windows) around Stressed Native P-Centers
    items.forEach(s => {
      if (!s.isGhost) {
        const nx = beatToX(s.beat);
        const binHalfW = Math.max(19, (0.095 / maxBeat) * spanW);
        svg += `
          <rect x="${nx - binHalfW}" y="${natTrackY + 22}" width="${binHalfW * 2}" height="${natTrackH + gutterH + lrnTrackH - 26}" fill="url(#g1-beatbin-grad)" />
          <polygon points="${nx - binHalfW * 0.65},${natTrackY + 22} ${nx + binHalfW * 0.65},${natTrackY + 22} ${nx + binHalfW},${natTrackY + 35} ${nx - binHalfW},${natTrackY + 35}" fill="rgba(16, 185, 129, 0.28)" />
          <line x1="${nx}" y1="${natTrackY + 22}" x2="${nx}" y2="${lrnTrackY + lrnTrackH - 6}" stroke="#10b981" stroke-width="1.3" stroke-opacity="0.55" stroke-dasharray="3 2" />
          <text x="${nx}" y="${natTrackY + 32}" text-anchor="middle" fill="#34d399" font-size="8.5" font-weight="800">BEAT BIN</text>
        `;
      }
    });

    // Render Each Syllable: Native Capsule, Elastic Tether Ribbon, Deviation Strip Badge, and Learner Callout
    items.forEach((s, idx) => {
      const nx = beatToX(s.beat);
      const nw = Math.max(24, (s.dur / maxBeat) * spanW);
      const nPreW = s.natPreBeats > 0 ? Math.max(14, (s.natPreBeats / maxBeat) * spanW) : 0;

      const lx = beatToX(s.learnerBeat);
      const lw = Math.max(24, (s.learnerDur / maxBeat) * spanW);
      const lPreW = s.natPreBeats > 0 ? nPreW : 0;

      // Determine high-contrast colors & tether styling
      let strokeColor = '#10b981';
      let ribbonFill = 'rgba(16, 185, 129, 0.20)';
      let capsuleFill = 'rgba(16, 185, 129, 0.25)';

      if (s.hasBlockBefore) {
        strokeColor = '#f43f5e';
        ribbonFill = 'rgba(244, 63, 94, 0.28)';
        capsuleFill = 'rgba(244, 63, 94, 0.34)';
      } else if (s.isStuttered) {
        strokeColor = '#e879f9';
        ribbonFill = 'rgba(192, 132, 252, 0.28)';
        capsuleFill = 'rgba(192, 132, 252, 0.34)';
      } else if (s.isProlonged) {
        strokeColor = '#f59e0b';
        ribbonFill = 'url(#g1-funnel-amber-grad)';
        capsuleFill = 'url(#g1-hatch-overhang-amber)';
      } else if (s.crashedPause || s.isClipped) {
        strokeColor = '#fb923c';
        ribbonFill = 'rgba(249, 115, 22, 0.28)';
        capsuleFill = 'rgba(249, 115, 22, 0.32)';
      } else if (s.status === 'late') {
        strokeColor = '#c084fc';
        ribbonFill = 'rgba(192, 132, 252, 0.24)';
        capsuleFill = 'rgba(192, 132, 252, 0.28)';
      } else if (s.errorType === 'expressive_rubato') {
        strokeColor = '#34d399';
        ribbonFill = 'rgba(16, 185, 129, 0.22)';
        capsuleFill = 'rgba(16, 185, 129, 0.28)';
      }

      const natTop = s.isGhost ? natTrackY + 46 : natTrackY + 36;
      const natH = s.isGhost ? 28 : 42;
      const natBot = natTop + natH;

      const lrnTop = s.isGhost && !s.isProlonged ? lrnTrackY + 42 : lrnTrackY + 30;
      const lrnH = s.isGhost && !s.isProlonged ? 30 : 46;

      // ----------------------------------------------------------------------
      // A. SPECIAL CALLOUT 1: MID-FOOT HESITATION BLOCK (Red/Rose Jagged Tear Zone)
      // ----------------------------------------------------------------------
      if (s.hasBlockBefore) {
        const prevItem = idx > 0 ? items[idx - 1] : null;
        const tearStartX = prevItem
          ? Math.min(lx - 28, beatToX(prevItem.learnerBeat + prevItem.learnerDur) + 2)
          : Math.max(58, lx - 64);
        const tearEndX = Math.max(tearStartX + 38, lx - (s.isStuttered ? 26 : 4));
        const tearW = tearEndX - tearStartX;
        const tearMidX = tearStartX + tearW / 2;

        // Jagged tear polygon splitting the tether gutter & learner track
        const jagLeft = `
          ${tearStartX},${gutterY + 18}
          ${tearStartX + 6},${gutterY + 38}
          ${tearStartX - 4},${gutterY + 58}
          ${tearStartX + 5},${lrnTrackY}
          ${tearStartX - 3},${lrnTrackY + 35}
          ${tearStartX + 6},${lrnTrackY + 70}
          ${tearStartX},${lrnTrackY + lrnTrackH - 6}
        `.trim();
        const jagRight = `
          ${tearEndX},${lrnTrackY + lrnTrackH - 6}
          ${tearEndX - 6},${lrnTrackY + 70}
          ${tearEndX + 4},${lrnTrackY + 35}
          ${tearEndX - 5},${lrnTrackY}
          ${tearEndX + 4},${gutterY + 58}
          ${tearEndX - 6},${gutterY + 38}
          ${tearEndX},${gutterY + 18}
        `.trim();

        svg += `
          <!-- Jagged Red/Rose Hesitation Block Tear Zone -->
          <polygon points="${jagLeft} ${jagRight}" fill="url(#g1-hatch-block-tear)" stroke="#f43f5e" stroke-width="2.2" />
          <line x1="${tearStartX + 6}" y1="${gutterY + 44}" x2="${tearEndX - 6}" y2="${gutterY + 44}" stroke="#fb7185" stroke-width="2" marker-start="url(#g1-arrow-rose)" marker-end="url(#g1-arrow-rose)" />
          <rect x="${tearMidX - 66}" y="${lrnTrackY + 26}" width="132" height="22" rx="5" fill="#881337" stroke="#fb7185" stroke-width="1.6" />
          <text x="${tearMidX}" y="${lrnTrackY + 41}" text-anchor="middle" fill="#ffe4e6" font-size="9.5" font-family="monospace" font-weight="900">
            ⚡ ${s.blockMs}ms BLOCK / "uh..."
          </text>
          <text x="${tearMidX}" y="${gutterY + 36}" text-anchor="middle" fill="#fda4af" font-size="9" font-weight="800">
            TETHER SPLIT WIDE OPEN!
          </text>
        `;
      }

      // ----------------------------------------------------------------------
      // B. ELASTIC TETHER RIBBON (Top Gutter + Bottom Gutter around Diff Strip)
      // ----------------------------------------------------------------------
      svg += `
        <polygon points="${nx},${natBot} ${nx + nw},${natBot} ${lx + lw},${lrnTop} ${lx},${lrnTop}" fill="${ribbonFill}" />
        <line x1="${nx}" y1="${natBot}" x2="${lx}" y2="${lrnTop}" stroke="${strokeColor}" stroke-width="${s.isProlonged || s.hasBlockBefore || s.crashedPause ? 2.8 : 2.1}" />
        <line x1="${nx + nw}" y1="${natBot}" x2="${lx + lw}" y2="${lrnTop}" stroke="${strokeColor}" stroke-width="${s.isProlonged ? 2.6 : 1.5}" stroke-dasharray="${s.isProlonged ? '' : '4 2'}" />
      `;

      // ----------------------------------------------------------------------
      // C. SPECIAL CALLOUT 2: ABNORMAL PROLONGATION FUNNEL ("theeee..." +140% Bloated)
      // ----------------------------------------------------------------------
      if (s.isProlonged) {
        const funnelY = gutterY + 42;
        const funnelLeft = (nx + lx) / 2;
        const funnelRight = (nx + nw + lx + lw) / 2;
        const funnelCenter = (funnelLeft + funnelRight) / 2;
        if (funnelRight - funnelLeft > 26) {
          svg += `
            <line x1="${funnelLeft + 4}" y1="${funnelY}" x2="${funnelRight - 4}" y2="${funnelY}" stroke="#fbbf24" stroke-width="2.2" marker-start="url(#g1-arrow-amber)" marker-end="url(#g1-arrow-amber)" />
          `;
        }
        svg += `
          <rect x="${funnelCenter - 46}" y="${gutterY + 20}" width="92" height="17" rx="8" fill="#78350f" stroke="#fbbf24" stroke-width="1.4" />
          <text x="${funnelCenter}" y="${gutterY + 32}" text-anchor="middle" fill="#fef08a" font-size="9" font-family="monospace" font-weight="900">
            +${s.bloatPct}% Bloated (${s.durRatio.toFixed(1)}×)
          </text>
        `;
      }

      // ----------------------------------------------------------------------
      // D. SPECIAL CALLOUT 4B: OBLITERATED PAUSE GATE (Steep Leftward-Diving Orange Tether)
      // ----------------------------------------------------------------------
      if (s.crashedPause) {
        const crashX = (nx + lx) / 2;
        svg += `
          <line x1="${nx}" y1="${gutterY + 26}" x2="${lx + 6}" y2="${gutterY + 58}" stroke="#fb923c" stroke-width="2.6" marker-end="url(#g1-arrow-orange)" />
          <rect x="${crashX - 58}" y="${gutterY + 19}" width="116" height="17" rx="5" fill="#7c2d12" stroke="#fb923c" stroke-width="1.4" />
          <text x="${crashX}" y="${gutterY + 31}" text-anchor="middle" fill="#ffedd5" font-size="9" font-family="monospace" font-weight="900">
            ⏪ CRASHED PAUSE GATE
          </text>
        `;
      }

      // ----------------------------------------------------------------------
      // E. DEDICATED DEVIATION & ENERGY DIFF STRIP CELL (Inside Middle Gutter)
      // ----------------------------------------------------------------------
      const cellCenterX = clamp((nx + nw / 2 + lx + lw / 2) / 2, 54, 906);
      const cellW = Math.max(66, Math.min(104, Math.max(nw, lw) + 18));
      const staggerY = idx % 2 === 0 ? diffStripY + 15 : diffStripY + 19;

      svg += `
        <g>
          <rect x="${cellCenterX - cellW / 2}" y="${staggerY}" width="${cellW}" height="27" rx="5" fill="${s.stripBg}" stroke="${s.stripColor}" stroke-width="1.3" />
          <text x="${cellCenterX}" y="${staggerY + 11.5}" text-anchor="middle" fill="#ffffff" font-size="9" font-family="ui-monospace, SFMono-Regular, monospace" font-weight="900">
            ${s.stripPrimary}
          </text>
          <text x="${cellCenterX}" y="${staggerY + 22.5}" text-anchor="middle" fill="${s.stripColor}" font-size="8" font-family="ui-monospace, SFMono-Regular, monospace" font-weight="700">
            ${s.stripSecondary}
          </text>
        </g>
      `;

      // ----------------------------------------------------------------------
      // F. NATIVE REFERENCE SYLLABLE (Top Track)
      // ----------------------------------------------------------------------
      if (nPreW > 0) {
        svg += `
          <rect x="${nx - nPreW}" y="${natTop + 5}" width="${nPreW}" height="${natH - 10}" rx="4" fill="url(#g1-hatch-consonant)" stroke="#f59e0b" stroke-width="1.3" />
          <text x="${nx - nPreW / 2}" y="${natTop + natH / 2 + 3.5}" text-anchor="middle" fill="#fde68a" font-size="9" font-family="monospace" font-weight="800">${s.pre}</text>
        `;
      }
      svg += `
        <rect x="${nx}" y="${natTop}" width="${nw}" height="${natH}" rx="${s.isGhost ? 12 : 7}" fill="${s.isGhost ? 'rgba(56, 189, 248, 0.14)' : 'rgba(56, 189, 248, 0.28)'}" stroke="#38bdf8" stroke-width="${s.isGhost ? 1.4 : 2.2}" />
        <polygon points="${nx},${natTop - 5} ${nx + 5},${natTop} ${nx},${natTop + 5} ${nx - 5},${natTop}" fill="#38bdf8" />
        <text x="${nx + nw / 2}" y="${natTop + natH / 2 + 4}" text-anchor="middle" fill="#f8fafc" font-size="${s.isGhost ? 10.5 : 12}" font-weight="${s.isGhost ? 600 : 800}">${s.text}</text>
      `;

      // ----------------------------------------------------------------------
      // G. SPECIAL CALLOUT 3: STUTTER / FALSE-START REPETITIONS ([p-][p-]PROB)
      // ----------------------------------------------------------------------
      if (s.isStuttered) {
        const echoBoxW = 22;
        const echoCount = Math.min(3, Math.max(2, s.stutterCount || 2));
        const totalEchoW = echoCount * (echoBoxW + 3);
        const startEchoX = lx - totalEchoW - 2;
        const preToken = (s.pre || s.text.slice(0, 1) || 'p').toLowerCase() + '-';

        for (let k = 0; k < echoCount; k++) {
          const ex = startEchoX + k * (echoBoxW + 3);
          svg += `
            <rect x="${ex}" y="${lrnTop + 4}" width="${echoBoxW}" height="${lrnH - 8}" rx="4" fill="rgba(192, 132, 252, 0.32)" stroke="#e879f9" stroke-width="1.8" stroke-dasharray="3 1" />
            <text x="${ex + echoBoxW / 2}" y="${lrnTop + lrnH / 2 + 3.5}" text-anchor="middle" fill="#fae8ff" font-size="8.5" font-family="monospace" font-weight="900">[${preToken}]</text>
          `;
        }
        svg += `
          <rect x="${lx - totalEchoW / 2 - 44}" y="${lrnTop - 19}" width="88" height="15" rx="4" fill="#581c87" stroke="#e879f9" stroke-width="1.2" />
          <text x="${lx - totalEchoW / 2}" y="${lrnTop - 8.5}" text-anchor="middle" fill="#f5d0fe" font-size="8.5" font-family="monospace" font-weight="900">
            ${s.stutterPrefix} COLLISION!
          </text>
        `;
      } else if (lPreW > 0) {
        const isClusterLag = s.errorType === 'cluster_lag';
        svg += `
          <rect x="${lx - lPreW}" y="${lrnTop + 5}" width="${lPreW}" height="${lrnH - 10}" rx="4" fill="${isClusterLag ? 'url(#g1-hatch-consonant-late)' : 'url(#g1-hatch-consonant)'}" stroke="${isClusterLag ? '#e879f9' : '#f59e0b'}" stroke-width="1.5" />
          <text x="${lx - lPreW / 2}" y="${lrnTop + lrnH / 2 + 3.5}" text-anchor="middle" fill="${isClusterLag ? '#fae8ff' : '#fde68a'}" font-size="9" font-family="monospace" font-weight="800">${s.pre}</text>
        `;
        if (isClusterLag) {
          svg += `<text x="${lx - lPreW / 2}" y="${lrnTop - 6}" text-anchor="middle" fill="#e879f9" font-size="8.5" font-weight="900">/${s.pre}/ on beat!</text>`;
        }
      }

      // ----------------------------------------------------------------------
      // H. SPECIAL CALLOUT 4A: GUILLOTINE CUT MARKER (|✂ Clipped -52%)
      // ----------------------------------------------------------------------
      if (s.isClipped) {
        const fullNatW = Math.max(nw, lw * 1.9);
        const missingW = Math.max(18, fullNatW - lw);
        const cutX = lx + lw;
        svg += `
          <!-- Chopped-off missing vowel tail ghost box -->
          <rect x="${cutX}" y="${lrnTop + 2}" width="${missingW}" height="${lrnH - 4}" rx="5" fill="url(#g1-hatch-clipped-gap)" stroke="#fb923c" stroke-width="1.5" stroke-dasharray="3 2" />
          <!-- Guillotine Blade Vertical Cut Line -->
          <line x1="${cutX}" y1="${lrnTop - 10}" x2="${cutX}" y2="${lrnTop + lrnH + 10}" stroke="#f43f5e" stroke-width="3" />
          <rect x="${cutX - 4}" y="${lrnTop - 19}" width="84" height="15" rx="4" fill="#7c2d12" stroke="#fb923c" stroke-width="1.3" />
          <text x="${cutX + 38}" y="${lrnTop - 8.5}" text-anchor="middle" fill="#ffedd5" font-size="8.5" font-family="monospace" font-weight="900">
            |✂ Clipped ${s.clippedPct}%
          </text>
        `;
      }

      // ----------------------------------------------------------------------
      // I. LEARNER SYLLABLE BLOCK & BOTTOM CALLOUT PILL
      // ----------------------------------------------------------------------
      svg += `
        <rect x="${lx}" y="${lrnTop}" width="${lw}" height="${lrnH}" rx="${s.isGhost && !s.isProlonged ? 12 : 7}" fill="${capsuleFill}" stroke="${strokeColor}" stroke-width="${s.isProlonged || s.hasBlockBefore || s.isStuttered || s.isClipped ? 2.6 : 2.0}" />
        <polygon points="${lx},${lrnTop - 6} ${lx + 5.5},${lrnTop} ${lx},${lrnTop + 6} ${lx - 5.5},${lrnTop}" fill="${strokeColor}" />
        <text x="${lx + lw / 2}" y="${lrnTop + lrnH / 2 + 4}" text-anchor="middle" fill="#ffffff" font-size="${s.isProlonged ? 12 : (s.isGhost ? 10.5 : 12)}" font-weight="900">${s.learnerText}</text>
      `;

      // Bottom Track Callout Badge under every problem or anchor syllable
      const bottomCallout = s.hasBlockBefore
        ? `♦ +${Math.max(280, s.apparentMs)}ms Late`
        : s.isStuttered
        ? `♦ +${Math.max(210, s.apparentMs)}ms Late`
        : s.isProlonged
        ? `+${s.bloatPct}% Bloated`
        : s.isClipped
        ? `|✂ ${s.clippedPct}% Clipped`
        : s.crashedPause
        ? `⏪ ${s.apparentMs}ms Rushed`
        : `${s.apparentMs >= 0 ? '+' : ''}${s.apparentMs}ms`;

      svg += `
        <text x="${lx + lw / 2}" y="${lrnTrackY + lrnTrackH - 8}" text-anchor="middle" fill="${strokeColor}" font-size="9.5" font-family="ui-monospace, SFMono-Regular, monospace" font-weight="900">
          ${bottomCallout}
        </text>
      `;
    });

    svg += renderAnimatedPlayheadSVG(svgH);
    return svg;
  }

  // --------------------------------------------------------------------------
  // 5. SECONDARY VIEW 2: 'prosogram_overlay'
  //    Melodics Overhang Overlay + Mertens' Prosogram Pitch/Duration Stylization
  // --------------------------------------------------------------------------
  function renderProsogramOverlaySVG(data) {
    const { phrase, items } = data;
    const maxBeat = getMaxBeat(phrase, items);
    const beatToX = makeBeatToX(maxBeat, 66, 934);
    const spanW = 934 - 66;

    const svgH = 390;
    const plotTop = 46;
    const plotBot = 338;
    const plotH = plotBot - plotTop;

    function stToY(st) {
      const clamped = clamp(st, -4.5, 6.5);
      return plotTop + 26 + ((6.5 - clamped) / 11.0) * (plotH - 52);
    }

    let svg = buildSharedSvgDefs();
    svg += `<rect x="0" y="0" width="960" height="${svgH}" rx="10" fill="#070d19" />`;
    svg += renderTopDiagnosticHeaderSVG(data);

    svg += `<rect x="56" y="${plotTop}" width="888" height="${plotH}" rx="8" fill="rgba(15, 23, 42, 0.90)" stroke="rgba(148, 163, 184, 0.25)" />`;

    // Horizontal Semitone Grid Lines (-4, -2, 0, +2, +4, +6 ST)
    [-4, -2, 0, 2, 4, 6].forEach(st => {
      const y = stToY(st);
      const isZero = st === 0;
      svg += `
        <line x1="56" y1="${y}" x2="944" y2="${y}" stroke="${isZero ? 'rgba(56, 189, 248, 0.35)' : 'rgba(148, 163, 184, 0.10)'}" stroke-width="${isZero ? 1.6 : 1}" stroke-dasharray="${isZero ? '5 3' : ''}" />
        <text x="48" y="${y + 4}" text-anchor="end" fill="${isZero ? '#38bdf8' : '#94a3b8'}" font-size="10" font-family="monospace" font-weight="${isZero ? '800' : '600'}">${st > 0 ? `+${st}` : st} ST</text>
      `;
    });

    svg += `<text x="15" y="${plotTop + plotH / 2}" text-anchor="middle" fill="#94a3b8" font-size="10.5" font-weight="800" transform="rotate(-90 15 ${plotTop + plotH / 2})">PERCEIVED PITCH (Prosogram ST)</text>`;

    for (let b = 0; b <= maxBeat; b += 0.5) {
      const gx = beatToX(b);
      const isInt = Math.abs(b - Math.round(b)) < 0.01 && b >= 1 && b <= 5;
      svg += `<line x1="${gx}" y1="${plotTop}" x2="${gx}" y2="${plotBot}" stroke="${isInt ? 'rgba(99, 102, 241, 0.28)' : 'rgba(148, 163, 184, 0.06)'}" stroke-width="${isInt ? 1.4 : 1}" />`;
      if (isInt) {
        svg += `<text x="${gx}" y="${plotBot + 16}" text-anchor="middle" fill="#818cf8" font-size="10.5" font-family="monospace" font-weight="800">Beat ${Math.round(b)}.0</text>`;
      }
    }

    // Legend Row
    svg += `
      <g transform="translate(68, ${plotTop + 16})">
        <rect x="0" y="-10" width="18" height="11" rx="3" fill="rgba(56, 189, 248, 0.12)" stroke="#38bdf8" stroke-width="1.6" stroke-dasharray="3 2" />
        <text x="24" y="-1" fill="#38bdf8" font-size="10" font-weight="800">Native Ghost Box + Dynamic Glissando</text>

        <rect x="242" y="-10" width="18" height="11" rx="3" fill="url(#g1-hatch-overhang-amber)" stroke="#fbbf24" stroke-width="1.6" />
        <text x="266" y="-1" fill="#fbbf24" font-size="10" font-weight="800">Bloated Overhang Spill (+140%)</text>

        <rect x="458" y="-10" width="18" height="11" rx="3" fill="url(#g1-hatch-block-tear)" stroke="#f43f5e" stroke-width="1.6" />
        <text x="482" y="-1" fill="#fb7185" font-size="10" font-weight="800">⚡ Hesitation Pitch Void</text>

        <rect x="642" y="-10" width="18" height="11" rx="3" fill="url(#g1-hatch-clipped-gap)" stroke="#fb923c" stroke-width="1.5" stroke-dasharray="2 2" />
        <text x="666" y="-1" fill="#fdba74" font-size="10" font-weight="800">|✂ Clipped Guillotine Gap</text>
      </g>
    `;

    // Dotted Native Intonation Contour vs. Learner Flattened Contour
    const natContourPts = items.map(s => {
      const cx = beatToX(s.beat + s.dur / 2);
      const cy = stToY(s.pitchST + s.pitchSlope * 0.3);
      return `${cx.toFixed(1)},${cy.toFixed(1)}`;
    }).join(' ');
    const lrnContourPts = items.map(s => {
      const cx = beatToX(s.learnerBeat + s.learnerDur / 2);
      const cy = stToY(s.learnerPitchST + s.learnerPitchSlope * 0.3);
      return `${cx.toFixed(1)},${cy.toFixed(1)}`;
    }).join(' ');

    svg += `
      <polyline points="${natContourPts}" fill="none" stroke="rgba(56, 189, 248, 0.32)" stroke-width="2" stroke-dasharray="5 4" />
      <polyline points="${lrnContourPts}" fill="none" stroke="rgba(245, 158, 11, 0.45)" stroke-width="2" />
    `;

    items.forEach((s, idx) => {
      const nx = beatToX(s.beat);
      const nw = Math.max(26, (s.dur / maxBeat) * spanW);
      const lx = beatToX(s.learnerBeat);
      const lw = Math.max(26, (s.learnerDur / maxBeat) * spanW);

      const nPitchStart = s.pitchST;
      const nPitchEnd = s.pitchST + s.pitchSlope;
      const nyStart = stToY(nPitchStart);
      const nyEnd = stToY(nPitchEnd);
      const nBoxTop = Math.min(nyStart, nyEnd) - (s.isGhost ? 13 : 19);
      const nBoxH = Math.abs(nyEnd - nyStart) + (s.isGhost ? 26 : 38);

      const lPitchStart = s.learnerPitchST;
      const lPitchEnd = s.learnerPitchST + s.learnerPitchSlope;
      const lyStart = stToY(lPitchStart);
      const lyEnd = stToY(lPitchEnd);
      const lBoxTop = Math.min(lyStart, lyEnd) - (s.isGhost && !s.isProlonged ? 13 : 18);
      const lBoxH = Math.abs(lyEnd - lyStart) + (s.isGhost && !s.isProlonged ? 26 : 36);

      // Mid-Foot Hesitation Pitch Dropout Zone
      if (s.hasBlockBefore) {
        const prev = idx > 0 ? items[idx - 1] : null;
        const bx1 = prev ? Math.min(lx - 26, beatToX(prev.learnerBeat + prev.learnerDur) + 2) : lx - 50;
        const bw = Math.max(30, lx - bx1 - 4);
        svg += `
          <rect x="${bx1}" y="${plotTop + 28}" width="${bw}" height="${plotH - 42}" rx="6" fill="url(#g1-hatch-block-tear)" stroke="#f43f5e" stroke-width="1.8" />
          <text x="${bx1 + bw / 2}" y="${plotTop + plotH / 2}" text-anchor="middle" fill="#ffe4e6" font-size="9.5" font-family="monospace" font-weight="900">
            ⚡ ${s.blockMs}ms BLOCK
          </text>
        `;
      }

      const natRight = nx + nw;
      const lrnRight = lx + lw;

      // Empty Clipped Guillotine Gap
      if (s.isClipped || (lrnRight < natRight - 7 && lx <= natRight)) {
        const gapX = Math.max(nx, lrnRight);
        const gapW = Math.max(18, natRight - gapX);
        svg += `
          <rect x="${gapX}" y="${nBoxTop}" width="${gapW}" height="${nBoxH}" rx="5" fill="url(#g1-hatch-clipped-gap)" stroke="#fb923c" stroke-width="1.6" stroke-dasharray="3 2" />
          <text x="${gapX + gapW / 2}" y="${nBoxTop - 6}" text-anchor="middle" fill="#fdba74" font-size="9" font-family="monospace" font-weight="900">|✂ Clipped ${s.clippedPct || -50}%</text>
        `;
      }

      // Native Translucent Dashed Cyan Ghost Box + Mertens Glissando Ramp
      svg += `
        <rect x="${nx}" y="${nBoxTop}" width="${nw}" height="${nBoxH}" rx="7" fill="rgba(56, 189, 248, 0.09)" stroke="#38bdf8" stroke-width="1.8" stroke-dasharray="5 3" />
        <line x1="${nx + 4}" y1="${nyStart}" x2="${nx + nw - 4}" y2="${nyEnd}" stroke="#38bdf8" stroke-width="3.2" stroke-linecap="round" stroke-opacity="0.7" />
      `;

      const baseColor = s.hasBlockBefore
        ? '#f43f5e'
        : s.isStuttered
        ? '#e879f9'
        : s.isProlonged
        ? '#fbbf24'
        : s.isClipped || s.crashedPause
        ? '#fb923c'
        : s.status === 'late'
        ? '#c084fc'
        : '#10b981';

      const baseFill = s.isProlonged
        ? 'url(#g1-hatch-overhang-amber)'
        : s.isStuttered || s.status === 'late'
        ? 'rgba(192, 132, 252, 0.30)'
        : s.hasBlockBefore
        ? 'rgba(244, 63, 94, 0.34)'
        : s.isClipped || s.crashedPause
        ? 'rgba(249, 115, 22, 0.30)'
        : 'rgba(16, 185, 129, 0.30)';

      // Learner Solid Bar/Capsule
      svg += `<rect x="${lx}" y="${lBoxTop}" width="${lw}" height="${lBoxH}" rx="7" fill="${baseFill}" stroke="${baseColor}" stroke-width="2.2" />`;

      // Right Overhang Spill Zone
      if (lrnRight > natRight + 5) {
        const spillX = Math.max(lx, natRight);
        const spillW = lrnRight - spillX;
        const hatchId = s.status === 'late' || s.isStuttered ? 'url(#g1-hatch-overhang-purple)' : 'url(#g1-hatch-overhang-amber)';
        svg += `
          <rect x="${spillX}" y="${lBoxTop}" width="${spillW}" height="${lBoxH}" rx="5" fill="${hatchId}" stroke="${baseColor}" stroke-width="2.2" />
          <text x="${spillX + spillW / 2}" y="${lBoxTop + lBoxH + 14}" text-anchor="middle" fill="${baseColor}" font-size="9" font-family="monospace" font-weight="900">
            ${s.isProlonged ? `+${s.bloatPct}% Bloated Spill` : s.isStuttered ? `${s.stutterPrefix} Late` : `+${s.apparentMs}ms Spill`}
          </text>
        `;
      }

      // Left Overhang Spill Zone (Rushed Pause Crash)
      if (lx < nx - 5) {
        const spillW = Math.min(lw, nx - lx);
        svg += `
          <rect x="${lx}" y="${lBoxTop}" width="${spillW}" height="${lBoxH}" rx="5" fill="url(#g1-hatch-overhang-amber)" stroke="#fb923c" stroke-width="2.2" />
          <text x="${lx + spillW / 2}" y="${lBoxTop + lBoxH + 14}" text-anchor="middle" fill="#fb923c" font-size="9" font-family="monospace" font-weight="900">⏪ ${s.apparentMs}ms Rushed</text>
        `;
      }

      // Learner Prosogram Pitch Glissando Slope inside Capsule
      svg += `
        <line x1="${lx + 5}" y1="${lyStart}" x2="${lx + lw - 5}" y2="${lyEnd}" stroke="#ffffff" stroke-width="3.2" stroke-linecap="round" />
        <circle cx="${lx + 5}" cy="${lyStart}" r="3.5" fill="${baseColor}" stroke="#ffffff" stroke-width="1" />
        <text x="${lx + lw / 2}" y="${lBoxTop + lBoxH / 2 + 4}" text-anchor="middle" fill="#ffffff" font-size="11.5" font-weight="900">${s.learnerText}</text>
      `;
    });

    svg += `<text x="500" y="376" text-anchor="middle" fill="#94a3b8" font-size="10.5" font-weight="700">Horizontal = Time (Beats) | Vertical = Perceived Pitch (Semitones) &amp; Glissando Slope (Mertens Prosogram + Melodics Overhang Diff)</text>`;
    svg += renderAnimatedPlayheadSVG(svgH);
    return svg;
  }

  // --------------------------------------------------------------------------
  // 6. SECONDARY VIEW 3: 'foot_budget_strips'
  //    Polak 100% Stress-Foot Budget Bars + Rhythm Contrast & nPVI Gauge
  // --------------------------------------------------------------------------
  function renderFootBudgetStripsSVG(data) {
    const { phrase, items, profile, metrics } = data;
    const svgH = 405;
    let svg = buildSharedSvgDefs();
    svg += `<rect x="0" y="0" width="960" height="${svgH}" rx="10" fill="#070d19" />`;
    svg += renderTopDiagnosticHeaderSVG(data);

    // TOP HALF: Rainer Polak 100% Stress-Foot Budget Bars
    svg += `
      <rect x="16" y="44" width="928" height="172" rx="8" fill="rgba(15, 23, 42, 0.90)" stroke="rgba(148, 163, 184, 0.25)" />
      <text x="28" y="63" fill="#f8fafc" font-size="11.5" font-weight="800">
        POLAK 100% STRESS-FOOT BUDGET BARS — Shows How Bloated Schwas &amp; Mid-Foot Blocks Devour up to 65% of the Foot Budget vs. 14% in Native Speech
      </text>
    `;

    const feetList = buildFootBudgetSplits(phrase, items, profile);

    feetList.slice(0, 2).forEach((foot, idx) => {
      const colX = idx === 0 ? 28 : 492;
      const colW = 438;
      const stripX = colX + 56;
      const stripW = colW - 64;
      const baseY = 74;

      svg += `
        <rect x="${colX}" y="${baseY}" width="${colW}" height="130" rx="7" fill="rgba(2, 6, 23, 0.65)" stroke="rgba(99, 102, 241, 0.28)" />
        <text x="${colX + 10}" y="${baseY + 17}" fill="#818cf8" font-size="10.5" font-weight="800">${foot.name}</text>
        <text x="${colX + colW - 10}" y="${baseY + 17}" text-anchor="end" fill="#fbbf24" font-size="9.5" font-family="monospace" font-weight="800">${foot.budgetCallout}</text>
      `;

      // Native 100% Bar
      svg += `<text x="${colX + 10}" y="${baseY + 45}" fill="#38bdf8" font-size="10" font-weight="800">Native</text>`;
      let nx = stripX;
      const natCenters = [];
      foot.nativeSplits.forEach(sp => {
        const w = (sp.pct / 100) * stripW;
        natCenters.push({ x1: nx, x2: nx + w });
        const fill = sp.ghost ? 'rgba(56, 189, 248, 0.16)' : 'rgba(56, 189, 248, 0.38)';
        svg += `
          <rect x="${nx}" y="${baseY + 26}" width="${Math.max(18, w - 2)}" height="26" rx="4" fill="${fill}" stroke="#38bdf8" stroke-width="1.3" />
          <text x="${nx + w / 2}" y="${baseY + 43}" text-anchor="middle" fill="#f8fafc" font-size="9.5" font-weight="800">${sp.label} ${sp.pct}%</text>
        `;
        nx += w;
      });

      // Learner 100% Bar
      svg += `<text x="${colX + 10}" y="${baseY + 104}" fill="#f8fafc" font-size="10" font-weight="800">Learner</text>`;
      let lx = stripX;
      foot.learnerSplits.forEach((sp, sIdx) => {
        const w = (sp.pct / 100) * stripW;
        const stroke = sp.isBlock
          ? '#f43f5e'
          : sp.status === 'ok' || sp.status === 'rubato'
          ? '#10b981'
          : sp.status === 'late'
          ? '#e879f9'
          : '#f59e0b';
        const fill = sp.isBlock
          ? 'url(#g1-hatch-block-tear)'
          : sp.isBloated
          ? 'url(#g1-hatch-overhang-amber)'
          : sp.status === 'ok' || sp.status === 'rubato'
          ? 'rgba(16, 185, 129, 0.28)'
          : sp.status === 'late'
          ? 'rgba(192, 132, 252, 0.30)'
          : 'rgba(249, 115, 22, 0.30)';

        const natRef = natCenters[Math.min(sIdx, natCenters.length - 1)];
        if (natRef) {
          svg += `
            <polygon points="${natRef.x1},${baseY + 52} ${natRef.x2},${baseY + 52} ${lx + w},${baseY + 86} ${lx},${baseY + 86}" fill="${stroke}" fill-opacity="0.18" />
            <line x1="${natRef.x2}" y1="${baseY + 52}" x2="${lx + w}" y2="${baseY + 86}" stroke="${stroke}" stroke-width="1.4" stroke-dasharray="2 2" />
          `;
        }

        svg += `
          <rect x="${lx}" y="${baseY + 86}" width="${Math.max(18, w - 2)}" height="30" rx="4" fill="${fill}" stroke="${stroke}" stroke-width="2" />
          <text x="${lx + w / 2}" y="${baseY + 105}" text-anchor="middle" fill="#ffffff" font-size="9.5" font-weight="900">${sp.label} ${sp.pct}%</text>
        `;
        lx += w;
      });
    });

    // BOTTOM HALF (LEFT): Desain & Honing Chronotopological Simplex Triangle
    svg += `
      <rect x="16" y="224" width="456" height="170" rx="8" fill="rgba(15, 23, 42, 0.90)" stroke="rgba(148, 163, 184, 0.25)" />
      <text x="28" y="242" fill="#f8fafc" font-size="11" font-weight="800">DESAIN &amp; HONING CHRONOTOPOLOGICAL SIMPLEX (${metrics.triLabel})</text>
      <text x="28" y="255" fill="#94a3b8" font-size="9.5">Barycentric 3-Interval Ratio Space (I₁ : I₂ : I₃) — Machine-Gun 1:1:1 Center vs. Stress-Timed 2:1:1</text>
    `;

    const V1 = { x: 218, y: 268 };
    const V2 = { x: 126, y: 378 };
    const V3 = { x: 310, y: 378 };

    function baryToXY(p1, p2, p3) {
      return {
        x: p1 * V1.x + p2 * V2.x + p3 * V3.x,
        y: p1 * V1.y + p2 * V2.y + p3 * V3.y
      };
    }

    const center111 = baryToXY(1 / 3, 1 / 3, 1 / 3);
    const native211 = baryToXY(0.56, 0.22, 0.22);
    const natPt = baryToXY(metrics.natSimplex[0], metrics.natSimplex[1], metrics.natSimplex[2]);
    const lrnPt = baryToXY(metrics.lrnSimplex[0], metrics.lrnSimplex[1], metrics.lrnSimplex[2]);

    svg += `
      <polygon points="${V1.x},${V1.y} ${V2.x},${V2.y} ${V3.x},${V3.y}" fill="rgba(2, 6, 23, 0.75)" stroke="#64748b" stroke-width="1.6" />
      <circle cx="${center111.x}" cy="${center111.y}" r="16" fill="rgba(245, 158, 11, 0.16)" stroke="#f59e0b" stroke-dasharray="3 2" />
      <text x="${center111.x + 20}" y="${center111.y + 4}" fill="#fbbf24" font-size="9" font-weight="800">1:1:1 Flat</text>

      <ellipse cx="${native211.x}" cy="${native211.y}" rx="20" ry="12" fill="rgba(56, 189, 248, 0.16)" stroke="#38bdf8" stroke-dasharray="3 2" />
      <text x="${native211.x - 23}" y="${native211.y - 3}" text-anchor="end" fill="#38bdf8" font-size="9" font-weight="800">2:1:1 Pocket</text>

      <line x1="${lrnPt.x}" y1="${lrnPt.y}" x2="${natPt.x}" y2="${natPt.y}" stroke="#f59e0b" stroke-width="2.2" marker-end="url(#g1-arrow-cyan)" />
      <circle cx="${natPt.x}" cy="${natPt.y}" r="6" fill="#38bdf8" stroke="#0f172a" stroke-width="1.5" />
      <circle cx="${lrnPt.x}" cy="${lrnPt.y}" r="6.5" fill="${profile === 'native_expressive' ? '#10b981' : '#f43f5e'}" stroke="#ffffff" stroke-width="1.5" />
    `;

    const nRatioStr = metrics.natSimplex.map(v => Math.round(v * 100) + '%').join(' : ');
    const lRatioStr = metrics.lrnSimplex.map(v => Math.round(v * 100) + '%').join(' : ');
    svg += `
      <g transform="translate(326, 274)">
        <rect x="0" y="0" width="132" height="96" rx="6" fill="rgba(2, 6, 23, 0.72)" stroke="rgba(148,163,184,0.22)" />
        <circle cx="12" cy="18" r="4.5" fill="#38bdf8" />
        <text x="22" y="21" fill="#38bdf8" font-size="10" font-weight="800">Native Triplet</text>
        <text x="12" y="37" fill="#f8fafc" font-size="10" font-family="monospace" font-weight="800">${nRatioStr}</text>

        <circle cx="12" cy="58" r="4.5" fill="${profile === 'native_expressive' ? '#10b981' : '#f43f5e'}" />
        <text x="22" y="61" fill="#fbbf24" font-size="10" font-weight="800">Learner Triplet</text>
        <text x="12" y="77" fill="#ffffff" font-size="10" font-family="monospace" font-weight="800">${lRatioStr}</text>
      </g>
    `;

    // BOTTOM HALF (RIGHT): High-Contrast nPVI Rhythm Contrast Gauge & Foot Theft Summary
    const natNPVI = metrics.nativeNPVI;
    const lrnNPVI = metrics.learnerNPVI;
    const lrnGaugeColor = lrnNPVI >= 48 ? '#10b981' : (lrnNPVI >= 34 ? '#f59e0b' : '#f43f5e');

    svg += `
      <rect x="484" y="224" width="460" height="170" rx="8" fill="rgba(15, 23, 42, 0.90)" stroke="rgba(148, 163, 184, 0.25)" />
      <text x="500" y="242" fill="#f8fafc" font-size="11" font-weight="800">nPVI RHYTHM CONTRAST METER &amp; FOOT BUDGET DIAGNOSTIC</text>
      <text x="500" y="255" fill="#94a3b8" font-size="9.5">Pairwise Durational Contrast (0–30 = Robotic/Flat | 55–75 = Native Stress-Timed Alternation)</text>

      <g transform="translate(500, 266)">
        <text x="0" y="14" fill="#38bdf8" font-size="10.5" font-weight="800">Native Stress-Timed Reference</text>
        <text x="426" y="14" text-anchor="end" fill="#38bdf8" font-size="11.5" font-family="monospace" font-weight="900">nPVI = ${natNPVI} (High Contrast)</text>
        <rect x="0" y="20" width="426" height="14" rx="7" fill="rgba(51, 65, 85, 0.65)" />
        <rect x="0" y="20" width="${clamp((natNPVI / 85) * 426, 20, 426)}" height="14" rx="7" fill="#38bdf8" />

        <text x="0" y="54" fill="#f8fafc" font-size="10.5" font-weight="800">Selected Dysfluent / Learner Profile</text>
        <text x="426" y="54" text-anchor="end" fill="${lrnGaugeColor}" font-size="11.5" font-family="monospace" font-weight="900">nPVI = ${lrnNPVI} (${lrnNPVI < 36 ? 'Collapsed Contrast' : 'Expressive Contrast'})</text>
        <rect x="0" y="60" width="426" height="14" rx="7" fill="rgba(51, 65, 85, 0.65)" />
        <rect x="0" y="60" width="${clamp((lrnNPVI / 85) * 426, 20, 426)}" height="14" rx="7" fill="${lrnGaugeColor}" />

        <rect x="0" y="84" width="426" height="32" rx="6" fill="rgba(2, 6, 23, 0.78)" stroke="${lrnGaugeColor}" stroke-width="1.2" />
        <text x="12" y="104" fill="#f8fafc" font-size="10" font-family="monospace" font-weight="800">
          ${profile === 'dysfluent_hesitation'
            ? '⚡ FOOT THEFT: "theeee... + [450ms block]" devours 65% of Foot 1 budget vs. 14% Native!'
            : profile === 'dysfluent_stutter'
            ? '🔁 STUTTER THEFT: "[c-][c-]" false-start repetitions consume 38% of foot onset runway!'
            : profile === 'syllable_timed_choppy'
            ? '🤖 SCHWA BLOAT: Unreduced function words eat 58% of foot budget (target: 24%)!'
            : profile === 'cluttered_runon'
            ? '✂️ CLUTTERED CLIP: Stressed vowel chopped -52%, collapsing phrase-final foot hold!'
            : '✨ NATIVE LOCK: Stressed vowels hold 72% of foot budget; schwas compress to 14%!'}
        </text>
      </g>
    `;

    svg += renderAnimatedPlayheadSVG(svgH);
    return svg;
  }

  /**
   * Builds 100% Normalized Stress-Foot Budget Splits for `'foot_budget_strips'`,
   * explicitly highlighting how `"theeee + [block]"` eats 65% of the foot budget vs. 14% in native speech.
   */
  function buildFootBudgetSplits(phrase, items, profile) {
    const footMap = new Map();
    items.forEach(s => {
      const fid = typeof s.footId === 'number' ? s.footId : 1;
      if (!footMap.has(fid)) footMap.set(fid, []);
      footMap.get(fid).push(s);
    });

    const candidateFeet = Array.from(footMap.entries())
      .filter(([, grp]) => grp.length >= 2)
      .slice(0, 2);

    if (candidateFeet.length === 0) {
      candidateFeet.push([1, items.slice(0, Math.min(4, items.length))]);
    }

    return candidateFeet.map(([fid, grp], fIdx) => {
      const footMeta = (phrase && Array.isArray(phrase.feet) && phrase.feet.find(f => f.footId === fid)) || null;
      const footTitle = footMeta && footMeta.label
        ? footMeta.label
        : `Foot ${fid}: '${grp.map(s => s.text.replace(/\.\.\./g, '')).join(' ')}'`;

      const natSum = grp.reduce((acc, s) => acc + s.dur, 0) || 1;
      const natPcts = grp.map(s => Math.max(10, Math.round((s.dur / natSum) * 100)));
      // Ensure last ghost syllable in Foot 1 shows ~14% in native speech
      if (fIdx === 0 && grp.length >= 3 && grp[grp.length - 1].isGhost) {
        natPcts[grp.length - 1] = 14;
      }
      const natDiff = 100 - natPcts.reduce((a, b) => a + b, 0);
      natPcts[0] = Math.max(15, natPcts[0] + natDiff);

      const nativeSplits = grp.map((s, i) => ({
        label: s.text.replace(/\.\.\./g, '').replace(/-/g, ''),
        pct: natPcts[i],
        ghost: s.isGhost
      }));

      // Build Learner 100% Foot Budget Splits
      if (profile === 'dysfluent_hesitation' && fIdx === 0) {
        // Explicitly show "theeee + [block]" eating 65% of the foot budget vs. 14% in native speech!
        const headLabel = grp[0].text.replace(/\.\.\./g, '').replace(/-/g, '');
        const midLabel = grp.length > 2 ? grp[1].text.replace(/\.\.\./g, '').replace(/-/g, '') : 'to';
        const lastGhost = grp[grp.length - 1];
        const prolLabel = makeProlongedText(lastGhost.text).replace(/\.\.\./g, '');
        return {
          name: footTitle,
          budgetCallout: `"${prolLabel} + [block]" = 65% vs. 14% Native!`,
          nativeSplits,
          learnerSplits: [
            { label: headLabel, pct: 22, status: 'warn' },
            { label: midLabel, pct: 13, status: 'warn' },
            { label: `${prolLabel} + [⚡block]`, pct: 65, status: 'block', isBlock: true, isBloated: true }
          ]
        };
      }

      const lrnRaw = grp.map(s => s.learnerDur + (s.hasBlockBefore ? s.blockBeats * 0.7 : 0) + (s.isStuttered ? 0.18 : 0));
      const lrnSum = lrnRaw.reduce((a, b) => a + b, 0) || 1;
      const lrnPcts = lrnRaw.map(v => Math.max(10, Math.round((v / lrnSum) * 100)));
      const lrnDiff = 100 - lrnPcts.reduce((a, b) => a + b, 0);
      lrnPcts[lrnPcts.length - 1] = Math.max(10, lrnPcts[lrnPcts.length - 1] + lrnDiff);

      const ghostBudgetNat = nativeSplits.filter(sp => sp.ghost).reduce((a, b) => a + b.pct, 0);
      const ghostBudgetLrn = grp.reduce((acc, s, i) => acc + (s.isGhost ? lrnPcts[i] : 0), 0);

      return {
        name: footTitle,
        budgetCallout: ghostBudgetLrn > ghostBudgetNat + 12
          ? `Schwas eat ${ghostBudgetLrn}% vs. ${ghostBudgetNat}% Native`
          : profile === 'cluttered_runon'
          ? `Clipped Stress (-52%)`
          : `Foot Ratio Locked`,
        nativeSplits,
        learnerSplits: grp.map((s, i) => ({
          label: s.isStuttered
            ? `${s.stutterPrefix}${s.text.replace(/\.\.\./g, '').replace(/-/g, '')}`
            : s.isProlonged
            ? s.learnerText.replace(/\.\.\./g, '')
            : s.isClipped
            ? `|✂${s.text.replace(/\.\.\./g, '').replace(/-/g, '')}`
            : s.text.replace(/\.\.\./g, '').replace(/-/g, ''),
          pct: lrnPcts[i],
          status: s.status || 'ok',
          isBlock: s.hasBlockBefore,
          isBloated: s.isProlonged
        }))
      };
    });
  }

  // --------------------------------------------------------------------------
  // 7. LEGACY MODE 4 SUPPORT: 'spectral_tracker'
  // --------------------------------------------------------------------------
  function renderSpectralTrackerSVG(data) {
    const { phrase, items } = data;
    const maxBeat = getMaxBeat(phrase, items);
    const beatToX = makeBeatToX(maxBeat, 64, 932);
    const spanW = 932 - 64;
    const svgH = 380;

    let svg = buildSharedSvgDefs();
    svg += `<rect x="0" y="0" width="960" height="${svgH}" rx="10" fill="#070d19" />`;
    svg += renderTopDiagnosticHeaderSVG(data);

    const lanes = [
      { title: 'NATIVE REFERENCE — Serato 3-Band RGB Waveform + SD3 P-Center Velocity Stalks', topY: 46, height: 146, isLearner: false },
      { title: 'DYSFLUENT / LEARNER TRACK — Bloated Schwas Punch Above Ghost Floor & Blocks Drop Energy to Zero', topY: 204, height: 152, isLearner: true }
    ];

    lanes.forEach(lane => {
      const { topY, height, isLearner, title } = lane;
      const baseY = topY + height - 22;
      const maxAmpH = height - 48;
      const primaryStressY = baseY - maxAmpH * 0.72;
      const ghostFloorY = baseY - maxAmpH * 0.34;

      svg += `
        <rect x="16" y="${topY}" width="928" height="${height}" rx="8" fill="rgba(15, 23, 42, 0.90)" stroke="rgba(148, 163, 184, 0.24)" />
        <text x="28" y="${topY + 16}" fill="${isLearner ? '#f8fafc' : '#38bdf8'}" font-size="11" font-weight="800">${title}</text>
        <line x1="58" y1="${primaryStressY}" x2="934" y2="${primaryStressY}" stroke="#10b981" stroke-width="1.3" stroke-dasharray="5 3" />
        <line x1="58" y1="${ghostFloorY}" x2="934" y2="${ghostFloorY}" stroke="#f59e0b" stroke-width="1.3" stroke-dasharray="3 3" />
        <line x1="58" y1="${baseY}" x2="934" y2="${baseY}" stroke="rgba(148, 163, 184, 0.35)" stroke-width="1" />
      `;

      items.forEach(s => {
        const beat = isLearner ? s.learnerBeat : s.beat;
        const dur = isLearner ? s.learnerDur : s.dur;
        const energy = isLearner ? s.learnerStress : s.stress;
        const pCenterX = beatToX(beat);
        const vowelW = Math.max(22, (dur / maxBeat) * spanW);
        const stalkTopY = baseY - energy * maxAmpH;
        const stalkColor = !isLearner
          ? (s.isGhost ? '#38bdf8' : '#10b981')
          : s.hasBlockBefore
          ? '#f43f5e'
          : s.isProlonged
          ? '#fbbf24'
          : s.isStuttered
          ? '#e879f9'
          : '#10b981';

        svg += `
          <rect x="${pCenterX}" y="${stalkTopY}" width="${vowelW}" height="${baseY - stalkTopY}" rx="4" fill="${stalkColor}" fill-opacity="0.32" stroke="${stalkColor}" stroke-width="1.5" />
          <line x1="${pCenterX}" y1="${baseY}" x2="${pCenterX}" y2="${stalkTopY}" stroke="${stalkColor}" stroke-width="2.8" />
          <circle cx="${pCenterX}" cy="${stalkTopY}" r="5.5" fill="${stalkColor}" stroke="#0f172a" stroke-width="1.5" />
          <text x="${pCenterX + vowelW / 2}" y="${baseY + 14}" text-anchor="middle" fill="#e2e8f0" font-size="10" font-weight="800">${isLearner ? s.learnerText : s.text}</text>
        `;
      });
    });

    svg += renderAnimatedPlayheadSVG(svgH);
    return svg;
  }

  // --------------------------------------------------------------------------
  // 8. ONE-CLICK AUDIO AUDITION BAR & REAL-TIME ANIMATED PLAYHEAD
  // --------------------------------------------------------------------------
  /**
   * Injects or updates the One-Click Audio Audition Bar directly above the Goal 1
   * SVG container so users can click:
   *   - 🔊 Play Native Reference
   *   - 🔊 Play Selected Dysfluent/Learner Take
   *   - 🎚️ Toggle Raw Clock (0%) vs. DTW Foot-Normalized (100%)
   * while watching the dual-track playhead sweep across both tracks in real time.
   */
  function ensureAuditionBarDOM(targetEl, data) {
    if (typeof document === 'undefined' || !targetEl) return;
    const parent = targetEl.tagName && targetEl.tagName.toLowerCase() === 'svg'
      ? targetEl.parentElement
      : targetEl;
    if (!parent || !parent.parentElement) return;

    let barEl = document.getElementById('goal1-audition-bar');
    if (!barEl) {
      barEl = document.createElement('div');
      barEl.id = 'goal1-audition-bar';
      barEl.className = 'flex flex-wrap items-center justify-between gap-2.5 bg-slate-900/95 border border-indigo-500/35 rounded-xl px-3.5 py-2.5 shadow-md';
      parent.parentElement.insertBefore(barEl, parent);
    }

    const isRaw = data.normFactor < 0.5;
    const profileShort = data.profileMeta.shortLabel.split('(')[0].trim();

    barEl.innerHTML = `
      <div class="flex flex-wrap items-center gap-2">
        <span class="px-2 py-0.5 rounded text-[11px] font-extrabold uppercase tracking-wider bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
          One-Click Audition
        </span>
        <button
          type="button"
          onclick="window.Goal1PostDiagnostics.auditionNative()"
          class="px-3 py-1.5 rounded-lg text-xs font-extrabold bg-sky-500/20 hover:bg-sky-500/30 text-sky-200 border border-sky-400/40 transition flex items-center gap-1.5 shadow-sm cursor-pointer"
        >
          <span>🔊</span>
          <span>Play Native Reference</span>
        </button>
        <button
          type="button"
          onclick="window.Goal1PostDiagnostics.auditionLearner()"
          class="px-3 py-1.5 rounded-lg text-xs font-extrabold bg-rose-500/25 hover:bg-rose-500/35 text-rose-200 border border-rose-400/50 transition flex items-center gap-1.5 shadow-sm cursor-pointer"
        >
          <span>🔊</span>
          <span>Play Dysfluent / Learner Take (${profileShort})</span>
        </button>
        <button
          type="button"
          onclick="window.Goal1PostDiagnostics.stopAudition()"
          class="px-2.5 py-1.5 rounded-lg text-xs font-bold bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition cursor-pointer"
          title="Stop Audio Audition"
        >
          ■ Stop
        </button>
      </div>

      <div class="flex flex-wrap items-center gap-2">
        <button
          type="button"
          onclick="window.Goal1PostDiagnostics.toggleNormFactor()"
          class="px-3 py-1.5 rounded-lg text-xs font-extrabold transition flex items-center gap-1.5 border cursor-pointer ${
            isRaw
              ? 'bg-rose-500/25 text-rose-200 border-rose-400/50'
              : 'bg-emerald-500/25 text-emerald-200 border-emerald-400/50'
          }"
        >
          <span>🎚️</span>
          <span>${isRaw ? 'Showing Raw Clock (0%) — Click for DTW (100%)' : 'Showing DTW Foot-Normalized (100%) — Click for Raw (0%)'}</span>
        </button>
      </div>
    `;
  }

  /**
   * Starts the real-time SVG playhead sweep animation across the active Goal 1 SVG.
   */
  function startPlayheadSweep(trackType, durationMs, maxBeat) {
    stopPlayheadSweep();
    if (typeof window === 'undefined' || typeof document === 'undefined') return;

    const playheadG = document.getElementById('g1-svg-playhead');
    const playheadLabel = document.getElementById('g1-svg-playhead-label');
    if (!playheadG) return;

    const beatToX = makeBeatToX(maxBeat, 56, 934);
    _auditionState.isPlaying = true;
    _auditionState.trackType = trackType;
    _auditionState.startTimeMs = performance.now();
    _auditionState.durationMs = durationMs;
    _auditionState.maxBeat = maxBeat;

    playheadG.style.opacity = '1';
    if (playheadLabel) {
      playheadLabel.textContent = trackType === 'native' ? '🔊 NATIVE REF' : '🔊 DYSFLUENT TAKE';
    }

    function step(nowMs) {
      if (!_auditionState.isPlaying) return;
      const elapsed = nowMs - _auditionState.startTimeMs;
      const frac = clamp(elapsed / Math.max(400, _auditionState.durationMs), 0, 1);
      const currentBeat = frac * 4.25;
      const x = beatToX(currentBeat);
      playheadG.setAttribute('transform', `translate(${x.toFixed(1)}, 0)`);

      if (frac < 1) {
        _auditionState.rafId = window.requestAnimationFrame(step);
      } else {
        stopPlayheadSweep();
      }
    }

    _auditionState.rafId = window.requestAnimationFrame(step);
  }

  function stopPlayheadSweep() {
    _auditionState.isPlaying = false;
    if (typeof window !== 'undefined' && _auditionState.rafId) {
      window.cancelAnimationFrame(_auditionState.rafId);
      _auditionState.rafId = null;
    }
    if (_auditionState.timeoutId) {
      clearTimeout(_auditionState.timeoutId);
      _auditionState.timeoutId = null;
    }
    if (typeof document !== 'undefined') {
      const playheadG = document.getElementById('g1-svg-playhead');
      if (playheadG) {
        playheadG.style.opacity = '0';
      }
    }
  }

  function auditionNative() {
    const state = _lastRenderState;
    const data = state.data || prepareComparativeData(state.phrase, state.learnerSyllables, state.profileKey, state.normFactor, state.vibe);
    const core = global.SpeechRhythmCore;
    const bpm = (core && core.audioEngine && core.audioEngine.bpm) || (data.phrase && data.phrase.defaultBpm) || 88;
    const barDurationMs = Math.round((60 / bpm) * 4.25 * 1000);
    const maxBeat = getMaxBeat(data.phrase, data.items);

    if (core && core.audioEngine && typeof core.audioEngine.playOneShotPhrase === 'function') {
      core.audioEngine.playOneShotPhrase(data.phrase, null);
    }
    startPlayheadSweep('native', barDurationMs, maxBeat);
    return { playing: 'native', durationMs: barDurationMs };
  }

  function auditionLearner() {
    const state = _lastRenderState;
    const data = state.data || prepareComparativeData(state.phrase, state.learnerSyllables, state.profileKey, state.normFactor, state.vibe);
    const core = global.SpeechRhythmCore;
    const bpm = (core && core.audioEngine && core.audioEngine.bpm) || (data.phrase && data.phrase.defaultBpm) || 88;
    const barDurationMs = Math.round((60 / bpm) * 4.45 * 1000);
    const maxBeat = getMaxBeat(data.phrase, data.items);

    if (core && core.audioEngine) {
      // Build audible dysfluent syllable cues including stutter pulses & prolonged schwas
      const cueList = [];
      data.items.forEach(s => {
        if (s.hasBlockBefore) {
          // Audible low creaky "uh..." hesitation filler before the blocked word
          cueList.push({
            text: 'uh...',
            pre: '',
            preDur: 0,
            vowel: 'uh',
            beat: Math.max(0.05, s.learnerBeat - Math.min(0.45, s.blockBeats * 0.75)),
            displayBeat: Math.max(0.05, s.learnerBeat - Math.min(0.45, s.blockBeats * 0.75)),
            dur: 0.22,
            displayDur: 0.22,
            stress: 0.35,
            pitchST: -3.5,
            pitchSlope: -1.0,
            isGhost: true
          });
        }
        if (s.isStuttered) {
          const count = Math.min(3, Math.max(2, s.stutterCount || 2));
          for (let k = 0; k < count; k++) {
            const b = Math.max(0.02, s.learnerBeat - (count - k) * 0.11);
            cueList.push({
              text: s.pre || 'p',
              pre: s.pre || 'p',
              preDur: 0.05,
              vowel: 'e',
              beat: b,
              displayBeat: b,
              dur: 0.05,
              displayDur: 0.05,
              stress: 0.55,
              pitchST: s.learnerPitchST,
              pitchSlope: 0,
              isGhost: true
            });
          }
        }
        cueList.push({
          ...s,
          beat: s.learnerBeat,
          displayBeat: s.learnerBeat,
          dur: s.learnerDur,
          displayDur: s.learnerDur,
          stress: s.learnerStress,
          pitchST: s.learnerPitchST,
          pitchSlope: s.learnerPitchSlope
        });
      });

      if (typeof core.audioEngine.playOneShotPhrase === 'function') {
        core.audioEngine.playOneShotPhrase(data.phrase, cueList);
      }
    }

    startPlayheadSweep('learner', barDurationMs, maxBeat);
    return { playing: 'learner', profile: data.profile, durationMs: barDurationMs };
  }

  function stopAudition() {
    const core = global.SpeechRhythmCore;
    if (core && core.audioEngine && typeof core.audioEngine.stop === 'function') {
      core.audioEngine.stop();
    }
    stopPlayheadSweep();
  }

  function toggleNormFactor() {
    const nextNorm = _lastRenderState.normFactor >= 0.5 ? 0.0 : 1.0;
    _lastRenderState.normFactor = nextNorm;
    if (global.AppController && typeof global.AppController.setNormFactor === 'function') {
      global.AppController.setNormFactor(nextNorm);
    } else if (_lastRenderState.targetEl) {
      render(_lastRenderState.targetEl, {
        mode: _lastRenderState.mode,
        phrase: _lastRenderState.phrase,
        learnerSyllables: _lastRenderState.learnerSyllables,
        normFactor: nextNorm,
        profileKey: _lastRenderState.profileKey,
        vibe: _lastRenderState.vibe,
        coachingContainer: _lastRenderState.coachingContainer
      });
    }
    return nextNorm;
  }

  // --------------------------------------------------------------------------
  // 9. RICH DIAGNOSTIC COACHING CARDS (`renderCoachingSummary`)
  //    Explains the exact clinical/pedagogical pattern for the active Vibe
  //    (Presentation, Discussion, Argument, Storytelling) & Dysfluency Profile
  // --------------------------------------------------------------------------
  function renderCoachingSummary(containerEl, phraseInput, learnerSyllablesInput, profileKey = 'dysfluent_hesitation', normFactor = 1.0, explicitVibe = null) {
    const el = typeof containerEl === 'string' && typeof document !== 'undefined'
      ? document.getElementById(containerEl)
      : containerEl;

    const data = prepareComparativeData(phraseInput, learnerSyllablesInput, profileKey, normFactor, explicitVibe);
    const { items, profile, metrics, globalRate, vibe, profileMeta } = data;

    const blockItem = items.find(s => s.hasBlockBefore) || items.find(s => !s.isGhost) || items[0];
    const prolongedItem = items.find(s => s.isProlonged) || items.find(s => s.isGhost) || items[0];
    const stutterItem = items.find(s => s.isStuttered) || items.find(s => (s.pre || '').length >= 2) || blockItem;
    const clippedItem = items.find(s => s.isClipped) || items[items.length - 1] || blockItem;
    const nRatioStr = metrics.natSimplex.map(v => Math.round(v * 100) + '%').join(':');
    const lRatioStr = metrics.lrnSimplex.map(v => Math.round(v * 100) + '%').join(':');

    let cardsHTML = '';

    if (profile === 'dysfluent_hesitation') {
      cardsHTML = `
        <div class="p-4 rounded-xl bg-rose-500/10 border border-rose-500/35 space-y-1.5">
          <div class="flex items-center justify-between gap-2">
            <span class="font-extrabold text-rose-400 text-xs uppercase tracking-wider">1. ⚡ Mid-Foot Hesitation Block (+${blockItem.blockMs || 450}ms Tear)</span>
            <span class="px-2 py-0.5 rounded text-[11px] font-mono bg-rose-500/20 text-rose-200">+${Math.max(280, blockItem.apparentMs)}ms Late</span>
          </div>
          <p class="text-xs text-slate-300 leading-relaxed">
            Inserting an involuntary <strong>[ ⚡ ${blockItem.blockMs || 450}ms BLOCK / "uh..." ]</strong> inside the stress foot right before <strong>"${blockItem.text}"</strong> tore the VocAlign tether ribbons wide open. Never pause <em>between</em> a function word and its content-word head—pause only at clause boundaries!
          </p>
        </div>

        <div class="p-4 rounded-xl bg-amber-500/10 border border-amber-500/35 space-y-1.5">
          <div class="flex items-center justify-between gap-2">
            <span class="font-extrabold text-amber-400 text-xs uppercase tracking-wider">2. 2.5× Prolongation Funnel ("${prolongedItem.learnerText}")</span>
            <span class="px-2 py-0.5 rounded text-[11px] font-mono bg-amber-500/20 text-amber-200">+${prolongedItem.bloatPct || 140}% Bloated</span>
          </div>
          <p class="text-xs text-slate-300 leading-relaxed">
            Stretching <strong>"${prolongedItem.text}" &rarr; "${prolongedItem.learnerText}"</strong> to buy lexical retrieval time devoured <strong>65% of the stress-foot budget</strong> (vs. 14% in native speech). Compress function words into crisp 50ms schwa (<code>/ə/</code>) ghost notes and link directly into the stressed vowel.
          </p>
        </div>

        <div class="p-4 rounded-xl bg-sky-500/10 border border-sky-500/35 space-y-1.5">
          <div class="flex items-center justify-between gap-2">
            <span class="font-extrabold text-sky-300 text-xs uppercase tracking-wider">3. ${vibe.icon} ${vibe.id} Vibe Impact &amp; Clinical Fix</span>
            <span class="px-2 py-0.5 rounded text-[11px] font-mono bg-sky-500/20 text-sky-200">nPVI: ${metrics.learnerNPVI} vs ${metrics.nativeNPVI}</span>
          </div>
          <p class="text-xs text-slate-300 leading-relaxed">
            <strong>${vibe.id} Context:</strong> ${vibe.dysfluencyImpact} <strong>Drill:</strong> Use silent pre-phonatory airflow before the entire foot so <em>"${prolongedItem.text} ${blockItem.text}"</em> fires as one unified motor chunk.
          </p>
        </div>
      `;
    } else if (profile === 'dysfluent_stutter') {
      cardsHTML = `
        <div class="p-4 rounded-xl bg-purple-500/10 border border-purple-500/35 space-y-1.5">
          <div class="flex items-center justify-between gap-2">
            <span class="font-extrabold text-purple-300 text-xs uppercase tracking-wider">1. 🔁 Stutter Onset Repetitions (${stutterItem.stutterPrefix || '[p-][p-]'})</span>
            <span class="px-2 py-0.5 rounded text-[11px] font-mono bg-purple-500/20 text-purple-200">♦ +${Math.max(210, stutterItem.apparentMs)}ms Late</span>
          </div>
          <p class="text-xs text-slate-300 leading-relaxed">
            False-start consonant repetitions (<strong><code>${stutterItem.stutterPrefix || '[p-][p-]'}${stutterItem.text}</code></strong>) collided inside the pre-beat runway, delaying the vowel P-center (♦) by <strong>+${Math.max(210, stutterItem.apparentMs)}ms</strong> outside the Danielsen Beat Bin.
          </p>
        </div>

        <div class="p-4 rounded-xl bg-rose-500/10 border border-rose-500/35 space-y-1.5">
          <div class="flex items-center justify-between gap-2">
            <span class="font-extrabold text-rose-300 text-xs uppercase tracking-wider">2. Glottal Tension &amp; Pitch Flattening</span>
            <span class="px-2 py-0.5 rounded text-[11px] font-mono bg-rose-500/20 text-rose-200">Glottal Catch</span>
          </div>
          <p class="text-xs text-slate-300 leading-relaxed">
            Articulatory block on the initial plosive/cluster locked the larynx into a flat monotone step (0 ST/s slope vs. target ${stutterItem.pitchSlope} ST glissando). Soften consonant contact (easy onset) and aim straight for the vowel core!
          </p>
        </div>

        <div class="p-4 rounded-xl bg-sky-500/10 border border-sky-500/35 space-y-1.5">
          <div class="flex items-center justify-between gap-2">
            <span class="font-extrabold text-sky-300 text-xs uppercase tracking-wider">3. ${vibe.icon} ${vibe.id} Vibe Impact &amp; P-Center Lead-In</span>
            <span class="px-2 py-0.5 rounded text-[11px] font-mono bg-sky-500/20 text-sky-200">Runway Lead-In</span>
          </div>
          <p class="text-xs text-slate-300 leading-relaxed">
            <strong>${vibe.id} Context:</strong> ${vibe.dysfluencyImpact} <strong>Drill:</strong> Initiate continuous voicing on the preceding schwa and glide smoothly through <code>/${stutterItem.pre || 'str'}-/</code> 80ms <em>before</em> the beat.
          </p>
        </div>
      `;
    } else if (profile === 'syllable_timed_choppy') {
      cardsHTML = `
        <div class="p-4 rounded-xl bg-amber-500/10 border border-amber-500/35 space-y-1.5">
          <div class="flex items-center justify-between gap-2">
            <span class="font-extrabold text-amber-400 text-xs uppercase tracking-wider">1. 🤖 +140% Bloated Schwa Function Words</span>
            <span class="px-2 py-0.5 rounded text-[11px] font-mono bg-amber-500/20 text-amber-200">nPVI: ${metrics.learnerNPVI} vs ${metrics.nativeNPVI}</span>
          </div>
          <p class="text-xs text-slate-300 leading-relaxed">
            Unstressed function words (<strong>"${prolongedItem.text}"</strong>) ballooned <strong>2.4× wider (+140% Bloated)</strong> in the Amber Funnel Ribbon (${lRatioStr} vs. target ${nRatioStr}), collapsing rhythm contrast into robotic 1:1:1 syllable-timing.
          </p>
        </div>

        <div class="p-4 rounded-xl bg-purple-500/10 border border-purple-500/35 space-y-1.5">
          <div class="flex items-center justify-between gap-2">
            <span class="font-extrabold text-purple-300 text-xs uppercase tracking-wider">2. /${stutterItem.pre || 'str'}/ On-Beat Cluster Lag (+165ms)</span>
            <span class="px-2 py-0.5 rounded text-[11px] font-mono bg-purple-500/20 text-purple-200">♦ Vowel Late</span>
          </div>
          <p class="text-xs text-slate-300 leading-relaxed">
            Launching <code>/${stutterItem.pre || 'str'}-/</code> <em>on</em> the beat instead of in the hatched pre-beat runway pushed the vowel nucleus <code>-${stutterItem.vowel}</code> (♦ P-center) late outside the Beat Bin.
          </p>
        </div>

        <div class="p-4 rounded-xl bg-sky-500/10 border border-sky-500/35 space-y-1.5">
          <div class="flex items-center justify-between gap-2">
            <span class="font-extrabold text-sky-300 text-xs uppercase tracking-wider">3. ${vibe.icon} ${vibe.id} Vibe &amp; DTW Rate Separation</span>
            <span class="px-2 py-0.5 rounded text-[11px] font-mono bg-sky-500/20 text-sky-200">${Math.round(data.normFactor * 100)}% DTW</span>
          </div>
          <p class="text-xs text-slate-300 leading-relaxed">
            <strong>${vibe.id} Context:</strong> ${vibe.nativeTrait} Even after DTW factors out your ${globalRate.toFixed(2)}× speaking rate, internal foot ratios remain flat (${lRatioStr})—whisper-compress schwas to 14% of the foot!
          </p>
        </div>
      `;
    } else if (profile === 'cluttered_runon') {
      cardsHTML = `
        <div class="p-4 rounded-xl bg-orange-500/10 border border-orange-500/35 space-y-1.5">
          <div class="flex items-center justify-between gap-2">
            <span class="font-extrabold text-orange-400 text-xs uppercase tracking-wider">1. |✂ Guillotine-Clipped Stressed Vowels (-52%)</span>
            <span class="px-2 py-0.5 rounded text-[11px] font-mono bg-orange-500/20 text-orange-200">0.48× Duration</span>
          </div>
          <p class="text-xs text-slate-300 leading-relaxed">
            Phrase-final and nuclear stressed vowels (<strong>"${clippedItem.text}"</strong>) were chopped in half (<strong>|✂ Clipped -52%</strong>), leaving a hatched empty gap inside the Native Ghost Box and robbing the listener of nuclear pitch glissando.
          </p>
        </div>

        <div class="p-4 rounded-xl bg-rose-500/10 border border-rose-500/35 space-y-1.5">
          <div class="flex items-center justify-between gap-2">
            <span class="font-extrabold text-rose-300 text-xs uppercase tracking-wider">2. ⏪ Obliterated Pause Gate (-195ms Rushed)</span>
            <span class="px-2 py-0.5 rounded text-[11px] font-mono bg-rose-500/20 text-rose-200">Leftward / Tether</span>
          </div>
          <p class="text-xs text-slate-300 leading-relaxed">
            Crashing straight through the syntactic breath boundary pulled the final clause <strong>195ms early</strong> (steep leftward-diving orange tether), telescoping words into an unintelligible cluttered run-on.
          </p>
        </div>

        <div class="p-4 rounded-xl bg-sky-500/10 border border-sky-500/35 space-y-1.5">
          <div class="flex items-center justify-between gap-2">
            <span class="font-extrabold text-sky-300 text-xs uppercase tracking-wider">3. ${vibe.icon} ${vibe.id} Vibe Pacing &amp; Boundary Hold</span>
            <span class="px-2 py-0.5 rounded text-[11px] font-mono bg-sky-500/20 text-sky-200">Rate: ${globalRate.toFixed(2)}×</span>
          </div>
          <p class="text-xs text-slate-300 leading-relaxed">
            <strong>${vibe.id} Context:</strong> ${vibe.dysfluencyImpact} <strong>Drill:</strong> Stretch phrase-final vowels 1.6× across the full Ghost Box and hold a deliberate half-beat breath suspension at clause gates.
          </p>
        </div>
      `;
    } else {
      cardsHTML = `
        <div class="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/35 space-y-1.5">
          <div class="flex items-center justify-between gap-2">
            <span class="font-extrabold text-emerald-400 text-xs uppercase tracking-wider">1. ✨ Expressive Beat-Bin Lock &amp; Rubato Pocket</span>
            <span class="px-2 py-0.5 rounded text-[11px] font-mono bg-emerald-500/20 text-emerald-200">${metrics.inBinNormalized}/${metrics.totalSyllables} In Beat Bin</span>
          </div>
          <p class="text-xs text-slate-300 leading-relaxed">
            Every stressed vowel onset (♦) lands cleanly inside the Danielsen Beat Bin with intentional <strong>+25ms to +55ms expressive rubato</strong> (shown in the Deviation Strip), while consonant clusters launch early in the runway.
          </p>
        </div>

        <div class="p-4 rounded-xl bg-sky-500/10 border border-sky-500/35 space-y-1.5">
          <div class="flex items-center justify-between gap-2">
            <span class="font-extrabold text-sky-300 text-xs uppercase tracking-wider">2. High Stress-Timed Contrast (nPVI = ${metrics.learnerNPVI})</span>
            <span class="px-2 py-0.5 rounded text-[11px] font-mono bg-sky-500/20 text-sky-200">Foot Ratio ${lRatioStr}</span>
          </div>
          <p class="text-xs text-slate-300 leading-relaxed">
            Function words compress to <strong>14% of the stress-foot budget</strong> while nuclear vowels sustain a full ${blockItem.pitchSlope} ST glissando contour—demonstrating healthy native prosodic contrast.
          </p>
        </div>

        <div class="p-4 rounded-xl bg-indigo-500/10 border border-indigo-500/35 space-y-1.5">
          <div class="flex items-center justify-between gap-2">
            <span class="font-extrabold text-indigo-300 text-xs uppercase tracking-wider">3. ${vibe.icon} ${vibe.id} Vibe Benchmark &amp; DTW Toggle</span>
            <span class="px-2 py-0.5 rounded text-[11px] font-mono bg-indigo-500/20 text-indigo-200">${profileMeta.shortLabel.split('(')[0]}</span>
          </div>
          <p class="text-xs text-slate-300 leading-relaxed">
            <strong>${vibe.id} Target:</strong> ${vibe.nativeTrait} Toggle <strong>Raw Clock (0%) vs. DTW (100%)</strong> above to see how DTW removes ${globalRate.toFixed(2)}× speaking-rate drift while preserving expressive micro-timing!
          </p>
        </div>
      `;
    }

    if (el) {
      el.innerHTML = cardsHTML;
    }
    return cardsHTML;
  }

  // --------------------------------------------------------------------------
  // 10. UNIFIED RENDER DISPATCHER & PUBLIC API
  // --------------------------------------------------------------------------
  function render(targetEl, modeOrOptions, phraseArg, learnerSyllablesArg, normFactorArg, profileKeyArg, coachingContainerArg) {
    const el = typeof targetEl === 'string' && typeof document !== 'undefined'
      ? document.getElementById(targetEl)
      : targetEl;

    let mode = 'vocalign_tether';
    let phrase = phraseArg;
    let learnerSyllables = learnerSyllablesArg;
    let normFactor = typeof normFactorArg === 'number' ? normFactorArg : 1.0;
    let profileKey = profileKeyArg || 'dysfluent_hesitation';
    let vibe = null;
    let coachingContainer = coachingContainerArg || null;

    if (modeOrOptions && typeof modeOrOptions === 'object' && !Array.isArray(modeOrOptions)) {
      mode = modeOrOptions.mode || modeOrOptions.diffMode || 'vocalign_tether';
      phrase = modeOrOptions.phrase ?? phrase;
      learnerSyllables = modeOrOptions.learnerSyllables ?? modeOrOptions.syllables ?? learnerSyllables;
      normFactor = typeof modeOrOptions.normFactor === 'number' ? modeOrOptions.normFactor : normFactor;
      profileKey = modeOrOptions.profileKey || modeOrOptions.profile || profileKey;
      vibe = modeOrOptions.vibe || null;
      coachingContainer = modeOrOptions.coachingContainer || coachingContainer;
    } else if (typeof modeOrOptions === 'string') {
      mode = modeOrOptions;
      if (typeof learnerSyllablesArg === 'string') {
        profileKey = learnerSyllablesArg;
        learnerSyllables = null;
      }
      if (typeof normFactorArg === 'string' && typeof profileKeyArg === 'number') {
        profileKey = normFactorArg;
        normFactor = profileKeyArg;
      }
    }

    const resolvedMode = normalizeModeKey(mode);
    const data = prepareComparativeData(phrase, learnerSyllables, profileKey, normFactor, vibe);

    let svgMarkup = '';
    let viewBoxHeight = 440;

    if (resolvedMode === 'vocalign_tether') {
      svgMarkup = renderVocAlignTetherSVG(data);
      viewBoxHeight = 440;
    } else if (resolvedMode === 'prosogram_overlay') {
      svgMarkup = renderProsogramOverlaySVG(data);
      viewBoxHeight = 390;
    } else if (resolvedMode === 'foot_budget_strips') {
      svgMarkup = renderFootBudgetStripsSVG(data);
      viewBoxHeight = 405;
    } else {
      svgMarkup = renderSpectralTrackerSVG(data);
      viewBoxHeight = 380;
    }

    _lastRenderState = {
      targetEl: el,
      mode: resolvedMode,
      phrase: data.phrase,
      learnerSyllables,
      normFactor: data.normFactor,
      profileKey: data.rawProfileKey,
      vibe: data.vibe.id,
      coachingContainer,
      data
    };

    if (el) {
      ensureAuditionBarDOM(el, data);
      if (el.tagName && el.tagName.toLowerCase() === 'svg') {
        el.setAttribute('viewBox', `0 0 960 ${viewBoxHeight}`);
        el.style.height = `${viewBoxHeight}px`;
        el.innerHTML = svgMarkup;
      } else {
        el.innerHTML = `
          <svg class="w-full block" style="min-width: 820px; height: ${viewBoxHeight}px;" viewBox="0 0 960 ${viewBoxHeight}">
            ${svgMarkup}
          </svg>
        `;
      }
    }

    if (coachingContainer) {
      renderCoachingSummary(coachingContainer, data.phrase, learnerSyllables, profileKey, data.normFactor, data.vibe.id);
    }

    return data;
  }

  function renderVocAlignTether(targetEl, phrase, learnerSyllables, normFactor = 1.0, profileKey = 'dysfluent_hesitation') {
    return render(targetEl, { mode: 'vocalign_tether', phrase, learnerSyllables, normFactor, profileKey });
  }

  function renderProsogramOverlay(targetEl, phrase, learnerSyllables, normFactor = 1.0, profileKey = 'dysfluent_hesitation') {
    return render(targetEl, { mode: 'prosogram_overlay', phrase, learnerSyllables, normFactor, profileKey });
  }

  function renderFootBudgetStrips(targetEl, phrase, learnerSyllables, normFactor = 1.0, profileKey = 'dysfluent_hesitation') {
    return render(targetEl, { mode: 'foot_budget_strips', phrase, learnerSyllables, normFactor, profileKey });
  }

  function renderSpectralTracker(targetEl, phrase, learnerSyllables, normFactor = 1.0, profileKey = 'dysfluent_hesitation') {
    return render(targetEl, { mode: 'spectral_tracker', phrase, learnerSyllables, normFactor, profileKey });
  }

  const Goal1PostDiagnostics = {
    MODES,
    MODE_ALIASES,
    PROFILE_METADATA,
    PROFILE_ALIASES,
    VIBE_PROFILES,
    normalizeModeKey,
    normalizeProfileKey,
    resolveVibe,
    prepareComparativeData,
    computeMetrics,
    render,
    renderMode: render,
    renderVocAlignTether,
    renderTetherDiff: renderVocAlignTether,
    renderProsogramOverlay,
    renderGhostProsogram: renderProsogramOverlay,
    renderFootBudgetStrips,
    renderFootStripsSimplex: renderFootBudgetStrips,
    renderSpectralTracker,
    renderCoachingSummary,
    auditionNative,
    auditionLearner,
    stopAudition,
    toggleNormFactor
  };

  global.Goal1PostDiagnostics = Goal1PostDiagnostics;
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = Goal1PostDiagnostics;
  }
})(typeof window !== 'undefined' ? window : globalThis);
