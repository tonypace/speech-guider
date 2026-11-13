import { SvgArticulatoryRenderer } from './svg_articulatory_renderer.js';

/** Inspect estimated tract states on the recording's sample clock. */
export function showAnalysisTrajectory(container, trajectory, blob) {
    const frames = trajectory?.frames;
    const rate = trajectory?.frame_rate;
    if (!container || !frames?.length || !(rate > 0)) return () => {};
    const section = document.createElement('section');
    section.className = 'bg-white rounded-lg p-6 mt-4';
    section.innerHTML = `<h3 class="text-lg font-semibold">Articulatory estimate</h3>
        <p>Audio-based estimate, not measured tongue contact or pronunciation scoring.</p>
        <div class="mt-3 flex flex-wrap items-center gap-3" data-playback>
            <audio controls preload="metadata" class="max-w-full"></audio>
            <label>Playback speed
                <select class="rounded border px-2 py-1">
                    <option value="0.3" selected>0.3×</option>
                    <option value="0.5">0.5×</option>
                    <option value="0.75">0.75×</option>
                    <option value="1">1×</option>
                    <option value="1.25">1.25×</option>
                    <option value="1.5">1.5×</option>
                    <option value="2">2×</option>
                </select>
            </label>
        </div>
        <div class="mt-3 max-w-xs">
            <div data-tract></div>
            <label class="block">Inspect frame <input type="range" min="0" step="1" value="0" class="block w-full"></label>
            <output></output>
        </div>`;
    container.appendChild(section);
    const renderer = new SvgArticulatoryRenderer(section.querySelector('[data-tract]'), { prefix: 'analysis-estimate' });
    renderer.mount();
    const slider = section.querySelector('input');
    slider.max = String(frames.length - 1);
    const audio = section.querySelector('audio');
    const speed = section.querySelector('select');
    const url = blob ? URL.createObjectURL(blob) : null;
    if (url) {
        audio.src = url;
        const setSpeed = () => {
            audio.defaultPlaybackRate = Number(speed.value);
            audio.playbackRate = audio.defaultPlaybackRate;
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
    audio.onseeked = () => render(Math.floor(audio.currentTime * rate));
    slider.oninput = () => {
        const index = Number(slider.value);
        if (url) audio.currentTime = index / rate;
        render(index);
    };
    render(0);
    return () => {
        cancelAnimationFrame(animation);
        audio.pause();
        audio.removeAttribute('src');
        if (url) URL.revokeObjectURL(url);
        renderer.destroy();
        section.remove();
    };
}
