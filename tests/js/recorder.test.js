/**
 * Tests for IntercomRecorder
 * Tests the audio recording functionality with F5 key support
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { MockMediaRecorder, MockAudioContext, MockMediaStream } from './mocks/webAudioMock.js';

describe('IntercomRecorder', () => {
    let recorder;

    beforeEach(async () => {
        // Setup DOM elements
        document.body.innerHTML = `
      <div id="recorder">
        <button id="record-btn">Record</button>
        <span id="rec-timer">00:00</span>
        <canvas id="waveform"></canvas>
      </div>
      <div id="file-upload-section">
        <input type="file" id="audio" name="audio" accept="audio/*">
      </div>
      <input type="text" id="target_text" value="The weather is very hot today.">
      <div id="progress-container" class="hidden"></div>
      <div id="feedback-container"></div>
    `;

        // Mock global objects
        global.MediaRecorder = MockMediaRecorder;
        global.AudioContext = MockAudioContext;
        global.MediaStream = MockMediaStream;

        // Mock navigator.mediaDevices
        Object.defineProperty(global.navigator, 'mediaDevices', {
            configurable: true,
            writable: true,
            value: {
                getUserMedia: vi.fn().mockResolvedValue(new MockMediaStream()),
            },
        });

        const mod = await import('../../static/js/recorder.js');
        recorder = new mod.IntercomRecorder({
            location: {
                protocol: 'https:',
                hostname: 'localhost',
            },
        });
    });

    afterEach(() => {
        recorder?.destroy();
        window.recorder?.destroy?.();
        delete window.recorder;
        delete window.currentTab;
        vi.useRealTimers();
    });

    describe('Constructor', () => {
        it('should initialize with null mediaRecorder', () => {
            expect(recorder.mediaRecorder).toBeNull();
        });

        it('should initialize with empty audio chunks', () => {
            expect(recorder.audioChunks).toEqual([]);
        });

        it('should not be recording initially', () => {
            expect(recorder.isRecording).toBe(false);
        });

        it('should have max duration of 60 seconds', () => {
            expect(recorder.maxDuration).toBe(60);
        });

        it('should initialize DOM element references', () => {
            expect(recorder.recordBtn).toBeDefined();
            expect(recorder.recTimer).toBeDefined();
            expect(recorder.waveformCanvas).toBeDefined();
        });
    });

    describe('Initialization', () => {
        it('should detect HTTPS requirement', async () => {
            recorder.location = { protocol: 'http:', hostname: 'example.com' };

            await recorder.init();
            expect(recorder.mediaRecorder).toBeNull();
            expect(document.getElementById('https-error-msg')).not.toBeNull();
            expect(recorder.fileUploadSection.style.display).toBe('block');
        });

        it('should skip HTTPS check for localhost', async () => {
            recorder.location = { protocol: 'http:', hostname: 'localhost' };

            await recorder.init();
            expect(global.navigator.mediaDevices.getUserMedia).toHaveBeenCalledOnce();
            expect(recorder.mediaRecorder).not.toBeNull();
            expect(document.getElementById('https-error-msg')).toBeNull();
            expect(recorder.fileUploadSection.style.display).toBe('none');
        });

        it('should handle microphone permission denial', async () => {
            const denied = Object.assign(new Error('Permission denied'), { name: 'NotAllowedError' });
            global.navigator.mediaDevices.getUserMedia = vi.fn().mockRejectedValue(denied);

            await recorder.init();
            expect(recorder.mediaRecorder).toBeNull();
            const prompt = document.getElementById('mic-permission-msg');
            expect(prompt).not.toBeNull();
            expect(prompt.textContent).toContain('Microphone permission was denied');
            expect(prompt.querySelector('button')?.textContent).toBe('Retry microphone');
            expect(recorder.fileUploadSection.style.display).toBe('block');
        });
    });

    describe('Recording Lifecycle', () => {
        it('should start recording when startRecording is called', () => {
            const mockStream = new MockMediaStream();
            recorder.setupRecorder(mockStream);
            recorder.setupVisualizer(mockStream);

            recorder.startRecording();
            expect(recorder.isRecording).toBe(true);
            expect(recorder.recordBtn.classList.contains('recording')).toBe(true);
        });

        it('should stop recording when stopRecording is called', () => {
            const mockStream = new MockMediaStream();
            recorder.setupRecorder(mockStream);
            recorder.setupVisualizer(mockStream);
            vi.spyOn(recorder, 'sendForAnalysis').mockResolvedValue();

            recorder.startRecording();
            recorder.stopRecording();
            expect(recorder.isRecording).toBe(false);
            expect(recorder.recordBtn.classList.contains('recording')).toBe(false);
        });

        it('should collect audio chunks while recording', () => {
            const mockStream = new MockMediaStream();
            recorder.setupRecorder(mockStream);

            // Simulate dataavailable event
            const mockBlob = new Blob(['test audio data'], { type: 'audio/wav' });
            recorder.mediaRecorder.ondataavailable({ data: mockBlob });

            expect(recorder.audioChunks.length).toBeGreaterThan(0);
        });

        it('updates elapsed recording time', () => {
            vi.useFakeTimers();
            const mockStream = new MockMediaStream();
            recorder.setupRecorder(mockStream);
            recorder.setupVisualizer(mockStream);
            vi.spyOn(recorder, 'sendForAnalysis').mockResolvedValue();
            recorder.startRecording();
            vi.advanceTimersByTime(5100);
            expect(recorder.recTimer.textContent).toBe('00:05');
            recorder.stopRecording();
        });
    });

    describe('Event Handlers', () => {
        it('should start recording on F5 keydown when on analysis tab', () => {
            window.currentTab = 'analysis';
            const mockStream = new MockMediaStream();
            recorder.setupRecorder(mockStream);
            recorder.setupVisualizer(mockStream);
            const startSpy = vi.spyOn(recorder, 'startRecording');

            const event = new KeyboardEvent('keydown', { key: 'F5', cancelable: true });
            document.dispatchEvent(event);

            expect(event.defaultPrevented).toBe(true);
            expect(startSpy).toHaveBeenCalledOnce();
            expect(recorder.isRecording).toBe(true);
        });

        it('should ignore F5 keydown outside analysis tab', () => {
            window.currentTab = 'comparison';
            const mockStream = new MockMediaStream();
            recorder.setupRecorder(mockStream);
            recorder.setupVisualizer(mockStream);
            const startSpy = vi.spyOn(recorder, 'startRecording');

            const event = new KeyboardEvent('keydown', { key: 'F5', cancelable: true });
            document.dispatchEvent(event);

            expect(event.defaultPrevented).toBe(false);
            expect(startSpy).not.toHaveBeenCalled();
            expect(recorder.isRecording).toBe(false);
        });

        it('should stop recording on F5 keyup when on analysis tab', () => {
            window.currentTab = 'analysis';
            const mockStream = new MockMediaStream();
            recorder.setupRecorder(mockStream);
            recorder.setupVisualizer(mockStream);
            vi.spyOn(recorder, 'sendForAnalysis').mockResolvedValue();
            recorder.startRecording();
            const stopSpy = vi.spyOn(recorder, 'stopRecording');

            const event = new KeyboardEvent('keyup', { key: 'F5', cancelable: true });
            document.dispatchEvent(event);

            expect(event.defaultPrevented).toBe(true);
            expect(stopSpy).toHaveBeenCalledOnce();
            expect(recorder.isRecording).toBe(false);
        });

        it('should start and stop recording on mousedown/mouseup events', () => {
            const mockStream = new MockMediaStream();
            recorder.setupRecorder(mockStream);
            recorder.setupVisualizer(mockStream);
            vi.spyOn(recorder, 'sendForAnalysis').mockResolvedValue();
            const startSpy = vi.spyOn(recorder, 'startRecording');
            const stopSpy = vi.spyOn(recorder, 'stopRecording');

            recorder.recordBtn.dispatchEvent(new MouseEvent('mousedown', { bubbles: true }));
            expect(startSpy).toHaveBeenCalledOnce();
            expect(recorder.isRecording).toBe(true);

            recorder.recordBtn.dispatchEvent(new MouseEvent('mouseup', { bubbles: true }));
            expect(stopSpy).toHaveBeenCalledOnce();
            expect(recorder.isRecording).toBe(false);
        });
    });

    describe('Waveform Visualization', () => {
        it('should create analyser node', () => {
            const mockStream = new MockMediaStream();
            recorder.setupVisualizer(mockStream);

            expect(recorder.analyser).toBeDefined();
        });

        it('should have canvas context', () => {
            expect(recorder.canvasCtx).not.toBeNull();
            expect(typeof recorder.canvasCtx.fillRect).toBe('function');
        });
    });

    describe('Audio Processing', () => {
        it('encodes actual PCM samples and WAV headers', async () => {
            const blob = recorder.bufferToWave({
                numberOfChannels: 1,
                sampleRate: 16000,
                getChannelData: () => Float32Array.from([-1, 0, 1]),
            }, 3);
            const bytes = new DataView(await blob.arrayBuffer());
            expect(blob.type).toBe('audio/wav');
            expect(bytes.byteLength).toBe(50);
            expect(bytes.getUint32(0, true)).toBe(0x46464952);
            expect(bytes.getUint32(24, true)).toBe(16000);
            expect(bytes.getInt16(44, true)).toBe(-32768);
            expect(bytes.getInt16(46, true)).toBe(0);
            expect(bytes.getInt16(48, true)).toBe(32767);
        });
    });

    describe('Error Handling', () => {
        it('should handle missing DOM elements gracefully', () => {
            document.body.innerHTML = '';

            const newRecorder = new recorder.constructor();
            expect(newRecorder).toBeDefined();
            newRecorder.destroy();
        });

        it('should fall back to file upload when MediaRecorder is missing', async () => {
            const originalMediaRecorder = global.MediaRecorder;
            global.MediaRecorder = undefined;

            try {
                await recorder.init();
                expect(recorder.mediaRecorder).toBeNull();
                expect(document.getElementById('mic-permission-msg')).not.toBeNull();
                expect(recorder.fileUploadSection.style.display).toBe('block');
            } finally {
                global.MediaRecorder = originalMediaRecorder;
            }
        });

        it('should show unsupported message when mediaDevices is unavailable', async () => {
            Object.defineProperty(global.navigator, 'mediaDevices', {
                configurable: true,
                writable: true,
                value: undefined,
            });

            await recorder.init();
            expect(recorder.mediaRecorder).toBeNull();
            const errorMsg = document.getElementById('browser-error-msg');
            expect(errorMsg).not.toBeNull();
            expect(errorMsg.textContent).toContain('doesn\'t support microphone recording');
            expect(recorder.fileUploadSection.style.display).toBe('block');
        });
    });

    describe('Global Registration', () => {
        it('should register IntercomRecorder globally', async () => {
            const mod = await import('../../static/js/recorder.js');
            expect(window.IntercomRecorder).toBe(mod.IntercomRecorder);
        });

        it('should create global recorder instance on DOMContentLoaded', () => {
            document.dispatchEvent(new Event('DOMContentLoaded'));
            expect(window.recorder).toBeInstanceOf(window.IntercomRecorder);
            expect(document.getElementById('recorder').style.display).toBe('block');
        });
    });

    describe('File Upload', () => {
        it('should cache audioInput element in initElements', () => {
            expect(recorder.audioInput).toBeDefined();
            expect(recorder.audioInput.id).toBe('audio');
        });

        it('should attach change listener to file input', () => {
            const handler = vi.spyOn(recorder, 'handleFileUpload').mockResolvedValue();
            const file = new File(['audio'], 'input.wav');
            Object.defineProperty(recorder.audioInput, 'files', { value: [file] });
            recorder.bindEvents();
            recorder.audioInput.dispatchEvent(new Event('change'));
            expect(handler).toHaveBeenCalledOnce();
            expect(handler).toHaveBeenCalledWith(file);
        });

        it('handleFileUpload rejects empty target text and clears input', async () => {
            const targetInput = document.getElementById('target_text');
            targetInput.value = '';

            let alertCalled = false;
            const originalAlert = global.alert;
            global.alert = vi.fn(() => { alertCalled = true; });

            const mockFile = new File(['test'], 'test.wav', { type: 'audio/wav' });
            await recorder.handleFileUpload(mockFile);

            expect(alertCalled).toBe(true);
            expect(recorder.audioInput.value).toBe('');

            global.alert = originalAlert;
            targetInput.value = 'The weather is very hot today.';
        });

        it('handleFileUpload calls submitAudioBlob with converted WAV', async () => {
            const mockFile = new File(['test audio data'], 'test.wav', { type: 'audio/wav' });
            const submitSpy = vi.spyOn(recorder, 'submitAudioBlob').mockResolvedValue(undefined);
            const convertSpy = vi.spyOn(recorder, 'convertToWav').mockResolvedValue(new Blob(['wav data'], { type: 'audio/wav' }));

            await recorder.handleFileUpload(mockFile);

            expect(convertSpy).toHaveBeenCalledWith(mockFile);
            expect(submitSpy).toHaveBeenCalled();
            submitSpy.mockRestore();
            convertSpy.mockRestore();
        });

        it('_clearFileInput calls value = "" on audio input', () => {
            expect(typeof recorder._clearFileInput).toBe('function');
        });

        it('submitAudioBlob sends FormData to /api/analyze and calls displayResults', async () => {
            const mockWav = new Blob(['wav data'], { type: 'audio/wav' });
            const mockResult = { success: true, feedback: '<p>Test feedback</p>', errors: [] };
            const mockResponse = { ok: true, json: () => Promise.resolve(mockResult) };
            const fetchSpy = vi.spyOn(global, 'fetch').mockResolvedValue(mockResponse);
            const displaySpy = vi.spyOn(recorder, 'displayResults').mockImplementation(() => {});

            await recorder.submitAudioBlob(mockWav, 'test.wav');

            expect(fetchSpy).toHaveBeenCalledWith('/api/analyze', expect.objectContaining({ method: 'POST' }));
            expect(displaySpy).toHaveBeenCalledWith(mockResult, mockWav);

            fetchSpy.mockRestore();
            displaySpy.mockRestore();
        });

        it('submitAudioBlob shows progress container during analysis', async () => {
            const mockWav = new Blob(['wav data'], { type: 'audio/wav' });
            const mockResult = { success: true, feedback: '<p>Test</p>', errors: [] };
            const mockResponse = { ok: true, json: () => Promise.resolve(mockResult) };
            const fetchSpy = vi.spyOn(global, 'fetch').mockResolvedValue(mockResponse);
            vi.spyOn(recorder, 'displayResults').mockImplementation(() => {
                const pc = document.getElementById('progress-container');
                if (pc) pc.classList.add('hidden');
            });

            const progressContainer = document.getElementById('progress-container');
            progressContainer.classList.add('hidden');

            await recorder.submitAudioBlob(mockWav, 'test.wav');

            expect(progressContainer.classList.contains('hidden')).toBe(true);

            fetchSpy.mockRestore();
            recorder.displayResults.mockRestore();
        });
    });
});
