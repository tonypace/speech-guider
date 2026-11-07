/**
 * Comparison Lab - UI module for side-by-side articulatory comparison
 *
 * Manages:
 * - Target text input with debounced reference generation
 * - Side-by-side animation containers
 * - Timeline controls: play/pause, scrub, speed, zoom, loop
 * - Student recording integration
 */

import { convertAudioToWav, encodePcmWav } from './audio_conversion.js';
import { listen } from './capture_resources.js';
import { SSLComparisonController } from './ssl_comparison_controller.js';

class ComparisonLab {
    constructor() {
        this.controller = null;
        this.leftRenderer = null;
        this.rightRenderer = null;
        this.currentTargetText = '';
        this.referenceLoaded = false;
        this.studentLoaded = false;
        this.isRecording = false;
        this.isStartingRecording = false;
        this.mediaRecorder = null;
        this.recordedChunks = [];
        this.destroyed = false;
        this.eventListeners = [];
        this.stream = null;
        this.initialized = false;

        // Debounce timer
        this.debounceTimer = null;
        this.debounceDelay = 1500; // ms - wait 1.5 seconds after typing stops

        // Pending request tracking
        this.pendingRequestController = null;
        this.pendingRequestText = null; // What text we're generating for
        this.currentRequestId = 0; // Incremental ID to detect stale requests
        this.studentRequestId = 0;
        this.permissionRequestId = 0;

        // Bind methods
        this.handleTextInput = this.handleTextInput.bind(this);
        this.generateReference = this.generateReference.bind(this);
        this.handleScrub = this.handleScrub.bind(this);
        this.handlePlayPause = this.handlePlayPause.bind(this);
        this.handleSpeedChange = this.handleSpeedChange.bind(this);
        this.handleZoomChange = this.handleZoomChange.bind(this);
        this.handleLoopToggle = this.handleLoopToggle.bind(this);
        this.handleLinkToggle = this.handleLinkToggle.bind(this);
        this.startRecording = this.startRecording.bind(this);
        this.stopRecording = this.stopRecording.bind(this);
        this.onReferenceFrame = this.onReferenceFrame.bind(this);
        this.onStudentFrame = this.onStudentFrame.bind(this);
        this.onTimeUpdate = this.onTimeUpdate.bind(this);
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
    // Wait for SVGArticulatoryRenderer to be available
        const checkAndInit = () => {
            if (typeof SvgArticulatoryRenderer === 'undefined') {
                setTimeout(checkAndInit, 100);
                return;
            }

            // Initialize reference (left) renderer
            const refContainer = document.getElementById('comparison-ref-animation');
            if (refContainer && !this.refRenderer) {
                this.refRenderer = new SvgArticulatoryRenderer(refContainer, {
                    width: refContainer.clientWidth,
                    height: 256,
                    showLabels: true,
                });
                this.refRenderer.mount();

                // Override the callback to use this renderer
                this.controller.onReferenceFrame = (frame, time) => {
                    if (this.refRenderer && frame) {
                        this.refRenderer.setState(frame);
                    }
                    this.updateReferenceScrub(time);
                };
            }

            // Initialize student (right) renderer
            const studentContainer = document.getElementById('comparison-student-animation');
            if (studentContainer && !this.studentRenderer) {
                this.studentRenderer = new SvgArticulatoryRenderer(studentContainer, {
                    width: studentContainer.clientWidth,
                    height: 256,
                    showLabels: true,
                });
                this.studentRenderer.mount();

                // Override the callback to use this renderer
                this.controller.onStudentFrame = (frame, time) => {
                    if (this.studentRenderer && frame) {
                        this.studentRenderer.setState(frame);
                    }
                    this.updateStudentScrub(time);
                };
            }
        };

        checkAndInit();
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
            onTimeUpdate: this.onTimeUpdate,
            onPlayStateChange: this.onPlayStateChange,
            defaultSpeed: 1.0,
            linkedPlayheads: false,
        });
    }

    /**
   * Setup event listeners for UI elements
   */
    setupEventListeners() {
        listen(this, window, 'beforeunload', () => this.destroy());
        // Text input debounce
        const textInput = document.getElementById('comparison-target-text');
        if (textInput) {
            listen(this, textInput, 'input', this.handleTextInput);
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

        // Zoom slider
        const zoomSlider = document.getElementById('comparison-zoom');
        if (zoomSlider) {
            listen(this, zoomSlider, 'input', this.handleZoomChange);
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

    /**
   * Handle text input with debounce
   */
    handleTextInput(event) {
        const text = event.target.value.trim();
        const generation = ++this.currentRequestId;
        if (this.pendingRequestController) this.pendingRequestController.abort();
        this.pendingRequestController = null;
        this.pendingRequestText = null;

        // Cancel pending timer
        if (this.debounceTimer) {
            clearTimeout(this.debounceTimer);
            this.debounceTimer = null;
        }

        if (!text) {
            this.currentTargetText = '';
            this.referenceLoaded = false;
            if (this.controller) this.controller.clearTrack('reference');
            this.updateUIState();
            return;
        }

        this.referenceLoaded = false;
        this.updateUIState();

        // Show preparing indicator immediately
        this.showReferenceStatus('preparing');

        // If we already have a pending request for DIFFERENT text, cancel it
        // and start new generation immediately
        // Debounce generation - wait for user to stop typing
        this.debounceTimer = setTimeout(() => {
            this.debounceTimer = null;
            if (generation !== this.currentRequestId) return;
            this.currentTargetText = text;
            this.generateReference(text, generation);
        }, this.debounceDelay);
    }

    /**
   * Generate reference audio and animation
   */
    async generateReference(text, generation = ++this.currentRequestId) {
    // Increment request ID to track staleness
        const requestId = generation;

        // Track what we're generating
        this.pendingRequestText = text;
        const requestController = new AbortController();
        this.pendingRequestController = requestController;

        try {
            const response = await fetch('/api/reference-animation', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ target_text: text, tts_provider: 'omnivoice' }),
                signal: requestController.signal,
            });

            if (!response.ok) {
                throw new Error(`Reference generation failed: ${response.status}`);
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
            await this.controller.loadReference(data.frames, data.audio_base64, () => requestId === this.currentRequestId);
            if (requestId !== this.currentRequestId) return;

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
                this.pendingRequestText = null;
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
   * Handle zoom change
   */
    handleZoomChange(event) {
        if (!this.controller) return;
        const zoomLevel = parseInt(event.target.value, 10);
        // Zoom 1 = full view, zoom 10 = narrow window
        const windowSize = 1 / zoomLevel;
        const currentPos = 0.5 - windowSize / 2;
        this.controller.setZoomWindow(Math.max(0, currentPos), Math.min(1, currentPos + windowSize));
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
    onReferenceFrame() {
    // Handled by initRenderers override
    }

    /**
   * Callback when student frame updates
   */
    onStudentFrame() {
    // Handled by initRenderers override
    }

    /**
   * Callback when time updates
   */
    onTimeUpdate() {
    // Update any shared UI elements
    }

    /**
   * Callback when play state changes
   */
    onPlayStateChange(refPlaying, studentPlaying) {
        const refBtn = document.getElementById('comparison-ref-play');
        const studentBtn = document.getElementById('comparison-student-play');

        if (refBtn) {
            refBtn.textContent = refPlaying ? '⏸' : '▶';
            refBtn.classList.toggle('bg-amber-500', refPlaying);
            refBtn.classList.toggle('bg-blue-500', !refPlaying);
        }

        if (studentBtn) {
            studentBtn.textContent = studentPlaying ? '⏸' : '▶';
            studentBtn.classList.toggle('bg-amber-500', studentPlaying);
            studentBtn.classList.toggle('bg-blue-500', !studentPlaying);
        }
    }

    /**
   * Start recording student audio
   */
    async startRecording() {
        if (this.destroyed || this.isRecording || this.isStartingRecording) return;
        this.isStartingRecording = true;
        const permission = ++this.permissionRequestId;
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            if (this.destroyed || permission !== this.permissionRequestId || !this.isStartingRecording || this.isRecording) {
                stream.getTracks().forEach((track) => track.stop());
                return;
            }
            this.isStartingRecording = false;
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
        } catch (error) {
            if (permission !== this.permissionRequestId) return;
            this.isStartingRecording = false;
            this.stream?.getTracks().forEach((track) => track.stop());
            this.stream = null;
            if (this.destroyed) return;
            console.error('[ComparisonLab] Recording error:', error);
            alert('Could not access microphone. Please check permissions.');
        }
    }

    /**
   * Stop recording
   */
    stopRecording() {
        this.permissionRequestId++;
        this.isStartingRecording = false;
        if (this.mediaRecorder && this.isRecording) {
            this.mediaRecorder.stop();
            this.isRecording = false;
            this.updateRecordButton();
        }
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

            console.log('[ComparisonLab] Response status:', response.status);
            console.log('[ComparisonLab] Response headers:', Object.fromEntries(response.headers.entries()));

            // Try to parse response regardless of status
            const responseText = await response.text();
            console.log('[ComparisonLab] Response body:', responseText);

            if (!response.ok) {
                let errorBody;
                try {
                    errorBody = JSON.parse(responseText);
                } catch {
                    errorBody = { error: responseText };
                }
                const detail = errorBody?.error || errorBody?.detail || `HTTP ${response.status}`;
                throw new Error(`Analysis failed: ${detail}`);
            }

            const data = JSON.parse(responseText);
            if (this.destroyed || generation !== this.studentRequestId) return;

            // Load student trajectory if available
            if (data.ssl_trajectory && data.ssl_trajectory.frames) {
                await this.controller.loadStudent(data.ssl_trajectory.frames, wav, isCurrent);
                if (this.destroyed || generation !== this.studentRequestId) return;
                this.studentLoaded = true;
                this.showStudentStatus('ready');
                this.updateUIState();
            } else if (data.success) {
                // Analysis succeeded but no trajectory (fallback path)
                console.log('[ComparisonLab] Analysis succeeded but no SSL trajectory available');
                this.showStudentStatus('error', 'Analysis complete but SSL trajectory not available');
            } else {
                this.showStudentStatus('error', data.error || 'Analysis failed');
            }
        } catch (error) {
            console.error('[ComparisonLab] Analysis error:', error);
            if (generation === this.studentRequestId) this.showStudentStatus('error');
        }
    }

    /**
   * Show student analysis status
   */
    showStudentStatus(status) {
        const statusEl = document.getElementById('comparison-student-status');
        if (!statusEl) return;

        const statusMap = {
            analyzing: { text: 'Analyzing pronunciation...', class: 'text-amber-600' },
            ready: { text: 'Student recording ready', class: 'text-green-600' },
            error: { text: 'Analysis failed', class: 'text-red-600' },
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

        // Enable/disable controls
        const controls = [
            'comparison-ref-play',
            'comparison-student-play',
            'comparison-ref-scrub',
            'comparison-student-scrub',
            'comparison-speed',
            'comparison-zoom',
            'comparison-loop',
            'comparison-link',
        ];

        controls.forEach((id) => {
            const el = document.getElementById(id);
            if (el) {
                const canUse = (id.includes('ref') && hasRef) ||
                       (id.includes('student') && hasStudent) ||
                       (!id.includes('ref') && !id.includes('student') && (hasRef || hasStudent));
                el.disabled = !canUse;
            }
        });

        // Record button needs reference
        const recordBtn = document.getElementById('comparison-record-btn');
        if (recordBtn) {
            recordBtn.disabled = !hasRef;
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
        this.leftRenderer?.destroy?.();
        this.rightRenderer?.destroy?.();
    }

    clear() {
        this.currentRequestId++;
        this.studentRequestId++;
        clearTimeout(this.debounceTimer);
        this.pendingRequestController?.abort();
        if (this.controller) {
            this.controller.clear();
        }
        this.referenceLoaded = false;
        this.studentLoaded = false;
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
