import { showAnalysisTrajectory } from './analysis_trajectory.js';
import { listen, releaseCapture } from './capture_resources.js';
import { openAnalysisProgress } from './analysis_progress.js';
import { convertAudioToWav, encodePcmWav, slicePcmWavBlob } from './audio_conversion.js';
import { getSettings, microphoneError, openMicrophone } from './microphone.js';

const DEFAULT_DIAGNOSTIC_PASSAGES = [
    {
        id: 'full_diagnostic',
        title: 'Full 6-Category Diagnostic',
        target_contrasts: ['/θ/', '/ð/', '/v/ vs /w/', '/r/ vs /l/', 'Final clusters', '/ɪ/ vs /iː/, /æ/ vs /ɛ/'],
        text: 'Every Thursday morning, Ruth and Phil drive their silver van past the busy harbor. Phil loves fresh fruit, so he grabs six sweet peaches and three red apples at the market. A thick fog rolls over the water, making the paths wet and slick. Ruth checks her watch, smiles, and says, "They\'ll ship those crates before noon if we hurry." Then they bet a small bat can reach the big ship before the sheep cross.',
    },
    {
        id: 'dental_fricatives',
        title: 'Dental Fricatives (/θ/ & /ð/)',
        target_contrasts: ['/θ/ vs /s, f, t/', '/ð/ vs /d, z/'],
        text: 'Ruth thinks those three thick paths lead to the harbor, though they breathe better in the northern weather on Thursday.',
    },
    {
        id: 'labiodental_glide',
        title: 'Labiodental vs. Glide (/v/ & /w/)',
        target_contrasts: ['/v/ vs /w/'],
        text: 'Phil drives a silver van over wet waves, while five visitors watch warm water swirl past the west harbor.',
    },
    {
        id: 'liquid_contrast',
        title: 'Liquid Contrast (/r/ & /l/)',
        target_contrasts: ['/r, ɹ̩/ vs /l, l̩/'],
        text: 'Right by the light, Ruth rolls red apples across fresh grass while Phil smiles and lifts a small silver glass.',
    },
    {
        id: 'final_clusters',
        title: 'Final Consonants & Clusters',
        target_contrasts: ['Coda stops', 'Final -ks / -ts / -st / -θs'],
        text: 'Phil grabs six crates, checks five desks and wet masks, and walks past the slick paths before work.',
    },
    {
        id: 'vowel_pairs',
        title: 'Tense/Lax & Front Vowel Pairs',
        target_contrasts: ['/ɪ/ vs /iː/', '/æ/ vs /ɛ/'],
        text: 'They bet a small bat can reach the big ship before the sheep cross; please sit in this seat and let the bad bed rest.',
    },
];

const STATUS_BADGE_META = {
    needs_focus: {
        label: 'Needs focus',
        className: 'bg-rose-100 text-rose-800 border-rose-200',
    },
    watch: {
        label: 'Watch',
        className: 'bg-amber-100 text-amber-800 border-amber-200',
    },
    clear: {
        label: 'Clear',
        className: 'bg-emerald-100 text-emerald-800 border-emerald-200',
    },
    not_tested: {
        label: 'Not in text',
        className: 'bg-gray-100 text-gray-600 border-gray-200',
    },
};

function jumpToComparisonLab(promptText) {
    const sourceInput = document.getElementById('target_text');
    const comparisonInput = document.getElementById('comparison-target-text');
    const nextText = promptText || (sourceInput ? sourceInput.value : '');
    if (comparisonInput && nextText && comparisonInput.value !== nextText) {
        comparisonInput.value = nextText;
        comparisonInput.dispatchEvent(new Event('input', { bubbles: true }));
    }
    window.switchTab?.('comparison');
}

