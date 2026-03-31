/**
 * Intercom-style audio recorder with F5 support
 * Hold to record, release to send for analysis
 */

class IntercomRecorder {
    constructor(options = {}) {
        this.mediaRecorder = null;
        this.audioChunks = [];
        this.isRecording = false;
        this.startTime = null;
        this.timerInterval = null;
        this.recordingTimeout = null;
        this.audioContext = null;
        this.analyser = null;
        this.dataArray = null;
        this.canvas = null;
        this.canvasCtx = null;
        this.maxDuration = 60; // 60 seconds max
        this.animationId = null;
        this.location = options.location || window.location;
        
        this.initElements();
        this.bindEvents();
    }

    initElements() {
        this.recordBtn = document.getElementById('record-btn');
        this.recTimer = document.getElementById('rec-timer');
        this.waveformCanvas = document.getElementById('waveform');
        this.recorderContainer = document.getElementById('recorder');
        this.fileUploadSection = document.getElementById('file-upload-section');
        
        if (this.waveformCanvas) {
            this.canvas = this.waveformCanvas;
            this.canvasCtx = this.canvas.getContext('2d');
        }
    }

    bindEvents() {
        // F5 key listener
        document.addEventListener('keydown', (e) => {
            if (e.key === 'F5' && window.currentTab === 'analysis') {
                e.preventDefault();
                if (!this.isRecording) {
                    this.startRecording();
                }
            }
        });

        document.addEventListener('keyup', (e) => {
            if (e.key === 'F5' && window.currentTab === 'analysis' && this.isRecording) {
                e.preventDefault();
                this.stopRecording();
            }
        });

        // Mouse/Touch events
        if (this.recordBtn) {
            this.recordBtn.addEventListener('mousedown', () => this.startRecording());
            this.recordBtn.addEventListener('mouseup', () => this.stopRecording());
            this.recordBtn.addEventListener('mouseleave', () => {
                if (this.isRecording) this.stopRecording();
            });

            // Touch events
            this.recordBtn.addEventListener('touchstart', (e) => {
                e.preventDefault();
                this.startRecording();
            });
            this.recordBtn.addEventListener('touchend', (e) => {
                e.preventDefault();
                this.stopRecording();
            });
        }
    }

    async init() {
        console.log('Initializing recorder...');
        console.log('Protocol:', this.location.protocol);
        console.log('Hostname:', this.location.hostname);
        console.log('navigator.mediaDevices:', navigator.mediaDevices);
        
        // Check if mediaDevices is supported
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            console.error('MediaDevices API not supported');
            console.log('Browser:', navigator.userAgent);
            this.showNotSupportedMessage();
            return;
        }

        // Check if running on HTTPS (required for getUserMedia except localhost)
        const isLocalhost = this.location.hostname === 'localhost' || this.location.hostname === '127.0.0.1';
        const isHttps = this.location.protocol === 'https:';
        
        console.log('Is localhost:', isLocalhost);
        console.log('Is HTTPS:', isHttps);
        
        if (!isHttps && !isLocalhost) {
            console.error('HTTPS required for microphone access');
            this.showHttpsRequiredMessage();
            return;
        }

        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            this.setupRecorder(stream);
            this.setupVisualizer(stream);
            
