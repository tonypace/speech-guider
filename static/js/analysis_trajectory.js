import { SvgArticulatoryRenderer } from './svg_articulatory_renderer.js';
import { getSettings } from './microphone.js';

/** Inspect estimated tract states on the recording's sample clock. */
export function showAnalysisTrajectory(container, trajectory, blob, options = {}) {
    const frames = trajectory?.frames;
    const rate = trajectory?.frame_rate;
    if (!container || !frames?.length || !(rate > 0)) return () => {};
    const contactEnabled = getSettings().contact_enabled !== false;
    const isR5 = options?.modelVersion === 'r5';
    const subtitle = isR5
        ? 'R5 audio-based estimate, not measured tongue contact or clinical scoring.'
        : `Audio-based estimate${contactEnabled ? ' (tongue contact enhanced)' : ''}, not measured tongue contact or pronunciation scoring.`;
    const section = document.createElement('section');
    section.className = 'bg-white rounded-lg shadow-md p-6 mb-6 min-h-[calc(100vh-8rem)] flex flex-col';
    section.innerHTML = `<div class="flex flex-wrap items-baseline justify-between gap-2">
            <div class="flex flex-wrap items-center gap-2">
                <h3 class="text-xl font-semibold text-gray-800">Articulatory estimate</h3>
                <span data-focus-badge class="hidden inline-flex items-center rounded-full bg-indigo-100 px-2.5 py-0.5 text-xs font-medium text-indigo-800"></span>
            </div>
            <p class="text-xs text-gray-500">${subtitle}</p>
        </div>
        <div class="mt-3 flex flex-wrap items-center gap-3" data-playback>
            <audio controls preload="metadata" class="max-w-full"></audio>
            <label class="text-sm text-gray-700">Playback speed
                <select class="rounded border px-2 py-1">
                    <option value="0.3">0.3×</option>
                    <option value="0.5" selected>0.5×</option>
                    <option value="0.75">0.75×</option>
                    <option value="1">1×</option>
                    <option value="1.25">1.25×</option>
                    <option value="1.5">1.5×</option>
                    <option value="2">2×</option>
                </select>
            </label>
            <span data-speed-badge class="inline-flex items-center rounded-full bg-amber-100 px-2.5 py-0.5 text-xs font-medium text-amber-800">Slow Motion (0.5x)</span>
        </div>
        <div class="mt-4 flex-1 flex flex-col justify-center w-full max-w-3xl mx-auto">
            <div data-tract class="w-full max-w-[62vh] aspect-square shrink-0 mx-auto"></div>
            <label class="block mt-3 text-sm text-gray-700">Inspect frame <input type="range" min="0" step="1" value="0" class="block w-full mt-1"></label>
            <output class="text-xs text-gray-600 mt-1"></output>
        </div>`;
    container.prepend(section);
    const renderer = new SvgArticulatoryRenderer(section.querySelector('[data-tract]'), {
        prefix: 'analysis-estimate',
        contactExaggeration: {
            enabled: contactEnabled,
            showContactHighlight: contactEnabled,
        },
    });
    renderer.mount();
    section.scrollIntoView?.({ behavior: 'smooth', block: 'start' });
    const slider = section.querySelector('input');
    slider.max = String(frames.length - 1);
    const audio = section.querySelector('audio');
    const speed = section.querySelector('select');
    const speedBadge = section.querySelector('[data-speed-badge]');
    const focusBadge = section.querySelector('[data-focus-badge]');
    const updateSpeedBadge = (rateValue) => {
        if (!speedBadge) return;
        if (rateValue < 1) {
            speedBadge.textContent = `Slow Motion (${rateValue}x)`;
            speedBadge.className = 'inline-flex items-center rounded-full bg-amber-100 px-2.5 py-0.5 text-xs font-medium text-amber-800';
        } else if (rateValue === 1) {
            speedBadge.textContent = 'Normal (1.0x)';
            speedBadge.className = 'inline-flex items-center rounded-full bg-emerald-100 px-2.5 py-0.5 text-xs font-medium text-emerald-800';
        } else {
            speedBadge.textContent = `Fast (${rateValue}x)`;
            speedBadge.className = 'inline-flex items-center rounded-full bg-blue-100 px-2.5 py-0.5 text-xs font-medium text-blue-800';
        }
    };
    const url = blob ? URL.createObjectURL(blob) : null;
    if (url) {
        audio.src = url;
        const setSpeed = () => {
            const rateValue = Number(speed.value);
            audio.defaultPlaybackRate = rateValue;
            audio.playbackRate = rateValue;
            updateSpeedBadge(rateValue);
        };
        speed.onchange = setSpeed;
        setSpeed();
    } else {
        section.querySelector('[data-playback]').hidden = true;
    }
    const render = (index) => {
        const bounded = Math.min(frames.length - 1, Math.max(0, index));
        renderer.setState(frames[bounded]);
        slider.value = String(bounded);
        section.querySelector('output').textContent = `${(bounded / rate).toFixed(3)} s · frame ${bounded + 1}/${frames.length}`;
    };
    let animation = null;
    const tick = () => {
        render(Math.floor(audio.currentTime * rate));
        if (!audio.paused && !audio.ended) animation = requestAnimationFrame(tick);
    };
    audio.onplay = () => { cancelAnimationFrame(animation); tick(); };
    audio.onpause = () => cancelAnimationFrame(animation);
    audio.onended = () => {
        cancelAnimationFrame(animation);
        render(Math.floor(audio.currentTime * rate));
    };
    audio.onseeked = () => render(Math.floor(audio.currentTime * rate));
    const onTabChange = (event) => {
        if (event.detail !== 'analysis') {
            audio.pause();
            cancelAnimationFrame(animation);
        }
    };
    window.addEventListener('speechguider:tabchange', onTabChange);
    slider.oninput = () => {
        const index = Number(slider.value);
        render(index);
        if (url) {
            try {
                audio.currentTime = index / rate;
            } catch {
                // Ignore seek attempts before audio metadata loads.
            }
        }
    };
    render(0);

    const dispose = () => {
        window.removeEventListener('speechguider:tabchange', onTabChange);
        cancelAnimationFrame(animation);
        audio.pause();
        audio.removeAttribute('src');
        if (url) URL.revokeObjectURL(url);
        renderer.destroy();
        section.remove();
    };

    dispose.seekTo = (startTime, endTime = null, label = '') => {
        const safeStart = Math.max(0, Number(startTime) || 0);
        const frameIndex = Math.round(safeStart * rate);
        render(frameIndex);
        if (url) {
            try {
                audio.currentTime = safeStart;
            } catch {
                // Ignore seek attempts before audio metadata loads.
            }
        }
        if (focusBadge) {
            if (label) {
                const spanText = Number.isFinite(Number(endTime))
                    ? `${safeStart.toFixed(2)}s–${Number(endTime).toFixed(2)}s`
                    : `${safeStart.toFixed(2)}s`;
                focusBadge.textContent = `Viewing "${label}" · ${spanText}`;
                focusBadge.classList.remove('hidden');
            } else {
                focusBadge.classList.add('hidden');
            }
        }
        section.scrollIntoView?.({ behavior: 'smooth', block: 'start' });
    };

    return dispose;
}
