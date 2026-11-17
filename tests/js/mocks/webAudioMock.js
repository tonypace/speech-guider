// Mock for Web Audio API - MediaRecorder, AudioContext, and MediaStream
import { vi } from 'vitest';

export class MockMediaRecorder {
    constructor(stream) {
        this.stream = stream;
        this.state = 'inactive';
        this.audioChunks = [];
        this.ondataavailable = null;
        this.onstop = null;
        this.onerror = null;
        this.onstart = null;
    }

    start() {
        this.state = 'recording';
        if (this.onstart) this.onstart();
    }

    stop() {
        this.state = 'inactive';
        // Simulate dataavailable event
        if (this.ondataavailable) {
            const mockBlob = new Blob(['mock audio data'], { type: 'audio/wav' });
            this.ondataavailable({ data: mockBlob });
        }
        if (this.onstop) this.onstop();
    }

    pause() {
        this.state = 'paused';
    }

    resume() {
        this.state = 'recording';
    }
}

export class MockAudioContext {
    constructor() {
        this.state = 'running';
        this.sampleRate = 44100;
        this.currentTime = 0;
        this.destination = {};
    }

    createAnalyser() {
        return {
            fftSize: 2048,
            frequencyBinCount: 1024,
            getByteFrequencyData: vi.fn((array) => {
                // Fill with mock frequency data
                for (let i = 0; i < array.length; i++) {
                    array[i] = Math.floor(Math.random() * 256);
                }
            }),
            getByteTimeDomainData: vi.fn((array) => {
                for (let i = 0; i < array.length; i++) {
                    array[i] = 128;
                }
            }),
            getFloatTimeDomainData: vi.fn((array) => {
                array.fill(0);
            }),
            connect: vi.fn(),
            disconnect: vi.fn(),
        };
    }

    createMediaStreamSource(stream) {
        return {
            connect: vi.fn(),
            disconnect: vi.fn(),
            mediaStream: stream,
        };
    }

    resume() {
        this.state = 'running';
        return Promise.resolve();
    }

    suspend() {
        this.state = 'suspended';
        return Promise.resolve();
    }

    close() {
        this.state = 'closed';
        return Promise.resolve();
    }
}

export class MockMediaStream {
    constructor(tracks = []) {
        this.tracks = tracks;
        this.active = true;
        this.id = 'mock-stream-' + Math.random().toString(36).substr(2, 9);
    }

    getTracks() {
        return this.tracks;
    }

    getAudioTracks() {
        return this.tracks.filter(track => track.kind === 'audio');
    }

    addTrack(track) {
        this.tracks.push(track);
    }

    removeTrack(track) {
        const index = this.tracks.indexOf(track);
        if (index > -1) {
            this.tracks.splice(index, 1);
        }
    }
}
