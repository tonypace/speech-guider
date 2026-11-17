/**
 * Speech Rhythm Interactive Suite — Authentic Speech Registers ("Vibes"),
 * Realistic Dysfluent vs. Native Speech Profiles & Web Audio Prosodic Voice Synthesizer
 * File: /home/tonyp/Projects/Speech Rhythm/app/data_and_audio.js
 *
 * Exposes `window.SpeechRhythmCore` containing:
 *   1. PHRASES & SPEECH_VIBES: 4 authentic spoken English discourse registers ("Vibes")
 *      with rich P-center consonant lead-ins, rhetorical pause gates, and foot structure,
 *      plus `applyVibeCadence(phraseOrId, vibeKey)`
 *   2. ERROR_PROFILES: 5 unmistakable Dysfluent & Learner comparison profiles + Live Recorded store:
 *      - 'dysfluent_hesitation' : Mid-Foot Hesitation Block (450ms) + Prolongation ("theeee...") + Clutter Rush
 *      - 'dysfluent_stutter'    : Initial Repetition / False Start ("c-c-CORE", "p-p-PROB") + +0.32b P-center lag
 *      - 'syllable_timed_choppy': L2 Choppy Word-by-Word (2.2x bloated schwas, 2.4x loudness, glottal gaps, 0.78x rate)
 *      - 'cluttered_runon'      : Dysfluent Cluttering (0.48x clipped vowels, obliterated -0.45b pause gate, 1.22x rate)
 *      - 'native_expressive'    : 2nd Native Speaker Rubato (0.86x rate; 300-500ms raw clock drift, locks in under DTW!)
 *      - 'live_recorded'        : Captures keyboard-tapped, virtual-bot, or mic-detected runs from Goal 2
 *   3. GrooveAudioEngine: Web Audio API Prosodic Voice & Dysfluency Synthesizer featuring
 *      `playUtterance(phrase, profileKeyOrSyllables, { onProgress, onComplete })` to audibly render
 *      both Native Reference and Dysfluent/Learner profiles (formant vowels, pitch contours,
 *      prolonged hesitations, "p-p-" stutter repetitions, glottal stops, and soft prosodic foot pulse).
 */

