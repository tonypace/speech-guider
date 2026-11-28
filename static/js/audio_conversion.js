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
export function encodePcmWav(audio, length = audio.length, mono = false, start = 0) {
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
    for (let frame = start, offset = 44; frame < start + length; frame++) {
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

/** Slice a 16-bit mono PCM WAV Blob to [startSec, endSec] seconds. */
export async function slicePcmWavBlob(wavBlob, startSec, endSec) {
    if (!wavBlob) return null;
    const buffer = await wavBlob.arrayBuffer();
    if (buffer.byteLength <= 44) return wavBlob;
    const view = new DataView(buffer);
    const sampleRate = view.getUint32(24, true) || 16000;
    const headerBytes = 44;
    const totalSamples = Math.floor((buffer.byteLength - headerBytes) / 2);
    if (totalSamples <= 0) return wavBlob;
    const startSample = Math.max(0, Math.min(totalSamples - 1, Math.floor(startSec * sampleRate)));
    const endSample = Math.max(startSample + 1, Math.min(totalSamples, Math.ceil(endSec * sampleRate)));
    const sliceSamples = new Int16Array(buffer, headerBytes + startSample * 2, endSample - startSample);
    const floatSamples = new Float32Array(sliceSamples.length);
    for (let i = 0; i < sliceSamples.length; i++) {
        floatSamples[i] = sliceSamples[i] / 0x8000;
    }
    return encodePcmWav(
        {
            numberOfChannels: 1,
            sampleRate,
            getChannelData: () => floatSamples,
        },
        floatSamples.length,
        false,
        0,
    );
}
