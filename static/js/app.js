import { SvgArticulatoryRenderer } from './svg_articulatory_renderer.js';
import { IPATooltips } from './ipa_tooltips.js';
import { IntercomRecorder } from './recorder.js';
const USE_SVG_RENDERER = true;

function debounce(fn, delay) {
  let timer = null;
  return function debounced(...args) {
    if (timer) clearTimeout(timer);
    timer = setTimeout(() => fn.apply(this, args), delay);
  };
}

window.__USE_SVG_RENDERER__ = USE_SVG_RENDERER;
window.IPATooltips = IPATooltips;
window.IntercomRecorder = IntercomRecorder;

const DEFAULT_SVG_STATE = window.SvgArticulatoryDefaultState || {
  lip_aperture: 0.25,
  lip_protrusion: 0.71,
  tongue_tip_constriction_location: 0.2,
  tongue_tip_constriction_degree: 1,
  lateral_tongue_drop: 0,
  velic_aperture: 0,
  tongue_body_constriction_location: 0.7,
  tongue_body_constriction_degree: 1,
  glottal_aperture: 0,
};

window.currentTab = 'analysis';
window.currentAnimationParams = { left: { ...DEFAULT_SVG_STATE }, right: { ...DEFAULT_SVG_STATE } };
window.currentHighlightParams = { zone: null };
window.selectedPhoneme = null;
window.svgAnimationRenderer = null;
window.svgLeftRenderer = null;
window.svgRightRenderer = null;

const SvgPhonemePresets = window.__PHONEME_PRESETS__ || {};
window.SvgPhonemePresets = SvgPhonemePresets;

function normalizeTongueDegree(value, legacyRestDistance) {
  const numericValue = Number(value);
  if (!Number.isFinite(numericValue)) return 1;
  if (numericValue <= 1) return Math.max(0, Math.min(1, numericValue));
  return Math.max(0, Math.min(1, numericValue / legacyRestDistance));
}

function normalizeScalar(value, legacyMax, fallback) {
  const numericValue = Number(value);
  if (!Number.isFinite(numericValue)) return fallback;
  if (numericValue <= 1) return Math.max(0, Math.min(1, numericValue));
  return Math.max(0, Math.min(1, numericValue / legacyMax));
}

function normalizeSvgState(state = {}) {
  return {
    ...DEFAULT_SVG_STATE,
    ...state,
    lip_aperture: normalizeScalar(
      state.lip_aperture ?? DEFAULT_SVG_STATE.lip_aperture,
      40,
      DEFAULT_SVG_STATE.lip_aperture,
    ),
    lip_protrusion: normalizeScalar(
      state.lip_protrusion ?? DEFAULT_SVG_STATE.lip_protrusion,
      14,
      DEFAULT_SVG_STATE.lip_protrusion,
    ),
    tongue_tip_constriction_degree: normalizeTongueDegree(
      state.tongue_tip_constriction_degree ?? DEFAULT_SVG_STATE.tongue_tip_constriction_degree,
      40,
    ),
    velic_aperture: normalizeScalar(
      state.velic_aperture ?? DEFAULT_SVG_STATE.velic_aperture,
      40,
      DEFAULT_SVG_STATE.velic_aperture,
    ),
    tongue_body_constriction_degree: normalizeTongueDegree(
      state.tongue_body_constriction_degree ?? DEFAULT_SVG_STATE.tongue_body_constriction_degree,
      30,
    ),
  };
}

function getSvgControlState() {
  return normalizeSvgState({
    lip_aperture: Number(document.getElementById('la-slider')?.value ?? DEFAULT_SVG_STATE.lip_aperture),
    lip_protrusion: Number(document.getElementById('lp-slider')?.value ?? DEFAULT_SVG_STATE.lip_protrusion),
    tongue_tip_constriction_location: Number(document.getElementById('ttcl-slider')?.value ?? DEFAULT_SVG_STATE.tongue_tip_constriction_location),
    tongue_tip_constriction_degree: Number(document.getElementById('ttcd-slider')?.value ?? DEFAULT_SVG_STATE.tongue_tip_constriction_degree),
    lateral_tongue_drop: Number(document.getElementById('lat-slider')?.value ?? DEFAULT_SVG_STATE.lateral_tongue_drop),
    velic_aperture: Number(document.getElementById('vel-slider')?.value ?? DEFAULT_SVG_STATE.velic_aperture),
    tongue_body_constriction_location: Number(document.getElementById('tbcl-slider')?.value ?? DEFAULT_SVG_STATE.tongue_body_constriction_location),
    tongue_body_constriction_degree: Number(document.getElementById('tbcd-slider')?.value ?? DEFAULT_SVG_STATE.tongue_body_constriction_degree),
    glottal_aperture: Number(document.getElementById('glo-slider')?.value ?? DEFAULT_SVG_STATE.glottal_aperture),
  });
}

