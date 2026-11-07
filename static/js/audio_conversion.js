/** Decode an upload using a temporary context, releasing it even on failure. */
export async function convertAudioToWav(audioBlob, sampleRate, encode) {
    const arrayBuffer = await audioBlob.arrayBuffer();
    const context = new (window.AudioContext || window.webkitAudioContext)({ sampleRate });
    try {
        const buffer = await context.decodeAudioData(arrayBuffer);
        return encode(buffer, buffer.length);
    } finally {
        await context.close();
    }
}

/** Encode a decoded buffer as PCM WAV, optionally averaging channels for inference. */
export function encodePcmWav(audio, length = audio.length, mono = false) {
    const channels = Array.from({ length: audio.numberOfChannels }, (_, index) => audio.getChannelData(index));
    const outputChannels = mono ? 1 : channels.length;
    const bytes = new ArrayBuffer(44 + length * outputChannels * 2);
    const wav = new DataView(bytes);
    wav.setUint32(0, 0x46464952, true); // RIFF
    wav.setUint32(4, bytes.byteLength - 8, true);
    wav.setUint32(8, 0x45564157, true); // WAVE
    wav.setUint32(12, 0x20746d66, true); // fmt
    wav.setUint32(16, 16, true);
    wav.setUint16(20, 1, true);
    wav.setUint16(22, outputChannels, true);
    wav.setUint32(24, audio.sampleRate, true);
    wav.setUint32(28, audio.sampleRate * outputChannels * 2, true);
    wav.setUint16(32, outputChannels * 2, true);
    wav.setUint16(34, 16, true);
    wav.setUint32(36, 0x61746164, true); // data
    wav.setUint32(40, bytes.byteLength - 44, true);
    for (let frame = 0, offset = 44; frame < length; frame++) {
        for (let channel = 0; channel < outputChannels; channel++, offset += 2) {
            const sample = mono
                ? channels.reduce((sum, data) => sum + data[frame], 0) / channels.length
                : channels[channel][frame];
            const clipped = Math.max(-1, Math.min(1, sample));
            wav.setInt16(offset, clipped * (clipped < 0 ? 32768 : 32767), true);
        }
    }
    return new Blob([bytes], { type: 'audio/wav' });
}
