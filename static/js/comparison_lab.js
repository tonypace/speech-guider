/**
 * Comparison Lab - UI module for side-by-side articulatory comparison
 *
 * Manages:
 * - Explicit reference generation for the target sentence
 * - Side-by-side animation containers
 * - Timeline controls: play/pause, scrub, speed, loop
 * - Student recording integration
 */

import { convertAudioToWav, encodePcmWav } from './audio_conversion.js';
import { listen } from './capture_resources.js';
import { getSettings, microphoneError, openMicrophone } from './microphone.js';
import { SSLComparisonController } from './ssl_comparison_controller.js';
import { SvgArticulatoryRenderer } from './svg_articulatory_renderer.js';

class ComparisonLab {
    constructor() {
        this.controller = null;
        this.refRenderer = null;
        this.studentRenderer = null;
        this.currentTargetText = '';
        this.referenceLoaded = false;
        this.studentLoaded = false;
        this.isRecording = false;
        this.isStartingRecording = false;
        this.isAnalyzingRecording = false;
        this.mediaRecorder = null;
        this.recordedChunks = [];
        this.destroyed = false;
        this.eventListeners = [];
        this.stream = null;
        this.initialized = false;

        // Pending request tracking
        this.pendingRequestController = null;
        this.currentRequestId = 0; // Incremental ID to detect stale requests
        this.studentRequestId = 0;
        this.permissionRequestId = 0;

        // Bind methods
        this.handleTextInput = this.handleTextInput.bind(this);
        this.generateReference = this.generateReference.bind(this);
        this.handleScrub = this.handleScrub.bind(this);
        this.handlePlayPause = this.handlePlayPause.bind(this);
        this.handleSpeedChange = this.handleSpeedChange.bind(this);
        this.handleLoopToggle = this.handleLoopToggle.bind(this);
        this.handleLinkToggle = this.handleLinkToggle.bind(this);
        this.startRecording = this.startRecording.bind(this);
        this.stopRecording = this.stopRecording.bind(this);
        this.onReferenceFrame = this.onReferenceFrame.bind(this);
        this.onStudentFrame = this.onStudentFrame.bind(this);
        this.onPlayStateChange = this.onPlayStateChange.bind(this);
    }

    /**
   * Initialize the Comparison Lab
   */
    init() {
        if (this.initialized || this.destroyed) return;
        this.initialized = true;
        this.setupController();
        this.setupEventListeners();
        this.initRenderers();
        this.updateUIState();
    }

    /**
   * Initialize SVG articulatory renderers for comparison lab
   */
    initRenderers() {
        const reference = document.getElementById('comparison-ref-animation');
        const student = document.getElementById('comparison-student-animation');
        if (reference) this.refRenderer = new SvgArticulatoryRenderer(reference, { prefix: 'comparison-reference' });
        if (student) this.studentRenderer = new SvgArticulatoryRenderer(student, { prefix: 'comparison-student' });
    }

    /**
   * Update reference scrub bar and time display
   */
    updateReferenceScrub(time) {
        const scrubBar = document.getElementById('comparison-ref-scrub');
        if (scrubBar && this.controller) {
            const duration = this.controller.getDuration('reference');
            scrubBar.value = duration > 0 ? (time / duration) * 100 : 0;
        }

        const timeDisplay = document.getElementById('comparison-ref-time');
        if (timeDisplay) {
            timeDisplay.textContent = this.formatTime(time);
        }
    }

    /**
   * Update student scrub bar and time display
   */
    updateStudentScrub(time) {
        const scrubBar = document.getElementById('comparison-student-scrub');
        if (scrubBar && this.controller) {
            const duration = this.controller.getDuration('student');
            scrubBar.value = duration > 0 ? (time / duration) * 100 : 0;
        }

        const timeDisplay = document.getElementById('comparison-student-time');
        if (timeDisplay) {
            timeDisplay.textContent = this.formatTime(time);
        }
    }

    /**
   * Setup the SSL comparison controller
   */
    setupController() {
        this.controller = new SSLComparisonController({
            onReferenceFrame: this.onReferenceFrame,
            onStudentFrame: this.onStudentFrame,
            onPlayStateChange: this.onPlayStateChange,
            onPlaybackError: (type) => {
                if (type === 'reference') this.showReferenceStatus('error', 'Reference audio could not play.');
                else this.showStudentStatus('error', 'Recording audio could not play.');
            },
            defaultSpeed: 0.3,
            linkedPlayheads: true,
        });
    }

