/**
 * Shared API mocking helpers for E2E tests.
 * Provides canned responses for /api/analyze and /api/select-error
 * so UI behavior can be tested deterministically without a live backend.
 */

const cannedAnalyzeResponse = {
  success: true,
  message: 'Analysis complete',
  errors: [
    {
      error_type: 'substitution',
      target_phoneme: 'p',
      predicted_phoneme: 'b',
      word_context: 'The [p]lace',
    },
    {
      error_type: 'voicing',
      target_phoneme: 'k',
      predicted_phoneme: 'g',
      word_context: 'hot [k]',
    },
  ],
  feedback: '<p>Nice try! Watch for voicing differences.</p>',
  alignment: {
    text: 'The weather is very hot today.',
    total_duration: 1.5,
    overall_score: 0.82,
    words: [
      {
        word: 'The',
        start_time: 0.0,
        end_time: 0.3,
        phonemes: [
          { phoneme: 'D', start_time: 0.0, end_time: 0.1, score: 0.9, is_error: false, predicted_phoneme: 'D', is_vowel: false, is_voiced: true },
          { phoneme: '@', start_time: 0.1, end_time: 0.3, score: 0.85, is_error: false, predicted_phoneme: '@', is_vowel: true, is_voiced: true },
        ],
      },
      {
        word: 'weather',
        start_time: 0.3,
        end_time: 0.7,
        phonemes: [
          { phoneme: 'w', start_time: 0.3, end_time: 0.4, score: 0.8, is_error: false, predicted_phoneme: 'w', is_vowel: false, is_voiced: true },
          { phoneme: 'E', start_time: 0.4, end_time: 0.5, score: 0.75, is_error: false, predicted_phoneme: 'E', is_vowel: true, is_voiced: true },
          { phoneme: 'T', start_time: 0.5, end_time: 0.55, score: 0.7, is_error: false, predicted_phoneme: 'T', is_vowel: false, is_voiced: false },
          { phoneme: '@', start_time: 0.55, end_time: 0.7, score: 0.8, is_error: false, predicted_phoneme: '@', is_vowel: true, is_voiced: true },
        ],
      },
      {
        word: 'is',
        start_time: 0.7,
        end_time: 0.9,
        phonemes: [
          { phoneme: 'I', start_time: 0.7, end_time: 0.8, score: 0.9, is_error: false, predicted_phoneme: 'I', is_vowel: true, is_voiced: true },
          { phoneme: 'z', start_time: 0.8, end_time: 0.9, score: 0.88, is_error: false, predicted_phoneme: 'z', is_vowel: false, is_voiced: true },
        ],
      },
      {
        word: 'very',
        start_time: 0.9,
        end_time: 1.1,
        phonemes: [
          { phoneme: 'v', start_time: 0.9, end_time: 1.0, score: 0.8, is_error: false, predicted_phoneme: 'v', is_vowel: false, is_voiced: true },
          { phoneme: 'E', start_time: 1.0, end_time: 1.1, score: 0.85, is_error: false, predicted_phoneme: 'E', is_vowel: true, is_voiced: true },
        ],
      },
      {
        word: 'hot',
        start_time: 1.1,
        end_time: 1.35,
        phonemes: [
          { phoneme: 'h', start_time: 1.1, end_time: 1.15, score: 0.6, is_error: false, predicted_phoneme: 'h', is_vowel: false, is_voiced: false },
          { phoneme: 'Q', start_time: 1.15, end_time: 1.2, score: 0.5, is_error: true, predicted_phoneme: 'Q', is_vowel: true, is_voiced: true },
          { phoneme: 't', start_time: 1.2, end_time: 1.35, score: 0.7, is_error: true, predicted_phoneme: 't', is_vowel: false, is_voiced: false },
        ],
      },
      {
        word: 'today.',
        start_time: 1.35,
        end_time: 1.5,
        phonemes: [
          { phoneme: 't', start_time: 1.35, end_time: 1.4, score: 0.9, is_error: false, predicted_phoneme: 't', is_vowel: false, is_voiced: false },
          { phoneme: '@', start_time: 1.4, end_time: 1.48, score: 0.88, is_error: false, predicted_phoneme: '@', is_vowel: true, is_voiced: true },
          { phoneme: 'd', start_time: 1.48, end_time: 1.5, score: 0.85, is_error: false, predicted_phoneme: 'd', is_vowel: false, is_voiced: true },
        ],
      },
    ],
  },
  prosody: {
    summary: {
      mean_f0_hz: 190,
      mean_midi: 67,
      mean_note: 'G#4',
      pitch_range_semitones: 8,
      pitch_range_label: 'nice variety',
      npvi: 52.3,
      npvi_label: 'moderate rhythm variety',
      syllable_count: 9,
      duration_seconds: 1.5,
    },
    rhythm: {
      npvi: 52.3,
    },
    pitch: {
      range_semitones: 8,
    },
  },
};