function applySvgControlState(state) {
  const sliderIds = {
    lip_aperture: 'la-slider',
    lip_protrusion: 'lp-slider',
    tongue_tip_constriction_location: 'ttcl-slider',
    tongue_tip_constriction_degree: 'ttcd-slider',
    lateral_tongue_drop: 'lat-slider',
    velic_aperture: 'vel-slider',
    tongue_body_constriction_location: 'tbcl-slider',
    tongue_body_constriction_degree: 'tbcd-slider',
    glottal_aperture: 'glo-slider',
  };

  for (const [key, id] of Object.entries(sliderIds)) {
    const el = document.getElementById(id);
    if (el && Object.prototype.hasOwnProperty.call(state, key)) {
      el.value = String(state[key]);
    }
  }
  updateSliderValueLabels();
}

const SLIDER_VALUE_IDS = {
  'la-slider': 'la-val',
  'lp-slider': 'lp-val',
  'ttcl-slider': 'ttcl-val',
  'ttcd-slider': 'ttcd-val',
  'lat-slider': 'lat-val',
  'vel-slider': 'vel-val',
  'tbcl-slider': 'tbcl-val',
  'tbcd-slider': 'tbcd-val',
  'glo-slider': 'glo-val',
};

function updateSliderValueLabels() {
  for (const [sliderId, labelId] of Object.entries(SLIDER_VALUE_IDS)) {
    const slider = document.getElementById(sliderId);
    const label = document.getElementById(labelId);
    if (slider && label) {
      const v = parseFloat(slider.value);
      label.textContent = v > 1 || v < 0 ? String(Math.round(v)) : v.toFixed(2);
    }
  }
}

function initTooltips() {
  document.querySelectorAll('.phoneme-btn').forEach((btn) => {
    const phoneme = btn.getAttribute('data-phoneme');
    if (!phoneme) return;
    btn.classList.add('ipa-phoneme');
    let tooltip = `/${phoneme}/`;
    const data = IPATooltips[phoneme];
    if (data) {
      const { word, highlight, lang } = data;
      const index = word.toLowerCase().indexOf(highlight.toLowerCase());
      tooltip = index >= 0
        ? `/${phoneme}/ as in ${word.slice(0, index)}**${word.slice(index, index + highlight.length).toUpperCase()}**${word.slice(index + highlight.length)}${lang ? ` (${lang})` : ''}`
        : `/${phoneme}/ as in ${word}${lang ? ` (${lang})` : ''}`;
    }
    btn.setAttribute('data-tooltip', tooltip);
  });
}

function mountSvgRenderers() {
  const animationContainer = document.getElementById('svg-articulatory-animation');
  const leftContainer = document.getElementById('svg-articulatory-left');
  const rightContainer = document.getElementById('svg-articulatory-right');

  if (animationContainer && !window.svgAnimationRenderer) {
    window.svgAnimationRenderer = new SvgArticulatoryRenderer(animationContainer, {
      prefix: 'anim',
      state: getSvgControlState(),
    });
    window.svgAnimationRenderer.mount();
  }

  if (leftContainer && !window.svgLeftRenderer) {
    window.svgLeftRenderer = new SvgArticulatoryRenderer(leftContainer, {
      prefix: 'left',
      state: DEFAULT_SVG_STATE,
    });
    window.svgLeftRenderer.mount();
  }

  if (rightContainer && !window.svgRightRenderer) {
    window.svgRightRenderer = new SvgArticulatoryRenderer(rightContainer, {
      prefix: 'right',
      state: DEFAULT_SVG_STATE,
    });
    window.svgRightRenderer.mount();
  }
}