    /**
   * Setup event listeners for UI elements
   */
    setupEventListeners() {
        listen(this, window, 'beforeunload', () => this.destroy());
        listen(this, window, 'speechguider:settingschange', ({ detail: { previous, next } }) => {
            if (previous.contact_enabled !== next.contact_enabled) {
                const text = this.currentTargetText;
                this.clear();
                this.currentTargetText = text;
                this.showReferenceStatus(text ? 'idle' : 'empty');
                this.showStudentStatus('idle');
            }
            this.updateUIState();
        });
        const textInput = document.getElementById('comparison-target-text');
        if (textInput) {
            listen(this, textInput, 'input', this.handleTextInput);
        }
        const form = document.getElementById('comparison-reference-form');
        if (form) {
            listen(this, form, 'submit', (event) => {
                event.preventDefault();
                const generate = document.getElementById('comparison-generate');
                if (generate && !generate.disabled && this.currentTargetText) {
                    void this.generateReference(this.currentTargetText);
                }
            });
        }
        const fullscreen = document.getElementById('comparison-fullscreen');
        if (fullscreen) {
            listen(this, fullscreen, 'click', () => this.toggleFullscreen());
            listen(this, document, 'fullscreenchange', () => {
                if (!document.fullscreenElement) this.setExpanded(false);
            });
            listen(this, document, 'keydown', (event) => {
                if (event.key === 'Escape' && fullscreen.getAttribute('aria-pressed') === 'true') {
                    this.exitFullscreen();
                }
            });
        }

        // Scrub bars
        const refScrub = document.getElementById('comparison-ref-scrub');
        const studentScrub = document.getElementById('comparison-student-scrub');
        if (refScrub) {
            listen(this, refScrub, 'input', (e) => this.handleScrub('reference', e.target.value));
        }
        if (studentScrub) {
            listen(this, studentScrub, 'input', (e) => this.handleScrub('student', e.target.value));
        }

        // Play/pause buttons
        const refPlayBtn = document.getElementById('comparison-ref-play');
        const studentPlayBtn = document.getElementById('comparison-student-play');
        if (refPlayBtn) {
            listen(this, refPlayBtn, 'click', () => this.handlePlayPause('reference'));
        }
        if (studentPlayBtn) {
            listen(this, studentPlayBtn, 'click', () => this.handlePlayPause('student'));
        }

        // Speed selector
        const speedSelect = document.getElementById('comparison-speed');
        if (speedSelect) {
            listen(this, speedSelect, 'change', this.handleSpeedChange);
        }

        // Loop toggle
        const loopToggle = document.getElementById('comparison-loop');
        if (loopToggle) {
            listen(this, loopToggle, 'change', this.handleLoopToggle);
        }

        // Link playheads toggle
        const linkToggle = document.getElementById('comparison-link');
        if (linkToggle) {
            listen(this, linkToggle, 'change', this.handleLinkToggle);
        }

        const matchToggle = document.getElementById('comparison-match-duration');
        if (matchToggle) {
            listen(this, matchToggle, 'change', () => {
                this.controller.setDurationMatching(matchToggle.checked);
                this.updateDurationMatching();
            });
        }

        // Record button
        const recordBtn = document.getElementById('comparison-record-btn');
        if (recordBtn) {
            listen(this, recordBtn, 'click', () => {
                if (this.isRecording) {
                    this.stopRecording();
                } else {
                    this.startRecording();
                }
            });
        }

        // Loop markers
        const loopInBtn = document.getElementById('comparison-loop-in');
        const loopOutBtn = document.getElementById('comparison-loop-out');
        if (loopInBtn) {
            listen(this, loopInBtn, 'click', () => this.setLoopIn());
        }
        if (loopOutBtn) {
            listen(this, loopOutBtn, 'click', () => this.setLoopOut());
        }
    }

    handleTextInput(event) {
        const text = event.target.value.trim();
        if (text === this.currentTargetText) return;
        this.clear();
        this.currentTargetText = text;
        this.showReferenceStatus(text ? 'idle' : 'empty');
        this.showStudentStatus('idle');
        this.updateUIState();
    }

    setExpanded(expanded) {
        document.getElementById('tab-panel-comparison')?.classList.toggle('comparison-expanded', expanded);
        const button = document.getElementById('comparison-fullscreen');
        if (button) {
            button.textContent = expanded ? 'Exit full screen' : 'Full screen';
            button.setAttribute('aria-pressed', String(expanded));
        }
    }

