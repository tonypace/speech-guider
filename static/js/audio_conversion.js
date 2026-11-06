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