/**
 * Intercom-style audio recorder with press-to-start / press-to-stop toggle support.
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
        this.stream = null;
        this.visualizerSource = null;
        this.eventListeners = [];
        this.eventsBound = false;
        this.destroyed = false;
        this.initPromise = null;
        this.permissionRequestId = 0;
        this.isStartingRecording = false;
        this.cancelOnStop = false;
        this.passages = [...DEFAULT_DIAGNOSTIC_PASSAGES];
        this.lastAudioBlob = null;
        this.lastAnalysisResult = null;
        this._refAudioUrl = null;

        this.initElements();
        this.bindEvents();
        this.initDiagnosticPassages();
        this.initReferencePlayback();
    }

    initElements() {
        this.recordBtn = document.getElementById('record-btn');
        this.recTimer = document.getElementById('rec-timer');
        this.waveformCanvas = document.getElementById('waveform');
        this.recorderContainer = document.getElementById('recorder');
        this.fileUploadSection = document.getElementById('file-upload-section');
        this.audioInput = document.getElementById('audio');
        this.passageSelect = document.getElementById('diagnostic-passage-select');
        this.passageBadges = document.getElementById('diagnostic-passage-badges');
        this.targetTextInput = document.getElementById('target_text');
        this.playRefBtn = document.getElementById('play-reference-btn');
        this.refAudioEl = document.getElementById('analysis-reference-audio');

        if (this.waveformCanvas) {
            this.canvas = this.waveformCanvas;
            this.canvasCtx = this.canvas.getContext('2d');
        }
    }

    initDiagnosticPassages() {
        if (!this.passageSelect) return;

        const renderBadges = (contrasts = []) => {
            if (!this.passageBadges) return;
            this.passageBadges.replaceChildren();
            contrasts.forEach((label) => {
                const chip = document.createElement('span');
                chip.className = 'rounded-full bg-blue-50 border border-blue-200 px-2 py-0.5 text-blue-700 font-medium';
                chip.textContent = label;
                this.passageBadges.appendChild(chip);
            });
        };

        this.selectDiagnosticPassage = (passageId, { clearResults = false } = {}) => {
            const found = this.passages.find((p) => p.id === passageId);
            if (!found) {
                renderBadges([]);
                return;
            }
            this.passageSelect.value = found.id;
            if (this.targetTextInput && this.targetTextInput.value !== found.text) {
                this.targetTextInput.value = found.text;
                this.targetTextInput.dispatchEvent(new Event('input', { bubbles: true }));
            }
            renderBadges(found.target_contrasts || []);
            if (clearResults) {
                this.disposeTrajectory?.();
                this.disposeTrajectory = null;
                document.getElementById('feedback-container')?.replaceChildren();
                document.getElementById('articulatory-section')?.classList.add('hidden');
                this.targetTextInput?.scrollIntoView?.({ behavior: 'smooth', block: 'center' });
            }
        };

        listen(this, this.passageSelect, 'change', (event) => {
            this.selectDiagnosticPassage(event.target.value);
        });

        if (this.targetTextInput) {
            listen(this, this.targetTextInput, 'input', () => {
                const current = this.targetTextInput.value.trim();
                const matched = this.passages.find((p) => p.text.trim() === current);
                if (matched) {
                    this.passageSelect.value = matched.id;
                    renderBadges(matched.target_contrasts || []);
                } else {
                    this.passageSelect.value = 'custom';
                    renderBadges([]);
                }
            });
        }

        if (typeof fetch === 'function') {
            Promise.resolve(fetch('/api/diagnostic-passages'))
                .then((resp) => (resp?.ok ? resp.json() : null))
                .then((data) => {
                    if (!this.destroyed && Array.isArray(data?.passages) && data.passages.length > 0) {
                        this.passages = data.passages;
                        const active = this.passages.find((p) => p.id === this.passageSelect.value);
                        if (active) renderBadges(active.target_contrasts || []);
                    }
                })
                .catch(() => {
                    // Keep inline default passages when running offline or in unit tests.
                });
        }
    }

    initReferencePlayback() {
        if (!this.playRefBtn || !this.refAudioEl) return;

        const stopRef = () => {
            this.refAudioEl.pause();
            this.refAudioEl.currentTime = 0;
            this.playRefBtn.textContent = '▶ Play Reference';
            this.playRefBtn.disabled = false;
        };

        listen(this, this.refAudioEl, 'ended', stopRef);
        listen(this, window, 'speechguider:tabchange', (event) => {
            if (event.detail !== 'analysis') stopRef();
        });

        listen(this, this.playRefBtn, 'click', async () => {
            if (!this.refAudioEl.paused) {
                stopRef();
                return;
            }
            const text = this.targetTextInput?.value?.trim() || '';
            if (!text) return;
            this.playRefBtn.disabled = true;
            this.playRefBtn.textContent = 'Loading…';
            try {
                const resp = await fetch('/api/reference-animation', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ target_text: text, tts_provider: 'omnivoice' }),
                });
                if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
                const data = await resp.json();
                const mime = data.audio_format === 'wav' ? 'audio/wav' : 'audio/ogg';
                this.refAudioEl.src = `data:${mime};base64,${data.audio_base64}`;
                this.playRefBtn.textContent = '■ Stop Reference';
                this.playRefBtn.disabled = false;
                await this.refAudioEl.play();
            } catch (err) {
                console.error('Reference playback failed:', err);
                stopRef();
                this.showAlert('Reference playback unavailable for this text.');
            }
        });
    }

    toggleRecording() {
        if (this.isRecording) {
            this.stopRecording();
        } else {
            this.startRecording();
        }
    }

    bindEvents() {
        if (this.eventsBound || this.destroyed) return;
        this.eventsBound = true;
        listen(this, window, 'beforeunload', () => this.destroy());

        // F5 toggle listener (disabled in Tauri mode - Tauri uses Tab instead)
        if (!window.__SPEECH_GUIDER_TAURI__ && !window.__TAURI__) {
            listen(this, document, 'keydown', (e) => {
                if (e.key === 'F5' && window.currentTab === 'analysis' && !e.repeat) {
                    e.preventDefault();
                    this.toggleRecording();
                }
            });
        }

        // Click / Space / Enter press-to-start / press-to-stop toggle on record button
        if (this.recordBtn) {
            listen(this, this.recordBtn, 'click', () => this.toggleRecording());
            listen(this, this.recordBtn, 'keydown', (e) => {
                if ((e.key === ' ' || e.key === 'Enter') && !e.repeat) {
                    e.preventDefault();
                    this.toggleRecording();
                }
            });
        }

        // File upload input
        if (this.audioInput) {
            listen(this, this.audioInput, 'change', (e) => {
                const file = e.target.files && e.target.files[0];
                if (file) {
                    this.handleFileUpload(file);
                }
            });
        }
    }

    async init() {
        if (this.destroyed) return;
        if (this.stream && this.mediaRecorder) return;
        if (this.initPromise) return this.initPromise;
        this.initPromise = this._initialize();
        return this.initPromise;
    }

    async _initialize() {
        if (this.recordBtn) this.recordBtn.disabled = getSettings().microphone_enabled === false;
        if (getSettings().microphone_enabled === false) {
            this.showPermissionPrompt('Microphone is off in Settings.', false);
            return;
        }
        document.getElementById('mic-permission-msg')?.remove();
        console.log('Initializing recorder...');
        console.log('Protocol:', this.location.protocol);
        console.log('Hostname:', this.location.hostname);
        console.log('navigator.mediaDevices:', navigator.mediaDevices);

        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            console.error('MediaDevices API not supported');
            console.log('Browser:', navigator.userAgent);
            this.showNotSupportedMessage();
            return;
        }

        const isLocalhost = this.location.hostname === 'localhost' || this.location.hostname === '127.0.0.1';
        const isHttps = this.location.protocol === 'https:';

        console.log('Is localhost:', isLocalhost);
        console.log('Is HTTPS:', isHttps);

        if (!isHttps && !isLocalhost) {
            console.error('HTTPS required for microphone access');
            this.showHttpsRequiredMessage();
            return;
        }

        const requestId = ++this.permissionRequestId;
        this.isStartingRecording = true;
        try {
            const stream = await openMicrophone();
            this.isStartingRecording = false;
            if (this.destroyed || requestId !== this.permissionRequestId) {
                stream.getTracks().forEach((track) => track.stop());
                return;
            }
            this.setupRecorder(stream);
            this.setupVisualizer(stream);

            if (this.recorderContainer) {
                this.recorderContainer.style.display = 'block';
            }
            if (this.fileUploadSection) {
                this.fileUploadSection.style.display = 'none';
            }
        } catch (err) {
            this.isStartingRecording = false;
            if (this.destroyed || requestId !== this.permissionRequestId) return;
            releaseCapture(this);
            this.mediaRecorder = null;
            console.error('Microphone access denied:', err);
            this.showPermissionPrompt(microphoneError(err));
        } finally {
            if (!this.destroyed) this.initPromise = null;
        }
    }

    async resetInput() {
        if (this.destroyed) return;
        this.stopRecording();
        const pending = this.initPromise;
        this.permissionRequestId += 1;
        releaseCapture(this);
        this.mediaRecorder = null;
        await pending;
        if (this.initPromise === pending) this.initPromise = null;
        if (window.currentTab === 'analysis') await this.init();
    }

    destroy() {
        this.disposeTrajectory?.();
        this.disposeTrajectory = null;
        if (this.destroyed) return;
        this.destroyed = true;
        this.permissionRequestId += 1;
        this.isStartingRecording = false;
        this.cancelOnStop = true;
        this.isRecording = false;
        clearInterval(this.timerInterval);
        clearTimeout(this.recordingTimeout);
        if (this.animationId) cancelAnimationFrame(this.animationId);
        this.animationId = null;
        if (this.mediaRecorder && this.mediaRecorder.state !== 'inactive') this.mediaRecorder.stop();
        this.eventListeners.forEach(([target, type, handler, options]) => target.removeEventListener(type, handler, options));
        this.eventListeners = [];
        releaseCapture(this);
        this.mediaRecorder = null;
        this.audioChunks = [];
        this.recordBtn?.classList.remove('recording');
    }

    showPermissionPrompt(message = 'Microphone access needed for recording', allowRetry = true) {
        const msgDiv = document.createElement('div');
        msgDiv.id = 'mic-permission-msg';
        msgDiv.className = 'text-center p-4 bg-yellow-50 border border-yellow-200 rounded mb-4';
        const detail = document.createElement('p');
        detail.className = 'text-yellow-800';
        detail.textContent = message;
        msgDiv.append(detail);
        if (allowRetry) {
            const retry = document.createElement('button');
            retry.type = 'button';
            retry.className = 'mt-3 bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700';
            retry.textContent = 'Retry microphone';
            retry.onclick = () => this.init();
            msgDiv.append(retry);
        }

        if (this.recorderContainer && !document.getElementById('mic-permission-msg')) {
            this.recorderContainer.parentNode.insertBefore(msgDiv, this.recorderContainer);
        }

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
        }

        if (this.fileUploadSection) {
            this.fileUploadSection.style.display = 'block';
        }
    }

    setupRecorder(stream) {
        this.stream = stream;
        this.mediaRecorder = new MediaRecorder(stream);

        this.mediaRecorder.ondataavailable = (e) => {
            if (e.data.size > 0) {
                this.audioChunks.push(e.data);
            }
        };

        this.mediaRecorder.onstop = () => {
            if (this.cancelOnStop || this.destroyed) return;
            this.sendForAnalysis();
        };
    }

    setupVisualizer(stream) {
        this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
        const source = this.audioContext.createMediaStreamSource(stream);
        this.visualizerSource = source;
        this.analyser = this.audioContext.createAnalyser();
        this.analyser.fftSize = 256;
        source.connect(this.analyser);

        const bufferLength = this.analyser.frequencyBinCount;
        this.dataArray = new Uint8Array(bufferLength);
    }

    startRecording() {
        if (this.destroyed || this.isStartingRecording || this.isRecording || !this.mediaRecorder) return;

        this.isRecording = true;
        this.audioChunks = [];
        this.startTime = Date.now();

        if (this.recordBtn) {
            this.recordBtn.classList.add('recording');
            const btnText = this.recordBtn.querySelector('.btn-text');
            if (btnText) btnText.textContent = 'Stop Recording';
        }

        this.timerInterval = setInterval(() => {
            const elapsed = Date.now() - this.startTime;
            const seconds = Math.floor(elapsed / 1000);
            const minutes = Math.floor(seconds / 60);
            const display = `${minutes.toString().padStart(2, '0')}:${(seconds % 60).toString().padStart(2, '0')}`;
            if (this.recTimer) {
                this.recTimer.textContent = display;
            }
        }, 100);

        this.mediaRecorder.start(100);
        this.drawWaveform();

        this.recordingTimeout = setTimeout(() => {
            if (this.isRecording) {
                console.log('Max duration reached, stopping recording');
                this.stopRecording();
            }
        }, this.maxDuration * 1000);
    }

    stopRecording() {
        if (this.destroyed) return;
        if (!this.isRecording) return;

        this.isRecording = false;
        clearInterval(this.timerInterval);
        clearTimeout(this.recordingTimeout);

        if (this.recordBtn) {
            this.recordBtn.classList.remove('recording');
            const btnText = this.recordBtn.querySelector('.btn-text');
            if (btnText) btnText.textContent = 'Press to Record';
        }

        if (this.animationId) {
            cancelAnimationFrame(this.animationId);
            this.animationId = null;
        }

        if (this.mediaRecorder && this.mediaRecorder.state !== 'inactive') {
            this.mediaRecorder.stop();
        }
    }

    drawWaveform() {
        if (!this.isRecording || !this.canvas || !this.canvasCtx) return;

        this.animationId = requestAnimationFrame(() => this.drawWaveform());
        this.analyser.getByteTimeDomainData(this.dataArray);

        this.canvasCtx.fillStyle = 'rgb(240, 240, 240)';
        this.canvasCtx.fillRect(0, 0, this.canvas.width, this.canvas.height);

        this.canvasCtx.lineWidth = 2;
        this.canvasCtx.strokeStyle = 'rgb(220, 38, 38)';
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

    showAlert(message) {
        this.clearAlert();
        const alertEl = document.createElement('div');
        alertEl.id = 'analysis-alert';
        alertEl.setAttribute('role', 'alert');
        alertEl.className = 'mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700';
        alertEl.textContent = message;

        const feedbackContainer = document.getElementById('feedback-container');
        if (feedbackContainer) {
            feedbackContainer.prepend(alertEl);
        } else if (this.recorderContainer?.parentNode) {
            this.recorderContainer.parentNode.insertBefore(alertEl, this.recorderContainer);
        }
    }

    clearAlert() {
        document.getElementById('analysis-alert')?.remove();
    }

    async sendForAnalysis() {
        if (this.destroyed || this.audioChunks.length === 0) {
            console.error('No audio recorded');
            return;
        }

        const audioBlob = new Blob(this.audioChunks, { type: this.mediaRecorder?.mimeType || this.audioChunks[0]?.type });

        try {
            const wavBlob = await this.convertToWav(audioBlob);
            if (!this.destroyed) await this.submitAudioBlob(wavBlob, 'recording.wav');
        } catch (error) {
            console.error('Audio conversion failed:', error);
            if (!this.destroyed) {
                this.showAlert('Failed to process recorded audio: ' + error.message);
            }
        } finally {
            if (this.recTimer) {
                this.recTimer.textContent = '00:00';
            }
        }
    }

    async submitAudioBlob(wavBlob, filename) {
        const targetTextInput = document.getElementById('target_text');
        const targetText = targetTextInput ? targetTextInput.value : '';

        if (!targetText.trim()) {
            this.showAlert('Please enter the target sentence first');
            return;
        }
        this.clearAlert();

        const formData = new FormData();
        formData.append('audio', wavBlob, filename);
        formData.append('target_text', targetText);

        const progressContainer = document.getElementById('progress-container');
        if (progressContainer) progressContainer.classList.remove('hidden');

        const progress = await openAnalysisProgress((update) => {
            const bar = document.getElementById('progress-bar');
            const text = document.getElementById('progress-text');
            if (bar) bar.style.width = `${Math.max(0, Math.min(1, update.progress)) * 100}%`;
            if (text) text.textContent = update.message;
        });
        if (progress) formData.append('job_id', progress.jobId);
        try {
            const response = await fetch('/api/analyze', {
                method: 'POST',
                body: formData,
            });

            if (!response.ok) {
                const payload = await response.json().catch(() => null);
                throw new Error(payload?.detail || payload?.error || `HTTP ${response.status}: ${response.statusText}`);
            }

            const result = await response.json();
            if (!this.destroyed) this.displayResults(result, wavBlob);
        } catch (error) {
            console.error('Analysis failed:', error);
            this.showAlert('Analysis failed: ' + error.message);
        } finally {
            if (progress) progress.close();
            if (progressContainer) progressContainer.classList.add('hidden');
        }
    }

    async handleFileUpload(file) {
        const targetTextInput = document.getElementById('target_text');
        const targetText = targetTextInput ? targetTextInput.value : '';

        if (!targetText.trim()) {
            this.showAlert('Please enter the target sentence first');
            this._clearFileInput();
            return;
        }

        try {
            const wavBlob = await this.convertToWav(file);
            const basename = file.name.replace(/\.[^.]+$/, '') || 'upload';
            await this.submitAudioBlob(wavBlob, `${basename}.wav`);
        } catch (error) {
            console.error('File upload failed:', error);
            this.showAlert('Failed to process audio file: ' + error.message);
        } finally {
            this._clearFileInput();
        }
    }

    _clearFileInput() {
        if (this.audioInput) {
            this.audioInput.value = '';
        }
    }

    async convertToWav(audioBlob) {
        return convertAudioToWav(audioBlob, 16000, (buffer, length) => this.bufferToWave(buffer, length));
    }

    bufferToWave(buffer, length) {
        return encodePcmWav(buffer, length);
    }

    async openSyllableInComparisonLab(targetLabel, startTime, endTime) {
        const traj = this.lastAnalysisResult?.ssl_trajectory;
        const rate = traj?.frame_rate || 50;
        const frames = traj?.frames || [];
        const padStart = Math.max(0, Number(startTime) - 0.08);
        const padEnd = Math.max(padStart + 0.08, Number(endTime) + 0.08);
        const startFrame = Math.max(0, Math.floor(padStart * rate));
        const endFrame = Math.min(frames.length, Math.ceil(padEnd * rate) + 1);
        const slicedFrames = frames.slice(startFrame, endFrame);

        let slicedWav = null;
        if (this.lastAudioBlob) {
            try {
                slicedWav = await slicePcmWavBlob(this.lastAudioBlob, padStart, padEnd);
            } catch (err) {
                console.warn('Failed to slice student WAV, falling back to full audio:', err);
                slicedWav = this.lastAudioBlob;
            }
        }

        window.switchTab?.('comparison');
        if (window.comparisonLab?.loadStudentSliceAndReference) {
            await window.comparisonLab.loadStudentSliceAndReference(targetLabel, slicedFrames, slicedWav);
        } else {
            jumpToComparisonLab(targetLabel);
        }
    }

    _buildSyllableDiffSection(alignment, errors = []) {
        if (!alignment?.words?.length) return null;

        const card = document.createElement('div');
        card.id = 'syllable-diff-card';
        card.className = 'bg-white rounded-lg shadow-md p-6 mb-6';

        const header = document.createElement('div');
        header.className = 'flex flex-wrap items-baseline justify-between gap-2 mb-3';
        const title = document.createElement('h3');
        title.className = 'text-lg font-semibold text-gray-800';
        title.textContent = 'Speech Diff (Click any red/yellow syllable to compare)';
        const legend = document.createElement('div');
        legend.className = 'flex flex-wrap items-center gap-2 text-xs text-gray-600';
        legend.innerHTML = `
            <span class="inline-flex items-center gap-1"><span class="inline-block w-2.5 h-2.5 rounded-full bg-rose-400"></span> Mismatch</span>
            <span class="inline-flex items-center gap-1"><span class="inline-block w-2.5 h-2.5 rounded-full bg-amber-400"></span> Borderline</span>
            <span class="inline-flex items-center gap-1"><span class="inline-block w-2.5 h-2.5 rounded-full bg-gray-300"></span> Clear / Not reached</span>
        `;
        header.append(title, legend);
        card.appendChild(header);

        const flow = document.createElement('div');
        flow.className = 'flex flex-wrap items-center gap-2 leading-relaxed';

        alignment.words.forEach((wordObj) => {
            if (wordObj.not_reached) {
                const unread = document.createElement('span');
                unread.className = 'rounded border border-dashed border-gray-200 bg-gray-50 px-2 py-1 text-sm text-gray-400 line-through';
                unread.textContent = wordObj.word;
                unread.title = 'Not reached in this recording';
                flow.appendChild(unread);
                return;
            }

            const syls = Array.isArray(wordObj.syllables) && wordObj.syllables.length > 0
                ? wordObj.syllables
                : [{
                    syllable_index: 0,
                    phonemes_target: (wordObj.phonemes || []).map((p) => p.phoneme),
                    phonemes_predicted: (wordObj.phonemes || []).map((p) => p.predicted_phoneme || p.phoneme),
                    start_time: wordObj.start_time,
                    end_time: wordObj.end_time,
                    score: 0,
                    severity: 'clear',
                }];

            const wordGroup = document.createElement('div');
            wordGroup.className = 'inline-flex items-center rounded-md border border-gray-200 bg-white overflow-hidden shadow-sm';

            const wordLabel = document.createElement('span');
            wordLabel.className = 'px-2 py-1 text-sm font-medium text-gray-800 border-r border-gray-100';
            wordLabel.textContent = wordObj.word;
            wordGroup.appendChild(wordLabel);

            syls.forEach((syl) => {
                const targetStr = (syl.phonemes_target || []).join('');
                const predStr = (syl.phonemes_predicted || []).join('');
                const sev = syl.severity || 'clear';
                let cls = 'px-1.5 py-1 text-xs font-mono transition ';
                if (sev === 'red') {
                    cls += 'bg-rose-100 text-rose-900 hover:bg-rose-200 font-semibold';
                } else if (sev === 'yellow') {
                    cls += 'bg-amber-100 text-amber-900 hover:bg-amber-200 font-semibold';
                } else {
                    cls += 'bg-gray-50 text-gray-600 hover:bg-gray-100';
                }

                const btn = document.createElement('button');
                btn.type = 'button';
                btn.className = cls;
                btn.textContent = `/${targetStr}/`;
                btn.title = sev === 'clear'
                    ? `/${targetStr}/ (${Number(syl.start_time).toFixed(2)}s)`
                    : `Expected /${targetStr}/ · heard closer to /${predStr}/ — click to compare in Comparison Lab`;
                btn.addEventListener('click', () => {
                    this.disposeTrajectory?.seekTo?.(syl.start_time, syl.end_time, wordObj.word);
                    const matchingErrIndex = errors.findIndex(
                        (err) => err.word_context === wordObj.word
                            && Number(err.start_time) >= Number(syl.start_time) - 0.02
                            && Number(err.end_time) <= Number(syl.end_time) + 0.02,
                    );
                    if (matchingErrIndex !== -1) {
                        window.selectError?.(matchingErrIndex);
                    }
                    if (sev === 'red' || sev === 'yellow') {
                        void this.openSyllableInComparisonLab(wordObj.word, syl.start_time, syl.end_time);
                    }
                });
                wordGroup.appendChild(btn);
            });

            flow.appendChild(wordGroup);
        });

        card.appendChild(flow);
        return card;
    }

    _buildWeaknessSummarySection(diagnostics) {
        const items = diagnostics?.weakness_summary;
        if (!Array.isArray(items) || items.length === 0) return null;

        const card = document.createElement('div');
        card.id = 'weakness-summary-card';
        card.className = 'bg-amber-50/70 border border-amber-200 rounded-lg p-5 mb-6';

        const title = document.createElement('h3');
        title.className = 'text-base font-semibold text-amber-950 mb-2';
        title.textContent = 'Detected Weaknesses & Focused Practice';
        card.appendChild(title);

        const list = document.createElement('ul');
        list.className = 'space-y-2';

        items.forEach((item) => {
            const li = document.createElement('li');
            li.className = 'flex flex-wrap items-center justify-between gap-2 rounded bg-white border border-amber-200/80 px-3 py-2 text-sm';

            const textSpan = document.createElement('span');
            textSpan.className = 'text-gray-800';
            textSpan.textContent = item.summary_text;

            const actions = document.createElement('div');
            actions.className = 'flex flex-wrap items-center gap-2 shrink-0';

            if (item.sample_word) {
                const compareBtn = document.createElement('button');
                compareBtn.type = 'button';
                compareBtn.className = 'rounded border border-blue-300 bg-blue-50 px-2.5 py-1 text-xs font-medium text-blue-700 hover:bg-blue-100 transition';
                compareBtn.textContent = `Compare "${item.sample_word.word}" →`;
                compareBtn.addEventListener('click', () => {
                    void this.openSyllableInComparisonLab(
                        item.sample_word.comparison_prompt || item.sample_word.word,
                        item.sample_word.start_time,
                        item.sample_word.end_time,
                    );
                });
                actions.appendChild(compareBtn);
            }

            const drillBtn = document.createElement('button');
            drillBtn.type = 'button';
            drillBtn.className = 'rounded bg-amber-600 px-2.5 py-1 text-xs font-medium text-white hover:bg-amber-700 transition';
            drillBtn.textContent = 'Practice focused drill →';
            drillBtn.addEventListener('click', () => {
                this.selectDiagnosticPassage?.(item.drill_passage_id, { clearResults: true });
            });
            actions.appendChild(drillBtn);

            li.append(textSpan, actions);
            list.appendChild(li);
        });

        card.appendChild(list);
        return card;
    }

    _buildDiagnosticsSection(diagnostics) {
        if (!diagnostics || diagnostics.status !== 'available' || !Array.isArray(diagnostics.categories)) {
            return null;
        }
        const wrapper = document.createElement('div');
        wrapper.id = 'pronunciation-diagnostics-section';
        wrapper.className = 'bg-white rounded-lg shadow-md p-6 mb-6';

        const header = document.createElement('div');
        header.className = 'flex flex-wrap items-baseline justify-between gap-2 mb-4';
        const title = document.createElement('h3');
        title.className = 'text-lg font-semibold text-gray-800';
        title.textContent = 'Pronunciation Weakness Summary (6 Categories)';
        const badgeCount = document.createElement('span');
        badgeCount.className = 'text-xs text-gray-500';
        badgeCount.textContent = `${diagnostics.flagged_count || 0} word cue(s) highlighted`;
        header.append(title, badgeCount);
        wrapper.appendChild(header);

        const grid = document.createElement('div');
        grid.id = 'pronunciation-diagnostics-grid';
        grid.className = 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4';

        diagnostics.categories.forEach((cat) => {
            const card = document.createElement('div');
            card.className = 'rounded-lg border border-gray-200 p-4 flex flex-col justify-between bg-slate-50/50';
            card.setAttribute('data-category-id', cat.id);

            const top = document.createElement('div');
            const cardHeader = document.createElement('div');
            cardHeader.className = 'flex items-start justify-between gap-2 mb-1';
            const catTitle = document.createElement('h4');
            catTitle.className = 'text-sm font-semibold text-gray-800';
            catTitle.textContent = cat.title;

            const meta = STATUS_BADGE_META[cat.status] || STATUS_BADGE_META.not_tested;
            const statusBadge = document.createElement('span');
            statusBadge.className = `shrink-0 rounded-full border px-2 py-0.5 text-[11px] font-medium ${meta.className}`;
            statusBadge.textContent = meta.label;
            cardHeader.append(catTitle, statusBadge);

            const contrastEl = document.createElement('div');
            contrastEl.className = 'text-xs font-mono text-blue-700 mb-2';
            contrastEl.textContent = cat.contrast;

            const summaryEl = document.createElement('p');
            summaryEl.className = 'text-xs text-gray-600 mb-3';
            summaryEl.textContent = cat.summary;

            top.append(cardHeader, contrastEl, summaryEl);
            card.appendChild(top);

            if (Array.isArray(cat.flagged_words) && cat.flagged_words.length > 0) {
                const wordsContainer = document.createElement('div');
                wordsContainer.className = 'flex flex-wrap gap-1.5 pt-2 border-t border-gray-200';

                cat.flagged_words.forEach((item) => {
                    const chipGroup = document.createElement('div');
                    chipGroup.className = 'inline-flex items-center rounded border border-amber-300 bg-white overflow-hidden text-xs';

                    const seekBtn = document.createElement('button');
                    seekBtn.type = 'button';
                    seekBtn.className = 'px-2 py-1 font-medium text-gray-800 hover:bg-amber-50 transition';
                    seekBtn.textContent = `${item.word} (/${item.target_phoneme}/)`;
                    seekBtn.title = item.evidence_summary || '';
                    seekBtn.addEventListener('click', () => {
                        this.disposeTrajectory?.seekTo?.(item.start_time, item.end_time, item.word);
                        if (Number.isInteger(item.error_index)) {
                            window.selectError?.(item.error_index);
                        }
                    });

                    const compareBtn = document.createElement('button');
                    compareBtn.type = 'button';
                    compareBtn.className = 'px-1.5 py-1 border-l border-amber-200 text-blue-600 hover:bg-blue-50 font-medium transition';
                    compareBtn.textContent = 'Compare →';
                    compareBtn.title = `Compare your "${item.word}" slice in Comparison Lab`;
                    compareBtn.addEventListener('click', () => {
                        void this.openSyllableInComparisonLab(
                            item.comparison_prompt || item.word,
                            item.start_time,
                            item.end_time,
                        );
                    });

                    chipGroup.append(seekBtn, compareBtn);
                    wordsContainer.appendChild(chipGroup);
                });

                card.appendChild(wordsContainer);
            }

            grid.appendChild(card);
        });

        wrapper.appendChild(grid);

        if (diagnostics.disclaimer) {
            const disclaimer = document.createElement('p');
            disclaimer.className = 'mt-4 text-xs text-gray-500';
            disclaimer.textContent = diagnostics.disclaimer;
            wrapper.appendChild(disclaimer);
        }

        return wrapper;
    }

    displayResults(result, blob = null) {
        this.disposeTrajectory?.();
        this.disposeTrajectory = null;
        this.lastAudioBlob = blob;
        this.lastAnalysisResult = result;

        this.clearAlert();
        const feedbackContainer = document.getElementById('feedback-container');
        if (feedbackContainer) {
            if (result.success || result.status === 'partial') {
                feedbackContainer.innerHTML = `
                    <div class="bg-white rounded-lg shadow-md p-6 mb-6">
                        <div class="prose max-w-none">
                            ${result.feedback}
                        </div>
                        <div class="mt-4 pt-3 border-t border-gray-100">
                            <button type="button" id="analysis-compare-cta" class="inline-flex items-center rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 transition">
                                Compare with Reference in Comparison Lab →
                            </button>
                        </div>
                    </div>
                `;
                const compareBtn = feedbackContainer.querySelector('#analysis-compare-cta');
                if (compareBtn) {
                    compareBtn.addEventListener('click', () => jumpToComparisonLab());
                }

                const diffEl = this._buildSyllableDiffSection(result.alignment, result.errors || []);
                if (diffEl) {
                    feedbackContainer.appendChild(diffEl);
                }

                const weaknessEl = this._buildWeaknessSummarySection(result.pronunciation_diagnostics);
                if (weaknessEl) {
                    feedbackContainer.appendChild(weaknessEl);
                }

                const diagnosticsEl = this._buildDiagnosticsSection(result.pronunciation_diagnostics);
                if (diagnosticsEl) {
                    feedbackContainer.appendChild(diagnosticsEl);
                }

                if (result.status === 'partial') {
                    const warning = document.createElement('p');
                    warning.className = 'bg-red-50 text-red-700 p-4';
                    warning.setAttribute('role', 'alert');
                    warning.textContent = result.ssl_warning || result.message;
                    feedbackContainer.prepend(warning);
                }
            } else {
                const errorCard = document.createElement('div');
                errorCard.className = 'bg-red-50 border border-red-200 rounded-lg p-6';
                const errorText = document.createElement('p');
                errorText.className = 'text-red-700';
                errorText.textContent = result.error || 'Analysis failed';
                errorCard.appendChild(errorText);
                feedbackContainer.replaceChildren(errorCard);
            }
        }

        const modelVersion = result.integration_meta?.model_version || 'r4';
        this.disposeTrajectory = showAnalysisTrajectory(feedbackContainer, result.ssl_trajectory, blob, {
            modelVersion,
        });

        const artSection = document.getElementById('articulatory-section');
        if (Array.isArray(result.errors) && result.errors.length > 0) {
            if (artSection) {
                artSection.classList.remove('hidden');
                this.populateErrors(result.errors);
            }
        } else {
            artSection?.classList.add('hidden');
            document.getElementById('error-list')?.replaceChildren();
            window.currentErrors = [];
            window.svgLeftRenderer?.stopAnimation();
            window.svgRightRenderer?.stopAnimation();
        }
    }

    populateErrors(errors) {
        window.currentErrors = errors;

        const errorList = document.getElementById('error-list');
        if (!errorList) {
            return;
        }

        errorList.innerHTML = '';

        errors.forEach((error, index) => {
            const btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'w-full text-left px-4 py-3 border border-gray-200 rounded hover:bg-gray-50 transition mb-2';
            const wrap = window.wrapIPATooltip || ((p) => p);
            btn.innerHTML = `
                <div class="flex items-center justify-between gap-2">
                    <div>
                        <span class="font-medium">${index + 1}.</span>
                        <span class="text-gray-700" data-word-context></span>
                        <span class="text-green-600">${wrap(error.target_phoneme)}</span>
                        <span class="text-gray-400">→</span>
                        <span class="text-red-600">${wrap(error.predicted_phoneme)}</span>
                    </div>
                    <span class="text-xs text-gray-500" data-time-span></span>
                </div>
                <div class="text-xs text-gray-500 mt-1" data-evidence></div>
            `;
            btn.querySelector('[data-word-context]').textContent = `'${error.word_context}':`;
            const timeEl = btn.querySelector('[data-time-span]');
            if (timeEl && Number.isFinite(Number(error.start_time))) {
                timeEl.textContent = `${Number(error.start_time).toFixed(2)}s`;
            }
            const evidenceEl = btn.querySelector('[data-evidence]');
            if (evidenceEl) {
                evidenceEl.textContent = error.evidence_summary || '';
            }
            btn.onclick = () => {
                if (Number.isFinite(Number(error.start_time))) {
                    this.disposeTrajectory?.seekTo?.(error.start_time, error.end_time, error.word_context);
                }
                window.selectError?.(index);
            };
            errorList.appendChild(btn);
        });
    }
}

if (typeof document !== 'undefined' && document.addEventListener) {
    document.addEventListener('DOMContentLoaded', () => {
        const recordBtn = document.getElementById('record-btn');
        const recorderContainer = document.getElementById('recorder');

        if (!recordBtn || !recorderContainer) {
            return;
        }

        window.recorder?.destroy?.();
        window.recorder = new IntercomRecorder();
        recorderContainer.style.display = 'block';

        window.recorder.init().catch((err) => {
            console.error('Failed to initialize recorder:', err);
        });
    });
}

export { IntercomRecorder };

if (typeof window !== 'undefined') {
    window.IntercomRecorder = IntercomRecorder;
}