    async toggleFullscreen() {
        const panel = document.getElementById('tab-panel-comparison');
        if (!panel) return;
        if (panel.classList.contains('comparison-expanded')) {
            this.exitFullscreen();
            return;
        }
        this.setExpanded(true);
        try {
            if (document.fullscreenEnabled) await panel.requestFullscreen();
        } catch {
            // The expanded view also works in webviews without native fullscreen.
        }
    }

    exitFullscreen() {
        this.setExpanded(false);
        if (document.fullscreenElement?.id === 'tab-panel-comparison') {
            void document.exitFullscreen().catch(() => {});
        }
    }

    leave() {
        this.exitFullscreen();
        this.controller?.pause('reference');
        this.controller?.pause('student');
        this.stopRecording();
    }

    /**
   * Generate reference audio and animation
   */
    async generateReference(text, generation = ++this.currentRequestId) {
    // Increment request ID to track staleness
        const requestId = generation;

        const requestController = new AbortController();
        this.pendingRequestController = requestController;
        this.showReferenceStatus('preparing');
        this.updateUIState();

        try {
            const response = await fetch('/api/reference-animation', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ target_text: text, tts_provider: 'omnivoice' }),
                signal: requestController.signal,
            });

            if (!response.ok) {
                const { detail } = await response.json().catch(() => null) || {};
                if (Array.isArray(detail)) {
                    const messages = detail.map(issue => issue?.msg).filter(message => typeof message === 'string');
                    if (messages.length) throw new Error(messages.join(' '));
                }
                throw new Error(typeof detail === 'string' ? detail : (
                    response.status === 503
                        ? 'Analysis worker is busy. Wait for the current request to finish, then retry.'
                        : `Reference generation failed: ${response.status}`
                ));
            }

            const data = await response.json();

            // Check if this is a stale response (user changed text while we were generating)
            if (requestId !== this.currentRequestId) {
                console.log('[ComparisonLab] Ignoring stale response for:', text);
                return;
            }

            // Check if text still matches what we expected
            if (this.currentTargetText !== text) {
                console.log('[ComparisonLab] Text changed during generation, ignoring result for:', text);
                this.showReferenceStatus('preparing');
                return;
            }

            // Load into controller
            const loaded = await this.controller.loadReference(data.frames, data.audio_base64, () => requestId === this.currentRequestId);
            if (loaded === false || requestId !== this.currentRequestId) return;

            this.referenceLoaded = true;
            this.showReferenceStatus(data.cached ? 'cached' : 'ready');
            this.updateUIState();

            // If we also have student data, auto-start comparison
            if (this.studentLoaded) {
                this.syncPlayheads();
            }
        } catch (error) {
            if (error.name === 'AbortError') {
                console.log('[ComparisonLab] Request cancelled for:', text);
                // Don't show error for cancelled requests
                return;
            }

            // Log detailed error info
            console.error('[ComparisonLab] Reference generation FAILED for:', text);
            console.error('[ComparisonLab] Error type:', error.name);
            console.error('[ComparisonLab] Error message:', error.message);
            console.error('[ComparisonLab] Request ID:', requestId, 'Current ID:', this.currentRequestId);

            // Only show error if this is still the current request
            if (requestId === this.currentRequestId) {
                this.showReferenceStatus('error', error.message);
            }
        } finally {
            // Only clear if this is our request
            if (requestId === this.currentRequestId) {
                this.pendingRequestController = null;
                this.updateUIState();
            }
        }
    }

    /**
   * Show reference preparation status
   */
    showReferenceStatus(status, errorMessage = null) {
        const statusEl = document.getElementById('comparison-ref-status');
        if (!statusEl) return;

        const statusMap = {
            empty: { text: 'Enter text to generate a reference.', class: 'text-gray-500' },
            idle: { text: 'Ready to generate a reference.', class: 'text-gray-500' },
            preparing: { text: 'Preparing reference...', class: 'text-amber-600' },
            ready: { text: 'Reference ready', class: 'text-green-600' },
            cached: { text: 'Reference ready (cached)', class: 'text-green-600' },
            error: { text: errorMessage ? `Error: ${errorMessage}` : 'Reference generation failed', class: 'text-red-600' },
        };

        const info = statusMap[status] || statusMap.error;
        statusEl.textContent = info.text;
        statusEl.className = `text-sm ${info.class}`;
    }

    /**
   * Handle scrub bar input
   */
    handleScrub(type, value) {
        if (!this.controller) return;

        const duration = this.controller.getDuration(type);
        const time = (value / 100) * duration;
        this.controller.setTime(type, time);
    }

    /**
   * Handle play/pause button
   */
    handlePlayPause(type) {
        if (!this.controller) return;
        if (this.controller.linkedPlayheads) {
            this.controller.pause(type === 'reference' ? 'student' : 'reference');
        }
        this.controller.togglePlay(type);
    }

    /**
   * Handle speed change
   */
    handleSpeedChange(event) {
        if (!this.controller) return;
        const speed = parseFloat(event.target.value);
        this.controller.setSpeed(speed);
    }

    /**
   * Handle loop toggle
   */
    handleLoopToggle(event) {
        if (!this.controller) return;
        const enabled = event.target.checked;
        if (enabled) {
            // Set default loop region to full duration if not set
            const refDuration = this.controller.getDuration('reference');
            this.controller.setLoopRegion(0, refDuration * 0.5, true);
        } else {
            this.controller.setLoopRegion(0, 0, false);
        }
    }

    /**
   * Set loop in point to current position
   */
    setLoopIn() {
        if (!this.controller) return;
        const currentLoop = this.controller.loopRegion;
        this.controller.setLoopRegion(
            this.controller.referenceTime,
            currentLoop.end,
            currentLoop.enabled
        );
    }

    /**
   * Set loop out point to current position
   */
    setLoopOut() {
        if (!this.controller) return;
        const currentLoop = this.controller.loopRegion;
        this.controller.setLoopRegion(
            currentLoop.start,
            this.controller.referenceTime,
            currentLoop.enabled
        );
    }

    /**
   * Handle link playheads toggle
   */
    handleLinkToggle(event) {
        if (!this.controller) return;
        this.controller.setLinkedPlayheads(event.target.checked);
    }

    /**
   * Callback when reference frame updates
   */
    onReferenceFrame(frame, time) {
        this.refRenderer?.setState(frame);
        this.updateReferenceScrub(time);
    }

    /**
   * Callback when student frame updates
   */
    onStudentFrame(frame, time) {
        this.studentRenderer?.setState(frame);
        this.updateStudentScrub(time);
    }

    /**
   * Callback when play state changes
   */
    onPlayStateChange(refPlaying, studentPlaying) {
        const refBtn = document.getElementById('comparison-ref-play');
        const studentBtn = document.getElementById('comparison-student-play');

        if (refBtn) {
            refBtn.textContent = refPlaying ? '⏸' : '▶';
            refBtn.setAttribute('aria-label', refPlaying ? 'Pause reference' : 'Play reference');
            refBtn.classList.toggle('bg-amber-500', refPlaying);
            refBtn.classList.toggle('bg-blue-500', !refPlaying);
        }

        if (studentBtn) {
            studentBtn.textContent = studentPlaying ? '⏸' : '▶';
            studentBtn.setAttribute('aria-label', studentPlaying ? 'Pause your recording' : 'Play your recording');
            studentBtn.classList.toggle('bg-amber-500', studentPlaying);
            studentBtn.classList.toggle('bg-blue-500', !studentPlaying);
        }
    }

    /**
   * Start recording student audio
   */
    async startRecording() {
        if (this.destroyed || this.isRecording || this.isStartingRecording || this.isAnalyzingRecording) return;
        this.isStartingRecording = true;
        this.updateUIState();
        const permission = ++this.permissionRequestId;
        try {
            const stream = await openMicrophone();
            if (this.destroyed || permission !== this.permissionRequestId || !this.isStartingRecording || this.isRecording) {
                stream.getTracks().forEach((track) => track.stop());
                return;
            }
            this.isStartingRecording = false;
            this.controller?.pause('reference');
            this.controller?.pause('student');
            this.stream = stream;
            this.mediaRecorder = new MediaRecorder(stream);
            this.recordedChunks = [];

            this.mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    this.recordedChunks.push(event.data);
                }
            };

            this.mediaRecorder.onstop = () => {
                if (!this.destroyed) this.processRecording();
                // Stop all tracks
                stream.getTracks().forEach((track) => track.stop());
                if (this.stream === stream) this.stream = null;
            };

            this.mediaRecorder.start();
            this.isRecording = true;
            this.updateRecordButton();
            this.updateUIState();
            this.showStudentStatus('recording');
        } catch (error) {
            if (permission !== this.permissionRequestId) return;
            this.isStartingRecording = false;
            this.stream?.getTracks().forEach((track) => track.stop());
            this.stream = null;
            if (this.destroyed) return;
            console.error('[ComparisonLab] Recording error:', error);
            this.showStudentStatus('error', microphoneError(error));
            this.updateUIState();
        }
    }

    /**
   * Stop recording
   */
    stopRecording() {
        this.permissionRequestId++;
        this.isStartingRecording = false;
        if (this.mediaRecorder && this.isRecording) {
            this.isRecording = false;
            this.isAnalyzingRecording = true;
            this.mediaRecorder.stop();
            this.updateRecordButton();
        }
        this.updateUIState();
    }

    /**
   * Process recorded audio
   */
    async processRecording() {
        if (this.destroyed) return;
        const blob = new Blob(this.recordedChunks, { type: this.mediaRecorder?.mimeType || this.recordedChunks[0]?.type });
        const generation = ++this.studentRequestId;
        const targetText = this.currentTargetText;
        const isCurrent = () => !this.destroyed && generation === this.studentRequestId;
        this.isAnalyzingRecording = true;
        this.updateUIState();

        try {
            this.showStudentStatus('analyzing');
            // The packaged backend can analyze these recordings without ffmpeg.
            const wav = await convertAudioToWav(blob, 16000, (audio, length) => encodePcmWav(audio, length, true));
            if (!isCurrent()) return;
            const formData = new FormData();
            formData.append('audio', wav, 'recording.wav');
            formData.append('target_text', targetText);

            const response = await fetch('/api/analyze', {
                method: 'POST',
                body: formData,
            });

            const data = await response.json().catch(() => null);
            if (!response.ok) {
                const detail = data?.error || data?.detail || `HTTP ${response.status}`;
                throw new Error(`Analysis failed: ${detail}`);
            }
            if (!isCurrent()) return;
            if (!data?.ssl_trajectory?.frames?.length) {
                throw new Error(data?.ssl_warning || data?.error || 'No mouth movement was returned. Try recording again.');
            }
            const loaded = await this.controller.loadStudent(data.ssl_trajectory.frames, wav, isCurrent);
            if (!loaded || !isCurrent()) return;
            this.studentLoaded = true;
            this.showStudentStatus('ready');
        } catch (error) {
            console.error('[ComparisonLab] Analysis error:', error);
            if (isCurrent()) this.showStudentStatus('error', error.message);
        } finally {
            if (isCurrent()) {
                this.isAnalyzingRecording = false;
                this.updateUIState();
            }
        }
    }

    /**
   * Show student analysis status
   */
    showStudentStatus(status, errorMessage = '') {
        const statusEl = document.getElementById('comparison-student-status');
        if (!statusEl) return;

        const statusMap = {
            idle: { text: '', class: 'text-gray-500' },
            recording: { text: 'Recording. Click Stop when finished.', class: 'text-amber-600' },
            analyzing: { text: 'Analyzing pronunciation...', class: 'text-amber-600' },
            ready: { text: 'Student recording ready', class: 'text-green-600' },
            error: { text: errorMessage || 'Analysis failed', class: 'text-red-600' },
        };

        const info = statusMap[status] || statusMap.error;
        statusEl.textContent = info.text;
        statusEl.className = `text-sm ${info.class}`;
    }

    /**
   * Update record button UI
   */
    updateRecordButton() {
        const btn = document.getElementById('comparison-record-btn');
        if (!btn) return;

        if (this.isRecording) {
            btn.textContent = '⏹ Stop';
            btn.classList.remove('bg-red-500');
            btn.classList.add('bg-amber-500');
        } else {
            btn.textContent = '🔴 Record';
            btn.classList.remove('bg-amber-500');
            btn.classList.add('bg-red-500');
        }
    }

    /**
   * Sync playheads when both tracks loaded
   */
    syncPlayheads() {
        if (!this.controller) return;
        // Sync student to reference position
        const refDuration = this.controller.getDuration('reference');
        const studentDuration = this.controller.getDuration('student');
        if (refDuration > 0 && studentDuration > 0) {
            this.controller.setTime('student', 0);
            this.controller.setTime('reference', 0);
        }
    }

    /**
   * Update UI state based on loaded data
   */
    updateUIState() {
        const hasRef = this.referenceLoaded;
        const hasStudent = this.studentLoaded;
        const busy = Boolean(this.pendingRequestController || this.isStartingRecording || this.isAnalyzingRecording);
        const lockInput = busy || this.isRecording;
        const target = document.getElementById('comparison-target-text');
        const textLimit = Number(target?.dataset.textLimit);
        // Python counts Unicode code points, while JavaScript string length counts UTF-16 units.
        const textTooLong = Array.from(this.currentTargetText).length > textLimit;
        const generate = document.getElementById('comparison-generate');
        if (target) {
            target.disabled = lockInput;
            target.setAttribute('aria-invalid', String(textTooLong));
        }
        if (generate) generate.disabled = lockInput || !this.currentTargetText || textTooLong;
        if (textTooLong) this.showReferenceStatus('error', `Shorten the target text to ${textLimit} characters or fewer.`);
        this.updateDurationMatching(lockInput);

        // Enable/disable controls
        const controls = [
            'comparison-ref-play',
            'comparison-student-play',
            'comparison-ref-scrub',
            'comparison-student-scrub',
            'comparison-speed',
            'comparison-loop',
            'comparison-link',
        ];

        controls.forEach((id) => {
            const el = document.getElementById(id);
            if (el) {
                const canUse = (id.includes('ref') && hasRef) ||
                       (id.includes('student') && hasStudent) ||
                       (!id.includes('ref') && !id.includes('student') && (hasRef || hasStudent));
                el.disabled = !canUse || this.isRecording || this.isStartingRecording;
            }
        });

        // Record button needs reference
        const recordBtn = document.getElementById('comparison-record-btn');
        if (recordBtn) {
            const microphoneDisabled = getSettings().microphone_enabled === false;
            recordBtn.disabled = busy || !hasRef || microphoneDisabled;
            recordBtn.title = microphoneDisabled ? 'Microphone is off in Settings' : '';
        }
    }

    updateDurationMatching(busy = false) {
        const toggle = document.getElementById('comparison-match-duration');
        if (!toggle) return;
        const status = document.getElementById('comparison-match-status');
        const hasBoth = this.referenceLoaded && this.studentLoaded;
        const rate = hasBoth ? this.controller.getMatchRate() : null;
        toggle.disabled = busy || rate === null;
        toggle.checked = this.controller.durationMatching;
        if (!hasBoth) status.textContent = 'Record the full target text to match durations.';
        else if (rate === null) status.textContent = 'Timing match unavailable. Check that the whole sentence was recorded at a similar pace.';
        else if (toggle.checked) {
            status.textContent = `Recording plays at ${Math.round(rate * 100)}% of its original pace before the Speed setting.`;
        } else {
            status.textContent = 'Turn on after confirming you recorded all the words.';
        }
    }

    /**
   * Format seconds to MM:SS.ms
   */
    formatTime(seconds) {
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        const ms = Math.floor((seconds % 1) * 100);
        return `${mins}:${secs.toString().padStart(2, '0')}.${ms.toString().padStart(2, '0')}`;
    }

    /**
   * Clear all data
   */
    destroy() {
        if (this.destroyed) return;
        this.destroyed = true;
        this.permissionRequestId++;
        this.isStartingRecording = false;
        this.clear();
        this.eventListeners.forEach(([target, type, handler, options]) => target.removeEventListener(type, handler, options));
        this.eventListeners = [];
        if (this.mediaRecorder?.state === 'recording') this.mediaRecorder.stop();
        this.stream?.getTracks().forEach((track) => track.stop());
        this.stream = null;
        this.isRecording = false;
        this.controller?.destroy();
        this.exitFullscreen();
    }

    clear() {
        this.currentRequestId++;
        this.studentRequestId++;
        this.pendingRequestController?.abort();
        this.pendingRequestController = null;
        this.controller?.clear();
        for (const [renderer, text] of [[this.refRenderer, 'No reference loaded'], [this.studentRenderer, 'Record to compare']]) {
            if (renderer) {
                renderer.destroy();
                renderer.container.textContent = text;
            }
        }
        this.updateReferenceScrub(0);
        this.updateStudentScrub(0);
        this.referenceLoaded = false;
        this.studentLoaded = false;
        this.isAnalyzingRecording = false;
        this.currentTargetText = '';
        this.updateUIState();
    }
}

// Export for module usage
export { ComparisonLab };

// Create global instance and attach to window
window.ComparisonLab = ComparisonLab;
window.comparisonLab = null;

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('tab-panel-comparison')) {
        window.comparisonLab?.destroy?.();
        window.comparisonLab = new ComparisonLab();
        window.comparisonLab.init();
    }
});
