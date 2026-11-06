import { describe, expect, it, vi } from 'vitest';
import { convertAudioToWav } from '../../static/js/audio_conversion.js';

describe('temporary audio conversion context', () => {
    it.each([16000, 44100])('keeps caller sample rate %i and encoder', async (sampleRate) => {
        const buffer = { length: 42 };
        const context = { decodeAudioData: vi.fn().mockResolvedValue(buffer), close: vi.fn() };
        const constructor = vi.fn(function() { return context; });
        const original = window.AudioContext;
        window.AudioContext = constructor;
        try {
            const encode = vi.fn().mockReturnValue('wav');
            const result = await convertAudioToWav({ arrayBuffer: async () => new ArrayBuffer(1) }, sampleRate, encode);
            expect(constructor).toHaveBeenCalledWith({ sampleRate });
            expect(encode).toHaveBeenCalledWith(buffer, 42);
            expect(result).toBe('wav');
            expect(context.close).toHaveBeenCalledOnce();
        } finally {
            window.AudioContext = original;
        }
    });

    it.each(['decode', 'encode'])('closes context when %s fails', async (stage) => {
        const error = new Error('Invalid audio');
        const context = {
            decodeAudioData: stage === 'decode' ? vi.fn().mockRejectedValue(error) : vi.fn().mockResolvedValue({ length: 1 }),
            close: vi.fn(),
        };
        const original = window.AudioContext;
        window.AudioContext = function() { return context; };
        try {
            await expect(convertAudioToWav(
                { arrayBuffer: async () => new ArrayBuffer(1) },
                16000,
                () => { throw error; },
            )).rejects.toThrow(error);
            expect(context.close).toHaveBeenCalledOnce();
        } finally {
            window.AudioContext = original;
        }
    });
});