(function (global) {
  'use strict';

  // ============================================================================
  // 1. DISCOURSE "VIBES" (SPEECH REGISTERS) & 4 AUTHENTIC PHRASES
  // ============================================================================

  const SPEECH_VIBES = {
    prepared: {
      id: 'prepared',
      vibeIndex: 0,
      name: '1. Prepared Speech / Presentation',
      shortLabel: 'Prepared Presentation',
      defaultBpm: 84,
      pauseGateMultiplier: 1.15,
      anacrusisCompression: 1.0,
      stressContrast: 1.05,
      pitchRangeScale: 1.05,
      swing: 0.02,
      snareLag: 0.0,
      description:
        'Balanced prosodic stress feet, deliberate 350ms rhetorical pause after nuclear focus ("CORE..."), and clear phrase-final lengthening.'
    },
    spontaneous: {
      id: 'spontaneous',
      vibeIndex: 1,
      name: '2. Spontaneous Discussion / Turn-Taking',
      shortLabel: 'Spontaneous Turn-Taking',
      defaultBpm: 92,
      pauseGateMultiplier: 0.85,
      anacrusisCompression: 0.76,
      stressContrast: 1.0,
      pitchRangeScale: 1.0,
      swing: 0.04,
      snareLag: 0.015,
      description:
        'Fast 3-syllable anacrusis pickup ("Well if you"), radical phonetic compression on multi-syllable adverbs ("actually" -> "AC-chlee"), and conversational bounce.'
    },
    contrastive: {
      id: 'contrastive',
      vibeIndex: 2,
      name: '3. Heated Argument / Contrastive Stress',
      shortLabel: 'Contrastive Argument',
      defaultBpm: 88,
      pauseGateMultiplier: 1.2,
      anacrusisCompression: 0.72,
      stressContrast: 1.32,
      pitchRangeScale: 1.35,
      swing: 0.03,
      snareLag: 0.025,
      description:
        'Extreme dynamic and F0 contrast between rapid low-energy function setups ("say it was") and explosive contrastive nuclear peaks ("EA-SY...", "POS-sible").'
    },
    narrative: {
      id: 'narrative',
      vibeIndex: 3,
      name: '4. Expressive Storytelling / Narrative',
      shortLabel: 'Narrative Storytelling',
      defaultBpm: 78,
      pauseGateMultiplier: 1.35,
      anacrusisCompression: 0.88,
      stressContrast: 1.18,
      pitchRangeScale: 1.25,
      swing: 0.0,
      snareLag: 0.04,
      description:
        'Elastic expressive rubato: drawn-out suspenseful opening foot ("SLOW-ly"), dramatic suspension pause after "O-pen...", and rapid action acceleration ("and vanished in the").'
    }
  };

  // Backwards-compatible map so both Vibe keys and legacy Groove keys work seamlessly
  const GROOVE_STYLES = {
    prepared: SPEECH_VIBES.prepared,
    spontaneous: SPEECH_VIBES.spontaneous,
    contrastive: SPEECH_VIBES.contrastive,
    narrative: SPEECH_VIBES.narrative,
    boombap: SPEECH_VIBES.prepared,
    latin_shuffle: SPEECH_VIBES.spontaneous,
    dilla: SPEECH_VIBES.contrastive,
    pulse: SPEECH_VIBES.narrative
  };

  const PHRASES = [
    // -------------------------------------------------------------------------
    // VIBE 0: Prepared Speech / Presentation
    // "We NEED to focus on the CORE... PROBLEMs first"
    // -------------------------------------------------------------------------
    {
      id: 0,
      vibeId: 'prepared',
      title: 'We NEED to focus on the CORE... PROBLEMs first',
      subtitle: 'Balanced Stress Feet, 350ms Rhetorical Pause Gate & /pr/ Cluster Lead-In',
      category: '1. Prepared Speech / Presentation',
      focus: 'Rhetorical Pause Gate & Balanced Stress Feet',
      totalBeats: 4.0,
      defaultBpm: 84,
      bpm: 84,
      recommendedGroove: 'prepared',
      ipa: '/wi ˈniːd tə ˈfoʊkəs ɒn ðə ˈkɔːɹ ... ˈpɹɑːbləmz ˈfɝːst/',
      pedagogicalFocus:
        'Keynote/presentation register: balanced stress feet lead into "CORE...", which receives phrase-final lengthening ' +
        'plus a deliberate 350ms (~0.48-beat) rhetorical pause gate. Then the /pr/ cluster on "PROB-" launches 0.11 beats early ' +
        'so its vowel P-center locks onto the post-pause beat.',
      rhetoricalPause: {
        afterSyllableId: 7,
        startBeat: 2.34,
        endBeat: 2.82,
        durationMs: 350,
        label: '350ms Rhetorical Pause Gate'
      },
      feet: [
        { footId: 0, label: 'Pickup: We', startBeat: 0.0, endBeat: 0.34 },
        { footId: 1, label: 'Foot 1: NEED to', startBeat: 0.34, endBeat: 0.90 },
        { footId: 2, label: 'Foot 2: FO-cus on the', startBeat: 0.90, endBeat: 1.84 },
        { footId: 3, label: 'Foot 3: CORE... [Pause Gate]', startBeat: 1.84, endBeat: 2.84 },
        { footId: 4, label: 'Foot 4: PROB-lems FIRST', startBeat: 2.84, endBeat: 4.0 }
      ],
      syllables: [
        {
          id: 0,
          text: 'We',
          pre: 'w',
          preDur: 0.04,
          vowel: 'e',
          ipa: 'wi',
          beat: 0.16,
          dur: 0.13,
          stress: 0.22,
          pitchST: -1.0,
          pitchSlope: 0,
          isGhost: true,
          isFinal: false,
          rhymeGroup: 0,
          footId: 0,
          tip: 'Light pickup pronoun setting up the opening stress on NEED.'
        },
        {
          id: 1,
          text: 'NEED',
          pre: 'n',
          preDur: 0.05,
          vowel: 'EED',
          ipa: 'ˈniːd',
          beat: 0.38,
          dur: 0.34,
          stress: 0.88,
          pitchST: 3.2,
          pitchSlope: 1.0,
          isGhost: false,
          isFinal: false,
          rhymeGroup: 1,
          footId: 1,
          tip: 'First primary stress head; high front vowel /iː/ establishes authority.'
        },
        {
          id: 2,
          text: 'to',
          pre: 't',
          preDur: 0.03,
          vowel: 'o',
          ipa: 'tə',
          beat: 0.76,
          dur: 0.11,
          stress: 0.16,
          pitchST: -1.5,
          pitchSlope: 0,
          isGhost: true,
          isFinal: false,
          rhymeGroup: 0,
          footId: 1,
          tip: 'Compressed infinitive marker /tə/ linking NEED to FO-cus.'
        },
        {
          id: 3,
          text: 'FO-',
          pre: 'f',
          preDur: 0.06,
          vowel: 'O',
          ipa: 'ˈfoʊ',
          beat: 0.94,
          dur: 0.30,
          stress: 0.84,
          pitchST: 2.8,
          pitchSlope: -1.0,
          isGhost: false,
          isFinal: false,
          rhymeGroup: 2,
          footId: 2,
          tip: 'Second stress foot head; labiodental /f/ begins slightly before Beat 0.94.'
        },
        {
          id: 4,
          text: 'cus',
          pre: 'c',
          preDur: 0.03,
          vowel: 'us',
          ipa: 'kəs',
          beat: 1.28,
          dur: 0.13,
          stress: 0.22,
          pitchST: -0.5,
          pitchSlope: 0,
          isGhost: true,
          isFinal: false,
          rhymeGroup: 0,
          footId: 2,
          tip: 'Unstressed second syllable /kəs/ stepping down into the function-word run.'
        },
        {
          id: 5,
          text: 'on',
          pre: '',
          preDur: 0.0,
          vowel: 'on',
          ipa: 'ən',
          beat: 1.48,
          dur: 0.12,
          stress: 0.18,
          pitchST: -1.8,
          pitchSlope: 0,
          isGhost: true,
          isFinal: false,
          rhymeGroup: 0,
          footId: 2,
          tip: 'Reduced preposition; keep short and smooth without a glottal stop.'
        },
        {
          id: 6,
          text: 'the',
          pre: 'th',
          preDur: 0.04,
          vowel: 'e',
          ipa: 'ðə',
          beat: 1.65,
          dur: 0.11,
          stress: 0.15,
          pitchST: -2.2,
          pitchSlope: 0,
          isGhost: true,
          isFinal: false,
          rhymeGroup: 0,
          footId: 2,
          tip: 'Ultra-light /ðə/ clearing space for the nuclear word CORE.'
        },
        {
          id: 7,
          text: 'CORE...',
          pre: 'c',
          preDur: 0.07,
          vowel: 'ORE',
          ipa: 'ˈkɔːɹ',
          beat: 1.86,
          dur: 0.48,
          stress: 1.00,
          pitchST: 4.6,
          pitchSlope: -3.2,
          isGhost: false,
          isFinal: true,
          hasPauseAfter: true,
          pauseBeats: 0.48,
          rhymeGroup: 2,
          footId: 3,
          tip: 'Phrase-final lengthening + 350ms rhetorical pause gate after CORE... before launching PROB-lems!'
        },
        {
          id: 8,
          text: 'PROB-',
          pre: 'pr',
          preDur: 0.11,
          vowel: 'OB',
          ipa: 'ˈpɹɑːb',
          beat: 2.86,
          dur: 0.32,
          stress: 0.90,
          pitchST: 3.4,
          pitchSlope: -1.2,
          isGhost: false,
          isFinal: false,
          rhymeGroup: 3,
          footId: 4,
          tip: 'Start /pr/ cluster 0.11 beats early (at Beat 2.75) right at the end of the rhetorical pause.'
        },
        {
          id: 9,
          text: 'lems',
          pre: 'l',
          preDur: 0.03,
          vowel: 'ems',
          ipa: 'ləmz',
          beat: 3.24,
          dur: 0.14,
          stress: 0.24,
          pitchST: 0.0,
          pitchSlope: 0,
          isGhost: true,
          isFinal: false,
          rhymeGroup: 0,
          footId: 4,
          tip: 'Quick schwa-nasal tail /ləmz/ rebounding into FIRST.'
        },
        {
          id: 10,
          text: 'FIRST',
          pre: 'f',
          preDur: 0.07,
          vowel: 'IRST',
          ipa: 'ˈfɝːst',
          beat: 3.48,
          dur: 0.44,
          stress: 0.94,
          pitchST: 2.6,
          pitchSlope: -4.2,
          isGhost: false,
          isFinal: true,
          rhymeGroup: 3,
          footId: 4,
          tip: 'Authoritative clause-final fall on /ˈfɝːst/.'
        }
      ]
    },

    // -------------------------------------------------------------------------
    // VIBE 1: Spontaneous Discussion / Turn-Taking
    // "Well if you LOOK at what actually HAP-pened there"
    // -------------------------------------------------------------------------
    {
      id: 1,
      vibeId: 'spontaneous',
      title: 'Well if you LOOK at what actually HAP-pened there',
      subtitle: 'Fast 3-Syllable Turn-Entry Pickup ("Well if you") & "AC-chlee" Compression',
      category: '2. Spontaneous Discussion / Turn-Taking',
      focus: 'Fast Anacrusis Pickup & "AC-chlee" Phonetic Compression',
      totalBeats: 4.0,
      defaultBpm: 92,
      bpm: 92,
      recommendedGroove: 'spontaneous',
      ipa: '/wɛl ɪf jə ˈlʊk ət wʌt ˈæktʃli ˈhæpənd ˈðɛɹ/',
      pedagogicalFocus:
        'Spontaneous turn-taking starts with a rapid 3-syllable floor-claiming pickup ("Well if you") that compresses into 0.70 beats ' +
        'before hitting the first anchor "LOOK". Notice how 4-syllable "ac-tu-al-ly" compresses into a 2-part burst ("AC-chlee") ' +
        'to preserve conversational foot bounce.',
      feet: [
        { footId: 0, label: 'Pickup: Well if you', startBeat: 0.0, endBeat: 0.78 },
        { footId: 1, label: 'Foot 1: LOOK at what', startBeat: 0.78, endBeat: 1.72 },
        { footId: 2, label: 'Foot 2: AC-tual-ly ("chlee")', startBeat: 1.72, endBeat: 2.54 },
        { footId: 3, label: 'Foot 3: HAP-pened THERE', startBeat: 2.54, endBeat: 4.0 }
      ],
      syllables: [
        {
          id: 0,
          text: 'Well',
          pre: 'w',
          preDur: 0.04,
          vowel: 'ell',
          ipa: 'wɛl',
          beat: 0.14,
          dur: 0.15,
          stress: 0.34,
          pitchST: 0.5,
          pitchSlope: -0.5,
          isGhost: true,
          isFinal: false,
          rhymeGroup: 0,
          footId: 0,
          tip: 'Fast discourse marker claiming the conversational floor.'
        },
        {
          id: 1,
          text: 'if',
          pre: '',
          preDur: 0.0,
          vowel: 'if',
          ipa: 'ɪf',
          beat: 0.35,
          dur: 0.11,
          stress: 0.16,
          pitchST: -1.2,
          pitchSlope: 0,
          isGhost: true,
          isFinal: false,
          rhymeGroup: 0,
          footId: 0,
          tip: 'Tucked conditional ghost syllable.'
        },
        {
          id: 2,
          text: 'you',
          pre: 'y',
          preDur: 0.03,
          vowel: 'ou',
          ipa: 'jə',
          beat: 0.52,
          dur: 0.11,
          stress: 0.15,
          pitchST: -1.8,
          pitchSlope: 0,
          isGhost: true,
          isFinal: false,
          rhymeGroup: 0,
          footId: 0,
          tip: 'Reduced /jə/ springboarding directly into LOOK.'
        },
        {
          id: 3,
          text: 'LOOK',
          pre: 'l',
          preDur: 0.05,
          vowel: 'OOK',
          ipa: 'ˈlʊk',
          beat: 0.80,
          dur: 0.34,
          stress: 0.90,
          pitchST: 3.6,
          pitchSlope: -1.0,
          isGhost: false,
          isFinal: false,
          rhymeGroup: 1,
          footId: 1,
          tip: 'First primary stress anchor after the 3-syllable turn-taking pickup.'
        },
        {
          id: 4,
          text: 'at',
          pre: '',
          preDur: 0.0,
          vowel: 'at',
          ipa: 'ət',
          beat: 1.22,
          dur: 0.11,
          stress: 0.16,
          pitchST: -1.5,
          pitchSlope: 0,
          isGhost: true,
          isFinal: false,
          rhymeGroup: 0,
          footId: 1,
          tip: 'Flapped/unreleased /ət/ ghost syllable.'
        },
        {
          id: 5,
          text: 'what',
          pre: 'wh',
          preDur: 0.03,
          vowel: 'at',
          ipa: 'wət',
          beat: 1.42,
          dur: 0.13,
          stress: 0.22,
          pitchST: -1.2,
          pitchSlope: 0,
          isGhost: true,
          isFinal: false,
          rhymeGroup: 0,
          footId: 1,
          tip: 'Unstressed relative pronoun before AC-tually.'
        },
        {
          id: 6,
          text: 'AC-',
          pre: '',
          preDur: 0.0,
          vowel: 'AC',
          ipa: 'ˈæk',
          beat: 1.74,
          dur: 0.30,
          stress: 0.86,
          pitchST: 3.2,
          pitchSlope: 1.2,
          isGhost: false,
          isFinal: false,
          rhymeGroup: 2,
          footId: 2,
          tip: 'Stressed open front vowel /æ/ initiating "actually".'
        },
        {
          id: 7,
          text: 'tual-ly',
          pre: 'tʃl',
          preDur: 0.06,
          vowel: 'ee',
          ipa: 'tʃli',
          beat: 2.12,
          dur: 0.16,
          stress: 0.24,
          pitchST: 0.4,
          pitchSlope: 0,
          isGhost: true,
          isFinal: false,
          rhymeGroup: 0,
          footId: 2,
          tip: 'Phonetic compression: 3 orthographic syllables ("-tu-al-ly") elide into a single fast /tʃli/ ("chlee")!'
        },
        {
          id: 8,
          text: 'HAP-',
          pre: 'h',
          preDur: 0.05,
          vowel: 'AP',
          ipa: 'ˈhæp',
          beat: 2.56,
          dur: 0.36,
          stress: 0.96,
          pitchST: 4.4,
          pitchSlope: -2.0,
          isGhost: false,
          isFinal: false,
          rhymeGroup: 2,
          footId: 3,
          tip: 'Nuclear stress punch echoing the /æ/ vowel of AC-.'
        },
        {
          id: 9,
          text: 'pened',
          pre: 'p',
          preDur: 0.03,
          vowel: 'ened',
          ipa: 'ənd',
          beat: 2.98,
          dur: 0.14,
          stress: 0.20,
          pitchST: -0.6,
          pitchSlope: 0,
          isGhost: true,
          isFinal: false,
          rhymeGroup: 0,
          footId: 3,
          tip: 'Syllabic nasal /ənd/ release.'
        },
        {
          id: 10,
          text: 'THERE',
          pre: 'th',
          preDur: 0.05,
          vowel: 'ERE',
          ipa: 'ˈðɛɹ',
          beat: 3.34,
          dur: 0.46,
          stress: 0.82,
          pitchST: 1.8,
          pitchSlope: -3.2,
          isGhost: false,
          isFinal: true,
          rhymeGroup: 3,
          footId: 3,
          tip: 'Clause-final deictic anchor with conversational fall.'
        }
      ]
    },

    // -------------------------------------------------------------------------
    // VIBE 2: Heated Argument / Contrastive Stress
    // "I didn't say it was EASY... I said it's POS-sible"
    // -------------------------------------------------------------------------
    {
      id: 2,
      vibeId: 'contrastive',
      title: "I didn't say it was EASY... I said it's POS-sible",
      subtitle: 'Extreme Dynamic Contrast, Rapid Low-Energy Setup & Explosive Nuclear Peaks',
      category: '3. Heated Argument / Contrastive Stress',
      focus: 'Contrastive F0 Peaks ("EA-SY..." vs. "POS-sible") & Suspension Pause',
      totalBeats: 4.0,
      defaultBpm: 88,
      bpm: 88,
      recommendedGroove: 'contrastive',
      ipa: '/aɪ ˈdɪdn̩t seɪ ɪt wəz ˈiːzi ... aɪ ˈsɛd ɪts ˈpʰɑːsəbəl/',
      pedagogicalFocus:
        'Contrastive argument register: "say it was" is crushed into a ultra-fast, low-pitch setup runway so that "EA-SY..." ' +
        'explodes with +5.5 ST pitch excursion and a suspension pause, followed by the counter-assertion "SAID it\'s POS-sible" ' +
        'with heavy /pʰ/ aspiration lead-in.',
      rhetoricalPause: {
        afterSyllableId: 5,
        startBeat: 2.08,
        endBeat: 2.48,
        durationMs: 280,
        label: 'Contrastive Suspension Pause'
      },
      feet: [
        { footId: 0, label: "Foot 1: I DID-n't say it was", startBeat: 0.0, endBeat: 1.50 },
        { footId: 1, label: 'Foot 2: EA-SY... [Suspension]', startBeat: 1.50, endBeat: 2.48 },
        { footId: 2, label: "Foot 3: I SAID it's", startBeat: 2.48, endBeat: 3.18 },
        { footId: 3, label: 'Foot 4: POS-si-ble', startBeat: 3.18, endBeat: 4.0 }
      ],
      syllables: [
        {
          id: 0,
          text: 'I',
          pre: '',
          preDur: 0.0,
          vowel: 'I',
          ipa: 'aɪ',
          beat: 0.14,
          dur: 0.12,
          stress: 0.22,
          pitchST: -1.5,
          pitchSlope: 0,
          isGhost: true,
          isFinal: false,
          rhymeGroup: 0,
          footId: 0,
          tip: 'Quick pronoun pickup.'
        },
        {
          id: 1,
          text: "DID-n't",
          pre: 'd',
          preDur: 0.04,
          vowel: 'ID',
          ipa: 'ˈdɪdn̩t',
          beat: 0.34,
          dur: 0.28,
          stress: 0.72,
          pitchST: 2.2,
          pitchSlope: -0.8,
          isGhost: false,
          isFinal: false,
          rhymeGroup: 1,
          footId: 0,
          tip: 'Secondary negative stress with syllabic nasal release /dn̩t/.'
        },
        {
          id: 2,
          text: 'say',
          pre: 's',
          preDur: 0.04,
          vowel: 'ay',
          ipa: 'seɪ',
          beat: 0.72,
          dur: 0.13,
          stress: 0.24,
          pitchST: -1.8,
          pitchSlope: 0,
          isGhost: true,
          isFinal: false,
          rhymeGroup: 0,
          footId: 0,
          tip: 'De-accented verb (already presupposed in discourse).'
        },
        {
          id: 3,
          text: 'it',
          pre: '',
          preDur: 0.0,
          vowel: 'it',
          ipa: 'ɪt',
          beat: 0.94,
          dur: 0.10,
          stress: 0.14,
          pitchST: -2.2,
          pitchSlope: 0,
          isGhost: true,
          isFinal: false,
          rhymeGroup: 0,
          footId: 0,
          tip: 'Rapid function word in the low-energy trough.'
        },
        {
          id: 4,
          text: 'was',
          pre: 'w',
          preDur: 0.03,
          vowel: 'as',
          ipa: 'wəz',
          beat: 1.12,
          dur: 0.11,
          stress: 0.15,
          pitchST: -2.5,
          pitchSlope: 0,
          isGhost: true,
          isFinal: false,
          rhymeGroup: 0,
          footId: 0,
          tip: 'Compressed /wəz/ launching the contrastive peak on EA-SY.'
        },
        {
          id: 5,
          text: 'EA-SY...',
          pre: '',
          preDur: 0.0,
          vowel: 'EA-SY',
          ipa: 'ˈiːzi',
          beat: 1.52,
          dur: 0.54,
          stress: 1.00,
          pitchST: 5.5,
          pitchSlope: 2.4,
          isGhost: false,
          isFinal: true,
          hasPauseAfter: true,
          pauseBeats: 0.40,
          rhymeGroup: 2,
          footId: 1,
          tip: 'Contrastive Peak #1 with fall-rise continuation contour (+5.5 ST) and suspension pause!'
        },
        {
          id: 6,
          text: 'I',
          pre: '',
          preDur: 0.0,
          vowel: 'I',
          ipa: 'aɪ',
          beat: 2.48,
          dur: 0.11,
          stress: 0.20,
          pitchST: -1.5,
          pitchSlope: 0,
          isGhost: true,
          isFinal: false,
          rhymeGroup: 0,
          footId: 2,
          tip: 'Post-pause pickup pronoun.'
        },
        {
          id: 7,
          text: 'SAID',
          pre: 's',
          preDur: 0.06,
          vowel: 'AID',
          ipa: 'ˈsɛd',
          beat: 2.66,
          dur: 0.26,
          stress: 0.78,
          pitchST: 2.5,
          pitchSlope: 0,
          isGhost: false,
          isFinal: false,
          rhymeGroup: 1,
          footId: 2,
          tip: 'Emphatic verum focus supporting the counter-claim.'
        },
        {
          id: 8,
          text: "it's",
          pre: '',
          preDur: 0.0,
          vowel: "it's",
          ipa: 'ɪts',
          beat: 2.98,
          dur: 0.11,
          stress: 0.16,
          pitchST: -2.0,
          pitchSlope: 0,
          isGhost: true,
          isFinal: false,
          rhymeGroup: 0,
          footId: 2,
          tip: 'Compressed contraction before the /pʰ/ aspiration on POS-.'
        },
        {
          id: 9,
          text: 'POS-',
          pre: 'p',
          preDur: 0.09,
          vowel: 'OS',
          ipa: 'ˈpʰɑːs',
          beat: 3.24,
          dur: 0.36,
          stress: 1.00,
          pitchST: 5.2,
          pitchSlope: -4.8,
          isGhost: false,
          isFinal: false,
          rhymeGroup: 3,
          footId: 3,
          tip: 'Contrastive Nuclear Punch #2: strong /pʰ/ aspiration lead-in with decisive falling pitch!'
        },
        {
          id: 10,
          text: 'si-ble',
          pre: 's',
          preDur: 0.03,
          vowel: 'ible',
          ipa: 'əbəl',
          beat: 3.66,
          dur: 0.26,
          stress: 0.24,
          pitchST: -2.2,
          pitchSlope: -1.5,
          isGhost: true,
          isFinal: true,
          rhymeGroup: 0,
          footId: 3,
          tip: 'Compressed post-nuclear tail /əbəl/.'
        }
      ]
    },

    // -------------------------------------------------------------------------
    // VIBE 3: Expressive Storytelling / Narrative
    // "Slow-ly the DOOR creaked O-pen... and vanished in the DARK"
    // -------------------------------------------------------------------------
    {
      id: 3,
      vibeId: 'narrative',
      title: 'Slow-ly the DOOR creaked O-pen... and vanished in the DARK',
      subtitle: 'Elastic Narrative Rubato, Drawn-Out Suspense & Action Acceleration',
      category: '4. Expressive Storytelling / Narrative',
      focus: 'Suspenseful Vowel Stretching, Dramatic Pause & Fast Action Burst',
      totalBeats: 4.0,
      defaultBpm: 78,
      bpm: 78,
      recommendedGroove: 'narrative',
      ipa: '/ˈsloʊli ðə ˈdɔːɹ ˈkɹiːkt ˈoʊpən ... ənd ˈvænɪʃt ɪn ðə ˈdɑːɹk/',
      pedagogicalFocus:
        'Narrative storytelling uses elastic tempo rubato within a single utterance: "SLOW-ly", "DOOR", and "O-pen..." ' +
        'stretch out with rich /sl/ and /kr/ clusters and a suspense pause, then "and VA-nished in the" accelerates rapidly ' +
        'before dropping into the deep clause-final "DARK".',
      rhetoricalPause: {
        afterSyllableId: 5,
        startBeat: 2.28,
        endBeat: 2.70,
        durationMs: 390,
        label: 'Dramatic Suspense Pause'
      },
      feet: [
        { footId: 0, label: 'Foot 1: SLOW-ly the', startBeat: 0.0, endBeat: 0.88 },
        { footId: 1, label: 'Foot 2: DOOR CREAKED', startBeat: 0.88, endBeat: 1.72 },
        { footId: 2, label: 'Foot 3: O-pen... [Suspense]', startBeat: 1.72, endBeat: 2.70 },
        { footId: 3, label: 'Foot 4: and VA-nished in the DARK', startBeat: 2.70, endBeat: 4.0 }
      ],
      syllables: [
        {
          id: 0,
          text: 'SLOW-',
          pre: 'sl',
          preDur: 0.11,
          vowel: 'OW',
          ipa: 'ˈsloʊ',
          beat: 0.18,
          dur: 0.38,
          stress: 0.90,
          pitchST: 3.0,
          pitchSlope: 1.8,
          isGhost: false,
          isFinal: false,
          rhymeGroup: 1,
          footId: 0,
          tip: 'Iconic expressive lengthening: initiate /sl/ glide early and stretch the /oʊ/ diphthong.'
        },
        {
          id: 1,
          text: 'ly',
          pre: 'l',
          preDur: 0.03,
          vowel: 'y',
          ipa: 'li',
          beat: 0.60,
          dur: 0.12,
          stress: 0.22,
          pitchST: 1.0,
          pitchSlope: 0,
          isGhost: true,
          isFinal: false,
          rhymeGroup: 0,
          footId: 0,
          tip: 'Light adverbial suffix.'
        },
        {
          id: 2,
          text: 'the',
          pre: 'th',
          preDur: 0.03,
          vowel: 'e',
          ipa: 'ðə',
          beat: 0.75,
          dur: 0.10,
          stress: 0.15,
          pitchST: -1.5,
          pitchSlope: 0,
          isGhost: true,
          isFinal: false,
          rhymeGroup: 0,
          footId: 0,
          tip: 'Quick article before DOOR.'
        },
        {
          id: 3,
          text: 'DOOR',
          pre: 'd',
          preDur: 0.05,
          vowel: 'OOR',
          ipa: 'ˈdɔːɹ',
          beat: 0.92,
          dur: 0.34,
          stress: 0.86,
          pitchST: 2.6,
          pitchSlope: -0.5,
          isGhost: false,
          isFinal: false,
          rhymeGroup: 1,
          footId: 1,
          tip: 'Heavy noun head anchoring Foot 2.'
        },
        {
          id: 4,
          text: 'CREAKED',
          pre: 'kr',
          preDur: 0.10,
          vowel: 'EAKED',
          ipa: 'ˈkɹiːkt',
          beat: 1.34,
          dur: 0.32,
          stress: 0.88,
          pitchST: 3.8,
          pitchSlope: 1.2,
          isGhost: false,
          isFinal: false,
          rhymeGroup: 2,
          footId: 1,
          tip: 'Start /kr/ cluster 0.10 beats early; high tense /iː/ evokes the creaking hinge.'
        },
        {
          id: 5,
          text: 'O-pen...',
          pre: '',
          preDur: 0.0,
          vowel: 'O-pen',
          ipa: 'ˈoʊpən',
          beat: 1.76,
          dur: 0.52,
          stress: 0.98,
          pitchST: 4.5,
          pitchSlope: -1.5,
          isGhost: false,
          isFinal: true,
          hasPauseAfter: true,
          pauseBeats: 0.42,
          rhymeGroup: 1,
          footId: 2,
          tip: 'Lengthened suspense vowel followed by a dramatic ~390ms narrative pause gate!'
        },
        {
          id: 6,
          text: 'and',
          pre: '',
          preDur: 0.0,
          vowel: 'and',
          ipa: 'ənd',
          beat: 2.70,
          dur: 0.10,
          stress: 0.16,
          pitchST: -1.8,
          pitchSlope: 0,
          isGhost: true,
          isFinal: false,
          rhymeGroup: 0,
          footId: 3,
          tip: 'Post-pause pickup launching the sudden action burst.'
        },
        {
          id: 7,
          text: 'VA-nished',
          pre: 'v',
          preDur: 0.05,
          vowel: 'A-nished',
          ipa: 'ˈvænɪʃt',
          beat: 2.86,
          dur: 0.28,
          stress: 0.88,
          pitchST: 3.4,
          pitchSlope: -1.8,
          isGhost: false,
          isFinal: false,
          rhymeGroup: 3,
          footId: 3,
          tip: 'Rapid action burst: brisker vowel duration conveys sudden disappearance.'
        },
        {
          id: 8,
          text: 'in',
          pre: '',
          preDur: 0.0,
          vowel: 'in',
          ipa: 'ɪn',
          beat: 3.20,
          dur: 0.10,
          stress: 0.15,
          pitchST: -1.6,
          pitchSlope: 0,
          isGhost: true,
          isFinal: false,
          rhymeGroup: 0,
          footId: 3,
          tip: 'Accelerated function word.'
        },
        {
          id: 9,
          text: 'the',
          pre: 'th',
          preDur: 0.03,
          vowel: 'e',
          ipa: 'ðə',
          beat: 3.34,
          dur: 0.10,
          stress: 0.14,
          pitchST: -2.2,
          pitchSlope: 0,
          isGhost: true,
          isFinal: false,
          rhymeGroup: 0,
          footId: 3,
          tip: 'Ultra-short article before DARK.'
        },
        {
          id: 10,
          text: 'DARK',
          pre: 'd',
          preDur: 0.06,
          vowel: 'ARK',
          ipa: 'ˈdɑːɹk',
          beat: 3.52,
          dur: 0.46,
          stress: 1.00,
          pitchST: 1.5,
          pitchSlope: -5.0,
          isGhost: false,
          isFinal: true,
          rhymeGroup: 3,
          footId: 3,
          tip: 'Deep, low-register falling finality (-5.0 ST slope) closing the story.'
        }
      ]
    }
  ];

  /**
   * Apply any of the 4 Discourse Vibe cadences to a phrase so the user can hear/inspect
   * how a phrase's prosodic timing shifts across registers.
   */
  function applyVibeCadence(phraseOrId, vibeKey) {
    const basePhrase = typeof phraseOrId === 'number' ? (PHRASES[phraseOrId] || PHRASES[0]) : (phraseOrId || PHRASES[0]);
    const vibe = GROOVE_STYLES[vibeKey] || SPEECH_VIBES.prepared;
    if (!vibe || basePhrase.vibeId === vibe.id) {
      return basePhrase;
    }

    const clonedSyls = basePhrase.syllables.map(function (syl, idx) {
      const isPickup = idx < 3 && syl.isGhost;
      const durScale = syl.isGhost
        ? (isPickup ? vibe.anacrusisCompression : 0.95)
        : (syl.isFinal ? vibe.pauseGateMultiplier : vibe.stressContrast);
      return Object.assign({}, syl, {
        dur: Number(Math.max(0.08, syl.dur * durScale).toFixed(3)),
        stress: syl.isGhost
          ? Math.max(0.12, Number((syl.stress * vibe.anacrusisCompression).toFixed(2)))
          : Math.min(1.0, Number((syl.stress * vibe.stressContrast).toFixed(2))),
        pitchST: Number((syl.pitchST * vibe.pitchRangeScale).toFixed(2)),
        pitchSlope: Number((syl.pitchSlope * vibe.pitchRangeScale).toFixed(2))
      });
    });

    return Object.assign({}, basePhrase, {
      activeVibe: vibe.id,
      defaultBpm: vibe.defaultBpm,
      bpm: vibe.defaultBpm,
      syllables: clonedSyls
    });
  }

  // ============================================================================
  // 2. 5 UNMISTAKABLE DYSFLUENT & LEARNER COMPARISON PROFILES + LIVE RECORDED
  // ============================================================================

  function deterministicJitter(phraseId, sylId, scale) {
    const seed = Math.sin((phraseId + 1) * 97.13 + (sylId + 1) * 53.71) * 10000;
    const frac = seed - Math.floor(seed);
    return (frac - 0.5) * 2 * scale;
  }

  const liveRecordedStore = {};

  const ERROR_PROFILES = {
    // -------------------------------------------------------------------------
    // PROFILE 1: Dysfluent Mid-Foot Hesitation Block + Prolongation ("uh...")
    // -------------------------------------------------------------------------
    dysfluent_hesitation: {
      id: 'dysfluent_hesitation',
      name: 'Dysfluent: Mid-Foot Hesitation Block + Prolongation ("uh...")',
      shortLabel: 'Mid-Foot Block + Prolongation',
      badgeColor: '#f43f5e',
      speakingRate: 0.88,
      description:
        'Prolongs a function word ("on theeee..." or "what..." by 2.6× duration) while searching for the next lexical word, ' +
        'inserts a 450ms silent/filled hesitation block ([⚡ 450ms Block]) right before the key content word (tearing the prosodic foot apart!), ' +
        'and then rushes/clutters the remaining syllables to catch up.',
      generate: function (phrase) {
        const rate = this.speakingRate;
        const syls = phrase.syllables;
        // Identify the function word at index 5 or 6 right before a major content word (index 6 or 7)
        let prolongedIdx = 5;
        for (let i = 3; i < syls.length - 2; i++) {
          if (syls[i].isGhost && !syls[i + 1].isGhost) {
            prolongedIdx = i;
            break;
          }
        }
        const blockTargetIdx = prolongedIdx + 1;
        const blockBeats = 0.65; // ~450ms hesitation block tearing the prosodic foot apart

        return syls.map(function (syl, idx) {
          const jitter = deterministicJitter(phrase.id + 5, syl.id, 0.012);
          let normBeat = syl.beat + jitter;
          let normDur = syl.dur;
          let stress = syl.stress;
          let pitchST = syl.pitchST;
          let pitchSlope = syl.pitchSlope;
          let dysfluencyTag = null;
          let errorTag = 'Normal Flow';
          let hesitationBlockBeats = 0;
          let hesitationBlockMs = 0;

          if (idx === prolongedIdx) {
            // Draw out function word by 2.6x ("theeee...", "whaaat...", "waaas...")
            normDur = Number((syl.dur * 2.6).toFixed(3));
            stress = Math.min(0.75, syl.stress + 0.42);
            pitchST = -0.5;
            pitchSlope = -1.2; // Creaky falling drawl
            dysfluencyTag = 'prolongation';
            errorTag = 'Prolonged Function Word (2.6× "' + syl.text + 'eee...")';
          } else if (idx === blockTargetIdx) {
            // Delayed by +0.65 beats (~450ms Hesitation Block right before content word!)
            normBeat = syl.beat + blockBeats;
            normDur = Number((syl.dur * 0.78).toFixed(3));
            stress = Math.min(1.0, syl.stress + 0.08);
            pitchST = syl.pitchST + 0.8;
            dysfluencyTag = 'block';
            hesitationBlockBeats = blockBeats;
            hesitationBlockMs = 450;
            errorTag = '[⚡ 450ms Block] Mid-Foot Hesitation (+0.65b late)';
          } else if (idx > blockTargetIdx) {
            // Post-block clutter rush: speaker compresses and rushes remaining words to catch up
            const remainingFrac = (idx - blockTargetIdx) / Math.max(1, syls.length - 1 - blockTargetIdx);
            const catchupOffset = blockBeats * (1 - remainingFrac * 0.68);
            normBeat = syl.beat + catchupOffset;
            normDur = Number((syl.dur * 0.62).toFixed(3));
            pitchSlope = syl.pitchSlope * 0.4;
            dysfluencyTag = 'clutter_rush';
            errorTag = 'Post-Block Clutter Rush (0.62× clipped catch-up)';
          }

          const rawBeat = normBeat / rate;
          return {
            id: syl.id,
            text: idx === prolongedIdx ? syl.text + 'eee...' : syl.text,
            originalText: syl.text,
            pre: syl.pre,
            preDur: syl.preDur,
            vowel: syl.vowel,
            targetBeat: syl.beat,
            beat: Number(normBeat.toFixed(3)),
            rawBeat: Number(rawBeat.toFixed(3)),
            dur: normDur,
            rawDur: Number((normDur / rate).toFixed(3)),
            stress: stress,
            pitchST: Number(pitchST.toFixed(2)),
            pitchSlope: Number(pitchSlope.toFixed(2)),
            isGhost: syl.isGhost,
            isFinal: syl.isFinal,
            rhymeGroup: syl.rhymeGroup,
            footId: syl.footId,
            speakingRate: rate,
            dysfluencyTag: dysfluencyTag,
            hesitationBlockBeats: hesitationBlockBeats,
            hesitationBlockMs: hesitationBlockMs,
            errorTag: errorTag
          };
        });
      }
    },

    // -------------------------------------------------------------------------
    // PROFILE 2: Dysfluent Initial Repetition / False Start ("p-p-prob...")
    // -------------------------------------------------------------------------
    dysfluent_stutter: {
      id: 'dysfluent_stutter',
      name: 'Dysfluent: Initial Repetition / False Start ("p-p-prob...") + Broken Flow',
      shortLabel: 'Initial Repetition ("p-p-...")',
      badgeColor: '#ec4899',
      speakingRate: 0.85,
      description:
        'Exhibits initial consonant/syllable repetitions ("c-c-CORE", "p-p-PROB", "l-l-LOOK", "h-h-HAP") with 2 rapid false-start bounces, ' +
        'delaying the true P-center vowel arrival by +0.32 beats and flattening the pitch contour into an anxious monotone.',
      generate: function (phrase) {
        const rate = this.speakingRate;
        const syls = phrase.syllables;
        // Pick the 2 most prominent stressed content syllables (preferring ones with onset consonants)
        const stressedIndices = [];
        syls.forEach(function (s, idx) {
          if (!s.isGhost && s.stress >= 0.85 && idx >= 1) {
            stressedIndices.push(idx);
          }
        });
        const repTargets = stressedIndices.slice(-2); // e.g. CORE & PROB- or LOOK & HAP-

        let cumulativeLag = 0;
        return syls.map(function (syl, idx) {
          const isRepTarget = repTargets.indexOf(idx) !== -1;
          const jitter = deterministicJitter(phrase.id + 15, syl.id, 0.01);

          let repetitions = 0;
          let dysfluencyTag = null;
          let preDur = syl.preDur;
          let normDur = syl.dur;
          let errorTag = 'Anxious Flat Pitch';
          let displayLabel = syl.text;

          if (isRepTarget) {
            repetitions = 2;
            dysfluencyTag = 'repetition';
            // +0.32 beat P-center vowel arrival lag due to 2 initial consonant-schwa repetitions
            const repLag = 0.32;
            cumulativeLag = Math.max(cumulativeLag, 0.14);
            const normBeat = syl.beat + repLag + jitter;
            const rawBeat = normBeat / rate;
            preDur = Number(Math.max(0.24, (syl.preDur || 0.06) + 0.22).toFixed(3));
            const onsetChar = (syl.pre || syl.text.charAt(0) || 'p').toLowerCase();
            displayLabel = onsetChar + '-' + onsetChar + '-' + syl.text;
            errorTag = 'Initial Repetition ("' + displayLabel + '", +0.32b P-Center Lag)';

            return {
              id: syl.id,
              text: displayLabel,
              originalText: syl.text,
              pre: syl.pre || onsetChar,
              preDur: preDur,
              vowel: syl.vowel,
              targetBeat: syl.beat,
              beat: Number(normBeat.toFixed(3)),
              rawBeat: Number(rawBeat.toFixed(3)),
              dur: Number((normDur * 0.86).toFixed(3)),
              rawDur: Number(((normDur * 0.86) / rate).toFixed(3)),
              stress: Math.min(1.0, syl.stress + 0.06),
              pitchST: Number((syl.pitchST * 0.38).toFixed(2)),
              pitchSlope: 0,
              isGhost: syl.isGhost,
              isFinal: syl.isFinal,
              rhymeGroup: syl.rhymeGroup,
              footId: syl.footId,
              speakingRate: rate,
              repetitions: repetitions,
              dysfluencyTag: dysfluencyTag,
              errorTag: errorTag
            };
          }

          const normBeat = syl.beat + cumulativeLag + jitter;
          const rawBeat = normBeat / rate;
          return {
            id: syl.id,
            text: syl.text,
            originalText: syl.text,
            pre: syl.pre,
            preDur: syl.preDur,
            vowel: syl.vowel,
            targetBeat: syl.beat,
            beat: Number(normBeat.toFixed(3)),
            rawBeat: Number(rawBeat.toFixed(3)),
            dur: Number((syl.dur * (syl.isGhost ? 1.25 : 0.9)).toFixed(3)),
            rawDur: Number(((syl.dur * (syl.isGhost ? 1.25 : 0.9)) / rate).toFixed(3)),
            stress: syl.isGhost ? Math.min(0.45, syl.stress + 0.16) : syl.stress * 0.88,
            pitchST: Number((syl.pitchST * 0.4).toFixed(2)),
            pitchSlope: 0,
            isGhost: syl.isGhost,
            isFinal: syl.isFinal,
            rhymeGroup: syl.rhymeGroup,
            footId: syl.footId,
            speakingRate: rate,
            repetitions: 0,
            dysfluencyTag: cumulativeLag > 0 ? 'post_repetition_drift' : null,
            errorTag: cumulativeLag > 0 ? 'Broken Foot Flow (+' + cumulativeLag.toFixed(2) + 'b drift)' : errorTag
          };
        });
      }
    },

    // -------------------------------------------------------------------------
    // PROFILE 3: L2 Choppy / Word-by-Word Syllable-Timed (Unreduced Schwas + Glottal Gaps)
    // -------------------------------------------------------------------------
    syllable_timed_choppy: {
      id: 'syllable_timed_choppy',
      name: 'L2 Choppy / Word-by-Word Syllable-Timed (Unreduced Schwas + Glottal Gaps)',
      shortLabel: 'L2 Choppy Syllable-Timed',
      badgeColor: '#f97316',
      speakingRate: 0.78, // Visibly and audibly slower global tempo (1 / 0.78 = 1.28x raw clock time)
      description:
        'Bloats every unstressed function word ("to", "on", "the", "if you") by 2.2× duration and 2.4× loudness, ' +
        'inserts robotic glottal stops between words instead of smooth liaison, and speaks at 0.78× global rate.',
      generate: function (phrase) {
        const rate = this.speakingRate;
        return phrase.syllables.map(function (syl, idx) {
          const isCluster = (syl.pre && syl.pre.length >= 2) || syl.preDur >= 0.08;
          const clusterLag = isCluster ? 0.19 : (syl.preDur > 0.04 ? 0.06 : 0.0);
          const earlyGhosts = phrase.syllables.slice(0, idx).filter(function (s) { return s.isGhost; }).length;
          // Cumulative push from bloated function words + glottal gaps
          const cumulativeGhostPush = earlyGhosts * 0.055;
          const jitter = deterministicJitter(phrase.id, syl.id, 0.01);

          const normBeat = syl.beat + clusterLag + cumulativeGhostPush + jitter;
          const rawBeat = normBeat / rate;

          const normDur = syl.isGhost
            ? Number((syl.dur * 2.2).toFixed(3))
            : syl.isFinal
            ? Number((syl.dur * 0.68).toFixed(3))
            : Number((syl.dur * 0.82).toFixed(3));

          const bloatedStress = syl.isGhost
            ? Math.min(0.78, Number((syl.stress * 2.4).toFixed(2)))
            : Math.max(0.62, Number((syl.stress - 0.16).toFixed(2)));

          return {
            id: syl.id,
            text: syl.text,
            originalText: syl.text,
            pre: syl.pre,
            preDur: isCluster ? Number((syl.preDur * 1.25).toFixed(3)) : syl.preDur,
            vowel: syl.vowel,
            targetBeat: syl.beat,
            beat: Number(normBeat.toFixed(3)),
            rawBeat: Number(rawBeat.toFixed(3)),
            dur: normDur,
            rawDur: Number((normDur / rate).toFixed(3)),
            stress: bloatedStress,
            pitchST: syl.isGhost ? 0.4 : Number((syl.pitchST * 0.35).toFixed(2)),
            pitchSlope: 0,
            isGhost: syl.isGhost,
            isFinal: syl.isFinal,
            rhymeGroup: syl.rhymeGroup,
            footId: syl.footId,
            speakingRate: rate,
            glottalGap: true,
            dysfluencyTag: syl.isGhost ? 'unreduced_schwa' : (isCluster ? 'cluster_lag' : 'glottal_gap'),
            errorTag: syl.isGhost
              ? 'Unreduced Function Word (2.2× dur, 2.4× loud + Glottal Gap)'
              : isCluster
              ? 'Cluster Lag (+0.19b): initiated /' + syl.pre + '/ on beat'
              : 'Choppy Word-by-Word Monotone'
          };
        });
      }
    },

    // -------------------------------------------------------------------------
    // PROFILE 4: Dysfluent Cluttering: Over-Rushed Run-On (Obliterated Pauses & Clipped Vowels)
    // -------------------------------------------------------------------------
    cluttered_runon: {
      id: 'cluttered_runon',
      name: 'Dysfluent Cluttering: Over-Rushed Run-On (Obliterated Pauses & Clipped Vowels)',
      shortLabel: 'Cluttered Run-On (No Pause)',
      badgeColor: '#eab308',
      speakingRate: 1.22, // 22% over-rushed global tempo
      description:
        'Clips stressed vowels to 0.48× duration, completely obliterates the rhetorical/suspense pause gate ' +
        '(−0.45 beats early rush into the next clause!), and slurs unstressed syllables together at 1.22× global speed.',
      generate: function (phrase) {
        const rate = this.speakingRate;
        let seenMidPause = false;
        return phrase.syllables.map(function (syl, idx) {
          const jitter = deterministicJitter(phrase.id + 10, syl.id, 0.014);
          let rushOffset = seenMidPause ? -0.45 : (idx >= 3 ? -0.14 : -0.04);

          if ((syl.hasPauseAfter || syl.isFinal) && idx < phrase.syllables.length - 1) {
            seenMidPause = true;
          } else if (syl.isFinal && idx === phrase.syllables.length - 1 && !seenMidPause) {
            rushOffset = -0.24;
          }

          const normBeat = Math.max(0.04, syl.beat + rushOffset + jitter);
          const rawBeat = normBeat / rate;
          const normDur = !syl.isGhost
            ? Number((syl.dur * 0.48).toFixed(3))
            : Number((syl.dur * 0.65).toFixed(3));

          return {
            id: syl.id,
            text: syl.text,
            originalText: syl.text,
            pre: syl.pre,
            preDur: Number(((syl.preDur || 0) * 0.6).toFixed(3)),
            vowel: syl.vowel,
            targetBeat: syl.beat,
            beat: Number(normBeat.toFixed(3)),
            rawBeat: Number(rawBeat.toFixed(3)),
            dur: normDur,
            rawDur: Number((normDur / rate).toFixed(3)),
            stress: syl.isFinal ? Math.max(0.48, syl.stress - 0.30) : syl.stress * 0.82,
            pitchST: Number((syl.pitchST * 0.5).toFixed(2)),
            pitchSlope: Number((syl.pitchSlope * 0.3).toFixed(2)),
            isGhost: syl.isGhost,
            isFinal: syl.isFinal,
            rhymeGroup: syl.rhymeGroup,
            footId: syl.footId,
            speakingRate: rate,
            dysfluencyTag: seenMidPause && rushOffset <= -0.4 ? 'obliterated_pause' : 'clipped_vowel',
            errorTag: (syl.hasPauseAfter || (syl.isFinal && idx < phrase.syllables.length - 1))
              ? 'Clipped Final Vowel (0.48×) + Obliterated Pause Gate!'
              : rushOffset <= -0.40
              ? 'Run-On Clause Crash (−0.45b early across pause gate)'
              : !syl.isGhost
              ? 'Clipped Stressed Nucleus (0.48× duration)'
              : 'Slurred Telescoped Syllable'
          };
        });
      }
    },

    // -------------------------------------------------------------------------
    // PROFILE 5: 2nd Native Speaker: Natural Expressive Rubato
    // -------------------------------------------------------------------------
    native_expressive: {
      id: 'native_expressive',
      name: '2nd Native Speaker: Natural Expressive Rubato (0.86× Speed, Same Foot Proportions)',
      shortLabel: '2nd Native Speaker (0.86× Rubato)',
      badgeColor: '#10b981',
      speakingRate: 0.86, // 0.86x global speed => raw clock drifts by +350 to +550ms, but DTW locks into Beat Bins!
      description:
        'Speaks at 0.86× global speed with a slightly wider rhetorical pause and +0.08 beat laid-back emphasis on the nuclear word. ' +
        'In Raw Clock Time (0%), it looks shifted by 300–500ms—yet once DTW Tempo Normalization (100%) is applied, ' +
        'its internal stress-foot ratios lock cleanly into the Beat Bins!',
      generate: function (phrase) {
        const rate = this.speakingRate;
        return phrase.syllables.map(function (syl) {
          const micro = deterministicJitter(phrase.id + 30, syl.id, 0.012);
          const isNuclear = !syl.isGhost && syl.stress >= 0.95;
          const rubatoOffset = isNuclear ? 0.065 : (!syl.isGhost && syl.stress >= 0.85 ? 0.025 : 0.0);
          const normBeat = Math.max(0.02, syl.beat + rubatoOffset + micro);
          const rawBeat = normBeat / rate;
          const normDur = syl.isGhost
            ? Number((syl.dur * 0.94).toFixed(3))
            : Number((syl.dur * (isNuclear ? 1.08 : 1.02)).toFixed(3));

          return {
            id: syl.id,
            text: syl.text,
            originalText: syl.text,
            pre: syl.pre,
            preDur: syl.preDur,
            vowel: syl.vowel,
            targetBeat: syl.beat,
            beat: Number(normBeat.toFixed(3)),
            rawBeat: Number(rawBeat.toFixed(3)),
            dur: normDur,
            rawDur: Number((normDur / rate).toFixed(3)),
            stress: syl.stress,
            pitchST: Number((syl.pitchST * 1.06).toFixed(2)),
            pitchSlope: Number((syl.pitchSlope * 1.08).toFixed(2)),
            isGhost: syl.isGhost,
            isFinal: syl.isFinal,
            rhymeGroup: syl.rhymeGroup,
            footId: syl.footId,
            speakingRate: rate,
            dysfluencyTag: 'native_rubato',
            errorTag: isNuclear
              ? 'Expressive Nuclear Rubato (+0.07b inside Beat Bin)'
              : 'In the Pocket (Preserved Foot Ratio)'
          };
        });
      }
    },

    // -------------------------------------------------------------------------
    // PROFILE 6: Live Recorded (Captures Goal 2 User Taps, Bot Runs, or Mic Onsets)
    // -------------------------------------------------------------------------
    live_recorded: {
      id: 'live_recorded',
      name: 'Live Recorded (Your Goal 2 Tapped / Bot / Mic Performance)',
      shortLabel: 'Your Live Recording',
      badgeColor: '#06b6d4',
      speakingRate: 1.0,
      description:
        'Your own syllable timings captured via Spacebar/Click, Virtual Speaker Bot, or Live Mic in Goal 2. ' +
        'Switch to Goal 1 at any time to inspect your P-center alignment, schwa reduction, and Beat Bin accuracy!',
      generate: function (phrase) {
        const saved = liveRecordedStore[phrase.id];
        if (saved && Array.isArray(saved.syllables) && saved.syllables.length === phrase.syllables.length) {
          return saved.syllables.map(function (s) {
            return Object.assign({}, s);
          });
        }
        // Default preview take before user records in Goal 2
        const defaultRate = 0.94;
        return phrase.syllables.map(function (syl) {
          const isCluster = (syl.pre && syl.pre.length >= 2) || syl.preDur >= 0.08;
          const offset = isCluster ? 0.11 : deterministicJitter(phrase.id + 40, syl.id, 0.03);
          const normBeat = Math.max(0.02, syl.beat + offset);
          const rawBeat = normBeat / defaultRate;
          const normDur = syl.isGhost ? Number((syl.dur * 1.3).toFixed(3)) : syl.dur;
          return {
            id: syl.id,
            text: syl.text,
            originalText: syl.text,
            pre: syl.pre,
            preDur: syl.preDur,
            vowel: syl.vowel,
            targetBeat: syl.beat,
            beat: Number(normBeat.toFixed(3)),
            rawBeat: Number(rawBeat.toFixed(3)),
            dur: normDur,
            rawDur: Number((normDur / defaultRate).toFixed(3)),
            stress: syl.stress,
            pitchST: syl.pitchST,
            pitchSlope: syl.pitchSlope,
            isGhost: syl.isGhost,
            isFinal: syl.isFinal,
            rhymeGroup: syl.rhymeGroup,
            footId: syl.footId,
            speakingRate: defaultRate,
            isSimulatedFallback: true,
            errorTag: 'Awaiting Goal 2 Capture (Preview Take)'
          };
        });
      }
    }
  };

  // Backwards-compatible profile aliases so any existing calls to old profile keys resolve cleanly
  ERROR_PROFILES.syllable_timed = ERROR_PROFILES.syllable_timed_choppy;
  ERROR_PROFILES.rushed_pause = ERROR_PROFILES.cluttered_runon;
  ERROR_PROFILES.native_like = ERROR_PROFILES.native_expressive;
  ERROR_PROFILES.dilla_drag = ERROR_PROFILES.native_expressive;

  /**
   * Save user-tapped, virtual-bot, or mic-detected syllable hits from Goal 2 into `ERROR_PROFILES.live_recorded`
   */
  function recordLiveSyllables(phraseId, hitEvents, measuredRate) {
    const phrase = PHRASES[phraseId] || PHRASES[0];
    const targetSpan = phrase.syllables[phrase.syllables.length - 1].beat - phrase.syllables[0].beat;

    const rawBeats = phrase.syllables.map(function (syl, idx) {
      const ev = hitEvents && hitEvents[idx];
      if (typeof ev === 'number' && !isNaN(ev)) return ev;
      if (ev && typeof ev.rawBeat === 'number') return ev.rawBeat;
      if (ev && typeof ev.beat === 'number') return ev.beat;
      return syl.beat;
    });

    const firstRaw = rawBeats[0];
    const lastRaw = rawBeats[rawBeats.length - 1];
    const actualSpan = Math.max(0.25, lastRaw - firstRaw);
    const inferredRate = measuredRate || Number((targetSpan / actualSpan).toFixed(3)) || 1.0;

    const recordedSyllables = phrase.syllables.map(function (syl, idx) {
      const ev = (hitEvents && hitEvents[idx] && typeof hitEvents[idx] === 'object') ? hitEvents[idx] : {};
      const rawBeat = rawBeats[idx];
      const normBeat =
        phrase.syllables[0].beat + (rawBeat - firstRaw) * (targetSpan / actualSpan);

      const dur = typeof ev.dur === 'number' ? ev.dur : syl.dur;
      const delta = normBeat - syl.beat;
      const absDelta = Math.abs(delta);

      let tag = ev.errorTag || 'In the Pocket!';
      if (!ev.errorTag) {
        if (absDelta > 0.14) {
          tag = delta > 0 ? 'Late P-Center (+' + delta.toFixed(2) + 'b)' : 'Rushed P-Center (' + delta.toFixed(2) + 'b)';
        } else if (absDelta > 0.08) {
          tag = delta > 0 ? 'Slightly Behind (+' + delta.toFixed(2) + 'b)' : 'Slightly Ahead (' + delta.toFixed(2) + 'b)';
        }
      }

      return {
        id: syl.id,
        text: ev.text || syl.text,
        originalText: syl.text,
        pre: syl.pre,
        preDur: typeof ev.preDur === 'number' ? ev.preDur : syl.preDur,
        vowel: syl.vowel,
        targetBeat: syl.beat,
        beat: Number(Math.max(0.01, Math.min(4.6, normBeat)).toFixed(3)),
        rawBeat: Number(rawBeat.toFixed(3)),
        dur: Number(dur.toFixed(3)),
        rawDur: Number((dur / inferredRate).toFixed(3)),
        stress: typeof ev.stress === 'number' ? ev.stress : syl.stress,
        pitchST: typeof ev.pitchST === 'number' ? ev.pitchST : syl.pitchST,
        pitchSlope: typeof ev.pitchSlope === 'number' ? ev.pitchSlope : syl.pitchSlope,
        isGhost: syl.isGhost,
        isFinal: syl.isFinal,
        rhymeGroup: syl.rhymeGroup,
        footId: syl.footId,
        speakingRate: inferredRate,
        repetitions: ev.repetitions || 0,
        dysfluencyTag: ev.dysfluencyTag || null,
        hesitationBlockBeats: ev.hesitationBlockBeats || 0,
        hesitationBlockMs: ev.hesitationBlockMs || 0,
        isSimulatedFallback: false,
        errorTag: tag
      };
    });

    liveRecordedStore[phrase.id] = {
      phraseId: phrase.id,
      timestamp: Date.now(),
      speakingRate: inferredRate,
      syllables: recordedSyllables
    };
    ERROR_PROFILES.live_recorded.speakingRate = inferredRate;
    return recordedSyllables;
  }

  /**
   * Generate learner syllables for a given phrase and profile key, respecting `normalizeTempo`
   */
  function generateLearnerSyllables(phraseOrId, profileKey, normalizeTempo) {
    const phrase = typeof phraseOrId === 'number' ? (PHRASES[phraseOrId] || PHRASES[0]) : (phraseOrId || PHRASES[0]);
    const profile = ERROR_PROFILES[profileKey] || ERROR_PROFILES.dysfluent_hesitation;
    const normalize = normalizeTempo !== undefined ? Boolean(normalizeTempo) : true;
    const list = profile.generate(phrase);

    return list.map(function (item) {
      const activeBeat = normalize ? item.beat : item.rawBeat;
      const activeDur = normalize ? item.dur : item.rawDur;
      const deltaBeat = Number((activeBeat - item.targetBeat).toFixed(3));
      return Object.assign({}, item, {
        displayBeat: activeBeat,
        displayDur: activeDur,
        deltaBeat: deltaBeat
      });
    });
  }

  /**
   * Compute acoustic & prosodic rhythm metrics (nPVI, %V, Beat Bin hit rate, Schwa Contrast, Pause Preservation, Fluency Index)
   */
  function computeRhythmMetrics(phraseOrId, learnerSyllables, normalizeTempo, beatBinTolerance) {
    const phrase = typeof phraseOrId === 'number' ? (PHRASES[phraseOrId] || PHRASES[0]) : (phraseOrId || PHRASES[0]);
    const tol = typeof beatBinTolerance === 'number' ? beatBinTolerance : 0.095;
    const normalize = normalizeTempo !== undefined ? Boolean(normalizeTempo) : true;

    function calcNPVI(durs) {
      if (!durs || durs.length < 2) return 0;
      let sum = 0;
      for (let i = 0; i < durs.length - 1; i++) {
        const d1 = Math.max(0.01, durs[i]);
        const d2 = Math.max(0.01, durs[i + 1]);
        sum += Math.abs((d1 - d2) / ((d1 + d2) / 2));
      }
      return Number(((100 * sum) / (durs.length - 1)).toFixed(1));
    }

    function calcPercentV(syls, useDisplay) {
      let vowelSum = 0;
      let consonantSum = 0;
      syls.forEach(function (s) {
        const vDur = useDisplay && typeof s.displayDur === 'number' ? s.displayDur : s.dur;
        const cDur = (s.preDur || 0.03) + 0.03;
        vowelSum += vDur;
        consonantSum += cDur;
      });
      return Number(((vowelSum / Math.max(0.1, vowelSum + consonantSum)) * 100).toFixed(1));
    }

    const nativeDurs = phrase.syllables.map(function (s) { return s.dur; });
    const learnerDurs = learnerSyllables.map(function (s) {
      return normalize ? s.dur : (s.rawDur || s.dur);
    });

    const nativeNPVI = calcNPVI(nativeDurs);
    const learnerNPVI = calcNPVI(learnerDurs);
    const nativePercentV = calcPercentV(phrase.syllables, false);
    const learnerPercentV = calcPercentV(learnerSyllables, true);

    let inBinCount = 0;
    let totalAbsError = 0;
    let clusterErrorSum = 0;
    let clusterCount = 0;
    let dysfluencyCount = 0;

    learnerSyllables.forEach(function (ls, idx) {
      const target = phrase.syllables[idx] || ls;
      const b = normalize ? ls.beat : (ls.rawBeat !== undefined ? ls.rawBeat : ls.beat);
      const err = Math.abs(b - target.beat);
      totalAbsError += err;
      if (err <= tol) {
        inBinCount++;
      }
      if ((target.pre && target.pre.length >= 2) || target.preDur >= 0.08) {
        clusterErrorSum += (b - target.beat);
        clusterCount++;
      }
      if (ls.dysfluencyTag && ls.dysfluencyTag !== 'native_rubato') {
        dysfluencyCount++;
      }
    });

    const pocketScore = Math.round((inBinCount / Math.max(1, learnerSyllables.length)) * 100);
    const meanBeatError = Number((totalAbsError / Math.max(1, learnerSyllables.length)).toFixed(3));
    const meanClusterLag = clusterCount > 0 ? Number((clusterErrorSum / clusterCount).toFixed(3)) : 0;

    const ghostDurs = learnerSyllables.filter(function (s) { return s.isGhost; }).map(function (s) { return s.dur; });
    const stressedDurs = learnerSyllables.filter(function (s) { return !s.isGhost; }).map(function (s) { return s.dur; });
    const avgGhost = ghostDurs.length ? ghostDurs.reduce(function (a, b) { return a + b; }, 0) / ghostDurs.length : 0.13;
    const avgStressed = stressedDurs.length ? stressedDurs.reduce(function (a, b) { return a + b; }, 0) / stressedDurs.length : 0.38;
    const contrastRatio = Number((avgStressed / Math.max(0.05, avgGhost)).toFixed(2));

    return {
      nativeNPVI: nativeNPVI,
      learnerNPVI: learnerNPVI,
      nativePercentV: nativePercentV,
      learnerPercentV: learnerPercentV,
      pocketScore: pocketScore,
      inBinCount: inBinCount,
      totalSyllables: learnerSyllables.length,
      meanBeatError: meanBeatError,
      meanClusterLag: meanClusterLag,
      contrastRatio: contrastRatio,
      dysfluencyCount: dysfluencyCount,
      speakingRate: (learnerSyllables[0] && learnerSyllables[0].speakingRate) || 1.0
    };
  }

  // ============================================================================
  // 3. WEB AUDIO PROSODIC VOICE & DYSFLUENCY SYNTHESIZER (`GrooveAudioEngine`)
  // ============================================================================

  class GrooveAudioEngine {
    constructor() {
      this.ctx = null;
      this.masterGain = null;
      this.bpm = 84;
      this.grooveStyle = 'prepared';
      this.isPlaying = false;
      this.playVocalCues = true;
      this.callAndResponseMode = false;
      this.currentPhrase = PHRASES[0];
      this.currentBar = 0;

      // Scheduler & utterance state
      this._schedulerTimer = null;
      this._oneShotTimeout = null;
      this._utteranceRaf = null;
      this._loopStartTime = 0;
      this._scheduledBars = new Set();
      this._onBarCallbacks = [];
      this._activeNodes = [];

      // Live Microphone & 3-Band Spectral / P-Center state
      this.micActive = false;
      this.micStream = null;
      this.analyser = null;
      this.freqData = null;
      this.timeData = null;
      this._prevVowelEnergy = 0;
      this._lastOnsetTimeMs = 0;
      this._onsetCooldownMs = 135;
      this._onsetThreshold = 0.085;
      this._onsetCallbacks = [];
    }

    initContext() {
      if (!this.ctx) {
        const AudioCtx = global.AudioContext || global.webkitAudioContext;
        if (!AudioCtx) return null;
        this.ctx = new AudioCtx();
        this.masterGain = this.ctx.createGain();
        this.masterGain.gain.value = 0.88;
        this.masterGain.connect(this.ctx.destination);
      }
      if (this.ctx.state === 'suspended') {
        try {
          this.ctx.resume();
        } catch (e) {
          // Ignore resume error in headless environments
        }
      }
      return this.ctx;
    }

    setBpm(bpm) {
      this.bpm = Math.max(50, Math.min(150, Number(bpm) || 84));
    }

    // Alias for index.html `setBPM`
    setBPM(bpm) {
      this.setBpm(bpm);
    }

    setGrooveStyle(styleKey) {
      if (GROOVE_STYLES[styleKey]) {
        this.grooveStyle = styleKey;
      }
    }

    setPhrase(phraseOrId) {
      this.currentPhrase = typeof phraseOrId === 'number' ? (PHRASES[phraseOrId] || PHRASES[0]) : (phraseOrId || PHRASES[0]);
      if (this.currentPhrase && this.currentPhrase.defaultBpm) {
        this.bpm = this.currentPhrase.defaultBpm;
      }
    }

    beatsToSeconds(beats) {
      return (60 / this.bpm) * beats;
    }

    getPlayheadState() {
      if (!this.isPlaying || !this.ctx) {
        return { isPlaying: false, beat: 0, barIndex: 0, isResponseBar: false, bpm: this.bpm };
      }
      const elapsedSec = Math.max(0, this.ctx.currentTime - this._loopStartTime);
      const secPerBeat = 60 / this.bpm;
      const totalBeatsElapsed = elapsedSec / secPerBeat;
      const barIndex = Math.floor(totalBeatsElapsed / 4.0);
      const beatInBar = totalBeatsElapsed % 4.0;
      const isResponseBar = this.callAndResponseMode ? (barIndex % 2 === 1) : false;

      return {
        isPlaying: true,
        beat: beatInBar,
        barIndex: barIndex,
        isResponseBar: isResponseBar,
        bpm: this.bpm,
        secPerBeat: secPerBeat
      };
    }

    // ------------------------------------------------------------------------
    // SOFT PROSODIC FOOT PULSE & AFFIRMATIVE FEEDBACK CHIMES
    // ------------------------------------------------------------------------

    playProsodicFootPulse(when, velocity, isMajorAnchor) {
      const ctx = this.initContext();
      if (!ctx) return;
      const vel = velocity !== undefined ? velocity : 0.45;
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();

      osc.type = 'sine';
      const startFreq = isMajorAnchor ? 105 : 82;
      osc.frequency.setValueAtTime(startFreq, when);
      osc.frequency.exponentialRampToValueAtTime(38, when + 0.14);

      gain.gain.setValueAtTime(0.001, when);
      gain.gain.linearRampToValueAtTime(vel * 0.42, when + 0.008);
      gain.gain.exponentialRampToValueAtTime(0.001, when + 0.16);

      osc.connect(gain);
      gain.connect(this.masterGain);
      osc.start(when);
      osc.stop(when + 0.17);
    }

    playFeedbackChime(kind) {
      const ctx = this.initContext();
      if (!ctx) return;
      const now = ctx.currentTime + 0.005;
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = 'triangle';
      const freq = kind === 'pocket' ? 587.33 : 440; // Warm D5 chime
      osc.frequency.setValueAtTime(freq, now);
      osc.frequency.exponentialRampToValueAtTime(freq * 1.25, now + 0.09);

      gain.gain.setValueAtTime(0.001, now);
      gain.gain.linearRampToValueAtTime(0.14, now + 0.005);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.11);

      osc.connect(gain);
      gain.connect(this.masterGain);
      osc.start(now);
      osc.stop(now + 0.12);
    }

    // Legacy percussion helpers kept soft & ergonomic for backwards compatibility
    playKick(when, velocity) {
      this.playProsodicFootPulse(when, velocity !== undefined ? velocity : 0.55, true);
    }

    playSnare(when, velocity, isGhost) {
      this.playWoodblock(when, (velocity !== undefined ? velocity : 0.5) * (isGhost ? 0.35 : 0.65), !isGhost);
    }

    playHat(when, velocity) {
      const ctx = this.initContext();
      if (!ctx) return;
      const vel = (velocity !== undefined ? velocity : 0.25) * 0.3;
      const dur = 0.035;
      const bufferSize = Math.max(64, Math.floor(ctx.sampleRate * dur));
      const noiseBuffer = ctx.createBuffer(1, bufferSize, ctx.sampleRate);
      const output = noiseBuffer.getChannelData(0);
      for (let i = 0; i < bufferSize; i++) {
        output[i] = (Math.random() * 2 - 1) * Math.exp(-i / (ctx.sampleRate * 0.012));
      }
      const src = ctx.createBufferSource();
      src.buffer = noiseBuffer;
      const hp = ctx.createBiquadFilter();
      hp.type = 'highpass';
      hp.frequency.setValueAtTime(5500, when);
      const gain = ctx.createGain();
      gain.gain.setValueAtTime(vel, when);
      gain.gain.exponentialRampToValueAtTime(0.001, when + dur);
      src.connect(hp);
      hp.connect(gain);
      gain.connect(this.masterGain);
      src.start(when);
      src.stop(when + dur + 0.01);
    }

    playWoodblock(when, velocity, isAccent) {
      const ctx = this.initContext();
      if (!ctx) return;
      const vel = velocity !== undefined ? velocity : 0.45;
      const freq = isAccent ? 640 : 480;
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = 'sine';
      osc.frequency.setValueAtTime(freq, when);
      osc.frequency.exponentialRampToValueAtTime(freq * 0.72, when + 0.05);
      gain.gain.setValueAtTime(0.001, when);
      gain.gain.linearRampToValueAtTime(vel * 0.35, when + 0.004);
      gain.gain.exponentialRampToValueAtTime(0.001, when + 0.06);
      osc.connect(gain);
      gain.connect(this.masterGain);
      osc.start(when);
      osc.stop(when + 0.065);
    }

    // ------------------------------------------------------------------------
    // EXPRESSIVE FORMANT VOICE & DYSFLUENCY SYNTHESIZER
    // ------------------------------------------------------------------------

    /**
     * Approximate F1, F2, F3 vowel formant frequencies (Hz) from syllable vowel text / IPA
     */
    _getVowelFormants(syl) {
      const vText = ((syl && syl.vowel) || (syl && syl.text) || '').toUpperCase();
      if (syl && syl.isGhost && syl.dysfluencyTag !== 'unreduced_schwa') {
        return { f1: 500, f2: 1480, f3: 2500 }; // Neutral central schwa /ə/
      }
      if (/EE|EA|I|Y/.test(vText)) {
        return { f1: 300, f2: 2280, f3: 2950 }; // High front /iː/ (NEED, EASY, CREAKED)
      }
      if (/OO|OU|OW|O/.test(vText) && !/ON|OB|OS/.test(vText)) {
        return { f1: 430, f2: 980, f3: 2450 }; // Back rounded /oʊ/, /ɔː/, /ʊ/ (CORE, FOCUS, SLOW, OPEN, LOOK, DOOR)
      }
      if (/ARK|OB|OS|AT|AP|AN/.test(vText)) {
        return { f1: 710, f2: 1520, f3: 2550 }; // Open /ɑː/, /æ/ (PROB, POSSIBLE, HAPPENED, DARK)
      }
      if (/IRST|ER|UR/.test(vText)) {
        return { f1: 470, f2: 1380, f3: 1720 }; // R-colored /ɝː/ (FIRST)
      }
      return { f1: 540, f2: 1620, f3: 2550 };
    }

    /**
     * Synthesize a single syllable's acoustic realization, including authentic dysfluency cues:
     *   - Initial stutter repetitions (`repetitions: 2` -> "c-c-CORE", "p-p-PROB")
     *   - Mid-foot hesitation block (`hesitationBlockBeats > 0` -> tense glottal "uh..." hum before block release)
     *   - Prolonged function word (`dysfluencyTag === 'prolongation'` -> creaky drawn-out vowel)
     *   - Unreduced L2 choppy schwa (`glottalGap: true` -> sharp glottal attack + bloated vowel)
     */
    playSyllableCue(syl, barStartTime, secPerBeat, isLearner) {
      const ctx = this.initContext();
      if (!ctx || !syl) return;

      const beatPos = isLearner
        ? (typeof syl.displayBeat === 'number' ? syl.displayBeat : (typeof syl.rawBeat === 'number' ? syl.rawBeat : syl.beat))
        : syl.beat;
      const durBeats = isLearner
        ? (typeof syl.displayDur === 'number' ? syl.displayDur : (typeof syl.rawDur === 'number' ? syl.rawDur : syl.dur))
        : syl.dur;

      const vowelStart = Math.max(ctx.currentTime + 0.005, barStartTime + beatPos * secPerBeat);
      const vowelDur = Math.max(0.045, durBeats * secPerBeat);
      const preDurSec = Math.max(0, (syl.preDur || 0) * secPerBeat);
      const preStart = Math.max(ctx.currentTime + 0.002, vowelStart - preDurSec);

      // A. Synthesize Initial Stutter Repetitions ("p-p-PROB", "c-c-CORE") if present
      if (isLearner && syl.repetitions && syl.repetitions > 0) {
        const repCount = syl.repetitions;
        const repWindowSec = Math.min(0.32, preDurSec > 0.12 ? preDurSec : 0.24);
        const repStepSec = repWindowSec / repCount;
        const repStartBase = Math.max(ctx.currentTime + 0.002, vowelStart - repWindowSec);

        for (let r = 0; r < repCount; r++) {
          const rTime = repStartBase + r * repStepSec;
          const rDur = Math.min(0.065, repStepSec * 0.62);
          // Consonant plosive/fricative burst
          this._scheduleConsonantNoise(ctx, rTime, rDur * 0.45, syl.pre || 'p', 0.34);
          // Short tense aborted schwa bounce
          this._scheduleFormantVoicing(ctx, rTime + rDur * 0.35, rDur * 0.65, {
            f0Start: 138,
            f0End: 132,
            f1: 490,
            f2: 1450,
            gain: 0.22,
            glottalAttack: true
          });
        }
      }

      // B. Synthesize Mid-Foot Hesitation Block filler ("uh..." tense glottal hum + silence) before blocked content word
      if (isLearner && syl.hesitationBlockBeats && syl.hesitationBlockBeats > 0) {
        const blockSec = syl.hesitationBlockBeats * secPerBeat;
        const uhStart = Math.max(ctx.currentTime + 0.002, vowelStart - blockSec * 0.82);
        const uhDur = Math.min(0.22, blockSec * 0.45);
        this._scheduleFormantVoicing(ctx, uhStart, uhDur, {
          f0Start: 118,
          f0End: 98, // Creaky vocal fry drop ("uhhh...")
          f1: 520,
          f2: 1350,
          gain: 0.20,
          glottalAttack: true
        });
      }

      // C. Pre-beat consonant cluster lead-in ("pr", "sl", "kr", "f", "s", "th")
      if (preDurSec > 0.008 && syl.pre && !(isLearner && syl.repetitions > 0)) {
        const level = syl.pre.length >= 2 ? 0.28 : 0.16;
        this._scheduleConsonantNoise(ctx, preStart, preDurSec, syl.pre, level);
      }

      // D. Main P-Center Vowel Nucleus (3-Formant Glottal Synthesizer)
      const baseHz = 142; // Expressive baritone/alto fundamental
      const startPitchHz = baseHz * Math.pow(2, (syl.pitchST || 0) / 12);
      const endPitchHz = baseHz * Math.pow(2, ((syl.pitchST || 0) + (syl.pitchSlope || 0)) / 12);
      const formants = this._getVowelFormants(syl);

      const isBloatedGhost = isLearner && syl.isGhost && (syl.dysfluencyTag === 'unreduced_schwa' || syl.dysfluencyTag === 'prolongation');
      const peakGain = isBloatedGhost
        ? 0.34
        : syl.isGhost
        ? 0.13
        : 0.25 + (syl.stress || 0.75) * 0.27;

      this._scheduleFormantVoicing(ctx, vowelStart, vowelDur, {
        f0Start: startPitchHz,
        f0End: endPitchHz,
        f1: formants.f1,
        f2: formants.f2,
        f3: formants.f3,
        gain: peakGain,
        glottalAttack: Boolean(syl.glottalGap || isBloatedGhost),
        creakyProlongation: syl.dysfluencyTag === 'prolongation'
      });
    }

    _scheduleConsonantNoise(ctx, startTime, durationSec, preText, level) {
      const safeStart = Math.max(ctx.currentTime, startTime);
      const safeDur = Math.max(0.012, durationSec);
      const bufLen = Math.max(128, Math.floor(ctx.sampleRate * safeDur));
      const noiseBuf = ctx.createBuffer(1, bufLen, ctx.sampleRate);
      const data = noiseBuf.getChannelData(0);
      for (let i = 0; i < bufLen; i++) {
        const env = Math.sin((i / bufLen) * Math.PI);
        data[i] = (Math.random() * 2 - 1) * env;
      }

      const noiseSrc = ctx.createBufferSource();
      noiseSrc.buffer = noiseBuf;

      const bp = ctx.createBiquadFilter();
      bp.type = 'bandpass';
      const isSibilant = /s|sh|ch|tʃ|th|f/i.test(preText || '');
      bp.frequency.setValueAtTime(isSibilant ? 3900 : 1650, safeStart);
      bp.Q.setValueAtTime(2.0, safeStart);

      const cGain = ctx.createGain();
      cGain.gain.setValueAtTime(0.001, safeStart);
      cGain.gain.linearRampToValueAtTime(level || 0.2, safeStart + safeDur * 0.6);
      cGain.gain.exponentialRampToValueAtTime(0.005, safeStart + safeDur);

      noiseSrc.connect(bp);
      bp.connect(cGain);
      cGain.connect(this.masterGain);
      noiseSrc.start(safeStart);
      noiseSrc.stop(safeStart + safeDur + 0.01);
    }

    _scheduleFormantVoicing(ctx, startTime, durationSec, params) {
      const safeStart = Math.max(ctx.currentTime, startTime);
      const safeDur = Math.max(0.035, durationSec);
      const f0Start = params.f0Start || 140;
      const f0End = params.f0End || f0Start;

      const glottal = ctx.createOscillator();
      const subOsc = ctx.createOscillator();
      glottal.type = 'sawtooth';
      subOsc.type = 'sine';

      glottal.frequency.setValueAtTime(f0Start, safeStart);
      glottal.frequency.linearRampToValueAtTime(f0End, safeStart + safeDur);
      subOsc.frequency.setValueAtTime(f0Start, safeStart);
      subOsc.frequency.linearRampToValueAtTime(f0End, safeStart + safeDur);

      // Add subtle vocal fry / creak modulation when prolonging a hesitation vowel ("theeee...")
      if (params.creakyProlongation) {
        const lfo = ctx.createOscillator();
        const lfoGain = ctx.createGain();
        lfo.frequency.setValueAtTime(26, safeStart);
        lfoGain.gain.setValueAtTime(14, safeStart);
        lfo.connect(lfoGain);
        lfoGain.connect(glottal.frequency);
        lfo.start(safeStart);
        lfo.stop(safeStart + safeDur);
      }

      const formant1 = ctx.createBiquadFilter();
      formant1.type = 'bandpass';
      formant1.frequency.setValueAtTime(params.f1 || 520, safeStart);
      formant1.Q.setValueAtTime(4.5, safeStart);

      const formant2 = ctx.createBiquadFilter();
      formant2.type = 'bandpass';
      formant2.frequency.setValueAtTime(params.f2 || 1500, safeStart);
      formant2.Q.setValueAtTime(5.5, safeStart);

      const vGain = ctx.createGain();
      const peak = params.gain || 0.25;
      const attackTime = params.glottalAttack ? 0.004 : Math.min(0.024, safeDur * 0.22);

      vGain.gain.setValueAtTime(0.001, safeStart);
      vGain.gain.linearRampToValueAtTime(peak, safeStart + attackTime);
      vGain.gain.setValueAtTime(peak * 0.86, safeStart + safeDur * 0.68);
      vGain.gain.exponentialRampToValueAtTime(0.001, safeStart + safeDur);

      glottal.connect(formant1);
      glottal.connect(formant2);
      formant1.connect(vGain);
      formant2.connect(vGain);
      subOsc.connect(vGain);
      vGain.connect(this.masterGain);

      glottal.start(safeStart);
      subOsc.start(safeStart);
      glottal.stop(safeStart + safeDur + 0.015);
      subOsc.stop(safeStart + safeDur + 0.015);
    }

    /**
     * Primary API to synthesize and audition ANY Utterance — Native Reference or ANY Dysfluent/Learner Profile!
     * Can be called from Goal 1 or Goal 2 without needing a microphone.
     *
     * @param {Object|number} phraseOrId - Target phrase object or index (0..3)
     * @param {string|Array} [profileKeyOrSyllables='native'] - 'native' | profileKey ('dysfluent_hesitation', etc.) | custom syllable array
     * @param {Object} [options] - `{ onProgress(beat, activeSyllable), onComplete(), normalizeTempo, withFootPulse }`
     */
    playUtterance(phraseOrId, profileKeyOrSyllables, options) {
      const ctx = this.initContext();
      const phrase = typeof phraseOrId === 'number' ? (PHRASES[phraseOrId] || PHRASES[0]) : (phraseOrId || this.currentPhrase || PHRASES[0]);
      const opts = options || {};

      if (this.isPlaying) {
        this.stop();
      }
      this.setPhrase(phrase);

      let isLearner = false;
      let syllablesToPlay = phrase.syllables;

      if (Array.isArray(profileKeyOrSyllables)) {
        syllablesToPlay = profileKeyOrSyllables;
        isLearner = true;
      } else if (
        typeof profileKeyOrSyllables === 'string' &&
        profileKeyOrSyllables !== 'native' &&
        profileKeyOrSyllables !== 'model' &&
        ERROR_PROFILES[profileKeyOrSyllables]
      ) {
        // Default to raw unnormalized timing (`normalizeTempo = false`) when auditioning a profile so rate differences (0.78x, 1.22x, 0.86x) are clearly audible!
        const useNorm = opts.normalizeTempo !== undefined ? Boolean(opts.normalizeTempo) : false;
        syllablesToPlay = generateLearnerSyllables(phrase, profileKeyOrSyllables, useNorm);
        isLearner = true;
      }

      const secPerBeat = 60 / this.bpm;
      let maxEndBeat = 4.0;
      syllablesToPlay.forEach(function (s) {
        const b = isLearner
          ? (typeof s.displayBeat === 'number' ? s.displayBeat : (typeof s.rawBeat === 'number' ? s.rawBeat : s.beat))
          : s.beat;
        const d = isLearner
          ? (typeof s.displayDur === 'number' ? s.displayDur : (typeof s.rawDur === 'number' ? s.rawDur : s.dur))
          : s.dur;
        if (b + d + 0.15 > maxEndBeat) {
          maxEndBeat = b + d + 0.15;
        }
      });

      const totalDurationSec = maxEndBeat * secPerBeat;
      const startTime = ctx ? ctx.currentTime + 0.04 : performance.now() / 1000;
      this.isPlaying = true;
      this._loopStartTime = startTime;

      if (ctx) {
        // 1. Schedule subtle prosodic foot pulses on stressed anchors (unless disabled)
        if (opts.withFootPulse !== false) {
          phrase.syllables.forEach((natSyl) => {
            if (!natSyl.isGhost && natSyl.stress >= 0.80) {
              const pulseTime = startTime + natSyl.beat * secPerBeat;
              this.playProsodicFootPulse(pulseTime, natSyl.stress >= 0.95 ? 0.45 : 0.28, natSyl.stress >= 0.95);
            }
          });
        }

        // 2. Schedule every syllable's formant voice & dysfluency cues
        syllablesToPlay.forEach((syl) => {
          this.playSyllableCue(syl, startTime, secPerBeat, isLearner);
        });
      }

      // 3. Progress tracker for UI playhead synchronization
      const startPerfMs = typeof performance !== 'undefined' ? performance.now() : Date.now();
      if (this._utteranceRaf) {
        clearInterval(this._utteranceRaf);
        this._utteranceRaf = null;
      }

      if (typeof opts.onProgress === 'function') {
        this._utteranceRaf = setInterval(() => {
          if (!this.isPlaying) {
            clearInterval(this._utteranceRaf);
            this._utteranceRaf = null;
            return;
          }
          const elapsedSec = ctx
            ? Math.max(0, ctx.currentTime - startTime)
            : ((typeof performance !== 'undefined' ? performance.now() : Date.now()) - startPerfMs) / 1000;
          const currentBeat = elapsedSec / secPerBeat;
          let activeSyl = null;
          for (let i = 0; i < syllablesToPlay.length; i++) {
            const s = syllablesToPlay[i];
            const b = isLearner ? (s.displayBeat !== undefined ? s.displayBeat : s.beat) : s.beat;
            const d = isLearner ? (s.displayDur !== undefined ? s.displayDur : s.dur) : s.dur;
            if (currentBeat >= b - (s.preDur || 0) && currentBeat <= b + d) {
              activeSyl = s;
              break;
            }
          }
          try {
            opts.onProgress({
              beat: Number(currentBeat.toFixed(3)),
              progress: Math.min(1, elapsedSec / Math.max(0.1, totalDurationSec)),
              activeSyllable: activeSyl,
              isLearner: isLearner
            });
          } catch (e) {
            // Ignore callback error
          }
        }, 35);
      }

      if (this._oneShotTimeout) clearTimeout(this._oneShotTimeout);
      this._oneShotTimeout = setTimeout(() => {
        this.isPlaying = false;
        if (this._utteranceRaf) {
          clearInterval(this._utteranceRaf);
          this._utteranceRaf = null;
        }
        if (typeof opts.onComplete === 'function') {
          try {
            opts.onComplete();
          } catch (e) {
            // Ignore callback error
          }
        }
      }, totalDurationSec * 1000 + 90);

      return {
        phrase: phrase,
        syllables: syllablesToPlay,
        isLearner: isLearner,
        totalBeats: Number(maxEndBeat.toFixed(2)),
        durationSec: Number(totalDurationSec.toFixed(2))
      };
    }

    /**
     * Schedule a 4-beat bar of prosodic foot pulse + vocal cues (used in 2-bar Call & Response loop)
     */
    scheduleBar(barIndex, barStartTime, options) {
      const ctx = this.initContext();
      if (!ctx) return;

      const opts = options || {};
      const secPerBeat = 60 / this.bpm;

      // 1. Soft prosodic foot pulse on main beats and stressed anchors
      for (let beat = 0; beat < 4; beat++) {
        const beatTime = barStartTime + beat * secPerBeat;
        this.playWoodblock(beatTime, beat === 0 ? 0.52 : 0.32, beat === 0);
      }
      if (this.currentPhrase && Array.isArray(this.currentPhrase.syllables)) {
        this.currentPhrase.syllables.forEach((natSyl) => {
          if (!natSyl.isGhost && natSyl.stress >= 0.82) {
            this.playProsodicFootPulse(barStartTime + natSyl.beat * secPerBeat, 0.36, natSyl.stress >= 0.95);
          }
        });
      }

      // 2. Synthesized Formant Vocal Cues on Native Call bars (Bar 0, 2, 4...)
      const isResponseBar = this.callAndResponseMode && (barIndex % 2 === 1);
      const shouldPlayVoice =
        opts.playVocalCues !== undefined
          ? opts.playVocalCues
          : (this.playVocalCues && !isResponseBar);

      if (shouldPlayVoice && this.currentPhrase && Array.isArray(this.currentPhrase.syllables)) {
        const syllablesToPlay = opts.syllables || this.currentPhrase.syllables;
        const isLearner = Boolean(opts.isLearner);
        syllablesToPlay.forEach((syl) => {
          this.playSyllableCue(syl, barStartTime, secPerBeat, isLearner);
        });
      }

      this._onBarCallbacks.forEach(function (cb) {
        try {
          cb({ barIndex: barIndex, barStartTime: barStartTime, isResponseBar: isResponseBar });
        } catch (e) {
          // Ignore callback error
        }
      });
    }

    /**
     * Backwards-compatible one-shot phrase player (routes to `playUtterance`)
     */
    playOneShotPhrase(phraseOrId, learnerSyllablesOrOptions, grooveStyle) {
      if (grooveStyle) this.setGrooveStyle(grooveStyle);
      if (Array.isArray(learnerSyllablesOrOptions) || typeof learnerSyllablesOrOptions === 'string') {
        return this.playUtterance(phraseOrId, learnerSyllablesOrOptions);
      }
      return this.playUtterance(phraseOrId, 'native', learnerSyllablesOrOptions || {});
    }

    /**
     * Start continuous 2-bar Call & Response loop
     */
    startLoop(options) {
      const ctx = this.initContext();
      if (!ctx) return;
      if (this._oneShotTimeout) {
        clearTimeout(this._oneShotTimeout);
        this._oneShotTimeout = null;
      }

      const opts = options || {};
      if (opts.bpm) this.setBpm(opts.bpm);
      if (opts.grooveStyle) this.setGrooveStyle(opts.grooveStyle);
      if (opts.phrase !== undefined) this.setPhrase(opts.phrase);
      if (opts.callAndResponseMode !== undefined) {
        this.callAndResponseMode = Boolean(opts.callAndResponseMode);
      }
      if (opts.playVocalCues !== undefined) {
        this.playVocalCues = Boolean(opts.playVocalCues);
      }

      this.isPlaying = true;
      this._loopStartTime = ctx.currentTime + 0.05;
      this._scheduledBars.clear();

      const lookaheadTick = () => {
        if (!this.isPlaying || !this.ctx) return;
        const secPerBar = (60 / this.bpm) * 4.0;
        const elapsed = this.ctx.currentTime - this._loopStartTime;
        const currentBar = Math.max(0, Math.floor(elapsed / secPerBar));

        for (let b = currentBar; b <= currentBar + 1; b++) {
          const barStart = this._loopStartTime + b * secPerBar;
          if (!this._scheduledBars.has(b) && barStart <= this.ctx.currentTime + 0.25) {
            this._scheduledBars.add(b);
            this.scheduleBar(b, barStart);
          }
        }
      };

      lookaheadTick();
      if (this._schedulerTimer) clearInterval(this._schedulerTimer);
      this._schedulerTimer = setInterval(lookaheadTick, 50);
    }

    // Alias used by `goal2_live_modes.js` (`core.audioEngine.start(...)`)
    start(options) {
      return this.startLoop(options);
    }

    stop() {
      this.isPlaying = false;
      if (this._schedulerTimer) {
        clearInterval(this._schedulerTimer);
        this._schedulerTimer = null;
      }
      if (this._oneShotTimeout) {
        clearTimeout(this._oneShotTimeout);
        this._oneShotTimeout = null;
      }
      if (this._utteranceRaf) {
        clearInterval(this._utteranceRaf);
        this._utteranceRaf = null;
      }
      this._scheduledBars.clear();
    }

    onBarStart(callback) {
      if (typeof callback === 'function') {
        this._onBarCallbacks.push(callback);
      }
    }

    // ------------------------------------------------------------------------
    // LIVE MICROPHONE 3-BAND SPECTRAL ANALYZER & P-CENTER VOWEL ONSET DETECTOR
    // ------------------------------------------------------------------------

    async startMic() {
      this.initContext();
      if (this.micActive && this.analyser) {
        return { active: true, mode: 'live_mic' };
      }

      if (!global.navigator || !global.navigator.mediaDevices || !global.navigator.mediaDevices.getUserMedia) {
        this.micActive = false;
        return { active: false, mode: 'simulated_fallback', reason: 'mediaDevices API unavailable' };
      }

      try {
        const stream = await global.navigator.mediaDevices.getUserMedia({
          audio: {
            echoCancellation: true,
            noiseSuppression: false,
            autoGainControl: false
          }
        });
        this.micStream = stream;
        const source = this.ctx.createMediaStreamSource(stream);
        this.analyser = this.ctx.createAnalyser();
        this.analyser.fftSize = 1024;
        this.analyser.smoothingTimeConstant = 0.55;
        source.connect(this.analyser);

        this.freqData = new Uint8Array(this.analyser.frequencyBinCount);
        this.timeData = new Uint8Array(this.analyser.fftSize);
        this.micActive = true;
        this._prevVowelEnergy = 0;

        return { active: true, mode: 'live_mic' };
      } catch (err) {
        this.micActive = false;
        return {
          active: false,
          mode: 'simulated_fallback',
          reason: err && err.message ? err.message : 'Microphone permission denied'
        };
      }
    }

    stopMic() {
      this.micActive = false;
      if (this.micStream) {
        this.micStream.getTracks().forEach(function (t) {
          t.stop();
        });
        this.micStream = null;
      }
      this.analyser = null;
    }

    onOnset(callback) {
      if (typeof callback === 'function') {
        this._onsetCallbacks.push(callback);
      }
    }

    getMicFrame() {
      if (this.micActive && this.analyser && this.freqData && this.ctx) {
        this.analyser.getByteFrequencyData(this.freqData);
        const nyquist = this.ctx.sampleRate / 2;
        const binCount = this.freqData.length;
        const hzPerBin = nyquist / binCount;

        let lowSum = 0, lowBins = 0;
        let midSum = 0, midBins = 0;
        let highSum = 0, highBins = 0;

        for (let i = 1; i < binCount; i++) {
          const hz = i * hzPerBin;
          const val = this.freqData[i] / 255;
          if (hz < 800) {
            lowSum += val;
            lowBins++;
          } else if (hz <= 3000) {
            midSum += val;
            midBins++;
          } else if (hz <= 8500) {
            highSum += val;
            highBins++;
          }
        }

        const lowRed = Math.min(1, (lowSum / Math.max(1, lowBins)) * 1.45);
        const midGreen = Math.min(1, (midSum / Math.max(1, midBins)) * 1.65);
        const highCyan = Math.min(1, (highSum / Math.max(1, highBins)) * 2.1);

        const vowelBand = lowRed * 0.6 + midGreen * 0.4;
        const flux = vowelBand - this._prevVowelEnergy;
        this._prevVowelEnergy = vowelBand * 0.7 + this._prevVowelEnergy * 0.3;

        const nowMs = typeof performance !== 'undefined' ? performance.now() : Date.now();
        let isVowelOnset = false;
        if (
          flux > this._onsetThreshold &&
          vowelBand > 0.16 &&
          nowMs - this._lastOnsetTimeMs > this._onsetCooldownMs
        ) {
          isVowelOnset = true;
          this._lastOnsetTimeMs = nowMs;
          const playhead = this.getPlayheadState();
          const onsetPayload = {
            beat: playhead.beat,
            barIndex: playhead.barIndex,
            vowelEnergy: vowelBand,
            consonantEnergy: highCyan,
            timestampMs: nowMs
          };
          this._onsetCallbacks.forEach(function (cb) {
            try {
              cb(onsetPayload);
            } catch (e) {
              // Ignore listener errors
            }
          });
        }

        return {
          source: 'live_mic',
          lowRed: Number(lowRed.toFixed(3)),
          midGreen: Number(midGreen.toFixed(3)),
          highCyan: Number(highCyan.toFixed(3)),
          vowelEnergy: Number(vowelBand.toFixed(3)),
          isVowelOnset: isVowelOnset
        };
      }

      // Simulated 3-band spectral envelope from current phrase playhead
      const state = this.getPlayheadState();
      let simLow = 0.02;
      let simMid = 0.02;
      let simHigh = 0.01;
      let isVowelOnset = false;

      if (state.isPlaying && this.currentPhrase && Array.isArray(this.currentPhrase.syllables)) {
        const beat = state.beat;
        this.currentPhrase.syllables.forEach(function (syl) {
          const preStart = syl.beat - (syl.preDur || 0);
          const vowelEnd = syl.beat + syl.dur;

          if (syl.preDur > 0 && beat >= preStart && beat < syl.beat) {
            const p = (beat - preStart) / Math.max(0.01, syl.preDur);
            simHigh = Math.max(simHigh, Math.sin(p * Math.PI) * (syl.pre.length >= 2 ? 0.85 : 0.48));
            simMid = Math.max(simMid, 0.18);
          }

          if (beat >= syl.beat && beat <= vowelEnd) {
            const vProg = (beat - syl.beat) / Math.max(0.02, syl.dur);
            const env = Math.sin(Math.pow(vProg, 0.65) * Math.PI);
            const stressScale = syl.isGhost ? 0.34 : (0.65 + syl.stress * 0.35);
            simLow = Math.max(simLow, env * stressScale * 0.92);
            simMid = Math.max(simMid, env * stressScale * 0.78);
            if (vProg < 0.08) {
              isVowelOnset = true;
            }
          }
        });
      }

      return {
        source: 'simulated',
        lowRed: Number(simLow.toFixed(3)),
        midGreen: Number(simMid.toFixed(3)),
        highCyan: Number(simHigh.toFixed(3)),
        vowelEnergy: Number((simLow * 0.6 + simMid * 0.4).toFixed(3)),
        isVowelOnset: isVowelOnset
      };
    }
  }

  const sharedAudioEngine = new GrooveAudioEngine();

  // ============================================================================
  // EXPORT TO WINDOW.SPEECHRHYTHMCORE
  // ============================================================================
  const SpeechRhythmCore = {
    PHRASES: PHRASES,
    SPEECH_VIBES: SPEECH_VIBES,
    ERROR_PROFILES: ERROR_PROFILES,
    GROOVE_STYLES: GROOVE_STYLES,
    GrooveAudioEngine: GrooveAudioEngine,
    audioEngine: sharedAudioEngine,
    applyVibeCadence: applyVibeCadence,
    recordLiveSyllables: recordLiveSyllables,
    generateLearnerSyllables: generateLearnerSyllables,
    computeRhythmMetrics: computeRhythmMetrics,
    playUtterance: function (phraseOrId, profileKeyOrSyllables, options) {
      return sharedAudioEngine.playUtterance(phraseOrId, profileKeyOrSyllables, options);
    }
  };

  global.SpeechRhythmCore = SpeechRhythmCore;
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = SpeechRhythmCore;
  }
})(typeof window !== 'undefined' ? window : globalThis);
