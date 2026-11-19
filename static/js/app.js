import { SvgArticulatoryRenderer, DEFAULT_STATE } from './svg_articulatory_renderer.js';
import './ipa_tooltips.js';
import './recorder.js';

window.currentTab = 'analysis';
window.currentAnimationParams = { left: { ...DEFAULT_STATE }, right: { ...DEFAULT_STATE } };
window.currentHighlightParams = { zone: null };
window.svgLeftRenderer = null;
window.svgRightRenderer = null;

function mountSvgRenderers() {
    const leftContainer = document.getElementById('svg-articulatory-left');
    const rightContainer = document.getElementById('svg-articulatory-right');

    if (leftContainer && !window.svgLeftRenderer) {
        window.svgLeftRenderer = new SvgArticulatoryRenderer(leftContainer, {
            prefix: 'left',
            state: DEFAULT_STATE,
        });
        window.svgLeftRenderer.mount();
    }

    if (rightContainer && !window.svgRightRenderer) {
        window.svgRightRenderer = new SvgArticulatoryRenderer(rightContainer, {
            prefix: 'right',
            state: DEFAULT_STATE,
        });
        window.svgRightRenderer.mount();
    }
}

window.switchTab = function switchTab(tabName) {
    const previousTab = window.currentTab;
    if (previousTab === 'comparison' && tabName !== 'comparison') {
        window.comparisonLab?.leave();
    }
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

    if (tabName === 'prosody' && window.prosodyLabRecorder) {
        window.prosodyLabRecorder.renderFromStorage();
        void window.prosodyLabRecorder.init();
    }
    if (tabName === 'analysis') {
        void window.recorder?.init();
    }

    if (previousTab === 'analysis' && tabName !== 'analysis') {
        window.svgLeftRenderer?.stopAnimation();
        window.svgRightRenderer?.stopAnimation();
        void resetRecorderInput(window.recorder);
    }
    if (previousTab === 'prosody' && tabName !== 'prosody') {
        window.prosodyLabRecorder?.stopAllAudio();
        window.prosodyLabRecorder?.stopFlowLoop();
        void resetRecorderInput(window.prosodyLabRecorder);
    }
    window.dispatchEvent(new CustomEvent('speechguider:tabchange', { detail: tabName }));
};

async function resetRecorderInput(recorder) {
    if (!recorder || recorder.destroyed) return;
    await recorder.resetInput?.();
}

window.addEventListener('speechguider:settingschange', ({ detail: { previous, next } }) => {
    if (previous.microphone_enabled !== next.microphone_enabled ||
        previous.microphone_device_id !== next.microphone_device_id ||
        previous.microphone_label !== next.microphone_label) {
        void resetRecorderInput(window.recorder);
        void resetRecorderInput(window.prosodyLabRecorder);
        if (next.microphone_enabled === false) window.comparisonLab?.stopRecording();
    }
});

window.updateVocalTractDescriptions = function updateVocalTractDescriptions(incorrectHtml, correctHtml, animationJson, highlightJson) {
    document.getElementById('left-description')?.replaceChildren();
    const leftDesc = document.getElementById('left-description');
    const rightDesc = document.getElementById('right-description');
    if (leftDesc) leftDesc.innerHTML = incorrectHtml || 'No error selected';
    if (rightDesc) rightDesc.innerHTML = correctHtml || 'No error selected';

    const leftMatch = incorrectHtml ? incorrectHtml.match(/\/([^/]+)\//) : null;
    const rightMatch = correctHtml ? correctHtml.match(/\/([^/]+)\//) : null;
    const leftPhonemeEl = document.getElementById('left-phoneme');
    const rightPhonemeEl = document.getElementById('right-phoneme');
    if (leftMatch && leftPhonemeEl) leftPhonemeEl.textContent = leftMatch[1];
    if (rightMatch && rightPhonemeEl) rightPhonemeEl.textContent = rightMatch[1];

    try {
        if (animationJson && typeof animationJson === 'string' && animationJson.trim()) {
            const params = JSON.parse(animationJson);
            if (params?.left) window.currentAnimationParams.left = { ...DEFAULT_STATE, ...params.left };
            if (params?.right) window.currentAnimationParams.right = { ...DEFAULT_STATE, ...params.right };
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
    } catch (err) {
        console.error('[selectError] Failed:', err);
    }
};

document.addEventListener('DOMContentLoaded', () => {
    mountSvgRenderers();
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