            // Show recorder, hide file upload
            if (this.recorderContainer) {
                this.recorderContainer.style.display = 'block';
            }
            if (this.fileUploadSection) {
                this.fileUploadSection.style.display = 'none';
            }
        } catch (err) {
            console.error('Microphone access denied:', err);
            this.showPermissionPrompt();
        }
    }

    showPermissionPrompt() {
        // Don't replace the entire container - just show a message above it
        const msgDiv = document.createElement('div');
        msgDiv.id = 'mic-permission-msg';
        msgDiv.className = 'text-center p-4 bg-yellow-50 border border-yellow-200 rounded mb-4';
        msgDiv.innerHTML = `
            <p class="text-yellow-800 mb-3">Microphone access needed for recording</p>
            <button onclick="recorder.init(); document.getElementById('mic-permission-msg').remove();" 
                    class="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 transition">
                Allow Microphone
            </button>
        `;
        
        if (this.recorderContainer && !document.getElementById('mic-permission-msg')) {
            this.recorderContainer.parentNode.insertBefore(msgDiv, this.recorderContainer);
        }
        
        // Keep file upload as fallback
        if (this.fileUploadSection) {
            this.fileUploadSection.style.display = 'block';
        }
    }

    showNotSupportedMessage() {
        const msgDiv = document.createElement('div');
        msgDiv.className = 'text-center p-4 bg-red-50 border border-red-200 rounded mb-4';
        msgDiv.innerHTML = `
            <p class="text-red-800 mb-2">Your browser doesn't support microphone recording.</p>
            <p class="text-sm text-red-600">Please use the file upload option below.</p>
        `;
        
        if (this.recorderContainer && !document.getElementById('browser-error-msg')) {
            msgDiv.id = 'browser-error-msg';
            this.recorderContainer.parentNode.insertBefore(msgDiv, this.recorderContainer);
            // Keep recorder visible but show it's unavailable
        }
        
        if (this.fileUploadSection) {
            this.fileUploadSection.style.display = 'block';
        }
    }

    showHttpsRequiredMessage() {
        const msgDiv = document.createElement('div');
        msgDiv.className = 'text-center p-4 bg-orange-50 border border-orange-200 rounded mb-4';
        msgDiv.innerHTML = `
            <p class="text-orange-800 mb-2">HTTPS Required</p>
            <p class="text-sm text-orange-600">Microphone access requires HTTPS. Please use the file upload option below, or access via localhost.</p>
        `;
        
        if (this.recorderContainer && !document.getElementById('https-error-msg')) {
            msgDiv.id = 'https-error-msg';
            this.recorderContainer.parentNode.insertBefore(msgDiv, this.recorderContainer);
            // Keep recorder visible
        }
        
        if (this.fileUploadSection) {
            this.fileUploadSection.style.display = 'block';
        }
    }

    setupRecorder(stream) {
        this.mediaRecorder = new MediaRecorder(stream);
        
        this.mediaRecorder.ondataavailable = (e) => {
            if (e.data.size > 0) {
                this.audioChunks.push(e.data);
            }
        };

        this.mediaRecorder.onstop = () => {
            this.sendForAnalysis();
        };
    }

    setupVisualizer(stream) {
        this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
        const source = this.audioContext.createMediaStreamSource(stream);
        this.analyser = this.audioContext.createAnalyser();
        this.analyser.fftSize = 256;
        source.connect(this.analyser);
        
        const bufferLength = this.analyser.frequencyBinCount;
        this.dataArray = new Uint8Array(bufferLength);
    }

    startRecording() {
        if (this.isRecording || !this.mediaRecorder) return;

        this.isRecording = true;
        this.audioChunks = [];
        this.startTime = Date.now();

        // Update UI
        if (this.recordBtn) {
            this.recordBtn.classList.add('recording');
            const btnText = this.recordBtn.querySelector('.btn-text');
            if (btnText) btnText.textContent = 'Recording...';
        }

        // Start timer
        this.timerInterval = setInterval(() => {
            const elapsed = Date.now() - this.startTime;
            const seconds = Math.floor(elapsed / 1000);
            const minutes = Math.floor(seconds / 60);
            const display = `${minutes.toString().padStart(2, '0')}:${(seconds % 60).toString().padStart(2, '0')}`;
            if (this.recTimer) {
                this.recTimer.textContent = display;
            }
        }, 100);

        // Start recording
        this.mediaRecorder.start(100); // Collect data every 100ms

        // Start visualizer
        this.drawWaveform();

        // Set max duration timeout
        this.recordingTimeout = setTimeout(() => {
            if (this.isRecording) {
                console.log('Max duration reached, stopping recording');
                this.stopRecording();
            }
        }, this.maxDuration * 1000);
    }

    stopRecording() {
        if (!this.isRecording) return;

        this.isRecording = false;

        // Clear intervals
        clearInterval(this.timerInterval);
        clearTimeout(this.recordingTimeout);

        // Update UI
        if (this.recordBtn) {
            this.recordBtn.classList.remove('recording');
            const btnText = this.recordBtn.querySelector('.btn-text');
            if (btnText) btnText.textContent = 'Hold to Record';
        }

        // Stop visualizer
        if (this.animationId) {
            cancelAnimationFrame(this.animationId);
            this.animationId = null;
        }

        // Stop recording
        if (this.mediaRecorder && this.mediaRecorder.state !== 'inactive') {
            this.mediaRecorder.stop();
        }
    }

    drawWaveform() {
        if (!this.isRecording || !this.canvas || !this.canvasCtx) return;

        this.animationId = requestAnimationFrame(() => this.drawWaveform());

        this.analyser.getByteTimeDomainData(this.dataArray);

        // Clear canvas
        this.canvasCtx.fillStyle = 'rgb(240, 240, 240)';
        this.canvasCtx.fillRect(0, 0, this.canvas.width, this.canvas.height);

        // Draw waveform
        this.canvasCtx.lineWidth = 2;
        this.canvasCtx.strokeStyle = 'rgb(220, 38, 38)'; // Red-600
        this.canvasCtx.beginPath();

        const sliceWidth = this.canvas.width * 1.0 / this.dataArray.length;
        let x = 0;

        for (let i = 0; i < this.dataArray.length; i++) {
            const v = this.dataArray[i] / 128.0;
            const y = v * this.canvas.height / 2;

            if (i === 0) {
                this.canvasCtx.moveTo(x, y);
            } else {
                this.canvasCtx.lineTo(x, y);
            }

            x += sliceWidth;
        }

        this.canvasCtx.lineTo(this.canvas.width, this.canvas.height / 2);
        this.canvasCtx.stroke();
    }

    async sendForAnalysis() {
        if (this.audioChunks.length === 0) {
            console.error('No audio recorded');
            return;
        }

        const audioBlob = new Blob(this.audioChunks, { type: 'audio/webm' });
        
        try {
            // Convert to 16kHz WAV
            const wavBlob = await this.convertToWav(audioBlob);
            
            // Get target text
            const targetTextInput = document.getElementById('target_text');
            const targetText = targetTextInput ? targetTextInput.value : '';

            if (!targetText.trim()) {
                alert('Please enter the target sentence first');
                return;
            }

            // Create FormData
            const formData = new FormData();
            formData.append('audio', wavBlob, 'recording.wav');
            formData.append('target_text', targetText);

            // Show progress
            if (document.getElementById('progress-container')) {
                document.getElementById('progress-container').classList.remove('hidden');
            }

            // Submit for analysis
            const response = await fetch('/api/analyze', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const result = await response.json();

            // Display results
            this.displayResults(result);

        } catch (error) {
            console.error('Analysis failed:', error);
            alert('Analysis failed: ' + error.message);
        } finally {
            // Reset timer display
            if (this.recTimer) {
                this.recTimer.textContent = '00:00';
            }
        }
    }

    async convertToWav(audioBlob) {
        // Read blob as array buffer
        const arrayBuffer = await audioBlob.arrayBuffer();
        
        // Create audio context at 16kHz
        const audioContext = new (window.AudioContext || window.webkitAudioContext)({
            sampleRate: 16000
        });
        
        // Decode audio
        const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);
        
        // Convert to mono 16-bit PCM WAV
        const wavBlob = this.bufferToWave(audioBuffer, audioBuffer.length);
        
        // Close context
        await audioContext.close();
        
        return wavBlob;
    }

    bufferToWave(abuffer, len) {
        const numOfChan = abuffer.numberOfChannels;
        const length = len * numOfChan * 2 + 44;
        const buffer = new ArrayBuffer(length);
        const view = new DataView(buffer);
        const channels = [];
        let offset = 0;
        let pos = 0;

        // Write WAV header
        // "RIFF" chunk descriptor
        setUint32(0x46464952); // "RIFF"
        setUint32(length - 8); // file length - 8
        setUint32(0x45564157); // "WAVE"

        // "fmt " sub-chunk
        setUint32(0x20746d66); // "fmt "
        setUint32(16); // length = 16
        setUint16(1); // PCM (uncompressed)
        setUint16(numOfChan);
        setUint32(abuffer.sampleRate);
        setUint32(abuffer.sampleRate * 2 * numOfChan); // avg. bytes/sec
        setUint16(numOfChan * 2); // block-align
        setUint16(16); // 16-bit (hardcoded in this example)

        // "data" sub-chunk
        setUint32(0x61746164); // "data"
        setUint32(length - pos - 4); // chunk length

        // Write interleaved data
        for (let i = 0; i < abuffer.numberOfChannels; i++) {
            channels.push(abuffer.getChannelData(i));
        }

        while (pos < length) {
            for (let i = 0; i < numOfChan; i++) {
                // Interleave channels
                let sample = Math.max(-1, Math.min(1, channels[i][offset]));
                // Convert to 16-bit signed integer
                sample = (0.5 + sample < 0 ? sample * 32768 : sample * 32767) | 0;
                view.setInt16(pos, sample, true);
                pos += 2;
            }
            offset++;
        }

        return new Blob([buffer], { type: 'audio/wav' });

        function setUint16(data) {
            view.setUint16(pos, data, true);
            pos += 2;
        }

        function setUint32(data) {
            view.setUint32(pos, data, true);
            pos += 4;
        }
    }

    displayResults(result) {
        console.log('[displayResults] Called');
        console.log('[displayResults] result.success:', result.success);
        console.log('[displayResults] result.feedback:', result.feedback);
        console.log('[displayResults] result.errors:', result.errors);
        
        // Update feedback container - server now sends HTML directly
        const feedbackContainer = document.getElementById('feedback-container');
        if (feedbackContainer) {
            if (result.success) {
                console.log('[displayResults] Inserting feedback HTML...');
                feedbackContainer.innerHTML = `
                    <div class="bg-white rounded-lg shadow-md p-6">
                        <div class="prose max-w-none">
                            ${result.feedback}
                        </div>
                    </div>
                `;
                console.log('[displayResults] Feedback HTML inserted');
            } else {
                feedbackContainer.innerHTML = `
                    <div class="bg-red-50 border border-red-200 rounded-lg p-6">
                        <p class="text-red-700">${result.error || 'Analysis failed'}</p>
                    </div>
                `;
            }
        }

        // Show articulatory section if there are errors
        if (result.errors && result.errors.length > 0) {
            const artSection = document.getElementById('articulatory-section');
            if (artSection) {
                artSection.classList.remove('hidden');
                this.populateErrors(result.errors);
            }
        }
    }

    populateErrors(errors) {
        console.log('[populateErrors] Called with', errors.length, 'errors');
        console.log('[populateErrors] Errors data:', JSON.stringify(errors, null, 2));
        
        // Store errors globally for window.selectError to use
        window.currentErrors = errors;
        console.log('[populateErrors] Set window.currentErrors to', errors.length, 'errors');
        
        const errorList = document.getElementById('error-list');
        if (!errorList) {
            console.error('[populateErrors] error-list element not found!');
            return;
        }

        errorList.innerHTML = '';
        
        errors.forEach((error, index) => {
            const btn = document.createElement('button');
            btn.className = 'w-full text-left px-4 py-3 border border-gray-200 rounded hover:bg-gray-50 transition mb-2';
            btn.innerHTML = `
                <span class="font-medium">${index + 1}.</span>
                <span class="text-gray-700">'${error.word_context}':</span>
                <span class="text-red-600">${window.wrapIPATooltip(error.target_phoneme)}</span>
                <span class="text-gray-400">→</span>
                <span class="text-blue-600">${window.wrapIPATooltip(error.predicted_phoneme)}</span>
            `;
            btn.onclick = () => window.selectError(index);
            errorList.appendChild(btn);
            console.log(`[populateErrors] Created button ${index} for error:`, error);
        });
    }
}

// Initialize recorder when DOM is ready
if (typeof document !== 'undefined' && document.addEventListener) {
    document.addEventListener('DOMContentLoaded', () => {
        console.log('DOM loaded, initializing recorder...');
        
        // Check if required elements exist
        const recordBtn = document.getElementById('record-btn');
        const recorderContainer = document.getElementById('recorder');
        
        if (!recordBtn) {
            console.error('Record button not found in DOM');
            return;
        }
        
        if (!recorderContainer) {
            console.error('Recorder container not found in DOM');
            return;
        }
        
        console.log('Found recorder elements, creating instance...');
        window.recorder = new IntercomRecorder();
        
        // Always show the recorder UI first
        recorderContainer.style.display = 'block';
        
        // Then try to initialize microphone
        window.recorder.init().catch(err => {
            console.error('Failed to initialize recorder:', err);
        });
    });
}

// ES Module exports
export { IntercomRecorder };

// Maintain backward compatibility
if (typeof window !== 'undefined') {
    window.IntercomRecorder = IntercomRecorder;
}
