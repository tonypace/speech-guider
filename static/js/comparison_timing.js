const WINDOW_SECONDS = 0.01;
const EDGE_PADDING_SECONDS = 0.1;
const MIN_SPEECH_SECONDS = 0.35;
const MIN_MATCH_RATE = 0.85;
const MAX_MATCH_RATE = 1.15;

/** Find quiet edges conservatively. Keep soft consonants and pauses inside the clip. */
export function measureSpeech(buffer) {
    const { length, sampleRate, numberOfChannels } = buffer;
    const windowSize = Math.round(WINDOW_SECONDS * sampleRate);
    const channels = Array.from({ length: numberOfChannels }, (_, index) => buffer.getChannelData(index));
    const levels = new Float32Array(Math.ceil(length / windowSize));
    let peak = 0;
    for (let window = 0; window < levels.length; window++) {
        const start = window * windowSize;
        const end = Math.min(start + windowSize, length);
        for (const channel of channels) {
            let energy = 0;
            for (let sample = start; sample < end; sample++) energy += channel[sample] ** 2;
            levels[window] = Math.max(levels[window], Math.sqrt(energy / (end - start)));
        }
        peak = Math.max(peak, levels[window]);
    }

    const threshold = Math.max(0.002, Math.min(0.01, peak * 0.025));
    const first = levels.findIndex(level => level >= threshold);
    if (first < 0) return null;
    let last = first;
    let activeWindows = 0;
    for (let window = first; window < levels.length; window++) {
        if (levels[window] >= threshold) {
            last = window;
            activeWindows++;
        }
    }
    if (activeWindows < 5) return null;

    const start = first * windowSize / sampleRate;
    const end = Math.min((last + 1) * windowSize, length) / sampleRate;
    return {
        start: Math.max(0, start - EDGE_PADDING_SECONDS),
        end: Math.min(buffer.duration, end + EDGE_PADDING_SECONDS),
        span: end - start,
        active: activeWindows * windowSize / sampleRate,
    };
}

/** A duration check can screen out suspect takes. The listener confirms the words. */
export function getDurationMatch(reference, student, referenceDuration, studentDuration) {
    if (!reference || !student || Math.min(reference.span, student.span) < MIN_SPEECH_SECONDS) return null;
    const speechRatio = student.span / reference.span;
    const rate = studentDuration / referenceDuration;
    if (speechRatio < MIN_MATCH_RATE || speechRatio > MAX_MATCH_RATE ||
        rate < MIN_MATCH_RATE || rate > MAX_MATCH_RATE ||
        student.active < reference.active * 0.65) return null;
    return rate;
}