function setAnimationState(state) {
  const normalizedState = normalizeSvgState(state);
  window.currentAnimationParams.left = { ...normalizedState };
  window.currentAnimationParams.right = { ...normalizedState };
  window.svgAnimationRenderer?.setState(normalizedState);
}

window.switchTab = function switchTab(tabName) {
  window.currentTab = tabName;

  document.querySelectorAll('.tab-btn').forEach((btn) => {
    btn.classList.remove('tab-btn-active', 'text-blue-600', 'border-b-2', 'border-blue-600');
    btn.classList.add('text-gray-500');
  });
  const activeBtn = document.getElementById(`tab-btn-${tabName}`);
  if (activeBtn) {
    activeBtn.classList.add('tab-btn-active', 'text-blue-600', 'border-b-2', 'border-blue-600');
    activeBtn.classList.remove('text-gray-500');
  }

  document.querySelectorAll('.tab-panel').forEach((panel) => panel.classList.add('hidden'));
  const activePanel = document.getElementById(`tab-panel-${tabName}`);
  if (activePanel) activePanel.classList.remove('hidden');

  if (window.svgAnimationRenderer) {
    if (tabName === 'animation') {
      window.svgAnimationRenderer.startAnimation();
    } else {
      window.svgAnimationRenderer.stopAnimation();
    }
  }

  if (tabName === 'prosody' && window.prosodyLabRecorder) {
    window.prosodyLabRecorder.renderFromStorage();
  }

  if (tabName !== 'analysis' && window.recorder?.isRecording) {
    window.recorder.stopRecording();
  }
  if (tabName !== 'prosody' && window.prosodyLabRecorder?.isRecording) {
    window.prosodyLabRecorder.stopRecording();
  }
};

window.initAnimationLab = function initAnimationLab() {
  mountSvgRenderers();
  window.updateAnimationFromSliders();
  return window.svgAnimationRenderer;
};

window.setPhonemePreset = function setPhonemePreset(phoneme) {
  window.selectPhoneme(phoneme);
};

window.updateAnimationFromSliders = debounce(function updateAnimationFromSliders() {
  const state = getSvgControlState();
  setAnimationState(state);
  updateSliderValueLabels();
}, 16);

window.selectPhoneme = function selectPhoneme(phoneme) {
  const preset = SvgPhonemePresets[phoneme] || window.SvgPhonemePresets?.[phoneme] || {
    name: phoneme,
    params: DEFAULT_SVG_STATE,
  };

  const customPresets = JSON.parse(localStorage.getItem('customPhonemePresets') || '{}');
  const presetSource = customPresets[phoneme] || preset;
  const presetParams = normalizeSvgState(
    presetSource.params !== undefined ? presetSource.params : (presetSource.state || DEFAULT_SVG_STATE),
  );

  window.selectedPhoneme = phoneme;
  const selectedPhonemeEl = document.getElementById('selected-phoneme');
  if (selectedPhonemeEl) selectedPhonemeEl.textContent = phoneme;
  const saveBtn = document.getElementById('save-position-btn');
  if (saveBtn) saveBtn.removeAttribute('disabled');

  document.querySelectorAll('.phoneme-btn').forEach((btn) => {
    btn.classList.remove('bg-blue-500', 'text-white');
    btn.classList.add('bg-blue-100', 'text-blue-700');
    if (btn.getAttribute('data-phoneme') === phoneme) {
      btn.classList.remove('bg-blue-100', 'text-blue-700');
      btn.classList.add('bg-blue-500', 'text-white');
    }
  });

  if (USE_SVG_RENDERER) {
    applySvgControlState(presetParams);
    setAnimationState(presetParams);
  }
};

window.savePhonemePosition = function savePhonemePosition() {
  if (!window.selectedPhoneme) return;
  const params = getSvgControlState();
  const customPresets = JSON.parse(localStorage.getItem('customPhonemePresets') || '{}');
  customPresets[window.selectedPhoneme] = {
    name: SvgPhonemePresets[window.selectedPhoneme]?.name || window.selectedPhoneme,
    params: normalizeSvgState(params),
  };
  localStorage.setItem('customPhonemePresets', JSON.stringify(customPresets));
  const statusEl = document.getElementById('save-status');
  if (statusEl) {
    statusEl.textContent = 'Saved!';
    setTimeout(() => {
      statusEl.textContent = '';
    }, 2000);
  }
};