const cannedSelectErrorResponse = {
  incorrect_desc: '<strong>What you\'re doing:</strong> Saying /b/ instead of /p/',
  correct_desc: '<strong>What you should do:</strong> Position tongue for /p/',
  animation_params: {
    left: {
      lip_aperture: 0.0,
      lip_protrusion: 0.43,
      tongue_tip_constriction_location: 0.45,
      tongue_tip_constriction_degree: 0.9,
      lateral_tongue_drop: 0,
      velic_aperture: 0.0,
      tongue_body_constriction_location: 0.55,
      tongue_body_constriction_degree: 0.55,
      glottal_aperture: 3,
    },
    right: {
      lip_aperture: 0.0,
      lip_protrusion: 0.43,
      tongue_tip_constriction_location: 0.45,
      tongue_tip_constriction_degree: 0.9,
      lateral_tongue_drop: 0,
      velic_aperture: 0.0,
      tongue_body_constriction_location: 0.55,
      tongue_body_constriction_degree: 0.55,
      glottal_aperture: 18,
    },
  },
  highlight_params: { zone: 'glottis' },
};

/**
 * Mock the /api/analyze endpoint with a canned response.
 * Uses a URL pattern that matches query params (cache-busting timestamp).
 * @param {import('@playwright/test').Page} page
 * @param {Partial<cannedAnalyzeResponse>} [overrides]
 */
async function mockAnalyze(page, overrides = {}) {
  const body = { ...cannedAnalyzeResponse, ...overrides };
  await page.route(/\/api\/analyze/, async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(body) });
  });
}

/**
 * Mock the /api/select-error endpoint with a canned response.
 * @param {import('@playwright/test').Page} page
 * @param {Partial<cannedSelectErrorResponse>} [overrides]
 */
async function mockSelectError(page, overrides = {}) {
  const body = { ...cannedSelectErrorResponse, ...overrides };
  await page.route(/\/api\/select-error/, async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(body) });
  });
}

/**
 * Mock prosody-lab analyze endpoint.
 * @param {import('@playwright/test').Page} page
 * @param {object} [overrides]
 */
async function mockProsodyLabAnalyze(page, overrides = {}) {
  const body = {
    success: true,
    summary: {
      mean_f0_hz: 180,
      mean_midi: 66,
      mean_note: 'F4',
      pitch_range_semitones: 10,
      pitch_range_label: 'nice variety',
      npvi: 48.1,
      npvi_label: 'moderate rhythm variety',
      syllable_count: 7,
      duration_seconds: 1.2,
    },
    pitch_track: [
      { time: 0.0, midi: 65, f0_hz: 174.6, note: 'F4', confidence: 0.9 },
      { time: 0.2, midi: 67, f0_hz: 196.0, note: 'G4', confidence: 0.88 },
      { time: 0.4, midi: 69, f0_hz: 220.0, note: 'A4', confidence: 0.85 },
    ],
    syllable_onsets: [0.0, 0.2, 0.4, 0.55, 0.7, 0.85, 1.0],
    rhythm: { npvi: 48.1 },
    pitch: { range_semitones: 10 },
    ...overrides,
  };
  await page.route(/\/api\/prosody-lab\/analyze/, async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(body) });
  });
}

module.exports = {
  cannedAnalyzeResponse,
  cannedSelectErrorResponse,
  mockAnalyze,
  mockSelectError,
  mockProsodyLabAnalyze,
};