window.updateAnimationParams = function updateAnimationParams(...args) {
  if (args.length === 1 && typeof args[0] === 'object') {
    setAnimationState(normalizeSvgState(args[0]));
  }
};

window.updateVocalTractDescriptions = function updateVocalTractDescriptions(incorrectHtml, correctHtml, animationJson, highlightJson) {
  document.getElementById('left-description')?.replaceChildren();
  const leftDesc = document.getElementById('left-description');
  const rightDesc = document.getElementById('right-description');
  if (leftDesc) leftDesc.innerHTML = incorrectHtml || 'No error selected';
  if (rightDesc) rightDesc.innerHTML = correctHtml || 'No error selected';

  const leftMatch = incorrectHtml ? incorrectHtml.match(/\/([^\/]+)\//) : null;
  const rightMatch = correctHtml ? correctHtml.match(/\/([^\/]+)\//) : null;
  const leftPhonemeEl = document.getElementById('left-phoneme');
  const rightPhonemeEl = document.getElementById('right-phoneme');
  if (leftMatch && leftPhonemeEl) leftPhonemeEl.textContent = leftMatch[1];
  if (rightMatch && rightPhonemeEl) rightPhonemeEl.textContent = rightMatch[1];

  try {
    if (animationJson && typeof animationJson === 'string' && animationJson.trim()) {
      const params = JSON.parse(animationJson);
      if (params?.left) window.currentAnimationParams.left = normalizeSvgState(params.left);
      if (params?.right) window.currentAnimationParams.right = normalizeSvgState(params.right);
    }
  } catch (error) {
    console.error('[updateVocalTractDescriptions] Failed to parse animation JSON:', error);
  }

  try {
    if (highlightJson && typeof highlightJson === 'string' && highlightJson.trim()) {
      const highlight = JSON.parse(highlightJson);
      if (highlight?.zone) window.currentHighlightParams.zone = highlight.zone;
    }
  } catch (error) {
    console.error('[updateVocalTractDescriptions] Failed to parse highlight JSON:', error);
  }

  if (window.currentAnimationParams.left) window.svgLeftRenderer?.setState(window.currentAnimationParams.left);
  if (window.currentAnimationParams.right) window.svgRightRenderer?.setState(window.currentAnimationParams.right);
  if (window.currentHighlightParams.zone) {
    window.svgLeftRenderer?.setHighlightZone(window.currentHighlightParams.zone);
    window.svgRightRenderer?.setHighlightZone(window.currentHighlightParams.zone);
  }
};

window.animateLeft = function animateLeft() {
  window.svgLeftRenderer?.startAnimation();
};

window.animateRight = function animateRight() {
  window.svgRightRenderer?.startAnimation();
};

window.selectError = async function selectError(index) {
  const errors = window.currentErrors;
  if (!errors || index < 0 || index >= errors.length) {
    console.error('[selectError] Invalid error index:', index);
    return;
  }
  try {
    const response = await fetch('/api/select-error', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ error_index: index, errors }),
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    window.updateVocalTractDescriptions(
      data.incorrect_desc,
      data.correct_desc,
      JSON.stringify(data.animation_params),
      JSON.stringify(data.highlight_params),
    );
    window.updateAnimationParams(data.animation_params);
  } catch (err) {
    console.error('[selectError] Failed:', err);
  }
};

document.addEventListener('DOMContentLoaded', () => {
  initTooltips();
  mountSvgRenderers();
  applySvgControlState(DEFAULT_SVG_STATE);
  setAnimationState(getSvgControlState());
  window.switchTab(window.currentTab);
});

window.__testAnalyze__ = function __testAnalyze__(targetText, mockResult) {
  if (targetText) {
    const el = document.getElementById('target_text');
    if (el) el.value = targetText;
  }
  if (window.recorder && typeof window.recorder.displayResults === 'function' && mockResult) {
    const progressContainer = document.getElementById('progress-container');
    if (progressContainer) progressContainer.classList.remove('hidden');
    window.recorder.displayResults(mockResult);
    if (progressContainer) progressContainer.classList.add('hidden');
  }
};
